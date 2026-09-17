"""Run the reusable linked engine with explicitly supplied research inputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import build_forecast
from .inputs import ModelInputError, load_json
from .reporting import write_reports


def main(default_root: Path | None = None) -> None:
    root = default_root or Path.cwd()
    parser = argparse.ArgumentParser(description="Generic reported-history linked model")
    parser.add_argument(
        "--statements",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output", type=Path, default=root / "outputs/linked_forecast"
    )
    args = parser.parse_args()
    try:
        case, assumptions = load_json(args.statements), load_json(args.assumptions)
        result = build_forecast(case, assumptions)
        write_reports(case, result, args.output)
    except (ModelInputError, OSError) as exc:
        print(f"Model stopped: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(f"Custom linked forecast from FY{case['base_year']} reported statements.")
    print(f"Historical checks passed: {len(result['historical_checks'])}")
    print(f"Forecast years balanced: {len(result['years'])}")
    print(f"Reports: {args.output.resolve()}")


if __name__ == "__main__":
    main()
