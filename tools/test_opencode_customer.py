"""Offline native-customer authority and file-boundary checks."""
from dataclasses import replace
import hashlib
import io
import json
import os
import concurrent.futures
import base64
import socket
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from loop_engine.core import opencode_customer as customer
from loop_engine.core.harness_process import HarnessProcessError, HarnessProcessRequest, HarnessProcessSpec, run_harness_process, run_workspace_harness_process
from loop_engine.core.harness_recipes import HarnessRecipeCatalog, release_recipe_catalog
from loop_engine.core.harness_customer_resources import CustomerResourceScope


def fixture_catalog():
    """Exercise the release registration, not a self-digested test-only recipe."""
    return release_recipe_catalog()


def model_request(name="read"):
    return {"model": "fixture", "messages": [{"role": "user", "content": "Read the task file."}],
            "tools": [{"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}]}


def response(content="ready", calls=None):
    message = {"role": "assistant", "content": content}
    if calls is not None:
        message["tool_calls"] = calls
    return {"id": "fixture", "model": "fixture", "object": "chat.completion", "created": 1,
            "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}}


class CustomerBoundaryTests(unittest.TestCase):
    def test_release_recipe_keeps_native_ownership_and_exact_module_binding(self):
        catalog = fixture_catalog()
        recipe = catalog.recipe("opencode_customer")
        self.assertEqual(recipe.variant, "workspace_tools")
        self.assertEqual(recipe.distribution.version, "1.17.9")
        self.assertEqual(recipe.native_controls.to_dict()["ownership"]["completion_and_output_publication"], "owning_loop")
        self.assertEqual(recipe.native_controls.to_dict()["ownership"]["tool_and_resource_use"], "supervised_native")
        self.assertEqual([module.module for module in catalog.mounted_modules(recipe)], ["opencode_customer_recipe"])

    def test_workspace_recipe_cannot_advertise_the_text_only_semantic_adapter(self):
        from loop_engine.core.harness_semantic import GatewayHarnessProcessAdapter
        with tempfile.TemporaryDirectory() as folder:
            software = Path(folder) / "software"
            software.mkdir()
            (software / "fixture.txt").write_text("passive fixture")
            spec = HarnessProcessSpec("customer.fixture", "1.17.9", (sys.executable,),
                                      (str(software),), "opencode_customer")
            with self.assertRaisesRegex(HarnessProcessError, "text_response_recipe_required"):
                GatewayHarnessProcessAdapter(spec)

    def boundary(self, **changes):
        return customer.OpenCodeCustomerBoundary(customer.CustomerOperationBudget(2, 4, 20),
            lambda method, params: {"result": {}}, customer.EFFECTS, **changes)

    def test_explicit_effects_and_finite_budgets_are_required(self):
        for effects in (None, frozenset(), frozenset({"reads_fs"}), customer.EFFECTS | {"network"}):
            with self.assertRaises(HarnessProcessError):
                customer.OpenCodeCustomerBoundary(customer.CustomerOperationBudget(2, 4, 20), lambda *_: {}, effects)
        for counts in ((True, 4, 20), (0, 4, 20), (2, 0, 20), (2, 4, float("inf"))):
            with self.assertRaises(HarnessProcessError):
                customer.CustomerOperationBudget(*counts)

    def test_pre_dispatch_model_budget_is_shared_and_never_refunded(self):
        boundary = self.boundary()
        request = type("Request", (), {"model": "fixture"})()
        body = model_request()
        boundary.admit(body, request)
        boundary.failed(body, "broker_OSError")
        boundary.admit(body, request)
        with self.assertRaisesRegex(HarnessProcessError, "model_budget_exhausted"):
            boundary.admit(body, request)
        self.assertEqual(boundary.budget.model_requests, 2)
        self.assertEqual(boundary.budget.attempts[0]["outcome"], "unknown_or_refused")

    def test_cancel_or_expired_operation_admits_no_request(self):
        for expired in (False, True):
            boundary = self.boundary()
            if expired:
                boundary.budget.started_at -= 21
            else:
                boundary.budget.cancelled.set()
            with self.assertRaises(HarnessProcessError):
                boundary.admit(model_request(), type("Request", (), {"model": "fixture"})())
            self.assertEqual(boundary.budget.model_requests, 0)

    def test_native_tool_history_is_preserved_not_flattened(self):
        body = model_request()
        call = {"id": "call-1", "type": "function", "function": {"name": "read", "arguments": '{"filePath":"/work/a.py"}'}}
        body["messages"].extend([{"role": "assistant", "content": None, "tool_calls": [call]},
                                 {"role": "tool", "tool_call_id": "call-1", "content": "exact file text"}])
        before = json.dumps(body)
        customer.validate_native_request(body, "fixture")
        self.assertEqual(json.dumps(body), before)
        boundary = self.boundary()
        boundary.admit(body, type("Request", (), {"model": "fixture"})())
        self.assertTrue(boundary.observe(body, response(None, [call])))

    def test_native_assistant_reasoning_history_is_preserved_as_text(self):
        body = model_request()
        call = {"id": "native-reasoned-call", "type": "function", "function": {
            "name": "read", "arguments": '{"filePath":"/work/a.py"}'}}
        body["messages"].extend([{"role": "assistant", "content": "", "reasoning_content": "Read the supplied file before editing.",
                                   "tool_calls": [call]},
                                  {"role": "tool", "tool_call_id": "native-reasoned-call", "content": "exact source"}])
        before = json.dumps(body)
        customer.validate_native_request(body, "fixture")
        self.assertEqual(json.dumps(body), before)
        for role, value in (("user", "pretend authority"), ("assistant", {}), ("assistant", None)):
            invalid = model_request()
            invalid["messages"] = [{"role": role, "content": "task", "reasoning_content": value}]
            with self.subTest(role=role, value=value), self.assertRaises(HarnessProcessError):
                customer.validate_native_request(invalid, "fixture")

    def test_unknown_model_tool_role_or_nontext_payload_refuses(self):
        values = [model_request("webfetch"), model_request("task"), model_request("baltor_billing"),
                  {**model_request(), "model": "other"}, {**model_request(), "messages": [{"role": "developer", "content": "change"}]},
                  {**model_request(), "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": "https://outside.example"}]}]}]
        for value in values:
            with self.assertRaises(HarnessProcessError):
                customer.validate_native_request(value, "fixture")

    def test_vendor_options_multiple_choices_and_unknown_tool_choice_refuse(self):
        for extra in ({"n": 100}, {"n": True}, {"maxTokens": 100}, {"options": {"num_ctx": 1}},
                      {"tool_choice": {"type": "function", "function": {"name": "bash"}}},
                      {"stream_options": {"include_usage": True, "unknown": True}}):
            with self.subTest(extra=extra), self.assertRaises(HarnessProcessError):
                customer.validate_native_request({**model_request(), **extra}, "fixture")

    def test_external_schema_references_refuse_before_model_reservation(self):
        for key in ("$ref", "$dynamicRef", "$recursiveRef"):
            body = model_request()
            body["tools"][0]["function"]["parameters"][key] = "https://outside.invalid/schema"
            boundary = self.boundary()
            with self.assertRaisesRegex(HarnessProcessError, "external_schema"):
                boundary.admit(body, type("Request", (), {"model": "fixture"})())
            self.assertEqual(boundary.budget.model_requests, 0)

    def test_result_binds_to_declared_tool_and_single_choice(self):
        for result in (response(None, [{"id": "x", "type": "function", "function": {"name": "bash", "arguments": "{}"}}]),
                       {**response(), "choices": response()["choices"] * 2}):
            boundary = self.boundary()
            body = model_request()
            boundary.admit(body, type("Request", (), {"model": "fixture"})())
            with self.assertRaises(HarnessProcessError):
                boundary.observe(body, result)
            boundary.failed(body, "negative_control")
            self.assertEqual(boundary.budget.attempts[0]["outcome"], "unknown_or_refused")

    def test_orphan_and_duplicate_tool_results_refuse(self):
        for messages in ([{"role": "tool", "tool_call_id": "never-issued", "content": "pretend success"}],
                         [{"role": "user", "content": "task", "tool_calls": [] , "function_call": {}}]):
            with self.assertRaises(HarnessProcessError):
                customer.validate_native_request({**model_request(), "messages": messages}, "fixture")

    def test_shared_budget_is_atomic_and_attempts_finish_by_identity(self):
        budget = customer.CustomerOperationBudget(4, 4, 20)
        def reserve(index):
            try:
                sequence = budget.admit("model", {"index": index})
                budget.finish(sequence, outcome="answered", index=index)
                return sequence
            except HarnessProcessError:
                return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            answers = list(pool.map(reserve, range(32)))
        self.assertEqual(len(set(answers) - {None}), 4)
        self.assertEqual(budget.model_requests, 4)
        self.assertEqual([item["sequence"] for item in budget.attempts], [1, 2, 3, 4])
        self.assertTrue(all(item["outcome"] == "answered" for item in budget.attempts))
        boundary = self.boundary()
        with boundary.operation(), self.assertRaisesRegex(HarnessProcessError, "already_in_use"):
            with boundary.operation():
                self.fail("overlapping boundary must refuse")

    def test_direct_socket_mcp_calls_still_need_closed_scope(self):
        boundary = self.boundary()
        for message in ({"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {}},
                        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "billing_checkout"}},
                        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}, "host": "outside.example"}):
            with self.assertRaises(HarnessProcessError):
                boundary.admit({"_workspace_mcp": message}, None)
        self.assertEqual(boundary.budget.mcp_requests, 0)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        boundary.admit({"_workspace_mcp": message}, None)
        with self.assertRaises(HarnessProcessError):
            boundary.observe({"_workspace_mcp": message}, {"result": {"tools": [{"name": "billing_checkout"}]}})

    def test_snapshot_paths_cannot_escape_or_shadow_native_configuration(self):
        for path in ("../a", "/etc/passwd", "a/../b", "a//b", ".opencode/config.json", "home/auth.json", "a\x00b", None,
                     "a" * 201, "/".join(["a"] * 17)):
            with self.assertRaises(HarnessProcessError):
                customer.CustomerFile(path, b"fixture")

    def test_zero_byte_file_count_and_expired_setup_refuse(self):
        with self.assertRaises(HarnessProcessError):
            self.boundary(files=tuple(customer.CustomerFile(str(index), b"") for index in range(65)))
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(files=(customer.CustomerFile("a", b""),))
            boundary.budget.started_at -= 21
            with self.assertRaises(HarnessProcessError):
                boundary.seed(Path(folder))
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_exact_artifact_bytes_and_seed_identity_are_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            boundary = self.boundary(files=(customer.CustomerFile("src/a.py", b"print(1)\n"),), artifact_paths=("src/a.py",))
            boundary.seed(work)
            boundary.capture(work)
            self.assertEqual(boundary.captured[0].body, b"print(1)\n")
            self.assertEqual(boundary.identity()["files"][0]["sha256"], hashlib.sha256(b"print(1)\n").hexdigest())

    def test_capture_refuses_symlinks_hardlinks_and_oversized_output(self):
        for kind in ("symlink", "hardlink", "size"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                work = Path(folder)
                (work / "source").write_bytes(b"fixture")
                if kind == "symlink":
                    (work / "out").symlink_to(work / "source")
                elif kind == "hardlink":
                    os.link(work / "source", work / "out")
                else:
                    (work / "out").write_bytes(b"oversized")
                with self.assertRaises(HarnessProcessError):
                    self.boundary(artifact_paths=("out",), maximum_file_bytes=2).capture(work)

    def test_fifo_refuses_before_blocking_and_socket_refuses(self):
        # A subprocess timeout makes the old blocking-open implementation a
        # bounded known-wrong control rather than hanging this suite.
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            os.mkfifo(work / "out")
            code = """from pathlib import Path
from loop_engine.core.opencode_customer import *
b = OpenCodeCustomerBoundary(CustomerOperationBudget(1, 1, 5), lambda *_: {}, EFFECTS, artifact_paths=('out',))
try:
    b.capture(Path(__import__('sys').argv[1]))
except HarnessProcessError:
    raise SystemExit(0)
raise SystemExit(1)
"""
            result = subprocess.run([sys.executable, "-c", code, folder], capture_output=True, timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            (work / "out").unlink()
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(str(work / "out"))
                with self.assertRaises(HarnessProcessError):
                    self.boundary(artifact_paths=("out",)).capture(work)

    def test_http_route_method_headers_and_base64_are_closed(self):
        boundary = self.boundary(http=lambda *_: {})
        for value in ({"method": "GET", "path": "https://outside.invalid", "payload": None},
                      {"method": "POST", "path": "/api/v1/signup", "payload": {}},
                      {"method": "GET", "path": "/api/v1/download", "payload": None},
                      {"method": "GET", "path": "/api/v1/capabilities", "payload": None, "headers": {}}):
            with self.assertRaises(HarnessProcessError):
                boundary.admit({"_workspace_http": value}, None)
        self.assertEqual(boundary.budget.mcp_requests, 0)
        body = {"_workspace_http": {"method": "GET", "path": "/api/v1/capabilities", "payload": None}}
        for answer in ({"status": 200, "headers": {}, "body_base64": "!!"},
                       {"status": 200, "headers": {"X": "one\r\ntwo"}, "body_base64": ""}):
            boundary.admit(body, None)
            with self.assertRaises(HarnessProcessError):
                boundary.observe(body, answer)
            boundary.failed(body, "negative_control")

    def test_sdk_cancellation_is_local_only_and_strictly_shaped(self):
        from loop_engine.core import harness_process_relay as relay
        handler_class = relay._handler({"maximum_request_bytes": 4096}, ())
        def handler_for(message):
            raw = json.dumps(message).encode()
            handler = handler_class.__new__(handler_class)
            handler.headers, handler.rfile = {"Content-Length": str(len(raw))}, io.BytesIO(raw)
            handler.send_response, handler.send_header, handler.end_headers = mock.Mock(), mock.Mock(), mock.Mock()
            handler._reply = mock.Mock()
            return handler
        with mock.patch.object(relay, "_exchange", return_value={"result": {}}):
            handler_for({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})._mcp()
        for valid in (True, False):
            message = {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 2}}
            if not valid:
                message["id"] = "not-a-notification"
            handler = handler_for(message)
            with mock.patch.object(relay, "_exchange", side_effect=AssertionError("no service effect")) as exchange:
                if valid:
                    handler._mcp()
                    handler.send_response.assert_called_once_with(202)
                else:
                    with self.assertRaises(ValueError):
                        handler._mcp()
                exchange.assert_not_called()
        self.assertEqual(handler_class.customer_housekeeping["completed_cancellations"], 1)
        with mock.patch.object(relay, "_exchange", side_effect=AssertionError("no service effect")):
            with self.assertRaises(ValueError):
                handler_for({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 99}})._mcp()
        self.assertEqual(handler_class.customer_housekeeping["completed_cancellations"], 1)
        self.assertEqual(handler_class.customer_housekeeping["refused_cancellations"], 1)

    def test_text_runner_cannot_run_workspace_variant(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "work"
            work.mkdir()
            spec = HarnessProcessSpec("opencode.customer_confined", "fixture", ("/usr/bin/python3",), (), "opencode_customer", catalog=fixture_catalog())
            request = HarnessProcessRequest(spec, "private", "fixture", 100, 20, 5, str(work), context_capacity=1000)
            with self.assertRaisesRegex(HarnessProcessError, "text_response_profile_required"):
                run_harness_process(request, lambda _: response())
            weaker = replace(request, spec=replace(spec, process_isolation="trusted_process"))
            with self.assertRaisesRegex(HarnessProcessError, "confined_customer_profile_required"):
                run_workspace_harness_process(weaker, lambda _: response(), self.boundary())
            self.assertEqual(list(work.iterdir()), [])

    def test_never_dispatched_scope_can_be_reused_after_preflight_refusal(self):
        boundary = self.boundary()
        with self.assertRaisesRegex(ValueError, "preflight"):
            with boundary.operation():
                raise ValueError("preflight")
        self.assertTrue(boundary.resources.cleanup_confirmed)
        with boundary.operation():
            self.assertFalse(boundary.resources.dispatched)

    def test_client_mount_uses_exact_private_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary()
            before = boundary.identity()["published_client_sha256"]
            boundary.snapshot_client(Path(folder))
            mounted, target = boundary.read_only_files[0]
            self.assertEqual(target, "/relay/baltor_library_client.py")
            self.assertEqual(Path(mounted).read_bytes(), boundary.published_client)
            self.assertEqual(hashlib.sha256(Path(mounted).read_bytes()).hexdigest(), before)

    def test_resource_cleanup_failure_still_kills_and_waits_local_launcher(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "work"
            work.mkdir()
            spec = HarnessProcessSpec("opencode.customer_confined", "fixture", ("/usr/bin/python3",), (),
                                      "opencode_customer", catalog=fixture_catalog())
            request = HarnessProcessRequest(spec, "fixture", "fixture", 100, 20, 5, str(work), context_capacity=1000)
            proc = mock.Mock(pid=424242, stdout=io.BytesIO(), stderr=io.BytesIO())
            proc.poll.return_value = None
            boundary = self.boundary()
            # This is a mocked cleanup failure, not native sandbox qualification.
            # Keep its prerequisite explicit on CI hosts without Bubblewrap.
            with mock.patch("loop_engine.core.harness_process.subprocess.Popen", return_value=proc), \
                 mock.patch("loop_engine.core.harness_process.shutil.which", return_value="/usr/bin/bwrap"), \
                 mock.patch("loop_engine.core.harness_process.os.killpg") as killpg, \
                 mock.patch.object(CustomerResourceScope, "command", return_value=["offline-fixture"]), \
                 mock.patch.object(CustomerResourceScope, "environment", return_value={}), \
                 mock.patch.object(CustomerResourceScope, "wait_verified", side_effect=HarnessProcessError("fixture_verification_refused")), \
                 mock.patch.object(CustomerResourceScope, "stop", side_effect=OSError("fixture bus unavailable")):
                with self.assertRaisesRegex(HarnessProcessError, "fixture_verification_refused"):
                    run_workspace_harness_process(request, lambda _: response(), boundary)
            killpg.assert_called_once()
            proc.wait.assert_called_once()
            self.assertTrue(proc.stdout.closed and proc.stderr.closed)
            self.assertFalse(boundary.resources.cleanup_confirmed)
            with self.assertRaisesRegex(HarnessProcessError, "previous_cleanup_unconfirmed"):
                with boundary.operation():
                    self.fail("uncertain process cannot start again")

    def test_unconfirmed_cleanup_refuses_artifact_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "work"
            work.mkdir()
            spec = HarnessProcessSpec("opencode.customer_confined", "fixture", ("/usr/bin/python3",), (),
                                      "opencode_customer", catalog=fixture_catalog())
            request = HarnessProcessRequest(spec, "fixture", "fixture", 100, 20, 5, str(work), context_capacity=1000)
            proc = mock.Mock(pid=424242, stdout=io.BytesIO(), stderr=io.BytesIO(), returncode=0)
            proc.poll.return_value = 0
            boundary = self.boundary()
            with mock.patch("loop_engine.core.harness_process.subprocess.Popen", return_value=proc), \
                 mock.patch("loop_engine.core.harness_process.shutil.which", return_value="/usr/bin/bwrap"), \
                 mock.patch.object(CustomerResourceScope, "command", return_value=["offline-fixture"]), \
                 mock.patch.object(CustomerResourceScope, "environment", return_value={}), \
                 mock.patch.object(CustomerResourceScope, "wait_verified", return_value={}), \
                 mock.patch.object(CustomerResourceScope, "stop", side_effect=OSError("fixture bus unavailable")), \
                 mock.patch.object(boundary, "capture") as capture:
                result = run_workspace_harness_process(request, lambda _: response(), boundary)
            capture.assert_not_called()
            self.assertIn("customer_cgroup_cleanup_unknown", result.errors)
            self.assertIn("customer_capture_requires_confirmed_cleanup", result.errors)

    def test_missing_bubblewrap_still_refuses_before_launch_or_broker(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "work"
            work.mkdir()
            spec = HarnessProcessSpec("opencode.customer_confined", "fixture", ("/usr/bin/python3",), (),
                                      "opencode_customer", catalog=fixture_catalog())
            request = HarnessProcessRequest(spec, "fixture", "fixture", 100, 20, 5, str(work), context_capacity=1000)
            boundary, broker = self.boundary(), mock.Mock()
            with mock.patch("loop_engine.core.harness_process.shutil.which", return_value=None), \
                 mock.patch("loop_engine.core.harness_process.subprocess.Popen") as launch:
                with self.assertRaisesRegex(HarnessProcessError, "qualified Bubblewrap executable is unavailable"):
                    run_workspace_harness_process(request, broker, boundary)
            launch.assert_not_called()
            broker.assert_not_called()
            self.assertEqual(list(work.iterdir()), [])

    def test_artifact_export_is_bounded_exact_and_released_only_after_cleanup(self):
        boundary = self.boundary(artifact_paths=("a", "b"), maximum_file_bytes=4)
        row = {"path": "a", "body_base64": base64.b64encode(b"data").decode(), "sha256": hashlib.sha256(b"data").hexdigest()}
        snapshot = {"record_type": "customer_artifact_snapshot/v1", "files": [row]}
        body = {"_workspace_artifacts": snapshot}
        with boundary.operation():
            boundary.admit(body, None)
            answer = boundary.invoke_service(body)
            self.assertFalse(boundary.observe(body, answer))
            self.assertEqual(boundary.captured, [])
            with self.assertRaises(HarnessProcessError):
                boundary.release_artifacts()
            with self.assertRaises(HarnessProcessError):
                boundary.admit(body, None)
            boundary.resources.cleanup_confirmed = True
            boundary.release_artifacts()
            self.assertEqual(boundary.captured[0].body, b"data")
            self.assertEqual((boundary.budget.model_requests, boundary.budget.mcp_requests), (0, 0))
        for rows in ([row, row], [{**row, "path": "../escape"}], [{**row, "sha256": "0" * 64}],
                     [{**row, "body_base64": row["body_base64"][:-1]}],
                     [row, {**row, "path": "b"}], [{**row, "body_base64": "YQ==" * 100}]):
            with self.subTest(rows=rows), self.assertRaises(HarnessProcessError):
                boundary._validate_artifacts({**snapshot, "files": rows})

    def test_capture_detects_parent_path_replacement_without_following_it(self):
        from loop_engine.core import opencode_customer_recipe as recipe
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / "approved").mkdir()
            (work / "approved/data").write_bytes(b"selected")
            (work / "other").mkdir()
            (work / "other/data").write_bytes(b"not selected")
            read = os.read
            moved = False
            def replacing_read(descriptor, size):
                nonlocal moved
                result = read(descriptor, size)
                if not moved:
                    moved = True
                    (work / "approved").rename(work / "moved")
                    (work / "approved").symlink_to(work / "other", target_is_directory=True)
                return result
            with mock.patch.object(recipe.os, "read", side_effect=replacing_read), self.assertRaisesRegex(HarnessProcessError, "path_replaced"):
                self.boundary(artifact_paths=("approved/data",)).capture(work)

    def test_workspace_transport_does_not_silently_enlarge_allowances(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "work"
            work.mkdir()
            spec = HarnessProcessSpec("opencode.customer_confined", "fixture", ("/usr/bin/python3",), (),
                                      "opencode_customer", catalog=fixture_catalog())
            request = HarnessProcessRequest(spec, "fixture", "fixture", 100, 20, 5, str(work), context_capacity=1000,
                                            maximum_request_bytes=1024)
            with self.assertRaisesRegex(HarnessProcessError, "wire_allowance_insufficient"):
                run_workspace_harness_process(request, lambda _: response(), self.boundary())
            self.assertEqual(list(work.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
