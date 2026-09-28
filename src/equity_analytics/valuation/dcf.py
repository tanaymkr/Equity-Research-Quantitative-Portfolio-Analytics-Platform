"""Free-cash-flow-to-the-firm discounted cash flow valuation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


def _finite(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number")


def _validate_rate(name: str, value: float, *, upper: float = 1.0) -> None:
    _finite(name, value)
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

    opening_nwc: float | None = None
    nonoperating_assets: float = 0.0
    minority_interest: float = 0.0
    other_claims: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "revenue",
            "cash",
            "debt",
            "shares_outstanding",
            "nonoperating_assets",
            "minority_interest",
            "other_claims",
        ):
            _finite(name, getattr(self, name))
        if any(
            getattr(self, n) < 0
            for n in ("nonoperating_assets", "minority_interest", "other_claims")
        ):
            raise ValueError("Equity bridge adjustments must be nonnegative")
        if self.opening_nwc is not None:
            _finite("opening_nwc", self.opening_nwc)
        if not isinstance(self.base_year, int) or isinstance(self.base_year, bool):
            raise TypeError("base_year must be an integer")
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
    terminal_roic: float | None = None

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
        terminal_roic: float | None = None,
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
            terminal_roic=terminal_roic,
        )

    def __post_init__(self) -> None:
        if not self.revenue_growth:
            raise ValueError("at least one forecast year is required")
        if len(self.revenue_growth) != len(self.ebit_margin):
            raise ValueError("revenue_growth and ebit_margin must have equal lengths")
        _finite("terminal_growth", self.terminal_growth)
        for growth in self.revenue_growth:
            _finite("revenue_growth", growth)
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
        if self.terminal_roic is not None:
            _finite("terminal_roic", self.terminal_roic)
            if (
                self.terminal_roic <= 0
                or not 0 <= self.terminal_growth < self.terminal_roic
            ):
                raise ValueError("ROIC terminal requires 0 <= growth < positive ROIC")
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

    nonoperating_assets: float = 0.0
    minority_interest: float = 0.0
    other_claims: float = 0.0
    terminal_fcff: float = 0.0
    terminal_method: str = "legacy_fcff_growth"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_dcf(
    snapshot: HistoricalSnapshot,
    assumptions: DCFAssumptions,
) -> DCFResult:
    """Calculate an FCFF DCF using an end-of-year discounting convention."""

    forecast: list[ForecastYear] = []
    prior_revenue = snapshot.revenue
    prior_nwc = (
        snapshot.opening_nwc
        if snapshot.opening_nwc is not None
        else snapshot.revenue * assumptions.nwc_pct_revenue
    )

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
    terminal_fcff = final_fcff * (1.0 + assumptions.terminal_growth)
    if assumptions.terminal_roic is not None:
        terminal_fcff = (
            forecast[-1].nopat
            * (1 + assumptions.terminal_growth)
            * (1 - assumptions.terminal_growth / assumptions.terminal_roic)
        )
    terminal_value = terminal_fcff / (assumptions.wacc - assumptions.terminal_growth)
    present_value_terminal = terminal_value * forecast[-1].discount_factor
    enterprise_value = (
        sum(year.present_value_fcff for year in forecast) + present_value_terminal
    )
    equity_value = (
        enterprise_value
        + snapshot.cash
        + snapshot.nonoperating_assets
        - snapshot.debt
        - snapshot.minority_interest
        - snapshot.other_claims
    )
    implied_value_per_share = equity_value / snapshot.shares_outstanding

    for name, value in (
        ("enterprise_value", enterprise_value),
        ("equity_value", equity_value),
        ("implied_value_per_share", implied_value_per_share),
    ):
        _finite(name, value)
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
        nonoperating_assets=snapshot.nonoperating_assets,
        minority_interest=snapshot.minority_interest,
        other_claims=snapshot.other_claims,
        terminal_fcff=terminal_fcff,
        terminal_method="roic_reinvestment"
        if assumptions.terminal_roic is not None
        else "legacy_fcff_growth",
    )
