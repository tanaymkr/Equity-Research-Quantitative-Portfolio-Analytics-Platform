"""Validate inputs before calculation; surface differences instead of plugging them."""

from __future__ import annotations

import json
from datetime import date
from math import isfinite
from pathlib import Path


class ModelInputError(ValueError):
    """An input is invalid, incomplete, or fails an accounting reconciliation."""


ASSETS = {
    "ppe",
    "rou_assets",
    "cwip",
    "investment_property",
    "goodwill",
    "intangibles",
    "intangibles_under_development",
    "joint_venture",
    "other_noncurrent_financial_assets",
    "noncurrent_tax_assets",
    "deferred_tax_assets",
    "other_noncurrent_assets",
    "inventories",
    "current_investments",
    "receivables",
    "cash",
    "other_bank_balances",
    "current_loans",
    "other_current_financial_assets",
    "contract_assets",
    "current_tax_assets",
    "other_current_assets",
}
LIABILITIES = {
    "term_debt",
    "revolver",
    "leases",
    "other_noncurrent_financial_liabilities",
    "noncurrent_provisions",
    "deferred_tax_liabilities",
    "payables",
    "other_current_financial_liabilities",
    "current_provisions",
    "current_tax_liabilities",
    "other_current_liabilities",
}
EQUITY = {
    "share_capital",
    "retained_earnings",
    "other_reserves",
    "noncontrolling_interest",
}
INCOME = {
    "revenue",
    "other_income",
    "materials",
    "inventory_change_expense",
    "employee_expense",
    "other_expense",
    "finance_cost",
    "depreciation_amortisation",
    "joint_venture_profit",
    "profit_before_tax",
    "current_tax",
    "deferred_tax",
    "net_income",
    "other_comprehensive_income",
    "operating_ebitda",
    "operating_ebit",
}
TOTALS = {
    "assets",
    "liabilities",
    "equity",
    "current_assets",
    "current_liabilities",
    "noncurrent_borrowings",
    "current_borrowings",
    "current_term_maturities",
    "noncurrent_leases",
    "current_leases",
    "shares_outstanding_million",
    "accrued_term_interest",
    "accrued_short_term_interest",
}
SERIES = {
    "revenue_growth",
    "ebitda_margin",
    "receivable_days",
    "inventory_pct_revenue",
    "payables_pct_revenue",
    "cash_capex_pct_revenue",
    "term_principal_repayment",
    "lease_principal_repayment",
    "new_lease_assets",
}
RATES = {
    "term_interest_rate",
    "revolver_interest_rate",
    "lease_interest_rate",
    "tax_rate",
    "dividend_payout_ratio",
    "tangible_capex_share",
    "commissioning_fraction",
}
SCALARS = {
    "minimum_cash",
    "revolver_limit",
    "new_ppe_life_years",
    "new_intangible_life_years",
    "new_rou_life_years",
    "joint_venture_profit",
    "joint_venture_dividend",
}
DCF_KEYS = {
    "wacc",
    "terminal_growth",
    "terminal_roic",
    "joint_venture_value",
    "investment_property_value",
    "noncontrolling_interest_value",
}
ROUNDING_TOLERANCE = 0.02  # Source amounts are rounded to INR 0.01 million.


def keys(obj: object, required: set[str], name: str) -> None:
    if not isinstance(obj, dict) or obj.keys() != required:
        actual = set(obj) if isinstance(obj, dict) else set()
        raise ModelInputError(
            f"{name}: missing={sorted(required - actual)}, "
            f"unknown={sorted(actual - required)}"
        )


def number(
    value: object, name: str, low: float | None = None, high: float | None = None
) -> float:
    if type(value) not in (int, float) or not isfinite(value):
        raise ModelInputError(f"{name}: expected a finite number")
    if (low is not None and value < low) or (high is not None and value > high):
        raise ModelInputError(f"{name}: outside permitted range [{low}, {high}]")
    return float(value)


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ModelInputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ModelInputError(f"non-finite JSON constant: {value}")


def load_json(path: str | Path) -> dict:
    try:
        result = json.loads(
            Path(path).read_text(encoding="utf-8-sig"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModelInputError(f"cannot load {path}: {exc}") from exc
    if not isinstance(result, dict):
        raise ModelInputError("input must be a JSON object")
    return result


def _dates(value: object, name: str) -> date:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except (TypeError, ValueError) as exc:
        raise ModelInputError(f"{name}: expected YYYY-MM-DD") from exc


def _numeric_map(
    obj: dict, required: set[str], name: str, nonnegative: bool = False
) -> None:
    keys(obj, required, name)
    for key, value in obj.items():
        number(value, f"{name}.{key}", 0 if nonnegative else None)


def reconcile_history(case: dict) -> list[dict]:
    """Return all audit residuals, including rounding; reject failed checks."""
    keys(
        case,
        {
            "schema_version",
            "company",
            "currency",
            "financial_unit",
            "statement_basis",
            "data_kind",
            "as_of",
            "base_year",
            "source",
            "notes",
            "annuals",
            "fy2025_reconciliations",
            "fy2025_asset_cohorts",
        },
        "case",
    )
    if type(case["schema_version"]) is not int or case["schema_version"] != 1:
        raise ModelInputError("only schema_version 1 is supported")
    if (
        case["currency"],
        case["financial_unit"],
        case["statement_basis"],
        case["data_kind"],
        case["base_year"],
    ) != ("INR", "million", "consolidated", "reported", 2025):
        raise ModelInputError("this case schema requires reported FY2025 INR million")
    source = case["source"]
    keys(
        source,
        {"title", "url", "published_on", "audit_report_date", "locators"},
        "source",
    )
    if not isinstance(source["url"], str) or not source["url"].startswith("https://"):
        raise ModelInputError("reported data requires an HTTPS source URL")
    published = _dates(source["published_on"], "published_on")
    if not (
        _dates(source["audit_report_date"], "audit_report_date")
        <= published
        <= _dates(case["as_of"], "as_of")
    ):
        raise ModelInputError("source dates are inconsistent with as_of")
    if not isinstance(case["annuals"], list) or len(case["annuals"]) != 2:
        raise ModelInputError("this historical case requires FY2024 and FY2025")
    checks = []

    def check(name: str, calculated: float, reported: float) -> None:
        residual = calculated - reported
        checks.append(
            {
                "name": name,
                "calculated": calculated,
                "reported": reported,
                "residual": residual,
                "passed": abs(residual) <= ROUNDING_TOLERANCE + 1e-8,
            }
        )

    for year, row in zip([2024, 2025], case["annuals"], strict=True):
        keys(
            row,
            {
                "fiscal_year",
                "period_end",
                "assets",
                "liabilities",
                "equity",
                "income",
                "cash_flow",
                "reported_totals",
            },
            f"FY{year}",
        )
        if type(row["fiscal_year"]) is not int or row["fiscal_year"] != year:
            raise ModelInputError("annuals must be ordered FY2024, FY2025")
        if (
            row["period_end"] != f"{year}-03-31"
            or _dates(row["period_end"], "period_end") > published
        ):
            raise ModelInputError("invalid fiscal period/source date")
        for section, names in [
            ("assets", ASSETS),
            ("liabilities", LIABILITIES),
            ("equity", EQUITY),
            ("income", INCOME),
            ("reported_totals", TOTALS),
        ]:
            _numeric_map(
                row[section],
                names,
                section,
                section in {"assets", "liabilities", "reported_totals"},
            )
        a, l, inc, cf, total = [
            row[k]
            for k in ["assets", "liabilities", "income", "cash_flow", "reported_totals"]
        ]
        if inc["revenue"] <= 0 or total["shares_outstanding_million"] <= 0:
            raise ModelInputError("revenue and shares must be positive")
        for section in ["assets", "liabilities", "equity"]:
            check(
                f"FY{year} {section} total", sum(row[section].values()), total[section]
            )
        check(
            f"FY{year} balance sheet",
            total["assets"],
            total["liabilities"] + total["equity"],
        )
        check(
            f"FY{year} borrowing pools",
            l["term_debt"] + l["revolver"],
            total["noncurrent_borrowings"] + total["current_borrowings"],
        )
        check(
            f"FY{year} term current maturities",
            l["term_debt"],
            total["noncurrent_borrowings"] + total["current_term_maturities"],
        )
        check(
            f"FY{year} lease pool",
            l["leases"],
            total["noncurrent_leases"] + total["current_leases"],
        )
        check(
            f"FY{year} operating EBITDA",
            inc["revenue"]
            - inc["materials"]
            - inc["inventory_change_expense"]
            - inc["employee_expense"]
            - inc["other_expense"],
            inc["operating_ebitda"],
        )
        check(
            f"FY{year} operating EBIT",
            inc["operating_ebitda"] - inc["depreciation_amortisation"],
            inc["operating_ebit"],
        )
        check(
            f"FY{year} profit before tax",
            inc["operating_ebit"]
            + inc["other_income"]
            + inc["joint_venture_profit"]
            - inc["finance_cost"],
            inc["profit_before_tax"],
        )
        check(
            f"FY{year} net income",
            inc["profit_before_tax"] - inc["current_tax"] - inc["deferred_tax"],
            inc["net_income"],
        )
        keys(
            cf,
            {
                "operating_adjustments",
                "working_capital_movements",
                "income_tax_paid",
                "investing",
                "financing",
                "operating_total",
                "investing_total",
                "financing_total",
                "opening_cash",
                "exchange_effect_on_cash",
                "closing_cash",
            },
            "cash_flow",
        )
        for name, value in cf.items():
            if isinstance(value, dict):
                if not value:
                    raise ModelInputError(f"empty cash flow section: {name}")
                for label, amount in value.items():
                    number(amount, f"cash_flow.{name}.{label}")
            else:
                number(value, f"cash_flow.{name}")
        check(
            f"FY{year} operating cash flow",
            inc["profit_before_tax"]
            + sum(cf["operating_adjustments"].values())
            + sum(cf["working_capital_movements"].values())
            + cf["income_tax_paid"],
            cf["operating_total"],
        )
        for category in ["investing", "financing"]:
            check(
                f"FY{year} {category} cash flow",
                sum(cf[category].values()),
                cf[f"{category}_total"],
            )
        check(
            f"FY{year} cash roll",
            cf["opening_cash"]
            + cf["operating_total"]
            + cf["investing_total"]
            + cf["financing_total"]
            + cf["exchange_effect_on_cash"],
            cf["closing_cash"],
        )
        check(f"FY{year} cash to balance sheet", cf["closing_cash"], a["cash"])
    check(
        "FY2025 opening cash",
        case["annuals"][1]["cash_flow"]["opening_cash"],
        case["annuals"][0]["assets"]["cash"],
    )
    rolls = case["fy2025_reconciliations"]
    expected_rolls = {
        "term_debt_including_accrued_interest",
        "short_term_debt_including_accrued_interest",
        "lease_liability",
        "ppe_net",
        "rou_net",
        "intangibles_net",
        "cwip",
        "intangibles_under_development",
        "equity",
    }
    keys(rolls, expected_rolls, "fy2025_reconciliations")
    for name, row in rolls.items():
        if not isinstance(row, dict) or not {"opening", "closing"} <= row.keys():
            raise ModelInputError(f"{name}: missing opening/closing")
        for field, value in row.items():
            number(value, f"{name}.{field}")
        check(
            f"FY2025 {name} roll",
            sum(v for k, v in row.items() if k != "closing"),
            row["closing"],
        )
    links = {
        "lease_liability": ("liabilities", "leases"),
        "ppe_net": ("assets", "ppe"),
        "rou_net": ("assets", "rou_assets"),
        "intangibles_net": ("assets", "intangibles"),
        "cwip": ("assets", "cwip"),
        "intangibles_under_development": ("assets", "intangibles_under_development"),
        "equity": ("reported_totals", "equity"),
    }
    for roll_name, (section, field) in links.items():
        for index, endpoint in [(0, "opening"), (1, "closing")]:
            check(
                f"FY2025 {roll_name} {endpoint} to statement",
                rolls[roll_name][endpoint],
                case["annuals"][index][section][field],
            )
    for roll_name, pool, accrued in [
        ("term_debt_including_accrued_interest", "term_debt", "accrued_term_interest"),
        (
            "short_term_debt_including_accrued_interest",
            "revolver",
            "accrued_short_term_interest",
        ),
    ]:
        for index, endpoint in [(0, "opening"), (1, "closing")]:
            row = case["annuals"][index]
            check(
                f"FY2025 {roll_name} {endpoint} to statement",
                rolls[roll_name][endpoint],
                row["liabilities"][pool] + row["reported_totals"][accrued],
            )
    check(
        "FY2025 D&A notes to income statement",
        -rolls["ppe_net"]["depreciation"]
        - rolls["rou_net"]["depreciation"]
        - rolls["intangibles_net"]["amortisation"],
        case["annuals"][1]["income"]["depreciation_amortisation"],
    )
    names = set()
    cohort_totals = {"ppe": 0.0, "rou_assets": 0.0, "intangibles": 0.0}
    if not isinstance(case["fy2025_asset_cohorts"], list):
        raise ModelInputError("asset cohorts must be a list")
    for row in case["fy2025_asset_cohorts"]:
        keys(row, {"name", "account", "net_book_value"}, "asset cohort")
        if row["name"] in names or row["account"] not in cohort_totals:
            raise ModelInputError("duplicate asset cohort or invalid account")
        names.add(row["name"])
        cohort_totals[row["account"]] += number(row["net_book_value"], "book value", 0)
    for account, value in cohort_totals.items():
        check(
            f"FY2025 opening cohort {account}",
            value,
            case["annuals"][-1]["assets"][account],
        )
    failed = [c for c in checks if not c["passed"]]
    if failed:
        raise ModelInputError(
            "historical reconciliation failed: "
            + "; ".join(f"{c['name']} residual={c['residual']:.6f}" for c in failed)
        )
    return checks


def validate_assumptions(a: dict, case: dict) -> int:
    keys(
        a,
        SERIES
        | RATES
        | SCALARS
        | {
            "schema_version",
            "label",
            "base_year",
            "notes",
            "dcf",
            "opening_remaining_life_years",
            "sweep_excess_cash_to_revolver",
        },
        "assumptions",
    )
    if type(a["schema_version"]) is not int or a["schema_version"] != 1:
        raise ModelInputError("assumption schema_version must be 1")
    if type(a["base_year"]) is not int or a["base_year"] != case["base_year"]:
        raise ModelInputError("assumption base year differs from reported history")
    if not isinstance(a["revenue_growth"], list):
        raise ModelInputError("revenue_growth must be an array")
    horizon = len(a["revenue_growth"])
    if not 1 <= horizon <= 10:
        raise ModelInputError("forecast must cover one to ten years")
    for name in SERIES:
        if not isinstance(a[name], list) or len(a[name]) != horizon:
            raise ModelInputError(f"{name}: must contain {horizon} annual values")
        for value in a[name]:
            number(
                value,
                name,
                -0.99
                if name == "revenue_growth"
                else -1
                if name == "ebitda_margin"
                else 0,
            )
            if name.endswith("pct_revenue"):
                number(value, name, 0, 2)
            elif name == "ebitda_margin":
                number(value, name, -1, 1)
            elif name == "receivable_days":
                number(value, name, 0, 730)
    for name in RATES:
        number(a[name], name, 0, 1)
    for name in SCALARS:
        number(a[name], name, None if name == "joint_venture_profit" else 0)
        if name.endswith("life_years"):
            number(a[name], name, 1)
    if type(a["sweep_excess_cash_to_revolver"]) is not bool:
        raise ModelInputError("cash sweep switch must be true or false")
    if a["revolver_limit"] < case["annuals"][-1]["liabilities"]["revolver"]:
        raise ModelInputError("revolver limit is below the opening balance")
    lives = a["opening_remaining_life_years"]
    keys(lives, {r["name"] for r in case["fy2025_asset_cohorts"]}, "remaining lives")
    for name, life in lives.items():
        if name == "ppe_land":
            if life is not None:
                raise ModelInputError("owned land must have null remaining life")
        else:
            number(life, f"remaining life {name}", 1)
    keys(a["dcf"], DCF_KEYS, "dcf")
    for name, value in a["dcf"].items():
        number(value, f"dcf.{name}", 0)
    d = a["dcf"]
    if not (
        d["terminal_growth"] < d["wacc"] <= 1
        and d["terminal_growth"] < d["terminal_roic"] <= 1
    ):
        raise ModelInputError("WACC and terminal ROIC must exceed growth and be <= 1")
    return horizon
