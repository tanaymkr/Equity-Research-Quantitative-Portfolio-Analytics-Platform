"""Reproducible annual FCFF scenarios using a dated SQL history and explicit inputs."""

import json
from dataclasses import asdict
from datetime import date
from hashlib import sha256
from html import escape
from pathlib import Path

from equity_analytics.data import DataStoreError

from .cost_of_capital import (
    default_free_rate,
    implied_discount_rate,
    unlevered_cost_of_capital,
    wacc_with_tax_shield,
)
from .dcf import (
    DCFAssumptions,
    HistoricalSnapshot,
    _finite,
    _validate_rate,
    calculate_dcf,
)
from .sensitivity import sensitivity_matrix

WACC_INPUTS = {
    "government_bond_yield",
    "sovereign_default_spread",
    "equity_risk_premium",
    "unlevered_beta",
    "pretax_cost_of_debt",
    "debt_weight",
}


def capm_wacc(inputs, tax_rate):
    """Platform cost-of-capital method; see equity_analytics.valuation.cost_of_capital."""
    if set(inputs) != WACC_INPUTS:
        raise ValueError("WACC requires exactly: " + ", ".join(sorted(WACC_INPUTS)))
    for name, value in inputs.items():
        _finite(name, value)
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
        if name != "unlevered_beta":
            _validate_rate(name, value)
    _validate_rate("tax_rate", tax_rate)
    risk_free = default_free_rate(
        inputs["government_bond_yield"], inputs["sovereign_default_spread"]
    )
    rates = wacc_with_tax_shield(
        unlevered_cost_of_capital(
            risk_free, inputs["unlevered_beta"], inputs["equity_risk_premium"]
        ),
        inputs["debt_weight"],
        tax_rate,
        inputs["pretax_cost_of_debt"],
    )
    _validate_rate("wacc", rates["wacc"])
    return {
        "risk_free_rate": risk_free,
        "unlevered_cost_of_capital": rates["unlevered_cost_of_capital"],
        "tax_shield": rates["tax_shield"],
        "aftertax_cost_of_debt": inputs["pretax_cost_of_debt"] * (1 - tax_rate),
        "wacc": rates["wacc"],
    }


def market_check(snapshot, values, reference, anchor_date, model_value, model_wacc):
    """Single discount rate at which the base case matches the market price."""
    price = reference["price"]
    _finite("market price", price)
    if price <= 0:
        raise ValueError("Market reference price must be positive")
    years = (
        date.fromisoformat(reference["date"]) - date.fromisoformat(anchor_date)
    ).days / 365
    if years < 0:
        raise ValueError("Market reference must not precede the anchor date")

    def value_at(rate):
        assumptions = DCFAssumptions.from_sequences(**values, wacc=rate)
        value = calculate_dcf(snapshot, assumptions).implied_value_per_share
        return value * (1 + rate) ** years

    return {
        "price_date": reference["date"],
        "price": price,
        "source": reference["source"],
        "model_value_per_share": model_value,
        "model_wacc": model_wacc,
        "implied_wacc": implied_discount_rate(
            value_at, price, low=values["terminal_growth"] + 0.005, high=0.30
        ),
        "method": "Base-case cash flows fixed; one rate solved by bisection; anchor value rolled forward to the price date at that rate.",
    }


def build_sql_dcf(store, config_path):
    raw = Path(config_path).read_bytes()
    config = json.loads(raw)
    if config["schema_version"] != 1:
        raise ValueError("Unsupported DCF configuration version")
    cutoff = date.fromisoformat(config["information_as_of"])
    if date.fromisoformat(config["assumptions_available_on"]) > cutoff:
        raise ValueError("Assumptions are later than information cutoff")
    for source in config["sources"]:
        if date.fromisoformat(source["available_on"]) > cutoff:
            raise ValueError("An assumption source is later than information cutoff")
    history = store.history_as_of(config["company_id"], cutoff.isoformat())
    c = history.company
    if c.ticker != config["ticker"]:
        raise ValueError("Assumptions ticker does not match SQL company")
    if c.data_kind != "reported":
        raise ValueError("SQL DCF requires reported financial history")
    if (c.currency, c.financial_unit) != (config["currency"], config["financial_unit"]):
        raise ValueError("Config currency/unit must match SQL history")
    if c.financial_unit != "million":
        raise ValueError("This adapter currently requires monetary inputs in millions")
    annual = history.annuals[-1]
    if (
        annual.fiscal_year != config["base_year"]
        or annual.period_end.isoformat() != config["anchor_date"]
    ):
        raise ValueError(
            "Config base period does not match latest SQL annual; review assumptions"
        )
    if annual.cash_and_equivalents is None or annual.total_debt is None:
        raise ValueError("Reported cash and debt are required; missing is not zero")
    bridge = config["bridge"]
    snapshot = HistoricalSnapshot(
        company_name=c.name,
        base_year=annual.fiscal_year,
        revenue=annual.revenue,
        cash=annual.cash_and_equivalents,
        debt=annual.total_debt,
        shares_outstanding=bridge["shares_million"],
        currency=c.currency,
        financial_unit=c.financial_unit,
        opening_nwc=bridge["opening_nwc"],
        nonoperating_assets=bridge["nonoperating_assets"],
        minority_interest=bridge["minority_interest"],
        other_claims=bridge["other_claims"],
    )
    if set(config["scenarios"]) != {"downside", "base", "upside"}:
        raise ValueError("Provide downside, base and upside scenarios")
    output = {}
    assumptions_by_case = {}
    for name, case in config["scenarios"].items():
        values = case["forecast"].copy()
        if values.get("terminal_roic") is None:
            raise ValueError("SQL DCF requires explicit terminal ROIC for reinvestment")
        discount = capm_wacc(case["wacc_inputs"], values["tax_rate"])
        assumptions = DCFAssumptions.from_sequences(**values, wacc=discount["wacc"])
        assumptions_by_case[name] = assumptions
        result = calculate_dcf(snapshot, assumptions)
        output[name] = {
            "wacc_build": discount,
            "assumptions": asdict(assumptions),
            "result": result.to_dict(),
        }
    sensitivity = sensitivity_matrix(
        snapshot, assumptions_by_case["base"], **config["sensitivity"]
    )
    market = None
    if "market_reference" in config:
        base_case = output["base"]
        market = market_check(
            snapshot,
            config["scenarios"]["base"]["forecast"],
            config["market_reference"],
            config["anchor_date"],
            base_case["result"]["implied_value_per_share"],
            base_case["wacc_build"]["wacc"],
        )
    history_payload = asdict(history)
    history_bytes = json.dumps(history_payload, default=str, sort_keys=True).encode()
    return {
        "schema_version": 1,
        "company_id": config["company_id"],
        "anchor_date": config["anchor_date"],
        "information_as_of": cutoff.isoformat(),
        "config_sha256": sha256(raw).hexdigest(),
        "history_sha256": sha256(history_bytes).hexdigest(),
        "history": history_payload,
        "configuration": config,
        "snapshot": asdict(snapshot),
        "scenarios": output,
        "sensitivity": sensitivity,
        "market_check": market,
        "warning": "Annual model anchored at fiscal year-end, using later information. Not a current-date target price or a point-in-time backtest. WACC and equity adjustments include estimates.",
    }


def _table(headers, rows):
    def cells(xs, tag):
        return "".join(f"<{tag}>{escape(str(x))}</{tag}>" for x in xs)

    return (
        '<div class="scroll"><table><tr>'
        + cells(headers, "th")
        + "</tr>"
        + "".join("<tr>" + cells(row, "td") + "</tr>" for row in rows)
        + "</table></div>"
    )


def export_sql_dcf(store, config_path, output):
    output = Path(output)
    targets = [output / n for n in ("valuation.json", "valuation.html")]
    if any(
        t.resolve() in {store.path.resolve(), Path(config_path).resolve()}
        for t in targets
    ):
        raise DataStoreError("Output must not overwrite database or assumptions")
    payload = build_sql_dcf(store, config_path)
    currency = escape(payload["snapshot"]["currency"])
    sections = []
    for name, case in payload["scenarios"].items():
        r = case["result"]
        sections.append(f"<h2>{escape(name.title())} scenario</h2>")
        sections.append(
            _table(
                ["Metric", "Value"],
                [
                    ["WACC", f"{r['wacc']:.2%}"],
                    [
                        "Unlevered cost of capital",
                        f"{case['wacc_build']['unlevered_cost_of_capital']:.2%}",
                    ],
                    ["Debt tax shield", f"{case['wacc_build']['tax_shield']:.3%}"],
                    ["Enterprise value", f"{r['enterprise_value']:,.2f}"],
                    ["Add cash", r["cash"]],
                    ["Add nonoperating assets (proxy)", r["nonoperating_assets"]],
                    ["Less debt incl. leases", r["debt"]],
                    ["Less minority value (proxy)", r["minority_interest"]],
                    ["Less other claims", r["other_claims"]],
                    ["Equity value", f"{r['equity_value']:,.2f}"],
                    ["Shares, million (dilution proxy)", r["shares_outstanding"]],
                    [
                        f"Model value/share, {currency}",
                        f"{r['implied_value_per_share']:,.2f}",
                    ],
                    ["Terminal FCFF", f"{r['terminal_fcff']:,.2f}"],
                    ["Terminal value", f"{r['terminal_value']:,.2f}"],
                    ["PV terminal", f"{r['present_value_terminal']:,.2f}"],
                    [
                        "PV terminal / EV",
                        f"{r['present_value_terminal'] / r['enterprise_value']:.1%}"
                        if r["enterprise_value"]
                        else "N/A",
                    ],
                ],
            )
        )
        keys = [
            "year",
            "revenue",
            "ebit",
            "nopat",
            "depreciation",
            "capex",
            "net_working_capital",
            "change_in_nwc",
            "fcff",
            "present_value_fcff",
        ]
        sections.append(
            _table(
                keys,
                [
                    [f"{y[k]:,.2f}" if k != "year" else y[k] for k in keys]
                    for y in r["forecast"]
                ],
            )
        )
    matrix = payload["sensitivity"]
    rates = payload["configuration"]["sensitivity"]["wacc_values"]
    sensitivity = _table(
        ["g / WACC"] + [f"{w:.1%}" for w in rates],
        [
            [f"{g:.1%}"]
            + ["N/A" if row[w] is None else f"{row[w]:,.2f}" for w in rates]
            for g, row in matrix.items()
        ],
    )
    config_text = escape(json.dumps(payload["configuration"], indent=2))
    market = payload["market_check"]
    market_html = ""
    if market is not None:
        implied = (
            f"a WACC of {market['implied_wacc']:.2%}"
            if market["implied_wacc"] is not None
            else "a WACC outside the search range"
        )
        market_html = (
            "<h2>What the market price implies</h2><p>"
            + escape(
                f"The share closed at {market['price']:,.2f} on {market['price_date']} "
                f"({market['source']}). The base case gives {market['model_value_per_share']:,.2f} "
                f"at a {market['model_wacc']:.2%} WACC. Holding its cash flows fixed, the price "
                f"implies {implied}. This check never changes the forecast."
            )
            + "</p>"
        )
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>SQL DCF research model</title>
<style>body{{font:15px/1.5 system-ui;background:#f4f6f8;color:#173451}}main{{max-width:1200px;margin:24px auto;background:white;padding:28px}}
th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:right}}th:first-child,td:first-child{{text-align:left}}
table{{border-collapse:collapse;width:100%}}.scroll{{overflow:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}
.notice{{background:#fff3cd;padding:16px}}</style><main><h1>{escape(payload["snapshot"]["company_name"])} — SQL DCF</h1>
<p>Money in {currency} million; shares in million; value/share in {currency}. Anchor: {payload["anchor_date"]}; information cutoff: {payload["information_as_of"]}.</p>
<p class="notice">{escape(payload["warning"])}</p>
{market_html}{"".join(sections)}<h2>Base case sensitivity: {currency}/share</h2>{sensitivity}
<h2>Assumptions, mapping and evidence</h2><p>Rates use decimals. All scenario inputs and their rationale are reproduced below.</p><pre>{config_text}</pre>
<p>Complete SQL history, sources, forecasts and reproducibility hashes: valuation.json.</p></main></html>"""
    output.mkdir(parents=True, exist_ok=True)
    targets[0].write_text(
        json.dumps(payload, indent=2, default=str, allow_nan=False) + "\n"
    )
    targets[1].write_text(html, encoding="utf-8")
    return payload
