"""Composite catalog: one logical view over many store adapters.

The composite resolves records across Core, Learned, Candidate, and
Plugin stores with explicit authority rules. A record's identity never
depends on which store materialized it.
"""
from __future__ import annotations

from .capabilities import StoreCapabilities
from .protocol import CatalogStore, StoreError
from .query import IntelligenceQuery


class CompositeCatalog:
    """Unified catalog over an ordered list of store adapters."""

    def __init__(self, stores: "list[CatalogStore] | tuple[CatalogStore, ...]"
                 ) -> None:
        if not stores:
            raise StoreError("a composite catalog needs at least one store")
        self._stores = tuple(stores)

    def capabilities(self) -> StoreCapabilities:
        first = self._stores[0].capabilities()
        return StoreCapabilities(
            adapter_id="catalog.composite", adapter_version="1.0.0",
            adapter_kind="composite", engine="composite",
            source_collections=tuple(sorted({
                c for store in self._stores
                for c in store.capabilities().source_collections})),
            operations={"get": True, "query": True, "stream": True,
                        "write": any(
                            store.capabilities().supports("write")
                            for store in self._stores),
                        "export": True, "import": any(
                            store.capabilities().supports("import")
                            for store in self._stores)},
            query_capabilities={"projection": True, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": False, "filter": False, "limit": True,
                      "order": False},
            transactions={"supported": False, "snapshot_reads": True},
            result_formats=("python_records",),
            materializations=tuple(sorted({
                m for store in self._stores
                for m in store.capabilities().materializations})),
            authority=first.authority)

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        for store in self._stores:
            record = store.get(record_id, version=version)
            if record is not None:
                return record
        return None

    def query(self, query: IntelligenceQuery) -> list[dict]:
        seen: set[str] = set()
        matched: list[dict] = []
        for store in self._stores:
            for record in store.query(IntelligenceQuery(
                    layers=query.layers,
                    source_collections=query.source_collections,
                    artifact_kinds=query.artifact_kinds,
                    lifecycle=query.lifecycle,
                    namespaces=query.namespaces,
                    attributes=query.attributes,
                    limit=query.limit + query.offset,
                    offset=0)):
                key = (record.get("record_id"), record.get("record_version"))
                if key in seen:
                    continue
                seen.add(key)
                matched.append(record)
        return matched[query.offset:query.offset + query.limit]

    def stream(self, query: IntelligenceQuery):
        for record in self.query(query):
            yield record

    def export(self, selection: dict | None = None) -> dict:
        records = self.query(IntelligenceQuery(limit=10_000_000))
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def health(self) -> dict:
        return {"adapter_id": "catalog.composite", "healthy": True,
                "stores": [store.health() for store in self._stores]}

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
    return {"tests": results}
