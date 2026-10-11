"""Checkout plan admission precedes any provider or customer effect.

All provider responses and credentials are in-memory fixtures. No live
customer, session, subscription or payment is created by these checks.
"""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

from loop_engine.core.service_runtime import stripe_session_checks as fixtures
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from loop_engine.core.service_runtime.stripe_sessions import (
    CHECKOUT_OPERATION, PORTAL_OPERATION, PORTAL_PATH, POST_METHOD,
    BillingSessionRequest, StripeSessionAdapter, StripeSessionPlan,
)


def pro_only(root, *, bind_customers=False):
    held = fixtures.fixture(root, bind_customers=bind_customers)
    held.policy = replace(held.policy, plans=(StripeSessionPlan("pro", "Pro", "price_basic", 1),))
    held.adapter = StripeSessionAdapter(held.runtime, held.policy, held.secret, transport=held.provider)
    fixtures.install_policy(held, held.adapter)
    return held


class CheckoutPlanBeforeEffectsTests(TestCase):
    def require_refusal(self, held, request, code):
        with self.assertRaises(ServiceRuntimeError) as caught:
            held.adapter.create(fixtures.principal(held), request)
        self.assertEqual(caught.exception.code, code)

    def assert_no_effects(self, held):
        self.assertEqual([(call.method, call.path) for call in held.provider.calls], [])
        self.assertEqual(held.secret_calls, [])
        self.assertEqual(held.provider.customers, {})
        self.assertEqual(fixtures.customer_rows(held), [])
        self.assertEqual(fixtures.rows(held), [])

    def test_unavailable_basic_max_and_unknown_plan_refuse_before_customer_creation(self):
        for plan in ("basic", "max", "unconfigured"):
            with self.subTest(plan=plan), TemporaryDirectory() as root:
                held = pro_only(Path(root))
                self.require_refusal(held, fixtures.request(held, "unavailable-plan", plan=plan), "unknown_session_plan")
                self.assert_no_effects(held)
                self.assertIsNone(fixtures.bound(held))

    def test_unknown_plan_for_bound_customer_also_makes_no_provider_call(self):
        with TemporaryDirectory() as root:
            held = pro_only(Path(root), bind_customers=True)
            self.require_refusal(held, fixtures.request(held, "unknown-bound", plan="max"), "unknown_session_plan")
            self.assert_no_effects(held)
            self.assertEqual(fixtures.bound(held)["provider_customer_id"], "cus_alpha")

    def test_valid_pro_still_creates_one_customer_and_exact_checkout(self):
        with TemporaryDirectory() as root:
            held = pro_only(Path(root))
            result = held.adapter.create(fixtures.principal(held), fixtures.request(held, "valid-pro", plan="pro"))
            self.assertEqual(result["status"], "created")
            self.assertEqual(len(fixtures.creations(held)), 1)
            self.assertEqual(len(fixtures.sessions_created(held)), 1)
            posted = dict(fixtures.sessions_created(held)[0].parameters)
            self.assertEqual(posted["line_items[0][price]"], "price_basic")
            self.assertEqual(posted["line_items[0][quantity]"], "1")
            self.assertEqual(posted["customer"], fixtures.bound(held)["provider_customer_id"])

    def test_bound_portal_keeps_its_configuration_without_creating_a_customer(self):
        with TemporaryDirectory() as root:
            held = pro_only(Path(root), bind_customers=True)
            result = held.adapter.create(fixtures.principal(held),
                fixtures.request(held, "portal-bound", operation=PORTAL_OPERATION))
            self.assertEqual(result["status"], "created")
            self.assertEqual(fixtures.creations(held), [])
            posts = [call for call in held.provider.calls if call.method == POST_METHOD]
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0].path, PORTAL_PATH)
            self.assertEqual(dict(posts[0].parameters), {"customer": "cus_alpha", "configuration": "bpc_fixture",
                                                       "return_url": held.policy.portal_return_url})

    def test_unbound_portal_refuses_without_creating_a_customer(self):
        with TemporaryDirectory() as root:
            held = pro_only(Path(root))
            self.require_refusal(held, fixtures.request(held, "portal-unbound", operation=PORTAL_OPERATION),
                                 "billing_customer_not_bound")
            self.assert_no_effects(held)

    def test_stale_policy_and_missing_effect_authority_still_refuse_first(self):
        with TemporaryDirectory() as root:
            held = pro_only(Path(root))
            stale = BillingSessionRequest(CHECKOUT_OPERATION, "stale", "0" * 64, "max")
            self.require_refusal(held, stale, "session_selection_changed")
            self.assert_no_effects(held)
            held.adapter = StripeSessionAdapter(held.runtime, replace(held.policy, allow_network=False),
                                                held.secret, transport=held.provider)
            self.require_refusal(held, fixtures.request(held, "no-authority", plan="max"),
                                 "session_network_authority_required")
            self.assert_no_effects(held)


if __name__ == "__main__":
    main()
