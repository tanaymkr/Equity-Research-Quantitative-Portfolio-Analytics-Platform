# Research universe: index membership and company master

This step turns an NSE index list (Nifty 100 by default) into a dated
universe that later factor research and backtests can trust. It also
writes a price configuration so the existing price pipeline can download
every member in one run.

## Run on Windows

Double-click `Run_Universe.bat`. It downloads the current Nifty 100 list from
NSE, stores it, and opens `outputs/universe/NIFTY100/report.html`.

NSE sometimes blocks automated downloads. If that happens:

1. Open <https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv>
   in a browser; it downloads the constituent list CSV. The same list is also
   linked from the Nifty 100 page on niftyindices.com.
2. Import the saved file, stating when you downloaded it:

```bash
python run_universe.py --import path/to/ind_nifty100list.csv --retrieved-at 2026-10-10T18:00:00+05:30
```

Then download prices for every member using the generated config:

```bash
python run_price_pipeline.py --download --config outputs/universe/NIFTY100/market_config.json --output outputs/prices/NIFTY100
```

Other NSE broad indices use the same file layout: `--universe NIFTY50`,
`NIFTY200` or `NIFTY500` (with `--download`, or `--import` plus a saved file).

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

- Snapshots are immutable. Re-importing the same file is a no-op. A different
  list for the same universe and date is rejected; the same file cannot be
  stored under two dates.
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
