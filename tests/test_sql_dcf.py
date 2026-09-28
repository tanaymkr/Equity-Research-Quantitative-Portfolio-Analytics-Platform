"""Economic identities and SQL/config boundaries, independent expected values."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from equity_analytics.data import FinancialStore
from equity_analytics.valuation.dcf import (
    DCFAssumptions,
    HistoricalSnapshot,
    calculate_dcf,
)
from equity_analytics.valuation.sql_dcf import build_sql_dcf, capm_wacc, export_sql_dcf

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store(tmp_path):
    result = FinancialStore(tmp_path / "research.sqlite")
    for year in (2024, 2026):
        result.ingest_file(
            ROOT / f"examples/wabag_fy{year}_reported_statements.json",
            company_id="WABAG",
        )
    return result


def test_sql_history_is_used_and_bridge_is_scaled(store, tmp_path):
    p = export_sql_dcf(
        store, ROOT / "examples/wabag_dcf_assumptions.json", tmp_path / "reports"
    )
    r = p["scenarios"]["base"]["result"]
    assert r["forecast"][0]["revenue"] == pytest.approx(39442 * 1.175)
    assert r["cash"] == 7851
    assert r["debt"] == 2284
    assert r["equity_value"] == pytest.approx(
        r["enterprise_value"] + 7851 + 721 - 2284 - 52
    )
    assert r["implied_value_per_share"] == pytest.approx(r["equity_value"] / 63.150829)
    assert [a["fiscal_year"] for a in p["history"]["annuals"]] == [2024, 2025, 2026]
    assert (tmp_path / "reports/valuation.html").is_file()
    json.loads((tmp_path / "reports/valuation.json").read_text())
    assert (
        p["scenarios"]["downside"]["result"]["implied_value_per_share"]
        < r["implied_value_per_share"]
    )
    assert (
        p["scenarios"]["upside"]["result"]["implied_value_per_share"]
        > r["implied_value_per_share"]
    )
    assert p["sensitivity"][0.04][0.10] > p["sensitivity"][0.04][0.14]


def test_one_year_economic_identity():
    s = HistoricalSnapshot(
        "Example",
        2026,
        1000,
        100,
        200,
        10,
        opening_nwc=100,
        nonoperating_assets=30,
        minority_interest=20,
        other_claims=10,
    )
    a = DCFAssumptions(
        (0.1,), (0.2,), 0.25, 0.02, 0.03, 0.12, 0.1, 0.04, terminal_roic=0.2
    )
    r = calculate_dcf(s, a)
    # Revenue1100, NOPAT165, D&A22, capex33, closing NWC132, change32 => FCFF122.
    assert r.forecast[0].fcff == pytest.approx(122)
    assert r.terminal_fcff == pytest.approx(165 * 1.04 * 0.8)
    ev = 122 / 1.1 + (165 * 1.04 * 0.8 / 0.06) / 1.1
    assert r.enterprise_value == pytest.approx(ev)
    assert r.implied_value_per_share == pytest.approx(
        (ev + 100 + 30 - 200 - 20 - 10) / 10
    )
    legacy = calculate_dcf(s, replace(a, terminal_roic=None))
    assert legacy.terminal_fcff == pytest.approx(122 * 1.04)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("base_year", 2025, "base period"),
        ("financial_unit", "crore", "currency/unit"),
        ("ticker", "TEGA.NS", "ticker"),
        ("assumptions_available_on", "2027-01-01", "later"),
    ],
)
def test_mismatched_inputs_fail(store, tmp_path, field, value, reason):
    c = json.loads((ROOT / "examples/wabag_dcf_assumptions.json").read_text())
    c[field] = value
    path = tmp_path / "assumptions.json"
    path.write_text(json.dumps(c))
    with pytest.raises(ValueError, match=reason):
        build_sql_dcf(store, path)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True])
def test_nonfinite_inputs_fail(bad):
    with pytest.raises(ValueError):
        HistoricalSnapshot("Example", 2026, bad, 0, 0, 1)
    with pytest.raises(ValueError):
        DCFAssumptions((bad,), (0.1,), 0.25, 0.02, 0.03, 0.1, 0.1, 0.04)
    with pytest.raises(ValueError):
        DCFAssumptions((0.1,), (0.1,), 0.25, 0.02, 0.03, 0.1, 0.1, bad)


def test_capm_weights_tax_only_debt():
    x = capm_wacc(
        {
            "risk_free_rate": 0.06,
            "beta": 1.2,
            "equity_risk_premium": 0.05,
            "pretax_cost_of_debt": 0.08,
            "debt_weight": 0.25,
        },
        0.25,
    )
    assert x["cost_of_equity"] == pytest.approx(0.12)
    assert x["wacc"] == pytest.approx(0.12 * 0.75 + 0.08 * 0.75 * 0.25)


def test_terminal_reinvestment_validation():
    with pytest.raises(ValueError, match="ROIC"):
        DCFAssumptions(
            (0.1,), (0.2,), 0.25, 0.02, 0.03, 0.1, 0.1, 0.04, terminal_roic=0.03
        )
