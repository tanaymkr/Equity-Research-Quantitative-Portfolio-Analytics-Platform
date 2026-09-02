"""Sensitivity analysis for the discounted cash flow model."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from equity_analytics.valuation.dcf import (
    DCFAssumptions,
    HistoricalSnapshot,
    calculate_dcf,
)


def sensitivity_matrix(
    snapshot: HistoricalSnapshot,
    assumptions: DCFAssumptions,
    *,
    wacc_values: Sequence[float],
    terminal_growth_values: Sequence[float],
) -> dict[float, dict[float, float | None]]:
    """Return implied share values for WACC/terminal-growth combinations.

    Invalid cells where terminal growth is greater than or equal to WACC are
    represented by ``None`` rather than silently applying an invalid formula.
    """

    matrix: dict[float, dict[float, float | None]] = {}
    for terminal_growth in terminal_growth_values:
        row: dict[float, float | None] = {}
        for wacc in wacc_values:
            if terminal_growth >= wacc:
                row[wacc] = None
                continue
            scenario = replace(
                assumptions,
                wacc=wacc,
                terminal_growth=terminal_growth,
            )
            row[wacc] = calculate_dcf(snapshot, scenario).implied_value_per_share
        matrix[terminal_growth] = row
    return matrix
