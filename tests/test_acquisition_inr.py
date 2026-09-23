"""Currency conversions checked against independently stated source amounts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.acquisition import AcquisitionInputError, build_acquisition_model
from equity_analytics.acquisition.history import load_acquisition_facts
from equity_analytics.acquisition.reporting import sensitivities

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    facts, _, _ = load_acquisition_facts(ROOT / "examples/tega_molycop_facts.json")
    assumptions = json.loads(
        (ROOT / "examples/tega_molycop_assumptions.json").read_text()
    )
    return facts, assumptions


def test_material_disclosures_are_translated_once_and_actuals_preserved(inputs):
    f, a = inputs
    assert f["currency_basis"]["inr_per_usd"] == 94.97
    assert f["currency_basis"]["fx_date"] == "2026-09-02"
    assert f["q1_fy2027"]["molycop_net_debt_inr_m"] == pytest.approx(672.5 * 94.97)
    assert f["deal"]["apollo_preference_issue_inr_m"] == pytest.approx(270 * 94.97)
    assert f["deal"]["provisional_intangibles_inr_m"] == pytest.approx(362.3 * 94.97)
    assert f["deal"]["reported_provisional_intangibles_inr_m"] == 34295.32
    assert f["q1_fy2027"]["molycop_revenue_inr_m"] == 12916.4
    assert f["q1_fy2027"]["molycop_da_inr_m"] == 484.98
    assert f["tega_fy2026"]["revenue"] == 16919.36
    assert a["scenarios"]["base"]["molycop_cost_synergies_inr_m"] == pytest.approx(
        [2 * 94.97, 10 * 94.97, 18 * 94.97] + [20 * 94.97] * 5
    )


@pytest.mark.parametrize("case", ["downside", "base", "upside"])
def test_same_inr_units_through_cash_flows_debt_and_equity(inputs, case):
    f, a = inputs
    result = build_acquisition_model(f, a, case)
    bridge = result["equity_bridge"]
    ownership = 394.295423 / (394.295423 + 74.107477)
    assert bridge["molycop_ordinary_ownership"] == pytest.approx(ownership)
    assert bridge["molycop_net_debt_full_inr_m"] == pytest.approx(672.5 * 94.97)
    assert result["opening_bridge_inr_m"][
        "tega_equity_contribution_cash_outflow"
    ] == pytest.approx(394.295423 * 94.97)
    first = result["molycop_forecast_inr_m"][0]
    growth = a["scenarios"][case]["molycop_first_year_total_ebitda_growth"]
    assert first["operating_ebitda"] + 1710.51 == pytest.approx(
        191 * 94.97 * (1 + growth) * 10 / 12
    )
    assert result["financing_schedule"][0][
        "molycop_cash_interest_inr_m"
    ] == pytest.approx(63 * 94.97 - f["q1_fy2027"]["molycop_finance_cost_inr_m"])
    for row in result["financing_schedule"]:
        assert row["tega_share_of_distribution_inr_m"] == pytest.approx(
            row["molycop_ordinary_distribution_inr_m"] * ownership
        )
    assert result["valuation_date"] == "2026-06-30"
    assert result["monetary_unit"] == "INR million"


@pytest.mark.parametrize(
    "change", ["one_rate", "both_rates", "date", "unit", "old_key"]
)
def test_reject_mixed_currency_and_metadata_only_changes(inputs, change):
    f, a = deepcopy(inputs)
    if change == "one_rate":
        a["currency_basis"]["inr_per_usd"] = 100
    elif change == "both_rates":
        f["currency_basis"]["inr_per_usd"] = 100
        a["currency_basis"]["inr_per_usd"] = 100
    elif change == "date":
        a["currency_basis"]["fx_date"] = "2026-09-03"
    elif change == "unit":
        f["units"]["molycop"] = "USD million"
    else:
        a["shared"]["preference_fair_value_usd_m"] = 270
    with pytest.raises(AcquisitionInputError):
        build_acquisition_model(f, a)


def test_money_sensitivities_use_inr_ranges(inputs):
    rows = sensitivities(*inputs)
    preference = [
        r for r in rows if r["parameter"] == "Preference current fair value (INR m)"
    ]
    assert [r["input"] for r in preference] == pytest.approx(
        [270 * 94.97, 330 * 94.97, 400 * 94.97]
    )
    assert len(rows) == 36
    assert any(r["parameter"] == "Conversion INR per USD" for r in rows)
