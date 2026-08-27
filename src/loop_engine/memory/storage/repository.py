"""Durable local candidate store for learning records.

Candidates are staged persistent memory records awaiting independent
review. This module is the smallest honest local storage profile for
them: an append-only JSONL journal under ``~/.loop-engine/memory/``.
It shares the in-memory store's semantics for query by delegating to
:class:`InMemoryMemoryStore`. Promotion is never performed by this
store; independent review happens elsewhere.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from ..model.memory_type import (MemoryEvidenceRef, MemoryIdentity,
                                 MemoryLifecycle, MemoryProvenance,
                                 MemoryScope, MemoryType)
from ..query.query import MemoryQuery, MemoryRetrievalReceipt
from ..semantic.record import SemanticMemoryRecord
from .store import InMemoryMemoryStore


def default_memory_root() -> Path:
    """The durable local memory journal root."""
    root = os.environ.get("LOOP_ENGINE_MEMORY_DIR", "")
    if root:
        return Path(root).expanduser().resolve()
    return (Path(os.path.expanduser("~"))
            / ".loop-engine" / "memory")


class CandidateJournal:
    """Append-only JSONL journal of staged semantic candidates.

    Each line is one immutable semantic candidate record envelope.
    Reading the journal reconstructs an in-memory store so queries
    share the canonical ranking pipeline. Candidate-only: records read
    back are filtered to lifecycle ``candidate``.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_memory_root()).expanduser().resolve()
        self.journal = self.root / "candidates.jsonl"

    def _ensure_dir(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def stage(self, record: SemanticMemoryRecord) -> str:
        """Append one candidate record. Returns the record identity."""
        if record.lifecycle is not MemoryLifecycle.CANDIDATE:
            raise ValueError("only candidate records may be staged here")
        self._ensure_dir()
        line = json.dumps(record.to_dict(), sort_keys=True, default=str)
        with self.journal.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return record.identity.record_id

    def _read_all(self) -> list[SemanticMemoryRecord]:
        records: list[SemanticMemoryRecord] = []
        if not self.journal.is_file():
            return records
        with self.journal.open(encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                records.append(candidate_from_dict(json.loads(raw)))
        return records

    def as_store(self) -> InMemoryMemoryStore:
        """Materialize the journal into an in-memory store."""
        return InMemoryMemoryStore(self._read_all())

    def list_candidates(self) -> list[dict]:
        """Return a summary of every recorded candidate."""
        return [
            {
                "record_id": record.identity.record_id,
                "version": record.identity.version,
                "subject": record.subject,
                "predicate": record.predicate,
                "claim_type": record.claim_type,
                "lifecycle": record.lifecycle.value,
            }
            for record in self._read_all()
            if record.lifecycle is MemoryLifecycle.CANDIDATE
        ]

    def query(self, query: MemoryQuery) -> MemoryRetrievalReceipt:
        return self.as_store().query(query)


def candidate_from_dict(data: dict) -> SemanticMemoryRecord:
    """Rebuild a semantic candidate from its stored envelope."""
    identity_data = data["identity"]
    identity = MemoryIdentity(
        identity_data["record_id"], identity_data["version"],
        identity_data["content_digest"],
        MemoryType(identity_data["memory_type"]))
    evidence = tuple(MemoryEvidenceRef(e["ref"], e.get("kind", "artifact"),
                                       e.get("relationship", "supports"))
                     for e in data.get("evidence_refs", []))
    return SemanticMemoryRecord(
        identity=identity,
        subject=data["subject"],
        predicate=data["predicate"],
        object_value=data["object_value"],
        claim_type=data.get("claim_type", "observed"),
        scope=MemoryScope(data.get("scope", "project")),
        valid_from=data.get("valid_from", ""),
        valid_until=data.get("valid_until", ""),
        confidence=data.get("confidence", 1.0),
        uncertainty=data.get("uncertainty", 0.0),
        evidence_refs=evidence,
        source_episodes=tuple(data.get("source_episodes", [])),
        supporting_claims=tuple(data.get("supporting_claims", [])),
        opposing_claims=tuple(data.get("opposing_claims", [])),
        contradiction_group=data.get("contradiction_group", ""),
        supersedes=data.get("supersedes", ""),
        superseded_by=data.get("superseded_by", ""),
        retracted=bool(data.get("retracted", False)),
        lifecycle=MemoryLifecycle(data.get("lifecycle", "candidate")),
        provenance=MemoryProvenance())


def self_test() -> dict:
    """Prove durable staging and honest read-back of candidates."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        journal = CandidateJournal(Path(tmp))
        record = SemanticMemoryRecord(
            identity=MemoryIdentity("candidate.test.1", "1.0.0", "b" * 64,
                                    MemoryType.SEMANTIC),
            subject="demo", predicate="produced",
            object_value="a lesson", claim_type="derived",
            lifecycle=MemoryLifecycle.CANDIDATE)
        journal.stage(record)
        listed = journal.list_candidates()
        check("staged_candidate_is_durable",
              listed and listed[0]["record_id"] == "candidate.test.1")
        receipt = journal.as_store().query(
            MemoryQuery(memory_types=("semantic",),
                        lifecycle=(MemoryLifecycle.CANDIDATE,)))
        check("staged_candidate_is_queryable",
              any(r.record_id == "candidate.test.1"
                  for r in receipt.selected))
        # A default-profile query must hide candidates.
        default_receipt = journal.as_store().query(
            MemoryQuery(memory_types=("semantic",)))
        check("default_query_hides_candidates",
              len(default_receipt.selected) == 0,
              "candidates are not active intelligence")
        active = SemanticMemoryRecord(
            identity=MemoryIdentity("x", "1.0.0", "c" * 64,
                                    MemoryType.SEMANTIC),
            subject="a", predicate="b", object_value="c",
            lifecycle=MemoryLifecycle.ACTIVE)
        try:
            journal.stage(active)
            check("non_candidate_is_rejected", False)
        except ValueError:
            check("non_candidate_is_rejected", True)
    return {"tests": results}
