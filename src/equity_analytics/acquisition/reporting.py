"""Self-contained HTML and Markdown reports; no third-party dependencies."""

from __future__ import annotations

import json
from copy import deepcopy
from html import escape
from pathlib import Path

from equity_analytics.forecasting.reporting import write_historical_reports

from .engine import build_acquisition_model


def _n(value):
    return f"{value:,.2f}"


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
                    _n(r["opening_depreciable_book_proxy"] + r["opening_cwip_proxy"]),
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
        "<nav><a href='#base'>Base</a><a href='#downside'>Downside</a><a href='#upside'>Upside</a><a href='#sensitivity'>Sensitivity</a><a href='#sources'>Sources</a></nav>",
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
