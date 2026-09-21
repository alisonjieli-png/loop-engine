"""Represent a large worker system with small cards and selected loop runs."""

import json

from loop_engine import LoopLedger
from loop_engine.loop.loop_capsule import ExternalPayloadRef, MaterializedPayload
from loop_engine.core.code_intelligence_assets import (
    MaterializationCache,
    code_asset_capsule,
    code_asset_record,
    execute_code_ref,
    spec_from_template,
    subsystem_records,
)


REPOSITORY_DIGEST = "7" * 64
DATASET_DIGEST = "8" * 64


def build_spec():
    return spec_from_template(
        "worker_system",
        asset_id="code.fulfillment_export_worker",
        name="Fulfillment export worker",
        description=(
            "A multi-file order export worker with preflight, execution, "
            "postflight, diagnostics, logging, and configuration subsystems."
        ),
        source_kind="github",
        body_ref=ExternalPayloadRef(
            "git+https://github.com/acme/fulfillment-worker.git@4a73c2e",
            REPOSITORY_DIGEST,
            size_bytes=180_000_000,
            media_type="application/vnd.git.repository",
        ),
        data_refs=(ExternalPayloadRef(
            "s3://acme-fulfillment/export-fixtures.parquet",
            DATASET_DIGEST,
            size_bytes=9_000_000_000,
            media_type="application/vnd.apache.parquet",
        ),),
        entrypoints=(
            "worker.preflight",
            "worker.export",
            "worker.postflight",
            "worker.diagnostics",
            "worker.log",
            "worker.configure",
        ),
        input_contract="export_work_packet/v1",
        output_contract="export_work_result/v1",
        file_count=40,
        line_count=1_000_000,
        license="Apache-2.0",
        metadata={
            "operation_family": "fulfillment.order_export",
            "keywords": ["fulfillment", "order export", "worker"],
            "subsystems": [
                "preflight", "execute", "postflight", "diagnostics",
                "logging", "configuration",
            ],
            "subsystem_entrypoints": {
                "preflight": ["worker.preflight"],
                "execute": ["worker.export"],
                "postflight": ["worker.postflight"],
                "diagnostics": ["worker.diagnostics"],
                "logging": ["worker.log"],
                "configuration": ["worker.configure"],
            },
            "extensions": {
                "acme.search.v1": {
                    "blocking_keys": ["python", "fulfillment", "worker"]
                }
            },
        },
    )


def admit_through_independent_review(candidate, ledger):
    """An imported codebase is a candidate until a different process admits it.

    The producer registers the candidate. A verifier that is not the producer
    qualifies the exact digests. A promotion authority that is neither of
    them makes it active. Only the active specification may be executed.
    """
    from loop_engine.catalog.stores.in_memory import EphemeralRecordStore
    from loop_engine.core.code_intelligence_assets import CodeAssetAdmissionRecord
    from loop_engine.core.reusable_capability_flywheel import (
        CandidateRegistrationRequest, CapabilityAuthority, PromotionRequest, QualificationRequest)
    from loop_engine.core.reusable_capability_harvest import (
        HarvestDispatch, ReuseObservationRequest, observe_reuse_opportunity_as_loop)
    from loop_engine.core.reusable_capability_records import (
        REUSE_ASSESSMENT_DIMENSIONS, ReuseAssessment, ReuseRecommendation)

    authority = CapabilityAuthority(EphemeralRecordStore())
    opportunity = observe_reuse_opportunity_as_loop(ReuseObservationRequest(
        "correlation-fulfillment-import", "run-fulfillment-import", "loop-import-producer",
        "practitioner.solver@1.0.0", "practitioner.code-import@1.0.0#example",
        "result-fulfillment-import", "execution-fulfillment-import",
        candidate.body_ref.uri, candidate.body_ref.digest, "repository",
        "fulfillment.order_export", "2026-09-20T12:00:00Z",
        True, True, HarvestDispatch.INLINE), ledger=ledger)
    evidence = ("example:contract-checks", "example:entrypoint-checks")
    assessment = ReuseAssessment(
        "assessment-fulfillment-import", opportunity.event_id, "loop-import-assessor", True,
        tuple((name, 8.0) for name in REUSE_ASSESSMENT_DIMENSIONS), 8.0, 0.8,
        ReuseRecommendation.CREATE_NEW_CAPABILITY_CANDIDATE,
        "An existing worker with declared entry points, contracts and effects.", evidence)
    authority.register_candidate_as_loop(CandidateRegistrationRequest(
        opportunity, assessment, candidate, "import-producer",
        ("execution-fulfillment-import", candidate.body_ref.uri)), ledger=ledger)
    admission = CodeAssetAdmissionRecord(
        "admission-fulfillment-worker-v1", candidate.asset_id, candidate.version,
        candidate.qualification_digest, candidate.body_ref.digest, candidate.dependency_digest,
        candidate.contract_digest, candidate.effect_digest,
        "import-producer", "independent-verifier", evidence, "9" * 64)
    authority.qualify_as_loop(QualificationRequest(
        candidate.asset_id, candidate.version, admission), ledger=ledger)
    authority.promote_as_loop(PromotionRequest(
        candidate.asset_id, candidate.version, "promotion-authority", evidence), ledger=ledger)
    return authority, authority.active_spec(candidate.asset_id, candidate.version)


def main():
    ledger = LoopLedger()
    authority, spec = admit_through_independent_review(build_spec(), ledger)
    top_level_card = code_asset_record(spec)
    subsystem_cards = subsystem_records(spec)
    reference = code_asset_capsule(spec).to_ref(source="code_intelligence")

    operations = {
        "worker.preflight": lambda packet: {
            "ready": bool(packet.get("destination")),
            "orders": len(packet.get("orders", ())),
        },
        "worker.export": lambda packet: {
            "destination": packet["destination"],
            "exported_order_ids": [row["order_id"] for row in packet["orders"]],
        },
        "worker.postflight": lambda packet: {
            "checked": len(packet.get("orders", ())),
            "status": "complete",
        },
    }
    cache = MaterializationCache(
        lambda payload_ref, payload_digest: MaterializedPayload(
            operations,
            payload_digest,
            local_ref="/example-cache/fulfillment-worker-4a73c2e",
        )
    )
    resolver = lambda payload_ref: cache(payload_ref, REPOSITORY_DIGEST)
    packet = {
        "destination": "warehouse-east",
        "orders": [{"order_id": "A-104"}, {"order_id": "A-105"}],
    }
    from loop_engine.core.code_intelligence_assets import (
        CodeAssetAdmissionError, CodeRefExecutionContext, CodeRefExecutionRequest)
    execution_context = CodeRefExecutionContext(ledger=ledger)
    try:
        execute_code_ref(CodeRefExecutionRequest(
            reference, resolver, entrypoint="worker.preflight", inputs=packet),
            execution_context)
        refused_without_admission = False
    except CodeAssetAdmissionError:
        refused_without_admission = True

    def run(entrypoint):
        return execute_code_ref(CodeRefExecutionRequest(
            reference, resolver, entrypoint=entrypoint, inputs=packet, authority=authority),
            execution_context)
    preflight, exported, postflight = run("worker.preflight"), run("worker.export"), run("worker.postflight")

    print("LARGE CODEBASE CARD")
    print(f"  serialized bytes: {len(json.dumps(top_level_card.to_dict()))}")
    print(f"  declared files: {top_level_card.body['file_count']}")
    print(f"  declared lines: {top_level_card.body['line_count']:,}")
    print(f"  body inline: {top_level_card.body['body_inline']}")
    print(f"  dataset inline: {'text' in top_level_card.body['data_refs'][0]}")
    print(f"  subsystem cards: {len(subsystem_cards)}")
    print(f"  refused without an admission authority: {refused_without_admission}")
    print(f"  materializations: {cache.calls}")
    print(f"  preflight: {preflight['value']}")
    print(f"  export: {exported['value']}")
    print(f"  postflight: {postflight['value']}")
    print(f"  loops recorded: {len(ledger.loops())}")


if __name__ == "__main__":
    main()
