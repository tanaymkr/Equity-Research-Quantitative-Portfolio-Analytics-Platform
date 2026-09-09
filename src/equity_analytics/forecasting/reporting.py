"""Readable reports generated from the same calculated records as the JSON output."""

from __future__ import annotations

import json
from pathlib import Path


def money(value: float) -> str:
    return f"{value:,.2f}"


def _table(labels: list[str], rows: list[tuple]) -> list[str]:
    return [
        "| " + " | ".join(labels) + " |",
        "| " + " | ".join(["---"] * len(labels)) + " |",
        *["| " + " | ".join(str(v) for v in row) + " |" for row in rows],
        "",
    ]


def historical_markdown(case: dict, result: dict) -> str:
    source = case["source"]
    annuals = case["annuals"]
    lines = [
        "# Tega: audited FY2024 and FY2025 historical statements",
        "",
        "Consolidated; INR million. One crore = ten million.",
        "",
        (
            f"Source: [{source['title']}]({source['url']}). "
            f"Information cutoff: {case['as_of']}."
        ),
        "",
        (
            "These are reported historical figures. The separate forecast uses "
            "illustrative analyst assumptions and does not incorporate FY2026 "
            "results or subsequent acquisitions."
        ),
        "",
    ]
    for title, section in [
        ("Income statement", "income"),
        ("Assets", "assets"),
        ("Liabilities", "liabilities"),
        ("Equity", "equity"),
    ]:
        lines += [f"## {title}", ""]
        lines += _table(
            ["Account", "FY2024 actual", "FY2025 actual"],
            [
                (k.replace("_", " "), *[money(y[section][k]) for y in annuals])
                for k in annuals[0][section]
            ],
        )
    lines += [
        (
            "Liabilities use principal pools: term debt includes its current "
            "maturities; the revolver excludes those maturities. Lease principal "
            "is separate. Other reserves exclude retained earnings."
        ),
        "",
        "## Reported balance sheet classifications and totals",
        "",
    ]
    lines += _table(
        ["Account", "FY2024 actual", "FY2025 actual"],
        [
            (k.replace("_", " "), *[money(y["reported_totals"][k]) for y in annuals])
            for k in annuals[0]["reported_totals"]
            if k != "shares_outstanding_million"
        ],
    )
    lines += [
        "Shares outstanding: 66.535492 million in both years (note 19A).",
        "",
        "## Cash flow statement",
        "",
        "Cash inflows/addbacks are positive; cash outflows/deductions are negative.",
        "",
    ]
    cf_rows = [
        (
            "Profit before tax",
            *[money(y["income"]["profit_before_tax"]) for y in annuals],
        )
    ]
    for section in ["operating_adjustments", "working_capital_movements"]:
        cf_rows += [
            (k.replace("_", " "), *[money(y["cash_flow"][section][k]) for y in annuals])
            for k in annuals[0]["cash_flow"][section]
        ]
    for k in ["income_tax_paid", "operating_total"]:
        cf_rows.append(
            (k.replace("_", " "), *[money(y["cash_flow"][k]) for y in annuals])
        )
    for section in ["investing", "financing"]:
        cf_rows += [
            (k.replace("_", " "), *[money(y["cash_flow"][section][k]) for y in annuals])
            for k in annuals[0]["cash_flow"][section]
        ]
        cf_rows.append(
            (
                section + " total",
                *[money(y["cash_flow"][section + "_total"]) for y in annuals],
            )
        )
    for k in ["opening_cash", "exchange_effect_on_cash", "closing_cash"]:
        cf_rows.append(
            (k.replace("_", " "), *[money(y["cash_flow"][k]) for y in annuals])
        )
    lines += _table(["Account", "FY2024 actual", "FY2025 actual"], cf_rows)
    lines += [
        "## FY2025 supporting reconciliations",
        "",
        (
            "Positive debt movements increase the liability. Interest accruals "
            "and payments cancel when equal; FX and new leases can change debt "
            "without borrowing cash. 'Other' preserves the source classification."
        ),
        "",
    ]
    for name, roll in case["fy2025_reconciliations"].items():
        lines += [f"### {name.replace('_', ' ')}", ""]
        lines += _table(
            ["Movement", "INR million"],
            [(k.replace("_", " "), money(v)) for k, v in roll.items()],
        )
    lines += [
        "## Source reconciliation checks",
        "",
        (
            "Tolerance is INR 0.02 million for the report's rounding. "
            "Residuals are displayed; no adjustment is inserted."
        ),
        "",
    ]
    lines += _table(
        ["Check", "Calculated minus reported", "Result"],
        [
            (c["name"], f"{c['residual']:.4f}", "PASS" if c["passed"] else "FAIL")
            for c in result["historical_checks"]
        ],
    )
    lines += ["## Notes", "", *[f"- {n}" for n in case["notes"]], ""]
    return "\n".join(lines)


def forecast_markdown(result: dict) -> str:
    years, dcf = result["years"], result["dcf"]
    labels = ["Metric"] + [f"FY{y['fiscal_year']} forecast" for y in years]
    lines = [
        "# Tega: linked financial forecast",
        "",
        result["label"],
        "",
        (
            "**Historical FY2025 case. Forecast values are illustrative. "
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
                "Fiscal-year-end reference: 31 March 2025; information was available "
                "by 26 August 2025. This is not a point-in-time March backtest. "
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
    (path / "historical_statements.md").write_text(
        historical_markdown(case, result), encoding="utf-8"
    )
