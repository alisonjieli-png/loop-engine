"""Boundary counterexamples for HTTP limits, host setup and signed billing.

These checks use temporary artifacts and loopback listeners. Identity and
billing signatures are local fixtures; no hosted identity, payment account,
model provider or public deployment is contacted.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import hmac
import json
from pathlib import Path
import threading
import time

from .http import ServiceHttpConfiguration, PROVISIONING_REQUEST_VERSION
from .http_auth import ServiceHttpAuthentication
from .http_test_fixtures import HttpDomainFixture, running_http, running_key_set


def _request(operation="list", **fields):
    return {"record_type": PROVISIONING_REQUEST_VERSION, "operation": operation, **fields}


def run_checks(check, root):
    _host_setup(check, root / "host")
    _limits(check, root / "limits")
    _key_endpoint(check, root / "keys")
    _billing(check, root / "billing")


def _host_setup(check, root):
    import httpx
    from ..harness_intelligence import HarnessIntelligenceDraft, item_from_body
    from .http_entrypoint import configure_host, load_host_application, load_host_manifest
    from .records import TenantKeyIssue, ServiceRuntimeError
    root.mkdir()
    artifacts = root / "artifacts"
    artifacts.mkdir()
    body = "Pinned host-reviewed instruction body"
    (artifacts / "instruction.txt").write_text(body)
    item = item_from_body(HarnessIntelligenceDraft("skill.host", "skill", "Host-reviewed source",
        "context_intelligence", "context:host/v1", "MIT"), body)
    manifest = {"record_type": "host_attested_intelligence_manifest/v1", "artifact_root": str(artifacts),
        "items": [{"reference": item.reference(), "body_path": "instruction.txt", "approval_ref": "host-review:fixture",
                   "grants": [{"tenant_id": "host", "body_allowed": True, "metering": "required"}]}]}
    manifest_path, config_path = root / "manifest.json", root / "service.json"
    manifest_path.write_text(json.dumps(manifest))
    def build(configuration):
        config_path.write_text(json.dumps({"record_type": "service_http_host_configuration/v1",
            "runtime": {"database_path": str(root / "state.db"), "writes_authorized": True},
            "http": asdict(configuration), "authentication": {"modes": ["host_key"]},
            "manifest_path": str(manifest_path), "tenants": [{"tenant_id": "host", "namespace": "host",
                "operator_entitlement": {"valid_until": int(time.time()) + 3600, "evidence_ref": "local-host-test"}}]}))
        configure_host(str(config_path))
        return load_host_application(str(config_path))[0]
    with running_http(None, application_factory=build) as (base, application):
        issued = application.runtime.issue_key(TenantKeyIssue("host", "host-loader-acceptance"))
        with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + issued.key}, trust_env=False) as client:
            result = client.post("/api/v1/provisioning", json=_request("read", identity=item.identity,
                request_id="host-file", expected_digest=item.digest))
            check("host_configuration_entrypoint_serves_exact_reviewed_files_through_real_HTTP",
                  result.status_code == 200 and result.json()["result"]["body"] == body
                  and result.json()["result"]["qualification_basis"] == "host_attested")
            application.runtime.set_grants("host", ())
            reopened, _ = load_host_application(str(config_path))
            check("serving_restart_does_not_reinstall_manifest_grants_after_revocation",
                  reopened.provisioning.invoke(issued.key, "list")["items"] == [])
    changed = json.loads(json.dumps(manifest))
    changed["items"][0]["body_path"] = "../outside.txt"
    (root / "outside.txt").write_text(body)
    unsafe = root / "unsafe.json"
    unsafe.write_text(json.dumps(changed))
    try:
        load_host_manifest(str(unsafe))
    except ServiceRuntimeError as error:
        refused = error.code == "unsafe_artifact_path"
    else:
        refused = False
    check("host_manifest_cannot_escape_its_declared_artifact_root", refused)
    (artifacts / "instruction.txt").write_text("X" * len(body))
    try:
        load_host_manifest(str(manifest_path))
    except ServiceRuntimeError as error:
        refused = error.code == "artifact_digest_mismatch"
    else:
        refused = False
    check("host_review_is_bound_to_exact_bytes_not_only_an_item_name", refused)


def _limits(check, root):
    import httpx
    from ..provisioning_server import ProvisioningGrant, ProvisioningItemBinding
    from .records import TenantKeyIssue
    root.mkdir()
    fixture = HttpDomainFixture(root)
    with running_http(fixture, maximum_response_bytes=8192, maximum_inline_body_bytes=128) as (base, _service):
        limited = fixture.runtime.issue_key(TenantKeyIssue("alpha", "metadata only", scopes=("provisioning:metadata",)))
        with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + limited.key}, trust_env=False) as client:
            listing = client.post("/api/v1/provisioning", json=_request()).json()["result"]
            denied = client.post("/api/v1/provisioning", json=_request("read", identity="skill.alpha", request_id="no-scope"))
            check("metadata_only_durable_key_neither_advertises_nor_performs_body_access",
                  not any(row["body_allowed"] for row in listing["items"])
                  and denied.status_code == 403 and not fixture.reads)
        updated = replace(fixture.catalogue.items["skill.alpha"], purpose="EXCESS_METADATA" * 1000)
        fixture.catalogue.items[updated.identity] = updated
        fixture.bindings[updated.identity] = ProvisioningItemBinding.from_item(updated)
        fixture.runtime.set_grants("alpha", (ProvisioningGrant("alpha", fixture.bindings[updated.identity], True),))
        with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False) as client:
            limited_response = client.post("/api/v1/provisioning", json=_request())
            check("response_limit_refuses_the_whole_payload_without_partial_metadata_disclosure",
                  limited_response.status_code == 413 and len(limited_response.content) < 8192
                  and "EXCESS_METADATA" not in limited_response.text)
    delayed_root = root / "delayed"
    delayed_root.mkdir()
    fixture = HttpDomainFixture(delayed_root)
    entered, release = threading.Event(), threading.Event()
    fixture.before_read = lambda _item: (entered.set(), release.wait(2))
    with running_http(fixture, request_timeout_seconds=0.1, maximum_concurrent_operations=1) as (base, _service):
        try:
            with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False, timeout=2) as client:
                late = client.post("/api/v1/provisioning", json=_request("read", identity="skill.alpha", request_id="late-once"))
                busy = client.get("/api/v1/session")
                check("expired_response_wait_is_not_success_and_running_work_keeps_its_capacity_slot",
                      entered.is_set() and late.status_code == 504 and busy.status_code == 503
                      and late.json()["effect_commitment"] == "not_asserted"
                      and late.json()["automatic_retry"] is False)
                release.set()
                deadline = time.monotonic() + 1
                while fixture.usage()["records"] == 0 and time.monotonic() < deadline:
                    time.sleep(0.005)
                check("timed_out_callback_can_commit_once_without_adapter_replay",
                      len(fixture.reads) == 1 and fixture.usage()["records"] == 1)
        finally:
            release.set()


def _key_endpoint(check, root):
    import httpx
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from .records import SubjectBindingRequest
    root.mkdir()
    fixture = HttpDomainFixture(root)
    with running_key_set() as (base, state):
        issuer = base + "/issuer"
        fixture.runtime.bind_subject(SubjectBindingRequest("alpha", issuer, "subject"))
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        state["keys"] = [{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": "key", "alg": "RS256"}]
        def credential(service):
            return jwt.encode({"iss": issuer, "aud": service + "/mcp", "sub": "subject", "exp": int(time.time()) + 60,
                               "scope": "provisioning:metadata"}, key, algorithm="RS256", headers={"kid": "key"})
        def auth(configuration):
            return ServiceHttpAuthentication(modes=("external_jwt",), issuer=issuer,
                audience=configuration.public_base_url + "/mcp",
                jwks_url=base + "/jwks", allow_loopback_issuer=True, maximum_key_set_bytes=1024)
        state.update(status=302, location=base + "/not-authorized")
        with running_http(fixture, authentication=auth) as (service, _application):
            refused = httpx.get(service + "/api/v1/session", headers={"Authorization": "Bearer " + credential(service)}, trust_env=False)
            check("configured_key_endpoint_cannot_redirect_authentication_to_another_resource",
                  refused.status_code == 401 and "/not-authorized" not in state["paths"])
        state.update(status=200, padding="X" * 2048)
        with running_http(fixture, authentication=auth) as (service, _application):
            refused = httpx.get(service + "/api/v1/session", headers={"Authorization": "Bearer " + credential(service)}, trust_env=False)
            check("external_key_set_respects_its_byte_allowance", refused.status_code == 401)


def _billing(check, root):
    import httpx
    from unittest.mock import patch
    from .billing import StripeEventProcessor
    from .billing_records import (StripeWebhookConfig, StripeEntitlementPolicy, StripeSubscriptionResolver,
                                 StripeCustomerSubscriptionSnapshot, StripeSubscriptionState)
    from .records import BillingCustomerBindingRequest, ServiceCommitUnknown
    root.mkdir()
    fixture = HttpDomainFixture(root, operator_access=False)
    fixture.runtime.bind_billing_customer(BillingCustomerBindingRequest("alpha", "cus_alpha", "acct_fixture"))
    policy = StripeEntitlementPolicy(("price_fixture",))
    fixture.runtime.configure_billing_policy(policy)
    configuration = StripeWebhookConfig("acct_fixture", "fixture_version", ("env:LOCAL_SIGNING_FIXTURE",))
    secret = "LOCAL_SIGNATURE_TEST_ONLY"
    status = {"subscriptions": ()}
    def snapshot(customer):
        return StripeCustomerSubscriptionSnapshot("acct_fixture", customer, "fixture_version", False,
            status["subscriptions"], hashlib.sha256(repr(status["subscriptions"]).encode()).hexdigest())
    processor = StripeEventProcessor(fixture.runtime, configuration, policy, lambda _ref: secret,
                                     StripeSubscriptionResolver("local-current-subscriptions", snapshot))
    def event(identity):
        timestamp = int(time.time())
        body = json.dumps({"id": identity, "object": "event", "api_version": "fixture_version", "livemode": False,
            "type": "customer.subscription.updated", "created": timestamp, "account": "acct_fixture",
            "data": {"object": {"id": "sub_fixture", "customer": "cus_alpha"}}}).encode()
        signature = hmac.new(secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
        return body, "t=" + str(timestamp) + ",v1=" + signature
    with running_http(fixture, billing_processor=processor) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False) as client:
            body, signature = event("evt_active")
            wrong = client.post("/api/v1/billing/webhook", content=body,
                headers={"Content-Type": "application/json", "Stripe-Signature": "t=0,v1=" + "0" * 64})
            check("webhook_does_not_accept_unsigned_or_wrongly_signed_subscription_authority",
                  wrong.status_code == 400 and fixture.runtime.authenticate_key(fixture.keys["alpha"].key).entitlement == "metadata")
            with patch.object(type(fixture.runtime._catalog), "commit", side_effect=ServiceCommitUnknown()):
                uncertain = client.post("/api/v1/billing/webhook", content=body,
                    headers={"Content-Type": "application/json", "Stripe-Signature": signature})
            check("unknown_billing_commit_is_a_retryable_HTTP_failure_not_a_success_acknowledgment",
                  uncertain.status_code == 503 and uncertain.json()["error"]["code"] == "billing_commit_unknown"
                  and uncertain.json()["error"]["details"]["committed"] is None)
            status["subscriptions"] = (StripeSubscriptionState("sub_fixture", "cus_alpha", "active",
                (("price_fixture", int(time.time()) + 3600),), True),)
            accepted = client.post("/api/v1/billing/webhook", content=body,
                headers={"Content-Type": "application/json", "Stripe-Signature": signature})
            duplicate = client.post("/api/v1/billing/webhook", content=body,
                headers={"Content-Type": "application/json", "Stripe-Signature": signature})
            check("actual_HTTP_signed_webhook_reconciles_current_state_and_deduplicates_delivery",
                  accepted.status_code == duplicate.status_code == 200
                  and accepted.json()["result"]["entitlement"] == "bodies"
                  and duplicate.json()["result"]["status"] == "duplicate")
    pending = StripeEventProcessor(fixture.runtime, configuration, policy, lambda _ref: secret)
    with running_http(fixture, billing_processor=pending) as (base, _service):
        body, signature = event("evt_pending")
        response = httpx.post(base + "/api/v1/billing/webhook", content=body,
            headers={"Content-Type": "application/json", "Stripe-Signature": signature}, trust_env=False)
        check("unreconciled_signed_webhook_retains_durable_pending_identity_without_false_activation",
              response.status_code == 503 and response.json()["effect_commitment"] == "durable_pending"
              and response.json()["error"]["details"]["event_id"] == "evt_pending"
              and fixture.runtime.authenticate_key(fixture.keys["alpha"].key).entitlement == "metadata")
