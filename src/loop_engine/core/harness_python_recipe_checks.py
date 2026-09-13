"""Pure positive and adversarial checks for the pinned Python CLI recipes.

Owns configuration and text delivery contracts. These fixtures do not import
third-party harnesses, launch processes or establish model quality.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .harness_python_recipes import PythonRecipeError, extract_python_output, prepare_python_recipe


def self_test():
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    def refused(call):
        try:
            call()
        except (PythonRecipeError, ValueError):
            return True
        return False

    with tempfile.TemporaryDirectory(prefix="python-harness-recipes-") as directory:
        root = Path(directory)
        task = root / "task.txt"
        task.write_text("PRIVATE_TASK_FIXTURE")
        config = {"command_prefix": ("/fixture/python-cli",), "model": "fixture-model",
                  "workspace_path": str(root), "task_path": str(task),
                  "output_capacity": 256, "output_allowance": 128}
        for style in ("mistral_vibe", "gptme"):
            config["command_prefix"] = ("/fixture/gptme-util" if style == "gptme" else "/fixture/vibe",)
            argv, env, prompt = prepare_python_recipe(style, config, "http://127.0.0.1:1234/v1")
            check(style + "_private_prompt_is_not_in_process_arguments",
                  prompt == b"PRIVATE_TASK_FIXTURE" and all("PRIVATE_TASK_FIXTURE" not in part for part in argv))
            check(style + "_foreign_endpoint_and_version_refuse",
                  refused(lambda: prepare_python_recipe(style, config, "https://foreign.invalid/v1"))
                  and refused(lambda: prepare_python_recipe(style, {**config, "package_version": "unknown"}, "http://127.0.0.1:1234/v1")))
            check(style + "_invalid_allowance_refuses",
                  refused(lambda: prepare_python_recipe(style, {**config, "output_allowance": 257}, "http://127.0.0.1:1234/v1")))
            if style == "gptme":
                check("gptme_explicit_tools_off_and_output_allowance",
                      argv[1:3] == ("llm", "generate") and env["GPTME_MAX_TOKENS"] == "128"
                      and argv[argv.index("--max-tokens") + 1] == "128")
                check("gptme_shortcut_cannot_silently_select_a_different_model",
                      refused(lambda: prepare_python_recipe(style, {**config,
                          "command_prefix": ("/fixture/gptme",)}, "http://127.0.0.1:1234/v1")))
            else:
                settings = (root / "home/.vibe/config.toml").read_text()
                check("vibe_disables_tools_skills_discovery_and_auxiliary_requests",
                      'disabled_tools = ["*"]' in settings and 'disabled_skills = ["*"]' in settings
                      and "include_project_context = false" in settings and "generate_titles = false" in settings
                      and "enable_telemetry = false" in settings and "--max-tokens" not in argv)
    vibe = {"type": "message", "role": "assistant", "generationStatus": "completed",
            "content": [{"type": "text", "text": "answer"}]}
    gptme = {"content": "answer", "model": "fixture-model", "usage": None}
    check("vibe_complete_output_matches_exact_broker_text", extract_python_output("mistral_vibe", json.dumps([vibe]), "answer") == "answer")
    check("gptme_complete_output_matches_exact_broker_text", extract_python_output("gptme", json.dumps(gptme) + "\n", "answer") == "answer")
    check("vibe_partial_later_message_cannot_reuse_earlier_answer", not extract_python_output("mistral_vibe", json.dumps([vibe, {**vibe, "generationStatus": "in_progress"}]), "answer"))
    check("gptme_final_mismatch_cannot_reuse_earlier_answer", not extract_python_output("gptme", json.dumps(gptme) + "\n" + json.dumps({**gptme, "content": "different"}), "answer"))
    check("native_effect_and_tool_messages_are_not_semantic_success", not extract_python_output("mistral_vibe", json.dumps([{"type": "effect"}, vibe]), "answer")
          and not extract_python_output("gptme", json.dumps({"type": "message", "role": "tool"}) + "\n" + json.dumps(gptme), "answer"))
    check("malformed_or_empty_output_refuses", all(not extract_python_output(style, text, "answer")
          for style in ("mistral_vibe", "gptme") for text in ("", "not-json", "{}", "null")))
    return {"record_type": "python_harness_recipe_checks/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
