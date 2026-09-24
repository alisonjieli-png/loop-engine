"""Tenant-scoped, reviewed harness intelligence disclosure.

Catalogue metadata is not disclosure authority. A host installs exact tenant
grants and a versioned read-only qualification resolver. Unknown or unapproved
items are absent from all responses, including discovery counts. Explicit host
review of a local catalogue is supported but is not independent qualification.

Body reads verify bytes before asking an installed meter for an exact committed
acknowledgment. Unknown commitment never becomes success. The reference meter
is volatile and idempotent within its lifetime. Durable billing and all-layer
admission remain host integrations, not new stores in this module.

Every approval names its library tier, and every list row, manifest and body
carries the tier and its exact label, so a caller always knows which admission
path an item passed. The tiers are the owner's decision of September 24, 2026,
recorded as "Library tiers" in the decision table of AGENTS.md:

```text
Library tier of an approved item   label
├── verified                       Verified    approved by independent reviewers of at
│                                              least two model families that did not
│                                              produce it, every automated check passing
└── community                      Community   every automated check passing and one
                                               independent review by a family that did
                                               not produce it
```

A request states which community items it may be offered. The default offers
none, so a caller that says nothing, or reads a record version without tiers,
receives verified items only. Verified items are listed before community items.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from types import MappingProxyType

from .facets import EFFECTS
from .harness_intelligence import (KINDS, SOURCE_LAYERS, HarnessIntelligenceCatalogue,
                                   HarnessIntelligenceError, HarnessIntelligenceItem,
                                   visibility)
from .service_api import ServiceError, key_digest

SERVER_RECORD_TYPE = "provisioning_server/v2"
#: Version 3 adds the community item choice. Version 2 had no library tier, so a
#: reader of it must not receive a community item it cannot tell apart.
REQUEST_RECORD_TYPE = "provisioning_request/v3"
#: The answers a reader that predates library tiers reads: verified items only,
#: with no tier field. `tierless_answer` produces them from the tiered answers.
DISCOVER_RECORD_TYPE = "provisioning_discover/v2"
LIST_RECORD_TYPE = "provisioning_list/v2"
MANIFEST_RECORD_TYPE = "provisioning_manifest/v2"
BODY_RECORD_TYPE = "provisioning_body/v2"
#: Version 3 of each answer names the library tier of every item it describes.
TIERED_DISCOVER_RECORD_TYPE = "provisioning_discover/v3"
TIERED_LIST_RECORD_TYPE = "provisioning_list/v3"
TIERED_MANIFEST_RECORD_TYPE = "provisioning_manifest/v3"
TIERED_BODY_RECORD_TYPE = "provisioning_body/v3"
REFUSAL_RECORD_TYPE = "provisioning_refusal/v2"
BINDING_RECORD_TYPE = "provisioning_item_binding/v1"
POLICY_RECORD_TYPE = "provisioning_access_policy/v1"
GRANT_RECORD_TYPE = "provisioning_grant/v1"
#: Version 2 adds the library tier of every approval.
QUALIFICATION_RECORD_TYPE = "provisioning_qualification/v2"
RESOLVER_RECORD_TYPE = "provisioning_qualification_resolver/v1"
METER_REQUEST_RECORD_TYPE = "provisioning_meter_request/v1"
METER_ACKNOWLEDGMENT_RECORD_TYPE = "provisioning_meter_acknowledgment/v1"
OPERATIONS = ("discover", "list", "manifest", "read")
ENTITLEMENTS = ("metadata", "bodies")
METERED_UNIT = "provisioned_item"
METERING_POLICIES = ("required", "unmetered")
QUALIFICATION_STATUSES = ("approved", "refused", "unknown")
QUALIFICATION_APPROVED, QUALIFICATION_REFUSED, QUALIFICATION_UNKNOWN = QUALIFICATION_STATUSES
QUALIFICATION_BASES = ("host_attested", "authoritative")
#: The two admission paths an approved item can have passed. See the module text.
LIBRARY_TIERS = ("verified", "community")
VERIFIED_TIER, COMMUNITY_TIER = LIBRARY_TIERS
#: The exact label every surface shows for a tier, and nothing shorter or longer.
TIER_LABELS = {VERIFIED_TIER: "Verified", COMMUNITY_TIER: "Community"}
#: Verified items are listed and ranked before community items.
TIER_ORDER = {VERIFIED_TIER: 0, COMMUNITY_TIER: 1}
#: Which community items a request may be offered. A file a harness may run is
#: an item that declares RUNNABLE_EFFECT, which the release rules require of
#: every package holding a script, a hook or an executable tool.
COMMUNITY_ITEM_CHOICES = ("excluded", "without_runnable_files", "included")
COMMUNITY_EXCLUDED, COMMUNITY_WITHOUT_RUNNABLE, COMMUNITY_INCLUDED = COMMUNITY_ITEM_CHOICES
RUNNABLE_EFFECT = "spawns_process"
METER_DURABILITY = ("volatile", "durable", "unknown")
NEVER_METERED = ("listing authorized items", "a manifest with digests and sizes",
                 "a refusal before metering", "reading the tenant's own usage")


class ProvisioningError(ServiceError):
    """Typed refusal, without revealing an unauthorized item's existence."""

    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def _version(actual: str, expected: str) -> None:
    if actual != expected:
        raise ProvisioningError("unsupported provisioning contract version", "unsupported_version")


def _name(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProvisioningError(f"{label} requires a nonempty string")


def _digest(value: str) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ProvisioningError("an exact lowercase SHA-256 digest is required")


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProvisioningItemBinding:
    """Exact source identity and complete disclosed catalogue descriptor."""

    identity: str
    source_layer: str
    source_ref: str
    body_digest: str
    descriptor_digest: str
    record_type: str = BINDING_RECORD_TYPE

    def __post_init__(self) -> None:
        _version(self.record_type, BINDING_RECORD_TYPE)
        _name(self.identity, "item identity")
        _name(self.source_ref, "source reference")
        if self.source_layer not in SOURCE_LAYERS:
            raise ProvisioningError("unsupported intelligence source layer")
        _digest(self.body_digest)
        _digest(self.descriptor_digest)

    @classmethod
    def from_item(cls, item: HarnessIntelligenceItem) -> "ProvisioningItemBinding":
        if not isinstance(item, HarnessIntelligenceItem):
            raise ProvisioningError("a typed catalogue item is required")
        return cls(item.identity, item.source_layer, item.source_ref,
                   item.digest, _hash(item.reference()))


@dataclass(frozen=True)
class ProvisioningQualification:
    """Exact resolver decision, never approval inferred from catalogue tags.

    Every approval has a library tier. An approval that names none came
    through the independent review panel, the only approval path before the
    community tier existed, so it is `verified`. A community approval always
    names its tier: only a release whose item version records the community
    tier produces one. A decision that is not an approval has no tier.
    """

    binding: ProvisioningItemBinding
    status: str
    basis: str
    approval_ref: str = ""
    library_tier: str = ""
    record_type: str = QUALIFICATION_RECORD_TYPE

    def __post_init__(self) -> None:
        _version(self.record_type, QUALIFICATION_RECORD_TYPE)
        if not isinstance(self.binding, ProvisioningItemBinding):
            raise ProvisioningError("qualification requires an exact item binding")
        if self.status not in QUALIFICATION_STATUSES or self.basis not in QUALIFICATION_BASES:
            raise ProvisioningError("qualification status or basis is unsupported")
        if self.status == QUALIFICATION_APPROVED:
            _name(self.approval_ref, "approval evidence reference")
            if not self.library_tier:
                object.__setattr__(self, "library_tier", VERIFIED_TIER)
            if self.library_tier not in LIBRARY_TIERS:
                raise ProvisioningError("an approval names a known library tier", "library_tier_invalid")
        elif self.library_tier:
            raise ProvisioningError("only an approval has a library tier", "library_tier_invalid")


@dataclass(frozen=True)
class ProvisioningQualificationResolver:
    """Trusted host metadata-only adapter: no body, network, model, or meter effects.

    A Python callback cannot be proved effect-free here. The host must uphold
    this contract and resolve exact source evidence when claiming authoritative
    qualification. Refusal never falls back to host attestation automatically.
    """

    resolver_id: str
    resolve: object = field(repr=False)
    read_only: bool = True
    record_type: str = RESOLVER_RECORD_TYPE

    def __post_init__(self) -> None:
        _version(self.record_type, RESOLVER_RECORD_TYPE)
        _name(self.resolver_id, "qualification resolver identity")
        if not callable(self.resolve) or self.read_only is not True:
            raise ProvisioningError("a read-only qualification resolver is required")


@dataclass(frozen=True)
class ProvisioningGrant:
    """Host permission to disclose one exact item to one tenant."""

    tenant_id: str
    binding: ProvisioningItemBinding
    body_allowed: bool = False
    metering: str = "required"
    record_type: str = GRANT_RECORD_TYPE

    def __post_init__(self) -> None:
        _version(self.record_type, GRANT_RECORD_TYPE)
        _name(self.tenant_id, "tenant identity")
        if not isinstance(self.binding, ProvisioningItemBinding):
            raise ProvisioningError("a grant requires an exact item binding")
        if type(self.body_allowed) is not bool or self.metering not in METERING_POLICIES:
            raise ProvisioningError("a grant requires explicit body and metering policies")


@dataclass(frozen=True)
class ProvisioningAccessPolicy:
    """Immutable host configuration, not a second qualification database."""

    grants: tuple[ProvisioningGrant, ...] = ()
    qualification_resolver: ProvisioningQualificationResolver | None = None
    record_type: str = POLICY_RECORD_TYPE
    _grant_index: object = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _version(self.record_type, POLICY_RECORD_TYPE)
        object.__setattr__(self, "grants", tuple(self.grants))
        if any(not isinstance(grant, ProvisioningGrant) for grant in self.grants):
            raise ProvisioningError("policy grants must be typed")
        keys = [(grant.tenant_id, grant.binding.identity) for grant in self.grants]
        if len(keys) != len(set(keys)):
            raise ProvisioningError("only one exact grant per tenant and item is permitted")
        object.__setattr__(self, "_grant_index", MappingProxyType(dict(zip(keys, self.grants))))
        if (self.qualification_resolver is not None and not isinstance(
                self.qualification_resolver, ProvisioningQualificationResolver)):
            raise ProvisioningError("qualification resolver must be typed")


@dataclass(frozen=True)
class ProvisioningTenant:
    """Host-installed identity, key digest, and maximum subscription tier."""

    tenant_id: str
    key_digest: str = field(repr=False)
    entitlement: str = ENTITLEMENTS[0]

    def __post_init__(self) -> None:
        _name(self.tenant_id, "tenant identity")
        _digest(self.key_digest)
        if self.entitlement not in ENTITLEMENTS:
            raise ProvisioningError("unsupported entitlement")


@dataclass(frozen=True)
class ProvisioningTenantResolver:
    """Host-installed current tenant lookup, never request-provided authority."""

    resolver_id: str
    resolve: object = field(repr=False)
    record_type: str = "provisioning_tenant_resolver/v1"

    def __post_init__(self):
        _version(self.record_type, "provisioning_tenant_resolver/v1")
        _name(self.resolver_id, "tenant resolver identity")
        if not callable(self.resolve):
            raise ProvisioningError("tenant resolver must be callable")


@dataclass(frozen=True)
class ProvisioningRequest:
    """Current request; effects are a filter, never a disclosure grant."""

    operation: str
    key: str = field(repr=False)
    identity: str = ""
    style: str = ""
    authority_effects: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    request_id: str = ""
    #: Which community items this request may be offered; the host sets it from
    #: the account's library setting. The default offers none.
    community_items: str = COMMUNITY_EXCLUDED
    record_type: str = REQUEST_RECORD_TYPE

    def __post_init__(self) -> None:
        _version(self.record_type, REQUEST_RECORD_TYPE)
        if self.operation not in OPERATIONS:
            raise ProvisioningError("unsupported provisioning operation")
        if self.community_items not in COMMUNITY_ITEM_CHOICES:
            raise ProvisioningError(f"community items are one of {COMMUNITY_ITEM_CHOICES}")
        _name(self.key, "caller key")
        for name in ("identity", "style", "request_id"):
            if not isinstance(getattr(self, name), str):
                raise ProvisioningError(f"{name} must be a string")
        for name, allowed in (("authority_effects", EFFECTS), ("kinds", KINDS)):
            values = getattr(self, name)
            if isinstance(values, str):
                raise ProvisioningError(f"{name} requires an explicit sequence")
            values = tuple(values)
            if any(value not in allowed for value in values):
                raise ProvisioningError(f"unsupported {name}")
            object.__setattr__(self, name, values)


@dataclass(frozen=True)
class ProvisioningMeterRequest:
    """One charge identity; the host meter must make retries idempotent."""

    tenant_id: str
    request_id: str
    binding: ProvisioningItemBinding
    unit: str = METERED_UNIT
    quantity: float = 1.0
    record_type: str = METER_REQUEST_RECORD_TYPE

    def __post_init__(self) -> None:
        _version(self.record_type, METER_REQUEST_RECORD_TYPE)
        _name(self.tenant_id, "tenant identity")
        _name(self.request_id, "metering request identity")
        if not isinstance(self.binding, ProvisioningItemBinding):
            raise ProvisioningError("metering requires an exact item binding")
        if self.unit != METERED_UNIT or type(self.quantity) not in (int, float) or self.quantity != 1:
            raise ProvisioningError("one body read meters exactly one provisioned item")


@dataclass(frozen=True)
class ProvisioningMeterAcknowledgment:
    """Only committed=True and an exact acknowledgment establish a charge."""

    request: ProvisioningMeterRequest
    committed: bool | None
    acknowledgment_ref: str = ""
    durability: str = "unknown"
    record_type: str = METER_ACKNOWLEDGMENT_RECORD_TYPE

    def __post_init__(self) -> None:
        _version(self.record_type, METER_ACKNOWLEDGMENT_RECORD_TYPE)
        if not isinstance(self.request, ProvisioningMeterRequest):
            raise ProvisioningError("acknowledgment requires its exact request")
        if self.committed is not None and type(self.committed) is not bool:
            raise ProvisioningError("commitment must be an exact boolean or unknown")
        if self.durability not in METER_DURABILITY:
            raise ProvisioningError("unsupported meter durability")
        if self.committed is True:
            _name(self.acknowledgment_ref, "meter acknowledgment")


@dataclass(frozen=True)
class ProvisioningServer:
    """Four operations, with host-only policy replacement for revocation."""

    catalogue: HarnessIntelligenceCatalogue
    tenants: tuple[ProvisioningTenant, ...] = ()
    body_reader: object = field(default=None, repr=False)
    meter: object = field(default=None, repr=False)
    server_id: str = "loop-engine-provisioning"
    access_policy: ProvisioningAccessPolicy = field(default_factory=ProvisioningAccessPolicy)
    record_type: str = SERVER_RECORD_TYPE
    tenant_resolver: ProvisioningTenantResolver | None = field(default=None, repr=False)
    _lock: object = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _version(self.record_type, SERVER_RECORD_TYPE)
        _name(self.server_id, "server identity")
        if not isinstance(self.catalogue, HarnessIntelligenceCatalogue):
            raise ProvisioningError("a typed catalogue is required")
        object.__setattr__(self, "tenants", tuple(self.tenants))
        if any(not isinstance(tenant, ProvisioningTenant) for tenant in self.tenants):
            raise ProvisioningError("tenants must be typed")
        if (len({tenant.tenant_id for tenant in self.tenants}) != len(self.tenants)
                or len({tenant.key_digest for tenant in self.tenants}) != len(self.tenants)):
            raise ProvisioningError("tenant identities and key digests must be unique")
        self._validate_policy(self.access_policy)
        if self.tenant_resolver is not None and not isinstance(self.tenant_resolver, ProvisioningTenantResolver):
            raise ProvisioningError("tenant resolver must be typed")

    def _validate_policy(self, policy: ProvisioningAccessPolicy) -> None:
        if not isinstance(policy, ProvisioningAccessPolicy):
            raise ProvisioningError("a typed host access policy is required")
        tenants = {tenant.tenant_id for tenant in self.tenants}
        if any(grant.tenant_id not in tenants for grant in policy.grants):
            raise ProvisioningError("a grant names an unconfigured tenant")

    def replace_access_policy(self, policy: ProvisioningAccessPolicy) -> None:
        """Host configuration only. Replacement serializes with active requests."""
        self._validate_policy(policy)
        with self._lock:
            object.__setattr__(self, "access_policy", policy)

    def tenant_for(self, key: str) -> ProvisioningTenant:
        if self.tenant_resolver is not None:
            try:
                tenant = self.tenant_resolver.resolve(key)
            except Exception:
                raise ProvisioningError("authentication failed", "unauthorized") from None
            if not isinstance(tenant, ProvisioningTenant) or not hmac.compare_digest(tenant.key_digest, key_digest(key)):
                raise ProvisioningError("authentication failed", "unauthorized")
            return tenant
        supplied = key_digest(key)
        for tenant in self.tenants:
            if hmac.compare_digest(supplied, tenant.key_digest):
                return tenant
        raise ProvisioningError("authentication failed", "unauthorized")

    def handle(self, request: ProvisioningRequest) -> dict:
        if not isinstance(request, ProvisioningRequest):
            raise ProvisioningError("a typed request is required")
        _version(request.record_type, REQUEST_RECORD_TYPE)
        with self._lock:
            tenant = self.tenant_for(request.key)
            if request.operation == "discover":
                return self._discover(tenant, request)
            if request.operation == "list":
                return self._list(tenant, request)
            if request.operation == "manifest":
                return self._manifest(tenant, request)
            return self._read(tenant, request)

    def _approved(self, tenant: ProvisioningTenant, item: HarnessIntelligenceItem):
        binding = ProvisioningItemBinding.from_item(item)
        policy = self.access_policy
        grant = policy._grant_index.get((tenant.tenant_id, binding.identity))
        resolver = policy.qualification_resolver
        if grant is None or grant.binding != binding or resolver is None:
            return None
        try:
            decision = resolver.resolve(binding)
        except Exception:  # a failed host resolver establishes no authority
            return None
        if (not isinstance(decision, ProvisioningQualification)
                or decision.record_type != QUALIFICATION_RECORD_TYPE
                or decision.binding != binding or decision.status != QUALIFICATION_APPROVED
                or not decision.approval_ref.strip()
                or self.access_policy is not policy
                or self.catalogue.items.get(item.identity) != item
                or ProvisioningItemBinding.from_item(item) != binding):
            return None
        return grant, decision

    def _visible(self, item: HarnessIntelligenceItem, request: ProvisioningRequest) -> str:
        try:
            return visibility(item, style=request.style,
                              authority_effects=request.authority_effects, kinds=request.kinds)
        except HarnessIntelligenceError as exc:
            raise ProvisioningError(str(exc)) from None

    def _offered(self, tenant: ProvisioningTenant, request: ProvisioningRequest):
        offered, withheld = [], []
        for item in tuple(self.catalogue.items.values()):
            approval = self._approved(tenant, item)
            if approval is None:
                continue
            grant, decision = approval
            if not in_library(item, decision, request.community_items):
                # The account chose not to receive this item. It is not held
                # back for a reason the caller could act on in this request,
                # so it is left out silently, like an item of another kind.
                continue
            reason = self._visible(item, request)
            if reason:
                withheld.append({"identity": item.identity, "reason": reason})
            else:
                offered.append({**item.reference(), "qualification_basis": decision.basis,
                                **tier_fields(decision),
                                "metering_policy": grant.metering,
                                "body_allowed": grant.body_allowed
                                and tenant.entitlement == ENTITLEMENTS[1]})
        offered.sort(key=lambda row: (TIER_ORDER[row["library_tier"]], row["identity"]))
        withheld.sort(key=lambda row: row["identity"])
        return offered, withheld

    def _discover(self, tenant: ProvisioningTenant, request: ProvisioningRequest) -> dict:
        offered, _ = self._offered(tenant, request)
        return {"record_type": TIERED_DISCOVER_RECORD_TYPE, "server_id": self.server_id,
                "operations": list(OPERATIONS),
                "kinds": [kind for kind in KINDS if any(item["kind"] == kind for item in offered)],
                "tenant_id": tenant.tenant_id, "entitlement": tenant.entitlement,
                "items_held": len(offered),
                "items_by_library_tier": {tier: sum(1 for item in offered if item["library_tier"] == tier)
                                          for tier in LIBRARY_TIERS},
                "community_items": request.community_items, "metered_unit": METERED_UNIT,
                "metered": False, "never_metered": list(NEVER_METERED),
                "bodies_available": callable(self.body_reader) and any(
                    item["body_allowed"] and (item["metering_policy"] == "unmetered"
                                              or callable(self.meter)) for item in offered)}

    def _list(self, tenant: ProvisioningTenant, request: ProvisioningRequest) -> dict:
        offered, withheld = self._offered(tenant, request)
        return {"record_type": TIERED_LIST_RECORD_TYPE, "tenant_id": tenant.tenant_id,
                "entitlement": tenant.entitlement, "items": offered,
                "withheld": withheld, "community_items": request.community_items, "metered": False}

    def _item(self, tenant: ProvisioningTenant, request: ProvisioningRequest):
        item = self.catalogue.items.get(request.identity)
        approval = self._approved(tenant, item) if item is not None else None
        if approval is None:
            raise ProvisioningError("item is unavailable to this tenant", "item_unavailable")
        if not in_library(item, approval[1], request.community_items):
            raise ProvisioningError("item is a community item this account's library setting leaves out",
                                    "item_outside_library_setting")
        reason = self._visible(item, request)
        if reason:
            raise ProvisioningError(f"item is withheld: {reason}", "item_withheld")
        return item, *approval

    def _manifest(self, tenant: ProvisioningTenant, request: ProvisioningRequest) -> dict:
        item, grant, decision = self._item(tenant, request)
        return {"record_type": TIERED_MANIFEST_RECORD_TYPE, "tenant_id": tenant.tenant_id,
                **{key: value for key, value in item.reference().items() if key != "record_type"},
                "qualification_basis": decision.basis, **tier_fields(decision),
                "metering_policy": grant.metering,
                "body_allowed": grant.body_allowed and tenant.entitlement == ENTITLEMENTS[1],
                "verify_before_use": True, "metered": False}

    def _recheck(self, tenant, request, binding, grant, decision) -> None:
        if self.tenant_for(request.key) != tenant:
            raise ProvisioningError("tenant authority changed", "unauthorized")
        current, current_grant, current_decision = self._item(tenant, request)
        if (ProvisioningItemBinding.from_item(current) != binding
                or current_grant != grant or current_decision != decision):
            raise ProvisioningError("disclosure authority changed", "item_unavailable")

    def _read(self, tenant: ProvisioningTenant, request: ProvisioningRequest) -> dict:
        item, grant, decision = self._item(tenant, request)
        if tenant.entitlement != ENTITLEMENTS[1] or grant.body_allowed is not True:
            raise ProvisioningError("body disclosure is not authorized", "body_forbidden")
        if not callable(self.body_reader):
            raise ProvisioningError("body reader is unavailable", "body_reader_unavailable")
        binding = ProvisioningItemBinding.from_item(item)
        meter_request = None
        if grant.metering == "required":
            if not callable(self.meter):
                raise ProvisioningError("required meter is unavailable", "meter_unavailable")
            meter_request = ProvisioningMeterRequest(tenant.tenant_id, request.request_id, binding)
        try:
            body = self.body_reader(item)
        except Exception:
            raise ProvisioningError("body reader failed", "body_reader_unavailable") from None
        if not isinstance(body, str):
            raise ProvisioningError("body reader did not return text", "body_integrity_failed")
        encoded = body.encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != item.digest or len(encoded) != item.size_bytes:
            raise ProvisioningError("body does not match the exact item", "body_integrity_failed")
        self._recheck(tenant, request, binding, grant, decision)
        acknowledgment = None
        if meter_request is not None:
            try:
                acknowledgment = self.meter(meter_request)
            except Exception:
                raise ProvisioningError("meter commitment is unknown; retry the same request identity",
                                        "meter_commit_unknown") from None
            if (not isinstance(acknowledgment, ProvisioningMeterAcknowledgment)
                    or acknowledgment.record_type != METER_ACKNOWLEDGMENT_RECORD_TYPE
                    or acknowledgment.request != meter_request
                    or acknowledgment.committed is not True
                    or not acknowledgment.acknowledgment_ref.strip()):
                raise ProvisioningError(
                    "meter commitment is not established; retry the same request identity",
                    "meter_commit_unknown")
            self._recheck(tenant, request, binding, grant, decision)
        return {"record_type": TIERED_BODY_RECORD_TYPE, "tenant_id": tenant.tenant_id,
                "identity": item.identity, "digest": item.digest,
                "size_bytes": item.size_bytes, "body": body,
                "qualification_basis": decision.basis, **tier_fields(decision),
                "metered": acknowledgment is not None,
                "metered_unit": METERED_UNIT if acknowledgment is not None else None,
                "metering_acknowledgment": asdict(acknowledgment) if acknowledgment else None}


#: Each tiered answer and the version 2 answer a reader that predates trust
#: tiers reads instead. Version 2 carried no tier, so it describes verified
#: items only.
TIERLESS_RECORD_TYPES = {TIERED_DISCOVER_RECORD_TYPE: DISCOVER_RECORD_TYPE, TIERED_LIST_RECORD_TYPE: LIST_RECORD_TYPE,
                         TIERED_MANIFEST_RECORD_TYPE: MANIFEST_RECORD_TYPE, TIERED_BODY_RECORD_TYPE: BODY_RECORD_TYPE}
_TIER_FIELDS = ("library_tier", "library_tier_label", "items_by_library_tier", "community_items")


def tierless_answer(result: dict) -> dict:
    """The version 2 shape of one answer, for a reader that cannot tell a community item from a verified one.

    It refuses rather than drop a label: an answer that names a community item,
    or was produced for a request that could receive one, has no version 2
    shape. A caller that negotiated version 2 therefore asks with the default
    community choice, which offers none.
    """
    record_type = result.get("record_type") if isinstance(result, dict) else None
    if record_type not in TIERLESS_RECORD_TYPES:
        raise ProvisioningError("this answer has no version 2 shape", "unsupported_version")
    rows = result.get("items", ()) if record_type == TIERED_LIST_RECORD_TYPE else (result,)
    if (result.get("community_items", COMMUNITY_EXCLUDED) != COMMUNITY_EXCLUDED
            or any(row.get("library_tier", VERIFIED_TIER) != VERIFIED_TIER for row in rows)
            or any(count for tier, count in result.get("items_by_library_tier", {}).items() if tier != VERIFIED_TIER)):
        raise ProvisioningError("a version 2 reader cannot receive a community item", "tier_required_by_answer")
    answer = {key: value for key, value in result.items() if key not in _TIER_FIELDS}
    if record_type == TIERED_LIST_RECORD_TYPE:
        answer["items"] = [{key: value for key, value in row.items() if key not in _TIER_FIELDS}
                           for row in result["items"]]
    answer["record_type"] = TIERLESS_RECORD_TYPES[record_type]
    return answer


def tier_fields(decision: ProvisioningQualification) -> dict:
    """The typed library tier of one approval and its exact label, as every answer carries them."""
    return {"library_tier": decision.library_tier, "library_tier_label": TIER_LABELS[decision.library_tier]}


def in_library(item: HarnessIntelligenceItem, decision: ProvisioningQualification, community_items: str) -> bool:
    """Whether an approved item belongs to what a request with this community choice may be offered.

    A verified item always does. A community item does only when the choice
    includes it: `without_runnable_files` leaves out every community item that
    declares RUNNABLE_EFFECT, and `excluded` leaves out every community item.
    """
    if decision.library_tier == VERIFIED_TIER:
        return True
    if decision.library_tier != COMMUNITY_TIER or community_items not in COMMUNITY_ITEM_CHOICES:
        return False
    if community_items == COMMUNITY_INCLUDED:
        return True
    return community_items == COMMUNITY_WITHOUT_RUNNABLE and RUNNABLE_EFFECT not in item.declared_effects


@dataclass
class RecordedMeter:
    """Volatile meter; exact retries reuse an acknowledgment without charging twice."""

    _rows: list = field(default_factory=list, init=False, repr=False)
    _acknowledgments: dict = field(default_factory=dict, init=False, repr=False)
    _lock: object = field(default_factory=threading.RLock, init=False, repr=False)

    @property
    def rows(self) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self._rows]

    def __call__(self, request: ProvisioningMeterRequest) -> ProvisioningMeterAcknowledgment:
        if not isinstance(request, ProvisioningMeterRequest):
            raise ProvisioningError("meter requires a typed request")
        with self._lock:
            identity = (request.tenant_id, request.request_id)
            existing = self._acknowledgments.get(identity)
            if existing is not None:
                if existing.request != request:
                    raise ProvisioningError("meter request identity was reused for another effect",
                                            "meter_request_conflict")
                return existing
            acknowledgment = ProvisioningMeterAcknowledgment(
                request, True, "volatile:" + _hash(asdict(request)), "volatile")
            self._rows.append({"tenant_id": request.tenant_id, "unit": request.unit,
                               "quantity": request.quantity, "request_id": request.request_id,
                               "record_ref": request.binding.identity,
                               "body_digest": request.binding.body_digest,
                               "acknowledgment_ref": acknowledgment.acknowledgment_ref, "at": time.time()})
            self._acknowledgments[identity] = acknowledgment
            return acknowledgment

    def total(self, tenant_id: str) -> float:
        with self._lock:
            return sum(row["quantity"] for row in self._rows if row["tenant_id"] == tenant_id)


def self_test() -> dict:
    """Collected public-path checks remain owned by this component."""
    from .provisioning_server_checks import self_test as run
    return run()
