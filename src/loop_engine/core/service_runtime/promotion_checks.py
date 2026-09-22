"""Real SQLite checks for promotion codes and for the comped access they grant.

Every check here uses the durable catalogue, a real temporary database and the
issued-principal path. No provider is called and no fixture is represented as a
payment. The transport-level checks live in `promotion_http_checks` alongside
them, and the HTTP suite runs those where its optional dependencies are declared.

Each refusal this module asserts is a known-wrong case: the code under test must
reject the thing the guard exists to prevent, and the exact reason is compared,
not only the fact that something was refused.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import threading

from ...catalog.stores.sqlite_store import SQLiteRecordStore
from .billing_records import StripeEntitlementPolicy
from .promotions import (ABSENT_CODE, ALREADY_REDEEMED, CODE_UNUSABLE, PAID_ACCESS_ACTIVE, REDEMPTION_FORBIDDEN,
                         REDEMPTION_UNAVAILABLE, ACCOUNT_REQUIRED, REASON_ALREADY_REDEEMED, REASON_EXHAUSTED,
                         REASON_EXPIRED, REASON_NOT_AUTHENTICATED, REASON_NOT_INSTALLED, REASON_NOT_STARTED,
                         REASON_PAID_SUBSCRIPTION, REASON_ACCESS_REVOKED, REASON_SUSPENDED, REASON_UNKNOWN_CODE,
                         PromotionCodeAdministration, PromotionCodeDefinition, PromotionGrant, PromotionPolicy,
                         PromotionRedemption, PromotionRedemptionRequest, PromotionRefused, NO_REFUSAL,
                         promotion_code_state)
from .records import ServiceRuntimeConfig, ServiceRuntimeError, TenantKeyIssue, TenantRegistration
from .runtime import (CODE_GRANT_SOURCE, ENTITLEMENT, HOST_GRANT_SOURCE, PROMOTION_CODE,
                      SCHEMAS, STRIPE_SNAPSHOT_SOURCE, TENANT, ServiceRuntime)
from .storage import ServiceCatalogBinding

#: Fixture codes are composed from a prefix and a separate body, so no whole
#: credential-shaped value is written into this file.
PREFIX = "BALTOR"
FIRST_BODY, SECOND_BODY, GUESSED_BODY = "AAAA-BBBB", "CCCC-DDDD", "ZZZZ-YYYY"
DAY = 24 * 3600


def fixture(folder, *, tenants=("account-a", "account-b"), redemption_enabled=True, storage=None):
    """One database, two accounts with keys, and the two promotion surfaces."""
    config = ServiceRuntimeConfig(str(Path(folder) / "service.sqlite"), writes_authorized=True)
    clock = [1_000_000]
    runtime = ServiceRuntime(config, storage=storage(config) if storage else None, clock=lambda: clock[0])
    keys = {}
    for tenant in tenants:
        runtime.register_tenant(TenantRegistration(tenant, "space:" + tenant))
        keys[tenant] = runtime.issue_key(TenantKeyIssue(tenant, "promotion fixture"))
    return (runtime, clock, keys, PromotionCodeAdministration(runtime),
            PromotionRedemption(runtime, PromotionPolicy(redemption_enabled=redemption_enabled)))


def definition(clock, body, **changes):
    settings = {"label": "invited beta", "grant": PromotionGrant(), "redemptions_allowed": 5,
                "repeat_allowed_for_one_account": False, "starts_at": clock[0] - 10,
                "expires_at": clock[0] + DAY, "approved_by": "reviewer.one",
                "approval_ref": "review:promotion-1"}
    settings.update(changes)
    settings.setdefault("code", PREFIX + "-" + body)
    return PromotionCodeDefinition(**settings)


def created(administration, clock, body, **changes):
    chosen = definition(clock, body, **changes)
    return chosen, administration.create(chosen, confirmed=True)


def offer(chosen, request_id):
    return PromotionRedemptionRequest(code=chosen.code, request_id=request_id)


def refusal(action):
    """Return the raised promotion refusal, or None when nothing was refused."""
    try:
        action()
    except PromotionRefused as error:
        return error
    return None


def refused(action, code=None):
    try:
        action()
    except ServiceRuntimeError as error:
        return code is None or error.code == code
    return False


def principal_for(runtime, keys, tenant):
    return runtime.authenticate_key(keys[tenant].key)


def _paying_account(runtime, tenant_id, clock, price="price_fixture_pro"):
    """Write the entitlement shape the billing webhook writes for a payment.

    The classification under test is the recorded source, so the fixture writes
    that record directly. It is not a provider call and proves nothing about
    Stripe; the webhook path has its own checks in `billing_checks`.
    """
    from .records import digest
    policy = StripeEntitlementPolicy((price,))
    runtime.configure_billing_policy(policy)
    catalog = runtime._catalog
    with catalog.store(write=True) as store:
        previous = catalog.read(store, ENTITLEMENT, tenant_id)
        row = catalog.record(ENTITLEMENT, tenant_id, {"record_type": SCHEMAS[ENTITLEMENT],
            "tenant_id": tenant_id, "enabled": True, "entitlement": "bodies",
            "valid_until": clock[0] + 30 * DAY, "source": STRIPE_SNAPSHOT_SOURCE,
            "policy_digest": digest(asdict(policy)), "event_id": "evt_fixture",
            "subscription_ids": ["sub_fixture"]}, tenant_id=tenant_id)
        catalog.commit(store, (row,), (catalog.guard(previous, row["record_id"]),))


def _counting_storage(counts):
    """A catalogue binding that records every read the store is asked for."""
    def bind(config):
        class Counted:
            def __init__(self, write):
                self.store = SQLiteRecordStore(config.database_path, read_only=not write)

            def __getattr__(self, name):
                return getattr(self.store, name)

            def get(self, identity):
                counts.append(("get", identity))
                return self.store.get(identity)

            def query(self, request):
                counts.append(("query", request.artifact_kinds))
                return self.store.query(request)
        return ServiceCatalogBinding(config, Counted)
    return bind


def run_checks():
    tests = []

    def check(name, action):
        try:
            with TemporaryDirectory(prefix="service-promotions-") as folder:
                result = bool(action(folder))
            detail = "real SQLite records; no provider call"
        except Exception as error:
            result, detail = False, type(error).__name__ + ": " + str(error)
        tests.append({"test": name, "passed": result, "detail": detail})

    def text_decides_nothing(folder):
        runtime, clock, keys, administration, redemption = fixture(
            folder, tenants=("one", "two", "three", "four"))
        # The text and the label of each code name a period the record does not
        # grant, and the last two codes carry the same label with different
        # grants. Any rule that read a period out of either text would answer
        # the same for both of them, or answer the period the text names.
        loud, _ = created(administration, clock, "FREE-FOREVER-LIFETIME",
                          grant=PromotionGrant(seconds=60 * DAY), label="one week only")
        quiet, _ = created(administration, clock, "TINY-TRIAL-ONE-HOUR",
                           grant=PromotionGrant(seconds=7 * DAY), label="sixty days of everything")
        twin_short, _ = created(administration, clock, "SAME-LABEL-FIRST",
                                grant=PromotionGrant(seconds=7 * DAY), label="invited beta")
        twin_long, _ = created(administration, clock, "SAME-LABEL-SECOND",
                               grant=PromotionGrant(seconds=60 * DAY), label="invited beta")
        given = [redemption.redeem(principal_for(runtime, keys, tenant), offer(chosen, "r-" + tenant))
                 for tenant, chosen in (("one", loud), ("two", quiet),
                                        ("three", twin_short), ("four", twin_long))]
        return ([row["valid_until"] - clock[0] for row in given]
                == [60 * DAY, 7 * DAY, 7 * DAY, 60 * DAY]
                and given[2]["label"] == given[3]["label"]
                and given[2]["valid_until"] != given[3]["valid_until"]
                and all(row["entitlement"] == "bodies" for row in given))
    check("a_codes_text_never_decides_what_it_grants", text_decides_nothing)

    def grants_through_the_entitlement_path(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, record = created(administration, clock, FIRST_BODY)
        before = principal_for(runtime, keys, "account-a").entitlement
        result = redemption.redeem(principal_for(runtime, keys, "account-a"), offer(chosen, "r1"))
        reopened = ServiceRuntime(runtime.config, clock=lambda: clock[0])
        after = reopened.authenticate_key(keys["account-a"].key)
        with reopened._catalog.store() as store:
            stored = reopened._catalog.read(store, ENTITLEMENT, "account-a")["payload"]
        return (before == "metadata" and after.entitlement == "bodies"
                and result["source"] == CODE_GRANT_SOURCE and result["payment"] is False
                and stored["source"] == CODE_GRANT_SOURCE
                and stored["promotion_code_id"] == record["code_id"]
                and stored["approval_ref"] == "review:promotion-1"
                and stored["approved_by"] == "reviewer.one"
                and "subscription_ids" not in stored and "policy_digest" not in stored)
    check("redeeming_a_code_grants_the_declared_entitlement_as_a_code_grant_not_a_payment",
          grants_through_the_entitlement_path)

    def one_request_spends_one_redemption(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, _ = created(administration, clock, FIRST_BODY)
        principal = principal_for(runtime, keys, "account-a")
        first = redemption.redeem(principal, offer(chosen, "same-request"))
        again = redemption.redeem(principal, offer(chosen, "same-request"))
        with runtime._catalog.store() as store:
            used = runtime._catalog.read(store, PROMOTION_CODE, chosen.digest)["payload"]["redemptions_used"]
        return (first["replayed"] is False and again["replayed"] is True and used == 1
                and again["valid_until"] == first["valid_until"]
                and again["promotion_code_id"] == first["promotion_code_id"])
    check("a_repeated_redemption_request_spends_one_redemption", one_request_spends_one_redemption)

    def changed_request_identity(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        first, _ = created(administration, clock, FIRST_BODY)
        second, _ = created(administration, clock, SECOND_BODY)
        principal = principal_for(runtime, keys, "account-a")
        redemption.redeem(principal, offer(first, "same-request"))
        return refused(lambda: redemption.redeem(principal, offer(second, "same-request")),
                       "promotion_request_identity_conflict")
    check("one_request_identity_cannot_cover_a_different_code", changed_request_identity)

    def last_redemption_race(folder):
        runtime, clock, keys, administration, _redemption = fixture(folder)
        chosen, _ = created(administration, clock, FIRST_BODY, redemptions_allowed=1)
        barrier = threading.Barrier(2)

        def attempt(tenant):
            separate = ServiceRuntime(runtime.config, clock=lambda: clock[0])
            principal = separate.authenticate_key(keys[tenant].key)
            redeemer = PromotionRedemption(separate, PromotionPolicy(redemption_enabled=True))
            barrier.wait(timeout=5)
            try:
                return redeemer.redeem(principal, offer(chosen, "race-" + tenant))["granted"]
            except ServiceRuntimeError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, ("account-a", "account-b")))
        reopened = ServiceRuntime(runtime.config, clock=lambda: clock[0])
        with reopened._catalog.store() as store:
            code = reopened._catalog.read(store, PROMOTION_CODE, chosen.digest)["payload"]
        holders = [tenant for tenant in ("account-a", "account-b")
                   if reopened.authenticate_key(keys[tenant].key).entitlement == "bodies"]
        return (sum(outcomes) == 1 and code["redemptions_used"] == 1
                and code["redemptions_used"] <= code["redemptions_allowed"] and len(holders) == 1)
    check("two_accounts_cannot_both_take_the_last_remaining_redemption", last_redemption_race)

    def count_never_passes_the_allowance(folder):
        """Known-wrong case for the write boundary: a state that wrongly permits.

        `promotion_code_state` is replaced by one that calls every code
        redeemable. That is exactly the mistake the last guard before the write
        exists to catch, so the redemption must still refuse and the durable
        count must stay where it was.
        """
        from unittest.mock import patch
        from . import promotions
        from .promotions import PromotionCodeState
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, _ = created(administration, clock, FIRST_BODY, redemptions_allowed=1,
                            repeat_allowed_for_one_account=True)
        principal = principal_for(runtime, keys, "account-a")
        redemption.redeem(principal, offer(chosen, "spend"))
        permissive = PromotionCodeState(known=True, suspended=False, not_started=False,
                                        expired=False, exhausted=False)
        with patch.object(promotions, "promotion_code_state", lambda payload, now: permissive):
            blocked = refusal(lambda: redemption.redeem(principal, offer(chosen, "over")))
        with runtime._catalog.store() as store:
            code = runtime._catalog.read(store, PROMOTION_CODE, chosen.digest)["payload"]
        return (permissive.redeemable is True and blocked is not None
                and blocked.reason == REASON_EXHAUSTED and blocked.code == CODE_UNUSABLE
                and code["redemptions_used"] == 1
                and code["redemptions_used"] <= code["redemptions_allowed"])
    check("a_committed_redemption_count_never_passes_the_allowance_even_when_the_state_permits_it",
          count_never_passes_the_allowance)

    def a_payment_that_lands_first_is_not_overwritten(folder):
        """Known-wrong case for the entitlement read set.

        A redemption reads the account's entitlement, decides the account does
        not pay, and then writes. A payment landing in that gap is exactly what
        the read-set guard exists to catch, so the commit must be refused and
        the payment must survive with its own source.
        """
        from unittest.mock import patch
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, _ = created(administration, clock, FIRST_BODY)
        principal = principal_for(runtime, keys, "account-a")
        webhook = ServiceRuntime(runtime.config, clock=lambda: clock[0])
        webhook.configure_billing_policy(StripeEntitlementPolicy(("price_fixture_pro",)))
        original, landed = ServiceCatalogBinding.commit, []

        def commit_after_a_payment_lands(self, store, records, guards):
            if not landed:
                landed.append(True)
                _paying_account(webhook, "account-a", clock)
            return original(self, store, records, guards)
        with patch.object(ServiceCatalogBinding, "commit", commit_after_a_payment_lands):
            refused_write = refused(lambda: redemption.redeem(principal, offer(chosen, "r1")),
                                    "concurrent_update")
        reopened = ServiceRuntime(runtime.config, clock=lambda: clock[0])
        with reopened._catalog.store() as store:
            stored = reopened._catalog.read(store, ENTITLEMENT, "account-a")["payload"]
            code = reopened._catalog.read(store, PROMOTION_CODE, chosen.digest)["payload"]
        return (bool(landed) and refused_write and stored["source"] == STRIPE_SNAPSHOT_SOURCE
                and "promotion_code_id" not in stored and code["redemptions_used"] == 0)
    check("a_payment_that_lands_during_a_redemption_is_never_overwritten_by_a_code_grant",
          a_payment_that_lands_first_is_not_overwritten)

    def unknown_and_exhausted_look_the_same(folder):
        counts = []
        runtime, clock, keys, administration, redemption = fixture(folder, storage=_counting_storage(counts))
        chosen, _ = created(administration, clock, FIRST_BODY, redemptions_allowed=1)
        redemption.redeem(principal_for(runtime, keys, "account-b"), offer(chosen, "spend"))
        principal = principal_for(runtime, keys, "account-a")
        guess = PromotionRedemptionRequest(code=PREFIX + "-" + GUESSED_BODY, request_id="guess")
        counts.clear()
        unknown = refusal(lambda: redemption.redeem(principal, guess))
        unknown_reads = list(counts)
        counts.clear()
        spent = refusal(lambda: redemption.redeem(principal, offer(chosen, "spent")))
        spent_reads = list(counts)
        # A refused attempt reads the per-account record as well, so moving that
        # read behind the refusal shortens both paths and fails this check.
        stand_in = runtime._catalog.identity("service_promotion_code_account", ("", "account-a"))
        return (unknown is not None and spent is not None
                and unknown.code == spent.code == CODE_UNUSABLE
                and str(unknown) == str(spent)
                and unknown.reason == REASON_UNKNOWN_CODE and spent.reason == REASON_EXHAUSTED
                and [kind for kind, _identity in unknown_reads] == [kind for kind, _identity in spent_reads]
                and len(unknown_reads) > 4
                and ("get", stand_in) in unknown_reads
                and ("get", runtime._catalog.identity("service_promotion_code", chosen.digest)) in spent_reads)
    check("an_unknown_code_and_an_exhausted_code_refuse_with_the_same_word_and_the_same_reads",
          unknown_and_exhausted_look_the_same)

    def code_state_reasons(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        principal = principal_for(runtime, keys, "account-a")
        unknown = refusal(lambda: redemption.redeem(principal, PromotionRedemptionRequest(
            code=PREFIX + "-" + GUESSED_BODY, request_id="a")))
        early, _ = created(administration, clock, "LATER-CODE-BODY", starts_at=clock[0] + DAY,
                           expires_at=clock[0] + 2 * DAY)
        not_started = refusal(lambda: redemption.redeem(principal, offer(early, "b")))
        old, old_record = created(administration, clock, "OLDER-CODE-BODY")
        administration.expire(old_record["code_id"], at=clock[0] - DAY)
        expired = refusal(lambda: redemption.redeem(principal, offer(old, "c")))
        spent, record = created(administration, clock, FIRST_BODY, redemptions_allowed=1)
        redemption.redeem(principal_for(runtime, keys, "account-b"), offer(spent, "d"))
        exhausted = refusal(lambda: redemption.redeem(principal, offer(spent, "e")))
        stopped, stopped_record = created(administration, clock, SECOND_BODY)
        administration.suspend(stopped_record["code_id"])
        suspended = refusal(lambda: redemption.redeem(principal, offer(stopped, "f")))
        seen = {"unknown": unknown, "not_started": not_started, "expired": expired,
                "exhausted": exhausted, "suspended": suspended}
        return (all(value is not None for value in seen.values())
                and {value.code for value in seen.values()} == {CODE_UNUSABLE}
                and [seen[name].reason for name in ("unknown", "not_started", "expired", "exhausted", "suspended")]
                == [REASON_UNKNOWN_CODE, REASON_NOT_STARTED, REASON_EXPIRED, REASON_EXHAUSTED, REASON_SUSPENDED]
                and record["code_id"] != stopped_record["code_id"])
    check("every_code_state_refusal_has_its_own_exact_reason_behind_one_disclosed_word", code_state_reasons)

    def account_reasons(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, _ = created(administration, clock, FIRST_BODY)
        principal = principal_for(runtime, keys, "account-a")
        redemption.redeem(principal, offer(chosen, "first"))
        repeated = refusal(lambda: redemption.redeem(principal, offer(chosen, "second")))
        _paying_account(runtime, "account-b", clock)
        paying = refusal(lambda: redemption.redeem(principal_for(runtime, keys, "account-b"),
                                                   offer(chosen, "paying")))
        runtime.revoke_entitlement("account-a")
        revoked = refusal(lambda: redemption.redeem(principal_for(runtime, keys, "account-a"),
                                                    offer(chosen, "revoked")))
        anonymous = refusal(lambda: redemption.redeem(None, offer(chosen, "anonymous")))
        closed = PromotionRedemption(runtime, PromotionPolicy(redemption_enabled=False))
        uninstalled = refusal(lambda: closed.redeem(principal, offer(chosen, "closed")))
        return ([(value.reason, value.code) for value in (repeated, paying, revoked, anonymous, uninstalled)]
                == [(REASON_ALREADY_REDEEMED, ALREADY_REDEEMED),
                    (REASON_PAID_SUBSCRIPTION, PAID_ACCESS_ACTIVE),
                    (REASON_ACCESS_REVOKED, REDEMPTION_FORBIDDEN),
                    (REASON_NOT_AUTHENTICATED, ACCOUNT_REQUIRED),
                    (REASON_NOT_INSTALLED, REDEMPTION_UNAVAILABLE)])
    check("every_account_refusal_names_its_own_reason_and_its_own_disclosed_word", account_reasons)

    def repeats_when_allowed(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, record = created(administration, clock, FIRST_BODY, repeat_allowed_for_one_account=True,
                                 redemptions_allowed=3)
        principal = principal_for(runtime, keys, "account-a")
        redemption.redeem(principal, offer(chosen, "one"))
        second = redemption.redeem(principal, offer(chosen, "two"))
        listing = administration.inspect()["codes"]
        selected = [row for row in listing if row["code_id"] == record["code_id"]][0]
        return (second["replayed"] is False and selected["redemptions_used"] == 2
                and selected["redeemed_by"] == ["account-a"])
    check("a_code_that_allows_repeats_can_be_redeemed_twice_by_one_account", repeats_when_allowed)

    def comped_is_not_revenue(folder):
        runtime, clock, keys, administration, redemption = fixture(
            folder, tenants=("paying", "code-comped", "host-comped"))
        chosen, _ = created(administration, clock, FIRST_BODY)
        _paying_account(runtime, "paying", clock)
        redemption.redeem(principal_for(runtime, keys, "code-comped"), offer(chosen, "r1"))
        runtime.set_operator_entitlement("host-comped", valid_until=clock[0] + DAY,
                                         evidence_ref="approval:invited-beta")
        report = runtime.access_source_report()
        rows = {row["tenant_id"]: row for row in report["accounts"]}
        return (report["revenue_bearing_tenants"] == ["paying"]
                and report["comped_tenants"] == ["code-comped", "host-comped"]
                and report["counts"]["revenue_bearing"] == 1 and report["counts"]["comped"] == 2
                and rows["code-comped"]["revenue_bearing"] is False
                and rows["code-comped"]["source"] == CODE_GRANT_SOURCE
                and rows["host-comped"]["source"] == HOST_GRANT_SOURCE
                and rows["paying"]["comped"] is False
                and rows["code-comped"]["subscription_ids"] == []
                and report["revenue_bearing_sources"] == [STRIPE_SNAPSHOT_SOURCE]
                and CODE_GRANT_SOURCE not in report["revenue_bearing_sources"]
                and all(tenant not in report["revenue_bearing_tenants"] for tenant in report["comped_tenants"]))
    check("a_comped_account_is_never_counted_as_revenue_in_the_access_source_report", comped_is_not_revenue)

    def unreadable_tenant_stops_the_report(folder):
        """Known-wrong case for the report's version check.

        A tenant record this release does not support must stop the report, not
        be reinterpreted. A report that guessed would count the account, and a
        miscounted account is the one thing this report exists to prevent.
        """
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, _ = created(administration, clock, FIRST_BODY)
        redemption.redeem(principal_for(runtime, keys, "account-a"), offer(chosen, "r1"))
        _paying_account(runtime, "account-b", clock)
        before = runtime.access_source_report()
        catalog = runtime._catalog
        with catalog.store(write=True) as store:
            row = catalog.read(store, TENANT, "account-a")
            unsupported = {**row, "record_version": "unsupported-version",
                           "payload": {**row["payload"], "record_type": "service_tenant/v0"}}
            catalog.commit(store, (unsupported,), (catalog.guard(row),))
        return (before["counts"]["comped"] == 1 and before["counts"]["revenue_bearing"] == 1
                and refused(lambda: runtime.access_source_report(), "unsupported_or_corrupt_record"))
    check("a_tenant_record_this_release_cannot_read_stops_the_report_instead_of_being_counted",
          unreadable_tenant_stops_the_report)

    def no_code_is_ever_returned(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, record = created(administration, clock, FIRST_BODY)
        redemption.redeem(principal_for(runtime, keys, "account-a"), offer(chosen, "r1"))
        listing = administration.inspect()
        written = Path(runtime.config.database_path).read_bytes()
        rendered = repr(listing) + repr(record) + repr(administration.suspend(record["code_id"]))
        return (chosen.code not in rendered and chosen.code.encode() not in written
                and chosen.digest.encode() in written
                and record["code_returned"] is False and listing["codes_returned"] is False
                and listing["codes"][0]["redeemed_by"] == ["account-a"]
                and listing["codes"][0]["redemptions_used"] == 1
                and "code" not in listing["codes"][0] and "code_digest" not in listing["codes"][0])
    check("no_operator_view_and_no_stored_record_holds_a_code_text", no_code_is_ever_returned)

    def lifecycle_stops_new_redemptions(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        first, first_record = created(administration, clock, FIRST_BODY)
        second, second_record = created(administration, clock, SECOND_BODY)
        granted = redemption.redeem(principal_for(runtime, keys, "account-a"), offer(first, "r1"))
        administration.suspend(first_record["code_id"])
        administration.expire(second_record["code_id"])
        still_allowed = principal_for(runtime, keys, "account-a").entitlement
        return (refusal(lambda: redemption.redeem(principal_for(runtime, keys, "account-b"),
                                                  offer(first, "r2"))).reason == REASON_SUSPENDED
                and refusal(lambda: redemption.redeem(principal_for(runtime, keys, "account-b"),
                                                      offer(second, "r3"))).reason == REASON_EXPIRED
                and still_allowed == "bodies" and granted["granted"] is True
                and refused(lambda: administration.suspend("unknown-code-identity"),
                            "promotion_code_not_found"))
    check("suspending_or_expiring_a_code_stops_new_redemptions_without_removing_granted_access",
          lifecycle_stops_new_redemptions)

    def creation_needs_confirmation(folder):
        runtime, clock, _keys, administration, _redemption = fixture(folder)
        chosen = definition(clock, FIRST_BODY)
        without = refused(lambda: administration.create(chosen), "promotion_confirmation_required")
        with runtime._catalog.store() as store:
            absent = runtime._catalog.read(store, PROMOTION_CODE, chosen.digest) is None
        administration.create(chosen, confirmed=True)
        return (without and absent
                and refused(lambda: administration.create(chosen, confirmed=True),
                            "promotion_code_already_exists")
                and refused(lambda: administration.create(definition(clock, SECOND_BODY,
                            starts_at=clock[0] - 2 * DAY, expires_at=clock[0] - DAY), confirmed=True),
                            "invalid_promotion_window"))
    check("creating_a_code_requires_explicit_confirmation_and_a_window_that_has_not_closed",
          creation_needs_confirmation)

    def never_shortens_access(folder):
        runtime, clock, keys, administration, redemption = fixture(folder)
        runtime.set_operator_entitlement("account-a", valid_until=clock[0] + 90 * DAY,
                                         evidence_ref="approval:long-invitation")
        chosen, _ = created(administration, clock, FIRST_BODY, grant=PromotionGrant(seconds=7 * DAY))
        result = redemption.redeem(principal_for(runtime, keys, "account-a"), offer(chosen, "r1"))
        with runtime._catalog.store() as store:
            stored = runtime._catalog.read(store, ENTITLEMENT, "account-a")["payload"]
        return (result["valid_until"] == clock[0] + 90 * DAY
                and stored["source"] == CODE_GRANT_SOURCE
                and stored["previous_source"] == HOST_GRANT_SOURCE
                and stored["previous_valid_until"] == clock[0] + 90 * DAY)
    check("a_redemption_records_a_code_grant_without_shortening_access_the_account_already_has",
          never_shortens_access)

    def unknown_commit_spends_nothing(folder):
        from unittest.mock import patch
        from .records import ServiceCommitUnknown
        runtime, clock, keys, administration, redemption = fixture(folder)
        chosen, _ = created(administration, clock, FIRST_BODY)
        principal = principal_for(runtime, keys, "account-a")
        with patch.object(ServiceCatalogBinding, "commit",
                          staticmethod(lambda *args: (_ for _ in ()).throw(ServiceCommitUnknown()))):
            blocked = refused(lambda: redemption.redeem(principal, offer(chosen, "r1")), "commit_unknown")
        with runtime._catalog.store() as store:
            code = runtime._catalog.read(store, PROMOTION_CODE, chosen.digest)["payload"]
            entitlement = runtime._catalog.read(store, ENTITLEMENT, "account-a")
        later = redemption.redeem(principal, offer(chosen, "r1"))
        return (blocked and code["redemptions_used"] == 0 and entitlement is None
                and later["granted"] is True and later["replayed"] is False)
    check("an_unknown_commit_is_not_a_spent_redemption_and_the_same_request_still_works",
          unknown_commit_spends_nothing)

    def typed_definition_refuses_loose_input(folder):
        runtime, clock, _keys, _administration, _redemption = fixture(folder)
        return (refused(lambda: definition(clock, FIRST_BODY, grant=PromotionGrant(entitlement="metadata")),
                        "unsupported_promotion_grant")
                and refused(lambda: definition(clock, FIRST_BODY, grant=PromotionGrant(seconds=10)),
                            "invalid_promotion_grant")
                and refused(lambda: definition(clock, FIRST_BODY, grant={"seconds": DAY}),
                            "invalid_promotion_grant")
                and refused(lambda: definition(clock, FIRST_BODY, repeat_allowed_for_one_account="yes"),
                            "invalid_promotion_definition")
                and refused(lambda: definition(clock, FIRST_BODY, redemptions_allowed=0),
                            "invalid_promotion_definition")
                and refused(lambda: definition(clock, FIRST_BODY, approval_ref="  "),
                            "invalid_request")
                and refused(lambda: definition(clock, "", code="ab"), "invalid_promotion_code")
                and refused(lambda: PromotionRedemptionRequest.from_dict(
                    {"record_type": "service_promotion_redemption_request/v0", "code": PREFIX + "-" + FIRST_BODY,
                     "request_id": "r1"}), "invalid_promotion_request")
                and refused(lambda: PromotionRedemptionRequest.from_dict(
                    {"record_type": "service_promotion_redemption_request/v1", "code": PREFIX + "-" + FIRST_BODY,
                     "request_id": "r1", "grant": {"seconds": 99}}), "invalid_promotion_request")
                and runtime.config.namespace == "hosted-service")
    check("a_code_definition_and_a_redemption_request_refuse_untyped_or_unversioned_input",
          typed_definition_refuses_loose_input)

    def state_evaluates_every_condition(folder):
        state = promotion_code_state(ABSENT_CODE, 1_000_000)
        live = promotion_code_state({"enabled": True, "starts_at": 1, "expires_at": 2_000_000,
                                     "redemptions_used": 0, "redemptions_allowed": 3}, 1_000_000)
        return (state.known is False and state.suspended is True and state.expired is True
                and state.exhausted is True and state.reason == REASON_UNKNOWN_CODE
                and state.redeemable is False
                and live.reason == NO_REFUSAL and live.redeemable is True and live.known is True
                and promotion_code_state({"enabled": True, "starts_at": 1, "expires_at": 2_000_000,
                                          "redemptions_used": 3, "redemptions_allowed": 3},
                                         1_000_000).reason == REASON_EXHAUSTED)
    check("code_state_fills_every_condition_for_a_real_code_and_for_an_unknown_one",
          state_evaluates_every_condition)

    def host_write_authority(folder):
        path = Path(folder) / "absent.sqlite"
        clock = [1_000_000]
        runtime = ServiceRuntime(ServiceRuntimeConfig(str(path)), clock=lambda: clock[0])
        administration = PromotionCodeAdministration(runtime)
        return (refused(lambda: administration.create(definition(clock, FIRST_BODY), confirmed=True),
                        "host_write_authority_required") and not path.exists())
    check("creating_a_code_without_host_write_authority_creates_no_database", host_write_authority)

    passed = sum(row["passed"] for row in tests)
    return {"record_type": "service_promotion_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}


def http_application(fixture, promotions):
    """One real application with promotion redemption installed, or without it."""
    from .http import ServiceHttpApplication
    from .http_auth import ServiceHttpAuthentication

    def build(configuration):
        return ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
                                      ServiceHttpAuthentication(), promotions=promotions)
    return build


def run_http_checks(check, root):
    """Loopback transport checks. The HTTP suite owns the optional dependencies."""
    import httpx
    from .http import PROMOTION_REDEMPTION_PATH
    from .http_test_fixtures import HttpDomainFixture, running_http
    from .request_limits import LIMIT_REACHED_CODE, ServiceRequestLimits

    def space(name):
        (root / name).mkdir(parents=True, exist_ok=True)
        return root / name

    fixture = HttpDomainFixture(space("served"), operator_access=False)
    administration = PromotionCodeAdministration(fixture.runtime)
    clock = [int(fixture.runtime._now())]
    live, live_record = created(administration, clock, FIRST_BODY, redemptions_allowed=1)
    spent, _ = created(administration, clock, SECOND_BODY, redemptions_allowed=1)
    promotions = PromotionRedemption(fixture.runtime, PromotionPolicy(redemption_enabled=True))
    promotions.redeem(fixture.runtime.authenticate_key(fixture.keys["beta"].key), offer(spent, "beta-spend"))
    with running_http(fixture, application_factory=http_application(fixture, promotions)) as (base, service):
        with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False, timeout=5) as client:
            before = client.post("/api/v1/provisioning", json={
                "record_type": "service_provisioning_request/v1", "operation": "read",
                "identity": "skill.alpha", "request_id": "before-redemption"})
            granted = client.post(PROMOTION_REDEMPTION_PATH, json={
                "record_type": "service_promotion_redemption_request/v1",
                "code": live.code, "request_id": "web-1"})
            after = client.post("/api/v1/provisioning", json={
                "record_type": "service_provisioning_request/v1", "operation": "read",
                "identity": "skill.alpha", "request_id": "after-redemption"})
            result = granted.json()["result"]
            check("a_served_redemption_grants_body_access_and_records_a_code_grant_not_a_payment",
                  before.status_code == 403 and granted.status_code == 200 and after.status_code == 200
                  and result["source"] == "promotion_code_grant" and result["payment"] is False
                  and result["promotion_code_id"] == live_record["code_id"]
                  and live.code not in granted.text)
            unknown = client.post(PROMOTION_REDEMPTION_PATH, json={
                "record_type": "service_promotion_redemption_request/v1",
                "code": PREFIX + "-" + GUESSED_BODY, "request_id": "web-2"})
            exhausted = client.post(PROMOTION_REDEMPTION_PATH, json={
                "record_type": "service_promotion_redemption_request/v1",
                "code": spent.code, "request_id": "web-3"})
            # Every refusal carries the reference of its own request, issued at
            # random before the code is read, so two refusals always differ in
            # that value and it carries nothing about the code. Every other
            # byte of the two answers must be the same.
            from .observability import valid_reference
            def without_reference(answer):
                reference = answer.json().get("request_reference")
                if not valid_reference(reference):
                    return None
                return answer.content.replace(reference.encode("ascii"), b"")
            check("the_served_refusal_for_an_unknown_and_an_exhausted_code_is_the_same_answer",
                  unknown.status_code == exhausted.status_code == 403
                  and without_reference(unknown) is not None
                  and without_reference(unknown) == without_reference(exhausted)
                  and unknown.json()["error"]["code"] == "promotion_code_unusable"
                  and "unknown" not in unknown.text and "exhausted" not in unknown.text)
            anonymous = httpx.post(base + PROMOTION_REDEMPTION_PATH, trust_env=False, json={
                "record_type": "service_promotion_redemption_request/v1",
                "code": live.code, "request_id": "web-4"})
            check("redemption_without_a_credential_is_refused_before_any_code_is_looked_at",
                  anonymous.status_code == 401 and "promotion" not in anonymous.json()["error"]["code"])
            capabilities = client.get("/api/v1/capabilities").json()["result"]["website"]
            check("capabilities_name_the_one_address_that_redeems_a_code",
                  capabilities["promotion_redemption_available"] is True
                  and capabilities["promotion_redemption_endpoint"] == PROMOTION_REDEMPTION_PATH
                  and service.promotions is promotions)

    closed = HttpDomainFixture(space("closed"), operator_access=False)
    with running_http(closed, application_factory=http_application(closed, None)) as (base, _service):
        with httpx.Client(base_url=base, headers=closed.headers(), trust_env=False, timeout=5) as client:
            answer = client.post(PROMOTION_REDEMPTION_PATH, json={
                "record_type": "service_promotion_redemption_request/v1",
                "code": PREFIX + "-" + FIRST_BODY, "request_id": "closed-1"})
            check("a_service_without_promotions_installed_refuses_the_address_as_unavailable",
                  answer.status_code == 503
                  and answer.json()["error"]["code"] == "promotion_redemption_unavailable")

    guessing = HttpDomainFixture(space("guessing"), operator_access=False)
    limits = ServiceRequestLimits(client_address_source="socket_peer", failures_allowed=2, window_seconds=600)
    guess_promotions = PromotionRedemption(guessing.runtime, PromotionPolicy(redemption_enabled=True))
    with running_http(guessing, application_factory=http_application(guessing, guess_promotions),
                      request_limits=limits) as (base, service):
        with httpx.Client(base_url=base, headers=guessing.headers(), trust_env=False, timeout=5) as client:
            statuses = [client.post(PROMOTION_REDEMPTION_PATH, json={
                "record_type": "service_promotion_redemption_request/v1",
                "code": PREFIX + "-GUESS-%04d" % attempt, "request_id": "guess-%d" % attempt}).status_code
                for attempt in range(3)]
            # The same address is now over its allowance for every signed-in
            # address of this service, not only for redemption.
            blocked = client.get("/api/v1/session")
            check("guessed_codes_reach_the_existing_failed_attempt_limit_for_that_address",
                  statuses == [403, 403, 429] and len(service.request_limiter) == 1
                  and blocked.status_code == 429
                  and blocked.json()["error"]["code"] == LIMIT_REACHED_CODE
                  and blocked.headers["retry-after"].isdigit())
