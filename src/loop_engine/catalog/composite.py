"""Composite catalog: one logical view over many store adapters.

The composite resolves records across Core, Learned, Candidate, and
Plugin stores with explicit authority rules. A record's identity never
depends on which store materialized it.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace

from .capabilities import StoreCapabilities
from .handshake import negotiate
from .protocol import CatalogStore, StoreError, UnsupportedOperationError
from .query import IntelligenceQuery, iter_query_records, snapshot_query


class CompositeCatalog:
    """Unified catalog over an ordered list of store adapters."""

    def __init__(self, stores: "list[CatalogStore] | tuple[CatalogStore, ...]"
                 ) -> None:
        if not stores:
            raise StoreError("a composite catalog needs at least one store")
        self._stores = tuple(stores)

    def capabilities(self) -> StoreCapabilities:
        members = [store.capabilities() for store in self._stores]
        operations = {name: all(negotiate(
            caps, required_operations=(name,)).permits(name) for caps in members)
            for name in ("get", "query", "stream")}
        operations["query"] = operations["query"] and operations["stream"]
        operations.update({"write": False, "import": False,
                           "export": operations["stream"]})
        return StoreCapabilities(
            adapter_id="catalog.composite", adapter_version="1.0.0",
            adapter_kind="composite", engine="composite",
            source_collections=tuple(sorted({
                c for store in self._stores
                for c in store.capabilities().source_collections})),
            operations=operations,
            query_capabilities={"projection": False, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": False, "filter": False, "attributes": False,
                      "limit": False, "order": False},
            transactions={"supported": False, "snapshot_reads": False},
            result_formats=("python_records",),
            materializations=tuple(sorted({
                m for store in self._stores
                for m in store.capabilities().materializations})),
            authority="derived_projection")

    def _require_read(self, operation: str) -> None:
        if not negotiate(self.capabilities(), required_operations=(operation,)).permits(operation):
            raise StoreError("composite member read compatibility is not established")

    @staticmethod
    def _record_signature(record: dict) -> str:
        try:
            encoded = json.dumps(record, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False)
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        except (TypeError, ValueError) as exc:
            raise StoreError("composite record must contain finite JSON data") from exc

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        self._require_read("get")
        selected = None
        signatures = {}
        for store in self._stores:
            record = store.get(record_id, version=version)
            if record is not None:
                if (record.get("record_id") != record_id
                        or (version is not None and record.get("record_version") != version)):
                    raise StoreError("member returned a different requested record identity")
                key = (record.get("record_id"), record.get("record_version"))
                signature = self._record_signature(record)
                if key in signatures and signatures[key] != signature:
                    raise StoreError("conflicting materializations of one record identity")
                signatures[key] = signature
                if selected is None:
                    selected = deepcopy(record)
        return selected

    def query(self, query: IntelligenceQuery) -> list[dict]:
        return list(self.stream(query))

    def _merged_records(self, query: IntelligenceQuery):
        """Refuse encountered conflicts; bounded reads do not audit unseen rows."""
        seen = {}
        for store in self._stores:
            records = iter(store.stream(replace(query, limit=None, offset=0)))
            try:
                for record in records:
                    if not query.matches(record):
                        continue
                    key = (record.get("record_id"), record.get("record_version"))
                    signature = self._record_signature(record)
                    if key in seen:
                        if seen[key] != signature:
                            raise StoreError("conflicting materializations of one record identity")
                        continue
                    seen[key] = signature
                    yield record
            finally:
                close = getattr(records, "close", None)
                if callable(close):
                    close()

    def stream(self, query: IntelligenceQuery):
        self._require_read("stream")
        query = snapshot_query(query)
        return iter_query_records(self._merged_records(query), query)

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        raise UnsupportedOperationError("composite write authority is not configured")

    def import_bundle(self, bundle: dict) -> dict:
        raise UnsupportedOperationError("composite import authority is not configured")

    def export(self, selection: dict | None = None) -> dict:
        records = self.query(IntelligenceQuery())
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def health(self) -> dict:
        states = []
        for store in self._stores:
            try:
                state = store.health()
                if not isinstance(state, dict):
                    state = {"healthy": False, "error_code": "invalid_health_response"}
            except Exception as exc:  # noqa: BLE001
                state = {"healthy": False, "error_type": type(exc).__name__}
            states.append(state)
        return {"adapter_id": "catalog.composite",
                "healthy": all(state.get("healthy") is True for state in states),
                "stores": states}

    def close(self) -> None:
        for store in self._stores:
            store.close()


def self_test() -> dict:
    """Prove the composite resolves across stores without duplicates."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from .stores.in_memory import EphemeralRecordStore
    core_store = EphemeralRecordStore()
    core_store.put({"record_id": "core.r1", "record_version": "1.0.0",
                    "intelligence_layer": "code",
                    "source_collection": "core",
                    "artifact_kind": "loop_definition", "lifecycle": "active",
                    "namespace": "core", "attributes": {}})
    learned_store = EphemeralRecordStore()
    learned_store.put({"record_id": "learned.r1", "record_version": "1.0.0",
                       "intelligence_layer": "code",
                       "source_collection": "learned",
                       "artifact_kind": "loop_canvas", "lifecycle": "active",
                       "namespace": "org:example", "attributes": {}})
    catalog = CompositeCatalog((core_store, learned_store))
    check("composite_resolves_across_stores",
          catalog.get("core.r1") is not None
          and catalog.get("learned.r1") is not None
          and catalog.get("missing") is None)
    query = IntelligenceQuery(layers=("code",), limit=10)
    check("composite_query_merges_stores",
          {r["record_id"] for r in catalog.query(query)}
          == {"core.r1", "learned.r1"})
    check("composite_health_reports_each_store",
          len(catalog.health()["stores"]) == 2)
    check("composite_does_not_advertise_write_authority",
          not catalog.capabilities().supports("write")
          and not catalog.capabilities().supports("import")
          and catalog.capabilities().authority == "derived_projection")
    left = EphemeralRecordStore([{"record_id": "same", "record_version": "1.0.0",
                                 "payload": {"value": 1}}])
    right = EphemeralRecordStore([{"record_id": "same", "record_version": "1.0.0",
                                  "payload": {"value": 2}}])
    conflict = CompositeCatalog((left, right))
    for name, operation in (("get", lambda: conflict.get("same")),
                            ("query", lambda: conflict.query(IntelligenceQuery()))):
        try:
            operation()
            refused = False
        except StoreError:
            refused = True
        check("encountered_identity_conflict_is_refused:" + name, refused)

    class Unhealthy(EphemeralRecordStore):
        def health(self):
            return {"healthy": False, "error_code": "fixture_unavailable"}

    check("composite_propagates_member_health_failure",
          not CompositeCatalog((left, Unhealthy())).health()["healthy"])

    class Unknown(EphemeralRecordStore):
        def capabilities(self):
            return replace(super().capabilities(), compatibility_verdict="unknown")

    try:
        CompositeCatalog((left, Unknown())).query(IntelligenceQuery())
        refused = False
    except StoreError:
        refused = True
    check("composite_refuses_unknown_member_compatibility", refused)
    scoped_records = [
        {"record_id": "denied", "record_version": "1.0.0", "namespace": "other",
         "attributes": {"tags": ["ok"]}},
        {"record_id": "allowed1", "record_version": "1.0.0", "namespace": "scope",
         "attributes": {"tags": ["ok"]}},
        {"record_id": "allowed2", "record_version": "1.0.0", "namespace": "scope",
         "attributes": {"tags": ["ok"]}},
    ]

    class Unfiltered(EphemeralRecordStore):
        def stream(self, query):
            return super().stream(IntelligenceQuery())

    defensive = CompositeCatalog((Unfiltered(scoped_records),))
    scoped = IntelligenceQuery(namespaces=("scope",), attributes={
        "tags": {"equals": ["ok"]}}, offset=1, limit=1)
    pending = defensive.stream(scoped)
    scoped.attributes["tags"]["equals"].append("changed")
    scoped.attributes.clear()
    check("composite_binds_and_filters_before_paging_even_for_unfiltered_member",
          [row["record_id"] for row in pending] == ["allowed2"])
    return {"tests": results}
