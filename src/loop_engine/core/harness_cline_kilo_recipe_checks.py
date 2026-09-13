"""Portable recipe and terminal checks for Cline and Kilo.

These fixtures exercise configuration and output admission without launching
a CLI. Installed-process and real-provider qualification are separate.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile

from .harness_cline_kilo_recipes import (
    CLINE_DISABLED_TOOLS, extract_cline_kilo_output, prepare_cline_kilo_recipe)


def self_test():
    tests = []
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})
    with tempfile.TemporaryDirectory(prefix="cline-kilo-check-") as temporary:
        work = Path(temporary)
        task = work / "task.txt"
        secret_prompt = "Private semantic task fixture"
        task.write_text(secret_prompt, encoding="utf-8")
        config = {"command_prefix": ("fixture-cli",), "model": "exact-model:version",
            "workspace_path": str(work), "task_path": str(task), "maximum_request_bytes": 4096,
            "output_capacity": 1024, "output_allowance": 512, "context_capacity": 8192,
            "timeout_seconds": 20}
        for style in ("cline", "kilo"):
            command, environment, stdin = prepare_cline_kilo_recipe(style, config, "http://127.0.0.1:4321/v1")
            check(style + "_task_uses_private_stdin_not_argv", stdin == secret_prompt.encode()
                  and all(secret_prompt not in part for part in command))
            if style == "cline":
                stored = json.loads(Path(environment["CLINE_PROVIDER_SETTINGS_PATH"]).read_text())
                globals_ = json.loads(Path(environment["CLINE_GLOBAL_SETTINGS_PATH"]).read_text())
                entry = stored["providers"]["openai-compatible"]
                check("cline_schema_binds_exact_private_endpoint_and_model", entry["updatedAt"].endswith("Z")
                    and entry["settings"]["baseUrl"] == "http://127.0.0.1:4321/v1"
                    and entry["settings"]["model"] == config["model"])
                check("cline_closes_known_native_tools_and_compaction", set(globals_["disabledTools"])
                    == set(CLINE_DISABLED_TOOLS) and "editor" in globals_["disabledTools"]
                    and globals_["compactionEnabled"] is False and globals_["toolAutoApprove"] is False)
            else:
                stored = json.loads(environment["KILO_CONFIG_CONTENT"])
                check("kilo_preserves_deny_all_with_private_input", stored["tools"] == {"*": False}
                    and stored["permission"] == {"*": "deny"} and "--file" not in command and "--pure" in command)
                limit = stored["provider"]["engine"]["models"][config["model"]]["limit"]
                check("kilo_keeps_output_and_context_capacities_separate", limit == {"context": 8192, "output": 1024})
        for url in ("https://api.example.test/v1", "http://localhost:4321/v1", "http://user:pass@127.0.0.1:4321/v1"):
            refused = False
            try:
                prepare_cline_kilo_recipe("cline", config, url)
            except ValueError:
                refused = True
            check("external_or_credentialed_endpoint_refused_" + str(len(tests)), refused)
        for values in ({"output_capacity": 0}, {"output_allowance": 1025}, {"model": "--help"}, {"task_path": "relative"}):
            refused = False
            try:
                prepare_cline_kilo_recipe("cline", {**config, **values}, "http://127.0.0.1:4321/v1")
            except ValueError:
                refused = True
            check("invalid_typed_recipe_field_refused_" + str(len(tests)), refused)
        refused = False
        try:
            prepare_cline_kilo_recipe("kilo", {**config, "context_capacity": None}, "http://127.0.0.1:4321/v1")
        except ValueError:
            refused = True
        check("kilo_unknown_context_capacity_refused", refused)

    answer = '{"answer":7}'
    cline = [{"type": "agent_event", "event": {"type": "done", "reason": "completed", "text": answer}},
             {"type": "run_result", "finishReason": "completed", "text": answer}]
    kilo = [{"type": "text", "part": {"type": "text", "text": answer}},
            {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop"}}]
    def render(rows):
        return "\n".join(json.dumps(row) for row in rows)
    for style, rows in (("cline", cline), ("kilo", kilo)):
        check(style + "_requires_exact_successful_terminal_text", extract_cline_kilo_output(style, render(rows), answer) == answer)
        check(style + "_missing_terminal_refused", extract_cline_kilo_output(style, render(rows[:-1]), answer) == "")
        check(style + "_duplicate_terminal_refused", extract_cline_kilo_output(style, render(rows + rows[-1:]), answer) == "")
        check(style + "_mismatched_or_empty_output_refused", extract_cline_kilo_output(style, render(rows), "other") == ""
              and extract_cline_kilo_output(style, "", answer) == "")
        check(style + "_error_after_success_refused", extract_cline_kilo_output(style, render(rows + [{"type": "error"}]), answer) == "")
    aborted = deepcopy(cline)
    aborted[-1]["finishReason"] = "aborted"
    check("cline_zero_exit_aborted_body_not_completion", extract_cline_kilo_output("cline", render(aborted), answer) == "")
    native = cline + [{"type": "agent_event", "event": {"type": "content_start", "contentType": "tool", "toolName": "editor"}}]
    check("cline_native_tool_record_refused", extract_cline_kilo_output("cline", render(native), answer) == "")
    native = kilo + [{"type": "tool_use", "part": {"type": "tool", "tool": "bash"}}]
    check("kilo_native_tool_record_refused", extract_cline_kilo_output("kilo", render(native), answer) == "")
    return {"record_type": "harness_cline_kilo_recipe_checks/v1", "tests": tests,
        "passed": sum(row["passed"] for row in tests), "total": len(tests),
        "all_passed": all(row["passed"] for row in tests)}
