# Historical financial analysis: next project increment

This update adds historical financial-statement ingestion and ratio analysis to
the Milestone 1 DCF project. The DCF remains the existing valuation engine.

## What is included

- A strict JSON reader and annual financial-statement data models.
- Nineteen annual metrics covering growth, profitability, returns, liquidity,
  leverage and cash flow, plus revenue CAGR across the full history.
- A complete synthetic FY2022-FY2026 example, with four growth intervals.
- A sourced Tega FY2024-FY2025 **income-statement-only** example.
- JSON and Markdown reports containing inputs, source references, metric values,
  normalization notes, and reasons for unavailable results.
- Twenty-one additional tests and a Jupyter notebook code walkthrough.

This package contains **new files only**, prepared against the original
`equity-research-quant-platform-milestone-1.zip`. The live GitHub repository has
not been inspected in this session because the GitHub connection is pending.
Do not overwrite a file with the same name if you have independently added one;
compare it first. Nothing in this package needs to replace `dcf.py`, `cli.py`,
`README.md`, `pyproject.toml`, or the original tests.

## Add it using GitHub Desktop

1. Extract this update ZIP into a temporary folder.
2. In GitHub Desktop, select the existing project, then **Repository > Show in
   Explorer**. This is the destination folder.
3. Copy the contents of the extracted update into that destination. Merge the
   `src`, `examples`, `tests` and `docs` folders. Keep `START_FINANCIAL_ANALYSIS.md`
   beside the existing README; do not nest the whole update folder inside it.
4. Review the additions in **Changes** before committing. A suitable summary is
   `Add historical financial-statement analysis`.
5. When you choose to publish the update, commit in GitHub Desktop and push it.

## Start learning

Read `docs/FINANCIAL_ANALYSIS_WALKTHROUGH.md`, then open
`notebooks/financial_analysis_walkthrough.ipynb` in your local Jupyter Notebook
or a notebook-capable editor. GitHub displays notebooks, but does not execute
their cells on an ordinary repository page. The notebook adds the project's
`src` folder to its Python path automatically.

For a terminal run from the project folder, Python 3.11+ is sufficient; this
module has no third-party runtime dependency:

```bash
python run_financial_analysis.py examples/demo_financial_history.json --output-dir outputs/history-demo
python run_financial_analysis.py examples/tega_fy2024_fy2025_income_example.json --output-dir outputs/history-tega
```

If the project is installed as described in the original README, the equivalent
entry point is `python -m equity_analytics.financials INPUT.json`.

The pre-generated reports are in `examples/financial_analysis_reports/`.

## Boundaries of this increment

The importer reads a normalized local JSON file. Source-statement extraction is
manual and documented; automated PDF extraction, data-provider downloads and
SQL persistence are later work. The engine supports five or more annual periods,
but the included **Tega** dataset has only two income-statement periods. The
five-year complete dataset is synthetic. Tega balance-sheet and cash-flow ratios
are unavailable until those inputs are sourced.

Historical results can inform forecast assumptions. They do not automatically
determine future growth, WACC or terminal growth, and this increment does not
change the existing DCF model's working-capital or terminal-value assumptions.

Next: complete Tega's annual balance-sheet and cash-flow inputs with audited
source notes, then build the historical-to-forecast assumption workflow.

