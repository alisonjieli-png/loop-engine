"""HEAD on the public read routes answers like GET without content, on real loopback HTTP.

The launch audit of October 16, 2026 (docs/verification/LAUNCH-AUDIT-BALTOR-2026-10-16.md, finding O8) found HEAD
answering 404 where GET answered 200 for the health and capabilities records, the tool-server document and the OAuth
discovery documents. All accounts, keys and origins here are local fixtures; no provider or production request is made.
"""
from contextlib import contextmanager
from dataclasses import replace
import unittest
from unittest import mock

from loop_engine.core.service_runtime import http as service_http
from loop_engine.core.service_runtime.brand_profiles import ServiceBrandProfile
from loop_engine.core.service_runtime.request_limits import ServiceRequestLimits, SOCKET_PEER_SOURCE
import test_oauth_http as oauth_fixture

PUBLIC_ONLY_ORIGIN = "https://agentafk.example.test"
PUBLIC_ONLY_HOST = "agentafk.example.test"
CHALLENGE = "fixture-challenge-token"
READ_ROUTES = ("/api/v1/health", "/api/v1/capabilities", "/api/v1/connect/openapi.json",
               "/.well-known/openai-apps-challenge", "/.well-known/oauth-authorization-server",
               "/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp")


def head_problems(get, head):
    """What keeps a HEAD answer from being GET's answer without its content (RFC 9110, section 9.3.2)."""
    problems = []
    if head.status_code != get.status_code:
        problems.append(f"status {head.status_code}, GET answered {get.status_code}")
    if head.content:
        problems.append("the HEAD answer carries content")
    for name in ("content-type", "cache-control", "x-content-type-options"):
        if head.headers.get(name) != get.headers.get(name):
            problems.append(f"{name} {head.headers.get(name)!r}, GET sent {get.headers.get(name)!r}")
    if head.headers.get("content-length") != str(len(get.content)):
        problems.append(f"content-length {head.headers.get('content-length')!r} for a GET body of {len(get.content)} bytes")
    return problems


class Observed:
    """A recorded answer, so the oracle can be shown a known-wrong one."""

    def __init__(self, status_code, headers, content):
        self.status_code, self.headers, self.content = status_code, headers, content


class HeadReadTests(unittest.TestCase):
    def setUp(self):
        original = oauth_fixture.running_http

        @contextmanager
        def configured(fixture, **kwargs):
            factory = kwargs.pop("application_factory")

            def application(config):
                profile = ServiceBrandProfile("agentafk", PUBLIC_ONLY_ORIGIN, "AgentAFK")
                config = replace(config, allowed_hosts=(*config.allowed_hosts, PUBLIC_ONLY_HOST),
                                 allowed_origins=(*config.allowed_origins, PUBLIC_ONLY_ORIGIN), brand_profiles=(profile,),
                                 openai_apps_challenge=CHALLENGE,
                                 request_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE))
                return factory(config)

            with original(fixture, application_factory=application, **kwargs) as running:
                yield running

        self.fixture = oauth_fixture.HttpOAuthIntegration(methodName="runTest")
        with mock.patch.object(oauth_fixture, "running_http", configured):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client

    def test_head_answers_like_get_on_every_public_read_route(self):
        for path in READ_ROUTES:
            with self.subTest(path=path):
                get, head = self.client.get(path), self.client.head(path)
                self.assertEqual(get.status_code, 200, (path, get.text[:200]))
                self.assertEqual(head_problems(get, head), [])
        self.assertEqual(self.client.get("/.well-known/openai-apps-challenge").text, CHALLENGE)

    def test_head_stays_refused_where_get_is_not_a_public_read(self):
        # Authenticated reads, an effectful authorization start and POST-only routes keep their declared methods.
        for path in ("/api/v1/session", "/api/v1/usage", "/api/v1/account/identity", "/authorize", "/api/v1/retrieval",
                     "/api/v1/download", "/api/v1/public-good"):
            with self.subTest(path=path):
                self.assertEqual(self.client.head(path).status_code, 404)

    def test_a_public_only_presentation_answers_head_on_health_and_still_refuses_other_routes(self):
        headers = {"Host": PUBLIC_ONLY_HOST}
        get, head = self.client.get("/api/v1/health", headers=headers), self.client.head("/api/v1/health", headers=headers)
        self.assertEqual(get.status_code, 200, get.text[:200])
        self.assertEqual(head_problems(get, head), [])
        for path in ("/api/v1/capabilities", "/.well-known/oauth-authorization-server", "/api/v1/connect/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.head(path, headers=headers).status_code, 404)
                self.assertEqual(self.client.get(path, headers=headers).status_code, 404)

    def test_known_wrong_controls(self):
        get = self.client.get("/api/v1/health")
        # KNOWN_WRONG: without the rule, HEAD answers 404 again, as the audit observed, and the oracle says so.
        with mock.patch.object(service_http, "HEAD_READ_ROUTES", frozenset()):
            removed = self.client.head("/api/v1/health")
        self.assertEqual(removed.status_code, 404)
        self.assertTrue(head_problems(get, removed))
        head = self.client.head("/api/v1/health")
        self.assertEqual(head_problems(get, head), [])
        # PLANTED: a HEAD answer that carries GET's content, and one whose length disagrees with GET's body.
        with_content = Observed(head.status_code, dict(head.headers), get.content)
        self.assertEqual(head_problems(get, with_content), ["the HEAD answer carries content"])
        wrong_length = Observed(head.status_code, {**dict(head.headers), "content-length": "0"}, b"")
        self.assertEqual(len(head_problems(get, wrong_length)), 1)


if __name__ == "__main__":
    unittest.main()
