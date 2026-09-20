"""Offline preparation and candidate-binding checks for remaining CLI recipes.

These pure tests do not execute upstream code or make provider calls. Their
installed-process controls and live task results remain separate evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .harness_remaining_recipes import (
    CRUSH_DISABLED_TOOLS, RemainingRecipeError, extract_remaining_output, prepare_remaining_recipe,
)


def self_test():
    results = {}
    with TemporaryDirectory(prefix="remaining-recipe-checks-") as temporary:
        root = Path(temporary)
        task = root / "task.txt"
        task.write_text('private-task-content\n{"contract":true}')
        source = root / "hermes-source"
        (source / "hermes_cli").mkdir(parents=True)
        (source / "hermes_cli/main.py").write_text("# no executable fixture\n")
        def config(label, **changes):
            value = {"command_prefix": ("/usr/bin/python3", str(source)), "model": "exact-model",
                     "workspace_path": str(root / label), "task_path": str(task),
                     "output_capacity": 4096, "output_allowance": 128, "context_capacity": 131072}
            value.update(changes)
            return value
        def refused(label, style="hermes_agent", url="http://127.0.0.1:8765/v1", **changes):
            try:
                prepare_remaining_recipe(style, config(label, **changes), url)
            except (RemainingRecipeError, ValueError):
                return True
            return False
        argv, env, stdin = prepare_remaining_recipe("hermes_agent", config("hermes"), "http://127.0.0.1:8765/v1")
        settings = json.loads((Path(env["HERMES_HOME"]) / "config.yaml").read_text())
        results["hermes_private_stdin"] = stdin == task.read_bytes() and "private-task-content" not in str(argv)
        results["hermes_original_entrypoint"] = "from hermes_cli.main import main" in Path(argv[1]).read_text()
        results["hermes_tools_closed"] = settings["platform_toolsets"]["cli"] == []
        results["hermes_title_disabled"] = settings["auxiliary"]["title_generation"]["enabled"] is False
        results["hermes_context_is_supplied"] = settings["model"]["context_length"] == 131072
        results["hermes_memory_disabled"] = not any(settings["memory"].values())
        for name, changes in (
            ("context_unknown", {"context_capacity": None}), ("context_small", {"context_capacity": 32000}),
            ("allowance_too_large", {"output_allowance": 4097}), ("boolean_allowance", {"output_allowance": True}),
            ("version_drift", {"package_version": "unqualified"}), ("model_control", {"model": "model\nchanged"}),
            ("source_missing", {"command_prefix": ("/usr/bin/python3", str(root / "absent"))}),
            ("relative_workspace", {"workspace_path": "relative"}), ("small_prompt_bound", {"maximum_request_bytes": 1}),
        ):
            results[name] = refused(name, **changes)
        results["external_endpoint_refused"] = refused("external", url="https://provider.example/v1")
        results["credentials_in_endpoint_refused"] = refused("credentials", url="http://key@127.0.0.1:1234/v1")
        results["unknown_style_refused"] = refused("unknown", style="unqualified")
        results["private_config_overwrite_refused"] = refused("hermes")
        _, _, _ = prepare_remaining_recipe("crush", config("crush", command_prefix=("/usr/bin/crush",)), "http://127.0.0.1:8765/v1")
        crush = json.loads((root / "crush/crush.json").read_text())
        results["crush_exact_disabled_registry"] = tuple(crush["options"]["disabled_tools"]) == CRUSH_DISABLED_TOOLS
        results["crush_both_models_brokered"] = all(v["provider"] == "loop_engine" and v["max_tokens"] == 128
                                                   for v in crush["models"].values())
        prepare_remaining_recipe("forgecode", config("forge", command_prefix=("/usr/bin/forge",)), "http://127.0.0.1:8765/v1")
        forge = (root / "forge/home/.forge/.forge.toml").read_text()
        results["forge_global_allowance_override"] = "max_tokens = 128" in forge and "[session]" in forge
        results["forge_global_tools_disabled"] = "tool_supported = false" in forge
        seeded = json.loads((root / "forge/forge-private-conversation.json").read_text())
        results["forge_empty_titled_fresh_session"] = bool(seeded["title"] and seeded["context"] is None and seeded["metrics"] == {})
    result = "candidate answer"
    identifier = "12345678-1234-1234-1234-123456789abc"
    framed = f"warning\n● [01:02:03] Initialize {identifier}\n{result}\n● [01:02:03] Finished {identifier}\n"
    for style in ("crush", "hermes_agent"):
        results[style + "_exact_observed"] = extract_remaining_output(style, result + "\n", ("title", result)) == result
        results[style + "_unobserved_refused"] = not extract_remaining_output(style, result, ("other",))
        results[style + "_ambiguous_whitespace_refused"] = not extract_remaining_output(style, result, (result, " " + result))
    results["forge_answer_before_auxiliary_reply"] = extract_remaining_output("forgecode", framed, (result, "title")) == result
    results["forge_seeded_continue_frame"] = extract_remaining_output("forgecode", framed.replace("Initialize", "Continue"), result) == result
    results["forge_no_finish_refused"] = not extract_remaining_output("forgecode", framed.split("Finished")[0], (result,))
    results["forge_multiple_frames_refused"] = not extract_remaining_output("forgecode", framed + framed, (result,))
    results["forge_extra_candidate_text_refused"] = not extract_remaining_output("forgecode", framed.replace(result, result + "extra"), (result,))
    tests = [{"test": name, "passed": passed} for name, passed in results.items()]
    passed = sum(item["passed"] is True for item in tests)
    return {"record_type": "harness_remaining_recipe_checks/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
