"""One way in: the service honours only the accounts that its own sign-up created.

Kind: internal service mechanics behind the `identity_administration/v1` edge.
It is an adapter used by the Loops that own sign-up, sign-in and the marking
command. It adds no runtime type and no store: the service records below live
in the existing catalogue, and the identity provider keeps users, passwords
and sessions.

The identity provider still takes its own public sign-up until the owner
closes it. Anyone holding the public key can register an address that is not
theirs, with a password they chose, and keep that password once the owner of
the address confirms it. This module closes that path inside the service:

```text
One way in
├── Baltor's sign-up creates the user through the administration interface
│   ├── marked in the provider's app_metadata, which only that interface writes
│   └── recorded in the service's own store, service_account_origin/v1
├── Every sign-in and every activation needs both marks, or it is refused
│   with account_origin_unverified
├── An address held by an account without both marks is replaced when its
│   owner signs up through Baltor
│   ├── its provider identity, creation time and confirmation state are kept
│   │   in service_account_replacement/v1, with a digest of the address
│   ├── it is deleted at the provider, which ends its sessions and refresh
│   │   tokens, and a fresh marked account is created for the same address
│   └── except an account the service already holds a sign-in for: it predates
│       the guard, keeps its place, and its owner is sent the usual notice
└── Accounts that existed before this guard get both marks once, through the
    `mark-accounts` command, which lists every change before it makes one
```

The identity administration edge has one engine today,
`SupabaseIdentityAdministration`. Another identity provider needs another
engine with the same five operations; nothing that calls the edge changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
import time
import uuid
from urllib.parse import urlencode

from .account_policy import PROVIDER_USER_ID
from .http import ServiceHttpError
from .http_auth import HttpAuthenticationError
from .records import ServiceRuntimeError, digest
from .runtime import SUBJECT

IDENTITY_ADMINISTRATION_PROTOCOL = "identity_administration/v1"
#: The key and value this service writes into a provider user's app_metadata.
#: The provider lets only its administration interface write that object.
ACCOUNT_MARKER, ACCOUNT_MARK = "baltor_account", "service_account_origin/v1"
#: The mark of the retired invitation command. It is read as history only and
#: admits nobody.
INVITATION_MARKER = "baltor_invitation"
ORIGIN, ORIGIN_VERSION = "service_account_origin", "service_account_origin/v1"
REPLACEMENT, REPLACEMENT_VERSION = "service_account_replacement", "service_account_replacement/v1"
PLAN_VERSION, MARKING_RESULT_VERSION = "service_account_marking_plan/v1", "service_account_marking_result/v1"
SIGNUP_ORIGIN, MIGRATION_ORIGIN = "signup", "migration"
ORIGINS = (SIGNUP_ORIGIN, MIGRATION_ORIGIN)
#: Why the marking command marks an account that predates the guard.
SERVICE_ACCOUNT_REASON, STAFF_REASON = "service_account", "staff"
ARCHIVED, DELETED, REPLACED = "archived", "deleted_at_the_provider", "replaced"
REFUSED_ORIGIN = "account_origin_unverified"
USERS_PATH = "/auth/v1/admin/users"
IDENTITY_KEY_PREFIX = "sb_secret_"
METHODS = ("GET", "POST", "PUT", "DELETE")
LOOKUP_PAGE_SIZE, LOOKUP_PAGES = 100, 5
LISTING_PAGE_SIZE, LISTING_PAGES = 200, 50


class IdentityAdministrationError(ServiceHttpError):
    """A caller-safe refusal at the identity administration edge. It never carries an address or a key."""

    def __init__(self, code):
        super().__init__(code, 503)


def address_digest(address):
    """The one-way digest kept in place of an address. The same rule names the sign-up allowance."""
    return hashlib.sha256(address.encode("utf-8")).hexdigest()


def masked_address(address):
    """A short hint an operator can recognise, without the whole address."""
    local, _, domain = address.partition("@")
    return (local[:1] + "***@" + domain) if local and domain else "***"


def provider_mark_present(user):
    """True when a provider user record carries this service's mark."""
    metadata = user.get("app_metadata") if isinstance(user, dict) else None
    return isinstance(metadata, dict) and metadata.get(ACCOUNT_MARKER) == ACCOUNT_MARK


def _origin_payload(row):
    payload = row.get("payload") if isinstance(row, dict) else None
    if not isinstance(payload, dict) or payload.get("record_type") != ORIGIN_VERSION or payload.get("origin") not in ORIGINS:
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return payload


def origin_of(runtime, issuer, subject):
    """This service's own record that it created or marked the account, or None."""
    with runtime._catalog.store() as store:
        row = runtime._catalog.read(store, ORIGIN, (issuer, subject))
    return None if row is None else _origin_payload(row)


def require_admitted(runtime, issuer, user):
    """Refuse a provider identity unless both places say this service created or marked it.

    `user` is the provider's current user record, read for this request. The
    mark in it can be written only through the administration interface, and
    the service record only by this service. Either one alone admits nobody.
    """
    subject = user.get("id") if isinstance(user, dict) else None
    if not isinstance(subject, str) or not provider_mark_present(user):
        raise HttpAuthenticationError(REFUSED_ORIGIN)
    try:
        origin = origin_of(runtime, issuer, subject)
    except ServiceRuntimeError:
        raise HttpAuthenticationError(REFUSED_ORIGIN) from None
    if origin is None or origin.get("issuer") != issuer or origin.get("subject") != subject:
        raise HttpAuthenticationError(REFUSED_ORIGIN)
    return origin


def record_origin(runtime, issuer, subject, origin, reason=""):
    """Write the service's record for one account once. A second call returns the first record."""
    if origin not in ORIGINS or not isinstance(subject, str) or not subject:
        raise ServiceRuntimeError("invalid_account_origin")
    catalog = runtime._catalog
    for _round in range(3):
        with catalog.store(write=True) as store:
            held = catalog.read(store, ORIGIN, (issuer, subject))
            if held is not None:
                return _origin_payload(held)
            row = catalog.record(ORIGIN, (issuer, subject), {
                "record_type": ORIGIN_VERSION, "issuer": issuer, "subject": subject, "origin": origin,
                "reason": reason, "provider_mark": ACCOUNT_MARK, "recorded_at": int(runtime._now())})
            try:
                catalog.commit(store, (row,), (catalog.guard(None, row["record_id"]),))
            except ServiceRuntimeError as error:
                if error.code != "concurrent_update":
                    raise
                continue
            return row["payload"]
    raise ServiceRuntimeError("concurrent_update")


@dataclass(frozen=True)
class IdentityAdministrationRequest:
    """One bounded request to the identity provider's administration interface."""

    method: str
    url: str
    body: dict | None = field(repr=False)
    timeout_seconds: float
    maximum_response_bytes: int

    def __post_init__(self):
        if self.method not in METHODS or USERS_PATH not in self.url or "#" in self.url:
            raise ServiceRuntimeError("unsupported_identity_administration_request")
        if (type(self.timeout_seconds) not in (int, float) or not 0 < self.timeout_seconds <= 30
                or type(self.maximum_response_bytes) is not int or not 1 <= self.maximum_response_bytes <= 4_194_304):
            raise ServiceRuntimeError("invalid_identity_administration_limits")


def send_identity_administration(request, secret):
    """Send exactly one request. Redirects are refused, no proxy is inherited, nothing is repeated."""
    import httpx
    from .account_email import _answer
    if not isinstance(request, IdentityAdministrationRequest):
        raise ServiceRuntimeError("unsupported_identity_administration_request")
    deadline = time.monotonic() + request.timeout_seconds
    body = None if request.body is None else json.dumps(request.body).encode("utf-8")
    headers = {"apikey": secret, "Authorization": "Bearer " + secret, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with httpx.Client(timeout=request.timeout_seconds, follow_redirects=False, trust_env=False) as client:
            with client.stream(request.method, request.url, headers=headers, content=body) as response:
                return _answer(response, request.maximum_response_bytes, "identity_administration_unavailable",
                               deadline)
    except ServiceHttpError:
        raise
    except Exception:
        raise IdentityAdministrationError("identity_administration_unavailable") from None


@dataclass(frozen=True)
class IdentityUser:
    """What this service reads about one provider user. It holds no password and no token."""

    user_id: str
    email: str = field(repr=False)
    created_at: str
    email_confirmed_at: str
    last_sign_in_at: str
    marked: bool
    invitation_marked: bool


def _moment_text(value):
    return value if isinstance(value, str) and len(value) <= 64 else ""


def identity_user(payload):
    """Read one provider user record, flat or wrapped in `user`, or refuse it."""
    value = payload.get("user") if isinstance(payload, dict) and isinstance(payload.get("user"), dict) else payload
    if not isinstance(value, dict):
        raise IdentityAdministrationError("identity_account_answer_unusable")
    user_id, email = value.get("id"), value.get("email")
    if not isinstance(user_id, str) or not PROVIDER_USER_ID.fullmatch(user_id) or not isinstance(email, str) or not email:
        raise IdentityAdministrationError("identity_account_answer_unusable")
    metadata = value.get("app_metadata") if isinstance(value.get("app_metadata"), dict) else {}
    return IdentityUser(user_id, email.strip().lower(), _moment_text(value.get("created_at")),
                        _moment_text(value.get("email_confirmed_at")), _moment_text(value.get("last_sign_in_at")),
                        provider_mark_present(value), metadata.get(INVITATION_MARKER) is not None)


class SupabaseIdentityAdministration:
    """The Supabase engine behind the `identity_administration/v1` edge.

    Five operations, each exactly one request except a lookup, which reads at
    most a few pages: create a marked user, find the user of one address,
    delete a user, mark a user, and read one page of users. A refusal of this
    service itself, status 401, 403 or 429, is reported as such and never read
    as a statement about an address.
    """

    protocol_version = IDENTITY_ADMINISTRATION_PROTOCOL

    def __init__(self, origin, *, allow_network, timeout_seconds=10.0, maximum_response_bytes=262_144,
                 transport=None):
        if type(allow_network) is not bool or (transport is not None and not callable(transport)):
            raise ServiceRuntimeError("invalid_identity_administration")
        self.origin, self.allow_network = origin.rstrip("/"), allow_network
        self.timeout_seconds, self.maximum_response_bytes = timeout_seconds, maximum_response_bytes
        self._transport = transport or send_identity_administration

    def _ask(self, method, path, body, secret, unknown):
        from .account_email import ProviderAnswer
        if not self.allow_network:
            raise IdentityAdministrationError("identity_network_authority_required")
        request = IdentityAdministrationRequest(method, self.origin + path, body, self.timeout_seconds,
                                                self.maximum_response_bytes)
        try:
            answer = self._transport(request, secret)
        except ServiceHttpError:
            raise
        except Exception:
            raise IdentityAdministrationError(unknown) from None
        if not isinstance(answer, ProviderAnswer):
            raise IdentityAdministrationError(unknown)
        if answer.status_code in (401, 403, 429):
            raise IdentityAdministrationError("identity_administration_refused")
        return answer

    @staticmethod
    def _user_path(user_id):
        if not isinstance(user_id, str) or not PROVIDER_USER_ID.fullmatch(user_id):
            raise ServiceRuntimeError("invalid_provider_user_identity")
        return USERS_PATH + "/" + user_id

    def create_marked_user(self, email, password, secret):
        """Create an unconfirmed user that carries the mark, or return None when the address is taken."""
        answer = self._ask("POST", USERS_PATH, {"email": email, "password": password, "email_confirm": False,
                                                 "app_metadata": {ACCOUNT_MARKER: ACCOUNT_MARK}},
                           secret, "identity_account_creation_unknown")
        if answer.status_code in (200, 201):
            user = identity_user(answer.payload)
            if user.email != email or not user.marked:
                raise IdentityAdministrationError("identity_account_answer_unusable")
            return user
        # Any other definite refusal may mean the address is taken. The lookup
        # decides; this release reads no field of a refusal body.
        if 400 <= answer.status_code < 500:
            return None
        raise IdentityAdministrationError("identity_account_creation_unknown")

    def find_user(self, email, secret):
        """The one user whose address is exactly `email`, or None. The provider's filter is a substring match."""
        for page in range(1, LOOKUP_PAGES + 1):
            answer = self._ask("GET", USERS_PATH + "?" + urlencode(
                {"filter": email, "page": page, "per_page": LOOKUP_PAGE_SIZE}), None, secret,
                "identity_account_lookup_unavailable")
            users = answer.payload.get("users")
            if answer.status_code != 200 or not isinstance(users, list):
                raise IdentityAdministrationError("identity_account_lookup_unavailable")
            matches = [identity_user(row) for row in users if isinstance(row, dict)
                       and isinstance(row.get("email"), str) and row["email"].strip().lower() == email]
            if len(matches) > 1:
                raise IdentityAdministrationError("identity_account_lookup_ambiguous")
            if matches:
                return matches[0]
            if len(users) < LOOKUP_PAGE_SIZE:
                return None
        raise IdentityAdministrationError("identity_account_lookup_incomplete")

    def delete_user(self, user_id, secret):
        """Delete one user at the provider. Its sessions and refresh tokens go with it."""
        answer = self._ask("DELETE", self._user_path(user_id), None, secret, "identity_account_deletion_unknown")
        if answer.status_code not in (200, 204, 404):
            raise IdentityAdministrationError("identity_account_deletion_unknown")

    def mark_user(self, user_id, secret):
        """Add the mark to one existing user. The provider merges it into the user's app_metadata."""
        answer = self._ask("PUT", self._user_path(user_id), {"app_metadata": {ACCOUNT_MARKER: ACCOUNT_MARK}},
                           secret, "identity_account_marking_unknown")
        if answer.status_code != 200:
            raise IdentityAdministrationError("identity_account_marking_unknown")
        user = identity_user(answer.payload)
        if user.user_id != user_id or not user.marked:
            raise IdentityAdministrationError("identity_account_answer_unusable")
        return user

    def list_users(self, secret, *, page, per_page=LISTING_PAGE_SIZE):
        """One page of provider users, oldest first as the provider orders them."""
        answer = self._ask("GET", USERS_PATH + "?" + urlencode({"page": page, "per_page": per_page}), None,
                           secret, "identity_user_listing_unavailable")
        users = answer.payload.get("users")
        if answer.status_code != 200 or not isinstance(users, list):
            raise IdentityAdministrationError("identity_user_listing_unavailable")
        return [identity_user(row) for row in users]

    def all_users(self, secret):
        """Every provider user, or a refusal when the listing would not end inside its bound."""
        users = []
        for page in range(1, LISTING_PAGES + 1):
            batch = self.list_users(secret, page=page)
            users.extend(batch)
            if len(batch) < LISTING_PAGE_SIZE:
                return users
        raise IdentityAdministrationError("identity_user_listing_incomplete")


def identity_administration_secret(resolver, reference):
    """Resolve the provider's server key, refusing a key of another kind before any request."""
    try:
        value = resolver(reference)
    except Exception:
        raise IdentityAdministrationError("identity_administration_secret_unavailable") from None
    if not isinstance(value, str) or not value.startswith(IDENTITY_KEY_PREFIX) or any(ch.isspace() for ch in value):
        raise IdentityAdministrationError("identity_administration_secret_unusable")
    return value


class AccountOrigins:
    """Creates, recognises, replaces and marks the accounts this service honours."""

    def __init__(self, runtime, issuer, administration):
        if getattr(administration, "protocol_version", None) != IDENTITY_ADMINISTRATION_PROTOCOL:
            raise ServiceRuntimeError("invalid_identity_administration",
                                      f"an identity administration engine speaks {IDENTITY_ADMINISTRATION_PROTOCOL}")
        self.runtime, self.issuer, self.administration = runtime, issuer, administration

    def honoured(self, user):
        """True when one provider user carries the mark and the service holds its record."""
        if not user.marked:
            return False
        try:
            return origin_of(self.runtime, self.issuer, user.user_id) is not None
        except ServiceRuntimeError:
            return False

    def _record(self, subject, origin, reason=""):
        try:
            return record_origin(self.runtime, self.issuer, subject, origin, reason)
        except ServiceRuntimeError:
            raise IdentityAdministrationError("account_origin_record_unavailable") from None

    def prepare_signup(self, email, password, secret):
        """Make sure `email` belongs to one account this service created, and name its provider user.

        A new address gets a marked user and the service record. An address
        whose account carries both marks keeps it: the link that follows either
        confirms it or, for a confirmed account, is refused and the owner is
        sent a notice. An account the service already holds a sign-in for
        predates the one way in, so it keeps its place until the marking
        command marks it, and None asks for the notice. Any other account under
        the address is archived, deleted at the provider and replaced by a
        fresh marked account.
        """
        created = self.administration.create_marked_user(email, password, secret)
        if created is not None:
            self._record(created.user_id, SIGNUP_ORIGIN)
            return created.user_id
        held = self.administration.find_user(email, secret)
        if held is None:
            raise IdentityAdministrationError("identity_account_creation_refused")
        if self.honoured(held):
            return held.user_id
        # Deleting an account the service already holds a sign-in for, on a
        # public request, would let anyone who knows the address end a real
        # person's account and its history. It cannot open without the marks.
        if self.bound(held.user_id):
            return None
        key = self._archive(held, email)
        self.administration.delete_user(held.user_id, secret)
        self._advance(key, state=DELETED, deleted_at=int(self.runtime._now()))
        replacement = self.administration.create_marked_user(email, password, secret)
        if replacement is None:
            raise IdentityAdministrationError("identity_account_replacement_incomplete")
        self._record(replacement.user_id, SIGNUP_ORIGIN)
        self._advance(key, state=REPLACED, replaced_at=int(self.runtime._now()),
                      replacement_provider_user_id=replacement.user_id)
        return replacement.user_id

    def bound(self, subject):
        """True when the service holds a sign-in bound to this provider user."""
        try:
            with self.runtime._catalog.store() as store:
                return self.runtime._catalog.read(store, SUBJECT, (self.issuer, subject)) is not None
        except ServiceRuntimeError:
            raise IdentityAdministrationError("account_origin_record_unavailable") from None

    def _archive(self, held, email):
        """Keep the replaced account's non-secret details before anything is deleted at the provider.

        The address itself is not kept: the published privacy notice lists no
        address in the service database outside the waiting list, so the record
        holds its digest, and the replacement account holds the address. The
        write also requires that no service sign-in is bound to the account, so
        a binding made meanwhile stops the replacement.
        """
        runtime, catalog, key = self.runtime, self.runtime._catalog, (self.issuer, held.user_id)
        try:
            with catalog.store(write=True) as store:
                previous = catalog.read(store, REPLACEMENT, key)
                origin_row = catalog.read(store, ORIGIN, key)
                earlier = previous["payload"] if previous is not None else {}
                row = catalog.record(REPLACEMENT, key, {
                    "record_type": REPLACEMENT_VERSION, "issuer": self.issuer, "provider_user_id": held.user_id,
                    "address_digest": address_digest(email), "provider_created_at": held.created_at,
                    "email_confirmed": bool(held.email_confirmed_at), "email_confirmed_at": held.email_confirmed_at,
                    "last_sign_in_at": held.last_sign_in_at, "provider_mark_present": held.marked,
                    "service_record_present": origin_row is not None,
                    "invitation_mark_present": held.invitation_marked,
                    "state": ARCHIVED, "attempts": earlier.get("attempts", 0) + 1,
                    "archived_at": int(runtime._now()), "deleted_at": None, "replaced_at": None,
                    "replacement_provider_user_id": ""})
                catalog.commit(store, (row,), (catalog.guard(previous, row["record_id"]),
                                               catalog.guard(origin_row, catalog.identity(ORIGIN, key)),
                                               catalog.guard(None, catalog.identity(SUBJECT, key))))
        except ServiceRuntimeError:
            raise IdentityAdministrationError("account_replacement_record_unavailable") from None
        return key

    def _advance(self, key, **changes):
        catalog = self.runtime._catalog
        try:
            with catalog.store(write=True) as store:
                row = catalog.read(store, REPLACEMENT, key)
                if row is None or row["payload"].get("record_type") != REPLACEMENT_VERSION:
                    raise ServiceRuntimeError("unsupported_or_corrupt_record")
                updated = {**row, "record_version": uuid.uuid4().hex, "payload": {**row["payload"], **changes}}
                catalog.commit(store, (updated,), (catalog.guard(row),))
        except ServiceRuntimeError:
            raise IdentityAdministrationError("account_replacement_record_unavailable") from None

    def replacements(self):
        """Every replacement record, newest first, for the superadmin view and the checks."""
        catalog = self.runtime._catalog
        with catalog.store() as store:
            rows = [row["payload"] for row in catalog.rows_all(store, REPLACEMENT)
                    if row["payload"].get("record_type") == REPLACEMENT_VERSION]
        return sorted(rows, key=lambda row: -(row.get("archived_at") or 0))

    def marking_plan(self, secret, policy):
        """List every change the marking command would make, and change nothing.

        An account is marked when the service already holds a sign-in bound to
        it, or when the host's staff list names it. Everything else is listed as
        left unmarked: it stays refused, and it is replaced if its owner signs
        up through Baltor.
        """
        users = self.administration.all_users(secret)
        catalog = self.runtime._catalog
        with catalog.store() as store:
            bound = {row["payload"].get("subject"): row["payload"].get("tenant_id", "")
                     for row in catalog.rows_all(store, SUBJECT) if row["payload"].get("issuer") == self.issuer}
            recorded = {row["payload"].get("subject") for row in catalog.rows_all(store, ORIGIN)
                        if row["payload"].get("issuer") == self.issuer}
        items, unmarked, honoured = [], [], 0
        for user in users:
            has_record = user.user_id in recorded
            if user.marked and has_record:
                honoured += 1
                continue
            reason = (SERVICE_ACCOUNT_REASON if user.user_id in bound
                      else STAFF_REASON if policy.role_for(user.user_id, user.email) else "")
            if reason:
                items.append({"provider_user_id": user.user_id, "address_hint": masked_address(user.email),
                              "reason": reason, "set_provider_mark": not user.marked,
                              "write_service_record": not has_record})
            else:
                unmarked.append({"provider_user_id": user.user_id, "address_hint": masked_address(user.email),
                                 "email_confirmed": bool(user.email_confirmed_at),
                                 "invitation_mark_present": user.invitation_marked})
        items.sort(key=lambda item: item["provider_user_id"])
        seen = {user.user_id for user in users}
        return {"record_type": PLAN_VERSION, "issuer": self.issuer, "changes": items,
                "plan_digest": digest({"issuer": self.issuer, "changes": [
                    {name: item[name] for name in ("provider_user_id", "reason", "set_provider_mark",
                                                  "write_service_record")} for item in items]}),
                "already_honoured": honoured, "left_unmarked": sorted(unmarked, key=lambda row: row["provider_user_id"]),
                "service_sign_ins_without_a_provider_user": sorted(subject for subject in bound if subject not in seen),
                "provider_users": len(users), "changed": False}

    def apply_marking(self, secret, policy, expected_plan_digest):
        """Apply exactly the plan the operator read, or refuse when it changed since."""
        if not isinstance(expected_plan_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_plan_digest):
            raise ServiceRuntimeError("account_marking_plan_digest_required",
                                      "run the command without --apply first and pass the plan_digest it printed")
        plan = self.marking_plan(secret, policy)
        if plan["plan_digest"] != expected_plan_digest:
            raise ServiceRuntimeError("account_marking_plan_changed",
                                      "the accounts changed after the plan was read; read the new plan first")
        applied = []
        for item in plan["changes"]:
            if item["write_service_record"]:
                self._record(item["provider_user_id"], MIGRATION_ORIGIN, item["reason"])
            if item["set_provider_mark"]:
                self.administration.mark_user(item["provider_user_id"], secret)
            applied.append(item["provider_user_id"])
        return {"record_type": MARKING_RESULT_VERSION, "plan_digest": plan["plan_digest"],
                "applied": applied, "changed": bool(applied), "left_unmarked": len(plan["left_unmarked"])}


def run_mark_accounts(path, *, apply=False, expected_plan=None):
    """The operator command: read the host file, list the plan, and apply it only when asked to.

    It starts no server. It needs the browser identity block, the account
    email block, whose identity settings and server key it uses, and host write
    authority to apply.
    """
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, _host_json, account_policy, environment_secret
    from .records import ServiceRuntimeConfig
    from .runtime import ServiceRuntime
    configuration = _host_json(path)
    if (configuration.get("record_type") != HOST_CONFIGURATION_VERSION or "runtime" not in configuration
            or not isinstance(configuration.get("browser_identity"), dict)
            or not isinstance(configuration.get("account_email"), dict)):
        raise ServiceRuntimeError("account_marking_needs_identity_settings",
                                  "the host file needs its runtime, browser_identity and account_email blocks")
    identity = configuration["account_email"]
    origin = identity.get("identity_origin", "")
    if origin != configuration["browser_identity"].get("project_url"):
        raise ServiceRuntimeError("account_email_identity_origin_mismatch")
    runtime = ServiceRuntime(ServiceRuntimeConfig(**configuration["runtime"]))
    administration = SupabaseIdentityAdministration(origin, allow_network=identity.get("allow_network") is True,
                                                    timeout_seconds=identity.get("timeout_seconds", 10.0))
    origins = AccountOrigins(runtime, origin.rstrip("/") + "/auth/v1", administration)
    secret = identity_administration_secret(environment_secret, identity.get("identity_service_key_ref"))
    policy = account_policy(configuration)
    if apply:
        return origins.apply_marking(secret, policy, expected_plan)
    return origins.marking_plan(secret, policy)
