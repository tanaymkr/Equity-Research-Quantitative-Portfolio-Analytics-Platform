> **Historical update note.** Valuation method, FX controls and consolidated statement coverage below are superseded by [the pro-forma consolidated model](TEGA_PRO_FORMA_CONSOLIDATION.md). Retained for the audit trail.

# Legacy Tega financial statement update

Prepared 23 September 2026 against repository commit
`b1705968f0e0e69de44bcb0b1c56a30d3cb53d07` (Forecasts Update).

This update fills previously unresolved **legacy Tega** income-statement,
balance-sheet and cash-flow rows in downside, base and upside. Existing
operating, asset, working-capital, debt and tax assumptions have priority;
remaining rows use historical balances/ratios or an explicit zero forecast.
All amounts are INR million except per-share figures.

## Install with GitHub Desktop and File Explorer

1. Download and extract `tega-legacy-statements-update.zip`.
2. In GitHub Desktop, select the repository, then **Repository > Show in Explorer**.
3. Open the extracted `equity-research-quant-platform` folder. Copy **its contents**
   into the existing repository folder. Choose **Replace the files in the destination**.
   Do not put a second project folder inside the repository. No deletions are needed.
4. Double-click the existing `Run_Tega_Model.bat`.
5. Open `outputs/tega_molycop/report.html`. Select a scenario and find **Legacy
   income statement**, **Legacy balance sheet** and **Legacy cash flow statement**.
6. Review the changed files in GitHub Desktop, commit, then click **Push origin**.

Suggested commit summary:

```text
Complete legacy Tega forecast statements with historical and zero fallbacks
```

Precomputed reports are also included at `examples/tega_molycop_reports/report.html`.
No PowerShell, new Python packages or new run command is needed.

## What fills each gap

| Item | Applied treatment |
| --- | --- |
| Revenue, operating costs and working capital | Existing approved forecasts and historical cost mix; unchanged |
| D&A, PPE, ROU, intangibles and construction | Existing aggregate asset cohorts; detail allocated from reported opening balances and FY26 additions mix; aggregate capex and D&A unchanged |
| Finance cost and borrowings | Existing debt/interest assumptions; new non-operating cash flows and shareholder dividends feed through the same borrowing/cash-sweep calculation |
| Current versus noncurrent debt | Historical principal mix and scheduled next-year payments; required additional funding treated as a current facility proxy; existing parent maturity used for classification |
| Cash interest income | FY25 financial-instrument interest divided by average FY24/FY25 cash and bank balances, applied to opening forecast cash; avoids extrapolating FY26 acquisition-funding cash |
| Miscellaneous income | FY25/FY26 nominal average: INR25.275m annually |
| Equity-accounted JV profit | FY24-FY26 annual mean: INR49.9167m; adds to JV carrying value |
| JV cash dividend | FY24-FY26 annual mean: INR48.75m; reduces JV carrying value and enters investing cash flow |
| Current tax | Existing 24.455767% historical effective rate on positive taxable earnings; no tax refund invented on losses |
| Deferred tax | Zero forecast movements; existing deferred tax balances retained |
| Shareholder dividend | INR2/share, using 75.127698m issued shares; one annual payment in FY27 July-March, then the same per-share historical fallback |
| Retained earnings | Opening retained earnings plus forecast PAT less dividends |
| Share capital and other reserves | Reported balances carried; no new issuance or OCI movement assumed |
| Goodwill, other non-operating assets, provisions and tax balances | Latest reported nominal balances carried unless a linked schedule supplies a movement |
| Unsupported forecast gains, writebacks, FX, impairments and other treasury transactions | Zero movements, explicitly assumptions rather than reported zeros |
| Cash-flow totals and closing cash | Calculated from income, working capital, capex, debt, interest, dividends and investing receipts; reconcile to the financing schedule |

JV share of profit is already after JV tax. Incremental parent tax on JV and
subsidiary distributions is assumed zero where no supported forecast exists;
this is **not a verified tax exemption**. Current tax is also used as cash tax,
with no new tax-payment timing difference or deferred-tax movement.

Inventory, warranty and other provisions already reflected in net operating
balances and the historical cost mix are not added back again as separate
forecast cash benefits. Additional unmodeled noncash adjustments default to zero.

## Scope and the opening reconciliation

**The June opening balance sheet is not fully reconciled.** Combining the existing
June cash/debt estimates with independently rolled reported assets, liabilities
and equity leaves **assets minus liabilities minus equity = INR-15.875m**,
or **-INR1.5875 crore**. This discrepancy remains visible in each forecast.
It is not inserted into cash, retained earnings, another asset or a new liability.

The opening bridge uses estimated Q1 operating cash flow, capex and principal,
whereas opening retained earnings now use the reported Q1 legacy PAT of
INR401.18m and the JV balance includes reported Q1 JV profit of INR9.28m.
Unobserved Q1 OCI and other movements default to zero. The retained debt bridge
also omits the Q1 new lease liability corresponding to the existing asset
schedule's Q1 ROU addition. These opening inputs need reconciliation together;
this update deliberately preserves the earlier opening bridge and DCF.

Future-period **movements** reconcile: income to cash, cash to debt, retained
earnings, asset allocations and the change in the balance-sheet discrepancy.
A zero movement check does not mean the opening discrepancy has been resolved.

FY27 income and cash flows cover **July 2026-March 2027**, consistent with the
existing valuation. Balance-sheet columns are as at 31 March; FY28-FY34 flows
cover twelve months. The nine-month FY27 PAT/EPS is not a full-year forecast.

This is a legacy Tega statement view that carries the parent's Molycop investment
at its modeled contribution cost and recognizes the existing modeled subsidiary
distributions as dividend income. It is neither Tega's legal standalone accounts
nor the full acquired group's consolidated statements. Legacy PAT/EPS must not
be presented as group PAT/EPS. The investment and distributions are not added
to the single group DCF a second time.

## What this update preserves

- The approved consumables/equipment revenue paths and all previously resolved
  scenario/shared assumptions.
- Aggregate legacy operating forecasts, capex, D&A and FCFF.
- Molycop operating forecasts, statement gaps, debt, preference and earnout calculations.
- Audited FY24-FY26 statement files, issued shares, INR currency basis and the
  existing opening valuation bridge.
- The single group DCF and its provisional scenario values/WACC inputs.

The new non-operating receipts, their cash tax and shareholder dividends change
future parent cash requirements and debt balances. These are consequences of
filling missing cash-flow lines, rather than new borrowing-rate assumptions.

## Sources and audit trail

- [FY26 annual report](https://www.tegaindustries.com/assets/pdfs/int/2026/20260828_105759.pdf):
  consolidated statements; Note 31 other income, Note 41(b) proposed dividend.
- [Q1 FY27 presentation](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260813_151914.pdf):
  Tega column of the consolidated profit-and-loss presentation, including JV
  profit, PBT, tax and PAT.
- `examples/tega_molycop_facts.json`: additional reported legacy disclosures.
- `examples/tega_molycop_assumptions.json`: `legacy_statement_policy` describes
  every fallback category and the zero-movement policy.
- `outputs/tega_molycop/legacy_statement_assumptions.json`: calculated historical
  parameters, their scope, and the opening discrepancy.
- Each scenario's `model.json`: complete numeric legacy statement fields,
  asset/liability/equity detail, D&A allocation and movement checks.

The source-review cutoff and June valuation date are unchanged. This is a
forecast-completion update, not a refresh of market data or investment advice.

## Validation

121 tests and 13 subtests pass; Ruff checks pass. Regression hashes compare
the verified pre-update repository reports with the updated model and confirm
unchanged approved operating forecasts, Molycop statements, group DCF and
scenario/shared assumptions. Additional tests check all 24 legacy forecast
periods, retained earnings, cash/debt linkage, dividend timing, zero movements
versus retained balances, and the absence of invented tax refunds on losses.
