"""Explicit USD-origin conversion registry; no substring-based money guessing."""

from copy import deepcopy
from math import isfinite


def prepare_currency(facts, assumptions):
    f, a = deepcopy(facts), deepcopy(assumptions)
    original = f["currency_basis"]
    if original != a["currency_basis"] or original["currency"] != "INR":
        raise ValueError("Source currency bases must match")
    # Source file is an immutable conversion snapshot. Only the separate input
    # below changes model FX; editing metadata would silently misstate USD values.
    if original["inr_per_usd"] != 94.97 or original["fx_date"] != "2026-09-02":
        raise ValueError(
            "Source snapshot must remain 94.97 at 2026-09-02; edit pro_forma.fx_inr_per_usd"
        )
    if any("_usd_m" in key for key in a["shared"]):
        raise ValueError("Legacy mixed-currency shared inputs are unsupported")
    rate = a["pro_forma"]["fx_inr_per_usd"]
    reference = original["inr_per_usd"]
    if not isfinite(rate) or rate <= 0 or reference <= 0:
        raise ValueError("FX must be positive and finite")
    containers = {"facts": f, "assumptions": a}
    audit = []

    def scale(v):
        if v is None:
            return None
        if isinstance(v, list):
            return [scale(x) for x in v]
        return v * rate / reference

    for path in a["pro_forma"]["fx_translation_paths"]:
        obj = containers
        for part in path[:-1]:
            obj = obj[part]
        key = path[-1]
        before = obj[key]
        obj[key] = deepcopy(before) if rate == reference else scale(before)
        audit.append(
            {"path": ".".join(path), "reference_inr": before, "model_inr": obj[key]}
        )
    for obj in (f, a):
        obj["currency_basis"]["reference_conversion_rate"] = reference
        obj["currency_basis"]["inr_per_usd"] = rate
        obj["currency_basis"]["method"] = (
            "USD-origin inputs rebased through explicit registry; reported INR actuals retained. Constant expected FX across all forecast years."
        )
    return f, a, audit
