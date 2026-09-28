"""Benchmark-calendar returns with exact endpoints and no missing-price fills."""

from itertools import pairwise
from math import isfinite

from .store import iso_date


def compare_returns(snapshots, benchmark_id, *, start, end, basis="price"):
    if iso_date(start) >= iso_date(end):
        raise ValueError("Start must precede exclusive end")
    if basis not in {"price", "total_return_proxy"}:
        raise ValueError("Unknown return basis")
    by_id = {s["instrument"]["instrument_id"]: s for s in snapshots}
    if len(by_id) != len(snapshots) or benchmark_id not in by_id:
        raise ValueError("Duplicate instruments or missing benchmark")
    if len({s["instrument"]["currency"] for s in snapshots}) != 1:
        raise ValueError("Mixed currencies require an explicit FX model")
    if len({s["data_kind"] for s in snapshots}) != 1:
        raise ValueError("Do not mix synthetic and reported series")
    benchmark = by_id[benchmark_id]
    required_kind = "price_index" if basis == "price" else "total_return_index"
    if benchmark["instrument"]["kind"] != required_kind:
        raise ValueError(
            "Benchmark kind does not match return basis; total returns require a total-return index"
        )
    maps = {}
    for cid, s in by_id.items():
        kind = s["instrument"]["kind"]
        if basis == "price" and kind == "total_return_index":
            raise ValueError(
                "Cannot compare a total-return index using price-return convention"
            )
        field = "close"
        if basis == "total_return_proxy" and kind == "equity":
            if s["source"]["adjusted_basis"] != "split_dividend_adjusted":
                raise ValueError(
                    "Adjusted equity prices are required for total-return proxy"
                )
            field = "adjusted_close"
        elif basis == "total_return_proxy" and kind != "total_return_index":
            raise ValueError("Price index is not a total-return benchmark")
        maps[cid] = {
            b["date"]: b.get(field) for b in s["bars"] if start <= b["date"] < end
        }
    calendar = sorted(maps[benchmark_id])
    if len(calendar) < 2:
        raise ValueError("At least two benchmark observations are required")
    rows = []
    for prior, current in pairwise(calendar):
        for cid, prices in maps.items():
            before, after = prices.get(prior), prices.get(current)
            value = None if before is None or after is None else after / before - 1
            if value is not None and not isfinite(value):
                raise ValueError("Return overflow")
            rows.append(
                {
                    "instrument_id": cid,
                    "start_date": prior,
                    "end_date": current,
                    "calendar_days": (iso_date(current) - iso_date(prior)).days,
                    "return": value,
                    "reason": "missing endpoint; not filled" if value is None else "",
                }
            )
    first, last = calendar[0], calendar[-1]
    summaries = []
    for cid, prices in maps.items():
        before, after = prices.get(first), prices.get(last)
        cumulative = None if before is None or after is None else after / before - 1
        if cumulative is not None and not isfinite(cumulative):
            raise ValueError("Cumulative return overflow")
        summaries.append(
            {
                "instrument_id": cid,
                "first_date": first,
                "last_date": last,
                "cumulative_endpoint_return": cumulative,
                "missing_intervals": sum(
                    r["return"] is None for r in rows if r["instrument_id"] == cid
                ),
                "observed_dates": len(prices),
                "off_benchmark_dates": len(set(prices) - set(calendar)),
            }
        )
    return {
        "return_basis": basis,
        "benchmark_id": benchmark_id,
        "start": start,
        "end_exclusive": end,
        "data_kind": benchmark["data_kind"],
        "currency": benchmark["instrument"]["currency"],
        "summaries": summaries,
        "returns": rows,
        "snapshots": [
            {
                "instrument": s["instrument"],
                "source": s["source"],
                "snapshot_id": s.get("snapshot_id"),
                "sha256": s.get("sha256"),
                "actions": s["actions"],
            }
            for s in snapshots
        ],
        "limitations": [
            "Benchmark observations define the calendar; no authoritative exchange-session completeness check.",
            "Null prices/returns remain missing; no zero substitution or forward fill.",
            "Cumulative endpoint returns can exist despite gaps; inspect missing intervals.",
            "Latest vendor-adjusted history is not historical point-in-time data.",
            "Corporate actions are stored for audit; do not add dividends or reapply splits to adjusted returns.",
        ],
    }
