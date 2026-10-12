# Research universe: index membership and company master

This step turns an NSE index list (Nifty 100 by default) into a dated
universe that later factor research and backtests can trust. It also
writes a price configuration so the existing price pipeline can download
every member in one run.

## Run on Windows

Two launchers, run in this order:

1. `Run_Universe.bat` downloads the current Nifty 100 list from NSE, stores
   it, and opens `outputs/universe/NIFTY100/report.html`. Re-running it is
   safe: an unchanged list is recorded as "confirmed" for today.
2. `Run_Universe_Prices.bat` first rebuilds `market_config.json` from the
   stored list (no download, so it can never reuse an old config), then
   downloads prices for every member and opens
   `outputs/prices/NIFTY100/report.html`. The benchmark index is downloaded
   first, so a rejected index fails in seconds.

If NSE blocks the download but a list is already stored, `Run_Universe.bat`
prints a WARNING and continues with the stored list; check the "list
effective" date it prints. With nothing stored, or to load a list yourself:

1. Open <https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv>
   in a browser; it downloads the constituent list CSV. The same list is also
   linked from the Nifty 100 page on niftyindices.com.
2. Import the saved file, stating when you downloaded it:

```bash
python run_universe.py --import path/to/ind_nifty100list.csv --retrieved-at 2026-10-10T18:00:00+05:30
```

`--retrieved-at`, `--effective-on` and `--source-url` only work with `--import`:
a fresh download is always dated by its own retrieval time.

Command-line equivalent of `Run_Universe_Prices.bat`:

```bash
python run_universe.py
python run_price_pipeline.py --download --config outputs/universe/NIFTY100/market_config.json --output outputs/prices/NIFTY100
```

Other NSE broad indices use the same file layout: `--universe NIFTY50`,
`NIFTY200` or `NIFTY500` (with `--download`, or `--import` plus a saved file).

**Benchmark.** Each universe is compared with its own price index: NIFTY50
with `^NSEI`, NIFTY100 with `^CNX100`, NIFTY200 with `^CNX200` and NIFTY500
with `^CRSLDX` (Yahoo tickers). Use `--benchmark NIFTY50` (or another of these)
to compare against a different index. These are price indices, so returns
exclude dividends on both sides.

`Run_Price_Pipeline.bat` is unchanged: it still downloads only Tega, Wabag and
the NIFTY 50 from `examples/market_config.json` into `outputs/prices/`.

## Outputs

`outputs/universe/<UNIVERSE>/`:

- `report.html`: warnings, statement-template and industry counts, changes
  between stored lists, and the member table.
- `members.csv`: company ID, NSE symbol, name, industry, template, series, ISIN.
- `summary.json`: the same information for scripts.
- `market_config.json`: input for `run_price_pipeline.py`.
- `downloads/`: the exact source CSV bytes, named by SHA-256.

The database is `outputs/data/universe.sqlite`, separate from the financial
and price databases. Outputs and databases are ignored by Git.

## How membership dates work

Each import is a **snapshot**: "these companies were in NIFTY100 on
`effective_on`". By default `effective_on` is the retrieval date, because a
list downloaded today only proves today's membership. Set `--effective-on` when
you import an older list whose date you can document (for example an archived
copy from before an index review).

- Each distinct list is stored once. Re-running `Run_Universe.bat` when NSE's
  list has not changed records a new date for the same list ("confirmed"), so
  it is never flagged stale while you keep refreshing it. Re-importing the same
  file for the same date is a no-op. A different list for a universe and date
  that already has one is rejected.
- `--as-of DATE` uses the latest snapshot effective on or before that date.
- **Survivorship guard:** asking for a date before the earliest stored list
  fails. Today's Nifty 100 excludes companies that dropped out, so applying it
  to 2021 would make a backtest look better than reality. `--allow-backfill`
  overrides this, and every output is then labelled survivorship-biased.
- A list more than 183 days older than the as-of date is flagged as stale,
  since NSE reviews its broad indices twice a year.
- The price config is marked `survivorship_biased` when its price start date
  is earlier than the list's effective date. This is the normal case with only
  one current list: price history is fine for building and debugging signals,
  but backtest results over that period carry this bias.

Loading older lists, one per index review, is how the universe becomes
survivorship-free. The report's "changes" table then shows additions, removals
and ISIN changes between consecutive lists.

## Company identity and templates

- `company_id` is the NSE symbol with `&` replaced by `_` (`M&M` becomes `M_M`),
  because the financial store does not allow `&` in IDs. Yahoo tickers use the
  exact symbol plus `.NS`. TEGA and WABAG keep the same IDs as before.
- ISINs are checked with the ISO 6166 check digit. An ISIN can change after a
  face-value split while the symbol stays the same; the changes table flags it.
- A symbol rename creates a new `company_id`. Linking renamed symbols needs an
  explicit alias table, which is not built yet.
- `template` routes each company to a statement model: `financials` for NSE's
  "Financial Services" industry (banks, NBFCs, insurers), `general` for other
  known industries, and `unclassified` (with a warning) for any industry label
  this code has not seen.

## Price-data problems found in the first Nifty 100 download

An audit of the October 2026 download (2021-04-01 to 2026-10-09, all 101
series complete to the last date) found Yahoo artefacts that would distort
momentum and backtest returns if used unadjusted:

| Instrument | Date | One-day "return" | Cause |
| --- | --- | --- | --- |
| VEDL | 2026-04-30 | -64.9% | Demerger; parent price not adjusted |
| TMPV (Tata Motors) | 2025-10-14 | -40.2% | Commercial-vehicle demerger; not adjusted |
| TRENT | 2026-01-01 | -33.0% | Price ratio 0.6695 matches a 1.5 split (0.6667); Yahoo dates the split 2026-06-04, where no step appears. Very likely a mis-dated corporate action |

Other large moves are real market events (Adani group, January-February 2023
and 21 November 2024; election-result day, 4 June 2024). Recent listings and
demerged entities (JIOFIN, HYUNDAI, TATACAP, ENRIN, TMCV, VAML, ETERNAL) have
missing intervals before their first trade, as expected. On 15 January 2026
the NIFTY 50 and a few stocks have null bars from Yahoo; they stay missing.

The factor step needs an explicit corporate-action adjustment table (or a
documented exclusion window) for these cases before momentum is computed.

## Not yet covered

- Financial statements for the members. The universe defines *who*; loading
  their annual statements into the financial store needs a data-source decision.
- Historical lists before the first import, and symbol-rename aliases.
- The price pipeline stops if any single ticker fails to download; with ~100
  names, check the console and rerun or remove the failing ticker from the
  generated config.

## Verification

```bash
python -m pytest tests/test_universe.py
python -m ruff check .
```

Tests cover ISIN validation, strict parsing, idempotent and immutable
snapshots, rollback, as-of selection with out-of-order loads, the survivorship
guard, stale and unclassified warnings, change detection, the price-config
shape, the download path (with a fake network) and the command end to end.
