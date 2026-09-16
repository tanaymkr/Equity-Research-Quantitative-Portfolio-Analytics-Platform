# Tega + Molycop: facts, assumptions and code walkthrough

**Tega Industries Limited, NSE: TEGA.** Valuation date: 30 June 2026.
Reviewed-source cutoff: 11 September 2026. INR10 million = INR1 crore.
Later-published information is used; this is not a point-in-time backtest or a
September spot-price target.

## Final transaction

| Item | Disclosed fact | Treatment |
| --- | --- | --- |
| Completion | 1 June 2026 | FY2027 includes ten acquired months; nine are future at June 30 |
| Ordinary contributions | Tega USD394.295423m; Apollo USD74.107477m | Approximately 84.2% / 15.8%, replacing the initial 77% / 23% proposal |
| Apollo preferences | USD270m | Separate claim before ordinary equity |
| Headline EV | Approximately USD1.5bn | Context, not a preset DCF result |
| Closing cash purchase | Approximately USD393m, including USD18m escrow | Already funded; neither is deducted again from future FCFF |
| Earnout | Up to USD120m within 45 months | Separate discounted claim; scenario amounts and dates are assumptions |
| Parent acquisition loan | INR15,000m | Included in the cash/debt bridge |

Sources: [closing filing](https://www.tegaindustries.com/assets/pdfs/int/2026/Q1/20260602_065818.pdf)
and [June call](https://www.tegaindustries.com/assets/pdfs/int/2026/Q1/20260608_232901.pdf).
The contribution ratio used by the model is 84.1787%.

External ordinary and preference contributions total USD738.4029m. Subtracting
approximately USD393m purchase cash and the subsequently described USD235m debt
reduction leaves USD110.4029m **unallocated in this simplified comparison**.
That is not profit or freely available cash: the complete closing funds-flow,
fees, adjustments and retained cash are not established. This comparison is not
used to fabricate a closing balance sheet.

## Financing evidence

[S&P's final rationale](https://www.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3581730)
describes a USD700m seven-year term loan and a USD220m five-year asset-based
facility, with USD138m drawn at closing. Its adjustments include preferences,
contingent consideration and USD50m other claims. It links the earnout to Cobre
Panama/Grasberg restarts, shipments, volumes and EBITDA; exact thresholds were
not established.

[ICRA's pre-close report](https://www.icra.in/Rating/ShowRationalReportFilePdf/143093)
describes perpetual preferences without mandatory cash dividends in the first
7.5 years, and a May 2033 parent-loan maturity. Cash deferral is not mandatory
redemption. Full preference return, premium and exit terms need confirmation.

The model uses USD270m as a provisional preference fair-value proxy, sensitized
at USD330m and USD400m. **The 12% PIK/later cash return is an analyst assumption,
not a disclosed coupon.** There is no invented mandatory redemption date.
Future PIK is shown separately and never deducted from FCFF a second time.

The USD50m other-claims reserve is a conservative proxy, not a verified allocation.
Reconcile net-debt scope, leases, pensions, JVs and lower-level minority interests
before replacing it. Sensitivity includes zero and USD100m. Apollo ordinary
ownership is applied separately after senior claims.

## Updated results and guidance

| Item | Evidence | Use |
| --- | --- | --- |
| Tega FY2026 revenue | INR16,919.36m | Updated legacy base year |
| Issued shares | 75,127,698 | Includes November 2025 dilution |
| Q1 legacy revenue | INR4,318.02m | Actual quarter excluded from future cash flows |
| Molycop June revenue | INR12,916.40m | One acquired month, not an annual run rate |
| Molycop FY June 2026 EBITDA | USD191m, management reported | Annual earnings anchor, with normalization uncertainty |
| FY June 2026 volume | 1.204m tonnes | Volume forecast anchor |
| Molycop June net debt | USD672.5m / about INR63,660m | Updated claim |
| Cost savings guidance | About USD20m in 2–2.5 years | Gradual realization |
| Molycop FY2027 capex | About USD28m for ten months | Nine remaining months estimated at USD25.2m |
| Legacy FY2027 capex | About USD40m including Chile | Estimated 25% spent in Q1 |

Sources: [annual report](https://www.tegaindustries.com/assets/pdfs/int/2026/20260828_105759.pdf),
[Q1 results](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260813_145142.pdf),
[Q1 presentation](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260813_151914.pdf),
[August call](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260820_123940.pdf).

August guidance supersedes earlier June estimates where they differ. The initial
5% volume and 4% EBITDA growth proxies are anchored to management's comparable
ten-month guidance. The comparable ten-month historical accounts are unavailable;
the model explicitly estimates them from annual history using uniform months.
Base revenue synergies and asset-sale proceeds are zero because neither was
quantified. Upside cross-selling is an analyst assumption.

The cost-savings forecast interprets USD20m as an annual EBITDA saving once
achieved. The transcript does not provide a detailed annual savings bridge.
Sensitivity separately tests zero, half and all of the assumed savings after
FY2027, keeping the first year's guidance-based EBITDA unchanged.

Q1 operating EBITDA excludes other income: legacy `1,011.29 - 256.52 = 754.77`
and Molycop `1,628.12 - (-82.39) = 1,710.51`, both INR million. The statutory
segment reconciliation supports this distinction.

Full-year Molycop FY2026 revenue was not established. The model estimates
`1.204 × (1,539 / 1.223) ≈ USD1,515.09m` using volume at FY2025 realization.
**This is not reported revenue.** Treating USD191m annual adjusted EBITDA as an
operating anchor is also an assumption; a ±USD10m normalization sensitivity is
included.

## Acquisition accounting and balance-sheet limits

The Q1 acquisition note reports provisional accounting consideration USD442.7m,
intangibles USD362.3m and goodwill USD527.74m. These remain subject to adjustment
within the measurement period of up to one year from completion.

Accounting consideration and roughly USD393m cash paid are different measurements.
Their USD49.7m difference is not assumed to be the earnout's fair value without a
reconciliation. Neither goodwill nor purchase consideration is added to DCF EV.

| Checkpoint | Assets INR m | Liabilities INR m | Equity INR m |
| --- | ---: | ---: | ---: |
| March 2026 audited | 43,145.00 | 9,073.24 | 34,071.76 |
| June segment totals | 225,707.18 | 184,387.09 | 41,320.09 derived |

June equity above is an arithmetic difference, not a complete equity/NCI breakdown.
These totals do not provide detailed acquired cash, receivables, inventory,
payables and debt tranches. The new module is an economic DCF with asset/funding
schedules, **not a completed statutory combined three-statement forecast**. The
old linked three-statement engine remains intact. No balancing plug hides missing
post-close account detail.

## Code path

| File | Purpose |
| --- | --- |
| `examples/tega_molycop_facts.json` | Disclosures, source IDs and explicit unknowns |
| `examples/tega_molycop_assumptions.json` | Editable estimates and three forecast cases with rationale |
| `src/equity_analytics/acquisition/engine.py` | Funding bridge, operating forecasts, D&A, FCFF, DCF and claims |
| `src/equity_analytics/acquisition/reporting.py` | Tables, sensitivities, HTML and Markdown |
| `src/equity_analytics/acquisition/__main__.py` | Load, calculate and export |
| `run_tega_model.py` / `run_tega_scenarios.py` | Simple launchers; historical mode retained |
| `tests/test_acquisition.py` | Financial regression checks |

1. **Opening bridge:** roll March unrestricted liquidity forward with new debt,
   estimated Q1 cash flows and the disclosed Tega contribution. The new loan
   increases cash and debt equally. Used fundraising cash is not added again.
   Base net debt including leases is about INR18,569.86m, an estimate rather than
   reported June parent net debt. Already-incurred FY2026 fees are not paid again;
   acquired Q1 fees are reflected in acquired June net debt.
2. **Forecast:** legacy consumables/equipment have separate growth and operating
   margins. Molycop uses USD volume, realization and EBITDA per tonne. FY2027
   EBITDA already includes first-year savings; they are not added twice. Subtract
   actual April–June legacy results and acquired June results before discounting.
3. **Working capital:** use collection days and revenue fractions for legacy
   Tega; use explicit NWC/revenue estimates for Molycop. Ratios use annual revenue
   run rates, not just the nine-month cash-flow stub.
4. **Assets:** straight-line cohorts, separate CWIP and half-period charges on
   new commissioned assets. First legacy period commissions 80% of opening CWIP
   and 30% of new capex; later periods use 100% and 90%. These are modeling
   conventions, not a disclosed construction timetable. Molycop's modeled
   existing asset balance is inferred from June annualized D&A, a 15-year PPA
   intangible life and eight-year residual asset life; it is not reported PPE.
   Goodwill is not amortized. PPA book amortization is not automatically tax
   deductible.
5. **FCFF:** EBITDA minus cash integration costs, unlevered tax, cash capex,
   new lease assets and change in NWC. Financing flows are excluded. Leases are
   financing, with new assets included in investment and claims in the bridge.
6. **DCF:** each business uses its own currency's WACC and growth. Required
   terminal reinvestment is `NOPAT × g / ROIC`. Terminal earnings exclude finite
   acquisition amortization. End-period discounting uses actual days/365.
7. **Equity:** deduct Molycop net debt, preferences, PV of earnout and other claims
   from USD EV; then take Tega's ordinary stake and convert to INR. Add legacy EV,
   subtract parent/legacy net debt, and add legacy nonoperating-asset proxies.
   Divide by issued shares in millions. Equity shortfall is floored at zero,
   assuming limited liability and no additional support obligation; the full
   contractual downside exposure remains uncertain.
8. **Funding diagnostics:** show interest, principal, sweeps, new funding,
   distributions and preference accretion. The splits, 70% cash retention and
   12% preference return are assumptions. New funding is flagged, not declared
   available. Review ABL maturity in FY2032 and term/parent maturities in FY2034.
   Covenants and refinancing are not certified. Molycop new leases and lease
   principal are both assumed USD3m annually.

FX is a rounded reporting translation proxy, `63,660 / 672.5`, not a verified
spot quote. Closing funding FX is independently editable. WACCs are explicit
analyst choices, not a current CAPM calibration.

## Scenarios and dilution

| Input | Downside | Base | Upside |
| --- | ---: | ---: | ---: |
| Initial consumables growth | 8% | 15% | 18% |
| Initial equipment growth | 0% | 15% | 25% |
| Initial Molycop EBITDA growth proxy | -8% | 4% | 8% |
| Eventual cost savings USD m | 10 | 20 | 20, earlier |
| Earnout USD m | 0 | 60 | 120 |
| Legacy INR WACC | 14% | 12% | 10.5% |
| Molycop USD WACC | 12% | 10.5% | 9% |
| Legacy / Molycop terminal growth | 3% / 2% | 4% / 2.5% | 4.5% / 3% |

No probabilities are assigned. Capex, integration cost and working capital also
vary; JSON contains the complete assumptions. Lower downside earnout partly
offsets operating weakness and reflects uncertain mine restarts.

The [August 22 proposal](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260822_115252.pdf)
would issue 478,435 shares for INR953.99939m cash. It is not assumed completed.
A separate pro-forma sensitivity adds both cash and shares. It does not eliminate
Apollo's existing Molycop ordinary stake.

The optional INR1,700 comparison holds the forecast fixed and calculates what
Molycop EV would be required to explain that user-supplied price. It never fits
assumptions to the market price. Tests validate mechanics, not an investment thesis.
