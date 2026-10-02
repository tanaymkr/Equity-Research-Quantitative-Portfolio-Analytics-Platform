# Wabag forecast methods — 29 September 2026

The company adapter is `case_studies/wabag`. The independent shared engine
`valuation/explicit.py` discounts the adapter's supplied cash flows. It never
recreates them using the old generic revenue/margin assumptions.

## Architecture and source controls

1. Load three annual consolidated statements from the existing SQL pipeline.
2. Reconcile revenue, consolidated profit, cash and lease-inclusive debt to the
   detailed sidecar `examples/wabag_linked/history.json` (12 comparisons).
3. Validate statement identities, source dates, units, required fields and beta.
4. Resolve annual drivers and roll forward the asset, debt, tax and equity schedules.
5. Calculate cash through CFO + CFI + CFF. No balancing asset or unlimited debt
   draw is inserted. Insufficient cash above the configured restricted floor
   stops the run with a funding-shortfall message.
6. Reconcile FCFF independently to the cash-flow statement, then discount it.
7. Export offline HTML/JSON, assumptions and SHA-256 input fingerprints.

Three-year fallbacks are reproducible from the included histories. Revenue
uses the FY24–FY26 CAGR (two intervals). Expense/balance ratios use the sum of
three years' expense or year-end balance divided by the sum of revenue, rather
than averaging ratios with different denominators. Taxes use profit before
associate earnings. Debt's later trajectory uses its three-year CAGR. Historical
averages are starting assumptions, not evidence that the trend will persist.

The original statements retain source rounding. FY24 assets exceed rounded
liabilities plus equity by INR1m. Forecast checks use a 1e-6m tolerance and do
not carry this historical discrepancy into a new balancing account. FY26, the
forecast anchor, reconciles exactly. Historical checks allow INR1m rounding.

## Income statement

Revenue and selected EBITDA margins determine total operating expenditure.
Employee costs and other expenses follow explicit broker forecasts, then
historical ratios. Cost of sales is the residual needed to achieve the margin
once the inventory movement and other expense budgets are included. It is
identified as a derived allocation, not an independently verified procurement
forecast. An edited FX gain reallocates this fixed total-margin budget.

Wabag presents transactional forex gains separately but regards them as
operating. No reliable annual FX forecast was found: future gains are an explicit
zero. FY24 FX remains inside its originally reported other-income line.
Bank charges remain in the statement's finance-cost line, but are subtracted
as operating expenses in FCFF. Only borrowing and lease interest are financing
costs in the WACC debt-cost calculation.

Interest income uses opening cash/bank balances and a pooled historical yield,
avoiding circular interest-on-closing-cash. Dividends received use the three-year
average, which includes a high FY24 receipt and needs review. Associate earnings
roll into the investment balance and are removed from CFO. They are excluded
from the tax base to avoid taxing the investee's earnings again.

Total profit, owners' profit and EPS are calculated; consensus profit is never
used as a balancing target. Expense budgets already include credit losses,
provision charges and share-based compensation. Those noncash amounts must not
be charged a second time when preparing the cash-flow statement.

## Balance sheet, working capital and cash flow

The detailed primary-statement layout includes non-current/current receivables,
other financial assets, contract/other current assets, inventories, payables,
provisions, taxes, bank balances, debt, leases, capital and reserves.
Operating balance ratios revert to their three-year pooled level in the first
forecast year. This explicit transition can cause a working-capital release
or investment and materially affects FCFF; inspect it before changing assumptions.

Operating NWC includes other bank balances as an explicit collateral policy.
It excludes cash equivalents, income/deferred tax balances, loans/investments
and financing debt/leases. This is broader than the earlier trade/contract
proxy and differs from management's 100–110 working-capital-day KPI. There is
no unsupported reconciliation of those definitions.

Credit-loss allowances are separate from net receivables. CFO adds the expense
back and subtracts the gross receivable cash movement, including the write-off
adjustment, so an allowance change alone creates no cash. Provisions show
opening stock + charge − net utilisation = closing stock. Unexplained negative
utilisation stops the run instead of creating an unsupported noncash credit.

Current tax paid reflects tax expense, tax assets and tax liabilities. Deferred
tax movements affect the deferred-tax asset without becoming cash. The adapter
supports an asset, not a new net deferred-tax liability. Jurisdiction-level
losses, expiry dates, detailed tax depreciation and deferred-tax liability
creation are outside this model.

## Debt and assets

FY26 bank debt is INR2,255m; leases add INR29m. Opening bank debt is grouped into
INR1,828m term funding, including INR294m current maturities, and INR427m revolving
facilities. Annual broker gross-debt targets constrain the schedule. Term
repayments reduce the balance, with the remaining target allocated to working
facilities. If the target is below scheduled closing term debt, explicit extra
repayment is recorded. This is a financing scenario, not an asserted committed
credit-facility limit.

The term-rate proxy weights the disclosed non-current NCD and term amounts/rates.
The historical working-facility proxy uses borrowing interest divided by average
gross borrowings over FY25 and FY26, drawing on all three year-end balances.
Regional loan allocation is incomplete. Lease rates use the three-year reported
interest/lease-balance proxy. None is a company-issued future interest-rate
forecast. Interest uses average opening/closing principal. Current maturities
are reclassified without producing an extra cash repayment.

Fixed assets separate land (non-depreciable), owned PPE, right-of-use assets and
software. Cash capex follows public consensus, then the historical ratio.
Depreciation targets follow the explicit broker estimates, then the historical
ratio; allocation uses FY26 charges of 43:15:4 and is capped by available asset
values. Any unused target is disclosed. This is not a full useful-life/vintage
model. No new leases are assumed unless supplied. When supplied, lease additions
increase both assets and lease financing and count as noncash reinvestment in FCFF.

## Equity, shares and valuation

Cash dividends pay the prior fiscal year's declared dividend. Later declarations
use the historical payout ratio with a floor at the preceding declaration.
Share-based compensation credits reserves and is added back in CFO. FCFF removes
that add-back, retaining the economic compensation cost; no future issuance is
invented to offset it. Ending basic shares are held fixed. The opening incremental
option dilution is a proxy; loss-year EPS uses basic shares to avoid antidilution.

Cash, investments, related-party loans, debt and minority claims in the DCF bridge
are opening balances, not the fifth-year cash generated by the forecasts. All
other bank balances are treated as operating collateral, so they are not added
again to equity value. The additional cash exclusion of INR1,217m assumes the
INR202m restriction and INR1,015m encumbrance do not overlap and lie entirely
within cash equivalents. This allocation is not verified and can overexclude
cash; it is explicitly editable. Book associate/other-investment/loan values
and minority interests are valuation proxies, not measured market values.

Observed weekly beta is recomputed from 125 stored Wabag and NIFTY50 price-return
pairs. Both instruments use matching observation dates within consecutive calendar
weeks; holidays can make the interval six or eight days. There is no missing-price
fill or implied dividend-reinvestment claim. These are later vendor snapshots,
not historical point-in-time prices. The observed R-squared is about 0.152.

Default-free INR rate = 7.1194% G-sec yield − 1.87% sovereign default spread.
Cost of equity = default-free INR rate + relevered beta × 4.23% mature-market
ERP + 2.85% India CRP × country loading. This is an analyst-selected CAPM/country-risk
framework. Beta is unlevered at reported gross debt and dated market equity,
then relevered at each forecast year's average gross debt. Market equity remains
reference price × basic shares; it is not replaced with book equity or the DCF
result. Debt approximates market value using its book amount. Forecast WACC
therefore changes with debt, borrowing rates and tax while market observations
are held constant. It is not a published Wabag or consensus WACC.

Explicit FCFF uses operating NOPAT (no negative-profit tax benefit), D&A, cash
capex, noncash lease additions and operating NWC. The CFO reconciliation removes
SBC's add-back and replaces reported cash tax with unlevered operating tax.
Exceptional cash items are excluded from recurring FCFF. Debt draw/repayment,
dividends and non-operating asset allocation do not become operating cash flow.

Discounting uses the product of annual (1 + WACC) factors. Terminal FCFF uses
NOPAT × (1 + growth) × (1 − growth / ROIC), avoiding a second terminal deduction
for capex or NWC. Terminal growth 4% and ROIC 15% are editable analyst choices.
The last forecast WACC is the terminal WACC; terminal financing is not separately
optimised. No management ROE target is relabelled as a ROIC forecast.

## Validation

After the scenario correction: 246 tests and 13 subtests pass; Ruff passes. The Wabag addition
includes tests for cash/equity dividend timing, debt draw/interest/tax effects,
capex and valuation, bank-charge classification, allowance double counting,
lease reinvestment, depreciation limits, historical driver scaling, missing
critical inputs, source cutoffs, beta integrity and SQL mismatches. The shared
explicit DCF has an independently hand-calculated two-period test with unequal
annual discount rates and a terminal-ROIC calculation.

The report checks 40 forecast identities, 36 historical reconciliations and 12
SQL values. These checks verify accounting and software behaviour; repayment
allocation, source differences, working-capital conversion and terminal economics
still require research judgement. A stub-period/current-date valuation and full HAM project model remain future
refinements. Base, upside and downside operating cases now run through the linked
model using editable analyst stresses in `scenarios.json`. The scenario dashboard
links to full reports for each case, and tests cover base preservation, annual
level adjustments, complete exports and failed-stress output replacement.
The legacy generic DCF retains its separate illustrative scenarios.
