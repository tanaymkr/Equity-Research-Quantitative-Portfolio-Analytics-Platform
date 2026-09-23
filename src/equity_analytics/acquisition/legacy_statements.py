"""Complete legacy Tega statement gaps without altering the operating DCF.

This is a legacy-only forecast with the Molycop investment at cost, not the
acquired group's statutory consolidation. Reported balances are never zeroed
just because forecast movements are assumed zero. The estimated June opening
balance discrepancy is exposed, not absorbed into equity, cash or another asset.
"""

from copy import deepcopy
from statistics import mean


def statement_parameters(facts, shared, policy):
    history = facts["legacy_statement_history"]
    annuals = {r["fiscal_year"]: r for r in history["annuals"]}
    current = annuals[2026]
    disclosures = facts["legacy_statement_disclosures"]["annual_note_31"]
    cash_base = mean(
        annuals[y]["assets"]["cash"] + annuals[y]["assets"]["other_bank_balances"]
        for y in (2024, 2025)
    )
    lease_principal = mean(
        -r["cash_flow"]["financing"]["lease_principal_paid"] for r in annuals.values()
    )
    bank_principal = mean(
        -r["cash_flow"]["financing"]["term_principal_repayment"]
        for r in annuals.values()
    )
    ppe_add = history["reconciliations"]["ppe_net"]["gross_additions"]
    int_add = history["reconciliations"]["intangibles_net"]["gross_additions"]
    return {
        "cash_interest_yield": disclosures["fy2025_interest_on_financial_instruments"]
        / cash_base,
        "cash_interest_yield_denominator_inr_m": cash_base,
        "annual_miscellaneous_income_inr_m": mean(
            disclosures[f"fy{y}_miscellaneous_receipts"] for y in (2025, 2026)
        ),
        "annual_joint_venture_profit_inr_m": mean(
            r["income"]["joint_venture_profit"] for r in annuals.values()
        ),
        "annual_joint_venture_dividend_inr_m": mean(
            r["cash_flow"]["investing"]["joint_venture_dividend"]
            for r in annuals.values()
        ),
        "dividend_per_share_inr": policy["dividend_per_share_inr"],
        "shares_million": current["reported_totals"]["shares_outstanding_million"],
        "effective_tax_rate": shared["earned_income_tax_rate_legacy"],
        "tangible_capex_fraction": ppe_add / (ppe_add + int_add),
        "lease_share_of_scheduled_principal": lease_principal
        / (lease_principal + bank_principal),
        "current_provisions_share_of_operating_liabilities": current["liabilities"][
            "current_provisions"
        ]
        / (
            current["liabilities"]["current_provisions"]
            + current["liabilities"]["other_current_liabilities"]
        ),
        "contract_assets_share_of_other_operating_assets": current["assets"][
            "contract_assets"
        ]
        / (
            current["assets"]["contract_assets"]
            + current["assets"]["other_current_assets"]
        ),
    }


def nonoperating_cashflows(row, opening_cash, interest, shield, jv_book, p):
    """Cash effects of formerly missing lines, before borrowing/sweeping cash."""
    fraction = row["period_years"]
    interest_income = max(opening_cash, 0) * p["cash_interest_yield"] * fraction
    miscellaneous = p["annual_miscellaneous_income_inr_m"] * fraction
    jv_profit = p["annual_joint_venture_profit_inr_m"] * fraction
    jv_dividend = min(
        max(jv_book + jv_profit, 0),
        p["annual_joint_venture_dividend_inr_m"] * fraction,
    )
    operating_cash_tax = row["unlevered_cash_tax"] - shield
    taxable = (
        row["ebit"]
        - row["integration_cash_cost"]
        - interest
        + interest_income
        + miscellaneous
    )
    current_tax = max(taxable, 0) * p["effective_tax_rate"]
    extra_tax = current_tax - operating_cash_tax
    # The annual dividend falls within July-March: do not prorate it to 9/12.
    dividend = p["dividend_per_share_inr"] * p["shares_million"]
    return {
        "parent_interest_income_inr_m": interest_income,
        "parent_miscellaneous_income_inr_m": miscellaneous,
        "parent_joint_venture_profit_inr_m": jv_profit,
        "parent_joint_venture_dividend_inr_m": jv_dividend,
        "parent_cash_tax_total_inr_m": current_tax,
        "parent_additional_nonoperating_tax_inr_m": extra_tax,
        "parent_dividends_paid_inr_m": dividend,
        "parent_nonoperating_cash_adjustment_inr_m": (
            interest_income + miscellaneous + jv_dividend - extra_tax - dividend
        ),
        "parent_joint_venture_closing_book_inr_m": jv_book + jv_profit - jv_dividend,
    }


class LegacyAssetDetail:
    """Allocate the existing pooled cohorts; preserve their lives and total D&A."""

    def __init__(self, facts, shared, bridge, parameters):
        h = facts["legacy_statement_history"]
        base = h["annuals"][-1]["assets"]
        self.land = facts["tega_fy2026"]["nondepreciable_land"]
        self.tangible = parameters["tangible_capex_fraction"]
        capex = bridge["q1_cash_capex_estimate"]
        commissioned = capex * shared["legacy_opening_commissioned_q1_capex_fraction"]
        q1_lease = shared["legacy_annual_new_lease_assets_inr_m"] / 4
        parts = {
            "ppe": base["ppe"] - self.land + commissioned * self.tangible,
            "rou_assets": base["rou_assets"] + q1_lease,
            "intangibles": base["intangibles"] + commissioned * (1 - self.tangible),
        }
        q1_da = facts["q1_fy2027"]["tega_da"]
        total = sum(parts.values())
        # Allocation only: pooled Q1 D&A is already fixed by the reported result.
        parts = {key: value * (1 - q1_da / total) for key, value in parts.items()}
        self.cohorts = [{"parts": parts, "annual": q1_da * 4}]
        self.cwip = {
            "ppe": base["cwip"] + (capex - commissioned) * self.tangible,
            "intangibles": base["intangibles_under_development"]
            + (capex - commissioned) * (1 - self.tangible),
        }

    def balances(self):
        result = {
            key: sum(c["parts"].get(key, 0) for c in self.cohorts)
            for key in ("ppe", "rou_assets", "intangibles")
        }
        result["ppe"] += self.land
        result["cwip"] = self.cwip["ppe"]
        result["intangibles_under_development"] = self.cwip["intangibles"]
        return result

    def advance(self, row, shared, first):
        fraction = row["period_years"]
        capex = row["cash_capex"]
        allocation = {"ppe": self.tangible, "intangibles": 1 - self.tangible}
        commissioned = {}
        for key, share in allocation.items():
            new_capex = capex * share
            amount = self.cwip[key] * (0.8 if first else 1) + new_capex * (
                0.3 if first else 0.9
            )
            commissioned[key] = amount
            self.cwip[key] += new_capex - amount
        da = {key: 0.0 for key in ("ppe", "rou_assets", "intangibles")}
        for cohort in self.cohorts:
            total = sum(cohort["parts"].values())
            charge = min(total, cohort["annual"] * fraction)
            for key, book in cohort["parts"].items():
                portion = charge * book / total if total else 0
                cohort["parts"][key] -= portion
                da[key] += portion
        for parts, life in (
            (commissioned, shared["legacy_new_asset_life_years"]),
            (
                {"rou_assets": row["new_lease_assets"]},
                shared["new_lease_asset_life_years"],
            ),
        ):
            total = sum(parts.values())
            charge = min(total, total / life * fraction / 2)
            closing = {}
            for key, book in parts.items():
                portion = charge * book / total if total else 0
                closing[key] = book - portion
                da[key] += portion
            self.cohorts.append({"parts": closing, "annual": total / life})
        balances = self.balances()
        checks = {
            "da_allocation_residual": sum(da.values()) - row["da"],
            "asset_allocation_residual": sum(balances.values())
            - row["closing_asset_book_proxy"],
            "cwip_allocation_residual": sum(self.cwip.values())
            - row["closing_cwip_proxy"],
            "commissioning_allocation_residual": sum(commissioned.values())
            - row["commissioned_assets"],
        }
        return balances, da, checks


class LegacyDebtDetail:
    """Split existing gross debt and principal without creating extra funding."""

    def __init__(self, facts, shared, bridge):
        base = facts["legacy_statement_history"]["annuals"][-1]["liabilities"]
        self.leases = base["leases"] - shared["q1_legacy_lease_principal_inr_m"]
        self.revolver = (
            base["revolver"] + bridge["required_opening_liquidity_topup_estimate"]
        )
        self.term = (
            bridge["opening_gross_debt_including_leases_estimate"]
            - self.leases
            - self.revolver
        )

    def balances(self):
        return {
            "term_debt": self.term,
            "revolver": self.revolver,
            "leases": self.leases,
        }

    def advance(self, row, funding, shared, parameters):
        mandatory = funding["parent_scheduled_repayment_inr_m"]
        lease_paid = min(
            self.leases, mandatory * parameters["lease_share_of_scheduled_principal"]
        )
        self.leases -= lease_paid
        remaining = mandatory - lease_paid
        for attr in ("term", "revolver", "leases"):
            paid = min(getattr(self, attr), remaining)
            setattr(self, attr, getattr(self, attr) - paid)
            remaining -= paid
        sweep = funding["parent_cash_sweep_inr_m"]
        for attr in ("revolver", "term", "leases"):
            paid = min(getattr(self, attr), sweep)
            setattr(self, attr, getattr(self, attr) - paid)
            sweep -= paid
        self.leases += row["new_lease_assets"]
        self.revolver += funding["parent_required_new_funding_inr_m"]
        principal = shared["legacy_scheduled_annual_principal_inr_m"]
        current_leases = min(
            self.leases, principal * parameters["lease_share_of_scheduled_principal"]
        )
        current_term = min(self.term, principal - current_leases)
        # Existing parent maturity May 2033 falls in the next twelve months at FY33.
        if row["fiscal_year"] >= 2033:
            current_term = self.term
        split = {
            "current_borrowings": self.revolver + current_term,
            "noncurrent_borrowings": self.term - current_term,
            "current_lease_liabilities": current_leases,
            "noncurrent_lease_liabilities": self.leases - current_leases,
        }
        residual = (
            sum(self.balances().values()) - funding["parent_closing_gross_debt_inr_m"]
        )
        if abs(remaining) > 1e-8 or abs(sweep) > 1e-8:
            raise ValueError("Legacy debt allocation exceeds available principal")
        return self.balances(), split, residual


def _balance_residual(assets, liabilities, equity):
    return sum(assets.values()) - sum(liabilities.values()) - sum(equity.values())


def complete_legacy_statements(partial, legacy, financing, facts, assumptions, bridge):
    """Populate all legacy-only gaps and reconcile each forecast movement."""
    shared = assumptions["shared"]
    policy = assumptions["legacy_statement_policy"]
    p = statement_parameters(facts, shared, policy)
    base = facts["legacy_statement_history"]["annuals"][-1]
    assets, liabilities, equity = [
        deepcopy(base[k]) for k in ("assets", "liabilities", "equity")
    ]
    asset_detail = LegacyAssetDetail(facts, shared, bridge, p)
    debt_detail = LegacyDebtDetail(facts, shared, bridge)
    assets.update(asset_detail.balances())
    assets.update(
        cash=bridge["opening_cash_estimate"],
        current_investments=0.0,
        other_bank_balances=facts["tega_fy2026"]["restricted_deposits"]
        + facts["tega_fy2026"]["unpaid_dividend_bank"],
        investment_in_molycop_at_cost=facts["deal"]["tega_ordinary_contribution_inr_m"],
        joint_venture=assets["joint_venture"]
        + facts["q1_fy2027"]["tega_joint_venture_profit"],
    )
    assets["receivables"] += shared["legacy_june_nwc_increment_inr_m"]
    liabilities.update(debt_detail.balances())
    equity["retained_earnings"] += facts["q1_fy2027"]["tega_net_income"]
    opening_residual = _balance_residual(assets, liabilities, equity)
    opening = {
        "date": "2026-06-30",
        "status": "Estimated legacy-only opening balances; no balancing plug",
        "assets": deepcopy(assets),
        "liabilities": deepcopy(liabilities),
        "equity": deepcopy(equity),
        "balance_sheet_residual_inr_m": opening_residual,
        "note": "Retains the existing June cash/debt bridge, reported Q1 legacy PAT/JV profit, and zero unobserved Q1 OCI/other movements. The residual records their unreconciled opening difference; it is not inserted into any account. The old bridge also excludes Q1 new lease liabilities while the asset schedule includes Q1 ROU additions. Opening data need reconciliation before calling this a balanced statutory forecast.",
    }
    rows = []
    for i, (statement, row, funding) in enumerate(
        zip(partial, legacy, financing, strict=True)
    ):
        statement = deepcopy(statement)
        old_a, old_e = deepcopy(assets), deepcopy(equity)
        allocation, da, checks = asset_detail.advance(row, shared, first=i == 0)
        assets.update(allocation)
        debt, debt_split, debt_check = debt_detail.advance(row, funding, shared, p)
        liabilities.update(debt)
        contract_share = p["contract_assets_share_of_other_operating_assets"]
        provision_share = p["current_provisions_share_of_operating_liabilities"]
        assets.update(
            receivables=row["closing_receivables"],
            inventories=row["closing_inventory"],
            other_current_assets=row["closing_other_operating_current_assets"]
            * (1 - contract_share),
            contract_assets=row["closing_other_operating_current_assets"]
            * contract_share,
            cash=funding["parent_closing_cash_inr_m"],
            joint_venture=funding["parent_joint_venture_closing_book_inr_m"],
        )
        liabilities.update(
            payables=row["closing_payables"],
            current_provisions=row["closing_other_operating_current_liabilities"]
            * provision_share,
            other_current_liabilities=row["closing_other_operating_current_liabilities"]
            * (1 - provision_share),
        )
        income = statement["income"]
        treasury = funding["parent_interest_income_inr_m"]
        misc = funding["parent_miscellaneous_income_inr_m"]
        subsidiary_dividend = funding["tega_share_of_distribution_inr_m"]
        jv_profit = funding["parent_joint_venture_profit_inr_m"]
        jv_dividend = funding["parent_joint_venture_dividend_inr_m"]
        current_tax = funding["parent_cash_tax_total_inr_m"]
        dividends = funding["parent_dividends_paid_inr_m"]
        other_income = treasury + misc + subsidiary_dividend
        pbt = income["operating_earnings_before_tax_proxy"] + other_income + jv_profit
        net_income = pbt - current_tax
        income.update(
            other_income=other_income,
            joint_venture_profit=jv_profit,
            profit_before_tax=pbt,
            current_tax_expense=current_tax,
            deferred_tax_expense=0.0,
            net_income=net_income,
            owners_net_income=net_income,
            eps_inr=net_income / p["shares_million"],
            interest_income=treasury,
            miscellaneous_income=misc,
            subsidiary_dividend_income=subsidiary_dividend,
            other_nonoperating_gains=0.0,
            impairment_expense=0.0,
            other_comprehensive_income=0.0,
            noncontrolling_net_income=0.0,
        )
        equity["retained_earnings"] += net_income - dividends
        bs = statement["balance_sheet"]
        bs.update(
            ppe=assets["ppe"],
            rou_assets=assets["rou_assets"],
            intangibles=assets["intangibles"],
            goodwill=assets["goodwill"],
            investments_and_other_financial_assets=sum(
                assets[k]
                for k in (
                    "joint_venture",
                    "investment_in_molycop_at_cost",
                    "current_investments",
                    "other_bank_balances",
                    "current_loans",
                    "other_current_financial_assets",
                    "other_noncurrent_financial_assets",
                )
            ),
            tax_assets_and_liabilities=sum(
                assets[k]
                for k in (
                    "current_tax_assets",
                    "noncurrent_tax_assets",
                    "deferred_tax_assets",
                )
            )
            - liabilities["current_tax_liabilities"]
            - liabilities["deferred_tax_liabilities"],
            noncurrent_provisions_and_other_liabilities=liabilities[
                "noncurrent_provisions"
            ]
            + liabilities["other_noncurrent_financial_liabilities"],
            share_capital=equity["share_capital"],
            retained_earnings=equity["retained_earnings"],
            other_reserves=equity["other_reserves"],
            noncontrolling_interest=equity["noncontrolling_interest"],
            total_assets=sum(assets.values()),
            total_liabilities=sum(liabilities.values()),
            total_equity=sum(equity.values()),
            balance_sheet_residual=_balance_residual(assets, liabilities, equity),
            **debt_split,
        )
        # Replace inapplicable / ambiguous placeholders with concrete line items.
        for key in (
            "debt_current_noncurrent_split",
            "net_bank_debt_proxy",
            "preference_balance_assumed",
        ):
            bs.pop(key)
        bs.update({f"asset_{key}": value for key, value in assets.items()})
        bs.update({f"liability_{key}": value for key, value in liabilities.items()})
        cf = statement["cash_flow"]
        cfo = (
            pbt
            + row["da"]
            + funding["parent_cash_interest_inr_m"]
            - treasury
            - subsidiary_dividend
            - jv_profit
            - row["delta_nwc"]
            - current_tax
        )
        cfi = -row["cash_capex"] + treasury + jv_dividend + subsidiary_dividend
        cff = (
            funding["parent_required_new_funding_inr_m"]
            - funding["parent_scheduled_repayment_inr_m"]
            - funding["parent_cash_sweep_inr_m"]
            - funding["parent_cash_interest_inr_m"]
            - dividends
        )
        cf.update(
            profit_before_tax=pbt,
            other_noncash_adjustments=0.0,
            joint_venture_profit_reversal=-jv_profit,
            investing_income_reversal=-treasury - subsidiary_dividend,
            income_tax_paid=-current_tax,
            deferred_tax_addback=0.0,
            other_investing_cashflows=0.0,
            interest_received=treasury,
            joint_venture_dividend_received=jv_dividend,
            dividends_to_tega_shareholders=-dividends,
            equity_issuance=0.0,
            fx_effect_on_cash=0.0,
            operating_cash_flow_total=cfo,
            investing_cash_flow_total=cfi,
            financing_cash_flow_total=cff,
            net_change_in_cash=cfo + cfi + cff,
            closing_cash_from_statements=old_a["cash"] + cfo + cfi + cff,
        )
        for key in (
            "statutory_operating_cash_flow_total",
            "statutory_investing_cash_flow_total",
            "statutory_financing_cash_flow_total",
        ):
            cf.pop(key)
        checks.update(
            debt_allocation_residual=debt_check,
            cash_flow_statement_residual=assets["cash"]
            - (old_a["cash"] + cfo + cfi + cff),
            retained_earnings_rollforward_residual=equity["retained_earnings"]
            - (old_e["retained_earnings"] + net_income - dividends),
            balance_sheet_movement_residual=bs["balance_sheet_residual"]
            - opening_residual,
            interest_and_dividend_exclusion_residual=row["fcff"]
            - (
                cfo
                - misc
                + funding["parent_additional_nonoperating_tax_inr_m"]
                - funding["parent_interest_tax_shield_inr_m"]
                - row["cash_capex"]
                - row["new_lease_assets"]
            ),
        )
        statement.update(
            scope="Legacy Tega with Molycop investment at cost and modeled distributions; not statutory consolidated group accounts. FY27 is July-March. Numeric fallback assumptions are not reported facts. Opening discrepancy is disclosed and carried unchanged; no plug.",
            assets=deepcopy(assets),
            liabilities=deepcopy(liabilities),
            equity=deepcopy(equity),
            depreciation_by_account=da,
            checks=checks,
        )
        if any(abs(value) > 1e-7 for value in checks.values()):
            raise ValueError(
                f"Legacy statement movement reconciliation failed: {checks}"
            )
        rows.append(statement)
    register = {
        "scope": policy["scope"],
        "policy": deepcopy(policy),
        "parameters": p,
        "source_ids": ["annual26", "q1_deck"],
        "historical_years": [
            r["fiscal_year"] for r in facts["legacy_statement_history"]["annuals"]
        ],
        "opening_balance_sheet_residual_inr_m": opening_residual,
        "zero_is_assumed_not_reported": True,
        "retained_balance_rule": "Zero forecast movement does not erase an opening asset or liability.",
        "double_counting_rule": "Subsidiary/JV investment balances and dividends are not added to group FCFF or DCF a second time.",
    }
    return rows, opening, register
