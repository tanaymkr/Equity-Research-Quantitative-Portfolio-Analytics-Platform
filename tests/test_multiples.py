"""P/E cross-check arithmetic and its use in both company models."""

import json
from pathlib import Path

import pytest

from equity_analytics.case_studies.tega.engine import (
    build_acquisition_model,
    market_implied_group_wacc,
)
from equity_analytics.case_studies.tega.history import load_acquisition_facts
from equity_analytics.case_studies.wabag.model import build_model, load_inputs
from equity_analytics.valuation.multiples import pe_cross_check, pe_text

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
BENCHMARK = {
    "name": "Test index",
    "pe": 20.0,
    "basis": "trailing earnings",
    "observed_on": "1 January 2026",
    "url": "https://example.org",
    "note": "Cross-check only.",
}


def test_pe_cross_check_hand_calculation():
    check = pe_cross_check(BENCHMARK, 2028, 50.0, 1500.0, 600.0)
    assert check["pe_value_per_share"] == pytest.approx(1000.0)
    assert check["market_pe"] == pytest.approx(30.0)
    assert check["dcf_pe"] == pytest.approx(12.0)
    assert "INR1,000.00 per share" in pe_text(check, "Example")


def test_non_positive_eps_gives_no_pe_value():
    check = pe_cross_check(BENCHMARK, 2028, -5.0, 1500.0, 600.0)
    assert check["pe_value_per_share"] is None
    assert check["market_pe"] is None
    assert "not meaningful" in pe_text(check, "Example")


@pytest.mark.parametrize(
    "change",
    [
        {"pe": 0},
        {"pe": float("nan")},
        {"name": None},
    ],
)
def test_bad_benchmark_is_rejected(change):
    benchmark = dict(BENCHMARK)
    if change.get("name", 1) is None:
        del benchmark["name"]
    else:
        benchmark.update(change)
    with pytest.raises((TypeError, ValueError)):
        pe_cross_check(benchmark, 2028, 50.0, 1500.0, 600.0)


def test_both_models_use_one_benchmark_and_fy2028_eps():
    facts, _, _ = load_acquisition_facts(EXAMPLES / "tega_molycop_facts.json")
    assumptions = json.loads((EXAMPLES / "tega_molycop_assumptions.json").read_text())
    tega = market_implied_group_wacc(facts, assumptions)["pe_cross_check"]
    model = build_acquisition_model(facts, assumptions)
    rows = model["consolidated_statements_inr_m"]["full_fiscal_year_income"]["rows"]
    eps = next(r for r in rows if r["fiscal_year"] == 2028)["income"]
    assert tega["eps"] == pytest.approx(eps["pro_forma_eps_inr"])
    assert tega["pe_value_per_share"] == pytest.approx(28.16 * tega["eps"])
    assert tega["market_pe"] == pytest.approx(1696.80 / tega["eps"])

    wabag_model = build_model(load_inputs(EXAMPLES / "wabag_linked"))
    wabag = wabag_model["market_check"]["pe_cross_check"]
    fy2028 = next(r for r in wabag_model["forecast"] if r["year"] == 2028)
    assert wabag["eps"] == pytest.approx(fy2028["income_statement"]["diluted_eps"])
    assert wabag["benchmark"] == tega["benchmark"]
    assert wabag["dcf_value_per_share"] == pytest.approx(
        wabag_model["dcf"]["implied_value_per_share"]
    )


def test_tega_consensus_comparison_lines_up_with_the_model():
    facts, _, _ = load_acquisition_facts(EXAMPLES / "tega_molycop_facts.json")
    assumptions = json.loads((EXAMPLES / "tega_molycop_assumptions.json").read_text())
    comparison = market_implied_group_wacc(facts, assumptions)["consensus_comparison"]
    model = build_acquisition_model(facts, assumptions)
    rows = model["consolidated_statements_inr_m"]["full_fiscal_year_income"]["rows"]
    income = {r["fiscal_year"]: r["income"] for r in rows}
    assert [y["fiscal_year"] for y in comparison["years"]] == [2027, 2028, 2029]
    fy28 = next(y for y in comparison["years"] if y["fiscal_year"] == 2028)
    lines = {line["line"]: line for line in fy28["lines"]}
    assert lines["EPS (INR)"]["consensus"] == 93.6
    assert lines["EPS (INR)"]["model"] == pytest.approx(
        income[2028]["pro_forma_eps_inr"]
    )
    interest = lines["Interest (model: incl. preference return)"]
    assert interest["model"] == pytest.approx(
        income[2028]["bank_and_lease_finance_cost"]
        + income[2028]["preference_return_economic_charge"]
    )
    for line in fy28["lines"]:
        assert line["difference"] == pytest.approx(line["model"] - line["consensus"])
    assert fy28["consensus_pe_at_snapshot_price"] == pytest.approx(1935 / 93.6)
    # Consensus never reaches the valuation.
    without = dict(facts)
    without.pop("consensus_snapshot")
    assert build_acquisition_model(without, assumptions)["equity_bridge"][
        "value_per_share_inr"
    ] == pytest.approx(model["equity_bridge"]["value_per_share_inr"])
