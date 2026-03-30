#!/usr/bin/env python3
"""Tests for gas_gauge.py"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gas_gauge


class TestParseUsage(unittest.TestCase):
    def test_empty_data(self):
        result = gas_gauge.parse_usage(None)
        self.assertEqual(result["gross"], 0)
        self.assertEqual(result["net"], 0)

    def test_empty_usage_items(self):
        result = gas_gauge.parse_usage({"usageItems": []})
        self.assertEqual(result["gross"], 0)
        self.assertEqual(result["net"], 0)

    def test_single_item(self):
        data = {
            "usageItems": [
                {
                    "product": "Copilot",
                    "model": "gpt-4o",
                    "grossQuantity": 42,
                    "netQuantity": 40,
                }
            ]
        }
        result = gas_gauge.parse_usage(data)
        self.assertEqual(result["gross"], 42)
        self.assertEqual(result["net"], 40)
        self.assertEqual(result["by_model"]["gpt-4o"], 42)
        self.assertEqual(result["by_product"]["Copilot"], 42)

    def test_multiple_items(self):
        data = {
            "usageItems": [
                {"product": "Copilot", "model": "gpt-4o", "grossQuantity": 10, "netQuantity": 10},
                {"product": "Copilot", "model": "claude-3.5-sonnet", "grossQuantity": 5, "netQuantity": 5},
                {"product": "Copilot Agent", "model": "gpt-4o", "grossQuantity": 20, "netQuantity": 18},
            ]
        }
        result = gas_gauge.parse_usage(data)
        self.assertEqual(result["gross"], 35)
        self.assertEqual(result["net"], 33)
        self.assertEqual(result["by_model"]["gpt-4o"], 30)
        self.assertEqual(result["by_model"]["claude-3.5-sonnet"], 5)
        self.assertEqual(result["by_product"]["Copilot"], 15)
        self.assertEqual(result["by_product"]["Copilot Agent"], 20)

    def test_missing_quantity_fields(self):
        data = {
            "usageItems": [
                {"product": "Copilot", "model": "gpt-4o"},
            ]
        }
        result = gas_gauge.parse_usage(data)
        self.assertEqual(result["gross"], 0)
        self.assertEqual(result["net"], 0)


class TestEstimateRemainingTasks(unittest.TestCase):
    def test_zero_remaining(self):
        result = gas_gauge.estimate_remaining_tasks(0)
        for task_type in result:
            self.assertEqual(result[task_type]["count"], 0)

    def test_simple_tasks(self):
        result = gas_gauge.estimate_remaining_tasks(100)
        simple_cost = gas_gauge.TASK_COSTS["simple"]["requests"]
        self.assertEqual(result["simple"]["count"], 100 // simple_cost)

    def test_complex_tasks(self):
        result = gas_gauge.estimate_remaining_tasks(150)
        complex_cost = gas_gauge.TASK_COSTS["complex"]["requests"]
        self.assertEqual(result["complex"]["count"], 150 // complex_cost)

    def test_large_remaining(self):
        result = gas_gauge.estimate_remaining_tasks(1000)
        self.assertGreater(result["simple"]["count"], result["complex"]["count"])


class TestDrawGauge(unittest.TestCase):
    def test_empty_gauge(self):
        bar = gas_gauge.draw_gauge(0, 100)
        self.assertIn("[", bar)
        self.assertIn("]", bar)

    def test_full_gauge(self):
        bar = gas_gauge.draw_gauge(100, 100)
        self.assertIn("[", bar)
        self.assertIn("]", bar)

    def test_zero_quota(self):
        bar = gas_gauge.draw_gauge(0, 0)
        self.assertIsNotNone(bar)

    def test_no_color_gauge(self):
        bar = gas_gauge.draw_gauge(50, 100, no_color=True)
        self.assertNotIn("\033[", bar)
        self.assertIn("[", bar)
        self.assertIn("]", bar)

    def test_colored_gauge_has_ansi(self):
        bar = gas_gauge.draw_gauge(50, 100, no_color=False)
        self.assertIn("\033[", bar)


class TestPlanQuotas(unittest.TestCase):
    def test_all_plans_present(self):
        for plan in ["free", "pro", "individual", "business", "enterprise"]:
            self.assertIn(plan, gas_gauge.PLAN_QUOTAS)
            self.assertGreater(gas_gauge.PLAN_QUOTAS[plan], 0)

    def test_free_plan_lowest(self):
        self.assertLessEqual(gas_gauge.PLAN_QUOTAS["free"], gas_gauge.PLAN_QUOTAS["pro"])

    def test_enterprise_highest(self):
        for plan, quota in gas_gauge.PLAN_QUOTAS.items():
            if plan != "enterprise":
                self.assertLessEqual(quota, gas_gauge.PLAN_QUOTAS["enterprise"])


class TestGetHeaders(unittest.TestCase):
    def test_headers_contain_auth(self):
        headers = gas_gauge.get_headers("mytoken")
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], "Bearer mytoken")

    def test_headers_contain_accept(self):
        headers = gas_gauge.get_headers("mytoken")
        self.assertIn("Accept", headers)


class TestFormatTimePeriod(unittest.TestCase):
    def test_valid_date(self):
        result = gas_gauge.format_time_period(2025, 6)
        self.assertIn("2025", result)

    def test_january(self):
        result = gas_gauge.format_time_period(2025, 1)
        self.assertIn("January", result)

    def test_december(self):
        result = gas_gauge.format_time_period(2025, 12)
        self.assertIn("December", result)


class TestAPIFunctions(unittest.TestCase):
    @patch("gas_gauge.requests.get")
    def test_get_authenticated_user(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"login": "testuser"}
        mock_get.return_value = mock_resp
        user = gas_gauge.get_authenticated_user("token123")
        self.assertEqual(user["login"], "testuser")
        mock_resp.raise_for_status.assert_called_once()

    @patch("gas_gauge.requests.get")
    def test_get_user_billing_usage_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        result = gas_gauge.get_user_billing_usage("token123")
        self.assertIsNone(result)

    @patch("gas_gauge.requests.get")
    def test_get_org_billing_usage_forbidden(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp
        result = gas_gauge.get_org_billing_usage("token123", "my-org")
        self.assertIsNone(result)

    @patch("gas_gauge.requests.get")
    def test_get_user_billing_usage_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"usageItems": []}
        mock_get.return_value = mock_resp
        result = gas_gauge.get_user_billing_usage("token123")
        self.assertEqual(result, {"usageItems": []})

    @patch("gas_gauge.requests.get")
    def test_get_org_billing_usage_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"usageItems": []}
        mock_get.return_value = mock_resp
        result = gas_gauge.get_org_billing_usage("token123", "my-org")
        self.assertEqual(result, {"usageItems": []})


class TestActionsBilling(unittest.TestCase):
    @patch("gas_gauge.requests.get")
    def test_get_user_actions_billing_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_minutes_used": 450,
            "included_minutes": 2000,
            "total_paid_minutes_used": 0,
        }
        mock_get.return_value = mock_resp
        result = gas_gauge.get_user_actions_billing("token123")
        self.assertEqual(result["total_minutes_used"], 450)

    @patch("gas_gauge.requests.get")
    def test_get_user_actions_billing_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        result = gas_gauge.get_user_actions_billing("token123")
        self.assertIsNone(result)

    @patch("gas_gauge.requests.get")
    def test_get_user_actions_billing_forbidden(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp
        result = gas_gauge.get_user_actions_billing("token123")
        self.assertIsNone(result)

    @patch("gas_gauge.requests.get")
    def test_get_org_actions_billing_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_minutes_used": 1200,
            "included_minutes": 3000,
            "total_paid_minutes_used": 50,
        }
        mock_get.return_value = mock_resp
        result = gas_gauge.get_org_actions_billing("token123", "my-org")
        self.assertEqual(result["total_minutes_used"], 1200)

    @patch("gas_gauge.requests.get")
    def test_get_org_actions_billing_forbidden(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp
        result = gas_gauge.get_org_actions_billing("token123", "my-org")
        self.assertIsNone(result)


class TestParseActionsUsage(unittest.TestCase):
    def test_none_data(self):
        result = gas_gauge.parse_actions_usage(None)
        self.assertEqual(result["minutes_used"], 0)
        self.assertEqual(result["included_minutes"], 0)
        self.assertEqual(result["total_paid_minutes_used"], 0)
        self.assertEqual(result["minutes_used_breakdown"], {})

    def test_full_data(self):
        data = {
            "total_minutes_used": 450,
            "included_minutes": 2000,
            "total_paid_minutes_used": 0,
            "minutes_used_breakdown": {"UBUNTU": 400, "MACOS": 50},
        }
        result = gas_gauge.parse_actions_usage(data)
        self.assertEqual(result["minutes_used"], 450)
        self.assertEqual(result["included_minutes"], 2000)
        self.assertEqual(result["total_paid_minutes_used"], 0)
        self.assertEqual(result["minutes_used_breakdown"]["UBUNTU"], 400)
        self.assertEqual(result["minutes_used_breakdown"]["MACOS"], 50)

    def test_overage_data(self):
        data = {
            "total_minutes_used": 2100,
            "included_minutes": 2000,
            "total_paid_minutes_used": 100,
        }
        result = gas_gauge.parse_actions_usage(data)
        self.assertEqual(result["minutes_used"], 2100)
        self.assertEqual(result["total_paid_minutes_used"], 100)

    def test_missing_fields_default_to_zero(self):
        result = gas_gauge.parse_actions_usage({})
        self.assertEqual(result["minutes_used"], 0)
        self.assertEqual(result["included_minutes"], 0)


class TestPrintActionsGauge(unittest.TestCase):
    def test_basic_output(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            gas_gauge.print_actions_gauge(
                minutes_used=450,
                included_minutes=2000,
                total_paid_minutes_used=0,
                login="testuser",
                no_color=True,
            )
        output = buf.getvalue()
        self.assertIn("Actions", output)
        self.assertIn("450", output)
        self.assertIn("2,000", output)

    def test_overage_shown(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            gas_gauge.print_actions_gauge(
                minutes_used=2100,
                included_minutes=2000,
                total_paid_minutes_used=100,
                login="testuser",
                no_color=True,
            )
        output = buf.getvalue()
        self.assertIn("100", output)
        self.assertIn("$", output)

    def test_org_scope_shown(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            gas_gauge.print_actions_gauge(
                minutes_used=100,
                included_minutes=3000,
                total_paid_minutes_used=0,
                login="testuser",
                org="my-org",
                no_color=True,
            )
        output = buf.getvalue()
        self.assertIn("Org: my-org", output)


class TestCLIFlags(unittest.TestCase):
    @patch("gas_gauge.get_authenticated_user")
    @patch("gas_gauge.get_user_billing_usage")
    @patch("gas_gauge.get_user_actions_billing")
    def test_copilot_only_flag(self, mock_actions, mock_copilot, mock_user):
        mock_user.return_value = {"login": "testuser"}
        mock_copilot.return_value = {"usageItems": []}
        mock_actions.return_value = None

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("sys.argv", ["gas_gauge.py", "--token", "tok", "--copilot-only", "--no-color"]):
                gas_gauge.main()

        mock_actions.assert_not_called()
        output = buf.getvalue()
        self.assertIn("Copilot Gas Gauge", output)

    @patch("gas_gauge.get_authenticated_user")
    @patch("gas_gauge.get_user_billing_usage")
    @patch("gas_gauge.get_user_actions_billing")
    def test_actions_only_flag(self, mock_actions, mock_copilot, mock_user):
        mock_user.return_value = {"login": "testuser"}
        mock_copilot.return_value = {"usageItems": []}
        mock_actions.return_value = {
            "total_minutes_used": 100,
            "included_minutes": 2000,
            "total_paid_minutes_used": 0,
        }

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("sys.argv", ["gas_gauge.py", "--token", "tok", "--actions-only", "--no-color"]):
                gas_gauge.main()

        mock_copilot.assert_not_called()
        output = buf.getvalue()
        self.assertIn("Actions", output)

    def test_actions_only_and_copilot_only_mutual_exclusion(self):
        with patch("sys.argv", ["gas_gauge.py", "--token", "tok", "--actions-only", "--copilot-only"]):
            with self.assertRaises(SystemExit) as cm:
                gas_gauge.main()
            self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
