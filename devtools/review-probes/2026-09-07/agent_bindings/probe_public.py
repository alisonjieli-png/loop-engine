"""End-to-end public adaptive flow with the offline fixture model (zero provider calls)."""
import json, tempfile, time, sys
from copy import deepcopy
from pathlib import Path
from loop_engine.core.adaptive_practitioner_bindings_checks import assignment, input_binding

def public_run2(assignments, *, source_value=None, parent_finishes=False, plan_text=None, resolver_value=None):
    from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
    from loop_engine.core.adaptive_practitioner import run_adaptive_practitioner
    from loop_engine.core.adaptive_practitioner_acceptance_checks import _decision, _decision_id, _orientation, _success_answers
    from loop_engine.core.adaptive_practitioner_records import AdaptivePractitionerDependencies, AdaptivePractitionerRequest
    from loop_engine.core.adaptive_host_runtime_checks import _answers, _fixture
    from loop_engine.core.run_history import RunHistory
    observed = []
    original = [2, 3] if source_value is None else source_value
    class ExactDependencyResolver:
        resolver_id = "fixture.dependency_values"
        def supports(self, task):
            try: return json.loads(task).get("record_type") == "delegated_problem/v1"
            except (ValueError, AttributeError): return False
        def execute(self, task):
            packet = json.loads(task); observed.append(packet)
            if packet["task_id"] == "source":
                return {"verified": True, "value": deepcopy(original)}
            inputs = packet["dependency_inputs"]
            if resolver_value is not None: return {"verified": True, "value": resolver_value(inputs)}
            if not inputs: return {"verified": True, "value": "barrier complete"}
            if inputs[0]["delivery"] == "reference": return {"verified": True, "value": inputs[0]["value_ref"]}
            return {"verified": True, "value": sum(inputs[0]["value"])}
    decision = _decision("SPAWN_LOOP", required_capabilities=[], permissions=[], goal="Resolve declared dependent subproblems.")
    plan = {"action_id": _decision_id(decision), "how_mode": "delegate", "act_mode": "spawn_practitioners",
            "capability_ref": "", "arguments": {}, "steps": ["resolve dependencies"],
            "spawned_tasks": assignments, "rationale": "Use exact typed prerequisite outputs."}
    verification = json.loads(_success_answers()[-2]); verification["scores"] = [1.0] * max(1, len(assignments))
    plan_json = json.dumps(plan) if plan_text is None else plan_text(plan)
    answers = (json.dumps(_orientation(candidate_capabilities=[])), json.dumps({"actions": [decision]}), plan_json,
               json.dumps(verification), json.dumps({"route": "continue" if parent_finishes else "stop_success", "reason": "The subproblems returned."}))
    # a second plan answer in case the runtime asks for a repair
    answers = answers[:3] + (plan_json,) + answers[3:]
    host = _fixture() if parent_finishes else None
    if host is not None: answers += _answers(host)
    events = []
    with tempfile.TemporaryDirectory(prefix="probe-public-") as root:
        try:
            output = run_adaptive_practitioner(
                AdaptivePractitionerRequest("Resolve the root with independently accepted dependent work.", runs_dir=root, mode="hybrid",
                                            max_passes=2 if parent_finishes else 1, quiet_model_io=True),
                AdaptivePractitionerDependencies(fixture_model_execution(FixtureModelExecutionRequest(answers=answers, max_model_calls=len(answers))),
                                                 deterministic_resolvers=(ExactDependencyResolver(),), host_runtime=host.binding if host is not None else None))
        except BaseException as exc:
            return {"CRASH": f"{type(exc).__name__}: {str(exc)[:300]}"}, observed, None, []
        history = output["run_history"]
        try:
            saved = RunHistory.load(str(Path(history["path"]).parent), output["run_id"])
            events = [dict(e.detail) for e in saved.event_log]
            intact = saved.verify_chain()["intact"]
        except Exception as exc:
            intact = f"history load failed: {exc}"
    return output, observed, intact, events

def brief(output):
    if "CRASH" in output: return output
    return {k: output.get(k) for k in ("status", "solved", "failure_code", "final_route", "model_calls", "task_results")} | {
        "failures": [str(f)[:160] for f in (output.get("failures") or [])][:3],
        "spawned": [{k: v for k, v in s.items() if k in ("task_id", "task_complete", "completes_spawning_task", "binding_disposition", "verification_kind", "error_type", "accepted_result")} for s in output.get("spawned_results", [])]}

if __name__ == '__main__':
    producer = assignment("source")
    consumer = assignment("consumer", dependencies=("source",), inputs=(input_binding(),), output=None)

    print("===== canonical fixture [consumer, producer] =====")
    t0 = time.time(); output, observed, intact, events = public_run2([consumer, producer]); print(f"{time.time()-t0:.1f}s")
    print("observed task order:", [p["task_id"] for p in observed]); print(json.dumps(brief(output), default=str)[:1500]); print("chain intact:", intact)
    kinds = [e.get("custom_kind") for e in events if e.get("custom_kind")]
    print("dependency kinds:", [k for k in kinds if "dependency" in k or "spawned_result" in k])
    # Part 2(e): step events per loop
    by_loop = {}
    for e in events:
        if e.get("event") == "run_step": by_loop.setdefault(e.get("loop_id"), []).append((e.get("step"), str(e.get("output"))[:40], e.get("accepted")))
    for lid, steps in by_loop.items(): print(f"  run_step events for {lid}: n={len(steps)}", steps[:10])
    inits = {e.get("loop_id"): (e.get("goal","")[:40], e.get("role"), e.get("relationship_kind")) for e in events if e.get("event") == "init"}
    print("loops:", inits)
    # parent certification evidence: any event on the parent citing spawned success as verification?
    parent = next((lid for lid, (g, r, k) in inits.items() if k == "starting"), None)
    print("parent loop:", parent, "| parent-level accepted/verification events mentioning spawned:", [ (e.get("event"), e.get("custom_kind")) for e in events if e.get("loop_id") == parent and any(s in json.dumps(e, default=str) for s in ("completes_spawning_task", "spawned_task_complete"))][:6])
    print("terminal events:", [(e.get("loop_id"), e.get("reason")) for e in events if e.get("event") == "terminal"])

    print("\n===== reference delivery: history honesty =====")
    rc = deepcopy(consumer); rc["inputs"][0]["delivery"] = "reference"
    output, observed, intact, events = public_run2([producer, rc])
    handed = next((p for p in observed if p["task_id"] == "consumer"), {}).get("dependency_inputs")
    print("consumer received:", json.dumps(handed)[:300])
    print("information events:", [(e.get("loop_id"), e.get("custom_kind") or e.get("event"), e.get("observation_kind") or e.get("kind") or e.get("status")) for e in events if "information_" in json.dumps(e, default=str)][:8])
    print(json.dumps(brief(output), default=str)[:600])

    print("\n===== cyclic / self-dependent plans through the public planning gate =====")
    for label, plan in (("self_dependency", [assignment("a", dependencies=("a",), output=None)]),
                        ("three_cycle", [assignment("x", dependencies=("z",), output=None), assignment("y", dependencies=("x",), output=None), assignment("z", dependencies=("y",), output=None)])):
        output, observed, intact, events = public_run2(plan)
        print(f"[{label}]", json.dumps(brief(output), default=str)[:700])
        print("   diagnostics:", [ (e.get("custom_kind"), str(e.get("error") or e.get("detail") or "")[:120]) for e in events if e.get("custom_kind") in ("execution_plan_invalid", "diagnostic") or "plan_invalid" in json.dumps(e)][:4])

    print("\n===== deeply nested schema in a model plan (RecursionError surface) =====")
    nested = '{"type":"array","items":' * 1500 + '{"type":"integer"}' + '}' * 1500
    p = deepcopy(producer); p["output_contract"]["schema"] = "__NESTED__"
    output, observed, intact, events = public_run2([consumer, p], plan_text=lambda plan: json.dumps(plan).replace('"__NESTED__"', nested))
    print(json.dumps(brief(output), default=str)[:700])

    print("\n===== NaN / Infinity / huge / big values from the producer =====")
    pnum = deepcopy(producer); pnum["output_contract"]["schema"] = {"type": "array", "items": {"type": "number"}}
    for label, prod, value in (("nan", pnum, [float("nan")]), ("inf", pnum, [float("inf")]), ("huge_int", producer, [10 ** 5000]), ("big_list_200k", producer, list(range(200_000)))):
        t0 = time.time(); output, observed, intact, events = public_run2([consumer, prod], source_value=value)
        b = brief(output)
        if "spawned" in b:
            for s in b["spawned"]:
                if isinstance(s.get("accepted_result"), dict): s["accepted_result"] = str(s["accepted_result"])[:80]
        print(f"[{label}] {time.time()-t0:.1f}s observed={[p['task_id'] for p in observed]}", json.dumps(b, default=str)[:900])

    print("\n===== consumer output that violates nothing but is not what the parent needs: parent certification =====")
    output, observed, intact, events = public_run2([consumer, producer], parent_finishes=False)
    print("parent says stop_success right after spawn -> solved:", output.get("solved"), "status:", output.get("status"), "failure_code:", output.get("failure_code"), "| task_results:", output.get("task_results"))
