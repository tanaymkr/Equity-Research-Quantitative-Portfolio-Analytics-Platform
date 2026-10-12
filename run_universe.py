"""Load NSE index constituents, report membership and write a price config."""

import argparse
import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from equity_analytics.universe.nse import (
    INDEX_FILES,
    NSE_ARCHIVE,
    download_constituents,
)
from equity_analytics.universe.report import write_report
from equity_analytics.universe.store import (
    BENCHMARKS,
    IST,
    UniverseStore,
    benchmark_for,
    price_config,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", default="NIFTY100")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--download", action="store_true", help="Fetch the current list from NSE"
    )
    mode.add_argument(
        "--import", dest="import_file", type=Path, help="A saved NSE constituent CSV"
    )
    parser.add_argument(
        "--retrieved-at",
        help="When the imported file was downloaded (ISO, with timezone). "
        "Default: now.",
    )
    parser.add_argument(
        "--effective-on",
        help="Date the list describes (YYYY-MM-DD). Default: retrieval date.",
    )
    parser.add_argument("--source-url", help="Where the imported file came from")
    parser.add_argument(
        "--as-of", help="Membership date (YYYY-MM-DD). Default: today in India"
    )
    parser.add_argument(
        "--allow-backfill",
        action="store_true",
        help="Use a later list for an earlier date (labelled survivorship-biased)",
    )
    parser.add_argument(
        "--benchmark",
        choices=sorted(BENCHMARKS),
        help="Price index to compare against. Default: the universe's own index",
    )
    parser.add_argument("--price-start", default="2021-04-01")
    parser.add_argument(
        "--price-end-exclusive",
        help="Default: the as-of date, which excludes an unfinished session",
    )
    parser.add_argument(
        "--db", type=Path, default=ROOT / "outputs/data/universe.sqlite"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        store = UniverseStore(args.db)
        output = args.output or ROOT / "outputs/universe" / args.universe
        if args.download or args.import_file:
            if args.download:
                print("Downloading", args.universe, "from NSE", flush=True)
                got = download_constituents(args.universe)
                raw, url, retrieved_at = got["raw"], got["url"], got["retrieved_at"]
            else:
                raw = args.import_file.read_bytes()
                default_url = (
                    NSE_ARCHIVE.format(file=INDEX_FILES[args.universe])
                    if args.universe in INDEX_FILES
                    else None
                )
                url = args.source_url or default_url
                if not url:
                    raise ValueError("--source-url is required for this universe")
                retrieved_at = args.retrieved_at or datetime.now(UTC).isoformat(
                    timespec="seconds"
                )
            effective_on = (
                args.effective_on
                or datetime.fromisoformat(retrieved_at)
                .astimezone(IST)
                .date()
                .isoformat()
            )
            result = store.ingest(
                raw,
                universe_id=args.universe,
                effective_on=effective_on,
                retrieved_at=retrieved_at,
                source_url=url,
            )
            # Keep the exact source bytes alongside the database for audit.
            folder = output / "downloads"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (hashlib.sha256(raw).hexdigest() + ".csv")).write_bytes(raw)
            print("Import:", result)
        as_of = args.as_of or datetime.now(IST).date().isoformat()
        membership = store.members(
            args.universe, as_of, allow_backfill=args.allow_backfill
        )
        config = price_config(
            membership,
            start=args.price_start,
            end_exclusive=args.price_end_exclusive or as_of,
            benchmark=benchmark_for(args.benchmark) if args.benchmark else None,
        )
        report = write_report(membership, store.changes(args.universe), config, output)
        print(
            f"{args.universe} on {as_of}: {len(membership['members'])} members "
            f"(list effective {membership['snapshot']['effective_on']})"
        )
        for warning in membership["warnings"]:
            print("WARNING:", warning)
        print("Report:", report)
        print("Benchmark:", config["benchmark_id"])
        print("Price config:", output / "market_config.json")
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print("Universe pipeline failed:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
