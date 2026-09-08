"""Historical financial-statement ingestion and ratio analysis."""

from equity_analytics.financials.io import history_from_dict, load_history
from equity_analytics.financials.models import (
    AnnualStatement,
    Company,
    FinancialDataError,
    FinancialHistory,
    SourceDocument,
)
from equity_analytics.financials.ratios import AnalysisReport, analyze_history

__all__ = [
    "AnalysisReport",
    "AnnualStatement",
    "Company",
    "FinancialDataError",
    "FinancialHistory",
    "SourceDocument",
    "analyze_history",
    "history_from_dict",
    "load_history",
]
