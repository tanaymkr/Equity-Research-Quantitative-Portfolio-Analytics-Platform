"""Single group FCFF DCF, ownership-adjusted claims and financing schedules.

All monetary schedules use INR million; per-tonne amounts use INR per tonne.
USD-origin inputs were translated once at the documented fixed exchange rate.
No reported post-acquisition balance sheet is manufactured from forecast plugs.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite

from .drivers import evidence_register
from .statements import linked_statements

REFERENCE_FX_DATE = "2026-09-02"
REFERENCE_FX_INR_PER_USD = 94.97


class AcquisitionInputError(ValueError):
    """Invalid or internally inconsistent acquisition inputs."""


def validate_currency_basis(facts, assumptions):
    """Reject mixed-currency inputs and metadata-only FX changes."""
    basis = facts.get("currency_basis", {})
    if (
        basis != assumptions.get("currency_basis")
        or basis.get("currency") != "INR"
        or basis.get("monetary_unit") != "million"
        or basis.get("fx_date") != REFERENCE_FX_DATE
        or basis.get("inr_per_usd") != REFERENCE_FX_INR_PER_USD
        or facts.get("units", {}).get("molycop") != "INR million"
    ):
        raise AcquisitionInputError(
            "Use matching INR inputs translated at 94.97 on 2026-09-02. "
            "Changing FX metadata alone does not reconvert monetary inputs."
        )

    def reject_old_keys(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if "_usd_m" in key or key in {
                    "fx_inr_per_usd",
                    "closing_funding_fx_inr_per_usd",
                    "molycop_wacc_usd",
                    "molycop_terminal_growth_usd",
                }:
                    raise AcquisitionInputError(f"Mixed-currency input: {key}")
                reject_old_keys(item)
        elif isinstance(value, list):
            for item in value:
                reject_old_keys(item)

    reject_old_keys(facts)
    reject_old_keys(assumptions)


def _finite(value, path="input"):
    if isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _finite(item, f"{path}[{index}]")
    elif isinstance(value, (int, float)) and not isfinite(value):
        raise AcquisitionInputError(f"{path} must be finite")


def _validate(facts, assumptions, case):
    if "tega_fy2026" not in facts:
        raise AcquisitionInputError(
            "Load the complete FY26 statements with load_acquisition_facts first"
        )
    validate_currency_basis(facts, assumptions)
    _finite(facts)
    _finite(assumptions)
    if facts["ticker"] != "NSE:TEGA":
        raise AcquisitionInputError("This case requires NSE:TEGA")
    if facts["valuation_date"] != "2026-06-30":
        raise AcquisitionInputError(
            "Rebuild the opening bridge before changing its date"
        )
    if case not in assumptions["scenarios"]:
        raise AcquisitionInputError(f"Unknown scenario: {case}")
    years = assumptions["years"]
    if years != list(range(2027, 2027 + len(years))) or len(years) < 2:
        raise AcquisitionInputError("Use consecutive fiscal years beginning FY2027")
    a, s = assumptions["scenarios"][case], assumptions["shared"]
    history_snapshot = assumptions.get("forecast_policy", {}).get(
        "historical_driver_calculations"
    )
    if history_snapshot is not None and history_snapshot != facts.get(
        "historical_drivers"
    ):
        raise AcquisitionInputError(
            "Historical sources changed; refresh the forecast driver review before running"
        )
    mix = s.get("legacy_operating_cost_mix", {})
    if (
        set(mix)
        != {
            "materials",
            "inventory_change_expense",
            "employee_expense",
            "other_expense",
        }
        or abs(sum(mix.values()) - 1) > 1e-9
    ):
        raise AcquisitionInputError(
            "Legacy operating cost shares must identify four components and sum to one"
        )
    for key, values in a.items():
        if isinstance(values, list) and key != "source_ids":
            if len(values) != len(years):
                raise AcquisitionInputError(
                    f"{key}: one value per forecast year required"
                )
            if "growth" in key and any(v <= -1 for v in values):
                raise AcquisitionInputError(f"{key}: growth must exceed -100%")
            if "margin" in key and any(not 0 <= v <= 1 for v in values):
                raise AcquisitionInputError(
                    f"{key}: margin must be between zero and one"
                )
            if any(
                word in key for word in ("capex", "synergies", "cost_inr", "cross_sell")
            ) and any(v < 0 for v in values):
                raise AcquisitionInputError(f"{key} cannot be negative")
    if assumptions.get("valuation_method") != "single_attributable_group_dcf":
        raise AcquisitionInputError("Use the single group DCF assumptions file")
    retired = {
        "legacy_wacc_inr",
        "legacy_terminal_growth_inr",
        "legacy_terminal_roic",
        "molycop_discount_rate",
        "molycop_terminal_growth",
        "molycop_terminal_roic",
    }
    if retired.intersection(a):
        raise AcquisitionInputError("Separate business DCF assumptions are retired")
    w, g, r = (
        a["group_wacc_inr"],
        a["group_terminal_growth_inr"],
        a["group_terminal_roic"],
    )
    if not 0 <= g < w < 1 or not g < r <= 1:
        raise AcquisitionInputError(
            "Group DCF: require 0 <= g < WACC and g < ROIC <= 1"
        )
    contributions = [
        facts["deal"][k]
        for k in (
            "tega_ordinary_contribution_inr_m",
            "apollo_ordinary_contribution_inr_m",
        )
    ]
    if min(contributions) < 0 or sum(contributions) <= 0:
        raise AcquisitionInputError(
            "Ordinary contributions must establish valid ownership"
        )
    for key in (
        "legacy_new_asset_life_years",
        "molycop_new_asset_life_years",
        "molycop_ppa_intangible_life_years",
        "new_lease_asset_life_years",
        "molycop_existing_asset_remaining_life_years",
    ):
        if s[key] <= 0:
            raise AcquisitionInputError(f"{key} must be positive")
    for key in (
        "q1_legacy_cash_capex_fraction_of_fy27",
        "legacy_opening_commissioned_q1_capex_fraction",
        "molycop_ppa_tax_deductible_fraction",
        "molycop_cash_retention_for_debt_fraction",
        "earned_income_tax_rate_legacy",
        "earned_income_tax_rate_molycop",
    ):
        if not 0 <= s[key] <= 1:
            raise AcquisitionInputError(f"{key} must be between zero and one")
    for key in (
        "preference_fair_value_inr_m",
        "molycop_other_claims_inr_m",
        "legacy_annual_new_lease_assets_inr_m",
        "molycop_annual_new_lease_assets_inr_m",
        "legacy_minimum_cash_inr_m",
        "preference_assumed_pik_rate",
        "preference_assumed_cash_rate_after_deferral",
    ):
        if s[key] < 0:
            raise AcquisitionInputError(f"{key} cannot be negative")
    if facts["tega_fy2026"]["shares"] <= 0:
        raise AcquisitionInputError("Issued shares must be positive")
    if not 0 <= a["earnout_inr_m"] <= facts["deal"]["earnout_max_inr_m"]:
        raise AcquisitionInputError("Earnout exceeds the disclosed range")
    earn_date = date.fromisoformat(a["earnout_payment_date"])
    if (
        not date(2026, 6, 30)
        < earn_date
        <= date.fromisoformat(facts["deal"]["earnout_deadline"])
    ):
        raise AcquisitionInputError(
            "Earnout date is outside the disclosed payment window"
        )
    if a["molycop_first_year_total_ebitda_growth"] <= -1:
        raise AcquisitionInputError("First-year EBITDA growth must exceed -100%")


def opening_bridge(facts, assumptions):
    """Roll reported March liquidity to June; estimates remain explicitly labeled."""
    h, q, d = facts["tega_fy2026"], facts["q1_fy2027"], facts["deal"]
    s = assumptions["shared"]
    liquid = (
        h["cash"]
        + h["bank_deposits"]
        - h["restricted_deposits"]
        + h["current_investments"]
    )
    contribution = d["tega_ordinary_contribution_inr_m"]
    # Historical bridge must be identical across operating scenarios.
    capex = (
        facts["management_guidance"]["tega_fy2027_capex_inr_m_approx"]
        * s["q1_legacy_cash_capex_fraction_of_fy27"]
    )
    repayment = (
        s["q1_legacy_lease_principal_inr_m"] + s["q1_legacy_other_principal_inr_m"]
    )
    cash = (
        liquid
        + d["parent_acquisition_loan_inr_m"]
        + s["q1_legacy_operating_cash_after_interest_tax_inr_m"]
        - contribution
        - capex
        - q["tega_transaction_expense"]
        - repayment
        + s["q1_legacy_other_cash_movement_inr_m"]
    )
    gross = (
        h["borrowings_noncurrent"]
        + h["borrowings_current"]
        + h["lease_liabilities"]
        + d["parent_acquisition_loan_inr_m"]
        - repayment
    )
    topup = max(s["legacy_minimum_cash_inr_m"] - cash, 0.0)
    return {
        "status": "Estimated June bridge; not a disclosed June cash/debt breakdown",
        "march_unrestricted_liquidity": liquid,
        "new_parent_loan": d["parent_acquisition_loan_inr_m"],
        "tega_equity_contribution_cash_outflow": contribution,
        "q1_operating_cash_estimate": s[
            "q1_legacy_operating_cash_after_interest_tax_inr_m"
        ],
        "q1_cash_capex_estimate": capex,
        "q1_transaction_fee_cash_assumption": q["tega_transaction_expense"],
        "q1_principal_estimate": repayment,
        "other_cash_movement_estimate": s["q1_legacy_other_cash_movement_inr_m"],
        "cash_before_liquidity_topup": cash,
        "required_opening_liquidity_topup_estimate": topup,
        "opening_cash_estimate": cash + topup,
        "opening_gross_debt_including_leases_estimate": gross + topup,
        "opening_net_debt_including_leases_estimate": gross - cash,
        "jv_book_value_proxy": h["jv_investment"],
        "investment_property_book_value_proxy": h["investment_property"],
    }


class _Assets:
    """Straight-line cohorts and a separate construction-in-progress roll-forward."""

    def __init__(
        self, book, annual_charge, cwip=0.0, ppa_book=0.0, ppa_life=15.0, land=0.0
    ):
        if book < 0 or annual_charge < 0:
            raise AcquisitionInputError(
                "Asset life implies negative existing D&A/book value"
            )
        self.cohorts = [{"book": book, "annual": annual_charge, "ppa": False}]
        if ppa_book:
            self.cohorts.append(
                {"book": ppa_book, "annual": ppa_book / ppa_life, "ppa": True}
            )
        self.cwip = cwip
        self.land = land

    def advance(self, fraction, capex, leases, life, lease_life, first=False):
        opening_depreciable = sum(c["book"] for c in self.cohorts)
        opening_cwip = self.cwip
        commissioned = opening_cwip * (0.8 if first else 1.0) + capex * (
            0.3 if first else 0.9
        )
        self.cwip += capex - commissioned
        da, ppa_da = 0.0, 0.0
        for cohort in self.cohorts:
            charge = min(cohort["book"], cohort["annual"] * fraction)
            cohort["book"] -= charge
            da += charge
            if cohort["ppa"]:
                ppa_da += charge
        for addition, asset_life in ((commissioned, life), (leases, lease_life)):
            charge = min(addition, addition / asset_life * fraction / 2)
            self.cohorts.append(
                {
                    "book": addition - charge,
                    "annual": addition / asset_life,
                    "ppa": False,
                }
            )
            da += charge
        closing = sum(c["book"] for c in self.cohorts) + self.cwip + self.land
        residual = closing - (
            opening_depreciable + opening_cwip + self.land + capex + leases - da
        )
        return {
            "opening_depreciable_book_proxy": opening_depreciable,
            "opening_cwip_proxy": opening_cwip,
            "nondepreciable_land": self.land,
            "commissioned_assets": commissioned,
            "cash_capex": capex,
            "new_lease_assets": leases,
            "da": da,
            "ppa_amortization": ppa_da,
            "closing_cwip_proxy": self.cwip,
            "closing_asset_book_proxy": closing,
            "asset_rollforward_residual": residual,
        }


def _group_cashflows(legacy, molycop, ownership, legacy_tax, molycop_tax):
    """Combine operating cash flows before a single discounting calculation.

    These are proportionate economic cash flows, not statutory consolidated
    statements. Molycop cash flows and its senior claims use the same ownership.
    """
    amount_keys = (
        "revenue",
        "operating_ebitda",
        "integration_cash_cost",
        "ebit",
        "unlevered_cash_tax",
        "closing_nwc",
        "delta_nwc",
        "fcff",
        "opening_depreciable_book_proxy",
        "opening_cwip_proxy",
        "nondepreciable_land",
        "commissioned_assets",
        "cash_capex",
        "new_lease_assets",
        "da",
        "ppa_amortization",
        "closing_cwip_proxy",
        "closing_asset_book_proxy",
        "asset_rollforward_residual",
    )
    result = []
    for lrow, mrow in zip(legacy, molycop, strict=True):
        timing = ("fiscal_year", "period_years", "discount_years")
        if any(lrow[k] != mrow[k] for k in timing):
            raise AcquisitionInputError(
                "Align business cash-flow periods before combining"
            )
        row = {k: lrow[k] for k in timing}
        row.update({k: lrow[k] + ownership * mrow[k] for k in amount_keys})
        legacy_normalized_ebit = lrow["ebit"] + lrow["ppa_amortization"]
        molycop_normalized_ebit = mrow["ebit"] + mrow["ppa_amortization"]
        # Keep separate cash-tax rates and floors; do not invent cross-border loss relief.
        row["normalized_terminal_nopat"] = (
            legacy_normalized_ebit
            - max(legacy_normalized_ebit, 0) * legacy_tax
            + ownership
            * (molycop_normalized_ebit - max(molycop_normalized_ebit, 0) * molycop_tax)
        )
        row.update(
            {
                "legacy_fcff": lrow["fcff"],
                "molycop_fcff_before_ownership": mrow["fcff"],
                "combined_fcff_before_ownership": lrow["fcff"] + mrow["fcff"],
                "noncontrolling_fcff_excluded": (1 - ownership) * mrow["fcff"],
                "ownership_fcff_residual": row["fcff"]
                - lrow["fcff"]
                - ownership * mrow["fcff"],
                "fcff_identity_residual": row["fcff"]
                - (
                    row["ebit"]
                    - row["integration_cash_cost"]
                    - row["unlevered_cash_tax"]
                    + row["da"]
                    - row["cash_capex"]
                    - row["new_lease_assets"]
                    - row["delta_nwc"]
                ),
            }
        )
        result.append(row)
    return result


def _dcf(rows, wacc, growth, roic):
    """Discount the combined attributable stream once, with one terminal value."""
    pv = sum(row["fcff"] / (1 + wacc) ** row["discount_years"] for row in rows)
    last = rows[-1]
    nopat = last["normalized_terminal_nopat"] * (1 + growth)
    reinvestment = max(nopat, 0) * growth / roic
    terminal_fcff = nopat - reinvestment
    tv = terminal_fcff / (wacc - growth)
    terminal_pv = tv / (1 + wacc) ** last["discount_years"]
    return {
        "scope": "Tega-attributable group cash flows; proportionate enterprise value",
        "wacc": wacc,
        "terminal_growth": growth,
        "terminal_roic": roic,
        "pv_forecast_fcff": pv,
        "terminal_nopat": nopat,
        "terminal_reinvestment": reinvestment,
        "terminal_fcff": terminal_fcff,
        "terminal_value": tv,
        "pv_terminal_value": terminal_pv,
        "enterprise_value": pv + terminal_pv,
        "terminal_share_of_ev": terminal_pv / (pv + terminal_pv)
        if pv + terminal_pv
        else None,
    }


def _cashflow(
    revenue, ebitda, integration, nwc, previous_nwc, assets, tax, ppa_tax_fraction
):
    ebit = ebitda - assets["da"]
    taxable = ebit - integration + assets["ppa_amortization"] * (1 - ppa_tax_fraction)
    cash_tax = max(taxable, 0) * tax
    delta_nwc = nwc - previous_nwc
    fcff = (
        ebit
        - integration
        - cash_tax
        + assets["da"]
        - assets["cash_capex"]
        - assets["new_lease_assets"]
        - delta_nwc
    )
    return {
        "revenue": revenue,
        "operating_ebitda": ebitda,
        "integration_cash_cost": integration,
        "ebit": ebit,
        "unlevered_cash_tax": cash_tax,
        "closing_nwc": nwc,
        "delta_nwc": delta_nwc,
        "fcff": fcff,
        **assets,
    }


def _financing(legacy, molycop, bridge, facts, s, a, ownership):
    """Illustrative liquidity checks; financing cash flows never reduce FCFF twice."""
    parent_debt = bridge["opening_gross_debt_including_leases_estimate"]
    parent_cash = bridge["opening_cash_estimate"]
    legacy_fy27_cost = a.get("legacy_fy27_finance_cost_inr_m")
    legacy_remaining_interest = (
        legacy_fy27_cost - facts["q1_fy2027"]["tega_finance_cost"]
        if legacy_fy27_cost is not None
        else None
    )
    parent_rate = (
        legacy_remaining_interest / (parent_debt * 0.75)
        if legacy_remaining_interest is not None and parent_debt > 0
        else s["legacy_debt_interest_rate"]
    )
    if legacy_remaining_interest is not None and legacy_remaining_interest < 0:
        raise AcquisitionInputError("FY27 finance cost cannot be below actual Q1")
    mc_net = facts["q1_fy2027"]["molycop_net_debt_inr_m"]
    # June 1 issue accretes for one modeled month before this opening date.
    pref = facts["deal"]["apollo_preference_issue_inr_m"] * (
        1 + s["preference_assumed_pik_rate"]
    ) ** (1 / 12)
    elapsed = 1 / 12
    deferral = facts["deal"]["preference_initial_cash_deferral_years"]
    result = []
    previous_date = date(2026, 6, 30)
    earn_date = date.fromisoformat(a["earnout_payment_date"])
    for i, (lrow, mrow) in enumerate(zip(legacy, molycop, strict=True)):
        fraction = lrow["period_years"]
        end = date(lrow["fiscal_year"], 3, 31)
        earnout = a["earnout_inr_m"] if previous_date < earn_date <= end else 0.0
        pik_years = min(fraction, max(deferral - elapsed, 0.0))
        pik = pref * ((1 + s["preference_assumed_pik_rate"]) ** pik_years - 1)
        pref_cash = (
            (pref + pik)
            * s["preference_assumed_cash_rate_after_deferral"]
            * (fraction - pik_years)
        )
        mc_interest = (
            s["molycop_fy27_ten_month_cash_interest_inr_m"]
            - facts["q1_fy2027"]["molycop_finance_cost_inr_m"]
            if i == 0
            else max(mc_net, 0) * s["molycop_net_debt_interest_rate_proxy"]
        )
        if mc_interest < 0:
            raise AcquisitionInputError(
                "Molycop ten-month interest is below actual June expense"
            )
        # Cap interest tax relief at operating cash tax: no invented tax refunds.
        mc_tax_shield = min(
            mrow["unlevered_cash_tax"],
            mc_interest * s["earned_income_tax_rate_molycop"],
        )
        lease_principal = s["molycop_annual_lease_principal_inr_m"] * fraction
        mc_cash_available = (
            mrow["fcff"]
            + mrow["new_lease_assets"]
            - lease_principal
            - mc_interest
            + mc_tax_shield
            - earnout
            - pref_cash
        )
        mandatory = (
            s["molycop_fy27_ten_month_scheduled_principal_inr_m"] * 0.9
            if i == 0
            else s["molycop_later_annual_scheduled_principal_inr_m"]
        )
        paydown = min(
            max(mc_net, 0),
            max(
                mandatory,
                max(mc_cash_available, 0)
                * s["molycop_cash_retention_for_debt_fraction"],
            ),
        )
        new_funding = max(paydown - mc_cash_available, 0.0)
        distribution = max(mc_cash_available - paydown, 0.0)
        closing_mc_net = mc_net - paydown + new_funding
        parent_receipt = distribution * ownership
        parent_interest = (
            legacy_remaining_interest
            if i == 0 and legacy_remaining_interest is not None
            else parent_debt * parent_rate * fraction
        )
        parent_tax_shield = min(
            lrow["unlevered_cash_tax"],
            parent_interest * s["earned_income_tax_rate_legacy"],
        )
        parent_before_debt_service = (
            parent_cash
            + lrow["fcff"]
            + lrow["new_lease_assets"]
            - parent_interest
            + parent_tax_shield
            + parent_receipt
        )
        parent_mandatory = min(
            parent_debt,
            s.get(
                "legacy_fy27_remaining_scheduled_principal_inr_m",
                s["legacy_scheduled_annual_principal_inr_m"] * fraction,
            )
            if i == 0
            else s["legacy_scheduled_annual_principal_inr_m"],
        )
        parent_draw = max(
            s["legacy_minimum_cash_inr_m"]
            + parent_mandatory
            - parent_before_debt_service,
            0.0,
        )
        sweep = min(
            max(
                parent_before_debt_service
                - parent_mandatory
                - s["legacy_minimum_cash_inr_m"],
                0.0,
            ),
            parent_debt - parent_mandatory,
        )
        closing_parent_debt = (
            parent_debt
            + lrow["new_lease_assets"]
            + parent_draw
            - parent_mandatory
            - sweep
        )
        closing_parent_cash = (
            parent_before_debt_service + parent_draw - parent_mandatory - sweep
        )
        result.append(
            {
                "fiscal_year": lrow["fiscal_year"],
                "molycop_opening_net_debt_inr_m": mc_net,
                "molycop_cash_interest_inr_m": mc_interest,
                "molycop_interest_tax_shield_inr_m": mc_tax_shield,
                "molycop_cash_available_inr_m": mc_cash_available,
                "earnout_cash_inr_m": earnout,
                "molycop_debt_paydown_inr_m": paydown,
                "molycop_required_new_funding_inr_m": new_funding,
                "molycop_new_lease_liability_inr_m": mrow["new_lease_assets"],
                "molycop_lease_principal_estimate_inr_m": lease_principal,
                "molycop_closing_net_bank_debt_inr_m": closing_mc_net,
                "molycop_ordinary_distribution_inr_m": distribution,
                "tega_share_of_distribution_inr_m": parent_receipt,
                "preference_opening_assumed_balance_inr_m": pref,
                "preference_non_cash_pik_inr_m": pik,
                "preference_cash_return_inr_m": pref_cash,
                "preference_closing_assumed_balance_inr_m": pref + pik,
                "parent_opening_gross_debt_inr_m": parent_debt,
                "parent_cash_interest_inr_m": parent_interest,
                "parent_interest_tax_shield_inr_m": parent_tax_shield,
                "parent_implied_annual_interest_rate": parent_rate,
                "parent_opening_cash_inr_m": parent_cash,
                "parent_scheduled_repayment_inr_m": parent_mandatory,
                "parent_cash_sweep_inr_m": sweep,
                "parent_new_lease_liability_inr_m": lrow["new_lease_assets"],
                "parent_required_new_funding_inr_m": parent_draw,
                "parent_closing_gross_debt_inr_m": closing_parent_debt,
                "parent_closing_cash_inr_m": closing_parent_cash,
                "parent_cash_rollforward_residual": closing_parent_cash
                - (
                    parent_cash
                    + lrow["fcff"]
                    + lrow["new_lease_assets"]
                    - parent_interest
                    + parent_tax_shield
                    + parent_receipt
                    + parent_draw
                    - parent_mandatory
                    - sweep
                ),
                "parent_debt_rollforward_residual": closing_parent_debt
                - (
                    parent_debt
                    + lrow["new_lease_assets"]
                    + parent_draw
                    - parent_mandatory
                    - sweep
                ),
                "molycop_net_debt_rollforward_residual": closing_mc_net
                - (mc_net + new_funding - paydown),
                "molycop_abl_maturity_review": previous_date < date(2031, 6, 1) <= end,
                "molycop_term_loan_maturity_review": previous_date
                < date(2033, 6, 1)
                <= end,
                "parent_acquisition_loan_maturity_review": previous_date
                < date(2033, 5, 31)
                <= end,
            }
        )
        parent_cash, parent_debt, mc_net, pref = (
            closing_parent_cash,
            closing_parent_debt,
            closing_mc_net,
            pref + pik,
        )
        elapsed += fraction
        previous_date = end
    return result


def build_acquisition_model(facts: dict, assumptions: dict, scenario="base") -> dict:
    """Build a reproducible, explicitly provisional post-acquisition valuation."""
    _validate(facts, assumptions, scenario)
    a, s = deepcopy(assumptions["scenarios"][scenario]), assumptions["shared"]
    h, q, d, mh = (
        facts["tega_fy2026"],
        facts["q1_fy2027"],
        facts["deal"],
        facts["molycop_history"],
    )
    fx = facts["currency_basis"]["inr_per_usd"]
    ownership = d["tega_ordinary_contribution_inr_m"] / (
        d["tega_ordinary_contribution_inr_m"] + d["apollo_ordinary_contribution_inr_m"]
    )
    bridge = opening_bridge(facts, assumptions)
    capex_q1 = bridge["q1_cash_capex_estimate"]
    commission_q1 = capex_q1 * s["legacy_opening_commissioned_q1_capex_fraction"]
    legacy_book = (
        h["ppe"]
        + h["right_of_use_assets"]
        + h["intangible_assets"]
        + commission_q1
        + s["legacy_annual_new_lease_assets_inr_m"] / 4
        - q["tega_da"]
    )
    legacy_cwip = h["cwip"] + h["intangible_development"] + capex_q1 - commission_q1
    land = h.get("nondepreciable_land", 0.0)
    la = _Assets(legacy_book - land, q["tega_da"] * 4, legacy_cwip, land=land)
    ppa_annual = (
        d["provisional_intangibles_inr_m"] / s["molycop_ppa_intangible_life_years"]
    )
    mc_existing_da = q["molycop_da_inr_m"] * 12 - ppa_annual
    ma = _Assets(
        mc_existing_da * s["molycop_existing_asset_remaining_life_years"],
        mc_existing_da,
        ppa_book=d["provisional_intangibles_inr_m"] - ppa_annual / 12,
        ppa_life=s["molycop_ppa_intangible_life_years"] - 1 / 12,
    )
    # Full-year 2026 revenue is not reported: infer using FY25 price per tonne.
    mc_price = mh["fy2025_revenue_inr_m"] / mh["fy2025_volume_m_tonnes"]
    mc_volume = mh["fy2026_volume_m_tonnes"]
    inferred_mc_revenue = mc_volume * mc_price
    previous_mc_nwc = inferred_mc_revenue * a["molycop_opening_nwc_revenue_fraction"]
    previous_legacy_nwc = (
        h["receivables"]
        + h["inventory"]
        - h["payables"]
        + h.get("other_operating_current_assets", 0.0)
        - h.get("other_operating_current_liabilities", 0.0)
        + s["legacy_june_nwc_increment_inr_m"]
    )
    consumables = h["consumables_gross_revenue"] - h["intersegment_revenue"]
    equipment = h["equipment_revenue"]
    mc_core_per_tonne = None
    legacy, molycop = [], []
    for i, fiscal_year in enumerate(assumptions["years"]):
        fraction = 0.75 if i == 0 else 1.0
        discount_years = (date(fiscal_year, 3, 31) - date(2026, 6, 30)).days / 365
        consumables *= 1 + a["legacy_consumables_growth"][i]
        equipment *= 1 + a["equipment_growth"][i]
        cross_sell = a["legacy_incremental_cross_sell_revenue_inr_m"][i]
        legacy_annual_revenue = consumables + equipment + cross_sell
        legacy_annual_ebitda = (consumables + cross_sell) * a[
            "consumables_operating_ebitda_margin"
        ][i] + equipment * a["equipment_operating_ebitda_margin"][i]
        lrev = legacy_annual_revenue - (q["tega_revenue"] if i == 0 else 0)
        lebitda = legacy_annual_ebitda - (
            q["tega_adjusted_ebitda_including_other_income"] - q["tega_other_income"]
            if i == 0
            else 0
        )
        lcapex = (
            a["legacy_capex_fy27_inr_m"] - capex_q1
            if i == 0
            else legacy_annual_revenue * a["legacy_later_capex_revenue_fraction"]
        )
        llease = (
            s["legacy_annual_new_lease_assets_inr_m"]
            * fraction
            * legacy_annual_revenue
            / h["revenue"]
        )
        las = la.advance(
            fraction,
            lcapex,
            llease,
            s["legacy_new_asset_life_years"],
            s["new_lease_asset_life_years"],
            first=i == 0,
        )
        receivables = legacy_annual_revenue * a["legacy_receivable_days"] / 365
        inventory = legacy_annual_revenue * a["legacy_inventory_revenue_fraction"]
        payables = legacy_annual_revenue * a["legacy_payable_revenue_fraction"]
        other_assets = legacy_annual_revenue * a.get(
            "legacy_other_operating_current_assets_revenue_fraction", 0.0
        )
        other_liabilities = legacy_annual_revenue * a.get(
            "legacy_other_operating_current_liabilities_revenue_fraction", 0.0
        )
        lnwc = receivables + inventory + other_assets - payables - other_liabilities
        lr = _cashflow(
            lrev,
            lebitda,
            0,
            lnwc,
            previous_legacy_nwc,
            las,
            s["earned_income_tax_rate_legacy"],
            1.0,
        )
        lr.update(
            {
                "fiscal_year": fiscal_year,
                "period_years": fraction,
                "discount_years": discount_years,
                "full_fiscal_year_revenue": legacy_annual_revenue,
                "full_fiscal_year_operating_ebitda": legacy_annual_ebitda,
                "consumables_full_year_revenue": consumables,
                "equipment_full_year_revenue": equipment,
                "cross_sell_full_year_revenue": cross_sell,
                "closing_receivables": receivables,
                "closing_inventory": inventory,
                "closing_payables": payables,
                "closing_other_operating_current_assets": other_assets,
                "closing_other_operating_current_liabilities": other_liabilities,
            }
        )
        legacy.append(lr)
        mc_volume *= 1 + a["molycop_volume_growth"][i]
        mc_price *= 1 + a["molycop_price_growth"][i]
        annual_mc_revenue = mc_volume * mc_price
        synergy = a["molycop_cost_synergies_inr_m"][i]
        if i == 0:
            full_owned_ebitda = (
                (
                    mh["fy2026_ebitda_inr_m"]
                    + s["molycop_fy2026_ebitda_operating_adjustment_inr_m"]
                )
                * (1 + a["molycop_first_year_total_ebitda_growth"])
                * 10
                / 12
            )
            mc_core_per_tonne = (full_owned_ebitda - synergy) / (mc_volume * 10 / 12)
            full_owned_revenue = annual_mc_revenue * 10 / 12
            mrev = full_owned_revenue - q["molycop_revenue_inr_m"]
            mebitda = full_owned_ebitda - q["molycop_operating_ebitda_inr_m"]
            mcapex = a["molycop_capex_fy27_ten_month_inr_m"] * 9 / 10
        else:
            mc_core_per_tonne *= 1 + a["molycop_core_ebitda_per_tonne_growth"][i]
            full_owned_revenue = mrev = annual_mc_revenue
            full_owned_ebitda = mebitda = mc_volume * mc_core_per_tonne + synergy
            mcapex = a["molycop_later_annual_capex_inr_m"][i]
            if fiscal_year >= a.get("molycop_capex_revenue_link_start_year", 9999):
                mcapex = (
                    molycop[-1]["cash_capex"]
                    * annual_mc_revenue
                    / molycop[-1]["annual_revenue_run_rate"]
                )
        if min(lrev, mrev, lcapex, mcapex, mebitda, mc_core_per_tonne) < 0:
            raise AcquisitionInputError(
                "Forecast is below actual YTD or implies negative core earnings/capex"
            )
        mlease = (
            s["molycop_annual_new_lease_assets_inr_m"]
            * fraction
            * annual_mc_revenue
            / inferred_mc_revenue
        )
        mas = ma.advance(
            fraction,
            mcapex,
            mlease,
            s["molycop_new_asset_life_years"],
            s["new_lease_asset_life_years"],
            first=False,
        )
        mnwc = annual_mc_revenue * a["molycop_forecast_nwc_revenue_fraction"]
        mr = _cashflow(
            mrev,
            mebitda,
            a["molycop_integration_cash_cost_inr_m"][i],
            mnwc,
            previous_mc_nwc,
            mas,
            s["earned_income_tax_rate_molycop"],
            s["molycop_ppa_tax_deductible_fraction"],
        )
        mr.update(
            {
                "fiscal_year": fiscal_year,
                "period_years": fraction,
                "discount_years": discount_years,
                "owned_fiscal_year_revenue": full_owned_revenue,
                "owned_fiscal_year_operating_ebitda": full_owned_ebitda,
                "annual_volume_run_rate_m_tonnes": mc_volume,
                "annual_revenue_run_rate": annual_mc_revenue,
                "price_per_tonne_inr_proxy": mc_price,
                "core_ebitda_per_tonne_inr_proxy": mc_core_per_tonne,
                "cost_synergies": synergy,
                "owned_months_in_fiscal_year": 10 if i == 0 else 12,
            }
        )
        molycop.append(mr)
        previous_legacy_nwc, previous_mc_nwc = lnwc, mnwc
    group = _group_cashflows(
        legacy,
        molycop,
        ownership,
        s["earned_income_tax_rate_legacy"],
        s["earned_income_tax_rate_molycop"],
    )
    group_value = _dcf(
        group,
        a["group_wacc_inr"],
        a["group_terminal_growth_inr"],
        a["group_terminal_roic"],
    )
    earn_years = (
        date.fromisoformat(a["earnout_payment_date"]) - date(2026, 6, 30)
    ).days / 365
    earn_pv = a["earnout_inr_m"] / (1 + a["group_wacc_inr"]) ** earn_years
    molycop_full_claims = (
        q["molycop_net_debt_inr_m"]
        + s["preference_fair_value_inr_m"]
        + earn_pv
        + s["molycop_other_claims_inr_m"]
    )
    attributable_claims = (
        bridge["opening_net_debt_including_leases_estimate"]
        + ownership * molycop_full_claims
    )
    nonoperating = h["jv_investment"] + h["investment_property"]
    raw_equity = group_value["enterprise_value"] - attributable_claims + nonoperating
    equity = max(raw_equity, 0.0)
    shares_m = h["shares"] / 1_000_000
    issue = facts["pending_equity_issue"]
    issue_equity = max(
        raw_equity + issue["gross_proceeds_inr_m"] - s["pending_issue_expenses_inr_m"],
        0.0,
    )
    financing = _financing(legacy, molycop, bridge, facts, s, a, ownership)
    statements = linked_statements(legacy, molycop, financing, s)
    warnings = [
        "Provisional model: June 30 valuation using information published through September 11, 2026; not a September spot-price target or point-in-time backtest.",
        "Legacy June cash/CFO/capex and Molycop working capital are estimates; detailed post-close balance sheet not obtained.",
        "Preference fair value and 12% PIK schedule are assumptions; contractual return and exit terms require confirmation.",
        "Molycop FY2026 revenue is inferred from volume and FY2025 realization; it is not reported revenue.",
        "Molycop FY2026 adjusted EBITDA is treated as operating EBITDA; full-year other income and the comparable ten-month earnings pattern are unavailable.",
        "Purchase accounting, intangible lives, tax deductibility, other senior claims and subsidiary minority/JV scope remain provisional.",
        "One group discount rate, terminal growth and ROIC apply to the combined stream. Initial values carry over former legacy assumptions as provisional group choices; they are not calibrated group WACCs.",
        "Ownership-adjusted economic DCF: include 100% legacy and Tega's share of Molycop cash flows and senior claims. These are not statutory consolidated financial statements.",
        "One pooled equity calculation does not value separate subsidiary default options or limited-liability ring-fencing. It may understate downside equity where Molycop shortfalls cannot reach the parent; contractual support remains unresolved.",
        "All USD-origin inputs use INR94.97 per USD at the September 2, 2026 market close. June 30 remains the valuation date; this is a later-date constant-currency restatement. Reported INR actuals are unchanged.",
        "Debt schedules estimate liquidity; they do not certify bank covenants, refinancing availability, preference exit rights or a statutory balanced forecast.",
        "September 20 assumption review: management > verifiable comparable consensus > historical trend. No public group consensus WACC or detailed Molycop statement consensus was verified. Remaining proxies are explicitly unresolved.",
        "Linked statement schedules are partial. Missing post-close balances and accounting items stay null; there is no balancing equity plug or verified statutory PAT/EPS forecast.",
    ]
    if raw_equity < 0:
        warnings.append(
            "Combined modeled equity is below zero and is floored once at zero; this is not a conclusion about legal debt recourse or an immediate cash shortfall."
        )
    if any(
        r["parent_required_new_funding_inr_m"] > 0.01
        or r["molycop_required_new_funding_inr_m"] > 0.01
        for r in financing
    ):
        warnings.append(
            "Forecast needs additional funding; availability and pricing are not confirmed."
        )
    checks = {
        "fy26_reported_balance_sheet_residual": h["assets"]
        - h["liabilities"]
        - h["equity"],
        "q1_segment_revenue_residual": q["group_revenue"]
        - q["tega_revenue"]
        - q["molycop_revenue_inr_m"],
        "q1_pat_attribution_residual": q["group_pat"] - q["owners_pat"] - q["nci_pat"],
        "first_year_legacy_revenue_tie": legacy[0]["revenue"]
        + q["tega_revenue"]
        - legacy[0]["full_fiscal_year_revenue"],
        "first_year_molycop_revenue_tie": molycop[0]["revenue"]
        + q["molycop_revenue_inr_m"]
        - molycop[0]["owned_fiscal_year_revenue"],
        "first_year_molycop_ebitda_tie": molycop[0]["operating_ebitda"]
        + q["molycop_operating_ebitda_inr_m"]
        - molycop[0]["owned_fiscal_year_operating_ebitda"],
        "max_asset_rollforward_residual": max(
            abs(r["asset_rollforward_residual"]) for r in legacy + molycop
        ),
        "max_group_ownership_fcff_residual": max(
            abs(r["ownership_fcff_residual"]) for r in group
        ),
        "max_group_fcff_identity_residual": max(
            abs(r["fcff_identity_residual"]) for r in group
        ),
        "equity_bridge_residual": raw_equity
        - (group_value["enterprise_value"] - attributable_claims + nonoperating),
        "max_parent_cash_rollforward_residual": max(
            abs(r["parent_cash_rollforward_residual"]) for r in financing
        ),
        "max_linked_operating_cashflow_residual": max(
            abs(r["cash_flow"]["fcff_reconciliation_residual"])
            for rows in statements.values()
            for r in rows
        ),
    }
    if any(abs(value) > 0.02 for value in checks.values()):
        raise AcquisitionInputError(f"Reconciliation failed: {checks}")
    return {
        "company": facts["company"],
        "ticker": facts["ticker"],
        "scenario": scenario,
        "valuation_date": facts["valuation_date"],
        "information_cutoff": facts["information_cutoff"],
        "reported_history": deepcopy(facts.get("reported_history")),
        "currency_basis": deepcopy(facts["currency_basis"]),
        "monetary_unit": "INR million",
        "status": facts["status"],
        "valuation_method": "single_attributable_group_dcf",
        "warnings": warnings,
        "opening_bridge_inr_m": bridge,
        "inferred_molycop_fy2026_revenue_inr_m": inferred_mc_revenue,
        "legacy_forecast_inr_m": legacy,
        "molycop_forecast_inr_m": molycop,
        "group_forecast_inr_m": group,
        "group_dcf_inr_m": group_value,
        "equity_bridge": {
            "molycop_ordinary_ownership": ownership,
            "fx_inr_per_usd": fx,
            "group_enterprise_value_inr_m": group_value["enterprise_value"],
            "legacy_net_debt_inr_m": bridge[
                "opening_net_debt_including_leases_estimate"
            ],
            "molycop_net_debt_full_inr_m": q["molycop_net_debt_inr_m"],
            "molycop_net_debt_attributable_inr_m": ownership
            * q["molycop_net_debt_inr_m"],
            "preference_fair_value_full_inr_m": s["preference_fair_value_inr_m"],
            "preference_fair_value_attributable_inr_m": ownership
            * s["preference_fair_value_inr_m"],
            "earnout_present_value_full_inr_m": earn_pv,
            "earnout_present_value_attributable_inr_m": ownership * earn_pv,
            "other_claims_full_inr_m": s["molycop_other_claims_inr_m"],
            "other_claims_attributable_inr_m": ownership
            * s["molycop_other_claims_inr_m"],
            "total_attributable_claims_inr_m": attributable_claims,
            "nonoperating_assets_inr_m": nonoperating,
            "raw_tega_equity_inr_m": raw_equity,
            "tega_equity_inr_m": equity,
            "issued_shares": h["shares"],
            "value_per_share_inr": equity / shares_m,
            "pending_issue_pro_forma_shares": h["shares"] + issue["additional_shares"],
            "pending_issue_pro_forma_value_per_share_inr": issue_equity
            / (shares_m + issue["additional_shares"] / 1_000_000),
        },
        "financing_schedule": financing,
        "linked_statements_inr_m": statements,
        "forecast_evidence": evidence_register(assumptions),
        "historical_drivers": deepcopy(facts.get("historical_drivers")),
        "guidance_comparisons": {
            "fy27_legacy_finance_cost_inr_m": financing[0]["parent_cash_interest_inr_m"]
            + q["tega_finance_cost"],
            "fy27_molycop_interest_plus_principal_inr_m": s[
                "molycop_fy27_ten_month_cash_interest_inr_m"
            ]
            + s["molycop_fy27_ten_month_scheduled_principal_inr_m"],
            "fy27_full_group_operating_ebitda_margin_proxy": (
                legacy[0]["full_fiscal_year_operating_ebitda"]
                + molycop[0]["owned_fiscal_year_operating_ebitda"]
            )
            / (
                legacy[0]["full_fiscal_year_revenue"]
                + molycop[0]["owned_fiscal_year_revenue"]
            ),
            "management_group_adjusted_ebitda_margin_approx": facts[
                "management_guidance"
            ].get("consolidated_adjusted_ebitda_margin_approx"),
            "margin_definition_note": "Model operating margin excludes other income. Management adjusted EBITDA may include it. Compare as a diagnostic; never plug earnings to force 15%.",
            "consensus_review": deepcopy(facts.get("consensus_review")),
        },
        "checks": checks,
        "scenario_assumptions": a,
        "shared_assumptions": deepcopy(s),
    }
