"""Claim 5 (admission) and Part 2(e) (kernel step events) and legacy-contract coercion."""
import json
from loop_engine.core.model_response_admission import admit_model_response_as_loop, ModelResponseAdmissionRequest

def admit(text, schema=None):
    try:
        r = admit_model_response_as_loop(ModelResponseAdmissionRequest(text, "inline:x", "0" * 64, schema=schema))
        return f"admitted={r.admitted} failure={r.failure_code!r} strategy={r.strategy} value_keys={sorted(r.value) if r.value else None}"
    except BaseException as exc:
        return f"RAISED {type(exc).__name__}: {str(exc)[:120]}"

print("===== claim 5: model response admission =====")
print("surplus field, no schema:", admit('{"a":1,"surplus":2}'))
print("surplus field, schema w/o additionalProperties:", admit('{"a":1,"surplus":2}', {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}))
print("surplus field, schema additionalProperties=false:", admit('{"a":1,"surplus":2}', {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"], "additionalProperties": False}))
print("duplicate keys:", admit('{"value":1,"value":2}'))
print("NaN:", admit('{"value":NaN}'))
print("1e999:", admit('{"value":1e999}'))
print("wrong record_type version (valid JSON):", admit('{"record_type":"adaptive_spawned_assignment/v2","task_id":"a"}'))
nested = '{"a":' * 1500 + '1' + '}' * 1500
print("nested 1500 deep object:", admit(nested))
nested_arr = '{"a":' + '[' * 1500 + '1' + ']' * 1500 + '}'
print("nested 1500 deep array in object:", admit(nested_arr))
print("nested 900 deep object:", admit('{"a":' * 900 + '1' + '}' * 900))

print("\n===== Part 2(e): kernel step events =====")
from loop_engine.loop.kernel import KernelRunRequest, ProblemSpec, default_impls
from loop_engine.loop.kernel_runtime import execute_kernel_run
run = execute_kernel_run(KernelRunRequest(ProblemSpec("count kernel events", success_criteria=("done",)), default_impls(), selected_mode="deterministic"))
print("final_route:", run.get("final_route"), "passes:", run.get("passes"), "terminal:", run.get("loop_terminal_code"))
# find the owner's ledger: execute_kernel_run created a Starting loop; recover events through Loop._live_instances
from loop_engine.loop.recursive_loop import Loop
owner = next((l for l in Loop._live_instances if l.loop_id == run["loop_id"] and l.definition_ref.content_digest == run["loop_definition_digest"]), None)
if owner is None:
    print("could not locate owner loop instance")
else:
    steps = [(e.get("step"), e.get("output"), e.get("accepted")) for e in owner.ledger.events if e.get("event") == "run_step" and e.get("loop_id") == owner.loop_id]
    print(f"run_step events on owner: n={len(steps)}")
    for s in steps: print("   ", s)
    print("custom kinds on owner:", [e.get("custom_kind") for e in owner.ledger.events if e.get("event") == "custom" and e.get("loop_id") == owner.loop_id])
    print("terminal:", [(e.get("reason")) for e in owner.ledger.events if e.get("event") == "terminal" and e.get("loop_id") == owner.loop_id])

print("\n===== Part 2(d) addendum: duck-typed legacy contract object =====")
from loop_engine.loop.recursive_loop import LoopConfig
class LegacyContract:
    goal = "legacy work"; output_roles = ("legacy_out",); input_roles = (); effects = ("pure",); execution_mode = "model_led"; role = "solution"
lp = Loop("legacy", LoopConfig(framework="custom", custom_steps=("act",), allowable_modes=("deterministic",), preferred_modes=("deterministic",)), contract=LegacyContract())
init = next(e for e in lp.ledger.events if e.get("event") == "init" and e.get("loop_id") == lp.loop_id)
print("bound contract:", lp.contract.execution_mode, lp.contract.role, lp.contract.output_roles, "| coercion recorded on init?", {k: v for k, v in init.items() if "coerc" in k} or "NO")

print("\n===== Part 2(d) addendum: strict LoopStartRequest path refuses mode mismatch? =====")
from loop_engine.loop.loop_definition import LoopDefinition, LoopDefinitionError
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.loop_role import LoopRoleIdentity, LoopRole
try:
    LoopDefinition.from_runtime(identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.reference_nine_step"),
        contract=LoopContract("strict", "hybrid", output_roles=("r",), role="practitioner"),
        config=LoopConfig(allowable_modes=("deterministic",), preferred_modes=("deterministic",)), compatibility=False)
    print("strict path ACCEPTED a hybrid contract with deterministic-only config (unexpected)")
except LoopDefinitionError as exc:
    print("strict path REFUSED:", str(exc)[:120])
