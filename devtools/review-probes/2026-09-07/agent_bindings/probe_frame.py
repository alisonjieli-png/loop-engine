"""Part 1 claims 2 and 4 at the SpawnedDependencyFrame level (no model calls)."""
import json, math, time
from copy import deepcopy
from dataclasses import replace
from loop_engine.core.adaptive_practitioner_bindings_checks import assignment, input_binding, frame_fixture
from loop_engine.core.adaptive_practitioner_bindings import (
    SpawnedAssignment, SpawnedDependencyFrame, DependencyBindingError, _digest)
from loop_engine.core.adaptive_practitioner_records import AdaptivePractitionerRequest
from loop_engine.core.information_access import InformationAccessRequest, InformationAccessError
from loop_engine.loop.kernel import ProblemSpec
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.loop.loop_role import LoopRoleIdentity, LoopRole

request = AdaptivePractitionerRequest("consumer", mode="deterministic")

def try_resolve(label, frame, target, consumer_loop=None):
    consumer_loop = consumer_loop or frame.owner.spawn("consumer")
    try:
        bound, delegation, resolver = frame.resolve(target, consumer_loop, request=request, spec=ProblemSpec("consumer"))
        print(f"[{label}] RESOLVED value={bound[0].port.value if bound else None!r}"[:200])
        return bound, delegation, resolver, consumer_loop
    except Exception as exc:
        print(f"[{label}] REFUSED {type(exc).__name__}: {str(exc)[:120]} disposition={getattr(getattr(exc,'disposition',None),'value',None)}")
        return None

print("===== claim 2: only completed, unchanged producer results satisfy inputs =====")
# 2a in-place mutation of the shared summary dict after register (this is the same object the runtime appends to spawned_results)
frame, producer, consumer, summary = frame_fixture()
summary["accepted_result"]["result"]["value"][0] = 99
try_resolve("mutated_result_after_register", frame, consumer)
# 2a' mutate a field outside accepted_result (e.g. objective)
frame, producer, consumer, summary = frame_fixture()
summary["objective"] = "rewritten"
try_resolve("mutated_metadata_after_register", frame, consumer)
# 2a'' mutate the LoopValue body held in frame.outputs (producer-side body replacement)
frame, producer, consumer, summary = frame_fixture()
frame.outputs["source"][0].value.append(4)
try_resolve("stored_body_replaced", frame, consumer)
# 2b FAILED producer re-registered after a COMPLETE registration (stale earlier result exists in frame.outputs)
frame, producer, consumer, summary = frame_fixture()
failed = deepcopy(summary); failed.update(task_complete=False, accepted_result=None)
frame.register(producer, failed)
print("outputs still holds stale wrapped value after failed re-register:", "source" in frame.outputs)
try_resolve("failed_after_complete_reregister", frame, consumer)
# 2b' complete producer but the issued ledger event says spawned_task_complete False
frame, producer, consumer, summary = frame_fixture(issue=False)
frame.owner.ledger.record(loop_id=frame.owner.loop_id, event="custom", custom_kind="adaptive_spawned_result_returned",
                          spawned_loop_id=summary["loop_id"], result_digest=_digest(summary), spawned_task_complete=False)
try_resolve("issued_event_says_incomplete", frame, consumer)
# 2b'' issued event recorded by a different loop_id (forged from a sibling)
frame, producer, consumer, summary = frame_fixture(issue=False)
frame.owner.ledger.record(loop_id="loop-forged", event="custom", custom_kind="adaptive_spawned_result_returned",
                          spawned_loop_id=summary["loop_id"], result_digest=_digest(summary), spawned_task_complete=True)
try_resolve("issued_event_from_other_loop", frame, consumer)
# 2c producer completed under a different plan digest / assignment version
frame, producer, consumer, summary = frame_fixture()
other = deepcopy(summary); other["dependency_plan_digest"] = "c" * 64
f2 = SpawnedDependencyFrame(frame.owner, frame.run_id, "c" * 64, dict(frame.assignments))
try:
    f2.register(producer, other); print("[different_plan_digest_register] ACCEPTED (unexpected)")
except Exception as exc:
    print(f"[different_plan_digest_register] REFUSED {type(exc).__name__}: {str(exc)[:100]} disposition={exc.disposition.value}")
# 2c' assignment changed after admission (output_contract schema swapped)
frame, producer, consumer, summary = frame_fixture()
from loop_engine.core.adaptive_practitioner_bindings import SpawnedOutputContract
frame.assignments["source"] = replace(producer, output_contract=SpawnedOutputContract("values/v1", "integer_sequence/v1", '{"type":"array"}', ("value",)))
try_resolve("assignment_schema_swapped_after_admission", frame, consumer)
# 2d register never called for producer (prerequisite never ran)
frame, producer, consumer, summary = frame_fixture()
frame.results.clear(); frame.outputs.clear()
try_resolve("prerequisite_never_registered", frame, consumer)

print("\n===== scope of start(): who may consume =====")
frame, producer, consumer, summary = frame_fixture()
sol = frame.owner.spawn("solution consumer", LoopConfig(allowable_modes=("deterministic",), preferred_modes=("deterministic",)),
                        identity=LoopRoleIdentity(LoopRole.SOLUTION, "solution.validator"))
try_resolve("solution_role_consumer", frame, consumer, sol)
frame, producer, consumer, summary = frame_fixture()
term = frame.owner.spawn("terminal consumer")
term.run(handler=lambda o, s, c: StepOutcome(s, "deterministic", 1.0), max_steps=len(term.steps()) + 1)
try_resolve("terminal_consumer", frame, consumer, term)
frame, producer, consumer, summary = frame_fixture()
stranger = Loop("stranger", LoopConfig(allowable_modes=("deterministic",), preferred_modes=("deterministic",)))
try_resolve("consumer_from_other_ledger", frame, consumer, stranger)
frame, producer, consumer, summary = frame_fixture()
grandchild = frame.owner.spawn("child").spawn("grandchild")
try_resolve("grandchild_consumer", frame, consumer, grandchild)
frame, producer, consumer, summary = frame_fixture()
c1 = frame.owner.spawn("consumer")
try_resolve("first_start", frame, consumer, c1)
try_resolve("second_start_same_task", frame, consumer, frame.owner.spawn("consumer again"))

print("\n===== claim 4: delivery values =====")
def custom_frame(schema, value, *, delivery="value"):
    prod = assignment("source"); prod["output_contract"]["schema"] = schema
    cons = assignment("consumer", dependencies=("source",), inputs=(input_binding(delivery=delivery),), output=None)
    producer = SpawnedAssignment.from_mapping(prod); consumer = SpawnedAssignment.from_mapping(cons)
    owner = Loop("owner", LoopConfig(allowable_modes=("deterministic",), preferred_modes=("deterministic",), delegated_modes=("deterministic",)))
    frame = SpawnedDependencyFrame(owner, "fixture-run", "b" * 64, {"source": producer, "consumer": consumer})
    produced = owner.spawn("producer"); frame.start(producer, produced)
    produced.run(handler=lambda o, s, c: StepOutcome(s, "deterministic", 1.0), max_steps=len(produced.steps()) + 1)
    summary = {"record_type": "spawned_practitioner_result/v1", "loop_id": produced.loop_id,
               "definition_id": produced.definition_ref.definition_id, "definition_version": produced.definition_ref.version,
               "definition_digest": produced.definition_ref.content_digest, "spawned_by_loop_id": owner.loop_id,
               "dependency_plan_digest": frame.plan_digest, "task_id": "source", "task_complete": True,
               "verification_record_digest": "a" * 64, "accepted_result": {"result": {"verified": True, "value": value}}}
    return frame, producer, consumer, summary, owner, produced

for label, schema, value in (
        ("nan_empty_schema", {}, [float("nan")]),
        ("inf_number_schema", {"type": "array", "items": {"type": "number"}}, [float("inf")]),
        ("nan_nested_dict", {}, {"a": {"b": float("nan")}}),
        ("bool_as_integer", {"type": "array", "items": {"type": "integer"}}, [True, 3]),
        ("huge_int", {"type": "array", "items": {"type": "integer"}}, [10 ** 5000]),
        ("big_list_300k", {"type": "array", "items": {"type": "integer"}}, list(range(300_000))),
        ("tuple_value", {}, (1, 2)),
        ("nonstring_key", {}, {1: 2})):
    frame, producer, consumer, summary, owner, produced = custom_frame(schema, value)
    t0 = time.time()
    try:
        frame.register(producer, summary)
        owner.ledger.record(loop_id=owner.loop_id, event="custom", custom_kind="adaptive_spawned_result_returned",
                            spawned_loop_id=produced.loop_id, result_digest=_digest(summary), spawned_task_complete=True)
        reg = "registered"
    except Exception as exc:
        reg = f"register REFUSED {type(exc).__name__}: {str(exc)[:90]} disp={getattr(getattr(exc,'disposition',None),'value',None)}"
    out = try_resolve(f"deliver:{label}", frame, consumer) if reg == "registered" else None
    print(f"    ({label}) {reg}; resolved={'yes' if out else 'no'}; {time.time()-t0:.2f}s")

print("\n===== claim 4: references =====")
frame, producer, consumer, summary = frame_fixture()
out = try_resolve("reference_baseline", frame, consumer)
bound, delegation, resolver, consumer_loop = out
ref = bound[0].reference
print("materialized observation events on consumer ledger:", [e.get("custom_kind") or e.get("event") for e in frame.owner.ledger.events if e.get("loop_id") == consumer_loop.loop_id and "information" in json.dumps(e, default=str)][:5])
for label, req in (
        ("other_run_same_loop", InformationAccessRequest(value_ref=ref, requester_loop_id=consumer_loop.loop_id, purpose="x", requester_run_id="other-run")),
        ("same_run_other_loop", InformationAccessRequest(value_ref=ref, requester_loop_id=frame.owner.loop_id, purpose="x", requester_run_id=frame.run_id)),
        ("no_run_id", InformationAccessRequest(value_ref=ref, requester_loop_id=consumer_loop.loop_id, purpose="x")),
        ("consumer_itself", InformationAccessRequest(value_ref=ref, requester_loop_id=consumer_loop.loop_id, purpose="x", requester_run_id=frame.run_id))):
    try:
        m = resolver.materialize(req); print(f"[materialize:{label}] OK value={m.value}")
    except Exception as exc:
        print(f"[materialize:{label}] REFUSED {type(exc).__name__}: {str(exc)[:100]}")
# body replaced after the consumer holds a reference
frame.outputs["source"][0].value.append(4)
try:
    m = resolver.materialize(InformationAccessRequest(value_ref=ref, requester_loop_id=consumer_loop.loop_id, purpose="x", requester_run_id=frame.run_id))
    print("[materialize after producer body mutated] OK value=", m.value)
except Exception as exc:
    print("[materialize after producer body mutated] REFUSED", type(exc).__name__, str(exc)[:100])
# a second consumer after the mutation
try_resolve("second_consumer_after_body_mutation", frame, consumer.__class__.from_mapping(dict(assignment("consumer2", dependencies=("source",), inputs=(input_binding(),), output=None))) if False else consumer)
# delivery=reference: what does the consumer get?
frame, producer, consumer, summary, owner, produced = custom_frame({"type": "array", "items": {"type": "integer"}}, [2, 3], delivery="reference")
frame.register(producer, summary)
owner.ledger.record(loop_id=owner.loop_id, event="custom", custom_kind="adaptive_spawned_result_returned", spawned_loop_id=produced.loop_id, result_digest=_digest(summary), spawned_task_complete=True)
out = try_resolve("delivery_reference", frame, consumer)
if out:
    bound, delegation, resolver, cl = out
    print("reference delivery port value type:", type(bound[0].port.value).__name__, "| to_dict keys:", sorted(bound[0].to_dict()))
    print("frame.resolvers keys:", list(frame.resolvers), "| consumer has any attribute exposing resolver?", any("resolver" in a.lower() for a in dir(cl)))
    print("ledger events with loop_id==consumer mentioning information:", [ (e.get("event"), e.get("custom_kind"), e.get("observation") or e.get("kind")) for e in owner.ledger.events if e.get("loop_id") == cl.loop_id and "information" in json.dumps(e, default=str)])
