"""Command-line entry point for the valuation module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from equity_analytics.valuation.dcf import (
    DCFAssumptions,
    HistoricalSnapshot,
    calculate_dcf,
)
from equity_analytics.valuation.sensitivity import sensitivity_matrix


def _load_model(path: Path) -> tuple[HistoricalSnapshot, DCFAssumptions]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    company = payload["company"]
    assumptions = payload["assumptions"]

    snapshot = HistoricalSnapshot(
        company_name=company["name"],
        base_year=company["base_year"],
        revenue=company["revenue"],
        cash=company["cash"],
        debt=company["debt"],
        shares_outstanding=company["shares_outstanding"],
        currency=company.get("currency", "INR"),
        financial_unit=company.get("financial_unit", "crore"),
    )
    dcf_assumptions = DCFAssumptions.from_sequences(**assumptions)
    return snapshot, dcf_assumptions


def _print_forecast(result: Any) -> None:
    print(f"\nDCF valuation — {result.company_name}")
    print("-" * 86)
    print(
        f"{'Year':>6} {'Growth':>9} {'Revenue':>13} {'EBIT':>13} "
        f"{'FCFF':>13} {'PV of FCFF':>14}"
    )
    for year in result.forecast:
        print(
            f"{year.year:>6} {year.revenue_growth:>8.1%} "
            f"{year.revenue:>13,.2f} {year.ebit:>13,.2f} "
            f"{year.fcff:>13,.2f} {year.present_value_fcff:>14,.2f}"
        )


def _print_summary(result: Any) -> None:
    unit = result.financial_unit
    print("\nValuation summary")
    print(f"Enterprise value:          {result.enterprise_value:>12,.2f} {unit}")
    print(f"Add: cash:                 {result.cash:>12,.2f} {unit}")
    print(f"Less: debt:                {result.debt:>12,.2f} {unit}")
    print(f"Equity value:              {result.equity_value:>12,.2f} {unit}")
    print(
        f"Implied value per share:   {result.implied_value_per_share:>12,.2f} "
        f"{result.currency}"
    )


def _print_sensitivity(
    snapshot: HistoricalSnapshot,
    assumptions: DCFAssumptions,
) -> None:
    wacc_values = tuple(assumptions.wacc + offset for offset in (-0.01, -0.005, 0, 0.005, 0.01))
    growth_values = tuple(
        assumptions.terminal_growth + offset for offset in (-0.005, 0, 0.005)
    )
    matrix = sensitivity_matrix(
        snapshot,
        assumptions,
        wacc_values=wacc_values,
        terminal_growth_values=growth_values,
    )

    print("\nImplied value/share sensitivity")
    print(f"{'g / WACC':>10}" + "".join(f"{rate:>12.1%}" for rate in wacc_values))
    for growth, row in matrix.items():
        values = "".join(
            f"{value:>12,.2f}" if value is not None else f"{'N/A':>12}"
            for value in row.values()
        )
        print(f"{growth:>10.1%}{values}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an FCFF DCF valuation")
    parser.add_argument("input", type=Path, help="Path to a DCF input JSON file")
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for the complete valuation result",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    snapshot, assumptions = _load_model(args.input)
    result = calculate_dcf(snapshot, assumptions)

    _print_forecast(result)
    _print_summary(result)
    _print_sensitivity(snapshot, assumptions)

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(result.to_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"\nSaved full result to {args.json_output}")


if __name__ == "__main__":
    main()

