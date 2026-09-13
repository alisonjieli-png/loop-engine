"""B. recover_expired() vs late terminal(): deterministic interleaving of two scheduler connections on one DB.
The interleaving is forced by wrapping _append_activation so the peer commits between the read and the insert --
the same ordering two polling worker processes can produce."""
import sqlite3
from common import *
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger

out = {}
root = tmpdir("probe-b-")
try:
    # B1: peer B recovers (dead-letters) an expired RUNNING activation; owner A's late terminal commits first.
    A, definition, series, profile = make_scheduler(root)
    B = SQLiteReactiveScheduler(str(root / "scheduler.sqlite")); B.register_profile(profile); B.register_series(series)
    adm = A.admit(_trigger(1, definition))
    ca = A.claim(ActivationClaimRequest("worker-A", "2026-09-07T00:00:00Z", 1, series.series_id))
    A.start(ActivationStartRequest(ca.activation.activation_id, ca.lease.lease_id, ca.lease.fencing_token, "2026-09-07T00:00:00Z"))
    real_append = B._append_activation
    state = {"fired": False}
    def interleaved(record):
        if not state["fired"]:
            state["fired"] = True
            A.terminal(ActivationTerminalRequest(ca.activation.activation_id, ca.lease.lease_id, ca.lease.fencing_token,
                ActivationStatus.COMPLETED, "2026-09-07T00:00:02Z", "loop-a", "ACCEPTED"))
        return real_append(record)
    B._append_activation = interleaved
    b1 = {}
    try:
        B.recover_expired("2026-09-07T00:00:02Z")
        b1["recover_raised"] = None
    except Exception as exc:
        b1["recover_raised"] = f"{type(exc).__name__}: {exc}"
    b1["B_connection_in_transaction_after"] = B._connection.in_transaction
    try:
        B.claim(ActivationClaimRequest("worker-B", "2026-09-07T00:00:03Z", 1, series.series_id))
        b1["next_claim_raised"] = None
    except Exception as exc:
        b1["next_claim_raised"] = f"{type(exc).__name__}: {exc}"
    try:
        B.claim(ActivationClaimRequest("worker-B", "2026-09-07T00:00:04Z", 1, series.series_id))
        b1["second_next_claim_raised"] = None
    except Exception as exc:
        b1["second_next_claim_raised"] = f"{type(exc).__name__}: {exc}"
    b1["durable_final_status"] = A.get_activation(adm.activation.activation_id).status.value
    out["B1_recovery_loses_pk_race_to_late_terminal"] = b1
    A.close(); B.close()

    # B2: through the REAL worker: owner A's terminal loses the race to peer B's recovery.
    root2 = root / "two"; root2.mkdir()
    A, definition, series, profile = make_scheduler(root2)
    B = SQLiteReactiveScheduler(str(root2 / "scheduler.sqlite")); B.register_profile(profile); B.register_series(series)
    adm = A.admit(_trigger(1, definition))
    real_append = A._append_activation
    state = {"fired": False}
    def interleaved_terminal(record):
        if record.status.terminal and not state["fired"]:
            state["fired"] = True
            B.recover_expired("2026-09-07T00:00:05Z")   # peer dead-letters the expired RUNNING record first
        return real_append(record)
    A._append_activation = interleaved_terminal
    executor = make_executor(definition, ok_outcome)
    b2 = {}
    try:
        outcome = run_once(A, executor, series, worker="worker-A", at="2026-09-07T00:00:00Z", lease=1,
                           terminal_at="2026-09-07T00:00:05Z")
        b2["run_once_outcome"] = {"claimed": outcome.claimed, "terminal_code": outcome.terminal_code,
                                  "error_code": outcome.error_code, "loop_id": outcome.loop_id}
    except Exception as exc:
        b2["run_once_raised"] = f"{type(exc).__name__}: {exc}"
    b2["A_connection_in_transaction_after"] = A._connection.in_transaction
    A.admit(_trigger(2, definition)) if False else None
    try:
        A.claim(ActivationClaimRequest("worker-A", "2026-09-07T00:00:06Z", 1, series.series_id))
        b2["next_claim_on_A_raised"] = None
    except Exception as exc:
        b2["next_claim_on_A_raised"] = f"{type(exc).__name__}: {exc}"
    b2["durable_final"] = {k: getattr(B.get_activation(adm.activation.activation_id), k) for k in ("status", "failure_code", "loop_id")}
    b2["loop_actually_terminal_code"] = executor.ledger_for(adm.activation.activation_id).events[-1].get("reason")
    out["B2_worker_terminal_loses_pk_race_to_peer_recovery"] = b2
    A.close(); B.close()

    # B3: run_many loses sibling outcomes when one run_once raises outside its try (stale fence at start)
    root3 = root / "three"; root3.mkdir()
    A, definition, series, profile = make_scheduler(root3, max_active=3)
    B = SQLiteReactiveScheduler(str(root3 / "scheduler.sqlite")); B.register_profile(profile); B.register_series(series)
    for i in (1, 2, 3):
        A.admit(_trigger(i, definition))
    real_start = A.start
    state = {"fired": False}
    def stolen_start(request):
        if not state["fired"]:
            state["fired"] = True
            # peer recovers the just-granted (unstarted, 1s) lease and re-claims it under a new fence
            B.recover_expired("2026-09-07T00:00:02Z")
            B.claim(ActivationClaimRequest("worker-B", "2026-09-07T00:00:02Z", 60, series.series_id))
        return real_start(request)
    A.start = stolen_start
    executor = make_executor(definition, ok_outcome)
    b3 = {}
    async def many():
        worker = AsyncReactiveWorker(A, executor)
        reqs = tuple(ReactiveWorkerRequest(ActivationClaimRequest(f"worker-A{i}", "2026-09-07T00:00:00Z", 1, series.series_id),
                                           "2026-09-07T00:00:00Z", "2026-09-07T00:00:00Z") for i in (1, 2, 3))
        return await worker.run_many(reqs)
    try:
        res = asyncio.run(many())
        b3["run_many_returned"] = [(r.claimed, r.terminal_code, r.error_code) for r in res]
    except Exception as exc:
        b3["run_many_raised"] = f"{type(exc).__name__}: {exc}"
    b3["durable_statuses"] = {t: B.get_activation(_trigger(t, definition).activation_id).status.value for t in (1, 2, 3)}
    out["B3_stale_fence_at_start_escapes_run_once_and_run_many"] = b3
    A.close(); B.close()
finally:
    shutil.rmtree(root, ignore_errors=True)
dump("probe_b_race.out.json", out)
print(json.dumps(out, indent=1, default=str))
