"""Durable repository for the governed semantic-learning lifecycle.

This module owns append-only storage and legal transitions. Operational work
runs through the canonical Loop envelope imported from learning_records.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from ..model.memory_type import (
    MemoryLifecycle, MemoryRef, MemoryScope)
from ..query.query import MemoryQuery
from ..semantic.record import SemanticMemoryRecord
from .learning_records import (
    JOURNAL_SCHEMA,
    JournalEnvelope,
    LearningDecision,
    LearningGovernanceEntry,
    LearningPolicy,
    LearningRecallResult,
    LearningRecordRef,
    LearningTransitionResult,
    LearningUseResult,
    LoopExecutionEvidence,
    candidate_from_dict,
    clean_evidence,
    digest_mapping,
    loop_evidence,
    prepare_staged_record,
    record_and_supplied_evidence,
    record_digest_matches,
    run_loop_action,
    transitioned_record,
)
from .store import InMemoryMemoryStore

if TYPE_CHECKING:
    from ...loop.recursive_loop import Loop
    from ..working.state import WorkingMemoryState


def default_memory_root() -> Path:
    root = os.environ.get("LOOP_ENGINE_MEMORY_DIR", "")
    if root:
        return Path(root).expanduser().resolve()
    return Path(os.path.expanduser("~")) / ".loop-engine" / "memory"


class CandidateJournal:
    """Append-only semantic learning journal with governed transitions."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_memory_root()).expanduser().resolve()
        self.journal = self.root / "candidates.jsonl"

    def _append(
            self, record: SemanticMemoryRecord | None,
            entry: LearningGovernanceEntry) -> None:
        if not entry.entry_digest:
            raise ValueError("cannot append an unsigned governance entry")
        if record is not None \
                and LearningRecordRef.from_record(record) != entry.result_ref:
            raise ValueError(
                "journal record does not match governance result reference")
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": JOURNAL_SCHEMA,
            "record": record.to_dict() if record is not None else None,
            "governance": entry.to_dict(),
        }
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.journal.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _envelopes(self) -> list[JournalEnvelope]:
        output: list[JournalEnvelope] = []
        if not self.journal.is_file():
            return output
        with self.journal.open(encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                    if data.get("schema") == JOURNAL_SCHEMA:
                        record = (
                            candidate_from_dict(data["record"])
                            if data.get("record") else None)
                        entry = LearningGovernanceEntry.from_dict(
                            data["governance"])
                        output.append(JournalEnvelope(record, entry))
                    else:
                        output.append(JournalEnvelope(
                            candidate_from_dict(data), None, True))
                except (
                        KeyError, TypeError, ValueError,
                        json.JSONDecodeError) as exc:
                    raise ValueError(
                        f"invalid learning journal line {line_number}: "
                        f"{exc}") from exc
        return output

    def _records(self) -> list[SemanticMemoryRecord]:
        return [
            item.record for item in self._envelopes()
            if item.record is not None]

    def governance_history(
            self, record_id: str = ""
            ) -> tuple[LearningGovernanceEntry, ...]:
        return tuple(
            item.governance for item in self._envelopes()
            if item.governance is not None
            and (not record_id
                 or item.governance.result_ref.record_id == record_id
                 or item.governance.source_ref.record_id == record_id))

    def validate_journal(self) -> dict:
        violations: list[str] = []
        previous = ""
        sequence = 1
        for index, item in enumerate(self._envelopes(), 1):
            record, entry = item.record, item.governance
            if item.legacy:
                violations.append(f"line {index}: legacy_ungoverned")
                continue
            if entry is None:
                violations.append(f"line {index}: missing_governance")
                continue
            if entry.sequence != sequence:
                violations.append(
                    f"line {index}: sequence {entry.sequence}, "
                    f"expected {sequence}")
            if entry.previous_entry_digest != previous:
                violations.append(
                    f"line {index}: broken_previous_digest")
            if entry.entry_digest != entry.recomputed_digest():
                violations.append(f"line {index}: entry_digest_mismatch")
            if record is not None:
                if not record_digest_matches(record):
                    violations.append(
                        f"line {index}: record_digest_mismatch")
                if LearningRecordRef.from_record(record) != entry.result_ref:
                    violations.append(f"line {index}: result_ref_mismatch")
            previous, sequence = entry.entry_digest, sequence + 1
        return {
            "valid": not violations, "entries": sequence - 1,
            "violations": violations, "tail_digest": previous}

    def _latest_envelope(self, record_id: str) -> JournalEnvelope:
        versions = [
            item for item in self._envelopes()
            if item.record is not None
            and item.record.identity.record_id == record_id]
        if not versions:
            raise ValueError(f"no record {record_id!r} in the journal")
        return versions[-1]

    def _latest(self, record_id: str) -> SemanticMemoryRecord:
        record = self._latest_envelope(record_id).record
        assert record is not None
        return record

    def _require_latest(self, ref: LearningRecordRef) -> JournalEnvelope:
        item = self._latest_envelope(ref.record_id)
        assert item.record is not None
        actual = LearningRecordRef.from_record(item.record)
        if actual != ref:
            raise ValueError(
                "stale learning reference: expected exact latest "
                f"{actual.to_dict()}, received {ref.to_dict()}")
        if item.legacy or item.governance is None:
            raise ValueError(
                "legacy ungoverned candidates require explicit migration")
        return item

    def _next_entry(
            self, *, action: str, source_ref: LearningRecordRef,
            result_ref: LearningRecordRef, actor: LoopExecutionEvidence,
            producer: str, reviewer: str, policy: LearningPolicy,
            scope: MemoryScope, evidence: tuple[str, ...], reason: str,
            decision: str, review_digest: str = "",
            related_ref: LearningRecordRef | None = None,
            metrics: dict[str, float] | None = None
            ) -> LearningGovernanceEntry:
        history = self.governance_history()
        return LearningGovernanceEntry(
            sequence=len(history) + 1, action=action,
            source_ref=source_ref, result_ref=result_ref, actor=actor,
            producer_loop_identity=producer,
            reviewer_loop_identity=reviewer,
            policy_version=policy.version, scope=scope,
            evidence_refs=evidence, reason=reason, decision=decision,
            previous_entry_digest=(
                history[-1].entry_digest if history else ""),
            review_entry_digest=review_digest, related_ref=related_ref,
            metrics=tuple(sorted((metrics or {}).items()))).signed()

    def as_store(self) -> InMemoryMemoryStore:
        latest: dict[str, JournalEnvelope] = {}
        for item in self._envelopes():
            if item.record is not None:
                latest[item.record.identity.record_id] = item
        records = []
        for item in latest.values():
            assert item.record is not None
            if item.record.lifecycle is MemoryLifecycle.ACTIVE \
                    and (item.governance is None
                         or item.governance.action != "candidate_promoted"):
                continue
            records.append(item.record)
        return InMemoryMemoryStore(records)

    def list_candidates(self) -> list[dict]:
        latest: dict[str, JournalEnvelope] = {}
        for item in self._envelopes():
            if item.record is not None:
                latest[item.record.identity.record_id] = item
        output = []
        for item in latest.values():
            record = item.record
            assert record is not None
            if record.lifecycle is MemoryLifecycle.CANDIDATE:
                output.append({
                    "record_id": record.identity.record_id,
                    "version": record.identity.version,
                    "content_digest": record.identity.content_digest,
                    "subject": record.subject,
                    "predicate": record.predicate,
                    "claim_type": record.claim_type,
                    "scope": record.scope.value,
                    "lifecycle": record.lifecycle.value,
                    "governed": (
                        not item.legacy and item.governance is not None),
                })
        return output

    def query(self, query: MemoryQuery):
        return self.as_store().query(query)

    def get_exact(self, ref: LearningRecordRef) -> SemanticMemoryRecord:
        for record in self._records():
            if LearningRecordRef.from_record(record) == ref:
                return record
        raise ValueError(f"learning record {ref.to_dict()} is unavailable")

    def stage(
            self, record: SemanticMemoryRecord, *, producer_loop: "Loop",
            policy: LearningPolicy, evidence_refs: tuple[str, ...] = (),
            reason: str = "verified run produced a reusable candidate"
            ) -> LearningTransitionResult:
        producer = loop_evidence(producer_loop, require_accepted=True)
        if producer.role != "practitioner":
            raise ValueError(
                "learning candidates require a Practitioner Loop")
        policy.require_scope(record.scope)
        refs = record_and_supplied_evidence(record, evidence_refs)
        if policy.require_evidence and not refs:
            raise ValueError("candidate staging requires evidence")
        if record.lifecycle is not MemoryLifecycle.CANDIDATE:
            raise ValueError("only candidate records may be staged")

        def action(active: "Loop") -> LearningTransitionResult:
            actor = loop_evidence(active)
            staged = prepare_staged_record(record, producer, refs)
            ref = LearningRecordRef.from_record(staged)
            if any(item.identity.record_id == ref.record_id
                   for item in self._records()):
                raise ValueError(
                    f"record id {ref.record_id!r} is already journaled")
            entry = self._next_entry(
                action="candidate_staged", source_ref=ref, result_ref=ref,
                actor=actor, producer=producer.loop_identity, reviewer="",
                policy=policy, scope=staged.scope, evidence=refs,
                reason=reason, decision="candidate")
            self._append(staged, entry)
            return LearningTransitionResult(staged, entry)

        result, _ = run_loop_action(
            objective=f"stage learning candidate {record.identity.record_id}",
            action=action, profile_id="practitioner.code_execution",
            role="practitioner", effects=("reads_fs", "writes_fs"),
            event_kind="stage")
        assert isinstance(result, LearningTransitionResult)
        return result

    def review(
            self, candidate_ref: LearningRecordRef, *,
            evaluator: Callable[
                [SemanticMemoryRecord], LearningDecision],
            policy: LearningPolicy) -> LearningTransitionResult:
        item = self._require_latest(candidate_ref)
        record, staged_entry = item.record, item.governance
        assert record is not None and staged_entry is not None
        if record.lifecycle is not MemoryLifecycle.CANDIDATE \
                or staged_entry.action != "candidate_staged":
            raise ValueError(
                "only an exact governed candidate enters review")
        policy.require_scope(record.scope)

        def action(active: "Loop") -> LearningTransitionResult:
            reviewer = loop_evidence(active)
            if reviewer.loop_identity == staged_entry.producer_loop_identity:
                raise ValueError(
                    "the producing Loop cannot review its own candidate")
            active.ledger.record(
                loop_id=active.loop_id, event="evaluation.started",
                record_id=record.identity.record_id,
                record_version=record.identity.version,
                record_digest=record.identity.content_digest)
            decision = evaluator(record)
            if not isinstance(decision, LearningDecision):
                raise TypeError(
                    "review evaluator must return LearningDecision")
            target = (MemoryLifecycle.UNDER_REVIEW if decision.approved
                      else MemoryLifecycle.REJECTED)
            reviewed = transitioned_record(
                record, target, decision.evidence_refs)
            entry = self._next_entry(
                action=("review_accepted" if decision.approved
                        else "review_rejected"),
                source_ref=candidate_ref,
                result_ref=LearningRecordRef.from_record(reviewed),
                actor=reviewer,
                producer=staged_entry.producer_loop_identity,
                reviewer=reviewer.loop_identity, policy=policy,
                scope=reviewed.scope, evidence=decision.evidence_refs,
                reason=decision.reason,
                decision=("accepted" if decision.approved else "rejected"))
            self._append(reviewed, entry)
            active.ledger.record(
                loop_id=active.loop_id, event="evaluation.completed",
                record_id=record.identity.record_id,
                accepted=decision.approved,
                governance_entry_digest=entry.entry_digest)
            return LearningTransitionResult(reviewed, entry)

        result, _ = run_loop_action(
            objective=f"independently review {candidate_ref.record_id}",
            action=action, profile_id="practitioner.verifier",
            role="practitioner", effects=("reads_fs", "writes_fs"),
            event_kind="review")
        assert isinstance(result, LearningTransitionResult)
        return result

    def promote(
            self, reviewed: LearningTransitionResult, *,
            authorizer: Callable[
                [SemanticMemoryRecord, LearningGovernanceEntry],
                LearningDecision],
            policy: LearningPolicy) -> LearningTransitionResult:
        if reviewed.governance.action != "review_accepted" \
                or reviewed.record.lifecycle \
                is not MemoryLifecycle.UNDER_REVIEW:
            raise ValueError(
                "promotion requires an accepted review result")
        item = self._require_latest(reviewed.ref)
        record, review_entry = item.record, item.governance
        assert record is not None and review_entry is not None
        if review_entry.entry_digest != reviewed.governance.entry_digest:
            raise ValueError(
                "promotion review record is stale or unavailable")
        policy.require_scope(record.scope)

        def action(active: "Loop") -> LearningTransitionResult:
            promoter = loop_evidence(active)
            producer = review_entry.producer_loop_identity
            reviewer = review_entry.reviewer_loop_identity
            if promoter.loop_identity in {producer, reviewer}:
                raise ValueError(
                    "promotion needs a Loop distinct from producer "
                    "and reviewer")
            active.ledger.record(
                loop_id=active.loop_id, event="evaluation.started",
                record_id=record.identity.record_id,
                review_entry_digest=review_entry.entry_digest)
            decision = authorizer(record, review_entry)
            if not isinstance(decision, LearningDecision):
                raise TypeError(
                    "promotion authorizer must return LearningDecision")
            target = (MemoryLifecycle.ACTIVE if decision.approved
                      else MemoryLifecycle.REJECTED)
            promoted = transitioned_record(
                record, target, decision.evidence_refs,
                claim_type=("reviewed" if decision.approved
                            else record.claim_type))
            entry = self._next_entry(
                action=("candidate_promoted" if decision.approved
                        else "promotion_rejected"),
                source_ref=reviewed.ref,
                result_ref=LearningRecordRef.from_record(promoted),
                actor=promoter, producer=producer, reviewer=reviewer,
                policy=policy, scope=promoted.scope,
                evidence=decision.evidence_refs, reason=decision.reason,
                decision=("active" if decision.approved else "rejected"),
                review_digest=review_entry.entry_digest)
            self._append(promoted, entry)
            active.ledger.record(
                loop_id=active.loop_id, event="evaluation.completed",
                record_id=record.identity.record_id,
                accepted=decision.approved,
                governance_entry_digest=entry.entry_digest)
            return LearningTransitionResult(promoted, entry)

        result, _ = run_loop_action(
            objective=f"authorize promotion of {reviewed.ref.record_id}",
            action=action, profile_id="practitioner.verifier",
            role="practitioner", effects=("reads_fs", "writes_fs"),
            event_kind="promote")
        assert isinstance(result, LearningTransitionResult)
        return result

    def rollback(
            self, active_ref: LearningRecordRef, *,
            authorizer: Callable[
                [SemanticMemoryRecord], LearningDecision],
            policy: LearningPolicy) -> LearningTransitionResult:
        item = self._require_latest(active_ref)
        record, prior = item.record, item.governance
        assert record is not None and prior is not None
        if record.lifecycle is not MemoryLifecycle.ACTIVE \
                or prior.action != "candidate_promoted":
            raise ValueError(
                "rollback requires an exact promoted active record")
        policy.require_scope(record.scope)

        def action(active: "Loop") -> LearningTransitionResult:
            authority = loop_evidence(active)
            decision = authorizer(record)
            if not isinstance(decision, LearningDecision):
                raise TypeError(
                    "rollback authorizer must return LearningDecision")
            if not decision.approved:
                raise PermissionError("rollback authority did not approve")
            revoked = transitioned_record(
                record, MemoryLifecycle.REVOKED,
                decision.evidence_refs, retracted=True)
            entry = self._next_entry(
                action="candidate_rolled_back", source_ref=active_ref,
                result_ref=LearningRecordRef.from_record(revoked),
                actor=authority, producer=prior.producer_loop_identity,
                reviewer=authority.loop_identity, policy=policy,
                scope=revoked.scope, evidence=decision.evidence_refs,
                reason=decision.reason, decision="revoked")
            self._append(revoked, entry)
            return LearningTransitionResult(revoked, entry)

        result, _ = run_loop_action(
            objective=f"roll back learned record {active_ref.record_id}",
            action=action, profile_id="practitioner.verifier",
            role="practitioner", effects=("reads_fs", "writes_fs"),
            event_kind="rollback")
        assert isinstance(result, LearningTransitionResult)
        return result

    def supersede(
            self, active_ref: LearningRecordRef,
            replacement_ref: LearningRecordRef, *,
            authorizer: Callable[
                [SemanticMemoryRecord, SemanticMemoryRecord],
                LearningDecision],
            policy: LearningPolicy) -> LearningTransitionResult:
        item = self._require_latest(active_ref)
        replacement_item = self._require_latest(replacement_ref)
        record, prior = item.record, item.governance
        replacement = replacement_item.record
        replacement_entry = replacement_item.governance
        assert record is not None and prior is not None
        assert replacement is not None and replacement_entry is not None
        if record.lifecycle is not MemoryLifecycle.ACTIVE \
                or replacement.lifecycle is not MemoryLifecycle.ACTIVE:
            raise ValueError(
                "supersession requires two exact active records")
        if replacement_entry.action != "candidate_promoted":
            raise ValueError(
                "replacement must have a promotion record")
        if replacement.supersedes != record.identity.record_id:
            raise ValueError(
                "replacement must explicitly name superseded record")
        if replacement.scope is not record.scope:
            raise ValueError("replacement cannot silently change scope")
        policy.require_scope(record.scope)

        def action(active: "Loop") -> LearningTransitionResult:
            authority = loop_evidence(active)
            decision = authorizer(record, replacement)
            if not isinstance(decision, LearningDecision):
                raise TypeError(
                    "supersession authorizer must return LearningDecision")
            if not decision.approved:
                raise PermissionError(
                    "supersession authority did not approve")
            deprecated = transitioned_record(
                record, MemoryLifecycle.DEPRECATED,
                decision.evidence_refs,
                superseded_by=replacement_ref.record_id)
            entry = self._next_entry(
                action="candidate_superseded", source_ref=active_ref,
                result_ref=LearningRecordRef.from_record(deprecated),
                actor=authority, producer=prior.producer_loop_identity,
                reviewer=authority.loop_identity, policy=policy,
                scope=deprecated.scope, evidence=decision.evidence_refs,
                reason=decision.reason, decision="deprecated",
                related_ref=replacement_ref)
            self._append(deprecated, entry)
            return LearningTransitionResult(deprecated, entry)

        result, _ = run_loop_action(
            objective=f"supersede learned record {active_ref.record_id}",
            action=action, profile_id="practitioner.verifier",
            role="practitioner", effects=("reads_fs", "writes_fs"),
            event_kind="supersede")
        assert isinstance(result, LearningTransitionResult)
        return result

    def recall(
            self, query: MemoryQuery, *, requesting_loop: "Loop",
            working_memory: "WorkingMemoryState", policy: LearningPolicy
            ) -> LearningRecallResult:
        loop_evidence(requesting_loop)
        if working_memory.loop_id != requesting_loop.loop_id:
            raise ValueError(
                "working memory must belong to the requesting Loop")
        policy.require_scope(query.scope)
        before = working_memory.snapshot()["digest"]

        def action(active: "Loop") -> LearningRecallResult:
            retrieval_record = self.query(query)
            records, digests = [], []
            query_actor = loop_evidence(active)
            for selected in retrieval_record.selected:
                exact = LearningRecordRef(
                    selected.record_id, selected.version,
                    self._digest_for_ref(selected), selected.memory_type)
                record = self.get_exact(exact)
                materialized, _ = run_loop_action(
                    objective=(
                        f"materialize learned record {selected.record_id}"),
                    action=lambda _loop, item=record: item,
                    profile_id="intelligence.materialize",
                    role="intelligence", effects=("reads_fs",),
                    event_kind="materialize", parent=active,
                    relationship="retrieved_by")
                assert isinstance(materialized, SemanticMemoryRecord)
                working_memory.put(
                    "recalled", selected.record_id,
                    {"ref": exact.to_dict(),
                     "record": materialized.to_dict()})
                promotion = self._promotion_for(exact)
                entry = self._next_entry(
                    action="intelligence_retrieved",
                    source_ref=exact, result_ref=exact, actor=query_actor,
                    producer=promotion.producer_loop_identity,
                    reviewer=promotion.reviewer_loop_identity,
                    policy=policy, scope=record.scope,
                    evidence=(
                        f"promotion:{promotion.entry_digest}",
                        "query:"
                        f"{digest_mapping(retrieval_record.to_dict())}"),
                    reason=(
                        "later run selected exact active "
                        "learned intelligence"),
                    decision="retrieved")
                self._append(None, entry)
                records.append(materialized)
                digests.append(entry.entry_digest)
            return LearningRecallResult(
                retrieval_record, tuple(records), query_actor, tuple(digests),
                before, working_memory.snapshot()["digest"])

        result, _ = run_loop_action(
            objective="query governed learned intelligence", action=action,
            profile_id="intelligence.search", role="intelligence",
            effects=("reads_fs", "writes_fs"), event_kind="recall",
            parent=requesting_loop, relationship="queried_by")
        assert isinstance(result, LearningRecallResult)
        return result

    def observe_use(
            self, recall: LearningRecallResult, *, consumer_loop: "Loop",
            working_memory: "WorkingMemoryState", result_score: float,
            control_score: float, policy: LearningPolicy,
            evidence_refs: tuple[str, ...], reason: str
            ) -> LearningUseResult:
        loop_evidence(consumer_loop)
        if working_memory.loop_id != consumer_loop.loop_id:
            raise ValueError(
                "working memory must belong to the consuming Loop")
        if not 0.0 <= result_score <= 1.0 \
                or not 0.0 <= control_score <= 1.0:
            raise ValueError("matched scores must be in [0, 1]")
        evidence = clean_evidence(evidence_refs)
        if not evidence or not reason.strip():
            raise ValueError("observed use needs evidence and a reason")
        record_refs = tuple(
            LearningRecordRef.from_record(item) for item in recall.records)
        if not record_refs:
            raise ValueError(
                "cannot observe use without a recalled record")
        for ref in record_refs:
            value = working_memory.get("recalled", ref.record_id)
            if not value or value.get("ref") != ref.to_dict():
                raise ValueError(
                    "observed use must bind a record in working memory")

        def action(active: "Loop") -> LearningUseResult:
            actor, digests = loop_evidence(active), []
            for ref in record_refs:
                record = self.get_exact(ref)
                promotion = self._promotion_for(ref)
                entry = self._next_entry(
                    action="intelligence_used", source_ref=ref,
                    result_ref=ref, actor=actor,
                    producer=promotion.producer_loop_identity,
                    reviewer=promotion.reviewer_loop_identity,
                    policy=policy, scope=record.scope,
                    evidence=evidence + (
                        f"query-loop:{recall.query_loop.loop_identity}",),
                    reason=reason, decision="used",
                    metrics={
                        "result_score": result_score,
                        "control_score": control_score,
                        "improvement": result_score - control_score})
                self._append(None, entry)
                digests.append(entry.entry_digest)
            return LearningUseResult(
                record_refs, result_score, control_score, tuple(digests))

        result, _ = run_loop_action(
            objective="record observed use of learned intelligence",
            action=action, profile_id="practitioner.code_execution",
            role="practitioner", effects=("reads_fs", "writes_fs"),
            event_kind="use", parent=consumer_loop,
            relationship="spawned_by")
        assert isinstance(result, LearningUseResult)
        return result

    def _digest_for_ref(self, ref: MemoryRef) -> str:
        for record in self._records():
            if record.identity.record_id == ref.record_id \
                    and record.identity.version == ref.version \
                    and record.identity.memory_type is ref.memory_type:
                return record.identity.content_digest
        raise ValueError(f"selected record {ref.to_dict()} is unavailable")

    def _promotion_for(
            self, ref: LearningRecordRef) -> LearningGovernanceEntry:
        matches = [
            item for item in self.governance_history(ref.record_id)
            if item.action == "candidate_promoted"
            and item.result_ref == ref]
        if not matches:
            raise ValueError(
                "active record has no exact promotion record")
        return matches[-1]
