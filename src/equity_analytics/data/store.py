"""Repeatable imports and latest-known annual facts, without rewriting filings.

Publication-date queries model end-of-day public information. They do not
claim historical availability to this particular database or intraday timing.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

from equity_analytics.financials.io import history_from_dict, load_history
from equity_analytics.financials.models import NUMERIC_FIELDS, FinancialDataError
from equity_analytics.financials.ratios import analyze_history

from .schema import SCHEMA_SQL, SCHEMA_VERSION


class DataStoreError(ValueError):
    """A load or query cannot preserve the dataset's declared meaning."""


def _date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise DataStoreError("as_of must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise DataStoreError("as_of must be YYYY-MM-DD")
    return value


def _record(obj):
    return {
        k: v.isoformat() if isinstance(v, date) else v for k, v in asdict(obj).items()
    }


class FinancialStore:
    """A file-backed SQLite store; writes use one transaction per input file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                if db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchone():
                    raise DataStoreError("Refusing to initialize an unrelated database")
                try:
                    db.executescript(
                        "BEGIN IMMEDIATE;\n"
                        + SCHEMA_SQL
                        + f"\nPRAGMA user_version={SCHEMA_VERSION};\nCOMMIT;"
                    )
                except sqlite3.Error:
                    db.rollback()
                    raise
            elif version != SCHEMA_VERSION:
                raise DataStoreError(f"Unsupported database schema version: {version}")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    @staticmethod
    def _log(db, company_id, path, raw, status, count, message):
        return db.execute(
            "INSERT INTO ingestion_runs "
            "(company_id,input_name,sha256,loaded_at,status,inserted_statements,"
            "message,raw_content) VALUES (?,?,?,?,?,?,?,?)",
            (
                company_id,
                str(path),
                hashlib.sha256(raw).hexdigest(),
                datetime.now(UTC).isoformat(),
                status,
                count,
                message,
                raw,
            ),
        ).lastrowid

    def ingest_file(self, path: str | Path, *, company_id: str) -> dict:
        """Reject changed records with reused IDs; a new filing needs a new ID.

        Repeated imports add an audit run but never duplicate financial facts.
        Different filings for one fiscal year are retained as separate versions.
        Same-date competing filings are rejected because date-only ordering
        cannot reliably determine which was public last.
        """
        if not isinstance(company_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", company_id
        ):
            raise DataStoreError("company_id must be 1–64 letters, digits, _, . or -")
        path = Path(path)
        raw = b""
        try:
            raw = path.read_bytes()
            history = load_history(path)
            if raw != path.read_bytes():
                raise DataStoreError("Input changed while being read; retry the load")
            warnings = [
                w for year in analyze_history(history).years for w in year.warnings
            ]
            if warnings:
                raise DataStoreError("Financial checks failed: " + "; ".join(warnings))
            with self.connection() as db, db:
                db.execute("BEGIN IMMEDIATE")
                company = history.company
                existing = db.execute(
                    "SELECT name,ticker FROM companies WHERE company_id=?",
                    (company_id,),
                ).fetchone()
                if existing and tuple(existing) != (company.name, company.ticker):
                    raise DataStoreError("Company ID already has different name/ticker")
                if not existing:
                    db.execute(
                        "INSERT INTO companies VALUES (?,?,?)",
                        (company_id, company.name, company.ticker),
                    )
                profile = db.execute(
                    "SELECT * FROM profiles WHERE company_id=? AND statement_basis=?",
                    (company_id, company.statement_basis),
                ).fetchone()
                metadata = (company.currency, company.financial_unit, company.data_kind)
                if profile:
                    if (
                        tuple(
                            profile[k]
                            for k in ("currency", "financial_unit", "data_kind")
                        )
                        != metadata
                    ):
                        raise DataStoreError("Currency, units or data kind conflict")
                    profile_id = profile["profile_id"]
                else:
                    profile_id = db.execute(
                        "INSERT INTO profiles (company_id,statement_basis,currency,"
                        "financial_unit,data_kind) VALUES (?,?,?,?,?)",
                        (company_id, company.statement_basis, *metadata),
                    ).lastrowid
                run_id = self._log(
                    db, company_id, path, raw, "loaded", 0, history.notes
                )
                changed = 0
                for source in history.sources:
                    fields = _record(source)
                    old = db.execute(
                        "SELECT source_id,title,published_on,locator,url FROM sources "
                        "WHERE profile_id=? AND source_id=?",
                        (profile_id, source.source_id),
                    ).fetchone()
                    if old:
                        if dict(old) != fields:
                            raise DataStoreError(
                                "Source ID reused with changed metadata"
                            )
                    else:
                        db.execute(
                            "INSERT INTO sources VALUES (?,?,?,?,?,?,?)",
                            (
                                profile_id,
                                source.source_id,
                                source.title,
                                source.published_on.isoformat(),
                                source.locator,
                                source.url,
                                run_id,
                            ),
                        )
                        changed += 1
                inserted = 0
                for annual in history.annuals:
                    fields = _record(annual)
                    old = db.execute(
                        "SELECT * FROM annual_statements WHERE profile_id=? "
                        "AND fiscal_year=? AND source_id=?",
                        (profile_id, annual.fiscal_year, annual.source_id),
                    ).fetchone()
                    if old:
                        if any(old[k] != value for k, value in fields.items()):
                            raise DataStoreError(
                                "Statement changed under existing source ID"
                            )
                        continue
                    same_day = db.execute(
                        "SELECT 1 FROM annual_statements a JOIN sources s "
                        "USING(profile_id,source_id) WHERE a.profile_id=? "
                        "AND a.fiscal_year=? AND s.published_on=(SELECT published_on "
                        "FROM sources WHERE profile_id=? AND source_id=?)",
                        (profile_id, annual.fiscal_year, profile_id, annual.source_id),
                    ).fetchone()
                    if same_day:
                        raise DataStoreError(
                            "Competing same-date filings need explicit ordering"
                        )
                    prior = db.execute(
                        "SELECT period_end FROM annual_statements WHERE profile_id=?",
                        (profile_id,),
                    ).fetchall()
                    if any(
                        row[0][5:] != annual.period_end.isoformat()[5:] for row in prior
                    ):
                        raise DataStoreError(
                            "Fiscal year-end changes need a separate adapter"
                        )
                    columns = ["profile_id", *fields, "first_run_id"]
                    db.execute(
                        f"INSERT INTO annual_statements ({','.join(columns)}) "
                        f"VALUES ({','.join('?' for _ in columns)})",
                        (profile_id, *fields.values(), run_id),
                    )
                    inserted += 1
                status = "loaded" if inserted or changed else "unchanged"
                db.execute(
                    "UPDATE ingestion_runs SET status=?,inserted_statements=? WHERE run_id=?",
                    (status, inserted, run_id),
                )
                return {
                    "run_id": run_id,
                    "company_id": company_id,
                    "status": status,
                    "inserted_statements": inserted,
                }
        except (OSError, FinancialDataError, DataStoreError, sqlite3.Error) as exc:
            with self.connection() as db, db:
                self._log(db, company_id, path, raw, "failed", 0, str(exc))
            raise DataStoreError(str(exc)) from exc

    def history_as_of(self, company_id: str, as_of: str, *, basis="consolidated"):
        """Return the latest published version of each year on/before as_of.

        Select a whole statement version, not individual metrics from different
        filings. Missing values in a newer filing are never filled from older ones.
        """
        _date(as_of)
        with self.connection() as db:
            profile = db.execute(
                "SELECT p.*,c.name,c.ticker FROM profiles p JOIN companies c "
                "USING(company_id) WHERE company_id=? AND statement_basis=?",
                (company_id, basis),
            ).fetchone()
            if profile is None:
                raise DataStoreError("Unknown company or statement basis")
            rows = db.execute(
                "WITH available AS (SELECT a.*,s.published_on, "
                "ROW_NUMBER() OVER (PARTITION BY a.fiscal_year "
                "ORDER BY s.published_on DESC) AS rank "
                "FROM annual_statements a JOIN sources s USING(profile_id,source_id) "
                "WHERE a.profile_id=? AND s.published_on<=?) "
                "SELECT * FROM available WHERE rank=1 ORDER BY fiscal_year",
                (profile["profile_id"], as_of),
            ).fetchall()
            if not rows:
                raise DataStoreError("No financial statements published by this date")
            source_ids = sorted({row["source_id"] for row in rows})
            sources = [
                dict(
                    db.execute(
                        "SELECT source_id,title,published_on,locator,url FROM sources "
                        "WHERE profile_id=? AND source_id=?",
                        (profile["profile_id"], sid),
                    ).fetchone()
                )
                for sid in source_ids
            ]
            annual_fields = (
                "fiscal_year",
                "period_end",
                "source_id",
                "months",
                "notes",
                *NUMERIC_FIELDS,
            )
            payload = {
                "schema_version": 1,
                "company": {
                    k: profile[k]
                    for k in (
                        "name",
                        "ticker",
                        "currency",
                        "financial_unit",
                        "statement_basis",
                        "data_kind",
                    )
                },
                "as_of": as_of,
                "sources": sources,
                "annuals": [{k: row[k] for k in annual_fields} for row in rows],
                "notes": "Latest filings published by the selected date (end of day). "
                "This is public-information timing, not database-known-at timing. "
                "Annual-report dates may lag earlier results releases.",
            }
            return history_from_dict(payload)

    def inventory(self) -> list[dict]:
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT c.company_id,c.name,c.ticker,p.statement_basis,p.currency,"
                    "p.financial_unit,p.data_kind,COUNT(a.statement_id) AS statement_versions "
                    "FROM companies c JOIN profiles p USING(company_id) "
                    "LEFT JOIN annual_statements a USING(profile_id) "
                    "GROUP BY p.profile_id ORDER BY c.company_id,p.statement_basis"
                )
            ]
