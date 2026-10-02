"""Build Wabag's linked statements and DCF from reproducible source snapshots."""

import argparse
import sys
from pathlib import Path


def main(argv=None):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    from equity_analytics.case_studies.wabag import build_model, load_inputs
    from equity_analytics.case_studies.wabag.reporting import export_report
    from equity_analytics.data import DataStoreError, FinancialStore

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=root / "examples/wabag_linked")
    parser.add_argument(
        "--db", type=Path, default=root / "outputs/data/research.sqlite"
    )
    parser.add_argument("--output", type=Path, default=root / "outputs/forecasts/wabag")
    args = parser.parse_args(argv)
    try:
        store = FinancialStore(args.db)
        # Idempotent source loading also supports a freshly extracted repository.
        for year in (2024, 2026):
            store.ingest_file(
                root / f"examples/wabag_fy{year}_reported_statements.json",
                company_id="WABAG",
            )
        payload = build_model(load_inputs(args.inputs), store=store)
        path = export_report(payload, args.output)
        print(
            f"Linked model: {len(payload['checks'])} accounting checks passed; {len(payload['sql_crosschecks'])} SQL values matched."
        )
        print(
            f"Illustrative DCF: INR {payload['dcf']['implied_value_per_share']:,.2f} per diluted share."
        )
        print(payload["convention"])
        print(f"Open: {path.resolve()}")
    except (
        DataStoreError,
        ValueError,
        TypeError,
        KeyError,
        OSError,
        OverflowError,
    ) as exc:
        parser.exit(2, f"Wabag forecast stopped: {exc}\n")


if __name__ == "__main__":
    main()
