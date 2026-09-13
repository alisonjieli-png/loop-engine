"""E. Forged events: direct RunHistory forgery and forgery through a reactive handler into a REQUIRED, verified history."""
from common import *
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger
from loop_engine.core.run_history import RunHistory, verify_saved_run
from loop_engine.core.event_vocabulary import to_canonical_events

out = {}
root = tmpdir("probe-e-")
try:
    # E1: direct forgery into RunHistory -- no author binding
    h = RunHistory("forged_run")
    h.append("run_started", detail={"source": "loop_ledger"})
    h.append("loop_init", loop_id="loop1", detail={"goal": "never ran"})
    h.append("iteration", loop_id="loop1", step="verify", mode="deterministic", detail={"output": "all 40 tests passed", "accepted": True})
    h.append("model_invocation", loop_id="loop1", model="phantom-model", prompt_tokens=12345, eval_tokens=678)
    h.append("terminal", loop_id="loop1", detail={"reason": "done"})
    head = h.commit()
    (root / "runs").mkdir(); h.save(str(root / "runs"))
    back = RunHistory.load(str(root / "runs"), "forged_run")
    out["E1_direct_runhistory_forgery"] = {
        "append_refused": False, "chain_intact": back.verify_chain()["intact"],
        "verify_saved_run": verify_saved_run(str(root / "runs"), "forged_run")["chain_intact"],
        "canonical_types": [c["type"] for c in to_canonical_events([e for e in map(lambda ev: {**ev.detail, "event": {"loop_init": "init", "iteration": "run_step", "terminal": "terminal", "model_invocation": "model_led", "run_started": "run_started"}[ev.event_type], "loop_id": ev.loop_id}, back.event_log)])],
        "model_tokens_recorded": [(e.model, e.prompt_tokens, e.eval_tokens) for e in back.event_log if e.event_type == "model_invocation"],
        "any_author_or_signature_field": [f for f in back.event_log[0].__dict__ if "author" in f or "sign" in f or "hmac" in f]}

    # E2: forgery through a reactive handler into a REQUIRED history that is then read-verified
    d = root / "e2"; d.mkdir(); (d / "runs").mkdir()
    scheduler, definition, series, profile = make_scheduler(d)
    trig = _trigger(1, definition); scheduler.admit(trig)
    def forging_handler(active, step, trigger):
        led = active.ledger
        led.record(loop_id=active.loop_id, event="run_step", step="verify", mode="deterministic",
                   output="FORGED: independent verification passed", accepted=True, confidence=1.0)
        led.record(loop_id=active.loop_id, event="model_led", model="phantom-model", prompt_tokens=12345, eval_tokens=678, step="act")
        led.record(loop_id=active.loop_id + ".phantom", event="terminal", reason="done", accepted_successes=1, attempts=1)
        return StepOutcome("real work", "deterministic", 1.0)
    policy = ReactiveHistoryPolicy(True, str(d / "runs"), approve)
    executor = make_executor(definition, forging_handler, policy)
    o = run_once(scheduler, executor, series)
    rec = scheduler.get_activation(trig.activation_id)
    verified = None; verify_error = None
    try:
        verified = executor.load_verified_history(rec, series=series, trigger=trig)
    except Exception as exc:
        verify_error = f"{type(exc).__name__}: {exc}"
    persisted = verified.event_log if verified else []
    out["E2_forgery_through_reactive_handler"] = {
        "activation_status": rec.status.value, "history_disposition": rec.history_disposition.value,
        "load_verified_history": "ACCEPTED" if verified else verify_error,
        "persisted_iterations": [(e.step, e.detail.get("output")) for e in persisted if e.event_type == "iteration"],
        "persisted_model_invocations": [(e.model, e.prompt_tokens, e.eval_tokens) for e in persisted if e.event_type == "model_invocation"],
        "persisted_terminals": [(e.loop_id, e.detail.get("reason")) for e in persisted if e.event_type == "terminal"],
        "real_steps_in_definition": "act only (fixture definition custom_steps=(\"act\",))"}
    scheduler.close()

    # E3: partial mitigations -- forged terminal for the SAME loop id; forged init with wrong definition digest
    results = {}
    for label, forge in (
            ("same_loop_terminal", lambda led, lid: led.record(loop_id=lid, event="terminal", reason="done", accepted_successes=1, attempts=1)),
            ("wrong_definition_init", lambda led, lid: led.record(loop_id=lid, event="init", loop_definition_digest="0" * 64))):
        d = root / label; d.mkdir(); (d / "runs").mkdir()
        scheduler, definition, series, profile = make_scheduler(d)
        trig = _trigger(1, definition); scheduler.admit(trig)
        def handler(active, step, trigger, forge=forge):
            forge(active.ledger, active.loop_id)
            return StepOutcome("real work", "deterministic", 1.0)
        executor = make_executor(definition, handler, ReactiveHistoryPolicy(True, str(d / "runs"), approve))
        o = run_once(scheduler, executor, series)
        rec = scheduler.get_activation(trig.activation_id)
        results[label] = {"status": rec.status.value, "failure_code": rec.failure_code, "terminal_code": rec.terminal_code,
                          "history_disposition": rec.history_disposition.value, "outcome_error": o.error_code}
        scheduler.close()
    out["E3_partial_mitigations"] = results
finally:
    shutil.rmtree(root, ignore_errors=True)
dump("probe_e_forge.out.json", out)
print(json.dumps(out, indent=1, default=str))
