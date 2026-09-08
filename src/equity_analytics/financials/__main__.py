"""Run with python -m equity_analytics.financials INPUT.json."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from equity_analytics.financials.io import load_history
from equity_analytics.financials.models import FinancialDataError
from equity_analytics.financials.ratios import AnalysisReport, Metric, analyze_history


def format_metric(metric: Metric) -> str:
    if metric.value is None:
        return "N/A"
    if metric.unit == "fraction":
        return f"{metric.value:.2%}"
    if metric.unit == "multiple":
        return f"{metric.value:.2f}x"
    return f"{metric.value:,.2f}"


def report_markdown(report: AnalysisReport) -> str:
    company = report.history.company
    lines = [
        f"# Financial history: {company.name}",
        "",
        f"{company.ticker} | {company.statement_basis} | {company.data_kind}",
        f"Money: {company.currency} {company.financial_unit}; as of {report.history.as_of}.",
        "",
        "| Metric | " + " | ".join(f"FY{y.fiscal_year}" for y in report.years) + " |",
        "| --- | " + " | ".join("---:" for _ in report.years) + " |",
    ]
    for name in report.years[0].metrics:
        lines.append(
            "| "
            + name.replace("_", " ")
            + " | "
            + " | ".join(format_metric(year.metrics[name]) for year in report.years)
            + " |"
        )
    lines += [
        "",
        (
            f"Revenue CAGR: {format_metric(report.revenue_cagr)} "
            f"over {report.cagr_intervals} annual intervals."
        ),
    ]
    if report.history.notes:
        lines += ["", report.history.notes]
    lines += ["", "## Unavailable metrics and checks", ""]
    for year in report.years:
        for name, metric in year.metrics.items():
            if metric.reason:
                lines.append(f"- FY{year.fiscal_year} {name}: {metric.reason}.")
        for warning in year.warnings:
            lines.append(f"- FY{year.fiscal_year} CHECK: {warning}.")
    lines += ["", "## Sources and normalization notes", ""]
    for source in report.history.sources:
        title = f"[{source.title}]({source.url})" if source.url else source.title
        lines.append(
            f"- {source.source_id}: {title}, published {source.published_on}; {source.locator}."
        )
    for annual in report.history.annuals:
        if annual.notes:
            lines.append(f"- FY{annual.fiscal_year}: {annual.notes}")
    lines += [
        "",
        (
            "CFO less capex is not automatically FCFF. Returns use average balances. "
            "The first period needs an earlier balance sheet for return metrics."
        ),
        "",
    ]
    return "\n".join(lines)


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"unsupported JSON type: {type(value).__name__}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Analyze normalized annual financial statements"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, help="Write analysis.json and analysis.md"
    )
    args = parser.parse_args(argv)
    try:
        history = load_history(args.input)
        report = analyze_history(history)
        print(report_markdown(report))
        if args.output_dir:
            targets = [
                args.output_dir / "analysis.json",
                args.output_dir / "analysis.md",
            ]
            if any(target.resolve() == args.input.resolve() for target in targets):
                raise FinancialDataError("output must not overwrite the input file")
            args.output_dir.mkdir(parents=True, exist_ok=True)
            targets[0].write_text(
                json.dumps(
                    report.to_dict(), indent=2, allow_nan=False, default=_json_default
                )
                + "\n",
                encoding="utf-8",
            )
            targets[1].write_text(report_markdown(report), encoding="utf-8")
    except (FinancialDataError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
