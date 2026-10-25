# Wabag linked financial statements and DCF

A fully linked three-statement model of VA Tech Wabag (income statement,
balance sheet and cash flow, FY2024–FY2026 history and FY2027–FY2031
forecasts) with supporting schedules and an FCFF DCF in three scenarios.

On Windows, double-click `scripts/Run_Wabag_Forecast.bat`; from a terminal,
run `python scripts/run_wabag_forecast.py`. Then open
**outputs/forecasts/wabag/forecast.html**. The companion `forecast.json`
contains all three scenarios, with every statement, schedule, resolved driver, source and check.
The opening page compares **Base, Upside and Downside**. Click a case to open
its complete statements and DCF. Individual reports are in the `base`, `upside`
and `downside` subfolders.
Python 3.11+; no third-party runtime packages and no downloads.
The launcher loads the existing Wabag source files into SQL automatically and
checks that the detailed model agrees with the annual SQL summary.

## Included

- FY2024–FY2026 consolidated history and FY2027–FY2031 forecasts, following
  Wabag's primary statement headings: profit and loss, balance sheet and cash flow.
- Debt, current maturities, revolving facilities, lease interest and repayments.
- Owned PPE, land, right-of-use assets, software, depreciation and amortisation.
- Operating working capital, tax, provisions, credit losses, dividends and equity.
- Dated market inputs, an industry beta relevered each year, market-equity
  weights and annual WACC, using the platform's
  [cost-of-capital method](../COST_OF_CAPITAL.md).
- The WACC implied by the share price, so the gap to the market is measured.
- Base, upside and downside operating cases, each with linked FCFF, terminal
  reinvestment, equity bridge and WACC/growth sensitivity.
- Consensus/broker comparisons, an input register, flagged zero assumptions,
  historical reconciliations and forecast accounting checks.

## Results with the stored inputs

| INR per diluted share | Downside | Base | Upside |
| --- | ---: | ---: | ---: |
| DCF value at the 31 March 2026 anchor | 461.30 | 630.42 | 780.79 |

The FY27 WACC is 13.31% in every case: cost of equity 13.43% from an
Engineering/Construction unlevered beta of 1.14 relevered to 1.155, a 5.25%
default-free rate and India's 7.08% equity risk premium.

Wabag closed at INR2,008.40 on 25 September 2026. Holding the base-case cash
flows fixed, that price implies a WACC of 7.36%. That is below the 12.3%
expected return on an average Indian stock under the same inputs, so the gap is
in the cash flows, not the discount rate. Each extra rupee of revenue ties up
about 48 paise of working capital, so growth of 12–18% a year absorbs most of
the profit. In FY27, free cash flow is −INR91m against after-tax operating
profit of INR4,248m.

## Edit assumptions

Use **examples/wabag_linked/assumptions.json**. Every input has a `value`,
`source` and `reason`. Annual inputs also have a `method`:

| Method | Interpretation |
| --- | --- |
| `absolute` | Use the input directly, in INR million or the stated unit |
| `revenue_ratio` | Multiply the input by that year's forecast revenue |
| `prior_revenue_growth` | Prior-year revenue × (1 + input) |
| `prior_debt_growth` | Prior-year bank borrowing × (1 + input) |

Rates use decimals: `0.135` = 13.5%. Revenue, capex and loan balances use
**millions, not crore**; 10 million = 1 crore. Shares use millions, so EPS
and DCF per share are in INR.

For example, change FY27 `ebitda_margin.value` to `0.14` for a 14% margin,
or change FY29 `revenue.value` to another annual revenue estimate. Historical
expense ratios automatically scale with the new revenue. Sourced absolute
broker expense estimates stay fixed until you edit them. Update `source` to
`analyst` and explain your choice in `reason` when replacing a sourced input.

`declared_dps = -1` means calculate a progressive dividend using the historical
payout ratio and prior declared dividend. It is not a negative cash dividend.
A declaration is paid in the following financial year.

The `policy` section holds terminal growth/ROIC, debt-rate proxies, repayment
assumptions and the cash exclusion. `wacc_overrides` can override `share_price`,
`gsec_yield`, `sovereign_default_spread`, `mature_erp`, `country_risk_premium`
or `unlevered_beta`. The original dated evidence remains in
`wacc_reference.json`, including Wabag's own regression beta as a cross-check;
document any new observations when updating the model.

Nonzero OCI, asset disposals and new equity issuance require additional
accounting schedules and are rejected. Other missing future flows are explicitly
zero-marked. Existing reported assets and liabilities are retained or rolled
forward. Missing critical inputs such as revenue, shares or discount rates
stop the run instead of becoming zero.

## Source hierarchy and scope

Annual-report disclosures supply the history and opening schedules. No complete
annual management IS/BS/CF forecast was found. The August 2026 management call
provides a FY27 EBITDA range; its midpoint is the default. Public MarketScreener
annual estimates supply FY27–FY29 revenue, capex and dividends; Motilal Oswal
supplies certain expense, D&A, borrowing and profit-allocation estimates.
Other lines use three-year ratios/averages or clearly identified modelling choices.

Company guidance ranges are not invented annual point forecasts. Broker PAT,
EPS, P/E and P/B are comparison data; our profit and EPS calculate from the
statements. The public consensus contributor count was not verified. A full
Moneycontrol Pro annual forecast table was not verified; Moneycontrol-hosted
broker reports retain their actual authorship. ICICI estimates are comparisons
because their historical classifications differ.

The estimate snapshots and their dates are intentionally fixed. Rerunning the
model does not silently fetch new forecasts or reset your assumptions. A new
financial year needs updated source inputs and a reviewed adapter; changing
only the year labels is not supported.

## Review before interpreting the valuation

The model is anchored at **31 March 2026**, with information through
**29 September 2026**. It is an illustrative annual valuation using later
information, not a September price target or a contemporaneous March backtest.
A current-date valuation still needs an interim balance-sheet and stub-period
roll-forward.

The important editable judgements are working-capital ratios, repayment timing,
future interest rates, future lease additions, restricted-cash allocation,
book-value claims, dilution and terminal growth/ROIC. A balanced model does not
establish the accuracy of these assumptions. See
[Wabag model methods](../WABAG_LINKED_MODEL.md) for definitions and limits.

## Commands

```bash
python scripts/run_wabag_forecast.py
python scripts/run_wabag_forecast.py --output outputs/forecasts/wabag_review
```

The [generic SQL-backed DCF](sql-dcf.md) (`python scripts/run_sql_dcf.py`)
values Wabag with the reusable engine and a separate, simpler assumption file,
so it gives a different answer. The linked model here is the main Wabag
valuation.

## Operating scenario adjustments

Edit **examples/wabag_linked/scenarios.json** to change the upside/downside
assumptions. The base model in `assumptions.json` is the starting point for
all three cases.

| Case | Revenue levels relative to base, FY27–FY31 | EBITDA margin change | Current receivable collection change |
| --- | --- | --- | --- |
| Base | 1.00× each year | 0 | 0 days |
| Upside | 1.05×, 1.08×, 1.10×, 1.12×, 1.15× | +1 percentage point | −10 days |
| Downside | 0.90×, 0.88×, 0.85×, 0.85×, 0.85× | −1.5 percentage points | +15 days |

These defaults are editable analyst stress assumptions, not published forecasts.
Revenue changes are applied to each base-year revenue level once, not compounded
as extra growth. Historical expense ratios scale with the new revenue.
The collection adjustment changes only current receivables, by days / 365 of
revenue. It does not replace management's differently defined NWC-day metric.

Each case reruns all financial statements, schedules and valuation. The same
debt targets, discount inputs and terminal policy apply by default, isolating
the operating changes. A case that cannot fund itself is marked **Needs revision**
and receives no manufactured valuation. Previous output for that failed case
is replaced so an old successful result cannot be mistaken for the current run.
