# Cost of capital and the market check

Every DCF in the platform uses one cost-of-capital method, implemented once in
`src/equity_analytics/valuation/cost_of_capital.py`. Each report then asks
what discount rate the share price implies, so the gap between model and market
is measured rather than tuned away.

## Method

```text
Risk-free rate   = 10-year government bond yield − sovereign default spread
Levered beta     = industry unlevered beta × (1 + (1 − tax) × D/E + P/E)
Cost of equity   = risk-free rate + levered beta × equity risk premium
WACC             = E/V × Ke + D/V × Kd × (1 − tax) + P/V × Kp
```

- **Risk-free rate.** The Indian 10-year G-sec includes India's default risk,
  so the default spread is removed before the country risk premium is added
  back in the equity premium. Otherwise country risk would be counted twice.
- **Equity risk premium.** India's total premium is the mature-market premium
  of 4.23% plus a country risk premium of 2.85%, giving 7.08% (Damodaran,
  January 2026). USD cash flows use the mature-market premium alone.
- **Beta.** Each business takes an industry unlevered beta and relevers it at
  the capital structure that also sets its WACC weights. Preference capital
  (P) has no tax shield. The stocks' own regression betas are reported only
  as cross-checks, because they are statistically too weak to value a company
  (see below).
- **Scenarios.** Downside, base and upside change operating drivers only. Every
  scenario uses the same discount rate, terminal growth and terminal ROIC.
  Discount-rate and terminal assumptions are tested in each report's
  sensitivity table instead, so a downside never stacks a business shock on a
  higher risk premium.

## Inputs and sources

| Input | Value | Source |
| --- | --- | --- |
| India default spread (Baa3) | 1.87% | [Damodaran, country risk premiums, January 2026](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html) |
| India country risk premium | 2.85% | same |
| Mature-market equity risk premium | 4.23% | same (premium for Aaa-rated countries) |
| India total equity risk premium | 7.08% | same |
| Engineering/Construction unlevered beta, corrected for cash | 1.14 (48 firms) | [Damodaran, betas by sector (US), January 2026](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html) |
| Machinery unlevered beta, corrected for cash | 0.89 (105 firms; industry D/E 14.69%) | same |
| Steel unlevered beta, corrected for cash | 0.94 (19 firms) | same |
| Indian 10-year G-sec | 6.9754% on 2 Sep 2026 (Tega); 7.1194% on 25 Sep 2026 (Wabag) | Each model's dated research observation |
| US 10-year Treasury | 4.79% on 2 Sep 2026 | [YCharts, 10-year Treasury constant maturity](https://ycharts.com/indicators/10year_treasury_constant_maturity_rate) |

The industry betas are from Damodaran's US dataset, the one published as a
web page. Beta measures risk relative to the market, so an industry average is a
reasonable proxy, but an India- or emerging-market industry sample would be
better (see open items).

## Applied to each business

| Business | Industry | β unlevered | Capital structure used | β relevered | Ke | WACC |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| Wabag (linked model, FY27) | Engineering/Construction | 1.14 | Average forecast debt / market equity at ₹2,008.40 (debt 1.7%) | 1.155 | 13.43% | 13.31% |
| Wabag (generic DCF) | Engineering/Construction | 1.14 | Debt incl. leases ₹2,284m / market equity (debt 1.8%) | 1.156 | 13.43% | 13.30% |
| Tega legacy business | Machinery | 0.89 | Industry D/E 14.69% (debt 12.8%) | 0.989 | 12.11% | 11.19% |
| Molycop (USD) | Steel | 0.94 | At close: term loan 48.1%, preference 18.6%, equity 33.3% | 2.454 | 15.17% | 10.44% |
| Tega + Molycop group | | | EV-weighted: legacy 50.15% / Molycop 49.85% | | | 10.82% |

Notes on the capital structures:

- **Wabag** has almost no debt, so its observed market-value weights are used.
- **Tega's legacy business** uses the machinery industry's average debt-to-equity
  ratio. Tega's own March 2026 balance sheet held cash raised for the
  acquisition, which is not a normal operating structure. Relevering at Tega's
  own pre-deal gearing instead (D/E about 2.4%) raises its WACC by only about
  0.2 percentage point, because relevering and debt weight largely offset.
- **Molycop** is relevered at the structure the deal created. The resulting
  high equity beta (2.45) is what 67% debt and preference funding does to the
  equity holders' risk. Its WACC (10.44%) stays close to its asset risk.

Debt costs:

- **Tega:** 6.56%, its FY2025–FY2026 borrowing interest paid of ₹355.56m over
  average borrowings of ₹5,423.08m, from the audited statements.
- **Wabag:** each forecast year's interest over average debt.
- **Molycop:** 9% pre-tax and 12% on the preference shares. These, together
  with its 27% tax rate, are still unsourced estimates, because the contractual
  rates are not disclosed.

The group blend weights each business by an operating enterprise value:

- **Molycop:** the USD1,455m deal-value weight.
- **Legacy Tega:** the market's own valuation before the deal. The close of
  ₹2,094.10 on 9 September 2025, the day before the announcement, times
  66,535,492 shares, plus 31 March 2025 net debt including leases, gives
  ₹139,019m.

## Why not the stocks' own regression betas

| Stock | Weekly regression beta vs NIFTY 50 | R² | Approx. standard error |
| --- | ---: | ---: | ---: |
| Tega (Sep 2024 – Sep 2026, 104 weeks) | 0.67 | 0.05 | 0.29 |
| Wabag (Apr 2024 – Sep 2026, 125 weeks) | 1.43 | 0.15 | 0.31 |

A 95% confidence interval of roughly ±0.6 around each estimate makes them
unusable on their own. The previous model versions used them directly, which is
how two Indian industrial businesses came to be discounted at 9.9% (Tega's
legacy business) and 14.0% (Wabag).

## What changed

| | Before | After |
| --- | --- | --- |
| Tega cost of equity | 11.0%: G-sec 6.98% + 0.67 regression beta × 5.97% historical Nifty premium, no country risk | 12.1%: method above |
| Molycop WACC inputs | Risk-free 4.5%, ERP 5%, beta 1.10, all unsourced | Treasury 4.79%, ERP 4.23%, Steel beta relevered at the deal structure |
| Tega legacy EV weight | ₹80,000m, unsourced | ₹139,019m, pre-announcement market value |
| Tega scenarios | Premium stress +2 / 0 / −0.5 points, terminal growth 3 / 4 / 4.5%, terminal ROIC 13 / 16 / 18% (downside / base / upside) | One rate; 4% growth and 16% ROIC in every case |
| Wabag linked model | Regression beta 1.43; ke = rf + β × 4.23% + 2.85% | Engineering/Construction beta; ke = rf + β × 7.08% |
| Wabag generic DCF | Risk-free 6.5%, ERP 6%; beta 1.2 / 1.0 / 0.9 and ROIC 12 / 15 / 18% (downside / base / upside) | Same inputs as the linked model; 15% ROIC in every case |

| INR per share (downside / base / upside) | Before | After |
| --- | --- | --- |
| Tega + Molycop | 294.22 / 1,171.99 / 1,734.08 | 258.47 / 589.01 / 732.64 |
| Wabag linked model | 424.27 / 579.30 / 716.59 | 461.30 / 630.42 / 780.79 |
| Wabag generic DCF | 497.90 / 808.15 / 1,037.41 | 527.67 / 712.60 / 809.49 |

## The market check

Each report solves for the single discount rate at which the base case equals
the share price, holding every forecast and claim fixed. It never changes the
forecasts.

| Model | Price | Model value (base) | Model WACC | Market-implied WACC |
| --- | --- | ---: | ---: | ---: |
| Tega + Molycop | ₹1,696.80 on 30 Jun 2026 (valuation date) | ₹589.01 | 10.82% | **8.54%** |
| Wabag linked model | ₹2,008.40 on 25 Sep 2026 | ₹630.42 at the 31 Mar anchor | 13.31% | **7.36%** |
| Wabag generic DCF | ₹2,008.40 on 25 Sep 2026 | ₹712.60 at the 31 Mar anchor | 13.30% | **7.37%** |

For Wabag, the anchor value is rolled forward to the price date at the same
rate. Prices come from the platform's Yahoo Finance snapshots.

**Reading it.** A Wabag WACC of 7.4% would be below the 12.3% expected return
on an average Indian stock under these inputs (5.25% + 1.0 × 7.08%). So the
gap cannot be a discount-rate problem; it sits in the cash flows. The market
expects far more cash than the forecasts contain.

- **Wabag: working capital.** Each extra rupee of revenue ties up about 48
  paise of working capital (61 paise in FY2027, as the ratio returns to its
  three-year average). With revenue growing 12–18% a year, that absorbs most
  of the profit. In
  FY2027 the increase in working capital (₹4,310m) is larger than after-tax
  operating profit (₹4,248m), and free cash flow is negative. Ninety per cent
  of enterprise value sits in the terminal value. The market is pricing in
  faster cash conversion or a longer period of high growth.
- **Tega: legacy forecast and leverage.** The legacy business alone is valued
  at ₹20,853m by its own forecast at its own WACC. The market valued it at
  about ₹139,000m before the deal was announced. Claims of ₹124,845m (net
  debt, preference shares, earnout, other claims and minority interest) sit
  ahead of shareholders against a group enterprise value of ₹169,053m. Each
  percentage point of group WACC therefore moves the value by about ₹280–380
  per share.

## Open items

- Molycop's debt cost, preference return and tax rate are unsourced estimates.
  No country risk premium is added for its operating countries, because its
  revenue by country is not in the sources.
- The industry betas are US samples. An emerging-market or India sample from the
  same dataset should be compared.
- The two models use G-sec observations from their own research dates (2 and
  25 September 2026).
- The forecasts were not changed in this revision. Wabag's working-capital
  ratio and five-year horizon, which steps from about 17% growth straight to the
  4% terminal rate, and Tega's legacy cash conversion are the next things to
  review.
