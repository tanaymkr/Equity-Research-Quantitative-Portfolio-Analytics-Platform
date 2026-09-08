"""Validated data contracts for one company's annual financial history.

All money fields in a history share its declared currency, unit and statement
basis. Losses and negative equity are valid; missing values remain None.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
from math import isfinite
from urllib.parse import urlparse


class FinancialDataError(ValueError):
    """An input cannot safely be used for annual financial analysis."""


def require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise FinancialDataError(f"{name} must be non-empty text")


@dataclass(frozen=True)
class Company:
    name: str
    ticker: str
    currency: str
    financial_unit: str
    statement_basis: str
    data_kind: str

    def __post_init__(self) -> None:
        for field in fields(self):
            require_text(field.name, getattr(self, field.name))
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise FinancialDataError("currency must be a three-letter code")
        if self.currency != self.currency.upper():
            raise FinancialDataError("currency must be uppercase, e.g. INR")
        if self.financial_unit not in {"units", "million", "crore"}:
            raise FinancialDataError("financial_unit must be units, million or crore")
        if self.statement_basis not in {"consolidated", "standalone"}:
            raise FinancialDataError(
                "statement_basis must be consolidated or standalone"
            )
        if self.data_kind not in {"synthetic", "reported"}:
            raise FinancialDataError("data_kind must be synthetic or reported")


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    title: str
    published_on: date
    locator: str
    url: str | None = None

    def __post_init__(self) -> None:
        for name in ("source_id", "title", "locator"):
            require_text(name, getattr(self, name))
        if type(self.published_on) is not date:
            raise FinancialDataError("published_on must be a date")
        if self.url is not None:
            require_text("url", self.url)
            parsed = urlparse(self.url)
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                raise FinancialDataError("source URL must be an http(s) URL")


@dataclass(frozen=True)
class AnnualStatement:
    fiscal_year: int
    period_end: date
    source_id: str
    revenue: float
    months: int = 12
    ebit: float | None = None
    depreciation_amortisation: float | None = None
    net_income: float | None = None
    net_income_to_owners: float | None = None
    finance_costs: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    equity_to_owners: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    cash_and_equivalents: float | None = None
    total_debt: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if type(self.fiscal_year) is not int or not 1900 <= self.fiscal_year <= 9999:
            raise FinancialDataError("fiscal_year must be an integer from 1900 to 9999")
        if type(self.period_end) is not date:
            raise FinancialDataError("period_end must be a date")
        if self.period_end.year != self.fiscal_year:
            raise FinancialDataError(
                "fiscal_year must be the calendar year of period_end"
            )
        if type(self.months) is not int or self.months != 12:
            raise FinancialDataError("only 12-month annual statements are supported")
        require_text("source_id", self.source_id)
        if not isinstance(self.notes, str):
            raise FinancialDataError("notes must be text")
        nonnegative = {
            "revenue",
            "depreciation_amortisation",
            "finance_costs",
            "total_assets",
            "total_liabilities",
            "current_assets",
            "current_liabilities",
            "cash_and_equivalents",
            "total_debt",
            "capex",
        }
        for name in NUMERIC_FIELDS:
            value = getattr(self, name)
            if value is None:
                if name == "revenue":
                    raise FinancialDataError("revenue is required; zero is allowed")
                continue
            if type(value) not in (int, float):
                raise FinancialDataError(f"{name} must be a number or null")
            try:
                finite = isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise FinancialDataError(f"{name} must be finite")
            if name in nonnegative and value < 0:
                raise FinancialDataError(f"{name} must be non-negative")
            object.__setattr__(self, name, float(value))


NUMERIC_FIELDS = tuple(
    field.name
    for field in fields(AnnualStatement)
    if field.name not in {"fiscal_year", "period_end", "source_id", "months", "notes"}
)


@dataclass(frozen=True)
class FinancialHistory:
    company: Company
    as_of: date
    sources: tuple[SourceDocument, ...]
    annuals: tuple[AnnualStatement, ...]
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.company, Company) or type(self.as_of) is not date:
            raise FinancialDataError("company and as_of must use their declared types")
        if not isinstance(self.notes, str):
            raise FinancialDataError("history notes must be text")
        if not self.annuals or not self.sources:
            raise FinancialDataError(
                "at least one annual statement and source are required"
            )
        if not all(isinstance(s, SourceDocument) for s in self.sources):
            raise FinancialDataError("sources must contain SourceDocument objects")
        if not all(isinstance(a, AnnualStatement) for a in self.annuals):
            raise FinancialDataError("annuals must contain AnnualStatement objects")
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(
            self,
            "annuals",
            tuple(sorted(self.annuals, key=lambda annual: annual.period_end)),
        )
        by_source = {source.source_id: source for source in self.sources}
        if len(by_source) != len(self.sources):
            raise FinancialDataError("duplicate source_id")
        if len({a.fiscal_year for a in self.annuals}) != len(self.annuals):
            raise FinancialDataError("duplicate fiscal_year")
        if len({(a.period_end.month, a.period_end.day) for a in self.annuals}) != 1:
            raise FinancialDataError(
                "fiscal year-end must be consistent within a history"
            )
        for source in self.sources:
            if source.published_on > self.as_of:
                raise FinancialDataError("source publication is after as_of")
            if self.company.data_kind == "reported" and source.url is None:
                raise FinancialDataError("reported data requires a source URL")
        for annual in self.annuals:
            if annual.source_id not in by_source:
                raise FinancialDataError(f"unknown source_id: {annual.source_id}")
            if annual.period_end > by_source[annual.source_id].published_on:
                raise FinancialDataError("annual period ends after source publication")
