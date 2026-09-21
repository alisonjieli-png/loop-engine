"""Versioned Stripe snapshot, signature, and entitlement policy records.

Prices and accounts are host choices. A snapshot is resolved from the provider,
not inferred from checkout navigation or event delivery order. Raw payloads and
credentials are not persisted in these records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re

from .records import ServiceRuntimeError, identifier, text

WEBHOOK_VERSION = "stripe_webhook_configuration/v1"
POLICY_VERSION = "stripe_entitlement_policy/v1"
CUSTOMER_PROJECTION_VERSION = "stripe_customer_projection/v1"
CUSTOMER_OBJECT = "customer"
CUSTOMER_IDENTITY_PREFIX = "cus_"
# The provider metadata field that names the Loop Engine account. An operator
# reading the provider dashboard sees which account a customer belongs to, and
# the customer search before creation looks the account up by this field.
TENANT_METADATA_KEY = "loop_engine_tenant_id"
SNAPSHOT_VERSION = "stripe_customer_subscription_snapshot/v1"
RESOLVER_VERSION = "stripe_subscription_resolver/v1"
STRIPE_READ_PROVIDER_VERSION = "stripe_read_provider/v1"
EVENT_TYPES = ("customer.subscription.created", "customer.subscription.updated",
               "customer.subscription.deleted", "invoice.paid", "invoice.payment_failed")
SUBSCRIPTION_ACTIVE = "active"
SUBSCRIPTION_TRIALING = "trialing"
SUBSCRIPTION_STATES = ("incomplete", "incomplete_expired", SUBSCRIPTION_TRIALING,
                       SUBSCRIPTION_ACTIVE, "past_due", "canceled", "unpaid", "paused")


def secret_reference(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:env|secret):[A-Za-z0-9_./:-]+", value):
        raise ServiceRuntimeError("invalid_secret_reference", "only a host secret reference is accepted")


@dataclass(frozen=True)
class StripeWebhookConfig:
    account_id: str
    api_version: str
    signing_secret_refs: tuple[str, ...]
    livemode: bool = False
    tolerance_seconds: int = 300
    maximum_payload_bytes: int = 1_000_000
    record_type: str = WEBHOOK_VERSION

    def __post_init__(self):
        if self.record_type != WEBHOOK_VERSION:
            raise ServiceRuntimeError("unsupported_version")
        identifier(self.account_id, "Stripe account")
        text(self.api_version, "Stripe event API version")
        object.__setattr__(self, "signing_secret_refs", tuple(self.signing_secret_refs))
        if not self.signing_secret_refs:
            raise ServiceRuntimeError("signing_secret_required")
        for ref in self.signing_secret_refs:
            secret_reference(ref)
        if (type(self.livemode) is not bool or type(self.tolerance_seconds) is not int
                or self.tolerance_seconds <= 0 or type(self.maximum_payload_bytes) is not int
                or self.maximum_payload_bytes <= 0):
            raise ServiceRuntimeError("invalid_configuration")


@dataclass(frozen=True)
class StripeEntitlementPolicy:
    """Exact owner-supplied Price IDs; no invented amount or default paid plan."""

    allowed_price_ids: tuple[str, ...]
    allow_trialing: bool = False
    record_type: str = POLICY_VERSION

    def __post_init__(self):
        if self.record_type != POLICY_VERSION or type(self.allow_trialing) is not bool:
            raise ServiceRuntimeError("unsupported_billing_policy")
        object.__setattr__(self, "allowed_price_ids", tuple(self.allowed_price_ids))
        if len(set(self.allowed_price_ids)) != len(self.allowed_price_ids):
            raise ServiceRuntimeError("duplicate_price_identity")
        for price in self.allowed_price_ids:
            identifier(price, "Stripe Price")


@dataclass(frozen=True)
class StripeCustomerProjection:
    """One verified provider customer that a named account owns.

    The service holds no name, no postal address and no email address for an
    account, so a customer it creates carries only the account identifier in
    its metadata. This record refuses a provider customer that the account
    cannot own, including one from the other test or live mode, a deleted one,
    and one whose metadata names another account.
    """

    customer_id: str
    tenant_id: str
    livemode: bool
    record_type: str = CUSTOMER_PROJECTION_VERSION

    def __post_init__(self):
        if self.record_type != CUSTOMER_PROJECTION_VERSION or type(self.livemode) is not bool:
            raise ServiceRuntimeError("unsupported_stripe_customer_projection")
        identifier(self.customer_id, "billing customer identity")
        identifier(self.tenant_id, "tenant identity")
        if not self.customer_id.startswith(CUSTOMER_IDENTITY_PREFIX):
            raise ServiceRuntimeError("unsupported_stripe_customer_identity")

    @classmethod
    def from_provider(cls, value, *, tenant_id, livemode, metadata_key=TENANT_METADATA_KEY):
        identifier(metadata_key, "provider metadata key")
        identifier(tenant_id, "tenant identity")
        metadata = value.get("metadata") if isinstance(value, dict) else None
        if (not isinstance(value, dict) or value.get("object") != CUSTOMER_OBJECT
                or not isinstance(value.get("id"), str) or value.get("livemode") is not livemode
                or value.get("deleted", False) is not False or not isinstance(metadata, dict)
                or metadata.get(metadata_key) != tenant_id):
            raise ServiceRuntimeError("unverified_stripe_customer")
        return cls(value["id"], tenant_id, livemode)


@dataclass(frozen=True)
class StripeSubscriptionState:
    subscription_id: str
    customer_id: str
    status: str
    price_periods: tuple[tuple[str, int], ...]
    latest_invoice_paid: bool | None
    collection_paused: bool = False
    trial_end: int | None = None

    def __post_init__(self):
        identifier(self.subscription_id, "subscription identity")
        identifier(self.customer_id, "customer identity")
        if self.status not in SUBSCRIPTION_STATES or type(self.collection_paused) is not bool:
            raise ServiceRuntimeError("unsupported_subscription_state")
        if self.latest_invoice_paid is not None and type(self.latest_invoice_paid) is not bool:
            raise ServiceRuntimeError("invalid_invoice_state")
        object.__setattr__(self, "price_periods", tuple(tuple(row) for row in self.price_periods))
        for price, end in self.price_periods:
            identifier(price, "price identity")
            if type(end) is not int or end <= 0:
                raise ServiceRuntimeError("invalid_subscription_period")
        if self.trial_end is not None and (type(self.trial_end) is not int or self.trial_end <= 0):
            raise ServiceRuntimeError("invalid_trial_period")


@dataclass(frozen=True)
class StripeCustomerSubscriptionSnapshot:
    account_id: str
    customer_id: str
    api_version: str
    livemode: bool
    subscriptions: tuple[StripeSubscriptionState, ...]
    source_digest: str
    complete: bool = True
    record_type: str = SNAPSHOT_VERSION

    def __post_init__(self):
        if self.record_type != SNAPSHOT_VERSION or type(self.complete) is not bool or type(self.livemode) is not bool:
            raise ServiceRuntimeError("unsupported_snapshot")
        identifier(self.account_id, "snapshot account")
        identifier(self.customer_id, "snapshot customer")
        text(self.api_version, "snapshot API version")
        object.__setattr__(self, "subscriptions", tuple(self.subscriptions))
        if (not re.fullmatch(r"[0-9a-f]{64}", self.source_digest)
                or any(not isinstance(row, StripeSubscriptionState) or row.customer_id != self.customer_id
                       for row in self.subscriptions)
                or len({row.subscription_id for row in self.subscriptions}) != len(self.subscriptions)):
            raise ServiceRuntimeError("invalid_snapshot")


@dataclass(frozen=True)
class StripeSubscriptionResolver:
    resolver_id: str
    resolve: object = field(repr=False)
    record_type: str = RESOLVER_VERSION

    def __post_init__(self):
        if self.record_type != RESOLVER_VERSION or not callable(self.resolve):
            raise ServiceRuntimeError("unsupported_billing_resolver")
        text(self.resolver_id, "resolver identity")


@dataclass(frozen=True)
class StripeProviderConfig:
    """Read-only account API boundary; merely configuring a secret grants no network."""

    account_id: str
    api_version: str
    api_key_ref: str
    allow_network: bool = False
    livemode: bool = False
    maximum_pages: int = 10
    timeout_seconds: float = 10.0
    maximum_response_bytes: int = 2_000_000
    record_type: str = STRIPE_READ_PROVIDER_VERSION

    def __post_init__(self):
        if self.record_type != STRIPE_READ_PROVIDER_VERSION:
            raise ServiceRuntimeError("unsupported_version")
        identifier(self.account_id, "provider account")
        text(self.api_version, "provider API version")
        secret_reference(self.api_key_ref)
        if (type(self.allow_network) is not bool or type(self.livemode) is not bool
                or type(self.maximum_pages) is not int or self.maximum_pages <= 0
                or type(self.maximum_response_bytes) is not int or self.maximum_response_bytes <= 0
                or type(self.timeout_seconds) not in (int, float)
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0):
            raise ServiceRuntimeError("invalid_configuration")


@dataclass(frozen=True)
class BillingEventResult:
    event_id: str
    status: str
    committed: bool | None
    tenant_id: str = ""
    entitlement: str = "metadata"
    diagnostic_code: str = ""

    def to_dict(self):
        return {"record_type": "billing_event_result/v1", "event_id": self.event_id,
                "status": self.status, "committed": self.committed, "tenant_id": self.tenant_id,
                "entitlement": self.entitlement, "diagnostic_code": self.diagnostic_code}
