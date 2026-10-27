# Roadmap

The platform is built in three milestones, each with a completion gate.
Tests and documentation ship with every feature rather than at the end.

## Milestone 1: company research — complete

| Component | Delivered |
| --- | --- |
| SQL data | Company, source and annual-statement storage with units, currency, basis, publication dates and filing versions; duplicate and reconciliation checks; an audit record of every ingestion run |
| Fundamentals | Growth, margins, ROE/ROA/ROCE, liquidity, leverage, coverage and cash conversion |
| Generic DCF | FCFF scenarios from SQL with opening working capital, capital claims, ROIC-based terminal reinvestment and sensitivity |
| Cost of capital | One method for every model (industry unlevered cost of capital less the interest tax shield, India risk premiums), with the market-implied WACC reported beside each valuation |
| Screening | Configurable filters on growth, quality and leverage as of a publication date |
| Case studies | Tega + Molycop pro-forma consolidated DCF; Wabag linked three-statement model and DCF |

Gate (met): a fresh checkout loads the documented data into SQL, produces
analysis and valuation, and compares real companies through reproducible
commands, with inputs, calculations and failures inspectable.

## Milestone 2: systematic research — in progress

Done:

- **Price data** (29 September 2026): immutable price snapshots, corporate
  actions, benchmark-calendar returns and coverage reports.
- **Research universe** (10–23 October 2026): Nifty 100 membership as dated,
  immutable lists with a survivorship-bias guard; prices for all members since
  April 2021; calendar checks for holiday rows and benchmark gaps; an audit of
  vendor price errors.

Next, in order:

1. **Corporate-action corrections** for the price errors found in the audit
   (unadjusted Vedanta and Tata Motors demergers, a mis-dated Trent split).
2. **Momentum signal**: 3-, 6- and 12-month returns with explicit
   normalization, tested by information coefficient and decile portfolios
   against the Nifty 100, with transaction costs and an out-of-sample split.
3. **Fundamentals for the universe**: a bulk source of annual statements for
   the Nifty 100, loaded through the normalized schema; then ROIC,
   working-capital days and market multiples; then value, quality and growth
   signals.
4. **Portfolio analytics**: returns, volatility, Sharpe, Sortino, beta,
   tracking error, turnover and attribution.
5. **Risk analytics**: historical and parametric VaR, Expected Shortfall and
   stress tests with declared horizon and confidence level.
6. **Index construction**: selection, weighting, caps, rebalancing and
   tracking.

Gate: reproduce a defined strategy and index, compare it with a benchmark,
test return and cost accounting and risk estimates, and report limitations
without selecting favourable periods or results.

Known data limits to resolve or document before a backtest: historical index
membership before October 2026, symbol-rename aliases, and Yahoo's six
missing NIFTY 100 index days.

## Milestone 3: presentation

A Streamlit interface over the tested modules (it owns no calculations), a
data dictionary and method notes.
