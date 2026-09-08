# Data contract and calculation conventions

## Input structure

Required top-level keys: `schema_version` (integer 1), `company`, `as_of`,
`sources`, and `annuals`. Optional `notes` records dataset limitations.

Company fields: `name`, `ticker`, `currency` (uppercase three-letter code),
`financial_unit` (`units`, `million` or `crore`), `statement_basis`
(`consolidated` or `standalone`) and `data_kind` (`reported` or `synthetic`).
The unit and basis apply to every annual row. No conversion or mixing is implicit.

Each source has a unique `source_id`, `title`, `published_on` (YYYY-MM-DD),
`locator` (page/table/column), and an HTTP(S) `url` for reported data. Dates must
not exceed `as_of`. These checks provide basic provenance; this version is not a
point-in-time database and does not prove that inputs are free of restatements.

Each annual row requires `fiscal_year` (the calendar year in which the fiscal
year ends), `period_end` (YYYY-MM-DD), `source_id` and `revenue`. `months` defaults
to 12; partial years are rejected. Duplicate years are rejected. Missing years
are allowed but disable consecutive-year calculations across the gap.

## Financial fields

Every amount below uses the company's declared money unit. Zero is a reported
zero; omission or JSON `null` means unavailable.

| Field | Meaning |
| --- | --- |
| revenue | Revenue from operations, excluding other income; non-negative |
| ebit | Operating EBIT excluding other income, finance costs and tax; may be negative |
| depreciation_amortisation | D&A expense for the period; positive magnitude |
| net_income | Total post-tax profit, including non-controlling interests |
| net_income_to_owners | Profit attributable to the parent's ordinary equity owners |
| finance_costs | Reported finance costs; includes more than cash interest in some accounts |
| total_assets | Closing balance-sheet total assets |
| total_liabilities | Closing balance-sheet total liabilities |
| total_equity | Closing equity including non-controlling interests; may be negative |
| equity_to_owners | Closing equity attributable to the parent's ordinary owners |
| current_assets | Closing current assets |
| current_liabilities | Closing current liabilities |
| cash_and_equivalents | Closing cash and equivalents; exclude restricted deposits and unverified investments |
| total_debt | Closing interest-bearing borrowings plus lease liabilities; document any exception |
| operating_cash_flow | CFO as reported after tax, with source interest classification retained |
| capex | Positive cash payments for tangible and intangible fixed assets; exclude acquisitions and financial investments |
| notes | Normalization decisions, omitted line items and source-specific caveats |

For consolidated data, owners' profit and owners' equity must match; do not use
total group profit with owners-only equity. If preferred equity is material,
normalize both numerator and denominator consistently before loading.

## Outputs

Ratios expressed as percentages use decimal fractions in JSON, e.g. `0.15`.
Markdown formats them as `15.00%`. Multiples are stored as numbers and displayed
with `x`. Money outputs retain the input money unit. No share-price metrics are
inferred from historical statement data.

| Metric | Formula |
| --- | --- |
| revenue | Supplied revenue |
| revenue_growth | Current / preceding-year revenue - 1 |
| net_income_growth | Current / preceding-year total net income - 1 |
| ebitda | Operating EBIT + D&A |
| ebit_margin | Operating EBIT / revenue |
| ebitda_margin | Operating EBITDA / revenue |
| net_margin | Total net income / revenue |
| roe | Owners' net income / average owners' equity |
| roa | Total net income / average total assets |
| roce | Operating EBIT / average (total assets - current liabilities) |
| current_ratio | Current assets / current liabilities |
| debt_to_equity | Total debt / total equity |
| net_debt | Total debt - cash and equivalents |
| net_debt_to_ebitda | Net debt / operating EBITDA |
| finance_cost_coverage | Operating EBIT / finance costs |
| operating_cash_flow_margin | CFO / revenue |
| operating_cash_flow_to_net_income | CFO / total net income |
| capex_to_revenue | Capex / revenue |
| cash_flow_after_capex | CFO - capex |
| revenue_cagr | (Last revenue / first revenue)^(1 / elapsed years) - 1 |

All ratio denominators must be positive. Growth from a zero or negative base
is unavailable. Margins can be negative, and net-debt/EBITDA can be negative
for a net-cash company with positive EBITDA. EBITDA at or below zero yields no
leverage multiple. ROE/ROA/ROCE require positive balances at both opening and
closing dates; the first observation or a missing preceding year yields N/A.
ROCE is a pre-tax accounting return, not ROIC. Finance-cost coverage is explicitly
named to avoid implying that all reported finance costs are pure interest expense.

`cash_flow_after_capex` is not automatically FCFF. Deriving FCFF requires
appropriate financing/tax adjustments or a NOPAT-based operating approach.
The existing DCF performs its own FCFF forecast and is not changed here.

The program flags balance-sheet mismatches above the larger of 0.1 money units
or 0.01% of assets; it also flags inconsistent component totals. These are
warnings because classification and source rounding can need analyst review.
Input validation cannot certify that a source number was transcribed correctly.

## Tega source normalization

This historical teaching example uses the FY24 column of Tega's
[8 August 2024 presentation](https://www.tegaindustries.com/images/media/Intimation_for_Investor_Presentation_-_08_08_2024.pdf)
and the FY25 column of its
[5 August 2025 presentation](https://www.tegaindustries.com/images/media/Intimation_for_Investor_Presentation_-_05_08_2025.pdf).
Both are on PDF page 7 (slide 6), in INR million. Operating EBIT is derived rather
than copied from a potentially inconsistent headline. The exact arithmetic and
source values are retained in the annual JSON notes. EBITDA is then reconstructed
using that operating EBIT and D&A. These are rounded presentation values; a full
company build should reconcile them to audited statements and subsequent restatements.

Missing Tega cash flows, debt and equity balances remain null. No current market
prices, target prices, recent acquisitions or FY2026 results are included.

The broader financial-analysis and FCFF concepts follow
[CFA Institute: Financial Analysis Techniques](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/financial-analysis-techniques)
and [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation).
The exact formula and missing-data conventions above are this project's choices.
