"""Guard company identity and the supported migration entry points."""

import importlib
import json
from pathlib import Path

import pytest

from equity_analytics.case_studies.tega.financial_history import (
    financial_history_payload,
)
from equity_analytics.financials.io import load_history
from equity_analytics.financials.models import FinancialDataError
from equity_analytics.forecasting.inputs import ModelInputError

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module", [
    "engine", "history", "consolidation", "currency", "drivers",
    "equity_bridge", "legacy_statements", "reporting", "statements", "wacc",
])
def test_legacy_module_is_the_same_implementation(module):
    old = importlib.import_module(f"equity_analytics.acquisition.{module}")
    new = importlib.import_module(f"equity_analytics.case_studies.tega.{module}")
    assert old is new


def test_tega_adapter_does_not_relabel_another_company(tmp_path):
    payload = json.loads(
        (ROOT / "examples/tega_fy2026_reported_statements.json").read_text()
    )
    payload["company"] = "Another Industrial Company"
    with pytest.raises(ModelInputError, match="Tega Industries Limited only"):
        financial_history_payload(payload)
    path = tmp_path / "other_company.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(FinancialDataError, match="normalized financial-history"):
        load_history(path)


def test_normalized_history_keeps_its_own_company_identity():
    path = ROOT / "examples/demo_financial_history.json"
    raw = json.loads(path.read_text())
    history = load_history(path)
    assert history.company.ticker == raw["company"]["ticker"]
    assert history.company.name == raw["company"]["name"]
