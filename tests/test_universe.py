import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from equity_analytics.universe import (
    UniverseStore,
    company_id_for,
    download_constituents,
    isin_valid,
    parse_constituents,
    price_config,
    statement_template,
)

HEADER = "Company Name,Industry,Symbol,Series,ISIN Code\n"


def with_check_digit(body):
    """Complete an 11-character ISIN body with its valid check digit."""
    return next(body + str(d) for d in range(10) if isin_valid(body + str(d)))


def csv_bytes(rows):
    """Artificial constituent rows: (name, industry, symbol). Not real holdings."""
    lines = [
        f"{name},{industry},{symbol},EQ,{with_check_digit(f'INE{n:05d}A01')}"
        for n, (name, industry, symbol) in enumerate(rows, start=1)
    ]
    return (HEADER + "\n".join(lines) + "\n").encode()


BASE = [
    ("Alpha Ltd.", "Capital Goods", "ALPHA"),
    ("Beta Bank Ltd.", "Financial Services", "BETA"),
    ("Gamma & Sons Ltd.", "Information Technology", "G&S"),
]
LATER = [BASE[0], BASE[2], ("Delta Ltd.", "Healthcare", "DELTA")]


def ingest(store, rows=BASE, effective_on="2025-03-31", **kw):
    return store.ingest(
        csv_bytes(rows),
        universe_id=kw.pop("universe_id", "TEST100"),
        effective_on=effective_on,
        retrieved_at=kw.pop("retrieved_at", effective_on + "T12:00:00+05:30"),
        source_url="test://fixture",
    )


@pytest.mark.parametrize(
    ("code", "valid"),
    [
        ("INE117A01022", True),  # published NSE ISINs
        ("INE002A01018", True),
        ("US0378331005", True),
        ("INE117A01023", False),  # wrong check digit
        ("INE117A0102", False),  # too short
        ("ine117a01022", False),
        (None, False),
    ],
)
def test_isin_check_digit(code, valid):
    assert isin_valid(code) is valid


def test_parse_reads_bom_and_trailing_blank_lines():
    raw = b"\xef\xbb\xbf" + csv_bytes(BASE) + b"\n\n"
    members = parse_constituents(raw)
    assert [m["symbol"] for m in members] == ["ALPHA", "BETA", "G&S"]
    assert members[1]["industry"] == "Financial Services"


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"Name,Symbol\nA,B\n", "Unexpected header"),
        (HEADER.encode(), "no members"),
        (HEADER.encode() + b"A,Power,A,EQ\n", "expected 5 columns"),
        (HEADER.encode() + b"A,Power,,EQ,INE117A01022\n", "blank field"),
        (HEADER.encode() + b"A,Power,a b,EQ,INE117A01022\n", "invalid symbol"),
        (HEADER.encode() + b"A,Power,A,EQ,INE117A01023\n", "invalid ISIN"),
        (
            HEADER.encode() + b"A,Power,A,EQ,INE117A01022\nB,Power,A,EQ,INE002A01018\n",
            "duplicate",
        ),
        (b"\xff\xfe", "not UTF-8"),
    ],
)
def test_parse_rejects_bad_files(raw, message):
    with pytest.raises(ValueError, match=message):
        parse_constituents(raw)


def test_ingest_is_idempotent_and_snapshots_are_immutable(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    first = ingest(store)
    assert first["status"] == "loaded" and first["members"] == 3
    assert ingest(store)["status"] == "unchanged"
    with pytest.raises(ValueError, match="immutable"):
        ingest(store, rows=LATER)  # different list, same date
    with pytest.raises(ValueError, match="cannot describe two dates"):
        ingest(store, effective_on="2025-09-30")  # same file, new date
    assert len(store.snapshots("TEST100")) == 1


def test_ingest_validates_dates_and_ids(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    with pytest.raises(ValueError, match="future date"):
        ingest(store, retrieved_at="2025-03-30T12:00:00+05:30")
    with pytest.raises(ValueError, match="timezone"):
        ingest(store, retrieved_at="2025-03-31T12:00:00")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        ingest(store, effective_on="31-03-2025")
    with pytest.raises(ValueError, match="universe_id"):
        ingest(store, universe_id="nifty 100")
    assert store.snapshots("TEST100") == []


def test_effective_date_is_judged_in_india_time(tmp_path):
    # 01:00 IST on 1 April is still 31 March in UTC; an IST-dated list is valid.
    store = UniverseStore(tmp_path / "u.sqlite")
    result = ingest(
        store, effective_on="2025-04-01", retrieved_at="2025-03-31T19:30:00Z"
    )
    assert result["status"] == "loaded"


def test_failed_ingest_leaves_no_partial_rows(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    with pytest.raises(ValueError):
        store.ingest(
            HEADER.encode() + b"A,Power,A,EQ,INE117A01023\n",
            universe_id="TEST100",
            effective_on="2025-03-31",
            retrieved_at="2025-03-31T12:00:00Z",
            source_url="test://bad",
        )
    with sqlite3.connect(tmp_path / "u.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM universe_members").fetchone()[0] == 0


def test_company_ids_and_templates(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    ingest(store)
    m = {x["symbol"]: x for x in store.members("TEST100", "2025-04-01")["members"]}
    assert m["G&S"]["company_id"] == "G_S" == company_id_for("G&S")
    assert m["BETA"]["template"] == "financials"
    assert m["ALPHA"]["template"] == "general"
    assert statement_template("Space Mining") == "unclassified"


def test_colliding_company_ids_are_rejected(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    with pytest.raises(ValueError, match="same company_id"):
        ingest(store, rows=[("A", "Power", "M&M"), ("B", "Power", "M_M")])


def test_membership_uses_latest_list_on_or_before_date(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    ingest(store, rows=LATER, effective_on="2025-09-30")  # load order is irrelevant
    ingest(store, rows=BASE, effective_on="2025-03-31")

    def ids(day):
        return [m["company_id"] for m in store.members("TEST100", day)["members"]]

    assert ids("2025-03-31") == ["ALPHA", "BETA", "G_S"]
    assert ids("2025-09-29") == ["ALPHA", "BETA", "G_S"]
    assert ids("2025-09-30") == ["ALPHA", "DELTA", "G_S"]


def test_survivorship_guard(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    ingest(store, effective_on="2025-03-31")
    with pytest.raises(ValueError, match="survivorship"):
        store.members("TEST100", "2024-01-01")
    result = store.members("TEST100", "2024-01-01", allow_backfill=True)
    assert result["survivorship_biased"] is True
    assert "Survivorship bias" in result["warnings"][0]
    assert store.members("TEST100", "2025-04-01")["survivorship_biased"] is False


def test_stale_and_unclassified_warnings(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    ingest(store, rows=[*BASE, ("Odd Ltd.", "Space Mining", "ODD")])
    fresh = store.members("TEST100", "2025-06-30")["warnings"]
    assert fresh == ["Unrecognised NSE industries: Space Mining"]
    stale = store.members("TEST100", "2026-03-31")
    assert stale["list_age_days"] == 365
    assert any(w.startswith("Stale list") for w in stale["warnings"])


def test_changes_between_snapshots(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    ingest(store, rows=BASE, effective_on="2025-03-31")
    ingest(store, rows=LATER, effective_on="2025-09-30")
    (change,) = store.changes("TEST100")
    assert change["added"] == ["DELTA"]
    assert change["removed"] == ["BETA"]
    # G&S moves from row 3 to row 2, so the fixture gives it a new ISIN (as a
    # face-value split would). It must be flagged, not treated as unchanged.
    assert change["isin_changed"] == ["G_S"]


def test_price_config_matches_price_pipeline_shape(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    ingest(store)
    membership = store.members("TEST100", "2025-04-01")
    config = price_config(membership, start="2024-04-01", end_exclusive="2025-04-01")
    tickers = [i["ticker"] for i in config["instruments"]]
    assert tickers == ["ALPHA.NS", "BETA.NS", "G&S.NS", "^NSEI"]
    assert config["benchmark_id"] == "NIFTY50"
    assert config["universe"]["survivorship_biased"] is True  # prices predate list
    later = price_config(membership, start="2025-03-31", end_exclusive="2025-04-01")
    assert later["universe"]["survivorship_biased"] is False
    with pytest.raises(ValueError, match="before"):
        price_config(membership, start="2025-04-01", end_exclusive="2025-04-01")


def test_store_refuses_other_databases(tmp_path):
    path = tmp_path / "other.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (x)")
    with pytest.raises(ValueError, match="Not a supported universe database"):
        UniverseStore(path)


def test_download_validates_before_returning():
    class Response:
        def __init__(self, raw):
            self.raw = raw

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return self.raw

    seen = []

    def opener(request, timeout):
        seen.append(request.full_url)
        return Response(csv_bytes(BASE))

    got = download_constituents("NIFTY100", opener=opener)
    assert seen == [
        "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv"
    ]
    assert got["raw"] == csv_bytes(BASE) and got["retrieved_at"].endswith("+00:00")
    with pytest.raises(ValueError, match="Unexpected header"):
        download_constituents("NIFTY100", opener=lambda r, timeout: Response(b"<html>"))
    with pytest.raises(ValueError, match="No known NSE file"):
        download_constituents("SENSEX", opener=opener)


def test_runner_end_to_end(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location(
        "run_universe", Path(__file__).parents[1] / "run_universe.py"
    )
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    main = runner.main

    source = tmp_path / "list.csv"
    source.write_bytes(csv_bytes(BASE))
    out = tmp_path / "out"
    db = tmp_path / "u.sqlite"
    args = [
        "--universe",
        "NIFTY100",
        "--import",
        str(source),
        "--retrieved-at",
        "2025-03-31T10:00:00+05:30",
        "--as-of",
        "2025-04-15",
        "--db",
        str(db),
        "--output",
        str(out),
    ]
    assert main(args) == 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["member_count"] == 3
    assert summary["templates"] == {"financials": 1, "general": 2}
    config = json.loads((out / "market_config.json").read_text())
    assert config["end_exclusive"] == "2025-04-15"
    assert (
        (out / "members.csv")
        .read_text(encoding="utf-8-sig")
        .startswith("company_id,symbol")
    )
    assert "NIFTY100 membership" in (out / "report.html").read_text()
    # A date before the only list fails loudly instead of backfilling.
    assert main(["--as-of", "2024-01-01", "--db", str(db), "--output", str(out)]) == 1
    assert "survivorship" in capsys.readouterr().err
