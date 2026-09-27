"""Build core income, balance-sheet and cash-flow links.

The engine completes legacy gaps using the explicit historical/zero policy.
Molycop missing accounts remain None. Neither business uses an equity plug.
FY2027 rows cover July-March future cash flows, not the entire financial year.
"""


def linked_statements(legacy, molycop, financing, shared):
    result = {"legacy": [], "molycop": []}
    for business, rows in (("legacy", legacy), ("molycop", molycop)):
        for row, funding in zip(rows, financing, strict=True):
            is_legacy = business == "legacy"
            prefix = "parent" if is_legacy else "molycop"
            interest = funding[f"{prefix}_cash_interest_inr_m"]
            shield = funding[f"{prefix}_interest_tax_shield_inr_m"]
            cash_tax = row["unlevered_cash_tax"] - shield
            operating_cost = row["revenue"] - row["operating_ebitda"]
            income = {
                "revenue": row["revenue"],
                "materials": None,
                "inventory_change_expense": None,
                "employee_expense": None,
                "other_expense": None,
                "unallocated_operating_expense": operating_cost
                if not is_legacy
                else 0.0,
                "operating_expense_total": operating_cost,
                "operating_ebitda": row["operating_ebitda"],
                "depreciation_amortisation": row["da"],
                "integration_expense_cash_proxy": row["integration_cash_cost"],
                "operating_profit_after_integration": row["ebit"]
                - row["integration_cash_cost"],
                "finance_cost_cash_proxy": interest,
                "operating_earnings_before_tax_proxy": row["ebit"]
                - row["integration_cash_cost"]
                - interest,
                "cash_tax_proxy": cash_tax,
                "operating_earnings_after_financing_and_cash_tax": row["ebit"]
                - row["integration_cash_cost"]
                - interest
                - cash_tax,
                "other_income": None,
                "joint_venture_profit": None,
                "profit_before_tax": None,
                "current_tax_expense": None,
                "deferred_tax_expense": None,
                "net_income": None,
                "owners_net_income": None,
                "eps_inr": None,
            }
            if is_legacy:
                income.update(
                    {
                        k: operating_cost * v
                        for k, v in shared["legacy_operating_cost_mix"].items()
                    }
                )
            balances = {
                "trade_receivables": row.get("closing_receivables"),
                "inventories": row.get("closing_inventory"),
                "trade_payables": row.get("closing_payables"),
                "other_operating_current_assets": row.get(
                    "closing_other_operating_current_assets"
                ),
                "other_operating_current_liabilities_and_current_provisions": row.get(
                    "closing_other_operating_current_liabilities"
                ),
                "net_operating_working_capital": row["closing_nwc"],
                "fixed_asset_book_including_cwip_proxy": row[
                    "closing_asset_book_proxy"
                ],
                "cwip_proxy": row["closing_cwip_proxy"],
                "nondepreciable_land": row["nondepreciable_land"]
                if is_legacy
                else None,
                "ppe": None,
                "rou_assets": None,
                "intangibles": None,
                "goodwill": None,
                "investments_and_other_financial_assets": None,
                "tax_assets_and_liabilities": None,
                "noncurrent_provisions_and_other_liabilities": None,
                "debt_current_noncurrent_split": None,
                "cash": funding["parent_closing_cash_inr_m"] if is_legacy else None,
                "gross_debt_including_leases_proxy": funding[
                    "parent_closing_gross_debt_inr_m"
                ]
                if is_legacy
                else None,
                "net_bank_debt_proxy": funding["molycop_closing_net_bank_debt_inr_m"]
                if not is_legacy
                else None,
                "preference_balance_assumed": funding[
                    "preference_closing_assumed_balance_inr_m"
                ]
                if not is_legacy
                else None,
                "share_capital": None,
                "retained_earnings": None,
                "other_reserves": None,
                "noncontrolling_interest": None,
                "total_assets": None,
                "total_liabilities": None,
                "total_equity": None,
                "balance_sheet_residual": None,
            }
            cfo = (
                row["operating_ebitda"]
                - row["integration_cash_cost"]
                - cash_tax
                - row["delta_nwc"]
            )
            cf = {
                "operating_earnings_before_tax_proxy": income[
                    "operating_earnings_before_tax_proxy"
                ],
                "da_addback": row["da"],
                "interest_addback": interest,
                "other_noncash_adjustments": None,
                "change_in_operating_working_capital": -row["delta_nwc"],
                "cash_tax_proxy": -cash_tax,
                "operating_cash_before_interest_proxy": cfo,
                "cash_capex": -row["cash_capex"],
                "cash_interest_proxy": -interest,
                "new_lease_assets_noncash": row["new_lease_assets"],
                "other_investing_cashflows": None,
                "dividends_to_tega_shareholders": None,
                "equity_issuance": None,
                "fx_effect_on_cash": None,
                "statutory_operating_cash_flow_total": None,
                "statutory_investing_cash_flow_total": None,
                "statutory_financing_cash_flow_total": None,
                "fcff_reconciliation_residual": row["fcff"]
                - (cfo - shield - row["cash_capex"] - row["new_lease_assets"]),
            }
            if is_legacy:
                repayment = (
                    funding["parent_scheduled_repayment_inr_m"]
                    + funding["parent_cash_sweep_inr_m"]
                )
                cf.update(
                    {
                        "opening_cash_proxy": funding["parent_opening_cash_inr_m"],
                        "subsidiary_distribution_received": funding[
                            "tega_share_of_distribution_inr_m"
                        ],
                        "debt_and_lease_principal_paid": -repayment,
                        "required_new_borrowing": funding[
                            "parent_required_new_funding_inr_m"
                        ],
                        "closing_cash_proxy": funding["parent_closing_cash_inr_m"],
                        "modeled_cash_rollforward_residual": funding[
                            "parent_cash_rollforward_residual"
                        ],
                    }
                )
            else:
                cf.update(
                    {
                        "opening_cash_proxy": None,
                        "debt_principal_paid": -funding["molycop_debt_paydown_inr_m"],
                        "lease_principal_paid": -funding[
                            "molycop_lease_principal_estimate_inr_m"
                        ],
                        "required_new_funding": funding[
                            "molycop_required_new_funding_inr_m"
                        ],
                        "ordinary_distributions_paid": -funding[
                            "molycop_ordinary_distribution_inr_m"
                        ],
                        "preference_return_paid": -funding[
                            "preference_cash_return_inr_m"
                        ],
                        "preference_noncash_accretion": funding[
                            "preference_non_cash_pik_inr_m"
                        ],
                        "earnout_paid": -funding["earnout_cash_inr_m"],
                        "closing_cash_proxy": None,
                        "modeled_cash_rollforward_residual": None,
                    }
                )
            result[business].append(
                {
                    "fiscal_year": row["fiscal_year"],
                    "period_years": row["period_years"],
                    "scope": "Partial future-period schedules at 100% business level; not statutory statements. None means unresolved, not zero. Operating earnings proxy excludes nonoperating income, JV profit, preference accounting and deferred taxes; it is not PAT.",
                    "income": income,
                    "balance_sheet": balances,
                    "cash_flow": cf,
                }
            )
    return result
