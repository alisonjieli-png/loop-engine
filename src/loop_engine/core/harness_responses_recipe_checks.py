"""Offline checks for the explicit Codex-family text protocol boundary.

Owns configuration, codec and terminal refusal controls. Real installed CLI
and provider qualification remain separate evidence.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile

from .harness_responses_recipes import (ResponsesRecipeError, prepare_responses_recipe,
    decode_responses_text_request, encode_responses_text_events, extract_responses_output)


def self_test():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    def refused(name, callback):
        try:
            callback()
        except ResponsesRecipeError:
            check(name, True)
        else:
            check(name, False)
    with tempfile.TemporaryDirectory(prefix="responses-recipe-") as directory:
        root = Path(directory)
        task = root / "task.txt"
        task.write_text("Private complete task\nwith another line.")
        config = {"command_prefix": ["/declared/codex"], "model": "exact-model", "workspace_path": str(root),
                  "task_path": str(task), "output_allowance": 77, "context_capacity": 20000,
                  "timeout_seconds": 120}
        for style, key, folder in (("codex", "CODEX_HOME", ".codex"),
                                   ("openinterpreter_rust", "INTERPRETER_HOME", ".openinterpreter")):
            argv, env, stdin = prepare_responses_recipe(style, config, "http://127.0.0.1:12345/v1")
            home = root / "home" / folder
            settings = (home / "config.toml").read_text()
            catalog = json.loads((home / "models.json").read_text())["models"][0]
            check(style + "_task_is_private_stdin", stdin == task.read_bytes() and "Private complete task" not in " ".join(argv))
            expected_wire = "chat" if style == "openinterpreter_rust" else "responses"
            check(style + "_private_home_and_responses_provider", env[key] == str(home)
                  and f'wire_api = "{expected_wire}"' in settings and 'requires_openai_auth = false' in settings)
            check(style + "_native_tools_absent_in_model_catalog", catalog["shell_type"] == "disabled"
                  and catalog["apply_patch_tool_type"] is None and catalog["experimental_supported_tools"] == [])
            check(style + "_native_feature_and_skill_gates", 'shell_tool = false' in settings
                  and 'view_image = false' in settings and '[tools.experimental_request_user_input]\nenabled = false' in settings
                  and '[skills.bundled]\nenabled = false' in settings)
            check(style + "_context_capacity_from_caller", catalog["context_window"] == 20000)
        for base in ("https://127.0.0.1:12345/v1", "http://other.example:12345/v1",
                     "http://secret@127.0.0.1:12345/v1", "http://127.0.0.1:12345/v1?x=y"):
            refused("foreign_provider_" + str(len(tests)), lambda base=base: prepare_responses_recipe("codex", config, base))
        refused("missing_typed_context_refused", lambda: prepare_responses_recipe("codex", {**config, "context_capacity": None}, "http://127.0.0.1:12345/v1"))
    body = {"model": "exact-model", "instructions": "System", "input": [{"role": "user",
        "content": [{"type": "input_text", "text": "Task\nbody"}]}], "stream": True, "store": False,
        "tools": [], "tool_choice": "auto", "reasoning": {}, "include": ["reasoning.encrypted_content"],
        "client_metadata": {"thread_id": "private-id"}, "max_output_tokens": 77}
    decoded = decode_responses_text_request("/v1/responses", body, "exact-model")
    check("text_contract_preserved", decoded == {"model": "exact-model", "stream": False, "max_tokens": 77,
          "messages": [{"role": "system", "content": "System"}, {"role": "user", "content": "Task\nbody"}]})
    for change in ({"tools": [{"type": "function", "name": "exec_command"}]}, {"tools": {}},
                   {"tool_choice": "required"}, {"previous_response_id": "other"}, {"model": "other"},
                   {"reasoning": {"effort": "high"}}, {"text": {"format": {"type": "json_schema"}}},
                   {"store": True}, {"store": "false"}, {"stream": "true"}, {"max_output_tokens": True},
                   {"client_metadata": {"authority": {"nested": "denied"}}},
                   {"input": [{"type": "function_call_output", "call_id": "x", "output": "done"}]},
                   {"input": [{"role": "user", "content": [{"type": "input_image", "image_url": "x"}]}]}):
        refused("unsafe_or_unsupported_request_" + str(len(tests)), lambda change=change:
                decode_responses_text_request("/v1/responses", {**body, **change}, "exact-model"))
    response = {"id": "resp-fixture", "model": "exact-model", "choices": [{"message": {
        "role": "assistant", "content": "Unchanged answer"}, "finish_reason": "stop"}]}
    events = encode_responses_text_events(response, "exact-model")
    check("finite_event_sequence_preserves_candidate", len(events) == 8 and events[-1]["type"] == "response.completed"
          and events[-1]["response"]["output"][0]["content"][0]["text"] == "Unchanged answer")
    check("missing_provider_usage_stays_unknown", "usage" not in events[-1]["response"])
    partial = encode_responses_text_events({**response, "usage": {"prompt_tokens": 7}}, "exact-model")
    check("partial_provider_usage_stays_partial", partial[-1]["response"]["usage"] == {"input_tokens": 7})
    tool = deepcopy(response)
    tool["choices"][0]["message"]["tool_calls"] = [{"name": "exec_command"}]
    refused("native_provider_tool_refused", lambda: encode_responses_text_events(tool, "exact-model"))
    truncated = deepcopy(response)
    truncated["choices"][0]["finish_reason"] = "length"
    refused("partial_provider_completion_refused", lambda: encode_responses_text_events(truncated, "exact-model"))
    rows = [{"type": "thread.started", "thread_id": "fixture"}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "answer"}},
            {"type": "turn.completed"}]
    lines = "\n".join(json.dumps(row) for row in rows)
    for style in ("codex", "openinterpreter_rust"):
        check(style + "_exact_completed_turn_accepted", extract_responses_output(style, lines, "answer") == "answer")
        check(style + "_foreign_or_missing_completion_refused", not extract_responses_output(style, lines, "other")
              and not extract_responses_output(style, "\n".join(json.dumps(row) for row in rows[:-1]), "answer"))
        native = rows[:2] + [{"type": "item.completed", "item": {"type": "command_execution"}}] + rows[2:]
        check(style + "_native_execution_refused", not extract_responses_output(style, "\n".join(json.dumps(row) for row in native), "answer"))
    return {"passed": sum(test["passed"] for test in tests), "total": len(tests), "tests": tests}
