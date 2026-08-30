"""In-memory memory store: deterministic local reference implementation.

This store holds persistent memory records (episodic, semantic,
procedural) behind the common query pipeline. It is the reference
backend for tests and small runs. Durable backends implement the same
semantics.
"""
from __future__ import annotations

from ..model.memory_type import (MemoryIdentity, MemoryLifecycle,
                                 MemoryScope, MemoryType)
from ..query.query import (MemoryQuery, MemoryRetrievalReceipt,
                           rank_records)


class InMemoryMemoryStore:
    """Deterministic in-process store for persistent memory records."""

    def __init__(self, records: list = ()) -> None:
        self._records: dict[str, list] = {}
        for record in records:
            self.put(record)

    def put(self, record) -> None:
        """Append one immutable record version."""
        identity = record.identity
        versions = self._records.setdefault(identity.record_id, [])
        for existing in versions:
            if existing.identity.version == identity.version:
                if existing.content_digest() != record.content_digest():
                    raise ValueError(
                        f"conflicting content for {identity.record_id} "
                        f"version {identity.version}")
                return
        versions.append(record)

    def get(self, record_id: str, version: str | None = None):
        versions = self._records.get(record_id, [])
        for record in versions:
            if version is None or record.identity.version == version:
                return record
        return None

    def list_versions(self, record_id: str) -> list[str]:
        return [r.identity.version
                for r in self._records.get(record_id, [])]

    def query(self, query: MemoryQuery) -> MemoryRetrievalReceipt:
        """Query with authorization-first filtering and explanation."""
        candidates = [
            record for versions in self._records.values()
            for record in versions]
        ranked = rank_records(query, candidates)
        results = (ranked["ranked"] if query.max_selected is None
                   else ranked["ranked"][:query.max_selected])
        selected = tuple(r.ref for r in results)
        conflicts = _detect_conflicts(results)
        return MemoryRetrievalReceipt(
            query=query,
            candidates_considered=len(candidates),
            candidates_rejected=tuple(ranked["rejected"]),
            results=tuple(results),
            selected=selected,
            conflicts=tuple(conflicts))


def _detect_conflicts(results: list) -> list[tuple[str, str]]:
    """Group semantic claims that share a contradiction group."""
    groups: dict[str, list[str]] = {}
    for result in results:
        record = getattr(result, "record", None)
        group = getattr(record, "contradiction_group", "") or ""
        if group:
            groups.setdefault(group, []).append(result.ref.record_id)
    return [tuple(ids) for ids in groups.values() if len(ids) > 1]


def self_test() -> dict:
    """Prove the store is deterministic, conflict-safe, and queryable."""
    from ..semantic.record import SemanticMemoryRecord
    from ..procedural.record import ProceduralMemoryRecord
    from ..episodic.record import EpisodicMemoryRecord

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    semantic = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.1", "1.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="repository", predicate="requires_python",
        object_value=">=3.10", claim_type="observed",
        confidence=1.0, lifecycle=MemoryLifecycle.ACTIVE)
    procedure = ProceduralMemoryRecord(
        identity=MemoryIdentity("mem.proc.1", "1.0.0", "a" * 64,
                                MemoryType.PROCEDURAL),
        name="repository-migration",
        purpose="migrate package paths safely",
        applicability="engine=0.9.0",
        lifecycle=MemoryLifecycle.ACTIVE)
    episode = EpisodicMemoryRecord(
        identity=MemoryIdentity("mem.ep.1", "1.0.0", "d" * 64,
                                MemoryType.EPISODIC),
        episode_kind="migration", triggering_goal="migrate packages",
        run_id="run-1", accepted=False, failure_classes=("import_break",),
        lifecycle=MemoryLifecycle.ACTIVE)

    store = InMemoryMemoryStore([semantic, procedure, episode])
    check("store_resolves_exact_versions",
          store.get("mem.sem.1", "1.0.0") is semantic
          and store.get("mem.sem.1", "9.9.9") is None
          and store.get("missing") is None)
    check("store_lists_versions",
          store.list_versions("mem.sem.1") == ["1.0.0"])

    query = MemoryQuery(memory_types=("episodic",), text="migrate",
                        scope=MemoryScope.RUN)
    receipt = store.query(query)
    check("query_selects_relevant_records",
          receipt.selected and receipt.selected[0].record_id
          == "mem.ep.1")
    check("receipt_explains_rejections",
          len(receipt.candidates_rejected) == 2
          and receipt.candidates_considered == 3
          and all("memory type" in item.reject_reason
                  for item in receipt.candidates_rejected))

    evidence_query = MemoryQuery(memory_types=("semantic",),
                                 require_evidence=True)
    evidence_receipt = store.query(evidence_query)
    check("evidence_requirement_filters_unsupported_records",
          len(evidence_receipt.selected) == 0
          and any("evidence required" in r.reject_reason
                  for r in evidence_receipt.candidates_rejected))

    try:
        conflicting = SemanticMemoryRecord(
            identity=MemoryIdentity("mem.sem.1", "1.0.0", "e" * 64,
                                    MemoryType.SEMANTIC),
            subject="repository", predicate="requires_python",
            object_value=">=3.12", claim_type="observed")
        store.put(conflicting)
        check("conflicting_immutable_version_is_rejected", False)
    except ValueError:
        check("conflicting_immutable_version_is_rejected", True)
    return {"tests": results}
