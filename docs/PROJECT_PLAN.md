# Investment Research Platform delivery plan

Agreed scope, 27 September 2026: SQL/Data, Fundamental analysis, Generic DCF,
Screening, Factors, Backtesting, Portfolio analytics, Risk analytics,
Index analytics and Streamlit.

The overall budget is 120–160 focused hours, subject to data access, quality
and research depth. At 2–3 hours per working day this is about 40–80 working
days; calendar duration depends on days worked per week. This is a planning
estimate, not an implementation status. Use completion gates below rather
than treating earlier week estimates as promises.

## Foundation: audit and boundaries

- Establish a passing baseline at a known Git revision.
- Isolate company-specific models and adapters.
- Preserve runnable examples and existing launchers.
- Distinguish implemented capabilities from planned ones in the README.

## Milestone 1: usable company research

1. SQL/Data: SQLite company, source, annual statement, price and assumption
   storage. Preserve units, currency, basis, publication dates and revisions.
   Validate duplicates and reconciliations; record each ingestion run.
2. Fundamentals: reuse current ratios; add documented ROIC, working-capital
   and market metrics when sufficient inputs exist.
3. DCF: strengthen finite-value validation, add reported opening NWC, capital
   claims, WACC calculation and scenario configurations. Document terminal policy.
4. Screening: compare growth, quality and leverage. Substitute unavailable
   numeric metrics with flagged zeros at the screening boundary (user-selected
   policy); preserve source SQL nulls. Valuation screening remains future work. Start with a small verified universe, expanding toward 20–30 stocks.

Gate: a fresh checkout loads documented data into SQL, produces analysis and
valuation, and compares multiple real companies through a reproducible command.
Inputs, calculations and failures are inspectable.

## Milestone 2: systematic research

- Factors: value, quality, momentum and growth with explicit normalization.
- Backtesting: publication dates, historical membership, corporate actions,
  rebalancing, transaction costs and benchmark. Document unavailable data.
- Portfolio: returns, volatility, Sharpe, Sortino, beta, tracking error,
  turnover and a specified attribution method.
- Risk: historical, parametric and Monte Carlo VaR, Expected Shortfall and
  stress tests with declared horizon and confidence level.
- Index: selection, weighting, caps, rebalancing, turnover and tracking.

Gate: reproduce a defined strategy and index, compare with a benchmark, test
return/cost accounting and risk estimates, and discuss limitations without
selecting only favorable periods or results.

## Milestone 3: presentation

Streamlit views, data dictionary, methods, screenshots and an interview
walkthrough. Tests and documentation accompany every earlier feature; this
milestone adds the final interface and presentation. Avoid empty placeholder
modules merely to match the roadmap.

## Current checkpoint and next build

As of 28 September 2026, annual SQL ingestion, fundamental analytics, the
SQL-backed Wabag DCF and the fundamental screener are implemented. Tega and
Wabag each have FY2024-FY2026 histories. DEMO is synthetic and excluded from
screening. The DCF engine works; Tanay owns the valuation assumptions and their
refinement. Its illustrative inputs do not establish investment-ready values.

Next implementation: a dated price-data layer with explicit adjustment,
corporate-action and benchmark conventions, followed by factor research.
Price provider choice and historical universe coverage must be documented.
Historical membership, assumption-version storage and provider automation
remain outstanding. No additional manually modelled company is required to
start that implementation.

## Price-data milestone

Implemented the separate market SQLite store, optional Yahoo downloader, Tega/Wabag/NIFTY 50 example configuration, immutable retrieval snapshots, corporate-action records, aligned price returns and coverage reports. See [START_PRICE_DATA.md](../START_PRICE_DATA.md). Next: factor definitions and validation, followed by explicit portfolio/backtest rules. Retrieval snapshots do not establish historical point-in-time availability.

## Wabag financial-statement milestone — 29 September 2026

Added FY27–31 linked consolidated IS/BS/CF, debt/lease and asset schedules, tax,
working capital, provisions, equity/dividends, dated market WACC inputs and
explicit FCFF discounting. Three years of reported statement detail reconcile
to SQL. Sources and missing-flow zeros are visible in the report. See
[the Wabag forecast guide](../START_WABAG_FORECAST.md). The next platform build
remains factor definitions and validation; a current-date Wabag valuation and
assumption refinement are separate research tasks.
