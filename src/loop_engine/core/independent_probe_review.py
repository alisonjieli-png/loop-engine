"""Retain rejected oracle reviews for a later parent-owned verification attempt.

Owns passive candidate records and exact-subject feedback selection. It does
not retry a model call, approve an oracle, execute a check, or promote code.
The existing artifact manager and independent verification records are the
only storage authorities.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .context_artifacts import ContextArtifactRef


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def oracle_review_admissible(review, criteria):
    """A reviewed candidate is eligible to execute, never already accepted."""
    if not isinstance(review, dict):
        return False
    refs = review.get("criterion_refs")
    return (review.get("valid") is True and review.get("issues") == []
        and isinstance(refs, list) and all(isinstance(ref, str) for ref in refs)
        and len(refs) == len(set(refs)) and set(refs) == set(dict(criteria)))


def capture_oracle_review(services, owner, request, subject, proposal, *,
                          generation, file_calls, review, review_call):
    """Save failures with the same proposal and generation lineage as successes."""
    admitted = oracle_review_admissible(review, request.criteria)
    record = {"record_type": "independent_oracle_review_candidate/v1",
        "verifier_loop_id": owner.loop_id, "subject_digest": _digest(subject),
        "task_digest": subject["task_digest"], "criteria_digest": subject["criteria_digest"],
        "proposal": deepcopy(proposal), "generation": deepcopy(generation),
        "file_calls": deepcopy(file_calls), "review": deepcopy(review),
        "review_call": deepcopy(review_call), "admitted_for_execution": admitted,
        "grants_task_acceptance": False, "grants_promotion": False}
    ref = services.artifacts.capture(json.dumps(record, ensure_ascii=False,
        sort_keys=True, allow_nan=False), media_type="application/json",
        artifact_kind="independent_oracle_review_candidate").raw.to_dict()
    summary = {key: record[key] for key in ("verifier_loop_id", "subject_digest",
        "task_digest", "criteria_digest", "admitted_for_execution")}
    summary.update(record_type="independent_oracle_review_attempt/v1", candidate_ref=ref)
    owner.ledger.record(loop_id=owner.loop_id, event="custom",
        custom_kind="independent_oracle_review", **summary)
    return summary


def prior_oracle_feedback(services, subject):
    """Load exact-subject feedback: a confirmed check dispute or a rejected candidate.

    A failure review that confirmed an executed check was wrong comes first,
    because it is the latest evidence about that exact subject. Returning
    feedback grants no retry. The parent must independently choose another
    verification operation with remaining shared model authority. Changed
    source, criteria, workspace or task identities do not match.
    """
    expected = _digest(subject)
    for review in reversed(getattr(services, "independent_failure_reviews", None) or ()):
        if (isinstance(review, dict) and review.get("decision") == "revise_check"
                and review.get("subject_digest") == expected
                and isinstance(review.get("disputed_proposal"), dict)):
            classification = review.get("classification") or {}
            return {"record_type": "independent_oracle_review_feedback/v1",
                "candidate_ref": deepcopy(review.get("review_ref")),
                "subject_digest": expected, "trust": "untrusted_proposal_and_model_review",
                "previous_proposal": deepcopy(review["disputed_proposal"]),
                "previous_review": {"source": "confirmed_failure_review",
                    "classification": classification.get("classification"),
                    "findings": deepcopy(classification.get("findings", [])),
                    "confirmation": deepcopy(review.get("confirmation"))},
                "grants_task_acceptance": False, "grants_promotion": False}
    for report in reversed(services.independent_verification_records):
        if report.get("subject_digest") != expected:
            continue
        for summary in reversed(report.get("oracle_reviews", ())):
            if (not isinstance(summary, dict)
                    or summary.get("record_type") != "independent_oracle_review_attempt/v1"
                    or summary.get("admitted_for_execution") is not False
                    or summary.get("subject_digest") != expected
                    or summary.get("verifier_loop_id") != report.get("verifier_loop_id")):
                continue
            candidate = json.loads(services.artifacts.store.get_text(
                ContextArtifactRef.from_dict(summary["candidate_ref"])))
            if (candidate.get("record_type") != "independent_oracle_review_candidate/v1"
                    or candidate.get("subject_digest") != expected
                    or candidate.get("task_digest") != subject["task_digest"]
                    or candidate.get("criteria_digest") != subject["criteria_digest"]
                    or candidate.get("verifier_loop_id") != summary["verifier_loop_id"]
                    or candidate.get("admitted_for_execution") is not False
                    or candidate.get("grants_task_acceptance") is not False
                    or candidate.get("grants_promotion") is not False):
                raise ValueError("retained oracle review feedback identity changed")
            return {"record_type": "independent_oracle_review_feedback/v1",
                "candidate_ref": deepcopy(summary["candidate_ref"]),
                "subject_digest": expected, "trust": "untrusted_proposal_and_model_review",
                "previous_proposal": candidate["proposal"], "previous_review": candidate["review"],
                "grants_task_acceptance": False, "grants_promotion": False}
    return None
