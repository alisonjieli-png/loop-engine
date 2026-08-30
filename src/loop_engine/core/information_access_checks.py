"""Executable checks for storage-neutral Loop value access.

Owns cross-storage, scope, restart, and integrity proof for information access.
It is verification only and never becomes a runtime or storage authority.
"""
from __future__ import annotations

import os
import tempfile

from ..loop.atomic_primitives import (
    LoopValue, LoopValueCreateRequest, LoopValueRef)
from ..loop.recursive_loop import LoopLedger
from .context_artifacts import ContextArtifactStore, ContextArtifactStoreSpec
from .information_access import (
    ContextArtifactInformationAdapter, InformationAccessError,
    InformationAccessFailureCode, InformationAccessOperation,
    InformationAccessRequest, InformationDurability,
    InformationPublicationRequest, InformationResolver, InformationScope,
    InformationStorageBinding, InlineInformationAdapter,
    SQLiteInformationAdapter)
from .runtime_observer import RuntimeObservationServices


def self_test() -> dict:
    """Prove one access contract across memory, file, and database storage."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    value = LoopValue.create(
        {"answer": 42, "source": "fixture"}, LoopValueCreateRequest(
            "answer/v1", "ranked_answer", "loop-producer",
            "core.fixture.producer", source_refs=("input:fixture",)))
    reference = value.to_ref()
    ledger = LoopLedger(id_namespace="information-access")
    resolver = InformationResolver(RuntimeObservationServices(ledger=ledger))
    inline = InlineInformationAdapter()
    resolver.register(inline)

    with tempfile.TemporaryDirectory() as temporary:
        artifact = ContextArtifactInformationAdapter(ContextArtifactStore(
            ContextArtifactStoreSpec(temporary, "information")))
        database = SQLiteInformationAdapter(os.path.join(
            temporary, "information.sqlite"))
        resolver.register(artifact)
        resolver.register(database)

        inline_binding = resolver.publish(InformationPublicationRequest(
            value, inline.adapter_id, InformationDurability.RUN,
            InformationScope.PRIVATE_LOOP, run_id="run-1"))
        artifact_binding = resolver.publish(InformationPublicationRequest(
            value, artifact.adapter_id, InformationDurability.SERIES,
            InformationScope.RUN_SHARED, run_id="run-1"))
        database_binding = resolver.publish(InformationPublicationRequest(
            value, database.adapter_id, InformationDurability.PERSISTENT,
            InformationScope.PROJECT_SHARED,
            required_permissions=("information.read.project",)))

        owner_result = resolver.materialize(InformationAccessRequest(
            "loop-producer", reference, "read own current value",
            requester_run_id="run-1",
            preferred_adapter_ids=(inline.adapter_id,)))
        artifact_result = resolver.materialize(InformationAccessRequest(
            "loop-consumer", reference, "read shared run value",
            requester_run_id="run-1",
            preferred_adapter_ids=(artifact.adapter_id,)))
        database_result = resolver.materialize(InformationAccessRequest(
            "loop-later", reference, "read persistent project value",
            granted_permissions=("information.read.project",),
            preferred_adapter_ids=(database.adapter_id,)))
        check("one_reference_resolves_across_three_storage_backends",
              owner_result.value == artifact_result.value
              == database_result.value == value.value
              and len({owner_result.value_ref, artifact_result.value_ref,
                       database_result.value_ref}) == 1)

        descriptor = resolver.describe(InformationAccessRequest(
            "loop-producer", reference, "inspect available representations",
            operation=InformationAccessOperation.DESCRIBE,
            requester_run_id="run-1",
            granted_permissions=("information.read.project",)))
        public_bindings = [binding.to_public_dict() for binding in (
            inline_binding, artifact_binding, database_binding)]
        check("descriptors_do_not_expose_physical_locator_tokens",
              len(descriptor.bindings) == 3
              and all("locator_token" not in item for item in public_bindings))

        denied = None
        try:
            resolver.materialize(InformationAccessRequest(
                "loop-outsider", reference, "cross-run read attempt",
                requester_run_id="run-2",
                preferred_adapter_ids=(artifact.adapter_id,)))
        except InformationAccessError as exc:
            denied = exc.code
        check("run_scope_is_enforced_before_materialization",
              denied in {InformationAccessFailureCode.NOT_FOUND,
                         InformationAccessFailureCode.ACCESS_DENIED})

        project_denied = None
        try:
            resolver.materialize(InformationAccessRequest(
                "loop-outsider", reference, "ungranted project read",
                preferred_adapter_ids=(database.adapter_id,)))
        except InformationAccessError as exc:
            project_denied = exc.code
        check("reference_possession_does_not_grant_project_access",
              project_denied in {InformationAccessFailureCode.NOT_FOUND,
                                 InformationAccessFailureCode.ACCESS_DENIED})

        restored = InformationStorageBinding.from_storage_dict(
            artifact_binding.to_storage_dict())
        check("durable_binding_round_trip_preserves_identity",
              restored == artifact_binding
              and LoopValueRef.from_dict(reference.to_dict()) == reference)

        restarted = InformationResolver()
        restarted.register(InlineInformationAdapter())
        restarted.attach(inline_binding)
        unavailable = None
        try:
            restarted.materialize(InformationAccessRequest(
                "loop-producer", reference, "read after process restart",
                requester_run_id="run-1"))
        except InformationAccessError as exc:
            unavailable = exc.code
        check("process_local_binding_does_not_claim_restart_durability",
              unavailable is InformationAccessFailureCode.ADAPTER_UNAVAILABLE)

        database._connection.execute(
            "UPDATE loop_value_materializations SET payload = ? "
            "WHERE binding_id = ?", ('{"answer":0}',
                                      database_binding.locator_token))
        database._connection.commit()
        integrity = None
        try:
            resolver.materialize(InformationAccessRequest(
                "loop-later", reference, "detect changed database body",
                granted_permissions=("information.read.project",),
                preferred_adapter_ids=(database.adapter_id,)))
        except InformationAccessError as exc:
            integrity = exc.code
        check("changed_database_body_fails_digest_verification",
              integrity is InformationAccessFailureCode.INTEGRITY_VIOLATION)
        from .event_vocabulary import to_canonical_events
        canonical = to_canonical_events(ledger.events)
        families = {item["type"] for item in canonical}
        check("publication_and_materialization_use_canonical_run_events",
              "information.binding.published" in families
              and "information.materialized" in families)
        database.close()

    malformed = None
    try:
        LoopValueRef.from_dict({**reference.to_dict(),
                                "content_digest": "z" * 64})
    except Exception as exc:  # exact source type belongs to atomic contract
        malformed = type(exc).__name__
    check("malformed_exact_reference_is_refused", bool(malformed),
          malformed or "")

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "information_access_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
