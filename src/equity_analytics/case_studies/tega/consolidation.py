"""100% pro-forma consolidation, explicit eliminations and linked FCFF.

Supporting business schedules remain separately auditable. They are consolidated
before valuation. Acquisition accounting allocations are provisional, not audited
statutory accounts. Fixed unallocated OPENING balances reconcile to reported June
control totals; they never change to force a forecast balance sheet to balance.
"""

from copy import deepcopy


def consolidate_operating(legacy, molycop, legacy_tax, molycop_tax, config):
    rows = []
    amount_keys = (
        "revenue",
        "operating_ebitda",
        "integration_cash_cost",
        "ebit",
        "unlevered_cash_tax",
        "closing_nwc",
        "delta_nwc",
        "cash_capex",
        "new_lease_assets",
        "da",
        "ppa_amortization",
        "closing_asset_book_proxy",
    )
    elim = config["consolidation"]
    # ASSUMPTION: no unrealised intercompany profit. Equal sales/cost elimination
    # leaves group EBIT unchanged. Nonzero profit requires a sourced tax model.
    if elim["intercompany_revenue_inr_m"] != elim["intercompany_operating_cost_inr_m"]:
        raise ValueError(
            "Intercompany trading elimination must have zero profit until tax basis is supplied"
        )
    for l, m in zip(legacy, molycop, strict=True):
        timing = ("fiscal_year", "period_years", "discount_years")
        if any(l[k] != m[k] for k in timing):
            raise ValueError("Forecast periods must align")
        r = {k: l[k] for k in timing}
        r.update({k: l[k] + m[k] for k in amount_keys})
        r["intercompany_revenue_eliminated"] = (
            elim["intercompany_revenue_inr_m"] * l["period_years"]
        )
        r["revenue"] -= r["intercompany_revenue_eliminated"]
        r["operating_expense_total"] = r["revenue"] - r["operating_ebitda"]
        r["nopat"] = r["ebit"] - r["integration_cash_cost"] - r["unlevered_cash_tax"]
        # FCFF is built from consolidated operating lines, never minority-scaled.
        r["fcff"] = (
            r["nopat"]
            + r["da"]
            - r["cash_capex"]
            - r["new_lease_assets"]
            - r["delta_nwc"]
        )
        r["legacy_fcff"] = l["fcff"]
        r["molycop_fcff_before_ownership"] = m["fcff"]
        r["consolidation_fcff_residual"] = r["fcff"] - l["fcff"] - m["fcff"]
        r["fcff_identity_residual"] = r["fcff"] - (
            r["nopat"]
            + r["da"]
            - r["cash_capex"]
            - r["new_lease_assets"]
            - r["delta_nwc"]
        )
        # Preserve separate jurisdictional tax floors; no cross-border loss offset.
        ln = l["ebit"] + l["ppa_amortization"]
        mn = m["ebit"] + m["ppa_amortization"]
        r["normalized_terminal_nopat"] = (
            ln - max(ln, 0) * legacy_tax + mn - max(mn, 0) * molycop_tax
        )
        rows.append(r)
    return rows


def consolidate_statements(
    legacy_statements,
    legacy_opening,
    molycop,
    funding,
    operating,
    facts,
    assumptions,
    ownership,
    shares,
):
    c = assumptions["pro_forma"]["consolidation"]
    s = assumptions["shared"]
    q = facts["q1_fy2027"]
    fx = assumptions["pro_forma"]["fx_inr_per_usd"]
    nci_fraction = 1 - ownership
    ar, inv, ap = (
        c[k]
        for k in (
            "molycop_receivables_to_nwc",
            "molycop_inventory_to_nwc",
            "molycop_payables_to_nwc",
        )
    )
    if min(ar, inv, ap) < 0 or abs(ar + inv - ap - 1) > 1e-9:
        raise ValueError("Molycop working-capital allocation must reconcile to NWC")
    if c["molycop_opening_cash_inr_m"] < 0:
        raise ValueError("Opening cash cannot be negative")
    lease = c["molycop_opening_lease_liability_usd_m"] * fx
    if not 0 <= lease <= s["molycop_other_claims_inr_m"]:
        raise ValueError(
            "Lease allocation must fit within existing other-claims reserve"
        )
    cash = c["molycop_opening_cash_inr_m"]
    net = funding[0]["molycop_opening_net_debt_inr_m"]
    fixed = (
        molycop[0]["opening_depreciable_book_proxy"] + molycop[0]["opening_cwip_proxy"]
    )
    nwc = molycop[0]["closing_nwc"] - molycop[0]["delta_nwc"]
    pref = funding[0]["preference_opening_assumed_balance_inr_m"]
    case = assumptions["scenarios"][assumptions["_active_scenario"]]
    earn = case[
        "earnout_inr_m"
    ]  # ASSUMPTION: face-value book liability, separate from DCF fair-value PV.
    goodwill = facts["deal"]["reported_provisional_goodwill_inr_m"]
    investment = legacy_opening["assets"]["investment_in_molycop_at_cost"]
    eliminated_balance = c["intercompany_receivable_payable_inr_m"]
    if eliminated_balance < 0:
        raise ValueError("Intercompany balances cannot be negative")

    # Explicit gross-up uses a labeled constant minimum cash proxy. If net debt
    # turns negative, surplus appears in cash instead of negative gross debt.
    def mc_cash(net):
        return cash + max(-net, 0)

    def mc_bank(net):
        return cash + max(net, 0)

    def components(lassets, lliabs, fixed, nwc, net, lease, pref, earn):
        assets = deepcopy(lassets)
        assets.pop("investment_in_molycop_at_cost", None)
        assets["receivables"] += ar * nwc - eliminated_balance
        assets["inventories"] += inv * nwc
        assets["cash"] += mc_cash(net)
        assets["molycop_fixed_assets_proxy"] = fixed
        assets["goodwill"] += goodwill
        liabilities = deepcopy(lliabs)
        liabilities["payables"] += ap * nwc - eliminated_balance
        liabilities["molycop_bank_debt_proxy"] = mc_bank(net)
        liabilities["molycop_lease_liability_proxy"] = lease
        liabilities["apollo_preference_book_proxy"] = pref
        liabilities["molycop_earnout_book_proxy"] = earn
        liabilities["other_acquisition_claims_proxy"] = (
            s["molycop_other_claims_inr_m"]
            - c["molycop_opening_lease_liability_usd_m"] * fx
        )
        return assets, liabilities

    opening_assets, opening_liabs = components(
        legacy_opening["assets"],
        legacy_opening["liabilities"],
        fixed,
        nwc,
        net,
        lease,
        pref,
        earn,
    )
    # These are IDENTIFIED missing allocations within published control totals.
    # They are frozen once, not recomputed as forecast plugs. Detailed Molycop
    # balances/PPA are required to replace them with specific accounts.
    unallocated_assets = q["group_assets"] - sum(opening_assets.values())
    unallocated_liabs = q["group_liabilities"] - sum(opening_liabs.values())
    opening_assets["unallocated_acquired_assets_opening_only"] = unallocated_assets
    opening_liabs["unallocated_acquired_liabilities_opening_only"] = unallocated_liabs
    group_equity = q["group_assets"] - q["group_liabilities"]
    nci_book = c["molycop_opening_nci_book_inr_m"]
    if nci_book is None:
        nci_book = facts["deal"]["apollo_ordinary_contribution_inr_m"]
    owners_book = group_equity - nci_book
    issue_cash = shares["incremental_issue_cash_inr_m"]
    issue_cost = (
        s["pending_issue_expenses_inr_m"] if shares["follow_on_shares_included"] else 0
    )
    # Pro-forma overlay is retained cash, not assumed invested or earning interest.
    issue_net = issue_cash - issue_cost
    opening_assets["pro_forma_follow_on_cash"] = issue_net
    owners_book += issue_net
    opening = {
        "date": facts["valuation_date"],
        "assets": opening_assets,
        "liabilities": opening_liabs,
        "owners_equity": owners_book,
        "noncontrolling_equity": nci_book,
        "total_assets": sum(opening_assets.values()),
        "total_liabilities": sum(opening_liabs.values()),
        "total_equity": owners_book + nci_book,
        "legacy_unresolved_opening_gap": legacy_opening["balance_sheet_residual_inr_m"],
        "allocation_note": c["_note"],
        "investment_eliminated": investment,
        "control_total_note": "Reported June group totals anchor the acquisition opening only. Unallocated residual accounts are disclosed and frozen. This does not resolve the separate legacy June gap or validate PPA.",
    }
    rows = []
    previous_group_cash = opening_assets["cash"] + issue_net
    for l, m, f, o in zip(legacy_statements, molycop, funding, operating, strict=True):
        li, lc = l["income"], l["cash_flow"]
        distribution = f["tega_share_of_distribution_inr_m"]
        mc_tax = m["unlevered_cash_tax"] - f["molycop_interest_tax_shield_inr_m"]
        preference_charge = (
            f["preference_non_cash_pik_inr_m"] + f["preference_cash_return_inr_m"]
        )
        # ASSUMPTION: Molycop other income, JV profit and deferred-tax movement
        # zero; preference return treated as a non-deductible economic charge.
        mc_profit = (
            m["ebit"]
            - m["integration_cash_cost"]
            - f["molycop_cash_interest_inr_m"]
            - mc_tax
            - preference_charge
        )
        income = {
            "revenue": o["revenue"],
            "operating_expense_total": o["operating_expense_total"],
            "operating_ebitda": o["operating_ebitda"],
            "depreciation_amortisation": o["da"],
            "ebit_before_integration": o["ebit"],
            "integration_expense": o["integration_cash_cost"],
            "ebit_after_integration": o["ebit"] - o["integration_cash_cost"],
            "bank_and_lease_finance_cost": li["finance_cost_cash_proxy"]
            + f["molycop_cash_interest_inr_m"],
            "preference_return_economic_charge": preference_charge,
            "other_income_after_dividend_elimination": li["other_income"]
            - distribution,
            "joint_venture_profit": li["joint_venture_profit"],
            "intercompany_dividend_eliminated": distribution,
            "current_tax_proxy": li["current_tax_expense"] + mc_tax,
            "deferred_tax_expense_assumed": li["deferred_tax_expense"],
        }
        income["profit_before_tax_proxy"] = (
            income["ebit_after_integration"]
            - income["bank_and_lease_finance_cost"]
            - preference_charge
            + income["other_income_after_dividend_elimination"]
            + income["joint_venture_profit"]
        )
        income["net_income_proxy"] = (
            income["profit_before_tax_proxy"]
            - income["current_tax_proxy"]
            - income["deferred_tax_expense_assumed"]
        )
        income["noncontrolling_profit_proxy"] = nci_fraction * mc_profit
        income["owners_net_income_proxy"] = (
            income["net_income_proxy"] - income["noncontrolling_profit_proxy"]
        )
        income["pro_forma_eps_inr"] = income["owners_net_income_proxy"] / (
            shares["diluted_shares"] / 1e6
        )
        lease += m["new_lease_assets"] - f["molycop_lease_principal_estimate_inr_m"]
        if lease < 0:
            raise ValueError("Molycop lease payments exceed modeled lease liability")
        earn -= f["earnout_cash_inr_m"]
        net = f["molycop_closing_net_bank_debt_inr_m"]
        assets, liabilities = components(
            l["assets"],
            l["liabilities"],
            m["closing_asset_book_proxy"],
            m["closing_nwc"],
            net,
            lease,
            f["preference_closing_assumed_balance_inr_m"],
            earn,
        )
        assets["unallocated_acquired_assets_opening_only"] = unallocated_assets
        assets["pro_forma_follow_on_cash"] = issue_net
        liabilities["unallocated_acquired_liabilities_opening_only"] = unallocated_liabs
        external_nci_dividend = nci_fraction * f["molycop_ordinary_distribution_inr_m"]
        owners_book += (
            income["owners_net_income_proxy"] + lc["dividends_to_tega_shareholders"]
        )
        nci_book += income["noncontrolling_profit_proxy"] - external_nci_dividend
        bs = {
            "total_assets": sum(assets.values()),
            "total_liabilities": sum(liabilities.values()),
            "owners_equity": owners_book,
            "noncontrolling_equity": nci_book,
            "total_equity": owners_book + nci_book,
            "consolidated_cash": assets["cash"] + issue_net,
            "net_operating_working_capital": o["closing_nwc"],
            "investment_in_molycop_after_elimination": 0.0,
        }
        bs["balance_sheet_residual"] = (
            bs["total_assets"] - bs["total_liabilities"] - bs["total_equity"]
        )
        mc_cfo = (
            m["operating_ebitda"] - m["integration_cash_cost"] - mc_tax - m["delta_nwc"]
        )
        cf = {
            "operating_cash_flow_proxy": lc["operating_cash_flow_total"] + mc_cfo,
            "investing_cash_flow_proxy": lc["investing_cash_flow_total"]
            - distribution
            - m["cash_capex"],
            "financing_cash_flow_proxy": lc["financing_cash_flow_total"]
            - f["molycop_cash_interest_inr_m"]
            - f["molycop_debt_paydown_inr_m"]
            - f["molycop_lease_principal_estimate_inr_m"]
            + f["molycop_required_new_funding_inr_m"]
            - external_nci_dividend
            - f["preference_cash_return_inr_m"]
            - f["earnout_cash_inr_m"],
            "cash_dividend_eliminated": distribution,
            "external_nci_dividend": external_nci_dividend,
            "noncash_preference_accretion": f["preference_non_cash_pik_inr_m"],
            "opening_cash": previous_group_cash,
            "closing_cash": bs["consolidated_cash"],
        }
        cf["net_change_in_cash"] = sum(
            cf[k]
            for k in (
                "operating_cash_flow_proxy",
                "investing_cash_flow_proxy",
                "financing_cash_flow_proxy",
            )
        )
        cf["cash_rollforward_residual"] = (
            cf["closing_cash"] - cf["opening_cash"] - cf["net_change_in_cash"]
        )
        previous_group_cash = cf["closing_cash"]
        rows.append(
            {
                "fiscal_year": m["fiscal_year"],
                "period_years": m["period_years"],
                "scope": "Economic pro-forma forecast; FY27 July-March future period; proxies and unallocated opening balances explicitly disclosed.",
                "income": income,
                "balance_sheet": bs,
                "assets": assets,
                "liabilities": liabilities,
                "cash_flow": cf,
                "fcff": {
                    k: o[k]
                    for k in (
                        "ebit",
                        "integration_cash_cost",
                        "unlevered_cash_tax",
                        "nopat",
                        "da",
                        "cash_capex",
                        "new_lease_assets",
                        "delta_nwc",
                        "fcff",
                    )
                },
            }
        )
    return {
        "opening": opening,
        "forecast": rows,
        "assumption_note": "Molycop nonoperating income and deferred tax zero; preference treated as economic finance charge without tax shield. Net income is a modeled proxy, not sourced Molycop PAT. Detailed statutory classification/PPA remains unresolved.",
    }


def fiscal_year_income_view(consolidated, facts, diluted_share_count):
    """Add reported elapsed Q1 to future FY27; never send actual cash flows to DCF.

    June preference charge is not separately disclosed: retained inside reported
    Q1 finance cost, with zero additional reclassification, avoiding double count.
    Full-year cash-flow totals are not invented without a reported Q1 CF statement.
    """
    q = facts["q1_fy2027"]
    rows = []
    for i, row in enumerate(consolidated["forecast"]):
        inc = deepcopy(row["income"])
        if i == 0:
            ebitda = (
                q["tega_adjusted_ebitda_including_other_income"]
                - q["tega_other_income"]
                + q["molycop_operating_ebitda_inr_m"]
            )
            da = q["tega_da"] + q["molycop_da_inr_m"]
            finance = q["tega_finance_cost"] + q["molycop_finance_cost_inr_m"]
            other = q["tega_other_income"] + q["molycop_other_income_inr_m"]
            pbt = (
                ebitda
                - da
                - q["group_transaction_expense"]
                - finance
                + other
                + q["tega_joint_venture_profit"]
            )
            actual = {
                "revenue": q["group_revenue"],
                "operating_expense_total": q["group_revenue"] - ebitda,
                "operating_ebitda": ebitda,
                "depreciation_amortisation": da,
                "ebit_before_integration": ebitda - da,
                "integration_expense": q["group_transaction_expense"],
                "ebit_after_integration": ebitda - da - q["group_transaction_expense"],
                "bank_and_lease_finance_cost": finance,
                "preference_return_economic_charge": 0.0,
                "other_income_after_dividend_elimination": other,
                "joint_venture_profit": q["tega_joint_venture_profit"],
                "intercompany_dividend_eliminated": 0.0,
                "profit_before_tax_proxy": pbt,
                "current_tax_proxy": pbt - q["group_pat"],
                "deferred_tax_expense_assumed": 0.0,
                "net_income_proxy": q["group_pat"],
                "noncontrolling_profit_proxy": q["nci_pat"],
                "owners_net_income_proxy": q["owners_pat"],
            }
            for k, v in actual.items():
                inc[k] += v
            # Pro-forma denominator is intentionally not statutory weighted-average EPS.
            inc["pro_forma_eps_inr"] = inc["owners_net_income_proxy"] / (
                diluted_share_count / 1e6
            )

        rows.append(
            {
                "fiscal_year": row["fiscal_year"],
                "tega_months": 12,
                "molycop_months": 10 if i == 0 else 12,
                "income": inc,
            }
        )
    return {
        "rows": rows,
        "note": "FY27 combines reported Q1 (Tega three months; Molycop June only) with nine future months. Actual Q1 total tax is shown in current-tax proxy without a deferred split; preference charge stays in reported finance cost. Full-year CF unavailable without Q1 CF. All annual EPS shown is pro-forma, not statutory weighted-average EPS.",
    }
