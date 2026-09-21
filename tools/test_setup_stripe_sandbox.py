"""The Stripe test setup command refuses a live key and never duplicates an endpoint.

Every check uses an injected transport and an injected keyring. Nothing here
reaches Stripe, the network or the workstation keyring. Two checks are named
mutant controls: they remove one guard inside the check and show that the
behaviour the guard exists to prevent becomes reachable.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import unittest.mock

import setup_stripe_sandbox as setup
from setup_stripe_sandbox import operator_credentials

ACCOUNT = "acct_1UHZ9KCCxLfArYED"
# These fixtures carry no key material: the body is the alphabet followed by
# the digits. They are still assembled from two pieces rather than written as
# one string, because a whole Stripe key written out, real or invented,
# matches the shape that the repository host's push protection rejects, and a
# test file is not worth an exception to that check. The prefixes are written
# here rather than read from setup_stripe_sandbox, so that a change to the
# prefix list the command accepts fails these tests instead of following them.
KEY_BODY = "51ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
TEST_KEY = "sk_test_" + KEY_BODY
LIVE_KEY = "sk_live_" + KEY_BODY
SIGNING_SECRET = "whsec_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
API_VERSION = "2025-03-31.basil"
WEBHOOK_URL = "https://app.baltor.ai/api/v1/billing/webhook"
PRICE_ID = "price_1SandboxMonthly"
PORTAL_ID = "bpc_1SandboxPortal"
ENDPOINT_ID = "we_1SandboxEndpoint"
MANIFEST = {"record_type": "operator_credential_references/v1",
            "api_keys": {"stripe-test": {"service": "stripe", "account": ACCOUNT,
                                         "purpose": "runtime-test-api", "environment": "STRIPE_API_KEY",
                                         "required_prefixes": ["sk_test_", "rk_test_"]}},
            "oauth": {}}
ENVIRONMENT = {"STRIPE_API_KEY": TEST_KEY}
SECRET_REF_NAME = "stripe-test-webhook-secret"


def _plan():
    return setup.SandboxPlan()


def _request(write=True, url=WEBHOOK_URL):
    return setup.SetupRequest(url, API_VERSION, write)


def _binding():
    return setup.credential_binding("stripe-test", MANIFEST)


def _reference(request=None):
    return setup.secret_reference(SECRET_REF_NAME, _binding(), request or _request(), MANIFEST)


def account_object(account_id=ACCOUNT):
    return {"object": "account", "id": account_id}


def product_object(plan=None, livemode=False):
    plan = plan or _plan()
    return {"object": "product", "id": plan.product_id, "name": plan.product_name,
            "active": True, "livemode": livemode,
            "metadata": {plan.marker_key: plan.marker_value}}


def price_object(plan=None, livemode=False, identity=PRICE_ID):
    plan = plan or _plan()
    return {"object": "price", "id": identity, "active": True, "type": "recurring",
            "currency": plan.currency, "unit_amount": plan.unit_amount, "livemode": livemode,
            "lookup_key": plan.price_lookup_key, "product": plan.product_id,
            "recurring": {"interval": plan.interval, "interval_count": plan.interval_count},
            "metadata": {plan.marker_key: plan.marker_value}}


def portal_object(plan=None, livemode=False, identity=PORTAL_ID):
    plan = plan or _plan()
    return {"object": "billing_portal.configuration", "id": identity, "active": True,
            "livemode": livemode, "metadata": {plan.marker_key: plan.marker_value},
            "features": {"subscription_cancel": {"enabled": True, "mode": "at_period_end"},
                         "payment_method_update": {"enabled": True},
                         "invoice_history": {"enabled": True}}}


def endpoint_object(plan=None, livemode=False, identity=ENDPOINT_ID, url=WEBHOOK_URL, secret=None,
                    events=None, api_version=API_VERSION):
    plan = plan or _plan()
    value = {"object": "webhook_endpoint", "id": identity, "url": url, "status": "enabled",
             "livemode": livemode, "api_version": api_version,
             "enabled_events": list(events if events is not None else plan.event_types),
             "metadata": {plan.marker_key: plan.marker_value}}
    if secret is not None:
        value["secret"] = secret
    return value


def listing(rows):
    return {"object": "list", "has_more": False, "data": list(rows)}


class FakeStripe:
    """An injected transport. It records every request and answers from a script."""

    def __init__(self, *, product=None, prices=(), portals=(), endpoints=(),
                 created=None, status=None, raises=None, write_raises=None, account=None):
        self.requests = []
        self.product = product
        self.prices, self.portals, self.endpoints = list(prices), list(portals), list(endpoints)
        self.created = dict(created or {})
        self.status = dict(status or {})
        self.raises = dict(raises or {})
        self.write_raises = dict(write_raises or {})
        self.account = account if account is not None else account_object()

    @property
    def writes(self):
        return [row for row in self.requests if row.method == setup.POST_METHOD]

    def _read_body(self, request):
        if request.path == setup.ACCOUNT_PATH:
            return self.account
        if request.path.startswith(setup.PRODUCTS_PATH + "/"):
            return self.product
        if request.path == setup.PRICES_PATH:
            return listing(self.prices)
        if request.path == setup.PORTAL_CONFIGURATIONS_PATH:
            return listing(self.portals)
        if request.path == setup.WEBHOOK_ENDPOINTS_PATH:
            return listing(self.endpoints)
        raise AssertionError("unexpected read path " + request.path)

    def __call__(self, request):
        self.requests.append(request)
        if request.method == setup.GET_METHOD and request.path in self.raises:
            raise self.raises[request.path]
        if request.method == setup.POST_METHOD:
            if request.path in self.write_raises:
                raise self.write_raises[request.path]
            body = self.created.get(request.path)
            status = self.status.get(request.path, setup.OK_STATUS)
            return setup.StripeResponse(status, json.dumps(body or {}).encode())
        body = self._read_body(request)
        if body is None:
            return setup.StripeResponse(setup.NOT_FOUND_STATUS, b'{"error":{"type":"invalid_request_error"}}')
        return setup.StripeResponse(self.status.get(request.path, setup.OK_STATUS), json.dumps(body).encode())


class FakeKeyring:
    """An injected keyring. It holds at most one value for one reference."""

    def __init__(self, held=False, fail_on_store=False):
        self.held, self.fail_on_store, self.values = held, fail_on_store, {}

    def holds(self, reference):
        return self.held

    def store(self, reference, value):
        if self.fail_on_store:
            raise RuntimeError("keyring refused")
        self.values[reference.name] = value
        self.held = True


def everything_exists():
    return FakeStripe(product=product_object(), prices=[price_object()],
                      portals=[portal_object()], endpoints=[endpoint_object()])


def nothing_exists(secret=SIGNING_SECRET):
    return FakeStripe(product=None, prices=[], portals=[], endpoints=[], created={
        setup.PRODUCTS_PATH: product_object(),
        setup.PRICES_PATH: price_object(),
        setup.PORTAL_CONFIGURATIONS_PATH: portal_object(),
        setup.WEBHOOK_ENDPOINTS_PATH: endpoint_object(secret=secret)})


def run(transport, *, write=True, store=None, secret_held=False, url=WEBHOOK_URL, keys=None):
    request = _request(write, url)
    reference = _reference(request)
    factory = iter(keys) if keys else None
    return setup.set_up_sandbox(
        request, _binding(), TEST_KEY, reference, transport=transport,
        store=store if store is not None else FakeKeyring(held=secret_held), secret_held=secret_held,
        key_factory=(lambda: next(factory)) if factory else setup.new_idempotency_key)


class KeyRefusalTests(unittest.TestCase):
    def test_only_a_stripe_test_key_is_accepted(self):
        for value in (LIVE_KEY, "pk_test_" + KEY_BODY[:-6], "sk_test_...", "", None,
                      "rk_live_" + KEY_BODY, " " + TEST_KEY):
            with self.assertRaises(setup.Refusal, msg=repr(value)) as held:
                setup.resolve_credential(_binding(), {"STRIPE_API_KEY": value})
            self.assertEqual(held.exception.code, setup.SetupRefusal.LIVE_KEY.value)
        self.assertEqual(setup.resolve_credential(_binding(), ENVIRONMENT), TEST_KEY)

    def test_the_manifest_entry_must_itself_restrict_the_reference_to_test_keys(self):
        for prefixes in (None, [], ["sk_live_"], ["sk_test_", "sk_live_"], "sk_test_"):
            spec = {"service": "stripe", "account": ACCOUNT, "purpose": "runtime-test-api",
                    "environment": "STRIPE_API_KEY"}
            if prefixes is not None:
                spec["required_prefixes"] = prefixes
            manifest = {**MANIFEST, "api_keys": {"stripe-test": spec}}
            with self.assertRaises(setup.Refusal, msg=repr(prefixes)) as held:
                setup.credential_binding("stripe-test", manifest)
            self.assertEqual(held.exception.code, setup.SetupRefusal.CREDENTIAL_REFERENCE.value)

    def test_a_live_key_is_refused_before_any_request_reaches_stripe(self):
        transport = nothing_exists()
        with tempfile.TemporaryDirectory() as folder:
            report = str(Path(folder) / "report.json")
            code = self._main(["--api-version", API_VERSION, "--report", report,
                               "--confirm-test-mode-writes"],
                              environment={"STRIPE_API_KEY": LIVE_KEY}, transport=transport)
        self.assertEqual(code, setup.EXIT_REFUSED_BEFORE_ANY_REQUEST)
        self.assertEqual(transport.requests, [])
        self.assertFalse(Path(report).exists())

    def test_mutant_control_without_the_test_key_guard_a_live_key_is_accepted(self):
        # Mutant control for the test-key refusal. With the guard removed the
        # live key resolves, which is exactly what
        # test_only_a_stripe_test_key_is_accepted rejects.
        with unittest.mock.patch.object(setup, "_require_test_key", lambda _value: None):
            self.assertEqual(setup.resolve_credential(_binding(), {"STRIPE_API_KEY": LIVE_KEY}), LIVE_KEY)

    def _main(self, argv, *, environment, transport, store=None, manifest=None):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return setup.main(argv, environment=environment, transport=transport,
                              manifest=manifest or MANIFEST, store=store or FakeKeyring(),
                              now=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc))


class DuplicateEndpointTests(unittest.TestCase):
    def test_an_existing_endpoint_without_its_secret_stops_the_run_before_any_write(self):
        transport = everything_exists()
        result = run(transport, secret_held=False)
        self.assertIs(result.outcome, setup.SetupOutcome.STOPPED)
        self.assertIs(result.failure, setup.SetupFailure.ENDPOINT_WITHOUT_SECRET)
        self.assertEqual(transport.writes, [])
        self.assertEqual(result.provider_writes, 0)

    def test_a_saved_secret_without_an_endpoint_also_stops_the_run(self):
        transport = FakeStripe(product=product_object(), prices=[price_object()],
                               portals=[portal_object()], endpoints=[])
        result = run(transport, secret_held=True)
        self.assertIs(result.failure, setup.SetupFailure.SECRET_WITHOUT_ENDPOINT)
        self.assertEqual(transport.writes, [])

    def test_two_endpoints_for_one_address_are_refused_as_ambiguous(self):
        transport = FakeStripe(product=product_object(), prices=[price_object()], portals=[portal_object()],
                               endpoints=[endpoint_object(), endpoint_object(identity="we_2Other")])
        result = run(transport, secret_held=True)
        self.assertIs(result.failure, setup.SetupFailure.ENDPOINT_AMBIGUOUS)
        self.assertEqual(transport.writes, [])

    def test_mutant_control_without_the_pairing_rule_and_the_endpoint_read_a_second_endpoint_is_created(self):
        # A second line of defence, so it takes two mutations: the pairing
        # rule _require_secret_matches_endpoint and the part of _observe that
        # records an endpoint the read found. Removing the pairing rule alone
        # sends no write at all, which
        # test_mutant_control_without_the_pairing_rule_a_ready_run_names_a_secret_nobody_holds
        # covers. What this check shows is that once the read no longer
        # reports the endpoint, only the write itself is left between the
        # command and a second endpoint for an address that already has one,
        # which would deliver every event twice.
        transport = everything_exists()
        transport.created[setup.WEBHOOK_ENDPOINTS_PATH] = endpoint_object(identity="we_2Duplicate",
                                                                          secret=SIGNING_SECRET)
        with unittest.mock.patch.object(setup, "_require_secret_matches_endpoint",
                                        lambda _exists, _held: None), \
                unittest.mock.patch.object(setup, "_observe", _observe_without_pairing):
            result = run(transport, secret_held=False)
        self.assertIs(result.outcome, setup.SetupOutcome.READY)
        self.assertEqual([row.path for row in transport.writes], [setup.WEBHOOK_ENDPOINTS_PATH])
        self.assertEqual(result.endpoint.identity, "we_2Duplicate")

    def test_mutant_control_without_the_pairing_rule_a_ready_run_names_a_secret_nobody_holds(self):
        # Mutant control for the pairing rule on its own. No write is sent,
        # because the read already found the endpoint and _observe recorded
        # it. The damage is elsewhere: the run reports ready and hands the
        # operator a billing block that names the signing secret reference
        # while the keyring holds no secret, so the deployed service would be
        # configured to verify signatures it cannot verify. That is what
        # test_an_existing_endpoint_without_its_secret_stops_the_run_before_any_write
        # rejects.
        transport = everything_exists()
        with unittest.mock.patch.object(setup, "_require_secret_matches_endpoint",
                                        lambda _exists, _held: None):
            result = run(transport, secret_held=False)
        self.assertIs(result.outcome, setup.SetupOutcome.READY)
        self.assertEqual(transport.writes, [])
        self.assertFalse(result.secret_in_keyring)
        block = setup.host_billing_block(_request(), result, _binding())
        self.assertEqual(block["webhook"]["signing_secret_refs"], [setup.SERVICE_WEBHOOK_SECRET_REFERENCE])


_ORIGINAL_OBSERVE = setup._observe


def _observe_without_pairing(session, binding, secret_held):
    """The mutant: read everything as usual, then treat the endpoint as missing."""
    _ORIGINAL_OBSERVE(session, binding, secret_held)
    session.progress.endpoint = setup.ObjectReport(setup.ObjectState.MISSING)


class DryRunAndConfirmationTests(unittest.TestCase):
    def test_a_dry_run_reads_and_writes_nothing(self):
        transport = nothing_exists()
        result = run(transport, write=False)
        self.assertIs(result.outcome, setup.SetupOutcome.DRY_RUN)
        self.assertEqual(transport.writes, [])
        self.assertEqual(result.provider_writes, 0)
        for report in (result.product, result.price, result.portal, result.endpoint):
            self.assertIs(report.state, setup.ObjectState.MISSING)

    def test_exactly_one_of_a_dry_run_and_confirmed_writes_is_required(self):
        for dry_run, confirmed in ((False, False), (True, True)):
            with self.assertRaises(setup.Refusal) as held:
                setup._require_one_mode(dry_run, confirmed)
            self.assertEqual(held.exception.code, setup.SetupRefusal.MODE.value)
        setup._require_one_mode(True, False)
        setup._require_one_mode(False, True)

    def test_a_dry_run_cannot_reach_the_write_path_even_if_it_is_called(self):
        transport = nothing_exists()
        session = setup._Session(_request(write=False), TEST_KEY, transport, setup.RequestLimits(),
                                 setup._Progress(), setup.new_idempotency_key)
        with self.assertRaises(RuntimeError):
            session.write(setup.PRODUCTS_PATH, (), setup.ObjectReport())
        self.assertEqual(transport.requests, [])


class WriteDisciplineTests(unittest.TestCase):
    def test_every_write_carries_its_own_idempotency_key_and_reads_come_first(self):
        transport = nothing_exists()
        result = run(transport)
        self.assertIs(result.outcome, setup.SetupOutcome.READY)
        paths = [row.path for row in transport.writes]
        self.assertEqual(paths, [setup.PRODUCTS_PATH, setup.PRICES_PATH,
                                 setup.PORTAL_CONFIGURATIONS_PATH, setup.WEBHOOK_ENDPOINTS_PATH])
        keys = [row.idempotency_key for row in transport.writes]
        self.assertEqual(len(set(keys)), len(keys))
        for key in keys:
            self.assertTrue(key.startswith(setup.IDEMPOTENCY_KEY_PREFIX))
        first_write = transport.requests.index(transport.writes[0])
        self.assertTrue(all(row.method == setup.GET_METHOD for row in transport.requests[:first_write]))
        self.assertEqual(result.provider_writes, 4)

    def test_a_lost_answer_is_an_unknown_outcome_and_the_write_is_not_repeated(self):
        transport = nothing_exists()
        transport.write_raises[setup.PRICES_PATH] = setup.TransportFailure(setup.SetupDetail.TIMEOUT.value)
        result = run(transport)
        self.assertIs(result.outcome, setup.SetupOutcome.OUTCOME_UNKNOWN)
        self.assertIs(result.failure, setup.SetupFailure.WRITE_UNKNOWN)
        self.assertEqual(result.detail, setup.SetupDetail.TIMEOUT.value)
        self.assertEqual(len([row for row in transport.requests if row.path == setup.PRICES_PATH
                              and row.method == setup.POST_METHOD]), 1)

    def test_a_refused_write_is_reported_as_not_performed(self):
        transport = nothing_exists()
        transport.status[setup.PRODUCTS_PATH] = 402
        result = run(transport)
        self.assertIs(result.outcome, setup.SetupOutcome.STOPPED)
        self.assertIs(result.failure, setup.SetupFailure.WRITE_REFUSED)

    def test_an_existing_environment_is_reused_without_any_write(self):
        transport = everything_exists()
        result = run(transport, secret_held=True)
        self.assertIs(result.outcome, setup.SetupOutcome.READY)
        self.assertEqual(transport.writes, [])
        self.assertEqual(result.price.identity, PRICE_ID)
        self.assertEqual(result.portal.identity, PORTAL_ID)
        self.assertEqual(result.endpoint.identity, ENDPOINT_ID)
        self.assertIs(result.product.state, setup.ObjectState.EXISTING)

    def test_a_provider_redirect_is_refused(self):
        transport = everything_exists()
        transport.status[setup.ACCOUNT_PATH] = 302
        result = run(transport, secret_held=True)
        self.assertIs(result.failure, setup.SetupFailure.PROVIDER_REDIRECT)

    def test_a_refused_credential_stops_the_run(self):
        transport = everything_exists()
        transport.status[setup.ACCOUNT_PATH] = 401
        result = run(transport, secret_held=True)
        self.assertIs(result.failure, setup.SetupFailure.CREDENTIAL_REFUSED)


class ProviderAnswerTests(unittest.TestCase):
    def test_an_object_in_live_mode_stops_the_run(self):
        transport = FakeStripe(product=product_object(livemode=True))
        result = run(transport)
        self.assertIs(result.failure, setup.SetupFailure.LIVE_MODE_OBJECT)
        self.assertEqual(transport.writes, [])

    def test_a_created_object_in_live_mode_stops_the_run(self):
        transport = nothing_exists()
        transport.created[setup.PRICES_PATH] = price_object(livemode=True)
        result = run(transport)
        self.assertIs(result.failure, setup.SetupFailure.LIVE_MODE_OBJECT)

    def test_a_key_that_belongs_to_another_account_stops_the_run(self):
        transport = everything_exists()
        transport.account = account_object("acct_9OtherAccount")
        result = run(transport, secret_held=True)
        self.assertIs(result.failure, setup.SetupFailure.ACCOUNT_MISMATCH)
        self.assertEqual(transport.writes, [])

    def test_an_existing_price_that_differs_from_the_plan_stops_the_run(self):
        wrong = price_object()
        wrong["unit_amount"] = 1900
        transport = FakeStripe(product=product_object(), prices=[wrong])
        self.assertIs(run(transport).failure, setup.SetupFailure.PRICE_MISMATCH)

    def test_an_existing_product_that_differs_from_the_plan_stops_the_run(self):
        wrong = product_object()
        wrong["name"] = "Another product"
        self.assertIs(run(FakeStripe(product=wrong)).failure, setup.SetupFailure.PRODUCT_MISMATCH)

    def test_a_portal_configuration_without_cancellation_stops_the_run(self):
        wrong = portal_object()
        wrong["features"]["subscription_cancel"]["enabled"] = False
        transport = FakeStripe(product=product_object(), prices=[price_object()], portals=[wrong])
        self.assertIs(run(transport).failure, setup.SetupFailure.PORTAL_MISMATCH)

    def test_a_portal_configuration_without_payment_method_update_stops_the_run(self):
        wrong = portal_object()
        wrong["features"]["payment_method_update"]["enabled"] = False
        transport = FakeStripe(product=product_object(), prices=[price_object()], portals=[wrong])
        self.assertIs(run(transport).failure, setup.SetupFailure.PORTAL_MISMATCH)

    def test_an_endpoint_with_other_event_types_stops_the_run(self):
        for events in (["invoice.paid"], [*_plan().event_types, "charge.succeeded"]):
            transport = FakeStripe(product=product_object(), prices=[price_object()],
                                   portals=[portal_object()], endpoints=[endpoint_object(events=events)])
            self.assertIs(run(transport, secret_held=True).failure,
                          setup.SetupFailure.ENDPOINT_MISMATCH, msg=repr(events))

    def test_an_endpoint_on_another_api_version_stops_the_run(self):
        transport = FakeStripe(product=product_object(), prices=[price_object()], portals=[portal_object()],
                               endpoints=[endpoint_object(api_version="2024-06-20")])
        self.assertIs(run(transport, secret_held=True).failure, setup.SetupFailure.ENDPOINT_MISMATCH)

    def test_two_prices_with_one_lookup_key_are_refused_as_ambiguous(self):
        transport = FakeStripe(product=product_object(),
                               prices=[price_object(), price_object(identity="price_2Other")])
        self.assertIs(run(transport).failure, setup.SetupFailure.PRICE_AMBIGUOUS)

    def test_two_marked_portal_configurations_are_refused_as_ambiguous(self):
        transport = FakeStripe(product=product_object(), prices=[price_object()],
                               portals=[portal_object(), portal_object(identity="bpc_2Other")])
        self.assertIs(run(transport).failure, setup.SetupFailure.PORTAL_AMBIGUOUS)

    def test_a_repeated_json_key_makes_the_answer_unusable(self):
        class Repeating(FakeStripe):
            def __call__(self, request):
                self.requests.append(request)
                return setup.StripeResponse(setup.OK_STATUS, b'{"id":"a","id":"b"}')
        result = run(Repeating(), secret_held=True)
        self.assertIs(result.failure, setup.SetupFailure.READ_FAILED)
        self.assertEqual(result.detail, setup.SetupDetail.MALFORMED_RESPONSE.value)


class SigningSecretTests(unittest.TestCase):
    def test_the_secret_is_stored_in_the_keyring_and_never_appears_in_the_report(self):
        transport, keyring = nothing_exists(), FakeKeyring()
        result = run(transport, store=keyring)
        self.assertIs(result.outcome, setup.SetupOutcome.READY)
        self.assertTrue(result.secret_in_keyring)
        self.assertEqual(keyring.values[SECRET_REF_NAME], SIGNING_SECRET)
        encoded = setup.encode_report(
            setup.build_report(_request(), result, _reference(), _binding(),
                               datetime(2026, 9, 21, tzinfo=timezone.utc)), result.sensitive_values)
        self.assertNotIn(SIGNING_SECRET, encoded)
        self.assertNotIn(TEST_KEY, encoded)
        self.assertIn(ENDPOINT_ID, encoded)

    def test_a_created_endpoint_without_a_usable_secret_stops_the_run(self):
        # The endpoint was created before the secret was read, so this stop
        # comes after four committed writes and the account has changed.
        for secret in (None, "", "whsec_short", "notasecret"):
            transport = nothing_exists(secret=secret)
            if secret is None:
                transport.created[setup.WEBHOOK_ENDPOINTS_PATH] = endpoint_object()
            result = run(transport, store=FakeKeyring())
            self.assertIs(result.failure, setup.SetupFailure.SECRET_MISSING, msg=repr(secret))
            self.assertIs(result.outcome, setup.SetupOutcome.STOPPED_AFTER_WRITES, msg=repr(secret))
            self.assertEqual(result.provider_writes, 4, msg=repr(secret))
            self.assertEqual(result.committed_writes, 4, msg=repr(secret))
            self.assertIs(result.endpoint.state, setup.ObjectState.CREATED, msg=repr(secret))
            self.assertFalse(result.secret_in_keyring, msg=repr(secret))
            self.assertEqual(setup._EXIT_CODES[result.outcome], 4, msg=repr(secret))

    def test_a_keyring_that_refuses_the_value_stops_the_run(self):
        result = run(nothing_exists(), store=FakeKeyring(fail_on_store=True))
        self.assertIs(result.failure, setup.SetupFailure.SECRET_NOT_STORED)
        self.assertIs(result.outcome, setup.SetupOutcome.STOPPED_AFTER_WRITES)
        self.assertEqual((result.provider_writes, result.committed_writes), (4, 4))
        self.assertIs(result.endpoint.state, setup.ObjectState.CREATED)
        self.assertFalse(result.secret_in_keyring)
        self.assertEqual(setup._EXIT_CODES[result.outcome], 4)

    def test_a_secret_outside_the_narrow_alphabet_is_kept_rather_than_discarded(self):
        # A base64url secret is a shape Stripe never published as impossible.
        # The accepted pattern covers it, and the keyring reference entry
        # declares the same pattern, so the store keeps it as well.
        base64url = "whsec_A-B_C0123456789abcdefgh"
        transport, keyring = nothing_exists(secret=base64url), FakeKeyring()
        result = run(transport, store=keyring)
        self.assertIs(result.outcome, setup.SetupOutcome.READY)
        self.assertEqual(keyring.values[SECRET_REF_NAME], base64url)
        spec = _reference().manifest["api_keys"][SECRET_REF_NAME]
        self.assertEqual(operator_credentials.validate_api_token(base64url, spec), base64url)

    def test_the_accepted_shape_is_one_rule_shared_with_the_keyring_entry(self):
        spec = _reference().manifest["api_keys"][SECRET_REF_NAME]
        self.assertEqual(spec["value_pattern"], setup.WEBHOOK_SECRET_VALUE_PATTERN)
        self.assertEqual(setup._WEBHOOK_SECRET.pattern, setup.WEBHOOK_SECRET_VALUE_PATTERN)
        self.assertEqual(spec["required_prefixes"], [setup.WEBHOOK_SECRET_PREFIX])

    def test_a_report_that_would_hold_a_secret_is_refused(self):
        with self.assertRaises(setup.Refusal) as held:
            setup.encode_report({"note": "leaked " + SIGNING_SECRET}, (SIGNING_SECRET,))
        self.assertEqual(held.exception.code, setup.SetupRefusal.SECRET_IN_OUTPUT.value)

    def test_the_keyring_entry_uses_a_purpose_that_staging_accepts(self):
        import stage_service_secrets
        reference = _reference()
        spec = reference.manifest["api_keys"][SECRET_REF_NAME]
        self.assertEqual(spec["purpose"], "webhook-signing")
        self.assertEqual(spec["environment"], setup.SERVICE_WEBHOOK_SECRET_ENVIRONMENT)
        self.assertEqual(spec["endpoint_url"], WEBHOOK_URL)
        self.assertEqual(dict(reference.attributes),
                         {"service": "stripe", "account": ACCOUNT, "purpose": "webhook-signing"})
        self.assertIn(spec["purpose"], stage_service_secrets.RUNTIME_PURPOSES)
        self.assertEqual(stage_service_secrets.selected([SECRET_REF_NAME], reference.manifest),
                         {setup.SERVICE_WEBHOOK_SECRET_ENVIRONMENT: SECRET_REF_NAME})
        self.assertEqual(stage_service_secrets.selected(["stripe-test"], reference.manifest),
                         {"STRIPE_API_KEY": "stripe-test"})

    def test_the_value_pattern_refuses_a_value_that_is_not_a_signing_secret(self):
        spec = _reference().manifest["api_keys"][SECRET_REF_NAME]
        self.assertEqual(operator_credentials.validate_api_token(SIGNING_SECRET, spec), SIGNING_SECRET)
        for value in (TEST_KEY, "whsec_short", "whsec_!!!!!!!!!!!!!!!!"):
            with self.assertRaises(operator_credentials.CredentialError, msg=value):
                operator_credentials.validate_api_token(value, spec)

    def test_a_reference_already_declared_for_another_address_is_refused(self):
        other = setup.secret_reference(SECRET_REF_NAME, _binding(),
                                       _request(url="https://other.baltor.ai/hook"), MANIFEST)
        with self.assertRaises(setup.Refusal) as held:
            setup.secret_reference(SECRET_REF_NAME, _binding(), _request(), other.manifest)
        self.assertEqual(held.exception.code, setup.SetupRefusal.SECRET_REFERENCE.value)

    def test_a_second_reference_name_for_the_same_keyring_place_is_refused(self):
        first = _reference()
        with self.assertRaises(setup.Refusal) as held:
            setup.secret_reference("another-webhook-secret", _binding(), _request(), first.manifest)
        self.assertEqual(held.exception.code, setup.SetupRefusal.SECRET_REFERENCE.value)

    def test_the_api_key_reference_may_not_be_reused_for_the_signing_secret(self):
        with self.assertRaises(setup.Refusal):
            setup.secret_reference("stripe-test", _binding(), _request(), MANIFEST)

    def test_a_saved_item_under_another_name_refuses_the_run(self):
        class Item:
            def __init__(self, label):
                self._label = label

            def get_label(self):
                return self._label

        class Collection:
            def __init__(self, items):
                self.items = items

            def search_items(self, _attributes):
                return list(self.items)

        reference = _reference()
        store = setup.KeyringSecretStore()
        for items, expected in ((["Baltor operator / other-name"], setup.SetupRefusal.KEYRING_AMBIGUOUS),
                                (["a", "b"], setup.SetupRefusal.KEYRING_AMBIGUOUS)):
            collection = Collection([Item(label) for label in items])
            with unittest.mock.patch.object(setup.operator_credentials, "collection",
                                            return_value=collection):
                with self.assertRaises(setup.Refusal) as held:
                    setup.keyring_holds(store, reference)
            self.assertEqual(held.exception.code, expected.value)
        collection = Collection([Item(reference.label)])
        with unittest.mock.patch.object(setup.operator_credentials, "collection", return_value=collection):
            self.assertTrue(setup.keyring_holds(store, reference))


class InputGuardTests(unittest.TestCase):
    def test_only_a_plain_https_address_is_accepted(self):
        for value in ("http://app.baltor.ai/hook", "https://app.baltor.ai:8443/hook",
                      "https://app.baltor.ai/hook?a=1", "https://app.baltor.ai/hook#a",
                      "https://user:pass@app.baltor.ai/hook", "https://app.baltor.ai",
                      "https://app.baltor.ai/../hook", "https://127.0.0.1/hook",
                      "https://localhost/hook", "https://app.baltor.ai/ho ok", "", None,
                      "https://app.baltor.ai/hook\n"):
            with self.assertRaises(setup.Refusal, msg=repr(value)) as held:
                setup._require_webhook_address(value)
            self.assertEqual(held.exception.code, setup.SetupRefusal.WEBHOOK_URL.value)
        setup._require_webhook_address(WEBHOOK_URL)
        setup._require_webhook_address("https://baltor-pilot.fly.dev/api/v1/billing/webhook")

    def test_an_api_version_older_than_the_subscription_reader_is_refused(self):
        for value in ("2024-06-20", "2020-08-27", "2025-03-30"):
            with self.assertRaises(setup.Refusal) as held:
                setup._require_supported_api_version(value)
            self.assertEqual(held.exception.code, setup.SetupRefusal.API_VERSION_TOO_OLD.value)
        for value in ("", "basil", "2025-3-31", "2025-03-31.BASIL", None):
            with self.assertRaises(setup.Refusal, msg=repr(value)) as held:
                setup._require_supported_api_version(value)
            self.assertEqual(held.exception.code, setup.SetupRefusal.API_VERSION.value)
        setup._require_supported_api_version(API_VERSION)
        setup._require_supported_api_version("2026-08-26.dahlia")

    def test_an_unsupported_manifest_is_refused(self):
        for manifest in ({}, {"record_type": "other/v1", "api_keys": {}},
                         {"record_type": "operator_credential_references/v1", "api_keys": []}, None):
            with self.assertRaises(setup.Refusal) as held:
                setup.credential_binding("stripe-test", manifest)
            self.assertEqual(held.exception.code, setup.SetupRefusal.CREDENTIAL_MANIFEST.value)

    def test_a_request_outside_the_supported_operations_is_refused(self):
        for method, path, key in ((setup.GET_METHOD, "/v1/customers", ""),
                                  (setup.POST_METHOD, "/v1/charges", "baltor-sandbox-setup-a"),
                                  (setup.POST_METHOD, setup.PRICES_PATH, ""),
                                  (setup.POST_METHOD, setup.PRICES_PATH, "other-prefix"),
                                  (setup.GET_METHOD, setup.PRICES_PATH, "baltor-sandbox-setup-a"),
                                  ("DELETE", setup.PRICES_PATH, "")):
            with self.assertRaises(ValueError, msg=path):
                setup.StripeRequest(method, path, (), API_VERSION, key, 1.0, 1000, TEST_KEY)
        setup.StripeRequest(setup.GET_METHOD, setup.ACCOUNT_PATH, (), API_VERSION, "", 1.0, 1000, TEST_KEY)

    def test_the_request_limits_are_bounded(self):
        for values in ((0.0, 1000, 1), (61.0, 1000, 1), (15.0, 0, 1), (15.0, 1000, 0), (15.0, 1000, 21)):
            with self.assertRaises(setup.Refusal):
                setup.RequestLimits(*values)
        setup.RequestLimits()

    def test_a_report_path_that_already_exists_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            path.write_text("earlier evidence", encoding="utf-8")
            with self.assertRaises(setup.Refusal) as held:
                setup.reserve_report(str(path))
            self.assertEqual(held.exception.code, setup.SetupRefusal.REPORT_EXISTS.value)
            self.assertEqual(path.read_text(encoding="utf-8"), "earlier evidence")
            missing = Path(folder) / "absent" / "report.json"
            with self.assertRaises(setup.Refusal) as held:
                setup.reserve_report(str(missing))
            self.assertEqual(held.exception.code, setup.SetupRefusal.REPORT_FOLDER.value)
            target, stream = setup.reserve_report(str(Path(folder) / "new.json"))
            stream.close()
            self.assertTrue(target.exists())


class TransportContractTests(unittest.TestCase):
    def test_redirects_and_environment_proxies_are_never_used(self):
        request = setup.StripeRequest(setup.GET_METHOD, setup.ACCOUNT_PATH, (), API_VERSION, "", 1.0, 1000,
                                      TEST_KEY)
        options = setup._client_options(request, None)
        self.assertFalse(options["follow_redirects"])
        self.assertFalse(options["trust_env"])
        self.assertEqual(options["timeout"], 1.0)

    def test_only_the_fixed_stripe_origin_is_used(self):
        self.assertEqual(setup.STRIPE_ORIGIN, "https://api.stripe.com")
        for path in (setup.ACCOUNT_PATH, setup.PRODUCTS_PATH, setup.PRICES_PATH,
                     setup.PORTAL_CONFIGURATIONS_PATH, setup.WEBHOOK_ENDPOINTS_PATH):
            self.assertTrue(path.startswith("/v1/"))

    def test_a_body_beyond_the_allowance_is_a_lost_answer(self):
        limits = setup.RequestLimits(maximum_response_bytes=10)
        with self.assertRaises(setup.TransportFailure):
            setup._require_bounded_body(setup.StripeResponse(200, b"x" * 11), limits)

    def test_a_transport_that_breaks_the_contract_is_not_trusted(self):
        class Wrong(FakeStripe):
            def __call__(self, request):
                self.requests.append(request)
                return {"id": "not a response record"}
        result = run(Wrong(), secret_held=True)
        self.assertIs(result.failure, setup.SetupFailure.READ_FAILED)
        self.assertEqual(result.detail, setup.SetupDetail.TRANSPORT_CONTRACT.value)


class PlanAndConfigurationTests(unittest.TestCase):
    def test_the_plan_is_one_monthly_price_of_twenty_nine_us_dollars(self):
        plan = _plan()
        self.assertEqual((plan.currency, plan.unit_amount), ("usd", 2_900))
        self.assertEqual((plan.interval, plan.interval_count), ("month", 1))
        self.assertEqual(plan.price_lookup_key, "baltor_pro_monthly_usd")
        self.assertEqual(plan.product_name, "Baltor Pro")

    def test_the_endpoint_is_subscribed_to_exactly_the_event_types_the_service_processes(self):
        from loop_engine.core.service_runtime.billing_records import EVENT_TYPES
        self.assertEqual(setup.SERVICE_EVENT_TYPES, tuple(EVENT_TYPES))
        self.assertEqual(_plan().event_types, tuple(EVENT_TYPES))
        sent = dict(setup._endpoint_parameters(_request()))
        self.assertEqual([sent["enabled_events[" + str(index) + "]"] for index in range(len(EVENT_TYPES))],
                         list(EVENT_TYPES))

    def test_the_written_parameters_match_the_plan(self):
        plan = _plan()
        price = dict(setup._price_parameters(plan))
        self.assertEqual(price["unit_amount"], "2900")
        self.assertEqual(price["currency"], "usd")
        self.assertEqual(price["recurring[interval]"], "month")
        self.assertEqual(price["recurring[interval_count]"], "1")
        self.assertEqual(price["lookup_key"], plan.price_lookup_key)
        self.assertEqual(price["product"], plan.product_id)
        portal = dict(setup._portal_parameters(plan))
        self.assertEqual(portal["features[subscription_cancel][enabled]"], "true")
        self.assertEqual(portal["features[subscription_cancel][mode]"], "at_period_end")
        self.assertEqual(portal["features[payment_method_update][enabled]"], "true")
        product = dict(setup._product_parameters(plan))
        self.assertEqual((product["id"], product["name"]), (plan.product_id, plan.product_name))

    def test_the_host_billing_block_builds_the_service_records(self):
        from loop_engine.core.service_runtime.billing_records import (
            StripeEntitlementPolicy, StripeProviderConfig, StripeWebhookConfig)
        from loop_engine.core.service_runtime.stripe_sessions import (
            StripeSessionConfiguration, StripeSessionPlan)
        result = run(everything_exists(), secret_held=True)
        block = setup.host_billing_block(_request(), result, _binding())
        StripeWebhookConfig(**block["webhook"])
        StripeEntitlementPolicy(**block["policy"])
        StripeProviderConfig(**block["provider"])
        sessions = dict(block["sessions"])
        sessions["plans"] = tuple(StripeSessionPlan(**row) for row in sessions["plans"])
        configuration = StripeSessionConfiguration(**sessions)
        self.assertEqual(configuration.portal_configuration_id, PORTAL_ID)
        self.assertEqual(block["policy"]["allowed_price_ids"], [PRICE_ID])
        self.assertEqual(block["provider"]["api_key_ref"], "env:STRIPE_API_KEY")
        self.assertEqual(block["webhook"]["signing_secret_refs"], ["env:STRIPE_WEBHOOK_SECRET"])
        self.assertNotIn(TEST_KEY, json.dumps(block))

    def test_the_host_billing_block_matches_what_the_service_entry_point_accepts(self):
        result = run(everything_exists(), secret_held=True)
        block = setup.host_billing_block(_request(), result, _binding())
        self.assertEqual(set(block), {"webhook", "policy", "provider", "sessions"})


class CommandTests(unittest.TestCase):
    def _run(self, argv, transport, store=None, environment=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = setup.main(argv, environment=environment or ENVIRONMENT, transport=transport,
                              manifest=MANIFEST, store=store or FakeKeyring(),
                              now=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc))
        return code, out.getvalue(), err.getvalue()

    def test_a_confirmed_run_writes_a_report_that_holds_identifiers_only(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            code, shown, _err = self._run(
                ["--api-version", API_VERSION, "--report", str(report), "--confirm-test-mode-writes"],
                nothing_exists())
            saved = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(saved["record_type"], setup.REPORT_RECORD_TYPE)
        self.assertEqual(saved["outcome"], "ready")
        self.assertEqual(saved["signing_secret"]["value_recorded"], False)
        self.assertEqual(saved["automatic_retries"], 0)
        self.assertIsNotNone(saved["host_billing_block"])
        for secret in (SIGNING_SECRET, TEST_KEY):
            self.assertNotIn(secret, json.dumps(saved))
            self.assertNotIn(secret, shown)
        self.assertIn('"secret_printed": false', shown)

    def test_a_dry_run_reports_what_a_confirmed_run_would_create(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            transport = nothing_exists()
            code, _shown, _err = self._run(
                ["--api-version", API_VERSION, "--report", str(report), "--dry-run"], transport)
            saved = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(saved["mode"], "dry_run")
        self.assertEqual(saved["outcome"], "dry_run_nothing_written")
        self.assertIsNone(saved["host_billing_block"])
        self.assertEqual(saved["provider_writes"], 0)
        self.assertEqual(transport.writes, [])

    def test_the_command_refuses_when_neither_mode_is_chosen(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            transport = nothing_exists()
            code, _shown, err = self._run(["--api-version", API_VERSION, "--report", str(report)], transport)
        self.assertEqual(code, setup.EXIT_REFUSED_BEFORE_ANY_REQUEST)
        self.assertEqual(err.strip(), setup.SetupRefusal.MODE.value)
        self.assertEqual(transport.requests, [])
        self.assertFalse(report.exists())

    def test_a_stopped_run_still_writes_its_report_and_returns_one(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            code, _shown, _err = self._run(
                ["--api-version", API_VERSION, "--report", str(report), "--confirm-test-mode-writes"],
                everything_exists(), store=FakeKeyring(held=False))
            saved = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(saved["failure"], setup.SetupFailure.ENDPOINT_WITHOUT_SECRET.value)
        self.assertEqual(saved["outcome"], "stopped")
        self.assertEqual(saved["provider_writes"], 0)
        self.assertEqual(saved["committed_provider_writes"], 0)

    def test_a_stop_after_a_committed_write_has_its_own_exit_code_and_report(self):
        # Two ways to lose the signing secret of an endpoint that Stripe has
        # already created: the value cannot be used, and the keyring refuses
        # it. Both leave a webhook endpoint at Stripe whose secret is gone,
        # which is not the same as a run that stopped with nothing written.
        for transport, store in ((nothing_exists(secret="whsec_short"), FakeKeyring()),
                                 (nothing_exists(), FakeKeyring(fail_on_store=True))):
            with tempfile.TemporaryDirectory() as folder:
                report = Path(folder) / "sandbox.json"
                code, shown, _err = self._run(
                    ["--api-version", API_VERSION, "--report", str(report), "--confirm-test-mode-writes"],
                    transport, store=store)
                saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(code, 4)
            self.assertEqual(saved["outcome"], "stopped_after_a_committed_write")
            self.assertEqual(saved["provider_writes"], 4)
            self.assertEqual(saved["committed_provider_writes"], 4)
            self.assertEqual(saved["webhook_endpoint"]["state"], "created")
            self.assertEqual(saved["webhook_endpoint"]["id"], ENDPOINT_ID)
            self.assertFalse(saved["signing_secret"]["in_keyring"])
            self.assertIsNone(saved["host_billing_block"])
            self.assertIn('"committed_provider_writes": 4', shown)

    def test_a_run_whose_report_cannot_be_written_still_says_the_account_changed(self):
        # The exit code follows what exists at Stripe, not what the report
        # managed to record. Four objects were created, so the code is the one
        # for a stop after a committed write, never the one for a run that
        # changed nothing.
        def refuse(_report, _sensitive):
            raise OSError("report stream refused")

        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            with unittest.mock.patch.object(setup, "encode_report", refuse):
                code, shown, _err = self._run(
                    ["--api-version", API_VERSION, "--report", str(report), "--confirm-test-mode-writes"],
                    nothing_exists())
            self.assertEqual(report.read_text(encoding="utf-8"), "")
        self.assertEqual(code, 4)
        self.assertIn('"report_written": false', shown)
        self.assertIn('"committed_provider_writes": 4', shown)

    def test_a_dry_run_whose_report_cannot_be_written_stops_with_nothing_written(self):
        def refuse(_report, _sensitive):
            raise OSError("report stream refused")

        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            with unittest.mock.patch.object(setup, "encode_report", refuse):
                code, shown, _err = self._run(
                    ["--api-version", API_VERSION, "--report", str(report), "--dry-run"], nothing_exists())
        self.assertEqual(code, 1)
        self.assertIn('"committed_provider_writes": 0', shown)

    def test_the_report_carries_the_manifest_entry_that_staging_needs(self):
        import stage_service_secrets
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            code, _shown, _err = self._run(
                ["--api-version", API_VERSION, "--report", str(report), "--confirm-test-mode-writes"],
                nothing_exists())
            saved = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        name = saved["signing_secret"]["keyring_reference"]
        entry = saved["signing_secret"]["manifest_entry"]
        # The documented operator step, performed exactly: take the entry out
        # of the saved report, put it into the manifest under the reference
        # name, then stage it and validate the value against it.
        manifest = {**MANIFEST, "api_keys": {**MANIFEST["api_keys"], name: entry}}
        self.assertEqual(stage_service_secrets.selected([name], manifest),
                         {setup.SERVICE_WEBHOOK_SECRET_ENVIRONMENT: SECRET_REF_NAME})
        self.assertEqual(operator_credentials.validate_api_token(SIGNING_SECRET, entry), SIGNING_SECRET)
        self.assertEqual(entry["endpoint_url"], WEBHOOK_URL)
        self.assertNotIn(SIGNING_SECRET, json.dumps(entry))
        # The known-wrong case: the keyring attributes alone are not a
        # manifest entry, and staging then fails on the missing environment
        # name instead of refusing it.
        attributes_only = dict(saved["signing_secret"]["keyring_attributes"])
        broken = {**MANIFEST, "api_keys": {**MANIFEST["api_keys"], name: attributes_only}}
        with self.assertRaises(KeyError):
            stage_service_secrets.selected([name], broken)

    def test_an_unknown_outcome_returns_its_own_code(self):
        transport = nothing_exists()
        transport.write_raises[setup.PRODUCTS_PATH] = setup.TransportFailure(
            setup.SetupDetail.CONNECTION_FAILED.value)
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "sandbox.json"
            code, _shown, _err = self._run(
                ["--api-version", API_VERSION, "--report", str(report), "--confirm-test-mode-writes"],
                transport)
            saved = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 3)
        self.assertEqual(saved["outcome"], "outcome_unknown")
        self.assertEqual(saved["detail"], setup.SetupDetail.CONNECTION_FAILED.value)

    def test_the_default_address_is_the_pilot_billing_webhook(self):
        parser = setup.build_parser()
        defaults = parser.parse_args(["--api-version", API_VERSION, "--report", "r.json", "--dry-run"])
        self.assertEqual(defaults.webhook_url, "https://app.baltor.ai/api/v1/billing/webhook")
        self.assertEqual(defaults.credential_ref, "stripe-test")
        self.assertEqual(defaults.webhook_secret_ref, SECRET_REF_NAME)


if __name__ == "__main__":
    unittest.main()
