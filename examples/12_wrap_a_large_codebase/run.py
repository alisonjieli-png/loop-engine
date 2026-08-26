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
        lifecycle="registered",
        admission_ref="example:independent-review/fulfillment-worker-v1",
        metadata={
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


def main():
    spec = build_spec()
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
    ledger = LoopLedger()

    preflight = execute_code_ref(
        reference, resolver, entrypoint="worker.preflight",
        inputs=packet, ledger=ledger)
    exported = execute_code_ref(
        reference, resolver, entrypoint="worker.export",
        inputs=packet, ledger=ledger)
    postflight = execute_code_ref(
        reference, resolver, entrypoint="worker.postflight",
        inputs=packet, ledger=ledger)

    print("LARGE CODEBASE CARD")
    print(f"  serialized bytes: {len(json.dumps(top_level_card.to_dict()))}")
    print(f"  declared files: {top_level_card.body['file_count']}")
    print(f"  declared lines: {top_level_card.body['line_count']:,}")
    print(f"  body inline: {top_level_card.body['body_inline']}")
    print(f"  dataset inline: {'text' in top_level_card.body['data_refs'][0]}")
    print(f"  subsystem cards: {len(subsystem_cards)}")
    print(f"  materializations: {cache.calls}")
    print(f"  preflight: {preflight['value']}")
    print(f"  export: {exported['value']}")
    print(f"  postflight: {postflight['value']}")
    print(f"  loops recorded: {len(ledger.loops())}")


if __name__ == "__main__":
    main()
