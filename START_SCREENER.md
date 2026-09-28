# Fundamental stock screener

Copy this update's contents into your repository folder, merging folders.
Run `Run_Screener.bat`, then open `outputs/screener/screener.html`.
If the database is missing, run `Run_Wabag_Analysis.bat` first.
No new runtime packages are required. Python 3.11+ is supported.

This package adds new files only. It does not replace DCF assumptions, valuation
code or your existing README. It works with the verified three-year Wabag update
and can also be used after the SQL DCF update.

## What you can change

Edit `examples/screener_config.json` in a text editor and rerun the launcher.
The initial filter is an editable example, not an investment recommendation:

- Revenue growth at least 10%.
- ROE at least 10%.
- Debt/equity at most 1x.
- Cash flow after capex at least zero.
- Sort by ROE, highest first.

All filters must pass (AND). Both minimum and maximum are inclusive.
Use `"filters": {}` to see every eligible company. A filter may have `min`,
`max`, or both. Unknown metric names and contradictory bounds fail explicitly.

Rates use decimals: **0.10 means 10%**, not 10. CSV rates remain decimals;
HTML displays percentage metrics as percentages. Multiples use x.
All monetary screening fields use **millions of the selected currency**:
INR 1 crore becomes INR 10 million. No FX conversion occurs; other currencies
are excluded with a reason.

`sort_by` selects one metric. `ascending: true` sorts lowest first;
`false` sorts highest first. Ties use company ID; position is an ordinal list
position among matches, not a factor score or a claim that a stock is better.
`columns` changes the HTML table; CSV and JSON retain all supported metrics.

## Missing numeric data: zero

As requested, any unavailable calculated metric becomes **0** for filtering,
sorting and output. This includes missing inputs, missing prior-year balances,
and ratios the analytics layer cannot compute (such as a zero denominator).
Substitution happens after the financial calculations; individual statement
inputs are not altered or replaced before calculating ratios.

- HTML marks substituted values with `*` and explains why.
- CSV contains one `<metric>_zero_filled` boolean per metric plus reasons.
- JSON contains the substituted values and a `zero_filled` reason mapping.
- Genuine calculated/reported zeros are not flagged as substitutions.
- Source SQL nulls and the existing financial/DCF modules remain unchanged.

A missing debt/equity ratio therefore passes a maximum-zero filter; this is the
selected zero policy. A company with no available filing is excluded, not
invented as an all-zero company. Corrupt SQL or invalid data stops the run.

## Timing and universe

- `as_of`: publication cutoff, inclusive, using the existing SQL version selector.
- `period_end`: defaults to `2026-03-31` so companies share the same annual end.
  Set to `null` to use each company's latest available year; dates are displayed.
- `max_age_days`: defaults to 550 calendar days between period end and cutoff.
  Set to `null` to disable, for example when examining older financial years.
- `company_ids`: `null` discovers all stored profiles; or use `["TEGA", "WABAG"]`.
- `basis`: `consolidated` by default; `standalone` is supported if loaded.
- `currency`: defaults to INR.

Synthetic DEMO data is excluded. Missing periods, unavailable histories, stale
financials, other currencies and unknown requested company IDs are listed with
reasons. No new financial data is fetched from the internet by the screener.
Historical annual-report availability still has the limitations of the data
layer; this module is not a survivorship-free research universe or backtest.

Tega's reported financials precede the Molycop acquisition. The screener uses
those reported statements, not the Tega-Molycop pro-forma model or DCF estimates.
Company-specific accounting definitions remain relevant to comparisons.

## Supported metrics

| Type | Keys |
|---|---|
| Money, in millions | revenue, ebitda, net_debt, cash_flow_after_capex |
| Fractions | revenue_growth, net_income_growth, ebit_margin, ebitda_margin, net_margin, roe, roa, roce, operating_cash_flow_margin, capex_to_revenue |
| Multiples | current_ratio, debt_to_equity, net_debt_to_ebitda, finance_cost_coverage, operating_cash_flow_to_net_income |

ROE uses owners' profit / average owners' equity. Finance-cost coverage uses
all finance costs, not only interest. CFO less capex is not automatically FCFF.
The definitions are inherited from `financials/ratios.py`.

## Outputs

- `screener.html`: matches, all evaluated companies, failed filters and exclusions.
- `screener.csv`: matched companies, sorted; headers remain even when empty.
- `all_companies.csv`: all evaluated companies, including nonmatches.
- `screener.json`: configuration, units, results, source metadata and audit reasons.

CSV files use UTF-8 with BOM for Excel. Formula-like text is prefixed with an
apostrophe; numeric negative values remain numeric. Generated outputs are ignored
by git. Commit/push the new source files through GitHub Desktop as usual.

## Command line

```bash
python run_screener.py
python run_screener.py --config examples/screener_config.json --db outputs/data/research.sqlite --output outputs/screener
python run_screener.py --as-of 2026-09-28
```

Implementation lives in `src/equity_analytics/screening/`. The Windows launcher
calls the same entry point as the CLI. No DCF assumptions are used for screening.
