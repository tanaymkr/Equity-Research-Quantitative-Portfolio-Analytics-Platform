"""FY26 source reconciliations and integration checks against independent totals."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.acquisition import build_acquisition_model
from equity_analytics.acquisition.history import (
    legacy_facts_from_statements,
    load_acquisition_facts,
)
from equity_analytics.financials.io import load_history
from equity_analytics.forecasting import (
    ModelInputError,
    build_forecast,
    load_json,
    reconcile_history,
)
from equity_analytics.forecasting.reporting import historical_markdown

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def history():
    return load_json(ROOT / "examples/tega_fy2026_reported_statements.json")


def test_fy26_primary_statements_and_notes_reconcile(history):
    checks = reconcile_history(history)
    assert len(checks) >= 90 and all(c["passed"] for c in checks)
    r = history["annuals"][-1]
    # Independent audited totals and source cash-roll arithmetic.
    assert r["reported_totals"]["assets"] == 43145.00
    assert r["reported_totals"]["liabilities"] + r["reported_totals"][
        "equity"
    ] == pytest.approx(43145.00)
    assert r["cash_flow"]["closing_cash"] == pytest.approx(
        1142.95 + 3503.39 - 10044.18 + 16899.06 + 137.64
    )
    assert r["income"]["net_income"] == pytest.approx(2011.12 - 918.40 + 333.81)
    assert r["income"]["operating_ebitda"] == pytest.approx(
        16919.36 - 7165.67 + 315.07 - 2799.33 - 4958.03
    )


@pytest.mark.parametrize(
    "section, key",
    [("income", "revenue"), ("assets", "cash"), ("equity", "other_reserves")],
)
def test_fy26_mismatched_statement_is_rejected(history, section, key):
    history["annuals"][-1][section][key] += 1
    with pytest.raises(ModelInputError, match="historical reconciliation failed"):
        reconcile_history(history)


def test_cash_issue_and_debt_flows_are_checked(history):
    history["annuals"][-1]["cash_flow"]["financing"]["term_borrowing_proceeds"] += 10
    with pytest.raises(ModelInputError, match="historical reconciliation failed"):
        reconcile_history(history)


def test_fy26_source_is_loaded_relative_to_facts_and_no_duplicate_values(
    tmp_path, monkeypatch
):
    directory = tmp_path / "nested"
    directory.mkdir()
    for name in ["tega_molycop_facts.json", "tega_fy2026_reported_statements.json"]:
        (directory / name).write_bytes((ROOT / "examples" / name).read_bytes())
    monkeypatch.chdir(tmp_path)
    raw = json.loads((directory / "tega_molycop_facts.json").read_text())
    assert "tega_fy2026" not in raw
    facts, case, checks = load_acquisition_facts(directory / "tega_molycop_facts.json")
    assert facts["tega_fy2026"]["shares"] == 75127698
    assert facts["tega_fy2026"]["cash_capex"] == 1359.36
    assert facts["tega_fy2026"]["cash_from_operations"] == 3503.39
    assert case["base_year"] == 2026 and all(c["passed"] for c in checks)


def test_cash_restriction_change_flows_from_notes_to_acquisition_equity(history):
    facts, _, _ = load_acquisition_facts(ROOT / "examples/tega_molycop_facts.json")
    assumptions = load_json(ROOT / "examples/tega_molycop_assumptions.json")
    original = build_acquisition_model(facts, assumptions)
    changed = deepcopy(history)
    changed["base_year_disclosures"]["cash_and_bank"]["pledged_bank_deposits"] += 100
    facts["tega_fy2026"], _ = legacy_facts_from_statements(changed)
    recalculated = build_acquisition_model(facts, assumptions)
    assert recalculated["equity_bridge"]["value_per_share_inr"] == pytest.approx(
        original["equity_bridge"]["value_per_share_inr"] - 100 / 75.127698
    )


def test_generic_engine_accepts_fy26_actuals(history, linked_assumptions):
    a = linked_assumptions(history)
    before = deepcopy(history)
    result = build_forecast(history, a)
    assert [r["fiscal_year"] for r in result["years"]] == list(range(2027, 2032))
    assert result["years"][0]["cash_flow"]["opening_cash"] == 11638.86
    assert result["dcf"]["shares_outstanding_million"] == 75.127698
    prior = history["annuals"][-1]["equity"]["retained_earnings"]
    for year in result["years"]:
        bs, cf = year["balance_sheet"], year["cash_flow"]
        assert bs["total_assets"] == pytest.approx(
            bs["total_liabilities"] + bs["total_equity"]
        )
        assert cf["closing_cash"] == pytest.approx(
            cf["opening_cash"] + cf["operating"] + cf["investing"] + cf["financing"]
        )
        assert bs["equity"]["retained_earnings"] == pytest.approx(
            prior + year["income"]["net_income"] + cf["dividends"]
        )
        prior = bs["equity"]["retained_earnings"]
    assert history == before


def test_ratio_module_reads_complete_fy26_source():
    latest = load_history(
        ROOT / "examples/tega_fy2026_reported_statements.json"
    ).annuals[-1]
    assert latest.fiscal_year == 2026 and latest.revenue == 16919.36
    assert latest.total_debt == pytest.approx(1275.60 + 1900.53 + 807.88)
    assert latest.operating_cash_flow == 3503.39 and latest.capex == 1359.36


def test_reports_include_new_cash_line_and_correct_years(history):
    text = historical_markdown(
        history, {"historical_checks": reconcile_history(history)}
    )
    assert "FY2025 actual" in text and "FY2026 actual" in text
    assert "FY2024 actual" not in text
    assert "term borrowing proceeds" in text and "503.58" in text
    assert "75.127698" in text and "66.535492" in text


def test_history_year_and_company_mismatch_is_rejected(history):
    history["base_year"] = 2025
    with pytest.raises(ModelInputError):
        reconcile_history(history)
    history["base_year"] = 2026
    history["company"] = "Different issuer"
    with pytest.raises(ModelInputError, match="Tega"):
        legacy_facts_from_statements(history)


def test_missing_statement_reference_stops_before_valuation(tmp_path):
    raw = load_json(ROOT / "examples/tega_molycop_facts.json")
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ModelInputError, match="cannot load"):
        load_acquisition_facts(path)


def test_pledged_cash_cannot_exceed_bank_deposits(history):
    history["base_year_disclosures"]["cash_and_bank"]["pledged_bank_deposits"] = 10000
    with pytest.raises(ModelInputError, match="pledged bank deposits"):
        reconcile_history(history)
