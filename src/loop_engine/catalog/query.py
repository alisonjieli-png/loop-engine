"""Typed backend-neutral intelligence query.

The public query contract is a typed object, not a raw SQL string. The
planner compiles it to DuckDB SQL, SQLite SQL, a local scan, or a
plugin-specific query. SQL is an execution language, not the ontology.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field


class QueryError(ValueError):
    """A query is invalid or cannot be satisfied."""


_FACET_COLUMNS = (
    ("layers", "intelligence_layer"),
    ("source_collections", "source_collection"),
    ("artifact_kinds", "artifact_kind"),
    ("lifecycle", "lifecycle"),
    ("namespaces", "namespace"),
)


def _validate_attributes(attributes: object) -> None:
    if not isinstance(attributes, dict):
        raise QueryError("attributes must be a predicate mapping")
    for key, predicate in attributes.items():
        if not isinstance(key, str) or not key:
            raise QueryError("attribute keys must be non-empty strings")
        if (not isinstance(predicate, dict) or not predicate
                or set(predicate) - {"equals", "contains"}):
            raise QueryError("attribute predicates support only equals and contains")


@dataclass(frozen=True)
class IntelligenceQuery:
    """One typed query over the unified intelligence catalog."""

    layers: tuple[str, ...] = ()
    source_collections: tuple[str, ...] = ()
    artifact_kinds: tuple[str, ...] = ()
    lifecycle: tuple[str, ...] = ()
    namespaces: tuple[str, ...] = ()
    attributes: dict = field(default_factory=dict)
    limit: "int | None" = None
    offset: int = 0

    def __post_init__(self) -> None:
        if (type(self.offset) is not int or self.offset < 0
                or (self.limit is not None
                    and (type(self.limit) is not int or self.limit < 0))):
            raise QueryError("limit and offset must be non-negative integers")
        for label, _column in _FACET_COLUMNS:
            values = getattr(self, label)
            if (not isinstance(values, (tuple, list))
                    or any(not isinstance(v, str) or not v for v in values)):
                raise QueryError(f"{label} must contain non-empty strings")
            object.__setattr__(self, label, tuple(values))
        _validate_attributes(self.attributes)
        object.__setattr__(self, "attributes", deepcopy(self.attributes))

    def matches(self, record: dict) -> bool:
        """Canonical predicates; all supplied operators are conjunctive.

        As in the original reference evaluator, an absent attribute has value
        None, and equals uses Python structural equality. Contains applies to
        a collection value, not a string substring or a nested field path.
        """
        _validate_attributes(self.attributes)
        if not isinstance(record, Mapping):
            raise QueryError("catalog query records must be mappings")
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
        attributes = record.get("attributes")
        if attributes is None:
            attributes = {}
        if self.attributes and not isinstance(attributes, Mapping):
            raise QueryError("record attributes must be a mapping")
        for key, predicate in self.attributes.items():
            value = attributes.get(key)
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
            "attributes": deepcopy(self.attributes),
            "limit": self.limit,
            "offset": self.offset,
        }


def snapshot_query(query: IntelligenceQuery) -> IntelligenceQuery:
    """Validate a typed request and detach its caller-owned mutable fields."""
    if not isinstance(query, IntelligenceQuery):
        raise QueryError("catalog reads require IntelligenceQuery, not raw SQL")
    return IntelligenceQuery(**query.to_dict())


def scalar_sql_predicates(query: IntelligenceQuery) -> tuple[str, list[object]]:
    """Compile fixed facet columns only; attribute matching stays residual.

    Returned SQL never contains caller-provided values or attribute names.
    Pagination is intentionally absent: it must follow all residual filters.
    """
    query = snapshot_query(query)
    clauses, parameters = [], []
    for field_name, column in _FACET_COLUMNS:
        values = getattr(query, field_name)
        if values:
            clauses.append(column + " IN (" + ", ".join("?" for _ in values) + ")")
            parameters.extend(values)
    return (" WHERE " + " AND ".join(clauses) if clauses else "", parameters)


def iter_query_records(records: Iterable[dict], query: IntelligenceQuery
                       ) -> Iterator[dict]:
    """Bind at call time, then filter before paging and isolate results."""
    query = snapshot_query(query)
    def matched_records():
        if query.limit == 0:
            return
        skipped, emitted = 0, 0
        iterator = iter(records)
        try:
            for record in iterator:
                if not query.matches(record):
                    continue
                if skipped < query.offset:
                    skipped += 1
                    continue
                yield deepcopy(dict(record))
                emitted += 1
                if query.limit is not None and emitted >= query.limit:
                    return
        finally:
            close = getattr(iterator, "close", None)
            if callable(close):
                close()
    return matched_records()


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
