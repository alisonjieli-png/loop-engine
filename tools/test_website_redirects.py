"""Canonical public pages on real loopback HTTP and the actual edge Worker.

All accounts, mail, OAuth keys and origins are local fixtures. No provider,
DNS or production requests are made. Removed guards exercise the same oracles.
"""
from contextlib import contextmanager
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import httpx

from loop_engine.core.service_runtime import brand_profiles, http as service_http
from loop_engine.core.service_runtime.brand_profiles import ServiceBrandProfile
from loop_engine.core.service_runtime.request_limits import ServiceRequestLimits, SOCKET_PEER_SOURCE
from loop_engine.core.service_runtime.static_site_checks import _fetch, local_site, node_runtime, site_worker
from loop_engine.core.service_runtime.static_site_export import SiteExport, write_export
import test_oauth_http as oauth_fixture

BASE_ORIGIN = "https://baltor.example.test"
BRANDS = {
    "agentfeeds": ("AgentFeeds", "agentfeeds.example.test"),
    "agentfoundry": ("AgentFoundry", "getagentfoundry.example.test"),
    "agentstudios": ("AgentStudios", "agentstudios.example.test"),
    "agentafk": ("AgentAFK", "agentafk.example.test"),
    "meatproxy": ("Don't be a meat proxy", "dontbeameatproxy.example.test"),
}
PROFILES = tuple(ServiceBrandProfile(brand, "https://" + prefix + host, name)
                 for brand, (name, host) in BRANDS.items() for prefix in ("", "www."))
PAIRS = {"www.baltor.example.test": BASE_ORIGIN,
         **{"www." + host: "https://" + host for _name, host in BRANDS.values()}}


def canonical_page_answer(answer, location):
    status, headers, body = answer
    return (status == 301 and headers.get("location") == location and body == b""
            and headers.get("cache-control") == "no-store"
            and {part.strip().lower() for part in headers.get("vary", "").split(",")}
            >= {"authorization", "cookie", "origin"})


def observation(response):
    return response.status_code, dict(response.headers), response.content


class RedirectPolicyTests(unittest.TestCase):
    def test_only_declared_same_brand_pairs_are_selected(self):
        hosts = ("baltor.example.test", *PAIRS, *(profile.host for profile in PROFILES))
        origins = (BASE_ORIGIN, "https://www.baltor.example.test", *(p.public_base_url for p in PROFILES))
        selected = brand_profiles.website_redirect_origins(BASE_ORIGIN, hosts, origins, PROFILES)
        self.assertEqual(selected, PAIRS)
        for missing in ("www.agentfeeds.example.test", "agentfeeds.example.test"):
            limited = brand_profiles.website_redirect_origins(BASE_ORIGIN,
                tuple(host for host in hosts if host != missing), origins, PROFILES)
            self.assertNotIn("www.agentfeeds.example.test", limited)
        limited = brand_profiles.website_redirect_origins(BASE_ORIGIN, hosts,
            tuple(origin for origin in origins if origin != "https://agentfeeds.example.test"), PROFILES)
        self.assertNotIn("www.agentfeeds.example.test", limited)
        mismatched = tuple(replace(p, brand="agentfoundry", display_name="AgentFoundry")
                           if p.host == "www.agentfeeds.example.test" else p for p in PROFILES)
        self.assertNotIn("www.agentfeeds.example.test",
            brand_profiles.website_redirect_origins(BASE_ORIGIN, hosts, origins, mismatched))

    def test_encoded_target_never_selects_another_origin_or_injects_a_header(self):
        self.assertEqual(brand_profiles.website_redirect_location(BASE_ORIGIN,
            b"//untrusted.invalid/%2f", b"next=https%3A%2F%2Funtrusted.invalid&x=1&x=2"),
            BASE_ORIGIN + "//untrusted.invalid/%2f?next=https%3A%2F%2Funtrusted.invalid&x=1&x=2")
        for path, query in ((b"https://untrusted.invalid", b""), (b"/", b"x=1\r\nLocation: bad"),
                            (b"/bad path", b""), (b"/\xff", b"")):
            self.assertIsNone(brand_profiles.website_redirect_location(BASE_ORIGIN, path, query))

    def test_redirect_oracle_rejects_old_alias_behavior_and_cache_or_target_regressions(self):
        good = (301, {"location": BASE_ORIGIN + "/?x=1", "cache-control": "no-store",
                      "vary": "Authorization, Cookie, Origin"}, b"")
        self.assertTrue(canonical_page_answer(good, BASE_ORIGIN + "/?x=1"))
        for bad in ((200, good[1], b"page"), (308, good[1], b""),
                    (301, {**good[1], "location": BASE_ORIGIN + "/"}, b""),
                    (301, {**good[1], "cache-control": "public, max-age=3600"}, b""),
                    (301, {**good[1], "vary": "Origin"}, b"")):
            self.assertFalse(canonical_page_answer(bad, BASE_ORIGIN + "/?x=1"))


class WebsiteRedirectHttpTests(unittest.TestCase):
    def setUp(self):
        original = oauth_fixture.running_http

        @contextmanager
        def configured(fixture, **kwargs):
            factory = kwargs.pop("application_factory")

            def application(config):
                config = replace(config, public_base_url=BASE_ORIGIN,
                    allowed_hosts=(*config.allowed_hosts, "baltor.example.test", *PAIRS,
                                   *(profile.host for profile in PROFILES)),
                    allowed_origins=(config.public_base_url, BASE_ORIGIN, "https://www.baltor.example.test",
                                     *(profile.public_base_url for profile in PROFILES)),
                    brand_profiles=PROFILES,
                    request_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE))
                return factory(config)

            with original(fixture, application_factory=application, **kwargs) as running:
                yield running

        self.fixture = oauth_fixture.HttpOAuthIntegration(methodName="runTest")
        with mock.patch.object(oauth_fixture, "running_http", configured):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client

    def test_six_public_page_pairs_redirect_get_and_head_preserving_encoded_target(self):
        for host, origin in PAIRS.items():
            for method in ("GET", "HEAD"):
                for path in ("/", "/%70rivacy?a=%2F&a=two+words&next=%2Faccount"):
                    with self.subTest(host=host, method=method, path=path):
                        answer = self.client.request(method, path, headers={"Host": host})
                        self.assertTrue(canonical_page_answer(observation(answer), origin + path),
                                        (answer.status_code, dict(answer.headers)))
                apex = self.client.request(method, "/", headers={"Host": urlsplit(origin).netloc})
                self.assertEqual(apex.status_code, 200)
                self.assertNotIn("location", apex.headers)

    def test_credentials_origin_and_local_browser_state_never_redirect(self):
        host = "www.agentfeeds.example.test"
        for extra in ({"Authorization": "Bearer synthetic-navigation"}, {"Cookie": "session=synthetic"},
                      {"Proxy-Authorization": "synthetic"}, {"Origin": "https://" + host}):
            with self.subTest(extra=tuple(extra)):
                answer = self.client.get("/", headers={"Host": host, **extra})
                self.assertEqual(answer.status_code, 200)
                self.assertNotIn("location", answer.headers)
        for path in ("/login", "/signup", "/get-started", "/account", "/saved", "/build",
                     "/auth/callback?code=synthetic", "/auth/confirm?token_hash=synthetic", "/oauth/consent"):
            with self.subTest(path=path):
                answer = self.client.get(path, headers={"Host": host})
                self.assertEqual(answer.status_code, 200)
                self.assertNotIn("location", answer.headers)
        for path in ("/api/v1/health", "/feeds/sources.json", "/assets/agentfeeds/site.css"):
            answer = self.client.get(path, headers={"Host": host})
            self.assertEqual(answer.status_code, 200)
            self.assertNotIn("location", answer.headers)
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            answer = self.client.request(method, "/", content=b"preserve-this-body",
                headers={"Host": host, "Origin": "https://" + host})
            self.assertNotIn("location", answer.headers)
            self.assertNotIn(answer.status_code, (301, 307, 308))

    def test_host_and_origin_refusals_still_precede_redirects(self):
        for headers, status in (({"Host": "www.attacker.invalid"}, 421),
                                ({"Host": "www.agentfeeds.example.test", "Origin": BASE_ORIGIN}, 403)):
            answer = self.client.get("/", headers=headers)
            self.assertEqual(answer.status_code, status)
            self.assertNotIn("location", answer.headers)

    def test_www_oauth_issuer_resource_consent_token_and_mcp_stay_origin_local(self):
        host = "www.agentfeeds.example.test"
        origin = "https://" + host
        headers = {"Host": host}
        metadata = self.client.get("/.well-known/oauth-authorization-server", headers=headers).json()
        self.assertEqual(metadata["issuer"], origin)
        resource = self.client.get("/.well-known/oauth-protected-resource/mcp", headers=headers).json()
        self.assertEqual(resource["resource"], origin + "/mcp")
        registration = self.client.post("/register", headers=headers, json={"client_name": "Alias fixture",
            "redirect_uris": [self.fixture.callback], "scope": "provisioning:metadata provisioning:read usage:read"})
        self.assertEqual(registration.status_code, 201, registration.text)
        client_id = registration.json()["client_id"]
        authorization = self.client.get("/authorize", headers=headers, params={
            "client_id": client_id, "response_type": "code", "redirect_uri": self.fixture.callback,
            "state": "alias-fixture", "code_challenge": self.fixture.challenge, "code_challenge_method": "S256",
            "resource": origin + "/mcp"})
        self.assertEqual(authorization.status_code, 302)
        self.assertTrue(authorization.headers["location"].startswith(origin + "/oauth/consent?"))
        identifier = parse_qs(urlsplit(authorization.headers["location"]).query)["authorization_id"][0]
        browser = {**headers, "Origin": origin, "Authorization": "Bearer " + self.fixture.browser_token}
        approved = self.client.post("/api/v1/oauth/consent", headers=browser,
            json={"record_type": "service_oauth_consent_decision/v1", "authorization_id": identifier, "decision": "approve"})
        self.assertEqual(approved.status_code, 200, approved.text)
        returned = parse_qs(urlsplit(approved.json()["result"]["redirect_uri"]).query)
        self.assertEqual(returned["iss"], [origin])
        token = self.client.post("/token", headers=headers, data={"grant_type": "authorization_code", "client_id": client_id,
            "code": returned["code"][0], "redirect_uri": self.fixture.callback, "code_verifier": self.fixture.verifier,
            "resource": origin + "/mcp"})
        self.assertEqual(token.status_code, 200, token.text)
        authenticated = {**headers, "Authorization": "Bearer " + token.json()["access_token"],
                         "Accept": "application/json, text/event-stream"}
        payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "alias-fixture", "version": "1"}}}
        answer = self.client.post("/mcp", headers=authenticated, json=payload)
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertNotIn("location", answer.headers)
        cross = self.client.post("/mcp", headers={**authenticated, "Host": "agentfeeds.example.test"}, json=payload)
        self.assertEqual(cross.status_code, 401, cross.text)
        self.assertNotIn("location", cross.headers)

    def test_real_http_known_wrong_controls_detect_removed_redirect_and_credential_guard(self):
        host = "www.agentfeeds.example.test"
        with mock.patch.object(service_http, "website_redirect_location", return_value=None):
            answer = self.client.get("/", headers={"Host": host})
            self.assertFalse(canonical_page_answer(observation(answer), PAIRS[host] + "/"))
        with mock.patch.object(service_http, "public_website_read", return_value=True):
            answer = self.client.get("/", headers={"Host": host, "Authorization": "Bearer synthetic-navigation"})
            self.assertEqual(answer.status_code, 301, "the removed credential guard did not change the observed behavior")


@contextmanager
def echo_origin():
    class Handler(BaseHTTPRequestHandler):
        def answer(self):
            payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            result = json.dumps({"method": self.command, "path": self.path, "body": payload.decode(),
                                 "authorization": self.headers.get("Authorization")}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            if self.path == "/sets-cookie":
                self.send_header("Set-Cookie", "session=synthetic")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(result)
        do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = answer

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


class WebsiteRedirectEdgeTests(unittest.TestCase):
    def setUp(self):
        self.node = node_runtime()
        if self.node is None:
            self.skipTest("Node 22.5 or newer is required")
        self.temp = tempfile.TemporaryDirectory(prefix="website-redirect-edge-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        body = b"<!doctype html><title>Public page</title>"
        digest = hashlib.sha256(body).hexdigest()
        self.manifest = {"record_type": "site_edge_manifest/v1", "export_id": "e" * 64,
            "canonical_hostname": "baltor.ai", "roots": {"baltor.ai": "/", "www.baltor.ai": "/"},
            "origin_prefixes": [], "origin_addresses": [], "unavailable": {},
            "classes": {"page": {"headers": {"Cache-Control": "no-store"}, "etag": False}},
            "files": {"/": {"sha256": digest, "media_type": "text/html; charset=utf-8", "class": "page", "head": False}}}
        self.export = SiteExport(self.manifest, {digest: body})
        self.folder = write_export(self.export, self.root / "export")
        self.counter = 0

    @contextmanager
    def worker(self, origin, source=None):
        self.counter += 1
        with local_site(self.root / str(self.counter), self.folder, self.export.export_id, origin,
                        node=self.node, source=source) as worker:
            yield worker

    def test_actual_worker_preserves_target_and_keeps_api_and_authenticated_requests_local(self):
        with echo_origin() as origin, self.worker(origin) as worker:
            for method in ("GET", "HEAD"):
                for path in ("/", "/%70rivacy?a=%2F&a=two+words&next=%2Faccount"):
                    answer = _fetch(worker.port, method, path, "www.baltor.ai")
                    self.assertTrue(canonical_page_answer(answer, "https://baltor.ai" + path), answer)
            for extra in ({"Authorization": "Bearer synthetic-navigation"}, {"Cookie": "session=synthetic"},
                          {"Proxy-Authorization": "synthetic"}, {"Origin": "https://www.baltor.ai"}):
                answer = _fetch(worker.port, "GET", "/", "www.baltor.ai", extra)
                self.assertEqual(answer[0], 200)
                self.assertNotIn("location", answer[1])
            for path in (*brand_profiles.ORIGIN_LOCAL_WEB_PATHS,
                         *(prefix + "/example" for prefix in brand_profiles.ORIGIN_LOCAL_WEB_PREFIXES),
                         "/%61uth/callback?code=synthetic", "/sets-cookie"):
                answer = _fetch(worker.port, "GET", path, "www.baltor.ai")
                self.assertEqual(answer[0], 200, path)
                self.assertNotIn("location", answer[1], path)
            for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
                answer = _fetch(worker.port, method, "/mcp?a=%2F&a=2", "www.baltor.ai",
                                {"Authorization": "Bearer synthetic-protocol"}, b"exact original body")
                self.assertEqual(answer[0], 200)
                self.assertEqual(json.loads(answer[2]), {"method": method, "path": "/mcp?a=%2F&a=2",
                    "body": "exact original body", "authorization": "Bearer synthetic-protocol"})
                self.assertNotIn("location", answer[1])
            for host in ("baltor.ai", "www.baltor.ai.evil.invalid", "edge.test"):
                answer = _fetch(worker.port, "GET", "/", host)
                self.assertEqual(answer[0], 200)
                self.assertNotIn("location", answer[1])

    def test_worker_requires_both_declared_roots_and_detects_known_wrong_variants(self):
        with echo_origin() as origin:
            for missing in ("www.baltor.ai", "baltor.ai"):
                roots = self.manifest["roots"]
                self.manifest["roots"] = {key: value for key, value in roots.items() if key != missing}
                write_export(self.export, self.folder)
                with self.worker(origin) as worker:
                    self.assertNotIn("location", _fetch(worker.port, "GET", "/", "www.baltor.ai")[1])
                self.manifest["roots"] = roots
            write_export(self.export, self.folder)
            source = site_worker()
            old = "return websiteRedirect(request, manifest, host, aliased, response) || response;"
            self.assertEqual(source.count(old), 1)
            with self.worker(origin, source.replace(old, "return response;")) as worker:
                self.assertFalse(canonical_page_answer(_fetch(worker.port, "GET", "/", "www.baltor.ai"),
                                                      "https://baltor.ai/"))
            old = "${canonical}${url.pathname}${url.search}"
            self.assertEqual(source.count(old), 1)
            with self.worker(origin, source.replace(old, "${canonical}${url.pathname}")) as worker:
                self.assertFalse(canonical_page_answer(_fetch(worker.port, "GET", "/?keep=%2F", "www.baltor.ai"),
                                                      "https://baltor.ai/?keep=%2F"))


if __name__ == "__main__":
    unittest.main()
