# Revenue and financial-driver update — 20 September 2026

This update applies the approved FY2027–FY2034 revenue paths. Management guidance
takes priority for other drivers, followed by verifiable comparable consensus,
then available historical ratios. Where none supplies a usable input, the report
identifies an unresolved estimate or a missing line. It does not invent consensus,
Molycop historical accounts, or a complete post-close balance sheet.

## Install with GitHub Desktop

1. Extract `tega-revenue-drivers-update.zip`.
2. In GitHub Desktop, select this repository and choose **Repository → Show in Explorer**.
3. Copy the contents of the ZIP's `equity-research-quant-platform` folder into that repository folder. Choose **Replace files**. Do not create a second nested project folder.
4. Double-click `Run_Tega_Model.bat`.
5. Open `outputs/tega_molycop/report.html`. Start with **Assumptions**, then the case you want. Each case includes income, balance-sheet and cash-flow schedules, with unresolved lines clearly labeled.
6. Review the changed files in GitHub Desktop. Suggested summary: **Apply approved revenue forecasts and source financial drivers**. Commit, then **Push origin** when ready.

No files need deletion. The ZIP overlays main commit `ffb79b196d61d56f4f658b83652c7311ff59b8ff`.
The remote repository is not changed by preparing this package.

## Approved annual revenue growth

These are underlying growth rates, not growth caused by adding the acquired
business to reported revenue. FY27 includes ten months of Molycop; only the nine
future July–March months enter the DCF.

| Business / case | FY27 | FY28 | FY29 | FY30 | FY31 | FY32 | FY33 | FY34 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Consumables downside | 8% | 8% | 8% | 7% | 6% | 5% | 5% | 5% |
| Consumables base | 15% | 15% | 14% | 12% | 10% | 9% | 8% | 7% |
| Consumables upside | 18% | 18% | 17% | 15% | 13% | 11% | 10% | 9% |
| Equipment downside | 8% | 8% | 7% | 6% | 6% | 5% | 4% | 4% |
| Equipment base | 14% | 14% | 12% | 10% | 10% | 8% | 8% | 7% |
| Equipment upside | 18% | 18% | 16% | 14% | 12% | 12% | 12% | 10% |
| Molycop downside | -3% | 1% | 2% | 2% | 2% | 2% | 2% | 2% |
| Molycop base | 5% | 5% | 5% | 5% | 5% | 5% | 5% | 5% |
| Molycop upside | 7% | 8% | 7% | 6% | 5% | 4% | 4% | 3.5% |

Molycop base assumes flat realization; the 5% management volume guide is for
FY27's comparable ten months only. Extending 5% through FY34 is the approved
model path. Upside annual growth drops below base in later years as approved.
No additional unquantified cross-selling revenue is stacked on these rates.

## Main driver changes

| Driver | Applied treatment | Basis |
|---|---|---|
| Consumables EBITDA margin | 20% downside; 21.5% base; 23% upside | Selections within management's 20–23% range; operating/adjusted definition remains a comparability risk |
| Equipment EBITDA margin | 12.1532% in each case | Mean of FY25 251.29/2,156.61 and FY26 340.09/2,687.53; Note 42 |
| Legacy operating cost split | Historical normalized cost shares allocate the margin-driven expense total | FY24–FY26; remove FY26 acquisition transaction expense from other expenses |
| Legacy receivables | 106.15 days of annual sales | Mean of FY24–FY26 year-end receivables/revenue × 365 |
| Legacy inventory / payables | 25.3063% / 15.1890% of sales | Mean FY24–FY26 closing ratios |
| Other operating current assets / liabilities | 4.1668% / 6.8701% of sales | FY24–FY26; exclude treasury, derivatives and tax balances |
| Legacy FY27 capex | INR3,798.80m | USD40m management estimate including Chile, converted once at 94.97 |
| Legacy FY28 onward capex | 7.3773% of revenue | Mean FY24–FY26 cash capex / sales |
| Molycop FY27 EBITDA | 4% growth in each case | Comparable-ten-month guidance; uniform-month earnings proxy because the comparable period is not disclosed |
| Molycop core profit / tonne | Flat after FY27; savings separately phased | Management's profit-per-tonne approach; no unsupported future margin expansion |
| Molycop capex | FY27 INR2,659.16m for ten months; FY28/29 INR3,323.95m downside, INR3,134.01m base, INR3,039.04m upside | Interpretations of management's USD28m and low/mid30s statements |
| Molycop later capex | FY29 amount grows with revenue from FY30 | Explicit extrapolation beyond the two-year guidance window; no verified historical capex series |
| Legacy FY27 finance cost | INR1,200m / 1,150m / 1,100m | Down/base/up selections within the INR1,100–1,200m management range; remove actual Q1 expense |
| Legacy tax proxy | 24.4558% | Mean FY24–FY26 accounting tax/PBT; not a statutory marginal tax rate or separately projected current/deferred tax |
| Group WACC | 14% / 12% / 10.5% | Existing provisional sensitivity assumptions; no verified public consensus |

Revenue drives expenses and working capital. Capex and lease additions feed asset
cohorts; those cohorts determine depreciation. Land is held outside depreciable
cohorts. Interest follows the debt schedule, tax follows earnings, and cash follows
operating, investing and financing movements. These lines do not all grow by the
revenue growth rate.

Legacy Q1 CFO is estimated from one quarter of historical annual CFO after
interest. It is not a reported Q1 cash-flow figure. March current maturities
anchor the FY27 repayment proxy; later repayments use the historical mean.

Molycop's ten-month interest/principal guide totals INR6,647.90m. The split remains
unverified. The model subtracts reported June interest from the ten-month interest
estimate instead of multiplying the total by nine-tenths. Preference accretion is
noncash and never subtracted twice from FCFF. Maturity review flags remain; the
model does not assert financing availability or compliance with covenants.

## Consensus and definition checks

The [public consensus summary](https://trendlyne.com/equity/consensus-estimates/743298/TEGA/tega-industries-ltd/)
showed four analysts and FY27 group revenue/profit growth of 824.4%/212.7% when
reviewed. It did not expose usable line-by-line statement forecasts, segment
estimates, underlying forecast definitions or a group consensus WACC. The headline
growth figures are comparison context; they do not override approved revenue or
determine expenses by backsolving profit. A single vendor's discount rate would
not establish analyst consensus. Access limits and URLs are recorded in the inputs.

Management's approximate 15% consolidated adjusted EBITDA margin is shown beside
the model's operating margin. Different treatment of other income and the inferred
Molycop revenue base limit comparability. No earnings plug forces agreement.

## What remains incomplete

The new `linked_statements_inr_m` output is a **partial forecast**, at 100% of each
business. It is not a statutory group consolidation. FY27 rows cover July–March;
the existing operating tables separately show full-year/owned-period revenue.

| Statement area | Why it is unresolved |
|---|---|
| Molycop materials, labour and other cost detail | No verified standalone cost breakdown; total operating costs remain visible |
| Post-close PPE/ROU/intangible splits and non-operating balances | The asset schedule uses disclosed data plus explicit allocation/life proxies; detailed opening accounts are missing |
| Molycop cash versus gross bank debt | Only the net-debt bridge is verified for model use; neither gross debt nor cash is invented |
| Statutory PBT, PAT and EPS | Other income, JV income, preference accounting, deferred tax and minority attribution require additional comparable inputs |
| Balance-sheet totals and retained earnings | Opening account breakdown and complete statutory profit/equity movements are unavailable; no equity plug |
| Complete statutory cash-flow statement | Tax timing, other noncash movements, treasury flows, distributions and FX reconciliation remain missing |

Historical legacy treasury income cannot simply be scaled with sales after cash
was spent on the acquisition. Likewise, legacy tax history cannot establish
Molycop's tax rate. Such scope mismatches stay explicit rather than being treated
as valid historical fallbacks. Molycop working capital, taxes, preference terms,
claims, integration costs and parts of asset/debt schedules remain provisional.

The **single ownership-adjusted INR group DCF** remains the only Tega valuation.
Audited FY26 statements and the fixed INR94.97/USD currency basis are preserved.
The valuation date remains 30 June 2026, with later information explicitly used;
these are conditional scenario values, not validated current price targets.

## Files to review

- `examples/tega_molycop_assumptions.json`: editable forecasts, evidence types and reviewed values.
- `examples/tega_molycop_facts.json`: source history, guidance and consensus-review details.
- `outputs/tega_molycop/forecast_assumptions.md`: driver table and historical calculations.
- `outputs/tega_molycop/forecast_evidence.json`: source status and values actually used.
- `outputs/tega_molycop/base/model.json` (also downside/upside): linked schedules and checks.

The report marks a driver as an override when its value differs from the reviewed
snapshot. Changing the underlying historical source requires refreshing the driver
review before the model will run. Tests check revenue transmission, guidance timing,
noncash items, cash/debt/asset reconciliations and honest missing-account handling.
