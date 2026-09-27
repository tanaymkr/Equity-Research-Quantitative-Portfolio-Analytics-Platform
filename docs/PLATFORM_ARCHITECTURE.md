# Platform architecture

## Current components

`financials` owns normalized annual contracts, validation, ratios and reports.
`valuation` owns the generic FCFF DCF and sensitivity. `forecasting` owns the
linked statement engine. Its detailed schema requires consolidated INR
million reports and includes Tega-derived account mappings; broad company
coverage is not established.

`case_studies.tega` owns acquisition forecasts, drivers, financing, June opening
estimates, consolidation, capital claims and reports. It consumes forecasting
reconciliation/report utilities. Its `financial_history` adapter converts
Tega statements to the normalized annual schema and rejects other companies.

The financial-history loader retains a legacy dispatch to that adapter for
full statement files. New companies should use the normalized schema directly.
Future source adapters belong in the data layer with explicit company,
currency, units and basis. The generic DCF does not import the Tega package.

## Migration

- Move acquisition implementations to `equity_analytics.case_studies.tega`.
- Retain `equity_analytics.acquisition` as aliases to the same module objects,
  preserving imports, exceptions and patched-function behavior.
- Include compatibility files at the old module locations for copy-and-paste
  upgrades, so replacing files does not require deleting the old source files.
- Preserve `python -m equity_analytics.acquisition` and `run_tega_model.py`.
  The canonical command is `python -m equity_analytics.case_studies.tega`.
- Move the Tega statement adapter out of `forecasting/history.py`, retaining
  the former import as a compatibility re-export.
- Keep inputs, source registrations and report formats in their existing paths.

Historical method documents retain compatible old import references. New
implementation references should use the canonical case-study path.

## Planned flow

Providers/files feed SQL through validated loaders. As-of SQL queries feed
fundamentals, price signals and forecasts. Fundamentals and valuation feed
screening. Dated signals feed strategy and index construction. Portfolio and
risk functions consume holdings, prices, cash flows and trades. Streamlit
calls these functions and owns no financial calculations.

SQL is not implemented in this change. Publication dates and statement
versions must be stored separately from financial period ends. Prices must
declare adjustment basis, and historical universes require documented
membership before describing a backtest as free of survivorship bias.
