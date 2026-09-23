"""Independent arithmetic and boundary checks for the single group valuation."""

import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from equity_analytics.acquisition import engine
from equity_analytics.acquisition.history import load_acquisition_facts

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    facts, _, _ = load_acquisition_facts(ROOT / "examples/tega_molycop_facts.json")
    assumptions = json.loads(
        (ROOT / "examples/tega_molycop_assumptions.json").read_text()
    )
    return facts, assumptions


@pytest.mark.parametrize("case", ["downside", "base", "upside"])
def test_one_consolidated_value_and_separate_audit_valuations(inputs, case):
    with patch.object(engine, "_dcf", wraps=engine._dcf) as spy:
        model = engine.build_acquisition_model(*inputs, case)
    assert spy.call_count == 3  # group valuation plus two audit/NCI intermediate EVs
    assert [k for k in model if "dcf" in k] == ["group_dcf_inr_m"]
    assert "molycop_enterprise_value_inr_m" not in model["equity_bridge"]
    assert "legacy_enterprise_value_inr_m" not in model["equity_bridge"]
    dcf = model["group_dcf_inr_m"]
    assert dcf["enterprise_value"] == pytest.approx(
        dcf["pv_forecast_fcff"] + dcf["pv_terminal_value"]
    )


def test_hand_calculated_common_discounting_and_terminal_reinvestment():
    # Two end-year cash flows, one terminal NOPAT and reinvestment requirement.
    rows = [
        {"fcff": 100, "discount_years": 1},
        {"fcff": 120, "discount_years": 2, "normalized_terminal_nopat": 200},
    ]
    result = engine._dcf(rows, 0.10, 0.02, 0.20)
    expected_terminal_fcff = 204 - 20.4
    expected_ev = 100 / 1.1 + 120 / 1.21 + (expected_terminal_fcff / 0.08) / 1.21
    assert result["terminal_fcff"] == pytest.approx(expected_terminal_fcff)
    assert result["enterprise_value"] == pytest.approx(expected_ev)


@pytest.mark.parametrize("ownership", [0, 0.8417868954269925, 1])
def test_attribution_includes_negative_cash_flows_and_matching_claims(
    inputs, ownership
):
    f, a = deepcopy(inputs)
    f["deal"]["tega_ordinary_contribution_inr_m"] = 40000 * ownership
    f["deal"]["apollo_ordinary_contribution_inr_m"] = 40000 * (1 - ownership)
    # A deliberately large investment creates a negative Molycop cash flow.
    a["scenarios"]["base"]["molycop_later_annual_capex_inr_m"][1] = 100000
    m = engine.build_acquisition_model(f, a)
    assert m["molycop_forecast_inr_m"][1]["fcff"] < 0
    for l, mc, g in zip(
        m["legacy_forecast_inr_m"],
        m["molycop_forecast_inr_m"],
        m["group_forecast_inr_m"],
        strict=True,
    ):
        assert g["fcff"] == pytest.approx(l["fcff"] + mc["fcff"])
        assert g["unlevered_cash_tax"] == pytest.approx(
            l["unlevered_cash_tax"] + mc["unlevered_cash_tax"]
        )
    b = m["equity_bridge"]
    assert b["molycop_ordinary_ownership"] == pytest.approx(ownership)
    assert b["minority_interest_inr_m"] == pytest.approx(
        (1 - ownership) * b["molycop_common_equity_inr_m"]
    )
    assert b["consolidated_net_debt_inr_m"] == pytest.approx(
        b["legacy_net_debt_inr_m"]
        + b["molycop_net_debt_full_inr_m"]
        - b["follow_on_issue_cash_added_inr_m"]
    )
    assert b["tega_equity_inr_m"] == max(b["raw_tega_equity_inr_m"], 0)


def test_losses_do_not_offset_another_tax_jurisdictions_terminal_profit(inputs):
    m = engine.build_acquisition_model(*inputs)
    legacy = deepcopy(m["legacy_forecast_inr_m"][:1])
    molycop = deepcopy(m["molycop_forecast_inr_m"][:1])
    legacy[0].update(ebit=-100, ppa_amortization=0)
    molycop[0].update(ebit=200, ppa_amortization=0)
    combined = engine.consolidate_operating(
        legacy, molycop, 0.25, 0.27, inputs[1]["pro_forma"]
    )
    assert combined[0]["normalized_terminal_nopat"] == pytest.approx(-100 + (200 - 54))


def test_earnout_uses_common_group_discount_rate(inputs):
    f, a = inputs
    m = engine.build_acquisition_model(f, a)
    case = a["scenarios"]["base"]
    years = (
        date.fromisoformat(case["earnout_payment_date"]) - date(2026, 6, 30)
    ).days / 365
    assert m["equity_bridge"]["earnout_present_value_full_inr_m"] == pytest.approx(
        case["earnout_inr_m"] / (1 + m["wacc_calculation"]["blended_wacc"]) ** years
    )


@pytest.mark.parametrize(
    "old_key",
    [
        "legacy_wacc_inr",
        "legacy_terminal_growth_inr",
        "legacy_terminal_roic",
        "molycop_discount_rate",
        "molycop_terminal_growth",
        "molycop_terminal_roic",
    ],
)
def test_retired_separate_dcf_settings_rejected(inputs, old_key):
    f, a = deepcopy(inputs)
    a["scenarios"]["base"][old_key] = 0.1
    with pytest.raises(engine.AcquisitionInputError, match="Separate business"):
        engine.build_acquisition_model(f, a)


def test_missing_group_method_rejected(inputs):
    f, a = deepcopy(inputs)
    del a["valuation_method"]
    with pytest.raises(engine.AcquisitionInputError, match="single group"):
        engine.build_acquisition_model(f, a)
