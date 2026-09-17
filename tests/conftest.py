"""Artificial arithmetic fixtures, independent of the retired Tega forecasts."""

import pytest

from equity_analytics.forecasting.inputs import asset_cohorts


@pytest.fixture
def linked_assumptions():
    """Build simple test inputs for either historical schema; no company outlook."""

    def make(case):
        actual = case["annuals"][-1]
        return {
            "schema_version": 1,
            "label": "Artificial arithmetic fixture for automated tests only",
            "base_year": case["base_year"],
            "revenue_growth": [0.0] * 5,
            "ebitda_margin": [0.2] * 5,
            "receivable_days": [110.0] * 5,
            "inventory_pct_revenue": [0.25] * 5,
            "payables_pct_revenue": [0.15] * 5,
            "cash_capex_pct_revenue": [0.1] * 5,
            "term_principal_repayment": [100.0] * 5,
            "lease_principal_repayment": [100.0] * 5,
            "new_lease_assets": [100.0] * 5,
            "term_interest_rate": 0.1,
            "revolver_interest_rate": 0.1,
            "lease_interest_rate": 0.1,
            "tax_rate": 0.25,
            "dividend_payout_ratio": 0.1,
            "minimum_cash": 500.0,
            "revolver_limit": 4000.0,
            "sweep_excess_cash_to_revolver": True,
            "tangible_capex_share": 0.9,
            "commissioning_fraction": 0.5,
            "new_ppe_life_years": 8.0,
            "new_intangible_life_years": 4.0,
            "new_rou_life_years": 6.0,
            "opening_remaining_life_years": {
                c["name"]: None if c["name"] == "ppe_land" else 3
                for c in asset_cohorts(case)
            },
            "joint_venture_profit": 0.0,
            "joint_venture_dividend": 0.0,
            "dcf": {
                "wacc": 0.12,
                "terminal_growth": 0.04,
                "terminal_roic": 0.15,
                "joint_venture_value": actual["assets"]["joint_venture"],
                "investment_property_value": actual["assets"]["investment_property"],
                "noncontrolling_interest_value": 0.0,
            },
            "notes": [
                (
                    "Deliberately artificial, flat inputs for accounting tests. "
                    "Not Tega forecasts, guidance or valuation assumptions."
                )
            ],
        }

    return make
