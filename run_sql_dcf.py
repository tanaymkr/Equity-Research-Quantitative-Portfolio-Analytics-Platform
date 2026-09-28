"""Run a company's annual DCF from SQLite and a separate assumptions file."""

import argparse
import sys
from pathlib import Path


def main(argv=None):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    from equity_analytics.data import DataStoreError, FinancialStore
    from equity_analytics.valuation.sql_dcf import export_sql_dcf

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", type=Path, default=root / "outputs/data/research.sqlite"
    )
    parser.add_argument(
        "--assumptions", type=Path, default=root / "examples/wabag_dcf_assumptions.json"
    )
    parser.add_argument("--output", type=Path, default=root / "outputs/valuation/wabag")
    args = parser.parse_args(argv)
    try:
        if not args.db.is_file():
            raise ValueError("Database missing. Run Run_Wabag_Analysis.bat first.")
        payload = export_sql_dcf(FinancialStore(args.db), args.assumptions, args.output)
        for name, case in payload["scenarios"].items():
            print(
                f"{name}: {payload['snapshot']['currency']} {case['result']['implied_value_per_share']:,.2f}/share (model estimate)"
            )
        print(payload["warning"])
        print(f"Open: {(args.output / 'valuation.html').resolve()}")
    except (
        DataStoreError,
        ValueError,
        TypeError,
        KeyError,
        OSError,
        OverflowError,
    ) as exc:
        parser.exit(2, f"DCF stopped: {exc}\n")


if __name__ == "__main__":
    main()
