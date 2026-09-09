# Start here: Tega's reported statements and linked model

This update adds an audited historical Tega case and a linked five-year forecast to your existing Python project.

**The historical inputs are actual consolidated FY2024 and FY2025 figures. Forecast assumptions are illustrative. This is a dated FY2025 case, not a current Tega valuation.** FY2026 results and subsequent acquisitions/financing are not included.

## Add the update through GitHub Desktop

1. Open GitHub Desktop and select `Equity-Research-Quantitative-Portfolio-Analytics-Platform`.
2. Click **Fetch origin**. If **Pull origin** appears, click it.
3. Select **Repository → Show in Explorer**. This opens the correct local repository folder.
4. Extract the downloaded `tega-linked-model-update.zip` using **Extract All** in File Explorer.
5. Open the extracted `tega-linked-model-update` folder. Copy **everything inside it** into your local repository folder. `START_TEGA_MODEL.md` and `run_tega_model.py` should sit beside your existing `README.md`. Merge the `src`, `examples`, `docs`, `notebooks`, and `tests` folders when Windows asks. Do not place the whole extracted folder inside the repository.
6. Return to GitHub Desktop. The package contains new files only; the existing project files should not show edits or deletions. Review the file list.
7. Enter the commit summary `Add Tega reported statements and linked financial model`, then click **Commit to main**.
8. Click **Push origin**. On GitHub, open **Actions** and wait for the new CI run to turn green.

The package was prepared against main commit `27a44c22a48fb46bdd786ddc4f32a4dabf776323`. The existing DCF demo and earlier financial-analysis files continue to work.

## Read the result before running anything

Open these files on GitHub:

- [Audited historical statements and source checks](examples/tega_model_reports/base/historical_statements.md)
- [Linked forecast, debt schedule, asset schedule and DCF](examples/tega_model_reports/base/forecast.md)
- [Scenario comparison and WACC/g sensitivity](examples/tega_model_reports/scenarios.md)
- [Code walkthrough and modeling conventions](docs/TEGA_MODEL_METHODS.md)
- [Source map and verification evidence](docs/TEGA_MODEL_VALIDATION.md)

The precomputed reports let you inspect the output without installing or running Python.

## Run locally without PowerShell

If Python 3.11 or later is installed, double-click **Run_Tega_Model.bat** in File Explorer. It runs the model and leaves the window open so you can read any error. The runner writes `model.json`, `forecast.md`, and `historical_statements.md` into `outputs/tega_fy2025`.

Alternatively, open the project in VS Code, open `run_tega_model.py`, and click **Run Python File**. No additional runtime packages or live-data credentials are required.

## Change an assumption

Open `examples/tega_fy2025_forecast_assumptions.json` in VS Code or another text editor. Change `revenue_growth`, `ebitda_margin`, collection days, capex, asset lives or debt assumptions, then run the model again. A decimal `0.10` means 10%. Each annual array covers FY2026 through FY2030 in order.

Keep the historical statements file as reported. The assumptions file is the place to make forecast changes. Scenario examples have separate `downside` and `upside` assumptions files; the methods guide explains how to run them.

## What this milestone completes

The project now has sourced historical statements, historical asset/debt/cash reconciliations, forecast working capital, depreciation and amortisation, debt and lease schedules, linked financial statements, and a DCF using the forecast's FCFF.

The next research task is to extend the historical period and replace the illustrative assumptions with a documented investment thesis. A current Tega valuation also requires the later reporting period, acquisition and financing details, current diluted shares, and researched valuation assumptions.
