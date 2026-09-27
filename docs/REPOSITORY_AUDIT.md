# Repository audit and foundation changes

Audit date: 27 September 2026.

Repository: `tanaymkr/Equity-Research-Quantitative-Portfolio-Analytics-Platform`

Baseline commit: `cf9e1c4c7fe4e1b9c5f27d10c65c7dfd16089206`
(Pro-Forma Consolidated Financial Statements Update).

The audit inspected the current GitHub tree and a full local clone at that
commit. No AGENTS.md instructions were present. This report describes code
and reproducibility; it does not re-verify external financial disclosures.

## Findings against the agreed platform

| Component | Evidence at baseline | Assessment |
| --- | --- | --- |
| SQL/Data | `financials/models.py`, `financials/io.py`, JSON examples | Useful annual contracts with publication dates and source references. No SQL schema, price provider, company master or revision store. |
| Fundamental analysis | `financials/ratios.py` | Growth, margins, ROE/ROA/ROCE, liquidity, leverage, coverage and cash analysis work. ROIC, working-capital days and market multiples are missing. |
| Generic DCF | `valuation/dcf.py`, `valuation/sensitivity.py`, `cli.py` | Working FCFF DCF and sensitivity. WACC is supplied; bridge includes cash/debt only. Examples are synthetic. |
| Detailed forecasts | `forecasting/` | Linked financial statements, debt and assets exist. INR/consolidation/account-mapping restrictions mean general company support is not demonstrated. |
| Tega acquisition | Original `acquisition/` | Substantial forecasts, funding, WACC, consolidation and bridge. Provisional inputs and opening residual remain explicit. |
| Screening | No implementation found | Planned. |
| Factors | No implementation found | Planned. |
| Backtesting | No implementation found | Planned. |
| Portfolio analytics | No implementation found | Planned. |
| Risk analytics | No implementation found | Planned. |
| Index analytics | No implementation found | Planned. |
| Streamlit | No app or dependency found | Planned. |

## Highest-priority gaps

1. **Persistence and information dates:** build company/source/annual data
   storage first. An annual period end does not establish when information was
   available. Current history validation checks publication against as-of,
   but no database retains multiple statement revisions. The existing Tega
   valuation deliberately uses later research and cannot supply a historical
   factor backtest without a separate information-date policy.
2. **Company identity:** the old `forecasting/history.py` converter hardcoded
   TEGA.NS, INR and consolidated basis. This change isolates it as the Tega
   adapter and rejects other company names. Other companies can already use
   the normalized annual-history schema.
3. **DCF validation:** `HistoricalSnapshot` accepts `float('nan')` as revenue
   because its positivity comparison does not reject NaN. This was reproduced.
   Strengthen finite-number/type validation for all numeric inputs and strict
   JSON serialization before using external multi-company inputs. Deferred
   from this structural change to keep valuation changes independently reviewable.
4. **DCF scope:** add reported opening NWC, explicit claims, WACC calculation
   and scenario orchestration. Negative EBIT/NWC profiles are currently
   excluded by ratio validation; decide the supported company universe and
   tax treatment before relaxing those rules. Terminal FCFF currently grows
   the last forecast year, rather than separately normalizing terminal reinvestment.
5. **Breadth of evidence:** only Tega has the detailed reported-company case.
   Generic synthetic tests do not establish coverage of 20–30 real stocks.
6. **Research data for later phases:** obtain documented price adjustment,
   publication/revision history and historical membership before claiming
   unbiased factor/index backtesting.

## What this local change does

- Moves the acquisition implementation into `case_studies/tega/` inside the
  Python package, with a separate case-study guide at repository root.
- Keeps previous acquisition imports as aliases to the same implementation
  objects; preserves old and new module launch commands and the Windows launcher.
- Moves the Tega history adapter into that case-study package and adds a
  company-identity guard. Its former import remains a compatibility re-export.
- Rewrites the README to reflect demonstrated features and missing modules.
- Replaces the outdated roadmap with the agreed ten-component scope, SQL-first
  milestone and measurable completion gates.
- Adds migration and company-identity regressions.

Inputs stay at their existing paths. The company forecast arithmetic, supplied
WACCs, ownership, capital claims and scenario assumptions were not edited.

## Validation

Environment: Python 3.12, pytest 9.1.1 and Ruff 0.16.9. Declared package minimum
remains Python 3.11; this local audit did not run a separate 3.11 interpreter.

- Baseline: **139 tests passed, 13 subtests passed**; Ruff passed.
- After changes: **151 tests passed, 13 subtests passed**; Ruff passed.
- All **17 generated Tega output files** compare byte-for-byte with the baseline
  through the root launcher, historical package launcher and canonical launcher.
- Generic DCF JSON compares byte-for-byte with its baseline.
- FY26 financial-analysis command completes through the relocated adapter.
- Existing accounting tests retain **92 FY26 historical reconciliations**.
- `git diff --check` passes.

Reproduced scenario values: downside INR294.2243919134, base INR1171.9907072393,
upside INR1734.0796661639 per share. These are model regression controls using
stored inputs, not new market estimates.

The unresolved legacy opening residual remains INR-15.875 million. Passing
arithmetic tests do not establish that provisional Molycop disclosures are complete.

## Next implementation

Start `src/equity_analytics/data/` with SQLite migrations and loaders feeding
the existing normalized annual contracts. First deliver a repeatable ingestion
and as-of query, with duplicates, missing data, revisions and provenance tested.
Then extend fundamentals and generic valuation against the stored data.

This change is prepared locally on `refactor/platform-foundation`. No remote
branch, commit, pull request or push was created as part of this audit.
