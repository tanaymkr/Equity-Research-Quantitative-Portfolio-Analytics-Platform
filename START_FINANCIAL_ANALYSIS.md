# Financial analysis: reported Tega FY25/FY26

The ratio module now accepts the complete, reconciled FY26 statement file used
by the linked model and acquisition DCF. It derives ratio inputs automatically.
The same source supplies reported FY25 comparatives.

With Python 3.11+, open Command Prompt in the repository folder and run:

```text
python run_financial_analysis.py examples/tega_fy2026_reported_statements.json --output-dir outputs/history-tega-fy2026
```

Open `outputs/history-tega-fy2026/analysis.md` for the ratios and
`analysis.json` for the machine-readable result. Reported revenue, operating EBIT,
PAT, balance-sheet totals, borrowing/lease balances, operating cash flow and cash
capex come from the validated complete statements. EBIT excludes other income
and JV profit; FY26 operating expenses include acquisition transaction costs.

To read the complete income statement, balance sheet and cash flows without
Python, open `examples/tega_molycop_reports/historical_statements.html`.
See [the FY26 source walkthrough](docs/TEGA_FY2026_STATEMENTS.md).

The existing synthetic examples and FY24/FY25 examples remain available as
historical demonstrations. They are not the latest Tega inputs.

The module calculates annual growth, profitability, liquidity, leverage and
cash-flow metrics. Return ratios require average opening/closing balances, so
some first-year ratios are unavailable. CFO less capex is not automatically FCFF.
A report with FY25 and FY26 has one growth interval, not a five-year CAGR.
