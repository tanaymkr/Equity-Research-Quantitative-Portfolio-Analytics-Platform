# Start the SQL financial-data pipeline

Requires Python 3.11+. SQLite is included in Python. No database server or
additional runtime packages are required.

## Copy-and-paste installation

Extract `Investment_Platform_SQL_Update.zip` and copy its contents directly
into your existing repository folder, alongside `run_tega_model.py`. Merge
folders and replace the supplied files. If you have edited these same files,
keep a backup before replacing them.

Double-click **Run_Data_Pipeline.bat**, or from the repository folder run:

```text
python run_data_pipeline.py
```

Open **outputs/data/tega/analysis.html** in your browser.

The command imports the FY25 and FY26 Tega statements plus the explicitly
synthetic DEMO history into **outputs/data/research.sqlite**. It then queries
that database using a publication cutoff of **11 September 2026** and exports
Tega FY24–FY26 financial analysis.

First run: 2 Tega versions from the FY25 report, 2 from the FY26 report, and
5 synthetic DEMO annuals. Tega FY25 has two preserved filing versions, so
4 stored Tega statements produce 3 selected financial years.

Second run: all three imports say `unchanged`, with zero new statement
versions. Audit runs still record when each import was attempted.

`run_tega_model.py` continues to produce the valuation report. Use the new
data launcher for SQL loading and historical financial analysis.

## Try an earlier publication cutoff

```text
python run_data_pipeline.py --as-of 2026-08-27 --output outputs/data/tega_earlier
```

The FY26 annual report was published on 28 August 2026 in the supplied source
register. The earlier query therefore selects only FY24 and FY25 from the
FY25 report. This is conservative: earlier earnings releases are not imported.
It does not imply the company had disclosed nothing before its annual report.

## Import another normalized history

After installing the project with `python -m pip install -e ".[dev]"`:

```text
python -m equity_analytics.data --db outputs/data/research.sqlite ingest path/to/company.json --company-id COMPANY_ID
python -m equity_analytics.data --db outputs/data/research.sqlite list
python -m equity_analytics.data --db outputs/data/research.sqlite query --company-id COMPANY_ID --as-of 2026-09-11 --output outputs/data/company
```

The input must follow the existing normalized financial-history schema.
Only Tega has an adapter for its full detailed statement files. Company IDs
are user-assigned stable identifiers; a conflicting name or ticker is rejected.
There is no automatic online provider download in this milestone.

## Checks

```text
python -m pytest
python -m ruff check .
```

Database files and generated outputs are ignored by Git. Commit the code,
source JSON and documentation, then regenerate the database from those inputs.
If a load fails, its message and raw input are kept in `ingestion_runs`, while
all financial changes from that file are rolled back. Read the error before
changing a source ID; it may indicate a unit or data correction problem.
