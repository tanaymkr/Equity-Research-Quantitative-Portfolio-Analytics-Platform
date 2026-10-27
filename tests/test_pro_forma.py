"""Independent arithmetic, claim scope, currency and consolidation regressions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.case_studies.tega import build_acquisition_model
from equity_analytics.case_studies.tega.equity_bridge import build_equity_bridge
from equity_analytics.case_studies.tega.history import load_acquisition_facts
from equity_analytics.case_studies.tega.wacc import blended_wacc, standalone_wacc

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    f, _, _ = load_acquisition_facts(ROOT / "examples/tega_molycop_facts.json")
    return f, json.loads((ROOT / "examples/tega_molycop_assumptions.json").read_text())


def test_hand_calculated_wacc_with_tax_shield_and_premium():
    x = {
        "government_bond_yield": 0.05,
        "sovereign_default_spread": 0.01,
        "equity_risk_premium": 0.06,
        "unlevered_beta": 0.6,
        "cost_of_debt": 0.08,
        "tax_rate": 0.25,
        "debt_weight": 0.4,
        "currency": "USD",
    }
    w = standalone_wacc(x)
    # Unlevered cost 4% + 0.6 x 6% = 7.6%; shield 40% x 25% x 8% = 0.8%
    assert w["risk_free_rate"] == pytest.approx(0.04)
    assert w["unlevered_cost_of_capital"] == pytest.approx(0.076)
    assert w["tax_shield"] == pytest.approx(0.008)
    assert w["standalone_wacc"] == pytest.approx(0.068)
    premium = standalone_wacc({**x, "transaction_premium": 0.02})
    assert premium["standalone_wacc"] == pytest.approx(0.088)
    with pytest.raises(ValueError):
        standalone_wacc({**x, "transaction_premium": -0.01})


@pytest.mark.parametrize(
    "key,value",
    [
        ("debt_weight", 1.1),
        ("debt_weight", -0.1),
        ("tax_rate", 1.1),
        ("unlevered_beta", float("nan")),
        ("unlevered_beta", 0.0),
        ("sovereign_default_spread", 0.2),
    ],
)
def test_invalid_wacc_rejected(inputs, key, value):
    x = deepcopy(inputs[1]["pro_forma"]["wacc"]["molycop"])
    x[key] = value
    with pytest.raises(ValueError):
        standalone_wacc(x)


def test_blend_weights_are_the_models_own_business_values(inputs):
    f, a = inputs
    m = build_acquisition_model(f, a)
    w = m["wacc_calculation"]
    values = m["standalone_values_for_audit_inr_m"]
    tega, molycop = (values[k]["enterprise_value"] for k in ("tega", "molycop"))
    share = tega / (tega + molycop)
    assert w["tega_ev_weight"] == pytest.approx(share)
    assert w["molycop_ev_weight"] == pytest.approx(1 - share)
    assert w["blended_wacc"] == pytest.approx(
        share * w["tega"]["standalone_wacc"]
        + (1 - share) * w["molycop"]["standalone_wacc"]
    )
    # One blended rate should nearly reproduce the sum of the two valuations.
    group = m["group_dcf_inr_m"]["enterprise_value"]
    assert group == pytest.approx(tega + molycop, rel=0.01)
    direct = blended_wacc(a["pro_forma"], "base", tega, molycop)
    assert direct["blended_wacc"] == pytest.approx(w["blended_wacc"])
    with pytest.raises(ValueError):
        blended_wacc(a["pro_forma"], "base", -1.0, molycop)


@pytest.mark.parametrize("case", ["downside", "base", "upside"])
def test_consolidated_statements_eliminate_investment_and_dividends(inputs, case):
    f, a = inputs
    m = build_acquisition_model(f, a, case)
    c = m["consolidated_statements_inr_m"]
    opening = c["opening"]
    assert opening["total_assets"] == pytest.approx(
        f["q1_fy2027"]["group_assets"] + 953.99939
    )
    assert opening["total_liabilities"] == pytest.approx(
        f["q1_fy2027"]["group_liabilities"]
    )
    assert opening["legacy_unresolved_opening_gap"] == pytest.approx(-15.875)
    for row, legacy, mc, group, fin in zip(
        c["forecast"],
        m["linked_statements_inr_m"]["legacy"],
        m["molycop_forecast_inr_m"],
        m["group_forecast_inr_m"],
        m["financing_schedule"],
        strict=True,
    ):
        assert "investment_in_molycop_at_cost" not in row["assets"]
        assert row["income"]["revenue"] == pytest.approx(
            legacy["income"]["revenue"] + mc["revenue"]
        )
        assert row["income"][
            "other_income_after_dividend_elimination"
        ] == pytest.approx(
            legacy["income"]["other_income"] - fin["tega_share_of_distribution_inr_m"]
        )
        assert row["fcff"]["fcff"] == pytest.approx(group["fcff"])
        assert (
            row["assets"]["unallocated_acquired_assets_opening_only"]
            == opening["assets"]["unallocated_acquired_assets_opening_only"]
        )
        assert (
            row["liabilities"]["unallocated_acquired_liabilities_opening_only"]
            == opening["liabilities"]["unallocated_acquired_liabilities_opening_only"]
        )
        assert row["balance_sheet"]["balance_sheet_residual"] == pytest.approx(
            0, abs=1e-7
        )
        assert row["cash_flow"]["cash_rollforward_residual"] == pytest.approx(
            0, abs=1e-7
        )


def test_full_year_stub_includes_june_but_dcf_excludes_it(inputs):
    m = build_acquisition_model(*inputs)
    s = m["fy27_stub_bridge"]
    f = inputs[0]
    assert s["molycop_full_year_owned_months"] == 10
    assert s["future_months_discounted"] == 9
    assert s["consolidated_full_year_revenue"] == pytest.approx(
        s["actual_ytd_revenue"] + s["future_consolidated_revenue"]
    )
    c = m["consolidated_statements_inr_m"]
    annual = c["full_fiscal_year_income"]["rows"][0]["income"]
    assert annual["revenue"] == pytest.approx(s["consolidated_full_year_revenue"])
    assert annual["owners_net_income_proxy"] == pytest.approx(
        c["forecast"][0]["income"]["owners_net_income_proxy"]
        + f["q1_fy2027"]["owners_pat"]
    )


def test_fx_input_reconverts_usd_origins_and_preserves_reported_inr(inputs):
    f, a = deepcopy(inputs)
    f0 = deepcopy(f)
    a0 = deepcopy(a)
    a["pro_forma"]["fx_inr_per_usd"] = 100
    m = build_acquisition_model(f, a)
    assert f == f0  # pure function: no mutations to historical data
    assert a["currency_basis"] == a0["currency_basis"]
    assert m["equity_bridge"]["molycop_net_debt_full_inr_m"] == pytest.approx(
        672.5 * 100
    )
    assert m["equity_bridge"]["preference_fair_value_full_inr_m"] == pytest.approx(
        270 * 100
    )
    assert m["wacc_calculation"]["molycop_weight_ev_inr_m"] == pytest.approx(
        m["standalone_values_for_audit_inr_m"]["molycop"]["enterprise_value"]
    )
    assert m["fy27_stub_bridge"]["actual_ytd_revenue"] == pytest.approx(
        f0["q1_fy2027"]["group_revenue"]
    )
    assert m["legacy_forecast_inr_m"][0]["revenue"] == pytest.approx(
        build_acquisition_model(f, a0)["legacy_forecast_inr_m"][0]["revenue"]
    )


@pytest.mark.parametrize("nci", [0.0, 0.1582, 1.0])
def test_bridge_deducts_nci_only_after_molycop_senior_claims(inputs, nci):
    f, a = inputs
    opening = {"opening_net_debt_including_leases_estimate": 10, "new_parent_loan": 0}
    f = deepcopy(f)
    a = deepcopy(a)
    f["q1_fy2027"]["molycop_net_debt_inr_m"] = 20
    a["shared"]["preference_fair_value_inr_m"] = 30
    a["shared"]["molycop_other_claims_inr_m"] = 5
    a["pro_forma"]["shares"]["include_follow_on"] = False
    b = build_equity_bridge(300, 100, opening, f, a, 5, 1 - nci)
    # 100 subsidiary EV - 20 debt - 30 pref - 5 earnout - 5 other = 40 common.
    assert b["minority_interest_inr_m"] == pytest.approx(nci * 40)
    expected = 300 - (10 + 20) - 30 - 5 - 5 - nci * 40 + b["nonoperating_assets_inr_m"]
    assert b["raw_tega_equity_inr_m"] == pytest.approx(expected)
    stressed = build_equity_bridge(300, 10, opening, f, a, 5, 1 - nci)
    assert stressed["minority_interest_inr_m"] == 0  # never subtract negative NCI


def test_debt_paydown_and_parent_term_loan_not_applied_twice(inputs):
    m = build_acquisition_model(*inputs)
    b = m["equity_bridge"]
    o = m["opening_bridge_inr_m"]
    assert b["parent_new_term_debt_already_included_inr_m"] == 15000
    assert b["molycop_preference_funded_paydown_already_included_inr_m"] == 270 * 94.97
    assert b["consolidated_net_debt_inr_m"] == pytest.approx(
        o["opening_net_debt_including_leases_estimate"] + 672.5 * 94.97 - 953.99939
    )


def test_operating_cashflows_do_not_depend_on_ownership(inputs):
    f, a = deepcopy(inputs)
    before = build_acquisition_model(f, a)
    a["pro_forma"]["molycop_nci_fraction_override"] = 0.25
    after = build_acquisition_model(f, a)
    assert before["group_forecast_inr_m"] == after["group_forecast_inr_m"]
    assert before["group_dcf_inr_m"] == after["group_dcf_inr_m"]
    assert after["equity_bridge"]["minority_interest_inr_m"] == pytest.approx(
        0.25 * after["equity_bridge"]["molycop_common_equity_inr_m"]
    )


def test_intercompany_eliminations_change_presentation_not_cashflow(inputs):
    f, a = deepcopy(inputs)
    before = build_acquisition_model(f, a)
    c = a["pro_forma"]["consolidation"]
    c["intercompany_revenue_inr_m"] = 100
    c["intercompany_operating_cost_inr_m"] = 100
    c["intercompany_receivable_payable_inr_m"] = 10
    after = build_acquisition_model(f, a)
    assert after["group_dcf_inr_m"] == before["group_dcf_inr_m"]
    assert after["group_forecast_inr_m"][0]["revenue"] == pytest.approx(
        before["group_forecast_inr_m"][0]["revenue"] - 75
    )


def test_higher_entity_risk_changes_blend_and_value(inputs):
    f, a = deepcopy(inputs)
    before = build_acquisition_model(f, a)
    a["pro_forma"]["wacc"]["molycop"]["unlevered_beta"] += 0.3
    after = build_acquisition_model(f, a)
    assert (
        after["wacc_calculation"]["blended_wacc"]
        > before["wacc_calculation"]["blended_wacc"]
    )
    assert (
        after["group_dcf_inr_m"]["enterprise_value"]
        < before["group_dcf_inr_m"]["enterprise_value"]
    )
