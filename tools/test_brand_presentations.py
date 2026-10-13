"""Real loopback brand boundaries; one runtime/account store and synthetic providers."""
from contextlib import contextmanager
from dataclasses import replace
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import httpx

from loop_engine.core.service_runtime.brand_profiles import ServiceBrandProfile
from loop_engine.core.service_runtime.http import ServiceHttpConfiguration
from loop_engine.core.service_runtime.account_email_checks import _Provider, _adapter, _settings
from loop_engine.core.service_runtime.request_limits import ServiceRequestLimits, SOCKET_PEER_SOURCE
from loop_engine.core.service_runtime.records import BillingCustomerBindingRequest
import test_oauth_http as existing

ORIGIN = "https://agentfeeds.example.test"
HOST = "agentfeeds.example.test"
PROFILE = ServiceBrandProfile("agentfeeds", ORIGIN)


class ProfileConfigurationTests(unittest.TestCase):
    def test_explicit_profile_versions_and_closed_host_origin_mapping(self):
        config = ServiceHttpConfiguration("https://service.example.test", ("service.example.test", HOST),
            allowed_origins=(ORIGIN,), brand_profiles=({"record_type": "service_brand_profile/v1", "brand": "agentfeeds",
                                                       "public_base_url": ORIGIN},))
        self.assertEqual(config.brand_profiles, (PROFILE,))
        wrong = (
            {}, {"record_type": "service_brand_profile/v0", "brand": "agentfeeds", "public_base_url": ORIGIN},
            {"record_type": "service_brand_profile/v1", "brand": "other", "public_base_url": ORIGIN},
            {"record_type": "service_brand_profile/v1", "brand": "agentfeeds", "public_base_url": ORIGIN + "/"},
            {"record_type": "service_brand_profile/v1", "brand": "agentfeeds", "public_base_url": ORIGIN, "unknown": True},
        )
        for value in wrong:
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                replace(config, brand_profiles=(value,))
        for change in ({"allowed_hosts": ("service.example.test",)}, {"allowed_origins": ()},
                       {"brand_profiles": (PROFILE, PROFILE)}, {"brand_profiles": (replace(PROFILE, public_base_url=config.public_base_url),)}):
            with self.subTest(change=change), self.assertRaises(ValueError): replace(config, **change)


class SharedBillingFixture:
    def __init__(self):
        self.created = []

    def options(self, principal=None):
        return {"record_type": "billing_session_options/v1", "policy_digest": "a" * 64,
                "checkout_available": True, "portal_available": True, "plans": []}

    def create(self, principal, request, **kwargs):
        self.created.append((principal, request))
        raise AssertionError("brand attempted a provider effect under another site's return policy")


class BrandHttpTests(unittest.TestCase):
    def setUp(self):
        self.mail = _Provider()
        self.billing = SharedBillingFixture()
        # Exercise the actual integrated renderer through the trusted host
        # selector; synthetic providers isolate mail and identity effects only.
        original = existing.running_http
        @contextmanager
        def branded(fixture, **kwargs):
            factory = kwargs.pop("application_factory")
            def application(config):
                config = replace(config, allowed_hosts=(*config.allowed_hosts, HOST),
                    allowed_origins=(*config.allowed_origins, ORIGIN), brand_profiles=(PROFILE,),
                    request_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE))
                result = factory(config)
                result.browser_identity.configuration = replace(result.browser_identity.configuration,
                    allowed_scopes=(*result.browser_identity.configuration.allowed_scopes, "billing:manage"))
                result.account_email = _adapter(self.mail, _settings(allow_loopback=True))
                result.billing_sessions = self.billing
                # Retain the actual constructed presentations for sharing
                # assertions without running their setup a second time.
                actual = result.brand_presentations()
                result.brand_presentations = lambda: actual
                self.presentation = actual[HOST]
                return result
            with original(fixture, application_factory=application, **kwargs) as value:
                yield value
        self.fixture = existing.HttpOAuthIntegration(methodName="runTest")
        with mock.patch.object(existing, "running_http", branded):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.app = self.fixture.app
        self.client = httpx.Client(base_url=self.fixture.base, headers={"Host": HOST}, trust_env=False,
                                   follow_redirects=False, timeout=15)
        self.addCleanup(self.client.close)
        self.browser = {"Authorization": "Bearer " + self.fixture.browser_token, "Origin": ORIGIN}

    def register(self, **changes):
        response = self.client.post("/register", json={"client_name": "Synthetic brand client",
            "redirect_uris": [self.fixture.callback], "scope": "provisioning:metadata provisioning:read usage:read", **changes})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["client_id"]

    def authorize(self, client_id, **changes):
        return self.client.get("/authorize", params={"response_type": "code", "client_id": client_id,
            "redirect_uri": self.fixture.callback, "state": "brand-state", "code_challenge": self.fixture.challenge,
            "code_challenge_method": "S256", "resource": ORIGIN + "/mcp", **changes})

    def issue(self):
        client_id = self.register()
        response = self.authorize(client_id)
        self.assertEqual(response.status_code, 302, response.text)
        location = response.headers["location"]
        self.assertTrue(location.startswith(ORIGIN + "/oauth/consent?"))
        identifier = parse_qs(urlsplit(location).query)["authorization_id"][0]
        response = self.client.get("/api/v1/oauth/consent", params={"authorization_id": identifier}, headers=self.browser)
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.post("/api/v1/oauth/consent", headers=self.browser,
            json={"record_type": "service_oauth_consent_decision/v1", "authorization_id": identifier, "decision": "approve"})
        self.assertEqual(response.status_code, 200, response.text)
        redirected = parse_qs(urlsplit(response.json()["result"]["redirect_uri"]).query)
        self.assertEqual(redirected["iss"], [ORIGIN])
        code = redirected["code"][0]
        form = {"grant_type": "authorization_code", "client_id": client_id, "code": code,
                "redirect_uri": self.fixture.callback, "code_verifier": self.fixture.verifier, "resource": ORIGIN + "/mcp"}
        return client_id, identifier, form

    def test_presentation_keeps_every_heavy_state_and_process_budget_shared(self):
        for name in ("runtime", "provisioning", "browser_identity", "client_access", "billing_sessions", "billing_processor",
                     "retention_schedule", "renewal_schedule", "catalogue_refresher", "public_links", "feedback",
                     "list_cursors", "_workers", "_slots", "_share_operations", "_share_lock", "request_limiter", "failure_journal"):
            self.assertIs(getattr(self.app, name), getattr(self.presentation, name), name)
        self.assertIs(self.app.provisioning.current_view(), self.presentation.provisioning.current_view())
        for name in ("address_attempts", "email_attempts", "account_origins"):
            self.assertIs(getattr(self.app.account_email, name), getattr(self.presentation.account_email, name), name)
        self.assertIs(self.app.oauth_http._attempts, self.presentation.oauth_http._attempts)
        self.assertIs(self.app.oauth_http._attempt_lock, self.presentation.oauth_http._attempt_lock)
        self.assertIs(self.app.runtime._catalog, self.presentation.oauth_authorization.catalog)

    def test_brand_metadata_and_pages_stay_local_and_default_site_survives(self):
        self.assertIn(ORIGIN, self.client.get("/").text)
        identity = self.client.get("/api/v1/account/identity").json()["result"]
        self.assertEqual(identity["redirect_url"], ORIGIN + "/auth/callback")
        self.assertEqual(self.client.get("/api/v1/capabilities").json()["result"]["website"]["display_name"], "AgentFeeds")
        metadata = self.client.get("/.well-known/oauth-authorization-server").json()
        self.assertEqual(metadata["issuer"], ORIGIN)
        self.assertEqual(metadata["authorization_endpoint"], ORIGIN + "/authorize")
        self.assertEqual(metadata["token_endpoint"], ORIGIN + "/token")
        self.assertEqual(metadata["service_documentation"], ORIGIN + "/connect")
        resource = self.client.get("/.well-known/oauth-protected-resource/mcp").json()
        self.assertEqual(resource["resource"], ORIGIN + "/mcp")
        self.assertEqual(resource["authorization_servers"], [ORIGIN])
        self.assertEqual(resource["resource_documentation"], ORIGIN + "/connect")
        self.assertEqual(self.fixture.client.get("/.well-known/oauth-authorization-server").json()["issuer"], self.fixture.base)
        self.assertEqual(self.client.get("/harness-files").status_code, 404)
        self.assertEqual(self.client.get("/assets/service.js").status_code, 404)
        notices = self.client.get("/assets/third-party-notices.txt")
        self.assertEqual(notices.status_code, 200, notices.text)
        self.assertTrue(notices.content)
        for suffix in ("json", "md", "rss"):
            feed = self.client.get("/feeds/sources." + suffix)
            self.assertEqual(feed.status_code, 200, feed.text)
            self.assertIn("AgentFeeds source collections", feed.text)
            self.assertNotIn("Baltor source collections", feed.text)
            self.assertNotIn("Browse Baltor", feed.text)
            self.assertEqual(self.client.get("/feeds/catalogue." + suffix).status_code, 404)

    def test_unknown_host_and_cross_brand_origins_refuse_before_mail(self):
        signup = {"record_type": "service_account_signup_request/v2", "email": "brand@example.invalid"}
        wrong = (
            {"Host": "unknown.example.test", "Origin": ORIGIN},
            {"Host": HOST, "Origin": self.fixture.base},
            {"Host": urlsplit(self.fixture.base).netloc, "Origin": ORIGIN},
            {"Host": HOST, "Origin": "https://agentfeeds.example.test.evil.invalid"},
        )
        for headers in wrong:
            with self.subTest(headers=headers):
                response = self.client.post("/api/v1/account/signup", json=signup, headers=headers)
                self.assertIn(response.status_code, (403, 421), response.text)
        self.assertEqual(self.mail.identity_requests, [])
        self.assertEqual(self.mail.mail_requests, [])

    def test_signup_and_recovery_email_use_brand_without_new_limiters(self):
        for action, record_type in (("signup", "service_account_signup_request/v2"), ("recovery", "service_account_recovery_request/v1")):
            response = self.client.post("/api/v1/account/" + action, headers={"Origin": ORIGIN},
                json={"record_type": record_type, "email": "brand@example.invalid"})
            self.assertEqual(response.status_code, 202, response.text)
            self.assertIn(ORIGIN + "/auth/confirm?", self.mail.sent_bodies[-1])
            self.assertIn("AgentFeeds", self.mail.sent_bodies[-1])
            self.assertNotIn(self.fixture.base, self.mail.sent_bodies[-1])
        self.assertEqual(len(self.mail.mail_requests), 2)

    def test_same_identity_activates_exact_same_account_and_billing_is_not_duplicated(self):
        runtime = self.app.runtime
        principal = runtime.authenticate_subject(self.fixture.identity_base + "/auth/v1", self.fixture.subject)
        runtime.bind_billing_customer(BillingCustomerBindingRequest(self.fixture.tenant, "cus_brand_fixture", "acct_brand_fixture"))
        before = runtime.billing_customer_for(principal)
        response = self.client.post("/api/v1/account/activate", headers=self.browser,
            json={"record_type": "service_account_activation_request/v1"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["result"]["tenant_id"], self.fixture.tenant)
        self.assertEqual(self.presentation.runtime.billing_customer_for(principal), before)
        options = self.client.get("/api/v1/billing/plans", headers=self.browser)
        self.assertEqual(options.status_code, 200, options.text)
        self.assertIs(options.json()["result"]["checkout_available"], False)
        self.assertIs(options.json()["result"]["portal_available"], False)
        for path in ("checkout", "portal"):
            response = self.client.post("/api/v1/billing/" + path, headers=self.browser,
                json={"record_type": "billing_session_request/v1", "request_id": "brand-session-fixture", "policy_digest": "a" * 64,
                      **({"plan_ref": "pro"} if path == "checkout" else {})})
            self.assertEqual(response.status_code, 501, response.text)
            self.assertEqual(response.json()["error"]["code"], "billing_sessions_not_installed")
        self.assertEqual(self.billing.created, [])

    def test_oauth_resource_callback_pkce_and_cross_brand_replay_refused(self):
        bad_registration = self.client.post("/register", json={"client_name": "Wrong client", "redirect_uris": ["https://bad.invalid/callback"]})
        self.assertEqual(bad_registration.status_code, 400)
        client_id, identifier, form = self.issue()
        wrong_resource = self.authorize(client_id, resource=self.fixture.base + "/mcp")
        self.assertEqual(wrong_resource.status_code, 302, wrong_resource.text)
        self.assertEqual(parse_qs(urlsplit(wrong_resource.headers["location"]).query)["error"], ["invalid_target"])
        # Another site cannot inspect or approve this issuer's pending handle,
        # redeem its code, or reuse the resulting opaque access/refresh token.
        cross_consent = self.fixture.client.get("/api/v1/oauth/consent", params={"authorization_id": identifier},
                                                 headers=self.fixture.browser_headers)
        self.assertEqual(cross_consent.status_code, 400, cross_consent.text)
        cross_code = self.fixture.client.post("/token", data={**form, "resource": self.fixture.base + "/mcp"})
        self.assertIn(cross_code.status_code, (400, 401), cross_code.text)
        bad_pkce = self.client.post("/token", data={**form, "code_verifier": "x" * 64})
        self.assertEqual(bad_pkce.status_code, 400, bad_pkce.text)
        response = self.client.post("/token", data=form)
        self.assertEqual(response.status_code, 200, response.text)
        tokens = response.json()
        local = self.client.get("/api/v1/usage", headers={"Authorization": "Bearer " + tokens["access_token"]})
        self.assertEqual(local.status_code, 200, local.text)
        protocol_headers = {"Authorization": "Bearer " + tokens["access_token"], "Accept": "application/json, text/event-stream"}
        initialize = self.client.post("/mcp", headers=protocol_headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "brand-fixture", "version": "1"}}})
        self.assertEqual(initialize.status_code, 200, initialize.text)
        self.assertIn("serverInfo", initialize.text)
        listing = self.client.post("/mcp", headers={**protocol_headers, "MCP-Protocol-Version": "2025-11-25"},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertIn("intelligence_search", listing.text)
        cross_mcp = self.fixture.client.post("/mcp", headers=protocol_headers,
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}})
        self.assertEqual(cross_mcp.status_code, 401, cross_mcp.text)
        cross = self.fixture.client.get("/api/v1/usage", headers={"Authorization": "Bearer " + tokens["access_token"]})
        self.assertEqual(cross.status_code, 401, cross.text)
        replay = self.client.post("/token", data=form)
        self.assertEqual(replay.status_code, 400)
        cross_refresh = self.fixture.client.post("/token", data={"grant_type": "refresh_token", "client_id": client_id,
            "refresh_token": tokens["refresh_token"], "resource": self.fixture.base + "/mcp"})
        self.assertIn(cross_refresh.status_code, (400, 401), cross_refresh.text)


if __name__ == "__main__":
    unittest.main()
