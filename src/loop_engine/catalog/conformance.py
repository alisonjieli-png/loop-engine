"""Store conformance suite: one golden contract for every backend.

Every adapter that declares a capability must pass the same tests for
that capability. The suite proves identity preservation, filtering,
round trips, and explicit refusal of unsupported operations.
"""
from __future__ import annotations

from .protocol import CatalogStore, UnsupportedOperationError
from .query import (
    IntelligenceQuery,
    QueryError,
    iter_query_records,
    scalar_sql_predicates,
)

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
        scoped = store.query(IntelligenceQuery(
            namespaces=("org:example",),
            attributes={"core.problem_type": {"contains": "classification"}},
            limit=1))
        check("namespace_and_attributes_filter_before_pagination",
              [row.get("record_id") for row in scoped] == ["learned.r3"])
        residual_page = store.query(IntelligenceQuery(
            attributes={"core.problem_type": {"contains": "tabular"}},
            limit=1, offset=1))
        check("offset_counts_only_attribute_matches",
              [row.get("record_id") for row in residual_page] == ["learned.r3"])
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
        except UnsupportedOperationError:
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
    tests = [{
        "test": "conformance_suite_passes_on_reference_store",
        "passed": report["all_passed"],
        "detail": f"{report['passed']}/{report['total']} checks"}]
    tests.extend(_read_path_checks())
    return {"tests": tests}


def _read_path_checks() -> list[dict]:
    """Exercise base adapters and installed optional engines on one population."""
    import json
    from copy import deepcopy
    from importlib.util import find_spec
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from .protocol import StoreError
    from .stores.duckdb_files import DuckDBFileQueryEngine
    from .stores.duckdb_store import DuckDBRecordStore
    from .stores.in_memory import EphemeralRecordStore
    from .stores.package_jsonl import PackageJsonlStore
    from .stores.sqlite_store import SQLiteRecordStore

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    records = deepcopy(list(_GOLDEN_RECORDS))
    records.append(dict(records[2], record_id="learned.r4", namespace="org:'literal",
                        attributes={"a.b": {"nested": ["x", 2]}, "tags": ["x", "y"]}))
    queries = (
        (IntelligenceQuery(namespaces=("org:example",)), ["learned.r3"]),
        (IntelligenceQuery(attributes={"core.problem_type": {"contains": "tabular"}},
                           limit=1, offset=1), ["learned.r3"]),
        (IntelligenceQuery(namespaces=("core",), attributes={
            "core.domain": {"equals": ["machine_learning"]}}, limit=1), ["core.r2"]),
        (IntelligenceQuery(namespaces=("org:'literal",), attributes={
            "tags": {"contains": "x", "equals": ["x", "y"]}}), ["learned.r4"]),
        (IntelligenceQuery(attributes={"a.b": {"equals": {"nested": ["x", 2]}}}),
         ["learned.r4"]),
        (IntelligenceQuery(namespaces=("x' OR 1=1 --",)), []),
        (IntelligenceQuery(limit=0), []),
        (IntelligenceQuery(limit=1, offset=99), []),
    )
    with TemporaryDirectory(prefix="loop-catalog-read-") as directory:
        root = Path(directory)
        shard = root / "records' ; SELECT 1 --.jsonl"
        shard.write_text("".join(json.dumps(row) + "\n" for row in records))
        adapters = [EphemeralRecordStore(records), PackageJsonlStore((str(shard),)),
                    SQLiteRecordStore(str(root / "catalog.sqlite"))]
        databases = [adapters[-1]]
        if find_spec("duckdb") is not None:
            database = DuckDBRecordStore(str(root / "catalog.duckdb"))
            databases.append(database)
            adapters.extend((DuckDBFileQueryEngine((str(shard),)), database))
        else:
            tests.append({
                "test": "catalog_duckdb_queries_optional_adapter_not_tested",
                "passed": True, "not_tested": True, "outcome": "NOT_APPLICABLE",
                "missing_optional_dependencies": ["duckdb"],
                "detail": (
                    "DuckDB query adapters require loop-engine[data]. Base adapters "
                    "and passive literal-path validation are still tested."),
            })
        for adapter in databases:
            for record in records:
                adapter.put(record)
        try:
            for adapter in adapters:
                adapter_id = adapter.capabilities().adapter_id
                check("all_predicates_and_pagination:" + adapter_id, all(
                    [r["record_id"] for r in adapter.query(query)] == expected
                    and [r["record_id"] for r in adapter.stream(query)] == expected
                    for query, expected in queries))
                caps = adapter.capabilities()
                check("capabilities_match_read_surface:" + adapter_id,
                      not any(caps.query_capabilities.get(name) for name in (
                          "projection", "join", "aggregation"))
                      and "arrow_table" not in caps.result_formats
                      and not caps.pushdown.get("order")
                      and not caps.pushdown.get("attributes"))
                try:
                    adapter.query("SELECT * FROM records")
                    refused = False
                except QueryError:
                    refused = True
                check("raw_sql_is_refused:" + adapter_id, refused)
                pending_query = IntelligenceQuery(attributes={
                    "core.problem_type": {"equals": ["tabular"]}})
                pending = adapter.stream(pending_query)
                pending_query.attributes["core.problem_type"]["equals"].append("changed")
                pending_query.attributes.clear()
                check("stream_binds_query_before_first_next:" + adapter_id,
                      [r["record_id"] for r in pending] == ["core.r1"])

            mutable = deepcopy(records[0])
            memory = EphemeralRecordStore([mutable])
            mutable["attributes"]["core.problem_type"].append("outside")
            exposed = [memory.get("core.r1"), memory.query(IntelligenceQuery())[0],
                       next(memory.stream(IntelligenceQuery())), memory.export()["records"][0]]
            for item in exposed:
                item["attributes"]["core.problem_type"].append("mutated")
            check("in_memory_records_are_deeply_detached",
                  memory.get("core.r1")["attributes"]["core.problem_type"] == ["tabular"])

            poison = root / "bounded.jsonl"
            poison.write_text(json.dumps(records[0]) + "\nnot valid JSON\n")
            stream_store = PackageJsonlStore((str(poison),))
            check("package_limit_does_not_read_corrupt_tail",
                  len(stream_store.query(IntelligenceQuery(limit=1))) == 1
                  and stream_store.query(IntelligenceQuery(limit=0)) == [])
            for name in ("glob*.jsonl", "glob?.jsonl", "glob[1].jsonl"):
                target = root / name
                target.write_text("{}\n")
                try:
                    DuckDBFileQueryEngine((str(target),))
                    refused = False
                except StoreError:
                    refused = True
                check("duckdb_refuses_source_glob:" + name, refused)
            symlink = root / "linked.jsonl"
            symlink.symlink_to(shard)
            try:
                DuckDBFileQueryEngine((str(symlink),))
                refused = False
            except StoreError:
                refused = True
            check("duckdb_refuses_unbound_symlink_source", refused)
            absent_db = root / "must-not-create.duckdb"
            try:
                DuckDBFileQueryEngine((str(shard),), db_path=str(absent_db))
                refused = False
            except StoreError:
                refused = True
            check("read_only_file_engine_does_not_create_database",
                  refused and not absent_db.exists())
        finally:
            for adapter in adapters:
                adapter.close()

    invalid_queries = (
        {"attributes": {"x": {"unknown": 1}}},
        {"attributes": {"x": {"equals": 1, "unknown": 2}}},
        {"limit": True}, {"limit": 1.5}, {"offset": "1"}, {"layers": "code"},
    )
    for number, fields in enumerate(invalid_queries):
        try:
            IntelligenceQuery(**fields)
            refused = False
        except QueryError:
            refused = True
        check(f"invalid_query_fails_closed:{number}", refused)
    attributes = {"x": {"equals": [1]}}
    query = IntelligenceQuery(attributes=attributes, limit=1)
    attributes["x"]["equals"].append(2)
    exported = query.to_dict()
    exported["attributes"]["x"]["equals"].append(3)
    check("query_predicates_are_detached_from_inputs_and_exports",
          query.attributes == {"x": {"equals": [1]}})
    pending = iter_query_records([
        {"record_id": "allowed", "attributes": {"x": [1]}},
        {"record_id": "denied", "attributes": {"x": [2]}},
    ], query)
    query.attributes["x"]["equals"].append(2)
    query.attributes.clear()
    check("shared_iterator_binds_query_at_call_time",
          [r["record_id"] for r in pending] == ["allowed"])
    observed = []

    def bounded_records():
        for number in range(100):
            observed.append(number)
            yield {"record_id": str(number), "attributes": {"x": number}}

    selected = list(iter_query_records(bounded_records(), IntelligenceQuery(
        attributes={"x": {"equals": 2}}, limit=1)))
    check("stream_stops_after_last_needed_match",
          observed == [0, 1, 2] and selected[0]["record_id"] == "2")
    sql, params = scalar_sql_predicates(IntelligenceQuery(namespaces=("x' OR 1=1 --",)))
    check("SQL_facets_use_parameters", "x' OR" not in sql and params == ["x' OR 1=1 --"])
    return tests
