"""Read-only architecture probes using memory and mocked export execution.

Run from the repository: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3
artifacts/architecture-audit-2026-09-19/intelligence-storage-probes.py

No files are created by this script. Export filesystem access and subprocess
execution are replaced with local fakes. Candidate invocation runs only a
literal, supplied lambda that returns an integer. No model or network call runs.
These are diagnostic observations, not product acceptance tests.
"""
from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from unittest.mock import patch

from loop_engine.catalog.capabilities import StoreCapabilities
from loop_engine.catalog.handshake import negotiate
from loop_engine.catalog.protocol import require_operation
from loop_engine.catalog.stores.in_memory import EphemeralRecordStore
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.catalog.versioning import content_digest, revise, version_record
from loop_engine.code_nodes import solution_export
from loop_engine.code_nodes.solutions_space import (
    SolutionsSpaceRecord,
    solutions_space_from_adaptive,
)
from loop_engine.core.code_intelligence_assets import (
    CodeRefExecutionRequest,
    code_asset_capsule,
    execute_code_ref,
    spec_from_template,
)
from loop_engine.core.facets import FacetFilter
from loop_engine.core.intelligence_layers import (
    IntelligenceSearchRequest,
    query_intelligence,
)
from loop_engine.core.retrieval import Retriever
from loop_engine.core.shared_memory_scopes import SharedMemory, SharedMemoryScope
from loop_engine.core.store_serve import StoreRecord
from loop_engine.loop.loop_capsule import (
    ExternalPayloadRef,
    IntelligenceLoadRequest,
    MaterializedPayload,
    intelligence_package_from_record,
    load_intelligence_ref,
)
from loop_engine.memory.model.memory_type import (
    MemoryIdentity,
    MemoryLifecycle,
    MemoryType,
)
from loop_engine.memory.query.query import MemoryQuery
from loop_engine.memory.semantic.record import SemanticMemoryRecord
from loop_engine.memory.storage.store import InMemoryMemoryStore
from loop_engine.templates.library import CORE_TEMPLATES, TemplateLibrary


class RaceStore(EphemeralRecordStore):
    """Force both absence reads to complete before either creation writes."""

    def __init__(self):
        super().__init__()
        self.barrier = Barrier(2)

    def get(self, record_id, version=None):
        value = super().get(record_id, version)
        if record_id == "new" and value is None:
            self.barrier.wait(timeout=3)
        return value


class VirtualPath:
    """An in-memory export tree; it performs no real filesystem access."""

    def __init__(self, files, name=""):
        self.files = files
        self.name = name

    def __truediv__(self, name):
        return VirtualPath(self.files, self.name + ("/" if self.name else "") + str(name))

    def is_file(self):
        return self.name in self.files

    def is_dir(self):
        return False

    def exists(self):
        return self.is_file()

    def read_text(self, *args, **kwargs):
        return self.files[self.name]

    def read_bytes(self):
        return self.read_text().encode("utf-8")


def run_probes():
    observations = {}
    for name, factory in (
        ("memory", EphemeralRecordStore),
        ("sqlite", lambda: SQLiteRecordStore(":memory:")),
    ):
        store = factory()
        try:
            store.put({"record_id": "fresh", "record_version": "1.0.0"},
                      precondition={"exists": False})
            observations["absent_create_" + name] = "accepted"
        except Exception as exc:
            observations["absent_create_" + name] = type(exc).__name__
        finally:
            store.close()

    store = EphemeralRecordStore()
    row = {"record_id": "revision-case", "record_version": "1.0.0",
           "attributes": {"revision_customer_field": "keep", "ordinary": "yes"},
           "payload": {"v": 1}}
    revise(store, row, expected_version=None)
    revise(store, {**row, "record_version": "1.0.1", "payload": {"v": 2}},
           expected_version="1.0.0")
    restored = version_record(store, "revision-case", "1.0.0")
    observations["revision_attribute_preservation"] = {
        "before": row["attributes"], "restored": restored["attributes"],
        "digest_matches": content_digest(row) == content_digest(restored)}

    race = RaceStore()

    def create(writer):
        revise(race, {"record_id": "new", "record_version": "1.0.0",
                      "payload": {"writer": writer}}, expected_version=None)
        return "accepted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        observations["concurrent_revise_create"] = list(executor.map(create, [1, 2]))

    scope = SharedMemoryScope("scope", "tenant:scope", ("alice", "bob"))
    memory = SharedMemory(SQLiteRecordStore(":memory:"))
    row = {"record_id": "note", "record_version": "1.0.0", "payload": {"v": 0}}
    memory.write(scope, "alice", row, written_at="t0")
    memory.write(scope, "alice", {**row, "payload": {"v": 1}},
                 written_at="t1", expected_version="1.0.0")
    memory.write(scope, "bob", {**row, "payload": {"v": 2}},
                 written_at="t2", expected_version="1.0.0")
    observations["same_version_shared_writes"] = {
        "both_accepted": True, "final_payload": memory.store.get("note")["payload"]}
    memory.store.close()

    spec = spec_from_template(
        "pure_function", asset_id="candidate", name="candidate",
        description="candidate fixture", source_kind="local_path",
        body_ref=ExternalPayloadRef("memory://fixture", "a" * 64))
    ref = code_asset_capsule(spec).to_ref()
    executed = execute_code_ref(CodeRefExecutionRequest(
        ref, lambda _: MaterializedPayload(lambda: 7, "a" * 64)))
    observations["candidate_direct_execution"] = {
        "lifecycle": spec.lifecycle, "admission_ref": spec.admission_ref,
        "value": executed["value"]}
    changed_data = replace(spec, data_refs=(ExternalPayloadRef("memory://other", "b" * 64),))
    observations["qualification_digest_omits_data_references"] = {
        "qualification_digest_equal": spec.qualification_digest == changed_data.qualification_digest,
        "card_digest_equal": spec.card_digest == changed_data.card_digest}

    record = StoreRecord("mutable", "context", "title", body={"text": "original"})
    ref = intelligence_package_from_record(record).to_ref()
    loaded = load_intelligence_ref(IntelligenceLoadRequest(ref, lambda _: "changed"))
    observations["inline_digest_binding"] = {
        "payload_digest": ref.payload_digest, "loaded": loaded["value"]}

    layers = {layer: [StoreRecord(layer + str(index), "context", "shared keyword")
                      for index in range(3)] for layer in (
        "context_intelligence", "code_intelligence",
        "runtime_history_solution_intelligence", "user_feedback_intelligence")}
    result = query_intelligence(IntelligenceSearchRequest("shared", layers, top_n=1))
    observations["query_top_n"] = {"requested": 1, "actual": len(result["hits"])}
    records = [StoreRecord("bad" + str(index), "context", "shared",
                           body={"facets": {"scope": "blocked"}}) for index in range(3)]
    records.append(StoreRecord("allowed", "context", "shared",
                               body={"facets": {"scope": "allowed"}}))
    result = Retriever(records).search(
        "shared", mode="lexical", top_n=1, flt=FacetFilter(require={"scope": "allowed"}))
    observations["postfilter_candidate_starvation"] = {
        "available_matching_record": "allowed", "hits": result["hits"]}

    class StringFlagStore(EphemeralRecordStore):
        def capabilities(self):
            return StoreCapabilities("fixture", "1.0.0", "in_memory",
                                     operations={"write": "false"})

    string_store = StringFlagStore()
    require_operation(string_store, "write")
    observations["capability_gate_disagreement"] = {
        "require_operation_permitted": True,
        "handshake_permitted": negotiate(string_store.capabilities()).permits("write")}

    claims = [SemanticMemoryRecord(
        MemoryIdentity("claim" + str(index), "1.0.0", "a" * 64, MemoryType.SEMANTIC),
        "supplier", "status", value, contradiction_group="supplier-status",
        lifecycle=MemoryLifecycle.ACTIVE) for index, value in enumerate(("open", "closed"))]
    result = InMemoryMemoryStore(claims).query(MemoryQuery(memory_types=("semantic",)))
    observations["memory_conflicts"] = {
        "selected": len(result.selected), "conflicts": list(result.conflicts)}

    template = CORE_TEMPLATES[0]
    changed = replace(template, input_contract="different/v1", maturity="deprecated")
    library = TemplateLibrary()
    library.register(changed)
    observations["template_contract_identity"] = {
        "digest_equal": template.content_digest() == changed.content_digest(),
        "registration_rejected": False,
        "stored_contract": library.get(template.template_id).input_contract,
        "stored_maturity": library.get(template.template_id).maturity}

    canvas = {"candidate_id": "candidate", "graph_digest": "g" * 64}
    space = solutions_space_from_adaptive("t" * 64, {
        "solved": True, "candidate_solution_canvases": [canvas],
        "selected_solution_canvas": canvas,
        "independent_verification_records": [{"status": "passed", "report_digest": "unrelated"}]})
    wire = space.to_dict()
    wire["content_digest"] = "incorrect"
    restored_space = SolutionsSpaceRecord.from_dict(wire)
    observations["solution_projection_trust"] = {
        "status_from_unbound_report": space.members[0].status,
        "report_digest": space.members[0].verification_report_digest,
        "wrong_serialized_digest_accepted": len(restored_space.members) == 1}

    export_spec = solution_export.SolutionExportSpec(
        "fixture", "1.0.0", "fixture", (solution_export.ExportedFile("__init__.py", ""),))
    changed_export = replace(export_spec, container=solution_export.ContainerSpec(arguments=("different",)))
    observations["export_spec_identity"] = {
        "digest_equal": export_spec.digest == changed_export.digest,
        "rendered_job_equal": solution_export.render_kubernetes_job(export_spec)
        == solution_export.render_kubernetes_job(changed_export)}

    captured = []

    def fake_runner(root, isolation, code, timeout):
        captured.append({"isolation": isolation, "code": code})
        return subprocess.CompletedProcess([], 0, "ok\n", "")

    manifest = {"package_name": "json; audit_marker = True #", "isolation": "unknown",
                "manifest_digest": "unverified", "files": {"../outside.py": "0" * 64}}
    files = {"MANIFEST.json": json.dumps(manifest), "../outside.py": "# harmless fixture\n"}
    with patch.object(solution_export, "Path", lambda _: VirtualPath(files)), \
            patch.object(solution_export, "_run_isolated", fake_runner):
        result = solution_export.verify_export("virtual")
    observations["export_verifier_control_flow_mocked"] = {
        "real_subprocesses_run": 0, "real_files_read": 0,
        "digest_check_passed": result.checks[0]["passed"],
        "runner_calls_despite_failed_integrity": len(captured),
        "unvalidated_package_in_generated_code": "audit_marker = True" in captured[0]["code"],
        "unvalidated_isolation_forwarded": captured[0]["isolation"],
        "returned_unverified_manifest_digest": result.manifest_digest}
    return {"record_type": "intelligence_storage_diagnostic_observations/v1",
            "probes_are_not_acceptance_tests": True,
            "external_calls": 0, "untrusted_export_execution": False,
            "observations": observations}


if __name__ == "__main__":
    print(json.dumps(run_probes(), indent=2, sort_keys=True))
