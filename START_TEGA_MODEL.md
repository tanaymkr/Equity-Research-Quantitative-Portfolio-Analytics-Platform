# Start here: Tega + Molycop acquisition DCF

The acquisition is incorporated in the Python valuation using final closing
terms, Tega FY2026 accounts, June 2026 acquired earnings and August guidance.

**The model is provisional.** It values the business at 30 June 2026 using
reviewed disclosures through 11 September 2026. Some opening balances and
financing terms remain assumptions. It is not a live September price target.

## Open the result first

After extracting the ZIP, double-click:

`examples/tega_molycop_reports/report.html`

Your normal browser opens the precomputed report; Python is not needed to read
it. On GitHub, use [the Markdown comparison](examples/tega_molycop_reports/scenarios.md),
since GitHub normally displays HTML source instead of rendering an uploaded page.

The report includes three cases, the equity bridge, asset and financing schedules,
sensitivities and sources. A downside equity shortfall is a conditional stress
result, not a forecast that the quoted share price becomes zero.

## Copy the update into your repository

1. In GitHub Desktop, select your repository and click **Fetch origin**.
   If **Pull origin** appears, click it.
2. Select **Repository → Show in Explorer**.
3. Right-click `tega-molycop-acquisition-update.zip` and choose **Extract All**.
4. Open the extracted `tega-molycop-acquisition-update` folder. Copy **all its
   contents** into the repository folder opened in step 2. Merge the folders.
   Replace the five existing files when Windows asks: `README.md`,
   `START_TEGA_MODEL.md`, `Run_Tega_Model.bat`, `run_tega_model.py`, and
   `run_tega_scenarios.py`.
5. The launchers must sit beside your existing `README.md`. Do not create a
   second nested project folder.
6. Review GitHub Desktop's changes: additions and the five edits above, with
   no deletions. This ZIP contains only the acquisition update.
7. Use commit summary **Add Tega Molycop acquisition DCF and source register**.
   Click **Commit to main**, then **Push origin**.
8. Open the repository's **Actions** tab to inspect the CI result.

Prepared against main commit `6e5073f6dade2fd96dc52bd6f8977527b2b79abf`.
If you have edited the five existing files, compare your edits before replacing
them. `docs/TEGA_MOLYCOP_UPDATE_FILES.json` lists every package file.

## Run without PowerShell

With Python 3.11+ installed, double-click **Run_Tega_Model.bat**.
Then open **outputs → tega_molycop → report.html** in File Explorer.

Alternatively, use VS Code's **Run Python File** on `run_tega_model.py`, or run
either command in **Command Prompt**, opened in the repository folder:

```text
python run_tega_model.py
python run_tega_scenarios.py
```

Both launchers produce all three acquisition scenarios. No internet connection,
live-data credentials or extra runtime packages are needed.

To compare against a price you supply without changing the valuation:

```text
python run_tega_model.py --reference-price 1700
```

This comparison is marked unverified and is never used to fit the forecast.

## Change assumptions

Open `examples/tega_molycop_assumptions.json` in VS Code.

- `shared` contains opening cash estimates, FX, asset lives, taxes and financing.
- `scenarios` contains `downside`, `base` and `upside` operating/valuation inputs.
- Arrays cover **FY2027 through FY2034**, in order.
- `0.15` means 15%. Molycop is in **USD million**; legacy Tega is in **INR million**.
- The facts file uses **actual shares**, not crore shares or million shares.

Keep `examples/tega_molycop_facts.json` for verified disclosures. A `null` means
an item was not established, not zero. Rerun after editing. Fresh outputs go to
`outputs/tega_molycop`; the committed example report remains a fixed snapshot.

## Original linked model

The FY2025 model and its historical files remain available:

```text
python run_tega_model.py --historical-fy2025
python run_tega_scenarios.py --historical-fy2025
```

The new acquisition module provides cash-flow, asset and financing schedules.
It does **not** claim to be a completed statutory three-statement forecast of
the combined group. That requires missing post-close balance-sheet detail and
finalized purchase accounting.

Read [the model walkthrough](docs/TEGA_MOLYCOP_MODEL.md) and
[validation and open inputs](docs/TEGA_MOLYCOP_VALIDATION.md).
