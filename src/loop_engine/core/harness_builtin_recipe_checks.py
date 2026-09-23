"""Offline checks for the Aider, Continue and Pi recipes.

Owns: the preparation and output admission contracts of the three recipes
that moved out of the relay and the runner (plan package X1). These checks
write only temporary files; they start no process and call no provider.
Installed-process qualification is separate evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from .harness_builtin_recipes import (BuiltinRecipeError, extract_builtin_output,
                                      prepare_builtin_recipe)


def self_test() -> dict:
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    def refused(operation):
        try:
            operation()
        except BuiltinRecipeError:
            return True
        return False

    base = "http://127.0.0.1:43210/v1"
    with tempfile.TemporaryDirectory(prefix="builtin-recipe-check-") as directory:
        root = Path(directory)
        config = {"command_prefix": ["/declared/cli"], "model": "exact-model",
                  "workspace_path": str(root), "task_path": "/relay/task.txt",
                  "output_allowance": 77, "output_capacity": 128, "context_capacity": 4096}
        argv, environment, prompt = prepare_builtin_recipe("aider", config, base)
        check("aider_reads_the_private_task_file_and_the_relay_only",
              argv[argv.index("--openai-api-base") + 1] == base
              and argv[argv.index("--model") + 1] == "openai/exact-model"
              and argv[-2:] == ("--message-file", "/relay/task.txt")
              and environment == {} and prompt is None)
        argv, _, _ = prepare_builtin_recipe("continue", config, base)
        settings = json.loads((root / "model-config.yaml").read_text())
        check("continue_config_binds_the_relay_and_the_output_allowance",
              settings["models"][0]["apiBase"] == base
              and settings["models"][0]["defaultCompletionOptions"] == {"maxTokens": 77}
              and argv[argv.index("--config") + 1] == str(root / "model-config.yaml")
              and argv[argv.index("--prompt") + 1] == "/relay/task.txt")
        argv, _, _ = prepare_builtin_recipe("pi", config, base)
        models = json.loads((root / "home/.pi/agent/models.json").read_text())
        model = models["providers"]["engine"]["models"][0]
        check("pi_models_carry_the_explicit_capacities_and_no_tools",
              model["contextWindow"] == 4096 and model["maxTokens"] == 128
              and "--no-tools" in argv and argv[-1] == "@/relay/task.txt")
        check("a_foreign_style_or_address_is_refused",
              refused(lambda: prepare_builtin_recipe("goose", config, base))
              and refused(lambda: prepare_builtin_recipe("aider", config, "http://example.com:1/v1"))
              and refused(lambda: prepare_builtin_recipe("aider", config, "http://127.0.0.1:1/other"))
              and refused(lambda: prepare_builtin_recipe(
                  "aider", {**config, "workspace_path": "relative"}, base)))
    check("aider_admits_only_the_exact_broker_text",
          extract_builtin_output("aider", "banner\nanswer\nfooter", "answer") == "answer"
          and extract_builtin_output("aider", "no match", "answer") == "")
    check("continue_admits_the_wrapper_or_the_direct_json_answer",
          extract_builtin_output("continue", '{"status":"success","response":"answer"}', "answer") == "answer"
          and extract_builtin_output("continue", '{"answer":7}\n', '{"answer":7}') == '{"answer":7}')
    finished = {"type": "message_end", "message": {"role": "assistant", "stopReason": "stop",
                "content": [{"type": "text", "text": "answer"}]}}
    check("pi_admits_only_a_stopped_final_message",
          extract_builtin_output("pi", json.dumps(finished), "answer") == "answer"
          and extract_builtin_output("pi", json.dumps(
              {**finished, "message": {**finished["message"], "stopReason": "error"}}), "answer") == "")
    check("another_style_or_a_missing_answer_admits_nothing",
          extract_builtin_output("goose", "answer", "answer") == ""
          and extract_builtin_output("aider", "answer", None) == "")
    return {"record_type": "harness_builtin_recipe_checks/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
