"""Historical-encoding refusal controls (question 4), rerun with ValueError catch."""
import hashlib, json, traceback
from loop_engine.loop.loop_definition import LoopDefinition, LoopDefinitionError
from loop_engine.loop.loop_definition_checks import _definition

def observed(label, value):
    print("OBSERVED " + label + ": " + repr(value), flush=True)

definition = _definition()
def redigest(value):
    body = {k: v for k, v in value.items() if k != "content_digest"}
    value["content_digest"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    return value
cases = {}
v = definition.to_dict(); v["record_type"] = "loop_definition/v1"; cases["v1_carrying_input_cardinalities"] = redigest(v)
v = definition.to_dict(); v["record_type"] = "loop_definition/v3"; cases["unsupported_v3"] = redigest(v)
v = definition.to_dict(); v["contract"]["input_cardinalities"] = [{"role": "absent", "cardinality": "multiple", "max_items": 2}]
cases["v2_cardinality_on_undeclared_role"] = redigest(v)
v = definition.to_dict(); v["contract"]["input_cardinalities"] = [{"role": "request", "cardinality": "multiple", "max_items": True}]
cases["v2_boolean_max_items"] = redigest(v)
v = definition.to_dict(); v["contract"]["input_cardinalities"] = [{"role": "request", "cardinality": "multiple", "max_items": 2, "extra": 1}]
cases["v2_extra_cardinality_key"] = redigest(v)
v = definition.to_dict(); v["contract"]["input_roles"] = ["request", "aux"]
v["contract"]["input_cardinalities"] = [{"role": "request", "cardinality": "multiple", "max_items": 2},
                                        {"role": "aux", "cardinality": "multiple", "max_items": 2}]
cases["v2_unsorted_cardinalities_valid_digest"] = redigest(v)
v = definition.to_dict(); v["contract"]["input_roles"] = ["aux", "request"]
v["contract"]["input_cardinalities"] = [{"role": "aux", "cardinality": "multiple", "max_items": 2},
                                        {"role": "request", "cardinality": "multiple", "max_items": 2}]
cases["v2_sorted_two_multiple_ports"] = redigest(v)
for name, value in cases.items():
    try:
        LoopDefinition.from_dict(value); observed(name, "LOADED")
    except LoopDefinitionError as exc:
        observed(name, "refused LoopDefinitionError: " + str(exc)[:80])
    except ValueError as exc:
        observed(name, "refused " + type(exc).__name__ + " (not LoopDefinitionError): " + str(exc)[:80])

from loop_engine.loop.spawned_task_checkpoint import SpawnedTaskCheckpoint, SpawnedTaskCheckpointError
from loop_engine.loop.delegation_checkpoint_checks import _terminal_checkpoint_case
cp = _terminal_checkpoint_case()["checkpoint"]
def cp_digest(value):
    body = {k: v for k, v in value.items() if k != "checkpoint_digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
v2 = cp.to_dict(); v2["schema_version"] = "spawned_task_checkpoint/v2"
v2["spec"]["contract"]["output_type"] = "multiple"; v2["spec"]["contract"]["max_outputs"] = 2
v2["checkpoint_digest"] = cp_digest(v2)
for name, value in (("checkpoint_v2_with_multiple_output_eleven_fields", v2),):
    try:
        SpawnedTaskCheckpoint.from_dict(value); observed(name, "LOADED")
    except (SpawnedTaskCheckpointError, ValueError) as exc:
        observed(name, "refused " + type(exc).__name__ + ": " + str(exc)[:80])
v2b = cp.to_dict(); v2b["schema_version"] = "spawned_task_checkpoint/v2"
for k in ("output_type", "max_outputs", "input_cardinalities"): v2b["spec"]["contract"].pop(k)
v2b["checkpoint_digest"] = cp_digest(v2b)
try:
    SpawnedTaskCheckpoint.from_dict(v2b); observed("checkpoint_v2_legacy_eight_field_contract", "LOADED")
except (SpawnedTaskCheckpointError, ValueError) as exc:
    observed("checkpoint_v2_legacy_eight_field_contract", "refused: " + str(exc)[:80])
v1 = cp.to_dict(); v1["schema_version"] = "spawned_task_checkpoint/v1"; v1["checkpoint_digest"] = cp_digest(v1)
try:
    SpawnedTaskCheckpoint.from_dict(v1); observed("checkpoint_v1", "LOADED")
except (SpawnedTaskCheckpointError, ValueError) as exc:
    observed("checkpoint_v1", "refused: " + str(exc)[:80])
counters = cp.to_dict(); counters["update_count"] = 2.9; counters["checkpoint_digest"] = ""
try:
    loaded = SpawnedTaskCheckpoint.from_dict(counters)
    observed("float_update_count_with_blank_digest", "LOADED update_count=" + repr(loaded.update_count))
except (SpawnedTaskCheckpointError, ValueError) as exc:
    observed("float_update_count_with_blank_digest", "refused: " + str(exc)[:80])
print("probe_f finished", flush=True)
