"""Offline lifecycle checks for parent-requested oracle review repair.

Uses existing fixture model and executor helpers. These checks establish no
real model quality, Docker isolation, or actual task acceptance claim.
"""
from __future__ import annotations

from copy import deepcopy
import tempfile
from pathlib import Path
from unittest.mock import patch

from . import independent_verification as verification
from .independent_verification_checks import (
    _GOOD_SOURCE, _proposal, _sandbox_observation, _services, _subject,
)


def _approval():
    return {"valid": True, "criterion_refs": ["criterion:0"], "issues": [],
            "notes": "Fresh independent fixture review: suitable to execute."}


def _rejection():
    return {"valid": False, "criterion_refs": ["criterion:0"],
            "issues": ["The independent expected sum of 7 and 5 must be 12, not 13."],
            "notes": "Rejected expected value; this review grants no acceptance."}


def _bad_proposal():
    proposal = _proposal()
    proposal["cases"][0]["expected"] = 13
    return proposal


def self_test():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})

    with tempfile.TemporaryDirectory(prefix="oracle-review-integration-") as directory:
        services, owner = _services(Path(directory), (_bad_proposal(), _rejection(), _proposal(), _approval()))
        request = _subject(services, source=_GOOD_SOURCE)
        executions = []
        def executor(execution_request, _context):
            executions.append(execution_request)
            return _sandbox_observation(execution_request)
        with patch.object(verification, "execute_generated_project", executor):
            first = verification.run_independent_verification(request, services, owner)
            first_snapshot = deepcopy(first)
            first_attempt = first["oracle_reviews"][0]
            retained = verification._load(services, first_attempt["candidate_ref"])
            check("rejected_review_records_candidate_and_remains_unavailable", first["status"] == "unavailable"
                  and first_attempt["admitted_for_execution"] is False and retained["review"] == _rejection()
                  and retained["proposal"] == _bad_proposal())
            check("rejection_dispatches_no_check_execution_or_automatic_retry", not executions
                  and services.model_session.calls_used == 2 and not services.independent_probe_cache
                  and len(services.independent_verification_records) == 1)
            check("rejected_candidate_retains_generation_and_review_lineage", bool(retained["generation"]["prompt_ref"])
                  and bool(retained["review_call"]["response_ref"]) and retained["file_calls"] == [])
            second = verification.run_independent_verification(request, services, owner)
        second_attempt = second["oracle_reviews"][0]
        candidate = verification._load(services, second_attempt["candidate_ref"])
        design = verification._load(services, candidate["generation"]["prompt_ref"])
        feedback = design.get("prior_rejected_oracle", {})
        check("later_parent_call_receives_exact_rejected_proposal_and_review", feedback.get("previous_proposal") == _bad_proposal()
              and feedback.get("previous_review") == _rejection()
              and feedback.get("candidate_ref") == first_attempt["candidate_ref"])
        check("feedback_is_exact_subject_and_explicitly_untrusted", feedback.get("subject_digest") == first["subject_digest"] == second["subject_digest"]
              and feedback.get("trust") == "untrusted_proposal_and_model_review"
              and feedback.get("grants_task_acceptance") is False and feedback.get("grants_promotion") is False)
        check("new_independent_controller_reviews_fresh_complete_proposal", first["verifier_loop_id"] != second["verifier_loop_id"]
              and candidate["review"] == _approval() and candidate["review_call"] != retained["review_call"]
              and candidate["proposal"] == _proposal())
        check("fresh_review_prompt_does_not_receive_prior_review_as_authority",
              "prior_rejected_oracle" not in verification._load(services, candidate["review_call"]["prompt_ref"]))
        check("fresh_approval_only_enables_external_controller_comparisons", second["status"] == "passed"
              and len(executions) == 1 and second["checks"][0]["passed"] is True
              and second["source_unchanged"] is True and second["grants_promotion"] is False)
        check("parent_retry_retains_original_rejection_unchanged", first == first_snapshot
              and services.independent_verification_records[0] == first_snapshot
              and services.model_session.calls_used == 4)

    with tempfile.TemporaryDirectory(prefix="oracle-review-repeat-rejection-") as directory:
        services, owner = _services(Path(directory), (_bad_proposal(), _rejection(), _proposal(), _rejection()))
        request = _subject(services, source=_GOOD_SOURCE)
        executions = []
        def executor(execution_request, _context):
            executions.append(execution_request)
            return _sandbox_observation(execution_request)
        with patch.object(verification, "execute_generated_project", executor):
            first = verification.run_independent_verification(request, services, owner)
            second = verification.run_independent_verification(request, services, owner)
        check("prior_feedback_never_substitutes_for_fresh_approval", first["status"] == second["status"] == "unavailable"
              and not executions and not services.independent_probe_cache and services.model_session.calls_used == 4)
        check("every_failed_parent_attempt_preserves_its_own_candidate", len(services.independent_verification_records) == 2
              and first["oracle_reviews"][0]["candidate_ref"] != second["oracle_reviews"][0]["candidate_ref"])

    with tempfile.TemporaryDirectory(prefix="oracle-review-changed-subject-") as directory:
        services, owner = _services(Path(directory), (_bad_proposal(), _rejection(), _proposal(), _approval()))
        original = _subject(services, source=_GOOD_SOURCE)
        changed = _subject(services, attempt="attempt-2", source=_GOOD_SOURCE + "\n# Changed subject identity.\n")
        executions = []
        def executor(execution_request, _context):
            executions.append(execution_request)
            return _sandbox_observation(execution_request)
        with patch.object(verification, "execute_generated_project", executor):
            first = verification.run_independent_verification(original, services, owner)
            second = verification.run_independent_verification(changed, services, owner)
        candidate = verification._load(services, second["oracle_reviews"][0]["candidate_ref"])
        design = verification._load(services, candidate["generation"]["prompt_ref"])
        check("changed_subject_gets_no_rejected_candidate_feedback", first["subject_digest"] != second["subject_digest"]
              and "prior_rejected_oracle" not in design)
        check("changed_subject_requires_fresh_design_review_and_execution", second["status"] == "passed"
              and len(executions) == 1 and services.model_session.calls_used == 4)

    with tempfile.TemporaryDirectory(prefix="oracle-review-exhausted-authority-") as directory:
        services, owner = _services(Path(directory), (_bad_proposal(), _rejection()))
        request = _subject(services, source=_GOOD_SOURCE)
        executions = []
        with patch.object(verification, "execute_generated_project", lambda *_args: executions.append(True)):
            first = verification.run_independent_verification(request, services, owner)
            second = verification.run_independent_verification(request, services, owner)
        check("stored_feedback_does_not_grant_additional_model_authority", first["status"] == second["status"] == "unavailable"
              and services.model_session.calls_used == 2 and not executions)

    return {"passed": sum(item["passed"] for item in tests), "total": len(tests), "tests": tests}
