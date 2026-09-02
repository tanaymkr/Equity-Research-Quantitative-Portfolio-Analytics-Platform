"""Core analytics for the equity research and portfolio platform."""

from equity_analytics.valuation.dcf import (
    DCFAssumptions,
    DCFResult,
    HistoricalSnapshot,
    calculate_dcf,
)

__all__ = [
    "DCFAssumptions",
    "DCFResult",
    "HistoricalSnapshot",
    "calculate_dcf",
]

__version__ = "0.1.0"

