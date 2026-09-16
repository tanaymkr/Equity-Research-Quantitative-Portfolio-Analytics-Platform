# Start here: FY26 statements and Tega + Molycop

The default Tega model now reads the complete FY26 consolidated income statement,
balance sheet and cash-flow statement, validates 92 historical reconciliations,
and uses that common source for the acquisition DCF. FY25 comparatives are included.

## Copy this update into your repository

1. In GitHub Desktop, select your repository and click **Fetch origin**. If
   **Pull origin** appears, click it.
2. Select **Repository -> Show in Explorer**.
3. Right-click `tega-fy26-statements-update.zip` and choose **Extract All**.
4. Open the extracted `tega-fy26-statements-update` folder. Copy **all its
   contents** into the repository folder. Merge folders and replace the existing
   files included in this update. The launchers belong beside `README.md`.
5. Review the changes in GitHub Desktop. There should be additions and edits,
   with no file deletions. If you have made other edits, compare them before
   replacing files. The full file list is in `docs/TEGA_FY2026_UPDATE_FILES.json`.
6. Commit with summary **Incorporate FY26 statements and link model inputs**,
   then click **Push origin**. Inspect the result in GitHub's **Actions** tab.

Prepared against main commit `371e3cf53833328767b1854a75e3fcd2faf90ff2`.
You need the existing repository; this ZIP contains the update files only.

## Read the results without running Python

Open either file in your browser:

- `examples/tega_molycop_reports/report.html`: acquisition scenarios and a link
  to the complete FY26 statements.
- `examples/tega_molycop_reports/historical_statements.html`: audited statements,
  supporting notes, debt/asset/equity rolls and all reconciliation checks.

On GitHub, read [the FY26 statements](examples/tega_molycop_reports/historical_statements.md)
and [the acquisition scenarios](examples/tega_molycop_reports/scenarios.md).

## Run without PowerShell

With Python 3.11+ installed, double-click **Run_Tega_Model.bat**. Then open
**outputs -> tega_molycop -> report.html**. No extra runtime packages are needed.

For the optional legacy-only linked forecast, use VS Code's **Run Python File**
on `run_tega_fy2026.py`, or run `python run_tega_fy2026.py` in Command Prompt.
It writes `outputs/tega_fy2026`. This control model excludes Molycop and acquisition
funding; its equity value is not the current combined group's value.

The FY25 archive still runs with `python run_tega_model.py --historical-fy2025`.

## Change assumptions

- Acquisition scenarios: `examples/tega_molycop_assumptions.json`.
- Legacy-only linked forecast: `examples/tega_fy2026_forecast_assumptions.json`.
- Audited actuals: `examples/tega_fy2026_reported_statements.json`.
- Acquisition facts: `examples/tega_molycop_facts.json`, which references the
  audited statement file and contains the deal and post-close disclosures.

Keep historical facts separate from forecasts. The two forecast assumption files
are separate editable models; their operating inputs are initially aligned.
Acquisition arrays cover FY2027-FY2034; legacy control arrays cover FY2027-FY2031.
Legacy money uses INR million, Molycop uses USD million. `0.15` means 15%.

The acquisition values remain provisional as of 30 June 2026. Some June balances,
preference economics and purchase-accounting inputs still require evidence.
Read [the FY26 walkthrough](docs/TEGA_FY2026_STATEMENTS.md) and
[the acquisition methodology](docs/TEGA_MOLYCOP_MODEL.md).
