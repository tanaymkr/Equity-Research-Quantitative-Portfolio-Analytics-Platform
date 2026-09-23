"""Self-contained HTML and Markdown reports; no third-party dependencies."""

from __future__ import annotations

import json
from copy import deepcopy
from html import escape
from pathlib import Path

from equity_analytics.forecasting.reporting import write_historical_reports

from .engine import build_acquisition_model


def _n(value):
    return "Unresolved" if value is None else f"{value:,.2f}"


def _table(headers, rows, html=False):
    if html:
        head = "".join(f"<th>{escape(str(v))}</th>" for v in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
            for row in rows
        )
        return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        + ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    )


def _legacy_statement_tables(result):
    """Display accounting lines once; retain all diagnostic aliases in model.json."""
    rows = result["linked_statements_inr_m"]["legacy"]
    flow_headers = ["Line item"] + [
        f"FY{r['fiscal_year']}" + (" Jul-Mar" if r["period_years"] < 1 else "")
        for r in rows
    ]
    income_keys = (
        "revenue",
        "materials",
        "inventory_change_expense",
        "employee_expense",
        "other_expense",
        "operating_expense_total",
        "operating_ebitda",
        "depreciation_amortisation",
        "integration_expense_cash_proxy",
        "operating_profit_after_integration",
        "finance_cost_cash_proxy",
        "interest_income",
        "miscellaneous_income",
        "subsidiary_dividend_income",
        "other_nonoperating_gains",
        "other_income",
        "joint_venture_profit",
        "profit_before_tax",
        "current_tax_expense",
        "deferred_tax_expense",
        "net_income",
        "owners_net_income",
        "eps_inr",
        "other_comprehensive_income",
    )
    yield (
        "Legacy income statement: modeled INR million; EPS INR/share",
        flow_headers,
        [
            [k.replace("_", " ")] + [_n(r["income"][k]) for r in rows]
            for k in income_keys
        ],
    )
    bs_rows = []
    for key in rows[0]["assets"]:
        bs_rows.append(
            ["Asset: " + key.replace("_", " ")] + [_n(r["assets"][key]) for r in rows]
        )
    bs_rows.append(
        ["TOTAL ASSETS"] + [_n(r["balance_sheet"]["total_assets"]) for r in rows]
    )
    for key in (
        "current_borrowings",
        "noncurrent_borrowings",
        "current_lease_liabilities",
        "noncurrent_lease_liabilities",
    ):
        bs_rows.append(
            ["Liability: " + key.replace("_", " ")]
            + [_n(r["balance_sheet"][key]) for r in rows]
        )
    for key in rows[0]["liabilities"]:
        if key not in ("term_debt", "revolver", "leases"):
            bs_rows.append(
                ["Liability: " + key.replace("_", " ")]
                + [_n(r["liabilities"][key]) for r in rows]
            )
    bs_rows.append(
        ["TOTAL LIABILITIES"]
        + [_n(r["balance_sheet"]["total_liabilities"]) for r in rows]
    )
    for key in rows[0]["equity"]:
        bs_rows.append(
            ["Equity: " + key.replace("_", " ")] + [_n(r["equity"][key]) for r in rows]
        )
    bs_rows.append(
        ["TOTAL EQUITY"] + [_n(r["balance_sheet"]["total_equity"]) for r in rows]
    )
    bs_rows.append(
        ["OPENING RECONCILIATION GAP CARRIED — not a plug"]
        + [_n(r["balance_sheet"]["balance_sheet_residual"]) for r in rows]
    )
    yield (
        "Legacy balance sheet: estimated INR million; Molycop investment at cost",
        ["Line item"] + [f"31 Mar {r['fiscal_year']}" for r in rows],
        bs_rows,
    )
    cash_keys = (
        "profit_before_tax",
        "da_addback",
        "interest_addback",
        "joint_venture_profit_reversal",
        "investing_income_reversal",
        "other_noncash_adjustments",
        "change_in_operating_working_capital",
        "income_tax_paid",
        "operating_cash_flow_total",
        "cash_capex",
        "interest_received",
        "joint_venture_dividend_received",
        "subsidiary_distribution_received",
        "other_investing_cashflows",
        "investing_cash_flow_total",
        "required_new_borrowing",
        "debt_and_lease_principal_paid",
        "cash_interest_proxy",
        "dividends_to_tega_shareholders",
        "equity_issuance",
        "financing_cash_flow_total",
        "net_change_in_cash",
        "fx_effect_on_cash",
        "opening_cash_proxy",
        "closing_cash_proxy",
        "new_lease_assets_noncash",
    )
    yield (
        "Legacy cash flow statement: modeled INR million",
        flow_headers,
        [
            [k.replace("_", " ")] + [_n(r["cash_flow"][k]) for r in rows]
            for k in cash_keys
        ],
    )
    yield (
        "Legacy D&A allocation from the existing asset schedule (INR million)",
        flow_headers,
        [
            [key.replace("_", " ")]
            + [_n(r["depreciation_by_account"][key]) for r in rows]
            for key in rows[0]["depreciation_by_account"]
        ],
    )
    yield (
        "Legacy statement movement checks (INR million); the opening gap is disclosed separately",
        flow_headers,
        [
            [key.replace("_", " ")] + [_n(r["checks"][key]) for r in rows]
            for key in rows[0]["checks"]
        ],
    )


def sensitivities(facts, assumptions):
    """Change one parameter at a time, preserving the full valuation waterfall."""
    definitions = [
        ("Group WACC", "scenario", "group_wacc_inr", [0.105, 0.12, 0.14]),
        (
            "Group terminal growth",
            "scenario",
            "group_terminal_growth_inr",
            [0.03, 0.04, 0.045],
        ),
        ("Group terminal ROIC", "scenario", "group_terminal_roic", [0.13, 0.16, 0.18]),
        (
            "Preference current fair value (INR m)",
            "shared",
            "preference_fair_value_inr_m",
            [25641.9, 31340.1, 37988.0],
        ),
        (
            "Other claims reserve (INR m)",
            "shared",
            "molycop_other_claims_inr_m",
            [0.0, 4748.5, 9497.0],
        ),
        (
            "Earnout cash payment (INR m)",
            "scenario",
            "earnout_inr_m",
            [0.0, 5698.2, 11396.4],
        ),
        (
            "Legacy Q1 cash flow estimate (INR m)",
            "shared",
            "q1_legacy_operating_cash_after_interest_tax_inr_m",
            [0, 600, 1200],
        ),
        (
            "Molycop forecast NWC / revenue",
            "scenario",
            "molycop_forecast_nwc_revenue_fraction",
            [0.18, 0.20, 0.23],
        ),
        (
            "Molycop FY26 EBITDA operating adjustment (INR m)",
            "shared",
            "molycop_fy2026_ebitda_operating_adjustment_inr_m",
            [-949.7, 0.0, 949.7],
        ),
    ]
    rows = []
    for label, scope, key, values in definitions:
        for value in values:
            changed = deepcopy(assumptions)
            target = (
                changed["shared"] if scope == "shared" else changed["scenarios"]["base"]
            )
            target[key] = value
            result = build_acquisition_model(facts, changed)
            rows.append(
                {
                    "parameter": label,
                    "input": value,
                    "value_per_share_inr": result["equity_bridge"][
                        "value_per_share_inr"
                    ],
                }
            )
    # FY2027 EBITDA is calibrated to ten-month guidance, which already includes
    # savings. Vary only later savings to isolate the run-rate interpretation.
    for multiplier in (0.0, 0.5, 1.0):
        changed = deepcopy(assumptions)
        base = changed["scenarios"]["base"]
        savings = base["molycop_cost_synergies_inr_m"]
        base["molycop_cost_synergies_inr_m"] = [savings[0]] + [
            value * multiplier for value in savings[1:]
        ]
        result = build_acquisition_model(facts, changed)
        rows.append(
            {
                "parameter": "Cost savings after FY2027 / base ramp",
                "input": multiplier,
                "value_per_share_inr": result["equity_bridge"]["value_per_share_inr"],
            }
        )
    return rows


def _case_tables(result):
    b = result["equity_bridge"]
    v = result["group_dcf_inr_m"]
    a = result["scenario_assumptions"]
    years = [r["fiscal_year"] for r in result["legacy_forecast_inr_m"]]
    yield (
        "Approved revenue growth (underlying annual rates)",
        ["Business"] + [f"FY{y}" for y in years],
        [
            ["Legacy consumables"]
            + [f"{x:.1%}" for x in a["legacy_consumables_growth"]],
            ["Equipment"] + [f"{x:.1%}" for x in a["equipment_growth"]],
            ["Molycop"]
            + [
                f"{(1 + x) * (1 + y) - 1:.1%}"
                for x, y in zip(
                    a["molycop_volume_growth"], a["molycop_price_growth"], strict=True
                )
            ],
        ],
    )
    yield (
        "One group DCF: cash flows attributable to Tega (INR million)",
        [
            "FY end",
            "Legacy FCFF",
            "Molycop FCFF (100%)",
            "Less: minority FCFF",
            "FCFF discounted",
            "Discount years",
            "PV of FCFF",
        ],
        [
            [
                r["fiscal_year"],
                _n(r["legacy_fcff"]),
                _n(r["molycop_fcff_before_ownership"]),
                _n(r["noncontrolling_fcff_excluded"]),
                _n(r["fcff"]),
                f"{r['discount_years']:.4f}",
                _n(r["fcff"] / (1 + v["wacc"]) ** r["discount_years"]),
            ]
            for r in result["group_forecast_inr_m"]
        ],
    )
    yield (
        "Single group terminal value and enterprise value (INR million)",
        [
            "Group WACC",
            "Terminal growth",
            "Terminal ROIC",
            "Terminal NOPAT",
            "Terminal reinvestment",
            "Terminal FCFF",
            "PV forecast FCFF",
            "PV terminal value",
            "Attributable enterprise value",
        ],
        [
            [
                f"{v['wacc']:.2%}",
                f"{v['terminal_growth']:.2%}",
                f"{v['terminal_roic']:.2%}",
                *[
                    _n(v[k])
                    for k in (
                        "terminal_nopat",
                        "terminal_reinvestment",
                        "terminal_fcff",
                        "pv_forecast_fcff",
                        "pv_terminal_value",
                        "enterprise_value",
                    )
                ],
            ]
        ],
    )
    rows = [
        [
            "Group enterprise value, attributable basis",
            _n(b["group_enterprise_value_inr_m"]),
            "INR m",
        ],
        [
            "Less: legacy/parent net debt (100%)",
            _n(b["legacy_net_debt_inr_m"]),
            "INR m",
        ],
        [
            "Less: attributable Molycop net debt",
            _n(b["molycop_net_debt_attributable_inr_m"]),
            "INR m",
        ],
        [
            "Less: attributable preference claim",
            _n(b["preference_fair_value_attributable_inr_m"]),
            "INR m",
        ],
        [
            "Less: attributable earnout present value",
            _n(b["earnout_present_value_attributable_inr_m"]),
            "INR m",
        ],
        [
            "Less: attributable other claims",
            _n(b["other_claims_attributable_inr_m"]),
            "INR m",
        ],
        [
            "Add: legacy JV/property proxies",
            _n(b["nonoperating_assets_inr_m"]),
            "INR m",
        ],
        [
            "Tega equity before aggregate zero floor",
            _n(b["raw_tega_equity_inr_m"]),
            "INR m",
        ],
        ["Issued shares", f"{b['issued_shares']:,}", "shares"],
        ["Provisional scenario value", _n(b["value_per_share_inr"]), "INR / share"],
        [
            "If proposed Apollo cash issue completes",
            _n(b["pending_issue_pro_forma_value_per_share_inr"]),
            "INR / share",
        ],
    ]
    yield ("Single group equity bridge", ["Item", "Amount", "Unit"], rows)
    yield (
        f"Molycop claim allocation: {b['molycop_ordinary_ownership']:.4%} attributable to Tega",
        ["Claim", "Full claim INR m", "Deducted on attributable basis INR m"],
        [
            [label, _n(b[full]), _n(b[part])]
            for label, full, part in (
                (
                    "Net debt",
                    "molycop_net_debt_full_inr_m",
                    "molycop_net_debt_attributable_inr_m",
                ),
                (
                    "Preference claim",
                    "preference_fair_value_full_inr_m",
                    "preference_fair_value_attributable_inr_m",
                ),
                (
                    "Earnout PV",
                    "earnout_present_value_full_inr_m",
                    "earnout_present_value_attributable_inr_m",
                ),
                (
                    "Other claims",
                    "other_claims_full_inr_m",
                    "other_claims_attributable_inr_m",
                ),
            )
        ],
    )
    for label, key, unit in (
        ("Legacy operating schedule", "legacy_forecast_inr_m", "INR m"),
        ("Molycop operating schedule (100%)", "molycop_forecast_inr_m", "INR m"),
    ):
        rows = result[key]
        yield (
            f"{label} ({unit})",
            [
                "FY end",
                "Months forecast",
                "Revenue",
                "Op. EBITDA",
                "D&A",
                "Cash tax",
                "Capex",
                "New lease assets",
                "Change NWC",
                "FCFF",
            ],
            [
                [r["fiscal_year"], int(r["period_years"] * 12)]
                + [
                    _n(r[k])
                    for k in (
                        "revenue",
                        "operating_ebitda",
                        "da",
                        "unlevered_cash_tax",
                        "cash_capex",
                        "new_lease_assets",
                        "delta_nwc",
                        "fcff",
                    )
                ]
                for r in rows
            ],
        )
        yield (
            f"{label}: asset schedule ({unit}; modeled book values)",
            [
                "FY end",
                "Opening assets incl. CWIP",
                "Cash capex",
                "New leases",
                "Commissioned",
                "D&A",
                "PPA amort.",
                "Closing CWIP",
                "Closing assets",
            ],
            [
                [
                    r["fiscal_year"],
                    _n(
                        r["opening_depreciable_book_proxy"]
                        + r["opening_cwip_proxy"]
                        + r["nondepreciable_land"]
                    ),
                ]
                + [
                    _n(r[k])
                    for k in (
                        "cash_capex",
                        "new_lease_assets",
                        "commissioned_assets",
                        "da",
                        "ppa_amortization",
                        "closing_cwip_proxy",
                        "closing_asset_book_proxy",
                    )
                ]
                for r in rows
            ],
        )
    yield (
        "Molycop ownership-period forecast (includes actual June in FY2027)",
        [
            "FY end",
            "Owned months",
            "Revenue INR m",
            "EBITDA INR m",
            "Cost savings INR m",
            "Integration cash INR m",
        ],
        [
            [r["fiscal_year"], r["owned_months_in_fiscal_year"]]
            + [
                _n(r[k])
                for k in (
                    "owned_fiscal_year_revenue",
                    "owned_fiscal_year_operating_ebitda",
                    "cost_synergies",
                    "integration_cash_cost",
                )
            ]
            for r in result["molycop_forecast_inr_m"]
        ],
    )
    yield (
        "Illustrative financing and cash needs",
        [
            "FY end",
            "MC net bank debt INR m",
            "MC interest INR m",
            "Earnout INR m",
            "Pref. PIK INR m",
            "Pref. balance INR m",
            "Parent debt INR m",
            "Parent funding needed INR m",
            "MC funding needed INR m",
        ],
        [
            [r["fiscal_year"]]
            + [
                _n(r[k])
                for k in (
                    "molycop_closing_net_bank_debt_inr_m",
                    "molycop_cash_interest_inr_m",
                    "earnout_cash_inr_m",
                    "preference_non_cash_pik_inr_m",
                    "preference_closing_assumed_balance_inr_m",
                    "parent_closing_gross_debt_inr_m",
                    "parent_required_new_funding_inr_m",
                    "molycop_required_new_funding_inr_m",
                )
            ]
            for r in result["financing_schedule"]
        ],
    )
    for business, rows in result.get("linked_statements_inr_m", {}).items():
        if business == "legacy":
            yield from _legacy_statement_tables(result)
            continue
        for section in ("income", "balance_sheet", "cash_flow"):
            status = (
                "historical/zero fallbacks"
                if business == "legacy"
                else "partial forecast"
            )
            units = (
                "INR million; EPS INR/share" if section == "income" else "INR million"
            )
            yield (
                f"{business.title()} {section.replace('_', ' ')}: {status}, {units}",
                ["Line item"]
                + [
                    f"FY{r['fiscal_year']}"
                    + (" Jul-Mar" if r["period_years"] < 1 else "")
                    for r in rows
                ],
                [
                    [key.replace("_", " ")] + [_n(r[section][key]) for r in rows]
                    for key in rows[0][section]
                ],
            )
    comparisons = result.get("guidance_comparisons", {})
    if comparisons:
        yield (
            "Guidance comparison: full FY27 / owned ten months as indicated",
            ["Item", "Model", "Guidance / interpretation"],
            [
                [
                    "Legacy full-year finance cost, INR m",
                    _n(comparisons["fy27_legacy_finance_cost_inr_m"]),
                    "1,100–1,200",
                ],
                [
                    "Molycop ten-month interest + principal, INR m",
                    _n(comparisons["fy27_molycop_interest_plus_principal_inr_m"]),
                    "6,647.90; split unverified",
                ],
                [
                    "100% group operating EBITDA margin proxy",
                    f"{comparisons['fy27_full_group_operating_ebitda_margin_proxy']:.2%}",
                    "~15% adjusted margin; definitions differ, gap not plugged",
                ],
            ],
        )


def _assumption_tables(result):
    evidence = result.get("forecast_evidence", {})
    yield (
        "Forecast evidence hierarchy and coverage",
        ["Line item", "Basis", "Period", "Treatment", "Status"],
        [
            [
                r["line_item"],
                r["basis"].replace("_", " "),
                r["period"],
                r["method"],
                r["status"],
            ]
            for r in evidence.get("drivers", [])
        ],
    )
    history = result.get("historical_drivers") or {}
    if history:
        selected = [
            ("receivable_days", "Receivables / sales, days", False),
            ("inventory_revenue_fraction", "Inventory / revenue", True),
            ("payable_revenue_fraction", "Payables / revenue", True),
            (
                "other_operating_current_assets_revenue_fraction",
                "Other operating current assets / revenue",
                True,
            ),
            (
                "other_operating_current_liabilities_revenue_fraction",
                "Other operating current liabilities / revenue",
                True,
            ),
            ("cash_capex_revenue_fraction", "Cash capex / revenue", True),
            (
                "effective_accounting_tax_rate",
                "Accounting tax / PBT (cash-tax proxy)",
                True,
            ),
        ]
        table = []
        for key, label, percent in selected:
            values = [r[key] for r in history["observations"]] + [
                history["averages"][key]
            ]
            table.append(
                [label] + [f"{x:.2%}" if percent else f"{x:.2f}" for x in values]
            )
        yield (
            "Historical ratios used",
            ["Driver"] + [f"FY{y}" for y in history["years"]] + ["Mean"],
            table,
        )
    legacy = result.get("legacy_statement_assumptions")
    if legacy:
        p = legacy["parameters"]
        yield (
            "Legacy Tega: values used to fill statement gaps",
            ["Line item", "Value", "Method"],
            [
                [
                    "Cash interest yield",
                    f"{p['cash_interest_yield']:.4%}",
                    "FY25 interest / average FY24-FY25 cash and bank balances; applied to opening forecast cash",
                ],
                [
                    "Miscellaneous income, annual INR m",
                    _n(p["annual_miscellaneous_income_inr_m"]),
                    "FY25-FY26 nominal mean; prorated for July-March",
                ],
                [
                    "JV profit, annual INR m",
                    _n(p["annual_joint_venture_profit_inr_m"]),
                    "FY24-FY26 mean; equity-accounted profit, excluded from operating FCFF",
                ],
                [
                    "JV cash dividend, annual INR m",
                    _n(p["annual_joint_venture_dividend_inr_m"]),
                    "FY24-FY26 mean; reduces JV carrying value",
                ],
                [
                    "Dividend per share, INR",
                    _n(p["dividend_per_share_inr"]),
                    "FY26 proposed INR2 dividend paid once in FY27; historical fallback thereafter",
                ],
                [
                    "Tax rate",
                    f"{p['effective_tax_rate']:.4%}",
                    "Existing FY24-FY26 mean effective rate on positive taxable earnings; deferred tax movements zero",
                ],
                [
                    "Other non-operating balances",
                    "FY26 balances carried",
                    "Zero movements do not erase existing assets, provisions, taxes or reserves",
                ],
                [
                    "Unpredictable new gains / FX / impairment / equity issuance",
                    "0 assumed",
                    "No extrapolation of exceptional historical movements",
                ],
                [
                    "June opening balance discrepancy, INR m",
                    _n(legacy["opening_balance_sheet_residual_inr_m"]),
                    "Disclosed diagnostic, carried unchanged; not set to zero or inserted into equity/cash",
                ],
            ],
        )


def write_reports(
    facts,
    assumptions,
    results,
    output: Path,
    reference_price=None,
    *,
    statements=None,
    historical_checks=None,
):
    output.mkdir(parents=True, exist_ok=True)
    sensitivity = sensitivities(facts, assumptions)
    summary_rows = []
    for name, result in results.items():
        b = result["equity_bridge"]
        summary_rows.append(
            [
                name.title(),
                "Equity shortfall under stress"
                if b["raw_tega_equity_inr_m"] < 0
                else f"INR {_n(b['value_per_share_inr'])}",
                _n(b["raw_tega_equity_inr_m"]),
                f"{result['group_dcf_inr_m']['wacc']:.1%}",
                f"{result['group_dcf_inr_m']['terminal_growth']:.1%}",
            ]
        )
    title = "Tega + Molycop: single group DCF"
    intro = (
        "PROVISIONAL. Valuation date: 30 June 2026. Research cutoff: 11 September 2026. "
        "Reported facts and management guidance are separated from analyst assumptions. "
        "These are conditional scenario values, not validated current price targets. "
        "A zero equity floor indicates insufficient modeled enterprise value to cover claims; "
        "it is not a prediction that the quoted stock price becomes zero."
    )
    intro += (
        " All model amounts are INR million unless marked per share or per tonne. "
        "USD-origin amounts use INR94.97 per USD, the September 2, 2026 closing rate "
        "reported by Reuters (not an FBIL reference fixing). Reported INR actuals are unchanged. "
        "Currency conversion uses a fixed rate; June 30 remains the valuation date. "
        "The single-group method changes valuation separately from currency conversion. One group discount rate and one terminal value apply in each scenario. "
        "Cash flows include 100% of legacy Tega plus its 84.1787% share of Molycop; "
        "Molycop senior claims use that same proportion. Group rates are provisional."
        " Forecast assumptions and public consensus coverage reviewed on 20 September 2026. "
        "Legacy Tega statement gaps use existing schedules, historical fallbacks and explicitly assumed zeros. "
        "Its investment in Molycop is shown at cost in this legacy-only view; this is not group PAT/EPS. "
        "The estimated June opening balance discrepancy remains visible. Molycop statements remain partial: Unresolved means missing evidence."
    )

    timing = (
        "FY2027 is April 2026–March 2027. Molycop is consolidated June–March (10 months). "
        "Actual June is retained; only July–March (9 months) is discounted as future cash flow. "
        "The legacy business similarly excludes its actual April–June quarter. "
        "End-period discounting uses actual days / 365. Operating schedules support one combined "
        "DCF; they are not separately valued. The cash flows used for valuation are "
        "ownership-adjusted economic amounts, not statutory consolidated statements."
    )
    headers = [
        "Scenario",
        "Provisional INR / share",
        "Raw equity INR m",
        "Group WACC",
        "Group terminal growth",
    ]
    md = [f"# {title}", "", intro, "", _table(headers, summary_rows), "", timing, ""]
    html = [
        f"<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{title}</title>",
        "<style>body{margin:0;background:#f3f5f8;color:#172536;font:16px/1.55 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:32px 22px}h1{font-size:34px;letter-spacing:-1px}h2{margin-top:36px}h3{margin-top:28px}.notice{background:#fff4d5;border-left:5px solid #c28514;padding:18px}section,details{background:white;border:1px solid #d8e0e9;border-radius:10px;padding:18px;margin:18px 0}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;margin:14px 0}th,td{padding:10px;border-bottom:1px solid #dce3eb;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{background:#edf2f8}a{color:#125ca1}summary{cursor:pointer;font-weight:650}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}li{margin:8px 0}nav a{margin-right:20px}@media print{body{background:white}main{max-width:none}details{break-inside:avoid}.table-wrap{overflow:visible}th,td{padding:5px;font-size:10px}}</style><main>",
        f"<h1>{title}</h1><p class='notice'>{escape(intro)}</p>",
        _table(headers, summary_rows, True),
        f"<p>{escape(timing)}</p>",
        "<nav><a href='#assumptions'>Assumptions</a><a href='#base'>Base</a><a href='#downside'>Downside</a><a href='#upside'>Upside</a><a href='#sensitivity'>Sensitivity</a><a href='#sources'>Sources</a></nav>",
    ]
    evidence = results["base"].get("forecast_evidence", {})
    evidence_md = [
        "# Revenue and financial forecast assumptions",
        "",
        "Reviewed 20 September 2026. User-approved revenue; then management guidance, verifiable comparable consensus, historical trend. Legacy Tega statement gaps now use user-authorized schedule/historical/zero fallbacks; Molycop gaps remain unresolved.",
        "",
    ]
    html.append(
        "<style>#assumptions td,#assumptions th{white-space:normal;vertical-align:top}#assumptions td:nth-child(4){min-width:260px;text-align:left}#assumptions td:first-child{min-width:130px}</style><section id='assumptions'><h2>Revenue and financial forecast assumptions</h2>"
    )
    for label, table_headers, table_rows in _assumption_tables(results["base"]):
        evidence_md += [f"## {label}", "", _table(table_headers, table_rows), ""]
        html += [f"<h3>{escape(label)}</h3>", _table(table_headers, table_rows, True)]
    for limitation in evidence.get("limitations", []):
        evidence_md += [f"- {limitation}"]
        html.append(f"<p>{escape(limitation)}</p>")
    consensus = evidence.get("consensus_review", {})
    if consensus:
        review = consensus["use"] + " " + consensus["wacc_status"]
        evidence_md += [
            "",
            "## Public consensus review",
            "",
            review,
            "",
            f"[Consensus summary checked]({consensus['url']})",
            "",
        ]
        html.append(
            f"<p>{escape(review)} <a href='{escape(consensus['url'])}'>Public consensus summary</a></p>"
        )
    html.append(
        "<p><a href='forecast_assumptions.md'>Read the assumptions note</a> · <a href='forecast_evidence.json'>Values and source coverage</a></p></section>"
    )
    (output / "forecast_assumptions.md").write_text(
        "\n".join(evidence_md) + "\n", encoding="utf-8"
    )
    (output / "forecast_evidence.json").write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    legacy_register = results["base"]["legacy_statement_assumptions"]
    (output / "legacy_statement_assumptions.json").write_text(
        json.dumps(legacy_register, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    html.append(
        "<section><h2>Legacy Tega statement scope</h2>"
        "<p>All legacy statement rows have numeric forecast values. Existing schedules take priority; "
        "remaining rows use historical balances/ratios or explicit zero assumptions. "
        "The FY27 income and cash-flow columns cover July-March; balance sheets are at 31 March. "
        "Molycop remains outside this statement view except for the parent's investment and existing modeled distributions.</p>"
        f"<p><strong>Opening reconciliation: INR{legacy_register['opening_balance_sheet_residual_inr_m']:,.3f} million.</strong> "
        "The retained June cash/debt estimates do not fully reconcile to the rolled reported balances. "
        "This gap remains visible in each balance sheet; future-period movements reconcile. "
        "No cash, equity or other-asset plug has been inserted.</p>"
        "<p><a href='legacy_statement_assumptions.json'>Legacy statement policy and calculated inputs</a></p></section>"
    )
    md += [
        "[Review forecast assumptions, historical ratios and data gaps](forecast_assumptions.md)",
        "",
    ]
    if statements is not None:
        write_historical_reports(statements, historical_checks, output)
        statement_text = f"The complete FY26 statements are the source for the legacy inputs. {len(historical_checks)} historical reconciliation checks passed."
        md += [
            "## Complete FY26 statements",
            "",
            statement_text,
            "",
            "[Income statement, balance sheet, cash flows and notes](historical_statements.md)",
            "",
        ]
        html += [
            f"<section><h2>Complete FY26 statements</h2><p>{statement_text}</p><p><a href='historical_statements.html'>Open the audited statements and supporting reconciliations</a></p><p>The acquisition cash/debt bridge below starts from these March balances; its June estimates remain labeled.</p></section>"
        ]
    if reference_price is not None:
        base = results["base"]["equity_bridge"]
        target_equity = reference_price * base["issued_shares"] / 1_000_000
        required_group_ev = (
            target_equity
            + base["total_attributable_claims_inr_m"]
            - base["nonoperating_assets_inr_m"]
        )
        reference_text = (
            f"User-supplied comparison price: INR {reference_price:,.2f} (unverified; not a live quote). "
            f"Holding claims and nonoperating assets fixed requires attributable group enterprise value of INR {required_group_ev:,.2f}m, "
            f"versus the model's INR {base['group_enterprise_value_inr_m']:,.2f}m. "
            "This algebraic comparison never changes the forecasts."
        )
        md += ["## Comparison supplied by the user", "", reference_text, ""]
        html += [
            f"<section><h2>Comparison supplied by the user</h2><p>{escape(reference_text)}</p></section>"
        ]
    for name, result in results.items():
        directory = output / name
        directory.mkdir(exist_ok=True)
        (directory / "model.json").write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        case_md = [
            f"# {name.title()} acquisition scenario",
            "",
            intro,
            "",
            result["scenario_assumptions"]["rationale"],
            "",
        ]
        html += [
            f"<section id='{name}'><h2>{name.title()} scenario</h2><p>{escape(result['scenario_assumptions']['rationale'])}</p>"
        ]
        for label, table_headers, table_rows in _case_tables(result):
            case_md += [f"## {label}", "", _table(table_headers, table_rows), ""]
            html += [
                f"<h3>{escape(label)}</h3>",
                _table(table_headers, table_rows, True),
            ]
        case_md += ["## Information gaps and checks", ""] + [
            f"- {w}" for w in result["warnings"]
        ]
        case_md += ["", "```json", json.dumps(result["checks"], indent=2), "```", ""]
        (directory / "forecast.md").write_text("\n".join(case_md), encoding="utf-8")
        html += [
            "<details><summary>Information gaps</summary><ul>"
            + "".join(f"<li>{escape(w)}</li>" for w in result["warnings"])
            + "</ul></details>",
            "<details><summary>Complete editable assumptions used in this calculation</summary><pre>"
            + escape(json.dumps(result["scenario_assumptions"], indent=2))
            + "</pre></details></section>",
        ]
        md += [f"- [{name.title()} forecast and schedules]({name}/forecast.md)"]
    bridge = results["base"]["opening_bridge_inr_m"]
    bridge_rows = [
        [k.replace("_", " "), _n(v)]
        for k, v in bridge.items()
        if isinstance(v, (int, float))
    ]
    md += [
        "",
        "## Estimated opening funding bridge (INR million)",
        "",
        _table(["Item", "Amount"], bridge_rows),
        "",
    ]
    html += [
        "<section><h2>Estimated opening funding bridge (INR million)</h2><p>The top-up is an estimated liquidity need, not a reported borrowing. It changes cash and debt equally.</p>",
        _table(["Item", "Amount"], bridge_rows, True),
        "</section>",
    ]
    sens_rows = [
        [
            r["parameter"],
            _n(r["input"]) if "(INR m)" in r["parameter"] else f"{r['input']:.4f}",
            _n(r["value_per_share_inr"]),
        ]
        for r in sensitivity
    ]
    md += [
        "## One-at-a-time base sensitivity",
        "",
        "Rates are decimals. All other assumptions remain at base. No probabilities assigned.",
        "",
        _table(["Input changed", "Value", "INR/share"], sens_rows),
        "",
    ]
    html += [
        "<section id='sensitivity'><h2>One-at-a-time base sensitivity</h2><p>Rates are decimals. All other assumptions remain at base.</p>",
        _table(["Input changed", "Value", "INR/share"], sens_rows, True),
        "</section>",
    ]
    warnings = results["base"]["warnings"]
    md += (
        ["## Material limitations", ""]
        + [f"- {w}" for w in warnings]
        + ["", "## Sources", ""]
    )
    html += [
        "<section><h2>Material limitations</h2><ul>"
        + "".join(f"<li>{escape(w)}</li>" for w in warnings)
        + "</ul></section>",
        "<details><summary>Shared assumptions and rationale</summary><pre>"
        + escape(json.dumps(assumptions["shared"], indent=2))
        + "</pre></details>",
        "<section id='sources'><h2>Sources</h2><ul>",
    ]
    for key, source in facts["sources"].items():
        md += [
            f"- {source['date']}: [{source['title']}]({source['url']}) — {source['location']} (`{key}`)."
        ]
        html += [
            f"<li>{source['date']}: <a href='{escape(source['url'], quote=True)}'>{escape(source['title'])}</a> — {escape(source['location'])}</li>"
        ]
    html += [
        "</ul></section><p>Recalculate: python run_tega_model.py · Full machine-readable results: base/model.json, downside/model.json, upside/model.json.</p></main></html>"
    ]
    (output / "report.html").write_text("\n".join(html), encoding="utf-8")
    (output / "scenarios.md").write_text("\n".join(md), encoding="utf-8")
    (output / "sensitivity.json").write_text(
        json.dumps(sensitivity, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output / "inputs_used.json").write_text(
        json.dumps(
            {
                "facts": facts,
                "assumptions": assumptions,
                "user_reference_price_inr_unverified": reference_price,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
