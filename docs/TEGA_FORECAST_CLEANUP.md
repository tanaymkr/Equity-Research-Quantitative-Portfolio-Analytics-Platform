# Remove old Tega forecasts

This update removes the older FY25-based scenarios that forecast FY26, plus the
separate FY26-based legacy-only case. The combined Tega-Molycop DCF is the single
Tega valuation model. Its FY27-FY34 forecasts, all three scenarios and assumptions
remain intact. Audited FY26 statements and their FY25 comparatives are retained.

Prepared against main commit `bb6624abb7d183fc3398f293d3ef36d778ad8f41`.
The update contains changed/new files and a cleanup launcher; extracting a ZIP
alone cannot delete obsolete files already present in your repository.

## Apply through GitHub Desktop

1. Select the repository in GitHub Desktop. Click **Fetch origin**, and
   **Pull origin** if offered. Select **Repository -> Show in Explorer**.
2. Extract `tega-forecast-cleanup-update.zip`. Open its inner
   `tega-forecast-cleanup-update` folder. Copy **all contents** into the repository
   folder beside `README.md`; merge folders and replace the included files.
   If you have edited any replacement file yourself, compare those edits first.
3. In the repository folder, double-click **Remove_Old_Tega_Forecasts.bat**.
   Python 3.11+ is required. It removes the 24 listed obsolete project files,
   then recognized old reports from the previous standard output folders.
   It leaves unrelated files in those folders intact. Running it again is safe.
4. In GitHub Desktop, review the edits, additions and deletions. Commit with
   summary **Remove obsolete Tega forecasts; retain combined DCF**, then click
   **Push origin**.
5. Run **Run_Tega_Model.bat**. Open **outputs -> tega_molycop -> report.html**.

The complete deleted-file list and expected original hashes are in
`TEGA_FORECAST_CLEANUP_FILES.json`. The cleanup stops before deleting anything
if an obsolete tracked file contains unexpected local changes. Review that file
before removing it manually. The Windows launcher was inspected; its underlying
Python cleanup was verified on Linux.

## What is removed

- `run_tega_fy2026.py`, the separate legacy-only launcher.
- `examples/tega_fy2025_forecast_assumptions.json`.
- `examples/tega_fy2025_downside_assumptions.json`.
- `examples/tega_fy2025_upside_assumptions.json`.
- `examples/tega_fy2026_forecast_assumptions.json`.
- All tracked files under `examples/tega_model_reports/` and
  `examples/tega_fy2026_model_reports/`.
- `notebooks/tega_linked_model_walkthrough.ipynb` and `docs/TEGA_MODEL_METHODS.md`.
- The historical mode in the Tega launchers.

Recognized generated reports are cleared from `outputs/tega_fy2025`,
`outputs/tega_fy2026`, `outputs/tega_model`, `outputs/tega_scenarios`,
`outputs/tega_downside` and `outputs/tega_upside`, when present. If you previously
chose a different output folder, remove that old report folder yourself.

## What remains

- The canonical audited FY26 statement file and earlier reported history.
- The acquisition facts, assumptions, valuation engine and combined reports.
- Financial-ratio analysis and the generic DCF demonstration.
- Reusable accounting functions, with artificial inputs for their automated
  tests. The generic linked-engine command requires explicit custom inputs;
  it no longer selects a Tega forecast by default.

`run_tega_scenarios.py` is an alias for `run_tega_model.py`; both launch the same
combined acquisition model. Old installation manifests remain historical audit
records; they are not current installation instructions.

The cleanup leaves the combined valuation results unchanged. It does not fill
the remaining gaps in a fully consolidated forecast of the acquired group's
three financial statements.
