"""Explicit Stripe checkout and portal session creation, not payment acceptance.

The server chooses exact account, customer, Price and return-URL policy.
Network/session authority defaults off. Durable effect identities survive
uncertainty; sensitive provider URLs are returned only to the caller, not stored.

An account that asks for checkout and has no provider customer yet gets exactly
one, created here and bound before the session. The adapter searches the
provider for the account identifier first, so a customer that an earlier
uncertain attempt left behind is bound instead of duplicated.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import ipaddress
import json
import math
import time
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

from .billing_effects import (
    BillingSessionEffectSpec, BillingSessionEffectStore, BillingSessionPolicyDefinition,
    CHECKOUT_OPERATION, PORTAL_OPERATION, SESSION_OPERATIONS, PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS,
)
from .billing_records import (
    CUSTOMER_IDENTITY_PREFIX, CUSTOMER_OBJECT, TENANT_METADATA_KEY, StripeCustomerProjection, secret_reference,
)
from .records import (
    BILLING_MANAGE_SCOPE, BillingCustomerBindingRequest, BillingCustomerEffectSpec, ServiceCommitUnknown,
    ServiceRuntimeError, canonical, digest, identifier, text,
)
from .runtime import ServiceRuntime
from .stripe_provider import STRIPE_ORIGIN, ACCOUNT_PATH

SESSION_CONFIGURATION_VERSION = "stripe_session_configuration/v1"
SESSION_REQUEST_VERSION = "billing_session_request/v1"
SESSION_RESULT_VERSION = "billing_session_result/v1"
SESSION_OPTIONS_VERSION = "billing_session_options/v1"
SESSION_UNCERTAINTY_VERSION = "billing_session_uncertainty/v1"
CUSTOMER_RESULT_VERSION = "billing_customer_binding_result/v1"
CUSTOMER_UNCERTAINTY_VERSION = "billing_customer_uncertainty/v1"
CHECKOUT_PATH = "/v1/checkout/sessions"
PORTAL_PATH = "/v1/billing_portal/sessions"
CUSTOMER_PATH = "/v1/customers/"
CUSTOMER_COLLECTION_PATH = "/v1/customers"
CUSTOMER_SEARCH_PATH = "/v1/customers/search"
PRICE_PATH = "/v1/prices/"
SUBSCRIPTION_MODE = "subscription"
RECURRING_PRICE = "recurring"
PRICE_OBJECT = "price"
SEARCH_RESULT_OBJECT = "search_result"
CHECKOUT_OBJECT, PORTAL_OBJECT = "checkout.session", "billing_portal.session"
CHECKOUT_HOST, PORTAL_HOST = "checkout.stripe.com", "billing.stripe.com"
GET_METHOD, POST_METHOD = "GET", "POST"
OPEN_SESSION_STATUS = "open"
SEARCH_QUERY_PARAMETER, SEARCH_LIMIT_PARAMETER = "query", "limit"
SEARCH_PARAMETERS = frozenset({SEARCH_QUERY_PARAMETER, SEARCH_LIMIT_PARAMETER})
# Two results are enough to see that an account has more than one customer.
SEARCH_PAGE_LIMIT = "2"
CUSTOMER_METADATA_PARAMETER = "metadata[" + TENANT_METADATA_KEY + "]"
# Every supported provider mutation declares the exact parameter names it may
# carry. A customer this service creates therefore cannot carry an email
# address, a name or any other personal detail, because the service holds none.
POST_PARAMETERS = {
    CHECKOUT_PATH: frozenset({"customer", "mode", "line_items[0][price]", "line_items[0][quantity]",
                              "success_url", "cancel_url"}),
    PORTAL_PATH: frozenset({"customer", "configuration", "return_url"}),
    CUSTOMER_COLLECTION_PATH: frozenset({CUSTOMER_METADATA_PARAMETER}),
}
# Stripe may prune idempotency keys after at least 24 hours. This adapter's
# explicit ceiling reserves one hour of margin; it is not a provider limit.
MAXIMUM_RECONCILIATION_SECONDS = PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS - 3600


class BillingSessionError(ServiceRuntimeError):
    """A caller-safe effect status with no provider body, key or redirect URL."""

    def __init__(self, code, *, request_id="", reservation=None, attempted=False, status=503):
        super().__init__(code)
        self.status = status
        self.details = {"record_type": SESSION_UNCERTAINTY_VERSION, "request_id": request_id,
                        "effect_ref": reservation.record_id if reservation is not None else None,
                        "creation_attempted": attempted, "provider_commitment": "not_asserted",
                        "retry_same_request": reservation is not None,
                        "retry_before": reservation.retry_before if reservation is not None else None}


class BillingCustomerError(BillingSessionError):
    """A caller-safe customer-creation status; no session was created.

    It is a billing session refusal because the transport already reports that
    family with its own status and details. `diagnostic_code` carries the exact
    domain refusal, never a provider body, key or message.
    """

    def __init__(self, code, *, request_id="", reservation=None, attempted=False, reason="", status=503):
        super().__init__(code, request_id=request_id, reservation=reservation,
                         attempted=attempted, status=status)
        self.details = {**self.details, "record_type": CUSTOMER_UNCERTAINTY_VERSION,
                        "diagnostic_code": reason}


def _customer_search_query(metadata_key, tenant_id):
    """Build the provider search for one account's own customer.

    Both parts are checked as service identities first, so neither can carry a
    quotation mark, a backslash or a space into the provider query.
    """
    identifier(metadata_key, "provider metadata key")
    identifier(tenant_id, "tenant identity")
    return "metadata['" + metadata_key + "']:'" + tenant_id + "'"


def _return_url(value, permit_loopback):
    text(value, "return URL")
    parsed = urlsplit(value)
    local = parsed.hostname == "localhost"
    try:
        local = local or ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        pass
    if (not parsed.hostname or parsed.username or parsed.password or parsed.fragment
            or any(character.isspace() for character in value)
            or (parsed.scheme != "https" and not (permit_loopback and local and parsed.scheme == "http"))):
        raise ServiceRuntimeError("invalid_session_return_url")


@dataclass(frozen=True)
class StripeSessionPlan:
    plan_ref: str
    label: str
    price_id: str
    quantity: int = 1

    def __post_init__(self):
        identifier(self.plan_ref, "plan reference")
        text(self.label, "plan label")
        identifier(self.price_id, "Price identity")
        if not self.price_id.startswith("price_"):
            raise ServiceRuntimeError("unsupported_session_price_identity")
        if type(self.quantity) is not int or self.quantity < 1:
            raise ServiceRuntimeError("invalid_session_quantity")


@dataclass(frozen=True)
class StripeSessionConfiguration:
    account_id: str
    api_version: str
    api_key_ref: str = field(repr=False)
    plans: tuple[StripeSessionPlan, ...] = ()
    checkout_success_url: str = ""
    checkout_cancel_url: str = ""
    portal_return_url: str = ""
    portal_configuration_id: str = ""
    allow_network: bool = False
    allow_session_creation: bool = False
    livemode: bool = False
    allow_loopback_return_urls: bool = False
    timeout_seconds: float = 10.0
    maximum_response_bytes: int = 1_000_000
    reconciliation_seconds: int = 3600
    record_type: str = SESSION_CONFIGURATION_VERSION

    def __post_init__(self):
        if self.record_type != SESSION_CONFIGURATION_VERSION:
            raise ServiceRuntimeError("unsupported_session_configuration")
        identifier(self.account_id, "Stripe account")
        text(self.api_version, "Stripe API version")
        secret_reference(self.api_key_ref)
        if any(type(getattr(self, name)) is not bool for name in (
                "allow_network", "allow_session_creation", "livemode", "allow_loopback_return_urls")):
            raise ServiceRuntimeError("invalid_session_authority")
        plans = tuple(self.plans)
        if (any(not isinstance(plan, StripeSessionPlan) for plan in plans)
                or len({plan.plan_ref for plan in plans}) != len(plans)
                or len({plan.price_id for plan in plans}) != len(plans)):
            raise ServiceRuntimeError("invalid_session_plans")
        if plans:
            _return_url(self.checkout_success_url, self.allow_loopback_return_urls)
            _return_url(self.checkout_cancel_url, self.allow_loopback_return_urls)
        if self.portal_configuration_id:
            identifier(self.portal_configuration_id, "portal configuration")
            if not self.portal_configuration_id.startswith("bpc_"):
                raise ServiceRuntimeError("unsupported_portal_configuration")
            _return_url(self.portal_return_url, self.allow_loopback_return_urls)
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 60 or type(self.maximum_response_bytes) is not int
                or self.maximum_response_bytes <= 0 or type(self.reconciliation_seconds) is not int
                or not self.lease_seconds < self.reconciliation_seconds <= MAXIMUM_RECONCILIATION_SECONDS):
            raise ServiceRuntimeError("invalid_session_allowance")
        object.__setattr__(self, "plans", plans)

    @property
    def lease_seconds(self):
        return math.ceil(self.timeout_seconds * 4) + 5

    def policy_definition(self):
        return BillingSessionPolicyDefinition(canonical(asdict(self)), tuple(plan.price_id for plan in self.plans))


@dataclass(frozen=True)
class BillingSessionRequest:
    operation: str
    request_id: str
    policy_digest: str
    plan_ref: str = ""
    record_type: str = SESSION_REQUEST_VERSION

    def __post_init__(self):
        from .billing_effects import exact_digest
        if self.record_type != SESSION_REQUEST_VERSION or self.operation not in SESSION_OPERATIONS:
            raise ServiceRuntimeError("unsupported_session_request")
        identifier(self.request_id, "session request identity")
        exact_digest(self.policy_digest)
        if self.operation == CHECKOUT_OPERATION:
            identifier(self.plan_ref, "public plan reference")
        elif self.plan_ref:
            raise ServiceRuntimeError("portal_has_no_price_selection")

    @classmethod
    def from_dict(cls, value, operation):
        required = {"record_type", "request_id", "policy_digest"}
        if operation == CHECKOUT_OPERATION:
            required.add("plan_ref")
        if not isinstance(value, dict) or set(value) != required:
            raise ServiceRuntimeError("invalid_session_request_fields")
        return cls(operation=operation, **value)


@dataclass(frozen=True)
class StripeSessionWireRequest:
    method: str
    path: str
    parameters: tuple[tuple[str, str], ...]
    api_version: str
    idempotency_key: str = field(repr=False)
    timeout_seconds: float
    maximum_response_bytes: int

    def __post_init__(self):
        text(self.api_version, "Stripe API version")
        parameters = tuple(tuple(pair) for pair in self.parameters)
        if (any(len(pair) != 2 or any(not isinstance(value, str) for value in pair) for pair in parameters)
                or len({pair[0] for pair in parameters}) != len(parameters)):
            raise ServiceRuntimeError("invalid_session_wire_parameters")
        names = {pair[0] for pair in parameters}
        if self.method == GET_METHOD:
            search = self.path == CUSTOMER_SEARCH_PATH
            if self.idempotency_key or (self.parameters and not search):
                raise ServiceRuntimeError("invalid_session_read_operation")
            if search:
                if not names or not names <= SEARCH_PARAMETERS:
                    raise ServiceRuntimeError("unsupported_customer_search_parameters")
            elif self.path != ACCOUNT_PATH:
                prefix = next((prefix for prefix in (CUSTOMER_PATH, PRICE_PATH) if self.path.startswith(prefix)), None)
                if prefix is None:
                    raise ServiceRuntimeError("unsupported_stripe_session_operation")
                identifier(self.path[len(prefix):], "Stripe resource identity")
        elif self.method == POST_METHOD and self.path in POST_PARAMETERS:
            identifier(self.idempotency_key, "provider idempotency identity")
            if not names <= POST_PARAMETERS[self.path]:
                raise ServiceRuntimeError("unsupported_session_wire_parameters")
        else:
            raise ServiceRuntimeError("unsupported_stripe_session_operation")
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or self.timeout_seconds <= 0 or type(self.maximum_response_bytes) is not int
                or self.maximum_response_bytes <= 0):
            raise ServiceRuntimeError("invalid_session_wire_allowance")
        object.__setattr__(self, "parameters", parameters)


def _send(request: StripeSessionWireRequest, secret: str):
    import httpx
    if not isinstance(request, StripeSessionWireRequest):
        raise ServiceRuntimeError("invalid_stripe_session_wire_request")
    allowed = ((request.method == GET_METHOD and (request.path == ACCOUNT_PATH
        or request.path.startswith(CUSTOMER_PATH) or request.path.startswith(PRICE_PATH)))
        or (request.method == POST_METHOD and request.path in POST_PARAMETERS))
    if not allowed or "?" in request.path or "#" in request.path:
        raise ServiceRuntimeError("unsupported_stripe_session_operation")
    headers = {"Authorization": "Bearer " + secret, "Stripe-Version": request.api_version,
               "Accept": "application/json"}
    if request.method == POST_METHOD:
        headers.update({"Idempotency-Key": request.idempotency_key,
                        "Content-Type": "application/x-www-form-urlencoded"})
    data = urlencode(request.parameters).encode() if request.method == POST_METHOD else None
    query = urlencode(request.parameters) if request.method == GET_METHOD else ""
    target = STRIPE_ORIGIN + request.path + ("?" + query if query else "")
    chunks, size = [], 0
    with httpx.Client(timeout=request.timeout_seconds, follow_redirects=False, trust_env=False) as client:
        with client.stream(request.method, target, headers=headers, content=data) as response:
            response.raise_for_status()
            # A provider client may normalize percent-encoding, so the origin,
            # path and decoded query are compared instead of the exact text.
            observed, expected = urlsplit(str(response.url)), urlsplit(target)
            if (observed[:3] != expected[:3]
                    or [tuple(pair) for pair in parse_qsl(observed.query)] != [tuple(pair) for pair in parse_qsl(query)]):
                raise ServiceRuntimeError("stripe_redirect_refused")
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > request.maximum_response_bytes:
                    raise ServiceRuntimeError("stripe_response_too_large")
                chunks.append(chunk)
    from .billing import _json
    return _json(b"".join(chunks))


class StripeSessionAdapter:
    """Host-policy session creator; caller input supplies no provider authority."""

    def __init__(self, runtime: ServiceRuntime, configuration: StripeSessionConfiguration, secret_resolver, *, transport=None):
        if (not isinstance(runtime, ServiceRuntime) or not isinstance(configuration, StripeSessionConfiguration)
                or not callable(secret_resolver) or (transport is not None and not callable(transport))):
            raise ServiceRuntimeError("invalid_session_adapter")
        self.runtime, self.configuration = runtime, configuration
        self.effects = BillingSessionEffectStore(runtime)
        self._secrets = secret_resolver
        self._transport = transport or _send
        self.transport_basis = "injected_transport" if transport is not None else "stripe_https"

    @property
    def policy_digest(self):
        return self.configuration.policy_definition().digest

    def configure_policy(self, *, expected_version=None):
        return self.effects.configure_policy(self.configuration.policy_definition(), expected_version=expected_version)

    def _binding(self, principal):
        """Return the durable provider binding, or None when the account has none yet."""
        try:
            return self.runtime.billing_customer_for(principal)
        except ServiceRuntimeError as error:
            if error.code != "billing_customer_not_bound":
                raise
            return None

    def options(self, principal=None):
        reason, bound = "", None
        try:
            self.effects.policy_available(self.policy_digest)
            if principal is not None:
                bound = self._binding(principal)
                if bound is not None and bound["provider_account_id"] != self.configuration.account_id:
                    raise ServiceRuntimeError("stripe_account_mismatch")
        except ServiceRuntimeError as error:
            reason = error.code
        if not self.runtime.config.writes_authorized:
            reason = "host_write_authority_required"
        enabled = not reason and self.configuration.allow_network and self.configuration.allow_session_creation
        # Checkout stays available for an account with no provider customer,
        # because checkout creates exactly one for it. The portal needs an
        # existing customer, so it stays unavailable until one is bound.
        return {"record_type": SESSION_OPTIONS_VERSION, "policy_digest": self.policy_digest,
                "checkout_available": bool(enabled and self.configuration.plans),
                "portal_available": bool(enabled and self.configuration.portal_configuration_id
                                         and (principal is None or bound is not None)),
                "plans": [{"plan_ref": plan.plan_ref, "label": plan.label} for plan in self.configuration.plans],
                "unavailable_reason": reason or ("session_network_not_authorized" if not enabled else ""),
                "payment_confirmation_source": "verified_subscription_state", "provider_qualified": False}

    def _authorize(self, principal, expires_at):
        if expires_at is not None and (type(expires_at) not in (int, float)
                or not math.isfinite(expires_at) or expires_at <= time.time()):
            raise ServiceRuntimeError("session_authorization_expired")
        current = self.runtime.revalidate(principal)
        if BILLING_MANAGE_SCOPE not in current.scopes:
            raise ServiceRuntimeError("scope_required")
        return current

    def _call(self, method, path, secret, *, parameters=(), idempotency_key=""):
        request = StripeSessionWireRequest(method, path, tuple(parameters), self.configuration.api_version,
            idempotency_key, self.configuration.timeout_seconds, self.configuration.maximum_response_bytes)
        value = self._transport(request, secret)
        if not isinstance(value, dict):
            raise ServiceRuntimeError("invalid_stripe_session_response")
        return value

    def _verified_account(self, secret):
        """Refuse before any effect when the credential reaches another account."""
        account = self._call(GET_METHOD, ACCOUNT_PATH, secret)
        if account.get("id") != self.configuration.account_id:
            raise ServiceRuntimeError("stripe_account_mismatch")
        return account

    def _customer_creation_parameters(self, tenant_id):
        """The complete provider form for a created customer.

        It carries the account identifier and nothing else. The service holds
        no name, postal address or email address, so it invents none.
        """
        identifier(tenant_id, "tenant identity")
        return ((CUSTOMER_METADATA_PARAMETER, tenant_id),)

    def _search_customer(self, tenant_id, secret):
        """Find a customer already created for this account, or None.

        An earlier attempt whose answer was lost may have left one behind. The
        provider search by the account identifier finds it, so the account is
        bound to that customer instead of getting a second one.
        """
        response = self._call(GET_METHOD, CUSTOMER_SEARCH_PATH, secret, parameters=(
            (SEARCH_QUERY_PARAMETER, _customer_search_query(TENANT_METADATA_KEY, tenant_id)),
            (SEARCH_LIMIT_PARAMETER, SEARCH_PAGE_LIMIT)))
        if (response.get("object") != SEARCH_RESULT_OBJECT or not isinstance(response.get("data"), list)
                or type(response.get("has_more")) is not bool):
            raise ServiceRuntimeError("invalid_customer_search_response")
        found = [StripeCustomerProjection.from_provider(row, tenant_id=tenant_id,
                                                        livemode=self.configuration.livemode)
                 for row in response["data"]]
        if len(found) > 1 or (found and response["has_more"] is True):
            raise ServiceRuntimeError("ambiguous_billing_customer_at_provider")
        return found[0] if found else None

    def ensure_customer(self, principal, *, authorization_expires_at=None):
        """Create exactly one provider customer for this account and bind it.

        The reservation holds the durable idempotency identity, so an uncertain
        answer is reconciled under the same identity rather than repeated. The
        search before creation covers the case where that identity can no
        longer reconcile, such as a repeat after the provider stopped keeping
        the key. A second caller is refused while a creation is running.
        """
        config = self.configuration
        current = self._authorize(principal, authorization_expires_at)
        if config.allow_network is not True or config.allow_session_creation is not True:
            raise ServiceRuntimeError("session_network_authority_required")
        self.effects.policy_available(self.policy_digest)
        spec = BillingCustomerEffectSpec(current.tenant_id, config.account_id, TENANT_METADATA_KEY)
        try:
            reservation = self.runtime.begin_billing_customer(current, spec, lease_seconds=config.lease_seconds,
                                                              reconciliation_seconds=config.reconciliation_seconds)
        except ServiceRuntimeError as error:
            if error.code == "billing_customer_already_bound":
                return {"record_type": CUSTOMER_RESULT_VERSION, "tenant_id": current.tenant_id,
                        "provider_account_id": config.account_id, "status": "already_bound",
                        "provider_customer_id": "", "transport_basis": self.transport_basis}
            if error.code == "billing_customer_creation_in_progress":
                raise BillingCustomerError(error.code, reason=error.code, status=503) from None
            raise
        attempted, found = False, None
        try:
            secret = self._secrets(config.api_key_ref)
            if not isinstance(secret, str) or not secret:
                raise ServiceRuntimeError("stripe_secret_unavailable")
            self._authorize(current, authorization_expires_at)
            self._verified_account(secret)
            found = self._search_customer(current.tenant_id, secret)
            if found is None:
                self._authorize(current, authorization_expires_at)
                self.runtime.authorize_billing_customer_dispatch(current, reservation)
                attempted = True
                response = self._call(POST_METHOD, CUSTOMER_COLLECTION_PATH, secret,
                    parameters=self._customer_creation_parameters(current.tenant_id),
                    idempotency_key=reservation.idempotency_key)
                found = StripeCustomerProjection.from_provider(response, tenant_id=current.tenant_id,
                                                               livemode=config.livemode)
            self.runtime.bind_billing_customer(BillingCustomerBindingRequest(
                current.tenant_id, found.customer_id, config.account_id), reservation=reservation)
        except Exception as error:
            reason = error.code if isinstance(error, ServiceRuntimeError) else ""
            try:
                self.runtime.finish_billing_customer(reservation, attempted=attempted,
                    diagnostic_code=reason or ("provider_commit_unknown" if attempted else "not_dispatched"))
            except Exception:
                pass  # The durable reservation still preserves the same reconciliation identity.
            code = "billing_customer_uncertain" if attempted else "billing_customer_not_created"
            raise BillingCustomerError(code, reservation=reservation, attempted=attempted, reason=reason) from None
        return {"record_type": CUSTOMER_RESULT_VERSION, "tenant_id": current.tenant_id,
                "provider_account_id": config.account_id, "provider_customer_id": found.customer_id,
                "status": "created" if attempted else "reconciled", "transport_basis": self.transport_basis}

    def _bound_customer(self, current, authorization_expires_at):
        """Resolve the account's provider customer, creating the one it may have."""
        bound = self._binding(current)
        if bound is not None:
            return bound
        try:
            self.ensure_customer(current, authorization_expires_at=authorization_expires_at)
        except ServiceRuntimeError:
            # Another writer may have bound this account while the request ran,
            # including a write whose acknowledgment was lost. A refusal is
            # reported only when the account really has no customer.
            bound = self._binding(current)
            if bound is None:
                raise
            return bound
        return self.runtime.billing_customer_for(current)

    def create(self, principal, request: BillingSessionRequest, *, authorization_expires_at=None):
        if not isinstance(request, BillingSessionRequest):
            raise ServiceRuntimeError("invalid_session_request")
        config = self.configuration
        current = self._authorize(principal, authorization_expires_at)
        if request.policy_digest != self.policy_digest:
            raise ServiceRuntimeError("session_selection_changed")
        if config.allow_network is not True or config.allow_session_creation is not True:
            raise ServiceRuntimeError("session_network_authority_required")
        self.effects.policy_available(self.policy_digest)
        # Checkout creates the account's one provider customer when it has
        # none. The portal needs an existing customer and never creates one.
        customer = (self._bound_customer(current, authorization_expires_at)
                    if request.operation == CHECKOUT_OPERATION else self.runtime.billing_customer_for(current))
        if (customer["provider_account_id"] != config.account_id
                or not customer["provider_customer_id"].startswith(CUSTOMER_IDENTITY_PREFIX)):
            raise ServiceRuntimeError("stripe_account_or_customer_mismatch")
        customer_id = customer["provider_customer_id"]
        price_id = ""
        if request.operation == CHECKOUT_OPERATION:
            selected = next((plan for plan in config.plans if plan.plan_ref == request.plan_ref), None)
            if selected is None:
                raise ServiceRuntimeError("unknown_session_plan")
            price_id = selected.price_id
            parameters = (("customer", customer_id), ("mode", SUBSCRIPTION_MODE),
                ("line_items[0][price]", price_id), ("line_items[0][quantity]", str(selected.quantity)),
                ("success_url", config.checkout_success_url), ("cancel_url", config.checkout_cancel_url))
            path = CHECKOUT_PATH
        else:
            if not config.portal_configuration_id:
                raise ServiceRuntimeError("portal_not_configured")
            parameters = (("customer", customer_id), ("configuration", config.portal_configuration_id),
                          ("return_url", config.portal_return_url))
            path = PORTAL_PATH
        spec = BillingSessionEffectSpec(current.tenant_id, request.request_id, request.operation,
            config.account_id, customer_id, self.policy_digest, digest({"path": path, "parameters": parameters}))
        reservation = self.effects.begin(current, spec, lease_seconds=config.lease_seconds,
                                         reconciliation_seconds=config.reconciliation_seconds)
        attempted = False
        try:
            secret = self._secrets(config.api_key_ref)
            if not isinstance(secret, str) or not secret:
                raise ServiceRuntimeError("stripe_secret_unavailable")
            self._authorize(current, authorization_expires_at)
            self._verified_account(secret)
            observed_customer = self._call(GET_METHOD, CUSTOMER_PATH + quote(customer_id, safe=""), secret)
            if (observed_customer.get("object") != CUSTOMER_OBJECT or observed_customer.get("id") != customer_id
                    or observed_customer.get("livemode") is not config.livemode or observed_customer.get("deleted", False) is not False):
                raise ServiceRuntimeError("stripe_customer_or_mode_mismatch")
            if price_id:
                price = self._call(GET_METHOD, PRICE_PATH + quote(price_id, safe=""), secret)
                if (price.get("object") != PRICE_OBJECT or price.get("id") != price_id
                        or price.get("livemode") is not config.livemode or price.get("active") is not True
                        or price.get("type") != RECURRING_PRICE):
                    raise ServiceRuntimeError("stripe_price_or_mode_mismatch")
            self._authorize(current, authorization_expires_at)
            self.effects.authorize_dispatch(current, reservation)
            attempted = True
            response = self._call(POST_METHOD, path, secret, parameters=parameters,
                                  idempotency_key=reservation.idempotency_key)
            expected_object = CHECKOUT_OBJECT if request.operation == CHECKOUT_OPERATION else PORTAL_OBJECT
            expected_host = CHECKOUT_HOST if request.operation == CHECKOUT_OPERATION else PORTAL_HOST
            redirect_url = response.get("url", "")
            text(redirect_url, "provider redirect URL")
            location = urlsplit(redirect_url)
            if (response.get("object") != expected_object or response.get("customer") != customer_id
                    or response.get("livemode") is not config.livemode or location.scheme != "https"
                    or location.hostname != expected_host or location.username or location.password
                    or location.port not in (None, 443)
                    or any(character.isspace() for character in redirect_url)):
                raise ServiceRuntimeError("unverified_session_response")
            identifier(response.get("id"), "provider session")
            if request.operation == CHECKOUT_OPERATION:
                if (response.get("mode") != SUBSCRIPTION_MODE or response.get("success_url") != config.checkout_success_url
                        or response.get("cancel_url") != config.checkout_cancel_url
                        or response.get("status") != OPEN_SESSION_STATUS
                        or type(response.get("expires_at")) is not int or response["expires_at"] <= time.time()):
                    raise ServiceRuntimeError("session_response_policy_mismatch")
            elif (response.get("configuration") != config.portal_configuration_id
                  or response.get("return_url") != config.portal_return_url):
                raise ServiceRuntimeError("session_response_policy_mismatch")
            confirmed = self.effects.finish(reservation, provider_session_id=response["id"], response_digest=digest(response))
        except Exception as error:
            try:
                self.effects.finish(reservation, diagnostic_code="provider_commit_unknown" if attempted else "not_dispatched",
                                    attempted=attempted)
            except Exception:
                pass  # The durable reservation still preserves the same reconciliation identity.
            code = "billing_session_uncertain" if attempted else "billing_session_not_dispatched"
            raise BillingSessionError(code, request_id=request.request_id, reservation=reservation, attempted=attempted) from None
        try:
            self._authorize(current, authorization_expires_at)
        except ServiceRuntimeError:
            raise BillingSessionError("billing_session_authority_expired_after_dispatch", request_id=request.request_id,
                                      reservation=reservation, attempted=True, status=401) from None
        return {"record_type": SESSION_RESULT_VERSION, "operation": request.operation,
                "request_id": request.request_id, "effect_ref": confirmed["effect_ref"],
                "status": "reconciled" if reservation.attempt_number > 1 else "created",
                "provider_session_id": response["id"], "redirect_url": response["url"],
                "payment_confirmed": False, "entitlement_changed": False, "transport_basis": self.transport_basis}


def self_test():
    from .stripe_session_checks import run_checks
    return run_checks()
