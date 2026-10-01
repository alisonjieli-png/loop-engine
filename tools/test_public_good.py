"""Public Good domain checks; synthetic SQLite state, no provider calls."""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from loop_engine.core.harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
from loop_engine.core.provisioning_server import ProvisioningError, ProvisioningGrant, ProvisioningItemBinding, ProvisioningQualification, ProvisioningQualificationResolver
from loop_engine.core.service_runtime.catalogue_serving import CatalogueView
from loop_engine.core.service_runtime.provisioning import DurableProvisioningBinding
from loop_engine.core.service_runtime.records import ServiceRuntimeConfig, ServiceRuntimeError, SubjectTenantRegistration, TenantKeyIssue, TenantRegistration
from loop_engine.core.service_runtime.runtime import ServiceRuntime
from loop_engine.core.service_runtime import public_good as pg


class PublicGoodTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.now = [1000]
        self.runtime = ServiceRuntime(ServiceRuntimeConfig(str(Path(self.folder.name) / "state.db"), writes_authorized=True), clock=lambda: self.now[0])
        self.runtime.ensure_subject_tenant(SubjectTenantRegistration("https://identity.example", "worker-fixture", "customer", follows_active_release=True))
        self.principal = self.runtime.authenticate_subject("https://identity.example", "worker-fixture")
        self.bodies = {"public.fixture": "PUBLIC SYNTHETIC BODY", "paid.fixture": "PAID SYNTHETIC BODY"}
        self.items = {key: item_from_body(HarnessIntelligenceDraft(key, "skill", "Synthetic useful fixture", "context_intelligence", "fixture:" + key, "MIT"), body) for key, body in self.bodies.items()}
        self.catalogue = HarnessIntelligenceCatalogue(self.items)
        self.bindings = {key: ProvisioningItemBinding.from_item(item) for key, item in self.items.items()}
        self.resolver = ProvisioningQualificationResolver("fixture", lambda binding: ProvisioningQualification(binding, "approved", "host_attested", "fixture-review"))
        self.reads = []
        self.before_read = None
        def reader(item):
            self.reads.append(item.identity)
            if self.before_read:
                self.before_read()
            return self.bodies[item.identity]
        self.view = CatalogueView(self.catalogue, self.resolver, reader, item_versions={key: ("a" if key.startswith("public") else "b") * 64 for key in self.items})
        self.binding = DurableProvisioningBinding(self.runtime, self.catalogue, self.resolver, reader, view=self.view)
        self.service = self.binding.public_good
        self.grant = pg.PublicGoodGrant(self.bindings["public.fixture"], "a" * 64, "fixture-review", "fixture-rights", (8,), "Synthetic worker-support capability", 2000)
        self.service.configure(self.view, (self.grant,))

    def ask(self, identity="public.fixture", request_id="fixture-read"):
        return self.binding.invoke_for_principal(self.principal, "read", identity=identity, expected_digest=self.bindings[identity].body_digest, request_id=request_id)

    def code(self, call):
        try:
            call()
        except (ServiceRuntimeError, ProvisioningError) as error:
            return error.code
        self.fail("expected refusal")

    def configure(self, grants=None, limits=None):
        before = self.service.snapshot(self.view)
        return self.service.configure(self.view, (self.grant,) if grants is None else grants, limits=limits or before.limits, expected_version=before.version)

    def refresh(self):
        from loop_engine.core.service_runtime.catalogue_releases import read_state
        with self.runtime._catalog.store() as store:
            _row, state = read_state(self.runtime._catalog, store)
        self.view = replace(self.view, state_revision=state["revision"] if state else 0)
        self.binding.install_view(self.view)

    def test_free_account_reads_only_exact_public_good_without_paid_usage(self):
        self.assertEqual(self.principal.entitlement, "metadata")
        self.assertEqual(self.ask()["body"], self.bodies["public.fixture"])
        self.assertEqual(self.runtime.revalidate(self.principal).entitlement, "metadata")
        self.assertEqual(self.runtime.usage_for(self.principal)["records"], 0)
        self.assertEqual(self.code(lambda: self.ask("paid.fixture")), "body_forbidden")
        self.assertEqual(self.reads, ["public.fixture"])
        with self.runtime._catalog.store() as store:
            self.assertTrue(pg.downloaded(self.runtime._catalog, store, self.principal.tenant_id, "public.fixture", self.grant.binding.body_digest))

    def test_existing_unmetered_grant_does_not_waive_subscription(self):
        self.configure(grants=())
        self.runtime.set_grants(self.principal.tenant_id, (ProvisioningGrant(self.principal.tenant_id, self.bindings["paid.fixture"], True, "unmetered"),))
        self.assertEqual(self.code(lambda: self.ask("paid.fixture")), "body_forbidden")
        self.assertFalse(self.reads)

    def test_paid_accounts_use_free_grant_without_charging_and_paid_items_still_charge(self):
        self.runtime.set_operator_entitlement(self.principal.tenant_id, valid_until=2000, evidence_ref="synthetic-comp")
        self.ask()
        self.assertEqual(self.runtime.usage_for(self.principal)["records"], 0)
        self.ask("paid.fixture")
        self.assertEqual(self.runtime.usage_for(self.principal)["records"], 1)

    def test_expired_and_changed_version_not_free(self):
        self.now[0] = 2000
        self.assertFalse(self.service.allows(self.principal, self.view, "public.fixture"))
        self.now[0] = 1000
        view = replace(self.view, item_versions={"public.fixture": "c" * 64})
        self.assertFalse(self.service.allows(self.principal, view, "public.fixture"))
        self.assertFalse(self.service.allows(self.principal, self.view, "public.fixture", "f" * 64))

    def test_denials_and_body_revocation_remain_authoritative(self):
        from loop_engine.core.service_runtime.catalogue_grants import follow_active_release
        follow_active_release(self.runtime, (self.principal.tenant_id,), denials=("public.fixture",))
        self.refresh()
        self.assertFalse(self.service.allows(self.principal, self.view, "public.fixture"))
        follow_active_release(self.runtime, (self.principal.tenant_id,))
        self.refresh()
        self.runtime.revoke_entitlement(self.principal.tenant_id)
        self.assertFalse(self.service.allows(self.principal, self.view, "public.fixture"))
        self.assertEqual(self.code(self.ask), "body_forbidden")

    def test_unbound_host_account_does_not_gain_public_good_body_access(self):
        self.runtime.register_tenant(TenantRegistration("host-fixture", "host-fixture"))
        key = self.runtime.issue_key(TenantKeyIssue("host-fixture", "fixture"))
        host = self.runtime.authenticate_key(key.key)
        self.assertFalse(self.service.allows(host, self.view, "public.fixture"))

    def test_owner_bound_customer_keys_keep_scope_revocation_and_shared_limits(self):
        from loop_engine.core.service_runtime.access import ServiceAccessAdministration, ServiceAccessSession, ServiceAccessRequest, ServiceClientAccessPolicy
        from loop_engine.core.service_runtime.records import SubjectBindingRequest
        management = ServiceAccessAdministration(self.runtime, ServiceClientAccessPolicy(writes_authorized=True))
        session = ServiceAccessSession(self.principal.authentication_record_id, "a" * 64, 1900, self.principal.scopes)
        def issue(name, scopes):
            request = ServiceAccessRequest("issue", name, self.principal.tenant_id, label="synthetic", scopes=scopes, lifetime_seconds=600)
            return management.apply(self.principal, request, session=session)["token"]
        first = issue("first", self.principal.scopes)
        second = issue("second", self.principal.scopes)
        narrow = issue("narrow", ("provisioning:metadata",))
        self.configure(limits=pg.PublicGoodLimits(requests_per_window=1))
        narrow_principal = self.runtime.authenticate_key(narrow)
        self.assertFalse(self.service.allows(narrow_principal, self.view, "public.fixture"))
        self.assertEqual(self.code(lambda: self.binding.invoke(narrow, "read", identity="public.fixture", request_id="narrow")), "scope_required")
        self.assertFalse(self.binding.invoke(first, "read", identity="public.fixture", request_id="full")["metered"])
        self.assertEqual(self.code(lambda: self.binding.invoke(second, "read", identity="public.fixture", request_id="second")), "public_good_rate_limited")
        self.runtime.revoke_subject(SubjectBindingRequest(self.principal.tenant_id, "https://identity.example", "worker-fixture"))
        self.assertEqual(self.code(lambda: self.binding.invoke(first, "read", identity="public.fixture", request_id="revoked")), "unauthorized")

    def test_no_ordinary_persisted_grant_can_smuggle_the_exception(self):
        from loop_engine.core.provisioning_server import ACCOUNT_GRANT_RECORD_TYPE
        self.assertEqual(self.code(lambda: self.runtime.set_grants(self.principal.tenant_id,
            (ProvisioningGrant(self.principal.tenant_id, self.bindings["paid.fixture"], True, "unmetered", ACCOUNT_GRANT_RECORD_TYPE),))),
            "public_good_requires_exact_policy")
        self.assertEqual(self.code(lambda: self.ask("paid.fixture")), "body_forbidden")
        self.assertFalse(self.reads)

    def test_disabled_account_and_forged_principal_refuse(self):
        self.assertEqual(self.code(lambda: self.service.allows(replace(self.principal, tenant_id="other"), self.view, "public.fixture")), "unissued_principal")
        self.runtime.set_tenant_enabled(self.principal.tenant_id, False)
        self.assertEqual(self.code(self.ask), "unauthorized")
        self.assertFalse(self.reads)

    def test_configure_is_guarded_exact_and_strict(self):
        self.assertEqual(self.code(lambda: self.service.configure(self.view, (self.grant,))), "public_good_policy_changed")
        self.assertEqual(self.code(lambda: self.configure((replace(self.grant, item_version="d"*64),))), "public_good_grant_not_current")
        bad = {**asdict(self.grant), "subscription_required": False}
        self.assertEqual(self.code(lambda: pg.PublicGoodGrant.from_dict(bad)), "public_good_record_invalid")
        self.assertEqual(self.code(lambda: pg.PublicGoodLimits(requests_per_window=True)), "public_good_limits_invalid")
        self.assertEqual(self.code(lambda: replace(self.grant, sdg_goals=(18,))), "public_good_record_invalid")

    def test_unknown_or_untyped_qualification_cannot_appear_in_browse(self):
        from types import SimpleNamespace
        fake = SimpleNamespace(status="approved", binding=self.grant.binding, approval_ref=self.grant.approval_ref)
        resolver = ProvisioningQualificationResolver("wrong", lambda binding: fake)
        self.assertFalse(self.service.snapshot(replace(self.view, qualification_resolver=resolver)).grants)
        def failed(_binding):
            raise OSError("synthetic source failure")
        resolver = ProvisioningQualificationResolver("failed", failed)
        self.assertFalse(self.service.snapshot(replace(self.view, qualification_resolver=resolver)).grants)

    def test_related_initiative_alone_is_an_explicit_access_grant(self):
        related = replace(self.grant, sdg_goals=(), initiatives=("worker-protection",))
        self.configure(grants=(related,))
        self.assertEqual(self.service.snapshot(self.view).grants[0].sdg_goals, ())
        self.assertEqual(self.service.snapshot(self.view).grants[0].initiatives, ("worker-protection",))
        self.assertFalse(self.ask()["metered"])

    def test_associations_reject_empty_boolean_duplicate_and_malformed_values(self):
        for changes in (
            {"sdg_goals": (), "initiatives": ()},
            {"sdg_goals": (True,), "initiatives": ("worker-protection",)},
            {"sdg_goals": (8, 8)},
            {"sdg_goals": "8", "initiatives": ("worker-protection",)},
            {"sdg_goals": (), "initiatives": ("worker-protection", "worker-protection")},
            {"sdg_goals": (), "initiatives": ("Uppercase",)},
            {"sdg_goals": (), "initiatives": ("unsafe/path",)},
            {"sdg_goals": (), "initiatives": (True,)},
            {"sdg_goals": (), "initiatives": ([],)},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.code(lambda: replace(self.grant, **changes)), "public_good_record_invalid")

    def test_revocation_or_expiry_during_body_read_prevents_delivery_record_and_disclosure(self):
        self.before_read = lambda: self.configure(grants=())
        self.assertIn(self.code(self.ask), ("public_good_authority_changed", "item_unavailable"))
        with self.runtime._catalog.store() as store:
            self.assertFalse(pg.downloaded(self.runtime._catalog, store, self.principal.tenant_id, "public.fixture", self.grant.binding.body_digest))

    def test_external_reservation_bounds_actual_response_and_cannot_replay(self):
        reservation = self.service.reserve(self.principal, self.view, "public.fixture", expected_digest=self.grant.binding.body_digest, request_id="package", response_bytes=200)
        body = self.binding.invoke_for_principal(self.principal, "read", identity="public.fixture", expected_digest=self.grant.binding.body_digest, request_id="package", public_good_reservation=reservation)
        self.assertEqual(body["metered"], False)
        self.assertEqual(self.code(lambda: self.service.complete(reservation, self.principal, self.view, response_bytes=201)), "public_good_reservation_invalid")
        result = self.service.complete(reservation, self.principal, self.view, response_bytes=80)
        self.assertEqual(result["record_type"], "service_public_good_delivery/v1")
        self.assertEqual(result["record_ref"][:8], "service:")
        self.assertEqual(result["billed_quantity"], 0)
        self.assertEqual(self.code(lambda: self.service.revalidate(reservation, self.principal, self.view)), "public_good_reservation_closed")

    def test_atomic_request_and_byte_limits_shared_by_concurrent_requests(self):
        self.configure(limits=pg.PublicGoodLimits(requests_per_window=2, bytes_per_window=100, maximum_response_bytes=100))
        def attempt(index):
            try:
                return self.service.reserve(self.principal, self.view, "public.fixture", expected_digest=self.grant.binding.body_digest, request_id="parallel-" + str(index), response_bytes=50)
            except ServiceRuntimeError as error:
                return error
        with ThreadPoolExecutor(max_workers=5) as executor:
            values = list(executor.map(attempt, range(5)))
        self.assertEqual(sum(isinstance(v, pg.PublicGoodReservation) for v in values), 2)
        self.assertTrue(all(v.code == "public_good_rate_limited" and v.retry_after_seconds > 0 for v in values if isinstance(v, ServiceRuntimeError)))

    def test_failed_read_still_consumes_reservation_and_window_resets(self):
        self.configure(limits=pg.PublicGoodLimits(requests_per_window=1, window_seconds=60))
        self.before_read = lambda: (_ for _ in ()).throw(ValueError("synthetic"))
        self.assertEqual(self.code(self.ask), "body_reader_unavailable")
        self.assertEqual(self.code(self.ask), "public_good_rate_limited")
        self.before_read = None
        self.now[0] = 1020  # Next fixed minute.
        self.assertEqual(self.ask()["metered"], False)

    def test_reservation_rechecks_withdrawal_and_account_at_completion(self):
        reservation = self.service.reserve(self.principal, self.view, "public.fixture", expected_digest=self.grant.binding.body_digest, request_id="planned", response_bytes=100)
        def withdraw(_identity, _digest):
            raise ServiceRuntimeError("item_withdrawn")
        withdrawn = replace(self.view, withdrawal_check=withdraw)
        self.assertEqual(self.code(lambda: self.service.complete(reservation, self.principal, withdrawn, response_bytes=50)), "item_withdrawn")
        self.runtime.set_tenant_enabled(self.principal.tenant_id, False)
        self.assertEqual(self.code(lambda: self.service.complete(reservation, self.principal, self.view, response_bytes=50)), "unauthorized")

    def test_expiry_and_policy_changes_refuse_held_reservations(self):
        reservation = self.service.reserve(self.principal, self.view, "public.fixture", expected_digest=self.grant.binding.body_digest, request_id="planned", response_bytes=100)
        self.now[0] = 2000
        self.assertEqual(self.code(lambda: self.service.revalidate(reservation, self.principal, self.view)), "public_good_authority_changed")
        self.now[0] = 1000
        self.configure(grants=(replace(self.grant, active=False),))
        self.assertFalse(self.service.snapshot(self.view).grants)
        self.assertEqual(self.code(lambda: self.service.revalidate(reservation, self.principal, self.view)), "public_good_authority_changed")

    def test_forged_and_cross_account_reservations_refuse(self):
        reservation = self.service.reserve(self.principal, self.view, "public.fixture", expected_digest=self.grant.binding.body_digest, request_id="planned", response_bytes=100)
        self.assertEqual(self.code(lambda: self.service.revalidate(replace(reservation, response_bytes=101), self.principal, self.view)), "public_good_reservation_invalid")
        self.runtime.ensure_subject_tenant(SubjectTenantRegistration("https://identity.example", "other-fixture", "customer"))
        other = self.runtime.authenticate_subject("https://identity.example", "other-fixture")
        self.assertEqual(self.code(lambda: self.service.revalidate(reservation, other, self.view)), "public_good_reservation_invalid")

    def test_transport_none_cannot_silently_auto_reserve_a_new_free_policy(self):
        self.assertEqual(self.code(lambda: self.binding.invoke_for_principal(self.principal, "read", identity="public.fixture",
            request_id="unplanned", public_good_reservation=None)), "public_good_authority_changed")
        self.assertFalse(self.reads)

    def test_expiry_at_delivery_record_commit_prevents_a_successful_return(self):
        reservation = self.service.reserve(self.principal, self.view, "public.fixture", expected_digest=self.grant.binding.body_digest, request_id="expiry", response_bytes=100)
        original = type(self.service.catalog).commit
        def expiring_commit(binding, *args, **kwargs):
            result = original(binding, *args, **kwargs)
            self.now[0] = 2000
            return result
        with patch.object(type(self.service.catalog), "commit", expiring_commit):
            self.assertEqual(self.code(lambda: self.service.complete(reservation, self.principal, self.view, response_bytes=50)), "public_good_authority_changed")

    def test_unknown_reservation_commit_never_replays_a_write(self):
        from loop_engine.core.service_runtime.records import ServiceCommitUnknown
        with patch.object(type(self.service.catalog), "commit", side_effect=ServiceCommitUnknown) as commit:
            self.assertEqual(self.code(lambda: self.service.reserve(self.principal, self.view, "public.fixture", expected_digest=self.grant.binding.body_digest, request_id="unknown", response_bytes=100)), "commit_unknown")
            self.assertEqual(commit.call_count, 1)

    def test_shared_host_ceiling_limits_different_accounts_atomically(self):
        self.configure(limits=pg.PublicGoodLimits(host_requests_per_window=1))
        self.runtime.ensure_subject_tenant(SubjectTenantRegistration("https://identity.example", "second-account", "customer"))
        second = self.runtime.authenticate_subject("https://identity.example", "second-account")
        self.ask()
        self.assertEqual(self.code(lambda: self.binding.invoke_for_principal(second, "read", identity="public.fixture", request_id="second-account")), "public_good_rate_limited")
        self.assertEqual(self.reads, ["public.fixture"])

    def test_removed_exact_version_guard_is_detected(self):
        with patch.object(pg, "_matches", return_value=True):
            substituted = replace(self.view, item_versions={"public.fixture": "e"*64})
            self.assertTrue(self.service.allows(self.principal, substituted, "public.fixture"))
        self.assertFalse(self.service.allows(self.principal, substituted, "public.fixture"))


if __name__ == "__main__":
    unittest.main()
