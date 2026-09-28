"""Screen semantics: zero substitution, timing, units, sorting and source integrity."""

import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.data import FinancialStore
from equity_analytics.screening.engine import METRICS, screen_companies
from equity_analytics.screening.reporting import export_screener

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config():
    p = json.loads((ROOT / "examples/screener_config.json").read_text())
    p.update(as_of="2026-09-28", period_end=None, filters={}, sort_by="debt_to_equity")
    return p


def add_company(
    store,
    tmp_path,
    cid,
    *,
    debt=None,
    unit="million",
    kind="reported",
    currency="INR",
    published="2026-07-01",
    name=None,
):
    p = {
        "schema_version": 1,
        "company": {
            "name": name or cid,
            "ticker": cid,
            "currency": currency,
            "financial_unit": unit,
            "statement_basis": "consolidated",
            "data_kind": kind,
        },
        "as_of": published,
        "sources": [
            {
                "source_id": "fixture",
                "title": "Test filing",
                "published_on": published,
                "locator": "test only",
                "url": "https://example.com/test-fixture",
            }
        ],
        "annuals": [
            {
                "fiscal_year": 2026,
                "period_end": "2026-03-31",
                "source_id": "fixture",
                "revenue": 100,
                "total_equity": 100,
                "total_debt": debt,
            }
        ],
    }
    path = tmp_path / f"{cid}.json"
    path.write_text(json.dumps(p))
    store.ingest_file(path, company_id=cid)


def test_missing_zero_filters_exports_and_readonly_sql(tmp_path, config):
    store = FinancialStore(tmp_path / "research.sqlite")
    add_company(store, tmp_path, "MISSING")
    add_company(store, tmp_path, "ZERO", debt=0)
    add_company(store, tmp_path, "DEBT", debt=10)
    before = hashlib.sha256(store.path.read_bytes()).hexdigest()
    config["filters"] = {"debt_to_equity": {"max": 0}}
    result = screen_companies(store, config)
    assert [r["company_id"] for r in result["matches"]] == ["MISSING", "ZERO"]
    missing, zero = result["matches"]
    assert missing["values"]["debt_to_equity"] == zero["values"]["debt_to_equity"] == 0
    assert "debt_to_equity" in missing["zero_filled"]
    assert "debt_to_equity" not in zero["zero_filled"]
    assert missing["values"]["roe"] == 0 and "roe" in missing["zero_filled"]
    assert not next(r for r in result["rows"] if r["company_id"] == "DEBT")["passes"]
    export_screener(result, tmp_path / "export")
    with (tmp_path / "export/screener.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert float(rows[0]["debt_to_equity"]) == 0
    assert rows[0]["debt_to_equity_zero_filled"] == "True"
    assert rows[1]["debt_to_equity_zero_filled"] == "False"
    assert hashlib.sha256(store.path.read_bytes()).hexdigest() == before
    assert store.history_as_of("MISSING", config["as_of"]).annuals[0].total_debt is None


def test_units_currency_and_synthetic_exclusions(tmp_path, config):
    store = FinancialStore(tmp_path / "db.sqlite")
    add_company(store, tmp_path, "CRORE", unit="crore")
    add_company(store, tmp_path, "MILLION")
    add_company(store, tmp_path, "USD", currency="USD")
    add_company(store, tmp_path, "DEMO", kind="synthetic")
    config["sort_by"] = "revenue"
    result = screen_companies(store, config)
    assert [r["values"]["revenue"] for r in result["matches"]] == [1000, 100]
    assert {r["company_id"] for r in result["excluded"]} == {"USD", "DEMO"}


def test_cutoff_period_age_and_unknown_are_not_fake_zero_companies(tmp_path, config):
    store = FinancialStore(tmp_path / "db.sqlite")
    add_company(store, tmp_path, "KNOWN", published="2026-07-01")
    config.update(as_of="2026-06-30", company_ids=["KNOWN", "UNKNOWN"])
    result = screen_companies(store, config)
    assert not result["rows"] and len(result["excluded"]) == 2
    config.update(as_of="2026-07-01", company_ids=["KNOWN"])
    assert len(screen_companies(store, config)["matches"]) == 1
    config["period_end"] = "2025-03-31"
    assert not screen_companies(store, config)["rows"]
    config.update(period_end=None, max_age_days=10)
    assert not screen_companies(store, config)["rows"]


def test_older_period_does_not_use_future_growth(tmp_path, config):
    store = FinancialStore(tmp_path / "db.sqlite")
    for y in (2024, 2026):
        store.ingest_file(
            ROOT / f"examples/wabag_fy{y}_reported_statements.json", company_id="WABAG"
        )
    config.update(period_end="2024-03-31", max_age_days=None)
    result = screen_companies(store, config)
    assert result["rows"][0]["values"]["revenue_growth"] == 0
    assert "revenue_growth" in result["rows"][0]["zero_filled"]
    assert result["rows"][0]["published_on"] == "2024-07-23"


@pytest.mark.parametrize(
    "key,value",
    [
        ("sort_by", "typo"),
        ("filters", {"typo": {"min": 1}}),
        ("filters", {"roe": {"min": 2, "max": 1}}),
        ("filters", {"roe": {"min": float("nan")}}),
        ("filters", {"roe": {"min": True}}),
        ("ascending", "false"),
        ("max_age_days", -1),
        ("period_end", "2027-03-31"),
    ],
)
def test_invalid_config_fails_before_query(tmp_path, config, key, value):
    config[key] = value
    with pytest.raises(ValueError):
        screen_companies(FinancialStore(tmp_path / "db.sqlite"), config)


def test_empty_csv_has_headers_and_output_protection(tmp_path, config):
    store = FinancialStore(tmp_path / "db.sqlite")
    result = screen_companies(store, config)
    export_screener(result, tmp_path / "export")
    with (tmp_path / "export/screener.csv").open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert set(METRICS) <= set(reader.fieldnames)
        assert list(reader) == []
    with pytest.raises(ValueError, match="overwrite"):
        export_screener(
            result,
            tmp_path / "export",
            protected_paths=[tmp_path / "export/screener.json"],
        )


def test_html_escape_csv_text_and_stable_sort(tmp_path, config):
    store = FinancialStore(tmp_path / "db.sqlite")
    add_company(store, tmp_path, "A", name="=1+1<script>", debt=0)
    add_company(store, tmp_path, "B", debt=20)
    first = screen_companies(store, config)
    assert [r["company_id"] for r in first["matches"]] == ["B", "A"]
    c = deepcopy(config)
    c["ascending"] = True
    second = screen_companies(store, c)
    assert [r["company_id"] for r in second["matches"]] == ["A", "B"]
    export_screener(second, tmp_path / "out")
    assert "&lt;script&gt;" in (tmp_path / "out/screener.html").read_text()
    with (tmp_path / "out/screener.csv").open(encoding="utf-8-sig") as f:
        assert next(csv.DictReader(f))["company_name"].startswith("'=1")
