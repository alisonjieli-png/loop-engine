"""Brand hostnames send Strict-Transport-Security; the Baltor hostnames leave it to the edge zone.

The brand domains reach Fly directly and sent no Strict-Transport-Security header on October 16, 2026, while the
baltor.ai hostnames receive it from the edge zone (artifacts/architecture-audit-2026-09-19/edge-zone-hardening-2026-10-16.json).
Every answer on a brand presentation with an HTTPS origin carries max-age=31536000, without includeSubDomains or preload;
the base presentation sends none, so a browser behind the edge never reads it twice. Local fixtures only: real loopback
HTTP, synthetic OAuth keys and example hostnames.
"""
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from loop_engine.core.service_runtime import http as service_http
from loop_engine.core.service_runtime.brand_profiles import ServiceBrandProfile
from loop_engine.core.service_runtime.request_limits import ServiceRequestLimits, SOCKET_PEER_SOURCE
import test_oauth_http as oauth_fixture

BASE_ORIGIN = "https://baltor.example.test"
BRANDS = {"agentfeeds": ("AgentFeeds", "agentfeeds.example.test"),
          "agentfoundry": ("AgentFoundry", "getagentfoundry.example.test"),
          "agentstudios": ("AgentStudios", "agentstudios.example.test"),
          "agentafk": ("AgentAFK", "agentafk.example.test"),
          "meatproxy": ("Don't be a meat proxy", "dontbeameatproxy.example.test")}
PROFILES = tuple(ServiceBrandProfile(brand, "https://" + prefix + host, name)
                 for brand, (name, host) in BRANDS.items() for prefix in ("", "www."))
EXPECTED = "max-age=31536000"


def transport_security_problems(headers, *, brand):
    """What is wrong with one answer's Strict-Transport-Security header for a brand or a Baltor hostname."""
    values = headers.get_list("strict-transport-security") if hasattr(headers, "get_list") else (
        [headers["strict-transport-security"]] if "strict-transport-security" in headers else [])
    if not brand:
        return [f"a Baltor hostname sent {values}"] if values else []
    if values != [EXPECTED]:
        return [f"a brand hostname sent {values}, not [{EXPECTED!r}]"]
    return []


class TransportSecurityRuleTests(unittest.TestCase):
    def test_only_an_https_brand_presentation_gets_the_header(self):
        rule = service_http.transport_security_headers
        self.assertEqual(rule(SimpleNamespace(brand_profile=None)), {})
        self.assertEqual(rule(SimpleNamespace(brand_profile=PROFILES[0])), {"Strict-Transport-Security": EXPECTED})
        loopback = ServiceBrandProfile("agentfeeds", "http://127.0.0.1:8080")
        self.assertEqual(rule(SimpleNamespace(brand_profile=loopback)), {})
        self.assertNotIn("includeSubDomains", service_http.STRICT_TRANSPORT_SECURITY)
        self.assertNotIn("preload", service_http.STRICT_TRANSPORT_SECURITY)


class TransportSecurityHttpTests(unittest.TestCase):
    def setUp(self):
        original = oauth_fixture.running_http

        @contextmanager
        def configured(fixture, **kwargs):
            factory = kwargs.pop("application_factory")

            def application(config):
                config = replace(config, public_base_url=BASE_ORIGIN,
                    allowed_hosts=(*config.allowed_hosts, "baltor.example.test", *(profile.host for profile in PROFILES)),
                    allowed_origins=(config.public_base_url, BASE_ORIGIN, *(profile.public_base_url for profile in PROFILES)),
                    brand_profiles=PROFILES, request_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE))
                return factory(config)

            with original(fixture, application_factory=application, **kwargs) as running:
                yield running

        self.fixture = oauth_fixture.HttpOAuthIntegration(methodName="runTest")
        with mock.patch.object(oauth_fixture, "running_http", configured):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client

    def answers(self, host):
        """A page, a canonical redirect, the health record, a missing address and a refused protocol request."""
        headers = {"Host": host}
        return {"page": self.client.get("/", headers=headers),
                "redirect": self.client.get("/", headers={"Host": "www." + host}) if not host.startswith("www.") else None,
                "health": self.client.get("/api/v1/health", headers=headers),
                "missing": self.client.get("/no-such-page", headers={**headers, "Accept": "text/html"}),
                "protocol": self.client.post("/mcp", headers=headers, json={})}

    def test_every_brand_answer_carries_the_header(self):
        for _name, host in BRANDS.values():
            for label, answer in self.answers(host).items():
                if answer is None:
                    continue
                with self.subTest(host=host, answer=label, status=answer.status_code):
                    # A 421 would mean the request never reached the brand presentation.
                    self.assertNotEqual(answer.status_code, 421)
                    self.assertEqual(transport_security_problems(answer.headers, brand=True), [])
        redirected = self.client.get("/", headers={"Host": "www.agentfeeds.example.test"})
        self.assertEqual(redirected.status_code, 301)

    def test_baltor_hostnames_leave_the_header_to_the_edge(self):
        for label, answer in self.answers("baltor.example.test").items():
            if label == "redirect":
                continue
            with self.subTest(answer=label, status=answer.status_code):
                self.assertNotEqual(answer.status_code, 421)
                self.assertEqual(transport_security_problems(answer.headers, brand=False), [])
        # The loopback address the fixture binds is the base presentation too.
        for path in ("/", "/api/v1/health", "/api/v1/capabilities", "/.well-known/oauth-authorization-server"):
            with self.subTest(path=path):
                self.assertEqual(transport_security_problems(self.client.get(path).headers, brand=False), [])

    def test_an_authenticated_brand_protocol_answer_carries_the_header(self):
        host = "agentfeeds.example.test"
        origin = "https://" + host
        headers = {"Host": host}
        registration = self.client.post("/register", headers=headers, json={"client_name": "Transport fixture",
            "redirect_uris": [self.fixture.callback], "scope": "provisioning:metadata provisioning:read usage:read"})
        self.assertEqual(registration.status_code, 201, registration.text)
        client_id = registration.json()["client_id"]
        authorization = self.client.get("/authorize", headers=headers, params={
            "client_id": client_id, "response_type": "code", "redirect_uri": self.fixture.callback,
            "state": "transport-fixture", "code_challenge": self.fixture.challenge, "code_challenge_method": "S256",
            "resource": origin + "/mcp"})
        self.assertEqual(authorization.status_code, 302, authorization.text)
        identifier = parse_qs(urlsplit(authorization.headers["location"]).query)["authorization_id"][0]
        approved = self.client.post("/api/v1/oauth/consent",
            headers={**headers, "Origin": origin, "Authorization": "Bearer " + self.fixture.browser_token},
            json={"record_type": "service_oauth_consent_decision/v1", "authorization_id": identifier, "decision": "approve"})
        self.assertEqual(approved.status_code, 200, approved.text)
        code = parse_qs(urlsplit(approved.json()["result"]["redirect_uri"]).query)["code"][0]
        token = self.client.post("/token", headers=headers, data={"grant_type": "authorization_code", "client_id": client_id,
            "code": code, "redirect_uri": self.fixture.callback, "code_verifier": self.fixture.verifier,
            "resource": origin + "/mcp"})
        self.assertEqual(token.status_code, 200, token.text)
        answer = self.client.post("/mcp", headers={**headers, "Authorization": "Bearer " + token.json()["access_token"],
            "Accept": "application/json, text/event-stream"}, json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "transport", "version": "1"}}})
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual(transport_security_problems(answer.headers, brand=True), [])

    def test_known_wrong_controls(self):
        host = BRANDS["agentfoundry"][1]
        # KNOWN_WRONG: the rule removed, as on October 16, 2026, leaves a brand page without the header.
        with mock.patch.object(service_http, "transport_security_headers", lambda _application: {}):
            bare = self.client.get("/", headers={"Host": host})
        self.assertEqual(bare.status_code, 200)
        self.assertTrue(transport_security_problems(bare.headers, brand=True))
        # KNOWN_WRONG: the header sent everywhere would reach a Baltor hostname, beside the edge zone's own.
        everywhere = lambda _application: {"Strict-Transport-Security": EXPECTED}  # noqa: E731
        with mock.patch.object(service_http, "transport_security_headers", everywhere):
            doubled = self.client.get("/", headers={"Host": "baltor.example.test"})
        self.assertEqual(doubled.status_code, 200)
        self.assertTrue(transport_security_problems(doubled.headers, brand=False))
        # PLANTED: subdomains and preload, and two copies, are refused for a brand hostname.
        for wrong in ({"strict-transport-security": EXPECTED + "; includeSubDomains"},
                      {"strict-transport-security": EXPECTED + "; preload"}):
            self.assertTrue(transport_security_problems(wrong, brand=True))
        self.assertEqual(transport_security_problems(self.client.get("/", headers={"Host": host}).headers, brand=True), [])


if __name__ == "__main__":
    unittest.main()
