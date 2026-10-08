"""One authorized Kaggle metadata read on the canonical Loop and existing private records.

Every operation shares one reservation ceiling and provider hold. Raw bodies,
secret headers, token-introspection bodies and account identity are never
stored. Only the validated metadata projection may enter private Lead records.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time

from loop_engine.loop.service_loop_envelope import ServiceLoopSpec, run_service_operation
from query_multiplier.executors import EMPTY, FAILED, OK, PARTIAL, RATE_LIMITED, REFUSED
from query_multiplier.transport import RequestRefused, Transport, load_policy
from tools import operator_credentials
from .community_intake import Lead
from .community_store import CommunityStore
from .kaggle_engine import KaggleMetadataExecutor
from .kaggle_request import AUTH, ENGINE, KEY_VARIABLE, MAXIMUM_BYTES, MAXIMUM_REQUESTS, REQUEST, RESULT, RIGHTS, KaggleError

ACCESS_ID = "community.source.kaggle.metadata_access"
ACCESS_VERSION = "kaggle_metadata_access/v1"
MAXIMUM_EPOCH = 253402300799


@dataclass(frozen=True)
class KaggleReadOptions:
    state: Path
    network_allowed: bool = False
    writes_allowed: bool = False
    enqueue: bool = False
    credential_reference: str = "kaggle-research-primary"
    credential_manifest: Path | None = None
    request_ceiling: int = MAXIMUM_REQUESTS

    def __post_init__(self):
        if any(type(value) is not bool for value in (self.network_allowed, self.writes_allowed, self.enqueue)):
            raise KaggleError("kaggle_grant_not_boolean")
        if type(self.request_ceiling) is not int or not 1 <= self.request_ceiling <= MAXIMUM_REQUESTS:
            raise KaggleError("kaggle_request_ceiling_invalid")
        if self.network_allowed and self.writes_allowed and not isinstance(self.state, Path):
            raise KaggleError("kaggle_private_state_required")


def _stamp(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _state(previous, ceiling):
    if type(ceiling) is not int or not 1 <= ceiling <= MAXIMUM_REQUESTS:raise KaggleError("kaggle_request_ceiling_invalid")
    if previous is None:return {"record_type": ACCESS_VERSION, "reservations_total": 0, "maximum_requests": ceiling, "request_state": "idle"}
    value = previous["document"]["data"]
    if (value.get("record_type") != ACCESS_VERSION or type(value.get("reservations_total")) is not int
            or not 0 <= value["reservations_total"] <= ceiling or type(value.get("maximum_requests")) is not int or value.get("maximum_requests") != ceiling
            or value.get("request_state") not in ("idle", "pending", "completed", "closed_unknown")):
        raise KaggleError("kaggle_access_record_incompatible")
    for key in ("next_allowed_epoch", "held_until_epoch"):
        if key in value and (type(value[key]) not in (int, float) or not math.isfinite(value[key]) or not 0 <= value[key] <= MAXIMUM_EPOCH):
            raise KaggleError("kaggle_access_record_invalid")
    if "quota_hold" in value and value["quota_hold"] != "unknown_provider_reset":
        raise KaggleError("kaggle_access_record_invalid")
    return dict(value)


def _lock(store):
    store.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(store.root / "scan.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _credential(options, resolver):
    if options.credential_manifest is None:data = operator_credentials.references()
    else:
        path = Path(options.credential_manifest)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
            raise KaggleError("kaggle_credential_manifest_invalid")
        data = json.loads(path.read_text())
    if type(data) is not dict or data.get("record_type") != "operator_credential_references/v1":
        raise KaggleError("kaggle_credential_manifest_invalid")
    keys = data.get("api_keys")
    if type(keys) is not dict:raise KaggleError("kaggle_credential_manifest_invalid")
    spec = keys.get(options.credential_reference, {})
    if (type(spec) is not dict or spec.get("service") != "kaggle" or spec.get("environment") != KEY_VARIABLE
            or spec.get("purpose") != "bounded-research-read"):
        raise KaggleError("kaggle_credential_reference_unbound")
    return operator_credentials.clean_token(resolver(options.credential_reference, data=data))


def _held_until(status, headers, moment, parsed_status):
    waits = [86400] if status in (401, 403) or parsed_status == REFUSED else [60] if status == 429 or parsed_status == RATE_LIMITED else []
    retry = headers.get("retry-after", "")
    if type(retry) is str and retry.isascii() and retry.isdigit():
        waits.append(int(retry) if len(retry) <= 12 else MAXIMUM_EPOCH)
    reset = headers.get("x-ratelimit-reset", "")
    remaining = headers.get("x-ratelimit-remaining", "")
    exhausted = type(remaining) is str and remaining.isascii() and remaining.isdigit() and len(remaining) <= 12 and int(remaining) == 0
    if (exhausted or status == 429 or parsed_status == RATE_LIMITED) and type(reset) is str and reset.isascii() and reset.isdigit() and len(reset) <= 12:
        if moment < int(reset) <= MAXIMUM_EPOCH:waits.append(int(reset) - moment)
    return min(MAXIMUM_EPOCH, moment + max(waits)) if waits else None


def _quota_reset_unknown(status, headers, moment, parsed_status):
    remaining = headers.get("x-ratelimit-remaining")
    if remaining is not None and not (type(remaining) is str and remaining.isascii() and remaining.isdigit() and len(remaining) <= 12):
        return True
    exhausted = remaining is not None and int(remaining) == 0
    if not exhausted and status != 429 and parsed_status != RATE_LIMITED:return False
    reset, retry = headers.get("x-ratelimit-reset", ""), headers.get("retry-after", "")
    known_reset = type(reset) is str and reset.isascii() and reset.isdigit() and len(reset) <= 12 and moment < int(reset) <= MAXIMUM_EPOCH
    known_retry = type(retry) is str and retry.isascii() and retry.isdigit() and len(retry) <= 12 and 0 < int(retry) <= MAXIMUM_EPOCH - moment
    return not (known_reset or known_retry)


def _enqueue(store, items, observed_at):
    for item in items:
        metadata_digest = sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        identity = "community.lead.kaggle." + sha256(item["key"].encode()).hexdigest()
        prior = store.get(identity)
        lead = Lead("kaggle", item["url"], item["title"], None, metadata_digest, (), (), tuple(item["linked_sources"]), 0)
        store.put(identity, "lead", "kaggle", "needs_research", {**lead.to_dict(), "metadata": item,
            "evidence_class": "provider_metadata_unverified", "classification": "no_workflow_hints_inferred",
            "observed_at": observed_at, "rights": dict(RIGHTS), "independent_review": "not_done"}, expected=prior)
    return len(items)


def read_once(selection, options, *, transport=None, resolver=operator_credentials.resolve, clock=time.time):
    engine = KaggleMetadataExecutor(selection)
    request = engine.render({}, selection.to_record(), page=selection.page)
    if not options.network_allowed or not options.writes_allowed:
        return {"record_type": RESULT, "state": "plan", "request": selection.to_record(), "wire_request": request,
                "effects_performed": False, "physical_send_attempts": 0, "rights": dict(RIGHTS)}
    if selection.operation == AUTH and options.enqueue:raise KaggleError("kaggle_auth_is_not_a_lead")
    store = CommunityStore(options.state, writes_allowed=True)
    try:lock = _lock(store)
    except BlockingIOError:return {"record_type": RESULT, "state": "already_running", "physical_send_attempts": 0}
    try:
        previous = store.get(ACCESS_ID);state = _state(previous, options.request_ceiling);moment = clock()
        if state["request_state"] == "pending":return {"record_type": RESULT, "state": "reconcile_required", "physical_send_attempts": 0}
        if state.get("quota_hold"):
            return {"record_type": RESULT, "state": "source_hold_unknown_reset", "physical_send_attempts": 0}
        if state["reservations_total"] >= state["maximum_requests"]:
            return {"record_type": RESULT, "state": "request_ceiling", "physical_send_attempts": 0}
        if max(state.get("next_allowed_epoch", 0), state.get("held_until_epoch", 0)) > moment:
            return {"record_type": RESULT, "state": "source_hold", "physical_send_attempts": 0,
                    "next_allowed_at": _stamp(max(state.get("next_allowed_epoch", 0), state.get("held_until_epoch", 0)))}

        def collect(active):
            try:
                key = _credential(options, resolver)
                client = transport or Transport(load_policy(), timeout_seconds=20, maximum_bytes=MAXIMUM_BYTES,
                                                 environment={KEY_VARIABLE: key})
                if client.environment.get(KEY_VARIABLE) != key:raise KaggleError("kaggle_transport_credential_mismatch")
                if not engine.request_compatible(request):raise KaggleError("kaggle_request_incompatible")
                client.check(engine, request)
            except (ValueError, RuntimeError, OSError):
                return {"record_type": RESULT, "state": "refused", "reason": "credential_or_request_preflight_failed", "physical_send_attempts": 0}
            reserved = {**state, "reservations_total": state["reservations_total"] + 1, "request_state": "pending",
                        "last_attempted_at": _stamp(moment), "next_allowed_epoch": moment + 1, "selection": selection.to_record()}
            store.put(ACCESS_ID, "source", "kaggle", "recorded", reserved, expected=previous)
            report = {"record_type": RESULT, "state": FAILED, "request": selection.to_record(), "wire_request": request,
                "observed_at": _stamp(moment), "physical_send_attempts": 1, "requests_reserved": 1,
                "raw_body_retained": False, "account_identity_retained": False, "rights": dict(RIGHTS),
                "authentication_proof": "not_checked_by_this_operation", "items": [], "private_leads_recorded": 0,
                "source_rows": None, "excluded_rows": 0, "empty_source_observed": False, "loop_id": active.loop_id}
            try:
                if selection.operation == AUTH:
                    # Token is materialized only inside the fixed-host dispatch, never the logical request or records.
                    secret_body = json.dumps({"token": key}, separators=(",", ":")).encode()
                    answer = client._http(engine, request, "POST", secret_body,
                        {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
                    del secret_body
                else:answer = client.send(engine, request)
            except Exception:
                report["reason"] = "dispatch_outcome_unknown"
                store.put("community.run.kaggle." + store.run_id, "run", "kaggle", "failed", report)
                return report
            report.update(http_status=answer.status, response_bytes=len(answer.body), truncated=answer.truncated,
                          response_observed=answer.status is not None, transport_error=answer.error_class)
            if answer.truncated or key.encode() in answer.body:
                report["reason"] = "oversized_or_credential_echo_response_refused"
            elif selection.operation == AUTH:
                try:
                    from loop_engine.core.service_runtime.catalogue_bundle import strict_json
                    value = strict_json(answer.body, "auth_shape_invalid") if answer.status == 200 else {}
                    valid = value.get("active") is True and type(value.get("username")) is str and bool(value["username"])
                    report["authentication_proof"] = "active_account_token" if valid else "not_established"
                    report["state"] = OK if valid else RATE_LIMITED if answer.status == 429 else REFUSED if answer.status in (200, 401, 403) else FAILED
                    del value
                except (ValueError, RecursionError):report["authentication_proof"] = "not_established"
            else:
                parsed = engine.parse(answer.status, answer.body)
                report.update(state=parsed.status, items=parsed.items, source_rows=engine.source_rows,
                    excluded_rows=parsed.rejected, empty_source_observed=engine.source_rows == 0 and parsed.status == EMPTY,
                    next_cursor=parsed.next_cursor, observations=len(parsed.items), visibility_and_licence_scope="metadata_only_not_independent_verification")
                if options.enqueue:report["private_leads_recorded"] = _enqueue(store, parsed.items, report["observed_at"])
            finished_at = clock()
            finished = {**reserved, "request_state": "completed" if answer.status is not None else "pending",
                        "next_allowed_epoch": finished_at + 1, "last_outcome": report["state"], "last_http_status": answer.status}
            hold = _held_until(answer.status, answer.headers, finished_at, report["state"])
            if hold:finished["held_until_epoch"] = hold
            if _quota_reset_unknown(answer.status, answer.headers, finished_at, report["state"]):
                finished["quota_hold"] = "unknown_provider_reset"
                report["quota_hold"] = "unknown_provider_reset"
            if report["state"] in (OK, EMPTY):finished["last_successful_at"] = _stamp(finished_at)
            report["session_reservations_total"] = finished["reservations_total"]
            store.put("community.run.kaggle." + store.run_id, "run", "kaggle", "complete" if report["state"] in (OK, EMPTY) else "failed", report)
            store.put(ACCESS_ID, "source", "kaggle", "recorded", finished, expected=store.get(ACCESS_ID))
            return report

        return run_service_operation(store.runtime, ServiceLoopSpec("kaggle_metadata_intake", "practitioner.code_execution",
            REQUEST, RESULT, ("reads_fs", "writes_fs", "reads_secret", "network"), "Read one Kaggle metadata selection privately.",
            "kaggle_metadata_failed"), collect)
    finally:os.close(lock)


def reconcile_unknown(options):
    if not options.writes_allowed:raise PermissionError("local_write_grant_required")
    store = CommunityStore(options.state, writes_allowed=True);lock = _lock(store)
    try:
        prior = store.get(ACCESS_ID);state = _state(prior, options.request_ceiling)
        if state["request_state"] != "pending":return {"state": "nothing_to_reconcile", "physical_send_attempts": 0}
        store.put(ACCESS_ID, "source", "kaggle", "failed", {**state, "request_state": "closed_unknown",
            "last_outcome": "unknown_read_outcome"}, expected=prior)
        return {"state": "closed_unknown", "reservations_total": state["reservations_total"], "physical_send_attempts": 0}
    finally:os.close(lock)
