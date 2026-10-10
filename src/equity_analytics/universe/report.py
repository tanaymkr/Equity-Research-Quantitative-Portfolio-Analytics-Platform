"""CSV, JSON and HTML outputs for a universe membership result."""

import csv
import json
from collections import Counter
from html import escape
from pathlib import Path

COLUMNS = ("company_id", "symbol", "name", "industry", "template", "series", "isin")


def _safe(value):
    # Stop spreadsheet apps treating text such as "-X" or "=X" as a formula.
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_report(membership, changes, config, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    members = membership["members"]
    with (output / "members.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for m in members:
            w.writerow({k: _safe(m[k]) for k in COLUMNS})
    industries = Counter(m["industry"] for m in members)
    templates = Counter(m["template"] for m in members)
    summary = {
        "universe_id": membership["universe_id"],
        "as_of": membership["as_of"],
        "snapshot": membership["snapshot"],
        "survivorship_biased": membership["survivorship_biased"],
        "list_age_days": membership["list_age_days"],
        "warnings": membership["warnings"],
        "member_count": len(members),
        "industries": dict(sorted(industries.items())),
        "templates": dict(sorted(templates.items())),
        "changes": changes,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    (output / "market_config.json").write_text(
        json.dumps(config, indent=2, allow_nan=False), encoding="utf-8"
    )
    snap = membership["snapshot"]

    def table(head, rows):
        h = "".join(f"<th>{escape(str(c))}</th>" for c in head)
        b = "".join(
            "<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>"
            for r in rows
        )
        return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"

    warnings = "".join(f"<li>{escape(w)}</li>" for w in membership["warnings"])
    change_rows = [
        (
            c["from"],
            c["to"],
            ", ".join(c["added"]) or "-",
            ", ".join(c["removed"]) or "-",
            ", ".join(c["isin_changed"]) or "-",
        )
        for c in changes
    ]
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(membership["universe_id"])} universe</title>
<style>
body{{font:14px/1.5 system-ui,sans-serif;margin:24px;color:#1d2433;background:#fff}}
table{{border-collapse:collapse;margin:8px 0 24px}}
th,td{{border:1px solid #d5d9e0;padding:4px 8px;text-align:left}}
th{{background:#f2f4f7}} .warn{{background:#fff6e5;border:1px solid #f0c36d;
padding:8px 16px}} .ok{{color:#2e7d32}}
</style></head><body>
<h1>{escape(membership["universe_id"])} membership as of {
        escape(membership["as_of"])
    }</h1>
<p>List effective <b>{escape(snap["effective_on"])}</b>, retrieved
{escape(snap["retrieved_at"])} from {escape(snap["source_url"])}.
{len(members)} members. SHA-256 {escape(snap["sha256"][:16])}&hellip;</p>
{
        f'<div class="warn"><b>Warnings</b><ul>{warnings}</ul></div>'
        if warnings
        else '<p class="ok">No survivorship, staleness or classification warnings.</p>'
    }
<h2>Statement templates</h2>
<p><i>financials</i> = banks, NBFCs and insurers, which need balance-sheet models
rather than FCFF/EBITDA metrics.</p>
{table(("Template", "Companies"), sorted(templates.items()))}
<h2>Industries</h2>
{table(("NSE industry", "Companies"), sorted(industries.items()))}
<h2>Changes between stored lists</h2>
{
        table(("From", "To", "Added", "Removed", "ISIN changed"), change_rows)
        if change_rows
        else "<p>Only one list stored; no changes to compare.</p>"
    }
<h2>Members</h2>
{table(COLUMNS, [[m[k] for k in COLUMNS] for m in members])}
</body></html>"""
    path = output / "report.html"
    path.write_text(html, encoding="utf-8")
    return path
