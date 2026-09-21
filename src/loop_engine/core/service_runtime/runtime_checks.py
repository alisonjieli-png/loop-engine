"""Real SQLite public-path checks for the durable hosted-service domain.

Owns restart, tenant/key/subject isolation, live revocation, usage idempotency,
unknown-write outcomes, atomic read-set batches, and module-boundary controls.
Uses local trusted fixtures only; it does not qualify a provider or deployment.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ast
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import threading

from ...catalog.protocol import (CatalogBatchAcknowledgment, CatalogRecordPrecondition,
    CatalogWriteBatch, PreconditionFailed, StoreError, UnsupportedOperationError, require_atomic_batch)
from ...catalog.stores.in_memory import EphemeralRecordStore
from ...catalog.stores.sqlite_store import SQLiteRecordStore
from ..harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
from ..provisioning_server import (ProvisioningError, ProvisioningGrant, ProvisioningItemBinding,
    ProvisioningQualification, ProvisioningQualificationResolver)
from .provisioning import DurableProvisioningBinding
from .records import (BILLING_MANAGE_SCOPE, DEFAULT_SCOPES, BillingCustomerBindingRequest,
                       BillingCustomerEffectSpec, EFFECT_CONFIRMED, EFFECT_NOT_ATTEMPTED, EFFECT_UNKNOWN,
                       ServiceRuntimeConfig, ServiceRuntimeError, SubjectBindingRequest,
                       TenantKeyIssue, TenantRegistration, SubjectTenantRegistration)
from .runtime import CUSTOMER_EFFECT, ServiceRuntime
from .storage import ServiceCatalogBinding

BILLING_TENANT, BILLING_ACCOUNT, METADATA_KEY = "billing", "acct_fixture", "loop_engine_tenant_id"


def billing_fixture(folder):
    """One account that may manage billing, with no provider customer yet."""
    runtime, _app, _key, _other, clock, _reads = fixture(folder)
    runtime.register_tenant(TenantRegistration(BILLING_TENANT, "billing-space",
                                               (*DEFAULT_SCOPES, BILLING_MANAGE_SCOPE)))
    key = runtime.issue_key(TenantKeyIssue(BILLING_TENANT, "explicit billing"))
    spec = BillingCustomerEffectSpec(BILLING_TENANT, BILLING_ACCOUNT, METADATA_KEY)
    return runtime, key, runtime.authenticate_key(key.key), spec, clock


def reserve(runtime, principal, spec, *, lease_seconds=10, reconciliation_seconds=100):
    return runtime.begin_billing_customer(principal, spec, lease_seconds=lease_seconds,
                                          reconciliation_seconds=reconciliation_seconds)


def binding(customer_id, tenant_id=BILLING_TENANT, account_id=BILLING_ACCOUNT):
    return BillingCustomerBindingRequest(tenant_id, customer_id, account_id)


def fixture(folder):
    config = ServiceRuntimeConfig(str(Path(folder) / "service.sqlite"), writes_authorized=True)
    clock = [1000]
    runtime = ServiceRuntime(config, clock=lambda: clock[0])
    runtime.register_tenant(TenantRegistration("tenant-a", "space-a"))
    runtime.register_tenant(TenantRegistration("tenant-b", "space-b"))
    key = runtime.issue_key(TenantKeyIssue("tenant-a", "local fixture"))
    other = runtime.issue_key(TenantKeyIssue("tenant-b", "other fixture"))
    runtime.set_operator_entitlement("tenant-a", valid_until=2000, evidence_ref="fixture:host-approval")
    item = item_from_body(HarnessIntelligenceDraft("skill.fixture", "skill", "Reviewed fixture",
        "context_intelligence", "context:fixture", "MIT"), "fixture body")
    catalogue = HarnessIntelligenceCatalogue()
    catalogue.register(item)
    binding = ProvisioningItemBinding.from_item(item)
    runtime.set_grants("tenant-a", (ProvisioningGrant("tenant-a", binding, True),))
    qualifier = ProvisioningQualificationResolver("fixture:review", lambda selected:
        ProvisioningQualification(selected, "approved", "host_attested", "fixture:review"))
    reads = []
    app = DurableProvisioningBinding(runtime, catalogue, qualifier,
        lambda item: reads.append(item.identity) or "fixture body")
    return runtime, app, key, other, clock, reads


def refused(action, code=None):
    try:
        action()
    except (ServiceRuntimeError, ProvisioningError, StoreError) as error:
        return code is None or getattr(error, "code", None) == code
    return False


def run_checks():
    tests = []
    def check(name, action):
        try:
            with TemporaryDirectory() as folder:
                result = bool(action(folder))
            detail = ""
        except Exception as error:
            result, detail = False, type(error).__name__ + ": " + str(error)
        tests.append({"test": name, "passed": result, "detail": detail})

    def account_creation(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        request = SubjectTenantRegistration('https://identity.example', 'verified-subject', 'customers')
        first = runtime.ensure_subject_tenant(request)
        reopened = ServiceRuntime(runtime.config, clock=lambda: 1000)
        second = reopened.ensure_subject_tenant(request)
        principal = reopened.authenticate_subject(request.issuer, request.subject)
        return (first['created'] and not second['created'] and first['tenant_id'] == second['tenant_id']
                and principal.entitlement == 'metadata' and principal.namespace == request.namespace
                and 'access:manage' not in principal.scopes)
    check('verified_subject_account_creation_is_atomic_durable_and_not_a_subscription', account_creation)

    def revoked_account(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        request = SubjectTenantRegistration('https://identity.example', 'verified-subject', 'customers')
        runtime.ensure_subject_tenant(request)
        runtime.revoke_subject(SubjectBindingRequest(request.tenant_id, request.issuer, request.subject))
        return refused(lambda: runtime.ensure_subject_tenant(request), 'unauthorized')
    check('repeat_account_activation_cannot_restore_a_revoked_subject', revoked_account)

    def disabled_account(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        request = SubjectTenantRegistration('https://identity.example', 'verified-subject', 'customers')
        runtime.ensure_subject_tenant(request); runtime.set_tenant_enabled(request.tenant_id, False)
        return refused(lambda: runtime.ensure_subject_tenant(request), 'unauthorized')
    check('repeat_account_activation_cannot_restore_a_disabled_tenant', disabled_account)

    def account_policy(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        request = SubjectTenantRegistration('https://identity.example', 'verified-subject', 'customers', ('usage:read',))
        runtime.ensure_subject_tenant(request)
        runtime.ensure_subject_tenant(replace(request, scopes=(*DEFAULT_SCOPES, BILLING_MANAGE_SCOPE)))
        return (runtime.authenticate_subject(request.issuer, request.subject).scopes == ('usage:read',)
                and refused(lambda: replace(request, scopes=('access:manage',)), 'automatic_administration_forbidden'))
    check('changed_bootstrap_preferences_cannot_expand_existing_account_authority', account_policy)

    def separate_issuers(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        left = SubjectTenantRegistration('https://first.example', 'same-subject', 'customers')
        right = replace(left, issuer='https://second.example')
        runtime.ensure_subject_tenant(left); runtime.ensure_subject_tenant(right)
        return left.tenant_id != right.tenant_id and left.namespace != right.namespace
    check('subject_identity_includes_the_verified_issuer', separate_issuers)

    def account_unknown(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        request = SubjectTenantRegistration('https://identity.example', 'verified-subject', 'customers')
        real = runtime._catalog.commit
        from unittest.mock import patch
        from .records import ServiceCommitUnknown
        def unknown(*args):
            real(*args)
            raise ServiceCommitUnknown()
        with patch.object(ServiceCatalogBinding, 'commit', staticmethod(unknown)):
            first_unknown = refused(lambda: runtime.ensure_subject_tenant(request), 'commit_unknown')
        result = runtime.ensure_subject_tenant(request)
        return first_unknown and result['committed'] is True and result['created'] is False
    check('unknown_account_commit_reconciles_the_same_identity_without_duplicate_creation', account_unknown)

    def durable(folder):
        runtime, _, key, _, _, _ = fixture(folder)
        reopened = ServiceRuntime(runtime.config, clock=lambda: 1000)
        principal = reopened.authenticate_key(key.key)
        return (principal.tenant_id == "tenant-a" and principal.entitlement == "bodies"
                and key.key not in repr(key) and key.key.encode() not in Path(runtime.config.database_path).read_bytes())
    check("tenant_key_entitlement_survive_reopen_without_plaintext_keys", durable)

    def billing_scope(folder):
        runtime, _, key, _, _, _ = fixture(folder)
        runtime.bind_billing_customer(BillingCustomerBindingRequest("tenant-a", "cus_a", "acct_a"))
        refused_default = refused(lambda: runtime.billing_customer_for(runtime.authenticate_key(key.key)), "scope_required")
        runtime.register_tenant(TenantRegistration("billing", "billing-space", (*DEFAULT_SCOPES, BILLING_MANAGE_SCOPE)))
        runtime.bind_billing_customer(BillingCustomerBindingRequest("billing", "cus_b", "acct_b"))
        billing_key = runtime.issue_key(TenantKeyIssue("billing", "explicit billing"))
        mapping = runtime.billing_customer_for(runtime.authenticate_key(billing_key.key))
        return (refused_default and BILLING_MANAGE_SCOPE not in DEFAULT_SCOPES
                and mapping["provider_account_id"] == "acct_b" and mapping["provider_customer_id"] == "cus_b")
    check("billing_customer_resolution_requires_explicit_non_default_scope", billing_scope)

    def customer_effect_identity(folder):
        runtime, _key, principal, spec, clock = billing_fixture(folder)
        first = reserve(runtime, principal, spec)
        running = refused(lambda: reserve(runtime, principal, spec), "billing_customer_creation_in_progress")
        runtime.finish_billing_customer(first, attempted=True, diagnostic_code="fixture_lost_answer")
        second = reserve(runtime, principal, spec)
        reopened = ServiceRuntime(runtime.config, clock=lambda: clock[0])
        with reopened._catalog.store() as store:
            stored = reopened._catalog.rows(store, CUSTOMER_EFFECT, BILLING_TENANT)
        return (running and second.record_id == first.record_id and second.attempt_number == 2
                and second.idempotency_key == first.idempotency_key and second.idempotency_cycles == 0
                and len(stored) == 1 and stored[0]["attributes"]["tenant_id"] == BILLING_TENANT
                and stored[0]["payload"]["diagnostic_code"] == "fixture_lost_answer")
    check("one_account_keeps_one_durable_customer_creation_identity_across_attempts", customer_effect_identity)

    def customer_effect_window(folder):
        runtime, _key, principal, spec, clock = billing_fixture(folder)
        first = reserve(runtime, principal, spec)
        runtime.finish_billing_customer(first, attempted=True, diagnostic_code="fixture_lost_answer")
        clock[0] += 101
        later = reserve(runtime, principal, spec)
        return (later.record_id == first.record_id and later.idempotency_cycles == 1
                and later.idempotency_key != first.idempotency_key
                and refused(lambda: runtime.bind_billing_customer(binding("cus_stale"), reservation=first),
                            "billing_customer_reservation_changed"))
    check("an_exhausted_reconciliation_window_takes_a_new_provider_idempotency_key", customer_effect_window)

    def customer_effect_allowance(folder):
        runtime, _key, principal, spec, _clock = billing_fixture(folder)
        return (refused(lambda: reserve(runtime, principal, spec, lease_seconds=100, reconciliation_seconds=100),
                        "invalid_billing_customer_effect_allowance")
                and refused(lambda: reserve(runtime, principal, spec, reconciliation_seconds=24 * 3600),
                            "invalid_billing_customer_effect_allowance")
                and refused(lambda: runtime.begin_billing_customer(principal, "not a spec", lease_seconds=10,
                            reconciliation_seconds=100), "invalid_billing_customer_effect"))
    check("customer_creation_refuses_an_allowance_beyond_the_provider_key_retention", customer_effect_allowance)

    def customer_effect_scope(folder):
        runtime, key, principal, spec, _clock = billing_fixture(folder)
        narrow = runtime.issue_key(TenantKeyIssue(BILLING_TENANT, "metadata only", scopes=DEFAULT_SCOPES))
        other_account = runtime.authenticate_key(key.key)
        return (BILLING_MANAGE_SCOPE not in DEFAULT_SCOPES
                and refused(lambda: reserve(runtime, runtime.authenticate_key(narrow.key), spec), "scope_required")
                and refused(lambda: reserve(runtime, other_account, replace(spec, tenant_id="tenant-a")),
                            "scope_required")
                and refused(lambda: runtime.authorize_billing_customer_dispatch(
                    runtime.authenticate_key(narrow.key), reserve(runtime, principal, spec)), "scope_required"))
    check("customer_creation_requires_the_explicit_billing_scope_for_its_own_account", customer_effect_scope)

    def customer_reservation_forgery(folder):
        runtime, _key, principal, spec, clock = billing_fixture(folder)
        reservation = reserve(runtime, principal, spec)
        separate = ServiceRuntime(runtime.config, clock=lambda: clock[0])
        other_spec = replace(spec, tenant_id="tenant-a")
        return (refused(lambda: runtime.bind_billing_customer(binding("cus_one"),
                    reservation=replace(reservation, idempotency_key="le-customer-forged")),
                    "unissued_billing_customer_reservation")
                and refused(lambda: runtime.bind_billing_customer(binding("cus_one"),
                    reservation=replace(reservation, authority_guards=())),
                    "unissued_billing_customer_reservation")
                and refused(lambda: separate.bind_billing_customer(binding("cus_one"), reservation=reservation),
                            "unissued_billing_customer_reservation")
                and refused(lambda: runtime.bind_billing_customer(binding("cus_one"),
                    reservation=replace(reservation, spec=other_spec)), "invalid_billing_customer_reservation")
                and refused(lambda: runtime.billing_customer_for(principal), "billing_customer_not_bound"))
    check("a_customer_binding_cannot_be_committed_with_a_forged_or_borrowed_reservation", customer_reservation_forgery)

    def customer_binding_is_final(folder):
        runtime, _key, principal, spec, _clock = billing_fixture(folder)
        reservation = reserve(runtime, principal, spec)
        runtime.bind_billing_customer(binding("cus_one"), reservation=reservation)
        with runtime._catalog.store() as store:
            effect = runtime._catalog.rows(store, CUSTOMER_EFFECT, BILLING_TENANT)[0]["payload"]
        return (effect["status"] == EFFECT_CONFIRMED and effect["provider_customer_id"] == "cus_one"
                and refused(lambda: runtime.bind_billing_customer(binding("cus_two")),
                            "billing_customer_already_bound")
                and refused(lambda: reserve(runtime, principal, spec), "billing_customer_already_bound")
                and runtime.billing_customer_for(principal)["provider_customer_id"] == "cus_one")
    check("a_bound_account_refuses_a_second_customer_and_a_further_creation", customer_binding_is_final)

    def customer_authority_changed(folder):
        runtime, key, principal, spec, _clock = billing_fixture(folder)
        reservation = reserve(runtime, principal, spec)
        runtime.revoke_key(BILLING_TENANT, key.key_id)
        return (refused(lambda: runtime.authorize_billing_customer_dispatch(principal, reservation), "unauthorized")
                and refused(lambda: runtime.bind_billing_customer(binding("cus_one"), reservation=reservation),
                            "billing_customer_authority_changed")
                and refused(lambda: runtime.billing_customer_for(principal), "unauthorized"))
    check("authority_removed_during_a_reserved_creation_prevents_the_binding", customer_authority_changed)

    def customer_effect_unknown_commit(folder):
        from unittest.mock import patch
        from .records import ServiceCommitUnknown
        runtime, _key, principal, spec, _clock = billing_fixture(folder)
        with patch.object(ServiceCatalogBinding, "commit", staticmethod(lambda *args: (_ for _ in ()).throw(ServiceCommitUnknown()))):
            blocked = refused(lambda: reserve(runtime, principal, spec), "commit_unknown")
        with runtime._catalog.store() as store:
            stored = runtime._catalog.rows(store, CUSTOMER_EFFECT, BILLING_TENANT)
        return blocked and not stored
    check("an_unknown_reservation_commit_is_not_a_reserved_creation", customer_effect_unknown_commit)

    def customer_effect_outcomes(folder):
        runtime, _key, principal, spec, _clock = billing_fixture(folder)
        first = reserve(runtime, principal, spec)
        not_attempted = runtime.finish_billing_customer(first, attempted=False, diagnostic_code="not_dispatched")
        second = reserve(runtime, principal, spec)
        unknown = runtime.finish_billing_customer(second, attempted=True, diagnostic_code="provider_commit_unknown")
        return (not_attempted["status"] == EFFECT_NOT_ATTEMPTED and unknown["status"] == EFFECT_UNKNOWN
                and not_attempted["effect_ref"] == unknown["effect_ref"]
                and refused(lambda: runtime.finish_billing_customer(second, attempted="yes"),
                            "invalid_effect_outcome"))
    check("an_attempted_and_a_not_attempted_customer_creation_are_separate_outcomes", customer_effect_outcomes)

    def billing_effect_vocabulary(folder):
        from . import billing_effects
        from . import records as service_records
        return all(getattr(billing_effects, name) == getattr(service_records, name) for name in (
            "EFFECT_PENDING", "EFFECT_CONFIRMED", "EFFECT_UNKNOWN", "EFFECT_NOT_ATTEMPTED",
            "PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS"))
    check("the_session_and_customer_effects_share_one_status_vocabulary", billing_effect_vocabulary)

    def host_authority(folder):
        path = Path(folder) / "absent.sqlite"
        runtime = ServiceRuntime(ServiceRuntimeConfig(str(path)))
        return refused(lambda: runtime.register_tenant(TenantRegistration("x", "x")), "host_write_authority_required") and not path.exists()
    check("absent_host_write_authority_creates_no_database", host_authority)

    def duplicate_namespace(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        rejected = refused(lambda: runtime.register_tenant(TenantRegistration("tenant-c", "space-a")), "concurrent_update")
        with runtime._catalog.store() as store:
            absent = runtime._catalog.read(store, "service_tenant", "tenant-c") is None
        return rejected and absent
    check("tenant_namespace_collision_rolls_back_the_whole_registration", duplicate_namespace)

    def key_revocation(folder):
        runtime, app, key, _, _, reads = fixture(folder)
        principal = runtime.authenticate_key(key.key)
        runtime.revoke_key("tenant-a", key.key_id)
        return (refused(lambda: runtime.authenticate_key(key.key), "unauthorized")
                and refused(lambda: app.invoke_for_principal(principal, "read", identity="skill.fixture", request_id="read"))
                and not reads)
    check("key_revocation_invalidates_previously_issued_principals", key_revocation)

    def expires(folder):
        runtime, app, _, _, clock, reads = fixture(folder)
        key = runtime.issue_key(TenantKeyIssue("tenant-a", "short", expires_at=1001))
        principal = runtime.authenticate_key(key.key)
        clock[0] = 1001
        return refused(lambda: app.invoke_for_principal(principal, "read", identity="skill.fixture", request_id="read")) and not reads
    check("expiry_is_checked_at_use_not_only_key_issue", expires)

    def scope_narrowing(folder):
        runtime, app, _, _, _, reads = fixture(folder)
        key = runtime.issue_key(TenantKeyIssue("tenant-a", "metadata", scopes=("provisioning:metadata",)))
        listing = app.invoke(key.key, "list")
        return (len(listing["items"]) == 1 and listing["items"][0]["body_allowed"] is False
                and app.invoke(key.key, "discover")["bodies_available"] is False
                and refused(lambda: app.invoke(key.key, "read", identity="skill.fixture", request_id="read"), "scope_required")
                and not reads)
    check("key_scopes_cannot_become_body_authority", scope_narrowing)

    def read_only_profile(folder):
        runtime, app, key, _, _, reads = fixture(folder)
        read_only = ServiceRuntime(replace(runtime.config, writes_authorized=False), clock=lambda: 1000)
        app.runtime = read_only
        listed = app.invoke(key.key, "list")
        hidden = (listed["items"][0]["body_allowed"] is False
                  and app.invoke(key.key, "discover")["bodies_available"] is False
                  and refused(lambda: app.invoke(key.key, "read", identity="skill.fixture", request_id="read"))
                  and not reads)
        grants, _ = runtime.grant_snapshot(runtime.authenticate_key(key.key))
        runtime.set_grants("tenant-a", tuple(replace(grant, metering="unmetered") for grant in grants))
        result = app.invoke(key.key, "read", identity="skill.fixture", request_id="unmetered")
        return hidden and result["body"] == "fixture body" and result["metered"] is False
    check("read_only_service_hides_required_metering_but_preserves_explicit_unmetered_grants", read_only_profile)

    def forged(folder):
        runtime, _, key, _, _, _ = fixture(folder)
        principal = runtime.authenticate_key(key.key)
        return (refused(lambda: runtime.revalidate(replace(principal, tenant_id="tenant-b")), "unissued_principal")
                and refused(lambda: runtime.revalidate(replace(principal, scopes=())), "unissued_principal"))
    check("mutated_principals_do_not_inherit_issued_authentication", forged)

    def subject_mapping(folder):
        runtime, _, _, _, _, _ = fixture(folder)
        request = SubjectBindingRequest("tenant-a", "https://issuer.example", "subject-a")
        runtime.bind_subject(request)
        principal = runtime.authenticate_subject(request.issuer, request.subject)
        unknown = refused(lambda: runtime.authenticate_subject("https://other.example", request.subject), "unauthorized")
        runtime.revoke_subject(request)
        return principal.tenant_id == "tenant-a" and unknown and refused(lambda: runtime.revalidate(principal), "unauthorized")
    check("external_subject_mapping_is_exact_durable_and_revocable", subject_mapping)

    def tenant_disabled(folder):
        runtime, app, key, _, _, reads = fixture(folder)
        runtime.set_tenant_enabled("tenant-a", False)
        return refused(lambda: app.invoke(key.key, "discover"), "unauthorized") and not reads
    check("disabled_tenant_cannot_discover_or_read", tenant_disabled)

    def cross_tenant(folder):
        runtime, app, key, other, _, reads = fixture(folder)
        return (app.invoke(other.key, "list")["items"] == []
                and refused(lambda: app.invoke(other.key, "read", identity="skill.fixture", request_id="read"))
                and runtime.usage_for(runtime.authenticate_key(other.key))["records"] == 0 and not reads)
    check("cross_tenant_body_and_usage_are_scoped", cross_tenant)

    def selected_digest(folder):
        _, app, key, _, _, reads = fixture(folder)
        return refused(lambda: app.invoke(key.key, "read", identity="skill.fixture", request_id="read", expected_digest="f" * 64)) and not reads
    check("selected_body_digest_mismatch_refuses_before_read_or_meter", selected_digest)

    def meter(folder):
        runtime, app, key, _, _, _ = fixture(folder)
        one = app.invoke(key.key, "read", identity="skill.fixture", request_id="same")
        two = app.invoke(key.key, "read", identity="skill.fixture", request_id="same")
        reopened = ServiceRuntime(runtime.config, clock=lambda: 1000)
        usage = reopened.usage_for(reopened.authenticate_key(key.key))
        return (one["metering_acknowledgment"] == two["metering_acknowledgment"]
                and one["metering_acknowledgment"]["durability"] == "durable" and usage["records"] == 1)
    check("exact_body_retry_has_one_durable_usage_record_after_restart", meter)

    def changed_usage(folder):
        from ..provisioning_server import ProvisioningMeterRequest
        runtime, app, key, _, _, _ = fixture(folder)
        app.invoke(key.key, "read", identity="skill.fixture", request_id="same")
        binding = ProvisioningItemBinding.from_item(app.catalogue.items["skill.fixture"])
        request = ProvisioningMeterRequest("tenant-a", "same", replace(binding, body_digest="f" * 64))
        return refused(lambda: runtime.record_usage(request, runtime.authenticate_key(key.key)), "usage_identity_conflict")
    check("idempotency_identity_cannot_cover_a_changed_body", changed_usage)

    def during_read(folder, change):
        runtime, app, key, _, _, reads = fixture(folder)
        def reader(item):
            change(runtime, key)
            reads.append(item.identity)
            return "fixture body"
        app.body_reader = reader
        rejected = refused(lambda: app.invoke(key.key, "read", identity="skill.fixture", request_id="read"))
        with runtime._catalog.store() as store:
            usage = runtime._catalog.rows(store, "service_usage", "tenant-a")
        return rejected and not usage and reads == ["skill.fixture"]
    check("key_revocation_during_body_read_prevents_meter_and_delivery",
          lambda folder: during_read(folder, lambda runtime, key: runtime.revoke_key("tenant-a", key.key_id)))
    check("grant_revocation_during_body_read_prevents_meter_and_delivery",
          lambda folder: during_read(folder, lambda runtime, key: runtime.set_grants("tenant-a", ())))
    check("entitlement_revocation_during_body_read_prevents_meter_and_delivery",
          lambda folder: during_read(folder, lambda runtime, key: runtime.revoke_entitlement("tenant-a")))

    def unknown_commit(folder):
        runtime, app, key, _, _, _ = fixture(folder)
        class LostAcknowledgment:
            def __init__(self, write):
                self.store = SQLiteRecordStore(runtime.config.database_path, read_only=not write)
            def __getattr__(self, name):
                return getattr(self.store, name)
            def apply_batch(self, request):
                self.store.apply_batch(request)
                return CatalogBatchAcknowledgment(request.digest, None)
        uncertain = ServiceRuntime(runtime.config, storage=ServiceCatalogBinding(runtime.config, LostAcknowledgment), clock=lambda: 1000)
        app.runtime = uncertain
        first = refused(lambda: app.invoke(key.key, "read", identity="skill.fixture", request_id="same"), "meter_commit_unknown")
        app.runtime = runtime
        second = app.invoke(key.key, "read", identity="skill.fixture", request_id="same")
        return first and second["metered"] and runtime.usage_for(runtime.authenticate_key(key.key))["records"] == 1
    check("unknown_commit_is_not_success_and_exact_retry_reconciles_once", unknown_commit)

    def concurrent_usage(folder):
        runtime, app, key, _, _, _ = fixture(folder)
        def reader(_):
            try:
                return app.invoke(key.key, "read", identity="skill.fixture", request_id="concurrent")["metered"]
            except (ServiceRuntimeError, ProvisioningError):
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(reader, range(12)))
        final = app.invoke(key.key, "read", identity="skill.fixture", request_id="concurrent")
        return any(outcomes) and final["metered"] and runtime.usage_for(runtime.authenticate_key(key.key))["records"] == 1
    check("separate_connections_concurrent_retries_do_not_double_meter", concurrent_usage)

    def atomic_conflict(folder):
        store = SQLiteRecordStore(str(Path(folder) / "batch.sqlite"))
        first = {"record_id": "head", "record_version": "1"}
        store.put(first)
        request = CatalogWriteBatch.from_records(({"record_id": "new", "record_version": "1"},
                                                  {"record_id": "head", "record_version": "2"}),
            (CatalogRecordPrecondition("new", must_not_exist=True), CatalogRecordPrecondition("head", "stale")))
        blocked = refused(lambda: store.apply_batch(request))
        result = blocked and store.get("new") is None and store.get("head")["record_version"] == "1"
        store.close()
        return result
    check("atomic_batch_conflict_writes_nothing", atomic_conflict)

    def transaction_rollback(folder):
        store = SQLiteRecordStore(str(Path(folder) / "batch.sqlite"))
        request = CatalogWriteBatch.from_records(tuple({"record_id": value, "record_version": "1"} for value in ("a", "b")),
            tuple(CatalogRecordPrecondition(value, must_not_exist=True) for value in ("a", "b")))
        original = store._write_values
        def fail_second(values):
            if values[0] == "b":
                raise StoreError("fixture failure")
            original(values)
        store._write_values = fail_second
        blocked = refused(lambda: store.apply_batch(request))
        result = blocked and store.get("a") is None and store.get("b") is None
        store.close()
        return result
    check("atomic_batch_mid_write_failure_rolls_back_all_rows", transaction_rollback)

    def batch_concurrent(folder):
        path = str(Path(folder) / "batch.sqlite")
        initial = SQLiteRecordStore(path)
        initial.put({"record_id": "head", "record_version": "1"})
        initial.close()
        barrier = threading.Barrier(2)
        def worker(index):
            store = SQLiteRecordStore(path)
            observed = store.get("head")
            barrier.wait(timeout=5)
            request = CatalogWriteBatch.from_records(({"record_id": "head", "record_version": str(index + 2)},),
                (CatalogRecordPrecondition("head", observed["record_version"]),))
            try:
                return store.apply_batch(request).committed is True
            except PreconditionFailed:
                return False
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return sum(pool.map(worker, range(2))) == 1
    check("atomic_read_set_serializes_two_competing_writers", batch_concurrent)

    def batch_contract(folder):
        record = {"record_id": "one", "record_version": "1", "payload": {"value": "original"}}
        request = CatalogWriteBatch.from_records((record,), (CatalogRecordPrecondition("one", must_not_exist=True),))
        record["payload"]["value"] = "changed"
        return (request.records[0]["payload"]["value"] == "original"
                and refused(lambda: require_atomic_batch(EphemeralRecordStore()))
                and refused(lambda: CatalogRecordPrecondition("one", "1", True))
                and refused(lambda: CatalogWriteBatch.from_records((record,), (CatalogRecordPrecondition("one", "1"),))))
    check("batch_snapshot_and_exact_optional_contract_refuse_ambiguous_adapters", batch_contract)

    def boundaries(folder):
        root = Path(__file__).parent
        for name in ("records.py", "runtime.py", "storage.py", "provisioning.py", "billing.py",
                     "billing_records.py", "stripe_provider.py"):
            tree = ast.parse((root / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(alias.name.split(".")[0] in ("sqlite3", "duckdb", "httpx", "fastapi") for alias in node.names):
                        return False
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module.startswith(("http", "loop_engine_devtools")):
                        return False
        return (root / "README.md").is_file()
    check("service_domain_uses_catalog_authority_without_transport_or_database_inversion", boundaries)

    passed = sum(row["passed"] for row in tests)
    return {"record_type": "service_runtime_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
