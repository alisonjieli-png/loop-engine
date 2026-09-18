"""Temporal facts and the fact graph over Context Intelligence records.

A temporal fact is a typed triple with a validity interval: subject,
predicate, object, valid from, valid to, a confidence, and the source that
asserted it. Facts are catalog records with artifact kind ``temporal_fact``
in the Context Intelligence layer, so search, namespaces, and stores stay
the ones the engine already has. Nothing is deleted: superseding a fact
closes its interval and names the successor.

The graph view answers the questions a memory needs: what was true about a
subject at a time (``as_of``), what changed over time (``history``), what an
entity connects to at a time (``neighbors``), and whether two entities are
connected through valid facts (``path``).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..catalog.protocol import CatalogStore, StoreError, require_operation
from ..catalog.query import IntelligenceQuery

FACT_ARTIFACT_KIND = "temporal_fact"
FACT_LAYER = "context"
FACT_RECORD_TYPE = "temporal_fact/v1"
OPEN_END = "9999-12-31T23:59:59Z"
_TIMESTAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$")


class TemporalFactError(ValueError):
    """A fact, interval, timestamp, or graph request is invalid."""


def normalize_timestamp(value: str) -> str:
    """One canonical UTC form, second precision, so text comparison is time order."""
    match = _TIMESTAMP.fullmatch(str(value or ""))
    if match is None:
        raise TemporalFactError(f"timestamp must be ISO 8601 with a zone, got {value!r}")
    year, month, day, hour, minute, second, zone = match.groups()
    offset = timezone.utc
    if zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        hours, minutes = int(zone[1:3]), int(zone[4:6])
        offset = timezone(sign * timedelta(hours=hours, minutes=minutes))
    try:
        moment = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second),
                          tzinfo=offset)
    except ValueError as exc:
        raise TemporalFactError(f"timestamp is not a real moment: {value!r}") from exc
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class TemporalFact:
    """One asserted triple with its validity interval and provenance."""

    subject: str
    predicate: str
    object: str
    valid_from: str
    valid_to: str = OPEN_END
    confidence: float = 1.0
    source_ref: str = ""
    superseded_by: str = ""
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        for name in ("subject", "predicate", "object"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise TemporalFactError(f"a fact needs a non-empty {name}")
        object.__setattr__(self, "valid_from", normalize_timestamp(self.valid_from))
        object.__setattr__(self, "valid_to", normalize_timestamp(self.valid_to))
        if self.valid_to <= self.valid_from:
            raise TemporalFactError("valid_to must be after valid_from")
        if not (isinstance(self.confidence, (int, float)) and 0.0 <= self.confidence <= 1.0):
            raise TemporalFactError("confidence must lie in [0, 1]")
        try:
            json.dumps(self.attributes, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise TemporalFactError("attributes must be strict JSON") from exc

    @property
    def fact_id(self) -> str:
        material = json.dumps([self.subject, self.predicate, self.object, self.valid_from],
                              separators=(",", ":"))
        return "fact." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

    def valid_at(self, at: str) -> bool:
        moment = normalize_timestamp(at)
        return self.valid_from <= moment < self.valid_to

    def to_dict(self) -> dict:
        return {"record_type": FACT_RECORD_TYPE, "fact_id": self.fact_id, "subject": self.subject,
                "predicate": self.predicate, "object": self.object,
                "valid_from": self.valid_from, "valid_to": self.valid_to,
                "confidence": self.confidence, "source_ref": self.source_ref,
                "superseded_by": self.superseded_by, "attributes": dict(self.attributes)}

    def to_record(self, namespace: str, version: str = "1.0.0") -> dict:
        return {"record_id": self.fact_id, "record_version": version,
                "intelligence_layer": FACT_LAYER, "source_collection": "learned",
                "artifact_kind": FACT_ARTIFACT_KIND,
                "lifecycle": "superseded" if self.superseded_by else "active",
                "namespace": namespace,
                "attributes": {"subject": self.subject, "predicate": self.predicate,
                               "object": self.object, "valid_from": self.valid_from,
                               "valid_to": self.valid_to, "confidence": self.confidence,
                               "source_ref": self.source_ref, "superseded_by": self.superseded_by,
                               **{f"fact.{key}": value for key, value in self.attributes.items()}},
                "payload": self.to_dict()}

    @classmethod
    def from_record(cls, record: dict) -> "TemporalFact":
        payload = record.get("payload") or {}
        if payload.get("record_type") != FACT_RECORD_TYPE:
            raise TemporalFactError("not a temporal fact record")
        return cls(payload["subject"], payload["predicate"], payload["object"], payload["valid_from"],
                   payload.get("valid_to", OPEN_END), float(payload.get("confidence", 1.0)),
                   str(payload.get("source_ref") or ""), str(payload.get("superseded_by") or ""),
                   dict(payload.get("attributes") or {}))


class FactGraph:
    """Assertions, supersession, and time-aware queries over one namespace."""

    def __init__(self, store: CatalogStore, namespace: str):
        if not isinstance(namespace, str) or not namespace.strip():
            raise TemporalFactError("a fact graph needs a namespace")
        self.store = store
        self.namespace = namespace

    def _query(self, **attributes) -> IntelligenceQuery:
        return IntelligenceQuery(layers=(FACT_LAYER,), artifact_kinds=(FACT_ARTIFACT_KIND,),
                                 namespaces=(self.namespace,),
                                 attributes={key: {"equals": value} for key, value in attributes.items()})

    def facts(self, **attributes) -> list[TemporalFact]:
        records = self.store.query(self._query(**attributes))
        return sorted((TemporalFact.from_record(item) for item in records),
                      key=lambda fact: (fact.valid_from, fact.fact_id))

    def assert_fact(self, fact: TemporalFact, *, functional: bool = False) -> TemporalFact:
        """Store a fact; an identical assertion is idempotent, a conflicting one is refused.

        A fact's identity includes its object, so a predicate may hold several
        objects at once (membership). Pass ``functional=True`` for a predicate
        that holds one object at a time (a chief executive): an overlapping
        fact with a different object is then refused until it is superseded.
        """
        require_operation(self.store, "write")
        existing = self.store.get(fact.fact_id)
        if existing is not None:
            stored = TemporalFact.from_record(existing)
            if stored == fact:
                return stored
            raise TemporalFactError(f"fact {fact.fact_id} already exists with different content")
        if functional:
            for other in self.facts(subject=fact.subject, predicate=fact.predicate):
                overlap = other.valid_from < fact.valid_to and fact.valid_from < other.valid_to
                if other.object != fact.object and overlap:
                    raise TemporalFactError(
                        f"functional predicate {fact.predicate!r} already holds {other.object!r} "
                        f"over an overlapping interval; supersede it first")
        self.store.put(fact.to_record(self.namespace))
        return fact

    def supersede(self, fact: TemporalFact, successor: TemporalFact) -> tuple[TemporalFact, TemporalFact]:
        """Close ``fact`` at the successor's start and store the successor."""
        if fact.subject != successor.subject or fact.predicate != successor.predicate:
            raise TemporalFactError("a successor keeps the subject and predicate")
        if successor.valid_from <= fact.valid_from:
            raise TemporalFactError("a successor starts after the fact it replaces")
        stored = self.store.get(fact.fact_id)
        if stored is None:
            raise TemporalFactError("only a stored fact can be superseded")
        current = TemporalFact.from_record(stored)
        if current.superseded_by:
            raise TemporalFactError(f"fact {fact.fact_id} is already superseded by {current.superseded_by}")
        added = self.assert_fact(successor)
        closed = TemporalFact(current.subject, current.predicate, current.object, current.valid_from,
                              successor.valid_from, current.confidence, current.source_ref,
                              added.fact_id, current.attributes)
        self.store.put(closed.to_record(self.namespace, "1.1.0"),
                       precondition={"record_version": stored["record_version"]})
        return closed, added

    def as_of_all(self, subject: str, predicate: str, at: str) -> list[TemporalFact]:
        """Every fact valid at ``at``, most recently started first, then most confident."""
        valid = [fact for fact in self.facts(subject=subject, predicate=predicate) if fact.valid_at(at)]
        return sorted(valid, key=lambda fact: (fact.valid_from, fact.confidence, fact.fact_id), reverse=True)

    def as_of(self, subject: str, predicate: str, at: str) -> TemporalFact | None:
        """The single best fact valid at ``at``, or None; use ``as_of_all`` for a multi-valued predicate."""
        valid = self.as_of_all(subject, predicate, at)
        return valid[0] if valid else None

    def history(self, subject: str, predicate: str) -> list[TemporalFact]:
        return self.facts(subject=subject, predicate=predicate)

    def neighbors(self, entity: str, at: str | None = None) -> list[dict]:
        """Every fact touching the entity, as directed edges, valid at ``at`` when given."""
        edges = []
        for direction, key in (("out", "subject"), ("in", "object")):
            for fact in self.facts(**{key: entity}):
                if at is not None and not fact.valid_at(at):
                    continue
                edges.append({"direction": direction, "fact_id": fact.fact_id,
                              "subject": fact.subject, "predicate": fact.predicate,
                              "object": fact.object, "confidence": fact.confidence})
        return sorted(edges, key=lambda edge: (edge["direction"], edge["predicate"], edge["fact_id"]))

    def path(self, start: str, goal: str, at: str, *, max_depth: int = 4) -> list[str] | None:
        """Entities from start to goal through facts valid at ``at``, or None."""
        if max_depth < 1:
            raise TemporalFactError("max_depth must be at least 1")
        frontier = [(start, [start])]
        seen = {start}
        while frontier:
            entity, route = frontier.pop(0)
            if len(route) > max_depth + 1:
                continue
            for edge in self.neighbors(entity, at):
                other = edge["object"] if edge["direction"] == "out" else edge["subject"]
                if other == goal:
                    return [*route, other]
                if other not in seen:
                    seen.add(other)
                    frontier.append((other, [*route, other]))
        return None


def self_test() -> dict:
    """Assertion, supersession, as-of, history, neighbors, and paths are time-aware."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except (TemporalFactError, StoreError):
            return True
        return False

    from ..catalog.stores.in_memory import EphemeralRecordStore
    check("timestamps_normalize_to_utc_seconds_and_refuse_bad_forms",
          normalize_timestamp("2026-09-18T10:00:00+02:00") == "2026-09-18T08:00:00Z"
          and normalize_timestamp("2026-09-18T10:00:00.250Z") == "2026-09-18T10:00:00Z"
          and refuses(lambda: normalize_timestamp("2026-09-18"))
          and refuses(lambda: normalize_timestamp("2026-13-01T00:00:00Z")))
    graph = FactGraph(EphemeralRecordStore(), "org:example")
    ceo_2020 = TemporalFact("acme", "chief_executive", "alice", "2020-01-01T00:00:00Z", source_ref="filing:2020")
    graph.assert_fact(ceo_2020)
    mallory = TemporalFact("acme", "chief_executive", "mallory", "2020-01-01T00:00:00Z")
    changed = TemporalFact("acme", "chief_executive", "alice", "2020-01-01T00:00:00Z", confidence=0.5)
    check("an_identical_assertion_is_idempotent_and_conflicting_ones_are_refused",
          graph.assert_fact(ceo_2020) == ceo_2020
          and refuses(lambda: graph.assert_fact(changed))
          and refuses(lambda: graph.assert_fact(mallory, functional=True))
          and graph.store.get(mallory.fact_id) is None)
    graph.assert_fact(TemporalFact("acme", "member_of", "chamber", "2020-01-01T00:00:00Z"))
    graph.assert_fact(TemporalFact("acme", "member_of", "guild", "2020-01-01T00:00:00Z"))
    check("a_multi_valued_predicate_holds_several_objects_and_as_of_all_lists_them",
          [fact.object for fact in graph.as_of_all("acme", "member_of", "2021-01-01T00:00:00Z")]
          == sorted(["chamber", "guild"], key=lambda name: TemporalFact("acme", "member_of", name,
                                                                        "2020-01-01T00:00:00Z").fact_id,
                    reverse=True)
          and len(graph.history("acme", "member_of")) == 2)
    closed, added = graph.supersede(ceo_2020, TemporalFact("acme", "chief_executive", "bob",
                                                          "2024-06-01T00:00:00Z", confidence=0.9,
                                                          source_ref="filing:2024"))
    check("supersession_closes_the_old_interval_and_names_the_successor",
          closed.valid_to == "2024-06-01T00:00:00Z" and closed.superseded_by == added.fact_id
          and graph.store.get(closed.fact_id)["lifecycle"] == "superseded"
          and refuses(lambda: graph.supersede(ceo_2020, TemporalFact("acme", "chief_executive", "carol",
                                                                     "2025-01-01T00:00:00Z"))))
    check("as_of_returns_the_fact_valid_at_a_time_and_not_its_successor",
          graph.as_of("acme", "chief_executive", "2022-03-03T00:00:00Z").object == "alice"
          and graph.as_of("acme", "chief_executive", "2024-06-01T00:00:00Z").object == "bob"
          and [fact.object for fact in graph.as_of_all("acme", "chief_executive", "2025-01-01T00:00:00Z")] == ["bob"]
          and [fact.object for fact in graph.as_of_all("acme", "chief_executive", "2022-01-01T00:00:00Z")] == ["alice"]
          and graph.as_of("acme", "chief_executive", "2019-01-01T00:00:00Z") is None
          and [fact.object for fact in graph.history("acme", "chief_executive")] == ["alice", "bob"])
    graph.assert_fact(TemporalFact("alice", "member_of", "board", "2018-01-01T00:00:00Z"))
    graph.assert_fact(TemporalFact("bob", "member_of", "board", "2024-06-01T00:00:00Z"))
    check("neighbors_and_paths_respect_validity",
          {edge["object"] for edge in graph.neighbors("acme", "2022-01-01T00:00:00Z")} == {"alice", "chamber", "guild"}
          and {edge["object"] for edge in graph.neighbors("acme", "2025-01-01T00:00:00Z")} == {"bob", "chamber", "guild"}
          and [edge["direction"] for edge in graph.neighbors("board")] == ["in", "in"]
          and graph.path("acme", "board", "2022-01-01T00:00:00Z") == ["acme", "alice", "board"]
          and graph.path("acme", "board", "2025-01-01T00:00:00Z") == ["acme", "bob", "board"]
          and graph.path("acme", "nowhere", "2025-01-01T00:00:00Z") is None
          and refuses(lambda: graph.path("acme", "board", "2025-01-01T00:00:00Z", max_depth=0)))
    check("facts_refuse_bad_intervals_confidence_and_empty_parts",
          refuses(lambda: TemporalFact("a", "b", "c", "2026-01-01T00:00:00Z", "2025-01-01T00:00:00Z"))
          and refuses(lambda: TemporalFact("a", "b", "c", "2026-01-01T00:00:00Z", confidence=1.5))
          and refuses(lambda: TemporalFact("", "b", "c", "2026-01-01T00:00:00Z"))
          and refuses(lambda: FactGraph(EphemeralRecordStore(), ""))
          and TemporalFact.from_record(ceo_2020.to_record("org:example")) == ceo_2020)
    other = FactGraph(graph.store, "org:other")
    check("namespaces_separate_graphs_in_one_store",
          other.as_of("acme", "chief_executive", "2022-03-03T00:00:00Z") is None
          and other.neighbors("acme") == [])
    passed = sum(item["passed"] for item in results)
    return {"record_type": "temporal_facts_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
