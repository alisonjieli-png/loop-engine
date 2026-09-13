"""Offline controls for retained rejected-oracle feedback.

Uses the existing artifact manager to check exact-subject identity and refusal
behavior. It makes no model calls and schedules no verifier retries.
"""
from __future__ import annotations

from copy import deepcopy
import tempfile
from types import SimpleNamespace

from .independent_probe_review import (
    _digest, capture_oracle_review, oracle_review_admissible, prior_oracle_feedback)


def self_test():
    from .context_artifacts import (
        ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
    from ..loop.recursive_loop import Loop
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})

    criteria = (("criterion:0", "actual requirement"),)
    accepted = {"valid": True, "criterion_refs": ["criterion:0"], "issues": []}
    check("review_candidate_needs_exact_coverage", oracle_review_admissible(accepted, criteria))
    for name, changed in (("wrong_ref", {**accepted, "criterion_refs": ["foreign"]}),
        ("duplicate_ref", {**accepted, "criterion_refs": ["criterion:0", "criterion:0"]}),
        ("untyped_ref", {**accepted, "criterion_refs": [1]}),
        ("false", {**accepted, "valid": False}), ("issues", {**accepted, "issues": ["wrong expected value"]}),
        ("untyped", [])):
        check("review_refuses_" + name, not oracle_review_admissible(changed, criteria))
    with tempfile.TemporaryDirectory(prefix="oracle-review-check-") as directory:
        artifacts = ContextArtifactManager(ContextArtifactServices(
            ContextArtifactStore(ContextArtifactStoreSpec(directory))))
        services = SimpleNamespace(artifacts=artifacts, independent_verification_records=[])
        owner = Loop("oracle review record fixture")
        subject = {"task_digest": "a"*64, "criteria_digest": "b"*64,
                   "inventory": [{"path": "main.py", "digest": "c"*64}]}
        proposal = {"cases": [{"expected": "wrong"}]}
        rejection = {**accepted, "valid": False, "issues": ["recompute expected value"]}
        summary = capture_oracle_review(services, owner, SimpleNamespace(criteria=criteria),
            subject, proposal, generation={"phase": "design"}, file_calls=[],
            review=rejection, review_call={"phase": "review"})
        check("rejection_is_retained_without_acceptance", summary["admitted_for_execution"] is False
              and bool(summary["candidate_ref"]))
        check("capturing_does_not_schedule_retry", not services.independent_verification_records
              and prior_oracle_feedback(services, subject) is None)
        report = {"subject_digest": _digest(subject), "verifier_loop_id": owner.loop_id,
                  "oracle_reviews": [summary]}
        services.independent_verification_records.append(report)
        feedback = prior_oracle_feedback(services, subject)
        check("later_parent_attempt_receives_exact_rejection", feedback["previous_review"] == rejection
              and feedback["previous_proposal"] == proposal and feedback["grants_promotion"] is False
              and feedback["grants_task_acceptance"] is False)
        for key, value in (("task_digest", "d"*64), ("criteria_digest", "e"*64),
                           ("inventory", [{"path": "main.py", "digest": "f"*64}])):
            check("unrelated_" + key + "_does_not_reuse_feedback",
                  prior_oracle_feedback(services, {**subject, key: value}) is None)
        spoof = deepcopy(report)
        spoof["oracle_reviews"][0]["candidate_ref"] = capture_oracle_review(services, owner,
            SimpleNamespace(criteria=criteria), subject, proposal, generation={}, file_calls=[],
            review=accepted, review_call={})["candidate_ref"]
        services.independent_verification_records[:] = [spoof]
        denied = False
        try:
            prior_oracle_feedback(services, subject)
        except ValueError:
            denied = True
        check("approved_candidate_cannot_be_relabelled_as_rejection", denied)
    return {"tests": tests, "passed": sum(t["passed"] for t in tests), "total": len(tests)}
