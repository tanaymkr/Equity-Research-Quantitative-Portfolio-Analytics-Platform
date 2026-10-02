"""Operating scenarios rerun the complete linked model, not just its DCF."""

import json
from copy import deepcopy
from hashlib import sha256
from html import escape
from pathlib import Path

from equity_analytics.valuation.dcf import _finite

from .model import build_model
from .reporting import CSS, export_report, fmt, table

CASE_ORDER = ("downside", "base", "upside")
ADJUSTMENTS = {"revenue_multiplier", "ebitda_margin_change", "receivable_days_change"}


def validate_scenarios(config):
    if config["schema_version"] != 1 or set(config["cases"]) != set(CASE_ORDER):
        raise ValueError(
            "Scenario configuration requires exactly base, upside and downside"
        )
    for name, case in config["cases"].items():
        if case["source"] != "analyst_scenario" or not case["reason"]:
            raise ValueError(
                "Operating scenarios must be labelled analyst_scenario with a reason"
            )
        a = case["adjustments"]
        if set(a) != ADJUSTMENTS:
            raise ValueError(f"{name}: unknown or missing scenario adjustment")
        for key in ("revenue_multiplier", "ebitda_margin_change"):
            if len(a[key]) != 5:
                raise ValueError(f"{name}: five annual adjustments are required")
            for value in a[key]:
                _finite(key, value)
                if key == "revenue_multiplier" and value <= 0:
                    raise ValueError("Revenue multipliers must be positive")
        _finite("receivable_days_change", a["receivable_days_change"])
    base = config["cases"]["base"]["adjustments"]
    if base != {
        "revenue_multiplier": [1] * 5,
        "ebitda_margin_change": [0] * 5,
        "receivable_days_change": 0,
    }:
        raise ValueError("Base case must preserve the user's existing assumptions")


def scenario_inputs(inputs, base, name, config):
    """Apply shocks to baseline levels once; historical expense ratios still scale."""
    result = deepcopy(inputs)
    case = config["cases"][name]
    a = case["adjustments"]
    for i, row in enumerate(result["assumptions"]["years"]):
        for key, value, rule in (
            (
                "revenue",
                base["forecast"][i]["resolved_drivers"]["revenue"]
                * a["revenue_multiplier"][i],
                "base revenue × scenario level multiplier",
            ),
            (
                "ebitda_margin",
                base["forecast"][i]["resolved_drivers"]["ebitda_margin"]
                + a["ebitda_margin_change"][i],
                "base EBITDA margin + percentage-point change",
            ),
        ):
            record = row["drivers"][key]
            original_source = record["source"]
            record.update(
                value=value,
                method="absolute",
                source="analyst_scenario",
                reason=f"{name}: {rule}; base source: {original_source}. {case['reason']}",
            )
    record = result["assumptions"]["operating_balance_ratios"]["ar_current"]
    record.update(
        value=record["value"] + a["receivable_days_change"] / 365,
        source="analyst_scenario",
        reason=f"{name}: add {a['receivable_days_change']} days / 365 to base current-receivable/revenue ratio. This is a collection stress, not management's differently defined NWC KPI.",
    )
    return result


def build_scenarios(inputs, config, *, store=None):
    validate_scenarios(config)
    base = build_model(inputs, store=store)
    results = {"base": {"status": "ok", "model": base}}
    for name in ("downside", "upside"):
        adjusted = scenario_inputs(inputs, base, name, config)
        try:
            model = build_model(adjusted, store=store)
        except ValueError as exc:
            # An infeasible stress has no manufactured value or hidden cash plug.
            results[name] = {"status": "failed", "error": str(exc)}
        else:
            results[name] = {"status": "ok", "model": model}
    scenario_hash = sha256(
        json.dumps(config, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    for name, item in results.items():
        if item["status"] == "ok":
            item["model"]["scenario"] = {
                "name": name,
                "configuration": deepcopy(config["cases"][name]),
                "configuration_sha256": scenario_hash,
            }
    return {
        "schema_version": 2,
        "company": base["company"],
        "information_as_of": base["information_as_of"],
        "convention": base["convention"],
        "scenario_configuration": deepcopy(config),
        "scenario_configuration_sha256": sha256(
            json.dumps(config, sort_keys=True, allow_nan=False).encode()
        ).hexdigest(),
        "scenarios": results,
    }


def _links(prefix=""):
    return "".join(
        f'<a href="{prefix}{name}/forecast.html">{name.title()} case</a>'
        for name in CASE_ORDER
    )


def export_scenarios(bundle, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    cards, comparison, case_notes = [], [], []
    for name in CASE_ORDER:
        item = bundle["scenarios"][name]
        if item["status"] == "ok":
            model = item["model"]
            path = export_report(model, directory / name)
            html = path.read_text(encoding="utf-8")
            html = html.replace(
                "<h1>VA Tech Wabag</h1>",
                f"<h1>VA Tech Wabag — {name.title()} case</h1>",
            )
            html = html.replace(
                "<nav>",
                '<nav><a href="../forecast.html">Scenario comparison</a>'
                + _links("../"),
                1,
            )
            assumptions_note = (
                '<p class="notice"><b>'
                + name.title()
                + " operating case.</b> Revenue, margin and collection assumptions flow through the complete statements. Scenario adjustments are analyst assumptions, not additional company guidance. Baseline input hashes identify the original files; the scenario configuration and modified input register identify the adjustments.</p>"
            )
            html = html.replace("<main>", "<main>" + assumptions_note, 1)
            path.write_text(html, encoding="utf-8")
            value = model["dcf"]["implied_value_per_share"]
            cards.append(
                f'<div><small>{name.title()} case · INR / diluted share</small><strong>{fmt(value)}</strong><a href="{name}/forecast.html">Open statements and DCF →</a></div>'
            )
            y = model["forecast"][0]
            comparison.append(
                [
                    name.title(),
                    value,
                    y["income_statement"]["revenue"],
                    y["income_statement"]["diluted_eps"],
                    f"{y['wacc']['wacc']:.2%}",
                    model["forecast"][-1]["balance_sheet"]["cash"],
                    f"{len(model['checks'])} passed",
                ]
            )
        else:
            message = escape(item["error"])
            cards.append(
                f"<div><small>{name.title()} case</small><strong>Needs revision</strong><p>{message}</p></div>"
            )
            comparison.append(
                [name.title(), None, None, None, None, None, item["error"]]
            )
            # Replace prior scenario outputs so an old successful valuation cannot
            # be mistaken for the current failed run when a bookmark is used.
            target = directory / name
            target.mkdir(exist_ok=True)
            (target / "forecast.json").write_text(
                json.dumps(item, indent=2) + "\n", encoding="utf-8"
            )
            (target / "forecast.html").write_text(
                f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{name.title()} case needs revision</title><h1>{name.title()} case needs revision</h1><p>{message}</p><a href="../forecast.html">Scenario comparison</a></html>',
                encoding="utf-8",
            )
        a = bundle["scenario_configuration"]["cases"][name]["adjustments"]
        case_notes.append(
            [
                name.title(),
                ", ".join(f"{x:.2f}×" for x in a["revenue_multiplier"]),
                ", ".join(f"{100 * x:+.1f} pp" for x in a["ebitda_margin_change"]),
                f"{a['receivable_days_change']:+g} days",
            ]
        )
    annual_rows = []
    for i in range(5):
        for name in CASE_ORDER:
            item = bundle["scenarios"][name]
            if item["status"] != "ok":
                continue
            y = item["model"]["forecast"][i]
            annual_rows.append(
                [
                    str(y["year"]),
                    name.title(),
                    y["income_statement"]["revenue"],
                    y["income_statement"]["owners_profit"],
                    y["income_statement"]["diluted_eps"],
                    y["valuation"]["fcff"],
                    y["balance_sheet"]["cash"],
                ]
            )
    body = '<div class="cards scenarios">' + "".join(cards) + "</div>"
    body += (
        '<p class="notice">'
        + escape(bundle["convention"])
        + " These are editable operating scenarios. They rerun all statements and schedules; the WACC/growth sensitivity remains a separate table inside each case.</p>"
    )
    body += (
        "<section><h2>Scenario comparison</h2>"
        + table(
            [
                "Case",
                "DCF / share (INR)",
                "FY27 revenue (m)",
                "FY27 diluted EPS",
                "FY27 WACC",
                "FY31 cash (m)",
                "Accounting checks",
            ],
            comparison,
        )
        + "</section>"
    )
    body += (
        "<section><h2>Editable scenario assumptions</h2><p>Your existing base assumptions are unchanged. Edit <code>examples/wabag_linked/scenarios.json</code> for the stress cases. Revenue multipliers apply to base revenue levels, not growth rates. Margin changes are percentage points. Receivable-day changes adjust only current trade receivables. Debt targets, terminal growth/ROIC and discount inputs use the same baseline policy across the three cases, so the comparison isolates operating assumptions.</p>"
        + table(
            [
                "Case",
                "Revenue multipliers FY27–31",
                "Margin changes FY27–31",
                "Collection change",
            ],
            case_notes,
        )
        + "<p>All stress adjustments are analyst choices for review; they are not broker forecasts or probabilities.</p></section>"
    )
    body += (
        "<section><h2>Five-year operating comparison</h2>"
        + table(
            [
                "FY",
                "Case",
                "Revenue (m)",
                "Owners PAT (m)",
                "Diluted EPS",
                "FCFF (m)",
                "Closing cash (m)",
            ],
            annual_rows,
        )
        + "</section>"
    )
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wabag · Base, upside and downside</title><style>'
        + CSS
        + '.scenarios{grid-template-columns:repeat(3,1fr)}@media(max-width:800px){.scenarios{grid-template-columns:1fr}}</style></head><body><header><div class="eyebrow">INVESTMENT RESEARCH PLATFORM</div><h1>Wabag · Three operating cases</h1><p>Base, upside and downside · Linked statements and valuation</p></header><nav>'
        + _links()
        + "</nav><main>"
        + body
        + "</main></body></html>"
    )
    (directory / "forecast.html").write_text(html, encoding="utf-8")
    (directory / "forecast.json").write_text(
        json.dumps(bundle, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return directory / "forecast.html"
