"""One cost-of-capital method shared by every valuation in the platform.

Cost of equity = (government bond yield - sovereign default spread)
                 + relevered beta x equity risk premium.

The beta is an industry (bottom-up) unlevered beta, relevered at the capital
structure that weights the WACC:

    levered beta = unlevered beta x (1 + (1 - tax) x D/E + P/E)

where P is preference capital, whose return is not tax deductible. Regression
betas of individual stocks may be reported beside it as a cross-check, but they
do not enter the valuation.
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


def relever_beta(unlevered_beta, debt_to_equity, tax_rate, preference_to_equity=0.0):
    """Hamada relevering, with preference capital treated as non-deductible."""
    for name, value in (
        ("unlevered_beta", unlevered_beta),
        ("debt_to_equity", debt_to_equity),
        ("tax_rate", tax_rate),
        ("preference_to_equity", preference_to_equity),
    ):
        _number(name, value)
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
    if unlevered_beta == 0:
        raise ValueError("unlevered_beta must be positive")
    if tax_rate >= 1:
        raise ValueError("tax_rate must be below 100%")
    return unlevered_beta * (1 + (1 - tax_rate) * debt_to_equity + preference_to_equity)


def cost_of_equity(risk_free_rate, levered_beta, equity_risk_premium):
    for name, value in (
        ("risk_free_rate", risk_free_rate),
        ("levered_beta", levered_beta),
        ("equity_risk_premium", equity_risk_premium),
    ):
        _number(name, value)
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
    return risk_free_rate + levered_beta * equity_risk_premium


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
