"""Derive ratio-module inputs from the same reconciled reported statements."""

from .inputs import reconcile_history


def financial_history_payload(case):
    reconcile_history(case)
    source = case["source"]
    source_id = f"tega_ar_{case['base_year']}"
    annuals = []
    for row in case["annuals"]:
        inc, a, li, eq, cf, total = [
            row[k]
            for k in (
                "income",
                "assets",
                "liabilities",
                "equity",
                "cash_flow",
                "reported_totals",
            )
        ]
        annuals.append(
            {
                "fiscal_year": row["fiscal_year"],
                "period_end": row["period_end"],
                "source_id": source_id,
                "revenue": inc["revenue"],
                "ebit": inc["operating_ebit"],
                "depreciation_amortisation": inc["depreciation_amortisation"],
                "net_income": inc["net_income"],
                "net_income_to_owners": inc["net_income"],
                "finance_costs": inc["finance_cost"],
                "total_assets": total["assets"],
                "total_liabilities": total["liabilities"],
                "total_equity": total["equity"],
                "equity_to_owners": total["equity"] - eq["noncontrolling_interest"],
                "current_assets": total["current_assets"],
                "current_liabilities": total["current_liabilities"],
                "cash_and_equivalents": a["cash"],
                "total_debt": li["term_debt"] + li["revolver"] + li["leases"],
                "operating_cash_flow": cf["operating_total"],
                "capex": -cf["investing"]["capital_asset_purchases"],
                "notes": "Derived from complete reported statements. EBIT excludes other income/JV profit; debt includes leases. NCI profit rounds to zero in these Tega accounts.",
            }
        )
    return {
        "schema_version": 1,
        "company": {
            "name": case["company"],
            "ticker": "TEGA.NS",
            "currency": "INR",
            "financial_unit": "million",
            "statement_basis": "consolidated",
            "data_kind": "reported",
        },
        "as_of": case["as_of"],
        "sources": [
            {
                "source_id": source_id,
                "title": source["title"],
                "published_on": source["published_on"],
                "url": source["url"],
                "locator": source["locators"]["balance_sheet"]
                + "; "
                + source["locators"]["cash_flow"],
            }
        ],
        "annuals": annuals,
        "notes": "Reported history, derived from the reconciled full statements. No forecast values. FY26 expenses include acquisition transaction costs. Returns use average balances.",
    }
