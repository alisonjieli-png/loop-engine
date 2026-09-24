"""Staff sign-up links: a superadmin starts Baltor's own sign-up for a few addresses.

Kind: internal service mechanics used by the governed HTTP operation of the
staff route `/api/v1/admin/sign-up-links`. It adds no runtime type, no store
and no graph vertex, and it adds no way in.

The owner asked on September 24, 2026 to let a superadmin type addresses and
invite people to sign up. The owner's rule is one way in, so a sign-up link is
Baltor's own email-first sign-up, started by a person instead of by the
visitor: the account is created with the same two marks by
`AccountOrigins.prepare_signup`, the link opens the same `/auth/confirm` page,
and the person chooses their own password there.

```text
One request from a superadmin
├── refused before anything: a caller without the permission, a record of
│   another version, more than ten addresses, or an address twice
├── a durable reservation under the request identity, in the audit record
├── for each address
│   ├── an account already open under it: refused, and no message
│   ├── over the allowance for one address that sign-up keeps: refused,
│   │   and no message
│   └── otherwise: the account is prepared with both marks, one link is
│       generated, and one message names the staff member who sent it
└── one write: a pending record for each link and the completed audit record
When the account opens
└── the pending record is completed, and free monthly Baltor Pro is granted
    in the same write when the superadmin asked for it
```

No address is kept here. The audit record and the pending records hold a
digest of the address and the provider user, the published privacy notice
keeps the address with the identity provider, and the account list reads it
from there.
"""
from __future__ import annotations

from dataclasses import dataclass
import uuid

from . import free_monthly
from .account_email import SIGNUP_ACTION, counted_email_key, email_address, generated_signup_password
from .account_policy import SEND_SIGN_UP_LINKS
from .http import ServiceHttpError
from .records import ServiceRuntimeError, digest, identifier

REQUEST_VERSION = "service_staff_sign_up_link_request/v1"
RESULT_VERSION = "service_staff_sign_up_link_result/v1"
LINK, LINK_VERSION = "service_staff_sign_up_link", "service_staff_sign_up_link/v1"
OPERATION = "send_sign_up_links"
#: A small batch: one request sends at most this many messages.
MOST_ADDRESSES = 10
SENT, HAS_ACCOUNT, SENT_RECENTLY, FAILED = "sent", "address_has_an_account", "address_sent_recently", "failed"
PENDING, ACTIVATED = "pending", "activated"
IN_PROGRESS, COMPLETED = "in_progress", "completed"
_REQUEST_FIELDS = frozenset({"record_type", "request_id", "addresses", "free_monthly"})


@dataclass(frozen=True)
class StaffSignUpLinkRequest:
    """One batch of addresses under one request identity, and whether each account includes free monthly."""

    request_id: str
    addresses: tuple
    free_monthly: bool
    record_type: str = REQUEST_VERSION

    def __post_init__(self):
        if self.record_type != REQUEST_VERSION or type(self.free_monthly) is not bool:
            raise ServiceRuntimeError("invalid_staff_sign_up_link_request")
        identifier(self.request_id, "request identity")
        if not isinstance(self.addresses, (list, tuple)) or not self.addresses:
            raise ServiceRuntimeError("invalid_staff_sign_up_link_request", "name at least one address")
        if len(self.addresses) > MOST_ADDRESSES:
            raise ServiceRuntimeError("sign_up_link_batch_too_large",
                                      f"one request sends at most {MOST_ADDRESSES} sign-up links")
        normalized = tuple(email_address(value) for value in self.addresses)
        if len(set(normalized)) != len(normalized):
            raise ServiceRuntimeError("invalid_staff_sign_up_link_request", "name each address once")
        object.__setattr__(self, "addresses", normalized)

    def __repr__(self):
        return "StaffSignUpLinkRequest(request_id=%r, addresses=%d, free_monthly=%r)" % (
            self.request_id, len(self.addresses), self.free_monthly)

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != _REQUEST_FIELDS
                or value.get("record_type") != REQUEST_VERSION):
            raise ServiceRuntimeError("invalid_staff_sign_up_link_request")
        return cls(**value)

    def identity(self):
        """The request identity covers every address, by digest, and the free monthly choice."""
        return digest({"record_type": self.record_type, "request_id": self.request_id,
                       "addresses": [counted_email_key(value) for value in self.addresses],
                       "free_monthly": self.free_monthly})


def staff_sign_up_message(display_name, sender, link, free_monthly):
    """The one message a sign-up link sends. It names who sent it and asks for nothing but a password."""
    included = ("\nYour account will include " + display_name + " Pro free each month.\n") if free_monthly else ""
    return (sender + " invited you to " + display_name,
            sender + " invited you to create a " + display_name + " account for this address.\n\n"
            "Open this link to confirm the address, choose your password and finish creating the account:\n"
            + link + "\n" + included + "\n"
            "If you did not expect this message, you can ignore it. The account cannot be used until the address "
            "is confirmed and a password is chosen on that page.\n")


def _link_payload(row):
    value = row.get("payload") if isinstance(row, dict) else None
    if not isinstance(value, dict) or value.get("record_type") != LINK_VERSION or value.get("state") not in (
            PENDING, ACTIVATED):
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return value


def links_by_subject(runtime, store, issuer):
    """What the account list shows about each sign-up link, keyed by provider user."""
    shown = {}
    for row in runtime._catalog.rows_all(store, LINK):
        value = _link_payload(row)
        if value.get("issuer") == issuer:
            shown[value["provider_user_id"]] = {"state": value["state"], "free_monthly": value["free_monthly"],
                                                "sent_at": value["sent_at"], "sent_by_role": value["sent_by_role"],
                                                "sends": value["sends"]}
    return shown


class _Refused(Exception):
    """One address refused before any message, with the outcome the result names."""

    def __init__(self, outcome):
        super().__init__(outcome)
        self.outcome = outcome


def _sent_once(adapter, origins, request, address, sender, secret):
    """Start Baltor's own sign-up for one address and send its one message, or refuse it before any message."""
    held = origins.administration.find_user(address, secret)
    if held is not None and (origins.bound(held.user_id)
                             or (origins.honoured(held) and bool(held.email_confirmed_at))):
        raise _Refused(HAS_ACCOUNT)
    # The allowance for one address that public sign-up keeps, shared with it.
    key = counted_email_key(address)
    if adapter.email_attempts.retry_after(key):
        raise _Refused(SENT_RECENTLY)
    adapter.email_attempts.record_failure(key)
    password = generated_signup_password()
    user_id = origins.prepare_signup(address, password, secret)
    if user_id is None:
        raise _Refused(HAS_ACCOUNT)
    token_hash = adapter.generated_link(SIGNUP_ACTION, address, password, secret, user_id)
    if not token_hash:
        raise _Refused(HAS_ACCOUNT)
    subject, body = staff_sign_up_message(adapter.display_name, sender, adapter.confirm_link(token_hash, SIGNUP_ACTION),
                                          request.free_monthly)
    adapter.send_message(address, subject, body)
    return user_id


def _audit_key(administration, staff, request):
    return (administration.issuer, staff.subject, request.request_id)


def _reserve(administration, staff, request):
    """Reserve the request identity before any provider request, or return the first result of it."""
    from .account_administration import AUDIT, AUDIT_VERSION
    catalog, runtime = administration.runtime._catalog, administration.runtime
    with catalog.store(write=True) as store:
        current, guards = administration._current_session(store, staff)
        key = _audit_key(administration, staff, request)
        held = catalog.read(store, AUDIT, key)
        if held is not None:
            value = held["payload"]
            if value.get("record_type") != AUDIT_VERSION:
                raise ServiceRuntimeError("unsupported_or_corrupt_record")
            if value.get("request_digest") != request.identity():
                raise ServiceRuntimeError("account_administration_request_identity_conflict")
            if value.get("state") != COMPLETED:
                raise ServiceRuntimeError("sign_up_links_in_progress")
            return current, value["result"]
        event = catalog.record(AUDIT, key, {
            "record_type": AUDIT_VERSION, "actor_subject": staff.subject, "actor_role": staff.role,
            "actor_tenant_id": current.tenant_id, "operation": OPERATION, "tenant_id": "",
            "request_digest": request.identity(), "state": IN_PROGRESS, "free_monthly": request.free_monthly,
            "address_digests": [counted_email_key(value) for value in request.addresses], "result": None,
            "at": int(runtime._now())}, tenant_id=current.tenant_id)
        if staff.expires_at <= runtime._now():
            raise ServiceRuntimeError("unauthorized")
        catalog.commit(store, (event,), (*guards, catalog.guard(None, event["record_id"])))
    return current, None


def _complete(administration, staff, request, outcomes):
    """Write every pending link and the completed audit record in one write."""
    from .account_administration import AUDIT
    catalog, runtime = administration.runtime._catalog, administration.runtime
    now = int(runtime._now())
    stored = [{"address_digest": counted_email_key(address), **outcome}
              for address, outcome in zip(request.addresses, outcomes)]
    result = {"record_type": RESULT_VERSION, "committed": True, "request_id": request.request_id,
              "free_monthly": request.free_monthly, "sent": sum(row["outcome"] == SENT for row in stored),
              "links": stored}
    with catalog.store(write=True) as store:
        key = _audit_key(administration, staff, request)
        event_row = catalog.read(store, AUDIT, key)
        if event_row is None or event_row["payload"].get("request_digest") != request.identity():
            raise ServiceRuntimeError("concurrent_update")
        rows, guards = [], [catalog.guard(event_row)]
        for row in stored:
            if row["outcome"] != SENT:
                continue
            link_key = (administration.issuer, row["provider_user_id"])
            previous = catalog.read(store, LINK, link_key)
            earlier = _link_payload(previous) if previous is not None else {}
            link = catalog.record(LINK, link_key, {
                "record_type": LINK_VERSION, "issuer": administration.issuer,
                "provider_user_id": row["provider_user_id"], "address_digest": row["address_digest"],
                "state": PENDING, "free_monthly": request.free_monthly, "sent_at": now,
                "sent_by_subject": staff.subject, "sent_by_role": staff.role, "request_id": request.request_id,
                "sends": earlier.get("sends", 0) + 1, "activated_at": None, "tenant_id": ""})
            rows.append(link)
            guards.append(catalog.guard(previous, link["record_id"]))
        rows.append({**event_row, "record_version": uuid.uuid4().hex,
                     "payload": {**event_row["payload"], "state": COMPLETED, "result": result, "completed_at": now}})
        catalog.commit(store, tuple(rows), tuple(guards))
    return result


def _answer(request, result, replayed):
    """The stored result with each address put back from the request, which the digest proved identical."""
    links = [{"address": address, **{name: value for name, value in row.items() if name != "address_digest"}}
             for address, row in zip(request.addresses, result["links"])]
    return {**result, "links": links, "replayed": replayed}


def send_sign_up_links(administration, adapter, staff, request):
    """Send one batch of sign-up links for a superadmin, or replay the first result of its request identity."""
    if not isinstance(request, StaffSignUpLinkRequest):
        raise ServiceRuntimeError("invalid_staff_sign_up_link_request")
    administration._require(staff, SEND_SIGN_UP_LINKS)
    origins = getattr(adapter, "account_origins", None) if adapter is not None else None
    if origins is None:
        raise ServiceHttpError("sign_up_links_unavailable", 503)
    if not adapter.signup_available:
        raise ServiceHttpError("account_signup_unavailable", 503)
    _current, replay = _reserve(administration, staff, request)
    if replay is not None:
        return _answer(request, replay, True)
    member = administration.policy.member_for(staff.subject, staff.email)
    sender = (member.name if member is not None and member.name else "") or staff.email or "A member of the team"
    secret = adapter.identity_secret()
    outcomes = []
    for address in request.addresses:
        try:
            outcomes.append({"outcome": SENT, "provider_user_id": _sent_once(adapter, origins, request, address,
                                                                            sender, secret)})
        except _Refused as refusal:
            outcomes.append({"outcome": refusal.outcome})
        except (ServiceHttpError, ServiceRuntimeError) as error:
            outcomes.append({"outcome": FAILED, "code": getattr(error, "code", "failed")})
    return _answer(request, _complete(administration, staff, request, outcomes), False)


def complete_on_activation(runtime, issuer, subject, tenant_id):
    """Complete a pending sign-up link when its account opens, with free monthly Baltor Pro when it was asked for.

    The grant and the completed record commit together. An account that
    already holds free monthly or a paid plan keeps it, and the record names
    why nothing was granted. A lost race reads again; a fault leaves the link
    pending, and the next activation completes it.
    """
    catalog = runtime._catalog
    for _round in range(3):
        try:
            with catalog.store(write=True) as store:
                row = catalog.read(store, LINK, (issuer, subject))
                if row is None:
                    return None
                value = _link_payload(row)
                if value["state"] != PENDING:
                    return value["state"]
                now = int(runtime._now())
                rows, guards, granted = [], [catalog.guard(row)], ""
                if value["free_monthly"]:
                    try:
                        grant, grant_guards, detail = free_monthly.grant_rows(
                            runtime, store, tenant_id, now, "sign_up_link:" + value["sent_by_subject"])
                        rows, guards, granted = list(grant), [*guards, *grant_guards], detail["grant_kind"]
                    except ServiceRuntimeError as error:
                        if error.code not in ("free_monthly_already_held", "paid_subscription_active"):
                            raise
                        granted = error.code
                rows.append({**row, "record_version": uuid.uuid4().hex, "payload": {
                    **value, "state": ACTIVATED, "activated_at": now, "tenant_id": tenant_id,
                    "free_monthly_outcome": granted}})
                catalog.commit(store, tuple(rows), tuple(guards))
                return ACTIVATED
        except ServiceRuntimeError as error:
            if error.code != "concurrent_update":
                raise
    return PENDING
