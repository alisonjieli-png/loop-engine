"""Signed-token and real loopback account-flow checks, with provider user fixtures.

These checks distinguish browser identity from protocol-resource tokens and
exercise the existing catalogue. They do not claim hosted provider or email
delivery qualification.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import time
from unittest.mock import patch

from . import browser_identity


def _raced_sign_out(fixture, policy, adapter, user, token):
    """Sign one session out, then check it while the retention removal runs at a chosen moment.

    Returns a function of one rounding rule. It signs a fresh session out, sets
    the runtime clock to that rule applied to the token expiry, runs the
    removal inside the provider call of a new request, and answers whether the
    request was accepted.
    """
    from types import SimpleNamespace
    import uuid
    import jwt
    from .browser_identity import BrowserIdentityAdapter
    from .http_auth import HttpAuthenticationError
    from .retention import remove_expired_session_revocations

    def sweeping(request):
        remove_expired_session_revocations(fixture.runtime)
        return user(request)
    checked = BrowserIdentityAdapter(fixture.runtime, policy, lambda _: "sb_publishable_local_fixture",
                                     transport=sweeping)

    def accepted(rounding):
        # A whole second plus one half, so rounding down and rounding up differ,
        # and a token identity of its own, so each call signs out a new session.
        credential = token(exp=int(time.time()) + 60.5, jti=uuid.uuid4().hex)
        adapter.logout(SimpleNamespace(credential=credential))
        moment = rounding(jwt.decode(credential, options={"verify_signature": False})["exp"])
        with patch.object(fixture.runtime, "_clock", lambda: moment):
            try:
                checked.authenticate(credential)
            except HttpAuthenticationError:
                return False
        return True
    return accepted


def run_checks(check, root: Path):
    import httpx
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from .browser_identity import BrowserIdentityAdapter, BrowserIdentityConfiguration
    from .access import ServiceAccessAdministration, ServiceClientAccessPolicy
    from .http import ServiceHttpApplication
    from .http_auth import HttpAuthenticationError
    from .http_test_fixtures import HttpDomainFixture, running_http, running_key_set
    from .records import ServiceRuntimeError, SubjectBindingRequest

    fixture = HttpDomainFixture(root)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    state = {"confirmed": True, "wrong_subject": False, "provider_calls": 0}
    with running_key_set() as (provider, public_keys):
        public_keys["keys"] = [{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())),
                                "kid": "identity-test", "alg": "RS256", "use": "sig"}]
        policy = BrowserIdentityConfiguration(provider, "fixture:publishable", "customers",
            registration_enabled=True, allow_network=True, allow_loopback=True)
        def token(**changes):
            return jwt.encode({"iss": provider + "/auth/v1", "aud": "authenticated", "sub": "verified-user",
                "exp": int(time.time()) + 600, "iat": int(time.time()), "role": "authenticated",
                "is_anonymous": False, "tenant_id": "alpha", **changes}, key,
                algorithm="RS256", headers={"kid": "identity-test"})
        def user(request):
            state["provider_calls"] += 1
            subject = jwt.decode(request.access_token, options={"verify_signature": False})["sub"]
            return {"id": "wrong-user" if state["wrong_subject"] else subject, "role": "authenticated",
                    "is_anonymous": False, "email_confirmed_at": "2026-01-01T00:00:00Z" if state["confirmed"] else None,
                    "user_metadata": {"email_verified": True, "tenant_id": "alpha", "role": "administrator"}}
        adapter = BrowserIdentityAdapter(fixture.runtime, policy, lambda _: "sb_publishable_local_fixture",
            starter_bindings=(fixture.bindings["skill.alpha"],), transport=user)
        client_access = ServiceAccessAdministration(fixture.runtime, ServiceClientAccessPolicy(writes_authorized=True))
        create = lambda config: ServiceHttpApplication(fixture.runtime, fixture.provisioning, config,
            browser_identity=adapter, client_access=client_access)
        with running_http(fixture, application_factory=create) as (base, application):
            with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
                encoded = token()
                headers = {"Authorization": "Bearer " + encoded}
                activation = {"record_type": "service_account_activation_request/v1"}
                config = client.get("/api/v1/account/identity")
                check("browser_identity_public_configuration_exposes_only_the_publishable_key",
                      config.status_code == 200 and config.json()["result"]["publishable_key"] == "sb_publishable_local_fixture"
                      and "secret" not in json.dumps(config.json()).lower())
                missing = client.get("/api/v1/session", headers=headers)
                check("valid_identity_does_not_silently_create_a_customer_during_a_read", missing.status_code == 401)
                bad = client.post("/api/v1/account/activate", headers=headers,
                                  json={**activation, "tenant_id": "alpha", "scopes": ["access:manage"]})
                check("activation_rejects_client_supplied_tenant_and_authority", bad.status_code == 400)
                result = client.post("/api/v1/account/activate", headers=headers, json=activation)
                tenant = result.json()["result"]["tenant_id"]
                again = client.post("/api/v1/account/activate", headers=headers, json=activation)
                check("HTTP_activation_creates_exactly_one_server_bound_customer",
                      result.status_code == again.status_code == 200 and tenant != "alpha"
                      and result.json()["result"]["created"] and not again.json()["result"]["created"])
                session = client.get("/api/v1/session", headers=headers).json()["result"]
                check("browser_identity_maps_to_the_durable_subject_not_editable_user_metadata",
                      session["authentication_mode"] == "browser_identity" and session["principal"]["tenant_id"] == tenant
                      and session["principal"]["entitlement"] == "metadata" and "access:manage" not in session["principal"]["scopes"])
                search = client.post("/api/v1/retrieval", headers=headers, json={
                    "record_type": "service_retrieval_request/v2", "query": "alpha", "mode": "lexical"}).json()["result"]
                check("new_account_sees_only_host_selected_starter_metadata_without_free_body_access",
                      len(search["hits"]) == 1 and not search["hits"][0]["body_allowed"]
                      and search["hits"][0]["reference"]["identity"] == "skill.alpha")
                protocol = client.post("/mcp", headers={**headers, "Accept": "application/json, text/event-stream"},
                    json={"jsonrpc": "2.0", "id": "browser-not-protocol", "method": "initialize",
                          "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}}})
                check("generic_browser_audience_never_becomes_protocol_resource_authority", protocol.status_code == 401)
                own_options = client.get("/api/v1/account/access", headers=headers)
                check("HTTP_customer_access_uses_the_verified_account_only", own_options.status_code == 200
                      and own_options.json()["result"]["target_tenants"] == [tenant])
                check("HTTP_customer_access_refuses_unknown_query_fields", client.get("/api/v1/account/access?tenant_id=alpha", headers=headers).status_code == 400)
                customer_issue = {"record_type":"service_client_access_request/v1", "operation":"issue", "request_id":"native-client",
                                  "label":"Local development tool", "scopes":["provisioning:metadata"], "lifetime_seconds":3600}
                client_reject = client.post("/api/v1/account/access", headers=headers, json={**customer_issue, "tenant_id":"alpha"})
                check("HTTP_customer_cannot_select_a_tenant", client_reject.status_code == 400)
                granted = client.post("/api/v1/account/access", headers=headers, json=customer_issue)
                issued = granted.json()["result"]
                check("HTTP_customer_token_is_committed_in_a_governed_operation", granted.status_code == 200
                      and granted.json()["execution"]["runtime_type"] == "Loop" and issued["committed"]
                      and granted.headers["cache-control"] == "no-store")
                client_headers = {"Authorization":"Bearer " + issued["token"]}
                check("HTTP_customer_token_authenticates_its_own_tenant", client.get("/api/v1/session", headers=client_headers).json()["result"]["principal"]["tenant_id"] == tenant)
                check("HTTP_customer_token_cannot_mint_more_tokens", client.post("/api/v1/account/access", headers=client_headers, json=customer_issue).status_code == 403)
                own_list = client.get("/api/v1/account/access", headers=headers)
                check("HTTP_customer_list_contains_no_credential_or_digest", issued["token"] not in own_list.text and "key_digest" not in own_list.text)
                another_headers = {"Authorization":"Bearer " + token(sub="other-customer")}
                client.post("/api/v1/account/activate", headers=another_headers, json=activation)
                check("HTTP_other_customer_has_an_empty_personal_token_list", client.get("/api/v1/account/access", headers=another_headers).json()["result"]["tokens"] == [])
                wrong_revoke = client.post("/api/v1/account/access", headers=another_headers, json={
                    "record_type":"service_client_access_request/v1", "operation":"revoke", "request_id":"wrong-owner", "key_id":issued["key"]["key_id"]})
                check("HTTP_other_customer_cannot_revoke_a_foreign_token", wrong_revoke.status_code == 404)
                cross_origin = client.post("/api/v1/account/access", headers={**headers, "Origin":"https://foreign.invalid"}, json=customer_issue)
                check("HTTP_foreign_origin_cannot_mint_customer_tokens", cross_origin.status_code == 403)
                repeated = client.post("/api/v1/account/access", headers=headers, json=customer_issue)
                check("HTTP_customer_issue_retry_has_no_second_secret", repeated.json()["result"]["replayed"] and repeated.json()["result"]["token"] is None)
                revoked_client = client.post("/api/v1/account/access", headers=headers, json={
                    "record_type":"service_client_access_request/v1", "operation":"revoke", "request_id":"retire-client", "key_id":issued["key"]["key_id"]})
                check("HTTP_customer_revocation_is_immediate", revoked_client.status_code == 200 and client.get("/api/v1/session", headers=client_headers).status_code == 401)
                for label, changes in (("audience", {"aud": "other-service"}), ("issuer", {"iss": "https://foreign.example"}),
                                       ("expired", {"exp": 1}), ("anonymous", {"is_anonymous": True}),
                                       ("service_role", {"role": "service_role"})):
                    rejected = client.post("/api/v1/account/activate", headers={"Authorization": "Bearer " + token(**changes)}, json=activation)
                    check("browser_account_refuses_" + label, rejected.status_code == 401)
                state["confirmed"] = False
                unverified = client.post("/api/v1/account/activate", headers={"Authorization": "Bearer " + token(sub="unverified")}, json=activation)
                check("editable_email_verified_claim_cannot_replace_provider_confirmation", unverified.status_code == 401)
                state["confirmed"] = True; state["wrong_subject"] = True
                wrong_user = client.get("/api/v1/session", headers=headers)
                check("provider_user_and_signed_subject_must_match", wrong_user.status_code == 401)
                state["wrong_subject"] = False
                revoked = client.post("/api/v1/account/logout", headers=headers, json={"record_type": "service_browser_logout_request/v1"})
                rejected = client.get("/api/v1/session", headers=headers)
                check("browser_logout_durably_refuses_the_same_signed_access_token", revoked.status_code == 200 and rejected.status_code == 401)
                from .runtime import ServiceRuntime
                reopened = BrowserIdentityAdapter(ServiceRuntime(fixture.runtime.config), policy, lambda _: "sb_publishable_local_fixture", transport=user)
                try:
                    reopened.authenticate(encoded); survives = False
                except HttpAuthenticationError:
                    survives = True
                check("browser_session_revocation_survives_service_restart", survives)
                # A revocation is removed once its session has expired and never
                # before, even while a request of that session is being checked.
                # The removal runs inside the provider call of one request, at
                # the start of the second the token expires in, and then at the
                # rounded-up expiry the revocation keeps. Each has a known-wrong
                # case with its own guard patched away.
                raced = _raced_sign_out(fixture, policy, adapter, user, token)
                check("a_revocation_outlives_every_moment_its_token_can_still_be_accepted",
                      raced(math.floor) is False)
                check("a_session_whose_revocation_is_removed_while_it_is_checked_is_still_refused",
                      raced(math.ceil) is False)
                with patch.object(browser_identity, "revocation_expiry", int):
                    check("KNOWN_WRONG_a_revocation_rounded_down_is_removed_while_its_token_is_accepted",
                          raced(math.floor) is True)
                with patch.object(browser_identity, "expired_by_now", lambda claims, now: False):
                    check("KNOWN_WRONG_without_the_second_expiry_read_a_removed_revocation_lets_the_session_in",
                          raced(math.ceil) is True)
                before = state["provider_calls"]
                disabled = BrowserIdentityAdapter(fixture.runtime, replace(policy, allow_network=False),
                    lambda _: (_ for _ in ()).throw(AssertionError("secret read without authority")), transport=user)
                try:
                    disabled.activate(token(sub="blocked")); blocked = False
                except HttpAuthenticationError:
                    blocked = True
                check("disabled_identity_network_resolves_no_key_and_calls_no_provider", blocked and state["provider_calls"] == before)
                # A visitor must be told that account creation is closed, not
                # that their request was malformed, so the page can point them
                # at the waiting list instead of showing a fault.
                from ..service_runtime.http import _status
                closed = BrowserIdentityAdapter(fixture.runtime, replace(policy, registration_enabled=False),
                    lambda _: "sb_publishable_local_fixture", transport=user)
                try:
                    closed.activate(token(sub="waiting")); refusal = None
                except ServiceRuntimeError as error:
                    refusal = error
                check("closed_account_creation_is_reported_as_unavailable_not_as_a_bad_request",
                      refusal is not None and refusal.code == "account_registration_unavailable"
                      and _status(refusal) == (503, "account_registration_unavailable"))
                wrong_key = BrowserIdentityAdapter(fixture.runtime, policy, lambda _: "sb_secret_local_fixture", transport=user)
                try:
                    wrong_key.public_configuration(); hidden = False
                except ServiceRuntimeError:
                    hidden = True
                check("server_secret_cannot_be_serialized_as_a_publishable_key", hidden)
                fresh = BrowserIdentityAdapter(fixture.runtime, policy, lambda _: "sb_publishable_local_fixture", transport=user)
                application.authenticator.browser_identity = fresh
                public_keys["status"] = 503
                unavailable = client.get("/api/v1/session", headers={"Authorization":"Bearer " + token(sub="other-customer")})
                check("identity_key_outage_is_retryable_not_invalid_credentials", unavailable.status_code == 503
                      and unavailable.json()["error"]["code"] == "identity_key_set_unavailable")
                public_keys["status"] = 200
                def provider_outage(_request):
                    raise HttpAuthenticationError("identity_provider_unavailable")
                fresh._transport = provider_outage
                unavailable = client.get("/api/v1/session", headers={"Authorization":"Bearer " + token(sub="other-customer")})
                check("identity_user_outage_is_retryable_not_a_sign_out", unavailable.status_code == 503)
