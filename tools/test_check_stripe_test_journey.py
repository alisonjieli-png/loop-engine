"""Offline checks of the Stripe test-mode journey: its refusals, its redaction and the host file it serves.

The journey itself needs the Stripe test environment, the Stripe command line and a browser, so it is run by an
operator (tools/check_stripe_test_journey.py). These checks need none of them. They hold the parts that decide
whether a run is safe and faithful: a key that is not a Stripe test key is refused before any request, the
listener's signing secret never reaches a stored line, an existing report is never overwritten, and the host file
the journey serves passes the deployment's own host loader with the billing block installed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import check_stripe_test_journey as journey
import setup_stripe_sandbox as sandbox

KEY_BODY = "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6"
MANIFEST = {"record_type": sandbox.MANIFEST_RECORD_TYPE,
            "api_keys": {"stripe-test": {"service": "stripe", "account": "acct_1UHZ9KCCxLfArYED",
                                         "purpose": "runtime-test-api", "environment": "STRIPE_API_KEY",
                                         "required_prefixes": ["sk_test_", "rk_test_"]}}}
SECRET_LINE = ("Ready! You are using Stripe API Version [2026-08-26.dahlia]. Your webhook signing secret is "
               "whsec_0123456789abcdefABCDEF0123456789 (^C to quit)")


class KeyRefusalTests(unittest.TestCase):
    def test_a_test_key_for_the_recorded_account_is_accepted(self):
        binding, key = journey.require_test_key({"STRIPE_API_KEY": "sk_test_" + KEY_BODY}, MANIFEST)
        self.assertEqual(binding.account_id, "acct_1UHZ9KCCxLfArYED")
        self.assertEqual(key, "sk_test_" + KEY_BODY)

    def test_a_live_key_a_publishable_key_and_no_key_are_refused_before_any_request(self):
        for value in ("sk_live_" + KEY_BODY, "rk_live_" + KEY_BODY, "pk_test_" + KEY_BODY, "", None):
            environment = {} if value is None else {"STRIPE_API_KEY": value}
            with self.assertRaises(journey.Refusal, msg=repr(value)):
                journey.require_test_key(environment, MANIFEST)

    def test_a_manifest_that_allows_live_prefixes_is_refused(self):
        widened = json.loads(json.dumps(MANIFEST))
        widened["api_keys"]["stripe-test"]["required_prefixes"] = ["sk_test_", "sk_live_"]
        with self.assertRaises(journey.Refusal):
            journey.require_test_key({"STRIPE_API_KEY": "sk_test_" + KEY_BODY}, widened)


class ListenerLogTests(unittest.TestCase):
    def test_the_signing_secret_is_taken_once_and_never_stored(self):
        log = journey.ListenerLog()
        log.consume(SECRET_LINE)
        self.assertEqual(log.version, "2026-08-26.dahlia")
        self.assertTrue(log.secret.startswith("whsec_"))
        self.assertNotIn(log.secret, json.dumps(log.lines))
        self.assertIn("whsec_[removed]", log.lines[0])

    def test_without_redaction_the_secret_would_be_stored(self):
        # Known-wrong control: the same line kept as printed holds the secret, which the check above refuses.
        log = journey.ListenerLog()
        with mock.patch.object(journey, "redact", lambda line: line):
            log.consume(SECRET_LINE)
        self.assertIn(log.secret, json.dumps(log.lines))

    def test_forwarded_events_and_the_service_answers_are_paired(self):
        log = journey.ListenerLog()
        for line in ("2026-10-05 19:56:11   --> invoice.paid [evt_1A]",
                     "2026-10-05 19:56:11   --> customer.subscription.created [evt_1B]",
                     "2026-10-05 19:56:12  <--  [503] POST http://127.0.0.1:5000/api/v1/billing/webhook [evt_1A]",
                     "2026-10-05 19:56:12  <--  [200] POST http://127.0.0.1:5000/api/v1/billing/webhook [evt_1B]"):
            log.consume(line)
        self.assertEqual(log.delivered("customer.subscription.created"), ["evt_1B"])
        self.assertEqual(log.delivered("invoice.paid"), [])
        self.assertEqual({row["event_id"]: row["statuses"] for row in log.deliveries()}, {"evt_1A": [503], "evt_1B": [200]})


class AddressTests(unittest.TestCase):
    def test_hosted_pages_are_recognised_only_on_the_exact_stripe_host(self):
        from loop_engine.core.service_runtime.stripe_sessions import CHECKOUT_HOST
        self.assertTrue(journey.hosted_on("https://" + CHECKOUT_HOST + "/c/pay/cs_test_1", CHECKOUT_HOST))
        for address in ("http://" + CHECKOUT_HOST + "/c/pay/cs_test_1", "https://" + CHECKOUT_HOST + ".example.com/x",
                        "https://user@" + CHECKOUT_HOST + "/x", "https://billing.example.com/x", ""):
            self.assertFalse(journey.hosted_on(address, CHECKOUT_HOST), address)


class ReportTests(unittest.TestCase):
    def test_an_existing_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "journey.json"
            path.write_text("{}")
            with self.assertRaises(journey.Refusal):
                journey.reserve_report(path)
            self.assertEqual(journey.reserve_report(Path(folder) / "new.json").name, "new.json")


class HostFileTests(unittest.TestCase):
    """The host file the journey serves is read by the deployment's own loader, with billing installed."""

    def test_the_host_loader_installs_checkout_the_portal_and_the_webhook(self):
        from loop_engine.core.service_runtime.http_entrypoint import load_host_application
        objects = {"price_id": "price_1Journey", "portal_configuration_id": "bpc_1Journey", "plan_ref": "pro-monthly",
                   "plan_label": "Baltor Pro", "unit_amount": 2900, "currency": "usd"}
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {
                journey.PUBLISHABLE_KEY_ENVIRONMENT: "sb_publishable_journey_stand_in"}):
            binding, _key = journey.require_test_key({"STRIPE_API_KEY": "sk_test_" + KEY_BODY}, MANIFEST)
            path = journey.write_host(Path(folder), "http://127.0.0.1:5000", 5000, "http://127.0.0.1:5001",
                                      objects, "2026-08-26.dahlia", binding.account_id,
                                      binding.service_api_key_reference)
            application, configuration = load_host_application(path)
            offers = application.billing_sessions.host_offers()
            self.assertEqual(offers, {"checkout": True, "portal": True})
            self.assertEqual(application.billing_processor.policy.allowed_price_ids, ("price_1Journey",))
            self.assertIn("billing:manage", application.browser_identity.configuration.allowed_scopes)
            self.assertEqual(application.billing_sessions.configuration.api_key_ref, "env:STRIPE_API_KEY")
            self.assertEqual(configuration["accounts"]["founding_free_monthly_accounts"], 0)
            # The billing block names environment references only, never a value.
            self.assertNotIn("sk_test_", path.read_text())
            self.assertNotIn("whsec_", path.read_text())


if __name__ == "__main__":
    unittest.main()
