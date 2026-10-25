"""P/E cross-check: the broker-style value beside a DCF, never a replacement for it."""

from math import isfinite

REQUIRED = ("name", "pe", "basis", "observed_on", "url", "note")


def _positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")


def pe_cross_check(benchmark, eps_year, eps, price, dcf_value):
    """Value at a benchmark P/E, and the P/E that the price and the DCF imply.

    Every figure uses the same EPS, so the three multiples are comparable.
    Returns no P/E value when EPS is not positive, because a P/E is then
    meaningless.
    """
    missing = [key for key in REQUIRED if key not in benchmark]
    if missing:
        raise ValueError(f"P/E benchmark is missing: {', '.join(missing)}")
    _positive("benchmark P/E", benchmark["pe"])
    _positive("market price", price)
    for name, value in (("eps", eps), ("dcf_value", dcf_value)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number")
        if not isfinite(value):
            raise ValueError(f"{name} must be finite")
    usable = eps > 0
    return {
        "benchmark": dict(benchmark),
        "eps_year": eps_year,
        "eps": eps,
        "pe_value_per_share": benchmark["pe"] * eps if usable else None,
        "market_price": price,
        "market_pe": price / eps if usable else None,
        "dcf_value_per_share": dcf_value,
        "dcf_pe": dcf_value / eps if usable else None,
    }


def pe_text(check, company):
    """One plain-language paragraph for reports."""
    b = check["benchmark"]
    if check["pe_value_per_share"] is None:
        return (
            f"P/E cross-check: FY{check['eps_year']} EPS is not positive, so a P/E "
            "value is not meaningful."
        )
    return (
        f"P/E cross-check: at the {b['name']} {b['pe']:.1f}x P/E ({b['basis']}; "
        f"{b['observed_on']}), {company}'s FY{check['eps_year']} EPS of "
        f"INR{check['eps']:,.2f} gives INR{check['pe_value_per_share']:,.2f} per share. "
        f"On the same EPS the share price is {check['market_pe']:.1f}x and the DCF "
        f"value {check['dcf_pe']:.1f}x. {b['note']}"
    )
