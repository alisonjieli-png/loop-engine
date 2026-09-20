"""Durable hosted-service domain and explicit external delivery adapters.

Records use the existing CatalogStore authority. HTTP and Model Context
Protocol transports consume this domain; this package creates no Loop runtime,
intelligence layer, billing source-of-truth clone, or managed-note bypass.
"""
from .records import (
    BillingCustomerBindingRequest, IssuedServiceKey, ServiceCommitUnknown,
    ServicePrincipal, ServiceRuntimeConfig, ServiceRuntimeError,
    SubjectBindingRequest, TenantKeyIssue, TenantRegistration,
)
from .runtime import ServiceRuntime
from .provisioning import DurableProvisioningBinding
from .billing import StripeEventProcessor
from .billing_records import (
    BillingEventResult, StripeCustomerSubscriptionSnapshot, StripeEntitlementPolicy,
    StripeProviderConfig, StripeSubscriptionResolver, StripeSubscriptionState,
    StripeWebhookConfig,
)
from .stripe_provider import StripeSubscriptionReader

__all__ = (
    "BillingCustomerBindingRequest", "IssuedServiceKey", "ServiceCommitUnknown",
    "ServicePrincipal", "ServiceRuntimeConfig", "ServiceRuntimeError",
    "SubjectBindingRequest", "TenantKeyIssue", "TenantRegistration",
    "ServiceRuntime", "DurableProvisioningBinding", "StripeEventProcessor",
    "BillingEventResult", "StripeCustomerSubscriptionSnapshot", "StripeEntitlementPolicy",
    "StripeProviderConfig", "StripeSubscriptionResolver", "StripeSubscriptionState",
    "StripeWebhookConfig", "StripeSubscriptionReader",
)
