"""Checks for the staff tools: keys, roles, plans, the audit record, credits, messages and imports.

Staff sign in with signed browser tokens from an owned loopback key set, and
the identity provider is the in-process stand-in project, so the account list,
the one way in and every message are played without a provider, a mailbox or a
network outside loopback. Every guard has a known-wrong control: `mutated`
rebuilds one function from its own source with the guard removed, and the
check that holds the guard must then fail.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import uuid

from . import account_import as import_module
from . import account_messages as message_module
from . import credits as credit_module
from . import staff_keys as keys_module
from . import staff_tool_accounts as account_tools
from .account_administration import AccountAdministration
from .account_email import AccountEmailAdapter
from .account_email_checks import IDENTITY_ORIGIN, _secrets, _settings
from .account_origin import ACCOUNT_MARK, ACCOUNT_MARKER, AccountOrigins, SupabaseIdentityAdministration, origin_of
from .account_origin_checks import MarkingIdentityProjectStandIn, mutated, signed_identity
from .account_policy import ANALYTICS, DEVELOPER, ROLE_PERMISSIONS, SUPERADMIN, ServiceAccountPolicy
from .activity import AUDIT, COUNTS_VERSION
from .observability import new_request_reference, valid_reference
from .records import ServiceRuntimeError
from .request_limits import SOCKET_PEER_SOURCE, ServiceRequestLimits
from .staff_keys import StaffKeyRequest, StaffKeys
from .staff_tools import StaffToolSettings, StaffTools

PEOPLE = (("owner", "owner@example.com"), ("developer", "developer@example.com"), ("numbers", "numbers@example.com"),
          ("first", "first.customer@example.com"), ("second", "second.customer@example.com"))
PUBLIC_ORIGIN = "https://baltor.example"


def code_of(action):
    """The refusal code of one action, or None when it succeeded."""
    try:
        action()
        return None
    except (ServiceRuntimeError, ValueError) as error:
        return getattr(error, "code", type(error).__name__)


class StaffWorld:
    """Three staff members and two customers who signed up through Baltor, and the staff tools over them."""

    def __init__(self, identity, *, mail_daily_cap=50, catalogue=None, policy=None):
        self.identity, self.runtime = identity, identity.fixture.runtime
        self.project, self.people = MarkingIdentityProjectStandIn(), {}
        for name, email in PEOPLE:
            subject = identity.person(email)
            user = self.project._new_user(email, "provider-held-" + uuid.uuid4().hex)
            user.update(id=subject, confirmed_at=datetime.now(timezone.utc) - timedelta(days=1),
                        app_metadata={ACCOUNT_MARKER: ACCOUNT_MARK})
            self.people[name] = subject
        self.policy = policy or ServiceAccountPolicy(staff=(
            {"role": SUPERADMIN, "email": "owner@example.com"},
            {"role": DEVELOPER, "provider_user_id": self.people["developer"]},
            {"role": ANALYTICS, "email": "numbers@example.com"}))
        self.browser = identity.adapter(founding_accounts=10)
        self.tenants = {name: self.browser.activate(identity.token(subject))["tenant_id"]
                        for name, subject in self.people.items()}
        self.origins = AccountOrigins(self.runtime, identity.issuer, SupabaseIdentityAdministration(
            IDENTITY_ORIGIN, allow_network=True, transport=self.project.admin))
        self.administration = AccountAdministration(self.runtime, self.policy, identity.issuer, origins=self.origins,
                                                    identity_secret=lambda: "sb_secret_fixture")
        self.email = AccountEmailAdapter(_settings(), _secrets, public_base_url=PUBLIC_ORIGIN,
            address_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE, failures_allowed=100),
            display_name="Baltor", identity_transport=self.project.generate_link, mail_transport=self.project.send_mail,
            account_origins=self.origins)
        self.settings, self.catalogue = StaffToolSettings(mail_daily_cap=mail_daily_cap), catalogue
        self.application, self._keys = None, {}

    def application_for(self, configuration):
        """The service with every staff part installed, for one transport configuration."""
        from .http import ServiceHttpApplication
        application = ServiceHttpApplication(self.runtime, self.identity.fixture.provisioning, configuration,
                                              browser_identity=self.browser, account_email=self.email,
                                              account_administration=self.administration)
        application.staff_tools = StaffTools(application, self.administration,
                                             StaffKeys(self.runtime, self.administration), self.settings,
                                             catalogue=self.catalogue)
        self.application = application
        return application

    @property
    def tools(self):
        if self.application is None:
            from .http import ServiceHttpConfiguration
            self.application_for(ServiceHttpConfiguration("http://127.0.0.1:9", ("127.0.0.1:9",),
                                                          allow_loopback_http=True))
        return self.application.staff_tools

    def session(self, name):
        token = self.identity.token(self.people[name])
        current = self.browser.authenticate(token)
        return self.administration.staff_session(current, hashlib.sha256(token.encode()).hexdigest()), token

    def member(self, name):
        return self.people[name] if name == "developer" else dict(PEOPLE)[name]

    def mint(self, name, **changes):
        staff, _token = self.session("owner")
        request = StaffKeyRequest("mint", uuid.uuid4().hex, staff_member=self.member(name),
                                  label="checks " + name, **changes)
        return self.tools.keys.apply(staff, request, new_request_reference())

    def actor(self, name, **changes):
        """A verified staff caller; one key for each staff member unless the check asks for another."""
        if changes or name not in self._keys:
            minted = self.mint(name, **changes)["key"]
            if changes:
                return self.tools.keys.authenticate(minted)
            self._keys[name] = minted
        return self.tools.keys.authenticate(self._keys[name])

    def call(self, actor, tool, arguments):
        return self.tools.call(actor, tool, arguments, new_request_reference(), "mcp")

    def plan_and_apply(self, actor, tool, arguments):
        arguments = {key: value for key, value in arguments.items() if key != "step"}
        planned = self.call(actor, tool, {"step": "plan", **arguments})
        return self.call(actor, tool, {"step": "apply", "plan_digest": planned["plan_digest"],
                                       "request_id": uuid.uuid4().hex, **arguments})

    def audit_rows(self):
        with self.runtime._catalog.store() as store:
            return [row["payload"] for row in self.runtime._catalog.rows_all(store, AUDIT)]

    def ledger(self, name):
        with self.runtime._catalog.store() as store:
            return credit_module.read_ledger(self.runtime, store, self.tenants[name])[1]


def _key_checks(check, world):
    minted = world.mint("owner")
    raw = minted["key"]
    stored = Path(world.runtime.config.database_path).read_bytes()
    replayed = world.tools.keys.apply(world.session("owner")[0], StaffKeyRequest(
        "mint", "fixed-request", staff_member="owner@example.com", label="replay"), new_request_reference())
    again = world.tools.keys.apply(world.session("owner")[0], StaffKeyRequest(
        "mint", "fixed-request", staff_member="owner@example.com", label="replay"), new_request_reference())
    actor = world.tools.keys.authenticate(raw)
    check("a_staff_key_is_shown_once_kept_as_a_digest_and_bound_to_its_role",
          raw.startswith("bsk_") and raw.encode() not in stored and hashlib.sha256(raw.encode()).hexdigest().encode()
          in stored and actor.role == SUPERADMIN and replayed["key"] and again["key"] is None
          and again["replayed"] is True and minted["expires_at"] - minted["minted_at"] == keys_module.DEFAULT_LIFETIME_SECONDS)
    customer_key = world.identity.fixture.keys["alpha"].key
    check("a_customer_or_host_key_is_never_a_staff_key_and_a_staff_key_never_a_customer_key",
          code_of(lambda: world.tools.keys.authenticate(customer_key)) == "staff_credential_required"
          and code_of(lambda: world.tools.keys.authenticate("bsk_" + "x" * 43)) == "staff_credential_required"
          and code_of(lambda: world.runtime.authenticate_key(raw)) == "unauthorized")
    staff, _token = world.session("owner")

    def revoked_refused():
        key = world.mint("numbers")
        world.tools.keys.apply(staff, StaffKeyRequest("revoke", uuid.uuid4().hex, key_id=key["key_id"]),
                               new_request_reference())
        return code_of(lambda: world.tools.keys.authenticate(key["key"])) == "staff_key_revoked"
    check("a_revoked_staff_key_is_refused_at_its_next_use", revoked_refused())
    with mutated(keys_module.StaffKeys, "_actor", "if key_state(value, now) == REVOKED:", "if False:"):
        check("removed_staff_key_revocation_is_detected", not revoked_refused())

    def expired_refused():
        key = world.mint("owner", lifetime_seconds=keys_module.SHORTEST_LIFETIME_SECONDS)
        with patch.object(world.runtime, "_clock", lambda: key["expires_at"] + 1):
            return code_of(lambda: world.tools.keys.authenticate(key["key"])) == "staff_key_expired"
    check("an_expired_staff_key_is_refused", expired_refused())
    with mutated(keys_module.StaffKeys, "_actor", "if key_state(value, now) == EXPIRED:", "if False:"):
        check("removed_staff_key_expiry_is_detected", not expired_refused())
    check("a_staff_key_lives_24_hours_by_default_and_never_past_seven_days",
          code_of(lambda: StaffKeyRequest("mint", "long", staff_member="owner@example.com", label="long",
                                          lifetime_seconds=8 * 86400)) == "invalid_staff_key_lifetime")
    # A plan made with a key that is revoked before the apply commits nothing.
    doomed = world.mint("owner")
    doomed_actor = world.tools.keys.authenticate(doomed["key"])
    arguments = {"tenant_id": world.tenants["second"], "downloads": 2, "reason": "revoked before apply"}
    planned = world.call(doomed_actor, "credits_grant", {"step": "plan", **arguments})
    world.tools.keys.apply(staff, StaffKeyRequest("revoke", uuid.uuid4().hex, key_id=doomed["key_id"]),
                           new_request_reference())
    applied = code_of(lambda: world.call(doomed_actor, "credits_grant", {
        "step": "apply", "plan_digest": planned["plan_digest"], "request_id": "after-revoke", **arguments}))
    check("a_plan_applied_after_its_key_was_revoked_commits_nothing",
          applied == "staff_key_revoked" and not world.ledger("second")["grants"])
    changed = StaffWorld.__new__(StaffWorld)
    changed.__dict__.update(world.__dict__)
    moved = ServiceAccountPolicy(staff=({"role": SUPERADMIN, "email": "owner@example.com"},
                                        {"role": ANALYTICS, "provider_user_id": world.people["developer"]}))
    developer_key = world.mint("developer")["key"]
    keys = StaffKeys(world.runtime, AccountAdministration(world.runtime, moved, world.identity.issuer))
    check("a_staff_key_whose_member_changed_role_is_refused",
          code_of(lambda: keys.authenticate(developer_key)) == "staff_key_role_changed")
    check("a_staff_key_can_mint_no_key", code_of(lambda: world.tools.keys.apply(
        world.tools.keys.authenticate(raw), StaffKeyRequest("mint", "by-key", staff_member="owner@example.com",
                                                            label="x"), new_request_reference())) is not None)


SUPERADMIN_ONLY = ("account_get", "account_action", "credits_grant", "credits_revoke", "message_send",
                   "accounts_invite", "accounts_import", "catalogue_publish", "catalogue_rollback", "item_withdraw")


def _superadmin_only_calls(world):
    customer = world.tenants["first"]
    return (("account_get", {"tenant_id": customer}),
            ("account_action", {"step": "plan", "operation": "disable", "tenant_id": customer}),
            ("credits_grant", {"step": "plan", "tenant_id": customer, "downloads": 5, "reason": "not allowed"}),
            ("credits_revoke", {"step": "plan", "tenant_id": customer, "grant_id": "0" * 32, "reason": "none"}),
            ("message_send", {"step": "plan", "purpose": "service_notice", "subject": "Hi", "body": "Hi",
                              "tenant_id": customer}),
            ("accounts_invite", {"step": "plan", "addresses": ["someone.new@example.com"]}),
            ("accounts_import", {"step": "plan", "csv": "email\nsomeone.new@example.com\n"}),
            ("catalogue_publish", {"step": "plan", "bundle": "any", "expected_bundle_digest": "0" * 64}),
            ("catalogue_rollback", {"step": "plan", "to_release": "0" * 64}),
            ("item_withdraw", {"step": "plan", "identity": "skill.alpha", "note": "not allowed"}))


def _limited_roles_hold(world, developer, analytics):
    """Developer and analytics reach no superadmin operation and change nothing; analytics reads no address."""
    before = (world.ledger("first"), len(world.project.messages))
    codes = [code_of(lambda: world.call(actor, name, arguments))
             for actor in (developer, analytics) for name, arguments in _superadmin_only_calls(world)]
    codes += [code_of(lambda: world.call(developer, "accounts_search", {})),
              code_of(lambda: world.call(analytics, "service_health", {}))]
    counts = world.call(analytics, "accounts_search", {})["result"]
    activity = world.call(analytics, "activity_search", {})["result"]
    return (codes == ["staff_tool_forbidden"] * len(codes)
            and counts["record_type"] == account_tools.ACCOUNT_COUNTS_VERSION and "@" not in json.dumps(counts)
            and counts["total"] == len(PEOPLE) and activity["record_type"] == COUNTS_VERSION
            and code_of(lambda: world.call(analytics, "accounts_search", {"text": "first"})) == "address_search_forbidden"
            and (world.ledger("first"), len(world.project.messages)) == before)


def _role_checks(check, world):
    developer, analytics = world.actor("developer"), world.actor("numbers")
    check("developer_and_analytics_reach_no_superadmin_tool_and_analytics_reads_no_address",
          _limited_roles_hold(world, developer, analytics))
    with patch.object(keys_module, "permissions_for", lambda role: ROLE_PERMISSIONS[SUPERADMIN]):
        check("removed_staff_tool_permission_table_is_detected", not _limited_roles_hold(world, developer, analytics))
    with mutated(account_tools, "accounts_search", "if not rows_allowed and fields.get(\"text\"):", "if False:"), \
            patch.dict(world.tools.tools, {"accounts_search": replace(world.tools.tools["accounts_search"],
                                                                      run=account_tools.accounts_search)}):
        check("removed_address_filter_guard_for_counts_is_detected", not _limited_roles_hold(world, developer, analytics))
    listed = {tool.name for tool in world.tools.visible(analytics)}
    check("the_analytics_tool_list_names_only_what_it_may_call",
          listed == {"accounts_search", "activity_search", "data_search", "catalogue_status"}
          and {tool.name for tool in world.tools.visible(developer)}
          == {"activity_search", "data_search", "catalogue_status", "service_health"}
          and len(world.tools.visible(world.actor("owner"))) == 15)


def _plan_checks(check, world):
    owner = world.actor("owner")
    arguments = {"tenant_id": world.tenants["first"], "downloads": 3, "valid_days": 7, "reason": "support gesture"}
    audit_before = len(world.audit_rows())
    planned = world.call(owner, "credits_grant", {"step": "plan", **arguments})

    def apply(**changes):
        chosen = {"step": "apply", "plan_digest": planned["plan_digest"], "request_id": "grant-1", **arguments}
        chosen.update(changes)
        return world.call(owner, "credits_grant", chosen)
    wrong = code_of(lambda: apply(plan_digest="0" * 64))
    other = code_of(lambda: apply(downloads=4))
    missing = code_of(lambda: world.call(owner, "credits_grant", {"step": "apply", **arguments}))
    unchanged = not world.ledger("first")["grants"]
    applied = apply()
    replayed = apply()
    stale = code_of(lambda: apply(request_id="grant-2"))
    grants = world.ledger("first")["grants"]
    check("an_apply_names_the_digest_of_the_plan_for_the_same_arguments_and_state",
          planned["plan"]["remaining_after"] == 3 and wrong == other == "plan_changed"
          and missing == "plan_digest_required" and unchanged and applied["result"]["committed"] is True
          and replayed["replayed"] is True and stale == "plan_changed" and len(grants) == 1
          and grants[0]["downloads"] == 3 and grants[0]["reason"] == "support gesture")
    with mutated(StaffTools, "call", "if not secrets.compare_digest(given, current):", "if False:"):
        before = len(world.ledger("first")["grants"])
        code_of(lambda: apply(plan_digest="0" * 64, request_id="grant-mutant"))
        check("removed_plan_digest_comparison_is_detected", len(world.ledger("first")["grants"]) != before)
    rows = world.audit_rows()
    check("every_staff_tool_call_writes_one_audit_record_with_its_request_reference",
          len(rows) - audit_before >= 8 and all(valid_reference(row["request_reference"]) for row in rows)
          and {row["outcome"] for row in rows[audit_before:]} == {"ok", "refused"}
          and "support gesture" not in json.dumps(rows))
    with patch("loop_engine.core.service_runtime.staff_tools.write_audit", lambda *args, **kwargs: None):
        before = len(world.audit_rows())
        world.call(owner, "service_health", {})
        check("removed_audit_record_is_detected", len(world.audit_rows()) == before)
    grant_id = grants[0]["grant_id"]
    held = credit_module.summary(world.ledger("first"), world.runtime._now())["remaining"]
    revoked = world.plan_and_apply(owner, "credits_revoke", {"tenant_id": world.tenants["first"], "grant_id": grant_id,
                                                            "reason": "gesture ended"})
    check("revoking_a_credit_grant_ends_its_unused_downloads",
          revoked["result"]["downloads_forfeited"] == 3
          and credit_module.summary(world.ledger("first"), world.runtime._now())["remaining"] == held - 3)
    protected = code_of(lambda: world.call(owner, "account_action", {
        "step": "plan", "operation": "disable", "tenant_id": world.tenants["numbers"]}))
    switched = world.plan_and_apply(owner, "account_action", {"operation": "disable",
                                                             "tenant_id": world.tenants["second"]})
    check("a_staff_tool_switches_a_customer_off_and_never_a_staff_member",
          protected == "staff_account_protected" and switched["result"]["enabled"] is False)
    with mutated(account_tools, "_action_rows", "        _protect_staff_accounts(tools, store, tenant_id)\n", "        pass\n"):
        check("removed_staff_account_protection_is_detected", code_of(lambda: world.call(owner, "account_action", {
            "step": "plan", "operation": "disable", "tenant_id": world.tenants["numbers"]})) != "staff_account_protected")


def _credit_reads(fixture, runtime, tenant, grants, *, later=None):
    """Grant `grants` (downloads, lifetime) to one account, then read until refused; the codes of each read."""
    now = int(runtime._now())
    with runtime._catalog.store(write=True) as store:
        for downloads, lifetime in grants:
            rows, guards, _detail = credit_module.grant_rows(runtime, store, credit_module.CreditGrant(
                tenant, downloads, now + lifetime, "credit checks"), "checks", now)
            runtime._catalog.commit(store, rows, guards)
    codes, key = [], fixture.keys[tenant].key
    clock = (lambda: later) if later is not None else runtime._clock
    with patch.object(runtime, "_clock", clock):
        for index in range(4):
            codes.append(code_of(lambda: fixture.provisioning.invoke(key, "read", identity="skill.alpha" if tenant ==
                                                                   "alpha" else "skill.beta", request_id="r" + str(index))))
        codes.append(code_of(lambda: fixture.provisioning.invoke(key, "read", identity="skill.alpha" if tenant ==
                                                               "alpha" else "skill.beta", request_id="r0")))
    return codes


def _credit_checks(check, root):
    from .http_test_fixtures import HttpDomainFixture
    (root / "credits").mkdir()
    fixture = HttpDomainFixture(root / "credits", operator_access=False)
    runtime = fixture.runtime
    honoured = _credit_reads(fixture, runtime, "alpha", [(2, 3600)])
    with runtime._catalog.store() as store:
        ledger = credit_module.read_ledger(runtime, store, "alpha")[1]
    usage = fixture.usage("alpha")
    check("credits_are_honoured_by_metering_one_download_each_and_a_repeat_draws_nothing",
          honoured == [None, None, "body_forbidden", "body_forbidden", None] and ledger["drawn"] == 2
          and usage["records"] == 2 and credit_module.summary(ledger, runtime._now())["remaining"] == 0)
    expired = _credit_reads(fixture, runtime, "beta", [(5, 3600)], later=int(runtime._now()) + 7200)
    check("credits_are_refused_after_their_expiry", expired[:4] == ["body_forbidden"] * 4)
    with mutated(credit_module, "usable", "and type(grant.get(\"expires_at\")) is int and grant[\"expires_at\"] > now",
                 ""):
        (root / "credits-mutant").mkdir()
        mutant = HttpDomainFixture(root / "credits-mutant", operator_access=False)
        check("removed_credit_expiry_is_detected",
              _credit_reads(mutant, mutant.runtime, "beta", [(5, 3600)],
                            later=int(mutant.runtime._now()) + 7200)[0] is None)
    (root / "planned").mkdir()
    planned = HttpDomainFixture(root / "planned")
    codes = _credit_reads(planned, planned.runtime, "alpha", [(1, 3600)])
    with planned.runtime._catalog.store() as store:
        held = credit_module.read_ledger(planned.runtime, store, "alpha")[1]
    check("an_account_with_a_plan_downloads_under_the_plan_and_draws_no_credit",
          codes[:4] == [None] * 4 and held["drawn"] == 0)


def _message_checks(check, root):
    with signed_identity(root / "messages", operator_access=False) as identity:
        world = StaffWorld(identity, mail_daily_cap=2)
        owner = world.actor("owner")
        first = world.tenants["first"]
        sent_before = len(world.project.messages)

        def message(**changes):
            arguments = {"step": "plan", "purpose": "service_notice", "subject": "Planned maintenance",
                         "body": "The service is read-only on Sunday for one hour.", "tenant_id": first}
            arguments.update(changes)
            return {key: value for key, value in arguments.items() if value is not None}
        refusals = [code_of(lambda: world.call(owner, "message_send", message(purpose=None))),
                    code_of(lambda: world.call(owner, "message_send", message(purpose="marketing"))),
                    code_of(lambda: world.call(owner, "message_send", message(purpose="Newsletter"))),
                    code_of(lambda: world.call(owner, "message_send", message(tenant_id=None, audience={})))]
        check("a_message_without_a_service_purpose_or_for_marketing_is_refused_before_anything_is_sent",
              refusals == ["message_service_purpose_required", "marketing_needs_recorded_consent",
                           "marketing_needs_recorded_consent", "staff_mail_daily_cap_reached"]
              and len(world.project.messages) == sent_before)
        with mutated(message_module, "purpose_of", "    if value in SERVICE_PURPOSES:\n        return value\n",
                     "    return value\n"):
            check("removed_service_purpose_rule_is_detected",
                  code_of(lambda: world.call(owner, "message_send", message(purpose="marketing"))) is None)
        planned = world.call(owner, "message_send", message())
        preview = planned["plan"]["preview"]
        sent = world.call(owner, "message_send", {**message(step="apply"), "plan_digest": planned["plan_digest"],
                                                  "request_id": "message-1"})
        delivered = world.project.messages[sent_before:]
        check("a_service_message_is_previewed_then_sent_inside_the_template",
              sent["result"]["sent"] == 1 and len(delivered) == 1
              and delivered[0]["to"] == "first.customer@example.com" and delivered[0]["subject"] == preview["subject"]
              and "It is not marketing" in delivered[0]["text"] and delivered[0]["text"] == preview["body"]
              and planned["plan"]["first_recipients"][0]["address_hint"] == "f***@example.com")
        # One message left today. A plan for one fits; after another send uses
        # the last one, the same plan's apply is refused and sends nothing.
        waiting = world.call(owner, "message_send", message())
        world.plan_and_apply(owner, "message_send", message(tenant_id=world.tenants["second"]))
        over = code_of(lambda: world.call(owner, "message_send", {**message(step="apply"),
                                                                   "plan_digest": waiting["plan_digest"],
                                                                   "request_id": "message-over"}))
        check("a_message_over_the_staff_daily_allowance_is_refused_at_plan_and_at_apply",
              over == "staff_mail_daily_cap_reached" and len(world.project.messages) == sent_before + 2
              and message_module.allowance(world.tools)["remaining"] == 0)
        with mutated(message_module, "reservation", "        if value[\"sent\"] + count > cap:", "        if False:"), \
                mutated(message_module, "require_allowance", "    if count > held[\"remaining\"]:", "    if False:"):
            check("removed_daily_message_allowance_is_detected", code_of(lambda: world.plan_and_apply(
                owner, "message_send", message(tenant_id=world.tenants["second"]))) is None)


IMPORT_CSV = ("Timestamp,Email Address,Name,Password\n"
              "2026-09-24,new.one@example.com,One,\n"
              "2026-09-24,new.two@example.com,Two,hunter2-typed-by-someone\n"
              "2026-09-24,NEW.ONE@example.com,Again,\n"
              "2026-09-24,not-an-address,Bad,\n"
              "2026-09-24,first.customer@example.com,Known,\n")


def _import_outcomes(world, owner):
    planned = world.call(owner, "accounts_import", {"step": "plan", "csv": IMPORT_CSV})
    return planned, [row["outcome"] for row in planned["plan"]["row_outcomes"]]


def _import_checks(check, root):
    with signed_identity(root / "imports", operator_access=False) as identity:
        world = StaffWorld(identity)
        owner = world.actor("owner")
        planned, outcomes = _import_outcomes(world, owner)
        expected = ["send", "second_way_in", "duplicate", "invalid_address", "address_has_an_account"]
        applied = world.call(owner, "accounts_import", {"step": "apply", "csv": IMPORT_CSV,
                                                        "plan_digest": planned["plan_digest"], "request_id": "import-1"})
        created = world.project.users.get("new.one@example.com")
        audit = json.dumps(world.audit_rows())
        check("an_import_row_that_would_create_a_second_way_in_is_refused_and_its_value_never_kept",
              outcomes == expected and planned["plan"]["authority_columns"] == ["password"]
              and planned["plan"]["row_outcomes"][1]["columns"] == ["password"]
              and "hunter2" not in json.dumps(planned) and "hunter2" not in audit
              and "new.two@example.com" not in world.project.users)
        check("imported_rows_are_validated_deduplicated_and_sent_through_the_one_way_in",
              applied["result"]["sent"] == 1 and created is not None
              and created["app_metadata"].get(ACCOUNT_MARKER) == ACCOUNT_MARK
              and origin_of(world.runtime, identity.issuer, created["id"]) is not None
              and [message["to"] for message in world.project.messages] == ["new.one@example.com"]
              and planned["plan"]["ignored_columns"] == ["timestamp", "name"])
        with mutated(import_module, "carries_authority",
                     "    return name in AUTHORITY_COLUMNS or any(word in name for word in AUTHORITY_WORDS)",
                     "    return False"):
            check("removed_second_way_in_guard_is_detected", _import_outcomes(world, owner)[1][1] != "second_way_in")
        from .staff_sign_up_links import LINK, PENDING
        with world.runtime._catalog.store() as store:
            link = world.runtime._catalog.read(store, LINK, (identity.issuer, created["id"]))["payload"]
        check("an_imported_sign_up_uses_the_staff_sign_up_link_and_leaves_its_pending_record",
              link["state"] == PENDING and link["free_monthly"] is False and link["sent_by_role"] == SUPERADMIN
              and link["sent_by_subject"].startswith("staff_key:")
              and "invited you" in world.project.messages[-1]["subject"])
        chosen = world.plan_and_apply(owner, "accounts_invite", {"addresses": ["monthly.person@example.com"],
                                                                 "free_monthly": True})
        person = world.project.users["monthly.person@example.com"]
        identity.people[person["id"]] = {"email": "monthly.person@example.com",
                                         "app_metadata": {ACCOUNT_MARKER: ACCOUNT_MARK}}
        opened = world.browser.activate(identity.token(person["id"]))
        account = world.call(owner, "account_get", {"tenant_id": opened["tenant_id"]})["result"]
        check("a_sign_up_link_with_free_monthly_opens_an_account_that_includes_baltor_pro",
              chosen["result"]["sent"] == 1 and opened.get("sign_up_link") == "activated"
              and account["plan"]["state"] == "free_monthly")
        developer = world.actor("developer")
        check("free_monthly_on_a_sign_up_link_needs_the_grant_permission", code_of(lambda: world.call(
            developer, "accounts_invite", {"step": "plan", "addresses": ["x.person@example.com"],
                                           "free_monthly": True})) == "staff_tool_forbidden")
        rows = world.call(owner, "accounts_import", {"step": "plan", "rows": [
            {"email": "json.row@example.com", "email_confirmed": True}, {"email": "json.two@example.com"}]})
        invited = world.call(owner, "accounts_invite", {"step": "plan", "addresses": [
            "typed.one@example.com", "TYPED.ONE@example.com", "second.customer@example.com", "new.one@example.com"]})
        check("typed_addresses_and_json_rows_follow_the_same_rules",
              [row["outcome"] for row in rows["plan"]["row_outcomes"]] == ["second_way_in", "send"]
              and [row["outcome"] for row in invited["plan"]["row_outcomes"]]
              == ["send", "duplicate", "address_has_an_account", "sign_up_pending"])


def _catalogue_checks(check, root):
    from . import staff_tool_catalogue as catalogue_tools
    from .catalogue_bundle import write_bundle
    from .catalogue_release_checks import SCHEMA, _policies, skill
    from .catalogue_releases import CatalogueOperatorContext, status
    from .catalogue_schema import CatalogueAttributeSchema
    from .staff_tool_catalogue import StaffCatalogue
    from .storage import ServiceCatalogBinding
    with signed_identity(root / "catalogue", operator_access=False) as identity:
        bodies, incoming = (root / "catalogue-bodies").resolve(), (root / "incoming").resolve()
        bodies.mkdir()
        incoming.mkdir()
        license_policy, family_policy = _policies()
        context = CatalogueOperatorContext(ServiceCatalogBinding(identity.fixture.runtime.config), str(bodies))
        world = StaffWorld(identity, catalogue=StaffCatalogue(context, str(incoming), license_policy, family_policy))
        owner = world.actor("owner")

        def bundle(name, items):
            return write_bundle(incoming / name, schema=CatalogueAttributeSchema.from_dict(SCHEMA),
                                lines=[skill(item, text) for item, text in items],
                                payloads=[text.encode() for _item, text in items])

        def publish(name, digest_value):
            return world.plan_and_apply(owner, "catalogue_publish", {"bundle": name,
                                                                      "expected_bundle_digest": digest_value})
        first = bundle("first", [("skill.one", "One body for the staff tool check"),
                                 ("skill.two", "Two body for the staff tool check")])
        wrong = code_of(lambda: world.call(owner, "catalogue_publish", {"step": "plan", "bundle": "first",
                                                                       "expected_bundle_digest": "0" * 64}))
        missing = code_of(lambda: world.call(owner, "catalogue_publish", {"step": "plan", "bundle": "absent",
                                                                         "expected_bundle_digest": first}))
        published = publish("first", first)["result"]
        listed = world.call(owner, "catalogue_status", {})["result"]
        check("catalogue_publish_keeps_the_bundle_digest_guard_and_needs_no_redeploy",
              wrong == "bundle_digest_mismatch" and missing == "catalogue_bundle_not_found"
              and published["state"] == "published" and status(context)["active_release_id"] == published["release_id"]
              and listed["store"]["active_release_id"] == published["release_id"]
              and listed["incoming_bundles"] == ["first"])
        with mutated(catalogue_tools, "publish_plan", "if bundle.digest != fields[\"expected_bundle_digest\"]:",
                     "if False:"), patch.dict(world.tools.tools, {"catalogue_publish": replace(
                         world.tools.tools["catalogue_publish"], run=catalogue_tools.publish_plan)}):
            check("removed_bundle_digest_guard_is_detected", code_of(lambda: world.call(
                owner, "catalogue_publish", {"step": "plan", "bundle": "first", "expected_bundle_digest": "0" * 64}))
                  is None)
        second = publish("second", bundle("second", [("skill.one", "One body, second edition")]))["result"]
        back = world.call(owner, "catalogue_rollback", {"step": "plan", "to_release": published["release_id"]})
        third = publish("third", bundle("third", [("skill.three", "Three body for the staff tool check")]))["result"]
        stale = code_of(lambda: world.call(owner, "catalogue_rollback", {
            "step": "apply", "to_release": published["release_id"], "plan_digest": back["plan_digest"],
            "request_id": "stale-rollback"}))
        rolled = world.plan_and_apply(owner, "catalogue_rollback", {"to_release": second["release_id"]})["result"]
        withdrawn = world.plan_and_apply(owner, "item_withdraw", {"identity": "skill.one",
                                                                  "note": "withdrawn by the staff tool check"})
        check("rollback_and_withdrawal_run_from_a_plan_against_the_active_release",
              third["state"] == "published" and stale == "plan_changed"
              and status(context)["active_release_id"] == second["release_id"] == rolled["release_id"]
              and withdrawn["result"]["state"] == "withdrawn" and status(context)["durable_withdrawals"] == 1)


def run_checks(check, root):
    root = Path(root)
    with signed_identity(root / "staff", operator_access=False) as identity:
        world = StaffWorld(identity)
        _key_checks(check, world)
        _role_checks(check, world)
        _plan_checks(check, world)
    _credit_checks(check, root)
    _message_checks(check, root)
    _import_checks(check, root)
    _catalogue_checks(check, root)
