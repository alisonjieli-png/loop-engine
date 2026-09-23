"""Offline checks for the separate brokered OpenCode semantic recipe.

Owns: output and configuration controls. Does not qualify the quarantined raw
host adapter, native effect execution, model quality or real-provider billing.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from .harness_opencode_recipe import extract_opencode_output, prepare_opencode_recipe


def self_test():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    config = {"command_prefix": ["/declared/opencode"], "model": "exact-model",
              "context_capacity": 16384, "output_capacity": 256, "output_allowance": 128}
    with tempfile.TemporaryDirectory(prefix="opencode-recipe-check-") as directory:
        task = Path(directory) / "task.txt"
        task.write_text("first line\n\nthird line: exact ✓\n", encoding="utf-8")
        config["task_path"] = str(task)
        argv, environment, stdin = prepare_opencode_recipe("opencode", config, "http://127.0.0.1:23456/v1")
    body = json.loads(environment["OPENCODE_CONFIG_CONTENT"])
    check("opencode_prompt_is_exact_private_stdin", "--file" not in argv
          and stdin == "first line\n\nthird line: exact ✓\n".encode())
    check("opencode_only_declared_provider_enabled", body["enabled_providers"] == ["engine"]
          and body["provider"]["engine"]["options"]["baseURL"] == "http://127.0.0.1:23456/v1")
    check("opencode_tools_and_permissions_both_disabled", body["tools"] == {"*": False}
          and body["agent"]["loop-engine"]["permission"] == {"*": "deny"})
    check("opencode_ambient_project_and_plugins_disabled", environment["OPENCODE_DISABLE_PROJECT_CONFIG"] == "true"
          and environment["OPENCODE_DISABLE_DEFAULT_PLUGINS"] == "true" and "--pure" in argv)
    check("opencode_state_is_within_private_workspace", environment["XDG_DATA_HOME"].startswith("/work/home/"))
    text = {"type": "text", "part": {"type": "text", "text": "answer"}}
    end = {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop"}}
    stream = json.dumps(text) + "\n" + json.dumps(end)
    check("opencode_exact_stopped_response_admitted", extract_opencode_output("opencode", stream, "answer") == "answer")
    check("opencode_unterminated_response_refused", not extract_opencode_output("opencode", json.dumps(text), "answer"))
    check("opencode_native_tool_event_refused", not extract_opencode_output(
        "opencode", stream + '\n{"type":"tool_use","part":{"type":"tool"}}', "answer"))
    check("opencode_error_after_answer_refused", not extract_opencode_output("opencode", stream + '\n{"type":"error"}', "answer"))
    check("opencode_foreign_content_refused", not extract_opencode_output("opencode", stream, "other"))
    check("opencode_functions_refuse_another_style", not extract_opencode_output("kilo", stream, "answer"))
    return {"passed": sum(t["passed"] for t in tests), "total": len(tests), "tests": tests}
