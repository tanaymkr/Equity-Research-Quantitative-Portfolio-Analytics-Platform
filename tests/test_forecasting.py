"""Accounting identities, independent arithmetic, and failure-path checks."""

from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.financials.io import load_history
from equity_analytics.forecasting import (
    FundingError,
    ModelInputError,
    build_forecast,
    load_json,
    reconcile_history,
)
from equity_analytics.forecasting.engine import AssetCohort
from equity_analytics.forecasting.inputs import SERIES

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case():
    return load_json(ROOT / "examples/tega_fy2025_reported_statements.json")


@pytest.fixture
def assumptions(case, linked_assumptions):
    return linked_assumptions(case)


def test_reported_history_reconciles_and_preserves_rounding(case):
    checks = reconcile_history(case)
    assert all(c["passed"] for c in checks)
    residuals = {c["name"]: c["residual"] for c in checks}
    assert residuals["FY2025 ppe_net roll"] == pytest.approx(-0.01)
    assert residuals[
        "FY2025 short_term_debt_including_accrued_interest closing to statement"
    ] == pytest.approx(0.01)
    assert case["annuals"][-1]["assets"]["ppe"] == 3658.40


def test_history_connects_to_existing_ratio_module():
    history = load_history(ROOT / "examples/tega_fy2024_fy2025_financial_history.json")
    latest = history.annuals[-1]
    assert latest.revenue == 16386.51
    assert latest.total_debt == 3296.49
    assert latest.operating_cash_flow == 1950.30
    assert latest.capex == 1701.80


def test_forecast_links_every_schedule_without_mutating_inputs(case, assumptions):
    original_case, original_assumptions = deepcopy(case), deepcopy(assumptions)
    result = build_forecast(case, assumptions)
    prior = case["annuals"][-1]
    for row in result["years"]:
        bs, cf = row["balance_sheet"], row["cash_flow"]
        assert bs["total_assets"] == pytest.approx(
            bs["total_liabilities"] + bs["total_equity"]
        )
        assert cf["closing_cash"] == pytest.approx(
            cf["opening_cash"] + cf["operating"] + cf["investing"] + cf["financing"]
        )
        assert bs["equity"]["retained_earnings"] == pytest.approx(
            prior["equity"]["retained_earnings"]
            + row["income"]["net_income"]
            + cf["dividends"]
        )
        for schedule in row["debt_schedule"]:
            assert schedule["closing"] == pytest.approx(
                schedule["opening"]
                + schedule["cash_draw"]
                + schedule["noncash_new_leases"]
                - schedule["principal_repayment"]
            )
            assert schedule["closing"] == pytest.approx(
                bs["liabilities"][schedule["pool"]]
            )
        for schedule in row["asset_schedule"]:
            assert schedule["closing"] >= 0
            assert schedule["closing"] == pytest.approx(
                schedule["opening"]
                + schedule["additions"]
                - schedule["depreciation_amortisation"]
            )
        assert bs["assets"]["goodwill"] == 611.24
        assert bs["assets"]["other_current_assets"] == 639.60
        assert cf["closing_cash"] >= assumptions["minimum_cash"] - 1e-8
        prior = bs
    assert case == original_case
    assert assumptions == original_assumptions


def test_independently_calculated_one_year_fixture(case, assumptions):
    # Known FY2025 base; zero growth/capex/WC change/JV/dividends/new leases.
    # All depreciable opening balances run off in one year; owned land survives.
    for key in SERIES:
        assumptions[key] = [assumptions[key][0]]
    assumptions.update(
        {
            "revenue_growth": [0],
            "ebitda_margin": [0.5],
            "receivable_days": [5010.47 / 16386.51 * 365],
            "inventory_pct_revenue": [4145.25 / 16386.51],
            "payables_pct_revenue": [2223.22 / 16386.51],
            "cash_capex_pct_revenue": [0],
            "commissioning_fraction": 0,
            "term_principal_repayment": [10],
            "lease_principal_repayment": [5],
            "new_lease_assets": [0],
            "term_interest_rate": 0.1,
            "revolver_interest_rate": 0.1,
            "lease_interest_rate": 0.1,
            "joint_venture_profit": 0,
            "joint_venture_dividend": 0,
            "dividend_payout_ratio": 0,
            "minimum_cash": 0,
            "sweep_excess_cash_to_revolver": False,
        }
    )
    assumptions["opening_remaining_life_years"] = {
        k: None if k == "ppe_land" else 1
        for k in assumptions["opening_remaining_life_years"]
    }
    year = build_forecast(case, assumptions)["years"][0]
    inc, cf, bs = year["income"], year["cash_flow"], year["balance_sheet"]
    assert inc["depreciation_amortisation"] == pytest.approx(4879.93)
    assert inc["ebit"] == pytest.approx(3313.325)
    assert inc["finance_cost"] == pytest.approx(329.649)
    assert inc["tax"] == pytest.approx(745.919)
    assert inc["net_income"] == pytest.approx(2237.757)
    assert cf["operating"] == pytest.approx(7447.336)
    assert cf["closing_cash"] == pytest.approx(8245.637)
    assert bs["total_assets"] == pytest.approx(23174.777)
    assert bs["assets"]["ppe"] == pytest.approx(698.51)
    assert bs["assets"]["rou_assets"] == pytest.approx(0)
    assert year["fcff"] == pytest.approx(7364.92375)


def test_half_year_depreciation_caps_at_book_value():
    cohort = AssetCohort("machine", "ppe", 100, 50)
    assert cohort.depreciate(0.5) == 25
    assert cohort.depreciate() == 50
    assert cohort.depreciate() == 25
    assert cohort.depreciate() == 0
    assert cohort.book == 0


def test_lease_addition_is_noncash_financing_and_economic_capex(case, assumptions):
    normal = build_forecast(case, assumptions)["years"][0]
    assumptions["new_lease_assets"][0] += 120
    changed = build_forecast(case, assumptions)["years"][0]
    # Six-year life, half-year first charge: incremental D&A is 10.
    assert changed["income"]["depreciation_amortisation"] - normal["income"][
        "depreciation_amortisation"
    ] == pytest.approx(10)
    assert changed["cash_flow"]["operating"] - normal["cash_flow"][
        "operating"
    ] == pytest.approx(2.5)
    assert changed["cash_flow"]["investing"] == normal["cash_flow"]["investing"]
    assert changed["fcff"] - normal["fcff"] == pytest.approx(-117.5)


def test_slow_collections_use_cash_and_reduce_fcff(case, assumptions):
    normal = build_forecast(case, assumptions)["years"][0]
    assumptions["receivable_days"][0] += 10
    changed = build_forecast(case, assumptions)["years"][0]
    cash_tied_up = normal["income"]["revenue"] * 10 / 365
    assert changed["cash_flow"]["operating"] == pytest.approx(
        normal["cash_flow"]["operating"] - cash_tied_up
    )
    assert changed["fcff"] == pytest.approx(normal["fcff"] - cash_tied_up)
    assert changed["income"] == normal["income"]


def test_longer_asset_life_changes_ebit_tax_and_equity(case, assumptions):
    normal = build_forecast(case, assumptions)["years"][0]
    assumptions["opening_remaining_life_years"]["ppe_plant_and_wear_parts"] = 6
    changed = build_forecast(case, assumptions)["years"][0]
    avoided_da = 1641.66 / 3 - 1641.66 / 6
    assert changed["income"]["ebit"] - normal["income"]["ebit"] == pytest.approx(
        avoided_da
    )
    assert changed["income"]["tax"] - normal["income"]["tax"] == pytest.approx(
        avoided_da * 0.25
    )
    assert changed["income"]["net_income"] > normal["income"]["net_income"]


def test_debt_rate_changes_interest_but_not_enterprise_fcff(case, assumptions):
    normal = build_forecast(case, assumptions)
    assumptions["term_interest_rate"] += 0.02
    changed = build_forecast(case, assumptions)
    assert changed["years"][0]["income"]["finance_cost"] - normal["years"][0]["income"][
        "finance_cost"
    ] == pytest.approx(1190.62 * 0.02)
    assert [y["fcff"] for y in changed["years"]] == pytest.approx(
        [y["fcff"] for y in normal["years"]]
    )
    assert changed["dcf"]["enterprise_value"] == pytest.approx(
        normal["dcf"]["enterprise_value"]
    )


def test_funding_draw_and_limit_failure(case, assumptions):
    assumptions["minimum_cash"] = 3000
    funded = build_forecast(case, assumptions)["years"][0]
    assert funded["cash_flow"]["revolver_draw"] > 0
    assert funded["cash_flow"]["closing_cash"] == pytest.approx(3000)
    assumptions["minimum_cash"] = 100000
    with pytest.raises(FundingError, match="facility limit exceeded"):
        build_forecast(case, assumptions)


@pytest.mark.parametrize("section,field", [("assets", "cash"), ("income", "revenue")])
def test_material_source_error_is_rejected(case, section, field):
    case["annuals"][-1][section][field] += 1
    with pytest.raises(ModelInputError, match="historical reconciliation failed"):
        reconcile_history(case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tax_rate", True),
        ("tax_rate", 1.1),
        ("minimum_cash", -1),
        ("new_ppe_life_years", 0),
        ("revenue_growth", [0.1]),
        ("sweep_excess_cash_to_revolver", "false"),
    ],
)
def test_bad_assumptions_are_rejected(case, assumptions, field, value):
    assumptions[field] = value
    with pytest.raises(ModelInputError):
        build_forecast(case, assumptions)


def test_unknown_key_and_overpayment_are_rejected(case, assumptions):
    assumptions["cash_capex_percent"] = 0.1
    with pytest.raises(ModelInputError, match="unknown"):
        build_forecast(case, assumptions)
    del assumptions["cash_capex_percent"]
    assumptions["term_principal_repayment"][0] = 10000
    with pytest.raises(ModelInputError, match="repayment exceeds"):
        build_forecast(case, assumptions)


def test_discount_terminal_and_bridge_math(case, assumptions):
    r = build_forecast(case, assumptions)
    d = r["dcf"]
    pv_flows = sum(y["fcff"] / 1.12**i for i, y in enumerate(r["years"], 1))
    terminal_nopat = r["years"][-1]["income"]["ebit"] * 1.04 * 0.75
    pv_terminal = terminal_nopat * (1 - 0.04 / 0.15) / 0.08 / 1.12**5
    assert d["enterprise_value"] == pytest.approx(pv_flows + pv_terminal)
    # Independently sum cash/investments/JV/property minus debt/leases/accrued interest.
    assert d["equity_value"] - d["enterprise_value"] == pytest.approx(495.36)
    assert d["value_per_share_inr"] == pytest.approx(d["equity_value"] / 66.535492)
    assumptions["dcf"]["wacc"] = 0.04
    with pytest.raises(ModelInputError, match="must exceed growth"):
        build_forecast(case, assumptions)


def test_loss_has_no_automatic_tax_refund_or_terminal_value(case, assumptions):
    assumptions["ebitda_margin"] = [-0.1] * 5
    assumptions["revolver_limit"] = 100000
    result = build_forecast(case, assumptions)
    assert all(y["income"]["tax"] == 0 for y in result["years"])
    assert not result["dcf"]["available"]


@pytest.mark.parametrize(
    "content", ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}']
)
def test_invalid_json_is_rejected(tmp_path, content):
    path = tmp_path / "invalid.json"
    path.write_text(content)
    with pytest.raises(ModelInputError):
        load_json(path)
