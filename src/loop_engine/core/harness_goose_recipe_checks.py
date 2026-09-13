"""Offline checks for the existing process adapter's pinned Goose recipe.

Owns: configuration and output-admission checks with no model or process calls.
Does not own: installed-harness qualification, provider accounting or effects.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from .harness_goose_recipe import extract_goose_output, prepare_goose_recipe


def self_test():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    with tempfile.TemporaryDirectory(prefix="goose-recipe-check-") as tmp:
        root = Path(tmp)
        task = root / "private-task.txt"
        task.write_text("private task", encoding="utf-8")
        config = {"command_prefix": ["/declared/goose"], "model": "exact-model",
                  "workspace_path": str(root), "task_path": str(task), "maximum_request_bytes": 100}
        argv, env, stdin = prepare_goose_recipe(config, "http://127.0.0.1:34567/v1")
        check("goose_private_task_is_stdin_not_command_content", stdin == b"private task" and "private task" not in argv)
        check("goose_native_provider_and_chat_mode_are_explicit", env["GOOSE_PROVIDER"] == "openai"
              and env["GOOSE_MODE"] == "chat" and env["OPENAI_HOST"] == "http://127.0.0.1:34567"
              and env["OPENAI_BASE_PATH"] == "v1/chat/completions")
        check("goose_default_extensions_and_automatic_title_are_suppressed", "--no-profile" in argv
              and "--name" in argv and "--with-builtin" not in argv)
        check("goose_settings_are_inside_declared_workspace", (root / "home/.config/goose/config.yaml").is_file())
        try:
            prepare_goose_recipe(config, "https://other.example/v1")
        except ValueError:
            check("goose_foreign_provider_origin_refused", True)
        else:
            check("goose_foreign_provider_origin_refused", False)
    message = {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "answer"}]}}
    complete = {"type": "complete"}
    stream = json.dumps(message) + "\n" + json.dumps(complete)
    check("goose_final_complete_reply_admitted", extract_goose_output(stream, "answer") == "answer")
    check("goose_partial_reply_not_admitted", not extract_goose_output(json.dumps(message), "answer"))
    failure = {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "unrecoverable error"}]}}
    check("goose_earlier_answer_does_not_mask_final_failure", not extract_goose_output(
        json.dumps(message) + "\n" + json.dumps(failure) + "\n" + json.dumps(complete), "answer"))
    check("goose_error_event_refused", not extract_goose_output(stream + '\n{"type":"error"}', "answer"))
    return {"passed": sum(t["passed"] for t in tests), "total": len(tests), "tests": tests}
