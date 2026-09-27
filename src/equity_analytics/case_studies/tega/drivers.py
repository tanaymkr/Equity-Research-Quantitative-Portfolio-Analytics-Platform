"""Historical driver calculations and an auditable forecast evidence register."""

from copy import deepcopy
from statistics import mean


def historical_drivers(previous, current):
    """Average annual ratios, giving each available year equal weight.

    FY25 overlaps: require it to agree, then prefer the newer audited source.
    Ratios use closing balances, not average-balance turnover statistics.
    """
    annuals = {r["fiscal_year"]: r for r in previous["annuals"]}
    for row in current["annuals"]:
        year = row["fiscal_year"]
        old = deepcopy(annuals.get(year, row))
        # The newer schema spells out this reported zero cash-flow line.
        old["cash_flow"]["financing"].setdefault("term_borrowing_proceeds", 0.0)
        if year in annuals and old != row:
            raise ValueError(f"Conflicting reported history for FY{year}")
        annuals[year] = row
    rows = [annuals[y] for y in sorted(annuals)]
    observations = []
    for row in rows:
        inc, a, li, cf = [
            row[k] for k in ("income", "assets", "liabilities", "cash_flow")
        ]
        rev = inc["revenue"]
        transaction = (
            current["base_year_disclosures"]["transaction_expense"]
            if row["fiscal_year"] == 2026
            else 0.0
        )
        costs = {
            "materials": inc["materials"],
            "inventory_change_expense": inc["inventory_change_expense"],
            "employee_expense": inc["employee_expense"],
            "other_expense": inc["other_expense"] - transaction,
        }
        total_cost = sum(costs.values())
        observations.append(
            {
                "fiscal_year": row["fiscal_year"],
                "receivable_days": a["receivables"] / rev * 365,
                "inventory_revenue_fraction": a["inventories"] / rev,
                "payable_revenue_fraction": li["payables"] / rev,
                "other_operating_current_assets_revenue_fraction": (
                    a["other_current_assets"] + a["contract_assets"]
                )
                / rev,
                "other_operating_current_liabilities_revenue_fraction": (
                    li["other_current_liabilities"] + li["current_provisions"]
                )
                / rev,
                "cash_capex_revenue_fraction": -cf["investing"][
                    "capital_asset_purchases"
                ]
                / rev,
                "effective_accounting_tax_rate": (
                    inc["current_tax"] + inc["deferred_tax"]
                )
                / inc["profit_before_tax"],
                "cfo_after_financing_interest": cf["operating_total"]
                + cf["financing"]["borrowing_interest_paid"]
                + cf["financing"]["lease_interest_paid"],
                "term_principal_repayment": -cf["financing"][
                    "term_principal_repayment"
                ],
                "lease_principal_repayment": -cf["financing"]["lease_principal_paid"],
                **{
                    f"{k}_share_of_operating_cost": v / total_cost
                    for k, v in costs.items()
                },
            }
        )
    averages = {
        k: mean(r[k] for r in observations)
        for k in observations[0]
        if k != "fiscal_year"
    }
    return {
        "years": sorted(annuals),
        "method": "Arithmetic mean of available annual ratios; closing-balance/sales convention. FY26 transaction costs removed from operating cost mix only. Tax is unadjusted total accounting tax / PBT, a cash-tax proxy rather than a statutory marginal tax rate.",
        "observations": observations,
        "averages": averages,
        "source_urls": [previous["source"]["url"], current["source"]["url"]],
    }


def evidence_register(assumptions):
    """Expose the values actually used; identify edits made after source review."""
    result = deepcopy(assumptions.get("forecast_policy", {}))
    for item in result.get("drivers", []):
        actual = {}
        for path in item["reviewed_values"]:
            value = assumptions
            for key in path.split("."):
                value = value[key]
            actual[path] = value
        item["current_values"] = actual
        item["changed_since_review"] = actual != item["reviewed_values"]
        if item["changed_since_review"]:
            item["status"] = "User/model override; source review must be refreshed"
    return result
