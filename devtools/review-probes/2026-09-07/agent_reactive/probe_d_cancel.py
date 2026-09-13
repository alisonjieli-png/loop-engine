"""D. Cancellation: late handler return, usage projection, output retention, cancel-after-accepted."""
from common import *
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopError
from loop_engine.core.run_history import RunHistory
from loop_engine.core.event_vocabulary import to_canonical_events

out = {}
def loop():
    return Loop("cooperative cancellation", LoopConfig(framework="custom", custom_steps=("act",),
        allowable_modes=("deterministic", "hybrid"), preferred_modes=("deterministic",), exit_condition="accepted_success"))

# D1: late return after cancel with one model call: ledger vs RunHistory vs OTel
lp = loop()
def cancel_then_return(active, step, context):
    active.cancel("operator stop")
    return StepOutcome("SECRET late output", "hybrid", 1.0, model_calls=1, spawn_goal="must not start")
res = lp.run(handler=cancel_then_return)
hist = RunHistory.from_ledger(lp.ledger.events, run_id="d1"); hist.commit()
spans = hist.to_otel_spans()
out["D1_late_return_usage"] = {
    "terminal_code": res.terminal_code, "result_model_calls": res.model_calls, "spawned": res.spawned,
    "ledger_reported_model_calls": [e.get("reported_model_calls") for e in lp.ledger.events if e.get("custom_kind") == "terminal_handler_return"],
    "run_history_model_invocation_events": sum(1 for e in hist.event_log if e.event_type == "model_invocation"),
    "run_history_event_types": [e.event_type for e in hist.event_log],
    "otel_model_spans": sum(1 for s in spans if s["kind"] == "model"),
    "late_output_retained_anywhere": any("SECRET" in json.dumps(e, default=str) for e in lp.ledger.events) or "SECRET" in res.output,
    "result_final_output": res.output}

# D2: over-reported usage after cancel (model_calls=2)
lp = loop()
def cancel_then_over(active, step, context):
    active.cancel("operator stop")
    return StepOutcome("x", "hybrid", 1.0, model_calls=2)
err = None
try: lp.run(handler=cancel_then_over)
except LoopError as exc: err = str(exc)
out["D2_overreported_usage_after_cancel"] = {"raised": err, "terminal_code": lp.result().terminal_code,
                                             "model_calls_recorded": lp.result().model_calls,
                                             "any_usage_event": [e for e in lp.ledger.events if e.get("reported_model_calls") is not None]}

# D3: cancel() after ACCEPTED terminal: relabel refused, but a cancel event is still appended
lp = loop()
res = lp.run(handler=lambda a, s, c: StepOutcome("ok", "deterministic", 1.0))
lp.cancel("late operator cancel")
events = [e.get("event") for e in lp.ledger.events]
canon = [c["type"] for c in to_canonical_events(lp.ledger.events)]
out["D3_cancel_after_accepted"] = {"terminal_code_after_cancel": lp.result().terminal_code,
    "terminal_events": events.count("terminal"), "cancel_events": events.count("cancel"),
    "ledger_tail": events[-3:], "canonical_tail": canon[-3:],
    "cancel_event_position_after_terminal": events.index("cancel") > events.index("terminal")}

dump("probe_d_cancel.out.json", out)
print(json.dumps(out, indent=1, default=str))
