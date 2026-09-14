"""Invalid-plan feedback, response format repair, and a Docker verifier probe.

The folded checks use declared fixtures. The separate opt-in qualification
executes the existing verifier in Docker without a real model call.
"""
from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ..code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution)
from . import independent_verification as verification
from .independent_probe_planning import InvalidProbePlan, validate_probe_plan
from .independent_verification_checks import (
    _CRITERIA, _GOOD_SOURCE, _proposal, _refused, _sandbox_observation, _services, _subject,
)


def _plans():
    criteria = _CRITERIA + (("criterion:1", "The returned value is numeric."),)
    missing = _proposal()
    missing["files"] = [{"path": "checks/probe.py", "purpose": "Observe the frozen combine function."}]
    corrected = deepcopy(missing)
    corrected["cases"].append({**corrected["cases"][0], "case_id": "numeric",
                               "criterion_refs": ["criterion:1"], "purpose": "Observe its numeric result."})
    source = _proposal()["files"][0]
    review = {"valid": True, "criterion_refs": ["criterion:0", "criterion:1"], "issues": [],
              "notes": "Both observations exercise the actual function and compare a numeric sum."}
    return criteria, missing, corrected, source, review


def run_plan_checks(check):
    criteria, missing, corrected, source, review = _plans()
    diagnostic = None
    try:
        validate_probe_plan(missing, criteria)
    except InvalidProbePlan as exc:
        diagnostic = exc.diagnostic.to_dict()
    check("invalid_plan_diagnostic_names_missing_criteria_without_padding",
          diagnostic is not None and diagnostic["missing_criteria"] == ["criterion:1"]
          and diagnostic["unknown_criteria"] == []
          and missing["cases"][0]["criterion_refs"] == ["criterion:0"])
    unknown = deepcopy(missing)
    unknown["cases"][0]["criterion_refs"] = ["criterion:foreign"]
    try:
        validate_probe_plan(unknown, criteria)
        unknown_diagnostic = None
    except InvalidProbePlan as exc:
        unknown_diagnostic = exc.diagnostic
    check("invalid_plan_diagnostic_names_unknown_and_missing_criteria",
          unknown_diagnostic is not None and unknown_diagnostic.unknown_criteria == ("criterion:foreign",)
          and unknown_diagnostic.missing_criteria == ("criterion:0", "criterion:1"))
    textual_timeout = deepcopy(corrected)
    textual_timeout["cases"][0]["timeout_seconds"] = "10"
    try:
        validate_probe_plan(textual_timeout, criteria)
        timeout_diagnostic = None
    except InvalidProbePlan as exc:
        timeout_diagnostic = exc.diagnostic
    check("invalid_case_diagnostic_names_the_case_and_the_field_to_repair",
          timeout_diagnostic is not None and timeout_diagnostic.code == "invalid_case_execution"
          and repr(textual_timeout["cases"][0]["case_id"]) in timeout_diagnostic.detail
          and "timeout_seconds must be a positive JSON number" in timeout_diagnostic.detail
          and '"10"' in timeout_diagnostic.detail and timeout_diagnostic.repairable
          and validate_probe_plan(corrected, criteria) is not None)
    check("plan_attempt_policy_is_explicit_positive_and_versioned",
          verification.IndependentVerificationPolicy().maximum_plan_attempts == 2
          and verification.IndependentVerificationPolicy(maximum_plan_attempts=5).to_dict()["record_type"]
          == "independent_verification_policy/v2"
          and all(_refused(lambda value=value: verification.IndependentVerificationPolicy(maximum_plan_attempts=value))
                  for value in (None, 0, -1, True, 1.5, "2")))

    for mode in ("repaired", "repeated_invalid", "budget_exhausted", "one_attempt",
                 "explicit_unavailable", "review_rejected", "observation_failed"):
        with tempfile.TemporaryDirectory(prefix="independent-plan-feedback-") as directory:
            responses = (missing, corrected, source, review)
            if mode == "repeated_invalid": responses = (missing, missing)
            elif mode in ("budget_exhausted", "one_attempt"): responses = (missing,)
            elif mode == "explicit_unavailable": responses = ({"status": "unavailable", "notes": "No executable plan."}, corrected)
            elif mode == "review_rejected": responses = (missing, corrected, source, {**review, "valid": False, "issues": ["oracle rejected"]})
            services, owner = _services(Path(directory), responses)
            services.request.independent_verification_policy = verification.IndependentVerificationPolicy(
                maximum_plan_attempts=1 if mode == "one_attempt" else 2)
            request = replace(_subject(services, source=_GOOD_SOURCE), criteria=criteria)
            executions = []

            def execute(active_request, _context):
                executions.append(active_request)
                observed = _sandbox_observation(active_request, "2\n" if mode == "observation_failed" else "12\n")
                observed["commands"] = [dict(observed["commands"][0]) for _ in active_request.manifest.commands]
                return observed

            with patch.object(verification, "execute_generated_project", execute):
                result = verification.run_independent_verification(request, services, owner)
            attempts = result["plan_attempts"]
            original = verification._load(services, attempts[0]["proposal_ref"])
            check("plan_feedback_" + mode + "_retains_original_model_proposal",
                  original == responses[0] and all(verification._load(services, item["attempt_ref"])["proposal_ref"]
                      == item["proposal_ref"] for item in attempts))
            if mode == "repaired":
                from ..strings.prompt_fragments import INDEPENDENT_PROBE_REVIEW_PROMPT
                bundle = verification._load(services, result["probe_ref"])
                feedback = verification._load(services, attempts[1]["generation"]["prompt_ref"])
                review_packet = verification._load(services, bundle["review_call"]["prompt_ref"])
                check("oracle_review_contract_shows_every_registered_criterion_once",
                      review_packet["response_contract"]["criterion_refs"]
                      == [ref for ref, _text in criteria])
                check("oracle_review_uses_the_governed_prompt_and_keeps_every_refusal_class",
                      review_packet["responsibility"] == INDEPENDENT_PROBE_REVIEW_PROMPT
                      and all(phrase in INDEPENDENT_PROBE_REVIEW_PROMPT for phrase in (
                          "Refuse tautological/hardcoded observations",
                          "does not execute/read the subject", "invented requirements",
                          "missed criteria", "wrong expectations",
                          "looser than the task justifies", "Return exact covered criterion refs")))
                check("invalid_plan_is_revised_before_code_generation_and_independent_review",
                      result["status"] == "passed" and services.model_session.calls_used == 4
                      and len(executions) == 1 and [item["valid"] for item in attempts] == [False, True]
                      and len(bundle["file_calls"]) == 1 and bundle["review"]["valid"]
                      and feedback["record_type"] == "independent_probe_design_repair/v1"
                      and feedback["repair_feedback"]["diagnostic"]["missing_criteria"] == ["criterion:1"]
                      and feedback["repair_feedback"]["previous_proposal"] == missing)
            elif mode == "observation_failed":
                check("plan_repair_does_not_convert_failing_execution_into_acceptance",
                      result["status"] == "failed" and services.model_session.calls_used == 4
                      and len(executions) == 1 and all(item["passed"] is False for item in result["checks"]))
            else:
                expected_calls = (2 if mode == "repeated_invalid" else 4 if mode == "review_rejected" else 1)
                check("plan_feedback_" + mode + "_refuses_without_executing_a_probe",
                      result["status"] == "unavailable" and not executions
                      and services.model_session.calls_used == expected_calls
                      and not services.independent_probe_cache)


def run_format_repair_checks(check):
    """An inadmissible verifier response is repaired, never beyond authority."""
    packet = {"record_type": "offline_independent_format_repair/v1",
              "responsibility": "Return the fixture value.",
              "response_contract": {"value": "integer"}}
    prose = "The value is twelve."
    for name, answers, calls in (
            ("repaired", (prose, '{"value":12}'), 3),
            ("repeated", (prose, prose, '{"value":12}'), 3),
            ("spent_authority", (prose, '{"value":12}'), 1)):
        with tempfile.TemporaryDirectory(prefix="loop-independent-format-") as folder:
            services, owner = _services(Path(folder))
            services.model_session = fixture_model_execution(FixtureModelExecutionRequest(
                answers=answers, max_model_calls=calls)).start_session()
            value, references, error = None, None, None
            try:
                value, references = verification._call(
                    services, owner, "fixture", packet)
            except ValueError as exc:
                error = exc
            repairs = [event for event in owner.ledger.events
                       if event.get("custom_kind")
                       == "independent_verification_format_repair"]
            if name == "repaired":
                prompt = (verification._load(services, references["prompt_ref"])
                          if references else {})
                check("inadmissible_verifier_response_is_repaired_within_authority",
                      error is None and value == {"value": 12}
                      and services.model_session.calls_used == 2
                      and len(repairs) == 1
                      and prompt.get("format_repair", {}).get(
                          "format_repair_required") is True,
                      str(error))
            elif name == "repeated":
                check("repeated_inadmissible_verifier_response_ends_format_repair",
                      error is not None and value is None
                      and services.model_session.calls_used == 2
                      and len(repairs) == 1, str(error))
            else:
                check("verifier_format_repair_never_exceeds_declared_calls",
                      error is not None and value is None
                      and services.model_session.calls_used == 1
                      and repairs == [], str(error))


def run_file_identity_checks(check):
    """A planned file keeps its declared path; a conflicting path is asked again."""
    from .generated_project import GeneratedProjectFileSpec
    spec = GeneratedProjectFileSpec("checks/probe.py", "Observe the frozen combine function.")
    body = _proposal()["files"][0]["content"]
    packet = {"record_type": "offline_independent_file_identity/v1",
              "responsibility": "Return the planned probe file.",
              "response_contract": {"path": spec.path, "content": "complete Python source"}}
    exact = {"path": spec.path, "content": body}
    moved = {"path": "checks/replacement.py", "content": body}
    for name, answers in (
            ("omitted", ({"content": body},)),
            ("conflict_repaired", (moved, exact)),
            ("conflict_repeated", (moved, moved)),
            ("extra_field_repaired", ({**exact, "notes": "extra"}, exact))):
        with tempfile.TemporaryDirectory(prefix="loop-independent-file-identity-") as folder:
            services, owner = _services(Path(folder), answers)
            value, references, error = None, None, None
            try:
                value, references = verification._call(
                    services, owner, "file.fixture", packet, file_spec=spec)
            except ValueError as exc:
                error = exc
            repairs = [event.get("failure_code") for event in owner.ledger.events
                       if event.get("custom_kind") == "independent_verification_format_repair"]
            bound = [event for event in owner.ledger.events
                     if event.get("custom_kind") == "independent_file_representation"]
            calls = services.model_session.calls_used
            if name == "omitted":
                check("file_response_without_a_path_receives_the_declared_path",
                      error is None and value == exact and repairs == [] and calls == 1
                      and len(bound) == 1 and bound[0].get("strategy") == "predeclared_path_binding"
                      and references["representation"]["path"] == spec.path, str(error))
            elif name == "conflict_repaired":
                check("file_response_with_a_different_path_is_asked_again_not_rebound",
                      error is None and value == exact and bound == [] and calls == 2
                      and repairs == ["file_identity_changed"], str(error))
            elif name == "conflict_repeated":
                check("repeated_different_file_path_is_still_refused",
                      error is not None and value is None and bound == [] and calls == 2
                      and repairs == ["file_identity_changed"], str(error))
            else:
                check("file_response_with_extra_fields_is_asked_again",
                      error is None and value == exact and bound == [] and calls == 2
                      and repairs == ["file_response_shape_invalid"], str(error))


def run_recovery_record_checks(check):
    """A declined recovery keeps its decision on record before the refusal."""
    from .recovery import RecoveryOutcome

    packet = {"record_type": "offline_independent_recovery_record/v1",
              "responsibility": "Return the fixture value.",
              "response_contract": {"value": "integer"}}
    for choice, chosen_by, selected in (
            ("abandoned", "llm", ("abandon",)),
            ("unreasoned", "deterministic", ("retry_same_route",))):
        with tempfile.TemporaryDirectory(prefix="loop-independent-recovery-record-") as folder:
            services, owner = _services(Path(folder))
            services.model_session = fixture_model_execution(FixtureModelExecutionRequest(
                answers=("FAIL",), max_model_calls=1,
                validator=lambda raw: raw != "FAIL")).start_session()

            def recovery(request, error_code, attempt, *, provider_responded,
                         chosen_by=chosen_by, selected=selected):
                return RecoveryOutcome(selected=selected, chosen_by=chosen_by,
                                       reason="Offline recovery decision fixture.")

            services._reasoned_recovery = recovery
            error = None
            try:
                verification._call(services, owner, "fixture", packet)
            except Exception as exc:
                error = exc
            declined = [event for event in owner.ledger.events
                        if event.get("custom_kind")
                        == "independent_verification_recovery_declined"]
            check("independent_" + choice + "_recovery_is_recorded_before_the_refusal",
                  error is not None and len(declined) == 1
                  and declined[0].get("phase") == "fixture"
                  and declined[0].get("reasoned") is (chosen_by == "llm")
                  and declined[0].get("selected") == list(selected)
                  and declined[0].get("reason") == "Offline recovery decision fixture.",
                  str(declined)[:300])


def qualify_plan_repair(output_root: str) -> dict:
    """Explicit Docker execution; model replies are local contract fixtures."""
    root = Path(output_root)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink() or any(root.iterdir()):
        raise ValueError("qualification requires an existing empty absolute directory")
    criteria, missing, corrected, source, review = _plans()
    services, owner = _services(root, (missing, corrected, source, review))
    request = replace(_subject(services, source=_GOOD_SOURCE), criteria=criteria)
    result = verification.run_independent_verification(request, services, owner)
    result["qualification_scope"] = "real Docker probe execution with fixture model replies; no live provider"
    (root / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
