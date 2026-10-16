"""Private endpoint settings: read at run time from operator configuration, refused when absent or malformed.

No keyring, network or private value is touched: the environment and the keyring are fixtures, and every
value below is an invented name under .invalid or .test.
"""
from __future__ import annotations

import json
import unittest

from tools import private_endpoints as pe

URL = "https://origin.fixture.invalid:6969/v1"
NAME = "origin.fixture.test"
URL_VARIABLE, NAME_VARIABLE = "LOOP_ENGINE_TACTICAL_BASE_URL", "LOOP_ENGINE_TACTICAL_TLS_SERVER_NAME"
URL_REFERENCE, NAME_REFERENCE = "tactical-model-endpoint", "tactical-model-tls-server-name"


def no_keyring(reference):
    raise LookupError("no keyring in this test")


class PrivateEndpointTest(unittest.TestCase):
    def resolve(self, environ, keyring=no_keyring):
        return pe.resolve("tactical", environ=environ, keyring=keyring)

    def test_the_environment_supplies_both_settings_and_a_summary_holds_only_digests(self):
        endpoint = self.resolve({URL_VARIABLE: URL + "/", NAME_VARIABLE: NAME})
        self.assertEqual((endpoint.base_url, endpoint.tls_server_name), (URL, NAME))
        self.assertEqual((endpoint.host, endpoint.port), ("origin.fixture.invalid", 6969))
        summary = json.dumps(endpoint.summary())
        for private in (URL, NAME, "origin.fixture"):
            self.assertNotIn(private, summary)
            self.assertNotIn(private, repr(endpoint))
        self.assertEqual(endpoint.summary()["sources"], {"base_url": "environment", "tls_server_name": "environment"})

    def test_the_keyring_supplies_a_setting_the_environment_lacks(self):
        held = {URL_REFERENCE: URL, NAME_REFERENCE: NAME}
        endpoint = self.resolve({NAME_VARIABLE: ""}, keyring=held.__getitem__)
        self.assertEqual((endpoint.base_url, endpoint.tls_server_name), (URL, NAME))
        self.assertEqual(endpoint.summary()["sources"], {"base_url": "keyring", "tls_server_name": "keyring"})

    def test_the_environment_wins_over_the_keyring(self):
        endpoint = self.resolve({URL_VARIABLE: URL}, keyring={URL_REFERENCE: "https://other.invalid/v1"}.get)
        self.assertEqual(endpoint.base_url, URL)

    def test_an_absent_connect_url_refuses_and_says_what_to_set(self):
        for keyring in (no_keyring, lambda reference: "", {}.get):
            with self.subTest(keyring=keyring), self.assertRaises(pe.PrivateEndpointError) as caught:
                self.resolve({NAME_VARIABLE: NAME}, keyring=keyring)
            self.assertEqual(caught.exception.code, "private_endpoint_unconfigured")
            self.assertIn(URL_VARIABLE, str(caught.exception))
            self.assertIn("store --ref " + URL_REFERENCE, str(caught.exception))
            self.assertNotIn(NAME, str(caught.exception))

    def test_an_absent_certificate_name_leaves_the_url_host_as_the_name(self):
        endpoint = self.resolve({URL_VARIABLE: URL})
        self.assertEqual(endpoint.tls_server_name, "")

    def test_malformed_values_refuse_without_echoing_them(self):
        cases = ({URL_VARIABLE: "http://origin.fixture.invalid:6969/v1"},
                 {URL_VARIABLE: "https://user:secret@origin.fixture.invalid/v1"},
                 {URL_VARIABLE: URL + "?key=1"}, {URL_VARIABLE: URL + "#part"},
                 {URL_VARIABLE: "https://Origin.Fixture.Invalid/v1"}, {URL_VARIABLE: "https://origin.fixture.invalid:x/v1"},
                 {URL_VARIABLE: URL + " extra"}, {URL_VARIABLE: URL, NAME_VARIABLE: "*.fixture.test"},
                 {URL_VARIABLE: URL, NAME_VARIABLE: "Origin.Fixture.Test"},
                 {URL_VARIABLE: URL, NAME_VARIABLE: "localhost"})
        for environ in cases:
            with self.subTest(environ=environ), self.assertRaises(pe.PrivateEndpointError) as caught:
                self.resolve(environ)
            self.assertEqual(caught.exception.code, "private_endpoint_invalid")
            for value in environ.values():
                self.assertNotIn(value, str(caught.exception))

    def test_an_undeclared_endpoint_or_reference_is_refused(self):
        with self.assertRaises(pe.PrivateEndpointError) as caught:
            pe.resolve("unknown-box", environ={})
        self.assertEqual(caught.exception.code, "private_endpoint_undeclared")
        with self.assertRaises(pe.PrivateEndpointError) as caught:
            pe.setting("not-in-the-manifest", environ={}, keyring=no_keyring)
        self.assertEqual(caught.exception.code, "private_setting_reference_unknown")

    def test_binding_references_resolve_to_provider_fields(self):
        references = {"endpoint": URL_REFERENCE, "tls_server_name": NAME_REFERENCE}
        self.assertEqual(pe.resolve_references(references, environ={URL_VARIABLE: URL, NAME_VARIABLE: NAME},
                                               keyring=no_keyring),
                         {"endpoint": URL, "tls_server_name": NAME})
        self.assertEqual(pe.resolve_references(references, environ={URL_VARIABLE: URL}, keyring=no_keyring),
                         {"endpoint": URL})
        for invalid in ({}, {"tls_server_name": NAME_REFERENCE}, {"endpoint": URL_REFERENCE, "model": "x"}, []):
            with self.subTest(invalid=invalid), self.assertRaises(pe.PrivateEndpointError):
                pe.resolve_references(invalid, environ={URL_VARIABLE: URL}, keyring=no_keyring)
        with self.assertRaises(pe.PrivateEndpointError) as caught:
            pe.resolve_references(references, environ={}, keyring=no_keyring)
        self.assertEqual(caught.exception.code, "private_endpoint_unconfigured")

    def test_the_manifest_declares_the_two_references_this_module_documents(self):
        data = pe.references_manifest()["api_keys"]
        self.assertEqual(data[URL_REFERENCE]["environment"], URL_VARIABLE)
        self.assertEqual(data[NAME_REFERENCE]["environment"], NAME_VARIABLE)
        self.assertEqual(pe.PRIVATE_ENDPOINTS["tactical"], {"base_url": URL_REFERENCE, "tls_server_name": NAME_REFERENCE})
        for reference in (URL_REFERENCE, NAME_REFERENCE):
            self.assertEqual(data[reference]["service"], "tactical")
            self.assertNotIn("value", data[reference])


if __name__ == "__main__":
    unittest.main()
