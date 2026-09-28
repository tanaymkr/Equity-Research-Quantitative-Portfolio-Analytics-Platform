"""Independent SQLite price store: immutable full-series retrieval snapshots."""

import hashlib
import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE market_instruments (
 instrument_id TEXT PRIMARY KEY, ticker TEXT NOT NULL, name TEXT NOT NULL,
 currency TEXT NOT NULL, kind TEXT NOT NULL, data_kind TEXT NOT NULL);
CREATE TABLE market_snapshots (
 snapshot_id INTEGER PRIMARY KEY, instrument_id TEXT NOT NULL REFERENCES market_instruments,
 retrieved_at TEXT NOT NULL, loaded_at TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
 provider TEXT NOT NULL, source_url TEXT NOT NULL, close_basis TEXT NOT NULL,
 adjusted_basis TEXT NOT NULL, raw_content BLOB NOT NULL);
CREATE TABLE market_prices (
 snapshot_id INTEGER NOT NULL REFERENCES market_snapshots, date TEXT NOT NULL,
 close REAL, adjusted_close REAL, volume REAL, PRIMARY KEY(snapshot_id,date));
CREATE TABLE market_actions (
 snapshot_id INTEGER NOT NULL REFERENCES market_snapshots, date TEXT NOT NULL,
 type TEXT NOT NULL, value REAL NOT NULL, PRIMARY KEY(snapshot_id,date,type));
CREATE INDEX market_retrieval ON market_snapshots(instrument_id,retrieved_at);
PRAGMA user_version=1;
"""


def iso_date(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Date must use YYYY-MM-DD")
    return parsed


def utc_timestamp(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo is None:
        raise ValueError("Retrieval timestamp requires a timezone")
    return d.astimezone(UTC).isoformat(timespec="microseconds")


def _number(value, name, *, zero=False, nullable=False):
    if value is None and nullable:
        return
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric data")
    if value < 0 or (not zero and value == 0):
        raise ValueError(f"{name} must be {'nonnegative' if zero else 'positive'}")


def validate_snapshot(p):
    if type(p["schema_version"]) is not int or p["schema_version"] != 1:
        raise ValueError("Unsupported price input schema")
    i, s = p["instrument"], p["source"]
    for key in ("instrument_id", "ticker", "name", "currency"):
        if not isinstance(i[key], str) or not i[key].strip():
            raise ValueError(f"Missing instrument {key}")
    if i["kind"] not in {"equity", "price_index", "total_return_index"}:
        raise ValueError("Unknown instrument kind")
    if p["data_kind"] not in {"reported", "synthetic"}:
        raise ValueError("Unknown data kind")
    for key in ("provider", "url"):
        if not isinstance(s[key], str) or not s[key]:
            raise ValueError(f"Missing source {key}")
    if s["close_basis"] not in {"split_adjusted", "index_level"}:
        raise ValueError("close_basis must be split_adjusted or index_level")
    if s["adjusted_basis"] not in {
        "split_dividend_adjusted",
        "not_available",
        "price_index",
        "total_return_index",
    }:
        raise ValueError("Unknown adjusted basis")
    if i["kind"] == "equity" and s["close_basis"] != "split_adjusted":
        raise ValueError(
            "Equity close must be split-adjusted for price-return comparisons"
        )
    if i["kind"] != "equity" and s["close_basis"] != "index_level":
        raise ValueError("Index close must be an index level")
    expected = {
        "price_index": "price_index",
        "total_return_index": "total_return_index",
    }
    if i["kind"] in expected and s["adjusted_basis"] != expected[i["kind"]]:
        raise ValueError("Index kind and adjustment metadata disagree")
    if i["kind"] == "equity" and s["adjusted_basis"] not in {
        "split_dividend_adjusted",
        "not_available",
    }:
        raise ValueError("Equity adjustment metadata is inconsistent")
    stamp = utc_timestamp(s["retrieved_at"])
    retrieved = datetime.fromisoformat(stamp).date()
    if not p["bars"]:
        raise ValueError("Empty price history")
    dates = []
    for b in p["bars"]:
        d = iso_date(b["date"])
        if d > retrieved:
            raise ValueError("Price date is later than retrieval date")
        dates.append(b["date"])
        for key in ("close", "adjusted_close"):
            _number(b.get(key), key, nullable=True)
        _number(b.get("volume"), "volume", zero=True, nullable=True)
    if dates != sorted(set(dates)):
        raise ValueError("Price dates must be unique and ascending")
    keys = set()
    for a in p["actions"]:
        d = iso_date(a["date"])
        if d > retrieved:
            raise ValueError("Action date is later than retrieval date")
        if a["type"] not in {"dividend", "split"}:
            raise ValueError("Unsupported corporate action type")
        _number(a["value"], "action value", zero=a["type"] == "dividend")
        key = (a["date"], a["type"])
        if key in keys:
            raise ValueError("Duplicate action date/type")
        keys.add(key)
    return stamp


class PriceStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            tables = {
                r[0]
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if not tables:
                db.executescript("BEGIN IMMEDIATE;\n" + SCHEMA + "\nCOMMIT;")
            elif (
                "market_snapshots" not in tables
                or db.execute("PRAGMA user_version").fetchone()[0] != 1
            ):
                raise ValueError(
                    "Not a supported price database; use a separate market.sqlite file"
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

    def ingest_file(self, path):
        raw = Path(path).read_bytes()
        p = json.loads(raw)
        stamp = validate_snapshot(p)
        digest = hashlib.sha256(raw).hexdigest()
        i, s = p["instrument"], p["source"]
        instrument = {**i, "data_kind": p["data_kind"]}
        keys = ("instrument_id", "ticker", "name", "currency", "kind", "data_kind")
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT snapshot_id FROM market_snapshots WHERE sha256=?", (digest,)
            ).fetchone()
            if prior:
                return {"status": "unchanged", "snapshot_id": prior[0], "bars": 0}
            old = db.execute(
                "SELECT * FROM market_instruments WHERE instrument_id=?",
                (i["instrument_id"],),
            ).fetchone()
            if old and any(old[k] != instrument[k] for k in keys):
                raise ValueError(
                    "Instrument metadata changed; use a distinct instrument ID"
                )
            if db.execute(
                "SELECT 1 FROM market_snapshots WHERE instrument_id=? AND retrieved_at=?",
                (i["instrument_id"], stamp),
            ).fetchone():
                raise ValueError("Conflicting snapshot at the same retrieval timestamp")
            if not old:
                db.execute(
                    "INSERT INTO market_instruments VALUES (?,?,?,?,?,?)",
                    tuple(instrument[k] for k in keys),
                )
            cursor = db.execute(
                "INSERT INTO market_snapshots (instrument_id,retrieved_at,loaded_at,sha256,provider,source_url,close_basis,adjusted_basis,raw_content) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    i["instrument_id"],
                    stamp,
                    datetime.now(UTC).isoformat(),
                    digest,
                    s["provider"],
                    s["url"],
                    s["close_basis"],
                    s["adjusted_basis"],
                    raw,
                ),
            )
            sid = cursor.lastrowid
            db.executemany(
                "INSERT INTO market_prices VALUES (?,?,?,?,?)",
                [
                    (
                        sid,
                        b["date"],
                        b.get("close"),
                        b.get("adjusted_close"),
                        b.get("volume"),
                    )
                    for b in p["bars"]
                ],
            )
            db.executemany(
                "INSERT INTO market_actions VALUES (?,?,?,?)",
                [(sid, a["date"], a["type"], a["value"]) for a in p["actions"]],
            )
        return {"status": "loaded", "snapshot_id": sid, "bars": len(p["bars"])}

    def snapshot(self, instrument_id, *, known_at=None):
        cutoff = (
            utc_timestamp(known_at)
            if known_at
            else datetime.now(UTC).isoformat(timespec="microseconds")
        )
        with self.connection() as db:
            r = db.execute(
                "SELECT * FROM market_snapshots WHERE instrument_id=? AND retrieved_at<=? ORDER BY retrieved_at DESC LIMIT 1",
                (instrument_id, cutoff),
            ).fetchone()
            if r is None:
                raise ValueError(
                    f"No price snapshot available for {instrument_id} by retrieval cutoff"
                )
            p = json.loads(r["raw_content"])
            p["bars"] = [
                dict(b)
                for b in db.execute(
                    "SELECT date,close,adjusted_close,volume FROM market_prices WHERE snapshot_id=? ORDER BY date",
                    (r["snapshot_id"],),
                )
            ]
            p["actions"] = [
                dict(a)
                for a in db.execute(
                    "SELECT date,type,value FROM market_actions WHERE snapshot_id=? ORDER BY date,type",
                    (r["snapshot_id"],),
                )
            ]
            p.pop("provider_response", None)
            return {
                **p,
                "snapshot_id": r["snapshot_id"],
                "sha256": r["sha256"],
                "loaded_at": r["loaded_at"],
            }
