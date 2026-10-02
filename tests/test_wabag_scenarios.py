"""Operating cases must recalculate statements and preserve user inputs."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from equity_analytics.case_studies.wabag import build_model, load_inputs
from equity_analytics.case_studies.wabag.scenarios import (
    build_scenarios,
    export_scenarios,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    return load_inputs(ROOT / "examples/wabag_linked")


@pytest.fixture
def config():
    return json.loads((ROOT / "examples/wabag_linked/scenarios.json").read_text())


def test_three_cases_are_linked_and_base_is_unchanged(inputs, config):
    before, original_config = deepcopy(inputs), deepcopy(config)
    single = build_model(inputs)
    result = build_scenarios(inputs, config)
    assert inputs == before and config == original_config
    assert result["scenarios"]["base"]["model"]["forecast"] == single["forecast"]
    assert result["scenarios"]["base"]["model"]["dcf"] == single["dcf"]
    values = []
    for name in ("downside", "base", "upside"):
        case = result["scenarios"][name]
        assert case["status"] == "ok"
        model = case["model"]
        assert len(model["checks"]) == 40
        assert all(c["passed"] for c in model["checks"])
        for row in model["forecast"]:
            assert row["balance_sheet"]["balance_residual"] == pytest.approx(
                0, abs=1e-6
            )
            assert row["valuation"]["fcff"] == pytest.approx(
                row["valuation"]["fcff_from_cfo"]
            )
        values.append(model["dcf"]["implied_value_per_share"])
    assert values[0] < values[1] < values[2]


def test_revenue_level_shocks_are_not_double_compounded(inputs, config):
    r = build_scenarios(inputs, config)["scenarios"]
    base, up = r["base"]["model"], r["upside"]["model"]
    for i, factor in enumerate([1.05, 1.08, 1.10, 1.12, 1.15]):
        assert up["forecast"][i]["income_statement"]["revenue"] == pytest.approx(
            base["forecast"][i]["income_statement"]["revenue"] * factor
        )
        assert up["forecast"][i]["resolved_drivers"]["ebitda_margin"] == pytest.approx(
            base["forecast"][i]["resolved_drivers"]["ebitda_margin"] + 0.01
        )
    assert up["assumptions"]["operating_balance_ratios"]["ar_current"][
        "value"
    ] == pytest.approx(
        base["assumptions"]["operating_balance_ratios"]["ar_current"]["value"]
        - 10 / 365
    )
    assert up["forecast"][0]["wacc"] == base["forecast"][0]["wacc"]
    assert (
        up["forecast"][0]["balance_sheet"]["cash"]
        != base["forecast"][0]["balance_sheet"]["cash"]
    )


def test_export_exposes_comparison_and_each_complete_case(inputs, config, tmp_path):
    r = build_scenarios(inputs, config)
    p = export_scenarios(r, tmp_path)
    main = p.read_text()
    assert "Wabag · Three operating cases" in main
    for name in ("base", "upside", "downside"):
        assert f'href="{name}/forecast.html"' in main
        html = (tmp_path / name / "forecast.html").read_text()
        assert f"VA Tech Wabag — {name.title()} case" in html
        assert (
            "Consolidated balance sheet" in html
            and "WACC and capital structure" in html
        )
        assert "../forecast.html" in html
        data = json.loads((tmp_path / name / "forecast.json").read_text())
        assert len(data["forecast"]) == 5
    assert set(json.loads((tmp_path / "forecast.json").read_text())["scenarios"]) == {
        "base",
        "upside",
        "downside",
    }


def test_infeasible_stress_does_not_reuse_a_stale_value(inputs, config, tmp_path):
    export_scenarios(build_scenarios(inputs, config), tmp_path)
    config["cases"]["downside"]["adjustments"]["receivable_days_change"] = 365
    r = build_scenarios(inputs, config)
    assert r["scenarios"]["downside"]["status"] == "failed"
    assert "funding shortfall" in r["scenarios"]["downside"]["error"]
    assert "model" not in r["scenarios"]["downside"]
    assert r["scenarios"]["base"]["status"] == "ok"
    export_scenarios(r, tmp_path)
    assert "Needs revision" in (tmp_path / "forecast.html").read_text()
    assert "Illustrative DCF" not in (tmp_path / "downside/forecast.html").read_text()
    assert "dcf" not in json.loads((tmp_path / "downside/forecast.json").read_text())


@pytest.mark.parametrize("change", ["base", "length", "nan", "unknown"])
def test_invalid_scenario_configuration_is_rejected(inputs, config, change):
    if change == "base":
        config["cases"]["base"]["adjustments"]["revenue_multiplier"][0] = 1.1
    elif change == "length":
        config["cases"]["upside"]["adjustments"]["ebitda_margin_change"].pop()
    elif change == "nan":
        config["cases"]["upside"]["adjustments"]["receivable_days_change"] = float(
            "nan"
        )
    else:
        config["cases"]["upside"]["adjustments"]["unlimited_borrowing"] = True
    with pytest.raises(ValueError):
        build_scenarios(inputs, config)
