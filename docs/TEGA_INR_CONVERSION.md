# Tega-Molycop model in INR

All active monetary inputs, forecasts, DCF values, asset and financing schedules,
equity bridges, sensitivities and HTML/Markdown reports now use **INR million**.
Share prices use INR per share and selling-price proxies use INR per tonne.
One INR million equals INR0.1 crore. Shares, tonnes, dates and percentages are unchanged.

## Exchange rate and source

**INR94.97 per US dollar, Indian market close on 2 September 2026**, as
[reported by Reuters](https://www.reuters.com/world/india/rbis-bid-lift-indian-rupee-put-test-by-oil-us-yields-2026-09-02/). This is a market closing rate, not an FBIL
reference fixing or a bank's customer conversion rate. The previous model used
an inferred June reporting translation of about INR94.66 per dollar.

Each USD-origin monetary amount was multiplied by 94.97 once before calculation.
The native INR engine no longer multiplies Molycop distributions or equity by FX
again. The same rate is used for acquisition funding and legacy capex originally
guided in USD. Prior source-currency inputs remain traceable in GitHub commit
`5e8ca508c887cad04216d649d8445aed03859417` and the primary source register.

| Model input | Converted INR million |
| --- | ---: |
| Tega ordinary contribution | 37,446.236322 |
| Molycop June net debt | 63,867.325 |
| Apollo preference issue / current value proxy | 25,641.90 |
| Maximum earnout | 11,396.40 |
| Eventual synergy anchor | 1,899.40 |
| Legacy FY27 capex guidance | 3,798.80 |
| Molycop ten-month capex guidance | 2,659.16 |
| Molycop management-reported FY26 EBITDA, translated | 18,139.27 |

## Historical accounts and valuation date

Already-reported INR financial statements and Q1 INR operating amounts retain
their original values. Where disclosures include both INR and USD versions,
`reported_..._inr_m` fields preserve the historical INR accounting amount; the
converted model input is separately named. For example, reported provisional
intangibles remain INR34,295.32m, while the translated USD-origin model base is
INR34,407.63m. This does not restate audited accounts.

The valuation date remains **30 June 2026**, and the financial research cutoff
remains **11 September 2026**. September 2 is the requested conversion date. This
is a constant-currency restatement using later FX, not a new September 2 valuation
or a point-in-time June backtest.

Operating growth, margins, taxes, asset lives and ownership were unchanged by
the currency conversion. The earlier INR-only update also retained business
discount rates, so translating each cash flow and its discounted value at one
constant rate was algebraically equivalent. No future FX path was assumed.

The **current single-DCF update changes the valuation method separately**. It
replaces business discount rates with one provisional group WACC, terminal growth
rate and ROIC per scenario. It is not valuation-equivalent to the earlier two-DCF
method. Group rates require calibration for combined-business risk and INR cash
flows; converting USD inputs alone does not establish a suitable INR WACC.

## Apply the current update

Prepared against main commit `5e8ca508c887cad04216d649d8445aed03859417`.
Use **tega-single-dcf-update.zip**, which includes both the INR conversion and
the single group DCF. Follow [the installation steps](TEGA_SINGLE_DCF.md).
The older INR-only package and its manifest are historical records, superseded
by this combined update; do not apply the older package afterward.

All editable monetary assumptions now use INR million. The paired `currency_basis`
metadata in facts and assumptions documents the fixed rate and source. Changing
metadata alone is rejected because monetary inputs would also need reconversion.
The previous independent translation/closing-FX sensitivities were removed;
30 operating, group discount/terminal and INR-claim sensitivity cases remain.

## Verification

The earlier currency-only release passed 2,190 comparisons of forecast, funding,
DCF and equity values against the prior engine with both FX inputs set to 94.97.
That proof does not imply parity after changing to a single group valuation. All three cases were
checked; the audited FY26 input file is unchanged byte-for-byte. Historical
statements still pass 92 reconciliations. Currency tests check source conversion,
preserved INR actuals, no second FX multiplication, matching metadata and INR
sensitivity ranges. Passing these checks does not validate forecast assumptions.
