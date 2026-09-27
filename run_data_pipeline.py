"""Load included histories into SQLite and export dated company analyses."""

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    from equity_analytics.data import DataStoreError, FinancialStore
    from equity_analytics.data.__main__ import export_analysis

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", type=Path, default=root / "outputs/data/research.sqlite"
    )
    parser.add_argument("--as-of", default="2026-09-11")
    parser.add_argument("--output", type=Path, default=root / "outputs/data/tega")
    parser.add_argument("--company-id", choices=["TEGA", "WABAG"], default="TEGA")
    args = parser.parse_args(argv)
    try:
        store = FinancialStore(args.db)
        for company_id, filename in (
            ("TEGA", "tega_fy2025_reported_statements.json"),
            ("TEGA", "tega_fy2026_reported_statements.json"),
            ("DEMO", "demo_financial_history.json"),
            ("WABAG", "wabag_fy2026_reported_statements.json"),
        ):
            result = store.ingest_file(
                root / "examples" / filename, company_id=company_id
            )
            print(
                f"{company_id}: {result['status']}; {result['inserted_statements']} new versions"
            )
        report = export_analysis(store, args.company_id, args.as_of, args.output)
        print(json.dumps(store.inventory(), indent=2))
        print(f"Database: {args.db.resolve()}")
        print(
            f"{args.company_id} publication cutoff: {args.as_of}; {len(report.years)} annual periods"
        )
        print(f"Open: {(args.output / 'analysis.html').resolve()}")
        print("DEMO is synthetic test data. TEGA and WABAG use sourced reported statements.")
    except (DataStoreError, OSError) as exc:
        parser.exit(2, f"Data step stopped: {exc}\n")


if __name__ == "__main__":
    main()
