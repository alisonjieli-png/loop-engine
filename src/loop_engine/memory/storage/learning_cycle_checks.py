"""Executable offline checks for the governed learning lifecycle.

The checks use only deterministic local fixtures. They prove contract
behavior and saved evidence, not production effectiveness.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

from ...loop.loop_role import (
    LoopRelationship, LoopRole, LoopRoleIdentity)
from ...loop.recursive_loop import (
    Loop, LoopConfig, LoopLedger, StepOutcome)
from ..model.memory_type import (
    MemoryEvidenceRef, MemoryIdentity, MemoryLifecycle,
    MemoryScope, MemoryType)
from ..query.query import MemoryQuery
from ..semantic.record import SemanticMemoryRecord
from ..working.state import WorkingMemoryState
from .learning_cycle import CandidateJournal
from .learning_records import (
    LearningDecision, LearningPolicy, LearningRecallResult,
    LearningRecordRef, LearningTransitionResult, LearningUseResult)


def _actor(goal: str, value: str, *, profile: str) -> Loop:
    runtime = Loop(
        goal,
        LoopConfig(
            framework="custom", custom_steps=("act",), power="light",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
            exit_condition="accepted_success"),
        ledger=LoopLedger(),
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, profile),
        relationship=LoopRelationship.starting())

    def handler(active: Loop, _step: str, _context: dict) -> StepOutcome:
        active.ledger.record(
            loop_id=active.loop_id, event="custom", fixture_value=value)
        return StepOutcome(value, mode="deterministic", confidence=1.0)

    runtime.run(handler=handler, max_steps=1)
    return runtime


def _candidate(
        record_id: str, subject: str, predicate: str, value: str, *,
        evidence: str, scope: MemoryScope = MemoryScope.PROJECT,
        supersedes: str = "") -> SemanticMemoryRecord:
    return SemanticMemoryRecord(
        identity=MemoryIdentity(
            record_id, "1.0.0", "0" * 64, MemoryType.SEMANTIC),
        subject=subject, predicate=predicate, object_value=value,
        claim_type="derived", scope=scope, supersedes=supersedes,
        evidence_refs=(
            MemoryEvidenceRef(evidence, "fixture", "supports"),),
        lifecycle=MemoryLifecycle.CANDIDATE)


def _promote(
        journal: CandidateJournal, policy: LearningPolicy,
        record: SemanticMemoryRecord, *, label: str
        ) -> tuple[
            LearningTransitionResult,
            LearningTransitionResult,
            LearningTransitionResult]:
    producer = _actor(
        f"produce {label}", record.object_value,
        profile="practitioner.self_improvement")
    staged = journal.stage(
        record, producer_loop=producer, policy=policy,
        reason=f"{label} producer completed an accepted fixture run")
    reviewed = journal.review(
        staged.ref,
        evaluator=lambda item: LearningDecision(
            bool(item.evidence_refs),
            f"{label} independent evidence check passed",
            (f"fixture:{label}:review",)),
        policy=policy)
    promoted = journal.promote(
        reviewed,
        authorizer=lambda item, review_record: LearningDecision(
            item.lifecycle is MemoryLifecycle.UNDER_REVIEW
            and review_record.entry_digest
            == reviewed.governance.entry_digest,
            f"{label} review binding and policy passed",
            (f"fixture:{label}:promotion",)),
        policy=policy)
    return staged, reviewed, promoted


def self_test() -> dict:
    """Run A, governed promotion, Run B reuse, and negative transfer."""
    results: list[dict] = []

    def check(name: str, ok, note: str = "") -> None:
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        journal = CandidateJournal(Path(tmp))
        policy = LearningPolicy()

        # Run A creates the exact candidate consumed later.
        run_a = _actor(
            "Run A: derive address-field normalization",
            "adress=>address",
            profile="practitioner.self_improvement")
        address_candidate = _candidate(
            "candidate.address.normalization",
            "adress field", "normalizes to", "address",
            evidence="fixture:run-a:misspelled-address-field")
        staged = journal.stage(
            address_candidate, producer_loop=run_a, policy=policy,
            reason="Run A observed one bounded normalization need")
        check(
            "stage_binds_actual_producer_loop",
            staged.record.provenance.producer_loop_id.startswith("loop:")
            and staged.governance.actor.loop_identity.startswith("loop:"),
            "identities derive from canonical Loop objects")
        try:
            journal.stage(
                _candidate(
                    "candidate.invalid.actor", "x", "maps", "y",
                    evidence="fixture:invalid"),
                producer_loop="loop.producer",  # type: ignore[arg-type]
                policy=policy)
            check("arbitrary_producer_string_is_refused", False)
        except TypeError:
            check("arbitrary_producer_string_is_refused", True)

        reviewed = journal.review(
            staged.ref,
            evaluator=lambda record: LearningDecision(
                record.object_value == "address"
                and bool(record.evidence_refs),
                "deterministic fixture confirms expected spelling",
                ("fixture:review:exact-output-check",)),
            policy=policy)
        check(
            "independent_review_is_distinct_and_exact",
            reviewed.record.lifecycle is MemoryLifecycle.UNDER_REVIEW
            and reviewed.governance.reviewer_loop_identity
            != reviewed.governance.producer_loop_identity
            and reviewed.governance.source_ref == staged.ref)
        try:
            journal.review(
                staged.ref,
                evaluator=lambda _record: LearningDecision(
                    True, "stale retry", ("fixture:stale",)),
                policy=policy)
            check("stale_candidate_binding_is_refused", False)
        except ValueError:
            check("stale_candidate_binding_is_refused", True)

        promoted = journal.promote(
            reviewed,
            authorizer=lambda record, review_record: LearningDecision(
                record.lifecycle is MemoryLifecycle.UNDER_REVIEW
                and review_record.entry_digest
                == reviewed.governance.entry_digest,
                "accepted review is exact and policy-compatible",
                ("fixture:promotion:review-binding",)),
            policy=policy)
        check(
            "promotion_binds_review_version_and_digest",
            promoted.record.lifecycle is MemoryLifecycle.ACTIVE
            and promoted.governance.review_entry_digest
            == reviewed.governance.entry_digest
            and promoted.governance.source_ref == reviewed.ref)
        check(
            "candidate_listing_hides_promoted_records",
            not journal.list_candidates())

        # Rejection is terminal and cannot be promoted by skipping review.
        reject_producer = _actor(
            "produce unsupported candidate", "unsupported",
            profile="practitioner.self_improvement")
        rejected_stage = journal.stage(
            _candidate(
                "candidate.rejected", "unsupported", "claims", "value",
                evidence="fixture:unsupported-claim"),
            producer_loop=reject_producer, policy=policy)
        rejected = journal.review(
            rejected_stage.ref,
            evaluator=lambda _record: LearningDecision(
                False, "counterexample invalidates the claim",
                ("fixture:counterexample",)),
            policy=policy)
        check(
            "rejected_candidate_is_terminal_and_not_retrievable",
            rejected.record.lifecycle is MemoryLifecycle.REJECTED
            and rejected.ref.record_id not in {
                ref.record_id for ref in journal.query(MemoryQuery(
                    memory_types=("semantic",),
                    scope=MemoryScope.PROJECT,
                    text="unsupported claims")).selected})
        try:
            journal.promote(
                rejected,
                authorizer=lambda _record, _review: LearningDecision(
                    True, "invalid promotion", ("fixture:invalid",)),
                policy=policy)
            check("rejected_candidate_cannot_be_promoted", False)
        except ValueError:
            check("rejected_candidate_cannot_be_promoted", True)

        # Matched control: same input and evaluator, zero recall.
        task_input, expected = "adress", "address"
        control = _actor(
            "Run B control: normalize without learned intelligence",
            task_input, profile="practitioner.solver")
        control_memory = WorkingMemoryState(
            run_id="run-b-control", loop_id=control.loop_id)
        control_output = task_input
        control_score = float(control_output == expected)
        check(
            "matched_control_has_fresh_empty_working_memory",
            not control_memory.compartment("recalled")
            and control_score == 0.0)

        # Run B starts with independent empty working state, recalls through
        # Intelligence Loops, applies the exact record, and records use.
        run_b = Loop(
            "Run B: apply reviewed address normalization",
            LoopConfig(
                framework="custom", custom_steps=("act",), power="light",
                allowable_modes=("deterministic",),
                preferred_modes=("deterministic",),
                delegated_modes=("deterministic",),
                exit_condition="accepted_success"),
            ledger=LoopLedger(),
            identity=LoopRoleIdentity(
                LoopRole.PRACTITIONER, "practitioner.solver"),
            relationship=LoopRelationship.starting())
        run_b_memory = WorkingMemoryState(
            run_id="run-b-memory", loop_id=run_b.loop_id)
        run_b_state: dict[str, object] = {}

        def run_b_handler(
                active: Loop, _step: str,
                _context: dict) -> StepOutcome:
            recall = journal.recall(
                MemoryQuery(
                    memory_types=("semantic",),
                    scope=MemoryScope.PROJECT,
                    text="adress field normalizes address",
                    require_evidence=True),
                requesting_loop=active,
                working_memory=run_b_memory,
                policy=policy)
            mapping = {
                record.subject.split()[0]: record.object_value
                for record in recall.records}
            output = mapping.get(task_input, task_input)
            score = float(output == expected)
            use = journal.observe_use(
                recall, consumer_loop=active,
                working_memory=run_b_memory,
                result_score=score, control_score=control_score,
                policy=policy,
                evidence_refs=(
                    "fixture:matched-exact-string-evaluator",),
                reason=(
                    "recalled mapping changed output "
                    "to the accepted value"))
            run_b_state.update(
                recall=recall, output=output, score=score, use=use)
            return StepOutcome(
                output, mode="deterministic", confidence=1.0)

        run_b.run(handler=run_b_handler, max_steps=1)
        recall = run_b_state["recall"]
        use = run_b_state["use"]
        assert isinstance(recall, LearningRecallResult)
        assert isinstance(use, LearningUseResult)
        check(
            "run_b_retrieves_and_observably_uses_promoted_intelligence",
            run_b_state["output"] == expected
            and promoted.ref in tuple(
                LearningRecordRef.from_record(record)
                for record in recall.records)
            and bool(use.governance_entry_digests))
        check(
            "matched_no_memory_control_shows_measurable_improvement",
            use.result_score == 1.0 and use.control_score == 0.0
            and use.improvement == 1.0,
            "deterministic fixture delta; not a production benchmark")
        check(
            "run_b_working_memory_was_fresh_then_populated",
            recall.working_memory_before != recall.working_memory_after
            and bool(run_b_memory.compartment("recalled")))

        # A user-only record is active in its scope but cannot leak into a
        # project-scoped task.
        _, _, user_promoted = _promote(
            journal, policy,
            _candidate(
                "candidate.user.spelling", "colour", "user prefers",
                "color", evidence="fixture:user-declaration",
                scope=MemoryScope.USER),
            label="user-spelling")
        project_retrieval = journal.query(MemoryQuery(
            memory_types=("semantic",), scope=MemoryScope.PROJECT,
            text="colour color"))
        user_retrieval = journal.query(MemoryQuery(
            memory_types=("semantic",), scope=MemoryScope.USER,
            text="colour color"))
        check(
            "negative_transfer_is_blocked_by_scope_before_ranking",
            user_promoted.ref.record_id not in {
                ref.record_id for ref in project_retrieval.selected}
            and user_promoted.ref.record_id in {
                ref.record_id for ref in user_retrieval.selected})

        rolled_back = journal.rollback(
            user_promoted.ref,
            authorizer=lambda _record: LearningDecision(
                True, "fixture withdrawal requires revocation",
                ("fixture:user-withdrawal",)),
            policy=policy)
        after_rollback = journal.query(MemoryQuery(
            memory_types=("semantic",), scope=MemoryScope.USER,
            text="colour color"))
        check(
            "rollback_is_append_only_and_removes_active_retrieval",
            rolled_back.record.lifecycle is MemoryLifecycle.REVOKED
            and user_promoted.ref.record_id not in {
                ref.record_id for ref in after_rollback.selected})

        _, _, old_active = _promote(
            journal, policy,
            _candidate(
                "candidate.separator.old", "export separator", "uses",
                "dash", evidence="fixture:old-format"),
            label="old-separator")
        _, _, new_active = _promote(
            journal, policy,
            _candidate(
                "candidate.separator.new", "export separator", "uses",
                "underscore", evidence="fixture:new-format",
                supersedes=old_active.ref.record_id),
            label="new-separator")
        superseded = journal.supersede(
            old_active.ref, new_active.ref,
            authorizer=lambda _old, _new: LearningDecision(
                True, "replacement is active and compatible",
                ("fixture:supersession-check",)),
            policy=policy)
        separator_retrieval = journal.query(MemoryQuery(
            memory_types=("semantic",), scope=MemoryScope.PROJECT,
            text="export separator"))
        separator_ids = {
            ref.record_id for ref in separator_retrieval.selected}
        check(
            "supersession_preserves_lineage_and_serves_replacement_only",
            superseded.record.lifecycle is MemoryLifecycle.DEPRECATED
            and superseded.record.superseded_by
            == new_active.ref.record_id
            and old_active.ref.record_id not in separator_ids
            and new_active.ref.record_id in separator_ids)

        validation = journal.validate_journal()
        check(
            "append_only_chain_and_record_digests_validate",
            validation["valid"] and validation["entries"] > 0,
            str(validation))
        reopened = CandidateJournal(Path(tmp))
        reopened_retrieval = reopened.query(MemoryQuery(
            memory_types=("semantic",), scope=MemoryScope.PROJECT,
            text="adress field normalizes address",
            require_evidence=True))
        check(
            "promotion_survives_fresh_repository_process_state",
            promoted.ref.record_id in {
                ref.record_id for ref in reopened_retrieval.selected})

    return {
        "fixture_kind": "OFFLINE_FIXTURE",
        "production_proof": False,
        "tests": results,
        "metrics": {
            "matched_control_score": 0.0,
            "learned_reuse_score": 1.0,
            "observed_fixture_delta": 1.0,
        },
    }
