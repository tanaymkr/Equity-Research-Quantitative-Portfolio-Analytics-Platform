"""Publication timing, version integrity, unit isolation and atomic ingestion."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.data import DataStoreError, FinancialStore
from equity_analytics.data.__main__ import export_analysis, main
from equity_analytics.financials.io import load_history

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def payload():
    return {
        "schema_version": 1,
        "company": {
            "name": "Test Co",
            "ticker": "TEST",
            "currency": "INR",
            "financial_unit": "million",
            "statement_basis": "consolidated",
            "data_kind": "synthetic",
        },
        "as_of": "2025-06-01",
        "sources": [
            {
                "source_id": "filing1",
                "title": "Original filing",
                "published_on": "2025-06-01",
                "locator": "test fixture",
            }
        ],
        "annuals": [
            {
                "fiscal_year": 2024,
                "period_end": "2024-12-31",
                "source_id": "filing1",
                "revenue": 100,
                "ebit": 10,
                "total_assets": 200,
                "total_liabilities": 80,
                "total_equity": 120,
            }
        ],
        "notes": "Synthetic arithmetic only",
    }


@pytest.fixture
def store(tmp_path):
    return FinancialStore(tmp_path / "test.sqlite")


def load(store, tmp_path, payload, company_id="TEST"):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return store.ingest_file(path, company_id=company_id)


def revision(payload):
    p = deepcopy(payload)
    p["as_of"] = "2026-06-01"
    p["sources"][0].update(
        source_id="filing2", title="Restated filing", published_on="2026-06-01"
    )
    p["annuals"][0].update(source_id="filing2", revenue=150, ebit=None)
    return p


def counts(store):
    with store.connection() as db:
        return [
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("companies", "profiles", "sources", "annual_statements")
        ]


def test_repeated_load_preserves_facts_and_records_raw_evidence(
    store, tmp_path, payload
):
    first = load(store, tmp_path, payload)
    second = load(store, tmp_path, payload)
    assert first["inserted_statements"] == 1
    assert second["status"] == "unchanged"
    assert counts(store) == [1, 1, 1, 1]
    with store.connection() as db:
        runs = db.execute("SELECT * FROM ingestion_runs ORDER BY run_id").fetchall()
        assert len(runs) == 2
        assert runs[0]["sha256"] == hashlib.sha256(runs[0]["raw_content"]).hexdigest()
        assert json.loads(runs[0]["raw_content"]) == payload


@pytest.mark.parametrize("new_first", [True, False])
def test_restated_facts_do_not_leak_into_earlier_dates(
    store, tmp_path, payload, new_first
):
    new = revision(payload)
    for p in [new, payload] if new_first else [payload, new]:
        load(store, tmp_path, p)
    old = store.history_as_of("TEST", "2026-05-31")
    current = store.history_as_of("TEST", "2026-06-01")
    assert old.annuals[0].revenue == 100
    assert old.annuals[0].ebit == 10
    assert current.annuals[0].revenue == 150
    assert current.annuals[0].ebit is None  # No filling from an older filing.
    assert [s.source_id for s in old.sources] == ["filing1"]
    assert [s.source_id for s in current.sources] == ["filing2"]
    with pytest.raises(DataStoreError, match="No financial statements"):
        store.history_as_of("TEST", "2025-05-31")
    assert store.history_as_of("TEST", "2025-06-01").annuals[0].revenue == 100


def test_changed_source_metadata_is_rejected(store, tmp_path, payload):
    load(store, tmp_path, payload)
    payload["sources"][0]["title"] = "Silently changed title"
    with pytest.raises(DataStoreError, match="Source ID reused"):
        load(store, tmp_path, payload)
    assert counts(store) == [1, 1, 1, 1]


def test_failed_file_rolls_back_all_fact_changes(store, tmp_path, payload):
    load(store, tmp_path, payload)
    early = deepcopy(payload["annuals"][0])
    early.update(fiscal_year=2023, period_end="2023-12-31")
    payload["annuals"].insert(0, early)
    payload["annuals"][1]["revenue"] = 999
    with pytest.raises(DataStoreError, match="Statement changed"):
        load(store, tmp_path, payload)
    assert counts(store) == [1, 1, 1, 1]
    with store.connection() as db:
        run = db.execute("SELECT * FROM ingestion_runs ORDER BY run_id DESC").fetchone()
        assert run["status"] == "failed"
        assert run["inserted_statements"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("currency", "USD"),
        ("financial_unit", "crore"),
        ("data_kind", "reported"),
    ],
)
def test_incompatible_units_currency_kind_rejected(
    store, tmp_path, payload, field, value
):
    payload["sources"][0]["url"] = "https://example.com/filing"
    load(store, tmp_path, payload)
    payload["company"][field] = value
    with pytest.raises(DataStoreError, match="Currency, units or data kind"):
        load(store, tmp_path, payload)


def test_standalone_and_consolidated_are_separate(store, tmp_path, payload):
    load(store, tmp_path, payload)
    payload["company"]["statement_basis"] = "standalone"
    payload["annuals"][0]["revenue"] = 50
    load(store, tmp_path, payload)
    assert counts(store) == [1, 2, 2, 2]
    assert store.history_as_of("TEST", "2025-06-01").annuals[0].revenue == 100
    assert (
        store.history_as_of("TEST", "2025-06-01", basis="standalone").annuals[0].revenue
        == 50
    )


def test_company_ids_do_not_merge_tickers_or_names(store, tmp_path, payload):
    load(store, tmp_path, payload)
    with pytest.raises(DataStoreError, match="UNIQUE"):
        load(store, tmp_path, payload, company_id="OTHER")
    payload["company"]["ticker"] = "OTHER"
    with pytest.raises(DataStoreError, match="different name/ticker"):
        load(store, tmp_path, payload)
    assert counts(store) == [1, 1, 1, 1]


def test_same_day_revisions_rejected_without_ordering(store, tmp_path, payload):
    load(store, tmp_path, payload)
    new = revision(payload)
    new["sources"][0]["published_on"] = "2025-06-01"
    with pytest.raises(DataStoreError, match="same-date"):
        load(store, tmp_path, new)
    assert counts(store) == [1, 1, 1, 1]


@pytest.mark.parametrize("bad_value", [None, float("nan"), float("inf"), "100"])
def test_invalid_revenue_never_reaches_facts(store, tmp_path, payload, bad_value):
    payload["annuals"][0]["revenue"] = bad_value
    with pytest.raises(DataStoreError):
        load(store, tmp_path, payload)
    assert counts(store) == [0, 0, 0, 0]


def test_balance_mismatch_rejected_and_missing_stays_missing(store, tmp_path, payload):
    payload["annuals"][0]["total_assets"] = 999
    with pytest.raises(DataStoreError, match="reconcile"):
        load(store, tmp_path, payload)
    payload["annuals"][0]["total_assets"] = None
    load(store, tmp_path, payload)
    assert store.history_as_of("TEST", "2025-06-01").annuals[0].total_assets is None


def test_unrelated_or_future_schema_refused(tmp_path):
    path = tmp_path / "foreign.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(DataStoreError, match="unrelated"):
        FinancialStore(path)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(DataStoreError, match="version"):
        FinancialStore(path)


def test_real_tega_filings_and_export_roundtrip(store, tmp_path):
    for year in (2025, 2026):
        store.ingest_file(
            ROOT / f"examples/tega_fy{year}_reported_statements.json", company_id="TEGA"
        )
    before = store.history_as_of("TEGA", "2026-08-27")
    after = store.history_as_of("TEGA", "2026-08-28")
    assert [a.fiscal_year for a in before.annuals] == [2024, 2025]
    assert [a.fiscal_year for a in after.annuals] == [2024, 2025, 2026]
    assert store.inventory()[0]["statement_versions"] == 4
    out = tmp_path / "reports"
    export_analysis(store, "TEGA", "2026-08-28", out)
    assert load_history(out / "history.json") == after


@pytest.mark.parametrize("as_of", ["20260601", "2026-02-30", "not-a-date"])
def test_bad_cutoff_rejected(store, as_of):
    with pytest.raises(DataStoreError, match="YYYY-MM-DD"):
        store.history_as_of("TEST", as_of)


def test_cli_load_and_query(tmp_path, payload, capsys):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(payload))
    prefix = ["--db", str(tmp_path / "cli.sqlite")]
    main([*prefix, "ingest", str(input_path), "--company-id", "TEST"])
    main(
        [
            *prefix,
            "query",
            "--company-id",
            "TEST",
            "--as-of",
            "2025-06-01",
            "--output",
            str(tmp_path / "out"),
        ]
    )
    assert "Test Co: 1 annual periods" in capsys.readouterr().out
    assert (tmp_path / "out/analysis.md").is_file()


def test_export_cannot_overwrite_database(tmp_path, payload):
    store = FinancialStore(tmp_path / "history.json")
    load(store, tmp_path, payload)
    with pytest.raises(DataStoreError, match="overwrite the database"):
        export_analysis(store, "TEST", "2025-06-01", tmp_path)
    assert counts(store) == [1, 1, 1, 1]


def test_html_escapes_source_content(store, tmp_path, payload):
    payload["company"]["name"] = "<script>alert(1)</script>"
    load(store, tmp_path, payload)
    export_analysis(store, "TEST", "2025-06-01", tmp_path / "report")
    html = (tmp_path / "report/analysis.html").read_text()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
