"""Exercise the bundled native harness against a private HTTP broker."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from unittest import mock
from urllib.request import build_opener

from loop_engine.core import harness_baltor_recipe as recipe
from loop_engine.core.harness_recipes import release_recipe_catalog


class BaltorHarnessTests(unittest.TestCase):
    def test_broker_redirect_is_refused_and_the_unguarded_control_reaches_the_target(self):
        arrivals = []
        class RedirectingBroker(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(302)
                self.send_header("Location", "/unexpected-target")
                self.end_headers()

            def do_GET(self):
                arrivals.append(self.path)
                answer = json.dumps({"choices": [{"message": {"content": "unbound answer"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(answer)))
                self.end_headers()
                self.wfile.write(answer)

            def log_message(self, *_args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), RedirectingBroker) as server, tempfile.TemporaryDirectory() as folder:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                task = Path(folder) / "task.txt"
                task.write_text("A bounded assignment")
                config = {"model": "bound", "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                          "task_path": str(task), "output_allowance": 123, "maximum_bytes": 4096}
                with self.assertRaisesRegex(ValueError, "private_broker_redirect_refused"):
                    recipe.invoke(config)
                self.assertEqual(arrivals, [])
                with mock.patch.object(recipe, "urlopen", build_opener().open):
                    self.assertEqual(recipe.invoke(config)["text"], "unbound answer")
                self.assertEqual(arrivals, ["/unexpected-target"])
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_host_configuration_requires_the_explicit_versioned_profile(self):
        from loop_engine.core.harness_configuration import load_harness_binding
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "harness.json"
            good = {"schema_version": 2, "process_isolation": "trusted_process", "harness_id": "baltor",
                    "package_version": "1.0.0", "style": "baltor", "command_prefix": [sys.executable, recipe.__file__],
                    "read_only_paths": [recipe.__file__]}
            path.write_text(json.dumps(good))
            held = load_harness_binding(str(path), work_root=str(root / "work"), socket_directory=str(root))
            self.assertEqual(held.registry.get("baltor").info().execution_capabilities.isolation, "none")
            for change in ({**good, "schema_version": 3}, {**good, "schema_version": True},
                           {**good, "schema_version": 1}, {**good, "process_isolation": "implicit_fallback"},
                           {key: value for key, value in good.items() if key != "process_isolation"}):
                path.write_text(json.dumps(change))
                with self.assertRaises(ValueError):
                    load_harness_binding(str(path), work_root=str(root / "work"), socket_directory=str(root))

    def test_trusted_process_is_explicit_fresh_and_does_not_claim_an_os_sandbox(self):
        from loop_engine.core.harness_process import HarnessProcessRequest, HarnessProcessSpec, run_harness_process
        from loop_engine.core.harness_semantic import GatewayHarnessProcessAdapter
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            work = root / "work"
            work.mkdir()
            spec = HarnessProcessSpec("baltor", "1.0.0", (sys.executable, recipe.__file__), (recipe.__file__,), "baltor",
                                      process_isolation="trusted_process")
            self.assertEqual(GatewayHarnessProcessAdapter(spec).info().execution_capabilities.isolation, "none")
            identities, received = [], []
            for number in (1, 2):
                marker = "private step " + str(number)
                expected = "accepted fixture " + str(number)
                def broker(body, expected=expected):
                    received.append(body)
                    return {"id": "fixture", "object": "chat.completion", "model": "fixture-model",
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": expected},
                                         "finish_reason": "stop"}], "usage": {"total_tokens": 5}}
                request = HarnessProcessRequest(spec, marker, "fixture-model", 100, 20, 10,
                                                str(work), socket_directory=str(root))
                with mock.patch.dict("os.environ", {"UNDECLARED_HARNESS_SECRET": "must never be inherited"}):
                    result = run_harness_process(request, broker)
                self.assertTrue(result.ok, (result.errors, result.stderr))
                self.assertEqual(result.output, expected)
                identities.append(result.process_identity)
            self.assertEqual(len(set(identities)), 2)
            self.assertEqual([body["messages"][0]["content"] for body in received], ["private step 1", "private step 2"])
            with self.assertRaises(ValueError):
                HarnessProcessSpec("baltor", "1.0.0", (sys.executable, recipe.__file__), (recipe.__file__,), "baltor",
                                   process_isolation="implicit_fallback")

    def test_native_process_preserves_the_assignment_and_uses_only_the_bound_broker(self):
        seen = []

        class Broker(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                body = json.dumps({"choices": [{"message": {"content": "exact verified broker answer"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Broker) as server, tempfile.TemporaryDirectory() as folder:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                root = Path(folder)
                task = root / "task.txt"
                task.write_text("Preserve this exact assignment, including Ω and its scoped constraints.")
                config = {"workspace_path": str(root), "task_path": str(task), "model": "bound-model",
                          "output_allowance": 321, "command_prefix": [sys.executable, recipe.__file__]}
                command, environment, prompt = recipe.prepare_baltor_recipe(
                    "baltor", config, f"http://127.0.0.1:{server.server_port}/v1")
                result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
                self.assertEqual((environment, prompt), ({}, None))
                self.assertEqual(seen, [("/v1/chat/completions", {"model": "bound-model",
                    "messages": [{"role": "user", "content": task.read_text()}], "max_tokens": 321, "stream": False})])
                self.assertEqual(recipe.extract_baltor_output("baltor", result.stdout, "exact verified broker answer"),
                                 "exact verified broker answer")
                self.assertEqual(recipe.extract_baltor_output("baltor", result.stdout, "different answer"), "")
                self.assertEqual(recipe.extract_baltor_output("baltor", result.stdout.replace(recipe.RESULT_RECORD, "unknown/v1"),
                                                              "exact verified broker answer"), "")
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_foreign_origins_unknown_fields_and_oversized_inputs_refuse_before_network(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(recipe, "urlopen") as network:
            path = Path(folder) / "task.txt"
            path.write_text("ten bytes plus")
            good = {"model": "m", "base_url": "http://127.0.0.1:18080/v1", "task_path": str(path),
                    "output_allowance": 123, "maximum_bytes": 4096}
            for changed in ({**good, "base_url": "https://example.com/v1"}, {**good, "extra": True},
                            {**good, "output_allowance": True}, {**good, "maximum_bytes": 10}):
                with self.assertRaises(ValueError):
                    recipe.invoke(changed)
            network.assert_not_called()

    def test_release_catalogue_resolves_the_exact_bundled_recipe(self):
        selected = release_recipe_catalog().recipe("baltor")
        self.assertEqual((selected.module, selected.prepare_function, selected.extract_function),
                         ("harness_baltor_recipe", "prepare_baltor_recipe", "extract_baltor_output"))
        self.assertEqual(selected.native_controls.to_dict()["ownership"]["planning_and_continuation"], "owning_loop")
