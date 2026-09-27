# Wabag: second reported company

Copy this update's contents into your existing repository folder, merge folders,
and replace matching files. Keep your previous Tega files. Double-click
`Run_Wabag_Analysis.bat` (Python 3.11+), or run `python run_wabag_analysis.py`.
No new runtime packages or network downloads are required.

Open:
- `outputs/data/wabag/analysis.html`: Wabag annual analysis.
- `outputs/data/tega/analysis.html`: existing Tega annual analysis.
- `outputs/data/company_comparison.html`: common-period comparison.

JSON and Markdown exports accompany each company report. Re-running adds an
unchanged ingestion audit entry but does not duplicate statement versions.
Commit source files to GitHub; generated outputs and SQLite remain ignored.

## Coverage and conventions

Wabag FY2025 and FY2026 are transcribed from the FY2026 consolidated annual
report, printed pp.244-247 (PDF pp.246-249), in INR million:
https://www.wabag.com/wp-content/uploads/2026/07/Annual-Report-2026.pdf

The report was dispatched on July 20, 2026, confirmed by Wabag's notice in
Business Standard, July 21, p.13:
https://www.wabag.com/wp-content/uploads/2026/07/Post-Dispatch_Newspaper-Publication.pdf

Both years carry the July 20 publication date: FY2025 is a comparative in this
filing, not a reconstruction of information available during FY2025. Queries
before that date correctly return no Wabag observations. Earlier filings can be
added later as separate source versions. The default cutoff is September 11, 2026.

| Mapping (INR million) | FY2025 | FY2026 |
|---|---:|---:|
| Revenue from operations | 32,940 | 39,442 |
| Operating EBIT | 4,164 | 4,712 |
| D&A | 59 | 62 |
| Total net profit | 2,948 | 3,698 |
| Profit attributable to owners | 2,953 | 3,705 |
| Debt including leases | 3,617 | 2,284 |
| Operating cash flow | 3,552 | 2,067 |
| Gross cash capex | 45 | 52 |

EBIT equals revenue less cost of sales/services, inventory changes, employee
expense, D&A and other expenses. It excludes separately disclosed FX gains,
other income, associate/JV profit and exceptional items. It is a platform
calculation, not management's headline EBITDA. Debt sums current/non-current
borrowings and lease liabilities. Cash uses cash equivalents only, excluding
other bank balances. Capex is purchases of PPE/intangibles, not net investing
cash flow. CFO minus capex is not automatically unlevered free cash flow.

The comparison requires reported data, matching currency/unit/basis and a common
period end; it excludes the synthetic demo. Tega and Wabag are not assumed to be
valuation peers. Review company-specific accounting notes before interpreting
relative margins or returns. First-year average-balance returns are unavailable
without opening balances.

This update adds historical data and fundamental analytics. Wabag forecasts,
DCF assumptions and valuation scenarios are the next step.
