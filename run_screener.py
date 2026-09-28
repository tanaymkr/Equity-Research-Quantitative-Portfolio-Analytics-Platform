"""Screen SQL financials using editable filters; unavailable metrics count as zero."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def main(argv=None):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    from equity_analytics.data import DataStoreError, FinancialStore
    from equity_analytics.screening import screen_companies
    from equity_analytics.screening.reporting import export_screener

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", type=Path, default=root / "outputs/data/research.sqlite"
    )
    parser.add_argument(
        "--config", type=Path, default=root / "examples/screener_config.json"
    )
    parser.add_argument("--output", type=Path, default=root / "outputs/screener")
    parser.add_argument("--as-of", help="Override the publication cutoff, YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        if not args.db.is_file():
            raise ValueError("Database missing. Run Run_Wabag_Analysis.bat first.")
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if args.as_of:
            config["as_of"] = args.as_of
        result = screen_companies(FinancialStore(args.db), config)
        export_screener(result, args.output, protected_paths=[args.db, args.config])
        print(json.dumps(result["counts"]))
        for row in result["matches"]:
            print(f"{row['position']}. {row['company_name']} — {row['period_end']}")
        print("Missing/unavailable metrics = 0; substitutions are flagged.")
        print(f"Open: {(args.output / 'screener.html').resolve()}")
    except (
        DataStoreError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        sqlite3.Error,
    ) as exc:
        parser.exit(2, f"Screener stopped: {exc}\n")


if __name__ == "__main__":
    main()
