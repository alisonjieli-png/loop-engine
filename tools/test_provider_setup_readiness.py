"""Provider setup follows configured routes; retired models are not key failures."""
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from loop_engine import cli_operations
from loop_engine.core import ollama_client
from loop_engine.core.model_gateway import (
    ModelGateway, ModelGatewayConfig, ModelGatewayRequest, ProviderSpec,
    _error_code,
)
from loop_engine.core.model_routes import ModelRoute, RouteRegistry, default_routes
from loop_engine.core.model_capabilities import ModelOutputCapability


class ProviderSetupReadiness(unittest.TestCase):
    def test_setup_examples_follow_the_default_route_without_a_retired_pin(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("README.md", "docs/guides/providers-and-keys.md",
                     "docs/guides/quick-start.md", "docs/guides/install-macos/README.md",
                     "docs/guides/install-windows/README.md"):
            with self.subTest(document=name):
                text = (root / name).read_text()
                self.assertIn("--model-route cloud.default", text)
                self.assertNotIn("--model-id deepseek-v4-flash:0731", text)
                self.assertIn("--allow-unbounded-total-tokens", text)
                self.assertIn("qualified exact-request bound", " ".join(text.split()))

    def test_default_is_the_available_route_with_room_for_its_declared_capacity(self):
        # The October 8 catalogue lists this already-wired model; the previous
        # default returned HTTP 410. Keep historical output evidence intact.
        self.assertEqual(ollama_client.DEFAULT_MODEL, "deepseek-v4-pro:0813")
        route = RouteRegistry().get("cloud.default")
        self.assertEqual(route.model, ollama_client.DEFAULT_MODEL)
        self.assertGreater(route.capabilities.max_context,
                           ollama_client.max_output_for(route.model))
        self.assertEqual(ollama_client.max_output_for("deepseek-v4-flash:0731"), 65536)

    def test_probe_uses_the_registry_and_preserves_a_quoted_settings_path(self):
        route = ModelRoute("cloud.default", "ollama_cloud", "fixture-model:latest")
        gateway = SimpleNamespace(providers={"ollama_cloud": object()},
                                  registry=RouteRegistry((route,)))
        command = cli_operations._provider_probe_command(
            gateway, "ollama_cloud", settings_file="/fixture/settings with spaces.json")
        words = shlex.split(command)
        for option, expected in (("--model-id", route.model),
                                 ("--model-route", route.name),
                                 ("--settings-file", "/fixture/settings with spaces.json"),
                                 ("--max-model-calls", "1")):
            self.assertEqual(words[words.index(option) + 1], expected)

    def test_no_probe_is_invented_for_an_absent_provider_or_generation_route(self):
        for gateway in (
            SimpleNamespace(providers={}, registry=RouteRegistry(default_routes())),
            SimpleNamespace(providers={"ollama_cloud": object()}, registry=RouteRegistry(())),
        ):
            self.assertEqual(cli_operations._provider_probe_command(gateway, "ollama_cloud"), "")

    def test_configure_and_doctor_share_the_actual_route_without_calls(self):
        route = ModelRoute("cloud.default", "ollama_cloud", "fixture-selected-model")
        gateway = SimpleNamespace(providers={"ollama_cloud": object()},
                                  registry=RouteRegistry((route,)))
        extension = SimpleNamespace(
            settings=SimpleNamespace(build_gateway=lambda: gateway, safe_summary=lambda: {}),
            snapshot=SimpleNamespace(content_digest="a" * 64, roots=(), to_dict=lambda: {}),
            activated_routes=(), to_dict=lambda: {})
        args = SimpleNamespace(settings_file="", format="json")
        with patch.dict(os.environ, {}, clear=True), patch.object(
                cli_operations, "resolve_cli_extensions", return_value=extension), patch.object(
                cli_operations, "_safe_provider_description", return_value={
                    "provider_id": "ollama_cloud", "credential_present": True}), patch(
                "loop_engine.architecture_contract.run_architecture_contract_checks",
                return_value={"passed": True}), patch(
                "urllib.request.urlopen", side_effect=AssertionError("no network")) as network:
            records = []
            for operation in (cli_operations.run_configure, cli_operations.run_doctor):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(operation(args), 0)
                records.append(json.loads(output.getvalue()))
            self.assertEqual(records[0]["next_action"], records[1]["solve_readiness"]["preferred_probe"])
            self.assertIn("fixture-selected-model", records[0]["next_action"])
            self.assertTrue(all(record["provider_calls_made"] == 0 for record in records))
            network.assert_not_called()

    def test_http_gone_names_only_the_requested_retired_model(self):
        model = "fixture-model:v1"
        retired = 'HTTP 410: {"error":"fixture-model:v1 was retired at 2026-09-25 (ref: abc401de)"}'
        self.assertEqual(_error_code(retired, requested_model=model), "model_not_found")
        for error in (retired.replace(model, "other-model:v1"),
                      "HTTP 410: endpoint was retired at 2026-09-25",
                      "HTTP 410: account was retired at 2026-09-25"):
            self.assertEqual(_error_code(error, requested_model=model), "provider_failed")
        self.assertEqual(_error_code(retired.replace("410", "401"), requested_model=model),
                         "authentication_failed")
        self.assertEqual(_error_code("HTTP 429: weekly usage limit (ref: abc410de)",
                                     requested_model=model), "usage_limit_reached")

    def test_gateway_supplies_requested_identity_without_faking_reported_identity(self):
        class RetiredAdapter:
            DEFAULT_MODEL = "fixture-model:v1"

            def verify(self, model=""):
                return True

            def live_models(self):
                return []

            def output_capability_for(self, model):
                return ModelOutputCapability(64, "offline fixture")

            def chat_maxout(self, *_args, **_kwargs):
                return SimpleNamespace(text="", model="", ok=False,
                    error="HTTP 410: fixture-model:v1 was retired at 2026-09-25",
                    prompt_tokens=None, eval_tokens=None, response_received=False,
                    physical_requests=1, attempts=1)

        gateway = ModelGateway(
            providers=(ProviderSpec("fixture", RetiredAdapter(), "fixture", "not_required"),),
            routes=(ModelRoute("fixture.route", "fixture", RetiredAdapter.DEFAULT_MODEL),))
        result = gateway.invoke(ModelGatewayRequest("offline fixture", ModelGatewayConfig(
            route_names=("fixture.route",), allow_failover=False, max_route_attempts=1)))
        self.assertEqual(result.error_code, "model_not_found")
        self.assertEqual(result.physical_model_calls, 1)
        self.assertEqual(result.attempts[-1].model, "")
        self.assertEqual(result.attempts[-1].expected_model, RetiredAdapter.DEFAULT_MODEL)
        self.assertIsNone(result.total_tokens)
        self.assertNotIn("2026-09-25", result.error)


if __name__ == "__main__":
    unittest.main()
