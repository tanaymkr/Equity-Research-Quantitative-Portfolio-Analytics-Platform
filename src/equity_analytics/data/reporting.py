"""Readable local report for the financial history selected from SQL."""

from html import escape

from equity_analytics.financials.__main__ import format_metric


def analysis_html(report):
    h = report.history
    c = h.company
    headers = "".join(f"<th>FY{year.fiscal_year}</th>" for year in report.years)
    rows = []
    for metric in report.years[0].metrics:
        values = "".join(
            f"<td>{escape(format_metric(year.metrics[metric]))}</td>"
            for year in report.years
        )
        rows.append(f"<tr><th>{escape(metric.replace('_', ' '))}</th>{values}</tr>")
    publications = {s.source_id: s for s in h.sources}
    evidence = []
    for annual in h.annuals:
        source = publications[annual.source_id]
        title = escape(source.title)
        if source.url:
            title = f'<a href="{escape(source.url, quote=True)}">{title}</a>'
        evidence.append(
            f"<tr><td>FY{annual.fiscal_year}</td><td>{source.published_on}</td>"
            f"<td>{title}</td></tr>"
        )
    issues = []
    for year in report.years:
        for name, metric in year.metrics.items():
            if metric.reason:
                issues.append(f"FY{year.fiscal_year} {name}: {metric.reason}")
        issues.extend(f"FY{year.fiscal_year}: {w}" for w in year.warnings)
    details = "".join(f"<li>{escape(s)}</li>" for s in issues)
    notes = "".join(
        f"<li>FY{a.fiscal_year}: {escape(a.notes)}</li>" for a in h.annuals if a.notes
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(c.name)} financial analysis</title>
<style>
body{{font:16px/1.55 system-ui,sans-serif;color:#24364a;background:#f4f6f8;margin:0}}
main{{max-width:1050px;margin:32px auto;padding:32px;background:white}}
h1,h2{{color:#173451}} h1{{margin-bottom:8px}} h2{{margin-top:32px}}
table{{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px}}
th,td{{padding:10px 12px;border-bottom:1px solid #dfe5eb;text-align:right}}
th:first-child,td:first-child{{text-align:left}} thead{{background:#e9eef4}}
.scroll{{overflow-x:auto}} a{{color:#125eaa}} .meta{{color:#506174}}
li{{margin:6px 0}} @media(max-width:650px){{main{{margin:0;padding:18px}}}}
</style></head><body><main>
<p class="meta">Investment Research Platform · SQL financial data</p>
<h1>{escape(c.name)}</h1>
<p>{escape(c.ticker)} · {escape(c.statement_basis)} · {escape(c.data_kind)} data<br>
Money: {escape(c.currency)} {escape(c.financial_unit)}.
Publication cutoff: <strong>{h.as_of}</strong>, end of day.</p>
<p>{escape(h.notes)}</p>
<h2>Annual financial analysis</h2>
<div class="scroll"><table><thead><tr><th>Metric</th>{headers}</tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p>Revenue CAGR: {escape(format_metric(report.revenue_cagr))} over
{report.cagr_intervals} annual intervals. CFO less capex is not automatically FCFF.</p>
<h2>Selected filing versions</h2>
<div class="scroll"><table><thead><tr><th>Period</th><th>Published</th><th>Source</th>
</tr></thead><tbody>{"".join(evidence)}</tbody></table></div>
<h2>Missing values and checks</h2><ul>{details or "<li>No metric exceptions.</li>"}</ul>
<h2>Statement notes</h2><ul>{notes}</ul>
<p><a href="history.json">Selected financial inputs</a> ·
<a href="analysis.json">Calculated metrics</a> · <a href="analysis.md">Markdown report</a></p>
</main></body></html>"""
