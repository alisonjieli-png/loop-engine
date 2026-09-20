"""Explicit read-only Stripe account reconciliation adapter.

This adapter can read the configured account and its current subscriptions.
It cannot create a customer, checkout, payment, price, or charge. Network and
secret access require explicit host configuration. Local injected transports
test the request/response contract without claiming live account integration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .billing_records import (
    StripeCustomerSubscriptionSnapshot, StripeProviderConfig, StripeSubscriptionResolver,
    StripeSubscriptionState,
)
from .records import ServiceRuntimeError, digest, identifier

STRIPE_ORIGIN = "https://api.stripe.com"
ACCOUNT_PATH = "/v1/account"
SUBSCRIPTIONS_PATH = "/v1/subscriptions"
INVOICE_PAID = "paid"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ServiceRuntimeError("stripe_redirect_refused")


@dataclass(frozen=True)
class StripeReadRequest:
    path: str
    query: tuple[tuple[str, str], ...]
    api_version: str
    timeout_seconds: float
    maximum_response_bytes: int


def _opener():
    """Direct connections only: the request carries the account's secret key.

    The default opener reads proxy settings from the process environment. The
    other provider clients in this package ignore them, and so must this one.
    """
    return build_opener(ProxyHandler({}), _NoRedirect())


def _read(request: StripeReadRequest, secret: str):
    if request.path not in (ACCOUNT_PATH, SUBSCRIPTIONS_PATH):
        raise ServiceRuntimeError("unsupported_stripe_operation")
    url = STRIPE_ORIGIN + request.path + ("?" + urlencode(request.query) if request.query else "")
    wire = Request(url, method="GET", headers={"Authorization": "Bearer " + secret,
        "Stripe-Version": request.api_version, "Accept": "application/json"})
    try:
        with _opener().open(wire, timeout=request.timeout_seconds) as response:
            if response.geturl().split("?", 1)[0] != STRIPE_ORIGIN + request.path:
                raise ServiceRuntimeError("stripe_redirect_refused")
            body = response.read(request.maximum_response_bytes + 1)
        if len(body) > request.maximum_response_bytes:
            raise ServiceRuntimeError("stripe_response_too_large")
        return json.loads(body.decode("utf-8"))
    except ServiceRuntimeError:
        raise
    except Exception:
        raise ServiceRuntimeError("stripe_provider_unavailable") from None


class StripeSubscriptionReader:
    """An installed resolver with exact account/API identity and bounded pagination."""

    def __init__(self, config: StripeProviderConfig, secret_resolver, *, transport=None):
        if not isinstance(config, StripeProviderConfig) or not callable(secret_resolver):
            raise ServiceRuntimeError("invalid_stripe_provider")
        if transport is not None and not callable(transport):
            raise ServiceRuntimeError("invalid_stripe_provider")
        self.config = config
        self._secrets = secret_resolver
        self._transport = transport if transport is not None else _read

    def as_resolver(self):
        return StripeSubscriptionResolver("stripe.account-subscriptions/v1", self.resolve)

    def _request(self, path, query, secret):
        try:
            value = self._transport(StripeReadRequest(path, tuple(query), self.config.api_version,
                self.config.timeout_seconds, self.config.maximum_response_bytes), secret)
        except Exception:
            raise ServiceRuntimeError("stripe_provider_unavailable") from None
        if not isinstance(value, dict):
            raise ServiceRuntimeError("invalid_stripe_response")
        return value

    def resolve(self, customer_id: str) -> StripeCustomerSubscriptionSnapshot:
        identifier(customer_id, "Stripe customer")
        if self.config.allow_network is not True:
            raise ServiceRuntimeError("stripe_network_authority_required")
        try:
            secret = self._secrets(self.config.api_key_ref)
        except Exception:
            raise ServiceRuntimeError("stripe_secret_unavailable") from None
        if not isinstance(secret, str) or not secret:
            raise ServiceRuntimeError("stripe_secret_unavailable")
        account = self._request(ACCOUNT_PATH, (), secret)
        if account.get("id") != self.config.account_id:
            raise ServiceRuntimeError("stripe_account_mismatch")
        pages, subscriptions, seen = [], [], set()
        cursor = ""
        for _page in range(self.config.maximum_pages):
            query = [("customer", customer_id), ("status", "all"), ("limit", "100"),
                     ("expand[]", "data.latest_invoice")]
            if cursor:
                query.append(("starting_after", cursor))
            page = self._request(SUBSCRIPTIONS_PATH, query, secret)
            if page.get("object") != "list" or not isinstance(page.get("data"), list) or type(page.get("has_more")) is not bool:
                raise ServiceRuntimeError("invalid_stripe_subscription_list")
            pages.append(page)
            for row in page["data"]:
                if (not isinstance(row, dict) or row.get("object") != "subscription"
                        or row.get("customer") != customer_id or row.get("livemode") is not self.config.livemode
                        or row.get("id") in seen):
                    raise ServiceRuntimeError("invalid_stripe_subscription")
                seen.add(row.get("id"))
                items = row.get("items")
                if (not isinstance(items, dict) or not isinstance(items.get("data"), list)
                        or items.get("has_more") is not False):
                    raise ServiceRuntimeError("incomplete_stripe_subscription_items")
                periods = []
                for item in items["data"]:
                    if not isinstance(item, dict) or not isinstance(item.get("price"), dict):
                        raise ServiceRuntimeError("invalid_stripe_subscription_item")
                    periods.append((item["price"].get("id"), item.get("current_period_end")))
                invoice = row.get("latest_invoice")
                paid = (invoice.get("paid") is True and invoice.get("status") == INVOICE_PAID
                        if isinstance(invoice, dict) else None)
                if isinstance(invoice, dict) and invoice.get("customer") != customer_id:
                    raise ServiceRuntimeError("invoice_customer_mismatch")
                subscriptions.append(StripeSubscriptionState(row.get("id"), customer_id,
                    row.get("status"), tuple(periods), paid, row.get("pause_collection") is not None,
                    row.get("trial_end")))
            if page["has_more"] is False:
                return StripeCustomerSubscriptionSnapshot(self.config.account_id, customer_id,
                    self.config.api_version, self.config.livemode, tuple(subscriptions), digest(pages))
            if not page["data"]:
                raise ServiceRuntimeError("incomplete_stripe_pagination")
            cursor = page["data"][-1]["id"]
        raise ServiceRuntimeError("stripe_pagination_allowance_exhausted")


def self_test():
    from .billing_checks import provider_checks
    return provider_checks()
