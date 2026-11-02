"""Standalone costs of capital and an auditable value-weighted blend.

All numeric choices live in assumptions.pro_forma, with adjacent source notes.
Constant FX is an explicit expected-rate assumption, not an implicit USD/INR hedge.
"""

from math import isfinite

from equity_analytics.valuation.cost_of_capital import (
    default_free_rate,
    unlevered_cost_of_capital,
    wacc_with_tax_shield,
)

REQUIRED = (
    "government_bond_yield",
    "sovereign_default_spread",
    "equity_risk_premium",
    "unlevered_beta",
    "cost_of_debt",
    "tax_rate",
    "debt_weight",
)


def standalone_wacc(inputs, equity_premium_stress=0.0):
    """Platform method: unlevered cost of capital less the interest tax shield.

    Preference capital earns no tax shield, so it does not change the WACC; its
    claim is deducted in the equity bridge. An optional ``transaction_premium``
    adds business-specific risk calibrated to an arm's-length purchase price.
    """
    for key in REQUIRED:
        if (
            isinstance(inputs[key], bool)
            or not isinstance(inputs[key], (int, float))
            or not isfinite(inputs[key])
        ):
            raise ValueError(f"WACC {key} must be finite")
    premium = inputs["equity_risk_premium"] + equity_premium_stress
    if premium < 0:
        raise ValueError("Equity risk premium cannot be negative")
    rf = default_free_rate(
        inputs["government_bond_yield"], inputs["sovereign_default_spread"]
    )
    transaction_premium = inputs.get("transaction_premium", 0.0)
    if (
        isinstance(transaction_premium, bool)
        or not isinstance(transaction_premium, (int, float))
        or not isfinite(transaction_premium)
        or transaction_premium < 0
    ):
        raise ValueError("WACC transaction_premium must be finite and nonnegative")
    capm_cost = unlevered_cost_of_capital(rf, inputs["unlevered_beta"], premium)
    rates = wacc_with_tax_shield(
        capm_cost + transaction_premium,
        inputs["debt_weight"],
        inputs["tax_rate"],
        inputs["cost_of_debt"],
    )
    return {
        "currency": inputs["currency"],
        "government_bond_yield": inputs["government_bond_yield"],
        "sovereign_default_spread": inputs["sovereign_default_spread"],
        "risk_free_rate": rf,
        "equity_risk_premium": premium,
        "unlevered_beta": inputs["unlevered_beta"],
        "capm_unlevered_cost": capm_cost,
        "transaction_premium": transaction_premium,
        "unlevered_cost_of_capital": rates["unlevered_cost_of_capital"],
        "cost_of_debt": inputs["cost_of_debt"],
        "debt_weight": inputs["debt_weight"],
        "tax_rate": inputs["tax_rate"],
        "tax_shield": rates["tax_shield"],
        "standalone_wacc": rates["wacc"],
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
