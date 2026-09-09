"""Compare explicit scenarios and recalculate WACC/g sensitivity locally."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    from equity_analytics.forecasting import ModelInputError, build_forecast, load_json
    from equity_analytics.forecasting.reporting import write_reports

    parser = argparse.ArgumentParser(description="Tega FY2025 illustrative scenarios")
    parser.add_argument("--output", type=Path, default=root / "outputs/tega_scenarios")
    args = parser.parse_args()
    case = load_json(root / "examples/tega_fy2025_reported_statements.json")
    files = {
        "base": "tega_fy2025_forecast_assumptions.json",
        "downside": "tega_fy2025_downside_assumptions.json",
        "upside": "tega_fy2025_upside_assumptions.json",
    }
    summary = []
    base_assumptions = load_json(root / "examples" / files["base"])
    for label, filename in files.items():
        a = load_json(root / "examples" / filename)
        try:
            r = build_forecast(case, a)
        except ModelInputError as exc:
            summary.append({"scenario": label, "available": False, "reason": str(exc)})
            continue
        write_reports(case, r, args.output / label)
        summary.append(
            {
                "scenario": label,
                "available": True,
                "first_year_growth": a["revenue_growth"][0],
                "first_year_ebitda_margin": a["ebitda_margin"][0],
                "first_year_receivable_days": a["receivable_days"][0],
                "final_year_revenue": r["years"][-1]["income"]["revenue"],
                "final_year_cash": r["years"][-1]["cash_flow"]["closing_cash"],
                "maximum_forecast_revolver": max(
                    y["balance_sheet"]["liabilities"]["revolver"] for y in r["years"]
                ),
                "value_per_share_inr": r["dcf"].get("value_per_share_inr"),
                "maximum_balance_residual": max(
                    abs(y["checks"]["balance_sheet_residual"]) for y in r["years"]
                ),
            }
        )
    sensitivity = []
    for wacc in [0.10, 0.12, 0.14]:
        for growth in [0.03, 0.04, 0.05]:
            a = deepcopy(base_assumptions)
            a["dcf"].update({"wacc": wacc, "terminal_growth": growth})
            d = build_forecast(case, a)["dcf"]
            sensitivity.append(
                {
                    "wacc": wacc,
                    "growth": growth,
                    "value_per_share_inr": d.get("value_per_share_inr"),
                }
            )
    lines = [
        "# Tega historical FY2025 case: illustrative scenarios",
        "",
        (
            "These are assumption experiments, not company guidance or a current "
            "valuation. All historical inputs remain the audited FY2024/FY2025 "
            "figures; modeled FY2026–FY2030 values are forecasts."
        ),
        "",
        (
            "All scenarios retain base capex, financing, tax, asset-life and "
            "DCF assumptions. Their growth, EBITDA margin and working-capital "
            "inputs differ; the complete JSON files are the source of each scenario. "
            "No probabilities are assigned."
        ),
        "",
        (
            "| Scenario | First-year growth | EBITDA margin | Collection days | "
            "FY2030 revenue (INR million) | Illustrative INR/share |"
        ),
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary:
        if not row["available"]:
            lines.append(
                f"| {row['scenario']} | Unavailable: {row['reason']} | | | | |"
            )
            continue
        value = row["value_per_share_inr"]
        value_text = f"{value:,.2f}" if value is not None else "Unavailable"
        lines.append(
            f"| {row['scenario']} | {row['first_year_growth']:.1%} | "
            f"{row['first_year_ebitda_margin']:.1%} | {row['first_year_receivable_days']} | "
            f"{row['final_year_revenue']:,.2f} | {value_text} |"
        )
    lines += [
        "",
        "## Base-case WACC and terminal growth sensitivity",
        "",
        (
            "Values are illustrative INR/share. Terminal ROIC remains 15%; "
            "changing growth also changes required terminal reinvestment."
        ),
        "",
        "| WACC | g = 3% | g = 4% | g = 5% |",
        "| --- | --- | --- | --- |",
    ]
    for wacc in [0.10, 0.12, 0.14]:
        values = [r["value_per_share_inr"] for r in sensitivity if r["wacc"] == wacc]
        lines.append(
            f"| {wacc:.0%} | "
            + " | ".join(
                f"{v:,.2f}" if v is not None else "Unavailable" for v in values
            )
            + " |"
        )
    lines += [
        "",
        "## Read the full model",
        "",
        "- [Base forecast and supporting schedules](base/forecast.md)",
        "- [Downside forecast and supporting schedules](downside/forecast.md)",
        "- [Upside forecast and supporting schedules](upside/forecast.md)",
        "- [Audited historical statements](base/historical_statements.md)",
        "",
        (
            "Reproduce this report with `python run_tega_scenarios.py`. "
            "It writes fresh outputs under `outputs/tega_scenarios`."
        ),
        "",
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "scenarios.md").write_text("\n".join(lines), encoding="utf-8")
    (args.output / "scenarios.json").write_text(
        json.dumps(
            {
                "label": "Historical FY2025; illustrative scenarios",
                "scenarios": summary,
                "sensitivity": sensitivity,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Scenario and sensitivity reports: {args.output.resolve()}")


if __name__ == "__main__":
    main()
