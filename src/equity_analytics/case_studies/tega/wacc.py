"""Standalone CAPM/financing costs and an auditable operating-EV blend.

All numeric choices live in assumptions.pro_forma, with adjacent source notes.
Constant FX is an explicit expected-rate assumption, not an implicit USD/INR hedge.
"""

from math import isfinite


def standalone_wacc(inputs, equity_premium_stress=0.0):
    for key in (
        "risk_free_rate",
        "equity_risk_premium",
        "beta",
        "cost_of_debt",
        "tax_rate",
        "debt_weight",
        "preference_weight",
        "cost_of_preference",
    ):
        if not isinstance(inputs[key], (int, float)) or not isfinite(inputs[key]):
            raise ValueError(f"WACC {key} must be finite")
    debt, pref = inputs["debt_weight"], inputs["preference_weight"]
    equity = 1 - debt - pref
    if min(debt, pref, equity) < 0 or not 0 <= inputs["tax_rate"] <= 1:
        raise ValueError(
            "Capital weights must be nonnegative and sum to one; tax in [0,1]"
        )
    if (
        min(
            inputs["risk_free_rate"],
            inputs["cost_of_debt"],
            inputs["cost_of_preference"],
            inputs["beta"],
        )
        < 0
    ):
        raise ValueError("Risk-free rate, financing costs and beta cannot be negative")
    premium = inputs["equity_risk_premium"] + equity_premium_stress
    if premium < 0:
        raise ValueError("Equity risk premium cannot be negative")
    ke = inputs["risk_free_rate"] + inputs["beta"] * premium
    after_tax_debt = inputs["cost_of_debt"] * (1 - inputs["tax_rate"])
    rate = equity * ke + debt * after_tax_debt + pref * inputs["cost_of_preference"]
    if not 0 < rate < 1:
        raise ValueError("WACC must be between zero and one")
    return {
        "currency": inputs["currency"],
        "risk_free_rate": inputs["risk_free_rate"],
        "equity_risk_premium": premium,
        "beta": inputs["beta"],
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


def blended_wacc(config, scenario):
    """Blend at 100% business EV weights, never the parent's ownership fraction.

    The current model assumes constant expected INR/USD throughout the forecast
    AND terminal period. Under that assumption the USD rate is numerically
    unchanged on conversion. If forecasting FX drift, both cash flows and rates
    must change together; editing the spot translation rate is not FX drift.
    """
    w = config["wacc"]
    stress = w["scenario_risk_premium"][scenario]
    tega = standalone_wacc(w["tega"], stress)
    mc = standalone_wacc(w["molycop"], stress)
    if tega["currency"] != "INR" or mc["currency"] != "USD":
        raise ValueError("Expected INR Tega and USD Molycop WACC inputs")
    tev = config["tega_ev_weight_inr_m"]
    mev = config["molycop_ev_weight_usd_m"] * config["fx_inr_per_usd"]
    if min(tev, mev) <= 0 or not all(isfinite(x) for x in (tev, mev)):
        raise ValueError(
            "Standalone operating EV weights must be positive finite amounts"
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
        "weight_basis": config["_ev_note"] + " " + config["_tega_ev_note"],
    }
