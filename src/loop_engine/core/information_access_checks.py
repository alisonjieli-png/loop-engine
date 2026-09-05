"""Executable checks for storage-neutral Loop value access.

Owns cross-storage, scope, restart, and integrity proof for information access.
It is verification only and never becomes a runtime or storage authority.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import replace

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


def _inline_snapshot_checks() -> list[dict]:
    """Check producer, consumer and unsupported-body trust boundaries offline."""
    tests: list[dict] = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": ""})

    body = {"nested": {"items": [1, {"label": "café"}]}}
    value = LoopValue.create(body, LoopValueCreateRequest(
        "snapshot/v1", "snapshot", "producer", "fixture.producer"))
    reference = value.to_ref()
    resolver = InformationResolver()
    adapter = InlineInformationAdapter()
    resolver.register(adapter)
    publication = InformationPublicationRequest(
        value, adapter.adapter_id, InformationDurability.RUN,
        InformationScope.PRIVATE_LOOP)
    binding = resolver.publish(publication)
    access = InformationAccessRequest("producer", reference, "snapshot check")
    first = resolver.materialize(access)
    body["nested"]["items"][1]["label"] = "producer change"
    body["nested"]["items"].append(2)
    check("inline_publication_detaches_nested_producer_alias",
          first.value == {"nested": {"items": [1, {"label": "café"}]}}
          and first.value is not body
          and first.value["nested"] is not body["nested"])
    second = resolver.materialize(access)
    first.value["nested"]["items"][1]["label"] = "consumer change"
    first.value["nested"]["items"].append(3)
    third = resolver.materialize(access)
    check("inline_consumer_mutation_does_not_change_storage_or_producer",
          second.value == third.value
          == {"nested": {"items": [1, {"label": "café"}]}}
          and body["nested"]["items"]
          == [1, {"label": "producer change"}, 2]
          and second.value["nested"] is not third.value["nested"])
    check("inline_snapshot_reference_and_verified_reread_remain_exact",
          value.to_ref() == reference == binding.value_ref
          == first.value_ref == second.value_ref == third.value_ref
          and all(item.digest_verified for item in (first, second, third)))
    direct = adapter.load(binding)
    direct["nested"]["items"].clear()
    check("inline_direct_load_is_also_a_defensive_copy",
          adapter.load(binding) == third.value)

    def refusal(operation, code: InformationAccessFailureCode) -> bool:
        try:
            operation()
        except InformationAccessError as exc:
            return exc.code is code
        return False

    check("inline_changed_producer_cannot_replace_original_reference",
          refusal(lambda: resolver.publish(publication),
                  InformationAccessFailureCode.INTEGRITY_VIOLATION)
          and resolver.materialize(access).value == third.value)
    check("inline_snapshot_size_limit_is_still_enforced",
          refusal(lambda: resolver.materialize(replace(
              access, maximum_bytes=binding.size_bytes - 1)),
              InformationAccessFailureCode.TOO_LARGE))
    check("inline_persistent_durability_is_still_refused",
          refusal(lambda: resolver.publish(replace(
              publication, durability=InformationDurability.PERSISTENT)),
              InformationAccessFailureCode.UNSUPPORTED_DURABILITY))

    tuple_body = ({"items": [None, True, 7, -0.0, "é"]},)
    tuple_value = LoopValue.create(tuple_body, LoopValueCreateRequest(
        "tuple/v1", "tuple", "producer", "fixture.producer"))
    tuple_binding = resolver.publish(replace(publication, value=tuple_value))
    tuple_loaded = adapter.load(tuple_binding)
    tuple_loaded[0]["items"].append(False)
    check("inline_tuple_contract_retains_type_without_nested_aliases",
          type(tuple_loaded) is tuple
          and adapter.load(tuple_binding) == tuple_body
          and tuple_loaded[0] is not tuple_body[0])
    # Tuples and lists share the existing intrinsic JSON digest, but an exact
    # published reference must not silently replace its Python body shape.
    check("inline_same_digest_different_container_cannot_replace_snapshot",
          refusal(lambda: resolver.publish(replace(
              publication, value=replace(tuple_value, value=list(tuple_body)))),
              InformationAccessFailureCode.INTEGRITY_VIOLATION)
          and type(adapter.load(tuple_binding)) is tuple)
    check("inline_changed_binding_reference_is_refused",
          refusal(lambda: adapter.load(replace(
              binding, value_ref=tuple_value.to_ref(), binding_digest="")),
              InformationAccessFailureCode.INTEGRITY_VIOLATION))

    hooks: list[str] = []

    class OpaqueHandle:
        def __str__(self):
            hooks.append("str")
            return "private handle"

        def __repr__(self):
            hooks.append("repr")
            return "private handle"

        def __deepcopy__(self, memo):
            hooks.append("deepcopy")
            return self

    class CustomMapping(dict):
        def items(self):
            hooks.append("items")
            return super().items()

    cycle: list = []
    cycle.append(cycle)
    rejected = (
        ("opaque_handle", OpaqueHandle()),
        ("nested_opaque_handle", {"item": OpaqueHandle()}),
        ("custom_mapping", CustomMapping(item=1)),
        ("non_string_key", {1: "item"}),
        ("nonfinite_float", float("nan")),
        ("nested_infinity", [float("inf")]),
        ("cyclic_data", cycle),
        ("binary_handle", b"bytes"),
    )
    for name, unsupported in rejected:
        # Do not call LoopValue.create on opaque data: its existing general
        # digest contract permits str hooks, outside this adapter's boundary.
        check("inline_refuses_" + name, refusal(
            lambda unsupported=unsupported: resolver.publish(replace(
                publication, value=replace(value, value=unsupported))),
            InformationAccessFailureCode.INVALID_REQUEST))
    check("inline_refusals_do_not_invoke_opaque_object_hooks", not hooks)
    check("inline_refused_publications_leave_exact_snapshot_available",
          resolver.materialize(access).value == third.value)
    adapter._values[binding.locator_token][1]["nested"]["items"].append(4)
    check("inline_corrupted_private_snapshot_fails_digest_verification",
          refusal(lambda: resolver.materialize(access),
                  InformationAccessFailureCode.INTEGRITY_VIOLATION))
    return tests


def self_test() -> dict:
    """Prove one access contract across memory, file, and database storage."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    value = LoopValue.create(
        {"answer": 42, "source": "fixture", "nested": {"items": [1]}},
        LoopValueCreateRequest(
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
        value.value["nested"]["items"].append(2)
        check("json_storage_backends_snapshot_the_producer_at_publication",
              all(item.value["nested"]["items"] == [1] for item in (
                  owner_result, artifact_result, database_result)))
        for item in (owner_result, artifact_result, database_result):
            item.value["nested"]["items"].append(3)
        rereads = [resolver.materialize(InformationAccessRequest(
            "loop-producer", reference, "verify detached JSON materialization",
            requester_run_id="run-1",
            granted_permissions=("information.read.project",),
            preferred_adapter_ids=(adapter.adapter_id,)))
            for adapter in (inline, artifact, database)]
        check("json_storage_backends_preserve_identity_after_consumer_mutation",
              all(item.value["nested"]["items"] == [1]
                  and item.value_ref == reference and item.digest_verified
                  for item in rereads)
              and value.to_ref() == reference)

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

    tests.extend(_inline_snapshot_checks())
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "information_access_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
