"""Portable CSV, JSON and HTML market-data reports."""

import csv
import json
from html import escape
from pathlib import Path


def write_report(result, snapshots, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    def write_csv(name, fields, rows):
        with (output / name).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in rows:
                w.writerow(
                    {
                        k: (
                            "'" + v
                            if isinstance(v, str) and v.startswith(("=", "+", "-", "@"))
                            else v
                        )
                        for k, v in row.items()
                    }
                )

    prices, actions = [], []
    for s in snapshots:
        cid = s["instrument"]["instrument_id"]
        for b in s["bars"]:
            if result["start"] <= b["date"] < result["end_exclusive"]:
                prices.append(
                    {
                        "instrument_id": cid,
                        **b,
                        "currency": s["instrument"]["currency"],
                        "retrieved_at": s["source"]["retrieved_at"],
                        "snapshot_id": s["snapshot_id"],
                    }
                )
        actions.extend({"instrument_id": cid, **a} for a in s["actions"])
    write_csv(
        "prices.csv",
        [
            "instrument_id",
            "date",
            "close",
            "adjusted_close",
            "volume",
            "currency",
            "retrieved_at",
            "snapshot_id",
        ],
        prices,
    )
    write_csv(
        "returns.csv",
        [
            "instrument_id",
            "start_date",
            "end_date",
            "calendar_days",
            "return",
            "reason",
        ],
        result["returns"],
    )
    write_csv(
        "corporate_actions.csv", ["instrument_id", "date", "type", "value"], actions
    )
    (output / "summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf-8"
    )
    rows = ""
    for s in result["summaries"]:
        value = s["cumulative_endpoint_return"]
        display = "Missing" if value is None else f"{value:.2%}"
        rows += (
            "<tr>"
            + "".join(
                f"<td>{escape(str(v))}</td>"
                for v in [
                    s["instrument_id"],
                    s["first_date"],
                    s["last_date"],
                    s["observed_dates"],
                    display,
                    s["missing_intervals"],
                    s["off_benchmark_dates"],
                ]
            )
            + "</tr>"
        )
    notes = "".join("<li>" + escape(v) + "</li>" for v in result["limitations"])
    sources = "".join(
        "<li>"
        + escape(
            s["instrument"]["ticker"]
            + " — "
            + s["source"]["provider"]
            + "; retrieved "
            + s["source"]["retrieved_at"]
        )
        + "</li>"
        for s in result["snapshots"]
    )
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Historical price data</title>
<style>body{{font:16px system-ui;max-width:1150px;margin:40px auto;padding:20px;color:#183044;background:#f5f8fb}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #ddd}}li{{margin:10px 0}}a{{color:#1268a0}}</style>
<h1>Historical price data</h1><p>Basis: <b>{escape(result["return_basis"])}</b> · Benchmark: {escape(result["benchmark_id"])} · Currency: {escape(result["currency"])} · Data: {escape(result["data_kind"])}</p>
<p>Requested period: {result["start"]} to {result["end_exclusive"]} (end excluded). Returns below use common benchmark endpoints; dates with missing prices are not filled.</p>
<table><tr><th>Instrument</th><th>First endpoint</th><th>Last endpoint</th><th>Observed dates</th><th>Endpoint return</th><th>Missing intervals</th><th>Off-calendar dates</th></tr>{rows}</table>
<h2>Downloads</h2><p><a href="prices.csv">Prices</a> · <a href="returns.csv">Returns</a> · <a href="corporate_actions.csv">Corporate actions</a> · <a href="summary.json">Audit summary</a></p>
<h2>Sources</h2><ul>{sources}</ul><h2>Interpretation</h2><ul>{notes}</ul>
<p>NIFTY 50 (^NSEI) is configured as a price index. Its comparison excludes dividends. Equity adjusted closes are stored separately for future total-return research.</p></html>"""
    (output / "report.html").write_text(html, encoding="utf-8")
    return output / "report.html"
