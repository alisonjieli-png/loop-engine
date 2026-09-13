"""Does InformationStorageBinding.from_storage_dict accept a blank binding digest?"""
import json
from loop_engine.core.information_access import (
    InformationStorageBinding, InformationPublicationRequest, InlineInformationAdapter,
    InformationResolver, InformationAccessRequest, InformationAccessError)
from loop_engine.loop.atomic_primitives import LoopValue, LoopValueCreateRequest


def observed(label, value):
    print("OBSERVED " + label + ": " + repr(value), flush=True)


value = LoopValue.create({"secret": "private"}, LoopValueCreateRequest(
    value_contract_ref="result/v1", semantic_role="result", producer_loop_id="owner-loop",
    producer_definition_ref="definition.fixture@1.0.0"))
adapter = InlineInformationAdapter()
resolver = InformationResolver()
resolver.register(adapter)
binding = resolver.publish(InformationPublicationRequest(value, adapter.adapter_id, "run", "private_loop", run_id="run-1"))
observed("original_scope", binding.scope.value)
stored = binding.to_storage_dict()
tampered = dict(stored)
tampered["scope"] = "public"
tampered["binding_digest"] = ""
try:
    loaded = InformationStorageBinding.from_storage_dict(tampered)
    observed("tampered_blank_digest_binding_loaded", True)
    observed("loaded_scope", loaded.scope.value)
    observed("fresh_digest_assigned", bool(loaded.binding_digest))
    # Attach the widened binding to a fresh resolver and read it as an unrelated Loop.
    other = InformationResolver(); other.register(adapter); other.attach(loaded)
    try:
        material = other.materialize(InformationAccessRequest("stranger-loop", loaded.value_ref, "probe"))
        observed("stranger_loop_materialized_private_value", material.value)
    except InformationAccessError as exc:
        observed("stranger_loop_refused", exc.code.value)
except (InformationAccessError, ValueError) as exc:
    observed("tampered_blank_digest_binding_loaded", False)
    observed("refusal", str(exc)[:120])
control = dict(stored); control["scope"] = "public"
try:
    InformationStorageBinding.from_storage_dict(control)
    observed("control_tampered_with_original_digest_loaded", True)
except (InformationAccessError, ValueError):
    observed("control_tampered_with_original_digest_loaded", False)
