# Delivery plan

Target pace: 2–3 focused hours per day for approximately five weeks, with a
sixth week available as buffer.

## Phase 1 — Equity research and valuation (days 1–7)

- Establish the package architecture and financial data contracts.
- Build and test the FCFF DCF engine.
- Add scenario and sensitivity analysis.
- Add historical-statement ingestion and ratio analysis.
- Produce the first company research workflow.

**Acceptance criteria:** A user can load a documented company input, reproduce
the DCF, inspect every forecast line, and export an audit-friendly result.

## Phase 2 — Portfolio analytics (days 8–11)

- Holdings and transaction models.
- Return, volatility, drawdown, Sharpe, Sortino, and benchmark attribution.
- Correlation and diversification diagnostics.

**Acceptance criteria:** A portfolio can be compared with a benchmark over a
chosen date range with transparent calculations.

## Phase 3 — Factor research and backtesting (days 12–18)

- Value, quality, momentum, size, and low-volatility signals.
- Cross-sectional ranking and portfolio construction.
- Rebalancing, costs, turnover, and look-ahead-bias controls.

**Acceptance criteria:** A factor strategy can be reproduced from raw inputs to
performance report without using future information.

## Phase 4 — Risk analytics (days 19–23)

- Historical, parametric, and Monte Carlo VaR.
- Expected Shortfall.
- Scenario and stress testing.
- Risk contribution and concentration diagnostics.

**Acceptance criteria:** Risk outputs are tested against known examples and
clearly state horizon, confidence level, and assumptions.

## Phase 5 — Data platform (days 24–27)

- SQL schema for companies, statements, prices, factors, and portfolios.
- Repeatable ingestion and validation pipeline.
- Caching, data-quality checks, and provenance metadata.

**Acceptance criteria:** The analytics layer reads consistent, validated data
through a documented repository interface.

## Phase 6 — Streamlit application (days 28–32)

- Research, valuation, portfolio, factor, and risk pages.
- Interactive controls, tables, charts, and exports.
- Graceful error and empty-state handling.

**Acceptance criteria:** A new user can complete the core research and portfolio
workflows without using the command line.

## Phase 7 — Quality and presentation (days 33–36)

- Expand automated tests and continuous integration.
- Add architecture, methodology, and data-dictionary documentation.
- Create screenshots, example outputs, and a concise GitHub walkthrough.
- Review reproducibility, performance, and investment disclaimers.

**Acceptance criteria:** The repository installs cleanly, tests pass, examples
run, and the documentation explains both the finance and the engineering.

