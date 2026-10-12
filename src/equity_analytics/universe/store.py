"""Dated index-membership snapshots and the company master derived from them.

A snapshot records "these companies were in this universe on effective_on".
Snapshots are immutable, like annual filings: a changed list for the same
universe and date is rejected; a new list needs its own effective date.

Membership for a date uses the latest snapshot effective on or before it.
Using a later list for an earlier date is survivorship bias, so it is refused
unless the caller explicitly allows it, and the result is then labelled.
"""

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

from .nse import parse_constituents

SCHEMA_VERSION = 1
# NSE membership dates are Indian calendar dates. A fixed offset avoids
# needing tzdata on Windows; India has no daylight saving.
IST = timezone(timedelta(hours=5, minutes=30))
SCHEMA = """
CREATE TABLE universe_snapshots (
 snapshot_id INTEGER PRIMARY KEY,
 universe_id TEXT NOT NULL,
 effective_on TEXT NOT NULL,
 retrieved_at TEXT NOT NULL,
 loaded_at TEXT NOT NULL,
 source_url TEXT NOT NULL,
 sha256 TEXT NOT NULL,
 member_count INTEGER NOT NULL CHECK(member_count > 0),
 raw_content BLOB NOT NULL,
 UNIQUE(universe_id, effective_on),
 UNIQUE(universe_id, sha256));
CREATE TABLE universe_members (
 snapshot_id INTEGER NOT NULL REFERENCES universe_snapshots,
 company_id TEXT NOT NULL,
 symbol TEXT NOT NULL,
 name TEXT NOT NULL,
 industry TEXT NOT NULL,
 series TEXT NOT NULL,
 isin TEXT NOT NULL,
 PRIMARY KEY(snapshot_id, company_id),
 UNIQUE(snapshot_id, symbol),
 UNIQUE(snapshot_id, isin));
CREATE INDEX universe_dates ON universe_snapshots(universe_id, effective_on);
"""

UNIVERSE_ID = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,31}")

# NSE industry labels. Financial Services companies (banks, NBFCs, insurers)
# need balance-sheet models, not FCFF/EBITDA metrics.
FINANCIALS = {"Financial Services"}
GENERAL = {
    "Automobile and Auto Components",
    "Capital Goods",
    "Chemicals",
    "Construction",
    "Construction Materials",
    "Consumer Durables",
    "Consumer Services",
    "Diversified",
    "Fast Moving Consumer Goods",
    "Forest Materials",
    "Healthcare",
    "Information Technology",
    "Media Entertainment & Publication",
    "Metals & Mining",
    "Oil Gas & Consumable Fuels",
    "Power",
    "Realty",
    "Services",
    "Telecommunication",
    "Textiles",
    "Utilities",
}
# Days after which a snapshot is flagged stale. NSE reviews its broad indices
# semi-annually, so a list older than about six months may have changed.
STALE_AFTER_DAYS = 183


def company_id_for(symbol):
    """Platform ID from an NSE symbol; '&' is not allowed in financial-store IDs."""
    return symbol.replace("&", "_")


def statement_template(industry):
    if industry in FINANCIALS:
        return "financials"
    if industry in GENERAL:
        return "general"
    return "unclassified"


def _iso_date(value, name):
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None or parsed.isoformat() != value:
        raise ValueError(f"{name} must be YYYY-MM-DD")
    return parsed


def _utc(value):
    try:
        stamp = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("retrieved_at must be an ISO timestamp") from exc
    if stamp.tzinfo is None:
        raise ValueError("retrieved_at requires a timezone")
    return stamp.astimezone(UTC)


class UniverseStore:
    """File-backed SQLite store, separate from the financial and price databases."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if version == 0 and not tables:
                db.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + SCHEMA
                    + f"\nPRAGMA user_version={SCHEMA_VERSION};\nCOMMIT;"
                )
            elif version != SCHEMA_VERSION or not any(
                t[0] == "universe_snapshots" for t in tables
            ):
                raise ValueError(
                    "Not a supported universe database; use a separate universe.sqlite"
                )

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    def ingest(self, raw, *, universe_id, effective_on, retrieved_at, source_url):
        """Store one constituent list. Identical re-imports are no-ops."""
        if not isinstance(universe_id, str) or not UNIVERSE_ID.fullmatch(universe_id):
            raise ValueError("universe_id must be upper-case letters, digits, _ or -")
        effective = _iso_date(effective_on, "effective_on")
        stamp = _utc(retrieved_at)
        if effective > stamp.astimezone(IST).date():
            raise ValueError(
                "effective_on cannot be after retrieval: a list cannot describe "
                "a future date"
            )
        if not isinstance(source_url, str) or not source_url.strip():
            raise ValueError("source_url is required")
        raw = bytes(raw)
        members = parse_constituents(raw)
        ids = [company_id_for(m["symbol"]) for m in members]
        if len(set(ids)) != len(ids):
            raise ValueError("Two symbols map to the same company_id")
        digest = hashlib.sha256(raw).hexdigest()
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            same = db.execute(
                "SELECT snapshot_id, effective_on, sha256 FROM universe_snapshots "
                "WHERE universe_id=? AND (sha256=? OR effective_on=?)",
                (universe_id, digest, effective_on),
            ).fetchall()
            for row in same:
                if row["sha256"] == digest and row["effective_on"] == effective_on:
                    return {"status": "unchanged", "snapshot_id": row["snapshot_id"]}
                if row["effective_on"] == effective_on:
                    raise ValueError(
                        f"{universe_id} already has a different list effective "
                        f"{effective_on}; snapshots are immutable"
                    )
                raise ValueError(
                    f"This exact file is already stored for {universe_id} as "
                    f"effective {row['effective_on']}; one file cannot describe "
                    "two dates"
                )
            sid = db.execute(
                "INSERT INTO universe_snapshots (universe_id,effective_on,"
                "retrieved_at,loaded_at,source_url,sha256,member_count,raw_content) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    universe_id,
                    effective_on,
                    stamp.isoformat(timespec="seconds"),
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    source_url.strip(),
                    digest,
                    len(members),
                    raw,
                ),
            ).lastrowid
            db.executemany(
                "INSERT INTO universe_members VALUES (?,?,?,?,?,?,?)",
                [
                    (
                        sid,
                        company_id_for(m["symbol"]),
                        m["symbol"],
                        m["name"],
                        m["industry"],
                        m["series"],
                        m["isin"],
                    )
                    for m in members
                ],
            )
        return {"status": "loaded", "snapshot_id": sid, "members": len(members)}

    def snapshots(self, universe_id):
        with self.connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT snapshot_id,universe_id,effective_on,retrieved_at,"
                    "source_url,sha256,member_count FROM universe_snapshots "
                    "WHERE universe_id=? ORDER BY effective_on",
                    (universe_id,),
                )
            ]

    def _members(self, db, snapshot_id):
        rows = db.execute(
            "SELECT company_id,symbol,name,industry,series,isin FROM universe_members "
            "WHERE snapshot_id=? ORDER BY company_id",
            (snapshot_id,),
        )
        return [
            {**dict(r), "template": statement_template(r["industry"])} for r in rows
        ]

    def members(self, universe_id, as_of, *, allow_backfill=False):
        """Membership on as_of, with explicit labels for every assumption."""
        day = _iso_date(as_of, "as_of")
        snaps = self.snapshots(universe_id)
        if not snaps:
            raise ValueError(f"No snapshots stored for {universe_id}")
        prior = [s for s in snaps if s["effective_on"] <= as_of]
        warnings = []
        if prior:
            chosen, biased = prior[-1], False
        elif allow_backfill:
            chosen, biased = snaps[0], True
            warnings.append(
                f"Survivorship bias: no list on or before {as_of}; using the list "
                f"effective {chosen['effective_on']}. Companies that left the index "
                "before then are missing."
            )
        else:
            raise ValueError(
                f"No {universe_id} list effective on or before {as_of} (earliest is "
                f"{snaps[0]['effective_on']}). Load an older list, or allow backfill "
                "and accept survivorship bias."
            )
        age = (day - date.fromisoformat(chosen["effective_on"])).days
        if age > STALE_AFTER_DAYS:
            warnings.append(
                f"Stale list: effective {chosen['effective_on']}, {age} days before "
                f"{as_of}. Index reviews since then are not reflected."
            )
        with self.connection() as db:
            members = self._members(db, chosen["snapshot_id"])
        unclassified = sorted(
            {m["industry"] for m in members if m["template"] == "unclassified"}
        )
        if unclassified:
            warnings.append("Unrecognised NSE industries: " + ", ".join(unclassified))
        return {
            "universe_id": universe_id,
            "as_of": as_of,
            "snapshot": chosen,
            "survivorship_biased": biased,
            "list_age_days": age,
            "warnings": warnings,
            "members": members,
        }

    def changes(self, universe_id):
        """Additions and removals between consecutive snapshots."""
        snaps = self.snapshots(universe_id)
        out = []
        with self.connection() as db:
            previous = None
            for s in snaps:
                current = {
                    m["company_id"]: m for m in self._members(db, s["snapshot_id"])
                }
                if previous is not None:
                    before, now = previous[1], current
                    out.append(
                        {
                            "from": previous[0]["effective_on"],
                            "to": s["effective_on"],
                            "added": sorted(set(now) - set(before)),
                            "removed": sorted(set(before) - set(now)),
                            "isin_changed": sorted(
                                c
                                for c in set(now) & set(before)
                                if now[c]["isin"] != before[c]["isin"]
                            ),
                        }
                    )
                previous = (s, current)
        return out


# Yahoo price-index tickers. Each universe is compared with its own index, so a
# Nifty 100 strategy is not judged against the narrower Nifty 50.
BENCHMARKS = {
    "NIFTY50": ("^NSEI", "NIFTY 50"),
    "NIFTY100": ("^CNX100", "NIFTY 100"),
    "NIFTY200": ("^CNX200", "NIFTY 200"),
    "NIFTY500": ("^CRSLDX", "NIFTY 500"),
}


def benchmark_for(universe_id):
    """The matching price index; an unknown universe must name its own."""
    if universe_id not in BENCHMARKS:
        raise ValueError(
            f"No default benchmark for {universe_id}; choose one with --benchmark"
        )
    ticker, name = BENCHMARKS[universe_id]
    return {
        "instrument_id": universe_id,
        "ticker": ticker,
        "name": name,
        "currency": "INR",
        "kind": "price_index",
    }


def price_config(membership, *, start, end_exclusive, benchmark=None):
    """A market_config.json for run_price_pipeline.py from a membership result.

    Tickers use Yahoo's NSE suffix (.NS) on the exact NSE symbol. Company IDs
    are NSE symbols with '&' replaced by '_', which match the existing TEGA and
    WABAG IDs in the financial and price stores.
    """
    if _iso_date(start, "start") >= _iso_date(end_exclusive, "end_exclusive"):
        raise ValueError("start must be before end_exclusive")
    benchmark = benchmark or benchmark_for(membership["universe_id"])
    instruments = [
        {
            "instrument_id": m["company_id"],
            "ticker": m["symbol"] + ".NS",
            "name": m["name"],
            "currency": "INR",
            "kind": "equity",
        }
        for m in membership["members"]
    ]
    if benchmark["instrument_id"] in {i["instrument_id"] for i in instruments}:
        raise ValueError("Benchmark ID collides with a member company ID")
    return {
        "schema_version": 1,
        "start": start,
        "end_exclusive": end_exclusive,
        "benchmark_id": benchmark["instrument_id"],
        "return_basis": "price",
        "universe": {
            "universe_id": membership["universe_id"],
            "as_of": membership["as_of"],
            "effective_on": membership["snapshot"]["effective_on"],
            "survivorship_biased": membership["survivorship_biased"]
            or start < membership["snapshot"]["effective_on"],
            "note": (
                "Prices before the list's effective date cover companies chosen "
                "with later knowledge. Treat pre-effective-date returns as "
                "survivorship-biased."
            ),
        },
        "instruments": [*instruments, benchmark],
    }
