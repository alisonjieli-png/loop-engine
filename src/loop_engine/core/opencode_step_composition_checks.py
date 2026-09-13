"""Offline contract and adversarial checks for composed OpenCode steps.

The checks build instances under a temporary directory and make no provider
or model call. Housed separately so the composition module stays under the
size cap, following the convention used by the other ``*_checks`` modules.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .opencode_step_composition import (
    OpenCodeCompositionError, SkillCandidate, StepLayer, admit_requests,
    source_only_edit_permission,
    compose_instance, default_catalogue, default_core, default_skill_library,
    dynamic_step_layer, inventory_step_layer, observation_step_layer,
    provisioned_step_layer, requirements_step_layer)


def run_checks() -> dict:
    """Prove layering, refusal, digest pinning and rendering on a temp tree."""

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    catalogue = default_catalogue()
    check("catalogue_registers_the_practitioner_steps",
          catalogue.registered() == ("implement", "orient", "plan", "verify"),
          str(catalogue.registered()))

    try:
        catalogue.select("orientt")
        check("unknown_step_refusal_names_the_registered_steps", False)
    except OpenCodeCompositionError as exc:
        check("unknown_step_refusal_names_the_registered_steps",
              "orient" in str(exc) and "verify" in str(exc), str(exc)[:110])

    core = default_core()
    check("core_digest_is_stable_and_verifiable",
          core.verify_core_unchanged() and len(core.digest) == 64,
          core.digest[:16])

    orient = catalogue.select("orient")
    rendered = orient.agent_markdown()
    check("agent_file_carries_tools_and_permissions",
          "edit: false" in rendered and "permission:" in rendered
          and "bash: deny" in rendered and rendered.startswith("---"),
          rendered.split("\n", 6)[-1][:70])

    with tempfile.TemporaryDirectory() as tmp:
        instance = compose_instance(core, orient, Path(tmp) / "ws")
        agent_path = instance.config_root / f"agent/{instance.agent_name}.md"
        skill_path = instance.config_root / "skill/response-contract/SKILL.md"
        check("instance_materializes_core_and_step_files",
              agent_path.is_file() and skill_path.is_file(),
              str(agent_path.relative_to(tmp)))
        check("manifest_records_core_digest_and_provenance",
              instance.manifest["core_digest"] == core.digest
              and instance.manifest["provenance"][
                  "skill/response-contract/SKILL.md"] == "core"
              and instance.manifest["provenance"][
                  f"agent/{instance.agent_name}.md"] == "step",
              instance.manifest["composed_digest"][:16])

        # Two different steps must produce different instances from the
        # same core -- that is the whole claim of per-step composition.
        verify_instance = compose_instance(
            core, catalogue.select("verify"), Path(tmp) / "ws2")
        check("different_steps_compose_different_instances",
              verify_instance.manifest["composed_digest"]
              != instance.manifest["composed_digest"]
              and verify_instance.manifest["core_digest"]
              == instance.manifest["core_digest"])
        check("verify_step_can_run_commands_but_not_edit",
              verify_instance.manifest["permission"]["bash"] == "allow"
              and verify_instance.manifest["permission"]["edit"] == "deny")

        # A step that collides with a core path is refused, not merged.
        colliding = StepLayer(
            step_id="collide", description="d", system_prompt="p",
            skills={"response-contract": "hijacked"})
        try:
            compose_instance(core, colliding, Path(tmp) / "ws3")
            check("step_cannot_overwrite_a_core_file", False, "overwrote")
        except OpenCodeCompositionError as exc:
            check("step_cannot_overwrite_a_core_file",
                  "not overridable" in str(exc), str(exc)[:100])

    # --- dynamic selection at instantiation ---
    library = default_skill_library()
    check("library_registers_the_default_candidates",
          library.available() == ("dataset-discipline",
                                  "reproduce-before-fix",
                                  "schedule-arithmetic"),
          str(library.available()))

    bug_layer, bug_prov = dynamic_step_layer(
        catalogue.select("plan"),
        "Fix the failing test in utils.py -- it raises a traceback", library)
    check("a_bug_task_admits_the_reproduce_skill",
          sorted(bug_layer.skills) == ["reproduce-before-fix"],
          str(sorted(bug_layer.skills)))
    check("selection_records_which_term_matched",
          "traceback" in bug_prov["reproduce-before-fix"]
          or "fail" in bug_prov["reproduce-before-fix"],
          bug_prov["reproduce-before-fix"])

    gantt_layer, _ = dynamic_step_layer(
        catalogue.select("plan"),
        "Build a gantt chart from the task dependency list", library)
    check("a_scheduling_task_admits_a_different_skill",
          sorted(gantt_layer.skills) == ["schedule-arithmetic"],
          str(sorted(gantt_layer.skills)))

    plain_layer, _ = dynamic_step_layer(
        catalogue.select("plan"), "Rename a variable", library)
    check("a_task_with_no_signal_carries_no_optional_skill",
          plain_layer.skills == {}, str(plain_layer.skills))

    # A skill eligible only for some steps must not leak into others.
    verify_layer, _ = dynamic_step_layer(
        catalogue.select("verify"),
        "Fix the failing test -- it raises a traceback", library)
    check("step_eligibility_is_honoured",
          "reproduce-before-fix" not in verify_layer.skills,
          str(sorted(verify_layer.skills)))

    # Selection must be stable: same task, same set, every time.
    once, _ = dynamic_step_layer(catalogue.select("plan"),
                                 "csv drift dataset accuracy", library)
    twice, _ = dynamic_step_layer(catalogue.select("plan"),
                                  "csv drift dataset accuracy", library)
    check("selection_is_deterministic",
          sorted(once.skills) == sorted(twice.skills)
          and sorted(once.skills) == ["dataset-discipline"],
          str(sorted(once.skills)))

    # --- inventory and requirements: what do I have, what do I need ---
    inv = inventory_step_layer(library, catalogue)
    check("inventory_step_is_read_only",
          inv.tools["edit"] is False and inv.tools["write"] is False
          and inv.tools["bash"] is False,
          "an inventory step that could act would stop inventorying")
    check("inventory_states_the_admissible_skills_and_steps",
          "reproduce-before-fix" in inv.system_prompt
          and "implement" in inv.system_prompt)

    req = requirements_step_layer(library)
    check("requirements_states_the_closed_vocabulary",
          all(name in req.system_prompt for name in library.available()),
          "a closed vocabulary that does not state itself makes the next "
          "attempt guess again")

    outcome = admit_requests(
        {"reproduce-before-fix": "to confirm the bug before editing",
         "time-travel": "to undo the mistake",
         "dataset-discipline": ""}, library)
    check("engine_grants_only_registered_skills",
          sorted(outcome.granted) == ["reproduce-before-fix"],
          str(sorted(outcome.granted)))
    check("an_unregistered_request_is_refused",
          outcome.refused == ("time-travel",), str(outcome.refused))
    check("a_request_without_a_stated_use_is_dropped",
          outcome.dropped_without_use == ("dataset-discipline",),
          "asking for everything costs budget and says nothing about the task")
    check("the_refusal_names_what_would_have_been_accepted",
          all(name in outcome.refusal_message()
              for name in library.available()),
          outcome.refusal_message()[:110])

    # A bare list carries no stated use, so nothing is granted from one.
    bare = admit_requests(["reproduce-before-fix"], library)
    check("a_bare_name_list_grants_nothing",
          bare.granted == {} and bare.dropped_without_use
          == ("reproduce-before-fix",))

    provisioned = provisioned_step_layer(catalogue.select("implement"), outcome)
    check("granted_skills_reach_the_next_step",
          "reproduce-before-fix" in provisioned.skills
          and provisioned.step_id == "implement",
          str(sorted(provisioned.skills)))
    fixed = StepLayer(step_id="implement", description="d",
                      system_prompt="p",
                      skills={"reproduce-before-fix": "THE STEP OWN BODY"})
    kept = provisioned_step_layer(fixed, outcome)
    check("a_granted_skill_cannot_displace_a_steps_own",
          kept.skills["reproduce-before-fix"] == "THE STEP OWN BODY")

    # --- path-scoped permissions: source yes, tests no ---
    rule = source_only_edit_permission()
    check("source_only_rule_denies_every_test_layout_and_allows_the_rest",
          rule.get("*") == "allow"
          and all(rule.get(g) == "deny" for g in
                  ("**/test_*", "**/tests/**", "**/*.spec.*", "**/conftest.py")),
          f"{sum(v == 'deny' for v in rule.values())} deny patterns")
    scoped = StepLayer(step_id="s", description="d", system_prompt="p",
                       permission={"edit": rule, "bash": "allow"})
    rendered = scoped.agent_markdown()
    check("pattern_permissions_render_as_nested_yaml",
          '  edit:\n' in rendered and '    "**/tests/**": deny' in rendered
          and '    "*": allow' in rendered,
          rendered.split("permission:")[1][:80].replace("\n", " | "))
    imp = catalogue.select("implement")
    check("implement_ships_source_only_edits_by_default",
          isinstance(imp.permission.get("edit"), dict)
          and imp.permission["edit"].get("**/tests/**") == "deny",
          "found live: a step with unrestricted edit mocked urlopen so an "
          "integration test tested nothing, and the gate went green")
    for bad, why, frag in (
            ({"edit": {}}, "an_empty_pattern_object", "at least one pattern"),
            ({"edit": {"*": "sometimes"}}, "an_unknown_verb_inside_a_pattern",
             "must be one of"),
            ({"edit": {"tests/**": "ask"}}, "ask_inside_a_pattern_when_unattended",
             "hangs the run")):
        try:
            StepLayer(step_id="s", description="d", system_prompt="p",
                      permission=bad)
            check(f"refuses_{why}", False, "accepted")
        except OpenCodeCompositionError as exc:
            check(f"refuses_{why}", frag in str(exc), str(exc)[:90])

    # --- forced observation after a failure ---
    obs = observation_step_layer(
        "verify", "AssertionError: expected 3, got 4\n  at test_clamp line 12")
    check("observation_step_cannot_edit_or_write",
          obs.tools["edit"] is False and obs.tools["write"] is False
          and obs.permission["edit"] == "deny",
          str(obs.tools))
    check("observation_step_can_still_run_the_failing_thing",
          obs.tools["bash"] is True and obs.permission["bash"] == "allow")
    check("observation_step_always_carries_the_observation_skill",
          list(obs.skills) == ["observe-the-failure"])
    check("observation_step_quotes_the_real_failure_text",
          "expected 3, got 4" in obs.system_prompt,
          obs.system_prompt[-90:])
    try:
        observation_step_layer("", "x")
        check("observation_step_must_name_the_failed_step", False)
    except OpenCodeCompositionError as exc:
        check("observation_step_must_name_the_failed_step",
              "name the step that failed" in str(exc), str(exc)[:80])

    obs_inst_ok = True
    try:
        import tempfile as _tf
        with _tf.TemporaryDirectory() as _t:
            inst = compose_instance(core, obs, Path(_t) / "obs")
            obs_inst_ok = (inst.manifest["permission"]["edit"] == "deny"
                           and "observe-the-failure" in inst.manifest["skills"])
    except OpenCodeCompositionError:
        obs_inst_ok = False
    check("observation_step_composes_into_a_real_instance", obs_inst_ok)

    # The false positive found on a real run: "error" inside "ValueError"
    # pulled a debugging skill into a from-scratch creation task.
    creation = ("Create stats.py with median(xs) and percentile(xs, p). "
                "median must raise ValueError on empty input.")
    created_layer, _ = dynamic_step_layer(
        catalogue.select("plan"), creation, library)
    check("triggers_match_words_not_substrings",
          "reproduce-before-fix" not in created_layer.skills,
          f"ValueError must not trigger 'error': {sorted(created_layer.skills)}")
    still_matches, _ = dynamic_step_layer(
        catalogue.select("plan"),
        "the build fails with an error on startup", library)
    check("a_real_error_word_still_triggers",
          "reproduce-before-fix" in still_matches.skills,
          str(sorted(still_matches.skills)))

    try:
        SkillCandidate(name="no-triggers", body="x", triggers=())
        check("a_skill_without_triggers_is_refused", False)
    except OpenCodeCompositionError as exc:
        check("a_skill_without_triggers_is_refused",
              "always load or never load" in str(exc), str(exc)[:90])

    try:
        SkillCandidate(name="a/b", body="x", triggers=("t",))
        check("a_skill_name_with_a_slash_is_refused", False)
    except OpenCodeCompositionError as exc:
        check("a_skill_name_with_a_slash_is_refused",
              "one path segment" in str(exc), str(exc)[:90])

    try:
        StepLayer(step_id="s", description="d", system_prompt="p",
                  tools={"telepathy": True})
        check("unknown_tool_is_refused_at_composition", False)
    except OpenCodeCompositionError as exc:
        check("unknown_tool_is_refused_at_composition",
              "unknown tool" in str(exc), str(exc)[:90])

    try:
        StepLayer(step_id="s", description="d", system_prompt="p",
                  permission={"bash": "ask"}, unattended=True)
        check("ask_permission_refused_for_unattended_steps", False)
    except OpenCodeCompositionError as exc:
        check("ask_permission_refused_for_unattended_steps",
              "hangs the run" in str(exc), str(exc)[:90])

    try:
        StepLayer(step_id="s", description="d", system_prompt="  ")
        check("empty_system_prompt_is_refused", False)
    except OpenCodeCompositionError as exc:
        check("empty_system_prompt_is_refused",
              "silently inherits" in str(exc), str(exc)[:90])

    return {"module": "core.opencode_step_composition", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
