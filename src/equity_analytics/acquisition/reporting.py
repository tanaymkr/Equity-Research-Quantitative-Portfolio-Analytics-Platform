"""Self-contained HTML and Markdown reports; no third-party dependencies."""

from __future__ import annotations

import json
from copy import deepcopy
from html import escape
from pathlib import Path

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
        ("Molycop USD WACC", "scenario", "molycop_wacc_usd", [0.09, 0.105, 0.12]),
        ("Legacy INR WACC", "scenario", "legacy_wacc_inr", [0.105, 0.12, 0.14]),
        (
            "Molycop terminal USD growth",
            "scenario",
            "molycop_terminal_growth_usd",
            [0.02, 0.025, 0.03],
        ),
        (
            "Legacy terminal INR growth",
            "scenario",
            "legacy_terminal_growth_inr",
            [0.03, 0.04, 0.045],
        ),
        (
            "Preference current fair value (USD m)",
            "shared",
            "preference_fair_value_usd_m",
            [270, 330, 400],
        ),
        (
            "Other claims reserve (USD m)",
            "shared",
            "molycop_other_claims_usd_m",
            [0, 50, 100],
        ),
        ("Earnout cash payment (USD m)", "scenario", "earnout_usd_m", [0, 60, 120]),
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
            "Molycop FY26 EBITDA operating adjustment (USD m)",
            "shared",
            "molycop_fy2026_ebitda_operating_adjustment_usd_m",
            [-10, 0, 10],
        ),
        (
            "Translation INR/USD; closing payment FX fixed",
            "shared",
            "fx_inr_per_usd",
            [90, assumptions["shared"]["fx_inr_per_usd"], 100],
        ),
        (
            "Closing payment INR/USD; valuation FX fixed",
            "shared",
            "closing_funding_fx_inr_per_usd",
            [90, assumptions["shared"]["closing_funding_fx_inr_per_usd"], 100],
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
        savings = base["molycop_cost_synergies_usd_m"]
        base["molycop_cost_synergies_usd_m"] = [savings[0]] + [
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
    yield (
        "Equity bridge",
        ["Item", "Amount", "Unit"],
        [
            [
                "Legacy enterprise value",
                _n(b["legacy_enterprise_value_inr_m"]),
                "INR m",
            ],
            [
                "Less: legacy/parent net debt after acquisition funding",
                _n(b["legacy_net_debt_inr_m"]),
                "INR m",
            ],
            [
                "Add: legacy JV/property book-value proxy",
                _n(b["legacy_jv_and_property_book_proxy_inr_m"]),
                "INR m",
            ],
            [
                "Molycop enterprise value",
                _n(b["molycop_enterprise_value_usd_m"]),
                "USD m",
            ],
            ["Less: Molycop net debt", _n(b["molycop_net_debt_usd_m"]), "USD m"],
            [
                "Less: preference fair-value proxy",
                _n(b["preference_fair_value_proxy_usd_m"]),
                "USD m",
            ],
            [
                "Less: earnout present value",
                _n(b["earnout_present_value_usd_m"]),
                "USD m",
            ],
            [
                "Less: other-claims reserve",
                _n(b["other_claims_reserve_usd_m"]),
                "USD m",
            ],
            [
                "Molycop ordinary residual before zero floor",
                _n(b["molycop_raw_residual_usd_m"]),
                "USD m",
            ],
            [
                "Tega's ordinary ownership",
                f"{b['molycop_ordinary_ownership']:.4%}",
                "%",
            ],
            [
                "Tega's Molycop interest after claims and ownership",
                _n(b["tega_molycop_interest_inr_m"]),
                "INR m",
            ],
            [
                "Tega total equity before zero floor",
                _n(b["raw_tega_equity_inr_m"]),
                "INR m",
            ],
            ["Issued shares", f"{b['issued_shares']:,}", "shares"],
            ["Provisional scenario value", _n(b["value_per_share_inr"]), "INR / share"],
            [
                "If proposed Apollo cash issue completes (gross proceeds)",
                _n(b["pending_issue_pro_forma_value_per_share_inr"]),
                "INR / share",
            ],
        ],
    )
    for label, key, unit in (
        ("Legacy cash flows", "legacy_forecast_inr_m", "INR m"),
        ("Molycop cash flows", "molycop_forecast_usd_m", "USD m"),
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
            "Revenue USD m",
            "EBITDA USD m",
            "Cost savings USD m",
            "Integration cash USD m",
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
            for r in result["molycop_forecast_usd_m"]
        ],
    )
    yield (
        "Illustrative financing and cash needs",
        [
            "FY end",
            "MC net bank debt USD m",
            "MC interest USD m",
            "Earnout USD m",
            "Pref. PIK USD m",
            "Pref. balance USD m",
            "Parent debt INR m",
            "Parent funding needed INR m",
            "MC funding needed USD m",
        ],
        [
            [r["fiscal_year"]]
            + [
                _n(r[k])
                for k in (
                    "molycop_closing_net_bank_debt_usd_m",
                    "molycop_cash_interest_usd_m",
                    "earnout_cash_usd_m",
                    "preference_non_cash_pik_usd_m",
                    "preference_closing_assumed_balance_usd_m",
                    "parent_closing_gross_debt_inr_m",
                    "parent_required_new_funding_inr_m",
                    "molycop_required_new_funding_usd_m",
                )
            ]
            for r in result["financing_schedule"]
        ],
    )
    yield (
        "Terminal value assumptions",
        [
            "Business",
            "Currency",
            "WACC",
            "g",
            "ROIC",
            "PV forecast FCFF",
            "PV terminal",
            "Terminal / EV",
        ],
        [
            [
                name,
                currency,
                f"{v['wacc']:.2%}",
                f"{v['terminal_growth']:.2%}",
                f"{v['terminal_roic']:.2%}",
                _n(v["pv_forecast_fcff"]),
                _n(v["pv_terminal_value"]),
                f"{v['terminal_share_of_ev']:.1%}",
            ]
            for name, currency, v in (
                ("Legacy", "INR m", result["legacy_dcf_inr_m"]),
                ("Molycop", "USD m", result["molycop_dcf_usd_m"]),
            )
        ],
    )


def write_reports(facts, assumptions, results, output: Path, reference_price=None):
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
                f"{result['legacy_dcf_inr_m']['wacc']:.1%}",
                f"{result['molycop_dcf_usd_m']['wacc']:.1%}",
            ]
        )
    title = "Tega + Molycop: acquisition DCF"
    intro = (
        "PROVISIONAL. Valuation date: 30 June 2026. Research cutoff: 11 September 2026. "
        "Reported facts and management guidance are separated from analyst assumptions. "
        "These are conditional scenario values, not validated current price targets. "
        "A zero equity floor indicates insufficient modeled enterprise value to cover claims; "
        "it is not a prediction that the quoted stock price becomes zero."
    )
    timing = (
        "FY2027 is April 2026–March 2027. Molycop is consolidated June–March (10 months). "
        "Actual June is retained; only July–March (9 months) is discounted as future cash flow. "
        "The legacy business similarly excludes its actual April–June quarter. "
        "End-period discounting uses actual days / 365. USD and INR discount rates remain separate."
    )
    headers = [
        "Scenario",
        "Provisional INR / share",
        "Raw equity INR m",
        "Legacy INR WACC",
        "MC USD WACC",
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
    if reference_price is not None:
        base = results["base"]["equity_bridge"]
        target_equity = reference_price * base["issued_shares"] / 1_000_000
        required_mc_ev = (
            (target_equity - base["legacy_equity_after_acquisition_funding_inr_m"])
            / (base["molycop_ordinary_ownership"] * base["fx_inr_per_usd"])
            + base["molycop_net_debt_usd_m"]
            + base["preference_fair_value_proxy_usd_m"]
            + base["earnout_present_value_usd_m"]
            + base["other_claims_reserve_usd_m"]
        )
        reference_text = (
            f"User-supplied comparison price: INR {reference_price:,.2f} (unverified; not a live quote). "
            f"Holding the base legacy valuation and all claims fixed would require a Molycop EV of USD {required_mc_ev:,.2f}m, "
            f"versus the model's USD {base['molycop_enterprise_value_usd_m']:,.2f}m. "
            "This is an algebraic comparison, not a change to the forecast or a valuation recommendation."
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
        [r["parameter"], _n(r["input"]), _n(r["value_per_share_inr"])]
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
