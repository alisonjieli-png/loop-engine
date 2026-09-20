"""Local contract checks for exact checkout and portal effects.

The provider is an explicit injected transport with Stripe-shaped records.
Real temporary catalogue transactions are exercised, but no Stripe account,
customer, price, session, subscription or charge is created remotely.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace

from .billing_effects import (
    BillingSessionEffectSpec, SESSION_EFFECT_KIND, SESSION_POLICY_KIND, EFFECT_UNKNOWN, EFFECT_CONFIRMED,
)
from .billing_records import StripeEntitlementPolicy
from .records import (
    BILLING_MANAGE_SCOPE, DEFAULT_SCOPES, BillingCustomerBindingRequest, ServiceRuntimeConfig, ServiceRuntimeError,
    TenantKeyIssue, TenantRegistration,
)
from .runtime import ServiceRuntime
from .stripe_sessions import (
    ACCOUNT_PATH, CHECKOUT_OPERATION, CHECKOUT_PATH, CUSTOMER_PATH, GET_METHOD, PORTAL_OPERATION,
    PORTAL_PATH, POST_METHOD, PRICE_PATH, BillingSessionError, BillingSessionRequest,
    StripeSessionAdapter, StripeSessionConfiguration, StripeSessionPlan,
)

FIXTURE_SECRET = "LOCAL_SESSION_ADAPTER_SECRET"
FIXTURE_URL_TOKEN = "LOCAL_PORTAL_CAPABILITY_TOKEN"


class LocalStripeSessionTransport:
    def __init__(self):
        self.calls, self.effects = [], {}
        self.lose_next_response = False
        self.after_read = None
        self.override_customer = None
        self.override_account = None
        self.override_price = None
        self.override_result = None
        self.after_post = None

    def __call__(self, request, secret):
        if secret != FIXTURE_SECRET:
            raise AssertionError("wrong fixture credential")
        self.calls.append(request)
        if request.method == GET_METHOD:
            if request.path == ACCOUNT_PATH:
                result = self.override_account or {"id": "acct_fixture", "object": "account"}
            elif request.path.startswith(CUSTOMER_PATH):
                result = self.override_customer or {"id": request.path[len(CUSTOMER_PATH):], "object": "customer", "livemode": False}
            elif request.path.startswith(PRICE_PATH):
                result = self.override_price or {"id": request.path[len(PRICE_PATH):], "object": "price",
                                                "type": "recurring", "active": True, "livemode": False}
            else:
                raise AssertionError("unexpected provider path")
            if self.after_read is not None:
                self.after_read(request)
            return result
        if request.method != POST_METHOD or request.path not in (CHECKOUT_PATH, PORTAL_PATH):
            raise AssertionError("unexpected provider mutation")
        parameters = dict(request.parameters)
        existing = self.effects.get(request.idempotency_key)
        if existing is not None:
            if existing[0] != (request.path, request.parameters):
                raise RuntimeError("provider idempotency conflict")
            result = existing[1]
        else:
            result = {"id": ("cs_fixture_" if request.path == CHECKOUT_PATH else "bps_fixture_") + str(len(self.effects) + 1),
                      "object": "checkout.session" if request.path == CHECKOUT_PATH else "billing_portal.session",
                      "customer": parameters["customer"], "livemode": False, "created": int(time.time()),
                      "status": "open", "expires_at": int(time.time()) + 3600,
                      "url": ("https://checkout.stripe.com/c/pay/local_fixture#provider_fragment" if request.path == CHECKOUT_PATH
                              else "https://billing.stripe.com/p/session?secret=" + FIXTURE_URL_TOKEN),
                      **{key: value for key, value in parameters.items() if key in (
                          "mode", "success_url", "cancel_url", "configuration", "return_url")}}
            self.effects[request.idempotency_key] = ((request.path, request.parameters), result)
        if self.lose_next_response:
            self.lose_next_response = False
            raise TimeoutError("connection lost after creation " + FIXTURE_SECRET)
        if self.after_post is not None:
            self.after_post(request)
        return self.override_result or dict(result)


def fixture(root):
    clock = {"now": int(time.time())}
    configuration = ServiceRuntimeConfig(str(Path(root) / "service.db"), writes_authorized=True)
    runtime = ServiceRuntime(configuration, clock=lambda: clock["now"])
    keys = {}
    for tenant in ("alpha", "beta"):
        runtime.register_tenant(TenantRegistration(tenant, "tenant:" + tenant,
                                                  scopes=(*DEFAULT_SCOPES, BILLING_MANAGE_SCOPE)))
        keys[tenant] = runtime.issue_key(TenantKeyIssue(tenant, "local billing acceptance"))
        runtime.bind_billing_customer(BillingCustomerBindingRequest(tenant, "cus_" + tenant, "acct_fixture"))
    runtime.configure_billing_policy(StripeEntitlementPolicy(("price_basic", "price_other")))
    policy = StripeSessionConfiguration("acct_fixture", "fixture_version", "env:LOCAL_STRIPE_SESSION",
        plans=(StripeSessionPlan("basic", "Basic service", "price_basic"), StripeSessionPlan("other", "Other service", "price_other")),
        checkout_success_url="https://app.example/billing/success", checkout_cancel_url="https://app.example/billing/cancel",
        portal_return_url="https://app.example/account", portal_configuration_id="bpc_fixture",
        allow_network=True, allow_session_creation=True)
    provider = LocalStripeSessionTransport()
    secret_calls = []
    def secret(reference):
        secret_calls.append(reference)
        return FIXTURE_SECRET
    adapter = StripeSessionAdapter(runtime, policy, secret, transport=provider)
    installation = adapter.configure_policy()
    return SimpleNamespace(runtime=runtime, config=configuration, clock=clock, keys=keys, adapter=adapter,
                           policy=policy, provider=provider, secret_calls=secret_calls, installation=installation,
                           secret=secret)


def request(held, identity, *, operation=CHECKOUT_OPERATION, plan="basic"):
    return BillingSessionRequest(operation, identity, held.adapter.policy_digest,
                                 plan if operation == CHECKOUT_OPERATION else "")


def principal(held, tenant="alpha"):
    return held.runtime.authenticate_key(held.keys[tenant].key)


def rows(held):
    with held.runtime._catalog.store() as store:
        return held.runtime._catalog.rows(store, SESSION_EFFECT_KIND, "alpha")


def refused(function, code=None):
    try:
        function()
    except ServiceRuntimeError as error:
        return code is None or error.code == code
    return False


def observed_result(function):
    """Retain an unexpected domain refusal as a failed positive assertion."""
    try:
        return function()
    except ServiceRuntimeError as error:
        return {"unexpected_refusal": error.code}


def run_domain_checks(check):
    with tempfile.TemporaryDirectory(prefix="stripe-session-positive-") as root:
        held = fixture(root)
        result = held.adapter.create(principal(held), request(held, "checkout-one"))
        posted = [call for call in held.provider.calls if call.method == POST_METHOD][0]
        parameters = dict(posted.parameters)
        check("checkout_uses_only_server_bound_account_customer_price_and_return_policy",
              result["provider_session_id"] == "cs_fixture_1" and parameters["customer"] == "cus_alpha"
              and parameters["line_items[0][price]"] == "price_basic" and parameters["line_items[0][quantity]"] == "1"
              and parameters["success_url"] == held.policy.checkout_success_url and parameters["mode"] == "subscription")
        check("session_creation_never_confirms_payment_or_changes_entitlement",
              result["payment_confirmed"] is False and result["entitlement_changed"] is False
              and principal(held).entitlement == "metadata" and result["transport_basis"] == "injected_transport")
        repeat = observed_result(lambda: held.adapter.create(principal(held), request(held, "checkout-one")))
        check("same_request_reconciles_the_same_provider_idempotency_identity",
              repeat.get("status") == "reconciled" and repeat.get("provider_session_id") == result["provider_session_id"]
              and len(held.provider.effects) == 1)
        check("changed_plan_cannot_reuse_an_existing_effect_request_identity",
              refused(lambda: held.adapter.create(principal(held), request(held, "checkout-one", plan="other")),
                      "session_request_identity_conflict") and len(held.provider.effects) == 1)
        portal = held.adapter.create(principal(held), request(held, "portal-one", operation=PORTAL_OPERATION))
        check("portal_uses_exact_server_configuration_and_customer",
              portal["provider_session_id"] == "bps_fixture_2"
              and dict(held.provider.calls[-1].parameters) == {"customer": "cus_alpha", "configuration": "bpc_fixture",
                                                             "return_url": held.policy.portal_return_url})
        stored = json.dumps(rows(held))
        check("credentials_and_ephemeral_portal_URLs_are_not_persisted_in_effect_records",
              FIXTURE_SECRET not in stored and FIXTURE_URL_TOKEN not in stored
              and portal["redirect_url"] not in stored and "provider_session_id" in stored)
        before = len(held.provider.calls)
        held.clock["now"] += held.policy.reconciliation_seconds + 1
        check("an_expired_reconciliation_window_cannot_silently_create_a_new_provider_effect",
              refused(lambda: held.adapter.create(principal(held), request(held, "checkout-one")),
                      "session_reconciliation_window_exhausted") and len(held.provider.calls) == before)

    with tempfile.TemporaryDirectory(prefix="stripe-session-authority-") as root:
        held = fixture(root)
        for field in ("allow_network", "allow_session_creation"):
            denied = StripeSessionAdapter(held.runtime, replace(held.policy, **{field: False}), held.secret, transport=held.provider)
            body = BillingSessionRequest(CHECKOUT_OPERATION, field, denied.policy_digest, "basic")
            check(field + "_is_required_before_secret_resolution_or_provider_work",
                  refused(lambda: denied.create(principal(held), body), "session_network_authority_required")
                  and not held.secret_calls and not held.provider.calls and not rows(held))
        limited = held.runtime.issue_key(TenantKeyIssue("alpha", "metadata", scopes=DEFAULT_SCOPES))
        check("billing_management_is_an_explicit_scope_not_a_new_default_key_privilege",
              BILLING_MANAGE_SCOPE not in DEFAULT_SCOPES
              and refused(lambda: held.adapter.create(held.runtime.authenticate_key(limited.key), request(held, "no-scope")), "scope_required")
              and not held.provider.calls)
        fields = {"record_type": "billing_session_request/v1", "request_id": "injected", "policy_digest": held.adapter.policy_digest,
                  "plan_ref": "basic"}
        check("caller_wire_data_cannot_supply_price_customer_tenant_or_return_URL_authority",
              all(refused(lambda field=field: BillingSessionRequest.from_dict({**fields, field: "untrusted"}, CHECKOUT_OPERATION))
                  for field in ("price_id", "customer_id", "tenant_id", "return_url", "allow_network")))
        check("stale_plan_policy_and_unknown_plan_refuse_before_provider_work",
              refused(lambda: held.adapter.create(principal(held), replace(request(held, "stale"), policy_digest="0" * 64)),
                      "session_selection_changed")
              and refused(lambda: held.adapter.create(principal(held), request(held, "unknown", plan="unconfigured")), "unknown_session_plan")
              and not held.provider.calls)

    with tempfile.TemporaryDirectory(prefix="stripe-session-preflight-") as root:
        held = fixture(root)
        held.provider.override_account = {"id": "acct_unbound", "object": "account"}
        check("different_provider_account_refuses_before_customer_or_session_work",
              refused(lambda: held.adapter.create(principal(held), request(held, "wrong-account")), "billing_session_not_dispatched")
              and len(held.provider.calls) == 1 and not held.provider.effects)
        held.provider.override_account = None
        held.provider.override_customer = {"object": "customer", "id": "cus_alpha", "livemode": True}
        check("customer_and_key_mode_mismatch_refuses_before_the_creation_POST",
              refused(lambda: held.adapter.create(principal(held), request(held, "wrong-mode")), "billing_session_not_dispatched")
              and not held.provider.effects and all(row["payload"]["status"] == "not_attempted" for row in rows(held)))
        held.provider.override_customer = None
        held.provider.override_price = {"object": "price", "id": "price_basic", "livemode": False, "active": False, "type": "recurring"}
        check("inactive_or_unverified_price_cannot_reach_session_creation",
              refused(lambda: held.adapter.create(principal(held), request(held, "inactive-price")), "billing_session_not_dispatched")
              and not held.provider.effects)
        held.provider.override_price = None
        held.provider.after_read = lambda call: held.runtime.revoke_key("alpha", held.keys["alpha"].key_id) \
            if call.path.startswith(PRICE_PATH) else None
        issued = principal(held)
        check("revocation_during_preflight_refuses_before_creation",
              refused(lambda: held.adapter.create(issued, request(held, "revoked")), "billing_session_not_dispatched")
              and not held.provider.effects)

    with tempfile.TemporaryDirectory(prefix="stripe-session-unknown-") as root:
        held = fixture(root)
        held.provider.lose_next_response = True
        check("lost_provider_response_preserves_unknown_effect_and_does_not_retry_automatically",
              refused(lambda: held.adapter.create(principal(held), request(held, "uncertain")), "billing_session_uncertain")
              and len(held.provider.effects) == 1 and rows(held)[0]["payload"]["status"] == EFFECT_UNKNOWN
              and sum(call.method == POST_METHOD for call in held.provider.calls) == 1)
        reopened = ServiceRuntime(held.config, clock=lambda: held.clock["now"])
        adapter = StripeSessionAdapter(reopened, held.policy, held.secret, transport=held.provider)
        recovered = observed_result(lambda: adapter.create(reopened.authenticate_key(held.keys["alpha"].key), request(held, "uncertain")))
        check("restart_reconciles_the_original_key_without_a_second_provider_creation",
              recovered.get("status") == "reconciled" and len(held.provider.effects) == 1
              and rows(held)[0]["payload"]["status"] == EFFECT_CONFIRMED)

    with tempfile.TemporaryDirectory(prefix="stripe-session-concurrent-") as root:
        held = fixture(root)
        entered, release = threading.Event(), threading.Event()
        held.provider.after_read = lambda call: (entered.set(), release.wait(2)) if call.path == ACCOUNT_PATH else None
        current = principal(held)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(held.adapter.create, current, request(held, "concurrent"))
            entered.wait(1)
            try:
                blocked = refused(lambda: held.adapter.create(current, request(held, "concurrent")), "session_operation_in_progress")
            finally:
                release.set()
            result = first.result(timeout=3)
        check("concurrent_same_identity_attempts_do_not_dispatch_duplicate_creations",
              blocked and result["provider_session_id"] == "cs_fixture_1" and len(held.provider.effects) == 1
              and sum(call.method == POST_METHOD for call in held.provider.calls) == 1)

    with tempfile.TemporaryDirectory(prefix="stripe-session-reservation-") as root:
        held = fixture(root)
        spec = BillingSessionEffectSpec("alpha", "guarded", CHECKOUT_OPERATION, "acct_fixture", "cus_alpha",
                                        held.adapter.policy_digest, "a" * 64)
        reserved = held.adapter.effects.begin(principal(held), spec, lease_seconds=20, reconciliation_seconds=100)
        check("an_issued_reservation_cannot_drop_its_authority_guards",
              refused(lambda: held.adapter.effects.authorize_dispatch(principal(held), replace(reserved, authority_guards=())),
                      "unissued_session_reservation"))
        held.runtime.configure_billing_policy(StripeEntitlementPolicy(("price_basic",)),
            expected_version=next(guard.record_version for guard in reserved.authority_guards
                if guard.record_id == held.runtime._catalog.identity("service_billing_policy", "stripe")))
        check("a_changed_financial_policy_invalidates_an_inflight_session_reservation",
              refused(lambda: held.adapter.effects.authorize_dispatch(principal(held), reserved), "session_authority_changed"))


def run_checks():
    tests = []
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed), "detail": "durable local state and injected provider, no live Stripe"})
    from .stripe_session_transport_checks import run_transport_checks
    run_domain_checks(check)
    run_transport_checks(check)
    return {"tests": tests, "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
