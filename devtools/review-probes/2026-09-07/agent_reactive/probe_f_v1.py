"""F. Version-1 activation reader: legacy acceptance, shape refusal, and whether the legacy label is writable on new records."""
import hashlib
from common import *
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger
from loop_engine.loop.reactive_contracts import ReactiveContractError

out = {}
root = tmpdir("probe-f-")
try:
    scheduler, definition, series, profile = make_scheduler(root)
    trig = _trigger(1, definition); adm = scheduler.admit(trig)
    v2 = adm.activation.to_dict()
    def attempt(label, body):
        try:
            r = ActivationRecord.from_dict(body)
            return {"accepted": True, "disposition": r.history_disposition.value, "history_ref": r.history_ref}
        except ReactiveContractError as exc:
            return {"accepted": False, "error": str(exc)}
    v1 = {**v2, "record_type": "activation_record/v1"}; v1.pop("history_ref"); v1.pop("history_disposition")
    v1_with_history = {**v2, "record_type": "activation_record/v1"}
    v2_missing = {**v2}; v2_missing.pop("history_ref"); v2_missing.pop("history_disposition")
    v2_legacy_label = {**v2, "history_disposition": "legacy_unrecorded"}
    v1_persisted_label = {**v1}
    out["F1_reader_shapes"] = {
        "v1_exact": attempt("v1", v1), "v1_plus_history_keys": attempt("v1h", v1_with_history),
        "v2_missing_history_keys": attempt("v2m", v2_missing),
        "v2_with_legacy_unrecorded_label": attempt("v2l", v2_legacy_label),
        "v3_unknown": attempt("v3", {**v2, "record_type": "activation_record/v3"})}

    # F2: can a NEW worker publish COMPLETED labelled legacy_unrecorded through the real scheduler API?
    claim = scheduler.claim(ActivationClaimRequest("w", "2026-09-07T00:00:01Z", 60, series.series_id))
    scheduler.start(ActivationStartRequest(claim.activation.activation_id, claim.lease.lease_id, claim.lease.fencing_token, "2026-09-07T00:00:01Z"))
    try:
        t = scheduler.terminal(ActivationTerminalRequest(claim.activation.activation_id, claim.lease.lease_id, claim.lease.fencing_token,
            ActivationStatus.COMPLETED, "2026-09-07T00:00:02Z", "loop-new", "ACCEPTED",
            history_disposition=ActivationHistoryDisposition.LEGACY_UNRECORDED))
        raw = scheduler._connection.execute("SELECT body FROM reactive_activation_revisions WHERE activation_id=? ORDER BY revision DESC LIMIT 1", (t.activation_id,)).fetchone()[0]
        out["F2_new_record_labelled_legacy"] = {"accepted": True, "reader_disposition": scheduler.get_activation(t.activation_id).history_disposition.value,
                                                "stored_record_type": json.loads(raw)["record_type"]}
    except Exception as exc:
        out["F2_new_record_labelled_legacy"] = {"accepted": False, "error": f"{type(exc).__name__}: {exc}"}

    # F3: a genuine v1 row (rewritten in place with a valid digest) for a LEASED activation, then recovery + rerun
    trig2 = _trigger(2, definition); adm2 = scheduler.admit(trig2)
    c2 = scheduler.claim(ActivationClaimRequest("old-worker", "2026-09-07T00:01:00Z", 1, series.series_id))
    leased = c2.activation.to_dict(); leased["record_type"] = "activation_record/v1"; leased.pop("history_ref"); leased.pop("history_disposition")
    body = json.dumps(leased, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    scheduler._connection.execute("UPDATE reactive_activation_revisions SET body=?, record_digest=? WHERE activation_id=? AND revision=?",
                                  (body, hashlib.sha256(body.encode()).hexdigest(), c2.activation.activation_id, c2.activation.revision))
    scheduler._connection.commit()
    read_v1 = scheduler.get_activation(trig2.activation_id)
    scheduler.recover_expired("2026-09-07T00:01:05Z")
    executor = make_executor(definition, ok_outcome)
    o = run_once(scheduler, executor, series, worker="new-worker", at="2026-09-07T00:01:06Z")
    revs = scheduler.activation_history(trig2.activation_id)
    raw_types = [json.loads(r[0])["record_type"] for r in scheduler._connection.execute(
        "SELECT body FROM reactive_activation_revisions WHERE activation_id=? ORDER BY revision", (trig2.activation_id,)).fetchall()]
    out["F3_v1_row_recovered_and_rerun"] = {"v1_row_reads_as": read_v1.history_disposition.value,
        "revisions": [(r.revision, r.status.value, r.history_disposition.value, rt) for r, rt in zip(revs, raw_types)],
        "final_terminal_code": o.terminal_code}
    scheduler.close()
finally:
    shutil.rmtree(root, ignore_errors=True)
dump("probe_f_v1.out.json", out)
print(json.dumps(out, indent=1, default=str))
