"""Linked annual Wabag statements; cash is an output, never a balancing plug."""

import json
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path

from equity_analytics.valuation.dcf import HistoricalSnapshot, _finite, _validate_rate
from equity_analytics.valuation.explicit import ExplicitCashFlow, discount_cash_flows

from .layout import (
    BS_KEYS,
    CF_ADJUSTMENTS,
    CF_FINANCE,
    CF_INVEST,
    CF_WC,
    OP_ASSETS,
    OP_LIABS,
    balance_totals,
    income_totals,
    operating_nwc,
)

ZERO_ONLY = ("oci", "asset_disposals", "new_equity")
DRIVERS = {
    "revenue",
    "ebitda_margin",
    "employees",
    "other_expenses",
    "capex",
    "da_target",
    "bank_debt_target",
    "tax_rate",
    "deferred_tax_rate",
    "bank_charges",
    "interest_yield",
    "dividend_income",
    "associate_profit",
    "esop",
    "ecl_charge",
    "provision_contracts",
    "provision_employee",
    "provision_damages",
    "provision_warranty",
    "loans_advanced",
    "nci_profit",
    "declared_dps",
    "fx_gain",
    "exceptional",
    "oci",
    "asset_disposals",
    "new_leases",
    "new_equity",
    "associate_dividends",
    "new_investments",
    "nci_dividends",
    "writeoffs",
}
SIGNED = {
    "associate_profit",
    "deferred_tax_rate",
    "nci_profit",
    "fx_gain",
    "exceptional",
}
POLICY = {
    "terminal_growth",
    "terminal_roic",
    "cash_exclusion",
    "term_repayment",
    "term_rate",
    "working_rate",
    "lease_rate",
    "land_capex_share",
    "software_capex_share",
    "dividend_payout_tail",
}


def load_inputs(directory: Path | str) -> dict:
    result = {}
    hashes = {}
    for key in ("history", "forecast_references", "wacc_reference", "assumptions"):
        path = Path(directory) / f"{key}.json"
        raw = path.read_bytes()
        result[key] = json.loads(raw)
        hashes[path.name] = sha256(raw).hexdigest()
    result["input_sha256"] = hashes
    return result


def _records(records, expected, label):
    if set(records) != set(expected):
        raise ValueError(
            f"{label}: required keys differ: {set(records) ^ set(expected)}"
        )
    values = {}
    for key, record in records.items():
        _finite(f"{label}.{key}", record["value"])
        if not record["source"] or not record["reason"]:
            raise ValueError(f"Missing provenance for {label}.{key}")
        values[key] = record["value"]
    return values


def validate_inputs(inputs):
    h, cfg = inputs["history"], inputs["assumptions"]
    if h["schema_version"] != 1 or cfg["schema_version"] != 1:
        raise ValueError("Unsupported schema version")
    if (h["company_id"], h["currency"], h["unit"], h["basis"]) != (
        "WABAG",
        "INR",
        "million",
        "consolidated",
    ):
        raise ValueError("Wabag adapter requires consolidated INR million inputs")
    if [a["year"] for a in h["annuals"]] != [2024, 2025, 2026]:
        raise ValueError("This adapter requires the FY24-26 three-year history")
    if cfg["anchor_date"] != "2026-03-31" or cfg["horizon"] != 5:
        raise ValueError("This adapter requires FY26 anchor and five forecast years")
    cutoff = date.fromisoformat(cfg["information_as_of"])
    if date.fromisoformat(inputs["wacc_reference"]["price_date"]) > cutoff:
        raise ValueError("Market observation is later than information cutoff")
    for source in h["sources"].values():
        if date.fromisoformat(source["date"]) > cutoff:
            raise ValueError("Source is later than information cutoff")
    # Validate the entire financial input tree. Unknown/missing rows are never zero-filled.
    for key, value in h["opening_schedules"].items():
        _finite(f"opening_schedules.{key}", value)
        if value < 0:
            raise ValueError(f"opening_schedules.{key} cannot be negative")
    for a in h["annuals"]:
        if set(a["balance_sheet"]) != set(BS_KEYS):
            raise ValueError("Missing or unknown historical balance-sheet line")
        for section in ("balance_sheet", "income_statement", "cash_flow", "notes"):
            for k, value in a[section].items():
                _finite(f"FY{a['year']}.{section}.{k}", value)
        balance_totals(a["balance_sheet"])
        income_totals(a["income_statement"])
        if abs(a["balance_sheet"]["balance_residual"]) > 1:
            raise ValueError(
                "Historical balance sheet does not reconcile within rounding"
            )
        if abs(a["cash_flow"]["closing_cash"] - a["balance_sheet"]["cash"]) > 1:
            raise ValueError("Historical cash does not tie to balance sheet")
    p = _records(cfg["policy"], POLICY, "policy")
    for k, v in p.items():
        if v < 0:
            raise ValueError(f"policy.{k} cannot be negative")
    for k in (
        "term_rate",
        "working_rate",
        "lease_rate",
        "land_capex_share",
        "software_capex_share",
        "dividend_payout_tail",
    ):
        _validate_rate(k, p[k])
    if p["land_capex_share"] + p["software_capex_share"] > 1:
        raise ValueError("Capex allocation exceeds 100%")
    if p["cash_exclusion"] > h["annuals"][-1]["balance_sheet"]["cash"]:
        raise ValueError("Cash exclusion exceeds cash and equivalents")
    if not 0 <= p["terminal_growth"] < p["terminal_roic"]:
        raise ValueError("Terminal growth must be below positive ROIC")
    ratios = _records(
        cfg["operating_balance_ratios"],
        (*OP_ASSETS, *OP_LIABS, "tax_assets", "tax_liabilities", "other_bank"),
        "operating balances",
    )
    if any(v < 0 for v in ratios.values()):
        raise ValueError("Balance ratios cannot be negative")
    if [y["year"] for y in cfg["years"]] != list(range(2027, 2032)):
        raise ValueError("Forecast years must be FY27-31")
    for row in cfg["years"]:
        d = _records(row["drivers"], DRIVERS, str(row["year"]))
        for k, v in d.items():
            method = row["drivers"][k].get("method", "absolute")
            if method not in (
                "absolute",
                "revenue_ratio",
                "prior_revenue_growth",
                "prior_debt_growth",
            ):
                raise ValueError(f"Unknown driver method: {method}")
            if method.startswith("prior_"):
                expected = (
                    "revenue"
                    if method == "prior_revenue_growth"
                    else "bank_debt_target"
                )
                if k != expected or v <= -1:
                    raise ValueError(
                        "Growth methods require the matching driver and growth above -100%"
                    )
                continue
            if method == "revenue_ratio":
                if k in (
                    "revenue",
                    "tax_rate",
                    "ebitda_margin",
                    "interest_yield",
                    "deferred_tax_rate",
                ):
                    raise ValueError(f"Revenue-ratio method cannot be used for {k}")
                _validate_rate(k, v)
            if v < 0 and k not in SIGNED and not (k == "declared_dps" and v == -1):
                raise ValueError(f"{k} cannot be negative")
        if (
            row["drivers"]["revenue"].get("method", "absolute") == "absolute"
            and d["revenue"] <= 0
        ):
            raise ValueError("Revenue must be positive")
        for k in ("tax_rate", "ebitda_margin", "interest_yield"):
            _validate_rate(k, d[k])
        if any(d[k] != 0 for k in ZERO_ONLY):
            raise ValueError(
                "OCI, asset disposals and new equity need additional accounting schedules; keep zero"
            )
    return p, ratios


def resolve_drivers(records, prior_revenue, prior_bank_debt):
    """Keep sourced amounts fixed and scale explicitly marked historical ratios."""
    result = {k: v["value"] for k, v in records.items()}
    revenue = records["revenue"]
    if revenue.get("method") == "prior_revenue_growth":
        result["revenue"] = prior_revenue * (1 + revenue["value"])
    for k, record in records.items():
        if record.get("method") == "revenue_ratio":
            result[k] = record["value"] * result["revenue"]
        elif record.get("method") == "prior_debt_growth":
            result[k] = prior_bank_debt * (1 + record["value"])
    return result


def verify_beta(reference):
    """Recompute the dated OLS beta from the included observations."""
    observations = reference["beta_observations"]
    if len(observations) < 30:
        raise ValueError("At least 30 paired weekly observations required for beta")
    endings = []
    for row in observations:
        start, end = date.fromisoformat(row["start"]), date.fromisoformat(row["end"])
        start_week = start - timedelta(days=start.weekday())
        end_week = end - timedelta(days=end.weekday())
        if (end_week - start_week).days != 7 or end > date.fromisoformat(
            reference["price_date"]
        ):
            raise ValueError("Invalid weekly beta observation dates")
        endings.append(end)
        for key in ("stock_return", "benchmark_return"):
            _finite(key, row[key])
    if endings != sorted(set(endings)):
        raise ValueError("Beta observations must have unique increasing end dates")
    x = [r["benchmark_return"] for r in observations]
    y = [r["stock_return"] for r in observations]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    variance = sum((v - mx) ** 2 for v in x)
    covariance = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    if variance <= 0:
        raise ValueError("Benchmark has no variance")
    beta = covariance / variance
    if abs(beta - reference["levered_beta"]) > 1e-10:
        raise ValueError("Stored beta does not match included weekly returns")
    return beta


def _check(name, year, residual, tolerance=1e-6):
    return {
        "name": name,
        "year": year,
        "residual": residual,
        "tolerance": tolerance,
        "passed": abs(residual) <= tolerance,
    }


def historical_checks(annuals):
    checks = []
    for row in annuals:
        year = row["year"]
        b, s, c = (row[k] for k in ("balance_sheet", "income_statement", "cash_flow"))
        residuals = {
            "Reported asset total": b["assets"] - row["notes"]["reported_assets"],
            "Reported equity total": b["equity"] - row["notes"]["reported_equity"],
            "Reported liabilities total": b["liabilities"]
            - row["notes"]["reported_liabilities"],
            "Historical balance sheet": b["balance_residual"],
            "Historical net profit": s["pbt"]
            - s["current_tax"]
            - s["deferred_tax"]
            - s["net_income"],
            "Historical profit attribution": s["owners_profit"]
            + s["nci_profit"]
            - s["net_income"],
            "Historical CF adjustments": c["pbt"]
            + sum(c[k] for k in CF_ADJUSTMENTS)
            - c["op_before_wc"],
            "Historical working capital": c["op_before_wc"]
            + sum(c[k] for k in CF_WC)
            - c["cash_generated"],
            "Historical CFO": c["cash_generated"] + c["taxes_paid"] - c["cfo"],
            "Historical CFI": sum(c[k] for k in CF_INVEST) - c["cfi"],
            "Historical CFF": sum(c[k] for k in CF_FINANCE) - c["cff"],
            "Historical cash roll-forward": c["opening_cash"]
            + c["cash_change"]
            + c["cash_fx"]
            + c["cash_held_for_sale"]
            - c["closing_cash"],
        }
        checks.extend(
            _check(name, year, value, tolerance=1.0)
            for name, value in residuals.items()
        )
    failed = [c for c in checks if not c["passed"]]
    if failed:
        raise ValueError(f"Historical statements fail source reconciliation: {failed}")
    return checks


def _asset_schedule(previous, d, p):
    opening = {k: previous[k] for k in ("land", "owned", "rou", "software")}
    additions = {
        "land": d["capex"] * p["land_capex_share"],
        "software": d["capex"] * p["software_capex_share"],
        "rou": d["new_leases"],
    }
    additions["owned"] = d["capex"] - additions["land"] - additions["software"]
    depreciation = {"land": 0.0}
    for k, weight in (("owned", 43), ("rou", 15), ("software", 4)):
        # Annual allocation, capped at available net assets; not useful-life estimation.
        depreciation[k] = min(opening[k] + additions[k], d["da_target"] * weight / 62)
    closing = {k: opening[k] + additions[k] - depreciation[k] for k in opening}
    return {
        "opening": opening,
        "additions": additions,
        "depreciation": depreciation,
        "closing": closing,
        "da": sum(depreciation.values()),
        "capex": d["capex"],
        "uncaptured_da_target": d["da_target"] - sum(depreciation.values()),
    }


def _debt_schedule(previous, previous_bs, d, p, period):
    term_open, working_open = previous["term"], previous["working"]
    scheduled = min(term_open, p["term_repayment"])
    extra = max(0.0, term_open - scheduled - d["bank_debt_target"])
    term_close = term_open - scheduled - extra
    working_close = d["bank_debt_target"] - term_close
    lease_open = previous_bs["lease_nc"] + previous_bs["lease_current"]
    lease_repaid = min(lease_open, 6.0 if period == 0 else 5.75)
    lease_close = lease_open + d["new_leases"] - lease_repaid
    interest_term = (term_open + term_close) / 2 * p["term_rate"]
    interest_working = (working_open + working_close) / 2 * p["working_rate"]
    interest_lease = (lease_open + lease_close) / 2 * p["lease_rate"]
    return {
        "term_open": term_open,
        "working_open": working_open,
        "lease_open": lease_open,
        "scheduled_repayment": scheduled,
        "extra_repayment": extra,
        "term_close": term_close,
        "working_close": working_close,
        "working_net_draw": working_close - working_open,
        "lease_repaid": lease_repaid,
        "lease_additions": d["new_leases"],
        "lease_close": lease_close,
        "current_term": min(term_close, p["term_repayment"]),
        "current_lease": min(lease_close, 5.75),
        "term_rate": p["term_rate"],
        "working_rate": p["working_rate"],
        "lease_rate": p["lease_rate"],
        "interest_term": interest_term,
        "interest_working": interest_working,
        "interest_lease": interest_lease,
        "borrowing_interest": interest_term + interest_working,
        "interest_total": interest_term + interest_working + interest_lease,
        "total_open": term_open + working_open + lease_open,
        "total_close": term_close + working_close + lease_close,
    }


def _wacc(reference, overrides, debt, tax, base_debt, basic_shares, base_tax):
    r = {**reference, **overrides}
    allowed = {
        "share_price",
        "gsec_yield",
        "sovereign_default_spread",
        "mature_erp",
        "country_risk_premium",
        "country_loading",
        "levered_beta",
    }
    if set(overrides) - allowed:
        raise ValueError("Unknown WACC override")
    for k in allowed:
        _finite(k, r[k])
        if r[k] < 0:
            raise ValueError(f"{k} cannot be negative")
    if r["share_price"] <= 0:
        raise ValueError("A positive market equity price is required")
    market_equity = r["share_price"] * basic_shares
    rf = r["gsec_yield"] - r["sovereign_default_spread"]
    _validate_rate("default_free_inr_rate", rf)
    unlevered = r["levered_beta"] / (1 + (1 - base_tax) * base_debt / market_equity)
    average_debt = (debt["total_open"] + debt["total_close"]) / 2
    beta = unlevered * (1 + (1 - tax) * average_debt / market_equity)
    debt_weight = average_debt / (market_equity + average_debt)
    kd = debt["interest_total"] / average_debt if average_debt else 0.0
    ke = rf + beta * r["mature_erp"] + r["country_loading"] * r["country_risk_premium"]
    wacc = ke * (1 - debt_weight) + kd * (1 - tax) * debt_weight
    _validate_rate("wacc", wacc)
    return {
        "market_equity": market_equity,
        "average_gross_debt": average_debt,
        "debt_weight": debt_weight,
        "equity_weight": 1 - debt_weight,
        "default_free_inr_rate": rf,
        "unlevered_beta": unlevered,
        "relevered_beta": beta,
        "cost_of_equity": ke,
        "pretax_cost_of_debt": kd,
        "aftertax_cost_of_debt": kd * (1 - tax),
        "tax_rate": tax,
        "wacc": wacc,
    }


def crosscheck_sql(store, history, cutoff):
    """Optional read-only tie to the existing generic SQL data layer."""
    sql = store.history_as_of("WABAG", cutoff, basis="consolidated")
    if (sql.company.currency, sql.company.financial_unit) != ("INR", "million"):
        raise ValueError("SQL currency or units differ from linked model")
    by_year = {a.fiscal_year: a for a in sql.annuals}
    checked = []
    for a in history["annuals"]:
        if a["year"] not in by_year:
            raise ValueError(f"SQL is missing FY{a['year']}; run Wabag analysis first")
        row = by_year[a["year"]]
        bs, inc = a["balance_sheet"], a["income_statement"]
        mapping = {
            "revenue": inc["revenue"],
            "net_income": inc["net_income"],
            "cash_and_equivalents": bs["cash"],
            "total_debt": sum(
                bs[k] for k in ("debt_nc", "debt_current", "lease_nc", "lease_current")
            ),
        }
        for key, expected in mapping.items():
            value = getattr(row, key)
            if value is None or abs(value - expected) > 1:
                raise ValueError(
                    f"SQL mismatch in FY{a['year']} {key}: {value} vs {expected}"
                )
            checked.append(
                {"year": a["year"], "field": key, "sql": value, "detailed": expected}
            )
    return checked


def build_model(inputs: dict, *, store=None) -> dict:
    inputs = deepcopy(inputs)
    h, cfg = inputs["history"], inputs["assumptions"]
    sql_checks = (
        crosscheck_sql(store, h, cfg["information_as_of"]) if store is not None else []
    )
    p, ratios = validate_inputs(inputs)
    verify_beta(inputs["wacc_reference"])
    history_checks = historical_checks(h["annuals"])
    opening = h["opening_schedules"]
    base = h["annuals"][-1]
    b0 = base["balance_sheet"]
    shares = opening["shares_million"]
    diluted = shares + opening["dilution_options_million"]
    if not 0 < shares <= diluted:
        raise ValueError("Invalid shares or incremental option dilution")
    assets = {
        "land": opening["land"],
        "owned": opening["owned_ppe_ex_land_rou"],
        "rou": opening["rou_assets"],
        "software": b0["intangibles"],
    }
    if abs(sum(assets.values()) - b0["ppe"] - b0["intangibles"]) > 1e-6:
        raise ValueError("Opening fixed-asset schedule does not tie")
    debt_previous = {
        "term": opening["term_debt_including_current"],
        "working": opening["working_facilities"],
    }
    if abs(sum(debt_previous.values()) - b0["debt_nc"] - b0["debt_current"]) > 1e-6:
        raise ValueError("Opening debt schedule does not tie")
    previous_bs = b0
    prior_contract_inventory = opening["contract_inventory"]
    prior_declared_dps = base["notes"]["declared_dps"]
    allowance = opening["loss_allowance"]
    base_debt = sum(
        b0[k] for k in ("debt_nc", "debt_current", "lease_nc", "lease_current")
    )
    base_tax = (
        base["income_statement"]["current_tax"]
        + base["income_statement"]["deferred_tax"]
    ) / (base["income_statement"]["pbt"] - base["income_statement"]["associate_profit"])
    forecast, checks = [], []
    for period, row in enumerate(cfg["years"]):
        year = row["year"]
        prior_revenue = (
            forecast[-1]["income_statement"]["revenue"]
            if forecast
            else base["income_statement"]["revenue"]
        )
        prior_bank_debt = previous_bs["debt_nc"] + previous_bs["debt_current"]
        d = resolve_drivers(row["drivers"], prior_revenue, prior_bank_debt)
        b = {k: previous_bs[k] for k in BS_KEYS}
        for k, ratio in ratios.items():
            b[k] = d["revenue"] * ratio
        fixed = _asset_schedule(assets, d, p)
        debt = _debt_schedule(debt_previous, previous_bs, d, p, period)
        b["ppe"] = sum(fixed["closing"][k] for k in ("land", "owned", "rou"))
        b["intangibles"] = fixed["closing"]["software"]
        b["debt_nc"] = debt["term_close"] - debt["current_term"]
        b["debt_current"] = debt["current_term"] + debt["working_close"]
        b["lease_current"] = debt["current_lease"]
        b["lease_nc"] = debt["lease_close"] - debt["current_lease"]
        b["associates"] += (
            d["associate_profit"] + d["new_investments"] - d["associate_dividends"]
        )
        b["loans"] += d["loans_advanced"]
        contract_inventory = (
            b["inventories"] * opening["contract_inventory"] / b0["inventories"]
        )
        dividend_paid = prior_declared_dps * shares
        interest_income = (previous_bs["cash"] + previous_bs["other_bank"]) * d[
            "interest_yield"
        ]
        s = {
            "revenue": d["revenue"],
            "fx_gain": d["fx_gain"],
            "other_income": interest_income + d["dividend_income"],
            "inventory_change": prior_contract_inventory - contract_inventory,
            "employees": d["employees"],
            "other_expenses": d["other_expenses"],
            "finance_cost": debt["interest_total"] + d["bank_charges"],
            "da": fixed["da"],
            "associate_profit": d["associate_profit"],
            "exceptional": d["exceptional"],
            "oci_nonreclass": 0.0,
            "oci_reclass": 0.0,
            "oci_owners": 0.0,
            "oci_nci": 0.0,
            "net_income": 0.0,
        }
        # The sourced margin controls total operating expense; residual is identified.
        ebitda = s["revenue"] * d["ebitda_margin"]
        s["cost_sales"] = (
            s["revenue"]
            + s["fx_gain"]
            - ebitda
            - s["inventory_change"]
            - s["employees"]
            - s["other_expenses"]
        )
        if s["cost_sales"] < 0:
            raise ValueError(
                f"FY{year}: negative residual cost of sales; review margin / expense assumptions"
            )
        income_totals(s)
        tax_base = max(0.0, s["pbt"] - s["associate_profit"])
        s["deferred_tax"] = min(previous_bs["dta"], tax_base * d["deferred_tax_rate"])
        total_tax = tax_base * d["tax_rate"]
        s["current_tax"] = total_tax - s["deferred_tax"]
        s["net_income"] = s["pbt"] - total_tax
        s["nci_profit"] = d["nci_profit"]
        s["owners_profit"] = s["net_income"] - s["nci_profit"]
        s["basic_eps"] = s["owners_profit"] / shares
        s["diluted_eps"] = s["owners_profit"] / (
            diluted if s["owners_profit"] >= 0 else shares
        )
        income_totals(s)
        declared_dps = d["declared_dps"]
        if declared_dps == -1:
            declared_dps = max(
                prior_declared_dps, p["dividend_payout_tail"] * max(0, s["basic_eps"])
            )
        b["dta"] = previous_bs["dta"] - s["deferred_tax"]
        b["reserves"] += s["owners_profit"] + d["esop"] - dividend_paid
        b["nci"] += s["nci_profit"] - d["nci_dividends"]
        tax_paid = (
            s["current_tax"]
            + b["tax_assets"]
            - previous_bs["tax_assets"]
            - b["tax_liabilities"]
            + previous_bs["tax_liabilities"]
        )
        new_allowance = allowance + d["ecl_charge"] - d["writeoffs"]
        if new_allowance < 0:
            raise ValueError("Write-offs exceed the credit-loss allowance")
        delta = lambda *ks, current=b, prior=previous_bs: sum(
            current[k] - prior[k] for k in ks
        )
        provision_charge = sum(
            d[k]
            for k in (
                "provision_contracts",
                "provision_employee",
                "provision_damages",
                "provision_warranty",
            )
        )
        c = {
            "pbt": s["pbt"],
            "da": s["da"],
            "associates_adj": -s["associate_profit"],
            "unrealized_fx": 0.0,
            "bad_debt": d["ecl_charge"],
            "credit_writeback": 0.0,
            "asset_sale_gain": 0.0,
            "subsidiary_sale_gain": 0.0,
            "esop": d["esop"],
            "lease_interest": debt["interest_lease"],
            "borrowing_interest": debt["borrowing_interest"],
            "investment_income": -s["other_income"],
            **{
                k: d[k]
                for k in (
                    "provision_contracts",
                    "provision_employee",
                    "provision_damages",
                    "provision_warranty",
                )
            },
            "wc_receivables": -delta("ar_nc", "ar_current") - d["ecl_charge"],
            "wc_ofa": -delta("ofa_nc", "ofa_current"),
            "wc_other_assets": -delta("other_current_assets"),
            "wc_inventory": -delta("inventories"),
            "wc_payables": delta("ap_nc", "ap_msme", "ap_other"),
            "wc_ofl": delta("ofl_nc", "ofl_current"),
            "wc_other_liabilities": delta(
                "other_liabilities_nc", "other_liabilities_current"
            ),
            "wc_provisions": delta("provisions_nc", "provisions_current")
            - provision_charge,
            "taxes_paid": -tax_paid,
            "capex": -d["capex"],
            "asset_sale": 0.0,
            "subsidiary_sale": 0.0,
            "investment_purchase": -d["new_investments"],
            "loans_issued": -d["loans_advanced"],
            "dividends_received": d["dividend_income"] + d["associate_dividends"],
            "interest_received": interest_income,
            "deposits_movement": -delta("other_bank"),
            "long_debt_cash": debt["term_close"] - debt["term_open"],
            "short_debt_cash": debt["working_net_draw"],
            "equity_issue": 0.0,
            "lease_principal": -debt["lease_repaid"],
            "lease_interest_paid": -debt["interest_lease"],
            "interest_paid": -debt["borrowing_interest"],
            "dividends_paid": -dividend_paid - d["nci_dividends"],
            "cash_fx": 0.0,
            "opening_cash": previous_bs["cash"],
            "cash_held_for_sale": 0.0,
        }
        c["op_before_wc"] = c["pbt"] + sum(c[k] for k in CF_ADJUSTMENTS)
        c["cash_generated"] = c["op_before_wc"] + sum(c[k] for k in CF_WC)
        c["cfo"] = c["cash_generated"] + c["taxes_paid"]
        c["cfi"] = sum(c[k] for k in CF_INVEST)
        c["cff"] = sum(c[k] for k in CF_FINANCE)
        c["cash_change"] = c["cfo"] + c["cfi"] + c["cff"]
        c["closing_cash"] = c["opening_cash"] + c["cash_change"]
        b["cash"] = c["closing_cash"]
        balance_totals(b)
        if b["cash"] < p["cash_exclusion"]:
            raise ValueError(
                f"FY{year}: funding shortfall {p['cash_exclusion'] - b['cash']:.2f} million relative to restricted cash floor; revise funding or operating assumptions"
            )
        if b["associates"] < 0 or s["current_tax"] < 0:
            raise ValueError(
                "Unsupported negative associate asset / current tax expense"
            )
        if (
            d["esop"] + d["provision_employee"] > s["employees"]
            or d["ecl_charge"] > s["other_expenses"]
        ):
            raise ValueError("Noncash expense allocation exceeds its expense budget")
        ebit = ebitda - s["da"] - d["bank_charges"]
        operating_tax = max(ebit, 0.0) * d["tax_rate"]
        nopat = ebit - operating_tax
        change_nwc = operating_nwc(b) - operating_nwc(previous_bs)
        # Capitalised leases are financing: their noncash asset additions are
        # reinvestment, while principal payments are excluded from FCFF.
        fcff = nopat + s["da"] - d["capex"] - d["new_leases"] - change_nwc
        from_cfo = (
            c["cfo"]
            - d["esop"]
            - d["capex"]
            - d["new_leases"]
            - delta("other_bank")
            + tax_paid
            - operating_tax
            - d["exceptional"]
        )
        if c["wc_provisions"] > 1e-6:
            raise ValueError(
                f"FY{year}: provision stock growth exceeds expense charge; specify a supported charge rather than an unexplained noncash increase"
            )
        rates = _wacc(
            inputs["wacc_reference"],
            cfg["wacc_overrides"],
            debt,
            d["tax_rate"],
            base_debt,
            shares,
            base_tax,
        )
        year_checks = [
            _check("Balance sheet", year, b["balance_residual"]),
            _check("Cash flow to cash balance", year, c["closing_cash"] - b["cash"]),
            _check(
                "Cash roll-forward",
                year,
                previous_bs["cash"] + c["cfo"] + c["cfi"] + c["cff"] - b["cash"],
            ),
            _check(
                "Debt roll-forward",
                year,
                debt["total_open"]
                + c["long_debt_cash"]
                + c["short_debt_cash"]
                + d["new_leases"]
                - debt["lease_repaid"]
                - debt["total_close"],
            ),
            _check(
                "Fixed assets",
                year,
                sum(assets.values())
                + d["capex"]
                + d["new_leases"]
                - s["da"]
                - b["ppe"]
                - b["intangibles"],
            ),
            _check(
                "Equity roll-forward",
                year,
                previous_bs["equity"]
                + s["net_income"]
                + d["esop"]
                - dividend_paid
                - d["nci_dividends"]
                - b["equity"],
            ),
            _check("FCFF from CFO vs operating bridge", year, from_cfo - fcff),
            _check(
                "Current/non-current debt partition",
                year,
                sum(
                    b[k]
                    for k in ("debt_nc", "debt_current", "lease_nc", "lease_current")
                )
                - debt["total_close"],
            ),
        ]
        checks.extend(year_checks)
        forecast.append(
            {
                "year": year,
                "resolved_drivers": d,
                "income_statement": s,
                "balance_sheet": b,
                "cash_flow": c,
                "fixed_assets": fixed,
                "debt": debt,
                "wacc": rates,
                "working_capital": {
                    "opening": operating_nwc(previous_bs),
                    "closing": operating_nwc(b),
                    "change": change_nwc,
                },
                "tax": {
                    "taxable_profit_proxy": tax_base,
                    "total_tax": total_tax,
                    "deferred_tax": s["deferred_tax"],
                    "current_tax": s["current_tax"],
                    "cash_tax": tax_paid,
                },
                "equity": {
                    "opening_reserves": previous_bs["reserves"],
                    "owners_profit": s["owners_profit"],
                    "esop": d["esop"],
                    "cash_dividend": dividend_paid,
                    "closing_reserves": b["reserves"],
                    "declared_dps": declared_dps,
                    "basic_shares": shares,
                    "diluted_shares": diluted,
                },
                "credit_losses": {
                    "opening_allowance": allowance,
                    "charge": d["ecl_charge"],
                    "writeoffs": d["writeoffs"],
                    "closing_allowance": new_allowance,
                    "current_gross_receivables": b["ar_current"] + new_allowance,
                },
                "provisions": {
                    "opening": previous_bs["provisions_nc"]
                    + previous_bs["provisions_current"],
                    "charge": provision_charge,
                    "net_utilisation": -c["wc_provisions"],
                    "closing": b["provisions_nc"] + b["provisions_current"],
                },
                "valuation": {
                    "ebitda_before_bank_charges": ebitda,
                    "bank_charges": d["bank_charges"],
                    "ebit_after_bank_charges": ebit,
                    "nopat": nopat,
                    "da": s["da"],
                    "capex": d["capex"],
                    "noncash_lease_reinvestment": d["new_leases"],
                    "change_nwc": change_nwc,
                    "fcff": fcff,
                    "fcff_from_cfo": from_cfo,
                    "cash_tax_to_operating_tax": tax_paid - operating_tax,
                    "esop_economic_cost": d["esop"],
                },
            }
        )
        previous_bs = b
        assets = fixed["closing"]
        debt_previous = {"term": debt["term_close"], "working": debt["working_close"]}
        prior_contract_inventory, prior_declared_dps, allowance = (
            contract_inventory,
            declared_dps,
            new_allowance,
        )
    failed = [check for check in checks if not check["passed"]]
    if failed:
        raise ValueError(f"Accounting checks failed: {failed}")
    snapshot = HistoricalSnapshot(
        company_name=h["company"],
        base_year=2026,
        revenue=base["income_statement"]["revenue"],
        cash=b0["cash"] - p["cash_exclusion"],
        debt=base_debt,
        shares_outstanding=diluted,
        currency="INR",
        financial_unit="million",
        nonoperating_assets=b0["associates"] + b0["investments"] + b0["loans"],
        minority_interest=b0["nci"],
    )
    cash_flows = [
        ExplicitCashFlow(
            r["year"],
            r["valuation"]["fcff"],
            r["valuation"]["nopat"],
            r["wacc"]["wacc"],
        )
        for r in forecast
    ]
    dcf = discount_cash_flows(
        snapshot,
        cash_flows,
        terminal_growth=p["terminal_growth"],
        terminal_roic=p["terminal_roic"],
    )
    sensitivity = []
    for shift in (-0.01, 0.0, 0.01):
        cells = []
        for growth in (
            max(0.0, p["terminal_growth"] - 0.01),
            p["terminal_growth"],
            p["terminal_growth"] + 0.01,
        ):
            altered = [
                ExplicitCashFlow(r.year, r.fcff, r.nopat, r.wacc + shift)
                for r in cash_flows
            ]
            try:
                value = discount_cash_flows(
                    snapshot,
                    altered,
                    terminal_growth=growth,
                    terminal_roic=p["terminal_roic"],
                )["implied_value_per_share"]
            except ValueError:
                value = None
            cells.append({"terminal_growth": growth, "value_per_share": value})
        sensitivity.append({"wacc_shift": shift, "cells": cells})
    return {
        "schema_version": 1,
        "company": h["company"],
        "unit": "INR million",
        "anchor_date": cfg["anchor_date"],
        "information_as_of": cfg["information_as_of"],
        "convention": cfg["convention"],
        "input_sha256": inputs.get("input_sha256", {}),
        "historical": h["annuals"],
        "forecast": forecast,
        "dcf": dcf,
        "sensitivity": sensitivity,
        "checks": checks,
        "sql_crosschecks": sql_checks,
        "historical_checks": history_checks,
        "sources": h["sources"],
        "assumptions": cfg,
        "forecast_references": inputs["forecast_references"],
        "wacc_reference": inputs["wacc_reference"],
    }
