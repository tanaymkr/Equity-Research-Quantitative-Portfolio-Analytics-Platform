"""Annual financial ratios with explicit denominator and period conventions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

from equity_analytics.financials.models import AnnualStatement, FinancialHistory


@dataclass(frozen=True)
class Metric:
    value: float | None
    unit: str
    reason: str | None = None


@dataclass(frozen=True)
class YearAnalysis:
    fiscal_year: int
    metrics: dict[str, Metric]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisReport:
    history: FinancialHistory
    years: tuple[YearAnalysis, ...]
    revenue_cagr: Metric
    cagr_intervals: int

    def to_dict(self) -> dict[str, Any]:
        # Include all original inputs and source references for reproducibility.
        return asdict(self)


def _metric(value: float | None, unit: str, reason: str = "missing input") -> Metric:
    if value is None:
        return Metric(None, unit, reason)
    if not isfinite(value):
        return Metric(None, unit, "calculation exceeds finite numeric range")
    return Metric(value, unit)


def _ratio(
    numerator: float | None, denominator: float | None, unit: str = "fraction"
) -> Metric:
    if numerator is None or denominator is None:
        return Metric(None, unit, "missing numerator or denominator")
    if denominator <= 0:
        return Metric(None, unit, "denominator must be positive")
    return _metric(numerator / denominator, unit)


def _sum(a: float | None, b: float | None) -> float | None:
    value = None if a is None or b is None else a + b
    return value if value is not None and isfinite(value) else None


def _difference(a: float | None, b: float | None) -> float | None:
    value = None if a is None or b is None else a - b
    return value if value is not None and isfinite(value) else None


def _average(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return a / 2 + b / 2


def _yoy(current: float | None, prior: float | None, consecutive: bool) -> Metric:
    if not consecutive:
        return Metric(None, "fraction", "no immediately preceding annual period")
    result = _ratio(current, prior)
    return result if result.value is None else _metric(result.value - 1, "fraction")


def _average_return(
    numerator: float | None,
    current: float | None,
    prior: float | None,
    consecutive: bool,
) -> Metric:
    if not consecutive:
        return Metric(
            None, "fraction", "requires immediately preceding year-end balance"
        )
    if current is None or prior is None:
        return Metric(None, "fraction", "missing opening or closing balance")
    if current <= 0 or prior <= 0:
        return Metric(None, "fraction", "opening and closing balances must be positive")
    return _ratio(numerator, _average(current, prior))


def _quality_warnings(annual: AnnualStatement) -> tuple[str, ...]:
    warnings = []
    assets, liabilities, equity = (
        annual.total_assets,
        annual.total_liabilities,
        annual.total_equity,
    )
    # Accommodate rounding of source figures while flagging material mismatch.
    if (
        assets is not None
        and liabilities is not None
        and equity is not None
        and abs(assets - liabilities - equity) > max(0.1, abs(assets) * 0.0001)
    ):
        warnings.append("assets do not reconcile to liabilities plus total equity")
    for name, subset, total in (
        ("current assets", annual.current_assets, assets),
        ("current liabilities", annual.current_liabilities, liabilities),
        ("cash and equivalents", annual.cash_and_equivalents, annual.current_assets),
        ("total debt", annual.total_debt, liabilities),
    ):
        if subset is not None and total is not None and subset > total:
            warnings.append(f"{name} exceeds its containing balance-sheet total")
    return tuple(warnings)


def analyze_history(history: FinancialHistory) -> AnalysisReport:
    """Calculate available metrics; never replace absent source values with zero.

    EBIT is operating EBIT, excluding other income. EBITDA is EBIT plus D&A.
    ROE uses owners' profit / average owners' equity. ROA uses total net income /
    average total assets. ROCE uses EBIT / average (assets-current liabilities).
    CFO less capex is a historical cash measure, not automatically FCFF.
    """
    years = []
    previous = None
    money = f"{history.company.currency} {history.company.financial_unit}"
    for annual in history.annuals:
        consecutive = (
            previous is not None and annual.fiscal_year == previous.fiscal_year + 1
        )
        ebitda = _sum(annual.ebit, annual.depreciation_amortisation)
        net_debt = _difference(annual.total_debt, annual.cash_and_equivalents)
        cash_after_capex = _difference(annual.operating_cash_flow, annual.capex)
        capital_employed = _difference(annual.total_assets, annual.current_liabilities)
        prior_capital = (
            _difference(previous.total_assets, previous.current_liabilities)
            if previous
            else None
        )
        metrics = {
            "revenue": _metric(annual.revenue, money),
            "revenue_growth": _yoy(
                annual.revenue, previous.revenue if previous else None, consecutive
            ),
            "net_income_growth": _yoy(
                annual.net_income,
                previous.net_income if previous else None,
                consecutive,
            ),
            "ebitda": _metric(ebitda, money),
            "ebit_margin": _ratio(annual.ebit, annual.revenue),
            "ebitda_margin": _ratio(ebitda, annual.revenue),
            "net_margin": _ratio(annual.net_income, annual.revenue),
            "roe": _average_return(
                annual.net_income_to_owners,
                annual.equity_to_owners,
                previous.equity_to_owners if previous else None,
                consecutive,
            ),
            "roa": _average_return(
                annual.net_income,
                annual.total_assets,
                previous.total_assets if previous else None,
                consecutive,
            ),
            "roce": _average_return(
                annual.ebit, capital_employed, prior_capital, consecutive
            ),
            "current_ratio": _ratio(
                annual.current_assets, annual.current_liabilities, "multiple"
            ),
            "debt_to_equity": _ratio(
                annual.total_debt, annual.total_equity, "multiple"
            ),
            "net_debt": _metric(net_debt, money),
            "net_debt_to_ebitda": _ratio(net_debt, ebitda, "multiple"),
            "finance_cost_coverage": _ratio(
                annual.ebit, annual.finance_costs, "multiple"
            ),
            "operating_cash_flow_margin": _ratio(
                annual.operating_cash_flow, annual.revenue
            ),
            "operating_cash_flow_to_net_income": _ratio(
                annual.operating_cash_flow, annual.net_income, "multiple"
            ),
            "capex_to_revenue": _ratio(annual.capex, annual.revenue),
            "cash_flow_after_capex": _metric(cash_after_capex, money),
        }
        years.append(
            YearAnalysis(annual.fiscal_year, metrics, _quality_warnings(annual))
        )
        previous = annual
    first, last = history.annuals[0], history.annuals[-1]
    intervals = last.fiscal_year - first.fiscal_year
    if intervals <= 0 or first.revenue <= 0 or last.revenue <= 0:
        cagr = Metric(None, "fraction", "requires two dated positive revenue endpoints")
    else:
        cagr = _metric(
            (last.revenue / first.revenue) ** (1 / intervals) - 1, "fraction"
        )
    return AnalysisReport(history, tuple(years), cagr, intervals)
