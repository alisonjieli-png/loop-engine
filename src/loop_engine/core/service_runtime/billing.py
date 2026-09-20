"""Signed Stripe snapshot-event handling with durable invalidation and reconciliation.

Event identifiers deduplicate deliveries. Event timestamps never order updates.
A verified relevant event first removes paid access, then resolves current
provider state under a pre-fetch catalogue revision guard. Unknown provider
state stays unavailable. Only non-sensitive projections and digests persist.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import hmac
import json
import re
import uuid

from .billing_records import (
    BillingEventResult, EVENT_TYPES, StripeCustomerSubscriptionSnapshot,
    StripeEntitlementPolicy, StripeSubscriptionResolver, StripeWebhookConfig,
    SUBSCRIPTION_ACTIVE, SUBSCRIPTION_TRIALING,
)
from .records import ServiceCommitUnknown, ServiceRuntimeError, canonical, digest, identifier
from .runtime import (BILLING_POLICY, BODIES, CUSTOMER, ENTITLEMENT, METADATA, SCHEMAS,
                      STRIPE_SNAPSHOT_SOURCE, ServiceRuntime)

BILLING_EVENT = "service_stripe_event"
BILLING_EVENT_VERSION = "service_stripe_event/v1"
PENDING, APPLIED, IGNORED = "pending", "applied", "ignored"
EVENT_OBJECT = "event"


def _json(body):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")))
        canonical(value)
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise ServiceRuntimeError("invalid_stripe_payload") from None


class StripeEventProcessor:
    """Host-configured webhook boundary; no provider call without an installed resolver."""

    def __init__(self, runtime: ServiceRuntime, config: StripeWebhookConfig,
                 policy: StripeEntitlementPolicy, secret_resolver, subscription_resolver=None):
        if (not isinstance(runtime, ServiceRuntime) or not isinstance(config, StripeWebhookConfig)
                or not isinstance(policy, StripeEntitlementPolicy) or not callable(secret_resolver)
                or (subscription_resolver is not None and not isinstance(subscription_resolver, StripeSubscriptionResolver))):
            raise ServiceRuntimeError("invalid_billing_configuration")
        self.runtime, self.config, self.policy = runtime, config, policy
        self._secret_resolver, self._resolver = secret_resolver, subscription_resolver

    def _verified(self, raw_body, signature_header):
        if (not isinstance(raw_body, bytes) or len(raw_body) > self.config.maximum_payload_bytes
                or not isinstance(signature_header, str) or len(signature_header) > 16_384
                or "\n" in signature_header or "\r" in signature_header):
            raise ServiceRuntimeError("invalid_stripe_signature")
        fields = [piece.strip().split("=", 1) for piece in signature_header.split(",")]
        timestamps = [row[1] for row in fields if len(row) == 2 and row[0] == "t"]
        signatures = [row[1] for row in fields if len(row) == 2 and row[0] == "v1"
                      and re.fullmatch(r"[0-9a-f]{64}", row[1])]
        if len(timestamps) != 1 or not re.fullmatch(r"[0-9]{1,20}", timestamps[0]) or not signatures:
            raise ServiceRuntimeError("invalid_stripe_signature")
        timestamp = int(timestamps[0])
        if abs(self.runtime._now() - timestamp) > self.config.tolerance_seconds:
            raise ServiceRuntimeError("expired_stripe_signature")
        signed = timestamps[0].encode("ascii") + b"." + raw_body
        matched = False
        for reference in self.config.signing_secret_refs:
            try:
                secret = self._secret_resolver(reference)
            except Exception:
                raise ServiceRuntimeError("webhook_secret_unavailable") from None
            if not isinstance(secret, str) or not secret:
                raise ServiceRuntimeError("webhook_secret_unavailable")
            expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
            matched = any(hmac.compare_digest(expected, value) for value in signatures) or matched
        if not matched:
            raise ServiceRuntimeError("invalid_stripe_signature")
        event = _json(raw_body)
        if (not isinstance(event, dict) or event.get("object") != EVENT_OBJECT
                or event.get("api_version") != self.config.api_version
                or event.get("livemode") is not self.config.livemode
                or event.get("account", self.config.account_id) != self.config.account_id
                or type(event.get("created")) is not int or event["created"] < 0):
            raise ServiceRuntimeError("unsupported_stripe_event")
        identifier(event.get("id"), "event identity")
        kind = event.get("type")
        if not isinstance(kind, str) or not kind or len(kind) > 200:
            raise ServiceRuntimeError("invalid_stripe_event")
        obj = event.get("data", {}).get("object") if isinstance(event.get("data"), dict) else None
        if not isinstance(obj, dict):
            raise ServiceRuntimeError("unsupported_stripe_event")
        customer = obj.get("customer")
        if isinstance(customer, dict):
            customer = customer.get("id")
        if kind in EVENT_TYPES:
            identifier(customer, "event customer")
        semantic = {"id": event["id"], "type": kind, "api_version": event["api_version"],
                    "livemode": event["livemode"], "account_id": self.config.account_id,
                    "created": event["created"], "data_digest": digest(obj)}
        return {**semantic, "event_digest": digest(semantic), "body_digest": hashlib.sha256(raw_body).hexdigest(),
                "customer_id": customer if kind in EVENT_TYPES else None}

    def _event_payload(self, row):
        if row is None:
            return None
        value = row["payload"]
        if value.get("record_type") != BILLING_EVENT_VERSION:
            raise ServiceRuntimeError("unsupported_billing_event_record")
        return value

    def _begin(self, event):
        catalog = self.runtime._catalog
        logical = (self.config.account_id, self.config.livemode, event["id"])
        with catalog.store(write=True) as store:
            held = catalog.read(store, BILLING_EVENT, logical)
            prior = self._event_payload(held)
            if prior is not None and prior.get("event_digest") != event["event_digest"]:
                raise ServiceRuntimeError("stripe_event_identity_conflict")
            if prior is not None and prior.get("status") in (APPLIED, IGNORED):
                tenant_id = prior.get("tenant_id", "")
                entitlement = METADATA
                if tenant_id:
                    tenant, data = self.runtime._tenant(store, tenant_id)
                    policy = catalog.read(store, BILLING_POLICY, "stripe")
                    if data.get("enabled") is True and data.get("body_access_revoked") is False:
                        entitlement = self.runtime._entitlement(catalog.read(store, ENTITLEMENT, tenant_id), policy)
                return BillingEventResult(event["id"], "duplicate", True, tenant_id, entitlement)
            payload = {"record_type": BILLING_EVENT_VERSION, **event, "status": IGNORED, "tenant_id": ""}
            row = catalog.record(BILLING_EVENT, logical, payload)
            event_guard = catalog.guard(held, row["record_id"])
            if event["type"] not in EVENT_TYPES:
                catalog.commit(store, (row,), (event_guard,))
                return BillingEventResult(event["id"], IGNORED, True)
            customer = catalog.read(store, CUSTOMER, (self.config.account_id, event["customer_id"]))
            mapping = self.runtime._payload(customer, CUSTOMER)
            tenant_id = mapping.get("tenant_id")
            tenant, tenant_data = self.runtime._tenant(store, tenant_id)
            if (tenant_data.get("billing_customer_id") != event["customer_id"]
                    or tenant_data.get("billing_account_id") != self.config.account_id):
                raise ServiceRuntimeError("billing_customer_binding_mismatch")
            policy = catalog.read(store, BILLING_POLICY, "stripe")
            if self.runtime._payload(policy, BILLING_POLICY).get("policy_digest") != digest(asdict(self.policy)):
                raise ServiceRuntimeError("billing_policy_mismatch")
            prior_entitlement = catalog.read(store, ENTITLEMENT, tenant_id)
            pending = catalog.record(ENTITLEMENT, tenant_id, {"record_type": SCHEMAS[ENTITLEMENT],
                "tenant_id": tenant_id, "enabled": False, "entitlement": METADATA, "valid_until": None,
                "source": STRIPE_SNAPSHOT_SOURCE, "pending_event_id": event["id"],
                "policy_digest": digest(asdict(self.policy))}, tenant_id=tenant_id)
            row["attributes"]["tenant_id"] = tenant_id
            row["payload"].update(status=PENDING, tenant_id=tenant_id)
            catalog.commit(store, (row, pending), (event_guard, catalog.guard(tenant), catalog.guard(customer),
                catalog.guard(policy), catalog.guard(prior_entitlement, pending["record_id"])))
            return {"event": row, "entitlement": pending, "tenant": tenant,
                    "customer": customer, "policy": policy, "tenant_id": tenant_id}

    def _decision(self, snapshot):
        if (not isinstance(snapshot, StripeCustomerSubscriptionSnapshot) or snapshot.complete is not True
                or snapshot.account_id != self.config.account_id or snapshot.api_version != self.config.api_version
                or snapshot.livemode is not self.config.livemode):
            raise ServiceRuntimeError("billing_snapshot_unavailable")
        allowed = set(self.policy.allowed_price_ids)
        expiry = []
        selected = []
        for subscription in snapshot.subscriptions:
            ends = [end for price, end in subscription.price_periods if price in allowed and end > self.runtime._now()]
            if not ends or subscription.collection_paused:
                continue
            if subscription.status == SUBSCRIPTION_ACTIVE and subscription.latest_invoice_paid is True:
                expiry.append(max(ends))
                selected.append(subscription.subscription_id)
            elif (subscription.status == SUBSCRIPTION_TRIALING and self.policy.allow_trialing is True
                  and subscription.trial_end is not None and subscription.trial_end > self.runtime._now()):
                expiry.append(min(max(ends), subscription.trial_end))
                selected.append(subscription.subscription_id)
        return max(expiry) if expiry else None, tuple(selected)

    def handle(self, raw_body: bytes, signature_header: str) -> BillingEventResult:
        event = self._verified(raw_body, signature_header)
        return self._process(event)

    def resume_event(self, event_id: str) -> BillingEventResult:
        """Host-only durable retry of a previously verified pending notification."""
        identifier(event_id, "event identity")
        with self.runtime._catalog.store() as store:
            row = self.runtime._catalog.read(store, BILLING_EVENT,
                (self.config.account_id, self.config.livemode, event_id))
            event = self._event_payload(row)
            if (event is None or event.get("api_version") != self.config.api_version
                    or event.get("account_id") != self.config.account_id
                    or event.get("livemode") is not self.config.livemode):
                raise ServiceRuntimeError("verified_event_not_found")
        return self._process({key: event[key] for key in (
            "id", "type", "api_version", "livemode", "account_id", "created", "data_digest",
            "event_digest", "body_digest", "customer_id")})

    def _process(self, event):
        try:
            prepared = self._begin(event)
        except ServiceCommitUnknown:
            return BillingEventResult(event["id"], "commit_unknown", None, diagnostic_code="commit_unknown")
        if isinstance(prepared, BillingEventResult):
            return prepared
        if self._resolver is None:
            return BillingEventResult(event["id"], PENDING, True, prepared["tenant_id"],
                                      diagnostic_code="subscription_resolver_unavailable")
        try:
            snapshot = self._resolver.resolve(event["customer_id"])
            if not isinstance(snapshot, StripeCustomerSubscriptionSnapshot) or snapshot.customer_id != event["customer_id"]:
                raise ServiceRuntimeError("billing_snapshot_unavailable")
            expiry, subscriptions = self._decision(snapshot)
        except Exception:
            return BillingEventResult(event["id"], PENDING, True, prepared["tenant_id"],
                                      diagnostic_code="subscription_reconciliation_unavailable")
        catalog = self.runtime._catalog
        row = {**prepared["event"], "record_version": uuid.uuid4().hex,
               "payload": {**prepared["event"]["payload"], "status": APPLIED,
                           "provider_snapshot_digest": snapshot.source_digest}}
        entitlement = {**prepared["entitlement"], "record_version": uuid.uuid4().hex,
            "payload": {"record_type": SCHEMAS[ENTITLEMENT], "tenant_id": prepared["tenant_id"],
                "enabled": expiry is not None, "entitlement": BODIES if expiry is not None else METADATA,
                "valid_until": expiry, "source": STRIPE_SNAPSHOT_SOURCE, "event_id": event["id"],
                "policy_digest": digest(asdict(self.policy)), "provider_snapshot_digest": snapshot.source_digest,
                "subscription_ids": list(subscriptions)}}
        try:
            with catalog.store(write=True) as store:
                catalog.commit(store, (row, entitlement), tuple(catalog.guard(prepared[key])
                    for key in ("event", "entitlement", "tenant", "customer", "policy")))
        except ServiceCommitUnknown:
            return BillingEventResult(event["id"], "commit_unknown", None, prepared["tenant_id"],
                                      diagnostic_code="commit_unknown")
        except ServiceRuntimeError as error:
            if error.code != "concurrent_update":
                raise
            return BillingEventResult(event["id"], PENDING, False, prepared["tenant_id"],
                                      diagnostic_code="concurrent_reconciliation")
        allowed = (expiry is not None and prepared["tenant"]["payload"].get("enabled") is True
                   and prepared["tenant"]["payload"].get("body_access_revoked") is False)
        return BillingEventResult(event["id"], APPLIED, True, prepared["tenant_id"], BODIES if allowed else METADATA)


def self_test():
    from .billing_checks import run_checks
    return run_checks()
