"""Optional Yahoo chart adapter; vendor values retained without re-adjustment."""

import json
from datetime import UTC, datetime, timedelta, timezone
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .store import iso_date, validate_snapshot


def _exchange_timezone(name):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        # Windows may lack IANA tzdata. India has no DST in this dataset period.
        if name in {"Asia/Kolkata", "Asia/Calcutta"}:
            return timezone(timedelta(hours=5, minutes=30))
        raise ValueError("Install tzdata for this exchange timezone") from None


def normalize_chart(raw, instrument, url, retrieved_at, start, end):
    chart = raw["chart"]
    if chart.get("error") or not chart.get("result"):
        raise ValueError(f"Provider returned no result: {chart.get('error')}")
    r = chart["result"][0]
    meta = r["meta"]
    if (
        meta["symbol"].upper() != instrument["ticker"].upper()
        or meta["currency"] != instrument["currency"]
    ):
        raise ValueError("Provider ticker/currency differs from configured instrument")
    expected = "EQUITY" if instrument["kind"] == "equity" else "INDEX"
    if meta.get("instrumentType") != expected:
        raise ValueError("Provider instrument type differs from configuration")
    zone = _exchange_timezone(meta["exchangeTimezoneName"])
    timestamps = r.get("timestamp", [])
    q = r["indicators"]["quote"][0]
    adj = (
        r["indicators"]
        .get("adjclose", [{}])[0]
        .get("adjclose", [None] * len(timestamps))
    )
    closes = q.get("close", [])
    volumes = q.get("volume", [None] * len(timestamps))
    if any(len(x) != len(timestamps) for x in (adj, closes, volumes)):
        raise ValueError("Provider arrays have inconsistent lengths")
    bars = []
    for timestamp, close, adjusted, volume in zip(
        timestamps, closes, adj, volumes, strict=True
    ):
        day = datetime.fromtimestamp(timestamp, zone).date().isoformat()
        if start <= day < end:
            bars.append(
                {
                    "date": day,
                    "close": close,
                    "adjusted_close": adjusted,
                    "volume": volume,
                }
            )
    actions = []
    for kind, items in r.get("events", {}).items():
        if kind not in {"dividends", "splits"}:
            continue
        for event in items.values():
            day = datetime.fromtimestamp(event["date"], zone).date().isoformat()
            if start <= day < end:
                value = (
                    event["amount"]
                    if kind == "dividends"
                    else event["numerator"] / event["denominator"]
                )
                actions.append(
                    {
                        "date": day,
                        "type": "dividend" if kind == "dividends" else "split",
                        "value": value,
                    }
                )
    p = {
        "schema_version": 1,
        "instrument": instrument,
        "data_kind": "reported",
        "source": {
            "provider": "Yahoo Finance chart",
            "url": url,
            "retrieved_at": retrieved_at,
            "close_basis": "split_adjusted"
            if instrument["kind"] == "equity"
            else "index_level",
            "adjusted_basis": "split_dividend_adjusted"
            if instrument["kind"] == "equity"
            else instrument["kind"],
            "requested_start": start,
            "requested_end_exclusive": end,
            "exchange_timezone": meta["exchangeTimezoneName"],
            "note": "Vendor adjustments retained; actions are evidence, never applied twice. Historical revisions may incorporate events after a historical test date.",
        },
        "bars": bars,
        "actions": sorted(actions, key=lambda a: (a["date"], a["type"])),
        "provider_response": raw,
    }
    validate_snapshot(p)
    return p


def download_history(instrument, start, end):
    first, last = iso_date(start), iso_date(end)
    if first >= last:
        raise ValueError("Start must precede exclusive end")
    params = {
        "period1": int(datetime.combine(first, datetime.min.time(), UTC).timestamp()),
        "period2": int(datetime.combine(last, datetime.min.time(), UTC).timestamp()),
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + quote(instrument["ticker"], safe="")
        + "?"
        + urlencode(params)
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        raw = json.load(response)
    return normalize_chart(
        raw, instrument, url, datetime.now(UTC).isoformat(), start, end
    )
