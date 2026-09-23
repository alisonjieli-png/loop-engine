"""Named checks for the fresh instance recipes and the loading assessment.

Owns: the known-wrong cases of roadmap S-6.42 as pure checks: a recipe that
sets only the harness's configuration variable and keeps the user's home
folder, a candidate that claims support, a claim without evidence, loading
inferred from an exit or a listing, a decoy that reaches the request, a
changed installed version, and a step model endpoint that is not a loopback
origin. Does not own: launching a harness; the offline
launch with its network sandbox lives in
``tools/check_harness_fresh_instances.py`` and its own tests.
These checks start no process, open no socket and call no provider.
"""
from __future__ import annotations

from dataclasses import replace
import json
from unittest.mock import patch

from .harness_fresh_instances import (
    FreshInstanceLayout, FreshInstanceObservation, FreshInstanceRecipe, FreshInstanceRecipeError,
    MATERIAL_KINDS, assess_observation, configuration_files, decoy_files, render_launch,
    step_material_files)


def _release():
    from .harness_recipes import release_recipe_catalog
    return {item.recipe_id: item for item in release_recipe_catalog().fresh_instance_recipes}


def _layout(root="/step-root"):
    return FreshInstanceLayout(
        empty_home=f"{root}/empty-home", configuration_folder=f"{root}/configuration",
        step_folder=f"{root}/parent/step", step_parent=f"{root}/parent",
        model_origin="http://127.0.0.1:18080", model_name="probe", model_credential="not-a-real-key",
        probe_prompt="Reply with the word ready.", protocol_server_name="baltor_step",
        protocol_server_command=("/usr/bin/python3", f"{root}/protocol_server.py", "STEP-MCP"),
        model_context_capacity=32768, model_output_capacity=1024)


def _variant(recipe, **changes):
    return FreshInstanceRecipe.from_dict({**recipe.to_dict(), **changes})


def _refuses(operation) -> bool:
    """True only for the typed refusal; any other exception is not a refusal."""
    try:
        operation()
    except FreshInstanceRecipeError:
        return True
    except Exception:  # a KeyError or TypeError means the reader did not refuse cleanly
        return False
    return False


def _observation(recipe, requests, *, events=(), version=None, exit_code=0):
    markers = (("instruction_file", "STEP-AGENTS"), ("skills", "STEP-SKILL"),
               ("protocol_servers", "STEP-MCP"))
    return FreshInstanceObservation(
        recipe.recipe_id, recipe.pinned_version if version is None else version, tuple(requests),
        tuple(events), exit_code, False, markers, ("DECOY-GLOBAL", "DECOY-PARENT"))


def _reader_checks(check, recipes):
    codex = recipes["codex.fresh_instance"]
    value = codex.to_dict()
    cases = {
        "an_extra_key": lambda: FreshInstanceRecipe.from_dict({**value, "shell": "yes"}),
        "a_newer_version": lambda: FreshInstanceRecipe.from_dict(
            {**value, "record_type": "harness_fresh_instance_recipe/v2"}),
        "a_missing_key": lambda: FreshInstanceRecipe.from_dict(
            {key: item for key, item in value.items() if key != "evidence"}),
        "an_unknown_template_field": lambda: _variant(codex, arguments=["exec", "{user_home}"]),
        "an_unknown_writer": lambda: _variant(codex, configuration_writer="shell_script"),
        "a_global_location_without_a_decoy_kind": lambda: _variant(
            codex, global_locations=[".codex/auth.json"]),
        "an_upstream_outside_a_public_repository": lambda: _variant(
            codex, source={**value["source"], "upstream": "file:///opt/codex"}),
    }
    refused = {name: _refuses(case) for name, case in cases.items()}
    same = FreshInstanceRecipe.from_dict(json.loads(json.dumps(value))).digest == codex.digest
    check("every_fresh_instance_record_refuses_unknown_keys_and_unsupported_versions",
          all(refused.values()) and same, str([name for name, flag in refused.items() if not flag]))


def _home_checks(check, recipes):
    codex = recipes["codex.fresh_instance"]
    environment = dict(codex.environment)
    only_configuration = {name: item for name, item in environment.items() if name != "HOME"}
    no_configuration = {name: item for name, item in environment.items() if name != "CODEX_HOME"}
    wrong = {
        "codex_with_only_its_configuration_variable": lambda: _variant(codex, environment=only_configuration),
        "codex_with_the_users_home": lambda: _variant(codex, environment={**environment, "HOME": "/home/user"}),
        "codex_without_its_configuration_folder": lambda: _variant(codex, environment=no_configuration),
    }
    refused = {name: _refuses(case) for name, case in wrong.items()}
    release_ok = all(dict(item.environment).get("HOME") == "{empty_home}" for item in recipes.values())
    check("every_fresh_instance_recipe_starts_with_an_empty_home_and_its_own_configuration_folder",
          all(refused.values()) and release_ok, str(refused))
    import loop_engine.core.harness_fresh_instances as fresh
    with patch.object(fresh, "_empty_home_rule", lambda environment: None):
        accepted = not _refuses(wrong["codex_with_only_its_configuration_variable"])
    check("removed_empty_home_rule_is_detected", accepted,
          "without the rule a recipe that keeps the user's home folder must load")


def _preference_checks(check, recipes):
    claude = sorted((item for item in recipes.values() if item.harness == "claude_code"),
                    key=lambda item: item.order)
    # Bare mode with --add-dir loads CLAUDE.md files from the added folder and
    # every folder above it (observed at 2.1.280), so explicit flags only.
    bare_first = (bool(claude) and "--bare" in claude[0].arguments
                  and "--add-dir" not in claude[0].arguments)
    fallback = [item for item in claude[1:] if "--bare" not in item.arguments
                and dict(item.environment).get("CLAUDE_CONFIG_DIR") == "{configuration_folder}"
                and ("CLAUDE.md", "import_standard_file") in item.instruction_files]
    check("claude_code_prefers_bare_mode_and_keeps_the_configuration_folder_fallback",
          bare_first and len(fallback) == 1, str([item.recipe_id for item in claude]))
    if fallback:
        layout = _layout("/home/customer/steps")
        settings = dict(configuration_files(fallback[0], layout))[
            f"{layout.configuration_folder}/step-settings.json"]
        excluded = set(json.loads(settings)["claudeMdExcludes"])
        wanted = {f"{folder}/.claude/CLAUDE.md" for folder in (
            "/home/customer/steps/parent", "/home/customer/steps", "/home/customer", "/home")}
        check("the_claude_code_fallback_excludes_the_instruction_files_of_every_folder_above_the_step",
              wanted <= excluded and "/.claude/CLAUDE.md" in excluded
              and f"{layout.step_parent}/CLAUDE.md" in excluded
              and not any(path.startswith(layout.step_folder + "/") for path in excluded),
              str(sorted(wanted - excluded)))


def _claim_checks(check, recipes):
    zcode = recipes["zcode.app_server_candidate"]
    claimed = {**dict(zcode.material), "instruction_file": "loaded"}
    candidate_claim = _refuses(lambda: _variant(zcode, support_claim="material_loading",
                                                material=claimed))
    launch_refused = _refuses(lambda: render_launch(zcode, _layout()))
    check("a_candidate_recipe_makes_no_support_claim",
          zcode.candidate and zcode.support_claim == "none" and candidate_claim and launch_refused,
          f"claim_refused={candidate_claim} launch_refused={launch_refused}")
    codex = recipes["codex.fresh_instance"]
    no_evidence = _refuses(lambda: _variant(codex, evidence=[]))
    unproven_claim = _refuses(lambda: _variant(codex, material={
        "instruction_file": "not_proven", "skills": "not_proven", "protocol_servers": "not_proven"}))
    check("a_claim_names_its_pinned_version_and_its_evidence",
          no_evidence and unproven_claim and all(
              item.evidence and item.pinned_version for item in recipes.values()
              if item.support_claim != "none"),
          f"no_evidence={no_evidence} unproven_claim={unproven_claim}")


def _assessment_checks(check, recipes):
    codex = recipes["codex.fresh_instance"]
    loaded = "STEP-AGENTS STEP-SKILL STEP-MCP"
    clean = assess_observation(codex, _observation(codex, [loaded], events=("request tools/list",)))
    exit_only = assess_observation(codex, _observation(codex, [], exit_code=0))
    listed_only = assess_observation(codex, _observation(
        codex, ["STEP-AGENTS STEP-SKILL"], events=("start STEP-MCP", "request tools/list")))
    check("loading_is_counted_only_from_a_marker_inside_a_request",
          clean["passed"] and clean["rung"] == "material_loaded"
          and not exit_only["passed"] and exit_only["rung"] == "none"
          and not listed_only["passed"] and listed_only["rung"] == "material_listed",
          json.dumps([clean["rung"], exit_only["rung"], listed_only["rung"]]))
    leak = _observation(codex, [loaded + " DECOY-GLOBAL"])
    decoy_server = _observation(codex, [loaded], events=("start DECOY-GLOBAL",))
    check("a_decoy_in_the_request_fails_the_loading_check",
          not assess_observation(codex, leak)["passed"]
          and not assess_observation(codex, decoy_server)["passed"])
    import loop_engine.core.harness_fresh_instances as fresh
    with patch.object(fresh, "_decoys_found", lambda markers, text, events: []):
        accepted = assess_observation(codex, leak)["passed"]
    check("removed_decoy_rule_is_detected", accepted,
          "without the decoy rule a leaking launch must pass")
    drifted = assess_observation(codex, _observation(codex, [loaded], version="0.156.0"))
    check("version_drift_is_unqualified_until_proven_again",
          not drifted["passed"] and not drifted["version_matches_pin"])
    pi = recipes["pi.fresh_instance"]
    pi_result = assess_observation(pi, _observation(pi, ["STEP-AGENTS STEP-SKILL"]))
    check("material_a_harness_cannot_load_is_recorded_not_assumed",
          dict(pi.material)["protocol_servers"] == "not_supported" and pi_result["passed"]
          and pi_result["rung"] == "material_loaded"
          and not pi_result["material"]["protocol_servers"]["found_in_request"])


def _credential_checks(check, recipes):
    """The model credential reaches a harness only through its own environment."""
    sentinel = "SENTINEL-CREDENTIAL-7731"
    layout = replace(_layout(), model_credential=sentinel)
    leaks = []
    for item in recipes.values():
        if item.candidate:
            continue
        arguments, environment = render_launch(item, layout)
        written = configuration_files(item, layout) + step_material_files(
            item, layout, instructions="STEP-AGENTS", skill_description="STEP-SKILL")
        if any(sentinel in value for value in arguments):
            leaks.append(f"{item.recipe_id}: the command line carries it")
        if any(sentinel in text for _, text in written):
            leaks.append(f"{item.recipe_id}: a written file holds it")
        if sentinel not in environment.values():
            leaks.append(f"{item.recipe_id}: it does not reach the process environment")
    codex = recipes["codex.fresh_instance"]
    command_refused = _refuses(lambda: _variant(
        codex, arguments=["exec", "--api-key", "{model_credential}", "{probe_prompt}"]))
    check("no_fresh_instance_recipe_writes_the_model_credential_to_a_file_or_a_command_line",
          not leaks and command_refused, str(leaks) + f" command_refused={command_refused}")


def _layout_checks(check, recipes):
    layout = _layout()
    problems = []
    for item in recipes.values():
        if item.candidate:
            continue
        arguments, environment = render_launch(item, layout)
        rendered = list(arguments) + list(environment.values())
        if any("{" in value or "}" in value for value in rendered):
            problems.append(f"{item.recipe_id}: a template field was left unrendered")
        if environment.get("HOME") != layout.empty_home:
            problems.append(f"{item.recipe_id}: HOME is not the empty home folder")
        written = [path for path, _ in configuration_files(item, layout)] + [
            path for path, _ in step_material_files(item, layout, instructions="STEP-AGENTS",
                                                    skill_description="STEP-SKILL")]
        if any(path.startswith(layout.empty_home + "/") for path in written):
            problems.append(f"{item.recipe_id}: a file is written into the empty home folder")
        servers = "\n".join(text for _, text in configuration_files(item, layout))
        if dict(item.material)["protocol_servers"] != "not_supported" and (
                layout.protocol_server_name not in servers
                or layout.protocol_server_command[1] not in servers):
            problems.append(f"{item.recipe_id}: the step's protocol server is not declared")
        decoys = decoy_files(item, "/decoy-home", "DECOY-GLOBAL", layout.protocol_server_command)
        if len(decoys) != len(item.global_locations) or any(
                "DECOY-GLOBAL" not in text and layout.protocol_server_command[1] not in text
                for _, text in decoys):
            problems.append(f"{item.recipe_id}: a global location has no decoy")
    check("every_release_recipe_renders_its_step_material_and_leaves_the_home_folder_empty",
          not problems, str(problems[:4]))
    check("every_material_kind_is_declared_for_every_recipe",
          all(set(dict(item.material)) == set(MATERIAL_KINDS) for item in recipes.values()))


def _endpoint_checks(check, recipes):
    """A step's model endpoint is a loopback origin: the customer's own local
    model or the offline check's recording endpoint, never a remote address."""
    layout = _layout()
    wrong = ("http://203.0.113.7:18080", "https://127.0.0.1:18080", "http://localhost:18080",
             "http://127.0.0.1:18080/v1", "http://127.0.0.1:")
    accepted = [origin for origin in wrong
                if not _refuses(lambda origin=origin: replace(layout, model_origin=origin))]
    check("a_step_model_endpoint_is_a_loopback_origin", not accepted, str(accepted))


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:400]})

    recipes = _release()
    for run in (_reader_checks, _home_checks, _preference_checks, _claim_checks,
                _assessment_checks, _credential_checks, _layout_checks, _endpoint_checks):
        try:
            run(check, recipes)
        except Exception as exc:  # one broken group fails its checks, never the suite
            check(run.__name__.strip("_") + "_ran", False, f"{type(exc).__name__}: {exc}")
    return {"record_type": "harness_fresh_instance_checks/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
