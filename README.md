# Equity Research & Quantitative Portfolio Analytics Platform

An end-to-end research platform for company valuation, portfolio analytics,
factor research, backtesting, and risk management.

The project is being built as production-style analytical software: financial
logic lives in reusable Python modules, inputs are explicit and testable, and
the eventual Streamlit application will consume the same analytics layer.

## Pro-forma consolidated Tega case study

The current Tega case consolidates 100% of legacy Tega and Molycop line by line,
then discounts consolidated FCFF at an EV-weighted blend of their standalone
WACCs. The bridge deducts full net debt, preferences, earnout/other claims and
explicit ordinary minority interest. The main diluted count includes both
preferential issues pro forma with matching follow-on cash once.

[Install and audit the consolidated update](docs/TEGA_PRO_FORMA_CONSOLIDATION.md).

Supporting business operating forecasts retain the approved revenue paths.
All output amounts are INR million; FX is adjustable under `pro_forma` in the
assumptions JSON, defaulting to INR94.97/USD. Provisional WACC inputs and fixed
unallocated opening acquisition balances remain explicitly labeled. Consolidated
arithmetic is not a substitute for missing Molycop disclosures or verified PPA.
The separate legacy June opening gap remains unresolved.

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
