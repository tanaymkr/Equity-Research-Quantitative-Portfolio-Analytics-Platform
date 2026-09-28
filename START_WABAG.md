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

Wabag now covers FY2024, FY2025 and FY2026. FY2025 and FY2026 are transcribed from the FY2026 consolidated annual
report, printed pp.244-247 (PDF pp.246-249), in INR million:
https://www.wabag.com/wp-content/uploads/2026/07/Annual-Report-2026.pdf

The report was dispatched on July 20, 2026, confirmed by Wabag's notice in
Business Standard, July 21, p.13:
https://www.wabag.com/wp-content/uploads/2026/07/Post-Dispatch_Newspaper-Publication.pdf

Both years carry the July 20 publication date: FY2025 is a comparative in this
filing, not a reconstruction of information available during FY2025. Before that date, only FY2024 is available from the older filing (from July 23,
2024 onward). FY2025 historical availability still requires its own earlier filing. The default cutoff is September 11, 2026.

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

Historical data and fundamental analytics are available alongside the SQL DCF
and screener. See `START_SQL_DCF.md` and `START_SCREENER.md`.


## FY2023-24 annual report added

`examples/wabag_fy2024_reported_statements.json` adds FY2024 from the original
FY2023-24 annual report, printed pp.298-301 (PDF pp.300-303):
https://www.wabag.com/wp-content/uploads/2025/07/Annual-Report-FY-2023-24-Compressed.pdf

Publication date is July 23, 2024 (dispatch), confirmed in Business Standard,
July 24, 2024, p.15, in the company's post-dispatch notice:
https://www.wabag.com/wp-content/uploads/2024/09/Post-Dispatch-Notice-2024-Advertisements.pdf
The website upload-directory date is not the publication date.

FY2024 in INR million: revenue 28,564; operating EBIT 3,673; D&A 84;
total profit 2,504; owners' profit 2,456; total debt including leases 2,889;
CFO 1,335; gross capex 119. EBIT = 28,564 - 21,672 - (-5) - 2,354 - 84 - 786.
FX losses embedded in other expenses are retained; this classification differs
from the separately excluded FX gains in the newer report. Do not interpret
operating EBITDA as management's adjusted EBITDA.

The source reports assets 45,745, equity 18,239 and liabilities 27,505: a 1 million
rounding residual is retained within the existing validation tolerance.
FY2025 growth and average-balance return metrics now have FY2024 opening data.
FY2023 comparative figures in the older report are outside this update's scope.

This package includes the previous Wabag update as well. Copy its contents into
the repository, replace matching files, and run `Run_Wabag_Analysis.bat` again.
No database deletion is needed; existing FY2025/FY2026 source versions are unchanged.
