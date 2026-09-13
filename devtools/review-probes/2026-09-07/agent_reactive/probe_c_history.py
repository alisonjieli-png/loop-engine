"""C. ReactiveHistoryPolicy: requirement enforcement, midway persistence failure, reopen verification, orphan history."""
import hashlib, threading, time
from unittest.mock import patch
from common import *
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger
from loop_engine.core.run_history import RunHistory, _digest as rh_digest
from loop_engine.loop.effect_approval import EffectApprovalService
from loop_engine.loop.reactive_contracts import PersistenceMode

out = {}
root = tmpdir("probe-c-")
try:
    # C1: profile persistence DURABLE_SERIES + default binding (no policy) -> COMPLETED without history
    scheduler, definition, series, profile = make_scheduler(root / "c1")
    scheduler.admit(_trigger(1, definition))
    executor = make_executor(definition, ok_outcome)  # default ReactiveHistoryPolicy()
    o = run_once(scheduler, executor, series)
    rec = scheduler.get_activation(_trigger(1, definition).activation_id)
    out["C1_durable_series_profile_default_binding"] = {
        "profile_persistence": profile.persistence.value, "status": rec.status.value,
        "history_disposition": rec.history_disposition.value, "history_ref": rec.history_ref,
        "worker_reads_profile_persistence": False}
    scheduler.close()

    # C2: persistence fails AFTER RunHistory.save succeeded (approval restore raises)
    d = root / "c2"; d.mkdir(); (d / "runs").mkdir()
    scheduler, definition, series, profile = make_scheduler(d)
    scheduler.admit(_trigger(1, definition))
    policy = ReactiveHistoryPolicy(True, str(d / "runs"), approve)
    executor = make_executor(definition, ok_outcome, policy)
    with patch.object(EffectApprovalService, "restore", side_effect=OSError("disk full after save")):
        o = run_once(scheduler, executor, series)
    rec = scheduler.get_activation(_trigger(1, definition).activation_id)
    on_disk = sorted(p.name for p in (d / "runs").iterdir())
    manifest = json.loads((d / "runs" / on_disk[0] / "manifest.json").read_text()) if on_disk else None
    retry = scheduler.claim(ActivationClaimRequest("retry", "2026-09-07T00:01:00Z", 60, series.series_id))
    out["C2_failure_after_save"] = {
        "status": rec.status.value, "failure_code": rec.failure_code, "terminal_code": rec.terminal_code,
        "history_disposition": rec.history_disposition.value, "outcome_error_code": o.error_code,
        "orphan_run_dirs_on_disk": on_disk, "orphan_manifest_committed": manifest and manifest.get("committed"),
        "attempt": rec.attempt, "max_attempts": series.maximum_attempts_per_trigger, "retry_claim": retry,
        "exception_type_lost_in_durable_record": rec.failure_code == "HISTORY_PERSISTENCE_FAILED"}
    scheduler.close()

    # C3: reopen verification -- rewrite a middle event and RE-DIGEST the whole chain and manifest
    d = root / "c3"; d.mkdir(); (d / "runs").mkdir()
    scheduler, definition, series, profile = make_scheduler(d)
    trig = _trigger(1, definition); scheduler.admit(trig)
    policy = ReactiveHistoryPolicy(True, str(d / "runs"), approve)
    executor = make_executor(definition, ok_outcome, policy)
    o = run_once(scheduler, executor, series)
    rec = scheduler.get_activation(trig.activation_id)
    run_dir = d / "runs" / rec.history_ref.run_id
    hist = RunHistory.load(str(d / "runs"), rec.history_ref.run_id)
    # rewrite the iteration output and recompute digests forward
    target = next(e for e in hist.event_log if e.event_type == "iteration")
    target.detail["output"] = "TAMPERED: different answer"
    prev = ""
    for e in hist.event_log:
        e.prev_digest = prev
        e.event_digest = rh_digest(e.body()); prev = e.event_digest
    (run_dir / "events.jsonl").write_text("".join(json.dumps({**e.body(), "event_digest": e.event_digest}, default=str) + "\n" for e in hist.event_log))
    man = json.loads((run_dir / "manifest.json").read_text()); man["head_digest"] = hist.event_log[-1].event_digest
    (run_dir / "manifest.json").write_text(json.dumps(man))
    plain_load_ok = RunHistory.load(str(d / "runs"), rec.history_ref.run_id).verify_chain()["intact"]
    try:
        executor.load_verified_history(rec, series=series, trigger=trig); verified = "ACCEPTED"
    except Exception as exc:
        verified = f"refused: {type(exc).__name__}: {exc}"
    out["C3_redigested_tamper_reopen"] = {"RunHistory.load_alone_accepts_redigested_file": plain_load_ok,
                                          "executor.load_verified_history": verified}
    scheduler.close()

    # C4: asyncio cancel of the awaiting task with REQUIRED history: orphan thread still persists
    d = root / "c4"; d.mkdir(); (d / "runs").mkdir()
    scheduler, definition, series, profile = make_scheduler(d)
    trig = _trigger(1, definition); scheduler.admit(trig)
    started, release, done = threading.Event(), threading.Event(), threading.Event()
    def slow(active, step, trigger):
        started.set(); release.wait(5)
        return StepOutcome("late but complete", "deterministic", 1.0)
    policy = ReactiveHistoryPolicy(True, str(d / "runs"), approve)
    executor = make_executor(definition, slow, policy)
    async def exercise():
        task = asyncio.create_task(AsyncReactiveWorker(scheduler, executor).run_once(ReactiveWorkerRequest(
            ActivationClaimRequest("cancel-await", "2026-09-07T00:00:01Z", 1, series.series_id), "2026-09-07T00:00:01Z", "2026-09-07T00:00:01Z")))
        await asyncio.to_thread(started.wait, 3)
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        release.set()
        # let the orphaned thread finish execute() including _persist_history
        for _ in range(100):
            if list((d / "runs").iterdir()): break
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.3)
    asyncio.run(exercise())
    before = scheduler.get_activation(trig.activation_id)
    recovered = scheduler.recover_expired("2026-09-07T00:00:10Z")
    after = scheduler.get_activation(trig.activation_id)
    dirs = sorted(p.name for p in (d / "runs").iterdir())
    committed = json.loads((d / "runs" / dirs[0] / "manifest.json").read_text()).get("committed") if dirs else None
    out["C4_asyncio_cancel_required_history"] = {
        "status_after_cancel": before.status.value, "status_after_recover": after.status.value,
        "failure_code": after.failure_code, "history_disposition_on_dead_letter": after.history_disposition.value,
        "history_ref_on_dead_letter": after.history_ref, "persisted_run_dirs": dirs, "persisted_manifest_committed": committed}
    scheduler.close()
finally:
    shutil.rmtree(root, ignore_errors=True)
dump("probe_c_history.out.json", out)
print(json.dumps(out, indent=1, default=str))
