# Tega Industries / Molycop case study

An acquisition research application within the platform, using sourced Tega
statements and explicit forecasts. Molycop allocations remain provisional
where disclosures are unavailable.

## Run from the repository root

```bash
python run_tega_model.py
# Equivalent canonical entry point
python -m equity_analytics.case_studies.tega
```

Open `outputs/tega_molycop/report.html`. The historical
`python -m equity_analytics.acquisition` command remains supported.

## Inputs and code

- [FY26 statements](../../examples/tega_fy2026_reported_statements.json)
- [FY25 statements](../../examples/tega_fy2025_reported_statements.json)
- [Deal source register](../../examples/tega_molycop_facts.json)
- [Assumptions](../../examples/tega_molycop_assumptions.json)
- [Implementation](../../src/equity_analytics/case_studies/tega/)
- [Methodology](../../docs/TEGA_PRO_FORMA_CONSOLIDATION.md)
- [Installation and editing guide](../../START_TEGA_MODEL.md)

Money is INR million; the current diluted count is 75,606,133 actual shares.
Audited baseline values are INR294.224392 downside, INR1,171.990707 base and
INR1,734.079666 upside per share. These reproduce stored assumptions and are
not refreshed current valuations.

Valuation date: 30 June 2026. Research cutoff: 11 September 2026. This use of
later information means the case cannot directly supply historical backtests.
The legacy opening residual of INR-15.875 million remains unresolved.
Provisional WACC, preferences, working capital and opening allocations are
documented in the assumptions and generated report.
