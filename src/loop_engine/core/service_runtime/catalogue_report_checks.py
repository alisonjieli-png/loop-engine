"""Checks for customer reports, staff flags and the withdrawal rule of the served library (roadmap S-6.199).

Every check runs against a real temporary service store and body folder, and
the transport checks against a real loopback service with a running catalogue
refresher. No network, model or provider is used. The known-wrong cases are
the ones the roadmap step names: a report on an unknown item, a second report
from the same customer counted twice, a Verified item withdrawn on one report,
an anonymous or unstaffed caller withdrawing anything, and a withdrawal that
loses the item's record. Each rule is shown twice: the case is refused or
honoured, and a removed-guard control reruns it with the rule patched away.
"""
from __future__ import annotations

import json
import tempfile
import time
from unittest.mock import patch

from . import catalogue_reports, library_page
from .catalogue_grants import follow_active_release
from .catalogue_release_checks import Fixture, refused
from .catalogue_releases import is_withdrawn
from .catalogue_reports import (FLAG_OPERATION, RECORDED, REPORT_OPERATION, REPORT_TOOL, WITHDRAWN, record_feedback,
                                review_queue)
from .catalogue_serving import CatalogueRefresher, next_view, state_token
from .http import TIERED_PROVISIONING_REQUEST_VERSION
from .records import TenantKeyIssue, TenantRegistration
from .storage import ServiceCatalogBinding

REASON = "the steps delete files outside the project"


def _community(case, identity, text):
    line = case.line(identity, text)
    return {**line, "approval": {**line["approval"], "tier": "community"}}


def _customer(case, name):
    """One more account that follows the active release, with its own key."""
    case.runtime.register_tenant(TenantRegistration(name, "tenant:" + name))
    key = case.runtime.issue_key(TenantKeyIssue(name, "report checks"))
    case.runtime.set_operator_entitlement(name, valid_until=int(time.time()) + 3600,
                                          evidence_ref="local-check-not-payment")
    follow_active_release(case.runtime, [name])
    return key


def _served_now(case, view):
    return next_view(view, state_token(case.config), case.config, case.settings,
                     license_policy=case.license_policy, family_policy=case.family_policy)


def _rule_checks(check, root):
    case = Fixture(root)
    lines = [case.line("verified_one", "# Verified one\n"), case.line("verified_two", "# Verified two\n"),
             case.line("verified_three", "# Verified three\n"),
             _community(case, "community_one", "# Community one\n"),
             _community(case, "community_two", "# Community two\n")]
    case.publish(lines)
    _customer(case, "beta")
    binding = ServiceCatalogBinding(case.config)
    view = case.view()

    def digest(identity):
        return view.catalogue.items[identity].digest

    def feedback(named, **fields):
        return record_feedback(binding, view, **{"kind": REPORT_OPERATION, "tenant_id": "alpha", "reason": REASON,
                                                 "identity": named, "expected_digest": digest(named), **fields})

    def withdrawn_in_store(identity):
        with binding.store() as store:
            return is_withdrawn(binding, store, identity, digest(identity))

    check("a_report_on_an_unknown_item_is_refused",
          refused(lambda: feedback("community_one", identity="no_such_item"), "item_unavailable"))
    check("a_report_that_names_other_bytes_than_the_library_serves_is_refused",
          refused(lambda: feedback("community_one", expected_digest="f" * 64), "selected_body_digest_mismatch")
          and refused(lambda: feedback("community_one", expected_digest="short"), "invalid_selected_digest"))
    check("a_report_without_a_plain_bounded_reason_is_refused",
          refused(lambda: feedback("community_one", reason="  "), "report_reason_invalid")
          and refused(lambda: feedback("community_one", reason="x" * 401), "report_reason_invalid")
          and refused(lambda: feedback("community_one", reason="bad\x00bytes"), "report_reason_invalid"))
    check("an_anonymous_report_is_refused_and_withdraws_nothing",
          refused(lambda: feedback("community_one", tenant_id=""), "unauthorized")
          and not withdrawn_in_store("community_one"))
    check("a_flag_without_a_staff_role_is_refused",
          refused(lambda: feedback("verified_one", kind=FLAG_OPERATION), "staff_role_required")
          and refused(lambda: feedback("verified_one", kind=FLAG_OPERATION, role="customer"), "staff_role_required")
          and not withdrawn_in_store("verified_one"))

    first = feedback("community_one")
    served = _served_now(case, view)
    queue = review_queue(binding)
    check("a_customer_report_withdraws_a_community_item_and_queues_its_review",
          first["state"] == WITHDRAWN and first["withdrawn_now"] and first["library_tier"] == "community"
          and first["reports"] == 1 and withdrawn_in_store("community_one")
          and "community_one" not in served.catalogue.items
          and served.withdrawal_notes[("community_one", digest("community_one"))]["note"].endswith(REASON)
          and any(row["identity"] == "community_one" and row["reports"] == 1 and row["withdrawn"]
                  and row["reasons"] == [REASON] for row in queue["queued"]))
    check("a_reported_item_is_refused_at_read_on_the_view_that_still_lists_it",
          refused(lambda: case.binding(view).invoke(case.key.key, "manifest", identity="community_one"),
                  "item_withdrawn"))
    one = feedback("verified_one")
    again = feedback("verified_one", reason="a second time from the same account")
    check("one_report_does_not_withdraw_a_verified_item_and_a_repeat_from_the_same_account_counts_once",
          one["state"] == RECORDED and not one["withdrawn"] and one["reports_to_withdraw"] == 2
          and again["state"] == RECORDED and again["reports"] == 1 and again["recorded_before"]
          and not withdrawn_in_store("verified_one") and "verified_one" in _served_now(case, view).catalogue.items)
    two = feedback("verified_one", tenant_id="beta")
    check("a_second_report_from_another_customer_withdraws_a_verified_item",
          two["state"] == WITHDRAWN and two["withdrawn_now"] and two["reports"] == 2
          and withdrawn_in_store("verified_one") and "verified_one" not in _served_now(case, view).catalogue.items)
    flagged = feedback("verified_two", kind=FLAG_OPERATION, role="superadmin", reason="unsafe instruction")
    check("a_staff_flag_withdraws_a_verified_item_at_once",
          flagged["state"] == WITHDRAWN and flagged["flags"] == 1 and flagged["reports"] == 0
          and withdrawn_in_store("verified_two"))
    page = library_page.library_body(_served_now(case, view))
    with binding.store() as store:
        kept = [row["payload"] for row in binding.rows_all(store, catalogue_reports.REPORT_KIND)]
    check("every_withdrawal_keeps_its_record_and_its_note_on_the_library_page",
          'data-library-withdrawn="community_one"' in page and REASON in page
          and 'data-library-withdrawn="verified_two"' in page and "staff flag: unsafe instruction" in page
          and sorted((row["identity"], row["reporter_tenant_id"], row["kind"]) for row in kept)
          == [("community_one", "alpha", "report"), ("verified_one", "alpha", "report"),
              ("verified_one", "beta", "report"), ("verified_two", "alpha", "flag")]
          and all(row["reason"] and row["review_state"] == "queued" for row in kept))
    check("a_withdrawn_item_version_is_never_served_again_by_a_release",
          refused(lambda: case.publish(lines), "catalogue_release_lists_withdrawn_item"))
    reviewed = [case.line("verified_one", "# Verified one, reviewed again with new bytes\n"),
                case.line("verified_three", "# Verified three\n"), _community(case, "community_two", "# Community two\n")]
    case.publish(reviewed)
    check("a_new_review_of_new_bytes_serves_the_item_again",
          "verified_one" in case.view().catalogue.items and "community_one" not in case.view().catalogue.items)

    # Removed-guard controls. Each reruns a case above with the rule patched away and requires the predicate to fail.
    view = case.view()
    with patch.object(catalogue_reports, "withdrawal_due", lambda tier, records: False):
        check("removed_report_withdrawal_rule_is_detected", not feedback("community_two")["withdrawn"])
    with patch.object(catalogue_reports, "VERIFIED_REPORTS_TO_WITHDRAW", 1):
        check("a_verified_item_withdrawn_on_one_report_is_detected",
              feedback("verified_three", tenant_id="beta")["withdrawn"])


class _Served:
    def __init__(self, case):
        self.case, self.runtime = case, case.runtime
        self.provisioning = case.binding()


class _StaffList:
    """A stand-in for the account administration: one account holds the superadmin role, nobody else holds any."""

    def __init__(self, staff_tenant):
        self.staff_tenant = staff_tenant

    def role_of(self, authentication):
        return "superadmin" if authentication.principal.tenant_id == self.staff_tenant else ""


def _application(served, refresh_seconds, staff_tenant):
    from .http import ServiceHttpApplication
    from .http_auth import ServiceHttpAuthentication
    case = served.case

    def factory(configuration):
        service = ServiceHttpApplication(served.runtime, served.provisioning, configuration,
                                         ServiceHttpAuthentication())
        service.account_administration = _StaffList(staff_tenant)
        service.catalogue_refresher = CatalogueRefresher(
            served.provisioning, build=lambda current, token: next_view(
                current, token, case.config, case.settings, license_policy=case.license_policy,
                family_policy=case.family_policy),
            probe=lambda: state_token(case.config), journal=service.failure_journal,
            interval_seconds=refresh_seconds)
        return service
    return factory


def _transport_checks(check, root):
    import httpx
    from .http_test_fixtures import running_http
    from .protocol_checks import _protocol_message
    case = Fixture(root)
    case.publish([case.line("verified_one", "# Verified one\n"), case.line("verified_two", "# Verified two\n"),
                  _community(case, "community_one", "# Community one\n")])
    beta, staff = _customer(case, "beta"), _customer(case, "staff")
    served = _Served(case)
    view = served.provisioning.current_view()
    digests = {identity: item.digest for identity, item in view.catalogue.items.items()}

    def report(operation, identity, **fields):
        return {"record_type": TIERED_PROVISIONING_REQUEST_VERSION, "operation": operation, "identity": identity,
                "expected_digest": digests.get(identity, "0" * 64), "reason": REASON, **fields}
    with running_http(served, application_factory=_application(served, 0.05, "staff")) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            alpha = {"Authorization": "Bearer " + case.key.key}
            listed = lambda headers: sorted(row["identity"] for row in client.post(  # noqa: E731
                "/api/v1/provisioning", json={"record_type": TIERED_PROVISIONING_REQUEST_VERSION, "operation": "list"},
                headers=headers).json()["result"]["items"])
            before = listed(alpha)
            answer = client.post("/api/v1/provisioning", json=report("report", "community_one"), headers=alpha)
            # Before the refresher swaps the view, the read-time withdrawal check refuses the item; after the swap the
            # view no longer lists it. Either way the item is gone within the refresher's interval.
            manifest = client.post("/api/v1/provisioning", json={
                "record_type": TIERED_PROVISIONING_REQUEST_VERSION, "operation": "manifest", "identity": "community_one"},
                headers=alpha)
            deadline = time.monotonic() + 5
            while "community_one" in listed(alpha) and time.monotonic() < deadline:
                time.sleep(0.02)
            after = listed(alpha)
            check("a_report_over_http_withdraws_a_community_item_within_the_refresher_interval",
                  answer.status_code == 200 and answer.json()["result"]["withdrawn"] is True
                  and answer.json()["result"]["record_type"] == "service_catalogue_report_result/v1"
                  and "community_one" in before and "community_one" not in after
                  and manifest.status_code == 404
                  and manifest.json()["error"]["code"] in ("item_withdrawn", "item_unavailable"))
            old = client.post("/api/v1/provisioning", json={**report("report", "verified_one"),
                                                           "record_type": "service_provisioning_request/v1"}, headers=alpha)
            unknown = client.post("/api/v1/provisioning", json=report("report", "no_such_item"), headers=alpha)
            download = client.post("/api/v1/download", json=report("report", "verified_one"), headers=alpha)
            unauthenticated = client.post("/api/v1/provisioning", json=report("report", "verified_one"))
            check("a_report_is_a_version_2_operation_that_needs_an_account_and_a_served_item",
                  old.status_code == 400 and old.json()["error"]["code"] == "unsupported_operation"
                  and unknown.status_code == 404 and unknown.json()["error"]["code"] == "item_unavailable"
                  and download.status_code == 400 and download.json()["error"]["code"] == "download_requires_read"
                  and unauthenticated.status_code == 401)
            customer_flag = client.post("/api/v1/provisioning", json=report("flag", "verified_one"), headers=alpha)
            staff_flag = client.post("/api/v1/provisioning", json=report("flag", "verified_one"),
                                     headers={"Authorization": "Bearer " + staff.key})
            check("a_flag_over_http_needs_a_staff_role_and_withdraws_a_verified_item_at_once",
                  customer_flag.status_code == 403 and customer_flag.json()["error"]["code"] == "staff_role_required"
                  and staff_flag.status_code == 200 and staff_flag.json()["result"]["withdrawn"] is True
                  and staff_flag.json()["result"]["flags"] == 1)
            protocol = {"Authorization": "Bearer " + beta.key, "Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2025-11-25"}
            tools = _protocol_message(client.post("/mcp", headers=protocol, json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}))
            called = _protocol_message(client.post("/mcp", headers=protocol, json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                    "name": REPORT_TOOL, "arguments": {"identity": "verified_two",
                                                       "expected_digest": digests["verified_two"], "reason": REASON}}}))
            names = [tool["name"] for tool in ((tools or {}).get("result") or {}).get("tools", [])]
            structured = ((called or {}).get("result") or {}).get("structuredContent") or {}
            check("a_report_over_the_protocol_tool_is_recorded_against_the_exact_item_version",
                  REPORT_TOOL in names and structured.get("result", {}).get("state") == RECORDED
                  and structured["result"]["reports"] == 1 and structured["result"]["library_tier"] == "verified"
                  and "verified_two" in listed(alpha))
    from pathlib import Path
    from .http_test_fixtures import HttpDomainFixture
    (Path(root) / "image").mkdir()
    image = HttpDomainFixture(Path(root) / "image")
    with running_http(image) as (base, _service):
        answer = httpx.post(base + "/api/v1/provisioning", headers=image.headers(), trust_env=False, timeout=5,
                            json={"record_type": TIERED_PROVISIONING_REQUEST_VERSION, "operation": "report",
                                  "identity": "skill.alpha", "expected_digest": image.bindings["skill.alpha"].body_digest,
                                  "reason": REASON})
        check("a_host_without_a_catalogue_refresher_takes_no_report",
              answer.status_code == 503 and answer.json()["error"]["code"] == "catalogue_reports_unavailable")


def run_checks(check=None):
    tests = []
    if check is None:
        def check(name, passed):
            tests.append({"test": name, "passed": bool(passed),
                          "detail": "real temporary service store, body folder and loopback service; no provider"})
    with tempfile.TemporaryDirectory(prefix="catalogue-report-rules-") as directory:
        _rule_checks(check, directory)
    with tempfile.TemporaryDirectory(prefix="catalogue-report-transport-") as directory:
        _transport_checks(check, directory)
    return {"record_type": "catalogue_report_checks/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}


def self_test():
    return run_checks()


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2))
