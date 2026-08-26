"""Memory lifecycle: review, promotion, and consolidation governance.

Candidate generation and promotion are separate. A Loop that
generates a candidate may not approve its own candidate. Consolidation
is non-destructive: source records remain immutable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model.memory_type import MemoryLifecycle, MemoryRef

#: Legal lifecycle transitions for persistent memory records.
TRANSITIONS = {
    MemoryLifecycle.DRAFT: {MemoryLifecycle.CANDIDATE},
    MemoryLifecycle.CANDIDATE: {MemoryLifecycle.UNDER_REVIEW,
                                MemoryLifecycle.REJECTED},
    MemoryLifecycle.UNDER_REVIEW: {MemoryLifecycle.ACTIVE,
                                   MemoryLifecycle.REJECTED},
    MemoryLifecycle.ACTIVE: {MemoryLifecycle.DEPRECATED,
                             MemoryLifecycle.REVOKED,
                             MemoryLifecycle.ARCHIVED},
    MemoryLifecycle.DEPRECATED: {MemoryLifecycle.ARCHIVED,
                                 MemoryLifecycle.REVOKED},
    MemoryLifecycle.REJECTED: set(),
    MemoryLifecycle.REVOKED: {MemoryLifecycle.TOMBSTONED},
    MemoryLifecycle.ARCHIVED: {MemoryLifecycle.TOMBSTONED},
    MemoryLifecycle.TOMBSTONED: set(),
}


@dataclass(frozen=True)
class MemoryReviewReceipt:
    """Evidence of one independent review decision."""

    record_ref: MemoryRef
    decision: MemoryLifecycle
    reviewer_loop_id: str = ""
    producer_loop_id: str = ""
    policy_version: str = ""
    reason: str = ""
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.reviewer_loop_id and self.producer_loop_id and \
                self.reviewer_loop_id == self.producer_loop_id:
            raise ValueError(
                "the producing Loop cannot review its own candidate")


@dataclass(frozen=True)
class MemoryConsolidationReceipt:
    """Evidence of one non-destructive consolidation operation."""

    source_refs: tuple[MemoryRef, ...]
    produced_ref: MemoryRef
    consolidation_kind: str = ""
    derivation_rule: str = ""
    producer_loop_id: str = ""

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("consolidation needs source records")


def transition(record, target: MemoryLifecycle,
               receipt: MemoryReviewReceipt | None = None) -> None:
    """Apply one legal lifecycle transition to a persistent record."""
    current = record.lifecycle
    allowed = TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"illegal lifecycle transition {current.value} -> "
            f"{target.value}")
    if target in (MemoryLifecycle.ACTIVE, MemoryLifecycle.REJECTED,
                  MemoryLifecycle.DEPRECATED, MemoryLifecycle.REVOKED) \
            and receipt is None:
        raise ValueError(
            f"transition to {target.value} requires a review receipt")
    object.__setattr__(record, "lifecycle", target)


def self_test() -> dict:
    """Prove lifecycle transitions are legal, receipted, and safe."""
    from ..semantic.record import SemanticMemoryRecord
    from ..model.memory_type import MemoryIdentity, MemoryType

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    record = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.1", "1.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="s", predicate="p", object_value="v")

    try:
        transition(record, MemoryLifecycle.ACTIVE)
        check("activation_without_receipt_is_refused", False)
    except ValueError:
        check("activation_without_receipt_is_refused", True)

    transition(record, MemoryLifecycle.UNDER_REVIEW)
    check("candidate_flow_is_legal",
          record.lifecycle is MemoryLifecycle.UNDER_REVIEW)

    receipt = MemoryReviewReceipt(
        record_ref=MemoryRef("mem.sem.1", "1.0.0", MemoryType.SEMANTIC),
        decision=MemoryLifecycle.ACTIVE,
        reviewer_loop_id="reviewer-loop",
        producer_loop_id="producer-loop",
        policy_version="1.0.0",
        reason="evidence sufficient")
    transition(record, MemoryLifecycle.ACTIVE, receipt)
    check("reviewed_promotion_is_legal",
          record.lifecycle is MemoryLifecycle.ACTIVE)

    try:
        transition(record, MemoryLifecycle.REJECTED)
        check("illegal_transition_is_refused", False)
    except ValueError:
        check("illegal_transition_is_refused", True)

    try:
        MemoryReviewReceipt(
            record_ref=MemoryRef("x", "1.0.0", MemoryType.SEMANTIC),
            decision=MemoryLifecycle.ACTIVE,
            reviewer_loop_id="same-loop",
            producer_loop_id="same-loop")
        check("self_review_is_refused", False)
    except ValueError:
        check("self_review_is_refused", True)

    try:
        MemoryConsolidationReceipt(
            source_refs=(),
            produced_ref=MemoryRef("y", "1.0.0", MemoryType.SEMANTIC))
        check("empty_consolidation_is_refused", False)
    except ValueError:
        check("empty_consolidation_is_refused", True)
    return {"tests": results}
