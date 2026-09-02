"""Free-cash-flow-to-the-firm discounted cash flow valuation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any


def _validate_rate(name: str, value: float, *, upper: float = 1.0) -> None:
    if not 0.0 <= value < upper:
        raise ValueError(f"{name} must be between 0 and {upper}, got {value}")


@dataclass(frozen=True)
class HistoricalSnapshot:
    """Latest reported values used to anchor the forecast.

    Monetary values must use one consistent financial unit. Shares outstanding
    should use the matching scale so that equity value divided by shares yields
    the desired per-share currency value.
    """

    company_name: str
    base_year: int
    revenue: float
    cash: float
    debt: float
    shares_outstanding: float
    currency: str = "INR"
    financial_unit: str = "crore"

    def __post_init__(self) -> None:
        if not self.company_name.strip():
            raise ValueError("company_name cannot be empty")
        if self.revenue <= 0:
            raise ValueError("revenue must be positive")
        if self.cash < 0 or self.debt < 0:
            raise ValueError("cash and debt cannot be negative")
        if self.shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")


@dataclass(frozen=True)
class DCFAssumptions:
    """Forecast and discount-rate assumptions for an FCFF DCF."""

    revenue_growth: tuple[float, ...]
    ebit_margin: tuple[float, ...]
    tax_rate: float
    depreciation_pct_revenue: float
    capex_pct_revenue: float
    nwc_pct_revenue: float
    wacc: float
    terminal_growth: float

    @classmethod
    def from_sequences(
        cls,
        *,
        revenue_growth: Sequence[float],
        ebit_margin: Sequence[float],
        tax_rate: float,
        depreciation_pct_revenue: float,
        capex_pct_revenue: float,
        nwc_pct_revenue: float,
        wacc: float,
        terminal_growth: float,
    ) -> DCFAssumptions:
        return cls(
            revenue_growth=tuple(revenue_growth),
            ebit_margin=tuple(ebit_margin),
            tax_rate=tax_rate,
            depreciation_pct_revenue=depreciation_pct_revenue,
            capex_pct_revenue=capex_pct_revenue,
            nwc_pct_revenue=nwc_pct_revenue,
            wacc=wacc,
            terminal_growth=terminal_growth,
        )

    def __post_init__(self) -> None:
        if not self.revenue_growth:
            raise ValueError("at least one forecast year is required")
        if len(self.revenue_growth) != len(self.ebit_margin):
            raise ValueError("revenue_growth and ebit_margin must have equal lengths")
        for growth in self.revenue_growth:
            if growth <= -1.0:
                raise ValueError("revenue growth cannot be less than or equal to -100%")
        for margin in self.ebit_margin:
            _validate_rate("ebit_margin", margin)
        _validate_rate("tax_rate", self.tax_rate)
        _validate_rate("depreciation_pct_revenue", self.depreciation_pct_revenue)
        _validate_rate("capex_pct_revenue", self.capex_pct_revenue)
        _validate_rate("nwc_pct_revenue", self.nwc_pct_revenue)
        _validate_rate("wacc", self.wacc)
        if self.terminal_growth <= -1.0:
            raise ValueError("terminal_growth cannot be less than or equal to -100%")
        if self.terminal_growth >= self.wacc:
            raise ValueError("terminal_growth must be lower than wacc")


@dataclass(frozen=True)
class ForecastYear:
    year: int
    revenue_growth: float
    revenue: float
    ebit_margin: float
    ebit: float
    nopat: float
    depreciation: float
    capex: float
    net_working_capital: float
    change_in_nwc: float
    fcff: float
    discount_factor: float
    present_value_fcff: float


@dataclass(frozen=True)
class DCFResult:
    company_name: str
    currency: str
    financial_unit: str
    forecast: tuple[ForecastYear, ...]
    terminal_value: float
    present_value_terminal: float
    enterprise_value: float
    cash: float
    debt: float
    equity_value: float
    shares_outstanding: float
    implied_value_per_share: float
    wacc: float
    terminal_growth: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_dcf(
    snapshot: HistoricalSnapshot,
    assumptions: DCFAssumptions,
) -> DCFResult:
    """Calculate an FCFF DCF using an end-of-year discounting convention."""

    forecast: list[ForecastYear] = []
    prior_revenue = snapshot.revenue
    prior_nwc = snapshot.revenue * assumptions.nwc_pct_revenue

    for period, (growth, margin) in enumerate(
        zip(assumptions.revenue_growth, assumptions.ebit_margin, strict=True),
        start=1,
    ):
        revenue = prior_revenue * (1.0 + growth)
        ebit = revenue * margin
        nopat = ebit * (1.0 - assumptions.tax_rate)
        depreciation = revenue * assumptions.depreciation_pct_revenue
        capex = revenue * assumptions.capex_pct_revenue
        net_working_capital = revenue * assumptions.nwc_pct_revenue
        change_in_nwc = net_working_capital - prior_nwc
        fcff = nopat + depreciation - capex - change_in_nwc
        discount_factor = 1.0 / (1.0 + assumptions.wacc) ** period

        forecast.append(
            ForecastYear(
                year=snapshot.base_year + period,
                revenue_growth=growth,
                revenue=revenue,
                ebit_margin=margin,
                ebit=ebit,
                nopat=nopat,
                depreciation=depreciation,
                capex=capex,
                net_working_capital=net_working_capital,
                change_in_nwc=change_in_nwc,
                fcff=fcff,
                discount_factor=discount_factor,
                present_value_fcff=fcff * discount_factor,
            )
        )
        prior_revenue = revenue
        prior_nwc = net_working_capital

    final_fcff = forecast[-1].fcff
    terminal_value = (
        final_fcff
        * (1.0 + assumptions.terminal_growth)
        / (assumptions.wacc - assumptions.terminal_growth)
    )
    present_value_terminal = terminal_value * forecast[-1].discount_factor
    enterprise_value = (
        sum(year.present_value_fcff for year in forecast) + present_value_terminal
    )
    equity_value = enterprise_value + snapshot.cash - snapshot.debt
    implied_value_per_share = equity_value / snapshot.shares_outstanding

    return DCFResult(
        company_name=snapshot.company_name,
        currency=snapshot.currency,
        financial_unit=snapshot.financial_unit,
        forecast=tuple(forecast),
        terminal_value=terminal_value,
        present_value_terminal=present_value_terminal,
        enterprise_value=enterprise_value,
        cash=snapshot.cash,
        debt=snapshot.debt,
        equity_value=equity_value,
        shares_outstanding=snapshot.shares_outstanding,
        implied_value_per_share=implied_value_per_share,
        wacc=assumptions.wacc,
        terminal_growth=assumptions.terminal_growth,
    )
