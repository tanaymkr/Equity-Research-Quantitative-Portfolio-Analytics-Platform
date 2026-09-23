from dataclasses import replace

import pytest

from equity_analytics.valuation.dcf import (
    DCFAssumptions,
    HistoricalSnapshot,
    calculate_dcf,
)
from equity_analytics.valuation.sensitivity import sensitivity_matrix


@pytest.fixture
def snapshot() -> HistoricalSnapshot:
    return HistoricalSnapshot(
        company_name="Test Company",
        base_year=2026,
        revenue=1_000.0,
        cash=100.0,
        debt=250.0,
        shares_outstanding=50.0,
    )


@pytest.fixture
def assumptions() -> DCFAssumptions:
    return DCFAssumptions.from_sequences(
        revenue_growth=[0.10, 0.08, 0.06],
        ebit_margin=[0.15, 0.16, 0.17],
        tax_rate=0.25,
        depreciation_pct_revenue=0.03,
        capex_pct_revenue=0.04,
        nwc_pct_revenue=0.10,
        wacc=0.10,
        terminal_growth=0.04,
    )


def test_value_bridge_is_internally_consistent(snapshot, assumptions) -> None:
    result = calculate_dcf(snapshot, assumptions)
    pv_forecast = sum(year.present_value_fcff for year in result.forecast)

    assert result.enterprise_value == pytest.approx(
        pv_forecast + result.present_value_terminal
    )
    assert result.equity_value == pytest.approx(
        result.enterprise_value + snapshot.cash - snapshot.debt
    )
    assert result.implied_value_per_share == pytest.approx(
        result.equity_value / snapshot.shares_outstanding
    )


def test_fcff_components_reconcile(snapshot, assumptions) -> None:
    result = calculate_dcf(snapshot, assumptions)
    first_year = result.forecast[0]

    assert first_year.fcff == pytest.approx(
        first_year.nopat
        + first_year.depreciation
        - first_year.capex
        - first_year.change_in_nwc
    )


def test_higher_wacc_reduces_implied_value(snapshot, assumptions) -> None:
    base = calculate_dcf(snapshot, assumptions)
    higher_wacc = calculate_dcf(snapshot, replace(assumptions, wacc=0.12))

    assert higher_wacc.implied_value_per_share < base.implied_value_per_share


def test_terminal_growth_must_be_lower_than_wacc() -> None:
    with pytest.raises(ValueError, match="terminal_growth must be lower than wacc"):
        DCFAssumptions.from_sequences(
            revenue_growth=[0.08],
            ebit_margin=[0.15],
            tax_rate=0.25,
            depreciation_pct_revenue=0.03,
            capex_pct_revenue=0.04,
            nwc_pct_revenue=0.10,
            wacc=0.09,
            terminal_growth=0.09,
        )


def test_forecast_sequences_must_have_equal_lengths() -> None:
    with pytest.raises(ValueError, match="must have equal lengths"):
        DCFAssumptions.from_sequences(
            revenue_growth=[0.08, 0.06],
            ebit_margin=[0.15],
            tax_rate=0.25,
            depreciation_pct_revenue=0.03,
            capex_pct_revenue=0.04,
            nwc_pct_revenue=0.10,
            wacc=0.09,
            terminal_growth=0.04,
        )


def test_sensitivity_matrix_has_requested_dimensions(snapshot, assumptions) -> None:
    matrix = sensitivity_matrix(
        snapshot,
        assumptions,
        wacc_values=[0.09, 0.10, 0.11],
        terminal_growth_values=[0.03, 0.04],
    )

    assert len(matrix) == 2
    assert all(len(row) == 3 for row in matrix.values())
    assert all(value is not None for row in matrix.values() for value in row.values())
