"""Typed backend-neutral intelligence query.

The public query contract is a typed object, not a raw SQL string. The
planner compiles it to DuckDB SQL, SQLite SQL, a local scan, or a
plugin-specific query. SQL is an execution language, not the ontology.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class QueryError(ValueError):
    """A query is invalid or cannot be satisfied."""


@dataclass(frozen=True)
class IntelligenceQuery:
    """One typed query over the unified intelligence catalog."""

    layers: tuple[str, ...] = ()
    source_collections: tuple[str, ...] = ()
    artifact_kinds: tuple[str, ...] = ()
    lifecycle: tuple[str, ...] = ()
    namespaces: tuple[str, ...] = ()
    attributes: dict = field(default_factory=dict)
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 0 or self.offset < 0:
            raise QueryError("limit and offset cannot be negative")
        for label, values in (("layers", self.layers),
                              ("source_collections", self.source_collections),
                              ("artifact_kinds", self.artifact_kinds),
                              ("lifecycle", self.lifecycle),
                              ("namespaces", self.namespaces)):
            if any(not isinstance(v, str) or not v for v in values):
                raise QueryError(f"{label} must contain non-empty strings")
        for key, predicate in self.attributes.items():
            if not isinstance(key, str) or not key:
                raise QueryError("attribute keys must be non-empty strings")
            if not isinstance(predicate, dict) or not predicate:
                raise QueryError(
                    f"attribute {key!r} needs a predicate mapping")

    def matches(self, record: dict) -> bool:
        """Client-side predicate evaluation for stores without pushdown."""
        if self.layers and record.get("intelligence_layer") not in self.layers:
            return False
        if self.source_collections and record.get(
                "source_collection") not in self.source_collections:
            return False
        if self.artifact_kinds and record.get(
                "artifact_kind") not in self.artifact_kinds:
            return False
        if self.lifecycle and record.get("lifecycle") not in self.lifecycle:
            return False
        if self.namespaces and record.get("namespace") not in self.namespaces:
            return False
        for key, predicate in self.attributes.items():
            value = record.get("attributes", {}).get(key)
            if "equals" in predicate and value != predicate["equals"]:
                return False
            if "contains" in predicate:
                wanted = predicate["contains"]
                if not isinstance(value, (list, tuple, set)) \
                        or wanted not in value:
                    return False
        return True

    def to_dict(self) -> dict:
        return {
            "layers": list(self.layers),
            "source_collections": list(self.source_collections),
            "artifact_kinds": list(self.artifact_kinds),
            "lifecycle": list(self.lifecycle),
            "namespaces": list(self.namespaces),
            "attributes": self.attributes,
            "limit": self.limit,
            "offset": self.offset,
        }


def self_test() -> dict:
    """Prove the typed query model validates and filters correctly."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    query = IntelligenceQuery(
        layers=("code",),
        source_collections=("core", "learned"),
        artifact_kinds=("loop_definition", "loop_canvas"),
        attributes={"core.problem_type": {"contains": "tabular"}},
        limit=50)
    hit = {
        "intelligence_layer": "code", "source_collection": "learned",
        "artifact_kind": "loop_canvas", "lifecycle": "active",
        "namespace": "org:example",
        "attributes": {"core.problem_type": ["tabular", "classification"]},
    }
    miss_layer = dict(hit, intelligence_layer="context")
    miss_kind = dict(hit, artifact_kind="contract")
    miss_attr = dict(hit, attributes={"core.problem_type": ["image"]})
    check("typed_query_matches_relevant_records",
          query.matches(hit) and not query.matches(miss_layer)
          and not query.matches(miss_kind) and not query.matches(miss_attr))
    try:
        IntelligenceQuery(limit=-1)
        check("negative_limit_is_refused", False)
    except QueryError:
        check("negative_limit_is_refused", True)
    try:
        IntelligenceQuery(attributes={"core.x": {}})
        check("empty_predicate_is_refused", False)
    except QueryError:
        check("empty_predicate_is_refused", True)
    return {"tests": results}
