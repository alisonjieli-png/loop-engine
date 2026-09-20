"""Focused offline process-isolation and broker-boundary verification.

The fixture CLI exercises real Bubblewrap, Unix relay, HTTP and cancellation.
It is not provider integration or evidence about a third-party model's quality.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
import contextvars
import sys
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from .harness_process import (
    HarnessProcessError, HarnessProcessRequest, HarnessProcessSpec, run_harness_process)


_CLI = '''import json, os, pathlib, subprocess, sys, time, urllib.request
mode = sys.argv[1]
if mode == "timeout":
    subprocess.Popen(["/usr/bin/python3", "-c", "import time; from pathlib import Path; time.sleep(0.8); Path('/work/late-effect').write_text('late')"])
    time.sleep(10)
    sys.exit()
if mode == "flood":
    print("x" * 20000)
    sys.exit()
if mode == "binary":
    os.write(1, b"\\xff" * 20000)
    sys.exit()
if mode == "instructions":
    material = pathlib.Path("/work/AGENTS.md")
    if material.read_text() != "fixture instruction":
        sys.exit(7)
    try:
        material.write_text("changed")
    except OSError:
        pass
    else:
        sys.exit(8)
base = sys.argv[sys.argv.index("--openai-api-base") + 1]
model = sys.argv[sys.argv.index("--model") + 1].removeprefix("openai/")
task = pathlib.Path(sys.argv[sys.argv.index("--message-file") + 1]).read_text()
body = {"model": "foreign" if mode == "bad-model" else model,
        "messages": [{"role": "user", "content": task}], "max_tokens": 99999,
        "metadata": {"inherited_secret": "LE_PROCESS_FIXTURE_SECRET" in os.environ,
                     "original_home_visible": pathlib.Path("/home/username/.codex").exists()}}
if mode == "oversize":
    body["padding"] = "x" * 10000
if mode == "tools":
    body["tools"] = [{"type": "function", "function": {"name": "forbidden"}}]
try:
    request = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=3) as response:
        value = json.load(response)
    print(value["choices"][0]["message"]["content"])
except Exception:
    sys.exit(4)
'''


def qualification_checks():
    """Linux-only OS qualification; explicitly separate from base self-test."""
    tests = []
    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="le-process-check-") as temporary:
        root = Path(temporary)
        software, work = root / "software", root / "work"
        software.mkdir()
        work.mkdir()
        script = software / "cli.py"
        script.write_text(_CLI)

        def request(mode="text", **kwargs):
            spec = HarnessProcessSpec("process_fixture", "1.0.0",
                ("/usr/bin/python3", str(script), mode), (str(software),), "aider")
            return HarnessProcessRequest(spec, "private task fixture", "fixture-model", 64, 16,
                5.0, str(work), socket_directory=str(root.parent), **kwargs)

        received = []
        owner_context = contextvars.ContextVar("harness_check_owner", default="missing")
        owner_context.set("canonical-caller")
        observed_contexts = []
        def broker(body):
            received.append(body)
            observed_contexts.append(owner_context.get())
            return {"id": "fixture", "object": "chat.completion", "model": "fixture-model",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "fixture answer"},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}}

        with patch.dict(os.environ, {"LE_PROCESS_FIXTURE_SECRET": "never-visible"}):
            result = run_harness_process(request(), broker)
        check("isolated_cli_reaches_explicit_broker_with_private_task", result.ok
              and result.output == "fixture answer" and len(received) == 1,
              str(result.errors))
        check("host_configuration_and_credentials_are_not_inherited", received
              and received[0]["metadata"] == {"inherited_secret": False, "original_home_visible": False})
        check("typed_output_allocation_reaches_broker_not_cli_default", received
              and received[0]["max_tokens"] == 16 and received[0]["stream"] is False)
        check("exact_request_is_retained_before_broker_normalization", result.exchanges
              and json.loads(result.exchanges[0].request_json)["max_tokens"] == 99999
              and len(result.exchanges[0].response_digest) == 64)
        check("broker_preserves_calling_loop_context", observed_contexts == ["canonical-caller"])
        full = request()
        full = replace(full, output_allowance=None)
        check("absent_allocation_uses_full_declared_capacity", full.output_allowance == 64)
        import hashlib
        from .instance_instructions import InstructionMaterial
        material = InstructionMaterial("AGENTS.md", "fixture instruction",
                                       hashlib.sha256(b"fixture instruction").hexdigest())
        supplied = run_harness_process(request("instructions", instruction_material=(material,)), broker)
        check("instructions_reach_the_actual_native_working_directory_as_read_only_files",
              supplied.ok and supplied.instruction_manifest == ((material.name, material.digest),))

        calls = len(received)
        wrong = run_harness_process(request("bad-model"), broker)
        check("foreign_model_is_refused_before_broker", not wrong.ok and len(received) == calls
              and "request_identity_mismatch" in wrong.errors and wrong.broker_request_count == 0
              and wrong.received_request_count == 1)
        tools = run_harness_process(request("tools"), broker)
        check("native_tool_schema_cannot_cross_model_boundary", not tools.ok
              and len(received) == calls and "native_tools_not_authorized" in tools.errors)
        oversize = run_harness_process(request("oversize", maximum_request_bytes=2048), broker)
        check("oversize_http_body_never_reaches_broker", not oversize.ok and len(received) == calls)
        flood = run_harness_process(request("flood", maximum_output_bytes=1024), broker)
        check("stdout_memory_is_bounded_during_capture", flood.stdout_truncated
              and len(flood.stdout.encode()) <= 1024 and "process_output_limit" in flood.errors)
        binary = run_harness_process(request("binary", maximum_output_bytes=1024), broker)
        check("invalid_utf8_cannot_expand_returned_output_past_bound", binary.stdout_truncated
              and len(binary.stdout.encode()) <= 1024 and not binary.ok)

        def unavailable(body):
            raise RuntimeError("fixture transport unavailable")
        failure = run_harness_process(request(), unavailable)
        check("broker_failure_is_retained_without_synthetic_success", not failure.ok
              and failure.broker_request_count == 1 and failure.exchanges[0].error_code
              == "broker_RuntimeError" and not failure.output)

        def tool_response(body):
            value = broker(body)
            value["choices"][0]["message"]["tool_calls"] = [{"id": "forbidden"}]
            return value
        denied = run_harness_process(request(), tool_response)
        check("broker_tool_response_never_enters_harness", not denied.ok
              and "broker_response_not_text" in denied.errors
              and bool(denied.exchanges[0].response_digest))

        def large_response(body):
            value = broker(body)
            value["choices"][0]["message"]["content"] = "x" * 4096
            return value
        large = run_harness_process(request(maximum_response_bytes=1024), large_response)
        check("oversize_broker_response_is_refused", not large.ok
              and "response_byte_limit" in large.errors and large.broker_request_count == 1)

        timed = run_harness_process(replace(request("timeout"), timeout_seconds=0.25), broker)
        time.sleep(1.0)
        check("deadline_kills_descendants_before_late_workspace_effect", timed.timed_out
              and timed.elapsed_seconds < 3 and not list(work.rglob("late-effect")))

        frozen = request()
        script.write_text(_CLI + "\n# changed installed fixture\n")
        refused = False
        try:
            run_harness_process(frozen, broker)
        except HarnessProcessError:
            refused = True
        check("software_drift_is_refused_before_process_start", refused)

        for label, values in (
            ("allocation_exceeds_capacity", {"output_allowance": 65}),
            ("unknown_capacity", {"output_capacity": 0}),
            ("invalid_deadline", {"timeout_seconds": float("nan")}),
        ):
            refused = False
            try:
                replace(request(), **values)
            except HarnessProcessError:
                refused = True
            check(label + "_refused", refused)
        link = root / "linked-work"
        link.symlink_to(work, target_is_directory=True)
        refused = False
        try:
            replace(request(), work_dir=str(link))
        except HarnessProcessError:
            refused = True
        check("symlink_workspace_refused", refused)

    return {"record_type": "harness_process_checks/v1", "tests": tests,
            "passed": sum(test["passed"] for test in tests), "total": len(tests),
            "all_passed": all(test["passed"] for test in tests)}


def self_test():
    """Pure contracts and parsers; no Bubblewrap, subprocess, socket or provider."""
    from .harness_process import HarnessProcessResult, _output
    from .harness_process_relay import _decode, _stream_chunks
    tests = []
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})
    response = {"id": "fixture", "model": "fixture-model", "choices": [{"index": 0,
        "message": {"role": "assistant", "content": '{"answer":7}'}, "finish_reason": "stop"}]}
    check("continue_direct_json_matches_broker_reply", _output("continue", '{"answer":7}\n', response)
          == '{"answer":7}')
    check("aider_output_is_verified_against_actual_stdout", _output("aider",
          'banner\n{"answer":7}\nfooter', response) == '{"answer":7}'
          and _output("aider", "no corresponding output", response) == "")
    pi = {"type": "message_end", "message": {"role": "assistant", "stopReason": "stop",
          "content": [{"type": "text", "text": '{"answer":7}'}]}}
    check("pi_terminal_output_is_extracted_once", _output("pi", json.dumps(pi), response) == '{"answer":7}')
    pi["message"]["stopReason"] = "error"
    check("pi_failed_partial_message_is_not_success", _output("pi", json.dumps(pi), response) == "")
    empty = HarnessProcessResult(0, False, "", "", "", (), "a" * 64, 0)
    check("zero_exit_without_output_is_not_completion", not empty.ok)
    chunks = tuple(_stream_chunks(response))
    check("missing_provider_usage_remains_missing", all("usage" not in item for item in chunks))
    refused = False
    try:
        _decode(b'{"model":"a","model":"b"}')
    except ValueError:
        refused = True
    check("duplicate_json_fields_are_refused", refused)
    with tempfile.TemporaryDirectory(prefix="le-contract-") as temporary:
        root = Path(temporary)
        software, work = root / "software", root / "work"
        software.mkdir()
        work.mkdir()
        script = software / "identity.txt"
        script.write_text("passive fixture identity")
        spec = HarnessProcessSpec("process_fixture", "1.0.0", (sys.executable,), (str(software),), "aider")
        base = HarnessProcessRequest(spec, "fixture", "model", 64, None, 1, str(work),
                                     socket_directory=str(root.parent))
        check("default_allocation_is_full_explicit_capacity", base.output_allowance == 64)
        for label, values in (("zero_capacity", {"output_capacity": 0}),
                              ("excess_allocation", {"output_allowance": 65}),
                              ("nonfinite_deadline", {"timeout_seconds": float("nan")})):
            refused = False
            try:
                replace(base, **values)
            except HarnessProcessError:
                refused = True
            check(label + "_refused", refused)
    return {"record_type": "harness_process_contract_checks/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
