# Tega Industries + Molycop acquisition model

A pro-forma consolidated DCF of Tega Industries after its acquisition of
Molycop, built on Tega's audited FY2026 statements.

- Reads the complete audited FY2026 consolidated income statement, balance
  sheet and cash-flow statement (with FY2025 comparatives) and validates 92
  historical reconciliations before forecasting.
- Forecasts FY2027–FY2034 for both businesses, consolidates them line by line
  and values the group with one blended WACC, one terminal value and an
  explicit preference / non-controlling-interest / dilution equity bridge.
- Money is INR million; values are INR per share. USD-origin amounts use the
  2 September 2026 closing rate of INR94.97 per USD.

Method: [pro-forma consolidation](../TEGA_PRO_FORMA_CONSOLIDATION.md) ·
[revenue and driver sources](../TEGA_REVENUE_DRIVERS.md) ·
[FY2026 statements and reconciliation](../TEGA_FY2026_STATEMENTS.md) ·
[FY2024–FY2025 sources](../TEGA_FY2025_STATEMENTS.md)

## Run

On Windows, double-click `scripts/Run_Tega_Model.bat`, then open
`outputs/tega_molycop/report.html`. From a terminal in the repository folder:

```bash
python scripts/run_tega_model.py
# or, after `pip install -e .`
python -m equity_analytics.case_studies.tega
```

The report covers downside, base and upside cases and links to the complete
FY2026 statements. Python 3.11+; no third-party runtime packages.

## Read the results without running anything

- [`examples/tega_molycop_reports/scenarios.md`](../../examples/tega_molycop_reports/scenarios.md):
  the three acquisition scenarios.
- [`examples/tega_molycop_reports/historical_statements.md`](../../examples/tega_molycop_reports/historical_statements.md):
  audited statements, notes, debt/asset/equity roll-forwards and checks.
- The same folder holds the HTML report and full JSON model output.

With the stored assumptions the model gives **INR382.46 (downside),
INR743.26 (base) and INR895.43 (upside) per share** on 75,606,133 diluted
shares, at a base group WACC of 10.55%. These reproduce the stored
assumptions; they are not current price targets.

Tega closed at INR1,696.80 on 30 June 2026, the valuation date. Holding the
forecasts fixed, that price implies a group WACC of 8.65%
([`market_check.json`](../../examples/tega_molycop_reports/market_check.json)).
An 8.7% rate is below both businesses' standalone WACCs (11.19% and 10.44%),
so the market is most likely expecting more cash than these forecasts contain.
Leverage magnifies any such difference: group claims of INR124,874m (net debt,
preference shares, earnout, other claims and minority interest) sit ahead of
shareholders against an enterprise value of INR180,744m, so each percentage
point of WACC moves the value by roughly INR310–420 per share.

**P/E cross-check.** At 28.2x, the Nifty India Manufacturing three-year median
P/E, FY2028 pro-forma EPS of INR40.26 gives INR1,133.84 per share. The share
price is 42.1x the same EPS and the DCF value 18.5x. The method, the terminal
growth choice (4%, because most of the value is in dollars) and the legacy
capex basis are in [the cost-of-capital note](../COST_OF_CAPITAL.md).

## Inputs

| File | Contents |
| --- | --- |
| `examples/tega_molycop_assumptions.json` | Forecast scenarios, with `group_terminal_growth_inr` and `group_terminal_roic` (equal in every scenario); FX, cost-of-capital inputs and consolidation proxies are under `pro_forma` |
| `examples/tega_fy2026_reported_statements.json` | Audited FY2026 actuals (FY2025 comparatives) |
| `examples/tega_fy2025_reported_statements.json` | Audited FY2025 actuals |
| `examples/tega_molycop_facts.json` | Deal and post-close disclosures, risk-premium and price sources, and the valuation-date market price |

Historical facts stay separate from estimates. `0.15` means 15%. Currency
metadata records the conversion date and source; changing it alone does not
reconvert monetary inputs. Settings from the retired separate-business method
are rejected so it cannot be run by accident.

The audited statements also feed the ratio module:

```bash
python -m equity_analytics.financials examples/tega_fy2026_reported_statements.json --output-dir outputs/history-tega-fy2026
```

## Limitations

- Valuation date 30 June 2026, research cutoff 11 September 2026. The case
  uses information after its valuation date, so it cannot supply historical
  backtests.
- Some June balances, preference economics, working capital and
  purchase-accounting allocations for Molycop are provisional; a complete
  statutory three-statement forecast of the combined group is not available.
- A legacy opening residual of INR-15.875 million is disclosed, not plugged.

Code: [`src/equity_analytics/case_studies/tega/`](../../src/equity_analytics/case_studies/tega/)
