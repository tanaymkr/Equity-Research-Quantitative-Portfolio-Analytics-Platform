# FY26 statements: source, reconciliation and model connections

The complete FY2025/FY2026 consolidated income statements, balance sheets and
cash-flow statements now live in `examples/tega_fy2026_reported_statements.json`.
FY2025 is the comparative column of the FY2025-26 report. The reported statements
are separate from all forecast assumptions.

Source: [Tega Industries Annual Report 2025-26](https://www.tegaindustries.com/assets/pdfs/int/2026/20260828_105759.pdf),
audited 29 May 2026 and published 28 August 2026. All financial amounts below are
INR million. One crore equals ten million.

| Source | PDF page | Contents |
| --- | --- | --- |
| Consolidated balance sheet | 202 | Assets, liabilities, equity and current/noncurrent classifications |
| Consolidated income statement | 203 | Revenue, expenses, JV income, tax, PAT, OCI and EPS |
| Changes in equity | 204-205 | Share issue, issue expenses, retained earnings and reserves |
| Consolidated cash flows | 206-207 | Every operating adjustment, working-capital movement, investing and financing line |
| Notes 3(a)-3(e) | 220, 222-228 | PPE, leases, CWIP, intangibles and asset movements |
| Notes 13-14 | 234 | Cash, deposits, pledged deposits and unpaid dividends |
| Notes 19A/19C, 24 | 236-239, 242 | Shares, reserves and current debt maturities |
| Note 41(c) | 261-262 | Borrowing and lease roll-forwards, including cash and noncash movements |
| Notes 42-43, 47 | 263-264, 270 | Segments, EPS and acquisition transaction expenses |

The statements contain analytical pools for term debt, short-term debt, leases,
trade payables and reserves. Supporting disclosures retain the current maturities,
current/noncurrent lease split, trade-payable split and OCI components. Term debt
includes current maturities; the short-term pool excludes them. Shares are in
millions in the statement schema and actual units in the acquisition schema.

## Reconciliations

The FY26 source passes **92 checks**. Examples:

| Check | Reconciliation |
| --- | --- |
| Balance sheet | 43,145.00 assets = 9,073.24 liabilities + 34,071.76 equity |
| PAT | 2,011.12 PBT - 918.40 current tax + 333.81 deferred-tax credit = 1,426.53 |
| Closing cash | 1,142.95 opening + 3,503.39 CFO - 10,044.18 CFI + 16,899.06 CFF + 137.64 FX = 11,638.86 |
| Equity | 13,966.92 opening + 1,426.53 profit + 1,780.91 OCI - 133.07 dividends + 85.93 capital + 17,046.94 premium - 102.40 issue costs = 34,071.76 |
| D&A | 647.07 PPE + 252.14 ROU + 51.94 intangibles = 951.15 |
| Borrowings and leases | 1,275.60 noncurrent borrowing + 1,900.53 current borrowing + 807.88 leases = 3,984.01 |

Checks also cover cash-flow subtotals, share counts and issuance cash, EPS,
segment revenue, bank-note splits, debt-note endpoints, cash movements, asset
cohorts and current balance-sheet classifications. Source rounding up to INR0.02m
is shown explicitly; no balancing plug is inserted.

Cash capex is **1,359.36**, from the cash-flow statement. It is not interchangeable
with PPE additions or CWIP additions/capitalisations. Likewise, ROU additions of
337.79 and new lease liabilities of 337.72 are preserved as separate reported
amounts. Note 41(c) includes accrued interest; the balance-sheet debt pools exclude
it. The share denominator is **75.127698 million**, not the EPS weighted average
of 69.454488 million.

Reported operating EBITDA is **2,311.40**, excluding other income and including
775.77 of acquisition transaction expense. That expense is not silently removed
from reported earnings. Forecast operating margins are explicit assumptions.

## Where the numbers flow

`tega_fy2026_reported_statements.json` feeds both active paths:

1. **Default acquisition valuation:** `run_tega_model.py` resolves the statement
   file referenced in `tega_molycop_facts.json`, runs all historical checks and
   derives the legacy annual inputs. These drive segment revenue, opening cash,
   debt, working capital, asset balances, nonoperating assets and issued shares.
   The duplicated FY26 financial block was removed from the editable acquisition
   facts file. A missing or unreconciled statement file stops the run.
2. **Financial ratios:** `run_financial_analysis.py` accepts the same complete
   statement file, validates it, and derives its inputs without a second editable
   FY26 dataset.

## Run and read

With Python 3.11+, double-click `Run_Tega_Model.bat`. Open
`outputs/tega_molycop/report.html` and choose **Complete FY26 statements**.

The committed example can be read without Python:
`examples/tega_molycop_reports/historical_statements.html`.
It includes every statement row, supporting reconciliations and source locations.
`historical_checks.json` contains the calculated residuals;
`reported_statements_used.json` is the exact statement snapshot used.

Optional commands in Command Prompt, opened in the repository folder:

```text
python run_tega_model.py
python run_financial_analysis.py examples/tega_fy2026_reported_statements.json --output-dir outputs/history-tega-fy2026
```

The older FY25-based forecasts and the separate legacy-only forecast have been
removed. Audited FY24/FY25 source files remain available for historical analysis;
FY26 actuals remain the current model's historical foundation.

## Effect on the acquisition DCF

Under unchanged acquisition assumptions, the displayed scenario values remain
unchanged: the selected FY26 numerical inputs already used by the acquisition
DCF agree with the full reported statements. This update replaces the duplicated
input block with a reconciled common source and supplies the missing full
statements and supporting schedules; it does not fit values to the share price.

The acquisition valuation is still dated 30 June 2026, using reviewed disclosures
through 11 September 2026. March actuals do not establish June closing cash,
acquired working capital, preference-return economics or final purchase accounting.
Those estimates remain labeled. A complete statutory forecast of the acquired
group's balance sheet is still outside the available source detail.
