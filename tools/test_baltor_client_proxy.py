"""Baltor's stock opener through a real, controlled CONNECT tunnel and TLS origin.

No public endpoints or real credentials. Only socket destination mapping is
injected: origin.fixture.test:443 reaches an ephemeral loopback port. The
stock HTTPS handler still checks the generated certificate and hostname.
The proxy relays opaque TLS bytes, never terminates TLS. Tests clear proxy
environment state and use the existing throwaway CA helper.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
import os
from pathlib import Path
import select
import socket
import ssl
import tempfile
import threading
import unittest
from unittest import mock
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
CLIENT_PATH = ROOT / "integrations/baltor-library/skills/baltor-library/scripts/baltor.py"
ORIGIN_NAME = "origin.fixture.test"
WRONG_NAME = "wrong.fixture.test"
TOKEN = "synthetic-baltor-proxy-qa-only"
ROUTE = "/api/v1/retrieval"
REAL_CONNECT = socket.create_connection


class OriginHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append({"path": self.path, "headers": dict(self.headers)})
        if self.server.drop_response:
            self.close_connection = True
            return
        self.send_response(302 if self.server.redirect_to else 200)
        if self.server.redirect_to:
            self.send_header("Location", self.server.redirect_to)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.server.body)))
        self.end_headers()
        self.wfile.write(self.server.body)

    def log_message(self, *args):
        pass


class OriginServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, context=None):
        super().__init__(("127.0.0.1", 0), OriginHandler)
        self.context = context
        self.requests, self.accepted = [], 0
        self.redirect_to, self.drop_response, self.body = "", False, b'{"ok":true}'

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(3)
        self.accepted += 1
        if self.context is not None:
            try:
                connection = self.context.wrap_socket(connection, server_side=True)
            except BaseException:
                connection.close()
                raise
        return connection, address

    def handle_error(self, request, client_address):
        # TLS-refusal and lost-response controls intentionally close sockets.
        pass


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_CONNECT(self):
        self.server.connects.append({"target": self.path, "headers": dict(self.headers)})
        if self.server.refuse:
            self.send_error(407, "synthetic proxy authentication required")
            return
        if self.path not in {ORIGIN_NAME + ":443", WRONG_NAME + ":443"}:
            self.send_error(403)
            return
        with REAL_CONNECT(("127.0.0.1", self.server.origin.server_port), timeout=3) as upstream:
            self.send_response(200, "Connection established")
            self.end_headers()
            peers = {self.connection: upstream, upstream: self.connection}
            while True:
                readable, _, _ = select.select(list(peers), [], [], 3)
                if not readable:
                    return
                for peer in readable:
                    data = peer.recv(65536)
                    if not data:
                        return
                    # Bounded capture establishes that the client token was not
                    # sent in plaintext to the HTTP proxy outside the TLS tunnel.
                    self.server.wire.extend(data[:max(0, 131072-len(self.server.wire))])
                    peers[peer].sendall(data)

    def log_message(self, *args):
        pass


class ProxyServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, origin):
        super().__init__(("127.0.0.1", 0), ProxyHandler)
        self.origin, self.connects, self.wire, self.refuse = origin, [], bytearray(), False

    def handle_error(self, request, client_address):
        pass


@unittest.skipUnless(importlib.util.find_spec("cryptography"), "throwaway TLS CA needs serving's cryptography")
class BaltorClientProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.test_custom_endpoint_tls_trust import _certificates

        spec = importlib.util.spec_from_file_location("baltor_proxy_test_client", CLIENT_PATH)
        cls.client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.client_module)
        cls.folder = tempfile.TemporaryDirectory(prefix="baltor-proxy-tls-")
        cls.certificates = _certificates(Path(cls.folder.name))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.certificates["leaf"], cls.certificates["key"])
        cls.origin = OriginServer(context)
        cls.redirect_target = OriginServer()
        cls.proxy = ProxyServer(cls.origin)
        cls.servers = (cls.origin, cls.redirect_target, cls.proxy)
        cls.threads = []
        for server in cls.servers:
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
            thread.start()
            cls.threads.append(thread)

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.shutdown()
            server.server_close()
        for thread in cls.threads:
            thread.join(timeout=3)
        cls.folder.cleanup()

    def setUp(self):
        for server in (self.origin, self.redirect_target):
            server.requests.clear()
            server.accepted = 0
            server.redirect_to, server.drop_response, server.body = "", False, b'{"ok":true}'
        self.proxy.connects.clear()
        self.proxy.wire.clear()
        self.proxy.refuse = False
        self.addresses, self.direct_forbidden = [], False
        environment = {key: value for key, value in os.environ.items()
                       if not key.lower().endswith("_proxy") and key not in ("REQUEST_METHOD", "SSL_CERT_FILE", "SSL_CERT_DIR")}
        environment.update(SSL_CERT_FILE=self.certificates["anchor"], SSL_CERT_DIR=self.folder.name,
                           no_proxy="", https_proxy=self.proxy_url)
        self.environment = mock.patch.dict(os.environ, environment, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        connections = mock.patch.object(socket, "create_connection", side_effect=self.connect)
        connections.start()
        self.addCleanup(connections.stop)

    @property
    def proxy_url(self):
        return "http://127.0.0.1:" + str(self.proxy.server_port)

    def connect(self, address, *args, **kwargs):
        self.addresses.append(address)
        if address[0] in (ORIGIN_NAME, WRONG_NAME):
            if self.direct_forbidden:
                raise OSError("synthetic required proxy: direct route unavailable")
            address = ("127.0.0.1", self.origin.server_port)
        if address[0] != "127.0.0.1":
            raise AssertionError("test refused a non-loopback connection")
        return REAL_CONNECT(address, *args, **kwargs)

    def client(self, origin=None, opener=None):
        return self.client_module.Client({"record_type": "baltor_library_client_configuration/v2",
                                          "origin": origin or "https://" + ORIGIN_NAME,
                                          "credential_environment": "BALTOR_SERVICE_TOKEN",
                                          "authority_effects": ["reads_fs"]}, TOKEN, opener=opener)

    def assert_token_not_at_proxy(self):
        self.assertNotIn(TOKEN, json.dumps(self.proxy.connects))
        self.assertNotIn(TOKEN.encode(), self.proxy.wire)
        self.assertTrue(all("Authorization" not in row["headers"] for row in self.proxy.connects))

    def assert_refusal(self, client, expected="transport_failed"):
        with mock.patch.object(self.client_module.time, "sleep") as sleep:
            with self.assertRaises(self.client_module.Refusal) as caught:
                client.exchange(ROUTE)
            sleep.assert_not_called()
        self.assertEqual(caught.exception.code, expected)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertNotIn(TOKEN, json.dumps(caught.exception.details()))
        self.assertEqual(client.calls, 1)

    def test_stock_client_uses_required_https_proxy_and_tls_tunnel(self):
        self.direct_forbidden = True
        client = self.client()
        raw, _ = client.exchange(ROUTE)
        self.assertEqual(raw, b'{"ok":true}')
        self.assertEqual(self.addresses, [("127.0.0.1", self.proxy.server_port)])
        self.assertEqual([row["target"] for row in self.proxy.connects], [ORIGIN_NAME + ":443"])
        self.assertEqual(len(self.origin.requests), 1)
        self.assertEqual(self.origin.requests[0]["headers"]["Authorization"], "Bearer " + TOKEN)
        self.assertEqual(client.calls, 1)
        self.assert_token_not_at_proxy()

    def test_uppercase_https_proxy_is_honored(self):
        del os.environ["https_proxy"]
        os.environ["HTTPS_PROXY"] = self.proxy_url
        self.direct_forbidden = True
        self.assertEqual(self.client().exchange(ROUTE)[0], b'{"ok":true}')
        self.assertEqual(len(self.proxy.connects), 1)
        self.assert_token_not_at_proxy()

    def test_lowercase_proxy_takes_precedence(self):
        os.environ["HTTPS_PROXY"] = "http://unusable.fixture.test:12345"
        self.direct_forbidden = True
        self.assertEqual(self.client().exchange(ROUTE)[0], b'{"ok":true}')
        self.assertEqual(self.addresses, [("127.0.0.1", self.proxy.server_port)])

    def test_no_proxy_uses_explicit_direct_https_route(self):
        del os.environ["no_proxy"]
        os.environ["NO_PROXY"] = ORIGIN_NAME
        self.assertEqual(self.client().exchange(ROUTE)[0], b'{"ok":true}')
        self.assertEqual(self.addresses, [(ORIGIN_NAME, 443)])
        self.assertEqual(self.proxy.connects, [])
        self.assertEqual(len(self.origin.requests), 1)

    def test_without_proxy_configuration_direct_https_still_works(self):
        del os.environ["https_proxy"]
        self.assertEqual(self.client().exchange(ROUTE)[0], b'{"ok":true}')
        self.assertEqual(self.proxy.connects, [])
        self.assertEqual(self.addresses, [(ORIGIN_NAME, 443)])

    def test_unusable_required_proxy_has_no_direct_fallback_or_retry(self):
        # A bound but non-listening socket reserves a reliably closed port.
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            port = closed.getsockname()[1]
            os.environ["https_proxy"] = "http://127.0.0.1:" + str(port)
            self.assert_refusal(self.client())
        self.assertEqual(self.addresses, [("127.0.0.1", port)])
        self.assertEqual(self.proxy.connects, [])
        self.assertEqual(self.origin.accepted, 0)
        self.assertEqual(self.origin.requests, [])

    def test_proxy_connect_refusal_never_sends_origin_token_or_retries(self):
        self.proxy.refuse = True
        self.assert_refusal(self.client())
        self.assertEqual(len(self.proxy.connects), 1)
        self.assertEqual(self.origin.accepted, 0)
        self.assert_token_not_at_proxy()

    def test_proxy_authentication_stays_on_connect_not_at_origin(self):
        os.environ["https_proxy"] = self.proxy_url.replace("http://", "http://fixture-user:fixture-pass@")
        self.assertEqual(self.client().exchange(ROUTE)[0], b'{"ok":true}')
        self.assertIn("Proxy-Authorization", self.proxy.connects[0]["headers"])
        self.assertNotIn("Proxy-Authorization", self.origin.requests[0]["headers"])
        self.assert_token_not_at_proxy()

    def test_redirect_remains_refused_without_contacting_target(self):
        self.origin.redirect_to = "http://127.0.0.1:" + str(self.redirect_target.server_port) + "/trap"
        self.assert_refusal(self.client(), "redirect_refused")
        self.assertEqual(len(self.origin.requests), 1)
        self.assertEqual(self.redirect_target.accepted, 0)
        self.assertEqual(self.redirect_target.requests, [])
        self.assertEqual(len(self.proxy.connects), 1)
        self.assert_token_not_at_proxy()

    def test_untrusted_tls_certificate_refuses_before_origin_headers(self):
        os.environ["SSL_CERT_FILE"] = self.certificates["unrelated"]
        self.assert_refusal(self.client())
        self.assertEqual(len(self.proxy.connects), 1)
        self.assertEqual(self.origin.requests, [])
        self.assert_token_not_at_proxy()

    def test_tls_hostname_mismatch_refuses_before_origin_headers(self):
        self.assert_refusal(self.client("https://" + WRONG_NAME))
        self.assertEqual(len(self.proxy.connects), 1)
        self.assertEqual(self.origin.requests, [])
        self.assert_token_not_at_proxy()

    def test_https_origin_validation_still_refuses_before_network(self):
        for origin in ("http://" + ORIGIN_NAME, "https://" + ORIGIN_NAME + ":444", "https://user:secret@" + ORIGIN_NAME):
            with self.subTest(origin=origin), self.assertRaises(self.client_module.Refusal) as caught:
                self.client(origin)
            self.assertEqual(caught.exception.code, "https_origin_required")
        self.assertEqual(self.addresses, [])
        self.assertEqual(self.proxy.connects, [])
        self.assertEqual(self.origin.accepted, 0)

    def test_credential_echo_remains_redacted(self):
        self.origin.body = json.dumps({"echo": TOKEN}).encode()
        self.assert_refusal(self.client(), "credential_echo_refused")
        self.assertEqual(len(self.origin.requests), 1)
        self.assert_token_not_at_proxy()

    def test_lost_response_outcome_is_not_automatically_retried(self):
        self.origin.drop_response = True
        self.assert_refusal(self.client())
        self.assertEqual(len(self.origin.requests), 1)
        self.assertEqual(len(self.proxy.connects), 1)
        self.assert_token_not_at_proxy()

    def test_known_wrong_empty_proxy_handler_loses_required_route(self):
        self.direct_forbidden = True
        wrong = urllib.request.build_opener(urllib.request.ProxyHandler({}), self.client_module.NoRedirect())
        self.assert_refusal(self.client(opener=wrong))
        self.assertEqual(self.addresses, [(ORIGIN_NAME, 443)])
        self.assertEqual(self.proxy.connects, [])
        self.assertEqual(self.origin.accepted, 0)


if __name__ == "__main__":
    unittest.main()
