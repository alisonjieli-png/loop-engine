"""Episodic memory: bounded, time-ordered experience records.

An episode is an indexed, reviewable interpretation of Chronicle
events. The Chronicle remains authoritative; an episode preserves
exact links to source events and artifacts. Failures are first-class:
a failed episode is often more useful than a successful one.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..model.memory_type import (MemoryIdentity, MemoryProvenance,
                                 MemoryRef, MemoryScope, MemoryType,
                                 MemoryLifecycle, MemoryValidity,
                                 MemoryEvidenceRef)


@dataclass(frozen=True)
class EpisodicMemoryRecord:
    """One immutable, versioned episode."""

    identity: MemoryIdentity
    episode_kind: str
    triggering_goal: str
    run_id: str
    start_time: str = ""
    end_time: str = ""
    environment_ref: str = ""
    participating_loop_ids: tuple[str, ...] = ()
    parent_child_edges: tuple[tuple[str, str], ...] = ()
    chronicle_refs: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    memory_retrieved: tuple[MemoryRef, ...] = ()
    procedures_used: tuple[MemoryRef, ...] = ()
    outcomes: tuple[str, ...] = ()
    accepted: "bool | None" = None
    failure_classes: tuple[str, ...] = ()
    repairs: tuple[str, ...] = ()
    budget: str = ""
    actual_cost: str = ""
    exact_versions: dict = field(default_factory=dict)
    evidence_refs: tuple[MemoryEvidenceRef, ...] = ()
    summary: str = ""
    scope: MemoryScope = MemoryScope.RUN
    lifecycle: MemoryLifecycle = MemoryLifecycle.CANDIDATE
    provenance: MemoryProvenance = field(default_factory=MemoryProvenance)
    validity: MemoryValidity = field(default_factory=MemoryValidity)

    def __post_init__(self) -> None:
        if self.identity.memory_type is not MemoryType.EPISODIC:
            raise ValueError(
                "episodic records require memory_type 'episodic'")
        if self.end_time and self.start_time and \
                self.start_time > self.end_time:
            raise ValueError("episode start must not exceed end")

    def to_dict(self) -> dict:
        return {
            "identity": {
                "record_id": self.identity.record_id,
                "version": self.identity.version,
                "content_digest": self.identity.content_digest,
                "memory_type": self.identity.memory_type.value,
            },
            "episode_kind": self.episode_kind,
            "triggering_goal": self.triggering_goal,
            "run_id": self.run_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "environment_ref": self.environment_ref,
            "participating_loop_ids": list(self.participating_loop_ids),
            "parent_child_edges": list(self.parent_child_edges),
            "chronicle_refs": list(self.chronicle_refs),
            "observations": list(self.observations),
            "decisions": list(self.decisions),
            "actions": list(self.actions),
            "memory_retrieved": [r.to_dict()
                                 for r in self.memory_retrieved],
            "procedures_used": [r.to_dict() for r in self.procedures_used],
            "outcomes": list(self.outcomes),
            "accepted": self.accepted,
            "failure_classes": list(self.failure_classes),
            "repairs": list(self.repairs),
            "budget": self.budget,
            "actual_cost": self.actual_cost,
            "exact_versions": dict(self.exact_versions),
            "evidence_refs": [
                {"ref": e.ref, "kind": e.kind,
                 "relationship": e.relationship}
                for e in self.evidence_refs],
            "summary": self.summary,
            "scope": self.scope.value,
            "lifecycle": self.lifecycle.value,
        }

    def content_digest(self) -> str:
        serialized = json.dumps(self.to_dict(), sort_keys=True,
                                default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def self_test() -> dict:
    """Prove episodes preserve provenance, failures, and exact versions."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def make_episode(record_id: str, accepted) -> EpisodicMemoryRecord:
        identity = MemoryIdentity(record_id, "1.0.0", "d" * 64,
                                  MemoryType.EPISODIC)
        return EpisodicMemoryRecord(
            identity=identity,
            episode_kind="repository_migration",
            triggering_goal="migrate static_architecture to core",
            run_id="run-9",
            start_time="2026-08-26T10:00:00Z",
            end_time="2026-08-26T10:20:00Z",
            participating_loop_ids=("loop-1", "loop-2"),
            parent_child_edges=(("loop-1", "loop-2"),),
            chronicle_refs=("evt-1", "evt-2", "evt-3"),
            decisions=("use git mv",),
            actions=("mv src/loop_engine/static_architecture "
                     "src/loop_engine/core",),
            outcomes=("migration complete",),
            accepted=accepted,
            failure_classes=() if accepted else ("import_break",),
            repairs=() if accepted else ("rewrite imports",),
            exact_versions={"engine": "0.9.0"},
            summary=("successful migration" if accepted
                     else "failed migration"),
        )

    success = make_episode("mem.ep.success", True)
    failure = make_episode("mem.ep.failure", False)
    check("episode_preserves_chronicle_provenance",
          len(success.chronicle_refs) == 3
          and failure.participating_loop_ids
          == ("loop-1", "loop-2"))
    check("episode_preserves_failures",
          failure.accepted is False
          and failure.failure_classes == ("import_break",)
          and failure.repairs == ("rewrite imports",))
    check("episode_pins_exact_versions",
          success.exact_versions == {"engine": "0.9.0"})
    check("episode_digest_is_deterministic",
          success.content_digest() == success.content_digest()
          and success.content_digest() != failure.content_digest())
    try:
        EpisodicMemoryRecord(
            identity=MemoryIdentity("x", "1.0.0", "e" * 64,
                                    MemoryType.SEMANTIC),
            episode_kind="k", triggering_goal="g", run_id="r")
        check("non_episodic_identity_is_rejected", False)
    except ValueError:
        check("non_episodic_identity_is_rejected", True)
    try:
        EpisodicMemoryRecord(
            identity=MemoryIdentity("x", "1.0.0", "e" * 64,
                                    MemoryType.EPISODIC),
            episode_kind="k", triggering_goal="g", run_id="r",
            start_time="2026-08-26T11:00:00Z",
            end_time="2026-08-26T10:00:00Z")
        check("inverted_episode_interval_is_rejected", False)
    except ValueError:
        check("inverted_episode_interval_is_rejected", True)
    return {"tests": results}
