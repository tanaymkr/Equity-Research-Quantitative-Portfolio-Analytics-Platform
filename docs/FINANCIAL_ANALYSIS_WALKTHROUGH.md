# Walk through the historical analysis code

The new code follows a short path: read a JSON file, validate its data, calculate
each year's metrics, then format the results. It uses Python's standard library.

## 1. Read the input

Open `examples/demo_financial_history.json`. It has one company, source
documents, an information cutoff (`as_of`), and a list named `annuals`.
Each list item contains one full financial year's income statement, balance
sheet and cash-flow inputs. Values are fictional and use INR crore throughout.

```python
from equity_analytics.financials import load_history

history = load_history("examples/demo_financial_history.json")
latest = history.annuals[-1]
print(latest.revenue)  # 10000.0
```

`load_history()` in `financials/io.py` reads the text using `Path.read_text()`.
`json.loads()` turns it into a Python dictionary. `history_from_dict()` then
builds the `Company`, `SourceDocument`, `AnnualStatement` and `FinancialHistory`
objects defined in `models.py`.

`[-1]` selects the last annual record. The history sorts records chronologically,
so it selects the latest period even if the JSON listed the years out of order.

## 2. Validate before calculating

The data classes use `__post_init__()` to check their inputs after construction.
They reject misspelled fields, duplicate years, non-numeric values, NaN, infinity,
quarterly periods, unknown sources and source dates after the information cutoff.

A missing optional field becomes `None`. It never silently becomes zero.
Negative earnings and equity are allowed because real businesses can report
losses and accumulated deficits. Capex is a positive cash outflow magnitude.

All years must already be normalized to the same currency, unit and consolidated
or standalone basis. The program checks the declared contract; it cannot detect
an incorrectly transcribed million figure that was labelled crore.

## 3. Calculate one ratio

```python
from equity_analytics.financials import analyze_history

report = analyze_history(history)
margin = report.years[-1].metrics["ebit_margin"]
print(margin.value)  # 0.15
print(margin.unit)   # fraction
```

`analyze_history()` in `ratios.py` loops over the annual records. For EBIT margin,
it calls `_ratio(annual.ebit, annual.revenue)`. In the latest demo year:

    EBIT margin = 1,500 / 10,000 = 0.15 = 15%

`_ratio()` returns a `Metric` object with a `value`, `unit` and optional `reason`.
If a denominator is missing or non-positive, the value is `None` and the reason
explains why. Negative numerators are still meaningful for profit margins.

## 4. Compare years correctly

The loop remembers `previous`, the earlier annual record. Revenue growth in
FY2026 is `(10,000 / 9,000) - 1`, or approximately 11.11%.

ROE uses profit attributable to owners divided by average equity attributable to
owners. For the latest demo year, it is `1,000 / ((4,650 + 5,200) / 2)`, about
20.30%. Averaging the two balance-sheet dates better matches the profit earned
throughout the year. The first year's ROE is unavailable because its opening
balance sheet was not supplied.

When a year is missing, the engine does not call a multi-year change “YoY”.
It returns an unavailable YoY metric. Endpoint CAGR uses the actual elapsed
years: five annual observations span four annual growth intervals.

## 5. Examine cash flow and leverage

```python
metrics = report.years[-1].metrics
print(metrics["net_debt"].value)               # 750.0
print(metrics["cash_flow_after_capex"].value)  # 830.0
```

Net debt is total debt minus cash and equivalents. A negative result denotes
net cash. `cash_flow_after_capex` is CFO minus capex. Its financing and tax
classification follows the source cash-flow statement, so it is not automatically
the unlevered FCFF forecast by our DCF engine.

## 6. Follow the Tega example

Switch the input path to `examples/tega_fy2024_fy2025_income_example.json`.
Read each annual record's `notes` before comparing EBITDA margins. The example
normalizes the two presentations to operating EBIT and EBITDA excluding other
income. The records are in INR million, unlike the synthetic example in crore.

Try inspecting `report.years[-1].metrics["roe"].reason` after analyzing Tega.
It explains why a return on equity is unavailable with income statements alone.

## 7. Read the tests

`tests/test_financials.py` includes hand-calculated expected values, missing and
invalid input cases, and an export check. It uses `unittest` and is also collected
by the existing pytest workflow. The original six DCF tests remain in place.

Your first exercise: in a temporary copy of the synthetic JSON, change the latest
EBIT from 1,500 to 1,600. Rerun the model and predict which metrics change. EBIT
margin becomes 16%; EBITDA, ROCE, finance-cost coverage and net-debt/EBITDA also
change. Revenue growth and net margin stay as entered because this is a historical
analysis input, not a linked three-statement forecast.

