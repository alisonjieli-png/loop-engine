"""Exact-version, account-required free access over the existing CatalogStore.

Internal service mechanics, not a runtime or an admission system. Operators
select already admitted bytes; tags never select access. Ordinary entitlement
and paid usage records are unchanged. Reservations count each attempt, even
failed reads, in an atomic per-account fixed window. Delivery records state an
authorized response, not proof that a network peer received it.
One record per account/item version/month is replaced by later responses;
it supports report eligibility, not the requested history of every download.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import hmac
import math
import re
import uuid

from ..provisioning_server import ACCOUNT_GRANT_RECORD_TYPE, QUALIFICATION_APPROVED, ProvisioningGrant, ProvisioningItemBinding, ProvisioningQualification
from .catalogue_grants import release_following_grants, snapshot_grants
from .records import CLIENT_ACCESS_PROFILE, ServiceRuntimeError, digest, text

POLICY_KIND = "service_public_good_policy"
POLICY_VERSION = POLICY_KIND + "/v1"
POLICY_LOGICAL = "active"
GRANT_VERSION = "service_public_good_access_grant/v1"
LIMITS_VERSION = "service_public_good_limits/v1"
WINDOW_KIND = "service_public_good_window"
WINDOW_VERSION = WINDOW_KIND + "/v1"
HOST_WINDOW_KIND = "service_public_good_host_window"
DELIVERY_KIND = "service_public_good_delivery"
DELIVERY_VERSION = DELIVERY_KIND + "/v1"
EVENT_KIND = "service_public_good_policy_event"
MAXIMUM_CONCURRENT_RETRIES = 8


def _refuse(code="public_good_record_invalid"):
    raise ServiceRuntimeError(code)


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        _refuse()


def _shape(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        _refuse()


@dataclass(frozen=True)
class PublicGoodLimits:
    requests_per_window: int = 60
    bytes_per_window: int = 64 * 1024 * 1024
    window_seconds: int = 3600
    maximum_response_bytes: int = 16 * 1024 * 1024
    host_requests_per_window: int = 300
    host_bytes_per_window: int = 256 * 1024 * 1024
    record_type: str = LIMITS_VERSION

    def __post_init__(self):
        if self.record_type != LIMITS_VERSION:
            _refuse("public_good_limits_invalid")
        for value, ceiling in ((self.requests_per_window, 10000), (self.bytes_per_window, 2**40),
                               (self.window_seconds, 86400), (self.maximum_response_bytes, 2**30),
                               (self.host_requests_per_window, 100000), (self.host_bytes_per_window, 2**40)):
            if type(value) is not int or not 1 <= value <= ceiling:
                _refuse("public_good_limits_invalid")
        if self.maximum_response_bytes > min(self.bytes_per_window, self.host_bytes_per_window):
            _refuse("public_good_limits_invalid")

    @classmethod
    def from_dict(cls, value):
        _shape(value, cls.__dataclass_fields__)
        return cls(**value)


@dataclass(frozen=True)
class PublicGoodGrant:
    binding: ProvisioningItemBinding
    item_version: str
    approval_ref: str
    rights_ref: str
    sdg_goals: tuple[int, ...]
    public_benefit_reason: str
    expires_at: int
    initiatives: tuple[str, ...] = ()
    useful_paths: tuple[str, ...] = ()
    display_name: str = ""
    active: bool = True
    record_type: str = GRANT_VERSION

    def __post_init__(self):
        if self.record_type != GRANT_VERSION or not isinstance(self.binding, ProvisioningItemBinding):
            _refuse()
        _sha(self.item_version)
        for value in (self.approval_ref, self.rights_ref, self.public_benefit_reason):
            if not isinstance(value, str) or not value.strip() or len(value) > 2000 or not value.isprintable():
                _refuse()
        if not isinstance(self.sdg_goals, (tuple, list)):
            _refuse()
        goals = tuple(self.sdg_goals)
        if any(type(goal) is not int or not 1 <= goal <= 17 for goal in goals) or len(set(goals)) != len(goals):
            _refuse()
        object.__setattr__(self, "sdg_goals", tuple(sorted(goals)))
        initiatives = tuple(self.initiatives) if isinstance(self.initiatives, (list, tuple)) else None
        if (initiatives is None or len(initiatives) > 32
                or any(not isinstance(value, str) or not re.fullmatch("[a-z][a-z0-9-]{0,63}", value) for value in initiatives)
                or len(set(initiatives)) != len(initiatives) or type(self.active) is not bool
                or not goals and not initiatives):
            _refuse()
        object.__setattr__(self, "initiatives", initiatives)
        from .catalogue_packages import placement_path
        if not isinstance(self.useful_paths, (list, tuple)):
            _refuse()
        paths = tuple(self.useful_paths)
        for path in paths:
            placement_path(path)
        if len(paths) != len(set(paths)):
            _refuse()
        object.__setattr__(self, "useful_paths", paths)
        if not isinstance(self.display_name, str) or len(self.display_name) > 120 or self.display_name and not self.display_name.isprintable():
            _refuse()
        if type(self.expires_at) is not int or self.expires_at <= 0:
            _refuse()

    @classmethod
    def from_dict(cls, value):
        _shape(value, cls.__dataclass_fields__)
        _shape(value["binding"], ProvisioningItemBinding.__dataclass_fields__)
        try:
            return cls(**{**value, "binding": ProvisioningItemBinding(**value["binding"])})
        except (TypeError, ValueError):
            _refuse()


@dataclass(frozen=True)
class PublicGoodSnapshot:
    grants: tuple[PublicGoodGrant, ...]
    limits: PublicGoodLimits
    version: str
    guard: object = field(repr=False)
    state_guard: object = field(repr=False)

    @property
    def fingerprint(self):
        """Cache identity includes the eligible set, so expiry invalidates it too."""
        return digest([self.version, [(grant.binding.identity, grant.item_version) for grant in self.grants]])


@dataclass(frozen=True)
class PublicGoodReservation:
    tenant_id: str
    grant: PublicGoodGrant
    policy_version: str
    reservation_id: str
    request_id_digest: str
    response_bytes: int
    expires_at: int
    auth_guards: tuple = field(repr=False)
    _issuer: object = field(repr=False, compare=False)
    _proof: str = field(default="", repr=False)


class PublicGoodLimitError(ServiceRuntimeError):
    def __init__(self, retry_after_seconds):
        super().__init__("public_good_rate_limited")
        self.retry_after_seconds = max(1, math.ceil(retry_after_seconds))


def _matches(grant, view):
    item = view.catalogue.items.get(grant.binding.identity)
    if (item is None or view.item_versions.get(item.identity) != grant.item_version
            or ProvisioningItemBinding.from_item(item) != grant.binding
            or (item.identity, item.digest) in view.withdrawn):
        return False
    if grant.useful_paths:
        package = view.packages.get(item.identity)
        if package is None or not set(grant.useful_paths) <= {entry.path for entry in package.files}:
            return False
    try:
        decision = view.qualification_resolver.resolve(grant.binding)
    except Exception:
        return False
    return (isinstance(decision, ProvisioningQualification) and decision.status == QUALIFICATION_APPROVED and decision.binding == grant.binding
            and decision.approval_ref == grant.approval_ref)


class PublicGoodAccess:
    """Host-owned domain adapter; no HTTP or identity-provider authority."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.catalog = runtime._catalog
        self._issuer = object()

    def _policy(self, store):
        row = self.catalog.read(store, POLICY_KIND, POLICY_LOGICAL)
        if row is None:
            return None, (), PublicGoodLimits()
        value = row["payload"]
        _shape(value, ("record_type", "limits", "grants"))
        if value["record_type"] != POLICY_VERSION or not isinstance(value["grants"], list):
            _refuse()
        limits = PublicGoodLimits.from_dict(value["limits"])
        grants = tuple(PublicGoodGrant.from_dict(part) for part in value["grants"])
        if len({grant.binding.identity for grant in grants}) != len(grants):
            _refuse()
        return row, grants, limits

    def _snapshot(self, store, view):
        from .catalogue_releases import STATE_KIND, STATE_LOGICAL, is_withdrawn, read_state
        from .catalogue_grants import require_served_state
        row, grants, limits = self._policy(store)
        state_row, state = read_state(self.catalog, store)
        if grants:
            require_served_state(state, view)
        now = self.runtime._now()
        eligible = tuple(grant for grant in grants if grant.active and grant.expires_at > now and _matches(grant, view)
                         and not is_withdrawn(self.catalog, store, grant.binding.identity, grant.binding.body_digest))
        return PublicGoodSnapshot(eligible, limits, row["record_version"] if row else "",
            self.catalog.guard(row, self.catalog.identity(POLICY_KIND, POLICY_LOGICAL)),
            self.catalog.guard(state_row, self.catalog.identity(STATE_KIND, STATE_LOGICAL)))

    def snapshot(self, view):
        """Current eligible grant metadata only; this grants no anonymous body access."""
        with self.catalog.store() as store:
            return self._snapshot(store, view)

    def configure(self, view, grants, *, limits=None, expected_version=None):
        """Host-only atomic replacement of exact grants; never admits new content."""
        from .catalogue_grants import require_served_state
        from .catalogue_releases import STATE_KIND, STATE_LOGICAL, read_state, is_withdrawn
        grants = tuple(grants)
        limits = limits if limits is not None else PublicGoodLimits()
        if not isinstance(limits, PublicGoodLimits) or any(not isinstance(grant, PublicGoodGrant) for grant in grants):
            _refuse()
        if len({grant.binding.identity for grant in grants}) != len(grants):
            _refuse()
        with self.catalog.store(write=True) as store:
            previous, _held, _limits = self._policy(store)
            if (previous["record_version"] if previous else None) != expected_version:
                _refuse("public_good_policy_changed")
            state_row, state = read_state(self.catalog, store)
            require_served_state(state, view)
            if any(grant.expires_at <= self.runtime._now() or not _matches(grant, view)
                   or is_withdrawn(self.catalog, store, grant.binding.identity, grant.binding.body_digest) for grant in grants):
                _refuse("public_good_grant_not_current")
            payload = {"record_type": POLICY_VERSION, "limits": asdict(limits), "grants": [asdict(grant) for grant in grants]}
            row = self.catalog.record(POLICY_KIND, POLICY_LOGICAL, payload)
            event = self.catalog.record(EVENT_KIND, row["record_version"], {
                "record_type": EVENT_KIND + "/v1", "policy_version": row["record_version"],
                "previous_version": expected_version, "policy_digest": digest(payload),
                "grants": len(grants), "at": self.runtime._now()})
            self.catalog.commit(store, (row, event), (self.catalog.guard(previous, row["record_id"]),
                self.catalog.guard(state_row, self.catalog.identity(STATE_KIND, STATE_LOGICAL)),
                self.catalog.guard(None, event["record_id"])))
        return {"record_type": POLICY_VERSION, "version": row["record_version"], "grants": len(grants), "committed": True}

    def _account(self, store, principal):
        from .runtime import GRANTS, KEY, OWNER_BOUND_KEY_SCHEMA, PROVISIONING_READ_SCOPE, SCHEMAS, SUBJECT
        current, guards = self.runtime._revalidate(store, principal)
        _tenant_row, tenant = self.runtime._tenant(store, current.tenant_id)
        allowed = tenant.get("body_access_revoked") is False and PROVISIONING_READ_SCOPE in current.scopes
        if current.authentication_kind == KEY:
            row = self.catalog.read_id(store, current.authentication_record_id, kind=KEY)
            value = row["payload"]
            allowed = allowed and value.get("record_type") == OWNER_BOUND_KEY_SCHEMA and value.get("management_profile") == CLIENT_ACCESS_PROFILE
        elif current.authentication_kind != SUBJECT:
            allowed = False
        granted = self.catalog.read(store, GRANTS, current.tenant_id)
        denied = set()
        if granted is not None:
            value = self.runtime._payload(granted, GRANTS)
            if value["record_type"] == SCHEMAS[GRANTS]:
                denied = {grant.binding.identity for grant in snapshot_grants(value, current.tenant_id) if not grant.body_allowed}
            else:
                denied = set(release_following_grants(value, current.tenant_id).denials)
        return current, (*guards, self.catalog.guard(granted, self.catalog.identity(GRANTS, current.tenant_id))), denied, bool(allowed)

    def _selected(self, store, principal, view, identity, expected_digest=None):
        current, guards, denied, allowed = self._account(store, principal)
        snapshot = self._snapshot(store, view)
        grant = next((entry for entry in snapshot.grants if entry.binding.identity == identity), None)
        if not allowed or identity in denied or grant is None or (expected_digest is not None and grant.binding.body_digest != expected_digest):
            grant = None
        return current, guards, snapshot, grant

    def allows(self, principal, view, identity, expected_digest=None):
        with self.catalog.store() as store:
            return self._selected(store, principal, view, identity, expected_digest)[3] is not None

    def overlay(self, principal, view, grants, *, candidates=None):
        """Effective item grants and one authority token for this request."""
        with self.catalog.store() as store:
            current, _guards, denied, allowed = self._account(store, principal)
            snapshot = self._snapshot(store, view)
        chosen = None if candidates is None else set(candidates)
        effective = {grant.binding.identity: grant for grant in grants}
        if allowed:
            for grant in snapshot.grants:
                identity = grant.binding.identity
                if identity not in denied and (chosen is None or identity in chosen):
                    effective[identity] = ProvisioningGrant(current.tenant_id, grant.binding, True, "unmetered", ACCOUNT_GRANT_RECORD_TYPE)
        token = (snapshot.version, tuple((entry.binding.identity, entry.item_version) for entry in snapshot.grants), allowed, tuple(sorted(denied)))
        return tuple(effective.values()), token

    def _proof(self, reservation):
        document = {name: getattr(reservation, name) for name in ("tenant_id", "policy_version", "reservation_id", "request_id_digest", "response_bytes", "expires_at")}
        document.update(grant=asdict(reservation.grant), auth_guards=[asdict(guard) for guard in reservation.auth_guards])
        return hmac.new(self.runtime._principal_secret, digest(document).encode(), hashlib.sha256).hexdigest()

    def _window(self, store, tenant, now, limits, *, host=False):
        row = self.catalog.read(store, HOST_WINDOW_KIND if host else WINDOW_KIND, "all_accounts" if host else tenant)
        start = int(now) // limits.window_seconds * limits.window_seconds
        value = row["payload"] if row else None
        if value is not None:
            _shape(value, ("record_type", "tenant_id", "start", "end", "policy_limits", "requests", "bytes_reserved", "reservations"))
            if value["record_type"] != WINDOW_VERSION or value["tenant_id"] != tenant:
                _refuse()
            if (any(type(value[name]) is not int or value[name] < 0 for name in ("start", "end", "requests", "bytes_reserved"))
                    or value["start"] >= value["end"] or not isinstance(value["reservations"], dict)):
                _refuse()
        if value is None or now >= value["end"]:
            value = {"record_type": WINDOW_VERSION, "tenant_id": tenant, "start": start, "end": start + limits.window_seconds,
                     "policy_limits": asdict(limits), "requests": 0, "bytes_reserved": 0, "reservations": {}}
        elif value["policy_limits"] != asdict(limits):
            # A limits change applies to the current window at once and does not reset it: what the window has spent
            # stays spent and is judged by the new limits, so a raise helps every account now and a cut refuses only
            # an account already past it, until the window ends. A new window length starts with the next window.
            value = {**value, "policy_limits": asdict(limits)}
        return row, value

    def reserve(self, principal, view, identity, *, expected_digest, request_id, response_bytes):
        """Reserve each actual attempt; failures/retries do not refund service work."""
        _sha(expected_digest)
        text(request_id, "public good request identity")
        if len(request_id) > 512 or type(response_bytes) is not int or response_bytes < 0:
            _refuse("public_good_reservation_invalid")
        from dataclasses import replace
        for attempt in range(MAXIMUM_CONCURRENT_RETRIES):
            try:
                with self.catalog.store(write=True) as store:
                    current, guards, snapshot, grant = self._selected(store, principal, view, identity, expected_digest)
                    if grant is None:
                        return None
                    if response_bytes > snapshot.limits.maximum_response_bytes:
                        _refuse("public_good_response_limit")
                    # Every reservation changes the one host window. The window writes of this process take turns from
                    # reading the windows to the commit, so they wait for one another instead of refusing one another.
                    with self.catalog.serialized(WINDOW_KIND):
                        now = self.runtime._now()
                        previous, window = self._window(store, current.tenant_id, now, snapshot.limits)
                        previous_host, host_window = self._window(store, "", now, snapshot.limits, host=True)
                        if window["requests"] >= snapshot.limits.requests_per_window or window["bytes_reserved"] + response_bytes > snapshot.limits.bytes_per_window:
                            raise PublicGoodLimitError(window["end"] - now)
                        if (host_window["requests"] >= snapshot.limits.host_requests_per_window
                                or host_window["bytes_reserved"] + response_bytes > snapshot.limits.host_bytes_per_window):
                            raise PublicGoodLimitError(host_window["end"] - now)
                        reservation = PublicGoodReservation(current.tenant_id, grant, snapshot.version, uuid.uuid4().hex,
                            digest(request_id), response_bytes, min(window["end"], grant.expires_at), tuple(guards), self._issuer)
                        reservation = replace(reservation, _proof=self._proof(reservation))
                        updated = {**window, "requests": window["requests"] + 1, "bytes_reserved": window["bytes_reserved"] + response_bytes,
                                   "reservations": {**window["reservations"], reservation.reservation_id: {"proof": reservation._proof, "state": "reserved"}}}
                        row = self.catalog.record(WINDOW_KIND, current.tenant_id, updated, tenant_id=current.tenant_id)
                        host_row = self.catalog.record(HOST_WINDOW_KIND, "all_accounts",
                            {**host_window, "requests": host_window["requests"] + 1,
                             "bytes_reserved": host_window["bytes_reserved"] + response_bytes})
                        self.catalog.commit(store, (row, host_row), (*guards, snapshot.guard, snapshot.state_guard,
                            self.catalog.guard(previous, row["record_id"]), self.catalog.guard(previous_host, host_row["record_id"])))
                return reservation
            except ServiceRuntimeError as error:
                if error.code != "concurrent_update" or attempt == MAXIMUM_CONCURRENT_RETRIES - 1:
                    raise
        _refuse("concurrent_update")

    def _validate(self, store, reservation, principal, view, *, completed=False):
        current, guards, snapshot = self._authorized(store, reservation, principal, view)
        return current, guards, snapshot, self._held(store, reservation, current, completed=completed)

    def _authorized(self, store, reservation, principal, view):
        if (not isinstance(reservation, PublicGoodReservation) or reservation._issuer is not self._issuer
                or not hmac.compare_digest(reservation._proof, self._proof(reservation))):
            _refuse("public_good_reservation_invalid")
        current, guards, snapshot, grant = self._selected(store, principal, view, reservation.grant.binding.identity, reservation.grant.binding.body_digest)
        if current.tenant_id != reservation.tenant_id:
            _refuse("public_good_reservation_invalid")
        if self.runtime._now() >= reservation.expires_at or grant != reservation.grant or snapshot.version != reservation.policy_version:
            _refuse("public_good_authority_changed")
        if tuple(guards) != reservation.auth_guards:
            _refuse("public_good_authority_changed")
        if view.withdrawal_check is not None:
            view.withdrawal_check(grant.binding.identity, grant.binding.body_digest)
        return current, guards, snapshot

    def _held(self, store, reservation, current, *, completed=False):
        window = self.catalog.read(store, WINDOW_KIND, current.tenant_id)
        value = window["payload"] if window else {}
        entry = value.get("reservations", {}).get(reservation.reservation_id, {})
        if value.get("record_type") != WINDOW_VERSION or entry.get("proof") != reservation._proof:
            _refuse("public_good_reservation_invalid")
        if entry.get("state") != ("complete" if completed else "reserved"):
            _refuse("public_good_reservation_closed")
        return window

    def revalidate(self, reservation, principal, view):
        """Final transport guard, including policy, expiry, scope, account and withdrawal."""
        with self.catalog.store() as store:
            self._validate(store, reservation, principal, view)
        return True

    def complete(self, reservation, principal, view, *, response_bytes):
        """Close a reservation and store an authorized_response, not network delivery.

        The account/item-version/month key replaces the preceding record in
        that month. Every-download history remains a separate unimplemented
        transport/activity requirement.
        """
        if type(response_bytes) is not int or response_bytes < 0 or not isinstance(reservation, PublicGoodReservation) or response_bytes > reservation.response_bytes:
            _refuse("public_good_reservation_invalid")
        from .usage_meter import usage_period
        for attempt in range(MAXIMUM_CONCURRENT_RETRIES):
            try:
                with self.catalog.store(write=True) as store:
                    current, guards, snapshot = self._authorized(store, reservation, principal, view)
                    # The account window takes turns with the reservations of this process, as in `reserve`.
                    with self.catalog.serialized(WINDOW_KIND):
                        window = self._held(store, reservation, current)
                        now = self.runtime._now()
                        selected = reservation.grant
                        logical = (current.tenant_id, selected.binding.identity, selected.binding.body_digest, selected.item_version, usage_period(now))
                        previous = self.catalog.read(store, DELIVERY_KIND, logical)
                        payload = {"record_type": DELIVERY_VERSION, "tenant_id": current.tenant_id,
                            "item_identity": selected.binding.identity, "body_digest": selected.binding.body_digest,
                            "item_version": selected.item_version, "policy_version": snapshot.version,
                            "response_bytes": response_bytes, "billed_quantity": 0, "at": now,
                            "outcome": "authorized_response", "request_id_digest": reservation.request_id_digest}
                        delivery = self.catalog.record(DELIVERY_KIND, logical, payload, tenant_id=current.tenant_id)
                        value = window["payload"]
                        updated = self.catalog.record(WINDOW_KIND, current.tenant_id,
                            {**value, "reservations": {**value["reservations"], reservation.reservation_id: {"proof": reservation._proof, "state": "complete"}}},
                            tenant_id=current.tenant_id)
                        self.catalog.commit(store, (delivery, updated), (*guards, snapshot.guard, snapshot.state_guard,
                            self.catalog.guard(window), self.catalog.guard(previous, delivery["record_id"])))
                # Clock expiry or revocation may have crossed the commit itself.
                with self.catalog.store() as store:
                    self._validate(store, reservation, principal, view, completed=True)
                return {**payload, "record_ref": delivery["record_id"], "committed": True}
            except ServiceRuntimeError as error:
                if error.code != "concurrent_update" or attempt == MAXIMUM_CONCURRENT_RETRIES - 1:
                    raise
        _refuse("concurrent_update")


def downloaded(binding, store, tenant_id, identity, body_digest):
    """Exact nonbillable delivery record for the existing customer-report boundary."""
    for row in binding.rows(store, DELIVERY_KIND, tenant_id):
        value = row["payload"]
        if (value.get("record_type") == DELIVERY_VERSION and value.get("tenant_id") == tenant_id
                and value.get("item_identity") == identity and value.get("body_digest") == body_digest
                and value.get("outcome") == "authorized_response" and value.get("billed_quantity") == 0):
            return True
    return False
