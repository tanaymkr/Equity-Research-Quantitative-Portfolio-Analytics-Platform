"""Generate all three acquisition scenarios from the source register."""

import argparse
import json
import math
from pathlib import Path

from equity_analytics.forecasting.inputs import ModelInputError, load_json

from .engine import AcquisitionInputError, build_acquisition_model
from .history import load_acquisition_facts
from .reporting import write_reports


def main(default_root=None):
    root = Path(default_root or Path.cwd())
    parser = argparse.ArgumentParser(
        description="Tega + Molycop single attributable group DCF"
    )
    parser.add_argument(
        "--facts", type=Path, default=root / "examples/tega_molycop_facts.json"
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=root / "examples/tega_molycop_assumptions.json",
    )
    parser.add_argument(
        "--statements", type=Path, help="Override the complete FY26 statement source"
    )
    parser.add_argument("--output", type=Path, default=root / "outputs/tega_molycop")
    parser.add_argument(
        "--reference-price",
        type=float,
        help="Optional unverified comparison price; never calibrates the DCF",
    )
    args = parser.parse_args()
    if args.reference_price is not None and (
        not math.isfinite(args.reference_price) or args.reference_price <= 0
    ):
        parser.error("--reference-price must be a positive finite number")
    try:
        facts, statements, historical_checks = load_acquisition_facts(
            args.facts, args.statements
        )
        assumptions = load_json(args.assumptions)
        results = {
            name: build_acquisition_model(facts, assumptions, name)
            for name in ("downside", "base", "upside")
        }
        write_reports(
            facts,
            assumptions,
            results,
            args.output,
            args.reference_price,
            statements=statements,
            historical_checks=historical_checks,
        )
    except (
        OSError,
        json.JSONDecodeError,
        AcquisitionInputError,
        ModelInputError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        parser.exit(1, f"Model could not run: {exc}\n")
    print(
        "PROVISIONAL single group DCF; value date 2026-06-30; research through 2026-09-11."
    )
    print("Amounts: INR million. USD conversion: 94.97, market close on 2026-09-02.")
    print(
        "Legacy statement gaps filled using schedules/history/assumed zeros; Molycop remains partial."
    )
    gap = results["base"]["legacy_statement_opening_inr_m"][
        "balance_sheet_residual_inr_m"
    ]
    print(
        f"Estimated legacy June opening balance discrepancy: INR{gap:,.3f}m; no plug."
    )
    print(f"FY26 statement reconciliation checks passed: {len(historical_checks)}")
    for name, result in results.items():
        b = result["equity_bridge"]
        text = (
            "equity shortfall under stress (zero floor)"
            if b["raw_tega_equity_inr_m"] < 0
            else f"INR {b['value_per_share_inr']:,.2f}/share"
        )
        print(f"{name.title()}: {text}")
    print("Opening cash, working capital and preference terms remain provisional.")
    print(f"Open the report: {(args.output / 'report.html').resolve()}")


if __name__ == "__main__":
    main()
