"""G1. Natural (unforced) race: worker thread A calls terminal(), peer thread B calls recover_expired(), each on its OWN
scheduler connection (as two worker processes would). No monkeypatching; a Barrier only aligns the start of each round."""
import sqlite3, threading
from common import *
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger

out = {}
root = tmpdir("probe-g-")
try:
    M, definition, series, profile = make_scheduler(root, max_active=1000)
    path = str(root / "scheduler.sqlite")
    ROUNDS = 150
    start_barrier, end_barrier = threading.Barrier(3), threading.Barrier(3)
    shared = {"claim": None, "stop": False, "errors": [], "wedged": {}}

    def worker(label, action):
        S = SQLiteReactiveScheduler(path); S.register_profile(profile); S.register_series(series)
        for i in range(ROUNDS):
            start_barrier.wait()
            if not shared["stop"]:
                try:
                    action(S, shared["claim"])
                except Exception as exc:
                    shared["errors"].append((i, label, type(exc).__name__))
                try:
                    S._connection.execute("BEGIN IMMEDIATE"); S._connection.rollback()
                except sqlite3.OperationalError as exc:
                    shared["wedged"].setdefault(label, (i, str(exc)))
            end_barrier.wait()
        S.close()

    def a_terminal(S, c):
        S.terminal(ActivationTerminalRequest(c.activation.activation_id, c.lease.lease_id, c.lease.fencing_token,
            ActivationStatus.COMPLETED, "2026-09-07T00:00:05Z", "loop-a", "ACCEPTED"))
    def b_recover(S, c):
        S.recover_expired("2026-09-07T00:00:05Z")

    ta = threading.Thread(target=worker, args=("A", a_terminal)); tb = threading.Thread(target=worker, args=("B", b_recover))
    ta.start(); tb.start()
    rounds_done = 0
    for i in range(ROUNDS):
        if not shared["stop"]:
            try:
                trig = _trigger(i + 1, definition); M.admit(trig)
                c = M.claim(ActivationClaimRequest("worker-A", "2026-09-07T00:00:00Z", 1, series.series_id))
                M.start(ActivationStartRequest(c.activation.activation_id, c.lease.lease_id, c.lease.fencing_token, "2026-09-07T00:00:00Z"))
                shared["claim"] = c; rounds_done = i + 1
            except Exception as exc:
                shared["errors"].append((i, "main", f"{type(exc).__name__}: {exc}")); shared["stop"] = True
        start_barrier.wait(); end_barrier.wait()
        if shared["wedged"]:
            shared["stop"] = True
    ta.join(); tb.join()
    from collections import Counter
    out["G1_natural_race"] = {
        "rounds_driven": rounds_done,
        "error_counts": {f"{lbl}:{name}": n for (lbl, name), n in Counter((lbl, name) for _, lbl, name in shared["errors"] if lbl != "main").items()},
        "main_errors": [e for e in shared["errors"] if e[1] == "main"][:3],
        "wedged_connections": shared["wedged"],
        "note": "IntegrityError = lost the PK race on (activation_id, revision); wedged = the losing connection can no longer BEGIN IMMEDIATE"}
    M.close()
finally:
    shutil.rmtree(root, ignore_errors=True)
dump("probe_g_natural_race.out.json", out)
print(json.dumps(out, indent=1, default=str))
