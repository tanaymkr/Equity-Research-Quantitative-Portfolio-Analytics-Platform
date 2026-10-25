"""Standalone CAPM/financing costs and an auditable operating-EV blend.

All numeric choices live in assumptions.pro_forma, with adjacent source notes.
Constant FX is an explicit expected-rate assumption, not an implicit USD/INR hedge.
"""

from math import isfinite

from equity_analytics.valuation.cost_of_capital import (
    cost_of_equity,
    default_free_rate,
    relever_beta,
)

REQUIRED = (
    "government_bond_yield",
    "sovereign_default_spread",
    "equity_risk_premium",
    "unlevered_beta",
    "cost_of_debt",
    "tax_rate",
    "debt_weight",
    "preference_weight",
    "cost_of_preference",
)


def standalone_wacc(inputs, equity_premium_stress=0.0):
    """Platform cost-of-capital method: industry beta relevered at the weights."""
    for key in REQUIRED:
        if (
            isinstance(inputs[key], bool)
            or not isinstance(inputs[key], (int, float))
            or not isfinite(inputs[key])
        ):
            raise ValueError(f"WACC {key} must be finite")
    debt, pref = inputs["debt_weight"], inputs["preference_weight"]
    equity = 1 - debt - pref
    if min(debt, pref) < 0 or equity <= 0 or not 0 <= inputs["tax_rate"] < 1:
        raise ValueError(
            "Capital weights must be nonnegative with positive equity; tax in [0,1)"
        )
    if min(inputs["cost_of_debt"], inputs["cost_of_preference"]) < 0:
        raise ValueError("Financing costs cannot be negative")
    premium = inputs["equity_risk_premium"] + equity_premium_stress
    if premium < 0:
        raise ValueError("Equity risk premium cannot be negative")
    rf = default_free_rate(
        inputs["government_bond_yield"], inputs["sovereign_default_spread"]
    )
    beta = relever_beta(
        inputs["unlevered_beta"], debt / equity, inputs["tax_rate"], pref / equity
    )
    ke = cost_of_equity(rf, beta, premium)
    after_tax_debt = inputs["cost_of_debt"] * (1 - inputs["tax_rate"])
    rate = equity * ke + debt * after_tax_debt + pref * inputs["cost_of_preference"]
    if not 0 < rate < 1:
        raise ValueError("WACC must be between zero and one")
    return {
        "currency": inputs["currency"],
        "government_bond_yield": inputs["government_bond_yield"],
        "sovereign_default_spread": inputs["sovereign_default_spread"],
        "risk_free_rate": rf,
        "equity_risk_premium": premium,
        "unlevered_beta": inputs["unlevered_beta"],
        "beta": beta,
        "cost_of_equity": ke,
        "cost_of_debt": inputs["cost_of_debt"],
        "after_tax_cost_of_debt": after_tax_debt,
        "cost_of_preference": inputs["cost_of_preference"],
        "common_equity_weight": equity,
        "debt_weight": debt,
        "preference_weight": pref,
        "standalone_wacc": rate,
        "inputs": dict(inputs),
    }


def standalone_rates(config, scenario):
    """Each business's own WACC; the scenario stress is zero in stored inputs."""
    w = config["wacc"]
    stress = w["scenario_risk_premium"][scenario]
    tega = standalone_wacc(w["tega"], stress)
    mc = standalone_wacc(w["molycop"], stress)
    if tega["currency"] != "INR" or mc["currency"] != "USD":
        raise ValueError("Expected INR Tega and USD Molycop WACC inputs")
    return tega, mc


def blended_wacc(config, scenario, tega_ev_inr_m, molycop_ev_inr_m):
    """Blend at each business's own DCF value, so the weights match the cash flows.

    The weights are the standalone enterprise values of the forecast cash flows,
    each discounted at its own WACC. Neither depends on the blend, so there is
    no circularity, and the single group rate approximately reproduces the sum
    of the two standalone valuations. Ownership fractions are never used.

    The current model assumes constant expected INR/USD throughout the forecast
    AND terminal period. Under that assumption the USD rate is numerically
    unchanged on conversion. If forecasting FX drift, both cash flows and rates
    must change together; editing the spot translation rate is not FX drift.
    """
    tega, mc = standalone_rates(config, scenario)
    tev, mev = tega_ev_inr_m, molycop_ev_inr_m
    if min(tev, mev) <= 0 or not all(isfinite(x) for x in (tev, mev)):
        raise ValueError(
            "Standalone operating values must be positive to weight the WACC blend"
        )
    weight = tev / (tev + mev)
    return {
        "tega": tega,
        "molycop": mc,
        "tega_weight_ev_inr_m": tev,
        "molycop_weight_ev_inr_m": mev,
        "tega_ev_weight": weight,
        "molycop_ev_weight": 1 - weight,
        "molycop_wacc_inr_constant_fx": mc["standalone_wacc"],
        "blended_wacc": weight * tega["standalone_wacc"]
        + (1 - weight) * mc["standalone_wacc"],
        "currency_convention": config["_fx_note"],
        "weight_basis": (
            "Each business's standalone DCF enterprise value from this model's own "
            "forecast, discounted at its own WACC; market or deal values are not used "
            "as weights because they price different cash flows."
        ),
    }
