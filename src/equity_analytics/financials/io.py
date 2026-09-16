"""Load a strict, normalized JSON input; no website scraping or credentials."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from equity_analytics.financials.models import (
    AnnualStatement,
    Company,
    FinancialDataError,
    FinancialHistory,
    SourceDocument,
)


def _iso_date(value: Any) -> date:
    if not isinstance(value, str):
        raise FinancialDataError("dates must be strings in YYYY-MM-DD format")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise FinancialDataError("dates must be in YYYY-MM-DD format") from exc
    if parsed.isoformat() != value:
        raise FinancialDataError("dates must be in YYYY-MM-DD format")
    return parsed


def history_from_dict(payload: dict[str, Any]) -> FinancialHistory:
    """Construct validated records, preserving missing fields as None.

    Unknown keys are errors so that a misspelt financial field is not ignored.
    Records are sorted by fiscal period in FinancialHistory.
    """
    if not isinstance(payload, dict):
        raise FinancialDataError("input must be a JSON object")
    expected = {"schema_version", "company", "as_of", "sources", "annuals", "notes"}
    unknown = payload.keys() - expected
    missing = (expected - {"notes"}) - payload.keys()
    if unknown or missing:
        raise FinancialDataError(
            f"invalid top-level keys: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise FinancialDataError("only schema_version 1 is supported")
    if not isinstance(payload["sources"], list) or not isinstance(
        payload["annuals"], list
    ):
        raise FinancialDataError("sources and annuals must be JSON arrays")
    try:
        company = Company(**payload["company"])
        sources = []
        for source in payload["sources"]:
            fields = dict(source)
            fields["published_on"] = _iso_date(fields["published_on"])
            sources.append(SourceDocument(**fields))
        annuals = []
        for annual in payload["annuals"]:
            fields = dict(annual)
            fields["period_end"] = _iso_date(fields["period_end"])
            annuals.append(AnnualStatement(**fields))
        return FinancialHistory(
            company=company,
            as_of=_iso_date(payload["as_of"]),
            sources=tuple(sources),
            annuals=tuple(annuals),
            notes=payload.get("notes", ""),
        )
    except FinancialDataError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise FinancialDataError(f"invalid financial input structure: {exc}") from exc


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise FinancialDataError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _invalid_constant(value: str) -> None:
    raise FinancialDataError(f"non-finite JSON number: {value}")


def load_history(path: str | Path) -> FinancialHistory:
    """Read UTF-8 (including BOM) JSON and validate it before calculation."""
    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_keys,
            parse_constant=_invalid_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinancialDataError(f"cannot read financial input: {exc}") from exc
    if isinstance(payload, dict) and "base_year" in payload:
        from equity_analytics.forecasting.history import financial_history_payload
        from equity_analytics.forecasting.inputs import ModelInputError

        try:
            payload = financial_history_payload(payload)
        except (ModelInputError, KeyError, TypeError) as exc:
            raise FinancialDataError(f"invalid reported statements: {exc}") from exc
    return history_from_dict(payload)
