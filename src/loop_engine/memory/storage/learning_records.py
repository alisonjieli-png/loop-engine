"""Typed records and canonical Loop envelope for governed learning.

These objects are passive records, references, decisions, and lifecycle
evidence. The
operation helper executes their state changes through the sole Loop runtime;
it does not introduce another runtime or graph vertex.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Callable, TYPE_CHECKING

from ..lifecycle.lifecycle import TRANSITIONS
from ..model.memory_type import (
    MemoryEvidenceRef,
    MemoryIdentity,
    MemoryLifecycle,
    MemoryProvenance,
    MemoryRef,
    MemoryScope,
    MemoryType,
)
from ..semantic.record import SemanticMemoryRecord

if TYPE_CHECKING:
    from ...loop.recursive_loop import Loop, LoopLedger


JOURNAL_SCHEMA = "learning_journal/v1"
GOVERNANCE_SCHEMA = "learning_governance/v1"
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
ACTIONS = frozenset({
    "candidate_staged",
    "review_accepted",
    "review_rejected",
    "candidate_promoted",
    "promotion_rejected",
    "candidate_rolled_back",
    "candidate_superseded",
    "intelligence_retrieved",
    "intelligence_used",
})
REVIEW_ACTIONS = frozenset({
    "review_accepted",
    "review_rejected",
    "candidate_promoted",
    "promotion_rejected",
    "candidate_rolled_back",
    "candidate_superseded",
})


@dataclass(frozen=True)
class LearningPolicy:
    """Typed policy applied to a governed learning transition."""

    version: str = "1.0.0"
    allowed_scopes: tuple[MemoryScope, ...] = (
        MemoryScope.USER,
        MemoryScope.PROJECT,
        MemoryScope.WORKSPACE,
        MemoryScope.ORGANIZATION,
        MemoryScope.GLOBAL,
    )
    require_evidence: bool = True

    def __post_init__(self) -> None:
        if not SEMVER.fullmatch(self.version):
            raise ValueError(
                "learning policy version must use MAJOR.MINOR.PATCH")
        scopes = tuple(MemoryScope(scope) for scope in self.allowed_scopes)
        if not scopes or len(scopes) != len(set(scopes)):
            raise ValueError("learning policy needs unique allowed scopes")
        object.__setattr__(self, "allowed_scopes", scopes)

    def require_scope(self, scope: MemoryScope) -> None:
        if scope not in self.allowed_scopes:
            raise PermissionError(
                f"scope {scope.value!r} is outside learning policy "
                f"{self.version}")


@dataclass(frozen=True)
class LearningRecordRef:
    """Exact version-and-digest binding for one semantic record."""

    record_id: str
    version: str
    content_digest: str
    memory_type: MemoryType = MemoryType.SEMANTIC

    def __post_init__(self) -> None:
        if not self.record_id or not self.version or not self.content_digest:
            raise ValueError("learning reference needs id, version, and digest")
        if not SEMVER.fullmatch(self.version):
            raise ValueError(
                "learning record version must use MAJOR.MINOR.PATCH")
        object.__setattr__(self, "memory_type", MemoryType(self.memory_type))
        if self.memory_type is not MemoryType.SEMANTIC:
            raise ValueError("this journal currently stores semantic records")

    @classmethod
    def from_record(cls, record: SemanticMemoryRecord) -> "LearningRecordRef":
        identity = record.identity
        return cls(
            identity.record_id,
            identity.version,
            identity.content_digest,
            identity.memory_type,
        )

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "version": self.version,
            "content_digest": self.content_digest,
            "memory_type": self.memory_type.value,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LearningRecordRef":
        return cls(
            value["record_id"],
            value["version"],
            value["content_digest"],
            MemoryType(value.get("memory_type", "semantic")),
        )


@dataclass(frozen=True)
class LoopExecutionEvidence:
    """Definition-bound evidence derived from an actual canonical Loop."""

    loop_identity: str
    runtime_loop_id: str
    definition_id: str
    definition_version: str
    definition_digest: str
    role: str
    profile_id: str
    relationship: str
    initialization_event_digest: str

    def __post_init__(self) -> None:
        if any(not value for value in (
                self.loop_identity,
                self.runtime_loop_id,
                self.definition_id,
                self.definition_version,
                self.definition_digest,
                self.role,
                self.profile_id,
                self.relationship,
                self.initialization_event_digest)):
            raise ValueError("Loop execution evidence cannot contain blanks")

    def to_dict(self) -> dict:
        return {
            "loop_identity": self.loop_identity,
            "runtime_loop_id": self.runtime_loop_id,
            "definition_id": self.definition_id,
            "definition_version": self.definition_version,
            "definition_digest": self.definition_digest,
            "role": self.role,
            "profile_id": self.profile_id,
            "relationship": self.relationship,
            "initialization_event_digest":
                self.initialization_event_digest,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopExecutionEvidence":
        return cls(**value)


@dataclass(frozen=True)
class LearningDecision:
    """Evidence-backed decision returned by a verifier Loop."""

    approved: bool
    reason: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        refs = clean_evidence(self.evidence_refs)
        object.__setattr__(self, "evidence_refs", refs)
        if not self.reason.strip():
            raise ValueError("a learning decision needs a reason")
        if not refs:
            raise ValueError("a learning decision needs evidence")


@dataclass(frozen=True)
class LearningGovernanceEntry:
    """One hash-chained, append-only governance fact."""

    sequence: int
    action: str
    source_ref: LearningRecordRef
    result_ref: LearningRecordRef
    actor: LoopExecutionEvidence
    producer_loop_identity: str
    reviewer_loop_identity: str
    policy_version: str
    scope: MemoryScope
    evidence_refs: tuple[str, ...]
    reason: str
    decision: str
    previous_entry_digest: str = ""
    review_entry_digest: str = ""
    related_ref: LearningRecordRef | None = None
    metrics: tuple[tuple[str, float], ...] = ()
    entry_digest: str = ""
    schema: str = GOVERNANCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != GOVERNANCE_SCHEMA:
            raise ValueError("unknown learning governance schema")
        if self.sequence < 1 or self.action not in ACTIONS:
            raise ValueError("invalid learning governance sequence or action")
        if not self.producer_loop_identity:
            raise ValueError("producer Loop identity cannot be empty")
        if self.action in REVIEW_ACTIONS:
            if not self.reviewer_loop_identity:
                raise ValueError("reviewer Loop identity cannot be empty")
            if self.reviewer_loop_identity == self.producer_loop_identity:
                raise ValueError(
                    "the producing Loop cannot review its own candidate")
        if not SEMVER.fullmatch(self.policy_version):
            raise ValueError("governance policy version must be semantic")
        object.__setattr__(self, "scope", MemoryScope(self.scope))
        refs = clean_evidence(self.evidence_refs)
        object.__setattr__(self, "evidence_refs", refs)
        if not refs or not self.reason.strip() or not self.decision.strip():
            raise ValueError(
                "governance needs evidence, a reason, and a decision")
        if self.action in {"candidate_promoted", "promotion_rejected"} \
                and not self.review_entry_digest:
            raise ValueError("promotion must bind the exact review entry")
        if self.entry_digest and self.entry_digest != self.recomputed_digest():
            raise ValueError(
                "learning governance entry digest does not match")

    def _payload(self) -> dict:
        return {
            "schema": self.schema,
            "sequence": self.sequence,
            "action": self.action,
            "source_ref": self.source_ref.to_dict(),
            "result_ref": self.result_ref.to_dict(),
            "actor": self.actor.to_dict(),
            "producer_loop_identity": self.producer_loop_identity,
            "reviewer_loop_identity": self.reviewer_loop_identity,
            "policy_version": self.policy_version,
            "scope": self.scope.value,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
            "decision": self.decision,
            "previous_entry_digest": self.previous_entry_digest,
            "review_entry_digest": self.review_entry_digest,
            "related_ref": (
                self.related_ref.to_dict() if self.related_ref else None),
            "metrics": {name: value for name, value in self.metrics},
        }

    def recomputed_digest(self) -> str:
        return digest_mapping(self._payload())

    def signed(self) -> "LearningGovernanceEntry":
        return replace(self, entry_digest=self.recomputed_digest())

    def to_dict(self) -> dict:
        return {**self._payload(), "entry_digest": self.entry_digest}

    @classmethod
    def from_dict(cls, value: dict) -> "LearningGovernanceEntry":
        return cls(
            sequence=int(value["sequence"]),
            action=value["action"],
            source_ref=LearningRecordRef.from_dict(value["source_ref"]),
            result_ref=LearningRecordRef.from_dict(value["result_ref"]),
            actor=LoopExecutionEvidence.from_dict(value["actor"]),
            producer_loop_identity=value["producer_loop_identity"],
            reviewer_loop_identity=value.get(
                "reviewer_loop_identity", ""),
            policy_version=value["policy_version"],
            scope=MemoryScope(value["scope"]),
            evidence_refs=tuple(value.get("evidence_refs", ())),
            reason=value["reason"],
            decision=value["decision"],
            previous_entry_digest=value.get(
                "previous_entry_digest", ""),
            review_entry_digest=value.get("review_entry_digest", ""),
            related_ref=(
                LearningRecordRef.from_dict(value["related_ref"])
                if value.get("related_ref") else None),
            metrics=tuple(sorted(
                (str(name), float(metric))
                for name, metric in value.get("metrics", {}).items())),
            entry_digest=value["entry_digest"],
            schema=value.get("schema", ""),
        )


@dataclass(frozen=True)
class LearningTransitionResult:
    """Record and governance evidence for one lifecycle transition."""

    record: SemanticMemoryRecord
    governance: LearningGovernanceEntry

    @property
    def ref(self) -> LearningRecordRef:
        return LearningRecordRef.from_record(self.record)

    def to_dict(self) -> dict:
        return {
            "record": self.record.to_dict(),
            "governance": self.governance.to_dict(),
        }


@dataclass(frozen=True)
class LearningRecallResult:
    """Exact selected records and retrieval evidence for one later run."""

    retrieval_record: object
    records: tuple[SemanticMemoryRecord, ...]
    query_loop: LoopExecutionEvidence
    retrieval_entry_digests: tuple[str, ...]
    working_memory_before: str
    working_memory_after: str

    def to_dict(self) -> dict:
        return {
            "retrieval_record": self.retrieval_record.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "query_loop": self.query_loop.to_dict(),
            "retrieval_entry_digests":
                list(self.retrieval_entry_digests),
            "working_memory_before": self.working_memory_before,
            "working_memory_after": self.working_memory_after,
        }


@dataclass(frozen=True)
class LearningUseResult:
    """Observed use of exact recalled intelligence with a matched control."""

    record_refs: tuple[LearningRecordRef, ...]
    result_score: float
    control_score: float
    governance_entry_digests: tuple[str, ...]

    @property
    def improvement(self) -> float:
        return self.result_score - self.control_score

    def to_dict(self) -> dict:
        return {
            "record_refs": [ref.to_dict() for ref in self.record_refs],
            "result_score": self.result_score,
            "control_score": self.control_score,
            "improvement": self.improvement,
            "governance_entry_digests":
                list(self.governance_entry_digests),
        }


@dataclass(frozen=True)
class CandidateStageRequest:
    """Passive input contract for staging one verified candidate."""

    record: SemanticMemoryRecord
    producer_loop: "Loop"
    policy: LearningPolicy
    evidence_refs: tuple[str, ...] = ()
    reason: str = "verified run produced a reusable candidate"


@dataclass(frozen=True)
class LearningSupersessionRequest:
    """Passive input contract for replacing one active learned record."""

    active_ref: LearningRecordRef
    replacement_ref: LearningRecordRef
    authorizer: Callable[
        [SemanticMemoryRecord, SemanticMemoryRecord], LearningDecision]
    policy: LearningPolicy


@dataclass(frozen=True)
class LearningRecallRequest:
    """Passive input contract for governed recall into working memory."""

    query: "MemoryQuery"
    requesting_loop: "Loop"
    working_memory: "WorkingMemoryState"
    policy: LearningPolicy


@dataclass(frozen=True)
class LearningUseObservationRequest:
    """Passive input contract for matched-control learning-use evidence."""

    recall: LearningRecallResult
    consumer_loop: "Loop"
    working_memory: "WorkingMemoryState"
    result_score: float
    control_score: float
    policy: LearningPolicy
    evidence_refs: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class RecordTransitionRequest:
    """Passive input contract for one semantic lifecycle transition."""

    record: SemanticMemoryRecord
    target: MemoryLifecycle
    evidence_refs: tuple[str, ...]
    claim_type: str | None = None
    retracted: bool | None = None
    superseded_by: str | None = None


@dataclass(frozen=True)
class LearningOperationRequest:
    """Passive configuration for one bounded canonical Loop operation."""

    objective: str
    action: Callable[["Loop"], object]
    profile_id: str
    role: str
    effects: tuple[str, ...]
    event_kind: str
    parent: "Loop | None" = None
    ledger: "LoopLedger | None" = None
    relationship: str = "starting"


@dataclass(frozen=True)
class JournalEnvelope:
    record: SemanticMemoryRecord | None
    governance: LearningGovernanceEntry | None
    legacy: bool = False


def clean_evidence(values) -> tuple[str, ...]:
    cleaned = tuple(
        str(value).strip() for value in values if str(value).strip())
    if len(cleaned) != len(set(cleaned)):
        raise ValueError("evidence references must be unique")
    return cleaned


def digest_mapping(value: dict) -> str:
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_digest(data: dict) -> str:
    value = json.loads(json.dumps(data))
    value["identity"]["content_digest"] = ""
    return digest_mapping(value)


def record_digest_matches(record: SemanticMemoryRecord) -> bool:
    return record.identity.content_digest == record_digest(record.to_dict())


def resigned(data: dict) -> SemanticMemoryRecord:
    value = json.loads(json.dumps(data))
    value["identity"]["content_digest"] = record_digest(value)
    return candidate_from_dict(value)


def next_version(version: str) -> str:
    match = SEMVER.fullmatch(version)
    if match is None:
        raise ValueError(
            "governed record versions must use MAJOR.MINOR.PATCH")
    major, minor, patch = (int(part) for part in match.groups())
    return f"{major}.{minor}.{patch + 1}"


def record_and_supplied_evidence(
        record: SemanticMemoryRecord, supplied) -> tuple[str, ...]:
    stored = tuple(evidence.ref for evidence in record.evidence_refs)
    return clean_evidence(stored + tuple(supplied))


def prepare_staged_record(
        record: SemanticMemoryRecord,
        producer: LoopExecutionEvidence,
        evidence_refs: tuple[str, ...]) -> SemanticMemoryRecord:
    data = record.to_dict()
    data["lifecycle"] = MemoryLifecycle.CANDIDATE.value
    data["evidence_refs"] = [
        {"ref": ref, "kind": "artifact", "relationship": "supports"}
        for ref in evidence_refs]
    provenance = dict(data.get("provenance", {}))
    provenance["producer_loop_id"] = producer.loop_identity
    if not provenance.get("producer_run_id"):
        provenance["producer_run_id"] = (
            producer.initialization_event_digest)
    data["provenance"] = provenance
    return resigned(data)


def transitioned_record(
        record: SemanticMemoryRecord, target: MemoryLifecycle,
        evidence_refs: tuple[str, ...],
        **changes) -> SemanticMemoryRecord:
    if target not in TRANSITIONS.get(record.lifecycle, set()):
        raise ValueError(
            f"illegal lifecycle transition "
            f"{record.lifecycle.value} -> {target.value}")
    data = record.to_dict()
    data["identity"]["version"] = next_version(record.identity.version)
    data["lifecycle"] = target.value
    existing = tuple(
        item["ref"] for item in data.get("evidence_refs", ()))
    combined = clean_evidence(existing + tuple(evidence_refs))
    data["evidence_refs"] = [
        {"ref": ref, "kind": "artifact", "relationship": "supports"}
        for ref in combined]
    for name, value in changes.items():
        if name not in data:
            raise ValueError(f"unknown semantic record field {name!r}")
        data[name] = value
    return resigned(data)


def loop_evidence(
        loop: "Loop", *, require_accepted: bool = False
        ) -> LoopExecutionEvidence:
    """Build proof only from an actual canonical Loop and its ledger."""
    from ...loop.recursive_loop import Loop

    if not isinstance(loop, Loop):
        raise TypeError(
            "Loop evidence requires an actual canonical Loop object")
    if require_accepted and (
            not loop.is_terminal or not loop.result().accepted):
        raise ValueError(
            "governance actor Loop must have accepted its goal")
    initialization = next((
        event for event in loop.ledger.events
        if event.get("loop_id") == loop.loop_id
        and event.get("event") == "init"), None)
    if initialization is None:
        raise ValueError(
            "Loop has no definition-bound initialization event")
    event_payload = {
        "runtime_loop_id": loop.loop_id,
        "initialization": initialization,
        "definition": {
            "definition_id": loop.definition_ref.definition_id,
            "version": loop.definition_ref.version,
            "content_digest": loop.definition_ref.content_digest,
        },
    }
    init_digest = digest_mapping(event_payload)
    identity = digest_mapping({
        "runtime_loop_id": loop.loop_id,
        "initialization_event_digest": init_digest,
    })
    return LoopExecutionEvidence(
        loop_identity=f"loop:{identity}",
        runtime_loop_id=loop.loop_id,
        definition_id=loop.definition_ref.definition_id,
        definition_version=loop.definition_ref.version,
        definition_digest=loop.definition_ref.content_digest,
        role=loop.identity.role.value,
        profile_id=loop.identity.profile_id,
        relationship=loop.relationship.kind.value,
        initialization_event_digest=init_digest,
    )


def run_loop_action(
        *, objective: str, action: Callable[["Loop"], object],
        profile_id: str, role: str, effects: tuple[str, ...],
        event_kind: str, parent: "Loop | None" = None,
        ledger: "LoopLedger | None" = None,
        relationship: str = "starting") -> tuple[object, "Loop"]:
    """Run one bounded operation through the sole canonical Loop runtime."""
    from ...loop.loop_contract import contract_for_code_loop
    from ...loop.loop_role import (
        LoopRelationship, LoopRole, LoopRoleIdentity)
    from ...loop.recursive_loop import (
        Loop, LoopConfig, LoopLedger, StepOutcome)

    identity = LoopRoleIdentity(LoopRole(role), profile_id)
    config = LoopConfig(
        framework="custom", custom_steps=("execute",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), power="light",
        exit_condition="accepted_success")
    contract = contract_for_code_loop(
        objective, input_roles=("governed_request",),
        output_roles=("governed_result",), effects=effects, role=role)
    if parent is None:
        if relationship != "starting":
            raise ValueError("a parentless operation must be Starting")
        active = Loop(
            objective, config, ledger=ledger or LoopLedger(),
            contract=contract, identity=identity,
            relationship=LoopRelationship.starting())
    else:
        relationships = {
            "spawned_by": LoopRelationship.spawned_by(parent.loop_id),
            "queried_by": LoopRelationship.queried_by(parent.loop_id),
            "retrieved_by": LoopRelationship.retrieved_by(parent.loop_id),
        }
        if relationship not in relationships:
            raise ValueError(
                "spawned operation needs a typed relationship")
        active = parent.spawn(
            objective, config, contract=contract, identity=identity,
            relationship=relationships[relationship])
    holder: dict[str, object] = {}

    def handler(
            runtime: Loop, _step: str, _context: dict) -> StepOutcome:
        try:
            holder["value"] = action(runtime)
            record_operation_event(runtime, event_kind, holder["value"])
        except Exception as exc:  # noqa: BLE001
            holder["error"] = exc
            runtime.ledger.record(
                loop_id=runtime.loop_id, event="failure.detected",
                failure_kind="learning_governance_operation_failed",
                operation=event_kind, error_type=type(exc).__name__)
        return StepOutcome(
            output=(f"{event_kind}:failed" if "error" in holder
                    else f"{event_kind}:completed"),
            mode="deterministic", confidence=1.0)

    active.run(handler=handler, max_steps=1)
    if "error" in holder:
        raise holder["error"]  # type: ignore[misc]
    return holder.get("value"), active


def record_operation_event(loop: "Loop", event_kind: str, value) -> None:
    """Emit only members of the closed raw event vocabulary."""
    common = {"governance_operation": event_kind}
    if event_kind == "stage":
        loop.ledger.record(
            loop_id=loop.loop_id, event="learning_candidate_staged",
            **common)
    elif event_kind == "review":
        loop.ledger.record(
            loop_id=loop.loop_id, event="learning_candidate_validated",
            **common)
    elif event_kind in {"materialize", "recall"}:
        count = len(getattr(value, "records", ())) if value else 0
        loop.ledger.record(
            loop_id=loop.loop_id,
            event="intelligence.context.retrieved",
            selected_count=count, **common)
    else:
        loop.ledger.record(
            loop_id=loop.loop_id, event="custom", **common)


def provenance_from_dict(data: dict) -> MemoryProvenance:
    return MemoryProvenance(
        producer_origin=data.get(
            "producer_origin", "practitioner_run"),
        producer_loop_id=data.get("producer_loop_id", ""),
        producer_run_id=data.get("producer_run_id", ""),
        derivation_method=data.get("derivation_method", ""),
        source_refs=tuple(
            MemoryRef(
                ref["record_id"], ref["version"],
                MemoryType(ref["memory_type"]))
            for ref in data.get("source_refs", ())))


def candidate_from_dict(data: dict) -> SemanticMemoryRecord:
    """Rebuild a semantic candidate or governed successor."""
    identity_data = data["identity"]
    identity = MemoryIdentity(
        identity_data["record_id"], identity_data["version"],
        identity_data["content_digest"],
        MemoryType(identity_data["memory_type"]))
    evidence = tuple(
        MemoryEvidenceRef(
            item["ref"], item.get("kind", "artifact"),
            item.get("relationship", "supports"))
        for item in data.get("evidence_refs", ()))
    return SemanticMemoryRecord(
        identity=identity, subject=data["subject"],
        predicate=data["predicate"], object_value=data["object_value"],
        claim_type=data.get("claim_type", "observed"),
        scope=MemoryScope(data.get("scope", "project")),
        valid_from=data.get("valid_from", ""),
        valid_until=data.get("valid_until", ""),
        confidence=float(data.get("confidence", 1.0)),
        uncertainty=float(data.get("uncertainty", 0.0)),
        evidence_refs=evidence,
        source_episodes=tuple(data.get("source_episodes", ())),
        supporting_claims=tuple(data.get("supporting_claims", ())),
        opposing_claims=tuple(data.get("opposing_claims", ())),
        contradiction_group=data.get("contradiction_group", ""),
        supersedes=data.get("supersedes", ""),
        superseded_by=data.get("superseded_by", ""),
        retracted=bool(data.get("retracted", False)),
        lifecycle=MemoryLifecycle(data.get("lifecycle", "candidate")),
        provenance=provenance_from_dict(data.get("provenance", {})))
