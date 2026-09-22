"""Adversarial provider-shaped responses, removed-guard controls, and real HTTP
session acceptance.

The actual adapter serializer runs against a local injected HTTP transport.
The public routes run over loopback sockets and real durable catalogue records.
The removed-guard controls rerun the customer creation scenarios defined beside
the fixture in `stripe_session_checks.py`, each with one guard patched away.
No provider account, checkout, portal or payment is created remotely.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

from . import stripe_sessions as sessions
from .billing_effects import EFFECT_CONFIRMED, EFFECT_UNKNOWN
from .billing_records import TENANT_METADATA_KEY
from .http import ServiceHttpApplication, BILLING_CHECKOUT_PATH, BILLING_PLANS_PATH, BILLING_PORTAL_PATH
from .http_test_fixtures import running_http, running_key_set
from .records import (
    BillingCustomerAccountRelease, DEFAULT_SCOPES, ServiceCommitUnknown, ServiceRuntimeError,
    SubjectBindingRequest, TenantKeyIssue,
)
from .records import PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
from .stripe_session_checks import (
    FIXTURE_SECRET, advance, bound, creations, customer_rows, fixture, install_policy, principal,
    quiet, request, refused, rows,
)
from .stripe_sessions import ACCOUNT_PATH, MINIMUM_RECONCILIATION_SECONDS


def _response_checks(check):
    with tempfile.TemporaryDirectory(prefix="session-response-") as root:
        held = fixture(root)
        valid = held.adapter.create(principal(held), request(held, "valid"))
        check("provider_checkout_URL_fragment_is_preserved_as_documented",
              valid["redirect_url"].endswith("#provider_fragment"))
        original = next(iter(held.provider.effects.values()))[1]
        held.provider.override_result = {**original, "id": "cs_changed_identity"}
        check("same_provider_idempotency_key_cannot_change_its_confirmed_session_identity",
              refused(lambda: held.adapter.create(principal(held), request(held, "valid")), "billing_session_uncertain")
              and rows(held)[0]["payload"]["provider_session_id"] == original["id"])
        held.provider.override_result = None
        held.adapter.create(principal(held), request(held, "portal-valid", operation=sessions.PORTAL_OPERATION))
        portal = list(held.provider.effects.values())[-1][1]
        held.provider.override_result = {**portal, "configuration": "bpc_unbound"}
        check("portal_response_requires_the_exact_host_configuration",
              refused(lambda: held.adapter.create(principal(held), request(held, "portal-changed", operation=sessions.PORTAL_OPERATION)),
                      "billing_session_uncertain"))
        cases = (
            ("redirect_host", {"url": "https://untrusted.example/checkout"}),
            ("redirect_userinfo", {"url": "https://untrusted@checkout.stripe.com/c/pay/example"}),
            ("customer", {"customer": "cus_beta"}), ("livemode", {"livemode": True}),
            ("success_return", {"success_url": "https://untrusted.example/success"}),
            ("cancel_return", {"cancel_url": "https://untrusted.example/cancel"}),
            ("closed_session", {"status": "complete"}), ("expiry", {"expires_at": int(time.time()) - 1}),
        )
        for name, changed in cases:
            held.provider.override_result = {**original, **changed}
            check("provider_response_" + name + "_cannot_be_returned_as_success",
                  refused(lambda name=name: held.adapter.create(principal(held), request(held, name)), "billing_session_uncertain")
                  and any(row["payload"]["spec"]["request_id"] == name and row["payload"]["status"] == EFFECT_UNKNOWN
                          for row in rows(held)))
        held.provider.override_result = None
        before = len(held.provider.effects)
        held.provider.after_post = lambda _request: held.runtime.revoke_key("alpha", held.keys["alpha"].key_id)
        issued = principal(held)
        check("revocation_after_provider_creation_retains_effect_but_refuses_success",
              refused(lambda: held.adapter.create(issued, request(held, "after-post")),
                      "billing_session_authority_expired_after_dispatch")
              and len(held.provider.effects) == before + 1
              and any(row["payload"]["spec"]["request_id"] == "after-post"
                      and row["payload"]["status"] == EFFECT_CONFIRMED for row in rows(held)))

    with tempfile.TemporaryDirectory(prefix="session-commit-") as root:
        held = fixture(root)
        with patch.object(type(held.runtime._catalog), "commit", side_effect=ServiceCommitUnknown()):
            denied = refused(lambda: held.adapter.create(principal(held), request(held, "uncertain-reservation")), "commit_unknown")
        check("unknown_reservation_commit_never_reaches_secret_or_provider", denied and not held.secret_calls and not held.provider.calls)
        first = held.adapter.create(principal(held), request(held, "shared-client-id"))
        second = held.adapter.create(principal(held, "beta"), request(held, "shared-client-id"))
        check("request_identity_is_tenant_scoped_with_distinct_provider_idempotency_keys",
              first["effect_ref"] != second["effect_ref"] and first["provider_session_id"] != second["provider_session_id"]
              and {dict(call.parameters)["customer"] for call in held.provider.calls if call.method == sessions.POST_METHOD}
              == {"cus_alpha", "cus_beta"})
        changed = sessions.StripeSessionAdapter(held.runtime, replace(held.policy, checkout_cancel_url="https://app.example/new"),
                                               held.secret, transport=held.provider)
        check("changed_host_session_policy_requires_exact_durable_revision",
              refused(changed.configure_policy, "session_policy_revision_required")
              and held.adapter.configure_policy() == held.installation)


def _wire_checks(check):
    import httpx
    wire = sessions.StripeSessionWireRequest(sessions.POST_METHOD, sessions.CHECKOUT_PATH,
        (("customer", "cus_alpha"), ("line_items[0][price]", "price_basic")), "fixture_version", "le-session-exact", 2, 1024)
    observed, options = [], []
    original_client = httpx.Client
    state = {"status": 200, "body": b'{"id":"cs_fixture"}'}
    def handler(outgoing):
        observed.append(outgoing)
        return httpx.Response(state["status"], content=state["body"], headers={"Location": "https://untrusted.example/"})
    def client(**kwargs):
        options.append(kwargs)
        return original_client(**kwargs, transport=httpx.MockTransport(handler))
    with patch.object(httpx, "Client", client):
        value = sessions._send(wire, FIXTURE_SECRET)
        check("real_provider_serializer_binds_origin_version_form_and_idempotency_without_redirects",
              value["id"] == "cs_fixture" and str(observed[0].url) == sessions.STRIPE_ORIGIN + sessions.CHECKOUT_PATH
              and observed[0].headers["stripe-version"] == "fixture_version"
              and observed[0].headers["idempotency-key"] == "le-session-exact"
              and b"line_items%5B0%5D%5Bprice%5D=price_basic" in observed[0].content
              and options[0]["follow_redirects"] is False and options[0]["trust_env"] is False)
        state["status"] = 302
        try:
            sessions._send(wire, FIXTURE_SECRET)
            blocked = False
        except httpx.HTTPError:
            blocked = True
        check("provider_redirect_is_refused_without_following_its_location", blocked and len(observed) == 2)
        state.update(status=200, body=b"X" * 2048)
        check("provider_response_byte_limit_prevents_unbounded_loading",
              refused(lambda: sessions._send(wire, FIXTURE_SECRET), "stripe_response_too_large"))
        state["body"] = b'{"id":"one","id":"two"}'
        check("provider_duplicate_JSON_fields_are_not_accepted", refused(lambda: sessions._send(wire, FIXTURE_SECRET)))
    check("wire_contract_refuses_unscoped_paths_missing_idempotency_and_read_effect_fields",
          all(refused(case) for case in (
              lambda: replace(wire, idempotency_key=""),
              lambda: replace(wire, path="/v1/customers"),
              lambda: replace(wire, method=sessions.GET_METHOD, path=sessions.CUSTOMER_PATH + "../account",
                              parameters=(), idempotency_key=""),
              lambda: replace(wire, method=sessions.GET_METHOD, path=sessions.ACCOUNT_PATH),
          )))
    # The creation form reads no adapter state, so the unbound method returns
    # the exact parameters the adapter would send for that account.
    creation_form = sessions.StripeSessionAdapter._customer_creation_parameters(None, "alpha")
    check("the_customer_wire_contract_refuses_personal_fields_and_an_unbounded_search",
          refused(lambda: _customer_wire((("email", "person@example.test"),)),
                  "unsupported_session_wire_parameters")
          and refused(lambda: _customer_wire(creation_form, idempotency_key=""), "invalid_request")
          and refused(lambda: _search_wire(()), "unsupported_customer_search_parameters")
          and refused(lambda: _search_wire((("expand[]", "data"),)), "unsupported_customer_search_parameters")
          and refused(lambda: sessions._customer_search_query(TENANT_METADATA_KEY,
                                                              "alpha' or metadata['x']:'y"), "invalid_request"))


def _customer_wire(parameters, *, idempotency_key="le-customer-fixture"):
    return sessions.StripeSessionWireRequest(sessions.POST_METHOD, sessions.CUSTOMER_COLLECTION_PATH,
        tuple(parameters), "fixture_version", idempotency_key, 2, 1024)


def _search_wire(parameters):
    return sessions.StripeSessionWireRequest(sessions.GET_METHOD, sessions.CUSTOMER_SEARCH_PATH,
        tuple(parameters), "fixture_version", "", 2, 1024)


def _application(held, configuration, authentication=None):
    from ..harness_intelligence import HarnessIntelligenceCatalogue
    from ..provisioning_server import ProvisioningQualification, ProvisioningQualificationResolver
    from .provisioning import DurableProvisioningBinding
    catalogue = HarnessIntelligenceCatalogue()
    resolver = ProvisioningQualificationResolver("empty-session-check", lambda binding:
        ProvisioningQualification(binding, "unknown", "host_attested"))
    binding = DurableProvisioningBinding(held.runtime, catalogue, resolver, lambda _item: "")
    fields = {"authentication": authentication} if authentication is not None else {}
    return ServiceHttpApplication(held.runtime, binding, configuration, billing_sessions=held.adapter, **fields)


def _http_checks(check):
    import httpx
    with tempfile.TemporaryDirectory(prefix="session-http-") as root:
        held = fixture(root)
        with running_http(held, application_factory=lambda config: _application(held, config)) as (base, _service):
            with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + held.keys["alpha"].key},
                              trust_env=False, timeout=4) as client:
                capabilities = client.get("/api/v1/capabilities").json()["result"]
                plans = client.get(BILLING_PLANS_PATH).json()["result"]
                body = {"record_type": sessions.SESSION_REQUEST_VERSION, "request_id": "web-checkout",
                        "policy_digest": plans["policy_digest"], "plan_ref": "basic"}
                created = client.post(BILLING_CHECKOUT_PATH, json=body)
                repeat = client.post(BILLING_CHECKOUT_PATH, json=body)
                portal = client.post(BILLING_PORTAL_PATH, json={key: value for key, value in {
                    **body, "request_id": "web-portal"}.items() if key != "plan_ref"})
                check("real_HTTP_checkout_and_portal_use_versioned_canonical_Loop_results",
                      capabilities["billing"]["checkout"] and capabilities["billing"]["portal"]
                      and {plan["plan_ref"] for plan in plans["plans"]} == {"basic", "other"}
                      and "price_basic" not in json.dumps(plans)
                      and created.status_code == repeat.status_code == portal.status_code == 200
                      and repeat.json()["result"]["status"] == "reconciled"
                      and created.json()["execution"]["runtime_type"] == "Loop"
                      and portal.json()["result"]["entitlement_changed"] is False and len(held.provider.effects) == 2)
                count = len(held.provider.calls)
                injected = client.post(BILLING_CHECKOUT_PATH, json={**body, "customer_id": "cus_beta"})
                old = client.post(BILLING_CHECKOUT_PATH, json={**body, "record_type": "billing_session_request/v0"})
                conflict = client.post(BILLING_CHECKOUT_PATH, json={**body, "plan_ref": "other"})
                absent = httpx.post(base + BILLING_CHECKOUT_PATH, json=body, trust_env=False)
                check("real_HTTP_refuses_client_authority_obsolete_version_changed_selection_and_missing_token",
                      injected.status_code == old.status_code == 400 and conflict.status_code == 409
                      and absent.status_code == 401 and len(held.provider.calls) == count)
                limited = held.runtime.issue_key(TenantKeyIssue("alpha", "no billing", scopes=DEFAULT_SCOPES))
                headers = {"Authorization": "Bearer " + limited.key}
                options = client.get(BILLING_PLANS_PATH, headers=headers).json()["result"]
                denied = client.post(BILLING_CHECKOUT_PATH, json=body, headers=headers)
                check("real_HTTP_requires_explicit_billing_scope_and_does_not_advertise_it_to_limited_keys",
                      not options["checkout_available"] and not options["portal_available"]
                      and denied.status_code == 403 and len(held.provider.calls) == count)
                held.provider.lose_next_response = True
                unknown_body = {**body, "request_id": "web-unknown"}
                unknown = client.post(BILLING_CHECKOUT_PATH, json=unknown_body)
                check("real_HTTP_unknown_effect_keeps_same_request_identity_without_secret_echo_or_retry",
                      unknown.status_code == 503 and unknown.json()["automatic_retry"] is False
                      and unknown.json()["error"]["details"]["request_id"] == "web-unknown"
                      and unknown.json()["error"]["details"]["creation_attempted"] is True
                      and FIXTURE_SECRET not in unknown.text and len(held.provider.effects) == 3)
                recovered = client.post(BILLING_CHECKOUT_PATH, json=unknown_body)
                check("real_HTTP_same_identity_reconciles_uncertain_creation_once",
                      recovered.status_code == 200 and recovered.json()["result"]["status"] == "reconciled"
                      and len(held.provider.effects) == 3)
                held.runtime.set_tenant_enabled("alpha", False)
                count = len(held.provider.calls)
                revoked = client.post(BILLING_PORTAL_PATH, json={key: value for key, value in {
                    **body, "request_id": "revoked"}.items() if key != "plan_ref"})
                check("real_HTTP_revoked_tenant_cannot_create_or_reconcile_sessions",
                      revoked.status_code == 401 and len(held.provider.calls) == count)


def _token_checks(check):
    import httpx
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from .http_auth import ServiceHttpAuthentication, EXTERNAL_JWT_AUTHENTICATION
    with tempfile.TemporaryDirectory(prefix="session-token-") as root, running_key_set() as (issuer, key_set):
        held = fixture(root)
        held.runtime.bind_subject(SubjectBindingRequest("alpha", issuer, "billing-subject"))
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_set["keys"] = [{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": "billing-key", "alg": "RS256"}]
        def app(configuration):
            authentication = ServiceHttpAuthentication(modes=(EXTERNAL_JWT_AUTHENTICATION,), issuer=issuer,
                audience=configuration.public_base_url + "/mcp", jwks_url=issuer + "/jwks", allow_loopback_issuer=True)
            return _application(held, configuration, authentication)
        with running_http(held, application_factory=app) as (base, _service):
            def headers(scope):
                token = jwt.encode({"iss": issuer, "sub": "billing-subject", "aud": base + "/mcp",
                    "exp": int(time.time()) + 120, "scope": scope}, key, algorithm="RS256", headers={"kid": "billing-key"})
                return {"Authorization": "Bearer " + token}
            body = {"record_type": sessions.SESSION_REQUEST_VERSION, "request_id": "token-session",
                    "policy_digest": held.adapter.policy_digest, "plan_ref": "basic"}
            with httpx.Client(base_url=base, trust_env=False, timeout=4) as client:
                limited = headers("provisioning:metadata")
                advertised = client.get(BILLING_PLANS_PATH, headers=limited).json()["result"]
                refused_response = client.post(BILLING_CHECKOUT_PATH, json=body, headers=limited)
                check("narrow_external_token_cannot_borrow_its_subjects_durable_billing_scope",
                      refused_response.status_code == 403 and not advertised["checkout_available"]
                      and not held.provider.calls and not held.secret_calls)
                accepted = client.post(BILLING_CHECKOUT_PATH, json=body, headers=headers("billing:manage"))
                check("explicit_verified_external_billing_scope_can_create_the_bound_session",
                      accepted.status_code == 200 and len(held.provider.effects) == 1
                      and dict(held.provider.calls[-1].parameters)["customer"] == "cus_alpha")


def _timeout_checks(check):
    import httpx
    with tempfile.TemporaryDirectory(prefix="session-timeout-") as root:
        held = fixture(root)
        entered, release = threading.Event(), threading.Event()
        held.provider.after_read = lambda call: (entered.set(), release.wait(2)) if call.path == sessions.ACCOUNT_PATH else None
        with running_http(held, application_factory=lambda config: _application(held, config),
                          request_timeout_seconds=0.1, maximum_concurrent_operations=1) as (base, _service):
            body = {"record_type": sessions.SESSION_REQUEST_VERSION, "request_id": "timeout-session",
                    "policy_digest": held.adapter.policy_digest, "plan_ref": "basic"}
            try:
                with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + held.keys["alpha"].key},
                                  trust_env=False, timeout=3) as client:
                    timeout = client.post(BILLING_CHECKOUT_PATH, json=body)
                    busy = client.post(BILLING_CHECKOUT_PATH, json=body)
                    check("session_response_timeout_never_claims_cancellation_or_replays_running_creation",
                          entered.is_set() and timeout.status_code == 504 and busy.status_code == 503
                          and timeout.json()["automatic_retry"] is False and not held.provider.effects)
                    release.set()
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        if any(row["payload"]["status"] == EFFECT_CONFIRMED for row in rows(held)):
                            break
                        time.sleep(0.01)
                    held.provider.after_read = None
                    # The late callback still holds the only worker slot for a
                    # moment, and the deadline here is 100 milliseconds. A busy
                    # or late answer is the documented signal to retry the same
                    # request identity, so wait for the final answer instead of
                    # assuming a fixed pause is long enough on a slow machine.
                    # The assertions are unchanged: the answer must be the
                    # reconciled session and the provider must see one effect.
                    deadline = time.monotonic() + 10
                    result = client.post(BILLING_CHECKOUT_PATH, json=body)
                    while result.status_code in (503, 504) and time.monotonic() < deadline:
                        time.sleep(0.05)
                        result = client.post(BILLING_CHECKOUT_PATH, json=body)
                    check("late_session_completion_is_reconciled_under_the_original_identity",
                          result.status_code == 200 and result.json()["result"]["status"] == "reconciled"
                          and len(held.provider.effects) == 1)
            finally:
                release.set()


def _host_checks(check):
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, configure_host, load_host_application
    with tempfile.TemporaryDirectory(prefix="session-host-") as root:
        held = fixture(root)
        root = Path(root)
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(root), "items": []}))
        configuration = {"record_type": HOST_CONFIGURATION_VERSION,
            "runtime": {"database_path": str(root / "host.db"), "writes_authorized": True},
            "http": {"public_base_url": "https://service.example", "allowed_hosts": ["service.example"]},
            "authentication": {}, "manifest_path": str(manifest),
            "tenants": [{"tenant_id": "alpha", "namespace": "tenant:alpha", "scopes": [*DEFAULT_SCOPES, "billing:manage"],
                "billing_customer": {"provider_customer_id": "cus_alpha", "provider_account_id": "acct_fixture"}}],
            "billing": {"webhook": {"account_id": "acct_fixture", "api_version": "fixture_version",
                "signing_secret_refs": ["env:UNRESOLVED_FIXTURE"]}, "policy": {"allowed_price_ids": ["price_basic", "price_other"]},
                "sessions": asdict(replace(held.policy, allow_network=False, allow_session_creation=False))}}
        path = root / "host.json"
        path.write_text(json.dumps(configuration))
        result = configure_host(str(path))
        application, _settings = load_host_application(str(path))
        issued = application.runtime.issue_key(TenantKeyIssue("alpha", "host loader"))
        current = application.runtime.authenticate_key(issued.key)
        options = application.billing_sessions.options(current)
        check("executable_host_loader_installs_exact_session_policy_without_network_or_activation",
              result["remote_accounts_created"] is False and current.entitlement == "metadata"
              and options["checkout_available"] is False and options["portal_available"] is False
              and application.billing_sessions.effects.policy_available(options["policy_digest"])
              and application.runtime.billing_customer_for(current)["provider_customer_id"] == "cus_alpha")
        application._workers.shutdown(wait=False)


def a_shorter_lease_cannot_shorten_the_wait_for_the_previous_attempt(root):
    """A long attempt is lost, then the host lowers its own request timeout.

    The wait before a new provider key cycle belongs to the attempt that ran,
    not to whichever caller comes next. The lease follows the request timeout,
    so a lowered timeout gives the next caller a shorter lease. If that shorter
    lease could shorten the wait, the new cycle would run while the eventually
    consistent provider search is still blind to the customer the lost attempt
    created, and the account would end with two.
    """
    held = fixture(root, bind_customers=False)
    window = MINIMUM_RECONCILIATION_SECONDS
    patient = replace(held.policy, timeout_seconds=10.0, reconciliation_seconds=window)
    slow = sessions.StripeSessionAdapter(held.runtime, patient, held.secret, transport=held.provider)
    install_policy(held, slow)
    held.provider.search_lag_seconds = PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
    start, late = held.clock["now"], patient.lease_seconds - 5
    held.provider.after_read = lambda call: advance(held, late) if call.path == ACCOUNT_PATH else None
    held.provider.lose_next_response = True
    quiet(lambda: slow.ensure_customer(principal(held)))
    held.provider.after_read = None
    held.provider.effects.clear()  # the provider no longer keeps the retired key
    hasty = replace(held.policy, timeout_seconds=1.0, reconciliation_seconds=window)
    quick = sessions.StripeSessionAdapter(held.runtime, hasty, held.secret, transport=held.provider)
    install_policy(held, quick)
    # A record that carries no usable deadline is a failed assertion here, not
    # a raised error, so a removed guard fails this check by name.
    stored = customer_rows(held)[0]["payload"].get("dispatch_deadline")
    if type(stored) not in (int, float):
        return False
    # Past the window and past a deadline rebuilt from the short lease, but
    # still inside the allowance that belongs to the attempt that ran.
    held.clock["now"] = start + window + hasty.lease_seconds + 1
    early = refused(lambda: quick.ensure_customer(principal(held)),
                    "billing_customer_search_not_current_yet")
    made_nothing_early = len(creations(held)) == 1 and len(held.provider.customers) == 1
    held.clock["now"] = stored + PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS
    quiet(lambda: quick.ensure_customer(principal(held)))
    settled = bound(held)
    return (early and made_nothing_early and stored == start + patient.lease_seconds
            and hasty.lease_seconds < patient.lease_seconds and len(creations(held)) == 1
            and len(held.provider.customers) == 1 and settled is not None
            and settled["provider_customer_id"] in held.provider.customers)


def run_customer_window_checks(check):
    """The wait before a new provider key cycle, under a changed host timeout."""
    with tempfile.TemporaryDirectory(prefix="stripe-customer-lease-") as root:
        check("a_shorter_request_timeout_cannot_shorten_the_wait_for_the_previous_attempt",
              a_shorter_lease_cannot_shorten_the_wait_for_the_previous_attempt(root))

    with tempfile.TemporaryDirectory(prefix="stripe-customer-version-") as root:
        held = fixture(root, bind_customers=False)
        quiet(lambda: held.adapter.create(principal(held), request(held, "first-checkout")))
        row = customer_rows(held)[0]
        current = row["payload"]["record_type"]
        with held.runtime._catalog.store(write=True) as store:
            older = {**row, "record_version": "rewritten-for-this-check",
                     "payload": {**row["payload"], "record_type": "service_billing_customer_effect/v1"}}
            held.runtime._catalog.commit(store, (older,), (held.runtime._catalog.guard(row),))
        check("a_creation_record_without_the_recorded_dispatch_deadline_is_refused_by_its_version",
              current == "service_billing_customer_effect/v2"
              and refused(lambda: held.runtime.release_billing_customer_account(
                  BillingCustomerAccountRelease("alpha", "acct_fixture", "acct_live")),
                  "unsupported_or_corrupt_record"))


def run_customer_mutant_controls(check):
    """Each control reruns a named customer scenario with one guard removed.

    The scenario's own predicate must fail, so the removed behavior is the
    reason that the named check passes. The scenarios themselves live beside
    the fixture in `stripe_session_checks.py` and run there as named checks.
    """
    from . import runtime as runtime_module
    from .billing_records import StripeCustomerProjection
    from .stripe_session_checks import (
        a_new_cycle_waits_until_the_search_can_show_the_last_attempt,
        a_released_account_reaches_checkout_at_the_current_account,
        a_truncated_search_is_not_read_as_no_customer,
        an_unbound_account_reaches_checkout_after_the_account_changes,
        another_accounts_customer_is_never_bound, another_provider_account_creates_no_customer,
        first_checkout_binds_one_customer, repeat_after_the_window_finds_the_existing_customer,
    )

    def lenient(cls, value, *, tenant_id, livemode, metadata_key=TENANT_METADATA_KEY):
        return cls(value["id"], tenant_id, livemode)

    def truncation_honoured_only_when_rows_came_back(response, found):
        """The rule before the repair: a truncated empty page read as absence."""
        return not (len(found) > 1 or (found and response["has_more"] is True))

    def deadline_taken_from_anywhere_but_the_attempts_own_record(self, state, now):
        """The stored dispatch deadline ignored, as it was before the repair.

        Any substitute that can land earlier than the moment the previous
        attempt could last have reached the provider reopens the same hole. The
        attempt's own start time is one such substitute, and unlike the lease
        of whichever caller comes next it is readable from the record alone.
        """
        if not state.get("attempts"):
            return True
        started = state.get("last_attempt_at", state["retry_before"])
        return now >= started + PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS

    controls = (
        ("removed_recorded_dispatch_deadline_is_detected",
         a_shorter_lease_cannot_shorten_the_wait_for_the_previous_attempt,
         lambda: patch.object(runtime_module.ServiceRuntime, "_search_can_show_the_previous_attempt",
                              deadline_taken_from_anywhere_but_the_attempts_own_record)),
        ("removed_truncated_search_refusal_is_detected",
         a_truncated_search_is_not_read_as_no_customer,
         lambda: patch.object(sessions, "_search_answers_for_the_whole_account",
                              truncation_honoured_only_when_rows_came_back)),
        ("removed_search_freshness_wait_before_a_new_key_cycle_is_detected",
         a_new_cycle_waits_until_the_search_can_show_the_last_attempt,
         lambda: patch.object(runtime_module.ServiceRuntime, "_search_can_show_the_previous_attempt",
                              lambda self, state, now: True)),
        ("removed_provider_account_change_route_is_detected",
         an_unbound_account_reaches_checkout_after_the_account_changes,
         lambda: patch.object(runtime_module.ServiceRuntime, "_only_the_provider_account_changed",
                              staticmethod(lambda stored, requested: False))),
        ("removed_provider_account_release_is_detected",
         a_released_account_reaches_checkout_at_the_current_account,
         lambda: patch.object(runtime_module.ServiceRuntime, "release_billing_customer_account",
                              lambda self, request: {"committed": False})),
        ("removed_customer_search_before_creation_is_detected",
         repeat_after_the_window_finds_the_existing_customer,
         lambda: patch.object(sessions.StripeSessionAdapter, "_search_customer",
                              lambda self, tenant_id, secret: None)),
        ("removed_account_identifier_in_customer_metadata_is_detected",
         first_checkout_binds_one_customer,
         lambda: patch.object(sessions.StripeSessionAdapter, "_customer_creation_parameters",
                              lambda self, tenant_id: ())),
        ("removed_customer_ownership_check_is_detected",
         another_accounts_customer_is_never_bound,
         lambda: patch.object(StripeCustomerProjection, "from_provider", classmethod(lenient))),
        ("removed_provider_account_check_before_creation_is_detected",
         another_provider_account_creates_no_customer,
         lambda: patch.object(sessions.StripeSessionAdapter, "_verified_account",
                              lambda self, secret: {})),
    )
    for name, scenario, mutant in controls:
        with tempfile.TemporaryDirectory(prefix="stripe-customer-mutant-") as root:
            with mutant():
                # A removed guard must fail the scenario's own predicate. An
                # error raised instead, such as a patched rule whose signature
                # no longer matches its caller, says nothing about the guard,
                # so it fails the control rather than passing it.
                try:
                    observed = bool(scenario(root))
                except Exception:
                    observed = None
        check(name, observed is False)


def run_transport_checks(check):
    _response_checks(check)
    _wire_checks(check)
    _http_checks(check)
    _token_checks(check)
    _timeout_checks(check)
    _host_checks(check)
