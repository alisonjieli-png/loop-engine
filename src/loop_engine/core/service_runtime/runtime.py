"""Persistent tenant, authentication, disclosure, and usage domain.

The existing catalogue is the only service-state authority. Every mutation
uses a negotiated atomic read-set batch. Principals are issued locally and
revalidated; neither a checkout redirect nor a caller-provided tenant string
establishes subscription or disclosure authority.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import hmac
import math
import secrets
import time
import uuid

from ..provisioning_server import (
    ProvisioningGrant, ProvisioningItemBinding, ProvisioningMeterAcknowledgment,
    ProvisioningMeterRequest,
)
from .records import (
    BILLING_CUSTOMER_ACCOUNT_RELEASE_VERSION,
    BILLING_CUSTOMER_OUTCOME_VERSION, BILLING_MANAGE_SCOPE, CLIENT_ACCESS_PROFILE, BillingCustomerAccountRelease,
    BillingCustomerBindingRequest,
    BillingCustomerEffectSpec, BillingCustomerReservation, EFFECT_CONFIRMED, EFFECT_NOT_ATTEMPTED, EFFECT_PENDING,
    EFFECT_UNKNOWN, ENTITLEMENTS, IssuedServiceKey, PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS,
    PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS,
    ServiceCommitUnknown, ServicePrincipal, ServiceRuntimeConfig, ServiceRuntimeError,
    SubjectBindingRequest, SubjectTenantRegistration, TenantKeyIssue, TenantRegistration,
    billing_customer_request_differs_only_by_provider_account, billing_customer_search_can_show_the_previous_attempt,
    canonical, digest, identifier, scopes,
)
from .storage import ServiceCatalogBinding
from .catalogue_grants import release_following_grants, release_following_payload as _follows

(TENANT, KEY, SUBJECT, ENTITLEMENT, GRANTS, USAGE, CUSTOMER, CUSTOMER_EFFECT, TENANT_NAMESPACE, BILLING_POLICY,
 SESSION_REVOCATION, PROMOTION_CODE, PROMOTION_REDEMPTION, PROMOTION_ACCOUNT) = (
    "service_tenant", "service_key", "service_subject", "service_entitlement",
    "service_grants", "service_usage", "service_billing_customer", "service_billing_customer_effect",
    "service_tenant_namespace", "service_billing_policy", "service_browser_session_revocation",
    "service_promotion_code", "service_promotion_redemption", "service_promotion_code_account")
SCHEMAS = {kind: kind + "/v1" for kind in (TENANT, KEY, SUBJECT, ENTITLEMENT, GRANTS, USAGE, CUSTOMER,
                                           CUSTOMER_EFFECT, TENANT_NAMESPACE, BILLING_POLICY, SESSION_REVOCATION,
                                           PROMOTION_CODE, PROMOTION_REDEMPTION, PROMOTION_ACCOUNT)}
CUSTOMER_IDEMPOTENCY_PREFIX = "le-customer-"
# A customer-issued key is valid only while its owning sign-in stays enabled.
# It has its own record version, so a server that predates the owner rule
# refuses the record instead of honoring it without that rule after a rollback.
OWNER_BOUND_KEY_SCHEMA = KEY + "/v2"
KEY_SCHEMAS = (SCHEMAS[KEY], OWNER_BOUND_KEY_SCHEMA)
# The creation record carries the exact moment past which its own attempt could
# no longer have reached the provider. A release that predates that field
# rebuilds the moment from the lease of whichever caller comes next, and that
# lease can be shorter than the one the attempt really held. Such a release must
# refuse this record rather than read it, so the field arrives with its own
# record version.
DISPATCH_DEADLINE_CUSTOMER_EFFECT_SCHEMA = CUSTOMER_EFFECT + "/v2"
CUSTOMER_EFFECT_SCHEMAS = (DISPATCH_DEADLINE_CUSTOMER_EFFECT_SCHEMA,)
METADATA, BODIES = ENTITLEMENTS
HOST_GRANT_SOURCE = "explicit_host_grant"
STRIPE_SNAPSHOT_SOURCE = "stripe_snapshot"
#: Access that one person gave themselves by redeeming a promotion code. It is
#: written by `promotions.py` through the same entitlement record as a host
#: grant, and it is never evidence of a payment. A release that predates this
#: source reads an unknown source as metadata only, so an older server refuses
#: the access instead of honoring a record whose rules it does not know.
CODE_GRANT_SOURCE = "promotion_code_grant"
#: Money comes from one source only. Everything else is comped access. A usage
#: or billing report reads these two tuples instead of guessing from a record.
REVENUE_BEARING_SOURCES = (STRIPE_SNAPSHOT_SOURCE,)
COMPED_SOURCES = (HOST_GRANT_SOURCE, CODE_GRANT_SOURCE)
ENTITLEMENT_SOURCES = (*REVENUE_BEARING_SOURCES, *COMPED_SOURCES)
ACCESS_SOURCE_REPORT_VERSION = "service_access_source_report/v1"
PROVISIONING_METADATA_SCOPE, PROVISIONING_READ_SCOPE, USAGE_READ_SCOPE = (
    "provisioning:metadata", "provisioning:read", "usage:read")


class ServiceRuntime:
    """Host-owned runtime facade; each operation opens its own catalogue connection."""

    def __init__(self, config: ServiceRuntimeConfig, *, storage=None, clock=time.time):
        if not isinstance(config, ServiceRuntimeConfig) or not callable(clock):
            raise ServiceRuntimeError("invalid_configuration")
        if storage is not None and (not isinstance(storage, ServiceCatalogBinding) or storage.config != config):
            raise ServiceRuntimeError("invalid_configuration", "storage must match the exact host configuration")
        self.config = config
        self._catalog = storage if storage is not None else ServiceCatalogBinding(config)
        self._clock = clock
        self._issuer = object()
        self._principal_secret = secrets.token_bytes(32)
        self._effect_issuer = object()
        self._effect_secret = secrets.token_bytes(32)

    def _now(self):
        value = self._clock()
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ServiceRuntimeError("clock_unavailable")
        return value

    def _principal_proof(self, principal):
        value = {**principal.to_dict(), "authentication_record_id": principal.authentication_record_id,
                 "authentication_kind": principal.authentication_kind}
        return hmac.new(self._principal_secret, digest(value).encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _payload(row, kind):
        if row is None:
            raise ServiceRuntimeError("not_found")
        payload = row.get("payload")
        supported = (KEY_SCHEMAS if kind == KEY else
                     CUSTOMER_EFFECT_SCHEMAS if kind == CUSTOMER_EFFECT else
                     (SCHEMAS[kind], "service_grants/v2") if kind == GRANTS else (SCHEMAS[kind],))
        if not isinstance(payload, dict) or payload.get("record_type") not in supported:
            raise ServiceRuntimeError("unsupported_or_corrupt_record")
        return payload

    def _tenant(self, store, tenant_id):
        row = self._catalog.read(store, TENANT, tenant_id)
        value = self._payload(row, TENANT)
        if value.get("tenant_id") != tenant_id:
            raise ServiceRuntimeError("record_identity_mismatch")
        return row, value

    def _entitlement(self, row, policy=None):
        if row is None:
            return METADATA
        value = self._payload(row, ENTITLEMENT)
        if value.get("source") == STRIPE_SNAPSHOT_SOURCE:
            configured = self._payload(policy, BILLING_POLICY) if policy is not None else {}
            if not configured.get("policy_digest") or configured["policy_digest"] != value.get("policy_digest"):
                return METADATA
        elif value.get("source") not in COMPED_SOURCES:
            return METADATA
        until = value.get("valid_until")
        if (value.get("enabled") is True and value.get("entitlement") == BODIES
                and type(until) is int and until > self._now()):
            return BODIES
        return METADATA

    def register_tenant(self, request: TenantRegistration):
        if not isinstance(request, TenantRegistration):
            raise ServiceRuntimeError("invalid_request")
        with self._catalog.store(write=True) as store:
            identity = self._catalog.identity(TENANT, request.tenant_id)
            row = self._catalog.record(TENANT, request.tenant_id, {
                "record_type": SCHEMAS[TENANT], "tenant_id": request.tenant_id,
                "namespace": request.namespace, "scopes": list(request.scopes), "enabled": True,
                "body_access_revoked": False,
            }, tenant_id=request.tenant_id)
            namespace = self._catalog.record(TENANT_NAMESPACE, request.namespace,
                {"record_type": SCHEMAS[TENANT_NAMESPACE], "tenant_id": request.tenant_id}, tenant_id=request.tenant_id)
            self._catalog.commit(store, (row, namespace), (self._catalog.guard(None, identity),
                self._catalog.guard(None, namespace["record_id"])))
        return {"record_type": "service_tenant_registration/v1", "tenant_id": request.tenant_id,
                "namespace": request.namespace, "committed": True}

    def issue_key(self, request: TenantKeyIssue) -> IssuedServiceKey:
        if not isinstance(request, TenantKeyIssue):
            raise ServiceRuntimeError("invalid_request")
        if request.expires_at is not None and request.expires_at <= self._now():
            raise ServiceRuntimeError("invalid_expiry")
        raw = "le_" + secrets.token_urlsafe(32)
        hashed, key_id = hashlib.sha256(raw.encode()).hexdigest(), uuid.uuid4().hex
        with self._catalog.store(write=True) as store:
            tenant, data = self._tenant(store, request.tenant_id)
            if data.get("enabled") is not True:
                raise ServiceRuntimeError("tenant_disabled")
            permitted = scopes(data.get("scopes"))
            chosen = permitted if request.scopes is None else request.scopes
            if not set(chosen) <= set(permitted):
                raise ServiceRuntimeError("scope_escalation_refused")
            row = self._catalog.record(KEY, hashed, {"record_type": SCHEMAS[KEY],
                "tenant_id": request.tenant_id, "key_id": key_id, "key_digest": hashed,
                "label": request.label, "expires_at": request.expires_at, "scopes": list(chosen),
                "enabled": True}, tenant_id=request.tenant_id)
            self._catalog.commit(store, (row,), (self._catalog.guard(tenant),
                self._catalog.guard(None, row["record_id"])))
        return IssuedServiceKey(request.tenant_id, key_id, raw, request.expires_at)

    def ensure_subject_tenant(self, request: SubjectTenantRegistration):
        """Atomically create or reconcile a verified subject's first account.

        Existing bindings win. Repeat activation never changes permissions,
        restores a revoked account or restores removed catalogue grants.
        No subscription or body entitlement is created by account activation.
        """
        if not isinstance(request, SubjectTenantRegistration):
            raise ServiceRuntimeError("invalid_request")
        with self._catalog.store(write=True) as store:
            previous = self._catalog.read(store, SUBJECT, (request.issuer, request.subject))
            if previous is not None:
                value = self._payload(previous, SUBJECT)
                if value.get("issuer") != request.issuer or value.get("subject") != request.subject:
                    raise ServiceRuntimeError("record_identity_mismatch")
                principal, _ = self._principal(store, previous, SUBJECT)
                return {"record_type": "service_account_activation/v1", "tenant_id": principal.tenant_id,
                        "namespace": principal.namespace, "created": False, "committed": True}
            tenant_id, namespace = request.tenant_id, request.namespace
            rows = (
                self._catalog.record(TENANT, tenant_id, {"record_type": SCHEMAS[TENANT],
                    "tenant_id": tenant_id, "namespace": namespace, "scopes": list(request.scopes),
                    "enabled": True, "body_access_revoked": False}, tenant_id=tenant_id),
                self._catalog.record(TENANT_NAMESPACE, namespace, {"record_type": SCHEMAS[TENANT_NAMESPACE],
                    "tenant_id": tenant_id}, tenant_id=tenant_id),
                self._catalog.record(SUBJECT, (request.issuer, request.subject), {"record_type": SCHEMAS[SUBJECT],
                    "tenant_id": tenant_id, "issuer": request.issuer, "subject": request.subject,
                    "enabled": True}, tenant_id=tenant_id),
                self._catalog.record(GRANTS, tenant_id, _follows(tenant_id) if request.follows_active_release else {
                    "record_type": SCHEMAS[GRANTS], "tenant_id": tenant_id,
                    "grants": [asdict(ProvisioningGrant(tenant_id, binding, True))
                               for binding in request.starter_bindings]}, tenant_id=tenant_id),
            )
            self._catalog.commit(store, rows, tuple(self._catalog.guard(None, row["record_id"]) for row in rows))
        return {"record_type": "service_account_activation/v1", "tenant_id": tenant_id,
                "namespace": namespace, "created": True, "committed": True}

    def revoke_key(self, tenant_id: str, key_id: str):
        identifier(tenant_id, "tenant identity")
        identifier(key_id, "key identity")
        with self._catalog.store(write=True) as store:
            tenant, _ = self._tenant(store, tenant_id)
            rows = [row for row in self._catalog.rows(store, KEY, tenant_id)
                    if self._payload(row, KEY).get("key_id") == key_id]
            if len(rows) != 1:
                raise ServiceRuntimeError("key_not_found")
            row = rows[0]
            updated = {**row, "record_version": uuid.uuid4().hex,
                       "payload": {**row["payload"], "enabled": False}}
            self._catalog.commit(store, (updated,), (self._catalog.guard(tenant), self._catalog.guard(row)))
        return {"committed": True, "key_id": key_id, "revoked": True}

    def set_tenant_enabled(self, tenant_id: str, enabled: bool):
        if type(enabled) is not bool:
            raise ServiceRuntimeError("invalid_request")
        with self._catalog.store(write=True) as store:
            row, _ = self._tenant(store, tenant_id)
            updated = {**row, "record_version": uuid.uuid4().hex,
                       "payload": {**row["payload"], "enabled": enabled}}
            self._catalog.commit(store, (updated,), (self._catalog.guard(row),))
        return {"committed": True, "tenant_id": tenant_id, "enabled": enabled}

    def bind_subject(self, request: SubjectBindingRequest):
        if not isinstance(request, SubjectBindingRequest):
            raise ServiceRuntimeError("invalid_request")
        with self._catalog.store(write=True) as store:
            tenant, _ = self._tenant(store, request.tenant_id)
            row = self._catalog.record(SUBJECT, (request.issuer, request.subject), {
                "record_type": SCHEMAS[SUBJECT], "tenant_id": request.tenant_id,
                "issuer": request.issuer, "subject": request.subject, "enabled": True,
            }, tenant_id=request.tenant_id)
            self._catalog.commit(store, (row,), (self._catalog.guard(tenant),
                self._catalog.guard(None, row["record_id"])))
        return {"committed": True, "tenant_id": request.tenant_id}

    def revoke_subject(self, request: SubjectBindingRequest):
        if not isinstance(request, SubjectBindingRequest):
            raise ServiceRuntimeError("invalid_request")
        with self._catalog.store(write=True) as store:
            row = self._catalog.read(store, SUBJECT, (request.issuer, request.subject))
            data = self._payload(row, SUBJECT)
            if data.get("tenant_id") != request.tenant_id:
                raise ServiceRuntimeError("subject_not_found")
            updated = {**row, "record_version": uuid.uuid4().hex,
                       "payload": {**data, "enabled": False}}
            self._catalog.commit(store, (updated,), (self._catalog.guard(row),))
        return {"committed": True, "revoked": True}

    def browser_session_revoked(self, credential_digest):
        if (not isinstance(credential_digest, str) or len(credential_digest) != 64
                or any(character not in '0123456789abcdef' for character in credential_digest)):
            raise ServiceRuntimeError('invalid_credential_digest')
        with self._catalog.store() as store:
            row = self._catalog.read(store, SESSION_REVOCATION, credential_digest)
            if row is None:
                return False
            self._payload(row, SESSION_REVOCATION)
            return True

    def revoke_browser_session(self, principal, credential_digest, expires_at):
        """Refuse one browser session until it expires; then remove every revocation already expired.

        The removal runs after the sign-out commits and never changes its answer.
        """
        if not self.browser_session_revoked(credential_digest):
            if type(expires_at) is not int or expires_at <= self._now():
                raise ServiceRuntimeError('invalid_expiry')
            with self._catalog.store(write=True) as store:
                current, guards = self._revalidate(store, principal)
                if current.authentication_kind != SUBJECT:
                    raise ServiceRuntimeError('browser_identity_required')
                row = self._catalog.record(SESSION_REVOCATION, credential_digest,
                    {'record_type': SCHEMAS[SESSION_REVOCATION], 'tenant_id': current.tenant_id,
                     'credential_digest': credential_digest, 'expires_at': expires_at}, tenant_id=current.tenant_id)
                self._catalog.commit(store, (row,), (*guards, self._catalog.guard(None, row['record_id'])))
        from .retention import sweep_after_sign_out
        sweep_after_sign_out(self)
        return {'committed': True, 'revoked': True}

    def _principal(self, store, authentication, kind):
        data = self._payload(authentication, kind)
        if data.get("enabled") is not True:
            raise ServiceRuntimeError("unauthorized")
        tenant_id = data.get("tenant_id")
        tenant, tenant_data = self._tenant(store, tenant_id)
        if tenant_data.get("enabled") is not True:
            raise ServiceRuntimeError("unauthorized")
        permitted = set(scopes(tenant_data.get("scopes")))
        owner_guards = ()
        if kind == KEY:
            expiry = data.get("expires_at")
            if expiry is not None and (type(expiry) is not int or expiry <= self._now()):
                raise ServiceRuntimeError("unauthorized")
            permitted.intersection_update(scopes(data.get("scopes")))
            owner_bound = data.get("record_type") == OWNER_BOUND_KEY_SCHEMA
            # The record version and the customer profile must agree. A customer
            # key stored under the older version would hide the owner rule from
            # an older server, so the current server refuses that shape as well.
            if owner_bound is not (data.get("management_profile") == CLIENT_ACCESS_PROFILE):
                raise ServiceRuntimeError("unsupported_or_corrupt_record")
            if owner_bound:
                owner_ref = data.get("owner_subject_record_id")
                if not isinstance(owner_ref, str) or not owner_ref:
                    raise ServiceRuntimeError("unauthorized")
                owner = self._catalog.read_id(store, owner_ref, kind=SUBJECT)
                value = self._payload(owner, SUBJECT) if owner is not None else {}
                if value.get("enabled") is not True or value.get("tenant_id") != tenant_id:
                    raise ServiceRuntimeError("unauthorized")
                owner_guards = (self._catalog.guard(owner),)
        entitlement = self._catalog.read(store, ENTITLEMENT, tenant_id)
        policy = self._catalog.read(store, BILLING_POLICY, "stripe")
        principal = ServicePrincipal(tenant_id, tenant_data["namespace"], data.get("key_id", ""),
            self._entitlement(entitlement, policy) if tenant_data.get("body_access_revoked") is False else METADATA,
            tuple(sorted(permitted)), authentication["record_id"], kind, self._issuer)
        principal = replace(principal, _proof=self._principal_proof(principal))
        guards = (self._catalog.guard(authentication), self._catalog.guard(tenant),
                  self._catalog.guard(entitlement, self._catalog.identity(ENTITLEMENT, tenant_id)),
                  self._catalog.guard(policy, self._catalog.identity(BILLING_POLICY, "stripe")), *owner_guards)
        return principal, guards

    def authenticate_key(self, raw_key: str) -> ServicePrincipal:
        if not isinstance(raw_key, str) or not raw_key or len(raw_key) > 1024:
            raise ServiceRuntimeError("unauthorized")
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        with self._catalog.store() as store:
            row = self._catalog.read(store, KEY, hashed)
            if (row is None or not isinstance(row["payload"].get("key_digest"), str)
                    or not secrets.compare_digest(row["payload"]["key_digest"], hashed)):
                raise ServiceRuntimeError("unauthorized")
            return self._principal(store, row, KEY)[0]

    def authenticate_subject(self, issuer: str, subject: str) -> ServicePrincipal:
        with self._catalog.store() as store:
            row = self._catalog.read(store, SUBJECT, (issuer, subject))
            if row is None or row["payload"].get("issuer") != issuer or row["payload"].get("subject") != subject:
                raise ServiceRuntimeError("unauthorized")
            return self._principal(store, row, SUBJECT)[0]

    def _revalidate(self, store, principal):
        if not isinstance(principal, ServicePrincipal) or principal._issuer is not self._issuer:
            raise ServiceRuntimeError("unissued_principal")
        if not isinstance(principal._proof, str) or not hmac.compare_digest(principal._proof, self._principal_proof(principal)):
            raise ServiceRuntimeError("unissued_principal")
        if principal.authentication_kind not in (KEY, SUBJECT):
            raise ServiceRuntimeError("unissued_principal")
        row = self._catalog.read_id(store, principal.authentication_record_id, kind=principal.authentication_kind)
        current, guards = self._principal(store, row, principal.authentication_kind)
        if current.tenant_id != principal.tenant_id:
            raise ServiceRuntimeError("unauthorized")
        return current, guards

    def revalidate(self, principal):
        with self._catalog.store() as store:
            return self._revalidate(store, principal)[0]

    def set_grants(self, tenant_id: str, grants):
        grants = tuple(grants)
        if any(not isinstance(grant, ProvisioningGrant) or grant.tenant_id != tenant_id for grant in grants):
            raise ServiceRuntimeError("invalid_disclosure_grant")
        if len({grant.binding.identity for grant in grants}) != len(grants):
            raise ServiceRuntimeError("duplicate_disclosure_grant")
        with self._catalog.store(write=True) as store:
            tenant, _ = self._tenant(store, tenant_id)
            previous = self._catalog.read(store, GRANTS, tenant_id)
            row = self._catalog.record(GRANTS, tenant_id, {"record_type": SCHEMAS[GRANTS],
                "tenant_id": tenant_id, "grants": [asdict(grant) for grant in grants]}, tenant_id=tenant_id)
            self._catalog.commit(store, (row,), (self._catalog.guard(tenant),
                self._catalog.guard(previous, row["record_id"])))
        return {"committed": True, "tenant_id": tenant_id, "grants": len(grants)}

    def grant_snapshot(self, principal):
        with self._catalog.store() as store:
            current, _ = self._revalidate(store, principal)
            row = self._catalog.read(store, GRANTS, current.tenant_id)
            if row is None:
                return (), self._catalog.guard(None, self._catalog.identity(GRANTS, current.tenant_id))
            data = self._payload(row, GRANTS)
            if data["record_type"] != SCHEMAS[GRANTS]:
                return release_following_grants(data, current.tenant_id), self._catalog.guard(row)
            grants = tuple(ProvisioningGrant(**{**value, "binding": ProvisioningItemBinding(**value["binding"])})
                           for value in data["grants"])
            if data.get("tenant_id") != current.tenant_id or any(g.tenant_id != current.tenant_id for g in grants):
                raise ServiceRuntimeError("invalid_disclosure_grant")
            return grants, self._catalog.guard(row)

    def set_operator_entitlement(self, tenant_id: str, *, valid_until: int, evidence_ref: str):
        """Explicit host grant, not evidence of a Stripe payment or subscription."""
        from .records import text
        text(evidence_ref, "host approval reference")
        if type(valid_until) is not int or valid_until <= self._now():
            raise ServiceRuntimeError("invalid_expiry")
        with self._catalog.store(write=True) as store:
            tenant, _ = self._tenant(store, tenant_id)
            previous = self._catalog.read(store, ENTITLEMENT, tenant_id)
            row = self._catalog.record(ENTITLEMENT, tenant_id, {"record_type": SCHEMAS[ENTITLEMENT],
                "tenant_id": tenant_id, "enabled": True, "entitlement": BODIES,
                "valid_until": valid_until, "source": HOST_GRANT_SOURCE, "evidence_ref": evidence_ref}, tenant_id=tenant_id)
            updated_tenant = {**tenant, "record_version": uuid.uuid4().hex,
                              "payload": {**tenant["payload"], "body_access_revoked": False}}
            self._catalog.commit(store, (row, updated_tenant), (self._catalog.guard(tenant), self._catalog.guard(previous, row["record_id"])))
        return {"committed": True, "source": HOST_GRANT_SOURCE}

    def access_source_report(self):
        """Host-side report that separates paying accounts from comped accounts.

        One account's paid access comes from exactly one recorded source. Only a
        provider subscription snapshot is evidence of money, so only that source
        is revenue bearing. A host grant and a promotion code grant are comped
        and are counted separately. The classification reads the recorded
        `source` field; it never infers money from an expiry, a grant or a name.
        """
        now = self._now()
        with self._catalog.store() as store:
            policy = self._catalog.read(store, BILLING_POLICY, "stripe")
            accounts = []
            for row in self._catalog.rows_all(store, ENTITLEMENT):
                value = self._payload(row, ENTITLEMENT)
                tenant_id = value.get("tenant_id", "")
                tenant_row = self._catalog.read(store, TENANT, tenant_id)
                # The tenant record is read through the same version check every
                # other reader uses. A record this release does not support is
                # refused here rather than reinterpreted, because a miscounted
                # account is worse than a report that stops and names the fault.
                tenant = self._payload(tenant_row, TENANT) if tenant_row is not None else {}
                source = value.get("source", "")
                effective = (self._entitlement(row, policy)
                             if tenant.get("enabled") is True and tenant.get("body_access_revoked") is False
                             else METADATA)
                accounts.append({"tenant_id": tenant_id, "source": source,
                    "revenue_bearing": source in REVENUE_BEARING_SOURCES,
                    "comped": source in COMPED_SOURCES, "entitlement": effective,
                    "active": effective == BODIES, "valid_until": value.get("valid_until"),
                    "promotion_code_id": value.get("promotion_code_id", ""),
                    "approval_ref": value.get("approval_ref", "") or value.get("evidence_ref", ""),
                    "subscription_ids": list(value.get("subscription_ids", ()))})
        accounts.sort(key=lambda row: (row["source"], row["tenant_id"]))
        paying = [row for row in accounts if row["revenue_bearing"] and row["active"]]
        comped = [row for row in accounts if row["comped"] and row["active"]]
        return {"record_type": ACCESS_SOURCE_REPORT_VERSION, "observed_at": now,
            "revenue_bearing_sources": list(REVENUE_BEARING_SOURCES), "comped_sources": list(COMPED_SOURCES),
            "accounts": accounts,
            "counts": {"records": len(accounts), "revenue_bearing": len(paying), "comped": len(comped),
                       "without_paid_access": len(accounts) - len(paying) - len(comped)},
            "revenue_bearing_tenants": sorted(row["tenant_id"] for row in paying),
            "comped_tenants": sorted(row["tenant_id"] for row in comped),
            "limitations": [
                "This report counts accounts, not money. The amount invoiced is held by the payment provider.",
                "An account whose access came from a promotion code or a host grant is comped. It is never "
                "counted as revenue, whatever its expiry or its grants say.",
                "An account with no entitlement record has no row here; it has free access only."]}

    def configure_billing_policy(self, policy, *, expected_version=None):
        from .billing_records import StripeEntitlementPolicy
        if not isinstance(policy, StripeEntitlementPolicy):
            raise ServiceRuntimeError("invalid_billing_policy")
        encoded = asdict(policy)
        with self._catalog.store(write=True) as store:
            previous = self._catalog.read(store, BILLING_POLICY, "stripe")
            if previous is not None:
                if digest(self._payload(previous, BILLING_POLICY).get("policy")) == digest(encoded):
                    return {"committed": True, "record_version": previous["record_version"], "policy_digest": digest(encoded)}
                if expected_version != previous["record_version"]:
                    raise ServiceRuntimeError("billing_policy_revision_required")
            elif expected_version is not None:
                raise ServiceRuntimeError("billing_policy_revision_required")
            row = self._catalog.record(BILLING_POLICY, "stripe", {"record_type": SCHEMAS[BILLING_POLICY],
                "policy": encoded, "policy_digest": digest(encoded)})
            self._catalog.commit(store, (row,), (self._catalog.guard(previous, row["record_id"]),))
        return {"committed": True, "record_version": row["record_version"], "policy_digest": digest(encoded)}

    def revoke_entitlement(self, tenant_id: str):
        with self._catalog.store(write=True) as store:
            tenant, _ = self._tenant(store, tenant_id)
            previous = self._catalog.read(store, ENTITLEMENT, tenant_id)
            row = self._catalog.record(ENTITLEMENT, tenant_id, {"record_type": SCHEMAS[ENTITLEMENT],
                "tenant_id": tenant_id, "enabled": False, "entitlement": METADATA,
                "valid_until": None, "source": "host_revocation"}, tenant_id=tenant_id)
            updated_tenant = {**tenant, "record_version": uuid.uuid4().hex,
                              "payload": {**tenant["payload"], "body_access_revoked": True}}
            self._catalog.commit(store, (row, updated_tenant), (self._catalog.guard(tenant), self._catalog.guard(previous, row["record_id"])))
        return {"committed": True, "revoked": True}

    def _customer_effect_proof(self, reservation):
        document = {"spec": asdict(reservation.spec), "record_id": reservation.record_id,
                    "attempt_id": reservation.attempt_id, "idempotency_key": reservation.idempotency_key,
                    "retry_before": reservation.retry_before, "attempt_number": reservation.attempt_number,
                    "idempotency_cycles": reservation.idempotency_cycles,
                    "guards": [asdict(guard) for guard in reservation.authority_guards]}
        return hmac.new(self._effect_secret, canonical(document).encode(), hashlib.sha256).hexdigest()

    def _reserved_customer(self, store, reservation):
        if (not isinstance(reservation, BillingCustomerReservation)
                or reservation._issuer is not self._effect_issuer):
            raise ServiceRuntimeError("unissued_billing_customer_reservation")
        if (not isinstance(reservation._proof, str)
                or not hmac.compare_digest(reservation._proof, self._customer_effect_proof(reservation))):
            raise ServiceRuntimeError("unissued_billing_customer_reservation")
        row = self._catalog.read_id(store, reservation.record_id, kind=CUSTOMER_EFFECT)
        state = self._payload(row, CUSTOMER_EFFECT)
        if (state["spec_digest"] != reservation.spec.digest or state["attempt_id"] != reservation.attempt_id
                or state["idempotency_key"] != reservation.idempotency_key):
            raise ServiceRuntimeError("billing_customer_reservation_changed")
        return row, state

    def _unchanged_authority(self, store, reservation):
        for guard in reservation.authority_guards:
            actual = store.get(guard.record_id)
            if (guard.must_not_exist and actual is not None) or (not guard.must_not_exist
                    and (actual is None or actual["record_version"] != guard.record_version)):
                raise ServiceRuntimeError("billing_customer_authority_changed")

    # The two rules a creation record follows live beside that record in
    # `records.py`, with their reasons. They are bound here, so the reservation
    # below reads them and a removed-guard control can patch them on this class.
    _only_the_provider_account_changed = staticmethod(billing_customer_request_differs_only_by_provider_account)
    _search_can_show_the_previous_attempt = staticmethod(billing_customer_search_can_show_the_previous_attempt)

    def begin_billing_customer(self, principal, spec: BillingCustomerEffectSpec, *,
                               lease_seconds, reconciliation_seconds) -> BillingCustomerReservation:
        """Reserve the one provider customer creation this account may ever need.

        The durable identity is the account, so every attempt, restart and
        later repeat reuses one record. A running attempt holds a lease, so a
        second caller is refused instead of starting a second creation. When
        the reconciliation window has passed, the stored provider idempotency
        key can no longer reconcile an earlier uncertain attempt, so a new
        cycle takes a new key; the metadata search before creation is what
        then keeps the account at one customer, and a new cycle waits until
        that search can show whatever the previous attempt did.

        The configured provider account may change, for example when the
        service moves from the test account to the live one. A customer at the
        account being left does not exist at the new one, so an account with no
        binding starts a fresh cycle at the new provider account and keeps the
        account it left as evidence. An account that is bound needs the
        explicit `release_billing_customer_account` operation first.
        """
        if not isinstance(spec, BillingCustomerEffectSpec):
            raise ServiceRuntimeError("invalid_billing_customer_effect")
        if (type(lease_seconds) is not int or lease_seconds <= 0 or type(reconciliation_seconds) is not int
                or reconciliation_seconds < PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
                or not lease_seconds < reconciliation_seconds < PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS):
            raise ServiceRuntimeError("invalid_billing_customer_effect_allowance")
        now = self._now()
        with self._catalog.store(write=True) as store:
            current, authority = self._revalidate(store, principal)
            if current.tenant_id != spec.tenant_id or BILLING_MANAGE_SCOPE not in current.scopes:
                raise ServiceRuntimeError("scope_required")
            _tenant_row, tenant = self._tenant(store, current.tenant_id)
            if tenant.get("billing_customer_id") or tenant.get("billing_account_id"):
                raise ServiceRuntimeError("billing_customer_already_bound")
            previous = self._catalog.read(store, CUSTOMER_EFFECT, current.tenant_id)
            if previous is None:
                state = {"record_type": DISPATCH_DEADLINE_CUSTOMER_EFFECT_SCHEMA, "tenant_id": current.tenant_id,
                         "spec": asdict(spec), "spec_digest": spec.digest, "created_at": now,
                         "retry_before": now + reconciliation_seconds, "idempotency_cycles": 0,
                         "idempotency_key": CUSTOMER_IDEMPOTENCY_PREFIX + uuid.uuid4().hex,
                         "attempts": 0, "status": EFFECT_PENDING, "provider_customer_id": "",
                         "diagnostic_code": "", "superseded_provider_accounts": []}
            else:
                state = dict(self._payload(previous, CUSTOMER_EFFECT))
                stored, requested = state.get("spec"), asdict(spec)
                account_changed = False
                if state.get("spec_digest") != spec.digest or stored != requested:
                    if not self._only_the_provider_account_changed(stored, requested):
                        raise ServiceRuntimeError("billing_customer_request_identity_conflict")
                    account_changed = True
                if state.get("lease_until", 0) > now:
                    raise ServiceRuntimeError("billing_customer_creation_in_progress")
                if account_changed or now >= state["retry_before"]:
                    if not self._search_can_show_the_previous_attempt(state, now):
                        raise ServiceRuntimeError("billing_customer_search_not_current_yet")
                    if account_changed:
                        state.update(spec=requested, spec_digest=spec.digest,
                                     provider_customer_id="", diagnostic_code="",
                                     superseded_provider_accounts=[
                                         *state.get("superseded_provider_accounts", ()),
                                         {"provider_account_id": stored["provider_account_id"],
                                          "provider_customer_id": state.get("provider_customer_id", ""),
                                          "status": state.get("status", ""), "superseded_at": now}])
                    state.update(idempotency_key=CUSTOMER_IDEMPOTENCY_PREFIX + uuid.uuid4().hex,
                                 retry_before=now + reconciliation_seconds,
                                 idempotency_cycles=state["idempotency_cycles"] + 1, status=EFFECT_PENDING)
            attempt_id = uuid.uuid4().hex
            # The same moment `authorize_billing_customer_dispatch` refuses at,
            # stored so that a later cycle waits for this attempt rather than
            # for one rebuilt from its own lease.
            state.update(attempt_id=attempt_id, lease_until=now + lease_seconds,
                         dispatch_deadline=min(now + lease_seconds, state["retry_before"]),
                         attempts=state["attempts"] + 1, last_attempt_at=now)
            row = self._catalog.record(CUSTOMER_EFFECT, current.tenant_id, state, tenant_id=current.tenant_id)
            self._catalog.commit(store, (row,), (*authority, self._catalog.guard(previous, row["record_id"])))
        reservation = BillingCustomerReservation(spec=spec, record_id=row["record_id"], attempt_id=attempt_id,
            idempotency_key=state["idempotency_key"], retry_before=state["retry_before"],
            attempt_number=state["attempts"], idempotency_cycles=state["idempotency_cycles"],
            authority_guards=authority, _issuer=self._effect_issuer)
        return replace(reservation, _proof=self._customer_effect_proof(reservation))

    def authorize_billing_customer_dispatch(self, principal, reservation: BillingCustomerReservation):
        """Recheck current authority, the lease and every reserved guard before the provider call."""
        with self._catalog.store() as store:
            current, _ = self._revalidate(store, principal)
            if BILLING_MANAGE_SCOPE not in current.scopes or current.tenant_id != reservation.spec.tenant_id:
                raise ServiceRuntimeError("scope_required")
            _row, state = self._reserved_customer(store, reservation)
            if self._now() >= min(state["lease_until"], state["retry_before"]):
                raise ServiceRuntimeError("billing_customer_reservation_expired")
            self._unchanged_authority(store, reservation)
            _tenant_row, tenant = self._tenant(store, current.tenant_id)
            if tenant.get("billing_customer_id") or tenant.get("billing_account_id"):
                raise ServiceRuntimeError("billing_customer_already_bound")
        return True

    def finish_billing_customer(self, reservation: BillingCustomerReservation, *,
                                diagnostic_code="", attempted=True):
        """Retain an already attempted outcome; the same account identity retries it."""
        if type(attempted) is not bool:
            raise ServiceRuntimeError("invalid_effect_outcome")
        with self._catalog.store(write=True) as store:
            held, current = self._reserved_customer(store, reservation)
            state = dict(current)
            state.update(status=EFFECT_CONFIRMED if state["provider_customer_id"] else
                         EFFECT_UNKNOWN if attempted else EFFECT_NOT_ATTEMPTED,
                         diagnostic_code=diagnostic_code, lease_until=0, attempt_id="",
                         completed_at=self._now())
            updated = {**held, "record_version": uuid.uuid4().hex, "payload": state}
            self._catalog.commit(store, (updated,), (self._catalog.guard(held),))
        return {"record_type": BILLING_CUSTOMER_OUTCOME_VERSION, "effect_ref": held["record_id"],
                "status": state["status"], "retry_before": state["retry_before"]}

    def bind_billing_customer(self, request: BillingCustomerBindingRequest, *, reservation=None):
        """Bind one provider customer to one account under the existing catalogue guard.

        The tenant guard and the absent customer record commit together, so a
        second writer cannot bind a second customer. When a reservation is
        supplied, its authority guards and its durable attempt must still hold,
        and the effect record is confirmed in the same atomic write.
        """
        if not isinstance(request, BillingCustomerBindingRequest):
            raise ServiceRuntimeError("invalid_request")
        if reservation is not None and (not isinstance(reservation, BillingCustomerReservation)
                or reservation.spec.tenant_id != request.tenant_id
                or reservation.spec.provider_account_id != request.provider_account_id):
            raise ServiceRuntimeError("invalid_billing_customer_reservation")
        with self._catalog.store(write=True) as store:
            tenant, data = self._tenant(store, request.tenant_id)
            if data.get("billing_customer_id") or data.get("billing_account_id"):
                raise ServiceRuntimeError("billing_customer_already_bound")
            row = self._catalog.record(CUSTOMER, (request.provider_account_id, request.provider_customer_id), {
                "record_type": SCHEMAS[CUSTOMER], "tenant_id": request.tenant_id,
                "provider_customer_id": request.provider_customer_id,
                "provider_account_id": request.provider_account_id}, tenant_id=request.tenant_id)
            updated = {**tenant, "record_version": uuid.uuid4().hex,
                "payload": {**data, "billing_customer_id": request.provider_customer_id,
                            "billing_account_id": request.provider_account_id}}
            records = (updated, row)
            guards = (self._catalog.guard(tenant), self._catalog.guard(None, row["record_id"]))
            if reservation is not None:
                held, state = self._reserved_customer(store, reservation)
                self._unchanged_authority(store, reservation)
                if self._now() >= min(state["lease_until"], state["retry_before"]):
                    raise ServiceRuntimeError("billing_customer_reservation_expired")
                effect = {**held, "record_version": uuid.uuid4().hex, "payload": {**state,
                    "status": EFFECT_CONFIRMED, "provider_customer_id": request.provider_customer_id,
                    "diagnostic_code": "", "lease_until": 0, "attempt_id": "", "completed_at": self._now()}}
                records, guards = (*records, effect), (*guards, self._catalog.guard(held))
            self._catalog.commit(store, records, guards)
        return {"committed": True, "tenant_id": request.tenant_id,
                "provider_account_id": request.provider_account_id,
                "provider_customer_id": request.provider_customer_id,
                "reconciled_effect": reservation is not None}

    def release_billing_customer_account(self, request: BillingCustomerAccountRelease):
        """Free one account from a provider account the service has left.

        This is the defined route from a customer at one provider account to a
        customer at another, for example when the service moves from the test
        account to the live one. It is an explicit host operation, so an
        account that is bound to a different provider account stays refused
        until someone decides to release it. It refuses unless the account's
        binding and its creation record both name exactly the account being
        released, and it refuses while a creation is running.

        The released customer record is kept. It is the evidence of what the
        account had at the provider it left, and the provider event path cannot
        reach it any more because that path reads the customer record under the
        provider account the service is configured with. Clearing the binding
        makes the account eligible for one new customer at the current provider
        account through the ordinary checkout path.
        """
        if not isinstance(request, BillingCustomerAccountRelease):
            raise ServiceRuntimeError("invalid_request")
        now = self._now()
        with self._catalog.store(write=True) as store:
            tenant, data = self._tenant(store, request.tenant_id)
            previous = self._catalog.read(store, CUSTOMER_EFFECT, request.tenant_id)
            state = dict(self._payload(previous, CUSTOMER_EFFECT)) if previous is not None else None
            stored = state.get("spec") if state is not None else None
            if state is not None and not isinstance(stored, dict):
                raise ServiceRuntimeError("unsupported_or_corrupt_record")
            named = {data.get("billing_account_id") or "",
                     (stored.get("provider_account_id") if stored is not None else "") or ""}
            named.discard("")
            if named != {request.released_provider_account_id}:
                raise ServiceRuntimeError("billing_customer_release_account_mismatch")
            if state is not None and state.get("lease_until", 0) > now:
                raise ServiceRuntimeError("billing_customer_creation_in_progress")
            released_customer = data.get("billing_customer_id") or ""
            updated = {**tenant, "record_version": uuid.uuid4().hex,
                       "payload": {**data, "billing_customer_id": "", "billing_account_id": ""}}
            self._catalog.commit(store, (updated,), (self._catalog.guard(tenant),))
        return {"record_type": BILLING_CUSTOMER_ACCOUNT_RELEASE_VERSION, "committed": True,
                "tenant_id": request.tenant_id,
                "released_provider_account_id": request.released_provider_account_id,
                "released_provider_customer_id": released_customer,
                "current_provider_account_id": request.current_provider_account_id,
                "released_at": now}

    def billing_customer_for(self, principal: ServicePrincipal):
        """Resolve the exact durable provider mapping after current scope validation."""
        with self._catalog.store() as store:
            current, _ = self._revalidate(store, principal)
            if BILLING_MANAGE_SCOPE not in current.scopes:
                raise ServiceRuntimeError("scope_required")
            _tenant, tenant = self._tenant(store, current.tenant_id)
            account, customer = tenant.get("billing_account_id"), tenant.get("billing_customer_id")
            if not account or not customer:
                raise ServiceRuntimeError("billing_customer_not_bound")
            row = self._catalog.read(store, CUSTOMER, (account, customer))
            value = self._payload(row, CUSTOMER)
            if value.get("tenant_id") != current.tenant_id:
                raise ServiceRuntimeError("billing_customer_binding_mismatch")
            return {"record_type": "service_billing_customer_binding/v1", "tenant_id": current.tenant_id,
                    "provider_account_id": account, "provider_customer_id": customer,
                    "record_id": row["record_id"], "record_version": row["record_version"]}

    def record_usage(self, request: ProvisioningMeterRequest, principal: ServicePrincipal, *, guards=()):
        if not isinstance(request, ProvisioningMeterRequest):
            raise ServiceRuntimeError("invalid_usage_request")
        try:
            with self._catalog.store(write=True) as store:
                current, auth_guards = self._revalidate(store, principal)
                if (current.tenant_id != request.tenant_id or current.entitlement != BODIES
                        or PROVISIONING_READ_SCOPE not in current.scopes):
                    raise ServiceRuntimeError("body_forbidden")
                logical = (request.tenant_id, request.request_id)
                expected = digest(asdict(request))
                held = self._catalog.read(store, USAGE, logical)
                if held is not None:
                    data = self._payload(held, USAGE)
                    if data.get("request_digest") != expected:
                        raise ServiceRuntimeError("usage_identity_conflict")
                    return ProvisioningMeterAcknowledgment(request, True, held["record_id"], "durable")
                row = self._catalog.record(USAGE, logical, {"record_type": SCHEMAS[USAGE],
                    "tenant_id": request.tenant_id, "request_id_digest": digest(request.request_id),
                    "request_digest": expected, "unit": request.unit, "quantity": request.quantity,
                    "item_identity": request.binding.identity, "body_digest": request.binding.body_digest,
                    "at": self._now()}, tenant_id=request.tenant_id)
                self._catalog.commit(store, (row,), (*auth_guards, *guards, self._catalog.guard(None, row["record_id"])))
                return ProvisioningMeterAcknowledgment(request, True, row["record_id"], "durable")
        except ServiceCommitUnknown:
            return ProvisioningMeterAcknowledgment(request, None)

    def usage_for(self, principal: ServicePrincipal):
        with self._catalog.store() as store:
            current, _ = self._revalidate(store, principal)
            if USAGE_READ_SCOPE not in current.scopes:
                raise ServiceRuntimeError("scope_required")
            rows = self._catalog.rows(store, USAGE, current.tenant_id)
            totals = {}
            for row in rows:
                value = self._payload(row, USAGE)
                totals[value["unit"]] = totals.get(value["unit"], 0) + value["quantity"]
            return {"record_type": "durable_tenant_usage/v1", "tenant_id": current.tenant_id,
                    "records": len(rows), "totals": totals, "durability": "durable"}


def self_test():
    from .runtime_checks import run_checks
    return run_checks()
