"""Economic perturbations, accounting boundaries and source provenance."""

from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.case_studies.wabag import build_model, load_inputs
from equity_analytics.case_studies.wabag.model import verify_beta
from equity_analytics.case_studies.wabag.reporting import export_report
from equity_analytics.data import FinancialStore
from equity_analytics.valuation.dcf import HistoricalSnapshot
from equity_analytics.valuation.explicit import ExplicitCashFlow, discount_cash_flows

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    return load_inputs(ROOT / "examples/wabag_linked")


def driver(inputs, period, key, value, method="absolute"):
    item = inputs["assumptions"]["years"][period]["drivers"][key]
    item.update(
        value=value, source="analyst", reason="Test perturbation", method=method
    )


def test_complete_statements_balance_without_mutating_inputs(inputs):
    original = deepcopy(inputs)
    r = build_model(inputs)
    assert inputs == original
    assert len(r["checks"]) == 40
    assert all(c["passed"] for c in r["checks"] + r["historical_checks"])
    assert r["historical"][0]["balance_sheet"]["balance_residual"] == 1
    assert r["historical"][0]["income_statement"]["diluted_eps"] == 39.49
    for year in r["forecast"]:
        b, c, s = (year[k] for k in ("balance_sheet", "cash_flow", "income_statement"))
        assert b["assets"] == pytest.approx(b["liabilities"] + b["equity"])
        assert c["opening_cash"] + c["cfo"] + c["cfi"] + c["cff"] == pytest.approx(
            b["cash"]
        )
        assert s["net_income"] == pytest.approx(s["owners_profit"] + s["nci_profit"])
        assert year["valuation"]["fcff"] == pytest.approx(
            year["valuation"]["fcff_from_cfo"]
        )
        assert (
            s["owners_profit"]
            != inputs["forecast_references"]["consensus"]["net_profit"][0]
        )


def test_capex_spends_cash_creates_asset_and_reduces_value(inputs):
    base = build_model(inputs)
    driver(inputs, 0, "capex", base["forecast"][0]["resolved_drivers"]["capex"] + 100)
    changed = build_model(inputs)
    a, b = base["forecast"][0], changed["forecast"][0]
    assert b["balance_sheet"]["cash"] - a["balance_sheet"]["cash"] == pytest.approx(
        -100
    )
    assert sum(b["fixed_assets"]["closing"].values()) - sum(
        a["fixed_assets"]["closing"].values()
    ) == pytest.approx(100)
    assert b["valuation"]["fcff"] - a["valuation"]["fcff"] == pytest.approx(-100)
    assert changed["dcf"]["enterprise_value"] - base["dcf"][
        "enterprise_value"
    ] == pytest.approx(-100 * base["dcf"]["forecast"][0]["discount_factor"])


def test_dividend_payment_lag_reduces_cash_and_equity(inputs):
    base = build_model(inputs)
    driver(inputs, 0, "declared_dps", 7.075)  # +1 INR, paid in FY28
    changed = build_model(inputs)
    a, b = base["forecast"][1], changed["forecast"][1]
    assert b["balance_sheet"]["cash"] - a["balance_sheet"]["cash"] == pytest.approx(
        -62.309595
    )
    assert b["balance_sheet"]["equity"] - a["balance_sheet"]["equity"] == pytest.approx(
        -62.309595
    )
    assert changed["dcf"]["enterprise_value"] == pytest.approx(
        base["dcf"]["enterprise_value"]
    )


def test_debt_draw_changes_interest_tax_cash_and_market_weights(inputs):
    base = build_model(inputs)
    driver(inputs, 0, "bank_debt_target", 2155)  # +100 ending revolving debt
    changed = build_model(inputs)
    a, b = base["forecast"][0], changed["forecast"][0]
    extra_interest = 50 * b["debt"]["working_rate"]
    assert b["debt"]["interest_total"] - a["debt"]["interest_total"] == pytest.approx(
        extra_interest
    )
    assert b["balance_sheet"]["cash"] - a["balance_sheet"]["cash"] == pytest.approx(
        100 - extra_interest * (1 - 0.238 - 7 / 12097)
    )
    assert b["wacc"]["debt_weight"] > a["wacc"]["debt_weight"]
    assert b["valuation"]["fcff"] == pytest.approx(a["valuation"]["fcff"])


def test_banks_are_operating_costs_not_wacc_interest(inputs):
    base = build_model(inputs)
    bank = base["forecast"][0]["resolved_drivers"]["bank_charges"]
    driver(inputs, 0, "bank_charges", bank + 100)
    changed = build_model(inputs)
    a, b = base["forecast"][0], changed["forecast"][0]
    assert b["valuation"]["fcff"] - a["valuation"]["fcff"] == pytest.approx(
        -100 * (1 - 0.238)
    )
    assert b["wacc"] == a["wacc"]
    assert a["wacc"]["market_equity"] == pytest.approx(2008.4000244140625 * 62.309595)
    assert a["wacc"]["default_free_inr_rate"] == pytest.approx(0.071194 - 0.0187)
    assert a["wacc"]["cost_of_equity"] == pytest.approx(
        0.052494 + a["wacc"]["relevered_beta"] * 0.0423 + 0.0285
    )


def test_ecl_reclassification_does_not_create_cash(inputs):
    base = build_model(inputs)
    charge = base["forecast"][0]["resolved_drivers"]["ecl_charge"]
    driver(inputs, 0, "ecl_charge", charge + 100)
    changed = build_model(inputs)
    assert changed["forecast"][0]["credit_losses"]["closing_allowance"] - base[
        "forecast"
    ][0]["credit_losses"]["closing_allowance"] == pytest.approx(100)
    assert changed["forecast"][0]["cash_flow"]["cfo"] == pytest.approx(
        base["forecast"][0]["cash_flow"]["cfo"]
    )


def test_historical_ratios_and_tail_growth_respond_to_revenue(inputs):
    base = build_model(inputs)
    driver(inputs, 2, "revenue", 62000)
    changed = build_model(inputs)
    assert changed["forecast"][2]["income_statement"]["employees"] / base["forecast"][
        2
    ]["income_statement"]["employees"] == pytest.approx(62000 / 61132)
    assert changed["forecast"][3]["income_statement"]["revenue"] == pytest.approx(
        62000 * (39442 / 28564) ** 0.5
    )


def test_new_lease_is_noncash_financing_but_is_fcff_reinvestment(inputs):
    base = build_model(inputs)
    driver(inputs, 0, "new_leases", 100)
    changed = build_model(inputs)
    a, b = base["forecast"][0], changed["forecast"][0]
    assert b["balance_sheet"]["ppe"] - a["balance_sheet"]["ppe"] == pytest.approx(100)
    assert b["debt"]["total_close"] - a["debt"]["total_close"] == pytest.approx(100)
    assert b["valuation"]["fcff"] - a["valuation"]["fcff"] == pytest.approx(-100)
    assert b["cash_flow"]["capex"] == a["cash_flow"]["capex"]


def test_depreciation_caps_assets_and_never_depreciates_land(inputs):
    driver(inputs, 0, "da_target", 2000)
    result = build_model(inputs)
    a = result["forecast"][0]["fixed_assets"]
    assert a["closing"]["land"] == 170
    assert a["depreciation"]["land"] == 0
    assert all(x >= 0 for x in a["closing"].values())
    assert a["uncaptured_da_target"] > 0


def test_funding_shortfall_is_not_filled_with_an_unlimited_cash_plug(inputs):
    driver(inputs, 0, "capex", 100000)
    with pytest.raises(ValueError, match="funding shortfall"):
        build_model(inputs)


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), -5])
def test_missing_or_invalid_critical_data_never_becomes_zero(inputs, value):
    driver(inputs, 0, "revenue", value)
    with pytest.raises(ValueError):
        build_model(inputs)


def test_source_cutoff_and_beta_integrity(inputs):
    assert verify_beta(inputs["wacc_reference"]) == pytest.approx(1.4316874326603788)
    bad = deepcopy(inputs)
    bad["wacc_reference"]["beta_observations"][0]["stock_return"] += 1
    with pytest.raises(ValueError, match="Stored beta"):
        build_model(bad)
    inputs["assumptions"]["information_as_of"] = "2026-09-01"
    with pytest.raises(ValueError, match="later than"):
        build_model(inputs)


def test_sql_values_and_report_export(inputs, tmp_path):
    store = FinancialStore(tmp_path / "research.sqlite")
    for year in (2024, 2026):
        store.ingest_file(
            ROOT / f"examples/wabag_fy{year}_reported_statements.json",
            company_id="WABAG",
        )
    result = build_model(inputs, store=store)
    assert len(result["sql_crosschecks"]) == 12
    path = export_report(result, tmp_path / "reports")
    html = path.read_text(encoding="utf-8")
    assert "FY2031E" in html and "zero_unavailable" in html
    assert "Moneycontrol Pro annual forecast table was not verified" in html
    inputs["history"]["annuals"][-1]["income_statement"]["revenue"] += 100
    with pytest.raises(ValueError, match="SQL mismatch"):
        build_model(inputs, store=store)


def test_explicit_dcf_uses_sequential_rates_and_roic_terminal():
    snapshot = HistoricalSnapshot(
        "Test", 2026, 1000, 100, 200, 10, nonoperating_assets=30, minority_interest=20
    )
    result = discount_cash_flows(
        snapshot,
        [ExplicitCashFlow(2027, 50, 80, 0.1), ExplicitCashFlow(2028, 100, 120, 0.2)],
        terminal_growth=0.04,
        terminal_roic=0.16,
    )
    terminal = 120 * 1.04 * 0.75 / 0.16
    enterprise = 50 / 1.1 + (100 + terminal) / (1.1 * 1.2)
    assert result["enterprise_value"] == pytest.approx(enterprise)
    assert result["implied_value_per_share"] == pytest.approx(
        (enterprise + 100 + 30 - 200 - 20) / 10
    )
    assert result["forecast"][1]["fcff"] == 100


@pytest.mark.parametrize(
    "growth,roic,wacc", [(0.2, 0.3, 0.1), (0.1, 0.05, 0.2), (-0.01, 0.15, 0.1)]
)
def test_terminal_inputs_are_economically_bounded(growth, roic, wacc):
    s = HistoricalSnapshot("Test", 2026, 100, 0, 0, 1)
    with pytest.raises(ValueError):
        discount_cash_flows(
            s,
            [ExplicitCashFlow(2027, 10, 20, wacc)],
            terminal_growth=growth,
            terminal_roic=roic,
        )
