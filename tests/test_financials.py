"""Financial expectations and error cases; runnable with unittest or pytest."""

import contextlib
import copy
import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from equity_analytics.financials import (
    FinancialDataError,
    analyze_history,
    history_from_dict,
    load_history,
)
from equity_analytics.financials.__main__ import main


def payload():
    return {
        "schema_version": 1,
        "company": {
            "name": "Test",
            "ticker": "TEST",
            "currency": "INR",
            "financial_unit": "crore",
            "statement_basis": "consolidated",
            "data_kind": "synthetic",
        },
        "as_of": "2026-09-07",
        "sources": [
            {
                "source_id": "test",
                "title": "Test fixture",
                "published_on": "2026-09-01",
                "locator": "Known arithmetic",
            }
        ],
        "annuals": [
            {
                "fiscal_year": 2024,
                "period_end": "2024-03-31",
                "source_id": "test",
                "revenue": 100,
                "ebit": 10,
                "depreciation_amortisation": 5,
                "net_income": 8,
                "net_income_to_owners": 7,
                "finance_costs": 2,
                "total_assets": 200,
                "total_liabilities": 80,
                "total_equity": 120,
                "equity_to_owners": 100,
                "current_assets": 80,
                "current_liabilities": 40,
                "cash_and_equivalents": 10,
                "total_debt": 50,
                "operating_cash_flow": 12,
                "capex": 8,
            },
            {
                "fiscal_year": 2025,
                "period_end": "2025-03-31",
                "source_id": "test",
                "revenue": 121,
                "ebit": 20,
                "depreciation_amortisation": 5,
                "net_income": 12,
                "net_income_to_owners": 11,
                "finance_costs": 4,
                "total_assets": 240,
                "total_liabilities": 100,
                "total_equity": 140,
                "equity_to_owners": 120,
                "current_assets": 90,
                "current_liabilities": 60,
                "cash_and_equivalents": 70,
                "total_debt": 60,
                "operating_cash_flow": 18,
                "capex": 9,
            },
        ],
    }


class FinancialRatioTests(unittest.TestCase):
    def test_hand_calculated_outputs_include_average_balance_returns(self):
        r = analyze_history(history_from_dict(payload()))
        m = r.years[-1].metrics
        self.assertAlmostEqual(m["revenue_growth"].value, 0.21)
        self.assertAlmostEqual(m["roe"].value, 0.10)  # 11 / average(100, 120)
        self.assertAlmostEqual(m["roa"].value, 12 / 220)
        self.assertAlmostEqual(m["roce"].value, 20 / 170)
        self.assertEqual(m["ebitda"].value, 25)
        self.assertEqual(m["net_debt"].value, -10)
        self.assertAlmostEqual(m["net_debt_to_ebitda"].value, -0.4)
        self.assertEqual(m["current_ratio"].value, 1.5)
        self.assertEqual(m["finance_cost_coverage"].value, 5)
        self.assertEqual(m["cash_flow_after_capex"].value, 9)
        self.assertAlmostEqual(m["operating_cash_flow_to_net_income"].value, 1.5)
        self.assertAlmostEqual(r.revenue_cagr.value, 0.21)
        self.assertEqual(r.cagr_intervals, 1)

    def test_first_year_returns_need_opening_balances(self):
        m = analyze_history(history_from_dict(payload())).years[0].metrics
        for name in ("roe", "roa", "roce", "revenue_growth"):
            self.assertIsNone(m[name].value)
            self.assertIsNotNone(m[name].reason)

    def test_gap_uses_elapsed_years_for_cagr_and_disables_yoy_and_returns(self):
        p = payload()
        p["annuals"][1].update(fiscal_year=2026, period_end="2026-03-31")
        r = analyze_history(history_from_dict(p))
        self.assertAlmostEqual(r.revenue_cagr.value, 0.10)  # 100 to 121 in two years
        self.assertEqual(r.cagr_intervals, 2)
        self.assertIsNone(r.years[-1].metrics["revenue_growth"].value)
        self.assertIsNone(r.years[-1].metrics["roe"].value)

    def test_losses_and_negative_equity_are_valid_but_growth_or_returns_can_be_na(self):
        p = payload()
        p["annuals"][0].update(net_income=-10, equity_to_owners=-20)
        p["annuals"][1].update(net_income=-5, ebit=-30)
        m = analyze_history(history_from_dict(p)).years[-1].metrics
        self.assertLess(m["net_margin"].value, 0)
        self.assertIsNone(m["net_income_growth"].value)
        self.assertIsNone(m["roe"].value)
        self.assertIsNone(m["net_debt_to_ebitda"].value)

    def test_zero_denominators_return_na_not_infinity(self):
        p = payload()
        p["annuals"][1].update(revenue=0, current_liabilities=0, finance_costs=0)
        m = analyze_history(history_from_dict(p)).years[-1].metrics
        for name in (
            "net_margin",
            "ebit_margin",
            "current_ratio",
            "finance_cost_coverage",
        ):
            self.assertIsNone(m[name].value)
        self.assertEqual(m["revenue_growth"].value, -1)

    def test_absent_cash_flow_is_not_zero(self):
        p = payload()
        del p["annuals"][1]["operating_cash_flow"]
        m = analyze_history(history_from_dict(p)).years[-1].metrics
        self.assertIsNone(m["cash_flow_after_capex"].value)
        self.assertIsNone(m["operating_cash_flow_to_net_income"].value)

    def test_unsorted_input_sorts_without_mutating_input(self):
        p = payload()
        p["annuals"].reverse()
        before = copy.deepcopy(p)
        h = history_from_dict(p)
        self.assertEqual([a.fiscal_year for a in h.annuals], [2024, 2025])
        self.assertEqual(p, before)

    def test_balance_sheet_mismatch_is_exposed(self):
        p = payload()
        p["annuals"][1]["total_equity"] = 150
        r = analyze_history(history_from_dict(p))
        self.assertIn("assets do not reconcile", r.years[-1].warnings[0])

    def test_huge_finite_inputs_do_not_turn_invalid_ebitda_into_valid_leverage(self):
        p = payload()
        p["annuals"][1].update(ebit=1e308, depreciation_amortisation=1e308)
        m = analyze_history(history_from_dict(p)).years[-1].metrics
        self.assertIsNone(m["ebitda"].value)
        self.assertIsNone(m["net_debt_to_ebitda"].value)


class FinancialInputTests(unittest.TestCase):
    def test_non_finite_boolean_and_text_numbers_are_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, "100", 10**400):
            with self.subTest(value_type=type(value).__name__):
                p = payload()
                p["annuals"][0]["revenue"] = value
                with self.assertRaises(FinancialDataError):
                    history_from_dict(p)

    def test_duplicate_fiscal_years_are_rejected(self):
        p = payload()
        p["annuals"].append(p["annuals"][0].copy())
        with self.assertRaisesRegex(FinancialDataError, "duplicate fiscal_year"):
            history_from_dict(p)

    def test_negative_capex_requires_correct_sign_normalization(self):
        p = payload()
        p["annuals"][0]["capex"] = -1
        with self.assertRaisesRegex(FinancialDataError, "capex must be non-negative"):
            history_from_dict(p)

    def test_bad_schema_and_unknown_keys_are_rejected(self):
        for change in ({"schema_version": True}, {"schema_version": 2}, {"extra": 1}):
            p = payload()
            p.update(change)
            with self.assertRaises(FinancialDataError):
                history_from_dict(p)
        p = payload()
        p["annuals"][0]["reveneu"] = 1
        with self.assertRaises(FinancialDataError):
            history_from_dict(p)

    def test_unknown_units_or_mixed_per_year_units_are_rejected(self):
        p = payload()
        p["company"]["financial_unit"] = "lakh"
        with self.assertRaises(FinancialDataError):
            history_from_dict(p)
        p = payload()
        p["annuals"][0]["financial_unit"] = "million"
        with self.assertRaises(FinancialDataError):
            history_from_dict(p)

    def test_nonannual_periods_changed_year_end_and_incorrect_year_are_rejected(self):
        for change in (
            {"months": 3},
            {"period_end": "2024-12-31"},
            {"period_end": "2023-03-31"},
            {"fiscal_year": "2024"},
        ):
            p = payload()
            p["annuals"][0].update(change)
            with self.assertRaises(FinancialDataError):
                history_from_dict(p)

    def test_source_dates_references_and_urls_are_checked(self):
        p = payload()
        p["as_of"] = "2025-01-01"
        with self.assertRaisesRegex(FinancialDataError, "after as_of"):
            history_from_dict(p)
        p = payload()
        p["annuals"][0]["source_id"] = "missing"
        with self.assertRaises(FinancialDataError):
            history_from_dict(p)
        p = payload()
        p["company"]["data_kind"] = "reported"
        with self.assertRaisesRegex(FinancialDataError, "source URL"):
            history_from_dict(p)
        p = payload()
        p["sources"][0]["url"] = "not-a-url"
        with self.assertRaises(FinancialDataError):
            history_from_dict(p)

    def test_json_duplicates_and_nonstandard_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', "{bad"):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(FinancialDataError):
                    load_history(path)


class FinancialWorkflowTests(unittest.TestCase):
    def test_cli_exports_metadata_raw_inputs_values_and_missing_reasons(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text(json.dumps(payload()), encoding="utf-8-sig")
            with contextlib.redirect_stdout(StringIO()):
                main([str(source), "--output-dir", str(root / "output")])
            data = json.loads((root / "output/analysis.json").read_text())
            self.assertEqual(data["history"]["sources"][0]["source_id"], "test")
            self.assertEqual(data["history"]["annuals"][0]["period_end"], "2024-03-31")
            self.assertIsNone(data["years"][0]["metrics"]["roe"]["value"])
            self.assertTrue(data["years"][0]["metrics"]["roe"]["reason"])
            self.assertIn("CFO less capex", (root / "output/analysis.md").read_text())

    def test_cli_does_not_overwrite_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "analysis.json"
            original = json.dumps(payload())
            source.write_text(original)
            with (
                contextlib.redirect_stdout(StringIO()),
                contextlib.redirect_stderr(StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                main([str(source), "--output-dir", str(root)])
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(source.read_text(), original)

    def test_five_year_demo_has_four_growth_intervals(self):
        project = Path(__file__).resolve().parents[1]
        r = analyze_history(
            load_history(project / "examples/demo_financial_history.json")
        )
        self.assertEqual(len(r.years), 5)
        self.assertEqual(r.cagr_intervals, 4)
        self.assertEqual(r.years[-1].metrics["cash_flow_after_capex"].value, 830)

    def test_tega_example_keeps_operating_ebitda_consistent_and_gaps_explicit(self):
        project = Path(__file__).resolve().parents[1]
        r = analyze_history(
            load_history(project / "examples/tega_fy2024_fy2025_income_example.json")
        )
        self.assertAlmostEqual(r.years[0].metrics["ebitda"].value, 3159.7)
        self.assertAlmostEqual(r.years[1].metrics["ebitda"].value, 3398.1)
        self.assertIsNone(r.years[1].metrics["net_debt_to_ebitda"].value)
        self.assertEqual(r.history.company.financial_unit, "million")


if __name__ == "__main__":
    unittest.main()
