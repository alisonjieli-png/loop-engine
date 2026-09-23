"""Immutable host configuration and public service-domain records.

These records describe tenant state and explicitly authorized host writes.
They neither create another intelligence layer nor grant caller-selected
network, billing, or catalogue-disclosure authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re

CONFIG_VERSION = "service_runtime_config/v1"
DEFAULT_SCOPES = ("provisioning:metadata", "provisioning:read", "usage:read")
BILLING_MANAGE_SCOPE = "billing:manage"
ACCESS_MANAGE_SCOPE = "access:manage"
CLIENT_ACCESS_PROFILE = "service_client_access/v1"
SCOPES = (*DEFAULT_SCOPES, BILLING_MANAGE_SCOPE, ACCESS_MANAGE_SCOPE)
ENTITLEMENTS = ("metadata", "bodies")
SERVICE_COLLECTION = "hosted_service_state"
SUBJECT_TENANT_REGISTRATION_VERSION = "service_subject_tenant_registration/v1"
BILLING_CUSTOMER_EFFECT_SPEC_VERSION = "billing_customer_effect_spec/v1"
BILLING_CUSTOMER_OUTCOME_VERSION = "billing_customer_effect_outcome/v1"
BILLING_CUSTOMER_ACCOUNT_RELEASE_VERSION = "billing_customer_account_release/v1"
# One status vocabulary for every externally consequential billing effect.
# `billing_effects.py` owns the checkout and portal effect and declares the
# same four words; a check in `runtime_checks.py` fails when they drift apart.
EFFECT_PENDING, EFFECT_CONFIRMED, EFFECT_UNKNOWN, EFFECT_NOT_ATTEMPTED = (
    "pending", "confirmed", "unknown", "not_attempted")
# The provider documents a minimum 24-hour idempotency-key retention period.
# `billing_effects.py` declares the same observed provider fact, and a check
# fails when the two declarations differ.
PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS = 24 * 3600
# How stale this service is willing to assume a provider customer search may
# be. The provider search is eventually consistent, and this repository holds
# no measured bound for it, so this number is a declared host allowance and not
# a provider guarantee. It is used in one place: a new provider idempotency
# cycle may begin only once this much time has passed since the last moment the
# previous attempt could have reached the provider. That way a customer the
# previous attempt created is visible to the search before the search is
# trusted to say that the account has none. Raise it if a provider report shows
# a longer lag; never lower it to make a window fit.
PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS = 60


class ServiceRuntimeError(ValueError):
    """A stable domain refusal; exception text never includes a credential."""

    def __init__(self, code: str, message: str = "service operation refused"):
        super().__init__(message)
        self.code = code


class ServiceCommitUnknown(ServiceRuntimeError):
    def __init__(self):
        super().__init__("commit_unknown", "commit acknowledgment is unavailable; reconcile the same identity")


def text(value, label):
    if not isinstance(value, str) or not value.strip() or any(ord(ch) < 32 for ch in value):
        raise ServiceRuntimeError("invalid_request", f"{label} must be nonempty text without controls")
    return value


def identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise ServiceRuntimeError("invalid_request", f"{label} is not a supported identity")
    return value


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ServiceRuntimeError("invalid_record", "finite JSON data is required") from exc


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def scopes(values):
    if not isinstance(values, (list, tuple)) or any(value not in SCOPES for value in values):
        raise ServiceRuntimeError("invalid_request", "scopes must use the declared service vocabulary")
    if len(set(values)) != len(values):
        raise ServiceRuntimeError("invalid_request", "scopes must be distinct")
    return tuple(values)


@dataclass(frozen=True)
class ServiceRuntimeConfig:
    database_path: str
    namespace: str = "hosted-service"
    writes_authorized: bool = False
    record_type: str = CONFIG_VERSION

    def __post_init__(self):
        if self.record_type != CONFIG_VERSION:
            raise ServiceRuntimeError("unsupported_version")
        text(self.database_path, "database path")
        path = Path(self.database_path)
        if not path.is_absolute() or path.resolve() != path or path.is_symlink():
            raise ServiceRuntimeError("invalid_configuration", "database path must be absolute and free of symbolic links")
        identifier(self.namespace, "service namespace")
        if type(self.writes_authorized) is not bool:
            raise ServiceRuntimeError("invalid_configuration", "host write authority must be explicit")


@dataclass(frozen=True)
class TenantRegistration:
    tenant_id: str
    namespace: str
    scopes: tuple[str, ...] = DEFAULT_SCOPES

    def __post_init__(self):
        identifier(self.tenant_id, "tenant identity")
        identifier(self.namespace, "tenant namespace")
        object.__setattr__(self, "scopes", scopes(self.scopes))


@dataclass(frozen=True)
class TenantKeyIssue:
    tenant_id: str
    label: str
    expires_at: int | None = None
    scopes: tuple[str, ...] | None = None

    def __post_init__(self):
        identifier(self.tenant_id, "tenant identity")
        text(self.label, "key label")
        if self.expires_at is not None and (type(self.expires_at) is not int or self.expires_at <= 0):
            raise ServiceRuntimeError("invalid_request", "key expiry must be an epoch second")
        if self.scopes is not None:
            object.__setattr__(self, "scopes", scopes(self.scopes))


@dataclass(frozen=True)
class IssuedServiceKey:
    tenant_id: str
    key_id: str
    key: str = field(repr=False)
    expires_at: int | None = None


@dataclass(frozen=True)
class SubjectBindingRequest:
    tenant_id: str
    issuer: str
    subject: str

    def __post_init__(self):
        identifier(self.tenant_id, "tenant identity")
        text(self.issuer, "issuer")
        text(self.subject, "subject")


@dataclass(frozen=True)
class SubjectTenantRegistration:
    """Host-authorized first account for an already verified issuer and subject.

    The transport must verify identity before constructing this record. Caller
    JSON cannot choose a tenant, namespace, administrative scope or entitlement.
    """

    issuer: str
    subject: str
    namespace_prefix: str
    scopes: tuple[str, ...] = DEFAULT_SCOPES
    starter_bindings: tuple = ()
    record_type: str = SUBJECT_TENANT_REGISTRATION_VERSION
    #: A new account follows the active catalogue release instead of copying
    #: starter bindings once. The two are alternatives, so naming both refuses.
    follows_active_release: bool = False

    def __post_init__(self):
        if self.record_type != SUBJECT_TENANT_REGISTRATION_VERSION:
            raise ServiceRuntimeError("unsupported_version")
        if type(self.follows_active_release) is not bool or (self.follows_active_release and self.starter_bindings):
            raise ServiceRuntimeError("invalid_starter_bindings")
        text(self.issuer, "issuer"); text(self.subject, "subject")
        identifier(self.namespace_prefix, "namespace prefix")
        if len(self.issuer) > 2048 or len(self.subject) > 512 or len(self.namespace_prefix) > 32:
            raise ServiceRuntimeError("invalid_account_identity")
        selected = scopes(self.scopes)
        if ACCESS_MANAGE_SCOPE in selected:
            raise ServiceRuntimeError("automatic_administration_forbidden")
        from ..provisioning_server import ProvisioningItemBinding
        bindings = tuple(self.starter_bindings)
        if (len(bindings) > 128 or any(not isinstance(item, ProvisioningItemBinding) for item in bindings)
                or len({item.identity for item in bindings}) != len(bindings)):
            raise ServiceRuntimeError("invalid_starter_bindings")
        object.__setattr__(self, "scopes", selected)
        object.__setattr__(self, "starter_bindings", bindings)

    @property
    def tenant_id(self):
        return self.namespace_prefix + "." + digest([self.issuer, self.subject])

    @property
    def namespace(self):
        return self.namespace_prefix + ":" + digest([self.issuer, self.subject])


@dataclass(frozen=True)
class BillingCustomerBindingRequest:
    tenant_id: str
    provider_customer_id: str
    provider_account_id: str

    def __post_init__(self):
        identifier(self.tenant_id, "tenant identity")
        identifier(self.provider_customer_id, "billing customer identity")
        identifier(self.provider_account_id, "billing account identity")


@dataclass(frozen=True)
class BillingCustomerEffectSpec:
    """The exact provider customer creation that one account may ever ask for.

    The account has one such effect for its whole lifetime, so the durable
    identity of the effect is the account itself. The spec carries no personal
    detail because the service holds none.
    """

    tenant_id: str
    provider_account_id: str
    metadata_key: str
    record_type: str = BILLING_CUSTOMER_EFFECT_SPEC_VERSION

    def __post_init__(self):
        if self.record_type != BILLING_CUSTOMER_EFFECT_SPEC_VERSION:
            raise ServiceRuntimeError("unsupported_billing_customer_effect")
        identifier(self.tenant_id, "tenant identity")
        identifier(self.provider_account_id, "billing account identity")
        identifier(self.metadata_key, "provider metadata key")

    @property
    def digest(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class BillingCustomerAccountRelease:
    """Host authority to free one account from a provider account it has left.

    A customer created at one provider account does not exist at another, so an
    account whose service now points at a different provider account needs a
    new customer there. This record names the exact account, the provider
    account being released and the provider account the service uses now, so a
    release can never be read as permission to unbind a current provider
    account. It is host input, never caller input: no request body can build it.
    """

    tenant_id: str
    released_provider_account_id: str
    current_provider_account_id: str
    record_type: str = BILLING_CUSTOMER_ACCOUNT_RELEASE_VERSION

    def __post_init__(self):
        if self.record_type != BILLING_CUSTOMER_ACCOUNT_RELEASE_VERSION:
            raise ServiceRuntimeError("unsupported_billing_customer_release")
        identifier(self.tenant_id, "tenant identity")
        identifier(self.released_provider_account_id, "released billing account identity")
        identifier(self.current_provider_account_id, "current billing account identity")
        if self.released_provider_account_id == self.current_provider_account_id:
            raise ServiceRuntimeError("billing_customer_release_needs_another_account")


def billing_customer_request_differs_only_by_provider_account(stored, requested):
    """True when the stored request identity differs only by provider account.

    The configured provider account may change, for example when the
    service moves from the test account to the live one. Nothing else may
    differ: a different metadata key would send the search before creation
    to look for the wrong field, so that stays a request identity conflict.
    `ServiceRuntime.begin_billing_customer` reads this rule.
    """
    return (isinstance(stored, dict) and bool(stored.get("provider_account_id"))
            and {**stored, "provider_account_id": requested["provider_account_id"]} == requested)


def billing_customer_search_can_show_the_previous_attempt(state, now):
    """True when a provider search would already show the previous attempt.

    A new idempotency cycle abandons the stored provider key, so from then
    on the metadata search before creation is the only thing that keeps the
    account at one customer. The previous attempt could not have reached
    the provider later than its own recorded dispatch deadline, because
    `authorize_billing_customer_dispatch` refuses at that moment. The
    search is trusted only once the declared freshness allowance has passed
    since that deadline, so a customer the previous attempt created is
    visible before the search is read as saying there is none.

    The deadline is read from the record of the attempt that set it. It is
    never rebuilt from the lease of whichever caller comes next: a host that
    lowers its request timeout lowers that lease, and a rebuilt deadline
    would then land earlier than the one the previous attempt really had,
    which would start a new cycle while the search can still be blind to
    what that attempt created. `ServiceRuntime.begin_billing_customer` reads
    this rule with the `service_billing_customer_effect` record as `state`.
    """
    if not state.get("attempts"):
        return True
    # A record whose deadline is missing or beyond its own window is
    # treated as though its attempt ran to the end of that window. That is
    # the longer wait, and it is never earlier than the real deadline.
    deadline, window = state.get("dispatch_deadline"), state["retry_before"]
    if type(deadline) not in (int, float) or not deadline <= window:
        deadline = window
    return now >= deadline + PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS


@dataclass(frozen=True)
class BillingCustomerReservation:
    """Issued by the runtime for one reserved creation attempt, never from HTTP.

    The reservation carries the durable idempotency identity of the attempt and
    the read-set guards that were current when it was reserved. The runtime
    checks both again before the provider call and again before the binding.
    """

    spec: BillingCustomerEffectSpec
    record_id: str
    attempt_id: str
    idempotency_key: str = field(repr=False)
    retry_before: int
    attempt_number: int
    idempotency_cycles: int
    authority_guards: tuple = field(repr=False)
    _issuer: object = field(repr=False, compare=False)
    _proof: str = field(default="", repr=False, compare=False)


@dataclass(frozen=True)
class ServicePrincipal:
    """Issued in-process principal; never reconstructed from request JSON."""

    tenant_id: str
    namespace: str
    key_id: str
    entitlement: str
    scopes: tuple[str, ...]
    authentication_record_id: str = field(repr=False)
    authentication_kind: str = field(repr=False)
    _issuer: object = field(repr=False, compare=False)
    _proof: str = field(default="", repr=False, compare=False)

    def to_dict(self):
        return {"record_type": "service_principal/v1", "tenant_id": self.tenant_id,
                "namespace": self.namespace, "key_id": self.key_id,
                "entitlement": self.entitlement, "scopes": list(self.scopes)}
