# Investment Research Platform

Python research software for company financial analysis and valuation, with a
planned SQL data layer, screening, factor research, backtesting, portfolio,
risk, index analytics and Streamlit interface. Built by Tanay Malekar.

The working examples are a generic FCFF DCF, annual financial analysis, and
a detailed Tega/Molycop acquisition case study.

## What works today

| Component | Implemented | Remaining work |
| --- | --- | --- |
| SQL/Data | SQLite company/source records, annual statement versions, raw-input audit trail, repeatable imports and publication-date queries | Price ingestion, richer company metadata, assumption storage and provider adapters |
| Fundamental analysis | Growth, margins, ROE/ROA/ROCE, leverage, liquidity and cash metrics | ROIC, working-capital days, market multiples and universe comparison |
| Generic DCF | FCFF forecasts, supplied WACC, terminal growth, cash/debt bridge and sensitivity | Calculated WACC, scenarios, richer claims, reported opening NWC and stronger validation |
| Tega case study | Reported history, acquisition forecasts, consolidation, WACC, claims and scenarios | Resolve documented data limitations |
| Screening | Planned | Universe filters and comparable output |
| Factors | Planned | Value, quality, momentum and growth |
| Backtesting | Planned | Dated data, rebalancing, costs and benchmark |
| Portfolio analytics | Planned | Performance, risk and attribution |
| Risk analytics | Planned | VaR, Expected Shortfall and stress tests |
| Index analytics | Planned | Selection, weights, caps and rebalancing |
| Streamlit | Planned | Views consuming the analytical functions |

There is no automated 20–30-company pipeline yet. Generic examples are
explicitly synthetic. Tega reported figures have source references and
forecasts contain separately labeled assumptions.

## Run the working examples

Requires Python 3.11+. Current calculations use the standard library.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"

# Store included financial histories in SQLite and generate analysis from SQL
python run_data_pipeline.py

# Synthetic generic DCF and sensitivity
python -m equity_analytics.cli examples/demo_dcf.json --json-output outputs/demo_dcf.json

# Synthetic annual financial analysis
python -m equity_analytics.financials examples/demo_financial_history.json --output-dir outputs/demo_financials

# Sourced Tega statements and annual ratios
python -m equity_analytics.financials examples/tega_fy2026_reported_statements.json --output-dir outputs/tega_financials

# Tega/Molycop scenarios and HTML report
python run_tega_model.py

python -m pytest
python -m ruff check .
```

The installed `equity-dcf` command also runs the generic valuation. Tega's
report is written to `outputs/tega_molycop/report.html`. Generated outputs
are ignored by Git.

For the data milestone, double-click `Run_Data_Pipeline.bat` on Windows or use
the Python command above. Open `outputs/data/tega/analysis.html`. The database
is `outputs/data/research.sqlite`. It contains one real company (TEGA) and one
explicitly synthetic example (DEMO), not a verified multi-stock universe.
Rerunning records a new ingestion audit entry without duplicating statements.
See [Data pipeline instructions](START_DATA_PIPELINE.md).

## Code map

| Location | Responsibility |
| --- | --- |
| `src/equity_analytics/data/` | Versioned SQLite schema, ingestion evidence, annual statement storage and dated queries |
| `src/equity_analytics/financials/` | Annual data contracts, validation, ratios and reports |
| `src/equity_analytics/valuation/` | Generic FCFF valuation and sensitivity |
| `src/equity_analytics/forecasting/` | Linked statements using the existing detailed INR schema; broad company coverage needs validation |
| `src/equity_analytics/case_studies/tega/` | Acquisition, financing, consolidation, WACC, equity bridge and Tega statement adapter |
| `src/equity_analytics/acquisition/` | Compatibility imports and launcher for the old Tega package path |
| `examples/` | Inputs and checked-in reference reports |
| `tests/` | Accounting, valuation, scenario and migration checks |
| `docs/` | Methodology, audit and delivery plan |

Tega inputs retain their `examples/` paths so source references and launchers
continue to resolve. New code uses the `case_studies.tega` namespace.

## Conventions and limitations

Generic DCF money and shares must use matching scales: INR crore divided by
crore shares yields INR per share. The engine discounts at year end, accepts
WACC as an input and grows final forecast FCFF into perpetuity. Opening NWC
is inferred from revenue and the forecast NWC percentage. These limitations
need addressing before broader research use.

The Tega case uses INR million and actual diluted shares. Its valuation date
is 30 June 2026; its research cutoff is 11 September 2026. It uses later
disclosures and is not a point-in-time backtest input. Molycop opening
allocations, preference terms and several financing inputs remain provisional.
The legacy opening gap is INR15.875 million (INR1.5875 crore), without a plug.

## Read next

- [Repository audit](docs/REPOSITORY_AUDIT.md)
- [SQL schema and information-date policy](docs/DATA_LAYER.md)
- [Architecture and migration](docs/PLATFORM_ARCHITECTURE.md)
- [Delivery plan](docs/PROJECT_PLAN.md)
- [Tega case-study guide](case_studies/tega/README.md)
- [Financial-analysis methods](docs/FINANCIAL_ANALYSIS_METHODS.md)

### Second reported company: VA Tech Wabag

Run `python run_wabag_analysis.py` or `Run_Wabag_Analysis.bat` for Wabag
FY2024–FY2026 financials, Tega analysis and a common-period comparison.
See [START_WABAG.md](START_WABAG.md) for source evidence, mappings and limitations.
Wabag DCF forecasts are not included yet.
