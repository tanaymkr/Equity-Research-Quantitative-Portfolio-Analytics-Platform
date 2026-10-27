# Pro-forma consolidated Tega model

Method as of 23 September 2026. It replaced an earlier proportionate
cash-flow valuation; the valuation date remains 30 June 2026.

Run it with `scripts/Run_Tega_Model.bat` or `python scripts/run_tega_model.py`
and open `outputs/tega_molycop/report.html` (see [the guide](guides/tega-model.md)).
Precomputed results are in `examples/tega_molycop_reports/`.

## Modules

| Module | Responsibility |
| --- | --- |
| `case_studies/tega/consolidation.py` | 100% line-by-line IS, BS, CF and FCFF; eliminate parent investment and internal dividends; annual FY27 income and future-period views |
| `case_studies/tega/wacc.py` | Standalone costs of capital using the platform method, including non-tax-deductible preference funding; operating-EV-weighted blend |
| `case_studies/tega/equity_bridge.py` | Full capital claims, common NCI, share roll-forward and matching issue cash |
| `case_studies/tega/currency.py` | Reconvert an explicit registry of USD-origin inputs using the adjustable FX rate |
| `case_studies/tega/engine.py` | Business operating/financing schedules, consolidation orchestration and valuation |
| `case_studies/tega/reporting.py` | Intermediate rates, EVs, consolidated statements, bridge deductions, assumptions and sensitivities |

Paths above are relative to `src/equity_analytics/`.
Business schedules remain as supporting worksheets. Group FCFF is now calculated
from consolidated EBIT, jurisdiction-specific cash taxes, D&A, capex and working
capital. It includes 100% of Molycop, not 84.18%. New lease assets remain a separate
reinvestment deduction under the existing lease-as-financing convention.

## WACC and currency convention

For each business, using the platform method in
[the cost-of-capital note](COST_OF_CAPITAL.md):

`Unlevered cost = (bond yield − sovereign default spread) + industry unlevered beta × equity risk premium`

`WACC = unlevered cost − debt weight × tax rate × pre-tax cost of debt`

Preference funding has no tax shield, so it does not change the WACC. Its claim
is deducted explicitly in the EV-to-common-equity bridge.

`Blended WACC = legacy weight × legacy WACC + Molycop weight × Molycop WACC`

The weights are each business's standalone DCF value from this model: its own
forecast cash flows at its own WACC. A market or deal value would weight the
blend by cash flows the model does not contain.

All inputs live under **`pro_forma` in `examples/tega_molycop_assumptions.json`**.
Every new parameter group has adjacent `_note` fields. Decimal rates are used.

| Editable input | Default / status |
| --- | --- |
| `fx_inr_per_usd` | 94.97, retained September 2 reference |
| `molycop_ev_weight_usd_m` | 1,455 deal EV (closing filing rounds to 1,500); sets Molycop's capital-structure weights at close, not the blend |
| Tega bond yield / default spread / ERP | 6.9754% G-sec (2 September 2026) / 1.87% / 7.08% India total premium (Damodaran, January 2026) |
| Tega beta | Machinery unlevered beta corrected for cash 0.89 (Damodaran, January 2026); unlevered cost 11.41% |
| Tega debt cost / debt weight | 6.56%, FY2025–FY2026 borrowing interest paid / average borrowings / 12.81%, the industry D/E |
| Tega tax | Existing 24.4558% historical effective proxy; not a marginal statutory tax rate |
| Molycop bond yield / ERP | 4.79% US 10-year Treasury (2 September 2026) / 4.23% mature-market premium |
| Molycop beta | Steel unlevered beta corrected for cash 0.94; CAPM unlevered cost 8.77% |
| Molycop deal premium | 0 (industry inputs). The deal-calibrated alternative, 3.44%, makes the base-case Molycop DCF equal the INR142,455m paid at the 1 June 2026 close; it is reported as a cross-check (`engine.calibrate_molycop_premium`) |
| Molycop debt weight | 48.11%: term loan INR66,479m against the USD1,455m deal EV |
| Molycop debt cost / tax | 9% / 27%; **unsourced estimates** (contractual rates not disclosed) |
| Equity-premium stress by scenario | 0 in every scenario; the stress is tested in the sensitivity table only |

Results: Tega legacy WACC 11.20% and Molycop 7.60% in every scenario. The base
blend is 7.91% (legacy 8.6% / Molycop 91.4% of standalone value); downside and
upside blends are 7.85% and 7.98% because the business mix differs. Terminal
growth (4%) and terminal ROIC (16%) are the same in every scenario. On these
inputs the model values Molycop at 1.89 times the price paid in June 2026;
calibrated to that price, the base value would be INR599.31 per share. The
report and sensitivity table show both.

`examples/tega_capm_reference_20260902.json` keeps the earlier CAPM research:
a weekly regression beta of 0.67 with R² 0.05 and a historical Nifty premium.
It is a cross-check only. No consensus WACC is claimed.

The report also solves for the **market-implied group WACC**: the single group
rate at which the base case equals Tega's INR1,696.80 close on 30 June 2026, the
valuation date, with forecasts, claims and the NCI valuation held fixed. It is
8.34%, against 7.91% from the method above. The same file holds a P/E
cross-check: 28.2x (Nifty India Manufacturing three-year median) times FY2028
pro-forma EPS of INR40.26 gives INR1,133.84. Neither result changes the
forecasts.

The model retains the user's **constant expected INR/USD** convention through the
forecast and terminal period. Under this explicit expectation, the USD discount
rate is numerically unchanged when USD cash flows are restated in INR. This is a
modeling assumption, not a hedge or an interest-rate-parity result. A nominal INR
model with expected currency depreciation would require an FX path **and**
corresponding rate/terminal adjustments; adding an INR–USD risk-free spread only
to WACC while retaining unchanged cash flows would be inconsistent.

A static EV-weighted WACC is an approximation. It does not exactly price changing
business mix, differing duration or subsidiary risk. Changing statement layout
alone never makes a single rate economically exact.

The input files preserve the original INR translation snapshot. Change
`pro_forma.fx_inr_per_usd`, not `currency_basis`. The explicit registry reconverts
USD-origin inputs and preserves reported INR actuals; each conversion is output
in `currency_conversion_audit`. Reported INR PPA/control totals retain historical
translation and are not restated audited accounts.

## Timing and consolidation

Acquisition close is June 1, 2026. FY27 includes twelve months of legacy Tega and
ten months of Molycop (June–March). The June 30 valuation excludes the elapsed
April–June legacy quarter and June Molycop month. Therefore only **nine future
months** enter FY27 DCF. March-end balance sheets are not multiplied by a stub fraction.

The report provides both full fiscal-year income (actual elapsed period plus
future forecast) and July–March forward income/cash flows. Actual Q1 total tax is
shown as a cash/current-tax proxy without an invented current/deferred split.
A full-year FY27 CF statement is not manufactured without reported Q1 CF details.

Internal investment at cost is eliminated. Molycop dividends to Tega are removed
from group income and cash flow; dividends to Apollo remain external financing
cash flows. Adjustable intercompany trading/receivable balances default to zero.
Equal sales/cost eliminations assume no unrealised intercompany profit; nonzero
profit eliminations require a sourced tax basis before being enabled.

**Balance-sheet limitation:** reported June group assets/liabilities anchor the
opening. Missing acquired balances are shown as fixed unallocated opening assets
and liabilities, then carried unchanged. They are residual allocations of known
control totals, not identified/sourced accounts. Forecast cash, equity and working
capital are not adjusted each year to force balancing. The independent legacy
opening discrepancy of **−INR15.875m (−₹1.5875 crore)** remains disclosed and unresolved.
A reconciled consolidated roll-forward is not proof that purchase accounting is correct.

Molycop gross working-capital allocations, cash presentation, lease allocation
and opening NCI book value are explicitly provisional. Its economic net-income
proxy assumes zero nonoperating income/deferred-tax movement and deducts modeled
preference return without a tax shield. This is **not reported Molycop PAT** or a
validated statutory group earnings forecast. Book NCI and fair-value bridge NCI
are distinct measures. Earnout book balance uses a face-value proxy; the bridge
uses present value. Lease liabilities are allocated out of the existing other
claims reserve, never deducted a second time.

## Equity bridge and dilution

1. Combined EV comes solely from consolidated FCFF and one group terminal value.
2. Deduct full legacy + full Molycop net debt, net of pro-forma follow-on proceeds.
3. Deduct 100% of Apollo's preference fair-value proxy (USD270m × selected FX).
4. Deduct existing earnout PV and other senior-claim reserve separately.
5. Deduct Apollo ordinary NCI = 15.8213105% × positive Molycop common equity value.
6. Add legacy nonoperating JV/property value proxies.
7. Floor total Tega common equity at zero and divide by pro-forma diluted shares.

The subsidiary common-equity value for NCI uses an **auxiliary standalone Molycop
EV at its standalone WACC**, less its full net debt, preferences, earnout PV and
other claims. A legacy standalone EV is also printed for audit. These values are
never summed to form combined EV. Shared terminal growth/ROIC remain provisional
assumptions for these intermediate calculations. NCI is floored at zero; no
negative minority deduction is used to increase parent equity.

June net debt already follows acquisition refinancing. Do not deduct the USD270m
preference-funded paydown again. The parent's opening bridge already includes
INR15,000m new debt and matching funding cash; do not add the loan again. Historical
purchase consideration/escrow are not new EV deductions.

`66,535,492 + 8,592,206 + 478,435 = 75,606,133 shares`

The November issue is already in FY26 reported shares/cash. Only the follow-on's
INR953.99939m (₹95.399939 crore) gross proceeds are newly included, with adjustable
expenses. Its completion is assumed **pro forma**; the reviewed August 22 filing
is a proposal subject to approvals. Issue cash is retained as a separate opening
cash/equity overlay; no interest income or debt sweep is assumed on that overlay.
Forecast ordinary dividends retain the existing schedule; per-share valuation
uses all pro-forma shares. This denominator is not statutory weighted-average EPS.

## Fact checks against filings

- Closing filing: approximately 84.2%/15.8%, with ordinary contributions of
  USD394,295,423 and USD74,107,477. Their ratio is 84.1786895%/15.8213105%; 84.12% plus
  15.82% totals only 99.94%. The model uses complementary ownership percentages.
- The closing filing calls the USD270m instrument **redeemable preference shares**.
  The separate debt-like senior claim is retained; no unsupported fixed redemption
  date is invented. Economic classification here does not determine legal/Ind AS classification.
- An initial USD1.455bn EV is retained as a first-pass weight, noting that the closing
  filing states approximately USD1.5bn.
- USD1.54bn revenue / USD172m EBITDA are older disclosed figures. Existing newer
  management FY26 EBITDA/volume and approved revenue forecasts remain in place.

Primary filings:

- [June 1 closing, ownership, preferences and EV](https://www.tegaindustries.com/assets/pdfs/int/2026/Q1/20260602_065818.pdf)
- [Proposed follow-on issue, August 22](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260822_115252.pdf)
- [November issue auditor certificate](https://www.tegaindustries.com/assets/pdfs/int/2025/Q3/Certificate-from-Statutory-Auditor-pursuant-to-Reg-169-5-of-SEBI-ICDR-Regulations.pdf)
- [Q1 group results / provisional purchase accounting](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260813_145142.pdf)

## Verification

Tests (`tests/test_pro_forma.py` and the other `test_acquisition*` files) cover independent WACC and
bridge arithmetic, full-ownership FCFF, minority loss floors, source FX conversion,
share dilution with cash, no duplicate paydown/loan deductions, investment/dividend
eliminations, frozen opening allocations, consolidated cash/BS roll-forwards and
stub timing. `tests/test_cost_of_capital.py` checks the shared cost-of-capital
arithmetic, that every scenario uses the same business rates, and that the market-implied
rate reproduces the valuation-date price. Original business operating forecasts
are regression-tested unchanged.
Passing tests establishes arithmetic consistency, not the validity of unsourced inputs.
