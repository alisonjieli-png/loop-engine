import json, sys, time
from copy import deepcopy
sys.path.insert(0, "/tmp/claude-1000/-home-username-loop-engine/6d8b36e1-c0bf-4f98-a765-7be966b7d9c2/scratchpad/agent_bindings")
from loop_engine.core.adaptive_practitioner_bindings_checks import assignment, input_binding, spec_from
from loop_engine.core.adaptive_practitioner_bindings import compile_assignments
import probe_public as pp  # reuses public_run2 (module body re-runs its probes only under __main__? no -> guard below)
producer = assignment("source")
consumer = assignment("consumer", dependencies=("source",), inputs=(input_binding(),), output=None)

print("===== RunHistory event shape + step events in the adaptive flow =====")
from loop_engine.core.run_history import RunHistory
import tempfile
from pathlib import Path
# re-implement minimal: run and keep raw event objects
def raw_events(assignments, **kw):
    from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
    from loop_engine.core.adaptive_practitioner import run_adaptive_practitioner
    from loop_engine.core.adaptive_practitioner_acceptance_checks import _decision, _decision_id, _orientation, _success_answers
    from loop_engine.core.adaptive_practitioner_records import AdaptivePractitionerDependencies, AdaptivePractitionerRequest
    observed = []
    class R:
        resolver_id = "fixture.dependency_values"
        def supports(self, task):
            try: return json.loads(task).get("record_type") == "delegated_problem/v1"
            except (ValueError, AttributeError): return False
        def execute(self, task):
            packet = json.loads(task); observed.append(packet)
            if packet["task_id"] == "source": return {"verified": True, "value": [2, 3]}
            return {"verified": True, "value": sum(packet["dependency_inputs"][0]["value"])}
    decision = _decision("SPAWN_LOOP", required_capabilities=[], permissions=[], goal="g")
    plan = {"action_id": _decision_id(decision), "how_mode": "delegate", "act_mode": "spawn_practitioners", "capability_ref": "", "arguments": {}, "steps": ["s"], "spawned_tasks": assignments, "rationale": "r"}
    verification = json.loads(_success_answers()[-2]); verification["scores"] = [1.0] * len(assignments)
    answers = tuple(json.dumps(x) for x in (_orientation(candidate_capabilities=[]), {"actions": [decision]}, plan, verification, {"route": "stop_success", "reason": "done"}))
    with tempfile.TemporaryDirectory(prefix="probe-followup-") as root:
        output = run_adaptive_practitioner(AdaptivePractitionerRequest("root", runs_dir=root, mode="hybrid", max_passes=1, quiet_model_io=True),
            AdaptivePractitionerDependencies(fixture_model_execution(FixtureModelExecutionRequest(answers=answers, max_model_calls=len(answers))), deterministic_resolvers=(R(),)))
        saved = RunHistory.load(str(Path(output["run_history"]["path"]).parent), output["run_id"])
        log = list(saved.event_log)
        first = log[0]
        print("event object type:", type(first).__name__, "| attrs:", [a for a in dir(first) if not a.startswith("_")][:20])
        print("sample event:", {a: getattr(first, a) for a in ("kind", "event", "loop_id", "record_type") if hasattr(first, a)}, "| detail keys:", sorted(first.detail)[:12])
        kinds = {}
        for e in log:
            k = getattr(e, "kind", None) or e.detail.get("event") or e.detail.get("kind")
            kinds[k] = kinds.get(k, 0) + 1
        print("event kind histogram:", dict(sorted(kinds.items(), key=lambda kv: -kv[1])[:25]))
        steps = [e for e in log if (getattr(e, "kind", None) == "run_step" or e.detail.get("event") == "run_step")]
        by_loop = {}
        for e in steps:
            d = e.detail; lid = getattr(e, "loop_id", None) or d.get("loop_id")
            by_loop.setdefault(lid, []).append((d.get("step"), str(d.get("output"))[:34], d.get("accepted")))
        for lid, s in by_loop.items(): print(f"  run_step for {lid}: n={len(s)}", s)
        inits = [(getattr(e, "loop_id", None) or e.detail.get("loop_id"), e.detail.get("goal", "")[:30], e.detail.get("relationship_kind"), e.detail.get("role")) for e in log if (getattr(e, "kind", None) == "init" or e.detail.get("event") == "init")]
        print("inits:", inits)
        terms = [(getattr(e, "loop_id", None) or e.detail.get("loop_id"), e.detail.get("reason")) for e in log if (getattr(e, "kind", None) == "terminal" or e.detail.get("event") == "terminal")]
        print("terminals:", terms)
        # consumer task text size
        print("consumer task packet bytes:", len(json.dumps(next(p for p in observed if p["task_id"] == "consumer"))))
    return output
raw_events([consumer, producer])

print("\n===== nested schema depths that pass admission: does the run still abort? =====")
for depth in (300, 600, 900):
    nested = '{"type":"array","items":' * depth + '{"type":"integer"}' + '}' * depth
    p = deepcopy(producer); p["output_contract"]["schema"] = "__NESTED__"
    output, observed, intact, events = pp.public_run2([consumer, p], plan_text=lambda plan, nested=nested: json.dumps(plan).replace('"__NESTED__"', nested))
    b = pp.brief(output)
    print(f"[depth={depth}] status={b.get('status')} solved={b.get('solved')} failure_code={b.get('failure_code')} final_route={b.get('final_route')} model_calls={b.get('model_calls')} spawned={len(b.get('spawned', []))} failures={b.get('failures')}")
    diags = [(e.get("custom_kind"), str(e.get("error") or e.get("detail") or e.get("diagnostic") or "")[:140]) for e in events if "plan_invalid" in json.dumps(e, default=str)]
    print("     plan diagnostics:", diags[:3])

print("\n===== task text size for a big value delivered by value =====")
output, observed, intact, events = pp.public_run2([consumer, producer], source_value=list(range(200_000)))
pkt = next((p for p in observed if p["task_id"] == "consumer"), None)
print("consumer task packet bytes (this is the delegated task text handed to the consumer, i.e. model prompt material):", len(json.dumps(pkt)) if pkt else None)

print("\n===== distinct-role diamond compiles? =====")
def out(role, ref):
    return {"role": role, "value_contract_ref": ref, "schema": {"type": "array", "items": {"type": "integer"}}, "result_path": ["value"]}
a = assignment("a")
b = assignment("b", dependencies=("a",), inputs=(input_binding("a"),)); b["output_contract"] = out("values/v1", "integer_sequence/v1")
c = assignment("c", dependencies=("a",), inputs=(input_binding("a"),)); c["output_contract"] = out("other/v1", "other_sequence/v1")
d = assignment("d", dependencies=("b", "c"), inputs=(
    {"role": "values/v1", "source_task_id": "b", "source_role": "values/v1", "value_contract_ref": "integer_sequence/v1", "delivery": "value"},
    {"role": "other/v1", "source_task_id": "c", "source_role": "other/v1", "value_contract_ref": "other_sequence/v1", "delivery": "value"}), output=None)
for label, plan in (("diamond_distinct_roles_reverse_listed", [d, c, b, a]), ("diamond_distinct_roles_forward", [a, b, c, d])):
    try:
        order, digest = compile_assignments(tuple(spec_from(v) for v in plan), "root"); print(f"[{label}] ADMITTED order={order} -> {[plan[i]['task_id'] for i in order]}")
    except Exception as exc:
        print(f"[{label}] REFUSED {type(exc).__name__}: {str(exc)[:120]}")

print("\n===== Part 2(e): kernel step events with an explicit owner =====")
from loop_engine.loop.kernel import KernelRunRequest, ProblemSpec, default_impls
from loop_engine.loop.kernel_runtime import execute_kernel_run, _starting_loop
req = KernelRunRequest(ProblemSpec("count kernel events", success_criteria=("done",)), default_impls(), selected_mode="deterministic")
owner = _starting_loop(req)
run = execute_kernel_run(KernelRunRequest(req.spec, req.impls, selected_mode="deterministic", owner_loop=owner))
print("final_route:", run.get("final_route"), "passes:", run.get("passes"), "terminal:", run.get("loop_terminal_code"))
steps = [(e.get("step"), e.get("output"), e.get("accepted"), e.get("mode")) for e in owner.ledger.events if e.get("event") == "run_step" and e.get("loop_id") == owner.loop_id]
print(f"run_step events on owner: n={len(steps)}")
for s in steps: print("   ", s)
print("owner custom kinds:", [e.get("custom_kind") for e in owner.ledger.events if e.get("event") == "custom" and e.get("loop_id") == owner.loop_id])
print("owner terminal:", [e.get("reason") for e in owner.ledger.events if e.get("event") == "terminal" and e.get("loop_id") == owner.loop_id])
print("iteration_started count:", sum(1 for e in owner.ledger.events if e.get("event") == "iteration_started" and e.get("loop_id") == owner.loop_id))
print("all loop ids on ledger:", sorted({e.get("loop_id") for e in owner.ledger.events}))
