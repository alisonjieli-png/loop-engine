"""Offline checks for the explicit mini-SWE-agent semantic SDK adapter.

Owns: private recipe and submission/output contracts without third-party imports.
Does not own: installed SDK qualification, real model quality or acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from .harness_mini_swe_recipe import (
    SemanticSubmissionEnvironment, _submission, extract_mini_swe_output,
    prepare_mini_swe_recipe,
)


def self_test():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    with tempfile.TemporaryDirectory(prefix="mini-semantic-check-") as tmp:
        root = Path(tmp)
        task = root / "task.txt"
        task.write_text("private task", encoding="utf-8")
        config = {"command_prefix": ["/declared/python"], "model": "exact-model",
                  "workspace_path": str(root), "task_path": str(task),
                  "output_allowance": 77, "timeout_seconds": 31}
        argv, env, stdin = prepare_mini_swe_recipe("mini_swe_agent", config, "http://127.0.0.1:23456/v1")
        body = json.loads((root / "mini-semantic-config.json").read_text())
        check("mini_task_body_is_private_config_not_argv", "private task" not in argv
              and stdin is None and body["task"] == "private task")
        check("mini_allowance_and_timeout_come_from_caller", body["output_allowance"] == 77
              and body["timeout_seconds"] == 31)
        check("mini_home_and_user_startup_are_isolated", env["MSWEA_GLOBAL_CONFIG_DIR"].startswith(str(root))
              and env["PYTHONNOUSERSITE"] == "1")
        try:
            prepare_mini_swe_recipe("mini_swe_agent", config, "https://other.example/v1")
        except ValueError:
            check("mini_foreign_relay_refused", True)
        else:
            check("mini_foreign_relay_refused", False)
    check("mini_environment_does_not_project_host_environment", SemanticSubmissionEnvironment().get_template_vars() == {})
    check("mini_submission_is_data_not_shell_execution", _submission({"command": "candidate text"}) == "candidate text")
    for action in ({"command": "", "native_tool": "write"}, {"command": ""}, {"tool": "bash"}):
        try:
            _submission(action)
        except ValueError:
            check("mini_malformed_submission_refused_" + str(len(tests)), True)
        else:
            check("mini_malformed_submission_refused_" + str(len(tests)), False)
    row = {"type": "mini_swe_semantic_result", "exit_status": "Submitted", "candidate": "answer",
           "native_execution": False, "ok": True}
    check("mini_exact_candidate_admitted_only_after_submission", extract_mini_swe_output("mini_swe_agent", json.dumps(row), "answer") == "answer")
    check("mini_failed_or_native_execution_result_refused", not extract_mini_swe_output(
        "mini_swe_agent", json.dumps({**row, "native_execution": True}), "answer")
        and not extract_mini_swe_output("mini_swe_agent", json.dumps({**row, "ok": False}), "answer"))
    check("mini_foreign_candidate_refused", not extract_mini_swe_output("mini_swe_agent", json.dumps(row), "other"))
    check("mini_functions_refuse_another_style", not extract_mini_swe_output("gptme", json.dumps(row), "answer"))
    return {"passed": sum(t["passed"] for t in tests), "total": len(tests), "tests": tests}
