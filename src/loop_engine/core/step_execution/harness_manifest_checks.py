"""Offline checks for the step harness manifest and the step edge records.

Each check names its known-wrong case and passes only when that case is
refused before any use; each removed-guard control deletes one guard and
passes only when its check would then fail. Nothing here starts a process,
calls a model or opens a network connection.
"""
from __future__ import annotations

from dataclasses import replace
import json
from unittest.mock import patch

from . import harness_manifest as manifests
from . import records as step_records
from ..configuration_capabilities import digest
from ..engines.records import EngineRecordError
from .harness_manifest import StepHarnessManifest, release_manifest_catalog, render_launch
from .records import (
    ExecutorProfile, StepBudget, StepInput, StepMaterial, StepOutputPort, StepRequirements, StepRunRequest,
    StepRunResult, StepAccounting, StepOutput, unmet_step_requirements)

VALUES = {"empty_home": "/launch/home", "configuration_folder": "/launch/configuration",
          "step_folder": "/launch/step", "model_base_url": "http://127.0.0.1:18080/v1", "model_name": "probe",
          "model_credential": "loopback-relay-no-secret", "step_prompt": "Answer.",
          "step_request_file": "/launch/io/request.json", "step_result_file": "/launch/io/result.json",
          "software_root": "/opt/loop-engine/src"}


def _refused(action, code=None) -> bool:
    try:
        action()
    except EngineRecordError as exc:
        return code is None or exc.code == code
    except Exception:
        return False
    return False


def _manifest(name="fixture.step_harness") -> dict:
    return json.loads(json.dumps(release_manifest_catalog().manifest(name).to_dict()))


def _changed(record: dict, path: tuple, value) -> dict:
    record = json.loads(json.dumps(record))
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return record


def step_request(**changes) -> StepRunRequest:
    base = StepRunRequest(
        "request-1", "owning.loop1", "practitioner.solver@1.0.0", "fixture.definition",
        digest("definition"), "summarize", 1, "request-1", "Summarize the input.", "Use one sentence.",
        (StepInput("text", "text/plain", "Two engines serve one edge."),),
        (StepOutputPort("answer", "text/plain", True),), "fixture.answer/v1", "exact_text/v1", "final_only",
        "non_deterministic", "", {}, (), True, (), (), StepBudget(60.0, 2, None, 0), StepRequirements())
    return replace(base, **changes)


def the_packaged_manifests_are_valid_and_round_trip() -> bool:
    """Known wrong: a packaged manifest that its own reader refuses or reads differently."""
    catalog = release_manifest_catalog()
    return (len(catalog.manifests) == 3 and all(
        StepHarnessManifest.from_dict(item.to_dict()).content_digest == item.content_digest
        for item in catalog.manifests))


def a_manifest_reader_refuses_unknown_keys_and_versions() -> bool:
    """Known wrong: a manifest with an extra key, another version, a missing part, or a
    field in a part that the part does not define, such as a network allowance."""
    record = _manifest()
    return (_refused(lambda: StepHarnessManifest.from_dict({**record, "allow_network": True}),
                     "unknown_record_fields")
            and _refused(lambda: StepHarnessManifest.from_dict({**record, "record_type": "step_harness_manifest/v2"}),
                         "unsupported_record_version")
            and _refused(lambda: StepHarnessManifest.from_dict({k: v for k, v in record.items() if k != "sandbox"}),
                         "missing_record_fields")
            and _refused(lambda: StepHarnessManifest.from_dict(_changed(record, ("sandbox", "allow_network"), True)),
                         "unknown_record_fields"))


def a_manifest_starts_fresh_and_keeps_credentials_off_the_command_line() -> bool:
    """Known wrong (the September 22 finding): HOME left as the user's home; a configuration
    variable pointing elsewhere; the model credential on the command line, where any
    process can read it; a credential-named variable carrying another value."""
    record = _manifest()
    env = ("launch", "environment")
    return (_refused(lambda: StepHarnessManifest.from_dict(_changed(record, env + ("HOME",), "/home/user")),
                     "fresh_instance_rule")
            and _refused(lambda: StepHarnessManifest.from_dict(
                _changed(record, env + ("FIXTURE_HARNESS_CONFIGURATION",), "/etc/fixture")), "fresh_instance_rule")
            and _refused(lambda: StepHarnessManifest.from_dict(_changed(
                record, ("launch", "arguments"), ["--key", "{model_credential}"])), "credential_on_command_line")
            and _refused(lambda: StepHarnessManifest.from_dict(_changed(
                record, env + ("OPENAI_API_KEY",), "sk-literal")), "credential_in_manifest"))


def a_manifest_template_names_only_known_fields() -> bool:
    """Known wrong: a template naming a field outside the closed list, such as a host path."""
    record = _manifest()
    return (_refused(lambda: StepHarnessManifest.from_dict(_changed(
                record, ("launch", "arguments"), ["{host_home}/secrets"])), "invalid_template")
            and render_launch(release_manifest_catalog().manifest("fixture.step_harness"), VALUES)[0][-1]
            == "Answer.")


def a_manifest_never_widens_what_the_step_grants() -> bool:
    """Known wrong: a process harness declaring no isolation; a warm placement nobody
    qualified; a custom Loop harness asking for a network; a model wire with no endpoint;
    an unregistered layout profile; a skill folder that climbs out of the step folder."""
    record = _manifest()
    loop = _manifest("baltor_loop.process")
    return (_refused(lambda: StepHarnessManifest.from_dict(_changed(record, ("sandbox", "isolation"), "none")),
                     "invalid_vocabulary")
            and _refused(lambda: StepHarnessManifest.from_dict(
                _changed(record, ("sandbox", "placement"), "pooled_sessions")), "placement_not_qualified")
            and _refused(lambda: StepHarnessManifest.from_dict(_changed(
                _changed(loop, ("sandbox", "network"), "loopback_model_endpoint"),
                ("sandbox", "model_wire"), "openai_chat_completions")), "inconsistent_manifest")
            and _refused(lambda: StepHarnessManifest.from_dict(_changed(record, ("sandbox", "model_wire"), "none")),
                         "inconsistent_manifest")
            and _refused(lambda: StepHarnessManifest.from_dict(
                _changed(record, ("layout", "layout_profile"), "unknown-client")), "unknown_layout_profile")
            and _refused(lambda: StepHarnessManifest.from_dict(
                _changed(record, ("layout", "skills_directory"), "../skills")), "invalid_path"))


def a_manifest_declares_how_its_output_is_read() -> bool:
    """Known wrong: JSON lines with no event selector; a step result read from standard
    output; a text output with a pointer."""
    record = _manifest()
    completion = ("completion",)
    return (_refused(lambda: StepHarnessManifest.from_dict(_changed(record, completion + ("event_field",), "")),
                     "invalid_field")
            and _refused(lambda: StepHarnessManifest.from_dict(
                _changed(record, completion + ("output_format",), "step_run_result_json")), "invalid_field")
            and _refused(lambda: StepHarnessManifest.from_dict(
                _changed(_changed(_changed(record, completion + ("output_format",), "text"),
                                  completion + ("event_field",), ""), completion + ("event_value",), "")),
                "invalid_field"))


def step_edge_records_refuse_unknown_keys_and_versions() -> bool:
    """Known wrong: a request with an extra key; step_run_result/v2 read by the v1 reader; a
    result claiming its own acceptance; a digest that does not match its text."""
    request = step_request()
    record = request.to_dict()
    result = StepRunResult(request.request_id, request.digest, "completed", "", "",
                           (StepOutput("answer", "text/plain", "ok"),), (), (), "none", StepAccounting(1, 5, 2, None),
                           (), {}, None, (), None, None)
    written = result.to_dict()
    return (_refused(lambda: StepRunRequest.from_dict({**record, "priority": "high"}), "unknown_record_fields")
            and _refused(lambda: StepRunResult.from_dict({**written, "record_type": "step_run_result/v2"}),
                         "unsupported_record_version")
            and _refused(lambda: StepRunResult.from_dict({**written, "task_accepted": True}), "self_acceptance")
            and _refused(lambda: StepRunResult.from_dict(_changed(written, ("outputs", 0, "digest"), digest("x"))),
                         "derived_value_mismatch")
            and StepRunRequest.from_dict(json.loads(json.dumps(record))).digest == request.digest
            and StepRunResult.from_dict(json.loads(json.dumps(written))).to_dict() == written)


def a_step_keeps_its_mode_rules() -> bool:
    """Known wrong: a deterministic step authorizing model calls; a model-led step that does
    not require delegation (the harness-first rule); a procedure on a model-led step; a
    model-led step owned by a profile that allows only deterministic work."""
    return (_refused(lambda: step_request(mode="deterministic"), "mode_rule")
            and _refused(lambda: step_request(owning_profile_ref="practitioner.code_execution@1.0.0"), "mode_rule")
            and _refused(lambda: step_request(requirements=StepRequirements(delegation_required=False)), "mode_rule")
            and _refused(lambda: step_request(procedure_ref="text.render_template@1"), "mode_rule"))


def a_step_needing_tools_or_file_effects_is_refused_by_a_text_only_engine() -> bool:
    """Known wrong: a step granted file writes reaching an engine whose native tools are off;
    a skill reaching an engine that does not support skills; a model-led step reaching an
    engine with no model wire."""
    pi = release_manifest_catalog().manifest("pi.print").executor_profile()
    fixture = release_manifest_catalog().manifest("fixture.step_harness").executor_profile()
    loop = release_manifest_catalog().manifest("baltor_loop.process").executor_profile()
    skill = (StepMaterial("skill", "review-rules", "Review the rules."),)
    return ("tools_or_file_effects:text_only_engine" in unmet_step_requirements(
                step_request(granted_effects=("writes_fs",)), pi)
            and "component:skill" in unmet_step_requirements(step_request(material=skill), pi)
            and "component:skill" not in unmet_step_requirements(step_request(material=skill), fixture)
            and "model_wire:none" in unmet_step_requirements(step_request(), loop)
            and not unmet_step_requirements(step_request(), fixture))


def an_executor_profile_is_its_own_record() -> bool:
    """Known wrong: an in-process engine claiming process isolation; a profile that reads
    back differently."""
    profile = release_manifest_catalog().manifest("pi.print").executor_profile()
    return (ExecutorProfile.from_dict(profile.to_dict()) == profile
            and _refused(lambda: replace(profile, placement="in_process"), "invalid_field"))


CHECKS = (
    ("the_packaged_manifests_are_valid_and_round_trip", the_packaged_manifests_are_valid_and_round_trip, ()),
    ("a_manifest_reader_refuses_unknown_keys_and_versions", a_manifest_reader_refuses_unknown_keys_and_versions, ()),
    ("a_manifest_starts_fresh_and_keeps_credentials_off_the_command_line",
     a_manifest_starts_fresh_and_keeps_credentials_off_the_command_line,
     (("removed_fresh_launch_rule_is_detected", ((manifests, "_require_fresh_launch"),)),)),
    ("a_manifest_template_names_only_known_fields", a_manifest_template_names_only_known_fields, ()),
    ("a_manifest_never_widens_what_the_step_grants", a_manifest_never_widens_what_the_step_grants,
     (("removed_manifest_consistency_rule_is_detected", ((manifests, "_require_consistent_needs"),)),)),
    ("a_manifest_declares_how_its_output_is_read", a_manifest_declares_how_its_output_is_read, ()),
    ("step_edge_records_refuse_unknown_keys_and_versions", step_edge_records_refuse_unknown_keys_and_versions, ()),
    ("a_step_keeps_its_mode_rules", a_step_keeps_its_mode_rules,
     (("removed_step_mode_rule_is_detected", ((step_records, "_require_mode_rules"),)),)),
    ("a_step_needing_tools_or_file_effects_is_refused_by_a_text_only_engine",
     a_step_needing_tools_or_file_effects_is_refused_by_a_text_only_engine, ()),
    ("an_executor_profile_is_its_own_record", an_executor_profile_is_its_own_record, ()),
)


def run_checks() -> dict:
    tests = []
    for name, scenario, controls in CHECKS:
        tests.append({"name": name, "passed": _observe(scenario)})
        for control, removed in controls:
            patches = [patch.object(module, guard, lambda *a, **k: None) for module, guard in removed]
            for item in patches:
                item.start()
            try:
                tests.append({"name": control, "passed": _observe(scenario) is False})
            finally:
                for item in patches:
                    item.stop()
    return {"tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def _observe(scenario) -> bool:
    try:
        return bool(scenario())
    except Exception:
        return False


def self_test() -> dict:
    return run_checks()
