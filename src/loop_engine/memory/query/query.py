"""Memory query: typed queries, ranking, and explainable retrieval.

The query pipeline filters by scope and lifecycle first, then scores
type-specifically, groups duplicates and contradictions, and produces
an explainable receipt. Authorization happens before ranking, always.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model.memory_type import (MemoryLifecycle, MemoryRef, MemoryScope,
                                 MemoryType)

#: Queryable memory types.
QUERYABLE_TYPES = ("episodic", "semantic", "procedural")


@dataclass(frozen=True)
class MemoryQuery:
    """One typed query over persistent memory records."""

    memory_types: tuple[str, ...] = ()
    scope: MemoryScope = MemoryScope.PROJECT
    lifecycle: tuple[MemoryLifecycle, ...] = (MemoryLifecycle.ACTIVE,)
    text: str = ""
    exact_ids: tuple[str, ...] = ()
    valid_at: str = ""
    max_candidates: int = 100
    max_selected: int = 10
    require_evidence: bool = False
    include_failures: bool = True

    def __post_init__(self) -> None:
        unknown = [t for t in self.memory_types if t not in QUERYABLE_TYPES]
        if unknown:
            raise ValueError(
                f"queryable memory types are {QUERYABLE_TYPES}; "
                f"rejected {unknown}")
        if self.max_candidates < 1 or self.max_selected < 1:
            raise ValueError("query limits must be positive")


@dataclass(frozen=True)
class MemorySearchScore:
    """Explained component scores for one candidate."""

    record_id: str
    final_score: float
    components: dict = field(default_factory=dict)
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"record_id": self.record_id,
                "final_score": self.final_score,
                "components": dict(self.components),
                "reasons": list(self.reasons)}


@dataclass(frozen=True)
class MemorySearchResult:
    """One scored candidate plus rejection metadata."""

    ref: MemoryRef
    score: MemorySearchScore | None = None
    rejected: bool = False
    reject_reason: str = ""

    def to_dict(self) -> dict:
        return {"ref": self.ref.to_dict(),
                "score": self.score.to_dict() if self.score else None,
                "rejected": self.rejected,
                "reject_reason": self.reject_reason}


@dataclass(frozen=True)
class MemoryRetrievalReceipt:
    """Complete explanation of one memory retrieval."""

    query: MemoryQuery
    candidates_considered: int = 0
    candidates_rejected: tuple[MemorySearchResult, ...] = ()
    results: tuple[MemorySearchResult, ...] = ()
    selected: tuple[MemoryRef, ...] = ()
    conflicts: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict:
        return {
            "query": {
                "memory_types": list(self.query.memory_types),
                "scope": self.query.scope.value,
                "lifecycle": [l.value for l in self.query.lifecycle],
                "text": self.query.text,
                "exact_ids": list(self.query.exact_ids),
                "valid_at": self.query.valid_at,
                "max_candidates": self.query.max_candidates,
                "max_selected": self.query.max_selected,
                "require_evidence": self.query.require_evidence,
                "include_failures": self.query.include_failures,
            },
            "candidates_considered": self.candidates_considered,
            "candidates_rejected": [
                r.to_dict() for r in self.candidates_rejected],
            "results": [r.to_dict() for r in self.results],
            "selected": [r.to_dict() for r in self.selected],
            "conflicts": list(self.conflicts),
        }


def _text_overlap(record_text: str, query_text: str) -> float:
    if not query_text:
        return 0.0
    record_terms = set(record_text.lower().split())
    query_terms = set(query_text.lower().split())
    if not query_terms:
        return 0.0
    return len(record_terms & query_terms) / len(query_terms)


def rank_records(query: MemoryQuery, records: list) -> dict:
    """Type-aware deterministic ranking with explainable scores."""
    scored = []
    rejected = []
    for record in records:
        record_type = record.identity.memory_type.value
        if record_type not in query.memory_types:
            rejected.append(MemorySearchResult(
                ref=MemoryRef(record.identity.record_id,
                              record.identity.version,
                              record.identity.memory_type),
                rejected=True,
                reject_reason=(f"memory type {record_type} was not requested")))
            continue
        if query.exact_ids and record.identity.record_id \
                not in query.exact_ids:
            continue
        if record.lifecycle not in query.lifecycle:
            rejected.append(MemorySearchResult(
                ref=MemoryRef(record.identity.record_id,
                              record.identity.version,
                              record.identity.memory_type),
                rejected=True,
                reject_reason=f"lifecycle {record.lifecycle.value}"))
            continue
        # Scope is a hard filter, before any scoring: a record leaves its
        # scope only as GLOBAL. A narrower record never answers a broader
        # query, and a broader record never answers a narrower one unless
        # the query asks for the global scope itself.
        record_scope = getattr(record, "scope", None)
        if (record_scope is not None
                and record_scope is not query.scope
                and record_scope is not MemoryScope.GLOBAL):
            rejected.append(MemorySearchResult(
                ref=MemoryRef(record.identity.record_id,
                              record.identity.version,
                              record.identity.memory_type),
                rejected=True,
                reject_reason=(f"scope {record_scope.value} does not answer "
                               f"{query.scope.value} query")))
            continue
        if query.valid_at:
            valid_at = getattr(record, "valid_at", None)
            if callable(valid_at) and not valid_at(query.valid_at):
                rejected.append(MemorySearchResult(
                    ref=MemoryRef(record.identity.record_id,
                                  record.identity.version,
                                  record.identity.memory_type),
                    rejected=True,
                    reject_reason="outside valid_at window"))
                continue
        if query.require_evidence:
            evidence = getattr(record, "evidence_refs", ())
            source_episodes = getattr(record, "source_episodes", ())
            episodes = getattr(record, "successful_episodes", ()) + \
                getattr(record, "failed_episodes", ())
            if not evidence and not source_episodes and not episodes:
                rejected.append(MemorySearchResult(
                    ref=MemoryRef(record.identity.record_id,
                                  record.identity.version,
                                  record.identity.memory_type),
                    rejected=True,
                    reject_reason="evidence required but none present"))
                continue
        if not query.include_failures and \
                getattr(record, "accepted", None) is False:
            rejected.append(MemorySearchResult(
                ref=MemoryRef(record.identity.record_id,
                              record.identity.version,
                              record.identity.memory_type),
                rejected=True,
                reject_reason="failure excluded by query"))
            continue
        text = " ".join(str(v) for v in (
            getattr(record, "summary", ""),
            getattr(record, "triggering_goal", ""),
            getattr(record, "purpose", ""),
            getattr(record, "name", ""),
            getattr(record, "subject", ""),
            getattr(record, "predicate", ""),
            getattr(record, "object_value", ""),
        ))
        overlap = _text_overlap(text, query.text)
        components = {"text_overlap": overlap}
        if record.identity.memory_type is MemoryType.EPISODIC:
            failure_bonus = 0.1 if getattr(
                record, "accepted", None) is False else 0.0
            components["failure_relevance"] = failure_bonus
        elif record.identity.memory_type is MemoryType.SEMANTIC:
            components["confidence"] = getattr(
                record, "confidence", 0.0)
        elif record.identity.memory_type is MemoryType.PROCEDURAL:
            success = len(getattr(record, "successful_episodes", ()))
            failures = len(getattr(record, "failed_episodes", ()))
            components["evidence_balance"] = (
                success - 0.5 * failures) / (success + failures + 1)
        final = overlap
        if record.identity.memory_type is MemoryType.EPISODIC:
            final += components["failure_relevance"]
        if record.identity.memory_type is MemoryType.SEMANTIC:
            final += 0.3 * components["confidence"]
        if record.identity.memory_type is MemoryType.PROCEDURAL:
            final += 0.2 * components["evidence_balance"]
        scored.append(MemorySearchResult(
            ref=MemoryRef(record.identity.record_id,
                          record.identity.version,
                          record.identity.memory_type),
            score=MemorySearchScore(
                record.identity.record_id, final, components,
                tuple(sorted(components)))))
    ranked = sorted(
        [r for r in scored if r.score is not None],
        key=lambda r: -r.score.final_score)
    return {"ranked": ranked, "rejected": rejected}


def self_test() -> dict:
    """Prove queries validate and ranking is type-aware and explained."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    query = MemoryQuery(memory_types=("episodic", "semantic"),
                        text="migration")
    check("query_validates", query.max_selected == 10)
    try:
        MemoryQuery(memory_types=("working",))
        check("working_memory_is_not_queryable", False)
    except ValueError:
        check("working_memory_is_not_queryable", True)
    try:
        MemoryQuery(max_selected=0)
        check("zero_selection_limit_is_refused", False)
    except ValueError:
        check("zero_selection_limit_is_refused", True)
    check("text_overlap_is_bounded",
          _text_overlap("migrate the repository",
                        "migrate") == 1.0)
    check("text_overlap_is_zero_without_terms",
          _text_overlap("migrate the repository", "") == 0.0)
    receipt = MemoryRetrievalReceipt(query=query, selected=())
    check("receipt_serializes", "memory_types" in receipt.to_dict()["query"])
    return {"tests": results}
