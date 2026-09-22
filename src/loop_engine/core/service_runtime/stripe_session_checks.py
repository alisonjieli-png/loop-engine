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
import re
import tempfile
import threading
import time
from types import SimpleNamespace

from .billing_effects import (
    BillingSessionEffectSpec, SESSION_EFFECT_KIND, SESSION_POLICY_KIND, EFFECT_UNKNOWN, EFFECT_CONFIRMED,
)
from .billing_records import StripeEntitlementPolicy, TENANT_METADATA_KEY
from .records import (
    BILLING_MANAGE_SCOPE, DEFAULT_SCOPES, BillingCustomerAccountRelease, BillingCustomerBindingRequest,
    BillingCustomerEffectSpec,
    PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS, ServiceRuntimeConfig, ServiceRuntimeError,
    TenantKeyIssue, TenantRegistration,
)
from .runtime import CUSTOMER_EFFECT, ServiceRuntime
from .stripe_sessions import (
    ACCOUNT_PATH, CHECKOUT_OPERATION, CHECKOUT_PATH, CUSTOMER_COLLECTION_PATH, CUSTOMER_HELD_VERSION,
    CUSTOMER_METADATA_PARAMETER,
    CUSTOMER_PATH, CUSTOMER_SEARCH_PATH, GET_METHOD, MINIMUM_RECONCILIATION_SECONDS, PORTAL_OPERATION,
    PORTAL_PATH, POST_METHOD, PRICE_PATH, SEARCH_QUERY_PARAMETER, SEARCH_RESULT_OBJECT,
    BillingSessionError, BillingSessionRequest,
    StripeSessionAdapter, StripeSessionConfiguration, StripeSessionPlan,
)

FIXTURE_SECRET = "LOCAL_SESSION_ADAPTER_SECRET"
FIXTURE_URL_TOKEN = "LOCAL_PORTAL_CAPABILITY_TOKEN"
METADATA_PARAMETER_PATTERN = re.compile(r"metadata\[([^\]]+)\]")
SEARCH_QUERY_PATTERN = re.compile(r"metadata\['([^']*)'\]:'([^']*)'")


class LocalStripeSessionTransport:
    def __init__(self):
        self.calls, self.effects = [], {}
        self.customers = {}
        # The fixture clock, so a created customer is stamped on the same time
        # line the scenario advances, and the search can be made to lag behind
        # it the way an eventually consistent provider search does.
        self.clock = None
        self.search_lag_seconds = 0
        self.lose_next_response = False
        self.refuse_next_creation = False
        self.after_read = None
        self.override_customer = None
        self.override_account = None
        self.override_price = None
        self.override_search = None
        self.override_result = None
        self.after_post = None

    def _now(self):
        return int(self.clock() if self.clock is not None else time.time())

    def _search(self, parameters):
        """Answer a metadata search the way the provider documents it.

        The answer can be made to lag behind the customer list, because the
        provider search is eventually consistent. A customer becomes visible
        `search_lag_seconds` after it was created.
        """
        match = SEARCH_QUERY_PATTERN.fullmatch(parameters[SEARCH_QUERY_PARAMETER])
        if match is None:
            raise AssertionError("unsupported provider search query")
        key, value = match.group(1), match.group(2)
        fresh = self._now()
        matched = [row for row in self.customers.values() if row["metadata"].get(key) == value
                   and row.get("created", 0) + self.search_lag_seconds <= fresh]
        return {"object": SEARCH_RESULT_OBJECT, "url": CUSTOMER_SEARCH_PATH, "has_more": False, "data": matched}

    def __call__(self, request, secret):
        if secret != FIXTURE_SECRET:
            raise AssertionError("wrong fixture credential")
        self.calls.append(request)
        if request.method == GET_METHOD:
            if request.path == ACCOUNT_PATH:
                result = self.override_account or {"id": "acct_fixture", "object": "account"}
            elif request.path == CUSTOMER_SEARCH_PATH:
                result = self.override_search or self._search(dict(request.parameters))
            elif request.path.startswith(CUSTOMER_PATH):
                identity = request.path[len(CUSTOMER_PATH):]
                result = (self.override_customer or self.customers.get(identity)
                          or {"id": identity, "object": "customer", "livemode": False})
            elif request.path.startswith(PRICE_PATH):
                result = self.override_price or {"id": request.path[len(PRICE_PATH):], "object": "price",
                                                "type": "recurring", "active": True, "livemode": False}
            else:
                raise AssertionError("unexpected provider path")
            if self.after_read is not None:
                self.after_read(request)
            return result
        if request.method != POST_METHOD or request.path not in (CHECKOUT_PATH, PORTAL_PATH, CUSTOMER_COLLECTION_PATH):
            raise AssertionError("unexpected provider mutation")
        parameters = dict(request.parameters)
        if request.path == CUSTOMER_COLLECTION_PATH and self.refuse_next_creation:
            self.refuse_next_creation = False
            raise ServiceRuntimeError("stripe_customer_creation_refused")
        existing = self.effects.get(request.idempotency_key)
        if existing is not None:
            if existing[0] != (request.path, request.parameters):
                raise RuntimeError("provider idempotency conflict")
            result = existing[1]
        elif request.path == CUSTOMER_COLLECTION_PATH:
            result = {"id": "cus_fixture_" + str(len(self.customers) + 1), "object": "customer",
                      "livemode": False, "created": self._now(),
                      "metadata": {METADATA_PARAMETER_PATTERN.fullmatch(key).group(1): value
                                   for key, value in parameters.items()
                                   if METADATA_PARAMETER_PATTERN.fullmatch(key) is not None}}
            self.customers[result["id"]] = result
            self.effects[request.idempotency_key] = ((request.path, request.parameters), result)
        else:
            result = {"id": ("cs_fixture_" if request.path == CHECKOUT_PATH else "bps_fixture_") + str(len(self.effects) + 1),
                      "object": "checkout.session" if request.path == CHECKOUT_PATH else "billing_portal.session",
                      "customer": parameters["customer"], "livemode": False, "created": int(time.time()),
                      "status": "open", "expires_at": int(time.time()) + 3600,
                      "url": ("https://checkout.stripe.com/c/pay/local_fixture#provider_fragment" if request.path == CHECKOUT_PATH
                              else "https://billing.stripe.com/p/session?secret=" + FIXTURE_URL_TOKEN),
                      **{key: value for key, value in parameters.items() if key in (
                          "mode", "success_url", "cancel_url", "configuration", "return_url")},
                      # The provider answers with a Boolean where the form carried text.
                      **({"allow_promotion_codes": parameters["allow_promotion_codes"] == "true"}
                         if "allow_promotion_codes" in parameters else {})}
            self.effects[request.idempotency_key] = ((request.path, request.parameters), result)
        if self.lose_next_response:
            self.lose_next_response = False
            raise TimeoutError("connection lost after creation " + FIXTURE_SECRET)
        if self.after_post is not None:
            self.after_post(request)
        return self.override_result or dict(result)


def fixture(root, *, bind_customers=True, **policy_changes):
    clock = {"now": int(time.time())}
    configuration = ServiceRuntimeConfig(str(Path(root) / "service.db"), writes_authorized=True)
    runtime = ServiceRuntime(configuration, clock=lambda: clock["now"])
    keys = {}
    for tenant in ("alpha", "beta"):
        runtime.register_tenant(TenantRegistration(tenant, "tenant:" + tenant,
                                                  scopes=(*DEFAULT_SCOPES, BILLING_MANAGE_SCOPE)))
        keys[tenant] = runtime.issue_key(TenantKeyIssue(tenant, "local billing acceptance"))
        if bind_customers:
            runtime.bind_billing_customer(BillingCustomerBindingRequest(tenant, "cus_" + tenant, "acct_fixture"))
    runtime.configure_billing_policy(StripeEntitlementPolicy(("price_basic", "price_other")))
    policy = StripeSessionConfiguration("acct_fixture", "fixture_version", "env:LOCAL_STRIPE_SESSION",
        plans=(StripeSessionPlan("basic", "Basic service", "price_basic"), StripeSessionPlan("other", "Other service", "price_other")),
        checkout_success_url="https://app.example/billing/success", checkout_cancel_url="https://app.example/billing/cancel",
        portal_return_url="https://app.example/account", portal_configuration_id="bpc_fixture",
        allow_network=True, allow_session_creation=True, **policy_changes)
    provider = LocalStripeSessionTransport()
    provider.clock = lambda: clock["now"]
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


def captured(function):
    """Return the domain refusal itself so its caller-safe details can be read."""
    try:
        function()
    except ServiceRuntimeError as error:
        return error
    return None


def quiet(function):
    """Run one scenario step and keep a domain refusal as an observed outcome."""
    try:
        return function()
    except ServiceRuntimeError:
        return None


def install_policy(held, adapter):
    """Install this adapter's own session policy over the one the fixture set."""
    with held.runtime._catalog.store() as store:
        row = held.runtime._catalog.read(store, SESSION_POLICY_KIND, "stripe")
    return adapter.configure_policy(expected_version=row["record_version"])


def advance(held, seconds):
    """Move the fixture clock forward inside a provider call."""
    held.clock["now"] += seconds


def other_account_adapter(held, account_id="acct_live", **fields):
    """The same service pointed at a different provider account.

    It gets its own transport, because a customer at one provider account does
    not exist at another.
    """
    provider = LocalStripeSessionTransport()
    provider.clock = lambda: held.clock["now"]
    provider.override_account = {"id": account_id, "object": "account"}
    configuration = replace(held.policy, account_id=account_id, **fields)
    adapter = StripeSessionAdapter(held.runtime, configuration, held.secret, transport=provider)
    install_policy(held, adapter)
    return adapter, provider


def checkout(adapter, current, identity, plan="basic"):
    return adapter.create(current, BillingSessionRequest(CHECKOUT_OPERATION, identity,
                                                         adapter.policy_digest, plan))


def customer_rows(held, tenant="alpha"):
    with held.runtime._catalog.store() as store:
        return held.runtime._catalog.rows(store, CUSTOMER_EFFECT, tenant)


def creations(held):
    return [call for call in held.provider.calls
            if call.method == POST_METHOD and call.path == CUSTOMER_COLLECTION_PATH]


def bound(held, tenant="alpha"):
    """The account's durable binding, or None when it has none or cannot read one."""
    try:
        return held.adapter._binding(principal(held, tenant))
    except ServiceRuntimeError:
        return None


def sessions_created(held):
    return [call for call in held.provider.calls
            if call.method == POST_METHOD and call.path == CHECKOUT_PATH]


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


def first_checkout_binds_one_customer(root):
    """A person who signs in and never paid presses subscribe once."""
    held = fixture(root, bind_customers=False)
    quiet(lambda: held.adapter.create(principal(held), request(held, "first-checkout")))
    bound = held.adapter._binding(principal(held))
    return (len(creations(held)) == 1 and len(held.provider.customers) == 1 and bound is not None
            and bound["provider_customer_id"] in held.provider.customers
            and held.provider.customers[bound["provider_customer_id"]]["metadata"] == {TENANT_METADATA_KEY: "alpha"})


def repeat_after_the_window_finds_the_existing_customer(root):
    """The first answer was lost and the provider no longer keeps its key."""
    held = fixture(root, bind_customers=False)
    held.provider.lose_next_response = True
    quiet(lambda: held.adapter.create(principal(held), request(held, "lost-answer")))
    held.clock["now"] += held.policy.reconciliation_seconds + 1
    held.provider.effects.clear()
    quiet(lambda: held.adapter.create(principal(held), request(held, "months-later")))
    bound = held.adapter._binding(principal(held))
    return (len(creations(held)) == 1 and len(held.provider.customers) == 1 and bound is not None
            and customer_rows(held)[0]["payload"]["idempotency_cycles"] == 1)


def another_accounts_customer_is_never_bound(root):
    """The provider search answers with a customer that names another account."""
    held = fixture(root, bind_customers=False)
    foreign = {"id": "cus_named_for_beta", "object": "customer", "livemode": False,
               "metadata": {TENANT_METADATA_KEY: "beta"}}
    held.provider.customers[foreign["id"]] = foreign
    held.provider.override_search = {"object": SEARCH_RESULT_OBJECT, "url": CUSTOMER_SEARCH_PATH,
                                     "has_more": False, "data": [foreign]}
    quiet(lambda: held.adapter.create(principal(held), request(held, "alpha-checkout")))
    alpha = held.adapter._binding(principal(held))
    return alpha is None or alpha["provider_customer_id"] != foreign["id"]


def a_truncated_search_is_not_read_as_no_customer(root):
    """The provider answers with no rows and says the page was truncated.

    The account already owns a customer, so reading that answer as absence
    would give it a second one.
    """
    held = fixture(root, bind_customers=False)
    held.provider.customers["cus_already_there"] = {
        "id": "cus_already_there", "object": "customer", "livemode": False,
        "created": held.clock["now"], "metadata": {TENANT_METADATA_KEY: "alpha"}}
    held.provider.override_search = {"object": SEARCH_RESULT_OBJECT, "url": CUSTOMER_SEARCH_PATH,
                                     "has_more": True, "data": []}
    quiet(lambda: held.adapter.create(principal(held), request(held, "truncated-empty-page")))
    return (not creations(held) and list(held.provider.customers) == ["cus_already_there"]
            and bound(held) is None)


def a_new_cycle_waits_until_the_search_can_show_the_last_attempt(root):
    """A creation late in the window, whose answer was lost, then a repeat.

    The provider search is given exactly the freshness allowance the service
    declares, and the creation happens late in the reconciliation window, so
    the stored key is retired while the search can still be blind to what it
    made. Only the wait before a new cycle keeps the account at one customer.
    """
    held = fixture(root, bind_customers=False)
    tight = replace(held.policy, reconciliation_seconds=MINIMUM_RECONCILIATION_SECONDS)
    adapter = StripeSessionAdapter(held.runtime, tight, held.secret, transport=held.provider)
    install_policy(held, adapter)
    held.provider.search_lag_seconds = PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
    late = tight.lease_seconds - 5
    held.provider.after_read = lambda call: advance(held, late) if call.path == ACCOUNT_PATH else None
    held.provider.lose_next_response = True
    start = held.clock["now"]
    quiet(lambda: adapter.ensure_customer(principal(held)))
    held.provider.after_read = None
    held.provider.effects.clear()  # the provider no longer keeps the retired key
    held.clock["now"] = start + tight.reconciliation_seconds + 1
    early = refused(lambda: adapter.ensure_customer(principal(held)),
                    "billing_customer_search_not_current_yet")
    made_nothing_early = len(creations(held)) == 1 and len(held.provider.customers) == 1
    held.clock["now"] = start + tight.lease_seconds + PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
    quiet(lambda: adapter.ensure_customer(principal(held)))
    settled = bound(held)
    return (early and made_nothing_early and len(creations(held)) == 1
            and len(held.provider.customers) == 1 and settled is not None
            and settled["provider_customer_id"] in held.provider.customers)


def an_unbound_account_reaches_checkout_after_the_account_changes(root):
    """The account attempted checkout in the sandbox and never bound.

    The service is then pointed at another provider account. The customer the
    sandbox may hold does not exist there, so the account starts a fresh cycle
    at the current provider account and keeps the one it left as evidence.
    """
    held = fixture(root, bind_customers=False)
    held.provider.lose_next_response = True
    start = held.clock["now"]
    quiet(lambda: held.adapter.ensure_customer(principal(held)))
    left_behind = list(held.provider.customers)
    live, live_provider = other_account_adapter(held)
    held.clock["now"] = start + held.policy.lease_seconds + PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
    result = observed_result(lambda: checkout(live, principal(held), "after-account-change"))
    settled = bound(held)
    superseded = customer_rows(held)[0]["payload"]["superseded_provider_accounts"]
    return (isinstance(result, dict) and result.get("provider_session_id", "").startswith("cs_")
            and settled is not None and settled["provider_account_id"] == "acct_live"
            and settled["provider_customer_id"] in live_provider.customers
            and len(live_provider.customers) == 1
            and list(held.provider.customers) == left_behind and len(left_behind) == 1
            and [row["provider_account_id"] for row in superseded] == ["acct_fixture"])


def a_released_account_reaches_checkout_at_the_current_account(root):
    """The account bound a customer in the sandbox, then the service moved.

    A bound account stays refused until a host releases it by name. After the
    release it reaches checkout at the current provider account, and the
    customer it had at the account it left is kept as evidence.
    """
    held = fixture(root, bind_customers=False)
    quiet(lambda: held.adapter.create(principal(held), request(held, "sandbox-checkout")))
    sandbox = bound(held)
    live, live_provider = other_account_adapter(held)
    wedged = refused(lambda: checkout(live, principal(held), "before-release"),
                     "stripe_account_or_customer_mismatch")
    offered_before = live.options(principal(held))
    held.runtime.release_billing_customer_account(
        BillingCustomerAccountRelease("alpha", "acct_fixture", "acct_live"))
    held.clock["now"] += held.policy.lease_seconds + PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
    result = observed_result(lambda: checkout(live, principal(held), "after-release"))
    settled = bound(held)
    return (wedged and offered_before["checkout_available"] is False
            and sandbox is not None and sandbox["provider_account_id"] == "acct_fixture"
            and isinstance(result, dict) and result.get("provider_session_id", "").startswith("cs_")
            and settled is not None and settled["provider_account_id"] == "acct_live"
            and settled["provider_customer_id"] in live_provider.customers
            and len(live_provider.customers) == 1
            and sandbox["provider_customer_id"] in held.provider.customers
            and len(held.provider.customers) == 1)


def another_provider_account_creates_no_customer(root):
    """The configured credential reaches a provider account the host did not choose."""
    held = fixture(root, bind_customers=False)
    held.provider.override_account = {"id": "acct_unbound", "object": "account"}
    quiet(lambda: held.adapter.create(principal(held), request(held, "wrong-account")))
    return (not held.provider.customers and not creations(held)
            and held.adapter._binding(principal(held)) is None)


def run_customer_checks(check):
    with tempfile.TemporaryDirectory(prefix="stripe-customer-first-") as root:
        held = fixture(root, bind_customers=False)
        offered = held.adapter.options(principal(held))
        result = observed_result(lambda: held.adapter.create(principal(held), request(held, "first-checkout")))
        first = bound(held)
        session = sessions_created(held)
        check("an_account_that_never_paid_is_offered_checkout_and_gets_one_customer_and_one_session",
              offered["checkout_available"] is True and offered["portal_available"] is False
              and offered["unavailable_reason"] == "" and len(creations(held)) == 1
              and len(held.provider.customers) == 1 and result.get("payment_confirmed") is False
              and first is not None and first["provider_account_id"] == "acct_fixture"
              and first["provider_customer_id"] in held.provider.customers
              and len(session) == 1
              and dict(session[0].parameters)["customer"] == first["provider_customer_id"])
        created = held.provider.customers.get(first["provider_customer_id"]) if first else {}
        form = dict(creations(held)[0].parameters) if creations(held) else {}
        check("a_created_customer_carries_only_the_account_identifier_and_no_personal_detail",
              form == {CUSTOMER_METADATA_PARAMETER: "alpha"}
              and created.get("metadata") == {TENANT_METADATA_KEY: "alpha"}
              and not {"email", "name", "phone", "address[line1]", "description"} & set(form)
              and customer_rows(held)[0]["payload"]["status"] == EFFECT_CONFIRMED)
        observed_result(lambda: held.adapter.create(principal(held), request(held, "second-checkout")))
        again = bound(held)
        check("a_second_checkout_reuses_the_bound_customer_and_creates_nothing_at_the_provider",
              len(creations(held)) == 1 and len(held.provider.customers) == 1
              and len(customer_rows(held)) == 1 and again is not None and first is not None
              and again["provider_customer_id"] == first["provider_customer_id"]
              and held.adapter.options(principal(held))["portal_available"] is True)

    with tempfile.TemporaryDirectory(prefix="stripe-customer-scope-") as root:
        held = fixture(root, bind_customers=False)
        limited = held.runtime.issue_key(TenantKeyIssue("alpha", "metadata only", scopes=DEFAULT_SCOPES))
        narrow = held.runtime.authenticate_key(limited.key)
        check("a_caller_without_the_billing_scope_creates_no_customer_and_reaches_no_provider_call",
              refused(lambda: held.adapter.create(narrow, request(held, "no-scope")), "scope_required")
              and refused(lambda: held.adapter.ensure_customer(narrow), "scope_required")
              and not held.provider.calls and not held.secret_calls and not held.provider.customers
              and not customer_rows(held))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-authority-") as root:
        held = fixture(root, bind_customers=False)
        issued = principal(held)
        held.runtime.set_tenant_enabled("alpha", False)
        disabled = refused(lambda: held.adapter.ensure_customer(issued), "unauthorized")
        held.runtime.set_tenant_enabled("alpha", True)
        for field in ("allow_network", "allow_session_creation"):
            denied = StripeSessionAdapter(held.runtime, replace(held.policy, **{field: False}),
                                          held.secret, transport=held.provider)
            disabled = disabled and refused(lambda: denied.ensure_customer(principal(held)),
                                            "session_network_authority_required")
        check("a_disabled_account_or_absent_network_authority_creates_no_customer",
              disabled and not held.provider.calls and not held.secret_calls
              and not held.provider.customers and not customer_rows(held))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-other-account-") as root:
        held = fixture(root, bind_customers=False)
        held.runtime.bind_billing_customer(BillingCustomerBindingRequest("alpha", "cus_elsewhere", "acct_other"))
        blocked = refused(lambda: held.adapter.create(principal(held), request(held, "other-account")),
                          "stripe_account_or_customer_mismatch")
        held_result = observed_result(lambda: held.adapter.ensure_customer(principal(held)))
        offered = held.adapter.options(principal(held))
        check("an_account_bound_to_another_provider_account_is_refused_and_gets_no_second_customer",
              blocked and held_result.get("status") == "already_bound" and not held.provider.customers
              and not held.provider.calls and offered["checkout_available"] is False
              and offered["unavailable_reason"] == "stripe_account_mismatch"
              and held.runtime.billing_customer_for(principal(held))["provider_account_id"] == "acct_other")
        check("a_binding_this_request_did_not_make_is_reported_with_its_own_record_and_its_real_customer",
              held_result.get("record_type") == CUSTOMER_HELD_VERSION
              and held_result.get("provider_customer_id") == "cus_elsewhere"
              and held_result.get("provider_account_id") == "acct_other"
              and held_result.get("matches_configured_provider_account") is False
              and held.adapter.policy_digest and held.adapter.configuration.account_id == "acct_fixture")

    with tempfile.TemporaryDirectory(prefix="stripe-customer-uncertain-") as root:
        held = fixture(root, bind_customers=False)
        held.provider.lose_next_response = True
        error = captured(lambda: held.adapter.create(principal(held), request(held, "uncertain-customer")))
        left_behind = list(held.provider.customers)
        check("an_uncertain_creation_is_reported_as_uncertain_and_is_not_retried_by_the_service",
              isinstance(error, BillingSessionError) and error.code == "billing_customer_uncertain"
              and error.details["creation_attempted"] is True and error.details["retry_same_request"] is True
              and error.details["provider_commitment"] == "not_asserted"
              and error.details["record_type"] == "billing_customer_uncertainty/v1"
              and len(left_behind) == 1 and len(creations(held)) == 1
              and customer_rows(held)[0]["payload"]["status"] == EFFECT_UNKNOWN
              and refused(lambda: held.runtime.billing_customer_for(principal(held)), "billing_customer_not_bound"))
        stored = json.dumps(customer_rows(held))
        key = customer_rows(held)[0]["payload"]["idempotency_key"]
        observed_result(lambda: held.adapter.create(principal(held), request(held, "uncertain-customer")))
        reconciled = bound(held)
        check("the_retry_finds_the_customer_left_behind_by_its_metadata_and_binds_that_one",
              len(creations(held)) == 1 and len(held.provider.customers) == 1
              and reconciled is not None and reconciled["provider_customer_id"] == left_behind[0]
              and customer_rows(held)[0]["payload"]["idempotency_key"] == key
              and customer_rows(held)[0]["payload"]["status"] == EFFECT_CONFIRMED
              and FIXTURE_SECRET not in stored)

    with tempfile.TemporaryDirectory(prefix="stripe-customer-refused-") as root:
        held = fixture(root, bind_customers=False)
        held.provider.refuse_next_creation = True
        error = captured(lambda: held.adapter.create(principal(held), request(held, "refused-customer")))
        check("a_creation_refused_by_the_provider_leaves_no_binding_and_reports_the_refusal",
              isinstance(error, BillingSessionError) and error.code == "billing_customer_uncertain"
              and error.details["diagnostic_code"] == "stripe_customer_creation_refused"
              and error.status == 503 and not held.provider.customers
              and customer_rows(held)[0]["payload"]["diagnostic_code"] == "stripe_customer_creation_refused"
              and refused(lambda: held.runtime.billing_customer_for(principal(held)), "billing_customer_not_bound"))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-concurrent-") as root:
        held = fixture(root, bind_customers=False)
        entered, release = threading.Event(), threading.Event()
        held.provider.after_read = lambda call: (entered.set(), release.wait(2)) if call.path == ACCOUNT_PATH else None
        current = principal(held)
        with ThreadPoolExecutor(max_workers=2) as pool:
            running = pool.submit(lambda: observed_result(
                lambda: held.adapter.create(current, request(held, "concurrent-one"))))
            entered.wait(1)
            try:
                blocked = refused(lambda: held.adapter.create(current, request(held, "concurrent-two")),
                                  "billing_customer_creation_in_progress")
            finally:
                release.set()
            running.result(timeout=5)
        held.provider.after_read = None
        observed_result(lambda: held.adapter.create(current, request(held, "concurrent-two")))
        settled = bound(held)
        check("two_concurrent_first_requests_end_with_exactly_one_customer_and_one_binding",
              blocked and len(creations(held)) == 1 and len(held.provider.customers) == 1
              and len(customer_rows(held)) == 1 and settled is not None
              and settled["provider_customer_id"] in held.provider.customers)

    with tempfile.TemporaryDirectory(prefix="stripe-customer-ambiguous-") as root:
        held = fixture(root, bind_customers=False)
        twins = [{"id": "cus_twin_one", "object": "customer", "livemode": False,
                  "metadata": {TENANT_METADATA_KEY: "alpha"}},
                 {"id": "cus_twin_two", "object": "customer", "livemode": False,
                  "metadata": {TENANT_METADATA_KEY: "alpha"}}]
        held.provider.override_search = {"object": SEARCH_RESULT_OBJECT, "url": CUSTOMER_SEARCH_PATH,
                                         "has_more": False, "data": twins}
        error = captured(lambda: held.adapter.create(principal(held), request(held, "ambiguous")))
        held.provider.override_search = {"object": SEARCH_RESULT_OBJECT, "url": CUSTOMER_SEARCH_PATH,
                                         "has_more": True, "data": [twins[0]]}
        truncated = captured(lambda: held.adapter.create(principal(held), request(held, "truncated")))
        check("more_than_one_customer_for_one_account_is_refused_instead_of_choosing_one",
              isinstance(error, BillingSessionError) and error.code == "billing_customer_not_created"
              and error.details["diagnostic_code"] == "ambiguous_billing_customer_at_provider"
              and error.details["creation_attempted"] is False
              and truncated is not None
              and truncated.details["diagnostic_code"] == "ambiguous_billing_customer_at_provider"
              and not creations(held)
              and refused(lambda: held.runtime.billing_customer_for(principal(held)), "billing_customer_not_bound"))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-named-") as root:
        check("a_first_checkout_binds_one_customer_that_names_its_account",
              first_checkout_binds_one_customer(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-window-") as root:
        check("a_repeat_after_the_idempotency_window_finds_the_existing_customer_instead_of_creating_another",
              repeat_after_the_window_finds_the_existing_customer(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-page-") as root:
        check("an_account_that_already_owns_a_customer_keeps_it_when_the_search_page_is_truncated",
              a_truncated_search_is_not_read_as_no_customer(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-foreign-") as root:
        check("a_provider_customer_that_names_another_account_is_never_bound",
              another_accounts_customer_is_never_bound(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-account-") as root:
        check("a_credential_that_reaches_another_provider_account_creates_no_customer",
              another_provider_account_creates_no_customer(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-truncated-") as root:
        held = fixture(root, bind_customers=False)
        held.provider.override_search = {"object": SEARCH_RESULT_OBJECT, "url": CUSTOMER_SEARCH_PATH,
                                         "has_more": True, "data": []}
        error = captured(lambda: held.adapter.create(principal(held), request(held, "truncated-empty")))
        check("a_truncated_search_answer_with_no_rows_is_refused_instead_of_read_as_no_customer",
              isinstance(error, BillingSessionError) and error.code == "billing_customer_not_created"
              and error.details["diagnostic_code"] == "ambiguous_billing_customer_at_provider"
              and error.details["creation_attempted"] is False and not creations(held)
              and not held.provider.customers and bound(held) is None)

    with tempfile.TemporaryDirectory(prefix="stripe-customer-freshness-") as root:
        check("a_new_provider_key_cycle_waits_until_the_search_can_show_the_last_attempt",
              a_new_cycle_waits_until_the_search_can_show_the_last_attempt(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-floor-") as root:
        held = fixture(root, bind_customers=False)
        spec = BillingCustomerEffectSpec("alpha", "acct_fixture", TENANT_METADATA_KEY)
        check("a_reconciliation_window_below_the_declared_search_freshness_allowance_is_refused",
              MINIMUM_RECONCILIATION_SECONDS == PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
              and held.policy.lease_seconds < MINIMUM_RECONCILIATION_SECONDS
              and refused(lambda: replace(held.policy, reconciliation_seconds=MINIMUM_RECONCILIATION_SECONDS - 1),
                          "invalid_session_allowance")
              and refused(lambda: held.runtime.begin_billing_customer(
                  principal(held), spec, lease_seconds=10,
                  reconciliation_seconds=MINIMUM_RECONCILIATION_SECONDS - 1),
                  "invalid_billing_customer_effect_allowance")
              and not customer_rows(held))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-switch-") as root:
        check("an_unbound_account_reaches_checkout_after_the_configured_provider_account_changes",
              an_unbound_account_reaches_checkout_after_the_account_changes(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-release-") as root:
        check("a_released_account_reaches_checkout_at_the_provider_account_the_service_now_uses",
              a_released_account_reaches_checkout_at_the_current_account(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-release-refusal-") as root:
        held = fixture(root, bind_customers=False)
        quiet(lambda: held.adapter.create(principal(held), request(held, "sandbox-checkout")))
        live, _live_provider = other_account_adapter(held)
        mismatched = refused(lambda: held.runtime.release_billing_customer_account(
            BillingCustomerAccountRelease("alpha", "acct_live", "acct_other")),
            "billing_customer_release_account_mismatch")
        same = refused(lambda: BillingCustomerAccountRelease("alpha", "acct_fixture", "acct_fixture"),
                       "billing_customer_release_needs_another_account")
        other_tenant = refused(lambda: held.runtime.release_billing_customer_account(
            BillingCustomerAccountRelease("beta", "acct_fixture", "acct_live")),
            "billing_customer_release_account_mismatch")
        check("a_release_refuses_unless_it_names_the_exact_provider_account_the_account_holds",
              mismatched and same and other_tenant
              and held.runtime.billing_customer_for(principal(held))["provider_account_id"] == "acct_fixture"
              and refused(lambda: checkout(live, principal(held), "still-wedged"),
                          "stripe_account_or_customer_mismatch"))


def run_checks():
    tests = []
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed), "detail": "durable local state and injected provider, no live Stripe"})
    from .stripe_session_transport_checks import (
        run_customer_mutant_controls, run_customer_window_checks, run_transport_checks,
    )
    run_domain_checks(check)
    run_customer_checks(check)
    run_customer_window_checks(check)
    run_customer_mutant_controls(check)
    run_transport_checks(check)
    return {"tests": tests, "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
