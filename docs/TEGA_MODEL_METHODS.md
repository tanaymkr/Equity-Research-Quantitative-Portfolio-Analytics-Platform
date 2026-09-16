# How the linked Tega model works

This document describes the FY25 archive. For FY26 statements and the current
model paths, read [the FY26 walkthrough](TEGA_FY2026_STATEMENTS.md).

This is a historical FY2025 learning and research case. Reported FY2024/FY2025 statements are sourced from Tega's audited consolidated accounts. All future operating and valuation inputs are explicitly illustrative analyst assumptions.

## Files and reading order

| File | Purpose |
| --- | --- |
| `examples/tega_fy2025_reported_statements.json` | Audited historical income statement, balance sheet, cash flow, asset groups and FY2025 supporting reconciliations |
| `examples/tega_fy2024_fy2025_financial_history.json` | The same core facts normalized for the existing financial-analysis module |
| `examples/tega_fy2025_forecast_assumptions.json` | Base-case forecast and DCF assumptions |
| `src/equity_analytics/forecasting/inputs.py` | Input validation and historical accounting checks |
| `src/equity_analytics/forecasting/engine.py` | The linked forecast and valuation calculations |
| `src/equity_analytics/forecasting/reporting.py` | Human-readable reports generated from calculated records |
| `run_tega_model.py` | A small launcher that finds the local source and inputs |
| `tests/test_forecasting.py` | Independent arithmetic, model links and error-path tests |
| `notebooks/tega_linked_model_walkthrough.ipynb` | A guided notebook for inspecting and changing the model |

The new module is additive. The original `valuation/dcf.py` remains the earlier simplified DCF engine, and its sample data is still synthetic. The new Tega DCF uses the new linked forecast; it does not reinterpret the old demo as reported Tega data.

## Units, dates and scope

Every financial amount is in **INR million**; shares are in **millions of shares**, making equity value divided by shares equal to INR per share. One crore equals ten million. The source is consolidated, not standalone.

The base balance sheet is at 31 March 2025. The annual report was filed on 26 August 2025, which is the information cutoff. FY2026–FY2030 are modeled forecast columns even where a fiscal year has since ended. They are not observations of those years. The DCF uses 31 March 2025 as its fiscal-year-end discount reference; because it uses information published later, it is not a valid point-in-time March 2025 backtest.

## Reading the actual statements

The JSON preserves source line items and reported totals. For the analytical balance sheet, trade payables are aggregated across MSME/other suppliers. Term borrowings include current maturities; short-term borrowings exclude those maturities. Lease liabilities are their current plus noncurrent amounts. The original classifications remain in `reported_totals`.

Retained earnings are separately identified. Other reserves equal reported other equity minus retained earnings. Noncontrolling interests round to zero in this report; that does not prove they have no economic value.

`reconcile_history()` checks the statement totals, income calculations, cash flow subtotals, opening-to-closing cash, asset schedules, debt schedules, and links to the balance sheet. The company reports amounts to INR 0.01 million, so the allowed historical reconciliation tolerance is INR 0.02 million. Every residual appears in the report. The code does not insert rounding adjustments or cash plugs.

Operating EBITDA excludes other income and equity-accounted JV profit. Operating EBIT subtracts reported D&A from that EBITDA. The reported P&L's finance costs and the cash flow statement's finance-cost addback are different source figures; the history preserves both.

## Step 1: revenue and operating profit

`revenue = prior_revenue × (1 + revenue_growth)`

`EBITDA = revenue × EBITDA_margin`

`EBIT = EBITDA − depreciation_and_amortisation`

EBITDA is the operating assumption so changing an asset life changes D&A and EBIT. A fixed EBIT margin would conceal that effect. This version does not forecast each expense category or business segment separately.

## Step 2: working capital

`receivables = revenue × receivable_days / 365`

`inventories = revenue × inventory_pct_revenue`

`trade_payables = revenue × payables_pct_revenue`

`operating_NWC = receivables + inventories − trade_payables`

An increase in operating NWC uses cash. Inventory and payables use explicit revenue ratios, not mislabeled inventory/payable days based on incomplete COGS. Other operating asset and liability accounts remain individually constant in this initial version; their assumed changes are zero. Historical cash working-capital movements come directly from the cash flow statement and need not equal simple reported balance-sheet changes because FX, noncash items and classifications also matter.

## Step 3: capex, construction, depreciation and amortisation

Cash capex is `revenue × cash_capex_pct_revenue`. The tangible share goes into capital work in progress (CWIP), and the remainder into intangible assets under development. The commissioning assumption transfers a fraction of opening construction balances plus current additions into usable assets. Transfers are not a second cash outflow.

Opening PPE, right-of-use (ROU) and intangible balances are grouped into source-based cohorts. Each cohort's annual depreciation is opening net book value divided by **assumed remaining life**. Those remaining lives are analyst estimates, not reported facts. Owned land has no depreciation. Leasehold land is part of ROU and does depreciate. Goodwill and assets still under construction are not depreciated.

Newly commissioned assets use their assumed useful life and receive a half-year charge initially, a full-year charge in following years, and a final capped charge. Book value never drops below zero. Zero residual values are assumed. New PPE uses one blended life; Tega's plant category also includes short-lived customer wear parts, making a detailed wear-part replacement schedule a later research improvement.

`closing_net_asset = opening_net_asset + additions − depreciation`

The report displays each cohort, its D&A, and CWIP/development movements. Historical FX, disposals, accumulated depreciation removed on disposal, and CWIP transfers are shown separately in the reported reconciliations. They are not projected in the illustrative forecast.

Historical cash capex differs from accounting additions. The report's acquisition of capital assets is the cash-flow input; PPE additions, construction transfers, capital advances and noncash leases have different scopes. This version does not claim to have reconciled every historical cash-capex-to-fixed-asset difference.

## Step 4: debt and leases

The model has three principal pools: term debt, a simplified revolving facility, and lease liabilities.

`closing_term_debt = opening_term_debt − principal_repayment`

`closing_lease_debt = opening_lease_debt + new_leases − principal_repayment`

`interest = opening_principal × interest_rate`

Interest is paid during the year. Principal movements and revolver funding are modeled at year end, so new draws do not incur interest until the next modeled year. This convention avoids an interest/cash circularity; average debt or monthly schedules would be a later refinement.

New leases create equal asset and liability amounts in the **forecast**. They do not provide cash. The actual report's new ROU asset amount and its new lease-liability amount differ; the historical records retain those separately. Forecast lease interest is an expense and financing cash outflow; lease principal reduces the liability and is another financing cash outflow.

Disclosed current maturities inform the first modeled term and lease payments. Later repayments are assumptions, not an extracted contractual maturity schedule. Short-term reported borrowings are treated as a simplified revolver; the assumed facility limit is not a verified bank commitment. The forecast balance sheet uses aggregated principal pools rather than a statutory current/noncurrent maturity presentation.

### What noncash debt movements mean

Tega's actual FY2025 debt reconciliation includes FX movements, interest accruals, new leases and other changes. These can change the reported liability without a cash borrowing or principal payment. The historical schedule includes accrued interest where its title says so. The forecast principal pools exclude accrued interest; opening accrued interest remains in the individually frozen other financial-liability accounts.

Historical debt signs are normalized so positive movements increase a liability. A current/noncurrent reclassification does not change total debt. 'Other' is retained as the report's label; the model does not invent an explanation for an undisclosed movement.

## Step 5: earnings, tax, equity and cash

Forecast JV profit is an explicit flat input and is equity-accounted after the JV's own tax. No additional group-level tax on that profit or its dividend is assumed. Other income is assumed zero.

`profit_before_tax = EBIT + JV_profit − finance_cost`

`tax = max(EBIT − finance_cost, 0) × tax_rate`

`net_income = profit_before_tax − tax`

The model assumes tax expense equals cash tax. It does not recognize automatic cash refunds in loss years or tax-loss carryforwards. Opening tax assets/liabilities and deferred-tax balances remain constant; a full jurisdiction-specific deferred-tax schedule is not implemented.

`dividends = max(net_income, 0) × payout_ratio`

`closing_retained_earnings = opening_retained_earnings + net_income − dividends`

Share capital and other reserves remain constant. No future OCI, share issuance or acquisitions are assumed. JV carrying value increases by its profit and decreases by the JV dividend; a negative carrying value stops calculation.

`CFO = net_income + D&A + interest − JV_profit − change_in_operating_NWC`

`CFI = −cash_capex + JV_dividend`

`CFF = debt_draws − debt_principal_paid − lease_principal_paid − interest_paid − dividends`

`closing_cash = opening_cash + CFO + CFI + CFF`

Interest is added back in CFO because it is paid in CFF. This preserves the chosen financing presentation. If pre-funding cash falls below `minimum_cash`, the model draws only the needed amount on the assumed revolver. If the facility limit cannot cover it, `FundingError` stops the calculation. With cash sweep enabled, available excess cash first repays the revolver.

Assets, liabilities and equity are then summed independently. Both their balance and the retained-earnings/cash rolls are checked. There is no balancing 'other asset', invented equity or residual cash entry. The only automatic funding is the explicit, capped revolver.

## Step 6: DCF from the linked forecast

`NOPAT = EBIT − max(EBIT, 0) × tax_rate`

`FCFF = NOPAT + D&A − cash_capex − new_leased_assets − change_in_operating_NWC`

Leases are treated as financing. Lease principal is deducted in the enterprise-to-equity bridge, ROU depreciation is included in D&A, and new leased assets count as economic investment in FCFF. Omitting that investment while deducting lease debt would distort the model. Debt interest and principal payments are excluded from FCFF.

Operating FCFF excludes JV earnings and dividends; the JV receives a separate assumed value in the bridge. The historical property is vacant investment land, held constant without operating income, and likewise receives a separate assumed value. Current investments are assumed realizable at carrying value. Other bank balances are excluded from surplus cash because they include restricted and earmarked deposits.

`terminal_NOPAT = final_year_EBIT × (1 + g) × (1 − tax_rate)`

`terminal_FCFF = terminal_NOPAT × (1 − g / terminal_ROIC)`

`terminal_value = terminal_FCFF / (WACC − g)`

The terminal period uses explicit reinvestment linked to growth and ROIC rather than extrapolating a year in which opening assets may be running off. WACC and terminal ROIC must both exceed growth. Positive terminal NOPAT is required; otherwise valuation is marked unavailable. Terminal operating margins and all valuation parameters still require research and normalization.

All annual FCFF and terminal value are discounted at year end. The equity bridge adds cash, current investments, and the assumed values of the JV and investment property, then subtracts term debt, short-term debt, leases, accrued borrowing interest and assumed NCI value. The default JV/property values use carrying-value proxies; they are not independently appraised research estimates. Shares are the actual year-end 66.535492 million, not a forecast diluted share count.

## Run a different scenario

Each scenario JSON is a complete, editable assumption set. In **Command Prompt** from the repository folder:

```bat
python run_tega_model.py --historical-fy2025 --assumptions examples/tega_fy2025_downside_assumptions.json --output outputs/tega_downside
python run_tega_model.py --historical-fy2025 --assumptions examples/tega_fy2025_upside_assumptions.json --output outputs/tega_upside
```

The base case is the default when no options are passed. Precomputed scenario summaries explain exactly which operating inputs differ. The scenarios have no assigned probabilities and are not estimates of actual FY2026 performance.

## Limits that matter when presenting the project

Describe this as a **Python model built on audited historical Tega data with illustrative forecasts**. It is not yet a current investment recommendation. Before that, extend and reconcile the historical series, incorporate subsequent acquisitions and funding, research segment-level revenue/cost drivers, separate wear-part investment, obtain debt/lease maturity details, assess deferred taxes and nonoperating assets, and calibrate WACC, terminal assumptions and diluted shares.
