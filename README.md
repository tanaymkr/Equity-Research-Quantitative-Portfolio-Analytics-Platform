# Equity Research & Quantitative Portfolio Analytics Platform

An end-to-end research platform for company valuation, portfolio analytics,
factor research, backtesting, and risk management.

The project is being built as production-style analytical software: financial
logic lives in reusable Python modules, inputs are explicit and testable, and
the eventual Streamlit application will consume the same analytics layer.

## Current milestone

Milestone 1 establishes a working discounted cash flow (DCF) engine with:

- five-year revenue and operating forecasts;
- FCFF calculated from NOPAT, depreciation, capital expenditure, and change in
  net working capital;
- enterprise-to-equity value bridge;
- implied value per share;
- WACC versus terminal-growth sensitivity analysis;
- input validation, a command-line interface, and automated tests.

All values in the included example are synthetic. They are for demonstrating
the model, not for making an investment decision.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
equity-dcf examples/demo_dcf.json
```

To save the full calculation as JSON:

```bash
equity-dcf examples/demo_dcf.json --json-output outputs/demo_dcf_result.json
```

Run the test suite:

```bash
python -m pytest
```

## Project structure

```text
equity-research-quant-platform/
├── docs/                  # Project roadmap and methodology notes
├── examples/              # Reproducible model inputs
├── src/equity_analytics/  # Reusable analytics package
│   └── valuation/         # DCF and valuation sensitivity logic
└── tests/                 # Automated financial-logic tests
```

## Roadmap

1. Equity research and DCF valuation
2. Portfolio performance analytics
3. Factor research and backtesting
4. VaR, Expected Shortfall, and stress testing
5. SQL data layer and automated pipelines
6. Streamlit dashboard
7. Testing, documentation, and deployment polish

The detailed delivery plan is in [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

## Important modelling convention

The engine is unit-agnostic, but all monetary inputs must use the same unit.
For example, if revenue, cash, and debt are in INR crore and shares outstanding
are in crore shares, the resulting value per share is in INR.

