"""Access management checks over the existing durable service domain.

Owns real SQLite, loopback HTTP, concurrency and removed-guard fixtures.
The HTTP suite collects these checks. No external provider is contacted.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import hashlib
from pathlib import Path
import tempfile
import threading
import time
import uuid
from unittest.mock import patch

from .access import (ServiceAccessAdministration, ServiceAccessPolicy, ServiceAccessRequest,
                     ServiceAccessSession, ServiceClientAccessPolicy)
from .http import ServiceHttpApplication
from .http_test_fixtures import HttpDomainFixture, running_http
from .records import (ACCESS_MANAGE_SCOPE, BILLING_MANAGE_SCOPE, DEFAULT_SCOPES, ServiceCommitUnknown,
                      ServiceRuntimeError, SubjectBindingRequest, TenantKeyIssue, TenantRegistration)
from .runtime import KEY, OWNER_BOUND_KEY_SCHEMA, SCHEMAS, ServiceRuntime


def prepared(root, **policy):
    fixture = HttpDomainFixture(root)
    fixture.runtime.register_tenant(TenantRegistration("administrator", "administrator:private", (ACCESS_MANAGE_SCOPE,)))
    fixture.admin_key = fixture.runtime.issue_key(TenantKeyIssue("administrator", "local test administrator"))
    fixture.administration = ServiceAccessAdministration(fixture.runtime, ServiceAccessPolicy(
        ("administrator",), ("alpha", "beta"), writes_authorized=True, **policy))
    return fixture


def refused(function, *codes):
    try:
        function()
    except ServiceRuntimeError as error:
        return not codes or error.code in codes
    return False


def run_checks(check, root):
    fixture = prepared(root)
    runtime, administration = fixture.runtime, fixture.administration
    admin = runtime.authenticate_key(fixture.admin_key.key)
    user = runtime.authenticate_key(fixture.keys["alpha"].key)
    check("ordinary_customer_cannot_list_test_tokens", refused(lambda: administration.inspect(user), "access_administration_forbidden"))
    check("forged_administrator_principal_refused", refused(lambda: administration.inspect(replace(user, scopes=(ACCESS_MANAGE_SCOPE,))), "unissued_principal"))
    check("policy_cannot_delegate_administrator_scope", refused(lambda: ServiceAccessPolicy(("administrator",), ("alpha",), allowed_scopes=(ACCESS_MANAGE_SCOPE,))))
    check("policy_cannot_issue_into_administrator_tenant", refused(lambda: ServiceAccessPolicy(("administrator",), ("administrator",))))
    for value in (True, 0, -1, 1.2):
        check("invalid_token_limit_" + repr(value), refused(lambda: ServiceAccessPolicy(("administrator",), ("alpha",), maximum_active_tokens=value)))
    request = ServiceAccessRequest("issue", "first-test", "alpha", "Metadata test", ("provisioning:metadata",), 3600)
    result = administration.apply(admin, request)
    generated = result["token"]
    check("scoped_token_is_a_real_usable_service_credential", runtime.authenticate_key(generated).scopes == ("provisioning:metadata",))
    check("raw_token_is_absent_from_catalogue_and_audit", generated not in json.dumps(runtime._catalog.config.__dict__) and generated.encode() not in Path(runtime.config.database_path).read_bytes())
    repeat = administration.apply(admin, request)
    check("duplicate_submission_returns_same_key_but_no_secret", repeat["replayed"] and repeat["token"] is None and repeat["key"] == result["key"])
    check("changed_request_identity_refused", refused(lambda: administration.apply(admin, replace(request, label="Changed")), "access_request_identity_conflict"))
    check("wrong_target_refused", refused(lambda: administration.apply(admin, replace(request, request_id="wrong-target", tenant_id="unconfigured")), "access_target_forbidden"))
    check("privileged_scope_escalation_refused", refused(lambda: administration.apply(admin, replace(request, request_id="scope", scopes=(ACCESS_MANAGE_SCOPE,))), "scope_escalation_refused"))
    check("expiry_cannot_exceed_policy", refused(lambda: administration.apply(admin, replace(request, request_id="long", lifetime_seconds=604801)), "access_lifetime_exceeded"))
    check("unknown_fields_refused", refused(lambda: ServiceAccessRequest.from_dict({"record_type":"service_access_request/v1", "operation":"issue", "request_id":"wrong", "tenant_id":"alpha", "admin":True})))
    check("bootstrap_credentials_are_not_managed_test_tokens", not any(row["key_id"] == fixture.keys["alpha"].key_id for row in administration.inspect(admin)["tokens"]))
    check("bootstrap_credential_revocation_refused", refused(lambda: administration.apply(admin, ServiceAccessRequest("revoke", "revoke-bootstrap", "alpha", key_id=fixture.keys["alpha"].key_id)), "managed_access_token_not_found"))
    read_only = ServiceAccessAdministration(runtime, replace(administration.policy, writes_authorized=False))
    check("read_only_administration_cannot_mint", refused(lambda: read_only.apply(admin, replace(request, request_id="readonly")), "access_writes_not_authorized"))
    revoked = administration.apply(admin, ServiceAccessRequest("revoke", "revoke-first", "alpha", key_id=result["key"]["key_id"]))
    check("revocation_is_durable_and_immediate", revoked["key"]["state"] == "revoked" and refused(lambda: runtime.authenticate_key(generated), "unauthorized"))
    reopened = ServiceRuntime(runtime.config)
    check("revocation_survives_reopening_store", refused(lambda: reopened.authenticate_key(generated), "unauthorized"))
    # Deliberately remove authorization locally. The ordinary-user negative
    # case must now expose the defect, showing it detects the missing guard.
    with patch.object(administration, "_authorize", lambda store, principal: runtime._revalidate(store, admin)):
        check("removed_administrator_guard_is_detected", not refused(lambda: administration.inspect(user), "access_administration_forbidden"))
    runtime.revoke_key("administrator", fixture.admin_key.key_id)
    check("revoked_administrator_cannot_mint_from_stale_principal", refused(lambda: administration.apply(admin, replace(request, request_id="after-revoke")), "unauthorized"))


def concurrency_checks(check, root):
    fixture = prepared(root, maximum_active_tokens=1)
    administration, runtime = fixture.administration, fixture.runtime
    admin = runtime.authenticate_key(fixture.admin_key.key)
    barrier, original = threading.Barrier(2), administration._rows
    def rows(store, current=None):
        result = original(store, current)
        barrier.wait(timeout=5)
        return result
    def issue(identity):
        try:
            return administration.apply(admin, ServiceAccessRequest("issue", identity, "alpha", identity, DEFAULT_SCOPES, 3600))
        except ServiceRuntimeError as error:
            return {"refused":error.code}
    with patch.object(administration, "_rows", rows), ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(issue, ("parallel-a", "parallel-b")))
    check("concurrent_creates_cannot_exceed_active_limit", sum(row.get("committed") is True for row in results) == 1 and administration.inspect(admin)["active_tokens"] == 1)
    check("limit_enforced_on_subsequent_request", issue("parallel-c").get("refused") == "access_token_limit_reached")
    # A store can commit and then lose its acknowledgment. Retrying may find
    # the durable operation, but must never mint another secret for it.
    original_commit = runtime._catalog.commit
    target = next(row for row in results if row.get("committed"))["key"]
    administration.apply(admin, ServiceAccessRequest("revoke", "free-slot", target["tenant_id"], key_id=target["key_id"]))
    def uncertain(*args):
        original_commit(*args)
        raise ServiceCommitUnknown()
    request = ServiceAccessRequest("issue", "lost-ack", "alpha", "Lost acknowledgment", DEFAULT_SCOPES, 3600)
    with patch.object(type(runtime._catalog), "commit", lambda _self, *args: uncertain(*args)):
        check("unknown_commit_is_not_reported_as_success", refused(lambda: administration.apply(admin, request), "commit_unknown"))
    replay = administration.apply(admin, request)
    check("unknown_commit_retry_reconciles_without_duplicate_or_raw_key", replay["replayed"] is True and replay["token"] is None and administration.inspect(admin)["active_tokens"] == 1)


def http_checks(check, root):
    import httpx
    fixture = prepared(root)
    factory = lambda config: ServiceHttpApplication(fixture.runtime, fixture.provisioning, config, access_administration=fixture.administration)
    with running_http(fixture, application_factory=factory, display_name='Baltor <script>alert(1)</script>') as (base, _):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            page = client.get("/admin")
            check("administrator_route_loads_with_escaped_configured_brand", page.status_code == 200 and "Baltor &lt;script&gt;" in page.text and "Baltor <script>" not in page.text)
            check("anonymous_administrator_request_refused", client.get("/api/v1/admin/access").status_code == 401)
            client.headers.update(fixture.headers())
            check("normal_tenant_cannot_reach_administrator_API", client.get("/api/v1/admin/access").status_code == 403)
            client.headers.update({"Authorization":"Bearer " + fixture.admin_key.key})
            options = client.get("/api/v1/admin/access")
            check("administrator_sees_only_host_selected_tenants_and_limits", options.status_code == 200 and options.json()["result"]["target_tenants"] == ["alpha", "beta"])
            request = {"record_type":"service_access_request/v1", "operation":"issue", "request_id":"HTTP-test",
                       "tenant_id":"alpha", "label":"HTTP test", "scopes":["provisioning:metadata"], "lifetime_seconds":3600}
            issued = client.post("/api/v1/admin/access", json=request)
            result = issued.json()["result"]
            check("HTTP_creation_is_governed_and_uncached", issued.status_code == 200 and result["committed"] and issued.headers["cache-control"] == "no-store" and issued.json()["execution"]["runtime_type"] == "Loop")
            listing = client.get("/api/v1/admin/access")
            check("list_never_discloses_token_or_digest", result["token"] not in listing.text and "key_digest" not in listing.text)
            headers = {"Authorization":"Bearer " + result["token"]}
            check("issued_token_authenticates_in_real_HTTP_session", client.get("/api/v1/session", headers=headers).status_code == 200)
            check("issued_token_cannot_manage_access", client.get("/api/v1/admin/access", headers=headers).status_code == 403)
            denied = client.post("/api/v1/download", headers=headers, json={"record_type":"service_provisioning_request/v1", "operation":"read", "identity":"skill.alpha", "request_id":"no-body"})
            check("metadata_only_token_cannot_download", denied.status_code == 403 and not fixture.reads)
            denied_origin = client.post("/api/v1/admin/access", json={**request, "request_id":"cross-origin"}, headers={"Origin":"https://untrusted.invalid"})
            check("foreign_browser_origin_cannot_create_tokens", denied_origin.status_code == 403)
            revoked = client.post("/api/v1/admin/access", json={"record_type":"service_access_request/v1", "operation":"revoke", "request_id":"HTTP-revoke", "tenant_id":"alpha", "key_id":result["key"]["key_id"]})
            check("HTTP_revocation_refuses_next_authenticated_request", revoked.status_code == 200 and client.get("/api/v1/session", headers=headers).status_code == 401)


def customer_prepared(root, **policy):
    fixture = HttpDomainFixture(root)
    fixture.customers, fixture.customer_sessions = {}, {}
    for subject, tenant in (("customer-a", "alpha"), ("customer-b", "beta"), ("other-member", "alpha")):
        fixture.runtime.bind_subject(SubjectBindingRequest(tenant, "https://identity.example", subject))
        principal = fixture.runtime.authenticate_subject("https://identity.example", subject)
        fixture.customers[subject] = principal
        fixture.customer_sessions[subject] = ServiceAccessSession(principal.authentication_record_id,
            hashlib.sha256(subject.encode()).hexdigest(), fixture.runtime._now() + 600, DEFAULT_SCOPES)
    fixture.client_access = ServiceAccessAdministration(fixture.runtime, ServiceClientAccessPolicy(writes_authorized=True, **policy))
    return fixture


def version_checks(check, root):
    """A customer key must be unreadable to a server that lacks the owner rule.

    An older server accepts only the first key version and knows no owner
    binding. If a customer key used that version, a rollback would keep
    honoring it after its owner's sign-in was disabled.
    """
    fixture = customer_prepared(root)
    token = fixture.client_access.apply(fixture.customers["customer-a"], ServiceAccessRequest(
        "issue", "version-device", "alpha", label="Version check", scopes=("provisioning:metadata",),
        lifetime_seconds=3600), session=fixture.customer_sessions["customer-a"])["token"]
    runtime, catalog = fixture.runtime, fixture.runtime._catalog
    hashed = hashlib.sha256(token.encode()).hexdigest()
    with catalog.store() as store:
        row = catalog.read(store, KEY, hashed)
        host_row = catalog.read(store, KEY, hashlib.sha256(fixture.keys["alpha"].key.encode()).hexdigest())
    check("customer_key_uses_the_owner_bound_record_version", row["payload"]["record_type"] == OWNER_BOUND_KEY_SCHEMA)
    check("host_issued_key_keeps_the_first_record_version", host_row["payload"]["record_type"] == SCHEMAS[KEY])
    # The older reader is the same code limited to the versions it knew.
    with patch("loop_engine.core.service_runtime.runtime.KEY_SCHEMAS", (SCHEMAS[KEY],)):
        check("server_without_the_owner_rule_refuses_the_customer_key",
              refused(lambda: runtime.authenticate_key(token), "unsupported_or_corrupt_record")
              and runtime.authenticate_key(fixture.keys["alpha"].key).tenant_id == "alpha")
    # Known-wrong shape: the customer profile stored under the first version.
    downgraded = {**row, "record_version": uuid.uuid4().hex, "payload": {**row["payload"], "record_type": SCHEMAS[KEY]}}
    with catalog.store(write=True) as store:
        catalog.commit(store, (downgraded,), (catalog.guard(row),))
    check("customer_profile_under_the_first_version_is_refused",
          refused(lambda: runtime.authenticate_key(token), "unsupported_or_corrupt_record"))
    # A first-version key cannot claim the owner-bound version either.
    with catalog.store(write=True) as store:
        current = catalog.read(store, KEY, hashed)
        catalog.commit(store, ({**current, "record_version": uuid.uuid4().hex,
            "payload": {key: value for key, value in row["payload"].items() if key != "management_profile"}},), (catalog.guard(current),))
    check("owner_bound_version_without_the_customer_profile_is_refused",
          refused(lambda: runtime.authenticate_key(token), "unsupported_or_corrupt_record"))
    with catalog.store(write=True) as store:
        current = catalog.read(store, KEY, hashed)
        catalog.commit(store, ({**row, "record_version": uuid.uuid4().hex},), (catalog.guard(current),))
    check("restored_customer_key_authenticates_again", runtime.authenticate_key(token).tenant_id == "alpha")
    # Removing the version change recreates the rollback defect, and the first
    # check above is the one that must notice it.
    service = fixture.client_access
    principal, session = fixture.customers["other-member"], fixture.customer_sessions["other-member"]
    with patch("loop_engine.core.service_runtime.access.OWNER_BOUND_KEY_SCHEMA", SCHEMAS[KEY]):
        mutant = service.apply(principal, ServiceAccessRequest("issue", "without-version-change", "alpha",
            label="Mutant", scopes=("provisioning:metadata",), lifetime_seconds=3600), session=session)
    with catalog.store() as store:
        mutant_row = catalog.read(store, KEY, hashlib.sha256(mutant["token"].encode()).hexdigest())
    check("removed_key_version_change_is_detected", mutant_row["payload"]["record_type"] != OWNER_BOUND_KEY_SCHEMA
          and refused(lambda: runtime.authenticate_key(mutant["token"]), "unsupported_or_corrupt_record"))
    service.apply(principal, ServiceAccessRequest("revoke", "remove-mutant", "alpha", key_id=mutant["key"]["key_id"]), session=session)


def customer_checks(check, root):
    fixture = customer_prepared(root)
    service, runtime = fixture.client_access, fixture.runtime
    principal, session = fixture.customers["customer-a"], fixture.customer_sessions["customer-a"]
    other, other_session = fixture.customers["customer-b"], fixture.customer_sessions["customer-b"]
    colleague, colleague_session = fixture.customers["other-member"], fixture.customer_sessions["other-member"]
    payload = {"record_type":"service_client_access_request/v1", "operation":"issue", "request_id":"personal-device",
               "label":"Local development", "scopes":["provisioning:metadata"], "lifetime_seconds":3600}
    request = ServiceAccessRequest.from_customer_dict(payload, principal.tenant_id)
    check("customer_wire_contract_refuses_a_tenant_override", refused(lambda: ServiceAccessRequest.from_customer_dict({**payload, "tenant_id":"beta"}, "alpha")))
    check("customer_wire_contract_refuses_administrator_format", refused(lambda: ServiceAccessRequest.from_customer_dict({**payload, "record_type":"service_access_request/v1"}, "alpha")))
    check("customer_access_defaults_to_no_write_authority", ServiceClientAccessPolicy().writes_authorized is False)
    for privileged in (ACCESS_MANAGE_SCOPE, BILLING_MANAGE_SCOPE):
        check("customer_policy_refuses_" + privileged, refused(lambda: ServiceClientAccessPolicy(allowed_scopes=(privileged,))))
    for limit in (True, 0, 1.5, 10001):
        check("customer_record_limit_refuses_" + repr(limit), refused(lambda: ServiceClientAccessPolicy(maximum_token_records=limit)))
    check("customer_requires_a_verified_session_context", refused(lambda: service.inspect(principal), "browser_session_required"))
    check("customer_session_must_belong_to_the_subject", refused(lambda: service.inspect(principal, session=other_session), "browser_session_required"))
    check("expired_customer_session_cannot_mint", refused(lambda: service.apply(principal, request, session=replace(session, expires_at=1)), "unauthorized"))
    bearer = runtime.authenticate_key(fixture.keys["alpha"].key)
    check("service_token_cannot_manage_customer_credentials", refused(lambda: service.inspect(bearer, session=session), "browser_session_required"))
    check("customer_cannot_select_another_tenant", refused(lambda: service.apply(principal, replace(request, tenant_id="beta"), session=session), "access_target_forbidden"))
    narrow = replace(session, allowed_scopes=("provisioning:metadata",))
    check("customer_cannot_expand_transport_scopes", refused(lambda: service.apply(principal,
        replace(request, scopes=("provisioning:read",)), session=narrow), "scope_escalation_refused"))
    result = service.apply(principal, request, session=session)
    token, key = result["token"], result["key"]
    check("customer_token_is_real_and_narrowed", runtime.authenticate_key(token).scopes == ("provisioning:metadata",))
    options = service.inspect(principal, session=narrow)
    check("customer_options_are_narrowed_to_transport_and_tenant", options["allowed_scopes"] == ["provisioning:metadata"] and options["target_tenants"] == ["alpha"])
    check("customer_list_never_contains_a_secret_or_digest", token not in json.dumps(options) and "key_digest" not in json.dumps(options))
    check("customer_token_secret_is_not_stored", token.encode() not in Path(runtime.config.database_path).read_bytes())
    check("other_tenant_cannot_see_customer_tokens", service.inspect(other, session=other_session)["tokens"] == [])
    check("another_member_cannot_see_personal_tokens", service.inspect(colleague, session=colleague_session)["tokens"] == [])
    revocation = ServiceAccessRequest("revoke", "revoke-personal", "alpha", key_id=key["key_id"])
    check("another_member_cannot_revoke_personal_tokens", refused(lambda: service.apply(colleague, revocation, session=colleague_session), "managed_access_token_not_found"))
    check("other_tenant_cannot_revoke_customer_tokens", refused(lambda: service.apply(other, replace(revocation, tenant_id="beta"), session=other_session), "managed_access_token_not_found"))
    replay = service.apply(principal, request, session=session)
    check("customer_replay_returns_no_secret_and_mints_no_second_key", replay["replayed"] and replay["token"] is None and service.inspect(principal, session=session)["active_tokens"] == 1)
    check("customer_request_identity_cannot_change_effect", refused(lambda: service.apply(principal, replace(request, label="Changed"), session=session), "access_request_identity_conflict"))
    reopened = ServiceRuntime(runtime.config)
    check("customer_key_survives_restart_without_raw_secret_storage", reopened.authenticate_key(token).tenant_id == "alpha")
    service.apply(principal, revocation, session=session)
    check("customer_revocation_refuses_further_use", refused(lambda: runtime.authenticate_key(token), "unauthorized"))
    check("customer_new_revoke_request_cannot_grow_audit_for_revoked_key", refused(lambda: service.apply(principal, replace(revocation, request_id="again"), session=session), "access_token_already_revoked"))
    another = service.apply(principal, replace(request, request_id="bound-to-subject"), session=session)
    runtime.revoke_subject(SubjectBindingRequest("alpha", "https://identity.example", "customer-a"))
    check("revoked_customer_subject_disables_its_existing_client_tokens", refused(lambda: runtime.authenticate_key(another["token"]), "unauthorized"))
    check("revoked_customer_cannot_use_a_stale_principal", refused(lambda: service.inspect(principal, session=session), "unauthorized"))
    # Removing the session guard makes an ordinary service token a credential
    # manager; the negative check must detect that specific authority defect.
    with patch.object(service, "_customer_authorize", lambda store, actor, _session: runtime._revalidate(store, actor)):
        check("removed_customer_session_guard_is_detected", not refused(lambda: service.inspect(bearer, session=session), "browser_session_required"))


def customer_race_checks(check, root):
    fixture = customer_prepared(root, maximum_active_tokens=1, maximum_token_records=2)
    service, runtime = fixture.client_access, fixture.runtime
    principal, session = fixture.customers["customer-a"], fixture.customer_sessions["customer-a"]
    request = ServiceAccessRequest("issue", "race", "alpha", "Device", DEFAULT_SCOPES, 3600)
    barrier, original = threading.Barrier(2), service._rows
    def rows(store, current=None):
        result = original(store, current); barrier.wait(timeout=5); return result
    def issue(identity):
        try:return service.apply(principal, replace(request, request_id=identity), session=session)
        except ServiceRuntimeError as error:return {"refused":error.code}
    with patch.object(service, "_rows", rows), ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(issue, ("first", "second")))
    check("customer_concurrent_issues_respect_tenant_quota", sum(row.get("committed") is True for row in results) == 1 and service.inspect(principal, session=session)["active_tokens"] == 1)
    key = next(row["key"] for row in results if row.get("committed"))
    service.apply(principal, ServiceAccessRequest("revoke", "clear-slot", "alpha", key_id=key["key_id"]), session=session)
    original_commit = runtime._catalog.commit
    def uncertain(_self, *args):
        original_commit(*args); raise ServiceCommitUnknown()
    with patch.object(type(runtime._catalog), "commit", uncertain):
        check("customer_unknown_commit_is_not_success", refused(lambda: service.apply(principal, request, session=session), "commit_unknown"))
    replay = service.apply(principal, request, session=session)
    check("customer_unknown_commit_reconciles_without_reissuing_secret", replay["replayed"] and replay["token"] is None and service.inspect(principal, session=session)["active_tokens"] == 1)
    service.apply(principal, ServiceAccessRequest("revoke", "clear-second", "alpha", key_id=replay["key"]["key_id"]), session=session)
    check("customer_history_bound_is_not_reset_by_revocation", issue("beyond-history").get("refused") == "access_token_history_limit_reached")


def customer_logout_race_checks(check, root):
    fixture = customer_prepared(root)
    service, runtime = fixture.client_access, fixture.runtime
    principal, session = fixture.customers["customer-a"], fixture.customer_sessions["customer-a"]
    request = ServiceAccessRequest("issue", "logout-race", "alpha", "Device", DEFAULT_SCOPES, 3600)
    original = service._rows
    def revoke_during_read(store, current=None):
        result = original(store, current)
        runtime.revoke_browser_session(principal, session.credential_digest, int(session.expires_at))
        return result
    with patch.object(service, "_rows", revoke_during_read):
        check("customer_logout_race_prevents_token_commit", refused(lambda: service.apply(principal, request, session=session), "concurrent_update"))
    check("logged_out_session_cannot_inspect_or_mint", refused(lambda: service.inspect(principal, session=session), "unauthorized"))
    with runtime._catalog.store() as store:
        check("logout_race_leaves_no_customer_key", runtime._catalog.rows(store, KEY, "alpha") == [row for row in runtime._catalog.rows(store, KEY, "alpha") if row["payload"].get("management_profile") is None])


def run_all_checks():
    tests = []
    def check(name, passed):
        tests.append({"test":name, "passed":bool(passed)})
    for name, function in (("domain", run_checks), ("concurrency", concurrency_checks), ("HTTP", http_checks),
                           ("customer", customer_checks), ("customer_key_version", version_checks),
                           ("customer_concurrency", customer_race_checks),
                           ("customer_logout", customer_logout_race_checks)):
        with tempfile.TemporaryDirectory(prefix="service-access-" + name + "-") as directory:
            function(check, Path(directory))
    return {"tests":tests, "passed":sum(row["passed"] for row in tests), "total":len(tests), "all_passed":all(row["passed"] for row in tests)}
