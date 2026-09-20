"""Signed-event, persistent reconciliation, and read-only provider contract checks.

All signatures use local fixture secrets. Provider transports are injected
read-only fixtures; no Stripe account, checkout, payment, or charge is used.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading

from ...catalog.protocol import CatalogBatchAcknowledgment
from ...catalog.stores.sqlite_store import SQLiteRecordStore
from .billing import StripeEventProcessor
from .billing_records import (
    StripeCustomerSubscriptionSnapshot, StripeEntitlementPolicy, StripeProviderConfig,
    StripeSubscriptionResolver, StripeSubscriptionState, StripeWebhookConfig,
)
from .records import (BillingCustomerBindingRequest, ServiceRuntimeConfig,
                       ServiceRuntimeError, TenantKeyIssue, TenantRegistration)
from .runtime import ServiceRuntime
from .storage import ServiceCatalogBinding
from .stripe_provider import StripeSubscriptionReader, _NoRedirect, _opener

SECRET = "local-contract-fixture-not-an-account-secret"
API = "fixture_snapshot_api_version"


def body(identity="evt_fixture", *, kind="customer.subscription.updated", created=1, **extra):
    event = {"id": identity, "object": "event", "api_version": API, "livemode": False,
             "created": created, "type": kind,
             "data": {"object": {"id": "sub_fixture", "customer": "cus_fixture"}}}
    event.update(extra)
    return json.dumps(event).encode()


def signature(payload, timestamp=1000, secret=SECRET):
    signed = str(timestamp).encode() + b"." + payload
    return f"t={timestamp},v1=" + hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


def snapshot(*, status="active", paid=True, price="price_fixture", expiry=2000, **changes):
    row = StripeSubscriptionState("sub_fixture", "cus_fixture", status, ((price, expiry),), paid)
    base = StripeCustomerSubscriptionSnapshot("acct_fixture", "cus_fixture", API, False, (row,), "a" * 64)
    return replace(base, **changes)


def fixture(folder, *, resolver=True, allow_trialing=False, price_ids=("price_fixture",)):
    config = ServiceRuntimeConfig(str(Path(folder) / "billing.sqlite"), writes_authorized=True)
    runtime = ServiceRuntime(config, clock=lambda: 1000)
    runtime.register_tenant(TenantRegistration("tenant", "tenant-space"))
    key = runtime.issue_key(TenantKeyIssue("tenant", "fixture"))
    runtime.bind_billing_customer(BillingCustomerBindingRequest("tenant", "cus_fixture", "acct_fixture"))
    policy = StripeEntitlementPolicy(price_ids, allow_trialing)
    runtime.configure_billing_policy(policy)
    current, calls = [snapshot()], []
    def resolve(customer):
        calls.append(customer)
        if isinstance(current[0], Exception):
            raise current[0]
        return current[0]
    processor = StripeEventProcessor(runtime,
        StripeWebhookConfig("acct_fixture", API, ("env:STRIPE_FIXTURE",)), policy,
        lambda reference: SECRET, StripeSubscriptionResolver("fixture:current", resolve) if resolver else None)
    return runtime, processor, key, current, calls


def deliver(processor, payload):
    return processor.handle(payload, signature(payload))


def refuses(action, code=None):
    try:
        action()
    except ServiceRuntimeError as error:
        return code is None or error.code == code
    return False


def run_checks():
    tests = []
    def check(name, action):
        try:
            with TemporaryDirectory() as folder:
                passed = bool(action(folder))
            detail = ""
        except Exception as error:
            passed, detail = False, type(error).__name__ + ": " + str(error)
        tests.append({"test": name, "passed": passed, "detail": detail})

    def valid(folder):
        runtime, processor, key, _, calls = fixture(folder)
        result = deliver(processor, body())
        reopened = ServiceRuntime(runtime.config, clock=lambda: 1000)
        return (result.committed is True and result.status == "applied" and calls == ["cus_fixture"]
                and reopened.authenticate_key(key.key).entitlement == "bodies")
    check("signed_event_reconciles_current_paid_state_and_survives_restart", valid)

    for label, header, altered in (
            ("wrong_signature", lambda payload: signature(payload, secret="another"), lambda payload: payload),
            ("expired", lambda payload: signature(payload, timestamp=1), lambda payload: payload),
            ("future", lambda payload: signature(payload, timestamp=2000), lambda payload: payload),
            ("missing_v1", lambda payload: signature(payload).replace("v1=", "v0="), lambda payload: payload),
            ("duplicate_timestamp", lambda payload: signature(payload) + ",t=1000", lambda payload: payload),
            ("changed_raw_body", signature, lambda payload: payload + b" ")):
        def invalid(folder, header=header, altered=altered):
            runtime, processor, key, _, calls = fixture(folder)
            payload = body()
            rejected = refuses(lambda: processor.handle(altered(payload), header(payload)))
            with runtime._catalog.store() as store:
                events = runtime._catalog.rows(store, "service_stripe_event", "tenant")
            return rejected and not calls and not events and runtime.authenticate_key(key.key).entitlement == "metadata"
        check("signature_" + label + "_refuses_before_state_effects", invalid)

    def malformed_json(folder):
        _, processor, _, _, calls = fixture(folder)
        payload = body().replace(b'"livemode": false', b'"livemode": false, "livemode": true')
        return refuses(lambda: processor.handle(payload, signature(payload)), "invalid_stripe_payload") and not calls
    check("duplicate_json_keys_refuse_even_with_valid_signature", malformed_json)

    def malformed_timestamp(folder):
        _, processor, _, _, calls = fixture(folder)
        payload = body()
        return (refuses(lambda: processor.handle(payload, "t=١٠٠٠,v1=" + "a" * 64), "invalid_stripe_signature")
                and refuses(lambda: processor.handle(payload, "t=" + "1" * 1000 + ",v1=" + "a" * 64), "invalid_stripe_signature")
                and not calls)
    check("non_ascii_and_oversized_signature_timestamps_have_typed_refusals", malformed_timestamp)

    for label, change in (("api_version", {"api_version": "unknown"}),
                           ("mode", {"livemode": True}), ("account", {"account": "acct_other"})):
        def mismatch(folder, change=change):
            _, processor, _, _, calls = fixture(folder)
            payload = body(**change)
            return refuses(lambda: deliver(processor, payload), "unsupported_stripe_event") and not calls
        check("signed_" + label + "_mismatch_refuses", mismatch)

    def duplicate(folder):
        runtime, processor, key, _, calls = fixture(folder)
        payload = body()
        deliver(processor, payload)
        formatted = json.dumps(json.loads(payload), indent=2).encode()
        result = deliver(processor, formatted)
        return result.status == "duplicate" and len(calls) == 1 and runtime.authenticate_key(key.key).entitlement == "bodies"
    check("duplicate_event_identity_not_delivery_format_controls_replay", duplicate)

    def conflicting_id(folder):
        runtime, processor, key, _, calls = fixture(folder)
        deliver(processor, body())
        changed = body(data={"object": {"id": "sub_fixture", "customer": "cus_fixture", "status": "changed"}})
        return refuses(lambda: deliver(processor, changed), "stripe_event_identity_conflict") and len(calls) == 1
    check("same_event_identity_cannot_cover_changed_provider_data", conflicting_id)

    def checkout(folder):
        runtime, processor, key, _, calls = fixture(folder)
        result = deliver(processor, body(kind="checkout.session.completed"))
        return result.status == "ignored" and not calls and runtime.authenticate_key(key.key).entitlement == "metadata"
    check("checkout_completion_or_redirect_never_grants_access", checkout)

    def spoofed_tenant(folder):
        runtime, processor, _, _, _ = fixture(folder)
        runtime.register_tenant(TenantRegistration("other", "other-space"))
        other = runtime.issue_key(TenantKeyIssue("other", "fixture"))
        payload = body(data={"object": {"id": "sub_fixture", "customer": "cus_fixture", "metadata": {"tenant_id": "other"}}})
        result = deliver(processor, payload)
        return result.tenant_id == "tenant" and runtime.authenticate_key(other.key).entitlement == "metadata"
    check("event_metadata_cannot_select_another_tenant", spoofed_tenant)

    def customer_unknown(folder):
        _, processor, _, _, calls = fixture(folder)
        payload = body(data={"object": {"id": "sub_other", "customer": "cus_other"}})
        return refuses(lambda: deliver(processor, payload), "not_found") and not calls
    check("unbound_customer_does_not_create_or_select_a_tenant", customer_unknown)

    def out_of_order(folder):
        runtime, processor, key, current, calls = fixture(folder)
        current[0] = snapshot(status="canceled")
        deliver(processor, body("evt_new", created=999))
        result = deliver(processor, body("evt_old", created=1))
        return result.status == "applied" and len(calls) == 2 and runtime.authenticate_key(key.key).entitlement == "metadata"
    check("out_of_order_events_reconcile_current_state_not_created_order", out_of_order)

    def same_timestamp(folder):
        runtime, processor, key, current, calls = fixture(folder)
        deliver(processor, body("evt_a", created=1))
        current[0] = snapshot(status="canceled")
        deliver(processor, body("evt_b", created=1))
        return len(calls) == 2 and runtime.authenticate_key(key.key).entitlement == "metadata"
    check("distinct_events_in_the_same_second_are_both_processed", same_timestamp)

    def resume(folder):
        runtime, processor, key, _, _ = fixture(folder, resolver=False)
        result = deliver(processor, body())
        persisted = ServiceRuntime(runtime.config, clock=lambda: 1000)
        installed = StripeEventProcessor(persisted, processor.config, processor.policy, lambda reference: SECRET,
            StripeSubscriptionResolver("fixture:later", lambda customer: snapshot()))
        resumed = installed.resume_event("evt_fixture")
        return (result.status == "pending" and result.committed is True and resumed.status == "applied"
                and persisted.authenticate_key(key.key).entitlement == "bodies")
    check("verified_pending_events_resume_after_restart_without_raw_payload_storage", resume)

    def outage(folder):
        runtime, processor, key, current, _ = fixture(folder)
        deliver(processor, body("evt_active"))
        current[0] = RuntimeError("provider outage")
        result = deliver(processor, body("evt_unavailable"))
        return result.status == "pending" and runtime.authenticate_key(key.key).entitlement == "metadata"
    check("reconciliation_outage_invalidates_previous_paid_access", outage)

    for label, change in (("incomplete", {"complete": False}), ("account", {"account_id": "acct_other"}),
                           ("mode", {"livemode": True}), ("api_version", {"api_version": "unknown"})):
        def snapshot_mismatch(folder, change=change):
            runtime, processor, key, current, _ = fixture(folder)
            current[0] = snapshot(**change)
            result = deliver(processor, body())
            return result.status == "pending" and runtime.authenticate_key(key.key).entitlement == "metadata"
        check("snapshot_" + label + "_cannot_grant_entitlement", snapshot_mismatch)

    for label, data in (("unpaid", snapshot(paid=False)), ("canceled", snapshot(status="canceled")),
                        ("unconfigured_price", snapshot(price="price_other")),
                        ("expired_period", snapshot(expiry=500)), ("unknown_invoice", snapshot(paid=None)),
                        ("paused_collection", snapshot(subscriptions=(replace(snapshot().subscriptions[0], collection_paused=True),))),
                        ("trial_not_authorized", snapshot(status="trialing", subscriptions=(replace(snapshot().subscriptions[0], status="trialing", trial_end=1500),)))):
        def no_access(folder, data=data):
            runtime, processor, key, current, _ = fixture(folder)
            current[0] = data
            result = deliver(processor, body())
            return result.entitlement == "metadata" and runtime.authenticate_key(key.key).entitlement == "metadata"
        check(label + "_does_not_grant_paid_access", no_access)

    def trial(folder):
        runtime, processor, key, current, _ = fixture(folder, allow_trialing=True)
        current[0] = snapshot(subscriptions=(replace(snapshot().subscriptions[0], status="trialing", latest_invoice_paid=None, trial_end=1500),))
        return deliver(processor, body()).entitlement == "bodies" and runtime.authenticate_key(key.key).entitlement == "bodies"
    check("trial_access_requires_explicit_owner_policy", trial)

    def policy_change(folder):
        runtime, processor, key, _, _ = fixture(folder)
        version = runtime.configure_billing_policy(processor.policy)["record_version"]
        deliver(processor, body())
        denied = refuses(lambda: runtime.configure_billing_policy(StripeEntitlementPolicy(("price_other",))))
        runtime.configure_billing_policy(StripeEntitlementPolicy(("price_other",)), expected_version=version)
        return denied and runtime.authenticate_key(key.key).entitlement == "metadata"
    check("billing_policy_change_invalidates_old_grants_and_requires_exact_revision", policy_change)

    def admin_revocation(folder):
        runtime, processor, key, _, _ = fixture(folder)
        runtime.revoke_entitlement("tenant")
        result = deliver(processor, body())
        return result.entitlement == "metadata" and runtime.authenticate_key(key.key).entitlement == "metadata"
    check("Stripe_events_do_not_override_administrative_access_revocation", admin_revocation)

    def disabled_tenant(folder):
        runtime, processor, key, _, _ = fixture(folder)
        runtime.set_tenant_enabled("tenant", False)
        result = deliver(processor, body())
        return result.entitlement == "metadata" and refuses(lambda: runtime.authenticate_key(key.key), "unauthorized")
    check("billing_projection_does_not_claim_access_for_a_disabled_tenant", disabled_tenant)

    def concurrent(folder):
        runtime, processor, key, current, _ = fixture(folder)
        entered, release = threading.Event(), threading.Event()
        def stale(customer):
            captured = snapshot()
            entered.set()
            if not release.wait(timeout=10):
                raise RuntimeError("fixture coordination timeout")
            return captured
        first = StripeEventProcessor(runtime, processor.config, processor.policy, lambda reference: SECRET,
                                     StripeSubscriptionResolver("fixture:slow", stale))
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(deliver, first, body("evt_stale", created=1))
            if not entered.wait(timeout=10):
                raise RuntimeError("fixture coordination timeout")
            current[0] = snapshot(status="canceled")
            latest = deliver(processor, body("evt_latest", created=1))
            release.set()
            older = pending.result(timeout=10)
        return (latest.status == "applied" and older.diagnostic_code == "concurrent_reconciliation"
                and runtime.authenticate_key(key.key).entitlement == "metadata")
    check("stale_concurrent_provider_response_cannot_overwrite_newer_decision", concurrent)

    def unknown_commit(folder):
        runtime, processor, key, _, _ = fixture(folder)
        class Lost:
            def __init__(self, write): self.store = SQLiteRecordStore(runtime.config.database_path, read_only=not write)
            def __getattr__(self, name): return getattr(self.store, name)
            def apply_batch(self, request):
                self.store.apply_batch(request)
                return CatalogBatchAcknowledgment(request.digest, None)
        uncertain = ServiceRuntime(runtime.config, storage=ServiceCatalogBinding(runtime.config, Lost), clock=lambda: 1000)
        failed = StripeEventProcessor(uncertain, processor.config, processor.policy, lambda reference: SECRET)
        result = deliver(failed, body())
        resumed = processor.resume_event("evt_fixture")
        return result.committed is None and result.status == "commit_unknown" and resumed.status == "applied"
    check("lost_event_commit_acknowledgment_remains_unknown_until_reconciled", unknown_commit)

    passed = sum(row["passed"] for row in tests)
    return {"record_type": "stripe_billing_domain_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}


def provider_checks():
    tests = []
    def check(name, value): tests.append({"test": name, "passed": bool(value)})
    calls, secrets = [], []
    config = StripeProviderConfig("acct_fixture", API, "env:TEST", allow_network=True)
    def transport(request, key):
        calls.append(request)
        if request.path == "/v1/account": return {"id": "acct_fixture"}
        return {"object": "list", "has_more": False, "data": [{"object": "subscription",
            "id": "sub_fixture", "customer": "cus_fixture", "livemode": False, "status": "active",
            "items": {"has_more": False, "data": [{"price": {"id": "price_fixture"}, "current_period_end": 2000}]},
            "latest_invoice": {"customer": "cus_fixture", "paid": True, "status": "paid"},
            "pause_collection": None, "trial_end": None}]}
    reader = StripeSubscriptionReader(config, lambda ref: secrets.append(ref) or SECRET, transport=transport)
    result = reader.resolve("cus_fixture")
    check("provider_reader_binds_account_customer_version_mode_and_complete_items",
          result.complete and result.account_id == config.account_id and result.customer_id == "cus_fixture"
          and result.api_version == API and result.subscriptions[0].latest_invoice_paid is True
          and dict(calls[-1].query)["status"] == "all")
    calls.clear();secrets.clear()
    denied = StripeSubscriptionReader(replace(config, allow_network=False), lambda ref: secrets.append(ref), transport=transport)
    check("provider_network_denial_precedes_secret_or_transport",
          refuses(lambda: denied.resolve("cus_fixture"), "stripe_network_authority_required") and not calls and not secrets)
    wrong = StripeSubscriptionReader(config, lambda ref: SECRET, transport=lambda request, key: {"id": "acct_other"})
    check("provider_wrong_account_refuses", refuses(lambda: wrong.resolve("cus_fixture"), "stripe_account_mismatch"))
    check("provider_refuses_redirect_before_following_it", refuses(lambda: _NoRedirect().redirect_request(
        None, None, 302, "redirect", {}, "https://other.example"), "stripe_redirect_refused"))
    from unittest.mock import patch
    # The opener classes come from the provider module, which holds the
    # network registration; this checks file needs none of its own.
    from . import stripe_provider as provider
    def proxies(opener):
        return [handler.proxies for handler in opener.handlers if isinstance(handler, provider.ProxyHandler)]
    with patch.dict("os.environ", {"HTTPS_PROXY": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9"}):
        check("provider_reader_ignores_proxy_settings_from_the_environment", not any(proxies(_opener())))
        # Known-wrong control: the default opener does adopt that setting.
        check("default_opener_would_send_the_secret_through_an_environment_proxy",
              any(proxies(provider.build_opener(_NoRedirect()))))
    def truncated(request, key):
        value = transport(request, key)
        if request.path != "/v1/account": value["data"][0]["items"]["has_more"] = True
        return value
    check("provider_partial_item_list_is_not_a_complete_snapshot", refuses(lambda:
        StripeSubscriptionReader(config, lambda ref: SECRET, transport=truncated).resolve("cus_fixture"),
        "incomplete_stripe_subscription_items"))
    return {"record_type": "stripe_read_provider_test/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
