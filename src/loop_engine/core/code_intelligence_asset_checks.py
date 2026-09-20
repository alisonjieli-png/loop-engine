"""Offline checks for exact Code asset admission and callable execution.

The fixtures use trusted local records and pure callables. They do not qualify
an external package, repository, model, or deployment.
"""
from __future__ import annotations

import json
from dataclasses import replace

from .code_intelligence_assets import (
    CODE_INTELLIGENCE_TEMPLATES, CodeAssetAdmissionError, CodeAssetAdmissionRecord, CodeAssetSpec,
    CodeRefExecutionContext, CodeRefExecutionRequest, ExternalBodyRef,
    MaterializationCache, _sha256, admit_code_asset, code_asset_capsule,
    code_asset_record, code_template_records, execute_code_ref,
    spec_from_template, subsystem_records,
)


def _admitted_fixture(spec):
    """Install exact test admission in the existing authoritative record shapes."""
    from ..catalog.stores.in_memory import EphemeralRecordStore
    from .reusable_capability_flywheel import (
        CapabilityAuthority, _admission_record_id, _authority_record, _lifecycle_record,
    )
    admission = CodeAssetAdmissionRecord(
        "fixture-admission:" + spec.asset_id, spec.asset_id, spec.version,
        spec.qualification_digest, spec.body_ref.digest, spec.dependency_digest,
        spec.contract_digest, spec.effect_digest, "fixture-producer", "fixture-verifier",
        ("fixture:independent-contract-checks",), _sha256({"fixture_checks": "passed"}))
    registered = admit_code_asset(replace(spec, lifecycle="candidate", admission_ref=""), admission)
    exact = _authority_record(registered, "fixture-producer", ("fixture:source",), admission)
    store = EphemeralRecordStore([
        exact,
        {"record_id": _admission_record_id(admission.admission_id), "record_version": "1.0.0",
         "artifact_kind": "code_asset_admission", "attributes": {"admission": admission.to_dict()}},
        _lifecycle_record(registered, exact["record_id"], 3, admission_ref=admission.admission_id),
    ])
    return registered, CapabilityAuthority(store)


def run_checks() -> dict:
    from ..loop.recursive_loop import LoopLedger
    million_line_ref = ExternalBodyRef(
        "git+https://github.com/example/large-worker.git@0123456789abcdef",
        digest="a" * 64, size_bytes=180_000_000,
        media_type="application/vnd.git.repository")
    spec = spec_from_template(
        "worker_system", asset_id="code.large_worker", name="Large worker",
        description=("Forty-file worker with preflight, execution, postflight, "
                     "diagnostics, logging, and configuration subsystems."),
        source_kind="github", body_ref=million_line_ref,
        entrypoints=("worker.preflight", "worker.run", "worker.postflight",
                     "worker.diagnostics", "worker.log", "worker.configure"),
        input_contract="work_packet",
        output_contract="work_result",
        data_refs=(ExternalBodyRef(
            "s3://example-bucket/worker-fixtures.parquet", "d" * 64,
            size_bytes=9_000_000_000,
            media_type="application/vnd.apache.parquet"),),
        file_count=40, line_count=1_000_000,
        license="Apache-2.0", lifecycle="registered",
        admission_ref="promotion:test-worker-v1",
        metadata={"subsystems": ["preflight", "execute", "postflight",
                                 "diagnostics", "logging", "configuration"],
                  "subsystem_entrypoints": {
                      "preflight": ["worker.preflight"],
                      "execute": ["worker.run"],
                      "postflight": ["worker.postflight"],
                      "diagnostics": ["worker.diagnostics"],
                      "logging": ["worker.log"],
                      "configuration": ["worker.configure"]}})
    spec, authority = _admitted_fixture(spec)
    record = code_asset_record(spec)
    capsule = code_asset_capsule(spec)
    ref = capsule.to_ref(score=0.9, source="code_intelligence")
    lazy_before = not capsule.materialised
    ledger = LoopLedger()
    from ..loop.loop_capsule import MaterializedPayload
    cache = MaterializationCache(
        lambda payload_ref, payload_digest: MaterializedPayload(
            {"worker.run": lambda value: value + 1}, payload_digest,
            local_ref="/cache/large-worker"))
    resolver = lambda payload_ref: cache(payload_ref, million_line_ref.digest)
    out = execute_code_ref(CodeRefExecutionRequest(
        ref, resolver, entrypoint="worker.run", inputs=41, authority=authority),
        CodeRefExecutionContext(ledger=ledger))
    out_again = execute_code_ref(CodeRefExecutionRequest(
        ref, resolver, entrypoint="worker.run", inputs=9, authority=authority),
        CodeRefExecutionContext(ledger=ledger))
    records = code_template_records()
    subsystems = subsystem_records(spec)
    bad_digest = False
    try:
        execute_code_ref(CodeRefExecutionRequest(
            ref, lambda payload_ref: MaterializedPayload(
                {"worker.run": lambda value: value}, "b" * 64),
            entrypoint="worker.run", inputs=1, authority=authority))
    except ValueError:
        bad_digest = True
    self_admission = False
    try:
        spec_from_template(
            "pure_function", asset_id="code.unreviewed", name="Unreviewed",
            description="unreviewed", source_kind="local_path",
            body_ref=ExternalBodyRef("path:fn.py", "c" * 64),
            lifecycle="registered")
    except ValueError:
        self_admission = True
    admission = CodeAssetAdmissionRecord(
        "admission-large-worker", spec.asset_id, spec.version,
        spec.qualification_digest, spec.body_ref.digest,
        spec.dependency_digest, spec.contract_digest, spec.effect_digest,
        "producer-loop", "verifier-loop", ("suite:large-worker",),
        _sha256({"suite": "large-worker", "passed": True}))
    admission_candidate = replace(
        spec, lifecycle="candidate", admission_ref="")
    registered = admit_code_asset(admission_candidate, admission)
    changed_proof_refused = False
    try:
        admit_code_asset(
            admission_candidate,
            replace(admission, body_digest="b" * 64))
    except CodeAssetAdmissionError:
        changed_proof_refused = True
    attempts = []

    def observed_resolver(payload_ref):
        attempts.append(payload_ref)
        return MaterializedPayload({"worker.run": lambda value: value + 1}, spec.body_ref.digest)

    candidate_ref = code_asset_capsule(replace(spec, lifecycle="candidate", admission_ref="")).to_ref()
    from ..catalog.stores.in_memory import EphemeralRecordStore
    from .reusable_capability_flywheel import CapabilityAuthority
    refused_requests = (
        ("candidate", CodeRefExecutionRequest(candidate_ref, observed_resolver,
                                              entrypoint="worker.run", inputs=1, authority=authority)),
        ("missing_authority", CodeRefExecutionRequest(ref, observed_resolver, entrypoint="worker.run", inputs=1)),
        ("string_is_not_admission", CodeRefExecutionRequest(ref, observed_resolver, entrypoint="worker.run",
                                                            inputs=1, authority=spec.admission_ref)),
        ("missing_authority_record", CodeRefExecutionRequest(ref, observed_resolver, entrypoint="worker.run",
                                                              inputs=1, authority=CapabilityAuthority(EphemeralRecordStore()))),
        ("unadmitted_entrypoint", CodeRefExecutionRequest(ref, observed_resolver, entrypoint="worker.other",
                                                          inputs=1, authority=authority)),
        ("changed_contract", CodeRefExecutionRequest(
            replace(ref, handshake=replace(ref.handshake, input_contract="other/v1")),
            observed_resolver, entrypoint="worker.run", inputs=1, authority=authority)),
    )
    refusal_checks = []
    for name, request in refused_requests:
        before = len(attempts)
        try:
            execute_code_ref(request)
            refused = False
        except CodeAssetAdmissionError:
            refused = True
        refusal_checks.append({"test": "Code_admission_refuses_before_materialization:" + name,
                               "passed": refused and len(attempts) == before})
    for name, change in (
            ("effectful", {"effects": ("network",)}),
            ("unsupported_mode", {"modes": ("non_deterministic",)}),
            ("unknown_license", {"license": "unknown"})):
        altered, altered_authority = _admitted_fixture(replace(spec, **change))
        before = len(attempts)
        try:
            execute_code_ref(CodeRefExecutionRequest(
                code_asset_capsule(altered).to_ref(), observed_resolver, entrypoint="worker.run",
                inputs=1, authority=altered_authority))
            refused = False
        except CodeAssetAdmissionError:
            refused = True
        refusal_checks.append({"test": "Code_executor_unavailable_before_materialization:" + name,
                               "passed": refused and len(attempts) == before})
    revoked_spec, revoked_authority = _admitted_fixture(spec)
    revoked_authority.transition_as_loop(spec.asset_id, spec.version, "quarantined",
                                          "fixture-reviewer", ("fixture:revocation",))
    before = len(attempts)
    try:
        execute_code_ref(CodeRefExecutionRequest(
            code_asset_capsule(revoked_spec).to_ref(), observed_resolver,
            entrypoint="worker.run", inputs=1, authority=revoked_authority))
        revoked_refused = False
    except CodeAssetAdmissionError:
        revoked_refused = True
    refusal_checks.append({"test": "revoked_Code_authority_is_rechecked_before_materialization",
                           "passed": revoked_refused and len(attempts) == before})
    from .reusable_capability_flywheel import _admission_record_id
    unproven, unproven_authority = _admitted_fixture(spec)
    admission_record = unproven_authority.store.get(_admission_record_id(unproven.admission_ref))
    admission_record["attributes"]["admission"]["evidence_digest"] = "0" * 64
    unproven_authority.store.put(admission_record)
    before = len(attempts)
    try:
        execute_code_ref(CodeRefExecutionRequest(
            code_asset_capsule(unproven).to_ref(), observed_resolver,
            entrypoint="worker.run", inputs=1, authority=unproven_authority))
        evidence_refused = False
    except CodeAssetAdmissionError:
        evidence_refused = True
    refusal_checks.append({"test": "stored_admission_evidence_digest_is_validated_before_materialization",
                           "passed": evidence_refused and len(attempts) == before})
    from .intelligence_layers import IntelligenceSearchRequest, query_intelligence_refs
    versioned, versioned_authority = _admitted_fixture(replace(spec, version="2.3.4"))
    selected = query_intelligence_refs(IntelligenceSearchRequest(
        "large worker", {"code_intelligence": [code_asset_record(versioned)]}, top_n=1))[0]
    projected_execution = execute_code_ref(CodeRefExecutionRequest(
        selected, resolver, entrypoint="worker.run", inputs=4, authority=versioned_authority))
    refusal_checks.append({"test": "public_Code_search_preserves_exact_admitted_contract_and_version",
                           "passed": selected.handshake.version == "2.3.4"
                           and selected.handshake.input_contract == versioned.input_contract
                           and projected_execution["value"] == 5})
    changed_bindings_refused = []
    for altered in (
            replace(admission_candidate, data_refs=(ExternalBodyRef("memory://other-data", "e" * 64),)),
            replace(admission_candidate, dependencies=("different-package==2.0.0",))):
        try:
            admit_code_asset(altered, admission)
            changed_bindings_refused.append(False)
        except CodeAssetAdmissionError:
            changed_bindings_refused.append(True)
    refusal_checks.append({"test": "changed_data_and_dependency_bindings_invalidate_admission",
                           "passed": all(changed_bindings_refused)})
    other_data = replace(spec, data_refs=(ExternalBodyRef("memory://other-data", "e" * 64),))
    refusal_checks.append({"test": "selected_Code_reference_binds_qualified_data_identity",
                           "passed": code_asset_capsule(spec).to_ref().digest
                           != code_asset_capsule(other_data).to_ref().digest
                           and code_asset_capsule(spec).to_ref().handshake.qualification_digest
                           == spec.qualification_digest})
    current_wire = registered.to_dict()
    unsupported_cases = (
        ("asset_schema", lambda: CodeAssetSpec.from_dict(dict(current_wire, record_type="code_asset_spec/v1")),
         "unsupported_code_asset_version"),
        ("qualification_schema", lambda: CodeAssetSpec.from_dict(
            dict(current_wire, qualification_version="code_asset_qualification/v1")), "requalification_required"),
        ("constructed_qualification", lambda: replace(admission_candidate,
            qualification_version="code_asset_qualification/v1"), "requalification_required"),
        ("admission_schema", lambda: CodeAssetAdmissionRecord.from_dict(
            dict(admission.to_dict(), schema_version="code_asset_admission/v1")), "unsupported_admission_version"),
    )
    for name, operation, expected_code in unsupported_cases:
        try:
            operation()
            rejected = False
        except CodeAssetAdmissionError as exc:
            rejected = exc.code == expected_code
        refusal_checks.append({"test": "unsupported_Code_contract_has_typed_diagnostic:" + name,
                               "passed": rejected})
    current_round_trip = CodeAssetSpec.from_dict(registered.to_dict())
    refusal_checks.append({"test": "current_qualification_identity_survives_serialization",
                           "passed": current_round_trip.to_dict() == registered.to_dict()
                           and current_round_trip.to_dict()["record_type"] == "code_asset_spec/v2"})
    tests = [
        {"test": "large_system_search_card_contains_no_large_body",
         "passed": record.body["body_inline"] is False
         and record.body["file_count"] == 40
         and record.body["line_count"] == 1_000_000
         and "source" not in record.body.get("metadata", {})
         and len(json.dumps(record.to_dict())) < 5000},
        {"test": "large_code_is_lazy_then_executes_through_two_loops",
         "passed": lazy_before and out["value"] == 42
         and out_again["value"] == 10 and cache.calls == 1
         and out["materialization"]["local_ref"] == "/cache/large-worker"
         and out["materialization"]["model_calls"] == 0
         and out["execution"]["model_calls"] == 0
         and len(ledger.loops()) >= 2},
        {"test": "code_templates_cover_packages_repositories_and_workers",
         "passed": len(records) == len(CODE_INTELLIGENCE_TEMPLATES) >= 16
         and {record.body["template_id"] for record in records}
         >= {"pypi_package", "github_repository", "template_repository",
             "large_framework", "worker_system", "llm_harness",
             "command_line_tool", "core_plugin",
             "agent_skill_bundle", "workflow", "notebook"}},
        {"test": "large_framework_is_split_into_searchable_subsystem_cards",
         "passed": len(subsystems) == 6
         and all(record.body["body_inline"] is False for record in subsystems)
         and all(record.body["entrypoints"] for record in subsystems)
         and {record.body["facets"]["subcategory"] for record in subsystems}
         >= {"preflight", "postflight", "diagnostics", "logging"}},
        {"test": "payload_digest_and_admission_fail_closed",
         "passed": bad_digest and self_admission},
        {"test": "independent_admission_binds_exact_executable_identity",
         "passed": registered.lifecycle == "registered"
         and registered.admission_ref == admission.admission_id
         and registered.body_ref.digest == spec.body_ref.digest
         and registered.qualification_digest == spec.qualification_digest},
        {"test": "changed_artifact_cannot_reuse_prior_admission",
         "passed": changed_proof_refused},
        {"test": "large_datasets_remain_separate_digest_bound_references",
         "passed": record.body["data_refs"][0]["uri"].startswith("s3://")
         and record.body["data_refs"][0]["digest"] == "d" * 64
         and record.body["data_refs"][0]["size_bytes"] == 9_000_000_000
         and "worker-fixtures" not in json.dumps(record.body.get(
             "metadata", {}))},
    ]
    tests.extend(refusal_checks)
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
