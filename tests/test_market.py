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
