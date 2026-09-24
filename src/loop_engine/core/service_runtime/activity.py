"""The staff audit record and the activity search of the staff tools.

Kind: internal service mechanics used by the governed operations of the staff
tools. It adds no runtime type, no store and no graph vertex. Every staff tool
call writes one `service_staff_audit_event/v1` record under the request
reference the transport issued for it, in the existing service store; a call
with an effect writes it in the same batch as the effect.

Activity search reads what the service already keeps and adds nothing to it:

```text
Activity kinds
├── staff_tool       every staff tool call and every staff key change
├── administration   the account actions of the Administration page
├── sign_up          an account Baltor's sign-up created, or the marking command marked
├── activation       the first activation of an account from Baltor's sign-up,
│                    when the founding offer was considered for it
├── download         one metered download, and the credit grant it drew on
└── refusal          one refused request of the failure journal, by code
```

No record here holds an address. The audit record keeps a digest of the
arguments and the plan, never the arguments themselves, because the arguments
of a sign-up link or a message name addresses.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .records import ServiceRuntimeError, digest

AUDIT, AUDIT_VERSION = "service_staff_audit_event", "service_staff_audit_event/v1"
PAGE_VERSION, COUNTS_VERSION = "service_activity_page/v1", "service_activity_counts/v1"
STAFF_TOOL, ADMINISTRATION, SIGN_UP, ACTIVATION, DOWNLOAD, REFUSAL = (
    "staff_tool", "administration", "sign_up", "activation", "download", "refusal")
KINDS = (STAFF_TOOL, ADMINISTRATION, SIGN_UP, ACTIVATION, DOWNLOAD, REFUSAL)
TRANSPORTS = ("mcp", "http")
STEPS = ("read", "plan", "apply")
OUTCOMES = ("ok", "refused")
LARGEST_PAGE = 200


def _audit_payload(reference, *, transport, tool, step, actor_kind, actor_ref, role, outcome, at, code="",
                  request_id="", plan_digest="", arguments_digest="", target="", tenant_id=""):
    """One audit record. A field outside its vocabulary is refused, so a record can only say what it may say."""
    if (transport not in TRANSPORTS or step not in STEPS or outcome not in OUTCOMES
            or not isinstance(tool, str) or not tool or not isinstance(reference, str) or not reference
            or not isinstance(tenant_id, str)):
        raise ServiceRuntimeError("invalid_staff_audit_event")
    return {"record_type": AUDIT_VERSION, "request_reference": reference, "at": int(at), "transport": transport,
            "tool": tool, "step": step, "actor_kind": actor_kind, "actor_ref": actor_ref, "role": role,
            "outcome": outcome, "code": code, "request_id": request_id, "plan_digest": plan_digest,
            "arguments_digest": arguments_digest, "target": target, "tenant_id": tenant_id}


def _reference_value(reference):
    return getattr(reference, "value", reference)


def audit_row(runtime, reference, **fields):
    """The audit record of one call as a row, for a caller that commits it with its effect."""
    value = _reference_value(reference)
    payload = _audit_payload(value, at=runtime._now(), **fields)
    return runtime._catalog.record(AUDIT, (value, payload["tool"], payload["step"]), payload,
                                   tenant_id=payload["tenant_id"])


def write_audit(runtime, reference, **fields):
    """Commit the audit record of one call on its own. A record the reference already holds is kept."""
    catalog = runtime._catalog
    row = audit_row(runtime, reference, **fields)
    with catalog.store(write=True) as store:
        if catalog.read_id(store, row["record_id"], kind=AUDIT) is not None:
            return row["payload"]
        catalog.commit(store, (row,), (catalog.guard(None, row["record_id"]),))
    return row["payload"]


def unique_guards(guards):
    """One precondition for each record. Two different ones for the same record mean the state moved."""
    kept = {}
    for guard in guards:
        if guard.record_id in kept and kept[guard.record_id] != guard:
            raise ServiceRuntimeError("concurrent_update")
        kept[guard.record_id] = guard
    return tuple(kept.values())


def arguments_digest(arguments):
    """A digest of a call's arguments. It lets a record show two calls were the same without keeping either."""
    try:
        return digest(arguments)
    except ServiceRuntimeError:
        return ""


def _day(moment):
    return datetime.fromtimestamp(int(moment), timezone.utc).strftime("%Y-%m-%d")


def _audit_rows(runtime, store):
    rows = []
    for row in runtime._catalog.rows_all(store, AUDIT):
        value = row["payload"]
        if value.get("record_type") != AUDIT_VERSION:
            raise ServiceRuntimeError("unsupported_or_corrupt_record")
        target = value.get("target", "")
        rows.append({"kind": STAFF_TOOL, "at": value["at"], "tenant_id": value.get("tenant_id", ""),
                     "code": value.get("code", ""), "tool": value["tool"], "step": value["step"],
                     "outcome": value["outcome"], "transport": value["transport"], "actor_kind": value["actor_kind"],
                     "actor_ref": value["actor_ref"], "role": value["role"], "target": target,
                     "request_reference": value["request_reference"], "request_id": value.get("request_id", ""),
                     "plan_digest": value.get("plan_digest", "")})
    return rows


def _administration_rows(runtime, store):
    from .account_administration import AUDIT as PAGE_AUDIT, AUDIT_VERSION as PAGE_AUDIT_VERSION
    rows = []
    for row in runtime._catalog.rows_all(store, PAGE_AUDIT):
        value = row["payload"]
        if value.get("record_type") != PAGE_AUDIT_VERSION:
            continue
        rows.append({"kind": ADMINISTRATION, "at": value.get("at", 0), "tenant_id": value.get("tenant_id", ""),
                     "code": "", "operation": value.get("operation", ""), "actor_ref": "browser_session:"
                     + str(value.get("actor_subject", "")), "role": value.get("actor_role", "")})
    return rows


def _account_rows(runtime, store, issuer):
    from .account_origin import ORIGIN, ORIGIN_VERSION
    from .free_monthly import FOUNDING_ACCOUNT, FOUNDING_ACCOUNT_VERSION
    from .runtime import SUBJECT
    catalog = runtime._catalog
    tenants = {row["payload"].get("subject"): row["payload"].get("tenant_id", "")
               for row in catalog.rows_all(store, SUBJECT) if row["payload"].get("issuer") == issuer}
    rows = []
    for row in catalog.rows_all(store, ORIGIN):
        value = row["payload"]
        if value.get("record_type") == ORIGIN_VERSION and value.get("issuer") == issuer:
            rows.append({"kind": SIGN_UP, "at": value.get("recorded_at", 0), "code": "", "origin": value.get("origin"),
                         "provider_user_id": value.get("subject", ""),
                         "tenant_id": tenants.get(value.get("subject"), "")})
    for row in catalog.rows_all(store, FOUNDING_ACCOUNT):
        value = row["payload"]
        if value.get("record_type") == FOUNDING_ACCOUNT_VERSION:
            rows.append({"kind": ACTIVATION, "at": value.get("considered_at", 0), "code": "",
                         "tenant_id": value.get("tenant_id", ""), "founding_decision": value.get("decision", "")})
    return rows


def _download_rows(runtime, store):
    from .runtime import USAGE
    rows = []
    for row in runtime._catalog.rows_all(store, USAGE):
        value = runtime._payload(row, USAGE)
        rows.append({"kind": DOWNLOAD, "at": value.get("at", 0), "tenant_id": value.get("tenant_id", ""), "code": "",
                     "item_identity": value.get("item_identity", ""), "unit": value.get("unit", ""),
                     "credit_grant_id": value.get("credit_grant_id", "")})
    return rows


def _refusal_rows(journal):
    from .observability import MAXIMUM_FAILURE_LISTING
    return [{"kind": REFUSAL, "at": value.get("at", 0), "tenant_id": value.get("tenant_id", ""),
             "code": value.get("refusal_code", ""), "status": value.get("status"), "route": value.get("route", ""),
             "method": value.get("method", ""), "request_reference": value.get("request_reference", "")}
            for value in journal.recent(limit=MAXIMUM_FAILURE_LISTING)["failures"]]


@dataclass(frozen=True)
class ActivityQuery:
    """One activity search: which kinds, which account and code, which time, and which page."""

    kinds: tuple = KINDS
    tenant_id: str | None = None
    code: str | None = None
    since: int | None = None
    until: int | None = None
    page_size: int = 50
    cursor: int = 0
    counts_only: bool = False

    def __post_init__(self):
        chosen = tuple(dict.fromkeys(self.kinds))
        if not chosen or any(kind not in KINDS for kind in chosen):
            raise ServiceRuntimeError("invalid_activity_kind")
        if (type(self.page_size) is not int or not 1 <= self.page_size <= LARGEST_PAGE
                or type(self.cursor) is not int or self.cursor < 0 or type(self.counts_only) is not bool):
            raise ServiceRuntimeError("invalid_page")
        object.__setattr__(self, "kinds", chosen)


def search(runtime, query, *, issuer, journal):
    """Activity newest first, filtered by kind, account, code and time, one page at a time.

    `query.counts_only` answers with counts for each kind and each day and
    nothing else, which is all the analytics role may read.
    """
    if not isinstance(query, ActivityQuery):
        raise ServiceRuntimeError("invalid_activity_query")
    chosen, tenant_id, code, since, until = query.kinds, query.tenant_id, query.code, query.since, query.until
    rows = []
    with runtime._catalog.store() as store:
        if STAFF_TOOL in chosen:
            rows += _audit_rows(runtime, store)
        if ADMINISTRATION in chosen:
            rows += _administration_rows(runtime, store)
        if SIGN_UP in chosen or ACTIVATION in chosen:
            rows += [row for row in _account_rows(runtime, store, issuer) if row["kind"] in chosen]
        if DOWNLOAD in chosen:
            rows += _download_rows(runtime, store)
    if REFUSAL in chosen and journal is not None:
        rows += _refusal_rows(journal)
    kept = [row for row in rows
            if (tenant_id is None or row.get("tenant_id") == tenant_id) and (code is None or row.get("code") == code)
            and (since is None or row["at"] >= since) and (until is None or row["at"] < until)]
    kept.sort(key=lambda row: (-row["at"], row["kind"], str(row.get("request_reference") or row.get("tenant_id"))))
    if query.counts_only:
        days = {}
        for row in kept:
            day = days.setdefault(_day(row["at"]), {})
            day[row["kind"]] = day.get(row["kind"], 0) + 1
        return {"record_type": COUNTS_VERSION, "total": len(kept),
                "by_kind": {kind: sum(1 for row in kept if row["kind"] == kind) for kind in chosen},
                "by_day": dict(sorted(days.items(), reverse=True))}
    cursor, page_size = query.cursor, query.page_size
    page = kept[cursor:cursor + page_size]
    following = cursor + page_size if cursor + page_size < len(kept) else None
    return {"record_type": PAGE_VERSION, "events": page, "total": len(kept), "cursor": cursor,
            "next_cursor": following, "kinds": list(chosen),
            "limits": ["Refusals come from the failure journal, a bounded ring of the newest refused requests.",
                       "An activation is dated by the founding offer decision made at the account's first "
                       "activation; an account the marking command marked has no activation date."]}
