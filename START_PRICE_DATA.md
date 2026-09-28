# Historical price-data layer

## Install and run

1. Pull the latest repository cleanup first. This update was built on commit `e110e47949c3bec1c051b7bc6f6a89cd33329fe5`.
2. Copy the update ZIP contents directly into the repository root, preserving the `src`, `examples`, and `tests` folders. Python 3.11 or newer is required; no new runtime packages are needed.
3. Double-click `Run_Price_Pipeline.bat`. This downloads real data and opens `outputs/prices/report.html` when successful. Use this new launcher, rather than Run Tega Model.

Command-line equivalent:

```bash
python run_price_pipeline.py --download
```

The example configuration covers 2024-04-01 through 2026-09-28 (exclusive end 2026-09-29), using TEGA.NS, WABAG.NS and ^NSEI. Edit `examples/market_config.json` to change the dates. Use a completed trading-day range; downloading today's unfinished session can capture provisional values. Availability varies by provider; requested dates are not a promise of complete coverage.

## Outputs

- `outputs/data/market.sqlite`: instrument master, immutable retrieval snapshots, daily prices and corporate actions.
- `outputs/prices/downloads/`: normalized input JSON, including the original provider response, under content-hash filenames.
- `prices.csv`: close, adjusted close, volume, currency and retrieval metadata.
- `returns.csv`: simple decimal returns between consecutive benchmark observations. Weekends can make intervals longer than one calendar day.
- `corporate_actions.csv`: provider dividend amounts and split ratios (new shares / old shares), retained as evidence.
- `summary.json` and `report.html`: source lineage, coverage, endpoint returns and missing-interval counts.

Generated outputs and databases remain ignored by Git. Commit source/config/tests/docs, not downloaded data.

## Conventions

The default comparison uses **price returns**: Yahoo split-adjusted Close for equities and the NIFTY 50 price index level. This excludes dividends. Adjusted Close is also stored; the provider describes it as split/dividend adjusted. Corporate actions are not reapplied to these prices. The adapter checks ticker, currency, instrument type and array lengths, maps timestamps into the exchange timezone, and validates finite positive prices, nonnegative volumes and unique ascending dates.

The total-return proxy option requires an explicitly classified total-return index benchmark and dividend-adjusted equity observations. **^NSEI is not configured as a total-return index.** Renaming it will not produce TRI data; obtain a genuine TRI series before enabling that comparison.

Missing prices and returns remain null (blank in CSV). There is no forward fill, zero substitution, or adjusted-close fallback when Close is missing. This differs intentionally from the fundamental screener's requested missing-metric-as-zero policy. Both endpoints are required for each interval. An endpoint cumulative return can still be available when intermediate prices are missing: always inspect missing-interval counts.

The benchmark's observed dates define the comparison calendar; this is not yet an official NSE holiday/session calendar. Missing sessions absent from all series cannot be detected by this layer. Off-benchmark stock dates are counted, not silently inserted into the return calendar. Mixed currencies and mixed synthetic/reported data are rejected.

## Offline reuse and audit

After a successful download, regenerate the report without network access:

```bash
python run_price_pipeline.py
```

Import saved normalized JSON files into another database:

```bash
python run_price_pipeline.py --import path/to/first.json path/to/second.json path/to/benchmark.json
```

Each snapshot has a raw-content SHA-256, retrieval time, load time, adjustment metadata and retained source payload. Identical-file imports are idempotent. A newly retrieved series is a new full snapshot, even if market values are unchanged. Older snapshots remain available; we never splice differently adjusted versions together.

`--known-at 2026-09-28T23:59:59Z` selects the latest whole snapshot retrieved by that timestamp. This is a **retrieval cutoff**, not proof that historical adjusted values were known on each original trading date. Latest vendor history may be revised and may reflect subsequent corporate actions. Do not present it as a point-in-time or survivorship-free backtest dataset.

The market database is separate from the existing financial database to preserve its schema. TEGA/WABAG IDs match their annual-data IDs. A file import is transactional; multi-file imports are not a single transaction. All downloads complete and all input files validate before ingestion begins. A later metadata conflict can still leave earlier valid files imported. Network errors never cause synthetic fallback. Failed refreshes do not replace the existing report; check the console and displayed retrieval times before using an old report.

## Data source and limitations

The optional standard-library adapter uses Yahoo Finance's chart endpoint. This is an unofficial integration, so availability and response shape can change. Retained normalized JSON enables offline reproduction. Respect the provider's data-use terms; this update does not bundle downloaded histories for redistribution.

Provider references:
- Yahoo Adjusted Close: https://in.help.yahoo.com/kb/finance/adjusted-close-sln28256.html
- Upstream chart-adapter implementation: https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py

This milestone supplies the inputs for momentum/factor research. It does not implement portfolios, trading costs, rebalancing, risk metrics, or a complete backtest. Wabag DCF assumptions remain your separate research task.

## Verification

Install development dependencies, then run:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

New tests cover immutable revisions, duplicate imports, retrieval cutoffs, rollback, invalid prices, missing endpoints, dividend conventions, benchmark compatibility, exchange dates and preservation of unrelated financial databases.
