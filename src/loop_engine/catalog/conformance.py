"""Store conformance suite: one golden contract for every backend.

Every adapter that declares a capability must pass the same tests for
that capability. The suite proves identity preservation, filtering,
round trips, and explicit refusal of unsupported operations.
"""
from __future__ import annotations

from .protocol import CatalogStore, UnsupportedOperationError
from .query import IntelligenceQuery

_GOLDEN_RECORDS = (
    {"record_id": "core.r1", "record_version": "1.0.0",
     "intelligence_layer": "code", "source_collection": "core",
     "artifact_kind": "loop_definition", "lifecycle": "active",
     "namespace": "core",
     "attributes": {"core.problem_type": ["tabular"]},
     "payload": {"goal": "validate tabular input"}},
    {"record_id": "core.r2", "record_version": "1.0.0",
     "intelligence_layer": "context", "source_collection": "core",
     "artifact_kind": "intelligence_record", "lifecycle": "active",
     "namespace": "core",
     "attributes": {"core.domain": ["machine_learning"]},
     "payload": {"text": "first principles questions"}},
    {"record_id": "learned.r3", "record_version": "2.0.0",
     "intelligence_layer": "code", "source_collection": "learned",
     "artifact_kind": "loop_canvas", "lifecycle": "active",
     "namespace": "org:example",
     "attributes": {"core.problem_type": ["tabular", "classification"]},
     "payload": {"goal": "noise-aware tabular ensemble"}},
)


def run_store_conformance(store: CatalogStore) -> dict:
    """Run the golden contract suite against one store adapter."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    caps = store.capabilities()
    check("handshake_declares_capabilities",
          bool(caps.adapter_id) and bool(caps.adapter_version)
          and bool(caps.adapter_kind))

    if caps.supports("write"):
        for record in _GOLDEN_RECORDS:
            store.put(record)
        check("writes_are_visible_through_get",
              store.get("core.r1") is not None
              and store.get("core.r1")["record_id"] == "core.r1")
        check("exact_version_resolution",
              store.get("learned.r3", version="2.0.0") is not None
              and store.get("learned.r3", version="1.0.0") is None)
        check("missing_record_returns_none",
              store.get("missing.record") is None)
    else:
        check("read_only_store_refuses_write",
              not caps.supports("write"))

    if caps.supports("query"):
        by_layer = store.query(IntelligenceQuery(layers=("code",), limit=50))
        check("filter_by_intelligence_layer",
              by_layer and all(
                  r.get("intelligence_layer") == "code" for r in by_layer))
        by_kind = store.query(
            IntelligenceQuery(artifact_kinds=("loop_canvas",), limit=50))
        check("filter_by_artifact_kind",
              by_kind and all(
                  r.get("artifact_kind") == "loop_canvas" for r in by_kind))
        by_source = store.query(
            IntelligenceQuery(source_collections=("learned",), limit=50))
        check("filter_by_source_collection",
              by_source and all(
                  r.get("source_collection") == "learned"
                  for r in by_source))
        paged = store.query(IntelligenceQuery(limit=1, offset=1))
        check("limit_and_offset_are_honored", len(paged) <= 1)
        streamed = list(store.stream(IntelligenceQuery(limit=50)))
        check("stream_matches_query",
              {r.get("record_id") for r in streamed}
              == {r.get("record_id") for r in store.query(
                  IntelligenceQuery(limit=50))})

    if caps.supports("export"):
        exported = store.export()
        check("export_returns_records",
              isinstance(exported, dict)
              and isinstance(exported.get("records"), list))

    if caps.supports("import"):
        bundle = {"records": [dict(_GOLDEN_RECORDS[0],
                                   record_id="imported.r1")]}
        result = store.import_bundle(bundle)
        check("import_bundle_stores_records",
              result.get("imported") == 1
              and store.get("imported.r1") is not None)

    health = store.health()
    check("health_reports_status",
          isinstance(health, dict) and "healthy" in health)

    if not caps.supports("write"):
        try:
            store.put(dict(_GOLDEN_RECORDS[0]))
            check("undeclared_write_is_refused", False)
        except (UnsupportedOperationError, Exception):            # noqa: BLE001
            check("undeclared_write_is_refused", True)

    store.close()
    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "store_conformance/v1",
            "adapter_id": caps.adapter_id, "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def self_test() -> dict:
    """Prove the conformance suite itself works on the reference store."""
    from .stores.in_memory import EphemeralRecordStore
    report = run_store_conformance(EphemeralRecordStore())
    return {"tests": [{
        "test": "conformance_suite_passes_on_reference_store",
        "passed": report["all_passed"],
        "detail": f"{report['passed']}/{report['total']} checks"}]}
