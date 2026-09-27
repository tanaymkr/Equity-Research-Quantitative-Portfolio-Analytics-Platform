"""Compatibility alias for the relocated Tega case-study module."""

import sys
from importlib import import_module

sys.modules[__name__] = import_module(
    "equity_analytics.case_studies.tega.wacc"
)
