# Wabag linked financial statements and DCF

Copy the update's contents into your existing repository folder, merging folders
and replacing matching files. Run **Run_Wabag_Forecast.bat**. The existing
**Run_Wabag_DCF.bat** now opens this same linked model.

Open **outputs/forecasts/wabag/forecast.html**. The companion `forecast.json`
contains every statement, schedule, resolved driver, source and check.
Python 3.11+ is required; no new runtime packages or downloads are required.
The launcher loads the existing Wabag source files into SQL automatically and
checks that the detailed model agrees with the annual SQL summary.

## Included

- FY2024–FY2026 consolidated history and FY2027–FY2031 forecasts, following
  Wabag's primary statement headings: profit and loss, balance sheet and cash flow.
- Debt, current maturities, revolving facilities, lease interest and repayments.
- Owned PPE, land, right-of-use assets, software, depreciation and amortisation.
- Operating working capital, tax, provisions, credit losses, dividends and equity.
- Dated market inputs, observed beta, market-equity weights and annual WACC.
- Linked FCFF, terminal reinvestment, equity bridge and WACC/growth sensitivity.
- Consensus/broker comparisons, an input register, flagged zero assumptions,
  historical reconciliations and forecast accounting checks.

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
`gsec_yield`, `sovereign_default_spread`, `mature_erp`, `country_risk_premium`,
`country_loading` or `levered_beta`. The original dated evidence remains in
`wacc_reference.json`; document any new observations when updating the model.

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
[Wabag model methods](docs/WABAG_LINKED_MODEL.md) for definitions and limits.

## Commands and GitHub

```bash
python run_wabag_forecast.py
python run_wabag_forecast.py --output outputs/forecasts/wabag_review
python -m pytest
python -m ruff check .
```

The old generic driver-based example is still available with
`python run_sql_dcf.py`, writing `outputs/valuation/wabag/valuation.html`.
It uses a separate, older assumption file and will give a different answer.
The new linked model is the default Wabag launcher.

After reviewing the output, commit the source changes in GitHub Desktop and
push. Generated output and SQLite files remain ignored. Suggested commit:
**Add Wabag linked statements, schedules and sourced WACC**.
