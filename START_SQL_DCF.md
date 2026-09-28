# SQL-backed generic DCF: Wabag example

Copy this update into the repository, merge folders and replace matching files.
No deletion or new runtime dependencies are needed. Python 3.11+ is required.

1. Run `Run_Wabag_Analysis.bat` to create/update the three-year SQL history.
2. Run `Run_Wabag_DCF.bat`.
3. Open `outputs/valuation/wabag/valuation.html`.

The complete machine-readable audit output is `valuation.json` in the same folder.
Use GitHub Desktop to commit source changes and push; outputs remain ignored.

## What is now implemented

- SQL selection of latest available consolidated annuals, with publication cutoff.
- Separate editable company assumptions: `examples/wabag_dcf_assumptions.json`.
- Five forecast years: revenue, operating EBIT, NOPAT, D&A, capex, operating
  working capital, change in working capital, FCFF and discounted FCFF.
- CAPM cost of equity and weighted after-tax cost of capital.
- Downside, base and upside assumptions and results.
- Terminal reinvestment based on growth and ROIC.
- Enterprise-to-equity bridge with cash, debt, nonoperating assets, minority
  interests, other claims and explicitly scaled shares.
- Base-case WACC/growth sensitivity and source/input hashes for reproducibility.
- Validation of company identity, currency, units, base period, source dates,
  missing cash/debt, finite numbers and terminal assumptions.

The shared engine is in `src/equity_analytics/valuation/dcf.py`; the SQL adapter
is `src/equity_analytics/valuation/sql_dcf.py`. No Wabag-specific formulas live
in the engine. The example configuration supplies Wabag's supplemental inputs.
The current SQL adapter supports monetary units of million, with shares in
millions. Other units fail explicitly instead of silently producing wrong prices.

The detailed Tega-Molycop model remains its own case study. It does not use the
new Wabag assumptions. The original demo's terminal calculation is preserved
when `terminal_roic` is omitted, so existing callers retain their behaviour.

## Forecast conventions

`FCFF = EBIT * (1 - tax rate) + D&A - capex - change in operating NWC`.
Taxes assume positive operating profit; this version does not model loss
carryforwards. EBIT margins must be nonnegative. Annual periods use end-of-year
discounting. This is a driver-based FCFF forecast, not a fully linked projected
income statement, balance sheet and cash-flow statement.

Opening NWC is an explicit sourced trade/contract proxy, not automatically
current assets minus current liabilities. The first year's change uses that
opening amount. Future NWC is a revenue ratio. Wabag's proxy and management's
working-capital-days KPI have different definitions: no automatic reconciliation
or cash release is assumed between them.

`terminal FCFF = final NOPAT * (1 + g) * (1 - g / terminal ROIC)`.
Terminal value divides this by WACC minus growth. This method includes total
terminal reinvestment without separately subtracting capex/NWC a second time.
Terminal ROIC and transition to steady state are explicit analyst assumptions.

`equity = EV + cash + nonoperating assets - debt - minority value - other claims`.
Negative equity, if produced, is retained instead of clamped to zero. Reported
cash/debt are pulled from SQL; every supplemental bridge input is in the JSON.

## Evidence and assumptions

The configuration's `sources` and `rationale` sections are reproduced in the
HTML report. They distinguish guidance, historical ratios and analyst choices.
Guidance comes from Wabag's August 2026 management call. The file records a
conservative September 28 availability date based on retrieval, not an asserted
original transcript filing date. Annual-report source dates are retained.

Management EBITDA includes operating FX, while bank charges are below its
headline EBITDA. Forecast EBIT therefore deducts bank charges and D&A from
assumed management EBITDA. Historical SQL EBIT uses a different definition,
so the configuration explicitly documents the conversion. The historical
financial dataset is not rewritten to manufacture agreement.

No verified multi-broker consensus dataset was available for this build.
Historical pooled ratios inform D&A/capex and a normalized tax assumption.
Later growth/margin paths are analyst estimates. All three cases use individually
visible assumptions; a downside case may fall below management guidance.

## Important limits before treating this as an investment valuation

- This is an annual model anchored at March 31, 2026 using information and
  assumptions available later, through September 28, 2026. It is not a
  September spot valuation, a contemporaneous March valuation, or a backtest.
  There is no quarterly stub-period or interim balance-sheet roll-forward.
- Risk-free rate, beta, ERP and target debt weight are illustrative CAPM inputs,
  not verified current market observations. Cost of debt uses historical
  borrowing interest/average lease-inclusive debt, not all finance costs.
- Shares use ending issued shares plus incremental diluted-EPS options as a
  proxy. A current treasury-stock dilution calculation is not yet implemented.
- Investment and minority adjustments use book-value proxies, not fair values.
  All reported cash is assumed available; operating/restricted cash, claim and
  contingent-liability reviews remain necessary before investment use.
- Physical capex is not all business reinvestment: contract working capital
  is explicitly forecast. Provisions and detailed HAM project models are not.
- No live stock price or upside/downside versus market is reported.

These limitations are shown in the output, not hidden behind a price target.
The next refinement is a dated market-input/claims review and valuation-date
roll-forward; adding more companies is not required for this milestone.

## CLI and checks

```bash
python run_sql_dcf.py --db outputs/data/research.sqlite --assumptions examples/wabag_dcf_assumptions.json --output outputs/valuation/wabag
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

Changing SQL annuals to a newer base year intentionally requires reviewing the
assumptions file. Missing inputs cause an error rather than zero-filled forecasts.
