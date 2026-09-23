# Equity Research & Quantitative Portfolio Analytics Platform

An end-to-end research platform for company valuation, portfolio analytics,
factor research, backtesting, and risk management.

The project is being built as production-style analytical software: financial
logic lives in reusable Python modules, inputs are explicit and testable, and
the eventual Streamlit application will consume the same analytics layer.

## One group DCF per scenario

The September 20 update applies the approved revenue paths and reviews other
drivers in this order: management guidance, verifiable comparable consensus,
then available historical trends. Each input records its basis. Detailed
Molycop statement inputs and a public group consensus WACC remain unresolved.
Legacy Tega statement gaps now use linked schedules, historical fallbacks and
explicit zero assumptions. Its estimated June opening-balance discrepancy is
shown rather than plugged. Molycop statements remain partial. Legacy-only
PAT/EPS includes investment income and is not consolidated Tega group PAT/EPS.

[Install the legacy statement update](docs/TEGA_LEGACY_STATEMENTS_UPDATE.md).

[Install the revenue and financial-driver update](docs/TEGA_REVENUE_DRIVERS_UPDATE.md)
and [review its assumptions](examples/tega_molycop_reports/forecast_assumptions.md).

Legacy Tega and Molycop retain operating schedules, but their cash flows are
combined before discounting. Each scenario has one group discount rate, one
terminal value and one enterprise-to-equity bridge. The cash flows and Molycop
claims use Tega's 84.1787% ordinary ownership consistently. This proportionate
economic valuation is not a statutory consolidated forecast.

[Install the single-DCF update and read its assumptions](docs/TEGA_SINGLE_DCF.md).
Group discount rates remain provisional; the change is more than a currency restatement.

## INR model update

The combined Tega-Molycop model now uses INR million throughout. USD-origin
amounts use INR94.97 per dollar, the market closing rate on 2 September 2026.
Reported INR statements retain their historical values. Read the
[currency basis](docs/TEGA_INR_CONVERSION.md).

## FY26 statements are now connected

The complete audited FY25/FY26 consolidated statements and supporting notes now
feed the acquisition DCF and financial-ratio module from one source file. The
historical validator runs 92 reconciliations. The combined Tega-Molycop DCF is
the single Tega valuation model; its forecasts start in FY27. The superseded
forecasts and separate legacy-only case have been removed.

- [Read the complete FY26 statements](examples/tega_molycop_reports/historical_statements.md)
- [Source details and model connections](docs/TEGA_FY2026_STATEMENTS.md)
- [Install and run the update](START_TEGA_MODEL.md)

## Tega + Molycop acquisition update

The Tega launcher now runs an acquisition DCF using final June 2026 deal terms,
FY2026 accounts and the first post-acquisition results. It includes separate
business forecasts, ownership, preference shares, earnout, parent funding,
dilution, asset schedules and three scenarios.

**This is a provisional research model.** Value date: **30 June 2026**.
Reviewed-source cutoff: **11 September 2026**. Missing cash-flow, working-capital
and preference-return disclosures remain explicit assumptions. Outputs are not
validated current price targets or a point-in-time backtest.

- [Start here: install, run and edit](START_TEGA_MODEL.md)
- [Facts, assumptions and code walkthrough](docs/TEGA_MOLYCOP_MODEL.md)
- [Precomputed scenarios](examples/tega_molycop_reports/scenarios.md)
- [Validation and open inputs](docs/TEGA_MOLYCOP_VALIDATION.md)

With Python 3.11+, double-click `Run_Tega_Model.bat`, or run:

```text
python run_tega_model.py
```

Open `outputs/tega_molycop/report.html`. No extra runtime packages are needed.
`run_tega_scenarios.py` is an alias for the same combined model.
For cleanup instructions, see [Remove old Tega forecasts](docs/TEGA_FORECAST_CLEANUP.md).

## Current milestone

Milestone 1 establishes a working discounted cash flow (DCF) engine with:

- five-year revenue and operating forecasts;
- FCFF calculated from NOPAT, depreciation, capital expenditure, and change in
  net working capital;
- enterprise-to-equity value bridge;
- implied value per share;
- WACC versus terminal-growth sensitivity analysis;
- input validation, a command-line interface, and automated tests.

The generic `demo_dcf.json` is synthetic. Tega's reported-history files contain
sourced company figures; forecast assumptions are separately identified.

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
