"""Compatibility namespace for the Tega/Molycop case study.

New code should import equity_analytics.case_studies.tega. Submodule aliases
preserve existing imports and module identity, including patched functions.
"""

import importlib
import sys

from equity_analytics.case_studies.tega import (
    AcquisitionInputError,
    build_acquisition_model,
)

for _name in (
    "consolidation", "currency", "drivers", "engine", "equity_bridge",
    "history", "legacy_statements", "reporting", "statements", "wacc",
):
    _module = importlib.import_module(f"equity_analytics.case_studies.tega.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

__all__ = ["AcquisitionInputError", "build_acquisition_model"]
