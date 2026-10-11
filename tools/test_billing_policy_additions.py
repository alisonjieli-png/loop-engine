"""An additive price migration preserves existing access without provider effects."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from unittest import TestCase, main, mock

from loop_engine.core.service_runtime import billing_records
from loop_engine.core.service_runtime import billing_policy_checks as fixtures
from loop_engine.core.service_runtime.billing import StripeEventProcessor
from loop_engine.core.service_runtime.billing_records import (
    StripeCustomerSubscriptionSnapshot, StripeEntitlementPolicy, StripeSubscriptionResolver,
    StripeSubscriptionState,
)
from loop_engine.core.service_runtime.http_entrypoint import load_host_billing_context
from loop_engine.core.service_runtime.records import ServiceCommitUnknown, ServiceRuntimeError, digest
from loop_engine.core.service_runtime.runtime import BILLING_POLICY, ENTITLEMENT
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding


INVALID_PRICE_IDENTITIES = (
    None, True, False, 0, 1.0, [], {}, ["price_basic"], {"nested": ["price_basic"]},
    "", "price with spaces", "price/path", "-price", "p" * 129, "price\nnew", "price\x00new", "price_é",
)


class AdditiveBillingPolicyTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="billing-price-addition-")
        self.addCleanup(self.directory.cleanup)
        self.path, self.application = fixtures.configured(Path(self.directory.name))
        self.runtime = self.application.runtime

    def row(self, kind, identity):
        with self.runtime._catalog.store() as store:
            return self.runtime._catalog.read(store, kind, identity)

    def add_price(self):
        fixtures.rewrite(self.path, fixtures.a_new_entitlement_policy)

    def require_refusal(self, code, operation):
        with self.assertRaises(ServiceRuntimeError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def snapshot(self, *, paid=True):
        subscription = StripeSubscriptionState("sub_alpha", "cus_alpha", "active",
            (("price_basic", int(time.time()) + 3600),), paid)
        return StripeCustomerSubscriptionSnapshot(fixtures.ACCOUNT, "cus_alpha", fixtures.API,
            False, (subscription,), "b" * 64)

    def processor(self, resolver, *, application=None):
        application = application or self.application
        held = application.billing_processor
        return StripeEventProcessor(application.runtime, held.config, held.policy,
            lambda _ref: "local-price-addition-signing", resolver)

    def event(self, processor, identity):
        now = int(time.time())
        raw = json.dumps({"id": identity, "object": "event", "api_version": fixtures.API,
            "livemode": False, "created": now, "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_alpha", "customer": "cus_alpha"}}}).encode()
        signature = hmac.new(b"local-price-addition-signing", str(now).encode() + b"." + raw,
                             hashlib.sha256).hexdigest()
        return processor.handle(raw, f"t={now},v1={signature}")

    def test_addition_keeps_paid_grant_bytes_and_validity_without_provider_calls(self):
        self.assertEqual(fixtures.paid_account(self.application), "applied")
        before = self.row(ENTITLEMENT, "alpha")
        self.add_price()
        with mock.patch("loop_engine.core.service_runtime.stripe_provider._read",
                        side_effect=AssertionError("a policy migration cannot read Stripe")):
            status, report, _text = fixtures.apply(self.path)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["paid_access_ended_for_accounts"], 0)
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(report["billing_policy"]["record_type"], billing_records.COMPATIBLE_POLICY_VERSION)
        self.assertEqual(self.row(ENTITLEMENT, "alpha"), before)
        self.assertEqual(fixtures.paying(self.application), 1)

    def test_grant_committed_during_policy_preparation_is_not_missed(self):
        self.add_price()
        configure = self.runtime.__class__.configure_billing_policy
        fired = False

        def race(runtime, policy, **kwargs):
            nonlocal fired
            if not fired:
                fired = True
                self.assertEqual(fixtures.paid_account(self.application), "applied")
            return configure(runtime, policy, **kwargs)

        with mock.patch.object(self.runtime.__class__, "configure_billing_policy", race):
            status, report, _text = fixtures.apply(self.path)
        self.assertEqual(status, 0, report)
        self.assertTrue(fired)
        self.assertEqual(fixtures.paying(self.application), 1)
        current, _ = load_host_billing_context(str(self.path))
        self.assertEqual(fixtures.paying(current), 1)

    def test_grant_committed_after_policy_read_is_covered_without_range_lock(self):
        self.add_price()
        commit, raced = ServiceCatalogBinding.commit, False

        def grant_before_commit(binding, store, records, guards, removals=()):
            nonlocal raced
            if not raced and any(row["artifact_kind"] == BILLING_POLICY for row in records):
                raced = True
                self.assertEqual(fixtures.paid_account(self.application), "applied")
            return commit(binding, store, records, guards, removals)

        with mock.patch.object(ServiceCatalogBinding, "commit", grant_before_commit):
            status, report, _ = fixtures.apply(self.path)
        self.assertEqual(status, 0, report)
        self.assertTrue(raced)
        self.assertEqual(fixtures.paying(self.application), 1)

    def test_concurrent_administrative_revocation_is_never_overwritten(self):
        fixtures.paid_account(self.application)
        self.add_price()
        commit, revoked = ServiceCatalogBinding.commit, False

        def revoke_before_commit(binding, store, records, guards, removals=()):
            nonlocal revoked
            if not revoked and any(row["artifact_kind"] == BILLING_POLICY for row in records):
                revoked = True
                self.runtime.revoke_entitlement("alpha")
            return commit(binding, store, records, guards, removals)

        with mock.patch.object(ServiceCatalogBinding, "commit", revoke_before_commit):
            status, report, _ = fixtures.apply(self.path)
        self.assertEqual(status, 0, report)
        self.assertTrue(revoked)
        self.assertEqual(fixtures.paying(self.application), 0)
        self.assertEqual(self.row(ENTITLEMENT, "alpha")["payload"]["source"], "host_revocation")

    def test_reader_first_release_leaves_the_current_v1_record_unchanged(self):
        fixtures.paid_account(self.application)
        before = fixtures.stored(self.path)
        status, report, _ = fixtures.apply(self.path)
        self.assertEqual(status, 0, report)
        self.assertFalse(report["changed"])
        self.assertEqual(report["billing_policy"]["record_type"], billing_records.STORED_POLICY_VERSION)
        self.assertEqual(fixtures.stored(self.path), before)

    def test_repeated_additions_keep_the_original_grant_and_replay_is_idempotent(self):
        fixtures.paid_account(self.application)
        original = self.row(ENTITLEMENT, "alpha")
        for prices in (("price_basic", "price_new"), ("price_basic", "price_new", "price_later")):
            fixtures.rewrite(self.path, lambda host: host["billing"]["policy"].update(allowed_price_ids=list(prices)))
            status, report, _ = fixtures.apply(self.path)
            self.assertEqual(status, 0, report)
            self.assertEqual(fixtures.paying(self.application), 1)
            self.assertEqual(self.row(ENTITLEMENT, "alpha"), original)
        before = fixtures.stored(self.path)
        status, report, _ = fixtures.apply(self.path)
        self.assertEqual(status, 0, report)
        self.assertFalse(report["changed"])
        self.assertEqual(fixtures.stored(self.path), before)

    def test_narrowing_and_nonprice_changes_still_refuse_with_paid_access(self):
        fixtures.paid_account(self.application)
        self.add_price()
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        before = fixtures.stored(self.path)
        for policy in ({"allowed_price_ids": ["price_basic"]},
                       {"allowed_price_ids": ["price_basic", "price_new", "price_later"], "allow_trialing": True}):
            with self.subTest(policy=policy):
                fixtures.rewrite(self.path, lambda host: host["billing"].update(policy=policy))
                self.assertEqual(fixtures.refused_code(self.path), fixtures.PAID_ACCESS_REFUSAL)
                self.assertEqual(fixtures.stored(self.path), before)
                self.assertEqual(fixtures.paying(self.application), 1)

    def test_expired_failed_pending_and_revoked_grants_never_reactivate(self):
        variants = ("expired", "failed", "pending", "revoked", "disabled")
        for variant in variants:
            with self.subTest(variant=variant), TemporaryDirectory(prefix="billing-ineligible-") as directory:
                path, application = fixtures.configured(Path(directory))
                fixtures.paid_account(application)
                runtime = application.runtime
                if variant == "revoked":
                    runtime.revoke_entitlement("alpha")
                elif variant == "disabled":
                    runtime.set_tenant_enabled("alpha", False)
                else:
                    with runtime._catalog.store(write=True) as store:
                        held = runtime._catalog.read(store, ENTITLEMENT, "alpha")
                        payload = dict(held["payload"])
                        if variant == "expired":
                            payload["valid_until"] = int(time.time()) - 1
                        else:
                            payload.update(enabled=False, entitlement="metadata", valid_until=None)
                            if variant == "pending":
                                payload["pending_event_id"] = "evt_unresolved"
                        changed = runtime._catalog.record(ENTITLEMENT, "alpha", payload, tenant_id="alpha")
                        runtime._catalog.commit(store, (changed,), (runtime._catalog.guard(held),))
                with runtime._catalog.store() as store:
                    before = runtime._catalog.read(store, ENTITLEMENT, "alpha")
                fixtures.rewrite(path, fixtures.a_new_entitlement_policy)
                status, report, _ = fixtures.apply(path)
                self.assertEqual(status, 0, report)
                self.assertEqual(fixtures.paying(application), 0)
                with runtime._catalog.store() as store:
                    self.assertEqual(runtime._catalog.read(store, ENTITLEMENT, "alpha"), before)

    def test_operator_and_promotion_grants_are_byte_for_byte_unchanged(self):
        from loop_engine.core.service_runtime.runtime import CODE_GRANT_SOURCE
        for source in ("explicit_host_grant", CODE_GRANT_SOURCE):
            with self.subTest(source=source), TemporaryDirectory(prefix="billing-free-grant-") as directory:
                path, application = fixtures.configured(Path(directory))
                runtime = application.runtime
                runtime.set_operator_entitlement("alpha", valid_until=int(time.time()) + 3600,
                                                 evidence_ref="fixture:price-migration")
                if source == CODE_GRANT_SOURCE:
                    with runtime._catalog.store(write=True) as store:
                        held = runtime._catalog.read(store, ENTITLEMENT, "alpha")
                        changed = runtime._catalog.record(ENTITLEMENT, "alpha",
                            {**held["payload"], "source": source, "promotion_code_id": "fixture-promotion"},
                            tenant_id="alpha")
                        runtime._catalog.commit(store, (changed,), (runtime._catalog.guard(held),))
                with runtime._catalog.store() as store:
                    before = runtime._catalog.read(store, ENTITLEMENT, "alpha")
                fixtures.rewrite(path, fixtures.a_new_entitlement_policy)
                self.assertEqual(fixtures.apply(path)[0], 0)
                report = runtime.access_source_report()
                self.assertEqual(report["counts"]["comped"], 1)
                self.assertEqual(report["counts"]["revenue_bearing"], 0)
                with runtime._catalog.store() as store:
                    self.assertEqual(runtime._catalog.read(store, ENTITLEMENT, "alpha"), before)

    def test_stale_expected_revision_refuses_even_an_identical_policy(self):
        previous = self.row(BILLING_POLICY, "stripe")
        self.add_price()
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        before = fixtures.stored(self.path)
        policy = StripeEntitlementPolicy(("price_basic", "price_new"))
        self.require_refusal("billing_policy_revision_required", lambda: self.runtime.configure_billing_policy(
            policy, expected_version=previous["record_version"], preserve_price_additions=True))
        self.assertEqual(fixtures.stored(self.path), before)

    def test_concurrent_policy_writer_refuses_the_losing_atomic_batch(self):
        fixtures.paid_account(self.application)
        prior = self.row(BILLING_POLICY, "stripe")
        commit, raced = ServiceCatalogBinding.commit, False

        def compete(binding, store, records, guards, removals=()):
            nonlocal raced
            if not raced and any(row["artifact_kind"] == BILLING_POLICY for row in records):
                raced = True
                self.runtime.configure_billing_policy(StripeEntitlementPolicy(("price_basic", "price_competing")),
                    expected_version=prior["record_version"], preserve_price_additions=True)
            return commit(binding, store, records, guards, removals)

        with mock.patch.object(ServiceCatalogBinding, "commit", compete):
            self.require_refusal("concurrent_update", lambda: self.runtime.configure_billing_policy(
                StripeEntitlementPolicy(("price_basic", "price_new")), expected_version=prior["record_version"],
                preserve_price_additions=True))
        self.assertTrue(raced)
        self.assertEqual(self.row(BILLING_POLICY, "stripe")["payload"]["policy"]["allowed_price_ids"],
                         ["price_basic", "price_competing"])
        self.assertEqual(fixtures.paying(self.application), 1)

    def test_inflight_webhook_is_retained_pending_and_resumes_under_the_union(self):
        fixtures.paid_account(self.application)

        def during_read(_customer):
            self.add_price()
            self.assertEqual(fixtures.apply(self.path)[0], 0)
            return self.snapshot()

        processor = self.processor(StripeSubscriptionResolver("fixture:race", during_read))
        result = self.event(processor, "evt_inflight")
        self.assertEqual(result.status, "pending")
        self.assertEqual(result.diagnostic_code, "concurrent_reconciliation")
        self.assertEqual(fixtures.paying(self.application), 0)
        current, _ = load_host_billing_context(str(self.path))
        resumed = self.processor(StripeSubscriptionResolver("fixture:current", lambda _customer: self.snapshot()),
                                 application=current).resume_event("evt_inflight")
        self.assertEqual(resumed.status, "applied")
        self.assertEqual(fixtures.paying(current), 1)

    def test_old_webhook_processor_cannot_invalidate_preserved_access(self):
        fixtures.paid_account(self.application)
        old = self.processor(StripeSubscriptionResolver("fixture:old", lambda _customer: self.snapshot()))
        self.add_price()
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        before = fixtures.stored(self.path)
        self.require_refusal("billing_policy_mismatch", lambda: self.event(old, "evt_stale_writer"))
        self.assertEqual(fixtures.stored(self.path), before)
        self.assertEqual(fixtures.paying(self.application), 1)

    def test_current_failed_payment_still_ends_preserved_access(self):
        fixtures.paid_account(self.application)
        self.add_price()
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        current, _ = load_host_billing_context(str(self.path))
        processor = self.processor(StripeSubscriptionResolver("fixture:failed", lambda _customer: self.snapshot(paid=False)),
                                   application=current)
        self.assertEqual(self.event(processor, "evt_failed").status, "applied")
        self.assertEqual(fixtures.paying(current), 0)

    def test_unknown_commit_is_not_success_and_idempotent_reconciliation_keeps_access(self):
        fixtures.paid_account(self.application)
        self.add_price()
        commit, lost = ServiceCatalogBinding.commit, False

        def lose_reply(binding, store, records, guards, removals=()):
            nonlocal lost
            result = commit(binding, store, records, guards, removals)
            if not lost and any(row["artifact_kind"] == BILLING_POLICY for row in records):
                lost = True
                raise ServiceCommitUnknown()
            return result

        with mock.patch.object(ServiceCatalogBinding, "commit", lose_reply), self.assertRaises(ServiceCommitUnknown):
            fixtures.apply(self.path)
        self.assertEqual(fixtures.paying(self.application), 1)
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        self.assertEqual(fixtures.paying(self.application), 1)

    def test_checkout_price_rollback_keeps_the_accepted_union_and_grants(self):
        fixtures.paid_account(self.application)
        self.add_price()
        fixtures.rewrite(self.path, lambda host: host["billing"]["sessions"]["plans"][0].update(price_id="price_new"))
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        accepted = self.row(BILLING_POLICY, "stripe")
        grant = self.row(ENTITLEMENT, "alpha")
        fixtures.rewrite(self.path, lambda host: host["billing"]["sessions"]["plans"][0].update(price_id="price_basic"))
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        self.assertEqual(self.row(BILLING_POLICY, "stripe"), accepted)
        self.assertEqual(self.row(ENTITLEMENT, "alpha"), grant)
        self.assertEqual(fixtures.paying(self.application), 1)

    def test_compatibility_bounds_refuse_before_any_policy_write(self):
        fixtures.paid_account(self.application)
        self.add_price()
        before = fixtures.stored(self.path)
        for bound in ("MAXIMUM_COMPATIBLE_POLICIES", "MAXIMUM_COMPATIBLE_POLICY_BYTES"):
            with self.subTest(bound=bound), mock.patch.object(billing_records, bound, 0):
                self.require_refusal("billing_policy_compatibility_bound", lambda: fixtures.apply(self.path))
            self.assertEqual(fixtures.stored(self.path), before)
            self.assertEqual(fixtures.paying(self.application), 1)

    def test_full_compatibility_proofs_reject_forged_digest_terms_and_structure(self):
        previous = self.row(BILLING_POLICY, "stripe")["payload"]
        value = billing_records.additive_billing_policy_record(previous,
            StripeEntitlementPolicy(("price_basic", "price_new")))
        mutations = {
            "current digest": lambda v: v.update(policy_digest="a" * 64),
            "prior digest": lambda v: v["compatible_policies"][0].update(policy_digest="a" * 64),
            "extra field": lambda v: v.update(unchecked=True),
            "extra proof field": lambda v: v["compatible_policies"][0].update(unchecked=True),
            "duplicate proof": lambda v: v["compatible_policies"].append(deepcopy(v["compatible_policies"][0])),
            "self proof": lambda v: v["compatible_policies"].append({"policy": v["policy"], "policy_digest": v["policy_digest"]}),
        }
        for name, change in mutations.items():
            with self.subTest(name=name):
                changed = deepcopy(value)
                change(changed)
                self.require_refusal("invalid_billing_policy_proof",
                    lambda: billing_records.read_stored_billing_policy(changed))
        for prior in (StripeEntitlementPolicy(("price_basic",), allow_trialing=True),
                      StripeEntitlementPolicy(("price_unrelated",))):
            with self.subTest(prior=prior):
                changed = deepcopy(value)
                changed["compatible_policies"] = [{"policy": asdict(prior), "policy_digest": digest(asdict(prior))}]
                self.require_refusal("invalid_billing_policy_proof",
                    lambda: billing_records.read_stored_billing_policy(changed))

    def test_removed_compatibility_and_semantic_guards_are_detected(self):
        fixtures.paid_account(self.application)
        self.add_price()
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        with mock.patch.object(billing_records, "billing_policy_accepts_grant",
                               side_effect=lambda value, grant: value["policy_digest"] == grant):
            self.assertEqual(fixtures.paying(self.application), 0, "the known-wrong old matcher loses paid access")
        value = deepcopy(self.row(BILLING_POLICY, "stripe")["payload"])
        prior = StripeEntitlementPolicy(("price_basic",), allow_trialing=True)
        value["compatible_policies"] = [{"policy": asdict(prior), "policy_digest": digest(asdict(prior))}]
        with mock.patch.object(billing_records, "is_price_only_addition", return_value=True):
            self.assertTrue(billing_records.billing_policy_accepts_grant(value, digest(asdict(prior))),
                            "the removed semantic guard wrongly admits changed policy terms")

    def test_unknown_versions_and_unproved_grant_digests_are_refused(self):
        previous = self.row(BILLING_POLICY, "stripe")["payload"]
        value = billing_records.additive_billing_policy_record(previous,
            StripeEntitlementPolicy(("price_basic", "price_new")))
        self.assertFalse(billing_records.billing_policy_accepts_grant(value, "a" * 64))
        changed = {**value, "record_type": "service_billing_policy/v99"}
        self.require_refusal("unsupported_billing_policy_record",
                             lambda: billing_records.read_stored_billing_policy(changed))
        # The pre-migration image's policy reader accepts only v1. Do not
        # describe an image rollback as qualified after a v2 record is stored.
        self.assertNotEqual(value["record_type"], self.row(BILLING_POLICY, "stripe")["payload"]["record_type"])

    def test_malformed_price_identities_have_typed_refusals_in_current_and_archived_proofs(self):
        previous = self.row(BILLING_POLICY, "stripe")["payload"]
        compatible = billing_records.additive_billing_policy_record(previous,
            StripeEntitlementPolicy(("price_basic", "price_new")))
        before = fixtures.stored(self.path)
        for version, location in (("v1", "current"), ("v2", "current"), ("v2", "prior")):
            for invalid in INVALID_PRICE_IDENTITIES:
                with self.subTest(version=version, location=location, invalid=invalid):
                    value = deepcopy(previous if version == "v1" else compatible)
                    proof = value if location == "current" else value["compatible_policies"][0]
                    proof["policy"]["allowed_price_ids"] = [invalid]
                    self.require_refusal("invalid_billing_policy_proof",
                        lambda: billing_records.read_stored_billing_policy(value))
        self.assertEqual(fixtures.stored(self.path), before)

    def test_malformed_retained_proof_cannot_issue_a_principal_or_write_during_authentication(self):
        from loop_engine.core.service_runtime.records import SubjectBindingRequest
        fixtures.paid_account(self.application)
        self.runtime.bind_subject(SubjectBindingRequest("alpha", "fixture-issuer", "fixture-subject"))
        previous = self.row(BILLING_POLICY, "stripe")["payload"]
        self.add_price()
        self.assertEqual(fixtures.apply(self.path)[0], 0)
        compatible = self.row(BILLING_POLICY, "stripe")["payload"]
        for version, location in (("v1", "current"), ("v2", "current"), ("v2", "prior")):
            for invalid in INVALID_PRICE_IDENTITIES:
                with self.subTest(version=version, location=location, invalid=invalid):
                    value = deepcopy(previous if version == "v1" else compatible)
                    proof = value if location == "current" else value["compatible_policies"][0]
                    proof["policy"]["allowed_price_ids"] = [invalid]
                    with self.runtime._catalog.store(write=True) as store:
                        held = self.runtime._catalog.read(store, BILLING_POLICY, "stripe")
                        changed = self.runtime._catalog.record(BILLING_POLICY, "stripe", value)
                        self.runtime._catalog.commit(store, (changed,), (self.runtime._catalog.guard(held),))
                    before = fixtures.stored(self.path)
                    with mock.patch.object(ServiceCatalogBinding, "commit", side_effect=AssertionError("a reader cannot write")):
                        self.require_refusal("invalid_billing_policy_proof",
                            lambda: self.runtime.authenticate_subject("fixture-issuer", "fixture-subject"))
                    self.assertEqual(fixtures.stored(self.path), before)

    def test_price_identity_maximum_and_exact_string_type(self):
        largest = "p" * 128
        previous = {"record_type": billing_records.STORED_POLICY_VERSION,
                    "policy": asdict(StripeEntitlementPolicy((largest,)))}
        previous["policy_digest"] = digest(previous["policy"])
        value = billing_records.additive_billing_policy_record(previous,
            StripeEntitlementPolicy((largest, "price_new")))
        current, prior = billing_records.read_stored_billing_policy(value)
        self.assertIn(largest, current.allowed_price_ids)
        self.assertEqual(prior[0].allowed_price_ids, (largest,))

        class PriceText(str):
            pass

        for proof in (value, value["compatible_policies"][0]):
            mutated = deepcopy(proof)
            mutated["policy"]["allowed_price_ids"] = [PriceText(largest)]
            mutated["policy_digest"] = digest(mutated["policy"])
            self.require_refusal("invalid_billing_policy_proof", lambda: billing_records._policy_proof(
                {key: mutated[key] for key in ("policy", "policy_digest")}))

    def test_price_identity_validation_precedes_policy_construction(self):
        previous = self.row(BILLING_POLICY, "stripe")["payload"]
        for invalid in INVALID_PRICE_IDENTITIES:
            with self.subTest(invalid=invalid):
                proof = {key: deepcopy(previous[key]) for key in ("policy", "policy_digest")}
                proof["policy"]["allowed_price_ids"] = [invalid]
                with mock.patch.object(billing_records, "StripeEntitlementPolicy",
                                       side_effect=AssertionError("malformed IDs reached policy construction")):
                    self.require_refusal("invalid_billing_policy_proof", lambda: billing_records._policy_proof(proof))

    def test_preservation_flag_cannot_admit_narrowing_or_other_terms(self):
        prior = self.row(BILLING_POLICY, "stripe")
        for policy in (StripeEntitlementPolicy(()), StripeEntitlementPolicy(("price_other",)),
                       StripeEntitlementPolicy(("price_basic", "price_new"), allow_trialing=True)):
            with self.subTest(policy=policy):
                self.require_refusal("billing_policy_not_price_addition", lambda: self.runtime.configure_billing_policy(
                    policy, expected_version=prior["record_version"], preserve_price_additions=True))
                self.assertEqual(self.row(BILLING_POLICY, "stripe"), prior)

    def test_pending_checkout_outcome_is_not_rewritten_or_replayed(self):
        from loop_engine.core.service_runtime import stripe_session_checks as sessions
        from loop_engine.core.service_runtime.billing_effects import SESSION_EFFECT_KIND
        from loop_engine.core.service_runtime.stripe_sessions import StripeSessionAdapter
        with TemporaryDirectory(prefix="billing-pending-checkout-") as directory:
            case = sessions.fixture(directory)
            case.provider.lose_next_response = True
            request = sessions.request(case, "pending-price-change")
            principal = sessions.principal(case)
            with self.assertRaises(ServiceRuntimeError):
                case.adapter.create(principal, request)
            with case.runtime._catalog.store() as store:
                effects = case.runtime._catalog.rows_all(store, SESSION_EFFECT_KIND)
                held = case.runtime._catalog.read(store, BILLING_POLICY, "stripe")
            self.assertEqual(len(effects), 1)
            self.assertEqual(effects[0]["payload"]["status"], "unknown")
            calls = len(case.provider.calls)
            case.runtime.configure_billing_policy(StripeEntitlementPolicy(("price_basic", "price_other", "price_new")),
                expected_version=held["record_version"], preserve_price_additions=True)
            configuration = replace(case.adapter.configuration,
                plans=tuple(replace(plan, price_id="price_new") if plan.plan_ref == "basic" else plan
                            for plan in case.adapter.configuration.plans))
            newer = StripeSessionAdapter(case.runtime, configuration, lambda _ref: sessions.FIXTURE_SECRET,
                                         transport=case.provider)
            newer.configure_policy(expected_version=case.adapter.effects.held_policy()["record_version"])
            self.require_refusal("session_selection_changed", lambda: newer.create(principal, request))
            self.assertEqual(len(case.provider.calls), calls)
            with case.runtime._catalog.store() as store:
                self.assertEqual(case.runtime._catalog.rows_all(store, SESSION_EFFECT_KIND), effects)


if __name__ == "__main__":
    main()
