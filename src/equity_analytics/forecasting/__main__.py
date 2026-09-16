"""Run the dated Tega case locally without network access or extra packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import build_forecast
from .inputs import ModelInputError, load_json
from .reporting import write_reports


def main(default_root: Path | None = None, default_base_year: int = 2026) -> None:
    root = default_root or Path.cwd()
    parser = argparse.ArgumentParser(description="Tega reported-history linked model")
    parser.add_argument(
        "--statements",
        type=Path,
        default=root / f"examples/tega_fy{default_base_year}_reported_statements.json",
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=root / f"examples/tega_fy{default_base_year}_forecast_assumptions.json",
    )
    parser.add_argument(
        "--output", type=Path, default=root / f"outputs/tega_fy{default_base_year}"
    )
    args = parser.parse_args()
    try:
        case, assumptions = load_json(args.statements), load_json(args.assumptions)
        result = build_forecast(case, assumptions)
        write_reports(case, result, args.output)
    except (ModelInputError, OSError) as exc:
        print(f"Model stopped: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(
        f"Historical FY{case['base_year']} case; legacy-only illustrative forecast. Acquisition excluded."
    )
    print(f"Historical checks passed: {len(result['historical_checks'])}")
    print(f"Forecast years balanced: {len(result['years'])}")
    print(f"Reports: {args.output.resolve()}")


if __name__ == "__main__":
    main()
