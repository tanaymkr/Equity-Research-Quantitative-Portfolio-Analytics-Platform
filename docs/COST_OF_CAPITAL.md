# Cost of capital, market check and P/E cross-check

Every DCF in the platform uses one cost-of-capital method, implemented once in
`src/equity_analytics/valuation/cost_of_capital.py`. Each report then asks
what discount rate the share price implies, and shows a broker-style P/E value
beside the DCF. The gap between model and market is measured rather than tuned
away.

## Method

```text
Risk-free rate            = 10-year government bond yield − sovereign default spread
Unlevered cost of capital = risk-free rate + industry unlevered beta × equity risk premium
                            (+ a deal-calibrated premium for Molycop only)
WACC                      = unlevered cost of capital − D/V × tax rate × pre-tax cost of debt
```

The last line is the constant-leverage (Harris–Pringle) WACC from Berk–DeMarzo
and McKinsey's *Valuation*:

- **Debt.** Borrowing changes value only through the interest tax shield, so
  the WACC can never exceed the return the operating assets require.
- **Preference shares.** They earn no tax shield, so they don't change the WACC.
  Their claim is deducted in the equity bridge instead.
- **Risk-free rate.** The Indian 10-year G-sec includes India's default risk.
  The default spread is removed so that country risk isn't counted twice when
  the country risk premium is added in the equity premium.
- **Equity risk premium.** India's total premium is the mature-market premium of
  4.23% plus a country risk premium of 2.85%, giving 7.08% (Damodaran, January
  2026). USD cash flows use the mature-market premium alone.
- **Beta.** Each business uses an industry unlevered (asset) beta. The stocks'
  own regression betas are reported only as cross-checks, because they are
  statistically too weak to value a company (see below).
- **Scenarios.** Downside, base and upside change operating drivers only. Every
  scenario uses the same business discount rates, terminal growth and terminal
  ROIC. Discount-rate and terminal assumptions are tested in each report's
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
| Molycop enterprise value paid | ₹142,455m (USD1.5bn) at the 1 June 2026 close | Tega's closing filing |

The industry betas come from Damodaran's US dataset, the one published as a
web page. Beta measures risk relative to the market, so an industry average is a
reasonable proxy, but an India- or emerging-market industry sample would be
better (see open items).

## Applied to each business

| Business | Industry | β unlevered | CAPM unlevered cost | Deal premium | Debt weight | Pre-tax debt cost | Tax shield | WACC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Wabag (linked model, FY27) | Engineering/Construction | 1.14 | 13.32% | – | 1.7% | 8.65% | 0.04% | 13.29% |
| Wabag (generic DCF) | Engineering/Construction | 1.14 | 13.32% | – | 1.8% | 7.80% | 0.03% | 13.29% |
| Tega legacy business | Machinery | 0.89 | 11.41% | – | 12.8% | 6.56% | 0.21% | 11.20% |
| Molycop (USD) | Steel | 0.94 | 8.77% | 3.44% | 48.1% | 9.00% | 1.17% | 11.03% |
| Tega + Molycop group (base) | | | | | | | | 11.06% |

Notes on the inputs:

- **Debt weights.**
  - Wabag uses its observed market-value weights; it has almost no debt.
  - Tega's legacy business uses the machinery industry's average D/E. Its own
    March 2026 balance sheet held cash raised for the acquisition.
  - Molycop uses its term loan at close against the deal value.
- **Debt costs.**
  - Tega: 6.56%, its FY2025–FY2026 borrowing interest paid of ₹355.56m over
    average borrowings of ₹5,423.08m, from the audited statements.
  - Wabag: each forecast year's interest over average debt.
  - Molycop: 9%, still an unsourced estimate (contractual rates are not
    disclosed). Molycop's 27% tax rate is also unsourced.
- **The group blend** weights each business by its standalone DCF value in this
  model (its own cash flows at its own WACC): ₹25,259m for legacy Tega and
  ₹142,455m for Molycop in the base case, or 15.1% and 84.9%. One blended rate
  then nearly reproduces the sum of the two valuations. Because the mix differs
  by scenario, the blend is 11.05% / 11.06% / 11.06% (downside / base / upside).

## Why Molycop carries a deal-calibrated premium

With industry inputs alone, Molycop's WACC would be 7.60%. That values Molycop
at ₹268,764m, almost twice the ₹142,455m that Tega and Apollo paid at arm's
length on 1 June 2026, four months before this valuation date. A recent
arm's-length price is the best market evidence of a private company's value. So
Molycop's unlevered cost carries a **3.44% premium**, set so that its base-case
DCF equals the price paid. That gives a WACC of 11.03%.

The premium stands for risk that a US steel beta and the mature-market premium
leave out:

- a B+ credit rating (S&P)
- private ownership
- an earnout tied to emerging-market mines (Cobre Panama and Grasberg)

It is calibrated once, on the base case, and every scenario uses the same rate.
If the price paid excluded the forecast cost savings, the true premium would be
lower. `engine.calibrate_molycop_premium` recomputes it, and a test fails if
the stored premium stops reproducing the deal value.

| Molycop premium | Molycop WACC | Tega down / base / up (₹ per share) |
| ---: | ---: | --- |
| 0 (industry inputs only) | 7.60% | 1,419 / 2,087 / 2,312 |
| 1.72% (half) | 9.32% | base 1,105 |
| **3.44% (deal-calibrated)** | **11.03%** | **270 / 599 / 743** |

## Why the beta isn't relevered

An earlier version of this method relevered each industry beta for the company's
debt, treating the debt as riskless, and then also charged the debt and
preference shares at their promised 9% and 12%. That counts the risk of the
borrowing twice. For Molycop, with 67% debt and preference funding, it produced
a 10.44% WACC, above its 8.77% unlevered cost, which is impossible. For Wabag
and Tega's legacy business, which carry little debt, the two methods differ by
less than 0.1 percentage point.

## Why not the stocks' own regression betas

| Stock | Weekly regression beta vs NIFTY 50 | R² | Approx. standard error |
| --- | ---: | ---: | ---: |
| Tega (Sep 2024 – Sep 2026, 104 weeks) | 0.67 | 0.05 | 0.29 |
| Wabag (Apr 2024 – Sep 2026, 125 weeks) | 1.43 | 0.15 | 0.31 |

A 95% confidence interval of roughly ±0.6 around each estimate makes them
unusable on their own. The original model versions used them directly, which is
how two Indian industrial businesses came to be discounted at 9.9% (Tega's
legacy business) and 14.0% (Wabag).

## Terminal growth

| Model | Terminal growth | Why |
| --- | ---: | --- |
| Wabag (both models) | 5% | Rupee cash flows: the RBI's 4% inflation target for 2026–2031 ([Outlook Money, 26 March 2026](https://www.outlookmoney.com/banking/rbi-to-maintain-4-per-cent-inflation-target-until-2031-centre)) plus about 1% real growth. It stays below the 5.25% default-free rupee rate, so the business never outgrows the risk-free rate. |
| Tega + Molycop | 4% | About 85% of the group's value is Molycop, whose cash flows are in dollars. 5% would exceed the 4.79% US risk-free rate, the usual ceiling for perpetual growth. |

## Tega legacy capex

From FY2028, legacy capex is 5.21% of revenue: the FY2022–FY2024 average
(4.31%, 7.60%, 3.71%), before the Chile and Dahej expansions. FY2025 and FY2026
(10.39% and 8.03%) included that expansion spending
([CRISIL, 3 July 2025](https://www.crisil.com/mnt/winshare/Ratings/RatingList/RatingDocs/TegaIndustriesLimited_July%2003_%202025_RR_373439.html)),
and FY2027 already carries the remaining Chile spend separately. CRISIL's
₹70–80 crore annual maintenance capex is 4.4–4.7% of FY2025–FY2026 revenue, so
5.21% leaves room for growth. The FY2022–FY2023 figures come from
[Stock Analysis](https://stockanalysis.com/quote/nse/TEGA/financials/cash-flow-statement/),
whose FY2024 values match the audited statements. The previous 7.38% averaged
FY2024–FY2026, so it repeated expansion capex forever and pushed depreciation
to 9% of revenue, against 4–6% historically.

## What changed

| | Before | After |
| --- | --- | --- |
| Discount-rate formula | Regression or assumed betas; CAPM equity cost weighted with debt and preference costs | Unlevered cost of capital less the interest tax shield |
| Tega legacy business | Regression beta 0.67 × 5.97% historical premium; WACC 9.9% | Machinery beta, India premiums; WACC 11.20% |
| Molycop | Risk-free 4.5%, ERP 5%, beta 1.10, all unsourced; WACC 8.8% | Treasury 4.79%, mature ERP 4.23%, Steel beta, premium calibrated to the deal price; WACC 11.03% |
| Tega blend weights | Legacy ₹80,000m (unsourced) / Molycop USD1,455m | Each business's standalone DCF value in this model |
| Tega scenarios | Premium stress +2 / 0 / −0.5 points, terminal growth 3 / 4 / 4.5%, terminal ROIC 13 / 16 / 18% (downside / base / upside) | Same business rates; 4% growth and 16% ROIC in every case |
| Tega legacy capex from FY2028 | 7.38% of revenue (FY2024–FY2026) | 5.21% (FY2022–FY2024, before the expansions) |
| Wabag linked model | Regression beta 1.43; ke = rf + β × 4.23% + 2.85%; terminal growth 4% | Engineering/Construction beta; method above; terminal growth 5% |
| Wabag generic DCF | Risk-free 6.5%, ERP 6%; beta 1.2 / 1.0 / 0.9 and ROIC 12 / 15 / 18% (downside / base / upside); terminal growth 4% | Same inputs as the linked model; 15% ROIC and 5% growth in every case |

| INR per share (downside / base / upside) | Before | After |
| --- | --- | --- |
| Tega + Molycop | 294.22 / 1,171.99 / 1,734.08 | 269.70 / 599.31 / 743.36 |
| Wabag linked model | 424.27 / 579.30 / 716.59 | 472.85 / 646.15 / 800.51 |
| Wabag generic DCF | 497.90 / 808.15 / 1,037.41 | 537.37 / 726.48 / 826.05 |

## The market check

Each report solves for the single discount rate at which the base case equals
the share price, holding every forecast and claim fixed. It never changes the
forecasts.

| Model | Price | Model value (base) | Model WACC | Market-implied WACC |
| --- | --- | ---: | ---: | ---: |
| Tega + Molycop | ₹1,696.80 on 30 Jun 2026 (valuation date) | ₹599.31 | 11.06% | **8.69%** |
| Wabag linked model | ₹2,008.40 on 25 Sep 2026 | ₹646.15 at the 31 Mar anchor | 13.29% | **8.00%** |
| Wabag generic DCF | ₹2,008.40 on 25 Sep 2026 | ₹726.48 at the 31 Mar anchor | 13.29% | **8.01%** |

For Wabag, the anchor value is rolled forward to the price date at the same
rate. Prices come from the platform's Yahoo Finance snapshots.

**Reading it.** A Wabag WACC of 8.0% would be below the 12.3% expected return on
an average Indian stock under these inputs (5.25% + 1.0 × 7.08%). So the gap
cannot be a discount-rate problem; it sits in the cash flows. The market
expects far more cash than the forecasts contain.

- **Wabag: working capital.** Each extra rupee of revenue ties up about 48
  paise of working capital (61 paise in FY2027, as the ratio returns to its
  three-year average). With revenue growing 12–18% a year, that absorbs most of
  the profit. In FY2027 the increase in working capital (₹4,310m) is larger than
  after-tax operating profit (₹4,248m), and free cash flow is negative.
  Ninety-one per cent of enterprise value sits in the terminal value. The
  market is pricing in faster cash conversion or a longer period of high growth.
- **Tega: legacy Tega and leverage.**
  - Molycop is valued at the price paid. The legacy business alone is valued at
    ₹25,259m, about 7.4 times FY2025 EBITDA, by its own forecast at its own
    WACC.
  - The market valued legacy Tega at about ₹139,000m before the deal. At
    ₹1,697–2,094 a share it still implies ₹108,000–138,000m for it, about 32–41
    times EBITDA.
  - Claims of ₹122,888m sit ahead of shareholders against a group enterprise
    value of ₹167,875m: net debt, preference shares, earnout, other claims and
    minority interest. Each percentage point of group WACC therefore moves the
    value by about ₹270–360 per share.

## P/E cross-check

Brokers usually set target prices as a P/E multiple times forecast earnings.
Each company report shows that value beside the DCF
(`src/equity_analytics/valuation/multiples.py`):

- **Multiple:** 28.2x, the
  [Nifty India Manufacturing](https://www.indexpe.in/nifty-india-manufacturing)
  three-year median P/E (observed 23 October 2026).
- **Earnings:** each model's own FY2028 EPS. FY2028 is the first full year with
  Molycop and the year brokers were valuing in 2026.

| Model | FY2028 EPS | Value at 28.2x | Share price / FY2028 EPS | DCF value / FY2028 EPS |
| --- | ---: | ---: | ---: | ---: |
| Tega + Molycop (pro forma, after interest, preference return and minorities) | ₹40.26 | ₹1,133.84 | 42.1x | 14.9x |
| Tega at consensus FY2028 EPS (MarketScreener, 9 Oct 2026) | ₹93.60 | ₹2,635.78 | 20.7x at ₹1,935 | n/a |
| Wabag linked model | ₹83.86 | ₹2,361.50 | 23.9x | 7.7x |

Three caveats apply:

- **The benchmark is generous.** It is a trailing-earnings multiple, so
  applying it to FY2028 forecasts flatters the result.
- **It is observed after the cutoff.** It was recorded after the models'
  information cutoffs, so it is a cross-check only and never enters the DCF.
- **It is a broad index.** It covers Indian manufacturers in general, not
  direct peers. Nifty Capital Goods was not used: its 44x is driven by defence
  and electrical stocks, and its P/E history only starts in June 2026.

**Tega: model versus consensus.** Tega's model EPS is less than half of
consensus, although its revenue and EBITDA are at or above consensus. The
difference arises below EBITDA: interest including the preference return, other
income and tax ([details](guides/tega-model.md)). This is why the share price
looks like 42x the model's FY2028 EPS but about 20x consensus EPS.

The four analysts' price targets (S&P Global via
[Stock Analysis](https://stockanalysis.com/quote/bom/543413/forecast/), 1
October 2026) average ₹1,799, with a range of ₹1,740–1,880 and a Hold rating.
They rest on those consensus earnings. The range is the spread of four single
targets, not bull and bear scenarios.

**Wabag.** Motilal Oswal's target multiples were 22x FY2028 EPS
([26 May 2026](https://www.businesstoday.in/amp/markets/stocks/story/va-tech-wabag-share-price-targets-hint-at-up-to-31-upside-in-12-months-533312-2026-05-26))
and 28x
([12 October 2026](https://www.businesstoday.in/markets/stocks/story/va-tech-wabag-jhunjhunwala-stock-reclaims-rs-2000-mark-as-mofsl-expects-30-upside-561011-2026-10-12)).

The generic SQL DCF has no earnings forecast, so it has no P/E cross-check.

**Why the two methods disagree.** With discount rates of 11–13% and terminal
returns on capital of 15–16%, the terminal value is only about 8–11 times
after-tax operating profit. Growth adds little value when returns are close to
the cost of capital. A P/E value inherits whatever growth and returns the
market currently prices in. The gap between the two is the market's optimism
relative to these forecasts, not an arithmetic error.

## Open items

- Molycop's debt cost and tax rate are unsourced estimates, and its premium
  rests on the deal price and the model's Molycop forecast.
- The industry betas are US samples. An emerging-market or India sample from the
  same dataset should be compared.
- The two models use G-sec observations from their own research dates (2 and
  25 September 2026).
- Wabag's working-capital ratio and five-year horizon, which steps from about
  17% growth straight to the terminal rate, are the next forecast items to
  review. For Tega, the financing assumptions behind its below-consensus
  earnings are next.
- The P/E benchmark is a broad index. A dated peer set with forward multiples at
  each valuation date would be a better comparison.
