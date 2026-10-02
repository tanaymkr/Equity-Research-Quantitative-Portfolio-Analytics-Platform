"""Build Wabag's linked statements and DCF from reproducible source snapshots."""

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    from equity_analytics.case_studies.wabag import load_inputs
    from equity_analytics.case_studies.wabag.scenarios import (
        build_scenarios,
        export_scenarios,
    )
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
        config = json.loads(
            (args.inputs / "scenarios.json").read_text(encoding="utf-8")
        )
        payload = build_scenarios(load_inputs(args.inputs), config, store=store)
        path = export_scenarios(payload, args.output)
        for name in ("downside", "base", "upside"):
            case = payload["scenarios"][name]
            if case["status"] == "ok":
                model = case["model"]
                print(
                    f"{name.title()}: INR {model['dcf']['implied_value_per_share']:,.2f} per diluted share; {len(model['checks'])} accounting checks passed."
                )
            else:
                print(f"{name.title()}: needs revision — {case['error']}")
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
