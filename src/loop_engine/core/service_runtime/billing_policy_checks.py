"""Checks for re-applying the billing policies and for the health check that names their drift.

The known-wrong case of this module is the state release 13 served: a host
whose stored session policy holds the digest an older release computed from
the same host file. Checkout and the portal were unavailable, the health record
said nothing, and no command could repair it. Every guard here is shown doing
its job and refusing that case, and the removed-guard controls at the end rerun
a named scenario with one guard taken away and require its predicate to fail.

The host file is real and goes through the real loader, the real entry point
and the served routes, driven through the application's own ASGI interface
with no socket. No provider is contacted: the session transport and the secret
resolver are replaced by recorders, so a check can show that nothing reached
either of them.
"""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
from dataclasses import asdict, field, fields, make_dataclass, replace
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from unittest.mock import patch

from . import billing_effects, billing_policy as policy_module, http_entrypoint, observability, stripe_sessions
from .billing_effects import (
    BillingSessionEffectStore, BillingSessionPolicyDefinition, SESSION_POLICY_KIND, SESSION_POLICY_VERSION,
    SESSION_TERMS_VERSION,
)
from .billing_policy import APPLICATION_VERSION, PAID_ACCESS_REFUSAL, REFUSAL_VERSION
from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, configure_host, load_host_application, main
from .observability import BILLING_POLICY_CHECK, ReadinessCheck
from .records import ServiceRuntimeError, canonical, digest
from .runtime import BILLING_POLICY
from .stripe_sessions import SESSION_OPERATION_FIELDS, StripeSessionConfiguration, StripeSessionPlan

HOST, ACCOUNT, API = "service.example", "acct_fixture", "fixture_version"
KEY_REFERENCE, SIGNING_REFERENCE = "LOCAL_BILLING_POLICY_KEY", "LOCAL_BILLING_POLICY_SIGNING"
#: What the two environment references hold during a check. Neither value may
#: appear in anything the command prints.
MARKERS = {KEY_REFERENCE: "LOCAL-BILLING-POLICY-KEY-MARKER-7d41",
           SIGNING_REFERENCE: "LOCAL-BILLING-POLICY-SIGNING-MARKER-2b9e"}
SESSIONS = {"account_id": ACCOUNT, "api_version": API, "api_key_ref": "env:" + KEY_REFERENCE,
            "plans": [{"plan_ref": "pro", "label": "Pro", "price_id": "price_basic"}],
            "checkout_success_url": "https://service.example/app", "checkout_cancel_url": "https://service.example/app",
            "portal_return_url": "https://service.example/app", "portal_configuration_id": "bpc_fixture",
            "allow_network": True, "allow_session_creation": True}


def host_file(root, *, billing=True, sessions=None, allowed_prices=("price_basic",)):
    """Write one host file whose billing installs sessions, unless told otherwise, and its empty manifest."""
    root = Path(root)
    (root / "manifest.json").write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(root),
                                                    "items": []}))
    host = {"record_type": HOST_CONFIGURATION_VERSION,
            "runtime": {"database_path": str(root / "service.db"), "writes_authorized": True},
            "http": {"public_base_url": "https://" + HOST, "allowed_hosts": [HOST]},
            "authentication": {"modes": ["host_key"]}, "manifest_path": str(root / "manifest.json"),
            "tenants": [{"tenant_id": "alpha", "namespace": "tenant:alpha",
                         "billing_customer": {"provider_customer_id": "cus_alpha", "provider_account_id": ACCOUNT}}]}
    if billing:
        host["billing"] = {"webhook": {"account_id": ACCOUNT, "api_version": API,
                                       "signing_secret_refs": ["env:" + SIGNING_REFERENCE]},
                           "policy": {"allowed_price_ids": list(allowed_prices)}}
        if sessions is not False:
            host["billing"]["sessions"] = {**SESSIONS, **(sessions or {})}
    path = root / "host.json"
    path.write_text(json.dumps(host))
    return path


def rewrite(path, change):
    """Change the host file on disk, as an operator or a new release would."""
    host = json.loads(Path(path).read_text())
    change(host)
    Path(path).write_text(json.dumps(host))


def served(application, route):
    """One GET of a served route through the application's own ASGI interface. No socket is opened."""
    app, sent = application.create_app(), []

    async def exchange():
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET",
                 "scheme": "https", "path": route, "raw_path": route.encode(), "query_string": b"",
                 "root_path": "", "headers": [(b"host", HOST.encode())], "client": ("127.0.0.1", 40000),
                 "server": (HOST, 443)}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)
        await app(scope, receive, send)
    asyncio.run(exchange())
    return json.loads(b"".join(message.get("body", b"") for message in sent
                               if message["type"] == "http.response.body"))


def health_row(application):
    health = served(application, "/api/v1/health")["result"]
    return health, next(row for row in health["checks"] if row["name"] == BILLING_POLICY_CHECK)


def apply(path, *arguments):
    """Run the operator command through the service entry point. Return status, record and printed text."""
    printed = io.StringIO()
    with redirect_stdout(printed):
        status = main(["apply-billing-policy", "--config", str(path), *arguments])
    return status, json.loads(printed.getvalue()), printed.getvalue()


def refusal(function):
    try:
        function()
    except ServiceRuntimeError as error:
        return error.code
    return ""


def refused_code(path, *arguments):
    """The code of a refusal the command printed, or empty text when it printed none.

    A refusal raised instead of printed is returned with a prefix, so a
    scenario that expects the printed record cannot mistake it for one.
    """
    try:
        status, record, _printed = apply(path, *arguments)
    except ServiceRuntimeError as error:
        return "raised:" + error.code
    return record.get("code", "") if status == 1 and record.get("record_type") == REFUSAL_VERSION else ""


def stored(path):
    """Every row the durable store holds, as text, so that an unchanged store can be shown."""
    connection = sqlite3.connect(str(Path(path).parent / "service.db"))
    try:
        return json.dumps(connection.execute("SELECT * FROM records ORDER BY 1").fetchall(), default=str)
    finally:
        connection.close()


def configuration(**changes):
    settings = {**SESSIONS, **changes}
    return StripeSessionConfiguration(**{**settings, "plans": tuple(StripeSessionPlan(**row) for row in settings["plans"])})


def plant_older_terms(application):
    """Store the terms an older release computed from the same host file: the field release 13 added is missing."""
    sessions = application.billing_sessions
    terms = json.loads(sessions.configuration.policy_definition().policy_json)
    del terms["allow_promotion_codes"]
    older = BillingSessionPolicyDefinition(canonical(terms), tuple(plan.price_id for plan in sessions.configuration.plans))
    held = sessions.effects.held_policy()
    sessions.effects.configure_policy(older, expected_version=held["record_version"] if held else None)
    return older.digest


def configured(root, **host):
    path = host_file(root, **host)
    configure_host(str(path))
    application, _configuration = load_host_application(str(path))
    return path, application


def paid_account(application, tenant="alpha", customer="cus_alpha"):
    """Give one account paid access through a signed subscription notification, decided under the held policy."""
    from .billing import StripeEventProcessor
    from .billing_records import (StripeCustomerSubscriptionSnapshot, StripeSubscriptionResolver,
                                  StripeSubscriptionState, StripeWebhookConfig)
    now, secret = int(time.time()), "local-billing-policy-signing-fixture"
    period = StripeSubscriptionState("sub_" + tenant, customer, "active", (("price_basic", now + 3600),), True)
    snapshot = StripeCustomerSubscriptionSnapshot(ACCOUNT, customer, API, False, (period,), "b" * 64)
    processor = StripeEventProcessor(application.runtime, StripeWebhookConfig(ACCOUNT, API, ("env:UNUSED",)),
        application.billing_processor.policy, lambda _reference: secret,
        StripeSubscriptionResolver("fixture:current", lambda _customer: snapshot))
    payload = json.dumps({"id": "evt_paid_" + tenant, "object": "event", "api_version": API, "livemode": False,
                          "created": now, "type": "customer.subscription.updated",
                          "data": {"object": {"id": "sub_" + tenant, "customer": customer}}}).encode()
    signed = hmac.new(secret.encode(), str(now).encode() + b"." + payload, hashlib.sha256).hexdigest()
    return processor.handle(payload, f"t={now},v1={signed}").status


def paying(application):
    return application.runtime.access_source_report()["counts"]["revenue_bearing"]


def a_new_entitlement_policy(host):
    host["billing"]["policy"]["allowed_price_ids"] = ["price_basic", "price_new"]


# Scenarios. Each returns one predicate, so a removed-guard control can rerun
# it with one guard taken away and require the predicate to fail.

def drift_is_named_by_the_health_record(root):
    """The release 13 state: the adapter is installed and its stored policy is not current."""
    _path, application = configured(root)
    plant_older_terms(application)
    health, row = health_row(application)
    installed = next(item for item in health["checks"] if item["name"] == "billing_sessions_installed")
    return (health["ready"] is True and installed["passed"] is True and row["required"] is False
            and row["passed"] is False and row["code"] == "session_policy_changed")


def the_command_repairs_the_drift(root):
    """The running service keeps its adapter; the command, a separate process, repairs the store it reads."""
    path, running = configured(root)
    plant_older_terms(running)
    before = served(running, "/api/v1/capabilities")["result"]["billing"]
    status, record, _printed = apply(path)
    after = served(running, "/api/v1/capabilities")["result"]["billing"]
    _health, row = health_row(running)
    return (before["checkout"] is False and before["portal"] is False and status == 0
            and record["every_installed_policy_current"] is True and record["changed"] is True
            and after["checkout"] is True and after["portal"] is True and row["passed"] is True)


def a_concurrent_writer_is_refused_not_overwritten(root):
    """Another writer changes the session policy after the command read its version and before it wrote."""
    path, application = configured(root)
    plant_older_terms(application)
    other = BillingSessionPolicyDefinition(canonical({"record_type": SESSION_TERMS_VERSION, "writer": "other"}),
                                           ("price_basic",))
    read = BillingSessionEffectStore.held_policy

    def read_then_lose_the_race(self):
        held = read(self)
        self.configure_policy(other, expected_version=held["record_version"])
        return held
    with patch.object(BillingSessionEffectStore, "held_policy", read_then_lose_the_race):
        code = refused_code(path)
    kept = application.billing_sessions.effects.held_policy()
    return code == "session_policy_revision_required" and kept["policy_digest"] == other.digest


def prices_outside_the_billing_policy_change_nothing(root):
    """A host file names a new entitlement policy and a session price outside it; nothing is written."""
    path, _application = configured(root)
    rewrite(path, lambda host: (a_new_entitlement_policy(host), host["billing"]["sessions"]["plans"].append(
        {"plan_ref": "team", "label": "Team", "price_id": "price_other"})))
    before = stored(path)
    code = refused_code(path)
    return code == "session_price_not_in_billing_policy" and stored(path) == before


def paid_access_is_not_ended_without_the_operator_saying_so(root):
    """A changed entitlement policy while one account has paid access under the held one."""
    path, application = configured(root)
    granted = paid_account(application)
    rewrite(path, a_new_entitlement_policy)
    before = stored(path)
    code = refused_code(path)
    return (granted == "applied" and code == PAID_ACCESS_REFUSAL and stored(path) == before
            and paying(application) == 1)


def each_term_changes_the_policy_digest(_root=None):
    """The known-wrong cases of a narrower digest: each of these changes what a customer is charged or sees."""
    base = configuration()
    plan = base.plans[0]
    changes = {"price": {"plans": (replace(plan, price_id="price_other"),)},
               "quantity": {"plans": (replace(plan, quantity=2),)},
               "plan reference": {"plans": (replace(plan, plan_ref="team"),)},
               "plan label": {"plans": (replace(plan, label="Team"),)},
               "account": {"account_id": "acct_other"},
               "success address": {"checkout_success_url": "https://service.example/other"},
               "cancel address": {"checkout_cancel_url": "https://service.example/other"},
               "portal return address": {"portal_return_url": "https://service.example/other"},
               "portal configuration": {"portal_configuration_id": "bpc_other"},
               "livemode": {"livemode": True}, "promotion codes": {"allow_promotion_codes": True},
               "provider version": {"api_version": "fixture_version_2"}}
    held = base.policy_definition().digest
    return all(replace(base, **change).policy_definition().digest != held for change in changes.values())


def each_operational_setting_leaves_the_policy_digest(_root=None):
    base = configuration()
    changes = ({"timeout_seconds": 20.0}, {"maximum_response_bytes": 2_000_000}, {"reconciliation_seconds": 7200},
               {"allow_network": False}, {"allow_session_creation": False}, {"api_key_ref": "env:OTHER_KEY"},
               {"allow_loopback_return_urls": True})
    held = base.policy_definition().digest
    return all(replace(base, **change).policy_definition().digest == held for change in changes)


def version_one_records_are_neither_read_nor_overwritten(root):
    """Only a version one record is stored, in the slot the older releases read."""
    path, application = configured(root, sessions=False)
    catalog = application.runtime._catalog
    older = asdict(configuration())
    del older["allow_promotion_codes"]
    with catalog.store(write=True) as store:
        billing = catalog.read(store, BILLING_POLICY, "stripe")
        old = catalog.record(SESSION_POLICY_KIND, "stripe", {
            "record_type": "service_billing_session_policy/v1", "policy": older,
            "policy_digest": digest({"policy": older, "price_ids": ["price_basic"]}),
            "billing_policy_digest": billing["payload"]["policy_digest"]})
        catalog.commit(store, (old,), (catalog.guard(None, old["record_id"]),))
    rewrite(path, lambda host: host["billing"].update(sessions=dict(SESSIONS)))
    running, _configuration = load_host_application(str(path))
    unread = running.billing_sessions.options()["unavailable_reason"]
    try:
        status, record, _printed = apply(path)
    except ServiceRuntimeError:
        return False  # a command that cannot write the record of its own version fails this scenario
    with catalog.store() as store:
        left = catalog.read(store, SESSION_POLICY_KIND, "stripe")
    return (unread == "session_record_unavailable" and status == 0 and record["session_policy"]["changed"] is True
            and left is not None and left["record_version"] == old["record_version"] and left["payload"] == old["payload"]
            and record["session_policy"]["other_record_versions"] == ["service_billing_session_policy/v1"]
            and running.billing_sessions.options()["checkout_available"] is True)


def _drift_checks(check, root):
    path, running = configured(root / "drift")
    running_digest = running.billing_sessions.policy_digest
    older = plant_older_terms(running)
    capabilities = served(running, "/api/v1/capabilities")["result"]["billing"]
    check("a_stored_session_policy_an_older_release_wrote_leaves_checkout_and_the_portal_unavailable",
          capabilities["checkout"] is False and capabilities["portal"] is False
          and running.billing_sessions.options()["unavailable_reason"] == "session_policy_changed")
    health = json.dumps(served(running, "/api/v1/health"))
    check("the_health_record_names_the_drift_without_a_digest",
          "session_policy_changed" in health and older not in health and running_digest not in health)
    status, first, _printed = apply(path)
    session = first["session_policy"]
    check("apply_billing_policy_reports_the_held_and_the_applied_digests",
          status == 0 and first["record_type"] == APPLICATION_VERSION and session["record_type"] == SESSION_POLICY_VERSION
          and session["held_policy_digest"] == older and session["policy_digest"] == running_digest
          and session["held_record_version"] != session["record_version"] and session["changed"] is True
          and first["billing_policy"]["changed"] is False
          and first["billing_policy"]["held_policy_digest"] == first["billing_policy"]["policy_digest"]
          and session["billing_policy_digest"] == first["billing_policy"]["policy_digest"]
          and session["other_record_versions"] == [] and first["checkout_expected"] is True
          and first["portal_expected"] is True)
    before = stored(path)
    status, second, _printed = apply(path)
    check("a_second_apply_changes_nothing",
          status == 0 and second["changed"] is False and second["session_policy"]["changed"] is False
          and second["billing_policy"]["changed"] is False and stored(path) == before
          and second["session_policy"]["record_version"] == session["record_version"]
          and second["billing_policy"]["record_version"] == first["billing_policy"]["record_version"])
    plant_older_terms(running)
    sent, resolved = [], []
    with patch.dict(os.environ, MARKERS), \
            patch.object(stripe_sessions, "_send", lambda request, secret: sent.append(request.path) or {}), \
            patch.object(http_entrypoint, "environment_secret", lambda reference: resolved.append(reference) or ""):
        status, record, printed = apply(path)
    check("apply_billing_policy_prints_no_secret_resolves_none_and_calls_no_provider",
          status == 0 and record["changed"] is True and not sent and not resolved
          and not any(value in printed for value in (*MARKERS.values(), *MARKERS))
          and record["provider_calls"] == 0 and record["tenants_registered"] == 0
          and record["remote_accounts_created"] is False)
    with patch.object(policy_module, "billing_policy_refusal", lambda application: "session_policy_changed"):
        status, record, _printed = apply(path)
    check("the_command_fails_when_a_policy_is_still_not_current",
          status == 1 and record["every_installed_policy_current"] is False
          and record["refusal"] == "session_policy_changed")


def _entitlement_checks(check, root):
    path, application = configured(root / "reset")
    paid_account(application)
    rewrite(path, a_new_entitlement_policy)
    status, record, _printed = apply(path, "--reset-paid-access")
    check("the_operator_can_end_paid_access_explicitly_and_the_report_counts_it",
          status == 0 and record["paid_access_ended_for_accounts"] == 1 and record["billing_policy"]["changed"] is True
          and paying(application) == 0)
    path, _application = configured(root / "unpaid")
    rewrite(path, a_new_entitlement_policy)
    restarted, _configuration = load_host_application(str(path))
    _health, drifted = health_row(restarted)
    check("the_health_record_names_an_entitlement_policy_the_host_file_no_longer_names",
          drifted["passed"] is False and drifted["code"] == "billing_policy_changed")
    status, record, _printed = apply(path)
    _health, row = health_row(restarted)
    check("a_changed_entitlement_policy_without_paid_access_is_applied_with_its_session_policy",
          status == 0 and record["billing_policy"]["changed"] is True and record["session_policy"]["changed"] is True
          and record["paid_access_ended_for_accounts"] == 0 and row["passed"] is True
          and restarted.billing_sessions.options()["checkout_available"] is True)
    rewrite(path, lambda host: host["billing"]["sessions"]["plans"].append(
        {"plan_ref": "team", "label": "Team", "price_id": "price_other"}))
    from ...service_cli import service_command
    printed = io.StringIO()
    with redirect_stdout(printed):
        status = service_command(["apply-billing-policy", "--config", str(path)])
    wrapped = json.loads(printed.getvalue())
    printed = io.StringIO()
    with redirect_stdout(printed):
        undeclared = service_command(["apply-billing-policy", "--config", "relative/host.json"])
    generic = json.loads(printed.getvalue())
    check("a_declared_refusal_reaches_the_operator_with_its_code_through_the_public_command",
          status == 1 and wrapped == {"record_type": REFUSAL_VERSION, "code": "session_price_not_in_billing_policy"}
          and undeclared == 1 and generic["record_type"] == "service_cli_error/v1"
          and generic["code"] == "service_operation_refused")
    path, bare = configured(root / "bare", billing=False)
    before = stored(path)
    status, record, _printed = apply(path)
    health, row = health_row(bare)
    check("a_host_without_billing_changes_nothing_and_reports_nothing_to_install",
          status == 0 and record["billing_installed"] is False and record["sessions_installed"] is False
          and record["every_installed_policy_current"] is True and record["checkout_expected"] is False
          and stored(path) == before and health["ready"] is True and row["required"] is False
          and row["passed"] is False and row["code"] == "billing_not_installed")


def _terms_checks(check, root):
    base = configuration()
    names = {item.name for item in fields(StripeSessionConfiguration)}
    extended = make_dataclass("ConfigurationWithANewField", [("automatic_tax", bool, field(default=False))],
                              bases=(StripeSessionConfiguration,), frozen=True)
    grown = extended(**{item.name: getattr(base, item.name) for item in fields(StripeSessionConfiguration)})
    check("every_configuration_field_is_a_term_unless_it_is_named_operational",
          set(SESSION_OPERATION_FIELDS) <= names
          and set(base.session_terms()) - {"record_type"} == names - set(SESSION_OPERATION_FIELDS)
          and "automatic_tax" in grown.session_terms()
          and grown.policy_definition().digest != base.policy_definition().digest)
    _path, application = configured(root / "terms")
    with application.runtime._catalog.store() as store:
        row = application.runtime._catalog.read(store, SESSION_POLICY_KIND, billing_effects.SESSION_POLICY_IDENTITY)
    terms = row["payload"]["policy"]
    check("the_stored_policy_holds_the_terms_and_no_operational_setting",
          row["payload"]["record_type"] == SESSION_POLICY_VERSION and terms["record_type"] == SESSION_TERMS_VERSION
          and not (set(terms) - {"record_type"}) & set(SESSION_OPERATION_FIELDS)
          and row["payload"]["policy_digest"] == application.billing_sessions.policy_digest)
    check("a_whole_host_configuration_is_refused_as_a_policy",
          refusal(lambda: BillingSessionPolicyDefinition(canonical(asdict(base)), ("price_basic",)))
          == "unsupported_session_policy")


SCENARIOS = (
    ("the_health_record_names_a_drifted_session_policy_that_billing_sessions_installed_hides",
     drift_is_named_by_the_health_record),
    ("apply_billing_policy_restores_checkout_and_the_portal_on_the_running_service", the_command_repairs_the_drift),
    ("apply_billing_policy_names_the_held_versions_as_the_expected_revisions",
     a_concurrent_writer_is_refused_not_overwritten),
    ("a_host_file_whose_session_prices_are_outside_its_entitlement_policy_changes_nothing",
     prices_outside_the_billing_policy_change_nothing),
    ("a_changed_entitlement_policy_that_would_end_paid_access_is_refused",
     paid_access_is_not_ended_without_the_operator_saying_so),
    ("each_term_changes_the_policy_digest", each_term_changes_the_policy_digest),
    ("each_operational_setting_leaves_the_policy_digest_unchanged", each_operational_setting_leaves_the_policy_digest),
    ("this_release_neither_reads_nor_overwrites_a_version_one_record",
     version_one_records_are_neither_read_nor_overwritten),
)


def run_mutant_controls(check):
    """Each control reruns one named scenario with one guard removed; the scenario's predicate must fail."""
    original_configure = BillingSessionEffectStore.configure_policy

    def last_writer_wins(self, definition, *, expected_version=None):
        with self._catalog.store() as store:
            row = self._catalog.read(store, SESSION_POLICY_KIND, billing_effects.SESSION_POLICY_IDENTITY)
        return original_configure(self, definition, expected_version=row["record_version"] if row else None)

    def claimed_without_writing(self, *, expected_version=None):
        return {"committed": True, "record_version": expected_version, "policy_digest": self.policy_digest}

    controls = (
        ("removed_billing_policy_health_check_is_detected", drift_is_named_by_the_health_record,
         lambda: patch.object(observability, "billing_policy_readiness",
                              lambda measure: ReadinessCheck(BILLING_POLICY_CHECK, False, measure is not None))),
        ("removed_session_policy_application_is_detected", the_command_repairs_the_drift,
         lambda: patch.object(stripe_sessions.StripeSessionAdapter, "configure_policy", claimed_without_writing)),
        ("removed_expected_revision_is_detected", a_concurrent_writer_is_refused_not_overwritten,
         lambda: patch.object(BillingSessionEffectStore, "configure_policy", last_writer_wins)),
        ("removed_price_check_before_any_write_is_detected", prices_outside_the_billing_policy_change_nothing,
         lambda: patch.object(policy_module, "_session_prices_outside", lambda policy, sessions: [])),
        ("removed_paid_access_guard_is_detected", paid_access_is_not_ended_without_the_operator_saying_so,
         lambda: patch.object(policy_module, "_accounts_with_paid_access", lambda runtime: 0)),
        ("a_return_address_left_out_of_the_terms_is_detected", each_term_changes_the_policy_digest,
         lambda: patch.object(stripe_sessions, "SESSION_OPERATION_FIELDS",
                              (*SESSION_OPERATION_FIELDS, "checkout_cancel_url"))),
        ("a_timeout_counted_as_a_term_is_detected", each_operational_setting_leaves_the_policy_digest,
         lambda: patch.object(stripe_sessions, "SESSION_OPERATION_FIELDS",
                              tuple(name for name in SESSION_OPERATION_FIELDS if name != "timeout_seconds"))),
        ("reading_the_version_one_slot_is_detected", version_one_records_are_neither_read_nor_overwritten,
         lambda: patch.object(billing_effects, "SESSION_POLICY_IDENTITY", "stripe")),
    )
    for name, scenario, mutant in controls:
        with tempfile.TemporaryDirectory(prefix="billing-policy-mutant-") as root:
            with mutant():
                # A removed guard must fail the scenario's own predicate. An
                # error raised instead says nothing about the guard, so it
                # fails the control rather than passing it.
                try:
                    observed = bool(scenario(root))
                except Exception:
                    observed = None
        check(name, observed is False)


def run_checks(check=None):
    """Run every billing policy check, each group in its own temporary service directory."""
    tests = []
    if check is None:
        def check(name, passed):
            tests.append({"test": name, "passed": bool(passed),
                          "detail": "real host file, entry point and store; no provider, no socket"})
    for name, scenario in SCENARIOS:
        with tempfile.TemporaryDirectory(prefix="billing-policy-") as root:
            try:
                passed = bool(scenario(root))
            except Exception:
                passed = False
        check(name, passed)
    for name, group in (("drift", _drift_checks), ("entitlement", _entitlement_checks), ("terms", _terms_checks)):
        with tempfile.TemporaryDirectory(prefix="billing-policy-" + name + "-") as directory:
            root = Path(directory)
            for folder in ("drift", "reset", "unpaid", "bare", "terms"):
                (root / folder).mkdir()
            try:
                group(check, root)
            except Exception:
                # A group that stops part way is a failure with a name.
                check(f"the_{name}_checks_ran_to_completion", False)
    run_mutant_controls(check)
    return {"record_type": "service_billing_policy_test/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
