"""Checks for staff roles, superadmin account administration, free monthly Baltor Pro and the founding offer.

Staff sign in with signed browser tokens from an owned loopback key set, as in
`account_origin_checks.py`; the identity provider's user list is a stand-in
transport. No provider, mailbox or network outside loopback is used. Every
guard has a known-wrong control that removes it and makes its named check fail.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import threading
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from . import free_monthly as free_module
from .account_administration import AUDIT, AccountAdministration, AccountAdministrationRequest
from .account_email import ProviderAnswer
from .account_origin import AccountOrigins, SupabaseIdentityAdministration, USERS_PATH
from .account_origin_checks import mutated, signed_identity
from .browser_identity import BrowserIdentityAdapter
from .account_policy import (ACCOUNT_COUNTS, ANALYTICS, DEVELOPER, PERMISSIONS, ROLE_PERMISSIONS, SERVICE_DIAGNOSTICS,
                             SUPERADMIN, USAGE_COUNTS, ServiceAccountPolicy, permissions_for)
from .free_monthly import (ACCESS_HELD, FOUNDING, FOUNDING_FREE_MONTHLY, GRANTED, LIMIT_REACHED,
                           consider_founding_offer, founding_holders, next_month, renew_free_monthly)
from .records import ServiceRuntimeError
from .runtime import ENTITLEMENT, SUBJECT
from .storage import ServiceCatalogBinding

OPERATIONS = ("grant_free_monthly", "revoke_free_monthly", "disable", "enable")


def _code(function):
    try:
        function()
        return None
    except (ServiceRuntimeError, ValueError) as error:
        return getattr(error, "code", type(error).__name__)


def _role_checks(check):
    check("staff_role_permissions_are_the_table_in_code",
          ROLE_PERMISSIONS[SUPERADMIN] == frozenset(PERMISSIONS)
          and ROLE_PERMISSIONS[DEVELOPER] == frozenset({SERVICE_DIAGNOSTICS})
          and ROLE_PERMISSIONS[ANALYTICS] == frozenset({ACCOUNT_COUNTS, USAGE_COUNTS})
          and set(ROLE_PERMISSIONS) == {SUPERADMIN, DEVELOPER, ANALYTICS}
          and permissions_for("owner") == frozenset() and permissions_for("") == frozenset())
    policy = ServiceAccountPolicy(staff=({"role": SUPERADMIN, "email": "Owner@Example.com"},))
    check("a_staff_role_is_named_only_by_the_host_list_and_matched_in_lower_case",
          policy.role_for("f" * 8 + "-0000-4000-8000-" + "0" * 12, "owner@example.com") == SUPERADMIN
          and policy.role_for("", "someone@example.com") == ""
          and _code(lambda: ServiceAccountPolicy(staff=({"role": SUPERADMIN, "email": "a@example.com"},
                                                        {"role": ANALYTICS, "email": "A@example.com"})))
          == "invalid_account_policy"
          and _code(lambda: ServiceAccountPolicy(founding_free_monthly_accounts=-1)) == "invalid_account_policy")


def _people_listing(identity):
    """The identity provider's user list for the people of one signed identity fixture."""
    def admin(request, secret):
        query = parse_qs(urlsplit(request.url).query)
        if request.method != "GET" or urlsplit(request.url).path != USERS_PATH or query.get("page") != ["1"]:
            return ProviderAnswer(200, {"users": []})
        return ProviderAnswer(200, {"users": [
            {"id": subject, "email": person["email"], "created_at": "2026-09-2%dT00:00:00Z" % (index % 10),
             "email_confirmed_at": "2026-09-20T00:00:00Z", "last_sign_in_at": "2026-09-23T00:00:00Z",
             "app_metadata": person["app_metadata"]} for index, (subject, person) in enumerate(identity.people.items())]})
    return admin


class _Staff:
    """Four people who signed up through Baltor: three staff and one customer."""

    def __init__(self, identity, founding=None):
        self.identity = identity
        self.superadmin = identity.person("owner@example.com")
        self.developer = identity.person("developer@example.com")
        self.analytics = identity.person("numbers@example.com")
        self.customer = identity.person("customer@example.com")
        self.policy = ServiceAccountPolicy(founding_free_monthly_accounts=10 if founding is None else founding, staff=(
            {"role": SUPERADMIN, "email": "owner@example.com"},
            {"role": DEVELOPER, "provider_user_id": self.developer},
            {"role": ANALYTICS, "email": "numbers@example.com"}))
        self.adapter = identity.adapter(founding_accounts=founding)
        self.tenants = {subject: self.adapter.activate(identity.token(subject))["tenant_id"]
                        for subject in (self.superadmin, self.developer, self.analytics, self.customer)}
        runtime = identity.fixture.runtime
        self.administration = AccountAdministration(runtime, self.policy, identity.issuer, origins=AccountOrigins(
            runtime, identity.issuer, SupabaseIdentityAdministration(identity.origin, allow_network=True,
                                                                    transport=_people_listing(identity))),
            identity_secret=lambda: "sb_secret_fixture")

    def session(self, subject, **changes):
        token = self.identity.token(subject, **changes)
        current = self.adapter.authenticate(token)
        return self.administration.staff_session(current, hashlib.sha256(token.encode()).hexdigest()), token

    def request(self, operation, subject, request_id):
        return AccountAdministrationRequest(operation, request_id, self.tenants[subject])


def _audit_rows(runtime):
    with runtime._catalog.store() as store:
        return [row["payload"] for row in runtime._catalog.rows_all(store, AUDIT)]


def _entitled(runtime, tenant_id):
    """Whether an account's next check gives it bodies, read through a fresh principal."""
    with runtime._catalog.store() as store:
        subject = next(row for row in runtime._catalog.rows(store, SUBJECT, tenant_id))["payload"]
    return runtime.authenticate_subject(subject["issuer"], subject["subject"]).entitlement == "bodies"


def _limited_roles_change_nothing(root, name):
    with signed_identity(root / name, operator_access=False) as identity:
        return _limited_roles_hold(_Staff(identity))


def _limited_roles_hold(staff):
    runtime = staff.identity.fixture.runtime
    before = (_audit_rows(runtime), _entitled(runtime, staff.tenants[staff.customer]))
    codes = []
    for role_subject in (staff.developer, staff.analytics):
        session, _token = staff.session(role_subject)
        for operation in OPERATIONS:
            codes.append(_code(lambda: staff.administration.apply(
                session, staff.request(operation, staff.customer, "limited-" + operation))))
        codes.append(_code(lambda: staff.administration.accounts(session)))
    return (codes == ["account_administration_forbidden"] * 10
            and (_audit_rows(runtime), _entitled(runtime, staff.tenants[staff.customer])) == before)


def _administration_checks(check, root):
    check("developer_and_analytics_roles_cannot_grant_revoke_disable_enable_or_list",
          _limited_roles_change_nothing(root, "limited"))
    with patch("loop_engine.core.service_runtime.account_administration.permissions_for",
               lambda role: frozenset(PERMISSIONS)):
        check("removed_role_permission_table_is_detected", not _limited_roles_change_nothing(root, "limited-mutant"))
    check("revoking_free_monthly_removes_access_at_the_next_check", _revocation_removes_access(root, "revoke"))
    with mutated(free_module, "revoke_rows", "**value, \"enabled\": False, \"entitlement\": METADATA, \"valid_until\": None,",
                 "**value,"):
        check("removed_revocation_is_detected", not _revocation_removes_access(root, "revoke-mutant"))
    with signed_identity(root / "administration", operator_access=False) as identity:
        staff = _Staff(identity)
        runtime = identity.fixture.runtime
        customer_session_code = _code(lambda: staff.session(staff.customer))
        check("a_customer_account_holds_no_staff_role", customer_session_code == "staff_role_required")
        session, token = staff.session(staff.superadmin)
        customer = staff.tenants[staff.customer]
        results = [staff.administration.apply(session, staff.request(operation, staff.customer, "every-" + operation))
                   for operation in ("grant_free_monthly", "revoke_free_monthly", "disable", "enable")]
        audit = sorted((row["operation"], row["tenant_id"], row["actor_role"]) for row in _audit_rows(runtime))
        check("every_admin_action_writes_one_audit_record_with_its_actor_and_target",
              all(result["committed"] and not result["replayed"] for result in results)
              and audit == sorted((operation, customer, SUPERADMIN) for operation in OPERATIONS))
        grant = staff.request("grant_free_monthly", staff.customer, "grant-once")
        first = staff.administration.apply(session, grant)
        repeat = staff.administration.apply(session, grant)
        changed = _code(lambda: staff.administration.apply(session, AccountAdministrationRequest(
            "disable", "grant-once", customer)))
        check("a_repeated_request_identity_replays_and_a_changed_one_is_refused",
              first["replayed"] is False and repeat["replayed"] is True
              and {key: value for key, value in repeat.items() if key != "replayed"}
              == {key: value for key, value in first.items() if key != "replayed"}
              and changed == "account_administration_request_identity_conflict"
              and len(_audit_rows(runtime)) == 5)
        staff.administration.apply(session, staff.request("revoke_free_monthly", staff.customer, "revoke-now"))
        expired = replace(session, expires_at=1.0)
        before = len(_audit_rows(runtime))
        check("an_expired_staff_session_changes_nothing",
              _code(lambda: staff.administration.apply(expired, staff.request("disable", staff.customer, "late")))
              == "unauthorized" and len(_audit_rows(runtime)) == before)
        signed_out, signed_out_token = staff.session(staff.superadmin, jti="signing-out")
        staff.adapter.logout(type("Request", (), {"credential": signed_out_token})())
        check("a_signed_out_staff_session_changes_nothing",
              _code(lambda: staff.administration.apply(signed_out, staff.request("disable", staff.customer, "out")))
              == "unauthorized" and len(_audit_rows(runtime)) == before)
        check("a_superadmin_cannot_switch_off_their_own_account_and_a_host_tenant_is_not_an_account",
              _code(lambda: staff.administration.apply(session, staff.request("disable", staff.superadmin, "self")))
              == "staff_cannot_switch_off_own_account"
              and _code(lambda: staff.administration.apply(session, AccountAdministrationRequest(
                  "disable", "host-tenant", "alpha"))) == "account_not_found")
        disabled = staff.administration.apply(session, staff.request("disable", staff.customer, "switch-off"))
        try:
            staff.adapter.authenticate(identity.token(staff.customer))
            switched_off = False
        except Exception:
            switched_off = True
        staff.administration.apply(session, staff.request("enable", staff.customer, "switch-on"))
        check("disabling_an_account_stops_its_sign_in_and_enabling_restores_it",
              disabled["enabled"] is False and switched_off
              and staff.adapter.authenticate(identity.token(staff.customer)).principal.tenant_id == customer)
        listing = staff.administration.accounts(session)
        row = next(item for item in listing["accounts"] if item["tenant_id"] == customer)
        check("the_superadmin_list_shows_address_creation_confirmation_plan_and_last_use",
              listing["identity_details_available"] is True and row["email"] == "customer@example.com"
              and row["created_at"] and row["email_confirmed"] is True and row["last_sign_in_at"]
              and row["plan_state"] == "none" and row["created_by_this_service"] is True and "last_item_at" in row
              and listing["total"] == 4)


def _revocation_removes_access(root, name):
    """A granted account reads bodies; after revocation its very next check does not."""
    with signed_identity(root / name, operator_access=False) as identity:
        staff = _Staff(identity)
        runtime, customer = identity.fixture.runtime, staff.tenants[staff.customer]
        session, _token = staff.session(staff.superadmin)
        staff.administration.apply(session, staff.request("grant_free_monthly", staff.customer, "grant"))
        principal = staff.adapter.authenticate(identity.token(staff.customer)).principal
        before = principal.entitlement == "bodies"
        staff.administration.apply(session, staff.request("revoke_free_monthly", staff.customer, "revoke"))
        try:
            after = runtime.revalidate(principal).entitlement == "bodies"
        except ServiceRuntimeError:
            after = False
        return before and not after and not _entitled(runtime, customer)


def _new_account(identity, adapter, index):
    subject = identity.person("founder%02d@example.com" % index)
    return adapter.activate(identity.token(subject))


def _founding_count(runtime):
    """Accounts whose recorded entitlement is the founding offer and gives bodies now."""
    with runtime._catalog.store() as store:
        rows = runtime._catalog.rows_all(store, ENTITLEMENT)
        policy = runtime._catalog.read(store, "service_billing_policy", "stripe")
        return sum(1 for row in rows if row["payload"].get("grant_kind") == FOUNDING_FREE_MONTHLY
                   and runtime._entitlement(row, policy) == "bodies")


def _first_ten(root, name, limit=10, accounts=11):
    with signed_identity(root / name, operator_access=False) as identity:
        adapter = identity.adapter(founding_accounts=limit)
        decisions = [_new_account(identity, adapter, index)["founding_offer"] for index in range(accounts)]
        migrated = identity.person("migrated@example.com", origin="migration")
        migrated_answer = adapter.activate(identity.token(migrated))
        return decisions, _founding_count(identity.fixture.runtime), migrated_answer, identity


def _race_for_the_last_place(root, name):
    """Nine hold the offer; two new accounts read the count before either writes."""
    with signed_identity(root / name, operator_access=False) as identity:
        runtime = identity.fixture.runtime
        adapter = identity.adapter(founding_accounts=None)
        tenants = [_new_account(identity, adapter, index)["tenant_id"] for index in range(11)]
        for tenant in tenants[:9]:
            consider_founding_offer(runtime, tenant, 10)
        barrier, local = threading.Barrier(2), threading.local()
        original = ServiceCatalogBinding.read

        def racing(self, store, kind, logical_identity):
            row = original(self, store, kind, logical_identity)
            if kind == FOUNDING and not getattr(local, "waited", False):
                local.waited = True
                barrier.wait(timeout=5)
            return row
        outcomes = {}

        def attempt(tenant):
            outcomes[tenant] = free_module.consider_founding_offer(runtime, tenant, 10)
        with patch.object(ServiceCatalogBinding, "read", racing):
            workers = [threading.Thread(target=attempt, args=(tenant,)) for tenant in tenants[9:]]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(20)
        return sorted(outcomes.values()), len(founding_holders(runtime)), _founding_count(runtime)


def _founding_offer_follows_the_places(root, name):
    """The public statement of the founding offer: open with a place free, closed once the places are taken or with no offer.

    The pricing page and the Get started funnel state the offer only while the
    service reports it open, so a visitor is never promised a place that is gone.
    """
    with signed_identity(root / name, operator_access=False) as identity:
        adapter = identity.adapter(founding_accounts=2)
        answers = [adapter.founding_offer_open()]
        for index in range(2):
            _new_account(identity, adapter, index)
            answers.append(adapter.founding_offer_open())
        without = identity.adapter(founding_accounts=None).founding_offer_open()
        closed = BrowserIdentityAdapter(identity.fixture.runtime, replace(identity.policy, registration_enabled=False, email_signup_enabled=False),
                                        lambda _: "sb_publishable_local_fixture", transport=identity.user,
                                        founding_accounts=5).founding_offer_open()
        return answers == [True, True, False] and without is False and closed is False


def _founding_checks(check, root):
    check("the_founding_offer_is_reported_open_only_while_a_place_is_free",
          _founding_offer_follows_the_places(root, "offer-open"))
    with mutated(BrowserIdentityAdapter, "founding_offer_open",
                 "return len(founding_holders(self.runtime)) < self.founding_accounts", "return True"):
        check("removed_founding_place_count_in_the_public_offer_is_detected",
              not _founding_offer_follows_the_places(root, "offer-always-open"))

    def first_ten_hold(name):
        decisions, count, migrated, _identity = _first_ten(root, name)
        return decisions == [GRANTED] * 10 + [LIMIT_REACHED] and count == 10 and "founding_offer" not in migrated
    check("the_first_ten_accounts_hold_the_founding_offer_and_the_eleventh_does_not", first_ten_hold("first-ten"))
    wrong_decision = ("else GRANTED if len(holders) < limit else LIMIT_REACHED)", "else GRANTED)")
    # The decision and the count about to be written are compared separately,
    # so a wrong decision alone still stops at the limit, as promotion codes do.
    with mutated(free_module, "consider_founding_offer", *wrong_decision):
        capped = _first_ten(root, "wrong-decision")
    check("a_wrong_founding_decision_still_cannot_pass_the_limit", capped[1] == 10 and capped[0][-1] == "deferred")
    with mutated(free_module, "consider_founding_offer", *wrong_decision,
                 also=(("if tenant_id in holders or len(holders) + 1 > limit:", "if tenant_id in holders:"),)):
        check("removed_founding_limit_is_detected", not first_ten_hold("no-limit"))
    raced = _race_for_the_last_place(root, "race")
    check("a_race_for_the_last_founding_place_yields_exactly_ten", raced == ([GRANTED, LIMIT_REACHED], 10, 10))
    # The known-wrong design counts holders without a guarded counter: the
    # store takes no write without a precondition, so the mutant drops the
    # counter write and its guard together, and both racers are granted.
    with mutated(free_module, "consider_founding_offer",
                 ",\n                          catalog.guard(counter_row, catalog.identity(FOUNDING, FOUNDING_KEY))]", "]",
                 also=(('rows.append(catalog.record(FOUNDING, FOUNDING_KEY, {\n'
                        '                        "record_type": FOUNDING_VERSION, "holders": [*holders, tenant_id],\n'
                        '                        "granted_total": counter.get("granted_total", 0) + 1}))', "pass"),)):
        check("removed_counter_guard_lets_the_race_pass_ten_and_is_detected",
              _race_for_the_last_place(root, "race-mutant") == ([GRANTED, GRANTED], 9, 11))
    small, small_count, _migrated, _ = _first_ten(root, "host-count", limit=2, accounts=3)
    check("the_founding_count_comes_from_the_host_file", small == [GRANTED, GRANTED, LIMIT_REACHED] and small_count == 2)
    # The offer is visible and revocable in the superadmin view, and a revoked
    # place goes to the next account that finishes sign-up.
    with signed_identity(root / "revocable", operator_access=False) as identity:
        staff = _Staff(identity, founding=1)
        session, _ = staff.session(staff.superadmin)
        listing = staff.administration.accounts(session)
        holder = next(row for row in listing["accounts"] if row["founding"])
        revoked = staff.administration.apply(session, AccountAdministrationRequest(
            "revoke_free_monthly", "revoke-founding", holder["tenant_id"]))
        later = _new_account(identity, staff.adapter, 99)
        check("a_founding_offer_is_visible_and_revocable_and_its_place_goes_to_the_next_sign_up",
              holder["plan_state"] == FOUNDING_FREE_MONTHLY and listing["founding_holders"] == 1
              and revoked["grant_kind"] == FOUNDING_FREE_MONTHLY
              and later["founding_offer"] == GRANTED and len(founding_holders(identity.fixture.runtime)) == 1)
        already = _code(lambda: staff.administration.apply(session, AccountAdministrationRequest(
            "grant_free_monthly", "grant-founder", later["tenant_id"])))
        unconsidered = identity.adapter().activate(identity.token(identity.person("granted.first@example.com")))
        staff.administration.apply(session, AccountAdministrationRequest(
            "grant_free_monthly", "grant-first", unconsidered["tenant_id"]))
        check("an_account_that_already_holds_free_monthly_is_not_granted_twice_or_given_a_founding_place",
              already == "free_monthly_already_held"
              and consider_founding_offer(identity.fixture.runtime, later["tenant_id"], 5) == GRANTED
              and consider_founding_offer(identity.fixture.runtime, unconsidered["tenant_id"], 5) == ACCESS_HELD)


def _later(runtime, moment):
    """The same service store read at another moment."""
    from .runtime import ServiceRuntime
    return ServiceRuntime(runtime.config, clock=lambda: moment)


def _renews(root, name):
    """A grant due within three days moves on one calendar month, once, and gives bodies past its first end.

    After a revocation, nothing renews it. Returns the verdict and the two ends.
    """
    with signed_identity(root / name, operator_access=False) as identity:
        staff = _Staff(identity)
        runtime, customer = identity.fixture.runtime, staff.tenants[staff.customer]
        session, _ = staff.session(staff.superadmin)
        first_end = staff.administration.apply(session, staff.request(
            "grant_free_monthly", staff.customer, "monthly"))["valid_until"]
        near_end = _later(runtime, first_end - 86400)
        renewed = renew_free_monthly(near_end)["renewed"]
        with runtime._catalog.store() as store:
            renewed_until = runtime._catalog.read(store, ENTITLEMENT, customer)["payload"]["valid_until"]
        repeated = renew_free_monthly(near_end)["renewed"]
        past_first_end = _entitled(_later(runtime, first_end + 3600), customer)
        staff.administration.apply(session, staff.request("revoke_free_monthly", staff.customer, "end-monthly"))
        after_revocation = renew_free_monthly(_later(runtime, renewed_until - 3600))["renewed"]
        verdict = (renewed == 1 and renewed_until == next_month(first_end) and repeated == 0 and past_first_end
                   and after_revocation == 0 and not _entitled(runtime, customer))
        return verdict, renewed_until, first_end


def _renewal_checks(check, root):
    renewed, renewed_until, first_end = _renews(root, "renewal")
    check("free_monthly_renews_each_month_until_revoked",
          renewed is True and renewed_until == next_month(first_end))
    with mutated(free_module, "_renewal_due", "return (bool(free_monthly_kind(payload))",
                 "return False and (bool(free_monthly_kind(payload))"):
        check("removed_renewal_is_detected", _renews(root, "renewal-mutant")[0] is False)
    check("the_monthly_period_follows_the_calendar",
          next_month(1_769_817_600) == 1_772_236_800 and next_month(1_798_675_200) == 1_801_353_600)


def _http_checks(check, root):
    import httpx
    from .http import ServiceHttpApplication
    from .http_test_fixtures import running_http
    from .records import ACCESS_MANAGE_SCOPE, TenantKeyIssue, TenantRegistration
    with signed_identity(root / "http", operator_access=False) as identity:
        staff = _Staff(identity, founding=1)
        runtime = identity.fixture.runtime
        runtime.register_tenant(TenantRegistration("host-administrator", "host:administrator", (ACCESS_MANAGE_SCOPE,)))
        host_key = runtime.issue_key(TenantKeyIssue("host-administrator", "host administration")).key
        def create(config):
            return ServiceHttpApplication(runtime, identity.fixture.provisioning, config,
                                          browser_identity=staff.adapter, account_administration=staff.administration)
        with httpx.Client(trust_env=False, timeout=10) as client, \
                running_http(identity.fixture, application_factory=create) as (base, _service):
            def call(subject_or_key, path, payload=None, **headers):
                credential = subject_or_key if subject_or_key.startswith("le_") else identity.token(subject_or_key)
                sent = {"Authorization": "Bearer " + credential, **headers}
                return (client.post(base + path, headers=sent, json=payload) if payload is not None
                        else client.get(base + path, headers=sent))
            customer_answers = [call(staff.customer, "/api/v1/admin/overview"), call(staff.customer, "/api/v1/admin/accounts"),
                                call(staff.customer, "/api/v1/admin/accounts", {"record_type": "service_account_administration_request/v1",
                                     "operation": "grant_free_monthly", "request_id": "self-grant", "tenant_id": staff.tenants[staff.customer]})]
            host_answer = call(host_key, "/api/v1/admin/overview")
            check("a_non_staff_account_or_a_host_key_cannot_reach_the_staff_administration",
                  [answer.status_code for answer in customer_answers] == [403, 403, 403]
                  and all(answer.json()["error"]["code"] == "staff_role_required" for answer in customer_answers)
                  and host_answer.status_code == 403 and host_answer.json()["error"]["code"] == "staff_role_required")
            foreign = call(staff.superadmin, "/api/v1/admin/accounts", Origin="https://foreign.invalid")
            check("a_foreign_browser_origin_cannot_reach_the_staff_administration", foreign.status_code == 403
                  and foreign.json()["error"]["code"] == "invalid_origin")
            analytics = call(staff.analytics, "/api/v1/admin/overview").json()["result"]
            developer = call(staff.developer, "/api/v1/admin/overview").json()["result"]
            check("analytics_reads_counts_without_any_address_and_developer_reads_diagnostics_only",
                  analytics["role"] == ANALYTICS and analytics["account_counts"]["accounts"] == 4
                  and analytics["account_counts"]["founding_limit"] == 1 and "usage_counts" in analytics
                  and "diagnostics" not in analytics and "@" not in json.dumps(analytics)
                  and developer["role"] == DEVELOPER and "account_counts" not in developer
                  and developer["diagnostics"]["health"]["alive"] is True and "@" not in json.dumps(developer))
            listing = call(staff.superadmin, "/api/v1/admin/accounts")
            action = call(staff.superadmin, "/api/v1/admin/accounts", {
                "record_type": "service_account_administration_request/v1", "operation": "grant_free_monthly",
                "request_id": "http-grant", "tenant_id": staff.tenants[staff.analytics]})
            sessions = {name: call(subject, "/api/v1/session").json()["result"] for name, subject in
                        (("owner", staff.superadmin), ("numbers", staff.analytics), ("customer", staff.customer))}
            check("a_superadmin_lists_accounts_and_acts_over_http_through_a_governed_operation",
                  listing.status_code == 200 and listing.json()["execution"]["runtime_type"] == "Loop"
                  and any(row["email"] == "customer@example.com" for row in listing.json()["result"]["accounts"])
                  and action.status_code == 200 and action.json()["result"]["committed"] is True
                  and listing.headers["cache-control"] == "no-store")
            check("the_session_names_the_staff_role_and_the_free_monthly_plan",
                  sessions["owner"]["staff_role"] == SUPERADMIN and sessions["owner"]["access_source"] == "founding_free_monthly"
                  and sessions["numbers"]["staff_role"] == ANALYTICS and sessions["numbers"]["access_source"] == "free_monthly"
                  and sessions["customer"]["staff_role"] is None and sessions["customer"]["staff_permissions"] == []
                  and sessions["customer"]["access_source"] == "none")


def run_checks(check, root):
    _role_checks(check)
    _administration_checks(check, root)
    _founding_checks(check, root)
    _renewal_checks(check, root)
    _http_checks(check, root)
