# Start here: the combined Tega + Molycop model

The Tega model reads the complete audited FY26 consolidated income statement,
balance sheet and cash-flow statement, validates 92 historical reconciliations,
and uses that common source for the acquisition DCF. FY25 comparatives are included.
Forecast assumptions cover FY2027-FY2034 and include Molycop.
All monetary model inputs and reports use INR million, with INR per share for
valuations. USD-origin amounts use the 2 September 2026 closing rate of INR94.97.
The current method is pro-forma consolidation with a blended WACC and explicit
preference/NCI/dilution bridge. Follow [the latest update guide](docs/TEGA_PRO_FORMA_CONSOLIDATION.md).
Edit FX, WACC, EV weights and consolidation proxies under `pro_forma` in the
assumptions JSON. Detailed Molycop accounts and a verified legacy EV weight are
still required; outputs are provisional. Supporting operating schedules and
historical financial statements remain available.

## Run without PowerShell

With Python 3.11+ installed, double-click **Run_Tega_Model.bat**. Then open
**outputs -> tega_molycop -> report.html**. No extra runtime packages are needed.
The main report includes downside, base and upside cases and a link to the
complete FY26 statements.

You can also run `run_tega_model.py` with VS Code's **Run Python File**, or use
Command Prompt in the repository folder:

```text
python run_tega_model.py
```

`run_tega_scenarios.py` launches this same combined model.

## Read the examples without running Python

Open these files in your browser:

- `examples/tega_molycop_reports/report.html`: combined acquisition scenarios.
- `examples/tega_molycop_reports/historical_statements.html`: audited statements,
  notes, debt/asset/equity rolls and reconciliation checks.

On GitHub, read [the FY26 statements](examples/tega_molycop_reports/historical_statements.md)
and [the acquisition scenarios](examples/tega_molycop_reports/scenarios.md).

## Change assumptions

- Forecast scenarios: `examples/tega_molycop_assumptions.json`.
- Audited actuals: `examples/tega_fy2026_reported_statements.json`.
- Acquisition facts: `examples/tega_molycop_facts.json`, which references the
  audited statement file and contains the deal and post-close disclosures.

Group valuation settings are `group_wacc_inr`, `group_terminal_growth_inr` and
`group_terminal_roic` in each scenario. The former separate-business settings
are rejected to prevent accidentally running the retired method.

Keep historical facts separate from estimates. Both businesses use INR million;
`0.15` means 15%. Currency metadata records the fixed conversion date and source;
changing metadata alone does not reconvert the monetary inputs.

The reported statements also feed financial ratios:

```text
python run_financial_analysis.py examples/tega_fy2026_reported_statements.json --output-dir outputs/history-tega-fy2026
```

The acquisition values remain provisional as of 30 June 2026. Some June balances,
preference economics and purchase-accounting inputs still require evidence.
A complete statutory forecast of the acquired group's three statements remains
incomplete. Read [the FY26 walkthrough](docs/TEGA_FY2026_STATEMENTS.md) and
[the acquisition methodology](docs/TEGA_MOLYCOP_MODEL.md).
