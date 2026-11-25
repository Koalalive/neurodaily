from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import tempfile
import unittest
from unittest import mock

import httpx

from neurodaily import ai_summary, api_billing, demo


BASE = "https://api.example.test/v1"
MODEL = "fixture-model"
KEY = "private-model-key-unique-fixture"
USAGE = {"prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100,
         "prompt_tokens_details": {"cached_tokens": 400}}


def _price(**overrides):
    return {"base_url": BASE, "model": MODEL, "input": "3", "cached_input": "0.3",
            "output": "15", "currency": "USD", **overrides}


def _reply(*, status=200, content=None, usage=None, response_id="chatcmpl-fixture"):
    body = {"id": response_id, "choices": [{"message": {"content": content or "Ready."}}]}
    if usage is not None:
        body["usage"] = usage
    return httpx.Response(status, json=body, request=httpx.Request("POST", BASE + "/chat/completions"))


class BillingTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.directory = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(mock.patch.object(api_billing, "DEFAULT_DIRS", {"output": self.directory}))

    def request(self, **kwargs):
        args = {"base_url": BASE, "model": MODEL, "key": KEY,
                "messages": [{"role": "user", "content": "Unique unpublished prompt text."}],
                "max_tokens": 50, "timeout": 3, **kwargs}
        return ai_summary._chat_request(**args)

    def test_settings_are_normalized_and_saved_as_a_patch(self):
        self.assertEqual(api_billing.load_settings(), {"geo_enabled": False, "rates": []})
        rate = _price(base_url="https://API.EXAMPLE.TEST:443/v1/chat/completions/", input="03.00", currency="usd")
        first = api_billing.save_settings({"rates": [rate]})
        self.assertEqual(first["rates"], [_price()])
        self.assertEqual(api_billing.save_settings({"geo_enabled": True}), {**first, "geo_enabled": True})
        self.assertEqual(api_billing.save_settings({"geo_concurrency": 6})["geo_concurrency"], 6)
        self.assertEqual(api_billing.load_settings()["rates"], [_price()])
        invalid = (
            {"geo_enabled": "true"},
            {"geo_concurrency": 0},
            {"geo_concurrency": 17},
            {"geo_concurrency": "4"},
            {"rates": [rate, _price()]},
            {"rates": [_price(input="Infinity")]},
            {"rates": [_price(output=-1)]},
            {"rates": [_price(base_url="https://user:secret@api.example.test/v1")]},
            {"rates": [_price(base_url=BASE + "?key=secret")]},
            {"rates": [_price(base_url="http://api.example.test/v1")]},
        )
        for patch in invalid:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                api_billing.save_settings(patch)
        self.assertEqual(api_billing.load_settings()["rates"], [_price()])

    def test_rate_snapshot_exact_amounts_and_currency_totals(self):
        api_billing.save_settings({"rates": [_price()]})
        cny_rate = _price(currency="CNY", input="0.1", cached_input="0.01", output="10")

        def finish_first_request(*_args, **_kwargs):
            # Simulate a settings change while the HTTP request is in flight.
            api_billing.save_settings({"rates": [cny_rate]})
            return _reply(usage=USAGE)

        with mock.patch.object(ai_summary.httpx, "post", side_effect=finish_first_request):
            self.request(purpose="geolocation", run_id=5, profile="临床研究")
        deepseek_usage = {"prompt_cache_hit_tokens": 200, "prompt_cache_miss_tokens": 800,
                          "completion_tokens": 0}
        with mock.patch.object(ai_summary.httpx, "post", return_value=_reply(usage=deepseek_usage)) as post:
            self.request(temperature=0, response_format={"type": "json_object"})
        self.assertEqual(post.call_args.kwargs["json"]["temperature"], 0)
        self.assertEqual(post.call_args.kwargs["json"]["response_format"], {"type": "json_object"})
        report = api_billing.billing_report(limit=1)
        self.assertEqual(report["total_calls"], 2)
        self.assertEqual(report["calls"][0]["estimated_cost"], "0.000082")
        self.assertEqual(report["totals"]["cost_by_currency"], {"CNY": "0.000082", "USD": "0.00342"})
        self.assertEqual(report["totals"]["input_tokens"], 2000)
        self.assertEqual(report["totals"]["cached_input_tokens"], 600)
        first = api_billing.billing_report(limit=1, offset=1)["calls"][0]
        self.assertEqual(first, api_billing.billing_report(purpose="geolocation")["calls"][0])
        self.assertEqual({key: first[key] for key in ("run_id", "profile", "estimated_cost", "base_url")},
                         {"run_id": 5, "profile": "临床研究", "estimated_cost": "0.00342",
                          "base_url": "https://api.example.test"})
        self.assertEqual(first["rate"], {"currency": "USD", "input": "3", "cached_input": "0.3", "output": "15"})

    def test_cost_is_unknown_when_usage_or_cache_breakdown_is_missing(self):
        api_billing.save_settings({"rates": [_price()]})
        with mock.patch.object(ai_summary.httpx, "post", return_value=_reply(usage={"prompt_tokens": 10,
                                                                                     "completion_tokens": 2})):
            self.request()
            api_billing.save_settings({"rates": [_price(cached_input=None)]})
            self.request()
            self.request(model="unpriced-model")
        with mock.patch.object(ai_summary.httpx, "post", return_value=_reply()):
            self.request()
        report = api_billing.billing_report()
        self.assertEqual(report["totals"]["known_cost_calls"], 1)
        self.assertEqual(report["totals"]["unknown_cost_calls"], 3)
        self.assertEqual(report["totals"]["usage_reported_calls"], 3)
        self.assertIsNone(report["calls"][0]["total_tokens"])
        self.assertEqual(report["calls"][2]["estimated_cost"], "0.00006")

    def test_actual_summary_retries_and_cache_use_are_recorded(self):
        result = demo.build_result()
        result.config.output["dir"] = self.directory
        result.history_id = 41
        cfg = {**ai_summary.DEFAULT_CFG, "base_url": BASE, "model": MODEL}
        invalid = httpx.Response(200, json={"id": "bad-shape"}, request=httpx.Request("POST", BASE))
        with mock.patch.object(ai_summary.httpx, "post", side_effect=[httpx.ReadTimeout("secret error"),
            invalid, _reply(content="有效的日报摘要内容。" * 20, usage=USAGE)]) as post, \
                mock.patch("time.sleep"):
            text = ai_summary.generate(result, cfg, api_key_override=KEY)
            self.assertEqual(ai_summary.generate(result, cfg, api_key_override=KEY), text)
        self.assertEqual(post.call_count, 3)
        report = api_billing.billing_report(purpose="summary")
        self.assertEqual([call["status"] for call in report["calls"]],
                         ["success", "invalid_response", "timeout"])
        self.assertEqual({(call["run_id"], call["profile"]) for call in report["calls"]}, {(41, result.config_profile)})
        self.assertEqual(report["totals"]["failed_calls"], 2)

    def test_connection_errors_and_only_accounting_metadata_are_stored(self):
        with mock.patch.object(ai_summary, "load_cfg", return_value=dict(ai_summary.DEFAULT_CFG)), \
                mock.patch.object(ai_summary.httpx, "post", return_value=_reply(status=401, response_id=KEY)):
            result = ai_summary.test_connection({"base_url": BASE, "model": MODEL, "api_key": KEY})
        self.assertFalse(result["ok"])
        call = api_billing.billing_report(purpose="connection_test")["calls"][0]
        self.assertEqual((call["status"], call["http_status"], call["response_id"]), ("http_error", 401, None))
        with mock.patch.object(ai_summary.httpx, "post", return_value=_reply(usage=USAGE)):
            self.request(base_url=BASE + "/private-gateway-route", profile=KEY)
        call = api_billing.billing_report(purpose="other")["calls"][0]
        self.assertEqual(call["base_url"], "https://api.example.test")
        self.assertIsNone(call["profile"])
        raw = api_billing._db_path().read_bytes()
        for sensitive in (KEY, "private-gateway-route", "Unique unpublished prompt text.", "Reply with OK."):
            self.assertNotIn(sensitive.encode(), raw)

    def test_logging_failure_does_not_retry_a_paid_request(self):
        with mock.patch.object(api_billing, "record_call", side_effect=sqlite3.OperationalError("secret")), \
                mock.patch.object(ai_summary.httpx, "post", return_value=_reply(usage=USAGE)) as post, \
                self.assertLogs("neurodaily.ai_summary", "WARNING") as logs:
            self.assertEqual(self.request(), {"content": "Ready."})
        post.assert_called_once()
        self.assertNotIn("secret", " ".join(logs.output))

    def test_selected_date_range_filters_before_totals_and_pagination(self):
        for age in (2, 25, 40):
            api_billing.record_call(purpose="summary", base_url=BASE, model=MODEL, status="success",
                                    called_at=datetime.now(timezone.utc) - timedelta(days=age))
        report = api_billing.billing_report(days=30, limit=1, offset=1)
        self.assertEqual(report["total_calls"], 2)
        self.assertEqual(len(report["calls"]), 1)
        self.assertEqual(report["totals"]["successful_calls"], 2)
        self.assertIsInstance(json.dumps(report), str)
