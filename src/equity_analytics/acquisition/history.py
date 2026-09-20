"""Connect the acquisition DCF to the reconciled full FY26 statements."""

from copy import deepcopy
from pathlib import Path

from equity_analytics.forecasting.inputs import (
    ModelInputError,
    load_json,
    reconcile_history,
)

from .drivers import historical_drivers


def legacy_facts_from_statements(case):
    """Derive every legacy annual input; keep no second editable copy."""
    checks = reconcile_history(case)
    if case["base_year"] != 2026 or case["company"] != "Tega Industries Limited":
        raise ModelInputError(
            "Acquisition bridge requires Tega consolidated FY2026 statements"
        )
    row = case["annuals"][-1]
    a, li, inc, cf, t = [
        row[k]
        for k in ("assets", "liabilities", "income", "cash_flow", "reported_totals")
    ]
    d = case["base_year_disclosures"]
    h = {"source_ids": ["annual26"], "period_end": row["period_end"]}
    for target, source in {
        "revenue": "revenue",
        "other_income": "other_income",
        "depreciation_amortization": "depreciation_amortisation",
        "finance_cost": "finance_cost",
        "pat": "net_income",
    }.items():
        h[target] = inc[source]
    for target, source in {
        "cash": "cash",
        "current_investments": "current_investments",
        "receivables": "receivables",
        "inventory": "inventories",
        "jv_investment": "joint_venture",
        "investment_property": "investment_property",
        "ppe": "ppe",
        "cwip": "cwip",
        "right_of_use_assets": "rou_assets",
        "intangible_assets": "intangibles",
        "intangible_development": "intangibles_under_development",
    }.items():
        h[target] = a[source]
    h.update(
        {
            "consumables_gross_revenue": d["segment_revenue"]["consumables_gross"],
            "equipment_revenue": d["segment_revenue"]["equipment"],
            "intersegment_revenue": d["segment_revenue"]["intersegment"],
            "reported_ebitda_including_other_income": round(
                inc["operating_ebitda"] + inc["other_income"], 2
            ),
            "transaction_expense": d["transaction_expense"],
            "tax_expense": round(inc["current_tax"] + inc["deferred_tax"], 2),
            "cash_from_operations": cf["operating_total"],
            "cash_capex": -cf["investing"]["capital_asset_purchases"],
            "cash_lease_principal": -cf["financing"]["lease_principal_paid"],
            "cash_lease_interest": -cf["financing"]["lease_interest_paid"],
            "bank_deposits": d["cash_and_bank"]["other_bank_deposits"],
            "restricted_deposits": d["cash_and_bank"]["pledged_bank_deposits"],
            "unpaid_dividend_bank": d["cash_and_bank"]["unpaid_dividend_accounts"],
            "borrowings_noncurrent": t["noncurrent_borrowings"],
            "borrowings_current": t["current_borrowings"],
            "lease_liabilities": li["leases"],
            "payables": li["payables"],
            "assets": t["assets"],
            "liabilities": t["liabilities"],
            "equity": t["equity"],
            "shares": round(t["shares_outstanding_million"] * 1e6),
            "shares_issued_november2025": d["equity_issue"]["new_shares"],
            "november2025_issue_price_inr": d["equity_issue"]["issue_price_inr"],
            "other_operating_current_assets": a["other_current_assets"]
            + a["contract_assets"],
            "other_operating_current_liabilities": li["other_current_liabilities"]
            + li["current_provisions"],
            "nondepreciable_land": next(
                c["net_book_value"]
                for c in case["asset_cohorts"]
                if c["name"] == "ppe_land"
            ),
        }
    )
    return h, checks


def load_acquisition_facts(path, statements_path=None):
    """Resolve the statement path relative to the facts file, never the CWD."""
    path = Path(path)
    facts = load_json(path)
    if "tega_fy2026" in facts:
        raise ModelInputError(
            "Remove duplicated tega_fy2026 values; use reported_statements_file"
        )
    statement_path = (
        Path(statements_path)
        if statements_path
        else path.parent / facts["reported_statements_file"]
    )
    case = load_json(statement_path)
    if case["as_of"] > facts["information_cutoff"]:
        raise ModelInputError(
            "Reported statements exceed the acquisition research cutoff"
        )
    h, checks = legacy_facts_from_statements(case)
    result = deepcopy(facts)
    result["tega_fy2026"] = h
    result["sources"]["annual26"] = {
        "date": case["source"]["published_on"],
        "title": case["source"]["title"],
        "url": case["source"]["url"],
        "location": "Full consolidated statements and supporting notes; see historical_statements.md for PDF pages",
    }
    result["reported_history"] = {
        "file": statement_path.name,
        "base_year": case["base_year"],
        "source": case["source"],
        "reconciliation_checks_passed": len(checks),
    }
    if facts.get("historical_comparatives_file"):
        previous = load_json(path.parent / facts["historical_comparatives_file"])
        reconcile_history(previous)
        try:
            result["historical_drivers"] = historical_drivers(previous, case)
        except ValueError as exc:
            raise ModelInputError(str(exc)) from exc
    return result, case, checks
