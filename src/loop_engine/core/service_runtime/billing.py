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
    AUTOMATIC_COLLECTION, BillingEventResult, EVENT_TYPES, INVOICE_DRAFT, StripeCustomerSubscriptionSnapshot,
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
#: How long paid access outlasts the paid period while the renewal is settled. Stripe moves the period on at the
#: renewal moment, keeps the new invoice a draft for about an hour, and then charges the card; the events that
#: follow decide access (`invoice.paid` extends it, `invoice.payment_failed` and the past-due update end it). The
#: allowance only matters when those events are late: Stripe retries a webhook delivery for up to three days in live
#: mode (https://docs.stripe.com/webhooks#automatic-retries), so a paying customer never loses access because a
#: delivery was retried, and an account whose renewal events never arrive loses it three days after the period.
RENEWAL_GRACE_SECONDS = 3 * 86400
#: How many times one delivery starts when concurrent deliveries for the same account race. Stripe sends
#: `customer.subscription.created` and `invoice.paid` within the same second for every new subscription. In the Stripe
#: test journey of October 5, 2026 one of the pair was refused on every first payment, leaving a failed delivery for
#: Stripe to retry; on loopback the two raced in their first write in 5 of 6 trials, and the loser was answered 409.
BEGIN_ATTEMPTS = 3


def renewal_payment_pending(subscription):
    """True for an active subscription whose newest invoice is the renewal draft Stripe has not yet tried to charge.

    The period has already moved on, so the previous period was paid: a subscription whose earlier payment failed
    is past due, not active. Only automatic collection qualifies. A `send_invoice` subscription is active before its
    invoice is paid, so its draft says nothing about payment.
    """
    return (subscription.status == SUBSCRIPTION_ACTIVE and subscription.collection_method == AUTOMATIC_COLLECTION
            and subscription.latest_invoice_status == INVOICE_DRAFT and subscription.latest_invoice_created is not None)


def paid_access_until(subscription, policy, now):
    """The moment one subscription's paid access ends, or None when it grants none now.

    - Active with a paid newest invoice: the end of the paid period, plus the renewal allowance.
    - Active while the renewal invoice is still a draft: as long as the allowance from that invoice's creation, never
      past the period; the charge that follows decides the rest.
    - Trialing, only when the owner's policy allows trials: until the trial or the period ends.
    - Anything else, an unconfigured price, or paused collection: none.

    A cancellation the customer scheduled ends access at its own moment, with no allowance, because no renewal
    follows it. The terms of service promise access until the end of the paid month.
    """
    allowed = set(policy.allowed_price_ids)
    ends = [end for price, end in subscription.price_periods if price in allowed]
    if not ends or subscription.collection_paused:
        return None
    end = max(ends)
    if subscription.status == SUBSCRIPTION_ACTIVE and subscription.latest_invoice_paid is True:
        until = end + RENEWAL_GRACE_SECONDS
    elif renewal_payment_pending(subscription):
        until = min(end, subscription.latest_invoice_created + RENEWAL_GRACE_SECONDS)
    elif (subscription.status == SUBSCRIPTION_TRIALING and policy.allow_trialing is True
          and subscription.trial_end is not None):
        until = min(end, subscription.trial_end)
    else:
        return None
    if subscription.cancel_at is not None:
        until = min(until, subscription.cancel_at)
    return until if until > now else None


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
        now = self.runtime._now()
        expiry = []
        selected = []
        for subscription in snapshot.subscriptions:
            until = paid_access_until(subscription, self.policy, now)
            if until is not None:
                expiry.append(until)
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
        for attempt in range(BEGIN_ATTEMPTS):
            try:
                prepared = self._begin(event)
                break
            except ServiceCommitUnknown:
                return BillingEventResult(event["id"], "commit_unknown", None, diagnostic_code="commit_unknown")
            except ServiceRuntimeError as error:
                # Another delivery for the same account committed first and changed a record this one read. The
                # refused batch wrote nothing, so this delivery starts again from the records as they are now.
                if error.code != "concurrent_update" or attempt == BEGIN_ATTEMPTS - 1:
                    raise
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
