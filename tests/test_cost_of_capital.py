"""The shared cost-of-capital method and its use across every model."""

import json
from pathlib import Path

import pytest

from equity_analytics.case_studies.tega import build_acquisition_model
from equity_analytics.case_studies.tega.engine import market_implied_group_wacc
from equity_analytics.case_studies.tega.history import load_acquisition_facts
from equity_analytics.case_studies.wabag.model import build_model, load_inputs
from equity_analytics.valuation.cost_of_capital import (
    cost_of_equity,
    default_free_rate,
    implied_discount_rate,
    relever_beta,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def _json(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_default_free_rate_removes_sovereign_spread():
    assert default_free_rate(0.071194, 0.0187) == pytest.approx(0.052494)
    with pytest.raises(ValueError):
        default_free_rate(0.05, 0.06)
    with pytest.raises(ValueError):
        default_free_rate(0.05, -0.01)


def test_relever_beta_hand_calculation():
    # 0.9 x (1 + 0.75 x 0.5 + 0.25) = 1.4625
    assert relever_beta(0.9, 0.5, 0.25, 0.25) == pytest.approx(1.4625)
    assert relever_beta(1.14, 0.0, 0.25) == pytest.approx(1.14)
    for bad in ((0.0, 0.5, 0.25), (1.0, -0.1, 0.25), (1.0, 0.5, 1.0)):
        with pytest.raises(ValueError):
            relever_beta(*bad)


def test_cost_of_equity_is_capm():
    assert cost_of_equity(0.05, 1.2, 0.07) == pytest.approx(0.134)
    with pytest.raises(ValueError):
        cost_of_equity(0.05, float("nan"), 0.07)


def test_implied_rate_solves_and_refuses_to_extrapolate():
    def value_at(rate):
        return 100 / (rate - 0.04)

    rate = implied_discount_rate(value_at, 1000, low=0.05, high=0.30)
    assert rate == pytest.approx(0.14, abs=1e-6)
    assert implied_discount_rate(value_at, 1.0, low=0.05, high=0.2) is None


def test_every_model_uses_the_same_india_risk_premiums():
    tega = _json("tega_molycop_assumptions.json")["pro_forma"]["wacc"]["tega"]
    linked = _json("wabag_linked/wacc_reference.json")
    generic = _json("wabag_dcf_assumptions.json")["scenarios"]
    india_erp = linked["mature_erp"] + linked["country_risk_premium"]
    assert india_erp == pytest.approx(0.0708)
    assert tega["equity_risk_premium"] == pytest.approx(india_erp)
    assert tega["sovereign_default_spread"] == linked["sovereign_default_spread"]
    for case in generic.values():
        w = case["wacc_inputs"]
        assert w["equity_risk_premium"] == pytest.approx(india_erp)
        assert w["sovereign_default_spread"] == linked["sovereign_default_spread"]
        assert w["government_bond_yield"] == linked["gsec_yield"]
        assert w["unlevered_beta"] == linked["unlevered_beta"]


def test_scenarios_share_discount_and_terminal_parameters():
    tega = _json("tega_molycop_assumptions.json")
    stress = tega["pro_forma"]["wacc"]["scenario_risk_premium"]
    assert set(stress.values()) == {0.0}
    terminal = {
        (c["group_terminal_growth_inr"], c["group_terminal_roic"])
        for c in tega["scenarios"].values()
    }
    assert terminal == {(0.04, 0.16)}
    generic = _json("wabag_dcf_assumptions.json")["scenarios"]
    assert (
        len({json.dumps(c["wacc_inputs"], sort_keys=True) for c in generic.values()})
        == 1
    )
    assert {
        (c["forecast"]["terminal_growth"], c["forecast"]["terminal_roic"])
        for c in generic.values()
    } == {(0.04, 0.15)}


def test_tega_scenarios_use_the_same_business_rates():
    facts, _, _ = load_acquisition_facts(EXAMPLES / "tega_molycop_facts.json")
    assumptions = _json("tega_molycop_assumptions.json")
    models = [
        build_acquisition_model(facts, assumptions, case)["wacc_calculation"]
        for case in ("downside", "base", "upside")
    ]
    for business in ("tega", "molycop"):
        assert len({w[business]["standalone_wacc"] for w in models}) == 1
    # The blend moves only with each scenario's business mix.
    blends = [w["blended_wacc"] for w in models]
    assert max(blends) - min(blends) < 0.001


def test_tega_market_implied_rate_reproduces_the_price():
    facts, _, _ = load_acquisition_facts(EXAMPLES / "tega_molycop_facts.json")
    assumptions = _json("tega_molycop_assumptions.json")
    check = market_implied_group_wacc(facts, assumptions)
    assert check["price_inr"] == pytest.approx(1696.80)
    at_implied = build_acquisition_model(
        facts, assumptions, group_wacc_override=check["implied_group_wacc"]
    )
    assert at_implied["equity_bridge"]["value_per_share_inr"] == pytest.approx(
        1696.80, abs=0.01
    )
    assert check["implied_group_wacc"] < check["model_group_wacc"]


def test_tega_override_only_moves_the_group_rate():
    facts, _, _ = load_acquisition_facts(EXAMPLES / "tega_molycop_facts.json")
    assumptions = _json("tega_molycop_assumptions.json")
    base = build_acquisition_model(facts, assumptions)
    rate = base["wacc_calculation"]["blended_wacc"]
    same = build_acquisition_model(facts, assumptions, group_wacc_override=rate)
    assert same["equity_bridge"]["value_per_share_inr"] == pytest.approx(
        base["equity_bridge"]["value_per_share_inr"]
    )
    with pytest.raises(ValueError):
        build_acquisition_model(facts, assumptions, group_wacc_override=1.5)


def test_wabag_market_implied_rate_reproduces_the_price():
    model = build_model(load_inputs(EXAMPLES / "wabag_linked"))
    check = model["market_check"]
    rate = check["implied_wacc"]
    assert rate is not None and rate < check["model_wacc_first_year"]
    # Rebuild the per-share value at the implied rate, independently of the model.
    dcf = model["dcf"]
    factor, pv = 1.0, 0.0
    for row in dcf["forecast"]:
        factor /= 1 + rate
        pv += row["fcff"] * factor
    nopat = dcf["forecast"][-1]["nopat"] * (1 + dcf["terminal_growth"])
    terminal = nopat * (1 - dcf["terminal_growth"] / dcf["terminal_roic"])
    terminal /= rate - dcf["terminal_growth"]
    equity = (
        pv
        + terminal * factor
        + dcf["cash"]
        + dcf["nonoperating_assets"]
        - dcf["debt"]
        - dcf["minority_interest"]
        - dcf["other_claims"]
    )
    years = (178) / 365  # 31 March to 25 September 2026
    value = equity / dcf["shares_million"] * (1 + rate) ** years
    assert value == pytest.approx(check["price_inr"], rel=1e-5)
