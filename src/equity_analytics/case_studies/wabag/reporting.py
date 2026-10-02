"""Offline, auditable statement report; no network calls or runtime dependencies."""

import json
from html import escape
from pathlib import Path

from .layout import BS_ROWS, CF_ROWS, IS_ROWS, LABELS


def fmt(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def table(headers, rows):
    head = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    body = "".join(
        "<tr>"
        + "".join(
            f"<{('th' if i == 0 else 'td')}>{escape(fmt(c))}</{('th' if i == 0 else 'td')}>"
            for i, c in enumerate(row)
        )
        + "</tr>"
        for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def section(identifier, title, body):
    return f'<section id="{identifier}"><h2>{escape(title)}</h2>{body}</section>'


def report_html(payload):
    years = payload["forecast"]
    headers = ["INR million unless stated"] + [f"FY{r['year']}E" for r in years]
    parts = []
    dcf = payload["dcf"]
    parts.append(
        '<div class="cards">'
        + "".join(
            f"<div><small>{escape(label)}</small><strong>{escape(value)}</strong></div>"
            for label, value in (
                ("FY27 revenue", fmt(years[0]["income_statement"]["revenue"]) + "m"),
                (
                    "FY27 diluted EPS",
                    "INR " + fmt(years[0]["income_statement"]["diluted_eps"]),
                ),
                ("FY27 WACC", f"{years[0]['wacc']['wacc']:.2%}"),
                (
                    "Illustrative DCF / diluted share",
                    "INR " + fmt(dcf["implied_value_per_share"]),
                ),
            )
        )
        + "</div>"
    )
    parts.append(
        '<p class="notice"><b>Assumptions for review.</b> '
        + escape(payload["convention"])
        + " Source forecasts are benchmarks; this model calculates its own profit, cash flow and EPS. Amounts use INR millions (10 million = 1 crore).</p>"
    )
    parts.append(
        "<p>Edit <code>examples/wabag_linked/assumptions.json</code> and rerun <code>Run_Wabag_Forecast.bat</code>. Each input includes its source and rationale. The old SQL-only DCF remains a separate legacy example.</p>"
    )
    for key, identifier, title, fields in (
        ("income_statement", "income", "Consolidated profit and loss", IS_ROWS),
        ("balance_sheet", "balance", "Consolidated balance sheet", BS_ROWS),
        ("cash_flow", "cash", "Consolidated cash-flow statement", CF_ROWS),
    ):
        all_years = payload["historical"] + years
        cols = ["INR million unless stated"] + [
            f"FY{r['year']}{'A' if i < 3 else 'E'}" for i, r in enumerate(all_years)
        ]
        rows = [[LABELS[k]] + [r[key][k] for r in all_years] for k in fields]
        note = ""
        if key == "income_statement":
            note = "<p>Cost of sales is the residual expense required by the selected EBITDA margin after employee costs, other expenses and inventory changes. Finance costs include bank charges; the DCF treats those charges as operating costs. FY24 FX was included in other income in the source statement.</p>"
        if key == "balance_sheet":
            note = "<p>FY24 has a disclosed INR1m source-rounding residual. FY27–31 balance through the schedules; no cash plug is used. Current borrowing includes next-year term maturities and revolving facilities.</p>"
        if key == "cash_flow":
            note = "<p>Credit-loss and provision charges are already inside forecast expense budgets. Their noncash add-backs and gross working-capital movements offset correctly. FY24 lease recognition/repayment follows the original presentation; interest paid was not separately split into lease and borrowing interest.</p>"
        parts.append(section(identifier, title, note + table(cols, rows)))
    debt_keys = (
        "term_open",
        "scheduled_repayment",
        "extra_repayment",
        "term_close",
        "current_term",
        "working_open",
        "working_net_draw",
        "working_close",
        "lease_open",
        "lease_additions",
        "lease_repaid",
        "lease_close",
        "current_lease",
        "interest_term",
        "interest_working",
        "interest_lease",
        "total_close",
    )
    debt_rows = [
        [k.replace("_", " ").capitalize()] + [r["debt"][k] for r in years]
        for k in debt_keys
    ]
    parts.append(
        section(
            "debt",
            "Debt and lease schedule",
            "<p>FY27/FY28 bank-debt targets use Motilal Oswal estimates; later years use the three-year debt CAGR. The FY27 term repayment starts with disclosed current maturities. Repeated INR294m repayments after FY27 are an editable timing proxy. Borrowing rates are disclosed-rate blends / historical proxies; they are not exact loan-by-loan forecasts.</p>"
            + table(headers, debt_rows),
        )
    )
    asset_rows = []
    for bucket in ("land", "owned", "rou", "software"):
        for measure in ("opening", "additions", "depreciation", "closing"):
            asset_rows.append(
                [f"{bucket.title()} — {measure}"]
                + [r["fixed_assets"][measure][bucket] for r in years]
            )
    asset_rows += [
        ["Cash capex"] + [r["fixed_assets"]["capex"] for r in years],
        ["D&A target not used because of asset cap"]
        + [r["fixed_assets"]["uncaptured_da_target"] for r in years],
    ]
    parts.append(
        section(
            "assets",
            "Fixed assets, depreciation and amortisation",
            "<p>Land is not depreciated. Owned PPE, right-of-use assets and software roll forward separately. D&A uses explicit broker forecasts then historical ratios, allocated using FY26 charge proportions and capped at available assets. This is an annual allocation schedule, not an asset-vintage or tax-depreciation model. New lease additions default to a flagged zero.</p>"
            + table(headers, asset_rows),
        )
    )
    for key, identifier, title in (
        ("working_capital", "wc", "Operating working capital"),
        ("tax", "tax", "Tax schedule"),
        ("equity", "equity", "Equity, dividends and shares"),
        ("credit_losses", "credit", "Credit-loss allowance"),
        ("provisions", "provisions", "Provisions"),
    ):
        note = {
            "working_capital": "Includes operating receivables, inventories, other assets, payables, provisions and all other bank balances. Excludes financing, current tax balances and non-operating investments. Each operating balance uses its three-year pooled revenue ratio. This definition differs from management’s 100–110-day measure.",
            "tax": "Tax is applied to positive PBT before equity-accounted associate profit, with separate current, deferred and cash-tax calculations. Consolidated tax rates are proxies; jurisdiction-level losses and tax-credit expiry are not modelled.",
            "equity": "Cash dividends pay the preceding year’s declared DPS. Basic ending shares remain 62.309595m; 0.841234m incremental options form a diluted-share proxy. Future share issuance is zero. Share-based compensation remains an economic expense in FCFF.",
            "credit_losses": "A net receivable balance and its allowance are modelled separately. With write-offs, the gross cash-movement calculation adds those back to the gross balance change; no credit-loss add-back is counted twice.",
            "provisions": "Net utilisation equals opening provision plus embedded expense charge less closing provision. A negative amount would require a separate noncash movement; the default model rejects that unexplained condition.",
        }[key]
        rows = [
            [k.replace("_", " ").capitalize()] + [r[key][k] for r in years]
            for k in years[0][key]
        ]
        parts.append(
            section(
                identifier, title, "<p>" + escape(note) + "</p>" + table(headers, rows)
            )
        )
    rates = payload["wacc_reference"]
    wacc_rows = []
    for k in years[0]["wacc"]:
        wacc_rows.append(
            [k.replace("_", " ").capitalize()]
            + [
                (
                    f"{r['wacc'][k]:.3%}"
                    if k
                    not in (
                        "market_equity",
                        "average_gross_debt",
                        "unlevered_beta",
                        "relevered_beta",
                    )
                    else r["wacc"][k]
                )
                for r in years
            ]
        )
    wacc_note = f"<p>Price reference: {escape(rates['price_date'])}; INR{rates['share_price']:,.2f}. Observed levered beta {rates['levered_beta']:.4f}, from {len(rates['beta_observations'])} weekly Wabag / NIFTY50 price-return pairs. This is a local-index estimate with limited explanatory power (R² {rates['beta_statistics']['r_squared']:.3f}), not a forecast beta supplied by Wabag.</p>"
    wacc_note += "<p>Default-free INR rate = Indian 10-year G-sec yield − sovereign default spread. Cost of equity = default-free rate + relevered beta × mature-market ERP + India country-risk premium × country loading. Beta is unlevered using reported gross debt and market equity, then relevered using each year’s average forecast debt. Country risk is not added twice. Book debt approximates market debt; equity value is held at the dated reference price × basic shares to avoid circular valuation.</p>"
    parts.append(
        section(
            "wacc", "WACC and capital structure", wacc_note + table(headers, wacc_rows)
        )
    )
    rows = [
        [k.replace("_", " ").capitalize()] + [r["valuation"][k] for r in years]
        for k in years[0]["valuation"]
    ]
    rows += [
        ["Discount factor"] + [r["discount_factor"] for r in dcf["forecast"]],
        ["Present value of FCFF"] + [r["present_value"] for r in dcf["forecast"]],
    ]
    dcf_body = (
        "<p>FCFF = operating EBIT after bank charges × (1 − tax rate) + D&A − cash capex − noncash lease additions − change in operating working capital. The cash-flow-statement bridge is checked independently. Non-operating income and associate profits are excluded from FCFF; starting investments and related-party loans enter the equity bridge at book-value proxies.</p>"
        + table(headers, rows)
    )
    dcf_body += table(
        ["Valuation bridge", "INR million unless stated"],
        [
            [k.replace("_", " ").capitalize(), v]
            for k, v in dcf.items()
            if k not in ("forecast", "terminal_method")
        ],
    )
    dcf_body += "<p>Cash exclusion defaults to INR1,217m under a conservative, unverified allocation of restrictions between cash and other bank balances. All other bank balances are already treated as operating collateral. Review this to avoid excessive exclusion. Minority claims and non-operating assets use book values. Terminal growth and ROIC are analyst assumptions; management’s ROE aspiration is not a terminal ROIC forecast.</p>"
    growths = [c["terminal_growth"] for c in payload["sensitivity"][0]["cells"]]
    dcf_body += "<h3>WACC / terminal-growth sensitivity</h3>" + table(
        ["Shift to every annual WACC"] + [f"g {g:.0%}" for g in growths],
        [
            [f"{r['wacc_shift']:+.1%}"] + [c["value_per_share"] for c in r["cells"]]
            for r in payload["sensitivity"]
        ],
    )
    dcf_body += "<p>Terminal FCFF = final NOPAT × (1 + g) × (1 − g / ROIC). The discount factor is the product of each annual (1 + WACC), not a single fixed-rate shortcut. Invalid sensitivity combinations display a dash.</p>"
    parts.append(section("dcf", "Linked FCFF and DCF", dcf_body))
    comparisons = []
    market_price = {**rates, **payload["assumptions"]["wacc_overrides"]}["share_price"]
    for i, r in enumerate(years):
        eps = r["income_statement"]["basic_eps"]
        bvps = (r["balance_sheet"]["equity"] - r["balance_sheet"]["nci"]) / r["equity"][
            "basic_shares"
        ]
        comparisons.append(
            [
                f"FY{r['year']} linked",
                r["income_statement"]["revenue"],
                r["income_statement"]["owners_profit"],
                eps,
                market_price / eps if eps > 0 else None,
                market_price / bvps if bvps > 0 else None,
            ]
        )
        for name, ref in payload["forecast_references"].items():
            if r["year"] in ref["years"]:
                j = ref["years"].index(r["year"])
                comparisons.append(
                    [
                        f"FY{r['year']} {name}",
                        ref["revenue"][j],
                        ref["net_profit"][j],
                        ref["eps"][j],
                        ref.get("pe", [None] * len(ref["years"]))[j],
                        ref.get("pb", [None] * len(ref["years"]))[j],
                    ]
                )
    parts.append(
        section(
            "comparison",
            "Forecast comparison",
            "<p>Broker earnings and EPS are comparison values, not hardcoded outputs. Consensus is the public MarketScreener aggregation; contributor count and original estimate dates were not verified. Moneycontrol-hosted broker PDFs are their respective brokers’ forecasts. A Moneycontrol Pro annual forecast table was not verified. Linked P/E and P/B use the dated price reference; broker multiples retain their own report-date price and are not target multiples.</p>"
            + table(
                ["Source / year", "Revenue", "Owners PAT", "Basic EPS", "P/E", "P/B"],
                comparisons,
            ),
        )
    )
    check_rows = [
        [
            str(c["year"]),
            c["name"],
            f"{c['residual']:.2g}",
            f"{c['tolerance']:.1g}",
            c["passed"],
        ]
        for c in payload["checks"] + payload["historical_checks"]
    ]
    parts.append(
        section(
            "checks",
            "Accounting and source checks",
            f"<p>{len(payload['checks'])} forecast checks passed; {len(payload['historical_checks'])} historical reconciliations passed within source rounding. SQL cross-checks: {len(payload['sql_crosschecks'])}. Tolerances below are INR million. Tests establish calculation behaviour, not forecast accuracy.</p>"
            + table(["Year", "Check", "Residual", "Tolerance", "Status"], check_rows),
        )
    )
    assumption_rows = []
    cfg = payload["assumptions"]
    for group in ("policy", "operating_balance_ratios"):
        for k, v in cfg[group].items():
            assumption_rows.append(
                [
                    group,
                    k,
                    f"{v['value']:.8g}",
                    "value / ratio",
                    v["source"],
                    v["reason"],
                ]
            )
    for row in cfg["years"]:
        for k, v in row["drivers"].items():
            assumption_rows.append(
                [
                    f"FY{row['year']}",
                    k,
                    f"{v['value']:.8g}",
                    v.get("method", "absolute"),
                    v["source"],
                    v["reason"],
                ]
            )
    parts.append(
        section(
            "inputs",
            "Input register and flagged zeros",
            "<p>Hierarchy: relevant company guidance → consensus → identifiable broker → three-year historical rule → explicit zero where unavailable. Reported balance-sheet stocks are retained or rolled forward; they are not erased because a future flow is unavailable. Source “analyst” identifies modelling choices. The −1 DPS setting means derive a progressive dividend; it is not a negative dividend. Values with method revenue_ratio multiply forecast revenue; prior_revenue_growth and prior_debt_growth multiply the preceding balance by (1 + rate). Ratios and growth rates use decimals: 0.10 = 10%.</p>"
            + table(
                ["Period / group", "Input", "Value", "Method", "Source", "Reason"],
                assumption_rows,
            ),
        )
    )
    sources = (
        "<ul>"
        + "".join(
            f'<li><b>{escape(k)}</b> · {escape(v["date"])} · <a href="{escape(v["url"], quote=True)}">Source</a><br>{escape(v["locator"])}</li>'
            for k, v in payload["sources"].items()
        )
        + "</ul>"
    )
    for src in rates["provider_sources"]:
        sources += f'<p>{escape(src["instrument"])} price source · {escape(src["retrieved_at"])} · <a href="{escape(src["url"], quote=True)}">Vendor endpoint</a></p>'
    sources += (
        "<p>Local input hashes identify exactly which files produced this report:</p>"
        + table(["Input", "SHA-256"], payload["input_sha256"].items())
    )
    parts.append(section("sources", "Sources and reproducibility", sources))
    nav = "".join(
        f'<a href="#{i}">{label}</a>'
        for i, label in (
            ("income", "P&L"),
            ("balance", "Balance sheet"),
            ("cash", "Cash flow"),
            ("debt", "Debt"),
            ("assets", "D&A"),
            ("wc", "Working capital"),
            ("wacc", "WACC"),
            ("dcf", "DCF"),
            ("comparison", "Estimates"),
            ("checks", "Checks"),
            ("inputs", "Inputs"),
            ("sources", "Sources"),
        )
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wabag · Linked forecasts</title><style>'
        + CSS
        + '</style></head><body><header><div class="eyebrow">INVESTMENT RESEARCH PLATFORM</div><h1>VA Tech Wabag</h1><p>Consolidated financial forecasts · FY2024–2026 actuals · FY2027–2031 estimates</p><p>Information cutoff: '
        + escape(payload["information_as_of"])
        + "</p></header><nav>"
        + nav
        + "</nav><main>"
        + "".join(parts)
        + "</main><footer>Built from dated source snapshots. Re-run after reviewing assumptions.</footer></body></html>"
    )


CSS = """
:root{color-scheme:light;--ink:#142c3b;--muted:#506675;--line:#d7e2e8;--accent:#076e77}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:#f3f6f8;font:15px/1.6 system-ui,sans-serif}
header,main,footer{max-width:1500px;margin:auto;padding:28px 32px}header{padding-bottom:18px}h1{font-size:40px;line-height:1.2;margin:8px 0}h2{font-size:24px;margin:0 0 16px}h3{font-size:18px}.eyebrow{font-weight:700;letter-spacing:.12em;color:var(--accent);font-size:12px}p{max-width:1150px;color:var(--muted)}nav{position:sticky;top:0;z-index:3;background:#142c3b;display:flex;gap:18px;overflow:auto;padding:12px 32px}nav a{color:#fff;white-space:nowrap;text-decoration:none;font-size:14px}section{background:white;border:1px solid var(--line);border-radius:10px;padding:24px;margin:24px 0;scroll-margin-top:68px}.scroll{overflow:auto;max-width:100%}table{border-collapse:separate;border-spacing:0;width:100%;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top;white-space:nowrap}th:first-child,td:first-child{text-align:left}thead th{background:#e8f1f3;color:#174650}tbody th{font-weight:500;min-width:260px;text-align:left;white-space:normal;position:sticky;left:0;background:inherit}tbody tr:nth-child(odd){background:#f8fafb}tbody tr:nth-child(even){background:white}#inputs td:last-child{white-space:normal;min-width:360px;text-align:left}#inputs th{min-width:100px}#sources td{white-space:normal;overflow-wrap:anywhere}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.cards div{padding:20px;background:#fff;border-top:4px solid var(--accent);border-radius:6px}.cards small{display:block;color:var(--muted)}.cards strong{font-size:25px;display:block;margin-top:8px}.notice{background:#fff5dc;border-left:4px solid #b37912;padding:16px;max-width:none}code{background:#e7eef2;padding:2px 4px;border-radius:3px}a{color:var(--accent)}li{margin:14px 0}footer{font-size:12px;color:var(--muted)}@media(max-width:800px){header,main,footer{padding:20px 14px}.cards{grid-template-columns:repeat(2,1fr)}section{padding:16px}h1{font-size:32px}nav{padding-left:14px}}
"""


def export_report(payload, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "forecast.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (directory / "forecast.html").write_text(report_html(payload), encoding="utf-8")
    return directory / "forecast.html"
