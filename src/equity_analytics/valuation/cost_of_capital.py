"""One cost-of-capital method shared by every valuation in the platform.

Unlevered cost of capital = (government bond yield - sovereign default spread)
                            + industry unlevered beta x equity risk premium
WACC = unlevered cost of capital - debt / value x tax rate x pre-tax cost of debt

This is the constant-leverage (Harris-Pringle) WACC used in Berk-DeMarzo and
McKinsey's Valuation. Financing changes value only through the interest tax
shield, so the WACC can never exceed the return the operating assets require.
Preference capital has no tax shield and therefore leaves the WACC unchanged;
its claim is deducted in the equity bridge instead.

The alternative, relevering a beta as if debt were riskless while charging the
debt's promised yield, counts the risk of borrowing twice. For a business
funded mostly by high-yield debt and preference shares it can push the WACC
above the unlevered cost, which is impossible.

Regression betas of individual stocks may be reported beside the industry beta
as a cross-check, but they do not enter the valuation.
"""

from collections.abc import Callable
from math import isfinite


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if not isfinite(value):
        raise ValueError(f"{name} must be a finite number")


def default_free_rate(government_bond_yield, sovereign_default_spread):
    """Local-currency risk-free rate: the bond yield less its default spread."""
    _number("government_bond_yield", government_bond_yield)
    _number("sovereign_default_spread", sovereign_default_spread)
    if not 0 <= sovereign_default_spread <= government_bond_yield < 1:
        raise ValueError("Require 0 <= default spread <= government bond yield < 100%")
    return government_bond_yield - sovereign_default_spread


def unlevered_cost_of_capital(risk_free_rate, unlevered_beta, equity_risk_premium):
    """Return required on the operating assets alone (CAPM with an asset beta)."""
    for name, value in (
        ("risk_free_rate", risk_free_rate),
        ("unlevered_beta", unlevered_beta),
        ("equity_risk_premium", equity_risk_premium),
    ):
        _number(name, value)
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
    if unlevered_beta == 0:
        raise ValueError("unlevered_beta must be positive")
    return risk_free_rate + unlevered_beta * equity_risk_premium


def wacc_with_tax_shield(unlevered_cost, debt_weight, tax_rate, cost_of_debt):
    """Constant-leverage WACC: the unlevered cost less the interest tax shield."""
    for name, value in (
        ("unlevered_cost", unlevered_cost),
        ("debt_weight", debt_weight),
        ("tax_rate", tax_rate),
        ("cost_of_debt", cost_of_debt),
    ):
        _number(name, value)
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
    if debt_weight >= 1 or tax_rate >= 1:
        raise ValueError("Debt weight and tax rate must be below 100%")
    tax_shield = debt_weight * tax_rate * cost_of_debt
    wacc = unlevered_cost - tax_shield
    if not 0 < wacc < 1:
        raise ValueError("WACC must be between zero and one")
    return {
        "unlevered_cost_of_capital": unlevered_cost,
        "tax_shield": tax_shield,
        "wacc": wacc,
    }


def implied_discount_rate(
    value_at: Callable[[float], float],
    target: float,
    *,
    low: float = 0.03,
    high: float = 0.30,
    tolerance: float = 1e-7,
) -> float | None:
    """Discount rate at which ``value_at(rate)`` equals ``target``.

    ``value_at`` must fall as the rate rises. Returns None when the target lies
    outside the values at ``low`` and ``high``, rather than extrapolating.
    """
    _number("target", target)
    if not 0 < low < high < 1:
        raise ValueError("Require 0 < low < high < 1")
    value_low, value_high = value_at(low), value_at(high)
    if not value_low >= target >= value_high:
        return None
    while high - low > tolerance:
        middle = (low + high) / 2
        if value_at(middle) > target:
            low = middle
        else:
            high = middle
    return (low + high) / 2
