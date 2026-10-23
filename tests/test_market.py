import copy
import json
import sqlite3

import pytest

from equity_analytics.market.returns import compare_returns
from equity_analytics.market.store import PriceStore, validate_snapshot
from equity_analytics.market.yahoo import normalize_chart


def sample(cid="A", kind="equity", values=(100, 110, 121)):
    return {
        "schema_version": 1,
        "instrument": {
            "instrument_id": cid,
            "ticker": cid,
            "name": cid,
            "currency": "INR",
            "kind": kind,
        },
        "data_kind": "synthetic",
        "source": {
            "provider": "test",
            "url": "test://fixture",
            "retrieved_at": "2026-01-05T10:00:00Z",
            "close_basis": "split_adjusted" if kind == "equity" else "index_level",
            "adjusted_basis": "split_dividend_adjusted" if kind == "equity" else kind,
        },
        "bars": [
            {"date": f"2026-01-0{n}", "close": v, "adjusted_close": v, "volume": None}
            for n, v in enumerate(values, 1)
        ],
        "actions": [],
    }


def ingest(store, tmp_path, p):
    f = tmp_path / "input.json"
    f.write_text(json.dumps(p))
    return store.ingest_file(f)


def compare(p, bench=None, **kwargs):
    return compare_returns(
        [p, bench or sample("B", "price_index")],
        "B",
        start="2026-01-01",
        end="2026-01-04",
        **kwargs,
    )


def test_snapshot_revision_and_duplicate(tmp_path):
    store = PriceStore(tmp_path / "market.sqlite")
    p = sample()
    first = ingest(store, tmp_path, p)
    assert ingest(store, tmp_path, p)["status"] == "unchanged"
    p["source"]["retrieved_at"] = "2026-01-06T10:00:00Z"
    p["bars"][0]["close"] = 50
    ingest(store, tmp_path, p)
    assert store.snapshot("A")["bars"][0]["close"] == 50
    old = store.snapshot("A", known_at="2026-01-05T10:00:00Z")
    assert old["bars"][0]["close"] == 100
    assert old["snapshot_id"] == first["snapshot_id"]
    with pytest.raises(ValueError, match="No price snapshot"):
        store.snapshot("A", known_at="2025-01-01T00:00:00Z")
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM market_prices").fetchone()[0] == 6


def test_conflict_rolls_back(tmp_path):
    store = PriceStore(tmp_path / "market.sqlite")
    p = sample()
    ingest(store, tmp_path, p)
    p["bars"][0]["close"] = 50
    with pytest.raises(ValueError, match="Conflicting"):
        ingest(store, tmp_path, p)
    assert store.snapshot("A")["bars"][0]["close"] == 100


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), True, "100"])
def test_invalid_price(bad):
    p = sample()
    p["bars"][0]["close"] = bad
    with pytest.raises(ValueError):
        validate_snapshot(p)


def test_duplicate_date_rejected():
    p = sample()
    p["bars"].append(p["bars"][-1])
    with pytest.raises(ValueError, match="unique"):
        validate_snapshot(p)


def test_gap_never_bridged_or_filled():
    p = sample(values=(100, None, 121))
    p["bars"][1]["adjusted_close"] = 110
    result = compare(p)
    rows = [r for r in result["returns"] if r["instrument_id"] == "A"]
    assert all(r["return"] is None for r in rows)
    assert result["summaries"][0]["cumulative_endpoint_return"] == pytest.approx(0.21)
    assert result["summaries"][0]["missing_intervals"] == 2


def test_dividend_basis_and_benchmark():
    p = sample(values=(100, 99, 99))
    for b in p["bars"]:
        b["adjusted_close"] = 99
    p["actions"] = [{"date": "2026-01-02", "type": "dividend", "value": 1}]
    assert compare(p)["summaries"][0]["cumulative_endpoint_return"] == pytest.approx(
        -0.01
    )
    with pytest.raises(ValueError, match="Benchmark kind"):
        compare(p, basis="total_return_proxy")
    result = compare(p, sample("B", "total_return_index"), basis="total_return_proxy")
    assert result["summaries"][0]["cumulative_endpoint_return"] == 0


def test_foreign_database_untouched(tmp_path):
    path = tmp_path / "financial.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE financials (value INTEGER)")
    with pytest.raises(ValueError, match="separate"):
        PriceStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == [("financials",)]


def test_yahoo_normalization():
    from datetime import UTC, datetime

    ts = int(datetime(2026, 1, 1, 20, tzinfo=UTC).timestamp())
    raw = {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "A",
                        "currency": "INR",
                        "instrumentType": "EQUITY",
                        "exchangeTimezoneName": "Asia/Kolkata",
                    },
                    "timestamp": [ts],
                    "indicators": {
                        "quote": [{"close": [100], "volume": [0]}],
                        "adjclose": [{"adjclose": [99]}],
                    },
                    "events": {
                        "splits": {"x": {"date": ts, "numerator": 2, "denominator": 1}},
                        "dividends": {"x": {"date": ts, "amount": 1}},
                    },
                }
            ],
        }
    }
    p = normalize_chart(
        raw,
        sample()["instrument"],
        "test://provider",
        "2026-01-05T00:00:00Z",
        "2026-01-01",
        "2026-01-04",
    )
    assert p["bars"][0]["date"] == "2026-01-02"
    assert p["bars"][0]["close"] == 100
    assert p["bars"][0]["adjusted_close"] == 99
    assert p["actions"][1]["value"] == 2
    bad = copy.deepcopy(raw)
    bad["chart"]["result"][0]["indicators"]["quote"][0]["close"] = []
    with pytest.raises(ValueError, match="lengths"):
        normalize_chart(
            bad,
            sample()["instrument"],
            "test://provider",
            "2026-01-05T00:00:00Z",
            "2026-01-01",
            "2026-01-04",
        )


def series(cid, kind, closes):
    """Artificial series on consecutive January 2026 dates; None is a blank bar."""
    p = sample(cid, kind)
    p["bars"] = [
        {"date": f"2026-01-{n:02d}", "close": v, "adjusted_close": v, "volume": None}
        for n, v in enumerate(closes, 1)
        if v != "absent"
    ]
    return p


def calendar_result(stock, bench, end="2026-01-06"):
    return compare_returns([stock, bench], "B", start="2026-01-01", end=end)


def test_unpriced_trailing_date_is_dropped_not_fatal():
    # Yahoo can return the latest session with no close for every series. That
    # used to blank every cumulative return; the date is now dropped and listed.
    stock = series("A", "equity", (100, 110, 121, None))
    bench = series("B", "price_index", (1000, 1010, 1020, None))
    r = calendar_result(stock, bench)
    assert r["calendar_checks"] == {
        "dropped_dates": ["2026-01-04"],
        "stale_dates": [],
        "benchmark_gaps": [],
    }
    a, b = r["summaries"]
    assert a["last_date"] == "2026-01-03"
    assert a["cumulative_endpoint_return"] == pytest.approx(0.21)
    assert b["cumulative_endpoint_return"] == pytest.approx(0.02)
    assert a["missing_intervals"] == b["missing_intervals"] == 0
    assert a["observed_dates"] == 3  # the blank row is not a priced date


def test_holiday_row_is_dropped_and_spanned_by_one_interval():
    # A vendor row on an exchange holiday, blank for every series that has it.
    stock = series("A", "equity", (100, "absent", 105, 110))
    bench = series("B", "price_index", (1000, None, 1050, 1100))
    r = calendar_result(stock, bench, end="2026-01-05")
    assert r["calendar_checks"]["dropped_dates"] == ["2026-01-02"]
    a_rows = [x for x in r["returns"] if x["instrument_id"] == "A"]
    assert [(x["start_date"], x["end_date"]) for x in a_rows] == [
        ("2026-01-01", "2026-01-03"),
        ("2026-01-03", "2026-01-04"),
    ]
    assert a_rows[0]["calendar_days"] == 2
    assert a_rows[0]["return"] == pytest.approx(0.05)


def test_benchmark_gap_keeps_the_session_for_stocks():
    # The index is blank on a day the stock traded: keep the day so stock
    # returns are not merged across two sessions; only the benchmark is missing.
    stock = series("A", "equity", (100, 102, 104, 106))
    bench = series("B", "price_index", (1000, None, 1020, 1030))
    r = calendar_result(stock, bench, end="2026-01-05")
    assert r["calendar_checks"] == {
        "dropped_dates": [],
        "stale_dates": [],
        "benchmark_gaps": ["2026-01-02"],
    }
    a, b = r["summaries"]
    assert a["missing_intervals"] == 0
    assert b["missing_intervals"] == 2
    assert b["cumulative_endpoint_return"] == pytest.approx(0.03)
    assert all(x["calendar_days"] == 1 for x in r["returns"])


def test_stock_gap_is_still_never_bridged():
    # Unchanged rule: a stock blank on a real session stays missing on both sides.
    stock = series("A", "equity", (100, None, 104, 106))
    bench = series("B", "price_index", (1000, 1010, 1020, 1030))
    r = calendar_result(stock, bench, end="2026-01-05")
    assert r["calendar_checks"]["dropped_dates"] == []
    a_rows = [x for x in r["returns"] if x["instrument_id"] == "A"]
    assert [x["return"] is None for x in a_rows] == [True, True, False]


def test_report_lists_calendar_checks(tmp_path):
    from equity_analytics.market.report import write_report

    stock = series("A", "equity", (100, 102, 104, None))
    bench = series("B", "price_index", (1000, None, 1020, None))
    snaps = [{**s, "snapshot_id": 1, "sha256": "x"} for s in (stock, bench)]
    r = compare_returns(snaps, "B", start="2026-01-01", end="2026-01-05")
    html = write_report(r, snaps, tmp_path).read_text(encoding="utf-8")
    assert "Calendar checks" in html
    assert "2026-01-04" in html.split("Dropped dates")[1].split("</li>")[0]
    assert "2026-01-02" in html.split("Benchmark gaps")[1].split("</li>")[0]
    assert "Stale holiday rows" in html
    assert json.loads((tmp_path / "summary.json").read_text())["calendar_checks"]


def test_vendor_holiday_rows_repeating_prices_are_dropped():
    # Seen in real Yahoo data on 2026-01-15 (an NSE holiday): the index is blank
    # and every stock repeats the previous close. Not a session.
    stock = series("A", "equity", (100, 102, 102, 105))
    other = series("C", "equity", (50, 51, 51, 50))
    bench = series("B", "price_index", (1000, 1010, None, 1030))
    r = compare_returns(
        [stock, other, bench], "B", start="2026-01-01", end="2026-01-05"
    )
    assert r["calendar_checks"] == {
        "dropped_dates": [],
        "stale_dates": ["2026-01-03"],
        "benchmark_gaps": [],
    }
    b = next(x for x in r["summaries"] if x["instrument_id"] == "B")
    assert b["missing_intervals"] == 0
    a_rows = [x for x in r["returns"] if x["instrument_id"] == "A"]
    assert a_rows[-1]["start_date"] == "2026-01-02"
    assert a_rows[-1]["return"] == pytest.approx(105 / 102 - 1)


def test_unchanged_prices_with_a_benchmark_price_are_a_real_session():
    # The stale rule only applies when the benchmark is blank.
    stock = series("A", "equity", (100, 102, 102, 105))
    bench = series("B", "price_index", (1000, 1010, 1010, 1030))
    r = calendar_result(stock, bench, end="2026-01-05")
    assert r["calendar_checks"]["stale_dates"] == []
    assert len([x for x in r["returns"] if x["instrument_id"] == "A"]) == 3


def test_benchmark_gap_with_one_moving_stock_is_kept():
    # Any priced series moving means the session happened.
    stock = series("A", "equity", (100, 102, 102, 105))
    other = series("C", "equity", (50, 51, 52, 50))
    bench = series("B", "price_index", (1000, 1010, None, 1030))
    r = compare_returns(
        [stock, other, bench], "B", start="2026-01-01", end="2026-01-05"
    )
    assert r["calendar_checks"]["stale_dates"] == []
    assert r["calendar_checks"]["benchmark_gaps"] == ["2026-01-03"]
