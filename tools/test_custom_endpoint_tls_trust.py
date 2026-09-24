"""The custom endpoint's TLS trust contract against a real local TLS server.

A throwaway certificate authority, created per test run in a temporary
folder, signs a leaf certificate for ``origin.fixture.test``. The server
listens on 127.0.0.1, so the connect host differs from the expected name,
as it does for an origin reached by one DNS name that presents a
certificate for another. Each known-wrong control asserts that the server
parsed no request, so no request line, header, body or key was sent.
"""
import datetime
import hashlib
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

from loop_engine.core import custom_endpoint as ce
from loop_engine.core.custom_endpoint import CustomEndpoint, EndpointError, make_adapter
from loop_engine.core.model_capabilities import ModelOutputCapability
from loop_engine.core.runtime_settings import ProviderSettings, SettingsError

KEY = "fixture-key-" + "7" * 24
NAME = "origin.fixture.test"
MODEL = "fixture-coder"


def _certificates(folder: Path) -> dict:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    now = datetime.datetime.now(datetime.timezone.utc)

    def usage(signing):
        return x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                             data_encipherment=False, key_agreement=False, key_cert_sign=signing,
                             crl_sign=signing, encipher_only=False, decipher_only=False)

    def build(subject, issuer, key, signer, *extensions):
        builder = (x509.CertificateBuilder()
                   .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
                   .issuer_name(issuer).public_key(key.public_key())
                   .serial_number(x509.random_serial_number())
                   .not_valid_before(now - datetime.timedelta(minutes=5))
                   .not_valid_after(now + datetime.timedelta(days=1))
                   .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False))
        for extension, critical in extensions:
            builder = builder.add_extension(extension, critical=critical)
        return builder.sign(signer, hashes.SHA256())

    def authority(label):
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label)])
        return key, build(label, name, key, key, (x509.BasicConstraints(ca=True, path_length=None), True),
                          (usage(True), True))

    anchor_key, anchor = authority("Fixture trust anchor")
    _unrelated_key, unrelated = authority("Fixture unrelated anchor")
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf = build(NAME, anchor.subject, leaf_key, anchor_key,
                 (x509.SubjectAlternativeName([x509.DNSName(NAME)]), False),
                 (x509.BasicConstraints(ca=False, path_length=None), True), (usage(False), True),
                 (x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False),
                 (x509.AuthorityKeyIdentifier.from_issuer_public_key(anchor_key.public_key()), False))
    paths = {"anchor": folder / "anchor.pem", "unrelated": folder / "unrelated.pem",
             "leaf": folder / "leaf.pem", "key": folder / "leaf.key"}
    for label, certificate in (("anchor", anchor), ("unrelated", unrelated), ("leaf", leaf)):
        paths[label].write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    paths["key"].write_bytes(leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()))
    return {**{label: str(path) for label, path in paths.items()},
            "pin": hashlib.sha256(leaf.public_bytes(serialization.Encoding.DER)).hexdigest(),
            "unrelated_pin": hashlib.sha256(unrelated.public_bytes(serialization.Encoding.DER)).hexdigest()}


class _Recorder(http.server.BaseHTTPRequestHandler):
    def _record(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.server.requests.append({"method": self.command, "path": self.path,
                                     "headers": dict(self.headers), "body": body})
        return body

    def _json(self, value, status=200):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        self._record()
        if self.server.redirect_to:
            self.send_response(303)
            self.send_header("Location", self.server.redirect_to)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._json({"id": "fixture", "object": "chat.completion", "model": MODEL,
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ready"},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1}})

    def do_GET(self):
        self._record()
        self._json({"object": "list", "data": [{"id": MODEL, "object": "model"}]})

    def log_message(self, *args):
        return None


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, context=None):
        super().__init__(("127.0.0.1", 0), _Recorder)
        self.context, self.requests, self.accepted, self.redirect_to = context, [], 0, ""

    def get_request(self):
        connection, address = super().get_request()
        self.accepted += 1
        if self.context is not None:
            connection = self.context.wrap_socket(connection, server_side=True)
        return connection, address

    def handle_error(self, request, client_address):
        # A refused client closes the connection on purpose; the assertions
        # read the recorded requests, not this thread's broken pipe.
        return None


@unittest.skipUnless(find_spec("cryptography"), "cryptography creates the throwaway certificate authority")
class CustomEndpointTLSTrustTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.certificates = _certificates(Path(cls.folder.name))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.certificates["leaf"], cls.certificates["key"])
        cls.tls, cls.plain = _Server(context), _Server()
        for server in (cls.tls, cls.plain):
            threading.Thread(target=server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        for server in (cls.tls, cls.plain):
            server.shutdown()
            server.server_close()
        cls.folder.cleanup()

    def setUp(self):
        for server in (self.tls, self.plain):
            server.requests.clear()
            server.accepted = 0
        self.tls.redirect_to = ""

    def endpoint(self, **changes):
        fields = {"name": "tls_fixture", "base_url": f"https://127.0.0.1:{self.tls.server_port}/v1",
                  "model": MODEL, "api_key": KEY, "wire": "openai", "locality": "local", "stream": "buffer",
                  "tls_verification": "ca_file", "tls_ca_file": self.certificates["anchor"],
                  "tls_server_name": NAME, "tls_pinned_sha256": self.certificates["pin"],
                  "output_capability": ModelOutputCapability(64, "offline TLS fixture")}
        fields.update(changes)
        return CustomEndpoint(**fields)

    def chat(self, endpoint):
        return make_adapter(endpoint).chat("hello", temperature=0.0, timeout=10)

    def assert_refused_before_request(self, result, accepted=None):
        self.assertFalse(result.ok)
        self.assertTrue(result.error.startswith("tls_trust_refused:"), result.error)
        self.assertEqual(result.physical_requests, 0)
        self.assertEqual(self.tls.requests, [])
        self.assertNotIn(KEY, result.error)
        if accepted is not None:
            self.assertEqual(self.tls.accepted, accepted)

    def test_correct_name_anchor_and_pin_pass(self):
        result = self.chat(self.endpoint())
        self.assertTrue(result.ok, result.error)
        self.assertEqual((result.text, result.model, result.physical_requests), ("ready", MODEL, 1))
        [request] = self.tls.requests
        self.assertEqual(request["headers"]["Authorization"], "Bearer " + KEY)
        self.assertEqual(json.loads(request["body"])["model"], MODEL)
        listing = make_adapter(self.endpoint()).live_model_listing(timeout=10)
        self.assertTrue(listing["ok"] and listing["model_listed"], listing)

    def test_upper_case_colon_pin_is_normalized_and_still_passes(self):
        pin = ":".join(self.certificates["pin"][i:i + 2] for i in range(0, 64, 2)).upper()
        endpoint = self.endpoint(tls_pinned_sha256=pin)
        self.assertEqual(endpoint.tls_pinned_sha256, self.certificates["pin"])
        self.assertTrue(self.chat(endpoint).ok)

    def test_wrong_pin_refuses_before_any_request(self):
        result = self.chat(self.endpoint(tls_pinned_sha256=self.certificates["unrelated_pin"]))
        self.assert_refused_before_request(result)
        self.assertIn("pinned", result.error)
        listing = make_adapter(self.endpoint(tls_pinned_sha256="0" * 64)).live_model_listing(timeout=10)
        self.assertEqual(listing["error_type"], "TLSTrustRefused")
        self.assertEqual(self.tls.requests, [])

    def test_wrong_server_name_refuses_before_any_request(self):
        self.assert_refused_before_request(self.chat(self.endpoint(tls_server_name="other.fixture.test")))

    def test_connect_host_is_not_accepted_as_the_name(self):
        # Without the expected name the certificate cannot match 127.0.0.1.
        self.assert_refused_before_request(self.chat(self.endpoint(tls_server_name="")))

    def test_missing_anchor_file_refuses_before_any_socket(self):
        missing = str(Path(self.certificates["anchor"]).with_name("absent.pem"))
        self.assert_refused_before_request(self.chat(self.endpoint(tls_ca_file=missing)), accepted=0)

    def test_unrelated_anchor_refuses_before_any_request(self):
        self.assert_refused_before_request(self.chat(self.endpoint(tls_ca_file=self.certificates["unrelated"])))

    def test_system_store_without_the_anchor_refuses_before_any_request(self):
        self.assert_refused_before_request(self.chat(self.endpoint(tls_verification="default", tls_ca_file="")))

    def test_plain_http_declarations_are_refused(self):
        plain = f"http://127.0.0.1:{self.plain.server_port}/v1"
        for changes in ({"base_url": plain}, {"base_url": plain, "tls_verification": "default", "tls_ca_file": "",
                                              "tls_pinned_sha256": ""}):
            with self.subTest(changes=sorted(changes)), self.assertRaises(EndpointError):
                self.endpoint(**changes)
        with self.assertRaises(SettingsError):
            ProviderSettings("fixture", kind="custom", endpoint=plain, model=MODEL,
                             tls_verification="ca_file", tls_ca_file=self.certificates["anchor"])
        self.assertEqual(self.plain.accepted, 0)

    def test_inconsistent_trust_declarations_are_refused(self):
        for changes in ({"tls_ca_file": ""}, {"tls_verification": "default"},
                        {"tls_verification": "skip", "tls_ca_file": ""}, {"tls_pinned_sha256": "12" * 31},
                        {"tls_server_name": "*.fixture.test"}, {"tls_server_name": "Origin.Fixture.Test"}):
            with self.subTest(changes=sorted(changes)), self.assertRaises(EndpointError):
                self.endpoint(**changes)

    def test_plain_http_through_a_trusted_opener_sends_nothing(self):
        opener = ce._endpoint_opener(self.endpoint())
        request = urllib.request.Request(f"http://127.0.0.1:{self.plain.server_port}/v1/models",
                                         headers={"Authorization": "Bearer " + KEY})
        with self.assertRaises(urllib.error.URLError) as caught:
            opener.open(request, timeout=10)
        self.assertIsInstance(ce._trust_refusal(caught.exception), ce.TLSTrustRefused)
        self.assertEqual((self.plain.accepted, self.plain.requests), (0, []))

    def test_redirect_is_not_followed_and_the_key_stays_with_the_verified_server(self):
        self.tls.redirect_to = f"http://127.0.0.1:{self.plain.server_port}/collect"
        result = self.chat(self.endpoint())
        self.assertFalse(result.ok)
        self.assertTrue(result.error.startswith("HTTP 303"), result.error)
        self.assertEqual(result.physical_requests, 1)
        self.assertEqual(len(self.tls.requests), 1)
        self.assertEqual((self.plain.accepted, self.plain.requests), (0, []))

    def test_endpoint_record_and_settings_carry_the_contract_but_never_the_key(self):
        endpoint = self.endpoint()
        record = endpoint.describe()
        self.assertEqual((record["tls_server_name"], record["tls_pinned_sha256"]), (NAME, self.certificates["pin"]))
        self.assertNotIn(KEY, json.dumps(record) + repr(endpoint))
        settings = ProviderSettings("fixture", kind="custom", endpoint=endpoint.base_url, model=MODEL,
                                    tls_verification="ca_file", tls_ca_file=self.certificates["anchor"],
                                    tls_server_name=NAME, tls_pinned_sha256=self.certificates["pin"].upper())
        built = settings.custom_endpoint(KEY)
        self.assertEqual((built.tls_server_name, built.tls_pinned_sha256), (NAME, self.certificates["pin"]))
        self.assertEqual(settings.safe_summary()["tls_pinned_sha256"], self.certificates["pin"])
        with self.assertRaises(SettingsError):
            ProviderSettings("ollama_cloud", tls_pinned_sha256=self.certificates["pin"])


if __name__ == "__main__":
    unittest.main()
