"""Classify external harness memory into Loop Engine intelligence candidates.

External files, summaries, skills, tools, traces, and user messages are not one
generic memory type. This bridge maps each item to one of the four existing
intelligence layers and keeps it at candidate lifecycle. It never writes an
active store or promotes a candidate.

Large or executable bodies stay behind references. Search and materialization
remain separate loops.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .intelligence_layers import LAYERS, LAYER_PUBLIC_KEY


HARNESS_MEMORY_KINDS = (
    "markdown", "skill", "summary", "prompt", "rubric",
    "tool", "script", "package", "repository", "artifact",
    "run_trace", "checkpoint", "solution", "failure", "measurement",
    "user_instruction", "user_advice", "approval", "veto")

_KIND_LAYER = {
    **{kind: "context_intelligence" for kind in
       ("markdown", "skill", "summary", "prompt", "rubric")},
    **{kind: "code_intelligence" for kind in
       ("tool", "script", "package", "repository", "artifact")},
    **{kind: "runtime_history_solution_intelligence" for kind in
       ("run_trace", "checkpoint", "solution", "failure", "measurement")},
    **{kind: "user_feedback_intelligence" for kind in
       ("user_instruction", "user_advice", "approval", "veto")},
}


class HarnessIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class HarnessMemoryItem:
    """One external item before Loop Engine classification."""

    item_id: str
    kind: str
    title: str
    source_harness: str
    raw_ref: str
    content_preview: str = ""
    version: str = "1.0.0"
    provenance: str = "external_harness"
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id or not self.title.strip() or not self.raw_ref:
            raise HarnessIntelligenceError(
                "an external memory item needs id, title, and raw_ref")
        if self.kind not in HARNESS_MEMORY_KINDS:
            raise HarnessIntelligenceError(
                f"kind must be one of {HARNESS_MEMORY_KINDS}")
        if not self.source_harness:
            raise HarnessIntelligenceError("source_harness is required")
        object.__setattr__(self, "tags", tuple(self.tags))

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps({
            "item_id": self.item_id, "kind": self.kind,
            "source_harness": self.source_harness, "raw_ref": self.raw_ref,
            "version": self.version, "preview": self.content_preview,
            "metadata": dict(self.metadata),
        }, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class HarnessIntelligenceCandidate:
    candidate_id: str
    layer: str
    item: HarnessMemoryItem
    digest: str
    lifecycle: str = "candidate"
    scope: str = "run"

    def __post_init__(self) -> None:
        if self.layer not in LAYERS:
            raise HarnessIntelligenceError(f"layer must be one of {LAYERS}")
        if self.lifecycle != "candidate":
            raise HarnessIntelligenceError(
                "external harness intelligence enters as candidate only")

    @property
    def public_layer(self) -> str:
        return LAYER_PUBLIC_KEY[self.layer]

    def to_store_record(self):
        from .store_serve import StoreRecord
        kind = {
            "context_intelligence": "context",
            "code_intelligence": "node",
            "runtime_history_solution_intelligence": "context",
            "user_feedback_intelligence": "context",
        }[self.layer]
        return StoreRecord(
            record_id=f"harness_candidate.{self.candidate_id}", kind=kind,
            title=self.item.title,
            body={
                "layer": self.layer,
                "public_layer": self.public_layer,
                "item_type": self.item.kind,
                "description": self.item.content_preview[:500],
                "raw_ref": self.item.raw_ref,
                "source": self.item.source_harness,
                "provenance": self.item.provenance,
                "version": self.item.version,
                "digest": self.digest,
                "lifecycle": "candidate",
                "scope": self.scope,
                "executable": False,
            },
            tags=("external_harness", "candidate", self.public_layer,
                  self.item.kind, *self.item.tags),
            tier="experimental")


def classify_harness_memory(item: HarnessMemoryItem
                            ) -> HarnessIntelligenceCandidate:
    layer = _KIND_LAYER[item.kind]
    candidate_id = hashlib.sha256(
        f"{item.source_harness}:{item.item_id}:{item.digest}".encode()
    ).hexdigest()[:24]
    return HarnessIntelligenceCandidate(
        candidate_id, layer, item, item.digest)


@dataclass(frozen=True)
class HarnessMemoryImportResult:
    candidates: tuple[HarnessIntelligenceCandidate, ...]
    by_layer: Mapping[str, int]
    loop_id: str


def import_harness_memory_as_loop(items: Sequence[HarnessMemoryItem], *,
                                  parent=None, ledger=None
                                  ) -> HarnessMemoryImportResult:
    """Classify external items through a deterministic Loop."""
    from ..loop.encapsulate import as_practitioner_loop

    supplied = tuple(items)

    def classify_all():
        candidates = tuple(classify_harness_memory(item) for item in supplied)
        counts = {layer: sum(candidate.layer == layer
                             for candidate in candidates) for layer in LAYERS}
        return candidates, counts

    wrapped = as_practitioner_loop(
        "classify external harness memory into intelligence candidates",
        classify_all, parent=parent, ledger=ledger)
    candidates, counts = wrapped["value"]
    return HarnessMemoryImportResult(
        candidates, counts, wrapped["loop_id"])


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    kinds = (
        ("skill", "context_intelligence"),
        ("repository", "code_intelligence"),
        ("run_trace", "runtime_history_solution_intelligence"),
        ("user_instruction", "user_feedback_intelligence"),
    )
    items = tuple(HarnessMemoryItem(
        f"item-{index}", kind, f"Example {kind}", "fixture",
        f"artifact://{kind}", content_preview="bounded preview")
                  for index, (kind, _layer) in enumerate(kinds))
    imported = import_harness_memory_as_loop(items)
    check("external_memory_is_split_across_exactly_four_existing_layers",
          tuple(candidate.public_layer for candidate in imported.candidates)
          == tuple(layer for _kind, layer in kinds)
          and all(imported.by_layer[layer] == 1 for layer in LAYERS))
    check("classification_is_itself_a_loop",
          imported.loop_id.startswith("loop"))
    records = [candidate.to_store_record()
               for candidate in imported.candidates]
    check("all_imported_items_remain_candidate_and_non_executable",
          all(record.tier == "experimental"
              and record.body["lifecycle"] == "candidate"
              and record.body["executable"] is False for record in records))
    check("bodies_remain_behind_references",
          all(record.body["raw_ref"].startswith("artifact://")
              for record in records))

    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
