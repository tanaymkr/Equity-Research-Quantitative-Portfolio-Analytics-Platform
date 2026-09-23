# Acquisition model: validation and open inputs

**23 September 2026:** Legacy Tega statement gaps now use linked schedules, historical
fallbacks and explicit zero movements. Molycop remains partial. The estimated June
opening balance discrepancy remains visible; no balancing plug is used.
See [the legacy statement update and validation](TEGA_LEGACY_STATEMENTS_UPDATE.md).


Revenue/driver update base commit: `ffb79b196d61d56f4f658b83652c7311ff59b8ff`.
Package and assumption review: 20 September 2026. Financial-filing cutoff: 11 September 2026.
Valuation date: 30 June 2026. No remote repository writes were made.

The local suite passes **111 tests plus 13 subtests**. Ruff lint passes. The suite
covers the reusable DCF/linked engines, financial history, acquisition schedules,
INR conversion and the single group DCF. New group checks include exactly one
DCF call per scenario, independent terminal/PV arithmetic, ownership boundaries
of zero and 100%, negative cash-flow inclusion, matching cash-flow/claim ownership,
separate tax treatment and rejection of retired business discount settings.

Acquisition checks also cover timing, excluding other income, duplicate
deductions, opening cash/debt, pending dilution, preference PIK, book-versus-tax
amortization, asset/debt roll-forwards and invalid inputs. Report tables are
generated from code and JSON. Offline HTML structure and local links are checked;
no browser rendering verification is claimed for this update.

The complete FY26 statements now pass 92 historical reconciliations and are
the shared input to the combined acquisition DCF and the ratio module. The
older standalone forecasts have been removed. The reusable linked engine is
retained for development, with explicit custom inputs required. See
[the FY26 source walkthrough](TEGA_FY2026_STATEMENTS.md).

## Inputs still requiring evidence

| Gap | Treatment | Needed evidence |
| --- | --- | --- |
| June legacy cash/CFO/capex | Estimated roll-forward | Post-close balances and Q1 cash movements |
| Molycop full FY2026 income statement | Management EBITDA/volume; inferred revenue | Audited revenue, other income, D&A and adjustments |
| Molycop NWC | Ratios and sensitivity | Detailed operating balances |
| Preference economics | Issue-value proxy; assumed PIK/cash schedule | Return, premiums, exit/redemption and support terms |
| Earnout | INR0/5,698.20/11,396.40m scenarios | Exact tests, expected payment and fair value |
| PPA | Provisional intangible base; assumed life/taxes | Final allocation, useful lives and tax bases |
| Other claims and attribution | INR4,748.50m reserve with sensitivity | Net-debt scope, leases, pensions, JVs and lower-level NCI |
| Funding | Cash-need and maturity flags | Coupons, amortization, restrictions, covenants and refinancing |
| Cost of capital | Provisional group scenarios carried over from legacy | Dated rates, beta, risk premia, debt spreads and capital structure |
| Additional Apollo issue | Separate cash-plus-shares case | Completion, expenses and use of proceeds |

The code does not label these estimates as facts or manufacture a statutory
combined balance sheet using a plug. Passing tests establishes calculation
consistency, not forecast accuracy or a validated current price target.

## Reproduce

The runtime requires only standard Python 3.11+:

```text
python run_tega_model.py
```

Developer validation uses the project's existing CI commands:

```text
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

Reproduce the committed report and unverified user comparison:

```text
python run_tega_model.py --reference-price 1700 --output examples/tega_molycop_reports
```

The retired standalone forecast paths remain removed. Revenue, margins, working
capital, capex and financing inputs have changed in this release; the single group
valuation method is retained. New tests exercise revenue transmission through
expenses, working capital, capex and depreciation; guidance/actual interest timing;
historical-source conflicts; cash reconciliation; nondepreciating land; null
statutory totals and source-override labeling.

The audited FY26 input and all four historical report files remain byte-for-byte
unchanged. All 92 historical checks pass. The release overlay reproduces all 16
committed acquisition report files, including the new driver/source reports.
Thirty sensitivity rows remain. A negative raw equity residual is a valuation
result, not an immediate financing cash shortfall.

The legacy asset roll-forward now keeps INR754.45m land outside depreciation.
The Molycop interest schedule uses full ten-month assumed interest less actual
June expense. Neither correction changes the audited financial statements.
See [the driver review and remaining statement gaps](TEGA_REVENUE_DRIVERS_UPDATE.md).
