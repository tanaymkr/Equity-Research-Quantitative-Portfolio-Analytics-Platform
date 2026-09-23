# Tega + Molycop: single group DCF in INR

**23 September 2026:** Legacy Tega statement gaps now use linked schedules, historical
fallbacks and explicit zero movements. Molycop remains partial. The estimated June
opening balance discrepancy remains visible; no balancing plug is used.
See [the legacy statement update and validation](TEGA_LEGACY_STATEMENTS_UPDATE.md).


Current revenue/financial-driver assumptions were updated on 20 September 2026.
See [the source review and linked statement coverage](TEGA_REVENUE_DRIVERS_UPDATE.md).
The single group DCF method below is retained; earlier operating-input descriptions
are superseded where the new driver review differs.

**Tega Industries Limited, NSE: TEGA.** All monetary model amounts below are
**INR million**. Value date: **30 June 2026**. Financial research cutoff:
**11 September 2026**. USD-origin amounts are converted at **INR94.97 per dollar**,
the **2 September 2026 market close** [reported by Reuters](https://www.reuters.com/world/india/rbis-bid-lift-indian-rupee-put-test-by-oil-us-yields-2026-09-02/).
The [currency-conversion guide](TEGA_INR_CONVERSION.md) explains the conversion
and the distinction between translated model inputs and reported INR accounts.

This is a provisional acquisition DCF. The complete FY26 statements provide
reported history, while missing post-close balances and future performance remain
explicit estimates. It is not a completed statutory consolidated three-statement
forecast or a validated current share-price target.

## Disclosures used by the model

| Item | INR million unless otherwise shown | Treatment |
| --- | ---: | --- |
| Closing | 1 June 2026 | Ten owned months in FY27; nine future months after June 30 |
| Tega ordinary contribution | 37,446.236322 | Cash funding outflow |
| Apollo ordinary contribution | 7,037.987091 | Contribution ratio gives Tega 84.1787% |
| Apollo preference issue | 25,641.90 | Separate claim before ordinary equity |
| Headline acquisition EV | 142,455.00 | Context; not a preset DCF result |
| Approximate closing purchase cash | 37,323.21 | Already funded; not deducted twice |
| Escrow included in that cash | 1,709.46 | Not a second cash deduction |
| Maximum earnout | 11,396.40 | Scenario amounts and timing are estimates |
| Parent acquisition loan | 15,000.00 | Reported INR borrowing |
| Molycop June net debt, translated | 63,867.325 | Deducted from enterprise value |
| Molycop FY26 EBITDA, translated | 18,139.27 | Management-reported adjusted EBITDA; normalization uncertain |
| Legacy FY27 capex guidance, translated | 3,798.80 | Includes Chile; Q1 spend fraction estimated |
| Molycop ten-month capex guidance, translated | 2,659.16 | Remaining nine-month share estimated |
| Eventual savings anchor, translated | 1,899.40 | Annual run-rate interpretation and timing are assumptions |

Sources: [closing filing](https://www.tegaindustries.com/assets/pdfs/int/2026/Q1/20260602_065818.pdf),
[Q1 statutory results](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260813_145142.pdf),
[Q1 presentation](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260813_151914.pdf),
[August earnings call](https://www.tegaindustries.com/assets/pdfs/int/2026/Q2/20260820_123940.pdf).
The facts JSON contains the complete source register, disclosure dates and locations.

August guidance supersedes June estimates where they differ. Management's 15%
long-term consumables growth, approximately 5% Molycop volume growth and 4%
comparable ten-month EBITDA growth anchor the base case. The complete annual
forecast paths, margins and working capital are modeling choices. The comparable
ten-month historical earnings are estimated using uniform months. First-year
EBITDA already includes first-year savings, so those savings are not added twice.

Full-year Molycop FY26 revenue remains inferred from FY26 volume multiplied by
FY25 realization, all in INR. It is not reported revenue. Base cross-selling and
unquantified asset-sale proceeds are zero. Upside cross-selling is an estimate.

## Acquisition claims and schedules

[S&P](https://www.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3581730) documents debt terms and adjusted claims.
[ICRA](https://www.icra.in/Rating/ShowRationalReportFilePdf/143093) discusses the perpetual preferences and
initial 7.5-year cash-dividend deferral. Deferral does not mean mandatory redemption.
The preference issue value is only a provisional current-value proxy. The assumed
12% PIK/later cash return is not a disclosed contractual coupon. Future PIK is a
financing diagnostic, not an additional deduction from FCFF.

The INR4,748.50m other-claims reserve remains a provisional proxy
for unresolved lease/pension/other claims and subsidiary minority/JV scope.
Its allocation and overlap with net debt require reconciliation. Apollo's ordinary
stake is excluded by applying Tega's ownership to both Molycop cash flows and
Molycop senior claims; it is not part of this reserve.

The opening bridge rolls March reported INR liquidity through the translated Tega
contribution, parent loan, estimated Q1 operating cash, capex, fees and principal.
New debt and cash are added together. A required liquidity top-up is flagged as
an estimate, not a confirmed facility. Historic fundraising cash used for the
acquisition is not added to equity again.

Asset schedules use straight-line cohorts, CWIP commissioning and half-period
charges on new assets. Remaining lives and commissioning fractions are estimates.
Molycop's existing asset balance is inferred from reported June D&A and assumed
PPA/intangible lives; it is not reported PPE. Goodwill is not amortized. PPA
amortization does not automatically create a tax deduction. The original reported
INR PPA amounts remain separately recorded with `reported_` prefixes.

Debt schedules estimate interest, repayments, cash retention, distributions and
funding needs. They do not establish contractual coupons or certify covenants.
The later annual principal assumption is now explicit in INR. Maturity review
flags remain FY2032 for the ABL and FY2034 for the term/parent loans. Full parent
support obligations and preference exit economics remain unresolved.

## Calculation path

1. Load the complete FY26 statements and validate all 92 historical checks.
2. Load native INR acquisition facts and assumptions with matching FX metadata.
3. Forecast legacy consumables/equipment and Molycop volume, realization and
   operating margins. Subtract already-reported Q1/June INR actuals before
   discounting future cash flows.
4. Calculate FCFF after cash taxes, investment, leases and working capital.
   Financing flows are excluded from FCFF.
5. Combine 100% legacy FCFF with Tega's 84.1787% share of Molycop FCFF.
   Preserve separate cash-tax calculations; do not offset losses across businesses.
6. Discount this one attributable stream at one group WACC. Use one group terminal
   growth rate and ROIC: terminal reinvestment is positive normalized group NOPAT
   multiplied by `g / ROIC`. No standalone business terminal values are calculated.
7. Deduct full legacy/parent net debt and the same 84.1787% share of Molycop net
   debt, preferences, earnout PV and other claims. Earnout PV uses the group WACC.
   Add nonoperating JV/property value, then divide by issued Tega shares.
8. Floor only total equity at zero. There is no separate Molycop equity floor or
   valuation of subsidiary default options. Contractual parent support and
   limited-liability protection remain unresolved; this pooled method may
   understate downside equity if Molycop shortfalls cannot reach the parent.

These are ownership-adjusted economic cash flows, not statutory consolidated
financial statements. Full subsidiary claims remain visible in reports and
financing schedules. See [the single-DCF guide](TEGA_SINGLE_DCF.md).

## Scenario choices

| Input | Downside | Base | Upside |
| --- | ---: | ---: | ---: |
| Initial consumables growth | 8% | 15% | 18% |
| Initial equipment growth | 0% | 15% | 25% |
| Initial Molycop EBITDA growth proxy | -8% | 4% | 8% |
| Eventual cost savings, INR m | 949.70 | 1,899.40 | 1,899.40, earlier |
| Earnout payment, INR m | 0 | 5,698.20 | 11,396.40 |
| Group WACC | 14% | 12% | 10.5% |
| Group terminal growth | 3% | 4% | 4.5% |
| Group terminal ROIC | 13% | 16% | 18% |

The group rates carry over former legacy assumptions as provisional starting
choices. They are not calibrated combined-business INR WACCs. The previous
Molycop discount/terminal settings are removed. This architecture change affects
valuation; it is not merely a change in units. No scenario probabilities are
assigned. The assumptions JSON contains every yearly array and its rationale.

The proposed Apollo share issue remains a separate cash-plus-shares sensitivity:
478,435 shares and INR953.99939m gross proceeds. Completion is not assumed from
the September 8 beneficial-ownership clarification. An optional user-entered
share-price comparison is unverified and never fits the model to that price.

## Files

| File | Purpose |
| --- | --- |
| `examples/tega_fy2026_reported_statements.json` | Canonical audited INR statements |
| `examples/tega_molycop_facts.json` | INR disclosures, sources, FX basis and unknowns |
| `examples/tega_molycop_assumptions.json` | INR monetary estimates and three cases |
| `src/equity_analytics/acquisition/engine.py` | Native INR forecasts, funding and DCF |
| `src/equity_analytics/acquisition/reporting.py` | INR reports and sensitivities |
| `run_tega_model.py` / `run_tega_scenarios.py` | Launch the same combined model |

Use `Run_Tega_Model.bat`, then open `outputs/tega_molycop/report.html`.
