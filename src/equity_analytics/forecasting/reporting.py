"""Readable reports generated from the same calculated records as the JSON output."""

from __future__ import annotations

import json
from pathlib import Path

from .inputs import historical_rolls


def money(value: float) -> str:
    return f"{value:,.2f}"


def _table(labels: list[str], rows: list[tuple]) -> list[str]:
    return [
        "| " + " | ".join(labels) + " |",
        "| " + " | ".join(["---"] * len(labels)) + " |",
        *["| " + " | ".join(str(v) for v in row) + " |" for row in rows],
        "",
    ]


def historical_tables(case, checks):
    """One table source for HTML and Markdown, including every cash-flow line."""
    annuals = case["annuals"]
    labels = ["Account"] + [f"FY{y['fiscal_year']} actual" for y in annuals]
    for title, section in [
        ("Income statement", "income"),
        ("Assets", "assets"),
        ("Liabilities", "liabilities"),
        ("Equity", "equity"),
        ("Reported classifications and totals", "reported_totals"),
    ]:
        yield (
            title,
            labels,
            [
                [k.replace("_", " ")]
                + [
                    f"{y[section][k]:.6f}"
                    if k == "shares_outstanding_million"
                    else money(y[section][k])
                    for y in annuals
                ]
                for k in annuals[0][section]
            ],
        )
    rows = [
        ["Profit before tax"]
        + [money(y["income"]["profit_before_tax"]) for y in annuals]
    ]
    for section in [
        "operating_adjustments",
        "working_capital_movements",
        "investing",
        "financing",
    ]:
        if section == "investing":
            for key in ["income_tax_paid", "operating_total"]:
                rows.append(
                    [key.replace("_", " ")]
                    + [money(y["cash_flow"][key]) for y in annuals]
                )
        names = dict.fromkeys(k for y in annuals for k in y["cash_flow"][section])
        rows.extend(
            [
                [k.replace("_", " ")]
                + [money(y["cash_flow"][section].get(k, 0)) for y in annuals]
                for k in names
            ]
        )
        if section in {"investing", "financing"}:
            rows.append(
                [section + " total"]
                + [money(y["cash_flow"][section + "_total"]) for y in annuals]
            )
    for key in ["opening_cash", "exchange_effect_on_cash", "closing_cash"]:
        rows.append(
            [key.replace("_", " ")] + [money(y["cash_flow"][key]) for y in annuals]
        )
    yield "Cash flow statement", labels, rows
    for section, data in case.get("base_year_disclosures", {}).items():
        values = data if isinstance(data, dict) else {section: data}
        yield (
            f"FY{case['base_year']} {section.replace('_', ' ')}",
            ["Disclosed item", "Value (INR m unless shares/EPS)"],
            [
                [k.replace("_", " "), f"{v:.6f}" if "shares_million" in k else money(v)]
                for k, v in values.items()
            ],
        )
    for name, roll in historical_rolls(case).items():
        yield (
            f"FY{case['base_year']} {name.replace('_', ' ')}",
            ["Movement", "INR million"],
            [[k.replace("_", " "), money(v)] for k, v in roll.items()],
        )
    yield (
        "Historical reconciliation checks",
        ["Check", "Calculated minus reported", "Result"],
        [
            [c["name"], f"{c['residual']:.6f}", "PASS" if c["passed"] else "FAIL"]
            for c in checks
        ],
    )


def historical_markdown(case: dict, result: dict) -> str:
    source = case["source"]
    years = ", ".join(f"FY{y['fiscal_year']}" for y in case["annuals"])
    lines = [
        f"# Tega: audited {years} statements",
        "",
        "Consolidated; INR million. One crore = ten million. Shares use million units except the explicitly labeled new-share count; EPS and issue price are INR/share.",
        "",
        f"Source: [{source['title']}]({source['url']}). Information cutoff: {case['as_of']}.",
        "",
        "These are reported actuals. Forecast assumptions and later acquisition adjustments are separate. Historical rounding tolerance: INR0.02m; no balancing entry is inserted.",
        "",
    ]
    for title, labels, rows in historical_tables(case, result["historical_checks"]):
        lines += [f"## {title}", ""] + _table(labels, rows)
    lines += ["## Source locations", ""] + [
        f"- {k.replace('_', ' ')}: {v}" for k, v in source["locators"].items()
    ]
    lines += ["", "## Notes", ""] + [f"- {n}" for n in case["notes"]] + [""]
    return "\n".join(lines)


def write_historical_reports(case, checks, output):
    from html import escape

    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    (path / "historical_statements.md").write_text(
        historical_markdown(case, {"historical_checks": checks}), encoding="utf-8"
    )
    (path / "reported_statements_used.json").write_text(
        json.dumps(case, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (path / "historical_checks.json").write_text(
        json.dumps(checks, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    html = [
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Tega reported statements</title><style>body{font:16px/1.5 system-ui,sans-serif;color:#172536;max-width:1100px;margin:auto;padding:24px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#edf2f8}.wrap{overflow-x:auto}h2{margin-top:30px}</style>",
        f"<h1>Tega: FY{case['base_year']} reported statements</h1><p>Consolidated; INR million. Historical statements and supporting notes. Shares are in millions except the new-share count; EPS and issue price are INR/share.</p><p><a href='{escape(case['source']['url'], quote=True)}'>Official annual report</a> · {len(checks)} reconciliation checks passed.</p>",
    ]
    for title, labels, rows in historical_tables(case, checks):
        html += [
            f"<h2>{escape(title)}</h2><div class='wrap'><table><thead><tr>"
            + "".join(f"<th>{escape(str(v))}</th>" for v in labels)
            + "</tr></thead><tbody>"
        ]
        html += [
            "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
            for row in rows
        ]
        html += ["</tbody></table></div>"]
    html += (
        ["<h2>Source locations</h2><ul>"]
        + [
            f"<li>{escape(k)}: {escape(v)}</li>"
            for k, v in case["source"]["locators"].items()
        ]
        + ["</ul><h2>Notes</h2><ul>"]
    )
    html += [f"<li>{escape(note)}</li>" for note in case["notes"]] + ["</ul></html>"]
    (path / "historical_statements.html").write_text("\n".join(html), encoding="utf-8")


def forecast_markdown(result: dict) -> str:
    years, dcf = result["years"], result["dcf"]
    labels = ["Metric"] + [f"FY{y['fiscal_year']} forecast" for y in years]
    lines = [
        "# Tega: linked financial forecast",
        "",
        result["label"],
        "",
        (
            f"**Historical FY{result.get('base_year', 2025)} case. Forecast values are illustrative. "
            "This is not a current Tega valuation or company guidance.**"
        ),
        "",
        "Consolidated; INR million, except value per share in INR. "
        "Information cutoff: " + result["as_of"] + ".",
        "",
        "## Income statement",
        "",
    ]
    lines += _table(
        labels,
        [
            (k.replace("_", " "), *[money(y["income"][k]) for y in years])
            for k in years[0]["income"]
        ],
    )
    for section in ["assets", "liabilities", "equity"]:
        lines += [f"## Balance sheet: {section}", ""]
        lines += _table(
            labels,
            [
                (
                    k.replace("_", " "),
                    *[money(y["balance_sheet"][section][k]) for y in years],
                )
                for k in years[0]["balance_sheet"][section]
            ],
        )
    lines += ["## Balance sheet totals", ""]
    lines += _table(
        labels,
        [
            (k.replace("_", " "), *[money(y["balance_sheet"][k]) for y in years])
            for k in ["total_assets", "total_liabilities", "total_equity"]
        ],
    )
    lines += ["## Cash flow statement", ""]
    lines += _table(
        labels,
        [
            (k.replace("_", " "), *[money(y["cash_flow"][k]) for y in years])
            for k in years[0]["cash_flow"]
        ],
    )
    lines += [
        "## FCFF",
        "",
        (
            "FCFF = EBIT − operating cash tax + D&A − cash capex "
            "− new leased assets − change in operating working capital. "
            "Lease additions are included because leases are treated as debt. "
            "Debt interest and principal payments do not reduce FCFF."
        ),
        "",
    ]
    lines += _table(
        labels,
        [
            (k.replace("_", " "), *[money(y[k]) for y in years])
            for k in [
                "nopat",
                "delta_operating_working_capital",
                "new_leased_assets_economic_capex",
                "fcff",
            ]
        ],
    )
    lines += ["## Historical DCF illustration", ""]
    if dcf["available"]:
        lines += [
            (
                f"Fiscal-year-end reference: 31 March {result.get('base_year', 2025)}; information cutoff {result['as_of']}. "
                "This is not a point-in-time March backtest. "
                "All WACC, terminal and nonoperating value inputs are assumptions."
            ),
            "",
        ]
        lines += _table(
            ["Item", "Value"],
            [
                ("Enterprise value (INR million)", money(dcf["enterprise_value"])),
                *[(k.replace("_", " "), money(v)) for k, v in dcf["bridge"].items()],
                ("Equity value (INR million)", money(dcf["equity_value"])),
                (
                    "Shares outstanding (million)",
                    f"{dcf['shares_outstanding_million']:.6f}",
                ),
                (
                    "Illustrative value per share (INR)",
                    money(dcf["value_per_share_inr"]),
                ),
                (
                    "PV terminal value / enterprise value",
                    f"{dcf['terminal_share_of_enterprise_value']:.1%}",
                ),
            ],
        )
        lines += [
            (
                "Terminal FCFF uses terminal NOPAT × (1 − g / terminal ROIC). "
                "Current investments are assumed realizable at reported value. "
                "JV and investment-property values are separate assumptions. "
                "Other bank balances are not added as surplus cash."
            ),
            "",
        ]
    else:
        lines += ["DCF unavailable: " + dcf["reason"], ""]
    lines += [
        "## Forecast integrity",
        "",
        (
            "Balances are calculated from schedules. A funding gap draws on the "
            "explicit assumed revolver; an exceeded limit stops calculation."
        ),
        "",
    ]
    lines += _table(
        labels,
        [
            (k.replace("_", " "), *[f"{y['checks'][k]:.8f}" for y in years])
            for k in years[0]["checks"]
        ],
    )
    for y in years:
        lines += [f"## FY{y['fiscal_year']} debt schedule", ""]
        lines += _table(
            [
                "Pool",
                "Opening",
                "Cash draw",
                "New leases (noncash)",
                "Principal paid",
                "Interest paid",
                "Closing",
            ],
            [
                (
                    r["pool"],
                    *[
                        money(r[k])
                        for k in [
                            "opening",
                            "cash_draw",
                            "noncash_new_leases",
                            "principal_repayment",
                            "interest_expense_and_cash_paid",
                            "closing",
                        ]
                    ],
                )
                for r in y["debt_schedule"]
            ],
        )
        lines += [f"## FY{y['fiscal_year']} asset schedule", ""]
        lines += _table(
            ["Cohort", "Opening net", "Additions", "D&A", "Closing net"],
            [
                (
                    r["name"],
                    *[
                        money(r[k])
                        for k in [
                            "opening",
                            "additions",
                            "depreciation_amortisation",
                            "closing",
                        ]
                    ],
                )
                for r in y["asset_schedule"]
                if any(r[k] for k in ["opening", "additions"])
            ],
        )
        lines += _table(
            ["Construction", "Opening", "Cash capex", "Commissioned", "Closing"],
            [
                (
                    k,
                    *[
                        money(r[f])
                        for f in [
                            "opening",
                            "cash_additions",
                            "commissioned",
                            "closing",
                        ]
                    ],
                )
                for k, r in y["construction_schedule"].items()
            ],
        )
    lines += [
        "## Assumptions and limitations",
        "",
        *[f"- {note}" for note in result["assumptions"]["notes"]],
        "",
        (
            "The JSON output contains the complete inputs, source locators and "
            "unrounded calculated amounts."
        ),
        "",
    ]
    return "\n".join(lines)


def write_reports(case: dict, result: dict, output: str | Path) -> None:
    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    (path / "model.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (path / "forecast.md").write_text(forecast_markdown(result), encoding="utf-8")
    write_historical_reports(case, result["historical_checks"], path)
