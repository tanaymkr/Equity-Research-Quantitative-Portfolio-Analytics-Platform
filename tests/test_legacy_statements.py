"""Financial invariants for the legacy-only historical/zero fallback update."""

import json
from copy import deepcopy
from math import isfinite
from pathlib import Path

import pytest

from equity_analytics.acquisition import AcquisitionInputError, build_acquisition_model
from equity_analytics.acquisition.history import load_acquisition_facts

ROOT = Path(__file__).resolve().parents[1]


def assert_forecast_matches(actual, expected, path="forecast"):
    """Accept floating-point summation noise, preserving values and structure.

    Absolute tolerance 1e-8 is INR0.01 for INR-million amounts. No relative
    tolerance: large balances must not receive looser comparison thresholds.
    Text, missing fields, lengths, integers and None still compare exactly.
    """
    if isinstance(expected, dict):
        assert isinstance(actual, dict), path
        assert actual.keys() == expected.keys(), path
        for key in expected:
            assert_forecast_matches(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), path
        assert len(actual) == len(expected), path
        for i, (value, reference) in enumerate(zip(actual, expected, strict=True)):
            assert_forecast_matches(value, reference, f"{path}[{i}]")
    elif isinstance(expected, float):
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool), path
        assert actual == pytest.approx(expected, rel=0, abs=1e-8), path
    else:
        assert type(actual) is type(expected), path
        assert actual == expected, path


@pytest.fixture
def inputs():
    facts, _, _ = load_acquisition_facts(ROOT / "examples/tega_molycop_facts.json")
    assumptions = json.loads(
        (ROOT / "examples/tega_molycop_assumptions.json").read_text()
    )
    return facts, assumptions


@pytest.mark.parametrize("case", ["downside", "base", "upside"])
def test_complete_legacy_lines_reconcile_through_the_three_statements(inputs, case):
    model = build_acquisition_model(*inputs, case)
    opening = model["legacy_statement_opening_inr_m"]
    opening_cash = opening["assets"]["cash"]
    retained = opening["equity"]["retained_earnings"]
    for row, funding in zip(
        model["linked_statements_inr_m"]["legacy"],
        model["financing_schedule"],
        strict=True,
    ):
        income, bs, cf = (row[k] for k in ("income", "balance_sheet", "cash_flow"))
        for section in (income, bs, cf):
            assert all(
                isinstance(v, (int, float)) and isfinite(v) for v in section.values()
            )
        assert income["profit_before_tax"] == pytest.approx(
            income["operating_profit_after_integration"]
            - income["finance_cost_cash_proxy"]
            + income["other_income"]
            + income["joint_venture_profit"]
        )
        assert income["net_income"] == pytest.approx(
            income["profit_before_tax"]
            - income["current_tax_expense"]
            - income["deferred_tax_expense"]
        )
        assert income["eps_inr"] == pytest.approx(income["net_income"] / 75.127698)
        cfo = sum(
            cf[k]
            for k in (
                "profit_before_tax",
                "da_addback",
                "interest_addback",
                "joint_venture_profit_reversal",
                "investing_income_reversal",
                "other_noncash_adjustments",
                "change_in_operating_working_capital",
                "income_tax_paid",
            )
        )
        assert cf["operating_cash_flow_total"] == pytest.approx(cfo)
        cash = opening_cash + sum(
            cf[k]
            for k in (
                "operating_cash_flow_total",
                "investing_cash_flow_total",
                "financing_cash_flow_total",
                "fx_effect_on_cash",
            )
        )
        assert cash == pytest.approx(row["assets"]["cash"])
        assert cash == pytest.approx(funding["parent_closing_cash_inr_m"])
        retained += income["net_income"] + cf["dividends_to_tega_shareholders"]
        assert retained == pytest.approx(row["equity"]["retained_earnings"])
        assert bs["total_assets"] == pytest.approx(sum(row["assets"].values()))
        assert bs["total_liabilities"] == pytest.approx(
            sum(row["liabilities"].values())
        )
        assert bs["total_equity"] == pytest.approx(sum(row["equity"].values()))
        # A nonzero opening discrepancy must remain visible, not silently pass as balanced.
        assert bs["total_assets"] - bs["total_liabilities"] - bs[
            "total_equity"
        ] == pytest.approx(opening["balance_sheet_residual_inr_m"])
        assert abs(opening["balance_sheet_residual_inr_m"]) > 1
        assert max(abs(v) for v in row["checks"].values()) < 1e-7
        opening_cash = cash


@pytest.mark.parametrize("case", ["downside", "base", "upside"])
def test_approved_operating_forecasts_and_molycop_schedules_are_unchanged(inputs, case):
    baseline = json.loads(
        (ROOT / "tests/fixtures/legacy_update_baseline.json").read_text()
    )
    model = build_acquisition_model(*inputs, case)
    for key, expected in baseline["cases"][case].items():
        # DCF/bridge and group structure intentionally superseded by consolidation.
        # Preserve every original business operating row and Molycop funding view.
        if key not in {
            "legacy_forecast_inr_m",
            "molycop_forecast_inr_m",
            "molycop_statements",
        }:
            continue
        data = (
            model["linked_statements_inr_m"]["molycop"]
            if key == "molycop_statements"
            else model[key]
        )
        if key in {"scenario_assumptions", "shared_assumptions"}:
            assert data == expected, key
        else:
            assert_forecast_matches(data, expected, f"{case}.{key}")


def test_zero_movements_preserve_existing_balances_and_shares(inputs):
    facts, _ = inputs
    model = build_acquisition_model(*inputs)
    base = facts["legacy_statement_history"]["annuals"][-1]
    for row in model["linked_statements_inr_m"]["legacy"]:
        for key in (
            "goodwill",
            "deferred_tax_assets",
            "noncurrent_tax_assets",
            "current_tax_assets",
        ):
            assert row["assets"][key] == base["assets"][key] > 0
        for key in (
            "deferred_tax_liabilities",
            "noncurrent_provisions",
            "current_tax_liabilities",
        ):
            assert row["liabilities"][key] == base["liabilities"][key] > 0
        assert row["equity"]["share_capital"] == base["equity"]["share_capital"]
        assert row["equity"]["other_reserves"] == base["equity"]["other_reserves"]
        assert row["income"]["deferred_tax_expense"] == 0
        assert row["income"]["other_comprehensive_income"] == 0
        assert row["cash_flow"]["equity_issuance"] == 0
        assert row["cash_flow"]["fx_effect_on_cash"] == 0


def test_dividends_flow_into_cash_debt_and_equity_without_reentering_fcff(inputs):
    facts, assumptions = inputs
    before = build_acquisition_model(facts, assumptions)
    changed = deepcopy(assumptions)
    changed["legacy_statement_policy"]["dividend_per_share_inr"] = 0
    after = build_acquisition_model(facts, changed)
    payment = 2 * 75.127698
    assert before["financing_schedule"][0][
        "parent_dividends_paid_inr_m"
    ] == pytest.approx(payment)
    assert before["financing_schedule"][0]["parent_closing_gross_debt_inr_m"] - after[
        "financing_schedule"
    ][0]["parent_closing_gross_debt_inr_m"] == pytest.approx(payment)
    assert after["linked_statements_inr_m"]["legacy"][0]["equity"][
        "retained_earnings"
    ] - before["linked_statements_inr_m"]["legacy"][0]["equity"][
        "retained_earnings"
    ] == pytest.approx(payment)
    assert before["group_forecast_inr_m"] == after["group_forecast_inr_m"]
    assert before["equity_bridge"] == after["equity_bridge"]
    assert (
        before["linked_statements_inr_m"]["molycop"]
        == after["linked_statements_inr_m"]["molycop"]
    )


def test_historical_tax_and_treasury_income_do_not_create_tax_refunds_on_losses(inputs):
    facts, assumptions = deepcopy(inputs)
    assumptions["scenarios"]["base"]["consumables_operating_ebitda_margin"][1] = 0
    assumptions["scenarios"]["base"]["equipment_operating_ebitda_margin"][1] = 0
    model = build_acquisition_model(facts, assumptions)
    income = model["linked_statements_inr_m"]["legacy"][1]["income"]
    assert income["operating_earnings_before_tax_proxy"] < 0
    assert income["current_tax_expense"] == 0
    assert income["deferred_tax_expense"] == 0
    p = model["legacy_statement_assumptions"]["parameters"]
    expected_tax = (
        (564.06 - 32.9) / 2469.73
        + (749.43 - 158.65) / 2591.98
        + (918.4 - 333.81) / 2011.12
    ) / 3
    assert p["effective_tax_rate"] == pytest.approx(expected_tax)
    assert p["cash_interest_yield"] == pytest.approx(
        42.99 / ((863.17 + 3.94 + 1142.95 + 68.61) / 2)
    )


def test_fallback_policy_rejects_negative_dividend(inputs):
    facts, assumptions = deepcopy(inputs)
    assumptions["legacy_statement_policy"]["dividend_per_share_inr"] = -1
    with pytest.raises(AcquisitionInputError, match="nonnegative dividend"):
        build_acquisition_model(facts, assumptions)
