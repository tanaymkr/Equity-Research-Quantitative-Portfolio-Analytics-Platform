# One Tega-Molycop DCF per scenario

The model now combines operating cash flows before valuation. Downside, base and
upside each have **one group discount rate, one terminal value and one equity
bridge**. There is no separate legacy Tega DCF, Molycop DCF or sum of independently
valued businesses. The business operating schedules remain because growth,
working capital, tax and asset assumptions differ.

## Cash flows, ownership and claims

Tega's ordinary ownership is estimated from contributions:
`394.295423 / (394.295423 + 74.107477) = 84.1786895%`.

For every forecast year:

```text
Attributable group FCFF = legacy FCFF + 84.1786895% × Molycop FCFF
Group enterprise value = PV of group FCFF + PV of one group terminal value
Raw Tega equity = group enterprise value
                 − full legacy/parent net debt
                 − 84.1786895% × (Molycop net debt + preference fair value
                                  + earnout present value + other claims)
                 + nonoperating assets
Equity per share = max(raw Tega equity, 0) / issued Tega shares
```

All money is INR million; use millions of shares in the final division. There is
no second currency conversion or second ownership deduction. Full Molycop claims
and their attributable portions appear side by side. The legal debt balances and
full subsidiary financing schedule are not reduced by this valuation attribution.

This is a **proportionate economic group DCF**, not statutory consolidation.
Statutory accounts normally include 100% of a controlled subsidiary and separately
identify noncontrolling interests. Using proportionate cash flows and matching
claims avoids assigning Apollo's ordinary interest to Tega shareholders without
performing a separate subsidiary equity valuation. Lower-level minority/JV and
other-claim scope still requires reconciliation.

Cash taxes are calculated for each business before combining, with no assumed
cross-border loss offsets. Terminal NOPAT normalizes expiring purchase-price
amortization and excludes one-off integration costs; group reinvestment is
positive terminal NOPAT multiplied by group growth divided by group ROIC.
Earnout is discounted at the same group WACC as a provisional simplification.
The pending Apollo share issue remains a separate cash-plus-shares sensitivity.

Only aggregate equity is floored at zero. The model does not value subsidiary
limited-liability/default options separately. It may understate downside equity
if Molycop shortfalls cannot legally reach the parent. This does not establish
parent guarantees or recourse. A negative valuation residual is not a statement
that cash must immediately be raised; funding needs appear in the debt schedules.

## Provisional common valuation assumptions

| Group input | Downside | Base | Upside |
| --- | ---: | ---: | ---: |
| WACC | 14% | 12% | 10.5% |
| Terminal growth | 3% | 4% | 4.5% |
| Terminal ROIC | 13% | 16% | 18% |

These are former legacy assumptions adopted as provisional group choices, not
newly researched combined-business costs of capital. Former Molycop discount and
terminal assumptions are removed. The resulting valuations change; they are not
validated current price targets. Calibrating group WACC, terminal economics and
claim values remains necessary before using the model for an investment decision.

FY26 audited history, operating/asset forecasts, full financing schedules,
acquisition inputs and INR conversion are retained. USD-origin inputs use
INR94.97/USD at the 2 September 2026 market close. The valuation date remains
30 June 2026 and source cutoff 11 September 2026. See the
[INR guide](TEGA_INR_CONVERSION.md) for FX provenance and date limitations.

## Install using GitHub Desktop

This package includes the preceding INR conversion. You need only this package.
It was prepared against main commit `5e8ca508c887cad04216d649d8445aed03859417`.

1. In GitHub Desktop, choose **Repository -> Show in Explorer**.
2. Extract **tega-single-dcf-update.zip**. Open the inner
   **tega-single-dcf-update** folder and copy all its contents into the repository
   folder beside **README.md**. Merge folders and replace included files. If you
   made your own edits, compare those before replacing. No deletions are required.
3. Double-click **Run_Tega_Model.bat**. Open
   **outputs -> tega_molycop -> report.html**. The report should say
   **Tega + Molycop: single group DCF** and show one common WACC per scenario.
4. In GitHub Desktop, review the changes and use the commit summary
   **Use one combined Tega-Molycop DCF in INR**. Commit, then click **Push origin**.

Python 3.11+ is required. No PowerShell or additional runtime packages are needed.
You can also open `examples/tega_molycop_reports/report.html` for precomputed cases.
Re-running overwrites existing generated reports in the selected output folder.

## Code and result schema

`engine.py` generates both operating schedules, combines them in
`_group_cashflows`, calls `_dcf` once and builds one equity bridge. Results have
`group_forecast_inr_m` and `group_dcf_inr_m`. The former `legacy_dcf_inr_m` and
`molycop_dcf_inr_m` outputs no longer exist. The assumptions file declares
`valuation_method: single_attributable_group_dcf`; each scenario supplies
`group_wacc_inr`, `group_terminal_growth_inr` and `group_terminal_roic`.
Old separate-business valuation keys are rejected.

Reports include the annual cash-flow ownership bridge, common discounting,
terminal calculation and full-versus-attributable claims. Thirty sensitivities
cover group valuation, operating inputs and claims. Historic update manifests
are audit records; `TEGA_SINGLE_DCF_UPDATE_FILES.json` describes this release.
