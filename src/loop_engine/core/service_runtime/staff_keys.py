"""Staff keys: the credential a staff member's protocol client uses for the staff tools.

Kind: internal service mechanics used by the governed operations of the staff
tools (`staff_tools.py`) and their two transports, the protocol endpoint
`/admin/mcp` and the routes under `/api/v1/admin/tools/` (`admin_mcp.py`). It
adds no runtime type, no store and no graph vertex: a staff key is a passive
typed record in the existing service store.

The owner asked on September 24, 2026 for a protocol server and an interface
that let the person running Baltor manage it from Claude Code, Codex or any
protocol client. A browser session cannot be pasted into such a client, so a
superadmin mints a key for it:

```text
Staff key
├── minted by a superadmin in a signed-in browser session, never with a key,
│   so a key that leaks cannot mint another
├── bound to one entry of the host file's staff list and the role it holds;
│   a changed role or a removed entry refuses the key at its next use
├── shown once; the store keeps its SHA-256 digest and a masked hint of the
│   staff member, never the key and never the address
├── expires 24 hours after it is minted unless the superadmin chose another
│   lifetime, from five minutes to seven days
├── revoked by a superadmin at any time; the next call is refused, and a plan
│   applied after the revocation commits nothing
└── accepted by the staff tools alone: a customer key or a host key never
    reaches them, and a staff key never reaches a customer route
```

A staff key has its own prefix, `bsk_`, and its own record kind, so the
customer key reader, which reads `service_key` records, can never resolve one,
and the staff key reader never resolves a customer key.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import secrets
import uuid

from .account_policy import STAFF_KEYS_MANAGE, permissions_for
from .http import ServiceHttpError
from .http_auth import HttpAuthenticationError
from .records import ServiceRuntimeError, digest, identifier, text

KEY_PREFIX = "bsk_"
KEY, KEY_VERSION = "service_staff_key", "service_staff_key/v1"
MINT, MINT_VERSION = "service_staff_key_mint", "service_staff_key_mint/v1"
REQUEST_VERSION = "service_staff_key_request/v1"
RESULT_VERSION = "service_staff_key_result/v1"
LISTING_VERSION = "service_staff_key_listing/v1"
OPERATIONS = ("mint", "revoke")
#: The environment variable a connection entry names. The page and the guide
#: name this variable and never the key it holds.
ENVIRONMENT_VARIABLE = "BALTOR_STAFF_KEY"
DEFAULT_LIFETIME_SECONDS = 24 * 3600
SHORTEST_LIFETIME_SECONDS = 300
LONGEST_LIFETIME_SECONDS = 7 * 86400
#: Active keys one staff member may hold at once, and key records in all. A
#: full history refuses a new key instead of removing old records silently.
MOST_ACTIVE_KEYS_FOR_EACH_MEMBER = 5
MOST_KEY_RECORDS = 1000
ACTIVE, EXPIRED, REVOKED = "active", "expired", "revoked"
STAFF_KEY_AUTHENTICATION, BROWSER_SESSION = "staff_key", "browser_session"


def key_digest(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def member_identity(member):
    """The identity text of one staff entry, as the host file names it."""
    return member.provider_user_id or member.email


def identity_digest(member):
    """The digest a key record keeps in place of the staff member's identity."""
    named_by = "provider_user_id" if member.provider_user_id else "email"
    return hashlib.sha256((named_by + ":" + member_identity(member)).encode("utf-8")).hexdigest()


def member_hint(member):
    """A short hint an operator recognises, never a whole address."""
    if member.provider_user_id:
        return member.provider_user_id[:8] + "…"
    local, _, domain = member.email.partition("@")
    return local[:1] + "***@" + domain


@dataclass(frozen=True)
class StaffActor:
    """Verified facts about the staff member behind one staff tool call.

    A staff key call carries the key's identity; a browser session call
    carries the verified session of `account_administration.StaffSession`.
    Nothing in a request can build one: the transport builds it after a fresh
    check of the credential.
    """

    kind: str
    reference: str
    role: str
    identity_digest: str = field(repr=False)
    expires_at: float
    label: str = ""
    record_id: str = field(default="", repr=False)
    session: object = field(default=None, repr=False, compare=False)

    @property
    def actor_ref(self):
        return self.kind + ":" + self.reference

    @property
    def share(self):
        """The share of the worker pool this caller holds. A space keeps it apart from every account."""
        return "staff " + self.actor_ref

    def may(self, permission):
        return permission in permissions_for(self.role)


@dataclass(frozen=True)
class StaffKeyRequest:
    """One superadmin operation on staff keys: mint a key for a staff member, or revoke one."""

    operation: str
    request_id: str
    staff_member: str = ""
    label: str = ""
    lifetime_seconds: int = DEFAULT_LIFETIME_SECONDS
    key_id: str = ""
    record_type: str = REQUEST_VERSION

    def __post_init__(self):
        if self.record_type != REQUEST_VERSION or self.operation not in OPERATIONS:
            raise ServiceRuntimeError("invalid_staff_key_request")
        identifier(self.request_id, "request identity")
        if self.operation == "mint":
            if self.key_id or not isinstance(self.staff_member, str) or not self.staff_member:
                raise ServiceRuntimeError("invalid_staff_key_request", "a new key names one staff member")
            text(self.label, "key label")
            if len(self.label) > 100:
                raise ServiceRuntimeError("invalid_staff_key_request", "a key label has at most 100 characters")
            if (type(self.lifetime_seconds) is not int
                    or not SHORTEST_LIFETIME_SECONDS <= self.lifetime_seconds <= LONGEST_LIFETIME_SECONDS):
                raise ServiceRuntimeError("invalid_staff_key_lifetime",
                                          "a staff key lives from five minutes to seven days")
        elif self.staff_member or self.label or not isinstance(self.key_id, str) or len(self.key_id) != 32:
            raise ServiceRuntimeError("invalid_staff_key_request", "a revocation names one key identity")

    @classmethod
    def from_dict(cls, value):
        allowed = {"record_type", "operation", "request_id", "staff_member", "label", "lifetime_seconds", "key_id"}
        if (not isinstance(value, dict) or set(value) - allowed or value.get("record_type") != REQUEST_VERSION
                or not {"operation", "request_id"} <= set(value)):
            raise ServiceRuntimeError("invalid_staff_key_request")
        return cls(**value)

    def identity(self):
        return digest({"record_type": self.record_type, "operation": self.operation, "request_id": self.request_id,
                       "staff_member": self.staff_member.lower(), "label": self.label,
                       "lifetime_seconds": self.lifetime_seconds, "key_id": self.key_id})


def _key_payload(row):
    value = row.get("payload") if isinstance(row, dict) else None
    if not isinstance(value, dict) or value.get("record_type") != KEY_VERSION:
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return value


def key_state(value, now):
    if value.get("revoked_at") is not None:
        return REVOKED
    return ACTIVE if type(value.get("expires_at")) is int and value["expires_at"] > now else EXPIRED


class StaffKeys:
    """Mint, list, revoke and authenticate staff keys over the existing service store."""

    def __init__(self, runtime, administration):
        self.runtime, self.administration = runtime, administration

    @property
    def policy(self):
        return self.administration.policy

    def _member_named(self, name):
        wanted = name.strip().lower() if isinstance(name, str) else ""
        for member in self.policy.staff:
            if member_identity(member) == wanted:
                return member
        raise ServiceHttpError("staff_member_unknown", 404)

    def _member_for(self, digest_value):
        for member in self.policy.staff:
            if secrets.compare_digest(identity_digest(member), digest_value):
                return member
        return None

    @staticmethod
    def _require_manager(staff):
        if STAFF_KEYS_MANAGE not in permissions_for(getattr(staff, "role", "")):
            raise ServiceHttpError("staff_tool_forbidden", 403)

    def members(self):
        """The staff list a superadmin chooses from on the page: each entry, its role and its active keys."""
        now = int(self.runtime._now())
        with self.runtime._catalog.store() as store:
            payloads = [_key_payload(row) for row in self.runtime._catalog.rows_all(store, KEY)]
        return [{"staff_member": member_identity(member), "named_by": "provider_user_id" if member.provider_user_id
                 else "email", "role": member.role,
                 "active_keys": sum(1 for value in payloads if value["staff_identity_digest"] == identity_digest(member)
                                    and key_state(value, now) == ACTIVE)} for member in self.policy.staff]

    def listing(self, staff):
        """Every staff key's metadata, newest first. No digest and no key is ever listed."""
        self._require_manager(staff)
        now = int(self.runtime._now())
        with self.runtime._catalog.store() as store:
            self.administration._current_session(store, staff)
            payloads = [_key_payload(row) for row in self.runtime._catalog.rows_all(store, KEY)]
        rows = []
        for value in sorted(payloads, key=lambda item: (-item["minted_at"], item["key_id"])):
            member = self._member_for(value["staff_identity_digest"])
            rows.append({"key_id": value["key_id"], "label": value["label"], "role": value["role"],
                         "staff_member": member_identity(member) if member is not None else value["staff_hint"],
                         "staff_entry_current": member is not None and member.role == value["role"],
                         "minted_at": value["minted_at"], "expires_at": value["expires_at"],
                         "revoked_at": value["revoked_at"], "state": key_state(value, now)})
        return {"record_type": LISTING_VERSION, "keys": rows, "members": self.members(),
                "environment_variable": ENVIRONMENT_VARIABLE, "default_lifetime_seconds": DEFAULT_LIFETIME_SECONDS,
                "shortest_lifetime_seconds": SHORTEST_LIFETIME_SECONDS,
                "longest_lifetime_seconds": LONGEST_LIFETIME_SECONDS}

    def apply(self, staff, request, reference):
        """Mint or revoke under one request identity; a repeat replays and never shows a key again."""
        from .activity import audit_row
        if not isinstance(request, StaffKeyRequest):
            raise ServiceRuntimeError("invalid_staff_key_request")
        self._require_manager(staff)
        catalog, runtime = self.runtime._catalog, self.runtime
        raw = KEY_PREFIX + secrets.token_urlsafe(32) if request.operation == "mint" else ""
        with catalog.store(write=True) as store:
            _current, guards = self.administration._current_session(store, staff)
            mint_key = (staff.subject, request.request_id)
            held = catalog.read(store, MINT, mint_key)
            if held is not None:
                value = held["payload"]
                if value.get("record_type") != MINT_VERSION:
                    raise ServiceRuntimeError("unsupported_or_corrupt_record")
                if value.get("request_digest") != request.identity():
                    raise ServiceHttpError("staff_key_request_identity_conflict", 409)
                return {**value["result"], "key": None, "replayed": True}
            now = int(runtime._now())
            rows, row_guards, result = (self._mint_rows(store, staff, request, raw, now) if request.operation == "mint"
                                        else self._revoke_rows(store, staff, request, now))
            marker = catalog.record(MINT, mint_key, {"record_type": MINT_VERSION, "request_digest": request.identity(),
                                                     "result": result, "at": now})
            event = audit_row(runtime, reference, transport="http", tool="staff_keys." + request.operation,
                              step="apply", actor_kind=BROWSER_SESSION, actor_ref=BROWSER_SESSION + ":" + staff.subject,
                              role=staff.role, outcome="ok", request_id=request.request_id, target=result["key_id"])
            if staff.expires_at <= runtime._now():
                raise HttpAuthenticationError()
            catalog.commit(store, (*rows, marker, event), (*guards, *row_guards, catalog.guard(None, marker["record_id"]),
                                                           catalog.guard(None, event["record_id"])))
        return {**result, "key": raw or None, "replayed": False}

    def _mint_rows(self, store, staff, request, raw, now):
        catalog = self.runtime._catalog
        member = self._member_named(request.staff_member)
        payloads = [_key_payload(row) for row in catalog.rows_all(store, KEY)]
        if len(payloads) >= MOST_KEY_RECORDS:
            raise ServiceHttpError("staff_key_history_limit_reached", 409)
        bound = identity_digest(member)
        if sum(1 for value in payloads if value["staff_identity_digest"] == bound
               and key_state(value, now) == ACTIVE) >= MOST_ACTIVE_KEYS_FOR_EACH_MEMBER:
            raise ServiceHttpError("staff_key_limit_reached", 409)
        hashed, key_id = key_digest(raw), uuid.uuid4().hex
        row = catalog.record(KEY, hashed, {
            "record_type": KEY_VERSION, "key_id": key_id, "key_digest": hashed, "label": request.label,
            "staff_identity_digest": bound, "staff_hint": member_hint(member), "role": member.role,
            "minted_by": staff.subject, "minted_at": now, "expires_at": now + request.lifetime_seconds,
            "revoked_at": None, "revoked_by": "", "request_id": request.request_id})
        result = {"record_type": RESULT_VERSION, "operation": "mint", "key_id": key_id, "label": request.label,
                  "role": member.role, "staff_member": member_identity(member), "minted_at": now,
                  "expires_at": now + request.lifetime_seconds, "environment_variable": ENVIRONMENT_VARIABLE}
        return (row,), (catalog.guard(None, row["record_id"]),), result

    def _revoke_rows(self, store, staff, request, now):
        catalog = self.runtime._catalog
        found = [row for row in catalog.rows_all(store, KEY) if _key_payload(row)["key_id"] == request.key_id]
        if len(found) != 1:
            raise ServiceHttpError("staff_key_not_found", 404)
        row = found[0]
        value = _key_payload(row)
        result = {"record_type": RESULT_VERSION, "operation": "revoke", "key_id": request.key_id,
                  "revoked_at": value["revoked_at"] if value["revoked_at"] is not None else now,
                  "changed": value["revoked_at"] is None}
        if value["revoked_at"] is not None:
            return (), (catalog.guard(row),), result
        updated = {**row, "record_version": uuid.uuid4().hex,
                   "payload": {**value, "revoked_at": now, "revoked_by": staff.subject}}
        return (updated,), (catalog.guard(row),), result

    def _actor(self, row, hashed):
        """Check one stored key as of now, or refuse it with the reason a staff member can act on."""
        if row is None:
            raise HttpAuthenticationError("staff_credential_required")
        value = _key_payload(row)
        if not secrets.compare_digest(str(value.get("key_digest", "")), hashed):
            raise HttpAuthenticationError("staff_credential_required")
        now = self.runtime._now()
        if key_state(value, now) == REVOKED:
            raise HttpAuthenticationError("staff_key_revoked")
        if key_state(value, now) == EXPIRED:
            raise HttpAuthenticationError("staff_key_expired")
        member = self._member_for(value["staff_identity_digest"])
        if member is None or member.role != value["role"]:
            raise HttpAuthenticationError("staff_key_role_changed")
        return StaffActor(STAFF_KEY_AUTHENTICATION, value["key_id"], member.role, value["staff_identity_digest"],
                          float(value["expires_at"]), value["label"], row["record_id"])

    def authenticate(self, credential):
        """The staff member behind one presented key, or a refusal. A customer or host key is never one."""
        if (not isinstance(credential, str) or not credential.startswith(KEY_PREFIX)
                or not 20 <= len(credential) <= 128 or any(character.isspace() for character in credential)):
            raise HttpAuthenticationError("staff_credential_required")
        hashed = key_digest(credential)
        with self.runtime._catalog.store() as store:
            return self._actor(self.runtime._catalog.read(store, KEY, hashed), hashed)

    def current_guards(self, store, actor):
        """Check the caller again inside a write, and return what the commit must still find unchanged."""
        if not isinstance(actor, StaffActor):
            raise HttpAuthenticationError("staff_credential_required")
        if actor.kind == BROWSER_SESSION:
            _current, guards = self.administration._current_session(store, actor.session)
            return tuple(guards)
        row = self.runtime._catalog.read_id(store, actor.record_id, kind=KEY)
        current = self._actor(row, _key_payload(row)["key_digest"] if row is not None else "")
        if current.role != actor.role or current.reference != actor.reference:
            raise HttpAuthenticationError("staff_key_role_changed")
        return (self.runtime._catalog.guard(row),)

    def session_actor(self, staff):
        """The actor of a signed-in staff browser session, from its verified session."""
        member = self.policy.member_for(staff.subject, staff.email)
        if member is None:
            raise ServiceHttpError("staff_role_required", 403)
        return StaffActor(BROWSER_SESSION, staff.subject, staff.role, identity_digest(member), staff.expires_at, "",
                          "", staff)
