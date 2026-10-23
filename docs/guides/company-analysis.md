# Company financial analysis: SQL data and ratios

Loads sourced annual statements for Tega Industries and VA Tech Wabag into a
SQLite database that keeps every filing version with its publication date,
then exports ratio analysis for each company and a side-by-side comparison.

## Run

On Windows, double-click `scripts/Run_Company_Analysis.bat`. From a terminal
in the repository folder:

```bash
python scripts/run_company_analysis.py
```

Open:

- `outputs/data/tega/analysis.html` and `outputs/data/wabag/analysis.html`:
  annual analysis per company (JSON and Markdown alongside).
- `outputs/data/company_comparison.html`: common-period comparison.

The database is `outputs/data/research.sqlite`. Python 3.11+; SQLite ships
with Python, so there is no database server and no third-party runtime package.

A first run loads 2 Tega statement versions from the FY2025 report, 2 from the
FY2026 report, 3 Wabag years (FY2024 from the FY2024 report; FY2025 and
FY2026 from the FY2026 report) and 5 years of the explicitly synthetic DEMO
company, which is used for tests and excluded from comparisons. Running again
loads nothing new: each import is logged as `unchanged` and no statement is
duplicated.

## How publication dates work

Queries use a publication cutoff (default 11 September 2026) and select, for
each fiscal year, the latest filing published on or before it. Re-run with an
earlier cutoff to see what was public at that date:

```bash
python scripts/run_data_pipeline.py --as-of 2026-08-27 --output outputs/data/tega_earlier
```

Tega's FY2026 annual report was published on 28 August 2026, so this query
selects only FY2024 and FY2025, from the FY2025 report. The dates are
conservative: earlier earnings releases are not imported, so this does not
imply nothing was disclosed before each annual report.

Storage rules are in [the data-layer design](../DATA_LAYER.md).

## Ratios

The ratio module covers growth, margins, ROE/ROA/ROCE, liquidity, leverage,
coverage and cash conversion. It can also run directly on a statement file,
for example Tega's complete FY2026 statements (after `pip install -e .`):

```bash
python -m equity_analytics.financials examples/tega_fy2026_reported_statements.json --output-dir outputs/history-tega-fy2026
```

Return ratios use average opening/closing balances, so a company's first
year has none. CFO less capex is reported, but it is not treated as FCFF.
Definitions are in [the calculation conventions](../FINANCIAL_ANALYSIS_METHODS.md),
with a code walkthrough in [FINANCIAL_ANALYSIS_WALKTHROUGH.md](../FINANCIAL_ANALYSIS_WALKTHROUGH.md).

## Import another company

After `pip install -e ".[dev]"`:

```bash
python -m equity_analytics.data --db outputs/data/research.sqlite ingest path/to/company.json --company-id COMPANY_ID
python -m equity_analytics.data --db outputs/data/research.sqlite list
python -m equity_analytics.data --db outputs/data/research.sqlite query --company-id COMPANY_ID --as-of 2026-09-11 --output outputs/data/company
```

The file must follow the normalized financial-history schema. Company IDs are
stable identifiers; a conflicting name or ticker is rejected. A failed load
rolls back every change from that file and keeps the error and raw input in
`ingestion_runs`.

## Sources: VA Tech Wabag

All figures INR million, consolidated.

FY2025 and FY2026 come from the
[FY2026 annual report](https://www.wabag.com/wp-content/uploads/2026/07/Annual-Report-2026.pdf),
printed pp.244–247 (PDF pp.246–249), dispatched 20 July 2026 (confirmed by the
company's [post-dispatch notice](https://www.wabag.com/wp-content/uploads/2026/07/Post-Dispatch_Newspaper-Publication.pdf),
Business Standard, 21 July 2026, p.13). FY2025 is the comparative column of
that filing, so it carries the July 2026 publication date.

FY2024 comes from the
[FY2023-24 annual report](https://www.wabag.com/wp-content/uploads/2025/07/Annual-Report-FY-2023-24-Compressed.pdf),
printed pp.298–301 (PDF pp.300–303), dispatched 23 July 2024 (confirmed by the
[post-dispatch notice](https://www.wabag.com/wp-content/uploads/2024/09/Post-Dispatch-Notice-2024-Advertisements.pdf),
Business Standard, 24 July 2024, p.15). The website upload date is not the
publication date.

| INR million | FY2024 | FY2025 | FY2026 |
|---|---:|---:|---:|
| Revenue from operations | 28,564 | 32,940 | 39,442 |
| Operating EBIT | 3,673 | 4,164 | 4,712 |
| D&A | 84 | 59 | 62 |
| Total net profit | 2,504 | 2,948 | 3,698 |
| Profit attributable to owners | 2,456 | 2,953 | 3,705 |
| Debt including leases | 2,889 | 3,617 | 2,284 |
| Operating cash flow | 1,335 | 3,552 | 2,067 |
| Gross cash capex | 119 | 45 | 52 |

Operating EBIT is revenue less cost of sales/services, inventory changes,
employee expense, D&A and other expenses. It excludes separately disclosed FX
gains, other income, associate/JV profit and exceptional items, so it is a
platform calculation, not management's headline EBITDA. FX losses embedded in
FY2024 other expenses are retained, a classification that differs from the
newer report. Debt is current and non-current borrowings plus lease
liabilities; cash excludes other bank balances; capex is purchases of PPE and
intangibles. The FY2024 balance sheet has a 1 million rounding residual
(assets 45,745; equity 18,239; liabilities 27,505), within tolerance.

## Sources: Tega Industries

See [FY2026 statements and reconciliation](../TEGA_FY2026_STATEMENTS.md) and
[FY2024–FY2025 sources](../TEGA_FY2025_STATEMENTS.md). Tega's EBIT excludes
other income and JV profit; FY2026 operating expenses include acquisition
transaction costs.

## Comparing the two

The comparison requires reported data with matching currency, unit, basis and
period end. Tega and Wabag are not assumed to be valuation peers; check each
company's accounting notes before reading anything into relative margins or
returns.
