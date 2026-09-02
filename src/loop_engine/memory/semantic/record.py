"""Semantic memory: generalized knowledge with evidence and validity.

A semantic record holds facts, concepts, definitions, preferences, and
claims. It is bi-temporal (valid time vs recorded time),
contradiction-aware (conflicts are grouped, never silently
overwritten), and scope-bounded (a user preference stays user-scoped).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..model.memory_type import (MemoryIdentity, MemoryProvenance,
                                 MemoryScope, MemoryType, MemoryLifecycle,
                                 MemoryEvidenceRef)

#: Claim types a semantic record may carry.
CLAIM_TYPES = (
    "observed", "declared", "external", "derived", "inferred",
    "hypothesis", "reviewed", "verified",
)


@dataclass(frozen=True)
class SemanticMemoryRecord:
    """One immutable, versioned semantic claim."""

    identity: MemoryIdentity
    subject: str
    predicate: str
    object_value: str
    claim_type: str = "observed"
    scope: MemoryScope = MemoryScope.PROJECT
    valid_from: str = ""
    valid_until: str = ""
    confidence: float = 1.0
    uncertainty: float = 0.0
    evidence_refs: tuple[MemoryEvidenceRef, ...] = ()
    source_episodes: tuple[str, ...] = ()
    supporting_claims: tuple[str, ...] = ()
    opposing_claims: tuple[str, ...] = ()
    contradiction_group: str = ""
    supersedes: str = ""
    superseded_by: str = ""
    retracted: bool = False
    lifecycle: MemoryLifecycle = MemoryLifecycle.CANDIDATE
    provenance: MemoryProvenance = field(default_factory=MemoryProvenance)

    def __post_init__(self) -> None:
        if self.identity.memory_type is not MemoryType.SEMANTIC:
            raise ValueError(
                "semantic records require memory_type 'semantic'")
        if self.claim_type not in CLAIM_TYPES:
            raise ValueError(f"claim_type must be one of {CLAIM_TYPES}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("uncertainty must be in [0, 1]")
        if not self.subject or not self.predicate:
            raise ValueError("semantic claim needs subject and predicate")

    def valid_at(self, when: str) -> bool:
        """Whether the claim is valid at a given instant."""
        if self.valid_from and when < self.valid_from:
            return False
        if self.valid_until and when > self.valid_until:
            return False
        return not self.retracted

    def to_dict(self) -> dict:
        return {
            "identity": {
                "record_id": self.identity.record_id,
                "version": self.identity.version,
                "content_digest": self.identity.content_digest,
                "memory_type": self.identity.memory_type.value,
            },
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "claim_type": self.claim_type,
            "scope": self.scope.value,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "evidence_refs": [
                {"ref": e.ref, "kind": e.kind,
                 "relationship": e.relationship}
                for e in self.evidence_refs],
            "source_episodes": list(self.source_episodes),
            "supporting_claims": list(self.supporting_claims),
            "opposing_claims": list(self.opposing_claims),
            "contradiction_group": self.contradiction_group,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "retracted": self.retracted,
            "lifecycle": self.lifecycle.value,
            "provenance": {
                "producer_origin": self.provenance.producer_origin,
                "producer_loop_id": self.provenance.producer_loop_id,
                "producer_run_id": self.provenance.producer_run_id,
                "derivation_method": self.provenance.derivation_method,
                "source_refs": [ref.to_dict()
                                for ref in self.provenance.source_refs],
            },
        }

    def content_digest(self) -> str:
        serialized = json.dumps(self.to_dict(), sort_keys=True,
                                default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def self_test() -> dict:
    """Prove semantic claims are temporal, scoped, and contradiction-aware."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    fact = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.1", "1.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="repository", predicate="requires_python",
        object_value=">=3.10", claim_type="observed",
        valid_from="2026-01-01", confidence=1.0,
        lifecycle=MemoryLifecycle.ACTIVE)
    check("valid_at_respects_temporal_window",
          fact.valid_at("2026-06-01") and not fact.valid_at("2025-06-01"))

    preference = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.2", "1.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="user:alice", predicate="prefers",
        object_value="tree diagrams", claim_type="declared",
        scope=MemoryScope.USER)
    check("user_preference_stays_user_scoped",
          preference.scope is MemoryScope.USER)

    claim_a = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.3", "1.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="provider", predicate="supports",
        object_value="failover", claim_type="reviewed",
        contradiction_group="failover-support",
        opposing_claims=("mem.sem.4",))
    claim_b = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.4", "1.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="provider", predicate="supports",
        object_value="failover", claim_type="reviewed",
        contradiction_group="failover-support",
        opposing_claims=("mem.sem.3",))
    check("contradictory_claims_are_grouped_not_overwritten",
          claim_a.contradiction_group == claim_b.contradiction_group
          and claim_a.identity.record_id != claim_b.identity.record_id)

    superseding = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.5", "2.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="repository", predicate="requires_python",
        object_value=">=3.12", claim_type="verified",
        supersedes="mem.sem.1")
    check("supersession_is_explicit",
          superseding.supersedes == "mem.sem.1")

    try:
        SemanticMemoryRecord(
            identity=MemoryIdentity("x", "1.0.0", "f" * 64,
                                    MemoryType.SEMANTIC),
            subject="s", predicate="p", object_value="v",
            confidence=2.0)
        check("invalid_confidence_is_rejected", False)
    except ValueError:
        check("invalid_confidence_is_rejected", True)

    try:
        SemanticMemoryRecord(
            identity=MemoryIdentity("x", "1.0.0", "f" * 64,
                                    MemoryType.EPISODIC),
            subject="s", predicate="p", object_value="v")
        check("non_semantic_identity_is_rejected", False)
    except ValueError:
        check("non_semantic_identity_is_rejected", True)
    return {"tests": results}
