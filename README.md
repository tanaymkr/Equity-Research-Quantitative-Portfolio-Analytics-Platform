# Investment Research Platform

Python and SQLite research software for company financial analysis, valuation
and screening. Built by Tanay Malekar. The reported examples are **Tega
Industries** and **VA Tech Wabag**, each covering FY2024-FY2026. A separate
synthetic dataset supports learning and tests.

## What works today

| Component | Implemented | Remaining work |
| --- | --- | --- |
| SQL/data | Annual statements, company/source records, filing versions, raw-input audit trail and publication-date queries | Prices, corporate actions, provider adapters and historical membership |
| Fundamental analysis | Growth, margins, ROE/ROA/ROCE, leverage, liquidity, cash metrics and company comparison | ROIC, working-capital days and market multiples |
| Generic DCF | SQL inputs, company assumptions, FCFF scenarios, CAPM WACC, opening NWC, capital claims, terminal reinvestment and sensitivity | Market-input/claims refinement, valuation-date roll-forward and assumption versioning |
| Screening | Configurable bounds, sorting, dated statements, unit normalization, flagged zero substitution, HTML/CSV/JSON | Valuation filters and a broader sourced universe |
| Tega-Molycop case study | Reported history, acquisition forecasts, consolidation, group WACC, claims and scenarios | Resolve documented provisional deal/model inputs |
| Factors, backtesting, portfolio, risk and index analytics | Planned | Dated prices, methodology and implementation |
| Streamlit | Planned | Interface over tested analytical modules |

Two reported companies demonstrate the pipeline; an automated 20-30-company
universe is not implemented. The synthetic DEMO is excluded from screening.

## Run on Windows

Python 3.11+ is required. Runtime calculations use the standard library.
Run launchers from the repository folder:

| Task | Double-click | Open the resulting report |
| --- | --- | --- |
| Load SQL, analyse Tega and Wabag | `Run_Wabag_Analysis.bat` | `outputs/data/company_comparison.html` |
| Screen companies | `Run_Screener.bat` | `outputs/screener/screener.html` |
| Wabag DCF | `Run_Wabag_DCF.bat` | `outputs/valuation/wabag/valuation.html` |
| Detailed Tega-Molycop model | `Run_Tega_Model.bat` | `outputs/tega_molycop/report.html` |

Run the SQL loader first. Repeated imports record an audit entry but do not
duplicate financial facts. The database is `outputs/data/research.sqlite`.
`Run_Data_Pipeline.bat` remains available for loading data and exporting Tega's
individual analysis.

Edit screening rules in `examples/screener_config.json`. Missing/unavailable
numeric metrics count as **zero for filtering, sorting and CSV exports**, with
substitution flags and reasons. Source SQL nulls are preserved. Percentage
thresholds use decimals: `0.10` means 10%.

Edit Wabag valuation assumptions in `examples/wabag_dcf_assumptions.json`.
The DCF outputs remain preliminary: market inputs and some equity adjustments
are estimates. Tanay controls those assumptions. Tests establish calculation
and software behaviour; they do not validate an investment thesis.

## Python commands and development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"

python run_wabag_analysis.py
python run_screener.py
python run_sql_dcf.py
python run_tega_model.py

# Synthetic standalone examples
python -m equity_analytics.cli examples/demo_dcf.json --json-output outputs/demo_dcf.json
python -m equity_analytics.financials examples/demo_financial_history.json --output-dir outputs/demo_financials

python -m pytest
python -m ruff check .
```

Generated outputs, local databases and Python caches are ignored by Git.
The committed reports under `examples/` are reference snapshots, not live
results; regenerate `outputs/` after changing assumptions or data.

## Code map

| Location | Responsibility |
| --- | --- |
| `src/equity_analytics/data/` | SQLite schema, ingestion, publication-date queries and comparisons |
| `src/equity_analytics/financials/` | Annual contracts, validation, ratios and reports |
| `src/equity_analytics/screening/` | Filters, deterministic sorting, zero substitution and exports |
| `src/equity_analytics/valuation/` | Shared DCF, SQL adapter, CAPM WACC and sensitivity |
| `src/equity_analytics/forecasting/` | Detailed linked statements; broader company coverage requires validation |
| `src/equity_analytics/case_studies/tega/` | Tega-Molycop acquisition and consolidated model |
| `src/equity_analytics/acquisition/` | Compatibility imports for earlier Tega package paths |
| `examples/` | Sourced inputs, explicit assumptions, synthetic examples and reference reports |
| `tests/` | Accounting identities, valuation, ingestion, screening and compatibility checks |
| `docs/` | Methodology, dated validation records and roadmap |

## Model conventions and limits

Annual SQL queries use public source dates, not the date the database first
learned a fact. Annual reports can lag earlier results releases. This is not
complete point-in-time market data or a survivorship-free backtest universe.

The SQL DCF uses money and shares in millions. It supports explicit opening
NWC and a terminal ROIC reinvestment method. The older standalone demo retains
its original terminal-FCFF-growth method. Wabag's annual model is anchored at
31 March 2026 using later information; it is not a current-date price target.
See its guide for dilution, book-value claims and WACC limitations.

The detailed Tega model uses INR million, a 30 June 2026 valuation date and an
11 September 2026 research cutoff. Acquisition allocations and financing inputs
remain provisional. Its documented opening gap is INR15.875 million, without
a balancing plug. Reported Tega screening metrics predate the acquisition and
are not the pro-forma group forecasts.

## Guides

- [SQL pipeline](START_DATA_PIPELINE.md)
- [Wabag history and comparison](START_WABAG.md)
- [Screener](START_SCREENER.md)
- [SQL DCF](START_SQL_DCF.md)
- [Tega model](START_TEGA_MODEL.md)
- [Financial-analysis methods](docs/FINANCIAL_ANALYSIS_METHODS.md)
- [Architecture](docs/PLATFORM_ARCHITECTURE.md)
- [Delivery plan](docs/PROJECT_PLAN.md)

One-time ZIP manifests and the completed old-forecast cleanup utility have been
retired. Their prior versions remain in Git history. Model inputs, tested
compatibility imports and reference reports are retained.

## Historical price data

The price-data milestone adds SQLite history for Tega, Wabag and the NIFTY 50 price benchmark, source snapshots, corporate actions, coverage checks and aligned returns. Start with [START_PRICE_DATA.md](START_PRICE_DATA.md) and `Run_Price_Pipeline.bat`. The next research milestone is factor construction; a full backtest is not yet implemented.
