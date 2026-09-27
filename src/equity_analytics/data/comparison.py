"""Compare explicitly selected reported companies at a common fiscal period."""

from html import escape

from equity_analytics.financials.__main__ import format_metric
from equity_analytics.financials.ratios import analyze_history

from .store import DataStoreError


def comparison_html(store, company_ids, as_of):
    ids = list(dict.fromkeys(company_ids))
    if len(ids) < 2:
        raise DataStoreError("Select at least two distinct companies")
    reports = [analyze_history(store.history_as_of(cid, as_of)) for cid in ids]
    companies = [r.history.company for r in reports]
    if any(c.data_kind != "reported" for c in companies):
        raise DataStoreError("Comparison requires reported company data")
    if len({(c.currency, c.financial_unit, c.statement_basis) for c in companies}) != 1:
        raise DataStoreError("Comparison requires matching currency, unit and basis")
    periods = [{a.period_end for a in r.history.annuals} for r in reports]
    common = set.intersection(*periods)
    if not common:
        raise DataStoreError("Companies have no common annual period")
    end = max(common)
    selected = []
    evidence = []
    for report in reports:
        annual = next(a for a in report.history.annuals if a.period_end == end)
        selected.append(next(y for y in report.years if y.fiscal_year == annual.fiscal_year))
        source = next(s for s in report.history.sources if s.source_id == annual.source_id)
        evidence.append(f"<li>{escape(report.history.company.name)}: "
                        f"{escape(source.title)}; publication {source.published_on}; "
                        f"{escape(source.locator)}</li>")
    rows = []
    for key in selected[0].metrics:
        cells = ''.join(f'<td>{escape(format_metric(y.metrics[key]))}</td>' for y in selected)
        rows.append(f'<tr><th>{escape(key.replace("_", " "))}</th>{cells}</tr>')
    headers = ''.join(f'<th>{escape(c.name)}</th>' for c in companies)
    c = companies[0]
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Company comparison</title><style>
body{{font:16px/1.5 system-ui;margin:32px;color:#173451}}main{{max-width:1100px;margin:auto}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;border-bottom:1px solid #ddd;text-align:right}}
th:first-child{{text-align:left}}.scroll{{overflow-x:auto}}</style><main>
<h1>Reported financial comparison</h1><p>Period ending {end}; publication cutoff {escape(str(as_of))}.
{escape(c.statement_basis)}; money in {escape(c.currency)} {escape(c.financial_unit)}.</p>
<p>Common financial metrics, not a valuation peer group. Different business models and accounting
classifications limit comparability. Operating EBIT follows each dataset's documented mapping.
CFO less capex is not automatically FCFF. N/A means unavailable, not zero.</p>
<div class="scroll"><table><tr><th>Metric</th>{headers}</tr>{''.join(rows)}</table></div>
<h2>Sources</h2><ul>{''.join(evidence)}</ul></main></html>'''
