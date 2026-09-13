"""Invalid-plan feedback controls and an explicit Docker verifier probe.

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
                bundle = verification._load(services, result["probe_ref"])
                feedback = verification._load(services, attempts[1]["generation"]["prompt_ref"])
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
