import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from equity_analytics.universe import (
    UniverseStore,
    benchmark_for,
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
    assert len(store.snapshots("TEST100")) == 1


def test_unchanged_list_redownloaded_later_is_confirmed(tmp_path):
    # Re-running the launcher days later downloads an identical list. It must
    # confirm the list is still current, not fail (the bug this guards against).
    store = UniverseStore(tmp_path / "u.sqlite")
    first = ingest(store, effective_on="2025-03-31")
    again = ingest(store, effective_on="2025-09-30")
    assert again["status"] == "confirmed"
    assert again["snapshot_id"] == first["snapshot_id"]  # stored once
    dates = [s["effective_on"] for s in store.snapshots("TEST100")]
    assert dates == ["2025-03-31", "2025-09-30"]
    later = store.members("TEST100", "2026-01-31")
    assert later["snapshot"]["effective_on"] == "2025-09-30"
    assert later["list_age_days"] == 123  # age resets from the confirmation
    assert later["warnings"] == []
    assert store.changes("TEST100") == []  # no change between identical lists
    with sqlite3.connect(tmp_path / "u.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM universe_members").fetchone()[0] == 3


def test_version_1_database_is_upgraded_in_place(tmp_path):
    path = tmp_path / "u.sqlite"
    ingest(UniverseStore(path))
    with sqlite3.connect(path) as db:  # rebuild what version 1 looked like
        db.execute("DROP TABLE universe_observations")
        db.execute("PRAGMA user_version=1")
    store = UniverseStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    assert [s["effective_on"] for s in store.snapshots("TEST100")] == ["2025-03-31"]
    assert ingest(store, effective_on="2025-04-30")["status"] == "confirmed"


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
    ingest(store, universe_id="NIFTY100")
    membership = store.members("NIFTY100", "2025-04-01")
    config = price_config(membership, start="2024-04-01", end_exclusive="2025-04-01")
    tickers = [i["ticker"] for i in config["instruments"]]
    # A Nifty 100 universe is compared with the Nifty 100 index, not the Nifty 50.
    # Benchmark first so a rejected index fails before any member downloads.
    assert tickers == ["^CNX100", "ALPHA.NS", "BETA.NS", "G&S.NS"]
    assert config["benchmark_id"] == "NIFTY100"
    assert config["universe"]["survivorship_biased"] is True  # prices predate list
    later = price_config(membership, start="2025-03-31", end_exclusive="2025-04-01")
    assert later["universe"]["survivorship_biased"] is False
    with pytest.raises(ValueError, match="before"):
        price_config(membership, start="2025-04-01", end_exclusive="2025-04-01")


@pytest.mark.parametrize(
    ("universe_id", "ticker"),
    [
        ("NIFTY50", "^NSEI"),
        ("NIFTY100", "^CNX100"),
        ("NIFTY200", "^CNX200"),
        ("NIFTY500", "^CRSLDX"),
    ],
)
def test_each_universe_has_its_own_benchmark(universe_id, ticker):
    b = benchmark_for(universe_id)
    assert (b["instrument_id"], b["ticker"], b["kind"]) == (
        universe_id,
        ticker,
        "price_index",
    )


def test_unknown_universe_needs_an_explicit_benchmark(tmp_path):
    store = UniverseStore(tmp_path / "u.sqlite")
    ingest(store)
    membership = store.members("TEST100", "2025-04-01")
    with pytest.raises(ValueError, match="No default benchmark"):
        price_config(membership, start="2025-03-31", end_exclusive="2025-04-01")
    config = price_config(
        membership,
        start="2025-03-31",
        end_exclusive="2025-04-01",
        benchmark=benchmark_for("NIFTY50"),
    )
    assert config["benchmark_id"] == "NIFTY50"


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


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_universe", Path(__file__).parents[1] / "scripts" / "run_universe.py"
    )
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


def test_runner_end_to_end(tmp_path, capsys):
    main = load_runner().main

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
    assert config["benchmark_id"] == "NIFTY100"
    assert config["instruments"][0]["ticker"] == "^CNX100"
    # The benchmark can be overridden, e.g. to compare with the Nifty 50.
    assert (
        main(
            [
                *args[:2],
                "--as-of",
                "2025-04-15",
                "--db",
                str(db),
                "--output",
                str(out),
                "--benchmark",
                "NIFTY50",
            ]
        )
        == 0
    )
    config = json.loads((out / "market_config.json").read_text())
    assert config["instruments"][0]["ticker"] == "^NSEI"
    assert (
        (out / "members.csv")
        .read_text(encoding="utf-8-sig")
        .startswith("company_id,symbol")
    )
    assert "NIFTY100 membership" in (out / "report.html").read_text()
    # A date before the only list fails loudly instead of backfilling.
    assert main(["--as-of", "2024-01-01", "--db", str(db), "--output", str(out)]) == 1
    assert "survivorship" in capsys.readouterr().err


def test_runner_rebuilds_a_stale_config_without_downloading(tmp_path):
    # The prices launcher runs the universe step with no flags first. That must
    # overwrite an old config (e.g. one naming NIFTY50) from the stored list.
    runner = load_runner()
    db, out = tmp_path / "u.sqlite", tmp_path / "out"
    source = tmp_path / "list.csv"
    source.write_bytes(csv_bytes(BASE))
    common = ["--db", str(db), "--output", str(out), "--as-of", "2025-04-15"]
    assert (
        runner.main(
            [
                "--import",
                str(source),
                "--retrieved-at",
                "2025-03-31T10:00:00+05:30",
                *common,
            ]
        )
        == 0
    )
    stale = json.loads((out / "market_config.json").read_text())
    stale["benchmark_id"] = "NIFTY50"
    (out / "market_config.json").write_text(json.dumps(stale))
    assert runner.main(common) == 0
    fresh = json.loads((out / "market_config.json").read_text())
    assert fresh["benchmark_id"] == "NIFTY100"


def test_runner_needs_a_stored_list_when_nothing_is_imported(tmp_path, capsys):
    runner = load_runner()
    assert (
        runner.main(
            ["--db", str(tmp_path / "u.sqlite"), "--output", str(tmp_path / "out")]
        )
        == 1
    )
    assert "No snapshots stored" in capsys.readouterr().err


def test_runner_falls_back_to_stored_list_if_nse_blocks(tmp_path, capsys):
    runner = load_runner()
    db, out = tmp_path / "u.sqlite", tmp_path / "out"
    source = tmp_path / "list.csv"
    source.write_bytes(csv_bytes(BASE))
    common = ["--db", str(db), "--output", str(out), "--as-of", "2025-04-15"]

    def blocked(universe_id):
        raise OSError("HTTP Error 403: Forbidden")

    runner.download_constituents = blocked
    # Nothing stored yet: the failure must stop the run.
    assert runner.main(["--download", *common]) == 1
    assert "no NIFTY100 list is stored" in capsys.readouterr().err
    assert (
        runner.main(
            [
                "--import",
                str(source),
                "--retrieved-at",
                "2025-03-31T10:00:00+05:30",
                *common,
            ]
        )
        == 0
    )
    capsys.readouterr()
    # With a stored list: warn loudly, then continue with it.
    assert runner.main(["--download", *common]) == 0
    printed = capsys.readouterr().out
    assert "WARNING: NSE download failed" in printed
    assert "list effective 2025-03-31" in printed


@pytest.mark.parametrize(
    "flag",
    [
        ["--effective-on", "2024-01-01"],
        ["--retrieved-at", "2024-01-01T00:00:00Z"],
        ["--source-url", "x"],
    ],
)
def test_runner_rejects_import_flags_without_import(tmp_path, capsys, flag):
    # Back-dating a fresh download would apply today's list to the past.
    runner = load_runner()
    args = ["--download", *flag, "--db", str(tmp_path / "u.sqlite")]
    assert runner.main(args) == 1
    assert "can only be used with --import" in capsys.readouterr().err
