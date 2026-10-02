"""Discount externally modelled FCFF, with a separate WACC for each period."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from .dcf import HistoricalSnapshot, _finite, _validate_rate


@dataclass(frozen=True)
class ExplicitCashFlow:
    year: int
    fcff: float
    nopat: float
    wacc: float


def discount_cash_flows(
    snapshot: HistoricalSnapshot,
    cash_flows: Sequence[ExplicitCashFlow],
    *,
    terminal_growth: float,
    terminal_roic: float,
    terminal_wacc: float | None = None,
) -> dict:
    """Year-end DCF; terminal reinvestment = growth / ROIC, not last-year WC.

    Each rate discounts that year's interval. No revenue, margin or FCFF is
    regenerated here; the calling financial-statement model owns those values.
    """
    if not cash_flows:
        raise ValueError("At least one explicit cash flow is required")
    for key, value in (
        ("terminal_growth", terminal_growth),
        ("terminal_roic", terminal_roic),
    ):
        _finite(key, value)
    if not 0 <= terminal_growth < terminal_roic:
        raise ValueError("Require 0 <= terminal growth < positive terminal ROIC")
    terminal_wacc = cash_flows[-1].wacc if terminal_wacc is None else terminal_wacc
    _validate_rate("terminal_wacc", terminal_wacc)
    if terminal_wacc <= terminal_growth:
        raise ValueError("Terminal WACC must exceed terminal growth")
    factor, discounted = 1.0, []
    for period, row in enumerate(cash_flows, 1):
        if row.year != snapshot.base_year + period:
            raise ValueError(
                "Explicit cash-flow years must follow the anchor consecutively"
            )
        _finite("fcff", row.fcff)
        _finite("nopat", row.nopat)
        _validate_rate("wacc", row.wacc)
        factor /= 1 + row.wacc
        discounted.append(
            {
                **asdict(row),
                "discount_factor": factor,
                "present_value": row.fcff * factor,
            }
        )
    terminal_nopat = cash_flows[-1].nopat * (1 + terminal_growth)
    if terminal_nopat <= 0:
        raise ValueError("A positive sustainable terminal NOPAT is required")
    terminal_fcff = terminal_nopat * (1 - terminal_growth / terminal_roic)
    terminal_value = terminal_fcff / (terminal_wacc - terminal_growth)
    pv_terminal = terminal_value * factor
    enterprise = sum(row["present_value"] for row in discounted) + pv_terminal
    equity = (
        enterprise
        + snapshot.cash
        + snapshot.nonoperating_assets
        - snapshot.debt
        - snapshot.minority_interest
        - snapshot.other_claims
    )
    _finite("equity_value", equity)
    return {
        "forecast": discounted,
        "terminal_growth": terminal_growth,
        "terminal_roic": terminal_roic,
        "terminal_wacc": terminal_wacc,
        "terminal_fcff": terminal_fcff,
        "terminal_value": terminal_value,
        "present_value_terminal": pv_terminal,
        "enterprise_value": enterprise,
        "cash": snapshot.cash,
        "nonoperating_assets": snapshot.nonoperating_assets,
        "debt": snapshot.debt,
        "minority_interest": snapshot.minority_interest,
        "other_claims": snapshot.other_claims,
        "equity_value": equity,
        "shares_million": snapshot.shares_outstanding,
        "implied_value_per_share": equity / snapshot.shares_outstanding,
        "terminal_method": "roic_reinvestment",
    }
