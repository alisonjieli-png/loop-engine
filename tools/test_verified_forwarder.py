"""The verified loopback forwarder against a real local TLS origin. No model and no outside host is contacted.

A throwaway certificate authority, created per run, signs a leaf for ``origin.fixture.test``. The origin listens
on 127.0.0.1, so the connect host differs from the certificate's name, as it does for the owner's Tactical
server. Every known-wrong control asserts that the origin parsed no request: no request line, header, body or
key left the forwarder.

```text
verified forwarder
├── streams a verified answer and replaces the client's placeholder key
├── refuses before any request: wrong name, connect host as the name, unrelated anchor, wrong pin
├── refuses before any socket: changed or missing anchor, plain or credential-bearing upstream URL
├── forwards nothing outside its random path token or the upstream API base
└── a truncated upstream body reaches the client as a broken stream, never as a short complete one
```
"""
from __future__ import annotations

import hashlib
import http.client
import http.server
import json
import ssl
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from importlib.util import find_spec
from pathlib import Path

from tools import verified_forwarder as vf
from tools.test_custom_endpoint_tls_trust import NAME, _certificates

KEY = "fixture-key-" + "5" * 24
PLACEHOLDER = "placeholder-from-the-harness"
EVENTS = [b'data: {"choices": [{"delta": {"content": "Hel"}}]}\n\n',
          b'data: {"choices": [{"delta": {"content": "lo"}}]}\n\n', b"data: [DONE]\n\n"]
ROOT_ANCHOR = Path(__file__).resolve().parent / "resources/original-native-generation-providers"


class _Origin(http.server.BaseHTTPRequestHandler):
    """An OpenAI-shaped origin that streams server-sent events, or breaks off when told to."""

    def _record(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.server.requests.append({"method": self.command, "path": self.path, "headers": dict(self.headers),
                                     "body": body})
        return body

    def do_POST(self):
        self._record()
        if self.server.mode == "truncate":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", "4096")
            self.end_headers()
            self.wfile.write(EVENTS[0])
            self.wfile.flush()
            return  # HTTP/1.0 handler: the connection closes with 4,096 bytes promised
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for event in EVENTS:
            self.wfile.write(event)
            self.wfile.flush()

    def do_GET(self):
        self._record()
        raw = json.dumps({"object": "list", "data": [{"id": "fixture-coder"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        return None


class _OriginServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, context):
        super().__init__(("127.0.0.1", 0), _Origin)
        self.context, self.requests, self.accepted, self.mode = context, [], 0, "stream"

    def get_request(self):
        connection, address = super().get_request()
        self.accepted += 1
        return self.context.wrap_socket(connection, server_side=True), address

    def handle_error(self, request, client_address):
        return None


def _post(url: str, body: bytes = b'{"model": "fixture-coder", "stream": true}', key: str = PLACEHOLDER):
    request = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    return urllib.request.urlopen(request, timeout=10)


def _error(url: str, **options) -> tuple[int, dict]:
    try:
        with _post(url, **options) as response:
            response.read()
    except urllib.error.HTTPError as error:
        with error:
            return error.code, json.loads(error.read())
    raise AssertionError("the forwarder answered a request it had to refuse")


@unittest.skipUnless(find_spec("cryptography"), "cryptography creates the throwaway certificate authority")
class VerifiedForwarderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.certificates = _certificates(Path(cls.folder.name))
        cls.anchor_sha256 = hashlib.sha256(Path(cls.certificates["anchor"]).read_bytes()).hexdigest()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.certificates["leaf"], cls.certificates["key"])
        cls.origin = _OriginServer(context)
        threading.Thread(target=cls.origin.serve_forever, daemon=True).start()
        cls.upstream = f"https://127.0.0.1:{cls.origin.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.origin.shutdown()
        cls.origin.server_close()
        cls.folder.cleanup()

    def setUp(self):
        self.origin.requests.clear()
        self.origin.accepted, self.origin.mode = 0, "stream"

    def forwarder(self, **changes) -> vf.VerifiedForwarder:
        options = {"ca_file": self.certificates["anchor"], "ca_sha256": self.anchor_sha256,
                   "tls_server_name": NAME, "authorization": "Bearer " + KEY}
        options.update(changes)
        forwarder = vf.VerifiedForwarder(options.pop("upstream", self.upstream), **options)
        forwarder.start()
        self.addCleanup(forwarder.stop)
        return forwarder

    def assert_refused_before_request(self, forwarder, code="tls_trust_refused"):
        status, body = _error(forwarder.base_url + "/chat/completions")
        self.assertEqual((status, body["error"]["code"]), (502, code))
        self.assertEqual(self.origin.requests, [], "the origin parsed no request")
        text = json.dumps(body)
        for private in (NAME, "127.0.0.1", KEY, PLACEHOLDER):
            self.assertNotIn(private, text)

    def test_a_verified_answer_streams_back_with_the_key_this_process_holds(self):
        forwarder = self.forwarder()
        self.assertTrue(forwarder.base_url.startswith("http://127.0.0.1:"))
        with _post(forwarder.base_url + "/chat/completions") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Content-Type"], "text/event-stream")
            self.assertEqual(response.headers["Transfer-Encoding"], "chunked")
            self.assertEqual(response.read(), b"".join(EVENTS))
        [sent] = self.origin.requests
        self.assertEqual((sent["method"], sent["path"]), ("POST", "/v1/chat/completions"))
        self.assertEqual(sent["headers"]["Authorization"], "Bearer " + KEY, "the placeholder never leaves")
        self.assertEqual(json.loads(sent["body"]), {"model": "fixture-coder", "stream": True})
        self.assertEqual(forwarder.summary()["counts"]["forwarded"], 1)

    def test_without_a_held_key_the_client_authorization_passes_through(self):
        forwarder = self.forwarder(authorization=None)
        with urllib.request.urlopen(urllib.request.Request(
                forwarder.base_url + "/models", headers={"Authorization": "Bearer " + PLACEHOLDER}),
                timeout=10) as response:
            self.assertEqual(json.loads(response.read())["data"][0]["id"], "fixture-coder")
        [sent] = self.origin.requests
        self.assertEqual((sent["method"], sent["path"]), ("GET", "/v1/models"))
        self.assertEqual(sent["headers"]["Authorization"], "Bearer " + PLACEHOLDER)

    def test_a_wrong_expected_name_sends_nothing(self):
        self.assert_refused_before_request(self.forwarder(tls_server_name="other.fixture.test"))

    def test_the_connect_host_is_not_accepted_as_the_name(self):
        # Without the expected name the certificate cannot match 127.0.0.1: the old failure, now refused.
        self.assert_refused_before_request(self.forwarder(tls_server_name=""))

    def test_an_unrelated_anchor_sends_nothing(self):
        unrelated = Path(self.certificates["unrelated"])
        self.assert_refused_before_request(self.forwarder(
            ca_file=str(unrelated), ca_sha256=hashlib.sha256(unrelated.read_bytes()).hexdigest()))

    def test_a_wrong_leaf_pin_sends_nothing(self):
        self.assert_refused_before_request(self.forwarder(tls_pinned_sha256=self.certificates["unrelated_pin"]))

    def test_the_right_leaf_pin_passes(self):
        forwarder = self.forwarder(tls_pinned_sha256=self.certificates["pin"].upper())
        with _post(forwarder.base_url + "/chat/completions") as response:
            self.assertEqual(response.read(), b"".join(EVENTS))

    def test_a_changed_or_missing_anchor_refuses_before_any_socket(self):
        for changes, code in (({"ca_sha256": "0" * 64}, "trust_anchor_digest_mismatch"),
                              ({"ca_file": self.certificates["anchor"] + ".absent"}, "trust_anchor_unreadable"),
                              ({"ca_file": self.certificates["key"], "ca_sha256": None}, "trust_anchor_invalid")):
            with self.subTest(code=code), self.assertRaises(vf.ForwarderError) as caught:
                self.forwarder(**changes)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.origin.accepted, 0)

    def test_unverifiable_or_credential_bearing_declarations_are_refused(self):
        cases = ({"upstream": f"http://127.0.0.1:{self.origin.server_port}/v1"},
                 {"upstream": f"https://user:secret@127.0.0.1:{self.origin.server_port}/v1"},
                 {"upstream": self.upstream + "?beta=1"}, {"upstream": self.upstream + "#part"},
                 {"upstream": "https:///v1"}, {"tls_server_name": "*.fixture.test"},
                 {"tls_server_name": "Origin.Fixture.Test"}, {"tls_pinned_sha256": "12" * 31},
                 {"authorization": "Bearer one\r\nX-Injected: two"}, {"authorization": " "})
        for changes in cases:
            with self.subTest(changes=sorted(changes)), self.assertRaises(vf.ForwarderError):
                self.forwarder(**changes)
        self.assertEqual(self.origin.accepted, 0)

    def test_nothing_outside_the_path_token_or_the_api_base_is_forwarded(self):
        forwarder = self.forwarder()
        port = forwarder.base_url.split(":")[2].split("/")[0]
        for path in ("/v1/chat/completions", f"/{'x' * 32}/v1/chat/completions",
                     f"/{forwarder.token}/server_info", f"/{forwarder.token}/v1x/chat/completions", "/"):
            with self.subTest(path=path):
                status, body = _error(f"http://127.0.0.1:{port}{path}")
                self.assertEqual((status, body["error"]["code"]), (404, "not_forwarded"))
        self.assertEqual((self.origin.accepted, self.origin.requests), (0, []))

    def test_other_methods_are_not_forwarded(self):
        forwarder = self.forwarder()
        connection = http.client.HTTPConnection("127.0.0.1", int(forwarder.base_url.split(":")[2].split("/")[0]),
                                                timeout=10)
        connection.request("DELETE", "/" + forwarder.token + "/v1/models")
        self.assertEqual(connection.getresponse().status, 405)
        connection.close()
        self.assertEqual(self.origin.requests, [])

    def test_a_truncated_upstream_body_reaches_the_client_as_a_broken_stream(self):
        self.origin.mode = "truncate"
        forwarder = self.forwarder()
        with _post(forwarder.base_url + "/chat/completions") as response:
            with self.assertRaises(http.client.IncompleteRead):
                response.read()

    def test_a_handshake_reports_the_verified_leaf_without_sending_http(self):
        result = self.forwarder().handshake()
        self.assertEqual((result["verified"], result["leaf_sha256"]), (True, self.certificates["pin"]))
        self.assertEqual(self.origin.requests, [])

    def test_the_summary_names_no_host_name_token_or_key(self):
        forwarder = self.forwarder()
        text = json.dumps(forwarder.summary())
        for private in (NAME, "127.0.0.1", str(self.origin.server_port), forwarder.token, KEY):
            self.assertNotIn(private, text)
        self.assertEqual(forwarder.summary()["authorization"], "replaced")


class AnchorContextTest(unittest.TestCase):
    def test_the_committed_tactical_root_is_the_only_trusted_certificate(self):
        root = ROOT_ANCHOR / "cloudflare-origin-ca-rsa-root.pem"
        context = vf.anchor_context(root, hashlib.sha256(root.read_bytes()).hexdigest())
        self.assertEqual((context.verify_mode, context.check_hostname), (ssl.CERT_REQUIRED, True))
        [certificate] = context.get_ca_certs()
        subject = dict(item[0] for item in certificate["subject"])
        self.assertEqual(certificate["subject"], certificate["issuer"], "a self-signed root")
        self.assertEqual(subject["organizationalUnitName"], "CloudFlare Origin SSL Certificate Authority")
        self.assertEqual(subject["organizationName"], "CloudFlare, Inc.")


if __name__ == "__main__":
    unittest.main()
