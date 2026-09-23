"""Offline contracts for lightweight text recipes and the Messages codec.

Owns positive and refusal cases, not installation, execution authority or
model-quality claims. Installed-process qualification is separate.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile

from .harness_lightweight_recipes import (LightweightRecipeError, decode_anthropic_text_request,
    encode_anthropic_text_response, extract_lightweight_output, prepare_lightweight_recipe,
    prepare_trae_semantic_recipe)


def self_test():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    def refused(name, callback):
        try:
            callback()
        except LightweightRecipeError:
            check(name, True)
        else:
            check(name, False)
    with tempfile.TemporaryDirectory(prefix="lightweight-recipe-") as directory:
        root = Path(directory)
        task = root / "task.txt"
        task.write_text("Private task with\nmultiple lines.")
        config = {"command_prefix": ["/declared/python", "/declared/nanocode.py"],
                  "model": "exact-model", "workspace_path": str(root), "task_path": str(task),
                  "output_allowance": 99, "maximum_request_bytes": 2000}
        argv, environment, stdin = prepare_lightweight_recipe("nanocode", config, "http://127.0.0.1:12345/v1")
        settings = json.loads((root / "nanocode-private.json").read_text())
        wrapper = (root / "nanocode-headless.py").read_text()
        check("nano_complete_private_task_stays_out_of_argv", "Private task" not in " ".join(argv)
              and settings["task"] == str(task) and stdin is None)
        check("nano_source_and_endpoint_are_explicit", settings["source"] == "/declared/nanocode.py"
              and settings["base_url"] == "http://127.0.0.1:12345/v1")
        check("nano_empty_tool_registry_precedes_agent_main", wrapper.index("entry.TOOLS = {}") < wrapper.index("entry.main()"))
        check("nano_environment_contains_no_real_key", not any("KEY" in key for key in environment))
        for base in ("https://127.0.0.1:12345/v1", "http://foreign.example:12345/v1",
                     "http://secret@127.0.0.1:12345/v1", "http://127.0.0.1:12345/v1?x=1"):
            refused("foreign_endpoint_" + str(len(tests)), lambda base=base: prepare_lightweight_recipe("nanocode", config, base))
        refused("missing_allocation", lambda: prepare_lightweight_recipe("nanocode", {**config, "output_allowance": None}, "http://127.0.0.1:12345/v1"))
        refused("freebuff_hosted_protocol_refused", lambda: prepare_lightweight_recipe("freebuff", config, "http://127.0.0.1:12345/v1"))
        argv, _, _ = prepare_lightweight_recipe("trae_agent", {**config, "command_prefix": ["/declared/trae-cli"]}, "http://127.0.0.1:12345/v1")
        trae = json.loads((root / "trae-private.yaml").read_text())
        check("trae_config_requests_no_optional_models_or_native_tools", trae["agents"]["trae_agent"]["tools"] == []
              and trae["agents"]["trae_agent"]["enable_lakeview"] is False and trae["mcp_servers"] == {})
        check("trae_exact_allocation_and_one_step", trae["models"]["loop_engine"]["max_tokens"] == 99
              and trae["agents"]["trae_agent"]["max_steps"] == 1)
        argv, _, _ = prepare_trae_semantic_recipe("trae_agent", {**config, "command_prefix": ["/declared/python"]}, "http://127.0.0.1:12345/v1")
        sdk = (root / "trae-semantic.py").read_text()
        check("trae_semantic_invokes_upstream_agent_run", "await engine.run(" in sdk and "tool_names=[]" in sdk
              and "client.chat" not in sdk and "max_steps" not in sdk)
        refused("trae_semantic_profile_refuses_another_style", lambda: prepare_trae_semantic_recipe(
            "nanocode", {**config, "command_prefix": ["/declared/python"]}, "http://127.0.0.1:12345/v1"))
        check("trae_completion_requires_stopped_text_without_tools", "response.finish_reason == 'stop'" in sdk
              and "not response.tool_calls" in sdk and "bool(response.content)" in sdk)
    request = {"model": "exact-model", "max_tokens": 8192, "system": "System",
               "messages": [{"role": "user", "content": "Task\nbody"}], "tools": []}
    converted = decode_anthropic_text_request("/v1/messages", request, "exact-model")
    check("messages_codec_preserves_text_model_and_allowance", converted == {"model": "exact-model",
          "max_tokens": 8192, "stream": False, "messages": [{"role": "system", "content": "System"},
          {"role": "user", "content": "Task\nbody"}]})
    for change in ({"tools": [{"name": "bash"}]}, {"tool_choice": {"type": "auto"}},
                   {"model": "other"}, {"max_tokens": True}, {"temperature": float("nan")},
                   {"stream": True}, {"messages": [{"role": "user", "content": [{"type": "tool_result"}]}]}):
        refused("messages_request_refusal_" + str(len(tests)), lambda change=change:
                decode_anthropic_text_request("/v1/messages", {**request, **change}, "exact-model"))
    response = {"id": "fixture", "model": "exact-model", "choices": [{"message": {
                "role": "assistant", "content": "Unchanged text"}, "finish_reason": "stop"}]}
    encoded = encode_anthropic_text_response(response, "exact-model")
    check("response_text_exact_and_missing_usage_unknown", encoded["content"] == [{"type": "text", "text": "Unchanged text"}]
          and "usage" not in encoded)
    check("partial_usage_stays_partial", encode_anthropic_text_response({**response, "usage": {"prompt_tokens": 7}},
          "exact-model")["usage"] == {"input_tokens": 7})
    tool = deepcopy(response)
    tool["choices"][0]["message"]["tool_calls"] = [{"id": "untrusted"}]
    refused("response_native_tool_refused", lambda: encode_anthropic_text_response(tool, "exact-model"))
    truncated = deepcopy(response)
    truncated["choices"][0]["finish_reason"] = "length"
    refused("incomplete_response_refused", lambda: encode_anthropic_text_response(truncated, "exact-model"))
    check("nano_exact_display_accepted", extract_lightweight_output("nanocode", "\x1b[36m⏺\x1b[0m answer\n", "answer") == "answer")
    check("nano_display_error_and_mismatch_refused", not extract_lightweight_output("nanocode", "⏺ answer\n⏺ Error: refusal", "answer")
          and not extract_lightweight_output("nanocode", "⏺ answer", "different"))
    check("stock_cli_and_hosted_project_do_not_emit_accepted_output", not extract_lightweight_output("trae_agent", "answer", "answer")
          and not extract_lightweight_output("freebuff", "answer", "answer"))
    trae_result = {"type": "trae_semantic_result", "profile": "trae_text_submission/v1", "ok": True,
                   "upstream_success": True, "native_tool_registry_empty": True,
                   "native_tool_calls_seen": False, "candidate": "answer"}
    check("trae_exact_completed_semantic_submission_admitted", extract_lightweight_output("trae_agent", json.dumps(trae_result), "answer") == "answer")
    for change in ({"ok": False}, {"upstream_success": False}, {"native_tool_registry_empty": False},
                   {"native_tool_calls_seen": True}, {"candidate": "other"}, {"profile": "unknown"}):
        check("trae_incomplete_or_tool_candidate_refused_" + str(len(tests)), not extract_lightweight_output(
              "trae_agent", json.dumps({**trae_result, **change}), "answer"))
    return {"passed": sum(test["passed"] for test in tests), "total": len(tests), "tests": tests}
