"""SQLite storage for sourced annual statements and publication-date queries."""

from .store import DataStoreError, FinancialStore

__all__ = ["DataStoreError", "FinancialStore"]
