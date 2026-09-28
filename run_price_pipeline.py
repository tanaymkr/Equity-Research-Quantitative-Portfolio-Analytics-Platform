"""Download/import prices into SQLite and build an audited comparison report."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from equity_analytics.market.report import write_report
from equity_analytics.market.returns import compare_returns
from equity_analytics.market.store import (
    PriceStore,
    iso_date,
    validate_snapshot,
)
from equity_analytics.market.yahoo import download_history


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "examples/market_config.json"
    )
    parser.add_argument("--db", type=Path, default=ROOT / "outputs/data/market.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/prices")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--download", action="store_true")
    mode.add_argument("--import", dest="imports", nargs="+", type=Path)
    parser.add_argument(
        "--known-at",
        help="Timezone-aware retrieval cutoff; not historical publication time",
    )
    args = parser.parse_args(argv)
    try:
        c = json.loads(args.config.read_text(encoding="utf-8"))
        if c["schema_version"] != 1 or iso_date(c["start"]) >= iso_date(
            c["end_exclusive"]
        ):
            raise ValueError("Invalid config schema or date range")
        ids = [i["instrument_id"] for i in c["instruments"]]
        if len(ids) != len(set(ids)) or c["benchmark_id"] not in ids:
            raise ValueError("Config requires unique IDs and an included benchmark")
        paths = args.imports or []
        if args.download:
            payloads = []
            for instrument in c["instruments"]:
                print("Downloading", instrument["ticker"], flush=True)
                payloads.append(
                    download_history(instrument, c["start"], c["end_exclusive"])
                )
            folder = args.output / "downloads"
            folder.mkdir(parents=True, exist_ok=True)
            for p in payloads:
                raw = json.dumps(p, indent=2, allow_nan=False).encode("utf-8")
                path = folder / (hashlib.sha256(raw).hexdigest() + ".json")
                path.write_bytes(raw)
                paths.append(path)
        # Validate every file before modifying the database. Ingestion is atomic per file.
        for path in paths:
            validate_snapshot(json.loads(path.read_bytes()))
        store = PriceStore(args.db)
        for path in paths:
            print(path.name, store.ingest_file(path))
        snapshots = [store.snapshot(cid, known_at=args.known_at) for cid in ids]
        for expected, snapshot in zip(c["instruments"], snapshots, strict=True):
            if expected != snapshot["instrument"]:
                raise ValueError("Configured instrument differs from stored metadata")
        result = compare_returns(
            snapshots,
            c["benchmark_id"],
            start=c["start"],
            end=c["end_exclusive"],
            basis=c["return_basis"],
        )
        report = write_report(result, snapshots, args.output)
        print("Report:", report)
        for row in result["summaries"]:
            print(
                row["instrument_id"],
                row["observed_dates"],
                "dates;",
                row["missing_intervals"],
                "missing intervals",
            )
        return 0
    except (ValueError, KeyError, TypeError, OSError, ZeroDivisionError) as exc:
        print("Price pipeline failed:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
