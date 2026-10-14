"""AgentStudios uses the shared service with a separate exact-origin identity.

HTTP requests use real loopback transport and synthetic identity/mail providers.
No live account, DNS, model or provider effect is performed by this suite.
"""
from dataclasses import replace
import unittest
from unittest import mock

from loop_engine.core.service_runtime.brand_profiles import ServiceBrandProfile
from loop_engine.core.service_runtime.http import ServiceHttpConfiguration, ServiceHttpError
import test_brand_presentations as existing


ORIGIN = "https://agentstudios.example.test"
HOST = "agentstudios.example.test"


class StudiosConfigurationTests(unittest.TestCase):
    def test_exact_profile_is_account_enabled_but_never_implicitly_admitted(self):
        profile = ServiceBrandProfile("agentstudios", ORIGIN, "AgentStudios")
        self.assertFalse(profile.public_only)
        config = ServiceHttpConfiguration("https://service.example.test", ("service.example.test",))
        self.assertEqual(config.brand_profiles, ())
        self.assertNotIn(HOST, config.allowed_hosts)
        self.assertNotIn(ORIGIN, config.allowed_origins)
        for changes in ({"brand_profiles": (profile,)},
                        {"brand_profiles": (profile,), "allowed_hosts": (*config.allowed_hosts, HOST)},
                        {"brand_profiles": (profile,), "allowed_origins": (ORIGIN,)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes)
        admitted = replace(config, brand_profiles=(profile,),
                           allowed_hosts=(*config.allowed_hosts, HOST), allowed_origins=(ORIGIN,))
        self.assertEqual(admitted.brand_profiles, (profile,))
        for changes in ({"display_name": "Baltor"}, {"display_name": "AgentStudio"},
                        {"record_type": "service_brand_profile/v0"},
                        {"public_base_url": ORIGIN + "/path"},
                        {"public_base_url": "https://user@" + HOST}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(profile, **changes)

    def test_ten_explicit_profiles_fit_without_unbounded_configuration(self):
        profiles = tuple(ServiceBrandProfile("agentstudios", f"https://studio-{index}.example.test", "AgentStudios")
                         for index in range(11))
        config = ServiceHttpConfiguration("https://service.example.test",
            ("service.example.test", *(profile.host for profile in profiles)),
            allowed_origins=tuple(profile.public_base_url for profile in profiles), brand_profiles=profiles[:10])
        self.assertEqual(len(config.brand_profiles), 10)
        with self.assertRaises(ValueError):
            replace(config, brand_profiles=profiles)


class StudiosHttpTests(existing.BrandHttpTests):
    """Reuse the exact shared-state, identity, billing and OAuth replay oracles."""

    def setUp(self):
        profile = ServiceBrandProfile("agentstudios", ORIGIN, "AgentStudios")
        patched = mock.patch.multiple(existing, ORIGIN=ORIGIN, HOST=HOST, PROFILE=profile)
        patched.start()
        self.addCleanup(patched.stop)
        super().setUp()

    def test_brand_metadata_and_pages_stay_local_and_default_site_survives(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200, home.text)
        self.assertIn("AgentStudios", home.text)
        self.assertIn(ORIGIN, home.text)
        identity = self.client.get("/api/v1/account/identity").json()["result"]
        self.assertEqual(identity["redirect_url"], ORIGIN + "/auth/callback")
        capabilities = self.client.get("/api/v1/capabilities").json()["result"]
        self.assertEqual(capabilities["website"]["display_name"], "AgentStudios")
        metadata = self.client.get("/.well-known/oauth-authorization-server").json()
        for key, suffix in (("issuer", ""), ("authorization_endpoint", "/authorize"),
                            ("token_endpoint", "/token"), ("service_documentation", "/connect")):
            self.assertEqual(metadata[key], ORIGIN + suffix)
        resource = self.client.get("/.well-known/oauth-protected-resource/mcp").json()
        self.assertEqual(resource["resource"], ORIGIN + "/mcp")
        self.assertEqual(resource["authorization_servers"], [ORIGIN])
        self.assertEqual(resource["resource_documentation"], ORIGIN + "/connect")
        self.assertEqual(self.fixture.client.get("/.well-known/oauth-authorization-server").json()["issuer"], self.fixture.base)
        self.assertNotIn("AgentStudios", self.fixture.client.get("/").text)
        config = self.client.get("/client.example.json")
        self.assertEqual(config.status_code, 200, config.text)
        self.assertEqual(config.json(), {"record_type": "baltor_library_client_configuration/v2", "origin": ORIGIN,
                                        "credential_environment": "BALTOR_SERVICE_TOKEN", "authority_effects": ["reads_fs"]})

    def test_signup_and_recovery_email_use_brand_without_new_limiters(self):
        for action, record_type in (("signup", "service_account_signup_request/v2"),
                                    ("recovery", "service_account_recovery_request/v1")):
            response = self.client.post("/api/v1/account/" + action, headers={"Origin": ORIGIN},
                json={"record_type": record_type, "email": "studio@example.invalid"})
            self.assertEqual(response.status_code, 202, response.text)
            self.assertIn(ORIGIN + "/auth/confirm?", self.mail.sent_bodies[-1])
            self.assertIn("AgentStudios", self.mail.sent_bodies[-1])
            self.assertNotIn("AgentFeeds", self.mail.sent_bodies[-1])
            self.assertNotIn(self.fixture.base, self.mail.sent_bodies[-1])
        self.assertEqual(len(self.mail.mail_requests), 2)

    def test_unknown_routes_assets_and_errors_never_fall_back_to_baltor_html(self):
        for path in ("/not-a-page", "/harness-files", "/assets/service.js", "/assets/agentfeeds/site.css",
                     "/assets/agentfoundry/site.css", "/assets/agentafk/site.css", "/feeds/catalogue.json"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404, response.text)
                self.assertEqual(response.json()["error"]["code"], "route_unavailable")
                self.assertNotIn("text/html", response.headers["content-type"])
                self.assertNotIn("Baltor", response.text)
        for headers in ({"Host": "agentstudios.si"}, {"Host": "www.agentstudios.si"},
                        {"Host": HOST, "Origin": "null"},
                        {"Host": HOST, "Origin": "https://www.agentstudios.example.test"}):
            with self.subTest(headers=headers):
                response = self.client.get("/", headers=headers)
                self.assertIn(response.status_code, (403, 421), response.text)
                self.assertNotIn("access-control-allow-origin", response.headers)
                self.assertNotIn("text/html", response.headers["content-type"])

    def test_page_head_and_revalidation_keep_same_origin_representation(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        head = self.client.head("/")
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.content, b"")
        self.assertEqual(head.headers["content-length"], str(len(response.content)))
        self.assertEqual(head.headers["etag"], response.headers["etag"])
        unchanged = self.client.get("/", headers={"If-None-Match": response.headers["etag"]})
        self.assertEqual(unchanged.status_code, 304)
        self.assertEqual(unchanged.content, b"")
        self.assertIn("default-src 'none'", response.headers["content-security-policy"])
        self.assertEqual(response.headers["x-frame-options"], "DENY")

    def test_browser_errors_keep_studios_assets_and_escaped_failure_reference(self):
        from loop_engine.core.service_runtime import agentstudios_pages, web_pages

        def assert_studios_error(response, status):
            self.assertEqual(response.status_code, status, response.text)
            self.assertIn("text/html", response.headers["content-type"])
            self.assertIn("AgentStudios", response.text)
            self.assertIn("/assets/agentstudios/site.css", response.text)
            self.assertIn("/assets/agentstudios/mark.svg", response.text)
            for path in ("/assets/service.css", "/assets/architecture.css", "/assets/baltor-mark.svg"):
                self.assertNotIn(path, response.text)
            self.assertIn("noindex", response.text)
            self.assertIn("default-src 'none'", response.headers["content-security-policy"])

        headers = {"Accept": "text/html"}
        absent = self.client.get("/not-a-page?private-context=must-not-be-reflected", headers=headers)
        assert_studios_error(absent, 404)
        self.assertNotIn("must-not-be-reflected", absent.text)
        with mock.patch.object(self.presentation, "capabilities", side_effect=ServiceHttpError("catalogue_unavailable", 503)):
            failed = self.client.get("/api/v1/capabilities", headers=headers)
        assert_studios_error(failed, 503)
        self.assertIn("Reference", failed.text)
        for asset in ("/assets/agentstudios/site.css", "/assets/agentstudios/mark.svg"):
            self.assertEqual(self.client.get(asset).status_code, 200)
        # The old shared HTML response must fail the new presentation oracle.
        with mock.patch.object(agentstudios_pages, "error_page", return_value=web_pages.missing_address_page("AgentStudios")):
            wrong = self.client.get("/not-a-page", headers=headers)
        with self.assertRaises(AssertionError):
            assert_studios_error(wrong, 404)


if __name__ == "__main__":
    unittest.main()
