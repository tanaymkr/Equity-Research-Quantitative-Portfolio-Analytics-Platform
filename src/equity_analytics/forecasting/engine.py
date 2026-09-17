"""Linked income, balance sheet, cash flow, asset and financing schedules.

This is a deliberately bounded annual model, not a statutory consolidation engine.
Callers must supply their own inputs; no company forecast defaults are retained.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite

from .inputs import (
    ModelInputError,
    asset_cohorts,
    reconcile_history,
    validate_assumptions,
)


class FundingError(ModelInputError):
    """The assumed facility cannot meet the model's minimum cash requirement."""


@dataclass
class AssetCohort:
    name: str
    account: str
    book: float
    annual_charge: float

    def depreciate(self, fraction: float = 1.0) -> float:
        charge = min(self.book, self.annual_charge * fraction)
        self.book -= charge
        return charge


def operating_working_capital(assets: dict, liabilities: dict) -> float:
    return assets["receivables"] + assets["inventories"] - liabilities["payables"]


def _asset_schedule(cohorts: list[AssetCohort], additions: list[tuple]) -> list[dict]:
    rows = []
    for cohort in cohorts:
        opening = cohort.book
        charge = cohort.depreciate()
        rows.append(
            {
                "name": cohort.name,
                "account": cohort.account,
                "opening": opening,
                "additions": 0.0,
                "depreciation_amortisation": charge,
                "closing": cohort.book,
            }
        )
    for name, account, cost, life in additions:
        cohort = AssetCohort(name, account, cost, cost / life)
        charge = cohort.depreciate(0.5)
        cohorts.append(cohort)
        rows.append(
            {
                "name": name,
                "account": account,
                "opening": 0.0,
                "additions": cost,
                "depreciation_amortisation": charge,
                "closing": cohort.book,
            }
        )
    return rows


def _dcf(case: dict, assumptions: dict, years: list[dict]) -> dict:
    """End-year enterprise DCF with leases treated as financing."""
    base = case["annuals"][-1]
    d = assumptions["dcf"]
    wacc, growth, roic = d["wacc"], d["terminal_growth"], d["terminal_roic"]
    discounted = [r["fcff"] / (1 + wacc) ** i for i, r in enumerate(years, 1)]
    terminal_ebit = years[-1]["income"]["ebit"] * (1 + growth)
    terminal_nopat = terminal_ebit - max(terminal_ebit, 0) * assumptions["tax_rate"]
    if terminal_nopat <= 0:
        return {
            "available": False,
            "reason": "Positive sustainable terminal NOPAT is required.",
            "discounted_fcff": discounted,
        }
    terminal_reinvestment = terminal_nopat * growth / roic
    terminal_fcff = terminal_nopat - terminal_reinvestment
    terminal_value = terminal_fcff / (wacc - growth)
    pv_terminal = terminal_value / (1 + wacc) ** len(years)
    enterprise_value = sum(discounted) + pv_terminal
    a, l = base["assets"], base["liabilities"]
    bridge = {
        "cash": a["cash"],
        "current_investments": a["current_investments"],
        "joint_venture_value_assumption": d["joint_venture_value"],
        "investment_property_value_assumption": d["investment_property_value"],
        "term_debt": -l["term_debt"],
        "revolver": -l["revolver"],
        "lease_debt": -l["leases"],
        "noncontrolling_interest_value_assumption": -d["noncontrolling_interest_value"],
    }
    # Accrued interest sits in other financial liabilities, not principal pools.
    totals = base["reported_totals"]
    bridge["accrued_borrowing_interest"] = -(
        totals["accrued_term_interest"] + totals["accrued_short_term_interest"]
    )
    equity_value = enterprise_value + sum(bridge.values())
    shares = base["reported_totals"]["shares_outstanding_million"]
    return {
        "available": True,
        "basis": "Historical FY2025 illustrative DCF",
        "valuation_date": "2025-03-31",
        "information_as_of": case["as_of"],
        "discounted_fcff": discounted,
        "terminal_nopat": terminal_nopat,
        "terminal_reinvestment": terminal_reinvestment,
        "terminal_fcff": terminal_fcff,
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "bridge": bridge,
        "equity_value": equity_value,
        "shares_outstanding_million": shares,
        "value_per_share_inr": equity_value / shares,
        "terminal_share_of_enterprise_value": pv_terminal / enterprise_value,
    }


def build_forecast(case: dict, assumptions: dict) -> dict:
    """Validate a reported case, then recalculate every linked forecast schedule."""
    historical_checks = reconcile_history(case)
    horizon = validate_assumptions(assumptions, case)
    base, a = case["annuals"][-1], assumptions
    assets, liabilities, equity = [
        deepcopy(base[k]) for k in ["assets", "liabilities", "equity"]
    ]
    opening_rounding_residual = (
        sum(assets.values()) - sum(liabilities.values()) - sum(equity.values())
    )
    cohorts = []
    for row in asset_cohorts(case):
        life = a["opening_remaining_life_years"][row["name"]]
        cohorts.append(
            AssetCohort(
                row["name"],
                row["account"],
                row["net_book_value"],
                row["net_book_value"] / life if life else 0,
            )
        )
    years = []
    revenue = base["income"]["revenue"]
    for i in range(horizon):
        year = case["base_year"] + i + 1
        old_a, old_l, old_e = deepcopy(assets), deepcopy(liabilities), deepcopy(equity)
        revenue *= 1 + a["revenue_growth"][i]
        capex = revenue * a["cash_capex_pct_revenue"][i]
        tangible_capex = capex * a["tangible_capex_share"]
        intangible_capex = capex - tangible_capex
        commissioned_ppe = (old_a["cwip"] + tangible_capex) * a[
            "commissioning_fraction"
        ]
        commissioned_intangibles = (
            old_a["intangibles_under_development"] + intangible_capex
        ) * a["commissioning_fraction"]
        assets["cwip"] += tangible_capex - commissioned_ppe
        assets["intangibles_under_development"] += (
            intangible_capex - commissioned_intangibles
        )
        new_lease = a["new_lease_assets"][i]
        asset_rows = _asset_schedule(
            cohorts,
            [
                (f"ppe_{year}", "ppe", commissioned_ppe, a["new_ppe_life_years"]),
                (
                    f"intangibles_{year}",
                    "intangibles",
                    commissioned_intangibles,
                    a["new_intangible_life_years"],
                ),
                (f"rou_{year}", "rou_assets", new_lease, a["new_rou_life_years"]),
            ],
        )
        da = sum(r["depreciation_amortisation"] for r in asset_rows)
        for account in ["ppe", "rou_assets", "intangibles"]:
            assets[account] = sum(
                r["closing"] for r in asset_rows if r["account"] == account
            )
        assets["receivables"] = revenue * a["receivable_days"][i] / 365
        assets["inventories"] = revenue * a["inventory_pct_revenue"][i]
        liabilities["payables"] = revenue * a["payables_pct_revenue"][i]
        delta_nwc = operating_working_capital(
            assets, liabilities
        ) - operating_working_capital(old_a, old_l)
        term_payment = a["term_principal_repayment"][i]
        lease_payment = a["lease_principal_repayment"][i]
        if term_payment > old_l["term_debt"] + 1e-8:
            raise ModelInputError(f"FY{year}: term repayment exceeds opening principal")
        if lease_payment > old_l["leases"] + 1e-8:
            raise ModelInputError(
                f"FY{year}: lease repayment exceeds opening principal"
            )
        liabilities["term_debt"] = max(0, old_l["term_debt"] - term_payment)
        liabilities["leases"] = old_l["leases"] + new_lease - lease_payment
        interest_by_pool = {
            "term_debt": old_l["term_debt"] * a["term_interest_rate"],
            "revolver": old_l["revolver"] * a["revolver_interest_rate"],
            "leases": old_l["leases"] * a["lease_interest_rate"],
        }
        interest = sum(interest_by_pool.values())
        ebitda = revenue * a["ebitda_margin"][i]
        ebit = ebitda - da
        pbt = ebit + a["joint_venture_profit"] - interest
        # Equity-accounted JV profit is already after the JV's own tax.
        # No additional group-level tax on that profit/dividend is assumed.
        taxable_profit = ebit - interest
        tax = max(taxable_profit, 0) * a["tax_rate"]
        net_income = pbt - tax
        dividends = max(net_income, 0) * a["dividend_payout_ratio"]
        assets["joint_venture"] += (
            a["joint_venture_profit"] - a["joint_venture_dividend"]
        )
        if assets["joint_venture"] < -1e-8:
            raise ModelInputError(f"FY{year}: JV carrying value becomes negative")
        equity["retained_earnings"] += net_income - dividends
        cfo = net_income + da + interest - a["joint_venture_profit"] - delta_nwc
        cfi = -capex + a["joint_venture_dividend"]
        cff_before_revolver = -term_payment - lease_payment - interest - dividends
        cash_before_funding = old_a["cash"] + cfo + cfi + cff_before_revolver
        draw = max(a["minimum_cash"] - cash_before_funding, 0)
        if old_l["revolver"] + draw > a["revolver_limit"] + 1e-8:
            shortfall = old_l["revolver"] + draw - a["revolver_limit"]
            raise FundingError(
                f"FY{year}: facility limit exceeded by INR {shortfall:.2f} million"
            )
        sweep = (
            min(max(cash_before_funding - a["minimum_cash"], 0), old_l["revolver"])
            if a["sweep_excess_cash_to_revolver"]
            else 0
        )
        liabilities["revolver"] = old_l["revolver"] + draw - sweep
        cff = cff_before_revolver + draw - sweep
        assets["cash"] = old_a["cash"] + cfo + cfi + cff
        total_assets = sum(assets.values())
        total_liabilities = sum(liabilities.values())
        total_equity = sum(equity.values())
        residual = total_assets - total_liabilities - total_equity
        checks = {
            "balance_sheet_residual": residual,
            "change_in_opening_rounding_residual": residual - opening_rounding_residual,
            "cash_roll_residual": assets["cash"] - old_a["cash"] - cfo - cfi - cff,
            "retained_earnings_residual": equity["retained_earnings"]
            - old_e["retained_earnings"]
            - net_income
            + dividends,
        }
        for name, value in checks.items():
            tolerance = 0.02000001 if name == "balance_sheet_residual" else 1e-7
            if not isfinite(value) or abs(value) > tolerance:
                raise ModelInputError(f"FY{year}: {name} failed ({value})")
        if assets["cash"] < a["minimum_cash"] - 1e-7:
            raise FundingError(f"FY{year}: cash is below the required minimum")
        debt_rows = []
        for pool, repayment, addition in [
            ("term_debt", term_payment, 0),
            ("revolver", sweep, draw),
            ("leases", lease_payment, new_lease),
        ]:
            debt_rows.append(
                {
                    "pool": pool,
                    "opening": old_l[pool],
                    "cash_draw": addition if pool == "revolver" else 0,
                    "noncash_new_leases": addition if pool == "leases" else 0,
                    "principal_repayment": repayment,
                    "interest_expense_and_cash_paid": interest_by_pool[pool],
                    "closing": liabilities[pool],
                }
            )
        nopat = ebit - max(ebit, 0) * a["tax_rate"]
        # Leases are debt in the EV bridge, so new leased assets are economic capex.
        fcff = nopat + da - capex - new_lease - delta_nwc
        years.append(
            {
                "fiscal_year": year,
                "income": {
                    "revenue": revenue,
                    "ebitda": ebitda,
                    "depreciation_amortisation": da,
                    "ebit": ebit,
                    "joint_venture_profit": a["joint_venture_profit"],
                    "finance_cost": interest,
                    "profit_before_tax": pbt,
                    "taxable_profit": taxable_profit,
                    "tax": tax,
                    "net_income": net_income,
                },
                "balance_sheet": {
                    "assets": deepcopy(assets),
                    "liabilities": deepcopy(liabilities),
                    "equity": deepcopy(equity),
                    "total_assets": total_assets,
                    "total_liabilities": total_liabilities,
                    "total_equity": total_equity,
                },
                "cash_flow": {
                    "opening_cash": old_a["cash"],
                    "net_income": net_income,
                    "depreciation_amortisation": da,
                    "finance_cost_addback": interest,
                    "joint_venture_profit_deduction": -a["joint_venture_profit"],
                    "change_in_working_capital": -delta_nwc,
                    "operating": cfo,
                    "cash_capex": -capex,
                    "joint_venture_dividend": a["joint_venture_dividend"],
                    "investing": cfi,
                    "term_repayment": -term_payment,
                    "lease_principal_repayment": -lease_payment,
                    "interest_paid": -interest,
                    "dividends": -dividends,
                    "revolver_draw": draw,
                    "revolver_repayment": -sweep,
                    "financing": cff,
                    "closing_cash": assets["cash"],
                },
                "asset_schedule": asset_rows,
                "construction_schedule": {
                    "cwip": {
                        "opening": old_a["cwip"],
                        "cash_additions": tangible_capex,
                        "commissioned": commissioned_ppe,
                        "closing": assets["cwip"],
                    },
                    "development": {
                        "opening": old_a["intangibles_under_development"],
                        "cash_additions": intangible_capex,
                        "commissioned": commissioned_intangibles,
                        "closing": assets["intangibles_under_development"],
                    },
                },
                "debt_schedule": debt_rows,
                "nopat": nopat,
                "delta_operating_working_capital": delta_nwc,
                "new_leased_assets_economic_capex": new_lease,
                "fcff": fcff,
                "checks": checks,
            }
        )
    result = {
        "base_year": case["base_year"],
        "company": case["company"],
        "label": a["label"],
        "as_of": case["as_of"],
        "currency": "INR",
        "financial_unit": "million",
        "historical_rounding_tolerance": 0.02,
        "opening_balance_sheet_rounding_residual": opening_rounding_residual,
        "historical_checks": historical_checks,
        "assumptions": deepcopy(a),
        "historical_source": deepcopy(case["source"]),
        "years": years,
        "dcf": _dcf(case, a, years),
    }
    return result
