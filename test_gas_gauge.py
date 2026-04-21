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

    def test_float_values_are_normalized_to_int(self):
        data = {
            "total_minutes_used": 450.7,
            "included_minutes": 2000.0,
            "total_paid_minutes_used": 5.3,
        }
        result = gas_gauge.parse_actions_usage(data)
        self.assertIsInstance(result["minutes_used"], int)
        self.assertEqual(result["minutes_used"], 450)
        self.assertIsInstance(result["included_minutes"], int)
        self.assertEqual(result["included_minutes"], 2000)
        self.assertIsInstance(result["total_paid_minutes_used"], int)
        self.assertEqual(result["total_paid_minutes_used"], 5)


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

    def test_providers_only_skips_github_token_check(self):
        """--providers-only should not require GITHUB_TOKEN."""
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("sys.argv", ["gas_gauge.py", "--providers-only",
                                    "--providers", "anthropic", "--no-color"]):
                # Should NOT exit(1) even though --token is absent
                gas_gauge.main()
        output = buf.getvalue()
        self.assertIn("Anthropic", output)

    def test_providers_invalid_name(self):
        with patch("sys.argv", ["gas_gauge.py", "--token", "tok",
                                "--providers", "nonexistent_ai"]):
            with self.assertRaises(SystemExit) as cm:
                gas_gauge.main()
            self.assertEqual(cm.exception.code, 1)


class TestProviderConfig(unittest.TestCase):
    def test_all_expected_providers_present(self):
        for pid in ["openai", "anthropic", "deepseek", "perplexity", "gemini"]:
            self.assertIn(pid, gas_gauge.PROVIDERS)

    def test_providers_have_required_fields(self):
        for pid, cfg in gas_gauge.PROVIDERS.items():
            self.assertIn("name", cfg, f"{pid} missing 'name'")
            self.assertIn("env_var", cfg, f"{pid} missing 'env_var'")
            self.assertIn("limit_env_var", cfg, f"{pid} missing 'limit_env_var'")
            self.assertIn("supported", cfg, f"{pid} missing 'supported'")
            self.assertIn("billing_type", cfg, f"{pid} missing 'billing_type'")

    def test_unsupported_providers_have_note(self):
        for pid, cfg in gas_gauge.PROVIDERS.items():
            if not cfg.get("supported"):
                self.assertIn("note", cfg, f"{pid} is unsupported but has no 'note'")

    def test_all_provider_ids_list(self):
        self.assertEqual(set(gas_gauge.ALL_PROVIDER_IDS), set(gas_gauge.PROVIDERS.keys()))


class TestParseOpenAIUsage(unittest.TestCase):
    def test_none_returns_zeros(self):
        result = gas_gauge.parse_openai_usage(None)
        self.assertEqual(result["cost_usd"], 0.0)
        self.assertEqual(result["total_tokens"], 0)
        self.assertEqual(result["by_model"], {})

    def test_empty_dict_returns_zeros(self):
        result = gas_gauge.parse_openai_usage({})
        self.assertEqual(result["cost_usd"], 0.0)

    def test_total_usage_converted_from_cents(self):
        data = {"total_usage": 1234, "daily_costs": []}
        result = gas_gauge.parse_openai_usage(data)
        self.assertAlmostEqual(result["cost_usd"], 12.34)

    def test_by_model_aggregated_from_daily_costs(self):
        data = {
            "total_usage": 2000,
            "daily_costs": [
                {
                    "timestamp": 1704067200,
                    "line_items": [
                        {"name": "GPT-4 Turbo", "cost": 1000},
                        {"name": "GPT-3.5 Turbo", "cost": 500},
                    ],
                },
                {
                    "timestamp": 1704153600,
                    "line_items": [
                        {"name": "GPT-4 Turbo", "cost": 500},
                    ],
                },
            ],
        }
        result = gas_gauge.parse_openai_usage(data)
        self.assertAlmostEqual(result["by_model"]["GPT-4 Turbo"], 15.0)
        self.assertAlmostEqual(result["by_model"]["GPT-3.5 Turbo"], 5.0)

    def test_missing_cost_field_defaults_to_zero(self):
        data = {
            "total_usage": 0,
            "daily_costs": [
                {"timestamp": 1704067200, "line_items": [{"name": "GPT-4"}]},
            ],
        }
        result = gas_gauge.parse_openai_usage(data)
        self.assertAlmostEqual(result["by_model"].get("GPT-4", 0.0), 0.0)


class TestParseDeepSeekBalance(unittest.TestCase):
    def test_none_returns_defaults(self):
        result = gas_gauge.parse_deepseek_balance(None)
        self.assertEqual(result["balance"], 0.0)
        self.assertEqual(result["currency"], "USD")
        self.assertFalse(result["is_available"])

    def test_empty_dict_returns_defaults(self):
        result = gas_gauge.parse_deepseek_balance({})
        self.assertEqual(result["balance"], 0.0)

    def test_usd_balance_parsed(self):
        data = {
            "is_available": True,
            "balance_infos": [
                {"currency": "USD", "total_balance": "45.00",
                 "granted_balance": "0.00", "topped_up_balance": "45.00"},
            ],
        }
        result = gas_gauge.parse_deepseek_balance(data)
        self.assertAlmostEqual(result["balance"], 45.0)
        self.assertEqual(result["currency"], "USD")
        self.assertTrue(result["is_available"])

    def test_cny_balance_parsed(self):
        data = {
            "is_available": True,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "100.00"},
            ],
        }
        result = gas_gauge.parse_deepseek_balance(data)
        self.assertAlmostEqual(result["balance"], 100.0)
        self.assertEqual(result["currency"], "CNY")

    def test_invalid_balance_value_defaults_to_zero(self):
        data = {
            "is_available": True,
            "balance_infos": [{"currency": "USD", "total_balance": "not-a-number"}],
        }
        result = gas_gauge.parse_deepseek_balance(data)
        self.assertEqual(result["balance"], 0.0)


class TestProviderAPIFunctions(unittest.TestCase):
    @patch("gas_gauge.requests.get")
    def test_get_openai_usage_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"total_usage": 500, "daily_costs": []}
        mock_get.return_value = mock_resp
        result = gas_gauge.get_openai_usage("sk-test")
        self.assertEqual(result["total_usage"], 500)

    @patch("gas_gauge.requests.get")
    def test_get_openai_usage_unauthorized(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp
        result = gas_gauge.get_openai_usage("bad-key")
        self.assertIsNone(result)

    @patch("gas_gauge.requests.get")
    def test_get_openai_usage_forbidden(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp
        result = gas_gauge.get_openai_usage("bad-key")
        self.assertIsNone(result)

    @patch("gas_gauge.requests.get")
    def test_get_deepseek_balance_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "is_available": True,
            "balance_infos": [{"currency": "USD", "total_balance": "50.00"}],
        }
        mock_get.return_value = mock_resp
        result = gas_gauge.get_deepseek_balance("sk-test")
        self.assertTrue(result["is_available"])

    @patch("gas_gauge.requests.get")
    def test_get_deepseek_balance_unauthorized(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp
        result = gas_gauge.get_deepseek_balance("bad-key")
        self.assertIsNone(result)

    @patch("gas_gauge.requests.get")
    def test_get_deepseek_balance_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        result = gas_gauge.get_deepseek_balance("bad-key")
        self.assertIsNone(result)


class TestFetchProviderUsage(unittest.TestCase):
    def test_unknown_provider_returns_unavailable(self):
        result = gas_gauge.fetch_provider_usage("unknown_xyz")
        self.assertFalse(result.get("available", True))

    def test_unsupported_provider_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            result = gas_gauge.fetch_provider_usage("anthropic")
        self.assertFalse(result.get("available", True))
        self.assertIn("note", result)
        self.assertFalse(result.get("api_key_set", True))

    def test_unsupported_provider_with_api_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            result = gas_gauge.fetch_provider_usage("anthropic")
        self.assertFalse(result.get("available", True))
        self.assertTrue(result.get("api_key_set", False))

    def test_supported_provider_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            result = gas_gauge.fetch_provider_usage("openai")
        self.assertFalse(result.get("available", True))
        self.assertFalse(result.get("api_key_set", True))

    @patch("gas_gauge.get_openai_usage")
    def test_openai_api_returns_none_marks_unavailable(self, mock_fetch):
        mock_fetch.return_value = None
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            result = gas_gauge.fetch_provider_usage("openai")
        self.assertFalse(result.get("available", True))

    @patch("gas_gauge.get_openai_usage")
    def test_openai_success_returns_available(self, mock_fetch):
        mock_fetch.return_value = {"total_usage": 1234, "daily_costs": []}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test",
                                     "OPENAI_MONTHLY_LIMIT": "50.0"}):
            result = gas_gauge.fetch_provider_usage("openai")
        self.assertTrue(result.get("available", False))
        self.assertAlmostEqual(result["cost"], 12.34)
        self.assertAlmostEqual(result["limit"], 50.0)

    @patch("gas_gauge.get_deepseek_balance")
    def test_deepseek_success_returns_available(self, mock_fetch):
        mock_fetch.return_value = {
            "is_available": True,
            "balance_infos": [{"currency": "USD", "total_balance": "45.00"}],
        }
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            result = gas_gauge.fetch_provider_usage("deepseek")
        self.assertTrue(result.get("available", False))
        self.assertAlmostEqual(result["balance"], 45.0)


class TestPrintProviderGauge(unittest.TestCase):
    def _capture(self, usage, no_color=True):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            gas_gauge.print_provider_gauge(usage, no_color=no_color)
        return buf.getvalue()

    def test_unavailable_shows_warning(self):
        output = self._capture({
            "provider_id": "anthropic",
            "name": "Anthropic",
            "available": False,
            "api_key_set": False,
            "note": "No public API available.",
        })
        self.assertIn("Anthropic", output)
        self.assertIn("⚠️", output)
        self.assertIn("No public API available.", output)

    def test_unavailable_no_key_shows_env_var_hint(self):
        output = self._capture({
            "provider_id": "openai",
            "name": "OpenAI",
            "available": False,
            "api_key_set": False,
            "note": "Set OPENAI_API_KEY to enable.",
        })
        self.assertIn("OPENAI_API_KEY", output)

    def test_cost_gauge_with_limit(self):
        output = self._capture({
            "provider_id": "openai",
            "name": "OpenAI",
            "available": True,
            "billing_type": "cost",
            "cost": 12.45,
            "limit": 50.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "by_model": {"GPT-4 Turbo": 10.0, "GPT-3.5 Turbo": 2.45},
        })
        self.assertIn("OpenAI", output)
        self.assertIn("12.45", output)
        self.assertIn("50.00", output)

    def test_cost_gauge_without_limit_shows_hint(self):
        output = self._capture({
            "provider_id": "openai",
            "name": "OpenAI",
            "available": True,
            "billing_type": "cost",
            "cost": 5.0,
            "limit": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "by_model": {},
        })
        self.assertIn("OPENAI_MONTHLY_LIMIT", output)

    def test_balance_gauge_with_limit(self):
        output = self._capture({
            "provider_id": "deepseek",
            "name": "DeepSeek",
            "available": True,
            "billing_type": "balance",
            "balance": 45.0,
            "currency": "USD",
            "limit": 50.0,
            "is_available": True,
        })
        self.assertIn("DeepSeek", output)
        self.assertIn("45.0", output)

    def test_balance_gauge_without_limit_shows_hint(self):
        output = self._capture({
            "provider_id": "deepseek",
            "name": "DeepSeek",
            "available": True,
            "billing_type": "balance",
            "balance": 45.0,
            "currency": "USD",
            "limit": None,
            "is_available": True,
        })
        self.assertIn("DEEPSEEK_MONTHLY_LIMIT", output)

    def test_token_counts_shown_when_available(self):
        output = self._capture({
            "provider_id": "openai",
            "name": "OpenAI",
            "available": True,
            "billing_type": "cost",
            "cost": 1.0,
            "limit": None,
            "input_tokens": 100000,
            "output_tokens": 20000,
            "total_tokens": 120000,
            "by_model": {},
        })
        self.assertIn("120,000", output)
        self.assertIn("100,000", output)
        self.assertIn("20,000", output)

    def test_by_model_breakdown_shown(self):
        output = self._capture({
            "provider_id": "openai",
            "name": "OpenAI",
            "available": True,
            "billing_type": "cost",
            "cost": 15.0,
            "limit": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "by_model": {"GPT-4 Turbo": 10.0, "GPT-3.5 Turbo": 5.0},
        })
        self.assertIn("GPT-4 Turbo", output)
        self.assertIn("GPT-3.5 Turbo", output)


# ─── Session Analytics Tests ──────────────────────────────────────────────────

import tempfile
import io
from contextlib import redirect_stdout


class TestParseCwdFromYaml(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(gas_gauge._parse_cwd_from_yaml("cwd: /home/user/proj\n"),
                         "/home/user/proj")

    def test_trailing_comment(self):
        self.assertEqual(gas_gauge._parse_cwd_from_yaml("cwd: /home/user/proj # workspace\n"),
                         "/home/user/proj")

    def test_single_quotes(self):
        self.assertEqual(gas_gauge._parse_cwd_from_yaml("cwd: '/home/user/my project'\n"),
                         "/home/user/my project")

    def test_double_quotes(self):
        self.assertEqual(gas_gauge._parse_cwd_from_yaml('cwd: "/home/user/proj"\n'),
                         "/home/user/proj")

    def test_missing_key(self):
        self.assertIsNone(gas_gauge._parse_cwd_from_yaml("name: myproject\n"))

    def test_empty_value(self):
        self.assertIsNone(gas_gauge._parse_cwd_from_yaml("cwd: \n"))

    def test_multiline_finds_cwd(self):
        yaml = "name: proj\ncwd: /tmp/proj\nother: val\n"
        self.assertEqual(gas_gauge._parse_cwd_from_yaml(yaml), "/tmp/proj")


class TestParseCopilotEventsFile(unittest.TestCase):
    def _make_events_file(self, lines):
        import json as _json
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "events.jsonl")
        with open(path, "w") as f:
            for obj in lines:
                f.write(_json.dumps(obj) + "\n")
        return gas_gauge.Path(path)

    def test_empty_file(self):
        path = self._make_events_file([])
        self.assertEqual(gas_gauge._parse_copilot_events_file(path), [])

    def test_single_call(self):
        path = self._make_events_file([
            {"type": "session.model_change", "data": {"newModel": "gpt-4.1"}},
            {"type": "user.message", "data": {"content": "hello"}},
            {"type": "assistant.message", "timestamp": "2026-04-21T10:00:00Z",
             "data": {"messageId": "m1", "outputTokens": 120}},
        ])
        calls = gas_gauge._parse_copilot_events_file(path)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["model"], "gpt-4.1")
        self.assertEqual(calls[0]["output_tokens"], 120)
        self.assertEqual(calls[0]["user_message"], "hello")
        self.assertEqual(calls[0]["timestamp"], "2026-04-21T10:00:00Z")

    def test_skips_zero_tokens(self):
        path = self._make_events_file([
            {"type": "session.model_change", "data": {"newModel": "gpt-4.1"}},
            {"type": "assistant.message", "timestamp": "2026-04-21T10:00:00Z",
             "data": {"messageId": "m1", "outputTokens": 0}},
        ])
        self.assertEqual(gas_gauge._parse_copilot_events_file(path), [])

    def test_skips_messages_before_model(self):
        path = self._make_events_file([
            {"type": "assistant.message", "timestamp": "2026-04-21T10:00:00Z",
             "data": {"messageId": "m1", "outputTokens": 50}},
        ])
        self.assertEqual(gas_gauge._parse_copilot_events_file(path), [])

    def test_deduplicates_message_ids(self):
        path = self._make_events_file([
            {"type": "session.model_change", "data": {"newModel": "gpt-4.1"}},
            {"type": "assistant.message", "timestamp": "2026-04-21T10:00:00Z",
             "data": {"messageId": "dup", "outputTokens": 10}},
            {"type": "assistant.message", "timestamp": "2026-04-21T10:01:00Z",
             "data": {"messageId": "dup", "outputTokens": 10}},
        ])
        calls = gas_gauge._parse_copilot_events_file(path)
        self.assertEqual(len(calls), 1)

    def test_model_change_midway(self):
        path = self._make_events_file([
            {"type": "session.model_change", "data": {"newModel": "gpt-4.1"}},
            {"type": "assistant.message", "timestamp": "2026-04-21T10:00:00Z",
             "data": {"messageId": "m1", "outputTokens": 50}},
            {"type": "session.model_change", "data": {"newModel": "claude-3.7-sonnet"}},
            {"type": "assistant.message", "timestamp": "2026-04-21T10:01:00Z",
             "data": {"messageId": "m2", "outputTokens": 80}},
        ])
        calls = gas_gauge._parse_copilot_events_file(path)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["model"], "gpt-4.1")
        self.assertEqual(calls[1]["model"], "claude-3.7-sonnet")

    def test_tools_extracted(self):
        path = self._make_events_file([
            {"type": "session.model_change", "data": {"newModel": "gpt-4.1"}},
            {"type": "assistant.message", "timestamp": "2026-04-21T10:00:00Z",
             "data": {"messageId": "m1", "outputTokens": 30,
                      "toolRequests": [{"name": "bash"}, {"name": "read_file"}]}},
        ])
        calls = gas_gauge._parse_copilot_events_file(path)
        self.assertEqual(calls[0]["tools"], ["bash", "read_file"])

    def test_invalid_json_lines_skipped(self):
        tmpdir = tempfile.mkdtemp()
        path = gas_gauge.Path(os.path.join(tmpdir, "events.jsonl"))
        path.write_text(
            '{"type":"session.model_change","data":{"newModel":"gpt-4.1"}}\n'
            'INVALID_JSON_HERE\n'
            '{"type":"assistant.message","timestamp":"2026-04-21T10:00:00Z",'
            '"data":{"messageId":"m1","outputTokens":50}}\n'
        )
        calls = gas_gauge._parse_copilot_events_file(path)
        self.assertEqual(len(calls), 1)


class TestDiscoverCopilotSessions(unittest.TestCase):
    def _build_session_dir(self, root, session_id, has_events=True,
                           has_workspace=False, cwd=None):
        """Create a session directory with optional files."""
        import json as _json
        sess_dir = os.path.join(root, session_id)
        os.makedirs(sess_dir, exist_ok=True)
        if has_events:
            events_path = os.path.join(sess_dir, "events.jsonl")
            with open(events_path, "w") as f:
                f.write(_json.dumps({"type": "session.model_change",
                                     "data": {"newModel": "gpt-4.1"}}) + "\n")
        if has_workspace and cwd:
            with open(os.path.join(sess_dir, "workspace.yaml"), "w") as f:
                f.write(f"cwd: {cwd}\n")
        return sess_dir

    def test_no_dir_returns_empty(self):
        result = gas_gauge.discover_copilot_sessions(gas_gauge.Path("/nonexistent-abc"))
        self.assertEqual(result, [])

    def test_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as root:
            result = gas_gauge.discover_copilot_sessions(gas_gauge.Path(root))
        self.assertEqual(result, [])

    def test_discovers_session_with_events(self):
        with tempfile.TemporaryDirectory() as root:
            self._build_session_dir(root, "sess-001")
            result = gas_gauge.discover_copilot_sessions(gas_gauge.Path(root))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["session_id"], "sess-001")
        self.assertEqual(result[0]["project"], "sess-001")  # no workspace.yaml

    def test_project_from_workspace_yaml(self):
        with tempfile.TemporaryDirectory() as root:
            self._build_session_dir(root, "sess-002", has_workspace=True,
                                    cwd="/home/user/my-app")
            result = gas_gauge.discover_copilot_sessions(gas_gauge.Path(root))
        self.assertEqual(result[0]["project"], "my-app")

    def test_skips_dirs_without_events_jsonl(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "no-events"))
            result = gas_gauge.discover_copilot_sessions(gas_gauge.Path(root))
        self.assertEqual(result, [])

    def test_multiple_sessions_sorted(self):
        with tempfile.TemporaryDirectory() as root:
            for sid in ["sess-b", "sess-a", "sess-c"]:
                self._build_session_dir(root, sid)
            result = gas_gauge.discover_copilot_sessions(gas_gauge.Path(root))
        self.assertEqual([r["session_id"] for r in result],
                         ["sess-a", "sess-b", "sess-c"])


class TestParseSessionPeriod(unittest.TestCase):
    def test_today(self):
        start, end = gas_gauge.parse_session_period("today")
        today = gas_gauge.date.today()
        self.assertEqual(start, today)
        self.assertEqual(end, today)

    def test_week(self):
        start, end = gas_gauge.parse_session_period("week")
        today = gas_gauge.date.today()
        self.assertEqual(end, today)
        self.assertEqual((end - start).days, 6)

    def test_month(self):
        start, end = gas_gauge.parse_session_period("month")
        today = gas_gauge.date.today()
        self.assertEqual(start.day, 1)
        self.assertEqual(start.month, today.month)
        self.assertEqual(end, today)

    def test_all(self):
        start, end = gas_gauge.parse_session_period("all")
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_custom_range(self):
        start, end = gas_gauge.parse_session_period("2026-01-01:2026-01-31")
        self.assertEqual(start.isoformat(), "2026-01-01")
        self.assertEqual(end.isoformat(), "2026-01-31")

    def test_custom_range_reversed_raises(self):
        with self.assertRaises(ValueError):
            gas_gauge.parse_session_period("2026-01-31:2026-01-01")

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            gas_gauge.parse_session_period("yesterday")

    def test_case_insensitive(self):
        start, end = gas_gauge.parse_session_period("TODAY")
        self.assertEqual(start, gas_gauge.date.today())

    def test_invalid_date_in_range_raises(self):
        with self.assertRaises(ValueError):
            gas_gauge.parse_session_period("2026-13-01:2026-13-31")


class TestCallDate(unittest.TestCase):
    def test_iso_z(self):
        call = {"timestamp": "2026-04-21T10:00:00Z"}
        self.assertEqual(gas_gauge._call_date(call).isoformat(), "2026-04-21")

    def test_iso_offset(self):
        call = {"timestamp": "2026-04-21T10:00:00+00:00"}
        self.assertEqual(gas_gauge._call_date(call).isoformat(), "2026-04-21")

    def test_bare_date(self):
        call = {"timestamp": "2026-04-21"}
        self.assertEqual(gas_gauge._call_date(call).isoformat(), "2026-04-21")

    def test_empty_timestamp(self):
        self.assertIsNone(gas_gauge._call_date({"timestamp": ""}))

    def test_missing_timestamp(self):
        self.assertIsNone(gas_gauge._call_date({}))

    def test_garbage_returns_none(self):
        self.assertIsNone(gas_gauge._call_date({"timestamp": "not-a-date"}))


class TestFilterCallsByPeriod(unittest.TestCase):
    def _calls(self):
        return [
            {"timestamp": "2026-04-01T10:00:00Z", "output_tokens": 10},
            {"timestamp": "2026-04-15T10:00:00Z", "output_tokens": 20},
            {"timestamp": "2026-04-30T10:00:00Z", "output_tokens": 30},
        ]

    def test_no_filter_returns_all(self):
        calls = self._calls()
        result = gas_gauge._filter_calls_by_period(calls, None, None)
        self.assertEqual(len(result), 3)

    def test_start_only(self):
        from datetime import date as _date
        result = gas_gauge._filter_calls_by_period(
            self._calls(), _date(2026, 4, 10), None)
        self.assertEqual(len(result), 2)

    def test_end_only(self):
        from datetime import date as _date
        result = gas_gauge._filter_calls_by_period(
            self._calls(), None, _date(2026, 4, 14))
        self.assertEqual(len(result), 1)

    def test_range(self):
        from datetime import date as _date
        result = gas_gauge._filter_calls_by_period(
            self._calls(), _date(2026, 4, 1), _date(2026, 4, 15))
        self.assertEqual(len(result), 2)

    def test_no_match(self):
        from datetime import date as _date
        result = gas_gauge._filter_calls_by_period(
            self._calls(), _date(2026, 5, 1), _date(2026, 5, 31))
        self.assertEqual(result, [])

    def test_missing_timestamp_excluded_when_filter_active(self):
        from datetime import date as _date
        calls = [{"output_tokens": 10}]   # no timestamp
        result = gas_gauge._filter_calls_by_period(
            calls, _date(2026, 4, 1), _date(2026, 4, 30))
        self.assertEqual(result, [])

    def test_missing_timestamp_included_when_no_filter(self):
        calls = [{"output_tokens": 10}]
        result = gas_gauge._filter_calls_by_period(calls, None, None)
        self.assertEqual(len(result), 1)


class TestAggregateSessionAnalytics(unittest.TestCase):
    def _sessions(self):
        return [
            {
                "session_id": "s1",
                "project": "myapp",
                "calls": [
                    {"model": "gpt-4.1", "output_tokens": 100,
                     "timestamp": "2026-04-21T10:00:00Z", "tools": []},
                    {"model": "gpt-4.1", "output_tokens": 50,
                     "timestamp": "2026-04-21T11:00:00Z", "tools": []},
                ],
            },
            {
                "session_id": "s2",
                "project": "other-proj",
                "calls": [
                    {"model": "claude-3.7-sonnet", "output_tokens": 200,
                     "timestamp": "2026-04-20T09:00:00Z", "tools": []},
                ],
            },
        ]

    def test_total_tokens(self):
        result = gas_gauge.aggregate_session_analytics(self._sessions())
        self.assertEqual(result["total_output_tokens"], 350)

    def test_by_model(self):
        result = gas_gauge.aggregate_session_analytics(self._sessions())
        self.assertEqual(result["by_model"]["gpt-4.1"], 150)
        self.assertEqual(result["by_model"]["claude-3.7-sonnet"], 200)

    def test_by_project(self):
        result = gas_gauge.aggregate_session_analytics(self._sessions())
        self.assertEqual(result["by_project"]["myapp"], 150)
        self.assertEqual(result["by_project"]["other-proj"], 200)

    def test_top_sessions_sorted(self):
        result = gas_gauge.aggregate_session_analytics(self._sessions())
        tops = result["top_sessions"]
        self.assertEqual(tops[0]["session_id"], "s2")
        self.assertEqual(tops[0]["output_tokens"], 200)

    def test_daily_trend_sorted(self):
        result = gas_gauge.aggregate_session_analytics(self._sessions())
        dates = [d["date"] for d in result["daily_trend"]]
        self.assertEqual(dates, sorted(dates))

    def test_empty_sessions(self):
        result = gas_gauge.aggregate_session_analytics([])
        self.assertEqual(result["total_output_tokens"], 0)
        self.assertEqual(result["top_sessions"], [])
        self.assertEqual(result["daily_trend"], [])

    def test_top_sessions_capped_at_10(self):
        sessions = [
            {"session_id": f"s{i}", "project": "p",
             "calls": [{"model": "gpt-4.1", "output_tokens": i * 10,
                        "timestamp": "2026-04-21T10:00:00Z"}]}
            for i in range(1, 16)
        ]
        result = gas_gauge.aggregate_session_analytics(sessions)
        self.assertLessEqual(len(result["top_sessions"]), 10)


class TestRunSessionAnalytics(unittest.TestCase):
    def _build_session(self, root, session_id, model, tokens,
                       timestamp="2026-04-21T10:00:00Z"):
        import json as _json
        sess_dir = os.path.join(root, session_id)
        os.makedirs(sess_dir, exist_ok=True)
        events = [
            {"type": "session.model_change", "data": {"newModel": model}},
            {"type": "assistant.message", "timestamp": timestamp,
             "data": {"messageId": f"{session_id}-m1", "outputTokens": tokens}},
        ]
        with open(os.path.join(sess_dir, "events.jsonl"), "w") as f:
            for e in events:
                f.write(_json.dumps(e) + "\n")

    def test_no_sessions_returns_unavailable(self):
        with tempfile.TemporaryDirectory() as root:
            result = gas_gauge.run_session_analytics(session_state_dir=root,
                                                     period_str="all")
        self.assertFalse(result["available"])
        self.assertIn("error", result)

    def test_basic_run(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = tempfile.mkdtemp()
            self._build_session(root, "sess-1", "gpt-4.1", 200)
            result = gas_gauge.run_session_analytics(
                session_state_dir=root, period_str="all",
                cache_path=gas_gauge.Path(cache_dir) / "cache.json",
            )
        self.assertTrue(result["available"])
        self.assertEqual(result["total_output_tokens"], 200)
        self.assertEqual(result["session_count"], 1)
        self.assertEqual(result["active_session_count"], 1)

    def test_period_filters_out_old_calls(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = tempfile.mkdtemp()
            # session with old timestamp
            self._build_session(root, "old", "gpt-4.1", 100,
                                 timestamp="2020-01-01T10:00:00Z")
            result = gas_gauge.run_session_analytics(
                session_state_dir=root, period_str="today",
                cache_path=gas_gauge.Path(cache_dir) / "cache.json",
            )
        # session exists but no calls in 'today' range
        self.assertTrue(result["available"])
        self.assertEqual(result["active_session_count"], 0)
        self.assertEqual(result["total_output_tokens"], 0)

    def test_invalid_period_returns_error(self):
        result = gas_gauge.run_session_analytics(period_str="invalid-period")
        self.assertFalse(result["available"])
        self.assertIn("error", result)

    def test_caching_avoids_reparse(self):
        import json as _json
        with tempfile.TemporaryDirectory() as root:
            cache_dir = tempfile.mkdtemp()
            cache_path = gas_gauge.Path(cache_dir) / "cache.json"
            self._build_session(root, "sess-1", "gpt-4.1", 200)
            # First run — populates cache
            gas_gauge.run_session_analytics(session_state_dir=root,
                                             period_str="all",
                                             cache_path=cache_path)
            self.assertTrue(cache_path.exists())
            with open(cache_path) as f:
                cached = _json.load(f)
            self.assertEqual(cached["version"], gas_gauge.SESSION_CACHE_VERSION)
            self.assertTrue(len(cached["entries"]) > 0)

    def test_period_range_in_result(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = tempfile.mkdtemp()
            self._build_session(root, "sess-1", "gpt-4.1", 100)
            result = gas_gauge.run_session_analytics(
                session_state_dir=root, period_str="week",
                cache_path=gas_gauge.Path(cache_dir) / "cache.json",
            )
        self.assertIn("period_range", result)
        self.assertIn("to", result["period_range"])

    def test_all_period_range_label(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = tempfile.mkdtemp()
            self._build_session(root, "sess-1", "gpt-4.1", 100)
            result = gas_gauge.run_session_analytics(
                session_state_dir=root, period_str="all",
                cache_path=gas_gauge.Path(cache_dir) / "cache.json",
            )
        self.assertEqual(result["period_range"], "all time")


class TestPrintSessionAnalytics(unittest.TestCase):
    def _capture(self, analytics, no_color=True):
        buf = io.StringIO()
        with redirect_stdout(buf):
            gas_gauge.print_session_analytics(analytics, no_color=no_color)
        return buf.getvalue()

    def test_unavailable_shows_warning(self):
        output = self._capture({
            "available": False,
            "error": "No sessions found at /path",
            "session_dir": "/path",
        })
        self.assertIn("⚠️", output)
        self.assertIn("No sessions found at /path", output)
        self.assertIn("Session Analytics", output)

    def test_available_shows_summary(self):
        output = self._capture({
            "available": True,
            "period_range": "2026-04-15 to 2026-04-21",
            "session_dir": "/home/user/.copilot/session-state",
            "session_count": 5,
            "active_session_count": 3,
            "total_output_tokens": 12500,
            "by_model": {"gpt-4.1": 7500, "claude-3.7-sonnet": 5000},
            "by_project": {"myapp": 12500},
            "top_sessions": [
                {"session_id": "s1", "project": "myapp",
                 "output_tokens": 12500, "model": "gpt-4.1",
                 "first_ts": "2026-04-21T10:00:00Z"},
            ],
            "daily_trend": [
                {"date": "2026-04-21", "output_tokens": 12500},
            ],
        })
        self.assertIn("12,500", output)
        self.assertIn("gpt-4.1", output)
        self.assertIn("claude-3.7-sonnet", output)
        self.assertIn("myapp", output)
        self.assertIn("2026-04-15 to 2026-04-21", output)

    def test_empty_analytics_no_crash(self):
        output = self._capture({
            "available": True,
            "period_range": "all time",
            "session_dir": "/dir",
            "session_count": 0,
            "active_session_count": 0,
            "total_output_tokens": 0,
            "by_model": {},
            "by_project": {},
            "top_sessions": [],
            "daily_trend": [],
        })
        self.assertIn("Session Analytics", output)
        self.assertIn("0", output)

    def test_privacy_note_included(self):
        output = self._capture({
            "available": True,
            "period_range": "all time",
            "session_dir": "/dir",
            "session_count": 1,
            "active_session_count": 1,
            "total_output_tokens": 100,
            "by_model": {},
            "by_project": {},
            "top_sessions": [],
            "daily_trend": [],
        })
        self.assertIn("locally", output)
        self.assertIn("uploaded", output)

    def test_daily_trend_displayed(self):
        output = self._capture({
            "available": True,
            "period_range": "week",
            "session_dir": "/dir",
            "session_count": 1,
            "active_session_count": 1,
            "total_output_tokens": 100,
            "by_model": {},
            "by_project": {},
            "top_sessions": [],
            "daily_trend": [
                {"date": "2026-04-21", "output_tokens": 100},
            ],
        })
        self.assertIn("2026-04-21", output)
        self.assertIn("100", output)


class TestCLISessionFlags(unittest.TestCase):
    """Test the --session-analytics, --session-period, --session-json flags."""

    def test_session_json_skips_github_token_check(self):
        """--session-json should not require GITHUB_TOKEN."""
        with tempfile.TemporaryDirectory() as root:
            # No sessions means run_session_analytics returns unavailable
            with patch.dict(os.environ, {}, clear=True):
                with patch("sys.argv", ["gas_gauge.py", "--session-json",
                                        "--session-dir", root]):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        gas_gauge.main()
            output = buf.getvalue()
        # Should produce valid JSON (not crash with auth error)
        import json as _json
        data = _json.loads(output)
        self.assertIn("available", data)

    def test_session_json_outputs_valid_json(self):
        """--session-json output must be valid JSON with 'available' key."""
        import json as _json
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv", ["gas_gauge.py", "--session-json",
                                    "--session-dir", root]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    gas_gauge.main()
        data = _json.loads(buf.getvalue())
        self.assertIn("available", data)
        self.assertFalse(data["available"])  # empty dir

    def test_session_period_invalid_exits(self):
        """An invalid --session-period with --session-json should produce JSON error."""
        import json as _json
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv", ["gas_gauge.py", "--session-json",
                                    "--session-dir", root,
                                    "--session-period", "badperiod"]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    gas_gauge.main()
        data = _json.loads(buf.getvalue())
        self.assertFalse(data["available"])
        self.assertIn("error", data)

    def test_session_analytics_flag_with_providers_only(self):
        """--session-analytics can combine with --providers-only."""
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv", ["gas_gauge.py", "--providers-only",
                                    "--session-analytics",
                                    "--session-dir", root]):
                with patch("gas_gauge.fetch_provider_usage") as mock_prov:
                    mock_prov.return_value = {
                        "available": False,
                        "provider_id": "openai",
                        "name": "OpenAI",
                        "note": "No key set.",
                    }
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        gas_gauge.main()
        output = buf.getvalue()
        # Both provider and session analytics sections should appear
        self.assertIn("OpenAI", output)
        self.assertIn("Session Analytics", output)


if __name__ == "__main__":
    unittest.main()
