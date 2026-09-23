"""Economic linkage, evidence scope and accounting-gap regression tests."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.acquisition import build_acquisition_model
from equity_analytics.acquisition.drivers import historical_drivers
from equity_analytics.acquisition.engine import _Assets
from equity_analytics.acquisition.history import load_acquisition_facts

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    facts, _, _ = load_acquisition_facts(ROOT / "examples/tega_molycop_facts.json")
    assumptions = json.loads(
        (ROOT / "examples/tega_molycop_assumptions.json").read_text()
    )
    return facts, assumptions


def test_revenue_flows_through_expenses_working_capital_capex_and_assets(inputs):
    facts, assumptions = inputs
    before = build_acquisition_model(facts, assumptions)
    changed = deepcopy(assumptions)
    changed["scenarios"]["base"]["equipment_growth"][1] += 0.1
    after = build_acquisition_model(facts, changed)
    assert before["legacy_forecast_inr_m"][0] == after["legacy_forecast_inr_m"][0]
    for key in (
        "revenue",
        "operating_ebitda",
        "closing_receivables",
        "closing_inventory",
        "closing_payables",
        "cash_capex",
        "da",
    ):
        assert (
            after["legacy_forecast_inr_m"][1][key]
            > before["legacy_forecast_inr_m"][1][key]
        )
    for key in ("materials", "employee_expense", "other_expense"):
        assert (
            after["linked_statements_inr_m"]["legacy"][1]["income"][key]
            > before["linked_statements_inr_m"]["legacy"][1]["income"][key]
        )


def test_guided_capex_is_fixed_then_extrapolation_responds_to_revenue(inputs):
    facts, assumptions = inputs
    before = build_acquisition_model(facts, assumptions)
    changed = deepcopy(assumptions)
    changed["scenarios"]["base"]["molycop_volume_growth"][3] += 0.1
    after = build_acquisition_model(facts, changed)
    assert before["molycop_forecast_inr_m"][:3] == after["molycop_forecast_inr_m"][:3]
    assert (
        after["molycop_forecast_inr_m"][3]["cash_capex"]
        > before["molycop_forecast_inr_m"][3]["cash_capex"]
    )
    assert (
        after["molycop_forecast_inr_m"][4]["cash_capex"]
        > before["molycop_forecast_inr_m"][4]["cash_capex"]
    )


def test_history_uses_three_unique_years_and_actual_cash_capex(inputs):
    facts, assumptions = inputs
    history = facts["historical_drivers"]
    assert history["years"] == [2024, 2025, 2026]
    expected = (554.12 / 14927.14 + 1701.80 / 16386.51 + 1359.36 / 16919.36) / 3
    assert assumptions["scenarios"]["base"][
        "legacy_later_capex_revenue_fraction"
    ] == pytest.approx(expected)
    assert assumptions["scenarios"]["base"]["equipment_operating_ebitda_margin"][
        0
    ] == pytest.approx((251.29 / 2156.61 + 340.09 / 2687.53) / 2)
    previous = json.loads(
        (ROOT / "examples/tega_fy2025_reported_statements.json").read_text()
    )
    current = json.loads(
        (ROOT / "examples/tega_fy2026_reported_statements.json").read_text()
    )
    previous["annuals"][-1]["income"]["revenue"] += 1
    with pytest.raises(ValueError, match="Conflicting reported history"):
        historical_drivers(previous, current)


def test_income_to_cash_and_cash_to_debt_reconcile_without_claiming_balance(inputs):
    result = build_acquisition_model(*inputs)
    for business, rows in result["linked_statements_inr_m"].items():
        for row in rows:
            inc, bs, cf = [row[k] for k in ("income", "balance_sheet", "cash_flow")]
            assert inc["revenue"] - inc["operating_expense_total"] == pytest.approx(
                inc["operating_ebitda"]
            )
            expected_cfo = (
                cf["operating_earnings_before_tax_proxy"]
                + cf["da_addback"]
                + cf["interest_addback"]
                + cf["change_in_operating_working_capital"]
                + cf["cash_tax_proxy"]
            )
            assert cf["operating_cash_before_interest_proxy"] == pytest.approx(
                expected_cfo
            )
            assert abs(cf["fcff_reconciliation_residual"]) < 1e-8
            if business == "legacy":
                assert all(v is not None for v in bs.values())
                assert inc["net_income"] is not None
                expected_cash = cf["opening_cash_proxy"] + sum(
                    cf[k]
                    for k in (
                        "operating_cash_flow_total",
                        "investing_cash_flow_total",
                        "financing_cash_flow_total",
                    )
                )
                assert cf["closing_cash_proxy"] == pytest.approx(expected_cash)
            else:
                assert bs["total_assets"] is None and bs["total_equity"] is None
                assert (
                    bs["balance_sheet_residual"] is None and inc["net_income"] is None
                )
                assert (
                    bs["cash"] is None
                    and bs["gross_debt_including_leases_proxy"] is None
                )


def test_guidance_removes_actual_interest_and_no_consensus_wacc_is_invented(inputs):
    facts, assumptions = inputs
    result = build_acquisition_model(facts, assumptions)
    first = result["financing_schedule"][0]
    assert first["parent_cash_interest_inr_m"] + 193.23 == pytest.approx(1150)
    assert first["molycop_cash_interest_inr_m"] + 973.85 == pytest.approx(63 * 94.97)
    assert result["forecast_evidence"]["consensus_review"]["group_wacc"] is None
    assumptions["pro_forma"]["wacc"]["tega"]["beta"] = 0.9
    result = build_acquisition_model(facts, assumptions)
    entry = next(
        r
        for r in result["forecast_evidence"]["drivers"]
        if r["line_item"] == "Pro-forma consolidation and blended WACC"
    )
    assert entry["changed_since_review"]
    assert "override" in entry["status"]


def test_land_is_not_depreciated():
    assets = _Assets(100, 10, land=50)
    for _ in range(15):
        row = assets.advance(1, 0, 0, 8, 6)
        assert abs(row["asset_rollforward_residual"]) < 1e-9
    assert row["closing_asset_book_proxy"] == 50
    assert row["da"] == 0
