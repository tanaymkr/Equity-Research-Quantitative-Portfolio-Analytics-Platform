# SQL financial data: schema version 1

## Delivered scope

SQLite storage for company identities, annual filing versions and ingestion
evidence; a local-file importer; publication-date queries; and JSON, Markdown
and HTML financial-analysis exports. This integrates the existing ratio engine.

Initial coverage: TEGA reported financials and DEMO synthetic arithmetic data.
Price ingestion, exchanges/sectors, corporate-action data, model-assumption
versions, automated providers and historical universe membership are not yet built.

## Tables

| Table | Key and purpose |
| --- | --- |
| `companies` | User-assigned `company_id`; name and unique ticker. Identity changes require explicit future migration. |
| `profiles` | Company + statement basis. Currency, unit and reported/synthetic status cannot silently change. |
| `sources` | Profile + source ID. Publication date, title, URL, locator and first ingestion run. |
| `annual_statements` | Profile + fiscal year + source ID. Period end, months, notes and typed numeric financial columns. |
| `ingestion_runs` | Input filename, SHA-256, UTC load time, outcome, count, message and original file bytes. Failed runs have no fact changes. |

Financial columns follow `financials.models.AnnualStatement`: revenue, EBIT,
D&A, net income, owners' income, finance costs, balance-sheet totals, owners'
equity, current balances, cash, debt, operating cash flow and capex. Missing
values stay SQL NULL. Zero is a number. Ratios are calculated from selected
facts, not stored as competing copies.

`schema.py` defines the DDL. `PRAGMA user_version` controls schema versioning.
Version zero is initialized only if the database has no tables. Unknown
versions are rejected; no destructive migration is attempted. SQLite foreign
keys are enabled on each connection. Writes use one transaction per input.

## Filing and date policy

1. A source ID identifies an immutable filing within its company profile.
   Importing changed source metadata or financial values under the same ID fails.
2. A later filing uses a new source ID and its actual publication date. Older
   facts remain stored, including comparative periods reproduced or restated
   in the later filing. A new version does not necessarily imply a restatement.
3. As-of queries include publications on or before the selected date (end of day).
   They select the latest complete filing version for each fiscal year, without
   filling missing fields from older filings.
4. Same-date competing filings for one year are rejected because this schema
   has no verified intraday order. Do not invent a later date to bypass this.
5. Publication date is distinct from period end and ingestion timestamp. The
   query reconstructs public information from stored sources, not what this
   database actually held at a historical moment. Bitemporal correction support
   and intraday availability are not implemented.
6. The supplied annual-report dates can lag earlier earnings releases. Queries
   are conservative to the imported sources; they do not claim exhaustive
   information availability. Fiscal-year-end changes need an explicit adapter.

The original Tega acquisition valuation is a separate research case with a
June valuation date and September research cutoff. Loading its reported
history into SQL does not make that forecast a point-in-time backtest.

## Repeatability and rejection behavior

The loader validates source JSON through the existing financial contracts,
then checks available balance-sheet reconciliations and containing totals.
Incomplete statements remain valid where the contract permits missing values;
a missing value is not confirmation that an accounting check passed.

The same import adds a new audit run with `unchanged` and zero statement
inserts. Different files containing the same normalized facts also leave those
facts unchanged. Imports cannot merge conflicting company IDs/tickers, units,
currencies or data kinds. Standalone and consolidated profiles remain separate.

An input file's changes commit together. On validation or SQL error, financial
writes roll back and a failed ingestion entry preserves the error and raw
bytes (empty bytes if the file could not be read). Correction of an erroneously
entered source currently requires a reviewed rebuild from corrected source
files into a new database; silent overwrite is deliberately unsupported.

## SQL examples

View the two stored Tega FY25 publication versions:

```sql
SELECT c.company_id, a.fiscal_year, s.published_on, s.source_id, a.revenue
FROM annual_statements a
JOIN profiles p USING (profile_id)
JOIN companies c USING (company_id)
JOIN sources s USING (profile_id, source_id)
WHERE c.company_id = 'TEGA' AND a.fiscal_year = 2025
ORDER BY s.published_on;
```

Inspect import results:

```sql
SELECT run_id, company_id, loaded_at, status, inserted_statements, message
FROM ingestion_runs
ORDER BY run_id DESC;
```

The API uses SQL parameters for user values. Its as-of query filters publication
dates before applying `ROW_NUMBER()` per financial year; reversing this order
would incorrectly hide an older filing when a future revision exists.

## Validation

Tests cover repeat imports, raw-file hashes, later revisions in either load
order, publication boundaries, missing values, conflicting identifiers and
metadata, unit/basis separation, invalid numeric values, balance mismatches,
full rollback, failed-run evidence, database versions, CLI export, output
protection and Tega FY25/FY26 filing selection. Database files are generated
locally and are excluded from Git.
