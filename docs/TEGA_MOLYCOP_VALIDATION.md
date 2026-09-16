# Acquisition model: validation and open inputs

FY26 integration base commit: `371e3cf53833328767b1854a75e3fcd2faf90ff2`.
Package date: 16 September 2026. Reviewed-source cutoff: 11 September 2026.
Valuation date: 30 June 2026. No remote repository writes were made.

The local suite passes **79 tests plus 14 subtests**, including the original
DCF, financial-history and linked-forecast tests 15 acquisition tests and 13 FY26 integration checks.
Ruff lint passes. Q1 segment/P&L tables were visually checked against official
PDFs. Report tables are generated from JSON and code, not manually entered.

New checks cover acquisition timing, excluding other income, ownership after
senior claims, duplicate deductions, the cash/debt funding bridge, shares and
pending cash dilution, preference PIK, book-versus-tax amortization, asset/debt
roll-forwards, terminal reinvestment, sensitivity directions and invalid inputs.

The complete FY26 statements now pass 92 historical reconciliations and are
the shared input to the acquisition DCF, the FY26 legacy-only linked model
and the ratio module. The legacy control balances for FY2027-FY2031. Its scope
excludes the acquisition; the default launcher retains Molycop. See
[the FY26 source walkthrough](TEGA_FY2026_STATEMENTS.md).

## Inputs still requiring evidence

| Gap | Treatment | Needed evidence |
| --- | --- | --- |
| June legacy cash/CFO/capex | Estimated roll-forward | Post-close balances and Q1 cash movements |
| Molycop full FY2026 income statement | Management EBITDA/volume; inferred revenue | Audited revenue, other income, D&A and adjustments |
| Molycop NWC | Ratios and sensitivity | Detailed operating balances |
| Preference economics | Issue-value proxy; assumed PIK/cash schedule | Return, premiums, exit/redemption and support terms |
| Earnout | USD0/60/120m scenarios | Exact tests, expected payment and fair value |
| PPA | Provisional intangible base; assumed life/taxes | Final allocation, useful lives and tax bases |
| Other claims and attribution | USD50m reserve with sensitivity | Net-debt scope, leases, pensions, JVs and lower-level NCI |
| Funding | Cash-need and maturity flags | Coupons, amortization, restrictions, covenants and refinancing |
| Cost of capital | Analyst scenarios | Dated rates, beta, risk premia, debt spreads and capital structure |
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

The original dated linked model remains available with `--historical-fy2025`.
