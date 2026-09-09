"""Run the dated Tega case locally without network access or extra packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import build_forecast
from .inputs import ModelInputError, load_json
from .reporting import write_reports


def main(default_root: Path | None = None) -> None:
    root = default_root or Path.cwd()
    parser = argparse.ArgumentParser(description="Tega FY2025 historical model")
    parser.add_argument(
        "--statements",
        type=Path,
        default=root / "examples/tega_fy2025_reported_statements.json",
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=root / "examples/tega_fy2025_forecast_assumptions.json",
    )
    parser.add_argument("--output", type=Path, default=root / "outputs/tega_fy2025")
    args = parser.parse_args()
    try:
        case, assumptions = load_json(args.statements), load_json(args.assumptions)
        result = build_forecast(case, assumptions)
        write_reports(case, result, args.output)
    except (ModelInputError, OSError) as exc:
        print(f"Model stopped: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print("Historical FY2025 case; illustrative forecast, not a current valuation.")
    print(f"Historical checks passed: {len(result['historical_checks'])}")
    print(f"Forecast years balanced: {len(result['years'])}")
    print(f"Reports: {args.output.resolve()}")


if __name__ == "__main__":
    main()
