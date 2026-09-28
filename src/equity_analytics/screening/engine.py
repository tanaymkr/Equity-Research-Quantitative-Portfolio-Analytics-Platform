"""Screen reported financial metrics without modifying underlying observations."""

from datetime import date
from math import isfinite

from equity_analytics.data import DataStoreError
from equity_analytics.financials.ratios import analyze_history

MONEY = {"revenue", "ebitda", "net_debt", "cash_flow_after_capex"}
MULTIPLES = {
    "current_ratio",
    "debt_to_equity",
    "net_debt_to_ebitda",
    "finance_cost_coverage",
    "operating_cash_flow_to_net_income",
}
FRACTIONS = {
    "revenue_growth",
    "net_income_growth",
    "ebit_margin",
    "ebitda_margin",
    "net_margin",
    "roe",
    "roa",
    "roce",
    "operating_cash_flow_margin",
    "capex_to_revenue",
}
METRICS = tuple(sorted(MONEY | MULTIPLES | FRACTIONS))
UNIT_TO_MILLION = {"units": 1e-6, "million": 1.0, "crore": 10.0}


def validate_config(config):
    required = {
        "schema_version",
        "as_of",
        "company_ids",
        "basis",
        "currency",
        "period_end",
        "max_age_days",
        "filters",
        "sort_by",
        "ascending",
        "columns",
    }
    if set(config) != required:
        raise ValueError(f"Configuration keys must be exactly: {sorted(required)}")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("Unsupported screener configuration version")
    cutoff = date.fromisoformat(config["as_of"])
    period = (
        date.fromisoformat(config["period_end"])
        if config["period_end"] is not None
        else None
    )
    if period and period > cutoff:
        raise ValueError("period_end must not be after as_of")
    if config["basis"] not in {"consolidated", "standalone"}:
        raise ValueError("Unknown statement basis")
    if not isinstance(config["currency"], str) or len(config["currency"]) != 3:
        raise ValueError("Use a three-letter currency code")
    ids = config["company_ids"]
    if ids is not None and (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(x, str) or not x for x in ids)
        or len(ids) != len(set(ids))
    ):
        raise ValueError("company_ids must be null or a nonempty unique list")
    age = config["max_age_days"]
    if age is not None and (type(age) is not int or age < 0):
        raise ValueError("max_age_days must be null or a nonnegative integer")
    if type(config["ascending"]) is not bool:
        raise ValueError("ascending must be true or false")
    if config["sort_by"] not in METRICS:
        raise ValueError("Unknown sort metric")
    columns = config["columns"]
    if (
        not isinstance(columns, list)
        or not columns
        or any(x not in METRICS for x in columns)
        or len(columns) != len(set(columns))
    ):
        raise ValueError("columns must be a nonempty unique list of supported metrics")
    if not isinstance(config["filters"], dict):
        raise TypeError("filters must be an object")
    for metric, limits in config["filters"].items():
        if (
            metric not in METRICS
            or not isinstance(limits, dict)
            or not limits
            or not set(limits) <= {"min", "max"}
        ):
            raise ValueError(f"Invalid filter: {metric}")
        for value in limits.values():
            if type(value) not in (int, float) or not isfinite(value):
                raise ValueError("Filter thresholds must be finite numbers")
        if limits.get("min", -float("inf")) > limits.get("max", float("inf")):
            raise ValueError(f"Filter minimum exceeds maximum: {metric}")
    return cutoff, period


def screen_companies(store, config):
    cutoff, period = validate_config(config)
    profiles = {
        p["company_id"]: p
        for p in store.inventory()
        if p["statement_basis"] == config["basis"]
    }
    ids = (
        config["company_ids"] if config["company_ids"] is not None else sorted(profiles)
    )
    rows, excluded = [], []
    for cid in ids:
        profile = profiles.get(cid)
        reason = None
        if profile is None:
            reason = "unknown company or unavailable statement basis"
        elif profile["data_kind"] != "reported":
            reason = "synthetic data excluded"
        elif profile["currency"] != config["currency"]:
            reason = "currency differs; no FX conversion applied"
        if reason:
            excluded.append({"company_id": cid, "reason": reason})
            continue
        try:
            history = store.history_as_of(cid, config["as_of"], basis=config["basis"])
        except DataStoreError as exc:
            # Only the expected no-history condition is an exclusion. Corrupt data
            # and SQL failures must stop the run, not silently disappear.
            if str(exc) != "No financial statements published by this date":
                raise
            excluded.append({"company_id": cid, "reason": str(exc)})
            continue
        eligible = [
            a for a in history.annuals if period is None or a.period_end == period
        ]
        if not eligible:
            excluded.append(
                {
                    "company_id": cid,
                    "reason": "requested annual period unavailable at cutoff",
                }
            )
            continue
        annual = eligible[-1]
        age = (cutoff - annual.period_end).days
        if config["max_age_days"] is not None and age > config["max_age_days"]:
            excluded.append(
                {"company_id": cid, "reason": "financial period exceeds maximum age"}
            )
            continue
        report = analyze_history(history)
        year = next(y for y in report.years if y.fiscal_year == annual.fiscal_year)
        source = next(s for s in history.sources if s.source_id == annual.source_id)
        values, zero_filled = {}, {}
        for metric in METRICS:
            original = year.metrics[metric]
            if original.value is None:
                values[metric] = 0.0
                zero_filled[metric] = original.reason or "unavailable metric"
            else:
                value = original.value
                if metric in MONEY:
                    value *= UNIT_TO_MILLION[history.company.financial_unit]
                if not isfinite(value):
                    raise ValueError(f"{cid}: unit conversion overflow for {metric}")
                values[metric] = value
        failures = []
        for metric, limits in config["filters"].items():
            value = values[metric]
            if "min" in limits and value < limits["min"]:
                failures.append(f"{metric} below {limits['min']}")
            if "max" in limits and value > limits["max"]:
                failures.append(f"{metric} above {limits['max']}")
        rows.append(
            {
                "company_id": cid,
                "company_name": history.company.name,
                "ticker": history.company.ticker,
                "fiscal_year": annual.fiscal_year,
                "period_end": annual.period_end.isoformat(),
                "published_on": source.published_on.isoformat(),
                "age_days": age,
                "basis": config["basis"],
                "currency": history.company.currency,
                "financial_unit": "million",
                "source_id": source.source_id,
                "source_url": source.url,
                "source_title": source.title,
                "source_locator": source.locator,
                "values": values,
                "zero_filled": zero_filled,
                "warnings": list(year.warnings),
                "passes": not failures,
                "failed_filters": failures,
            }
        )
    # Stable deterministic ties. Position is ordinal, not a composite factor score.
    direction = 1 if config["ascending"] else -1
    rows.sort(
        key=lambda r: (direction * r["values"][config["sort_by"]], r["company_id"])
    )
    matches = [r for r in rows if r["passes"]]
    for i, row in enumerate(matches, 1):
        row["position"] = i
    return {
        "schema_version": 1,
        "configuration": config,
        "missing_policy": "zero",
        "metric_units": {
            m: (
                "million"
                if m in MONEY
                else "multiple"
                if m in MULTIPLES
                else "fraction"
            )
            for m in METRICS
        },
        "rows": rows,
        "matches": matches,
        "excluded": excluded,
        "counts": {
            "requested": len(ids),
            "evaluated": len(rows),
            "matched": len(matches),
            "excluded": len(excluded),
        },
    }
