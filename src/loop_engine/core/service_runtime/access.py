"""Host-configured administration and customer management of scoped credentials.

This is an internal service adapter, not an executable runtime. It extends
the existing catalogue authority and requires an issued administrator
principal or an exact verified customer session on every call. No password, email, payment or model account is
created. Raw credentials are returned once, never put in a stored record.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import secrets
import uuid

from .records import ACCESS_MANAGE_SCOPE, CLIENT_ACCESS_PROFILE, DEFAULT_SCOPES, ServiceRuntimeError, digest, identifier, scopes, text
from .runtime import KEY, OWNER_BOUND_KEY_SCHEMA, SCHEMAS, SESSION_REVOCATION, SUBJECT, TENANT, ServiceRuntime

POLICY_VERSION = "service_access_administration/v1"
REQUEST_VERSION = "service_access_request/v1"
RESULT_VERSION = "service_access_result/v1"
OPERATION_KIND = "service_access_operation"
CLIENT_REQUEST_VERSION = "service_client_access_request/v1"


def _validate_limits(policy):
    selected = scopes(policy.allowed_scopes)
    if not selected or not set(selected) <= set(DEFAULT_SCOPES):
        raise ServiceRuntimeError("privileged_scope_delegation_refused")
    if (type(policy.maximum_active_tokens) is not int or not 1 <= policy.maximum_active_tokens <= 1000
            or type(policy.maximum_lifetime_seconds) is not int or not 60 <= policy.maximum_lifetime_seconds <= 2592000
            or type(policy.default_lifetime_seconds) is not int
            or not 60 <= policy.default_lifetime_seconds <= policy.maximum_lifetime_seconds):
        raise ServiceRuntimeError("invalid_access_policy")
    object.__setattr__(policy, "allowed_scopes", selected)


@dataclass(frozen=True)
class ServiceAccessPolicy:
    """Passive owner-installed delegation limits; requests cannot expand them."""

    administrator_tenants: tuple[str, ...]
    target_tenants: tuple[str, ...]
    allowed_scopes: tuple[str, ...] = DEFAULT_SCOPES
    maximum_active_tokens: int = 20
    maximum_lifetime_seconds: int = 604800
    default_lifetime_seconds: int = 86400
    writes_authorized: bool = False
    record_type: str = POLICY_VERSION

    def __post_init__(self):
        if self.record_type != POLICY_VERSION or type(self.writes_authorized) is not bool:
            raise ServiceRuntimeError("invalid_access_policy")
        for field in ("administrator_tenants", "target_tenants"):
            values = tuple(getattr(self, field))
            if not values or len(values) > 20 or len(set(values)) != len(values):
                raise ServiceRuntimeError("invalid_access_policy")
            for value in values:
                identifier(value, "configured tenant")
            object.__setattr__(self, field, values)
        if set(self.administrator_tenants) & set(self.target_tenants):
            raise ServiceRuntimeError("administrator_self_delegation_refused")
        _validate_limits(self)


@dataclass(frozen=True)
class ServiceClientAccessPolicy:
    """Customer-owned credentials; no caller-selected tenant or privileged scope."""

    allowed_scopes: tuple[str, ...] = DEFAULT_SCOPES
    maximum_active_tokens: int = 10
    maximum_lifetime_seconds: int = 604800
    default_lifetime_seconds: int = 86400
    maximum_token_records: int = 1000
    writes_authorized: bool = False
    record_type: str = CLIENT_ACCESS_PROFILE

    def __post_init__(self):
        if self.record_type != CLIENT_ACCESS_PROFILE or type(self.writes_authorized) is not bool:
            raise ServiceRuntimeError("invalid_access_policy")
        _validate_limits(self)
        if (type(self.maximum_token_records) is not int
                or not self.maximum_active_tokens <= self.maximum_token_records <= 10000):
            raise ServiceRuntimeError("invalid_access_policy")


@dataclass(frozen=True)
class ServiceAccessSession:
    """Verified transport facts, without a raw token; not accepted from request JSON."""

    authentication_record_id: str
    credential_digest: str
    expires_at: float
    allowed_scopes: tuple[str, ...]

    def __post_init__(self):
        identifier(self.authentication_record_id, "subject binding")
        if (not isinstance(self.credential_digest, str) or len(self.credential_digest) != 64
                or any(value not in "0123456789abcdef" for value in self.credential_digest)
                or type(self.expires_at) not in (int, float) or not math.isfinite(self.expires_at)
                or self.expires_at <= 0):
            raise ServiceRuntimeError("invalid_access_session")
        object.__setattr__(self, "allowed_scopes", scopes(self.allowed_scopes))


@dataclass(frozen=True)
class ServiceAccessRequest:
    operation: str
    request_id: str
    tenant_id: str
    label: str = ""
    scopes: tuple[str, ...] = ()
    lifetime_seconds: int = 0
    key_id: str = ""
    record_type: str = REQUEST_VERSION

    def __post_init__(self):
        if self.record_type != REQUEST_VERSION or self.operation not in ("issue", "revoke"):
            raise ServiceRuntimeError("invalid_access_request")
        identifier(self.request_id, "request identity")
        identifier(self.tenant_id, "tenant identity")
        if self.operation == "issue":
            text(self.label, "token label")
            if len(self.label) > 100 or self.key_id or type(self.lifetime_seconds) is not int or self.lifetime_seconds < 60:
                raise ServiceRuntimeError("invalid_access_request")
            selected = scopes(self.scopes)
            if not selected:
                raise ServiceRuntimeError("invalid_access_request")
            object.__setattr__(self, "scopes", selected)
        elif self.label or self.scopes or self.lifetime_seconds:
            raise ServiceRuntimeError("invalid_access_request")
        else:
            identifier(self.key_id, "key identity")

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or value.get("record_type") != REQUEST_VERSION:
            raise ServiceRuntimeError("invalid_access_request")
        try:
            return cls(**value)
        except (TypeError, ValueError):
            raise ServiceRuntimeError("invalid_access_request") from None

    def identity(self):
        return digest({"record_type": self.record_type, "operation": self.operation,
            "request_id": self.request_id, "tenant_id": self.tenant_id, "label": self.label,
            "scopes": sorted(self.scopes), "lifetime_seconds": self.lifetime_seconds, "key_id": self.key_id})

    @classmethod
    def from_customer_dict(cls, value, tenant_id):
        """Map one explicit wire contract to a server-owned domain assignment."""
        allowed = {"record_type", "operation", "request_id", "label", "scopes", "lifetime_seconds", "key_id"}
        if (not isinstance(value, dict) or value.get("record_type") != CLIENT_REQUEST_VERSION
                or set(value) - allowed):
            raise ServiceRuntimeError("invalid_access_request")
        return cls.from_dict({**value, "record_type": REQUEST_VERSION, "tenant_id": tenant_id})


class ServiceAccessAdministration:
    """Catalogue-backed access management, used by governed HTTP operations."""

    def __init__(self, runtime: ServiceRuntime, policy: ServiceAccessPolicy | ServiceClientAccessPolicy):
        if not isinstance(runtime, ServiceRuntime) or not isinstance(policy, (ServiceAccessPolicy, ServiceClientAccessPolicy)):
            raise ServiceRuntimeError("invalid_access_policy")
        self.runtime, self.policy = runtime, policy

    @property
    def customer_managed(self):
        return isinstance(self.policy, ServiceClientAccessPolicy)

    def _targets(self, current):
        return (current.tenant_id,) if self.customer_managed else self.policy.target_tenants

    def _customer_authorize(self, store, principal, session):
        current, guards = self.runtime._revalidate(store, principal)
        if (current.authentication_kind != SUBJECT or not isinstance(session, ServiceAccessSession)
                or session.authentication_record_id != current.authentication_record_id):
            raise ServiceRuntimeError("browser_session_required")
        if session.expires_at <= self.runtime._now():
            raise ServiceRuntimeError("unauthorized")
        catalog = self.runtime._catalog
        revoked = catalog.read(store, SESSION_REVOCATION, session.credential_digest)
        if revoked is not None:
            raise ServiceRuntimeError("unauthorized")
        return current, (*guards, catalog.guard(None, catalog.identity(SESSION_REVOCATION, session.credential_digest)))

    def _authorize_context(self, store, principal, session):
        return (self._customer_authorize(store, principal, session) if self.customer_managed
                else self._authorize(store, principal))

    def _authorize(self, store, principal):
        current, guards = self.runtime._revalidate(store, principal)
        if (ACCESS_MANAGE_SCOPE not in current.scopes
                or current.tenant_id not in self.policy.administrator_tenants):
            raise ServiceRuntimeError("access_administration_forbidden")
        return current, guards

    def _rows(self, store, current=None):
        catalog = self.runtime._catalog
        return [row for tenant in self._targets(current) for row in catalog.rows(store, KEY, tenant)
                if self.runtime._payload(row, KEY).get("management_profile") == self.policy.record_type]

    def _owned(self, row, current):
        return not self.customer_managed or row["payload"].get("owner_subject_record_id") == current.authentication_record_id

    def _view(self, row, now):
        value = self.runtime._payload(row, KEY)
        state = ("revoked" if value.get("enabled") is not True else
                 "expired" if value["expires_at"] <= now else "active")
        return {name: value.get(name) for name in ("tenant_id", "key_id", "label", "scopes", "expires_at", "created_at")} | {"state": state}

    def inspect(self, principal, *, session=None):
        with self.runtime._catalog.store() as store:
            current, _ = self._authorize_context(store, principal, session)
            now = self.runtime._now()
            all_rows = self._rows(store, current)
            rows = [self._view(row, now) for row in all_rows if self._owned(row, current)]
            permitted = set(self.policy.allowed_scopes)
            if self.customer_managed:
                permitted.intersection_update(current.scopes, session.allowed_scopes)
        ordered = sorted(rows, key=lambda row: (row["state"] != "active", -(row["created_at"] or 0), row["key_id"]))
        return {"record_type": "service_client_access_options/v1" if self.customer_managed else "service_access_options/v1",
            "target_tenants": list(self._targets(current)), "allowed_scopes": sorted(permitted),
            "writes_authorized": self.policy.writes_authorized,
            "maximum_active_tokens": self.policy.maximum_active_tokens,
            "maximum_lifetime_seconds": self.policy.maximum_lifetime_seconds,
            "default_lifetime_seconds": self.policy.default_lifetime_seconds,
            "maximum_token_records": self.policy.maximum_token_records if self.customer_managed else None,
            "retained_token_records": len(all_rows),
            "active_tokens": sum(self._view(row, now)["state"] == "active" for row in all_rows),
            "tokens": ordered[:1000], "total_records": len(rows), "display_limit": 1000,
            "disclosure": "Tokens share the selected tenant's grants and usage. They do not create isolated tenants."}

    def apply(self, principal, request: ServiceAccessRequest, *, session=None):
        if not isinstance(request, ServiceAccessRequest):
            raise ServiceRuntimeError("invalid_access_request")
        catalog = self.runtime._catalog
        with catalog.store(write=True) as store:
            current, guards = self._authorize_context(store, principal, session)
            if not self.policy.writes_authorized:
                raise ServiceRuntimeError("access_writes_not_authorized")
            if request.tenant_id not in self._targets(current):
                raise ServiceRuntimeError("access_target_forbidden")
            serial_tenant = current.tenant_id if self.customer_managed else self.policy.administrator_tenants[0]
            serial, _data = self.runtime._tenant(store, serial_tenant)
            identity = ((CLIENT_ACCESS_PROFILE, current.authentication_record_id, request.request_id) if self.customer_managed
                        else (current.tenant_id, request.request_id))
            previous = catalog.read(store, OPERATION_KIND, identity)
            if previous is not None:
                if previous["payload"].get("request_digest") != request.identity():
                    raise ServiceRuntimeError("access_request_identity_conflict")
                return {**previous["payload"]["result"], "replayed": True, "token": None}
            now = int(self.runtime._now())
            tenant, tenant_data = self.runtime._tenant(store, request.tenant_id)
            if tenant_data.get("enabled") is not True:
                raise ServiceRuntimeError("tenant_disabled")
            rows = self._rows(store, current)
            raw = None
            if request.operation == "issue":
                if (not set(request.scopes) <= set(self.policy.allowed_scopes)
                        or not set(request.scopes) <= set(scopes(tenant_data.get("scopes")))
                        or (self.customer_managed and not set(request.scopes) <= set(session.allowed_scopes))):
                    raise ServiceRuntimeError("scope_escalation_refused")
                if request.lifetime_seconds > self.policy.maximum_lifetime_seconds:
                    raise ServiceRuntimeError("access_lifetime_exceeded")
                if self.customer_managed and len(rows) >= self.policy.maximum_token_records:
                    raise ServiceRuntimeError("access_token_history_limit_reached")
                if sum(self._view(row, now)["state"] == "active" for row in rows) >= self.policy.maximum_active_tokens:
                    raise ServiceRuntimeError("access_token_limit_reached")
                raw, key_id = "le_" + secrets.token_urlsafe(32), uuid.uuid4().hex
                hashed = hashlib.sha256(raw.encode()).hexdigest()
                changed = catalog.record(KEY, hashed, {"record_type": SCHEMAS[KEY], "key_digest": hashed,
                    "tenant_id": request.tenant_id, "key_id": key_id, "label": request.label,
                    "scopes": list(request.scopes), "created_at": now, "expires_at": now + request.lifetime_seconds,
                    "enabled": True, "management_profile": self.policy.record_type,
                    "issued_by": current.key_id, "administrator_tenant": current.tenant_id}, tenant_id=request.tenant_id)
                if self.customer_managed:
                    # The owner-bound version makes an older server refuse this
                    # key instead of honoring it without the owner rule.
                    changed["payload"].update(record_type=OWNER_BOUND_KEY_SCHEMA,
                                              owner_subject_record_id=current.authentication_record_id)
                    changed["payload"].pop("administrator_tenant")
                    changed["payload"].pop("issued_by")
                mutation_guard = catalog.guard(None, changed["record_id"])
            else:
                selected = [row for row in rows if row["payload"].get("key_id") == request.key_id
                            and row["payload"].get("tenant_id") == request.tenant_id and self._owned(row, current)]
                if len(selected) != 1:
                    raise ServiceRuntimeError("managed_access_token_not_found")
                original = selected[0]
                if self.customer_managed and original["payload"].get("enabled") is not True:
                    raise ServiceRuntimeError("access_token_already_revoked")
                changed = {**original, "record_version": uuid.uuid4().hex,
                           "payload": {**original["payload"], "enabled": False,
                                       "revoked_at": now, "revoked_by": current.key_id}}
                mutation_guard = catalog.guard(original)
            # All administrators serialize against the same owner-installed
            # tenant revision. This binds the global active-token count and
            # deduplication check to the same atomic write as the credential.
            serial_write = {**serial, "record_version": uuid.uuid4().hex}
            result = {"record_type": "service_client_access_result/v1" if self.customer_managed else RESULT_VERSION,
                      "operation": request.operation, "committed": True,
                      "key": self._view(changed, now), "request_id": request.request_id}
            event = catalog.record(OPERATION_KIND, identity, {"record_type": OPERATION_KIND + "/v1",
                "request_digest": request.identity(), "result": result, "actor_key_id": current.key_id,
                "actor_authentication_record_id": current.authentication_record_id,
                "created_at": now}, tenant_id=current.tenant_id)
            all_guards = (*guards, catalog.guard(tenant), catalog.guard(serial), mutation_guard,
                          catalog.guard(None, event["record_id"]))
            unique = {}
            for guard in all_guards:
                if guard.record_id in unique and unique[guard.record_id] != guard:
                    raise ServiceRuntimeError("concurrent_update")
                unique[guard.record_id] = guard
            if self.customer_managed and session.expires_at <= self.runtime._now():
                raise ServiceRuntimeError("unauthorized")
            catalog.commit(store, (changed, serial_write, event), tuple(unique.values()))
        return {**result, "replayed": False, "token": raw}
