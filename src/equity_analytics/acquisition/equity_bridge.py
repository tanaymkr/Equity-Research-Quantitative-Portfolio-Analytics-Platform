"""Full-consolidation EV to parent common equity: deduct each claim once."""


def diluted_shares(config, reported_shares):
    s = config["shares"]
    for key in (
        "pre_november_2025",
        "november_2025_issue",
        "follow_on_issue",
        "other_dilutive_shares",
    ):
        if not isinstance(s[key], int) or s[key] < 0:
            raise ValueError(f"{key} must be a nonnegative whole share count")
    issued = s["pre_november_2025"] + s["november_2025_issue"]
    if issued != reported_shares:
        raise ValueError("Share roll-forward does not match FY26 issued shares")
    follow = s["follow_on_issue"] if s["include_follow_on"] else 0
    total = issued + follow + s["other_dilutive_shares"]
    if total <= 0 or s["issue_price_inr"] <= 0:
        raise ValueError("Positive diluted shares and issue price required")
    cash = (
        0
        if s["follow_on_cash_already_in_opening"]
        else follow * s["issue_price_inr"] / 1e6
    )
    return {
        "pre_november_2025_shares": s["pre_november_2025"],
        "november_2025_issue_shares": s["november_2025_issue"],
        "issued_shares": issued,
        "follow_on_shares_included": follow,
        "other_dilutive_shares": s["other_dilutive_shares"],
        "diluted_shares": total,
        "incremental_issue_cash_inr_m": cash,
        "status": s["_note"],
    }


def build_equity_bridge(
    group_ev, molycop_ev, opening, facts, assumptions, earnout_pv, ownership
):
    """NCI values common equity AFTER full subsidiary senior claims.

    The Molycop EV is an auxiliary standalone value for NCI only. It is never
    added to combined EV, which comes solely from the consolidated group DCF.
    """
    c, s = assumptions["pro_forma"], assumptions["shared"]
    sh = diluted_shares(c, facts["tega_fy2026"]["shares"])
    mc_debt = facts["q1_fy2027"]["molycop_net_debt_inr_m"]
    legacy_debt = opening["opening_net_debt_including_leases_estimate"]
    pref = s["preference_fair_value_inr_m"]
    other = s["molycop_other_claims_inr_m"]
    mc_raw_common = molycop_ev - mc_debt - pref - earnout_pv - other
    nci = (1 - ownership) * max(mc_raw_common, 0.0)
    nonop = (
        facts["tega_fy2026"]["jv_investment"]
        + facts["tega_fy2026"]["investment_property"]
    )
    issue_cash = sh["incremental_issue_cash_inr_m"]
    issue_cost = (
        s["pending_issue_expenses_inr_m"] if sh["follow_on_shares_included"] else 0
    )
    net_debt = legacy_debt + mc_debt - issue_cash + issue_cost
    deductions = net_debt + pref + earnout_pv + other + nci
    raw = group_ev - deductions + nonop
    return {
        "molycop_ordinary_ownership": ownership,
        "minority_fraction": 1 - ownership,
        "fx_inr_per_usd": c["fx_inr_per_usd"],
        "group_enterprise_value_inr_m": group_ev,
        "legacy_net_debt_inr_m": legacy_debt,
        "parent_new_term_debt_already_included_inr_m": opening["new_parent_loan"],
        "molycop_net_debt_full_inr_m": mc_debt,
        "molycop_preference_funded_paydown_already_included_inr_m": facts["deal"][
            "apollo_preference_issue_inr_m"
        ],
        "net_debt_before_pro_forma_issue_inr_m": legacy_debt + mc_debt,
        "follow_on_issue_cash_added_inr_m": issue_cash,
        "follow_on_issue_expenses_inr_m": issue_cost,
        "consolidated_net_debt_inr_m": net_debt,
        "preference_fair_value_full_inr_m": pref,
        "earnout_present_value_full_inr_m": earnout_pv,
        "other_claims_full_inr_m": other,
        "molycop_standalone_ev_for_nci_inr_m": molycop_ev,
        "molycop_raw_common_equity_inr_m": mc_raw_common,
        "molycop_common_equity_inr_m": max(mc_raw_common, 0.0),
        "minority_interest_inr_m": nci,
        "total_bridge_deductions_inr_m": deductions,
        "nonoperating_assets_inr_m": nonop,
        "raw_tega_equity_inr_m": raw,
        "tega_equity_inr_m": max(raw, 0.0),
        **sh,
        "value_per_share_inr": max(raw, 0.0) / (sh["diluted_shares"] / 1e6),
        "bridge_residual_inr_m": raw
        - (group_ev - net_debt - pref - earnout_pv - other - nci + nonop),
        "debt_basis": "June post-close Molycop net debt excludes preferences and already follows preference-funded refinancing. Parent June debt already includes INR15000m acquisition loan. Neither flow is applied twice.",
        "nci_basis": "Standalone Molycop operating EV at its own WACC, less full net bank debt, preference fair value, earnout PV and other claims; ordinary equity floored at zero before applying NCI. Subsidiary support/recourse not established.",
    }
