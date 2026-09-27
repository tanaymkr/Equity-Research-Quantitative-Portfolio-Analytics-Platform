"""Version 1: immutable filing versions, numeric facts and ingestion evidence."""

from equity_analytics.financials.models import NUMERIC_FIELDS

SCHEMA_VERSION = 1
METRIC_COLUMNS = ",\n".join(
    f"{name} REAL" + (" NOT NULL" if name == "revenue" else "")
    for name in NUMERIC_FIELDS
)

SCHEMA_SQL = (
    """
CREATE TABLE companies (
    company_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ticker TEXT NOT NULL UNIQUE
);
CREATE TABLE profiles (
    profile_id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    statement_basis TEXT NOT NULL CHECK(statement_basis IN ('standalone','consolidated')),
    currency TEXT NOT NULL,
    financial_unit TEXT NOT NULL,
    data_kind TEXT NOT NULL CHECK(data_kind IN ('reported','synthetic')),
    UNIQUE(company_id, statement_basis)
);
CREATE TABLE ingestion_runs (
    run_id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    input_name TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('loaded','unchanged','failed')),
    inserted_statements INTEGER NOT NULL,
    message TEXT NOT NULL,
    raw_content BLOB NOT NULL
);
CREATE TABLE sources (
    profile_id INTEGER NOT NULL REFERENCES profiles(profile_id),
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    published_on TEXT NOT NULL,
    locator TEXT NOT NULL,
    url TEXT,
    first_run_id INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    PRIMARY KEY(profile_id, source_id)
);
CREATE TABLE annual_statements (
    statement_id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    period_end TEXT NOT NULL,
    months INTEGER NOT NULL CHECK(months = 12),
    notes TEXT NOT NULL,
    """
    + METRIC_COLUMNS
    + """,
    first_run_id INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    UNIQUE(profile_id, fiscal_year, source_id),
    FOREIGN KEY(profile_id, source_id) REFERENCES sources(profile_id, source_id)
);
CREATE INDEX source_publication ON sources(profile_id, published_on);
CREATE INDEX annual_period ON annual_statements(profile_id, fiscal_year);
"""
)
