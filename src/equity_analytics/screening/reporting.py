"""Local HTML, CSV and audit JSON for the fundamental screener."""

import csv
import json
from html import escape
from pathlib import Path

from .engine import FRACTIONS, METRICS

META = [
    "position",
    "company_id",
    "company_name",
    "ticker",
    "fiscal_year",
    "period_end",
    "published_on",
    "age_days",
    "basis",
    "currency",
    "financial_unit",
    "passes",
    "source_id",
    "source_url",
]


def _csv_safe(value):
    # Preserve numeric negatives; protect spreadsheet readers from formula-like text.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _write_csv(path, rows):
    fields = (
        META
        + list(METRICS)
        + [m + "_zero_filled" for m in METRICS]
        + ["zero_fill_reasons", "failed_filters"]
    )
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = {k: row.get(k, "") for k in META}
            flat.update(row["values"])
            flat.update({m + "_zero_filled": m in row["zero_filled"] for m in METRICS})
            flat["zero_fill_reasons"] = json.dumps(row["zero_filled"], sort_keys=True)
            flat["failed_filters"] = "; ".join(row["failed_filters"])
            writer.writerow({k: _csv_safe(v) for k, v in flat.items()})


def _html_table(rows, columns):
    headings = (
        ["Position", "Company", "Period end", "Published", "Result"]
        + columns
        + ["Zero-filled fields"]
    )
    body = []
    for row in rows:
        cells = [
            str(row.get("position", "—")),
            escape(row["company_name"]),
            row["period_end"],
            row["published_on"],
            "Pass" if row["passes"] else escape("; ".join(row["failed_filters"])),
        ]
        for metric in columns:
            value = row["values"][metric]
            display = f"{value:.2%}" if metric in FRACTIONS else f"{value:,.2f}"
            if metric in row["zero_filled"]:
                display = f'<span class="filled" title="{escape(row["zero_filled"][metric], quote=True)}">{display}*</span>'
            cells.append(display)
        cells.append(escape(", ".join(row["zero_filled"]) or "None"))
        body.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    if not rows:
        body.append(
            f'<tr><td colspan="{len(headings)}">No companies in this table.</td></tr>'
        )
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f"<th>{escape(h.replace('_', ' '))}</th>" for h in headings)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def screener_html(result):
    c = result["configuration"]
    counts = result["counts"]
    direction = "ascending" if c["ascending"] else "descending"
    excluded = (
        "".join(
            f"<li>{escape(r['company_id'])}: {escape(r['reason'])}</li>"
            for r in result["excluded"]
        )
        or "<li>None</li>"
    )
    flags = []
    for row in result["rows"]:
        for metric, reason in row["zero_filled"].items():
            flags.append(
                f"<li>{escape(row['company_id'])} — {escape(metric)}: {escape(reason)}</li>"
            )
        for warning in row["warnings"]:
            flags.append(f"<li>{escape(row['company_id'])} — {escape(warning)}</li>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Fundamental stock screener</title>
<style>body{{font:15px/1.5 system-ui;color:#173451;background:#f3f6fa;margin:0}}
main{{max-width:1400px;margin:24px auto;padding:28px;background:white}}h1{{margin-bottom:8px}}
.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{padding:10px;border-bottom:1px solid #dce3eb;text-align:right;vertical-align:top}}
th{{background:#e9eff6}}td:nth-child(2){{text-align:left;min-width:150px}}
.filled{{color:#805200;font-weight:bold}}.notice{{background:#fff4d6;padding:14px}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere}}a{{color:#145fab}}h2{{margin-top:30px}}
@media(max-width:650px){{main{{margin:0;padding:16px}}}}</style></head><body><main>
<h1>Fundamental stock screener</h1>
<p>{counts["matched"]} matched / {counts["evaluated"]} evaluated; {counts["excluded"]} excluded.
Publication cutoff: {escape(c["as_of"])}. {escape(c["basis"])} statements.</p>
<p>Period: {escape(c["period_end"] or "latest available for each company")}; sort:
{escape(c["sort_by"])} ({direction}). Money in {escape(c["currency"])} million.
Percentages are displayed as %, exported as decimal fractions. Multiples are in x.</p>
<p class="notice">Missing/unavailable metrics count as zero for filters, sorting and exports.
An asterisk (*) marks substituted zeros. Source SQL values are preserved.</p>
<p><a href="screener.csv">Matched companies CSV</a> · <a href="all_companies.csv">All evaluated companies CSV</a> ·
<a href="screener.json">Audit JSON</a></p>
<h2>Matching companies</h2>{_html_table(result["matches"], c["columns"])}
<h2>All evaluated companies</h2>{_html_table(result["rows"], c["columns"])}
<h2>Zero substitutions and data notes</h2><ul>{"".join(flags) or "<li>None for this run.</li>"}</ul>
<h2>Excluded companies</h2><ul>{excluded}</ul>
<h2>Active configuration</h2><pre>{escape(json.dumps(c, indent=2))}</pre>
<p>Filters combine with AND; bounds are inclusive. Positions follow the selected metric,
with company ID breaking ties. This is a financial filter, not a recommendation or factor score.
CFO less capex is not automatically FCFF. Historical reported Tega figures predate the Molycop
acquisition; this screen does not use its pro-forma model. Company accounting definitions can differ.</p>
</main></body></html>"""


def export_screener(result, output, *, protected_paths=()):
    output = Path(output)
    targets = [
        output / n
        for n in ("screener.csv", "all_companies.csv", "screener.json", "screener.html")
    ]
    protected = {Path(p).resolve() for p in protected_paths}
    if any(p.resolve() in protected for p in targets):
        raise ValueError("Screener output must not overwrite input files")
    output.mkdir(parents=True, exist_ok=True)
    _write_csv(targets[0], result["matches"])
    _write_csv(targets[1], result["rows"])
    targets[2].write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    targets[3].write_text(screener_html(result), encoding="utf-8")
