"""Immutable host configuration and public service-domain records.

These records describe tenant state and explicitly authorized host writes.
They neither create another intelligence layer nor grant caller-selected
network, billing, or catalogue-disclosure authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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

    def __post_init__(self):
        if self.record_type != SUBJECT_TENANT_REGISTRATION_VERSION:
            raise ServiceRuntimeError("unsupported_version")
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
