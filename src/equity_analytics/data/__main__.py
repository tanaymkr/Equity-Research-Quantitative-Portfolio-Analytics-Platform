"""Import files, inspect the database, and export dated financial analysis."""

import argparse
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from equity_analytics.financials.__main__ import report_markdown
from equity_analytics.financials.ratios import analyze_history

from .reporting import analysis_html
from .store import DataStoreError, FinancialStore


def _json_default(value):
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def export_analysis(store, company_id, as_of, output, *, basis="consolidated"):
    history = store.history_as_of(company_id, as_of, basis=basis)
    report = analyze_history(history)
    output = Path(output)
    targets = [
        output / name
        for name in ("history.json", "analysis.json", "analysis.md", "analysis.html")
    ]
    if store.path.resolve() in [target.resolve() for target in targets]:
        raise DataStoreError("Report output must not overwrite the database")
    output.mkdir(parents=True, exist_ok=True)
    payload = asdict(history)
    payload["schema_version"] = 1
    for name, data in (("history.json", payload), ("analysis.json", report.to_dict())):
        (output / name).write_text(
            json.dumps(data, indent=2, default=_json_default, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    (output / "analysis.md").write_text(report_markdown(report), encoding="utf-8")
    (output / "analysis.html").write_text(analysis_html(report), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("outputs/data/research.sqlite"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize the versioned SQLite schema")
    commands.add_parser("list", help="List stored company profiles")
    ingest = commands.add_parser(
        "ingest", help="Load one normalized or Tega statement JSON"
    )
    ingest.add_argument("input", type=Path)
    ingest.add_argument("--company-id", required=True)
    query = commands.add_parser("query", help="Export latest-known annuals and ratios")
    query.add_argument("--company-id", required=True)
    query.add_argument("--as-of", required=True, help="Publication cutoff YYYY-MM-DD")
    query.add_argument(
        "--basis", choices=["consolidated", "standalone"], default="consolidated"
    )
    query.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in {"query", "list"} and not args.db.is_file():
            raise DataStoreError("Database does not exist; initialize and import first")
        store = FinancialStore(args.db)
        if args.command == "ingest":
            print(json.dumps(store.ingest_file(args.input, company_id=args.company_id)))
        elif args.command == "list":
            print(json.dumps(store.inventory(), indent=2))
        elif args.command == "query":
            report = export_analysis(
                store, args.company_id, args.as_of, args.output, basis=args.basis
            )
            print(f"{report.history.company.name}: {len(report.years)} annual periods")
            print(f"Reports: {args.output.resolve()}")
        else:
            print(f"Database ready: {args.db.resolve()}")
    except (DataStoreError, OSError) as exc:
        parser.exit(2, f"Data step stopped: {exc}\n")


if __name__ == "__main__":
    main()
