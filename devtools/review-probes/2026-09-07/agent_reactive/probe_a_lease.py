"""A. Lease/attempt semantics: attempt counting, expiry boundary, foreign publish with a readable fence."""
from common import *
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger

out = {}
root = tmpdir("probe-a-")
try:
    # A1: max_attempts=2 -> how many leases can be granted before dead letter?
    scheduler, definition, series, profile = make_scheduler(root, max_attempts=2)
    adm = scheduler.admit(_trigger(1, definition))
    granted = []
    c1 = scheduler.claim(ActivationClaimRequest("w1", "2026-09-07T00:00:00Z", 1, series.series_id))
    granted.append((c1.activation.attempt, c1.lease.fencing_token, c1.lease.expires_at))
    # A1b: boundary -- recover at EXACTLY expires_at
    rec_boundary = scheduler.recover_expired(c1.lease.expires_at)
    out["boundary_recover_at_exact_expires_at"] = {
        "expires_at": c1.lease.expires_at,
        "recovered": [r.status.value for r in rec_boundary],
        "note": "expires_at > now is the validity test, so a lease is treated as expired at the exact instant expires_at"}
    c2 = scheduler.claim(ActivationClaimRequest("w2", "2026-09-07T00:00:02Z", 1, series.series_id))
    granted.append((c2.activation.attempt, c2.lease.fencing_token, c2.lease.expires_at))
    rec2 = scheduler.recover_expired("2026-09-07T00:00:05Z")
    c3 = scheduler.claim(ActivationClaimRequest("w3", "2026-09-07T00:00:06Z", 1, series.series_id))
    final = scheduler.get_activation(adm.activation.activation_id)
    out["attempt_counting"] = {
        "max_attempts": 2, "leases_granted": granted, "third_claim": c3,
        "final_status": final.status.value, "final_failure_code": final.failure_code,
        "final_attempt": final.attempt,
        "revision_statuses": [r.status.value for r in scheduler.activation_history(adm.activation.activation_id)]}
    scheduler.close()

    # A2: two processes on one DB: fence token is readable; foreign publisher can commit terminal
    rootb = root / "b"; rootb.mkdir()
    A, definition, series, profile = make_scheduler(rootb)
    B = SQLiteReactiveScheduler(str(rootb / "scheduler.sqlite")); B.register_profile(profile); B.register_series(series)
    adm = A.admit(_trigger(1, definition))
    ca = A.claim(ActivationClaimRequest("worker-A", "2026-09-07T00:00:00Z", 60, series.series_id))
    A.start(ActivationStartRequest(ca.activation.activation_id, ca.lease.lease_id, ca.lease.fencing_token, "2026-09-07T00:00:00Z"))
    # B never claimed; it only reads the durable record
    seen = B.get_activation(adm.activation.activation_id)
    b_claim = B.claim(ActivationClaimRequest("worker-B", "2026-09-07T00:00:01Z", 60, series.series_id))
    foreign = None; foreign_error = None
    try:
        foreign = B.terminal(ActivationTerminalRequest(seen.activation_id, seen.lease_id, seen.fencing_token,
            ActivationStatus.COMPLETED, "2026-09-07T00:00:02Z", "forged-loop-by-B", "ACCEPTED"))
    except Exception as exc:
        foreign_error = f"{type(exc).__name__}: {exc}"
    owner_error = None
    try:
        A.terminal(ActivationTerminalRequest(ca.activation.activation_id, ca.lease.lease_id, ca.lease.fencing_token,
            ActivationStatus.COMPLETED, "2026-09-07T00:00:03Z", "real-loop-by-A", "ACCEPTED"))
    except Exception as exc:
        owner_error = f"{type(exc).__name__}: {exc}"
    out["foreign_publish_with_readable_fence"] = {
        "B_claim_while_A_holds_lease": b_claim,
        "fence_readable_by_B": {"lease_id": seen.lease_id, "fencing_token": seen.fencing_token, "worker_id": seen.worker_id},
        "B_terminal_accepted": foreign is not None, "B_terminal_error": foreign_error,
        "published_loop_id": foreign.loop_id if foreign else None,
        "published_worker_id_field": foreign.worker_id if foreign else None,
        "A_owner_terminal_error": owner_error,
        "request_has_worker_id_field": "worker_id" in ActivationTerminalRequest.__dataclass_fields__}
    A.close(); B.close()
finally:
    shutil.rmtree(root, ignore_errors=True)
dump("probe_a_lease.out.json", out)
print(json.dumps(out, indent=1, default=str))
