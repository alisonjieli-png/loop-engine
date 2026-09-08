import json, tempfile
from pathlib import Path
from loop_engine.core.adaptive_practitioner_bindings_checks import assignment, input_binding
from loop_engine.core.run_history import RunHistory
from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
from loop_engine.core.adaptive_practitioner import run_adaptive_practitioner
from loop_engine.core.adaptive_practitioner_acceptance_checks import _decision, _decision_id, _orientation, _success_answers
from loop_engine.core.adaptive_practitioner_records import AdaptivePractitionerDependencies, AdaptivePractitionerRequest
producer = assignment("source"); consumer = assignment("consumer", dependencies=("source",), inputs=(input_binding(),), output=None)
class R:
    resolver_id = "fixture.dependency_values"
    def supports(self, task):
        try: return json.loads(task).get("record_type") == "delegated_problem/v1"
        except (ValueError, AttributeError): return False
    def execute(self, task):
        packet = json.loads(task)
        return {"verified": True, "value": [2, 3]} if packet["task_id"] == "source" else {"verified": True, "value": sum(packet["dependency_inputs"][0]["value"])}
decision = _decision("SPAWN_LOOP", required_capabilities=[], permissions=[], goal="g")
plan = {"action_id": _decision_id(decision), "how_mode": "delegate", "act_mode": "spawn_practitioners", "capability_ref": "", "arguments": {}, "steps": ["s"], "spawned_tasks": [consumer, producer], "rationale": "r"}
verification = json.loads(_success_answers()[-2]); verification["scores"] = [1.0, 1.0]
answers = tuple(json.dumps(x) for x in (_orientation(candidate_capabilities=[]), {"actions": [decision]}, plan, verification, {"route": "stop_success", "reason": "done"}))
with tempfile.TemporaryDirectory(prefix="probe-history-") as root:
    output = run_adaptive_practitioner(AdaptivePractitionerRequest("root", runs_dir=root, mode="hybrid", max_passes=1, quiet_model_io=True),
        AdaptivePractitionerDependencies(fixture_model_execution(FixtureModelExecutionRequest(answers=answers, max_model_calls=len(answers))), deterministic_resolvers=(R(),)))
    saved = RunHistory.load(str(Path(output["run_history"]["path"]).parent), output["run_id"])
    log = list(saved.event_log)
    hist = {}
    for e in log: hist[e.event_type] = hist.get(e.event_type, 0) + 1
    print("event_type histogram:", dict(sorted(hist.items(), key=lambda kv: -kv[1])))
    by_loop = {}
    for e in log:
        if e.event_type == "run_step":
            by_loop.setdefault(e.loop_id, []).append((e.step, str(e.detail.get("output"))[:36], e.detail.get("accepted"), e.status))
    for lid, s in by_loop.items():
        print(f"run_step in persisted history for {lid}: n={len(s)} accepted={sum(1 for x in s if x[2])}")
        for x in s: print("     ", x)
    print("init events:", [(e.loop_id, e.detail.get("goal", "")[:28], e.detail.get("relationship_kind"), e.spawning_loop_id) for e in log if e.event_type == "init"])
    print("terminal events:", [(e.loop_id, e.detail.get("reason"), e.status) for e in log if e.event_type == "terminal"])
    print("custom kinds:", [e.detail.get("custom_kind") for e in log if e.event_type == "custom" and e.detail.get("custom_kind") and ("dependency" in e.detail.get("custom_kind") or "spawned" in e.detail.get("custom_kind") or "kernel" in e.detail.get("custom_kind"))])
    print("chain intact:", saved.verify_chain()["intact"], "| output solved:", output["solved"], "| task_results:", output["task_results"])
