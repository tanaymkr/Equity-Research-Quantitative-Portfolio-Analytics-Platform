from pathlib import Path

import pytest

from equity_analytics.data import DataStoreError, FinancialStore
from equity_analytics.data.comparison import comparison_html
from equity_analytics.financials.ratios import analyze_history

ROOT = Path(__file__).resolve().parents[1]


def test_wabag_reconciliation_and_publication(tmp_path):
    store = FinancialStore(tmp_path / 'research.sqlite')
    path = ROOT / 'examples/wabag_fy2026_reported_statements.json'
    assert store.ingest_file(path, company_id='WABAG')['inserted_statements'] == 2
    assert store.ingest_file(path, company_id='WABAG')['status'] == 'unchanged'
    with pytest.raises(DataStoreError):
        store.history_as_of('WABAG', '2026-07-19')
    history = store.history_as_of('WABAG', '2026-07-20')
    prior, latest = history.annuals
    assert latest.total_assets == latest.total_equity + latest.total_liabilities
    assert latest.total_debt == 1534 + 721 + 23 + 6
    assert prior.total_debt == 1758 + 1815 + 28 + 16
    assert latest.ebit == 39442 - 30006 - 32 - 3004 - 62 - 1626
    assert prior.ebit == 32940 - 25598 - 7 - 2645 - 59 - 467
    assert latest.net_income_to_owners - 7 == latest.net_income
    assert latest.operating_cash_flow - latest.capex == 2015
    assert not any(y.warnings for y in analyze_history(history).years)


def test_comparison_uses_reported_common_period(tmp_path):
    store = FinancialStore(tmp_path / 'research.sqlite')
    for cid, name in [('WABAG', 'wabag_fy2026_reported_statements.json'),
                      ('TEGA', 'tega_fy2026_reported_statements.json'),
                      ('DEMO', 'demo_financial_history.json')]:
        store.ingest_file(ROOT / 'examples' / name, company_id=cid)
    html = comparison_html(store, ['TEGA', 'WABAG'], '2026-09-11')
    assert '2026-03-31' in html
    assert 'VA Tech Wabag Limited' in html
    assert 'INR million' in html
    with pytest.raises(DataStoreError, match='reported'):
        comparison_html(store, ['TEGA', 'DEMO'], '2026-09-11')
    with pytest.raises(DataStoreError, match='distinct'):
        comparison_html(store, ['WABAG', 'WABAG'], '2026-09-11')
