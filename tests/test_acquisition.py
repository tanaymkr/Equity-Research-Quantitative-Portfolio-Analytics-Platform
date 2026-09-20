"""Financial regression checks for acquisition timing, claims and funding."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from equity_analytics.acquisition import AcquisitionInputError, build_acquisition_model
from equity_analytics.acquisition.history import load_acquisition_facts

ROOT = Path(__file__).resolve().parents[1]


class AcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts, _, _ = load_acquisition_facts(
            ROOT / "examples/tega_molycop_facts.json"
        )
        cls.assumptions = json.loads(
            (ROOT / "examples/tega_molycop_assumptions.json").read_text()
        )
        cls.base = build_acquisition_model(cls.facts, cls.assumptions)

    def model(self, changes=None, facts=None):
        return build_acquisition_model(facts or self.facts, changes or self.assumptions)

    def test_ten_owned_months_nine_future_months_and_no_june_double_count(self):
        q = self.facts["q1_fy2027"]
        r = self.base["molycop_forecast_inr_m"][0]
        fx = self.facts["currency_basis"]["inr_per_usd"]
        self.assertEqual(r["owned_months_in_fiscal_year"], 10)
        self.assertEqual(r["period_years"], 0.75)
        self.assertAlmostEqual(
            r["revenue"] + q["molycop_revenue_inr_m"],
            r["owned_fiscal_year_revenue"],
        )
        self.assertAlmostEqual(
            r["operating_ebitda"] + q["molycop_operating_ebitda_inr_m"],
            191 * fx * 1.04 * 10 / 12,
        )
        self.assertAlmostEqual(r["discount_years"], 274 / 365)

    def test_other_income_not_used_as_operating_ebitda(self):
        q = self.facts["q1_fy2027"]
        l = self.base["legacy_forecast_inr_m"][0]
        self.assertAlmostEqual(
            l["full_fiscal_year_operating_ebitda"] - l["operating_ebitda"],
            1011.29 - 256.52,
        )
        self.assertAlmostEqual(q["molycop_operating_ebitda_inr_m"], 1628.12 - (-82.39))

    def test_group_equity_uses_matching_ownership_for_senior_claims(self):
        b = self.base["equity_bridge"]
        attributable_claims = b["legacy_net_debt_inr_m"] + b[
            "molycop_ordinary_ownership"
        ] * (
            672.5 * 94.97
            + 270 * 94.97
            + 50 * 94.97
            + b["earnout_present_value_full_inr_m"]
        )
        self.assertAlmostEqual(
            b["total_attributable_claims_inr_m"], attributable_claims
        )
        self.assertAlmostEqual(
            b["raw_tega_equity_inr_m"],
            b["group_enterprise_value_inr_m"]
            - attributable_claims
            + b["nonoperating_assets_inr_m"],
        )
        f = deepcopy(self.facts)
        f["q1_fy2027"]["molycop_net_debt_inr_m"] += 10 * 94.97
        reduced = self.model(facts=f)["equity_bridge"]["value_per_share_inr"]
        expected_loss = (
            10
            * b["fx_inr_per_usd"]
            * b["molycop_ordinary_ownership"]
            / (b["issued_shares"] / 1e6)
        )
        self.assertAlmostEqual(b["value_per_share_inr"] - reduced, expected_loss)

    def test_parent_loan_cash_and_debt_cancel_in_opening_net_debt(self):
        f = deepcopy(self.facts)
        f["deal"]["parent_acquisition_loan_inr_m"] += 500
        changed = self.model(facts=f)
        self.assertAlmostEqual(
            self.base["equity_bridge"]["legacy_net_debt_inr_m"],
            changed["equity_bridge"]["legacy_net_debt_inr_m"],
        )
        self.assertAlmostEqual(
            self.base["equity_bridge"]["value_per_share_inr"],
            changed["equity_bridge"]["value_per_share_inr"],
        )

    def test_purchase_price_and_escrow_are_not_deducted_again(self):
        f = deepcopy(self.facts)
        f["deal"]["cash_purchase_at_close_inr_m_approx"] += 10
        f["deal"]["escrow_included_in_cash_purchase_inr_m"] += 2
        f["deal"]["headline_enterprise_value_inr_m_approx"] += 100
        self.assertEqual(
            self.base["equity_bridge"], self.model(facts=f)["equity_bridge"]
        )

    def test_parent_contribution_changes_value_once(self):
        f = deepcopy(self.facts)
        d = f["deal"]
        # Increase contribution while holding the ordinary ownership ratio fixed.
        ratio = (
            d["apollo_ordinary_contribution_inr_m"]
            / d["tega_ordinary_contribution_inr_m"]
        )
        d["tega_ordinary_contribution_inr_m"] += 94.97
        d["apollo_ordinary_contribution_inr_m"] += 94.97 * ratio
        result = self.model(facts=f)
        expected = 94.97 / (75127698 / 1e6)
        self.assertAlmostEqual(
            self.base["equity_bridge"]["value_per_share_inr"]
            - result["equity_bridge"]["value_per_share_inr"],
            expected,
        )

    def test_share_count_and_pending_issue_include_cash_together(self):
        b = self.base["equity_bridge"]
        self.assertEqual(b["issued_shares"], 75127698)
        expected = (b["raw_tega_equity_inr_m"] + 953.99939) / (
            (75127698 + 478435) / 1e6
        )
        self.assertAlmostEqual(
            b["pending_issue_pro_forma_value_per_share_inr"], expected
        )
        f = deepcopy(self.facts)
        f["tega_fy2026"]["shares"] *= 2
        self.assertAlmostEqual(
            self.model(facts=f)["equity_bridge"]["value_per_share_inr"],
            b["value_per_share_inr"] / 2,
        )

    def test_preference_pik_is_non_cash_and_not_deducted_twice(self):
        a = deepcopy(self.assumptions)
        a["shared"]["preference_assumed_pik_rate"] = 0.15
        result = self.model(a)
        self.assertEqual(result["equity_bridge"], self.base["equity_bridge"])
        self.assertGreater(
            result["financing_schedule"][-1][
                "preference_closing_assumed_balance_inr_m"
            ],
            self.base["financing_schedule"][-1][
                "preference_closing_assumed_balance_inr_m"
            ],
        )
        for row in self.base["financing_schedule"][:-1]:
            self.assertEqual(row["preference_cash_return_inr_m"], 0)
        self.assertGreater(
            self.base["financing_schedule"][-1]["preference_cash_return_inr_m"], 0
        )

    def test_ppa_book_amortization_does_not_create_automatic_tax_shield(self):
        rate = self.assumptions["shared"]["earned_income_tax_rate_molycop"]
        for row in self.base["molycop_forecast_inr_m"]:
            taxable = (
                row["ebit"] - row["integration_cash_cost"] + row["ppa_amortization"]
            )
            self.assertAlmostEqual(row["unlevered_cash_tax"], max(taxable, 0) * rate)
        a = deepcopy(self.assumptions)
        a["shared"]["molycop_ppa_tax_deductible_fraction"] = 1
        self.assertGreater(
            self.model(a)["equity_bridge"]["value_per_share_inr"],
            self.base["equity_bridge"]["value_per_share_inr"],
        )

    def test_asset_and_financing_rollforwards(self):
        for row in (
            self.base["legacy_forecast_inr_m"] + self.base["molycop_forecast_inr_m"]
        ):
            self.assertAlmostEqual(
                row["closing_asset_book_proxy"],
                row["opening_depreciable_book_proxy"]
                + row["opening_cwip_proxy"]
                + row["nondepreciable_land"]
                + row["cash_capex"]
                + row["new_lease_assets"]
                - row["da"],
            )
            self.assertGreaterEqual(row["closing_asset_book_proxy"], 0)
        for row in self.base["financing_schedule"]:
            self.assertAlmostEqual(row["parent_debt_rollforward_residual"], 0)
            self.assertAlmostEqual(row["molycop_net_debt_rollforward_residual"], 0)
            self.assertGreaterEqual(row["parent_closing_cash_inr_m"], 500 - 1e-8)
            self.assertGreaterEqual(row["molycop_closing_net_bank_debt_inr_m"], -1e-8)

    def test_savings_are_not_added_to_first_year_guidance_twice(self):
        a = deepcopy(self.assumptions)
        a["scenarios"]["base"]["molycop_cost_synergies_inr_m"][0] += 3
        changed = self.model(a)["molycop_forecast_inr_m"][0]
        self.assertAlmostEqual(
            changed["owned_fiscal_year_operating_ebitda"],
            self.base["molycop_forecast_inr_m"][0][
                "owned_fiscal_year_operating_ebitda"
            ],
        )

    def test_terminal_reinvestment_is_required(self):
        for key in ("group_dcf_inr_m",):
            v = self.base[key]
            self.assertAlmostEqual(
                v["terminal_fcff"],
                v["terminal_nopat"] * (1 - v["terminal_growth"] / v["terminal_roic"]),
            )

    def test_claims_and_discount_sensitivity_have_expected_direction(self):
        value = self.base["equity_bridge"]["value_per_share_inr"]
        for scope, key, delta in (
            ("shared", "preference_fair_value_inr_m", 50),
            ("shared", "molycop_other_claims_inr_m", 20),
            ("scenario", "group_wacc_inr", 0.01),
        ):
            a = deepcopy(self.assumptions)
            target = a["shared"] if scope == "shared" else a["scenarios"]["base"]
            target[key] += delta
            with self.subTest(key=key):
                self.assertLess(
                    self.model(a)["equity_bridge"]["value_per_share_inr"], value
                )

    def test_invalid_financial_inputs_rejected(self):
        for key, value in (
            ("group_wacc_inr", 0.01),
            ("earnout_inr_m", 121 * 94.97),
            ("group_terminal_roic", 0.01),
            ("earnout_payment_date", "2031-01-01"),
        ):
            a = deepcopy(self.assumptions)
            a["scenarios"]["base"][key] = value
            with self.subTest(key=key), self.assertRaises(AcquisitionInputError):
                self.model(a)
        a = deepcopy(self.assumptions)
        a["shared"]["preference_fair_value_inr_m"] = float("nan")
        with self.assertRaises(AcquisitionInputError):
            self.model(a)

    def test_all_cases_reconcile_and_report_downside_shortfall(self):
        values = []
        for case in ("downside", "base", "upside"):
            result = build_acquisition_model(self.facts, self.assumptions, case)
            self.assertLess(max(abs(v) for v in result["checks"].values()), 0.02)
            values.append(result["equity_bridge"]["value_per_share_inr"])
        self.assertLess(values[0], values[1])
        self.assertLess(values[1], values[2])
        self.assertLess(
            build_acquisition_model(self.facts, self.assumptions, "downside")[
                "equity_bridge"
            ]["raw_tega_equity_inr_m"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
