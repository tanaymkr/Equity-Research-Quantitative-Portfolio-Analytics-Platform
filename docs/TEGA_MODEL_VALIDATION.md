# Tega model: sources and verification

## Repository reviewed

- Repository: [tanaymkr/Equity-Research-Quantitative-Portfolio-Analytics-Platform](https://github.com/tanaymkr/Equity-Research-Quantitative-Portfolio-Analytics-Platform)
- Main commit: `27a44c22a48fb46bdd786ddc4f32a4dabf776323`, `Add historical financial-statement analysis`.
- [Existing GitHub CI run](https://github.com/tanaymkr/Equity-Research-Quantitative-Portfolio-Analytics-Platform/actions/runs/34204621715): successful at that commit.
- The live repository has 30 tracked files. All 30 were copied and verified against their Git blob hashes before building this update.
- This package adds new files. It does not replace the existing DCF, financial-analysis code, examples, documentation, tests or CI workflow.
- No commit or push was made on your behalf. GitHub CI for this new update can only run after you upload it.

## Primary data source

[Tega Industries Limited Annual Report 2024-25, filed on NSE on 26 August 2025](https://nsearchives.nseindia.com/corporate/TEGA_26082025192638_Intimation_Notice_AGM_2025_sd.pdf).

The report contains consolidated FY2025 statements and FY2024 comparisons. The source figures below were transcribed from those statements and supporting notes, rather than inferred from the synthetic DCF demonstration.

| Data | Source locator in the 327-page PDF |
| --- | --- |
| Consolidated balance sheet | PDF page 224; printed page 242 |
| Consolidated income statement | PDF page 225; printed page 243 |
| Consolidated equity movements | PDF pages 226–227 |
| Consolidated cash flow | PDF pages 228–229 |
| PPE balances and movements | Note 3(a), PDF page 244 |
| ROU assets and lease liability | Note 3(b), PDF pages 246–249 |
| CWIP | Note 3(c), PDF page 250 |
| Intangibles and assets under development | Notes 3(d)–3(e), PDF pages 252–253 |
| Investment property | Note 4, PDF page 254 |
| Cash and other bank balances | Notes 13–14, PDF page 262 |
| Exact year-end share count | Note 19A, PDF page 264 |
| D&A expense by class | Note 36, PDF page 281 |
| Debt and accrued-interest reconciliation | Note 41(c), PDF pages 293–294 |

The official investor page lists a FY2026 annual report, but that report could not be retrieved during this work. This package therefore remains a clearly dated FY2025 historical case. It does not claim to contain the latest available financial period or subsequent acquisition/financing information.

## Reported values used to anchor the model

Consolidated, INR million:

| Metric | FY2024 actual | FY2025 actual |
| --- | --- | --- |
| Revenue | 14,927.14 | 16,386.51 |
| Operating EBITDA | 3,159.72 | 3,398.09 |
| D&A | 636.82 | 1,013.32 |
| Net income | 1,938.57 | 2,001.20 |
| Total assets | 18,901.39 | 20,952.02 |
| Total liabilities | 6,983.20 | 6,985.10 |
| Total equity | 11,918.19 | 13,966.92 |
| Cash | 863.17 | 1,142.95 |
| Borrowing principal excluding leases | 2,431.44 | 2,619.29 |
| Lease principal | 648.71 | 677.20 |
| Operating cash flow | 2,521.42 | 1,950.30 |
| Cash capex, positive magnitude | 554.12 | 1,701.80 |

Historical debt in the existing ratio-module input includes borrowing and lease principal. It excludes accrued interest. The new DCF bridge separately deducts accrued borrowing interest, avoiding double counting with the principal pools.

## Reconciliations and rounding

There are **64 historical checks** covering statement totals, income, cash flows, asset movements, debt movements, and links to reported balances. All pass at the disclosed INR 0.02 million tolerance.

Two nonzero residuals remain visible at source precision:

- The net PPE movement sums to INR 3,658.39 million against the reported closing INR 3,658.40 million: a negative INR 0.01 million residual.
- The short-term debt reconciliation closes at INR 1,432.41 million, versus principal of INR 1,428.67 million plus accrued interest of INR 3.73 million: a positive INR 0.01 million residual.

The model preserves both source figures in each case. It does not overwrite the reported number to make a reconciliation display zero. All other historical residuals are zero to four decimal places.

## Local verification

The complete project passes **51 tests and 6 subtests**, including all existing tests. Ruff 0.16.6 reports `All checks passed!`. Tests ran locally on Python 3.12.13; the existing GitHub workflow uses Python 3.11 and will run for the new update after upload. Source syntax was also checked against Python 3.11's grammar.

The new tests cover:

- Reported history reconciles without silently changing a rounding difference.
- The new normalized history works with the existing financial-analysis module.
- All forecast financial statements, asset and debt schedules link correctly; inputs are not mutated.
- A hand-calculated one-year case independently checks D&A, EBIT, interest, tax, net income, CFO, closing cash, total assets and FCFF.
- Half-year depreciation and final capped charges never depreciate an asset below zero.
- Slower collections use cash; changing asset lives changes EBIT and tax; changing borrowing rates changes interest without changing operating FCFF.
- New leases are noncash financing additions and economic investment in the lease-as-debt DCF.
- A required funding draw is explicit, and an exceeded facility limit stops calculation.
- Losses produce no automatic tax refund; a nonpositive sustainable terminal profit makes DCF unavailable.
- Bad input ranges, mismatched forecast lengths, excessive repayment, unknown keys, duplicate JSON keys and nonfinite JSON constants are rejected.

The base, downside and upside cases all run. Across all 15 forecast-year balance sheets, the largest absolute residual is below INR 0.00000001 million. The 3 × 3 WACC/g sensitivity grid recalculates terminal reinvestment as growth changes. All seven code cells in the new walkthrough notebook were executed successfully.

Commands used for the normal project checks:

```text
python -m pytest
python -m ruff check .
python run_tega_scenarios.py --output examples/tega_model_reports
```

The testing environment used isolated local development dependencies; the model itself uses the Python standard library. `Run_Tega_Model.bat` has been inspected but could not be executed on this Linux verification environment. Its underlying Python launcher was run successfully.

## Modeling boundaries

The balance sheet balances because each supported transaction updates its related statements and schedules, with funding limited by a stated assumption. This does not establish that the forecast assumptions are commercially realistic.

Remaining asset lives, future repayments, the facility limit, operating forecasts, WACC, terminal growth, terminal ROIC and nonoperating values are illustrative. Detailed asset vintages, wear-part reinvestment, contractual maturity ladders, deferred-tax forecasts, acquisition accounting, FX forecasts, and a current diluted equity bridge require further research. The source cash-capex-to-fixed-asset-additions bridge is not fully reconstructed.
