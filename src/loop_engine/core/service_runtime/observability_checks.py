"""Acceptance for operator observability, over real HTTP and a real store.

Every guard here is shown twice: once doing its job, and once refusing the
known-wrong case it exists to prevent. A check that only shows the good case
would still pass after the guard was deleted.
"""
from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path
import sqlite3
import tempfile
import time

from .http import PROVISIONING_REQUEST_VERSION
from .http_test_fixtures import HttpDomainFixture, running_http
from .observability import (
    FAILURE_RECORD_VERSION, HEALTH_RECORD_VERSION, MAXIMUM_FAILURE_LISTING, METADATA_AND_REQUEST_BODY,
    METADATA_ONLY, OTHER_METHOD, REFERENCE_CHARACTERS, UNMATCHED_ROUTE, RequestReference,
    ServiceFailureJournal, ServiceObservabilityPolicy, new_request_reference, readiness_deadline_report,
    readiness_report, valid_reference,
)
from .records import ServiceRuntimeConfig, ServiceRuntimeError

PRIVATE_BODY_MARK = "PRIVATE_PROBE_PAYLOAD_MARK"


def _refused(function, *arguments, **fields):
    """Return the refusal code of a call that must not succeed, or empty text."""
    try:
        function(*arguments, **fields)
    except ServiceRuntimeError as error:
        return error.code
    except Exception as error:  # pragma: no cover - a different failure is still a refusal
        return type(error).__name__
    return ""


def _stored_text(root):
    """Return every byte the durable store holds, as text an operator could read."""
    connection = sqlite3.connect(str(root / "service.db"))
    try:
        rows = connection.execute("SELECT * FROM records").fetchall()
    finally:
        connection.close()
    return json.dumps(rows, default=str)


def _journal(root, **policy_fields):
    config = ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=True)
    return ServiceFailureJournal(config, ("/api/v1/session", "/api/v1/provisioning", "/mcp"),
                                 policy=ServiceObservabilityPolicy(**policy_fields))


def _reference_checks(check, root):
    """A request reference is unguessable and cannot come from a credential."""
    issued = [new_request_reference().value for _index in range(2000)]
    check("a_request_reference_is_distinct_unguessable_and_correctly_shaped",
          len(set(issued)) == 2000 and all(valid_reference(value) for value in issued)
          and all(len(value) == REFERENCE_CHARACTERS for value in issued))
    # Known-wrong case: the issuing function takes no argument at all, so no
    # credential, address or tenant has any way to reach it. A change that
    # added one would fail here before it could derive a reference from a key.
    check("the_reference_issuer_accepts_no_input_a_credential_could_travel_in",
          not inspect.signature(new_request_reference).parameters)
    journal = _journal(root)
    credential_shaped = RequestReference("ref_" + "abcdefghijklmnopqrstuvwxyz"[:26])
    # Known-wrong case: a value with the right shape that this process did not
    # issue, of the kind a caller would produce from a credential digest. The
    # journal refuses it, so a recorded reference is always a random one.
    check("a_reference_this_process_did_not_issue_is_refused_by_the_journal",
          _refused(journal.build, credential_shaped, route="/api/v1/session", method="GET",
                   refusal_code="unauthorized", status=401, tenant_id="", sequence=1)
          == "unissued_request_reference")
    check("a_reference_of_the_wrong_shape_cannot_even_be_built",
          _refused(RequestReference, "not-a-reference") == "invalid_request_reference"
          and _refused(RequestReference, "ref_" + "A" * 26) == "invalid_request_reference"
          and not valid_reference("ref_" + "0" * 26))


def _record_shape_checks(check, root):
    """A failure record holds declared metadata and refuses everything else."""
    journal = _journal(root)
    reference = new_request_reference()
    built = journal.build(reference, route="/api/v1/provisioning", method="POST",
                          refusal_code="item_unavailable", status=404, tenant_id="alpha", sequence=7)
    check("a_failure_record_holds_the_identity_route_code_tenant_time_and_version",
          built["record_type"] == FAILURE_RECORD_VERSION
          and built["request_reference"] == reference.value
          and built["route"] == "/api/v1/provisioning" and built["method"] == "POST"
          and built["refusal_code"] == "item_unavailable" and built["status"] == 404
          and built["tenant_id"] == "alpha" and type(built["at"]) is int
          and isinstance(built["service_version"], str) and built["service_version"]
          and built["payload_capture"] == METADATA_ONLY and "request_body" not in built)
    # Known-wrong case: the raw path of a request the service does not declare.
    # A stranger chooses that text, so it is recorded as the unmatched name.
    check("an_undeclared_path_is_never_written_into_a_record_as_sent",
          journal.route_of("/api/v1/download?credential=" + PRIVATE_BODY_MARK) == UNMATCHED_ROUTE
          and journal.route_of("/api/v1/session") == "/api/v1/session"
          and _refused(journal.build, reference, route="/api/v1/download?x=1", method="GET",
                       refusal_code="unauthorized", status=401, tenant_id="", sequence=1)
          == "undeclared_failure_route")
    check("an_unusual_method_and_an_invalid_status_or_tenant_are_refused",
          journal.method_of("BREW") == OTHER_METHOD and journal.method_of("POST") == "POST"
          and _refused(journal.build, reference, route=UNMATCHED_ROUTE, method="BREW",
                       refusal_code="unauthorized", status=401, tenant_id="", sequence=1)
          == "unsupported_failure_method"
          and _refused(journal.build, reference, route=UNMATCHED_ROUTE, method="GET",
                       refusal_code="unauthorized", status=99, tenant_id="", sequence=1)
          == "invalid_failure_status"
          and _refused(journal.build, reference, route=UNMATCHED_ROUTE, method="GET",
                       refusal_code="unauthorized", status=401, tenant_id="not a tenant", sequence=1)
          == "invalid_request")
    # Known-wrong case: a caller asking to keep a request body while the host
    # policy records metadata only. The record refuses instead of quietly
    # storing a private payload against the host's written choice.
    check("a_request_body_is_refused_while_the_host_records_metadata_only",
          _refused(journal.build, reference, route=UNMATCHED_ROUTE, method="POST",
                   refusal_code="invalid_json", status=400, tenant_id="", sequence=1,
                   request_body=PRIVATE_BODY_MARK.encode()) == "payload_capture_not_authorized")
    opted_in = _journal(root, payload_capture=METADATA_AND_REQUEST_BODY)
    kept = opted_in.build(reference, route=UNMATCHED_ROUTE, method="POST", refusal_code="invalid_json",
                          status=400, tenant_id="", sequence=1, request_body=PRIVATE_BODY_MARK.encode())
    check("an_explicitly_configured_host_may_keep_a_bounded_request_body",
          kept["payload_capture"] == METADATA_AND_REQUEST_BODY
          and kept["request_body"]["text"] == PRIVATE_BODY_MARK
          and kept["request_body"]["truncated"] is False
          and opted_in.build(reference, route=UNMATCHED_ROUTE, method="POST",
                             refusal_code="invalid_json", status=400, tenant_id="", sequence=1,
                             request_body=b"x" * 5000)["request_body"]["truncated"] is True)
    check("an_unsupported_observability_policy_is_refused_before_it_is_used",
          _refused(ServiceObservabilityPolicy, payload_capture="everything")
          == "invalid_observability_policy"
          and _refused(ServiceObservabilityPolicy, retained_failures=0) == "invalid_observability_policy"
          and _refused(ServiceObservabilityPolicy, minimum_free_bytes=0) == "invalid_observability_policy"
          and _refused(ServiceObservabilityPolicy, minimum_free_bytes="lots") == "invalid_observability_policy"
          and _refused(ServiceObservabilityPolicy, record_type="service_observability_policy/v2")
          == "unsupported_observability_policy")


def _ring_checks(check, root):
    """The journal keeps a bounded number of records and orders them exactly."""
    journal = _journal(root, retained_failures=4)
    for index in range(10):
        outcome = journal.record(new_request_reference(), route="/api/v1/session", method="GET",
                                 refusal_code="unauthorized", status=401, tenant_id="alpha")
        if not outcome["recorded"]:
            break
    listed = journal.recent(limit=4)
    check("the_journal_keeps_only_its_retained_count_and_returns_the_newest_first",
          listed["stored"] == 4 and listed["returned"] == 4
          and [row["sequence"] for row in listed["failures"]] == [10, 9, 8, 7])
    # A restart continues the same sequence instead of overwriting the newest
    # records from the beginning of the ring.
    restarted = _journal(root, retained_failures=4)
    restarted.record(new_request_reference(), route="/api/v1/session", method="GET",
                     refusal_code="tenant_disabled", status=401, tenant_id="beta")
    after = restarted.recent(limit=4)
    check("a_restarted_service_continues_the_sequence_and_does_not_lose_the_newest",
          after["failures"][0]["sequence"] == 11 and after["stored"] == 4
          and [row["sequence"] for row in after["failures"]] == [11, 10, 9, 8])
    check("the_journal_can_be_read_for_one_tenant_and_for_one_reference",
          restarted.recent(limit=4, tenant_id="beta")["returned"] == 1
          and restarted.recent(limit=4, tenant_id="beta")["failures"][0]["tenant_id"] == "beta"
          and restarted.recent(limit=4, tenant_id="alpha")["returned"] == 3
          and restarted.detail(after["failures"][0]["request_reference"])["returned"] == 1
          and restarted.detail("ref_" + "a" * 26)["returned"] == 0)
    check("an_invalid_read_request_is_refused_rather_than_answered_with_everything",
          _refused(restarted.recent, limit=0) == "invalid_failure_limit"
          and _refused(restarted.recent, limit=MAXIMUM_FAILURE_LISTING + 1) == "invalid_failure_limit"
          and restarted.recent(limit=MAXIMUM_FAILURE_LISTING)["returned"] == 4
          and _refused(restarted.detail, "not-a-reference") == "invalid_request_reference"
          and _refused(restarted.recent, tenant_id="not a tenant") == "invalid_request")
    # Known-wrong case: a host that withheld write authority. Reading works;
    # recording does not silently write anyway.
    reader = ServiceFailureJournal(ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=False),
                                   ("/api/v1/session",), policy=ServiceObservabilityPolicy(retained_failures=4))
    outcome = reader.record(new_request_reference(), route="/api/v1/session", method="GET",
                            refusal_code="unauthorized", status=401, tenant_id="alpha")
    check("a_journal_without_host_write_authority_reads_but_never_writes",
          outcome["recorded"] is False and outcome["reason"] == "host_write_authority_required"
          and reader.recent(limit=4)["stored"] == 4)
    # Known-wrong case: recording turned off. Nothing is written and the answer
    # says why, instead of reporting a record that does not exist.
    silent = _journal(root, record_failures=False, retained_failures=4)
    check("a_host_that_turned_recording_off_records_nothing_and_says_so",
          silent.record(new_request_reference(), route="/api/v1/session", method="GET",
                        refusal_code="unauthorized", status=401, tenant_id="alpha")
          == {"recorded": False, "reason": "recording_disabled"}
          and silent.recent(limit=4)["failures"][0]["sequence"] == 11)


def _readiness_checks(check, root):
    """Readiness is measured, and it can report not ready."""
    (root / "ready").mkdir()
    fixture = HttpDomainFixture(root / "ready")
    policy = ServiceObservabilityPolicy(release_reference="probe-release")
    passing = readiness_report(config=fixture.runtime.config, provisioning=fixture.provisioning,
        authentication_modes=("host_key",), policy=policy, browser_identity_installed=False,
        billing_sessions_installed=False, billing_webhook_installed=False)
    check("a_service_with_every_dependency_answering_reports_alive_and_ready",
          passing["record_type"] == HEALTH_RECORD_VERSION and passing["alive"] is True
          and passing["ready"] is True and passing["readiness_checked"] is True
          and passing["release_reference"] == "probe-release"
          and {row["name"] for row in passing["checks"]} >= {
              "durable_store_answers", "volume_has_write_headroom", "catalogue_registered",
              "interface_page_readable", "authentication_mode_installed"})
    # The required set is exactly the three answers that decide whether this
    # machine can serve anyone at all. A change that quietly made one more
    # thing required, and so could take a working service out of service,
    # fails here.
    check("exactly_the_three_dependencies_that_can_stop_every_answer_are_required",
          {row["name"] for row in passing["checks"] if row["required"]}
          == {"durable_store_answers", "volume_has_write_headroom", "authentication_mode_installed"})
    # Known-wrong case: the durable store is gone. A health answer that could
    # not fail would still say ready here, which is what makes it decoration.
    missing = replace(fixture.runtime.config, database_path=str(root / "absent" / "service.db"))
    broken = readiness_report(config=missing, provisioning=fixture.provisioning,
        authentication_modes=("host_key",), policy=policy, browser_identity_installed=False,
        billing_sessions_installed=False, billing_webhook_installed=False)
    store_check = next(row for row in broken["checks"] if row["name"] == "durable_store_answers")
    check("a_service_whose_store_does_not_answer_reports_not_ready_with_the_reason",
          broken["alive"] is True and broken["ready"] is False
          and store_check["passed"] is False and store_check["required"] is True
          and store_check["code"] == "store_unavailable")
    # Known-wrong case: the volume has filled. A read still answers, so the
    # store check above passes and only this check can see it. The threshold is
    # driven past the real free space of the disk under the test, so the check
    # must compare a measured figure and cannot be a constant true.
    full = readiness_report(config=fixture.runtime.config, provisioning=fixture.provisioning,
        authentication_modes=("host_key",), policy=replace(policy, minimum_free_bytes=2**40),
        browser_identity_installed=False, billing_sessions_installed=False,
        billing_webhook_installed=False)
    volume_check = next(row for row in full["checks"] if row["name"] == "volume_has_write_headroom")
    store_still_answers = next(row for row in full["checks"] if row["name"] == "durable_store_answers")
    check("a_volume_without_room_to_write_is_not_ready_even_though_reads_answer",
          full["ready"] is False and volume_check["passed"] is False
          and volume_check["required"] is True and volume_check["code"] == "volume_nearly_full"
          and store_still_answers["passed"] is True)
    # Known-wrong case: the volume is not there to measure at all.
    absent_volume = readiness_report(config=missing, provisioning=fixture.provisioning,
        authentication_modes=("host_key",), policy=policy, browser_identity_installed=False,
        billing_sessions_installed=False, billing_webhook_installed=False)
    check("a_volume_that_cannot_be_measured_is_reported_rather_than_assumed_healthy",
          absent_volume["ready"] is False
          and next(row for row in absent_volume["checks"]
                   if row["name"] == "volume_has_write_headroom")["code"] == "volume_unavailable")
    # Known-wrong case: no way to sign any request in. Nothing this machine
    # serves can succeed, so it reports not ready.
    class _Empty:
        catalogue = type("catalogue", (), {"items": {}})()
    empty = readiness_report(config=fixture.runtime.config, provisioning=_Empty(),
        authentication_modes=(), policy=policy, browser_identity_installed=False,
        billing_sessions_installed=False, billing_webhook_installed=False)
    check("a_service_with_no_installed_authentication_mode_is_not_ready",
          empty["ready"] is False
          and {row["name"] for row in empty["checks"] if row["required"] and not row["passed"]}
          == {"authentication_mode_installed"}
          and next(row for row in empty["checks"]
                   if row["name"] == "authentication_mode_installed")["code"] == "no_authentication_mode")
    # An empty catalogue is reported and does not remove the machine. A fresh
    # deployment whose catalogue has not been loaded still serves every other
    # route, and the container check starts the image with no items at all.
    empty_catalogue = next(row for row in empty["checks"] if row["name"] == "catalogue_registered")
    serving_nothing = readiness_report(config=fixture.runtime.config, provisioning=_Empty(),
        authentication_modes=("host_key",), policy=policy, browser_identity_installed=False,
        billing_sessions_installed=False, billing_webhook_installed=False)
    check("an_empty_catalogue_is_reported_without_removing_the_machine_from_service",
          empty_catalogue["required"] is False and empty_catalogue["passed"] is False
          and empty_catalogue["code"] == "catalogue_empty"
          and serving_nothing["ready"] is True)
    # An adapter the host did not install, and an interface page that cannot be
    # read, are reported and do not make the machine unready, because every
    # route a customer harness calls still answers correctly.
    check("an_uninstalled_adapter_or_page_is_reported_without_removing_the_machine",
          passing["ready"] is True
          and all(row["required"] is False for row in passing["checks"]
                  if row["name"] in ("browser_identity_installed", "billing_sessions_installed",
                                     "billing_webhook_installed", "interface_page_readable",
                                     "catalogue_registered")))
    # Known-wrong case: measuring did not finish inside the request deadline.
    # The answer keeps the one health shape the deployment gate reads and says
    # not ready, with the one failed check that names why.
    late = readiness_deadline_report(policy)
    check("a_readiness_answer_that_ran_out_of_time_is_not_ready_in_the_same_shape",
          late["record_type"] == HEALTH_RECORD_VERSION and late["alive"] is True
          and late["ready"] is False and late["readiness_checked"] is True
          and set(late) == set(passing) and late["release_reference"] == "probe-release"
          and [row["name"] for row in late["checks"] if row["required"] and not row["passed"]]
          == ["readiness_within_deadline"])
    # A store nothing has written yet does not answer a read, so a service on
    # a fresh volume is alive and not ready until its host registers a tenant,
    # which is what creates the store. A release check that starts the image
    # on an empty volume must configure it first, as production does.
    (root / "fresh").mkdir()
    fresh = ServiceRuntimeConfig(str(root / "fresh" / "service.db"), writes_authorized=True)
    unconfigured = readiness_report(config=fresh, provisioning=fixture.provisioning,
        authentication_modes=("host_key",), policy=policy, browser_identity_installed=False,
        billing_sessions_installed=False, billing_webhook_installed=False)
    from .records import TenantRegistration
    from .runtime import ServiceRuntime
    ServiceRuntime(fresh).register_tenant(TenantRegistration("fresh", "fresh:private"))
    configured = readiness_report(config=fresh, provisioning=fixture.provisioning,
        authentication_modes=("host_key",), policy=policy, browser_identity_installed=False,
        billing_sessions_installed=False, billing_webhook_installed=False)
    check("a_store_nothing_has_created_is_not_ready_until_a_tenant_is_registered",
          unconfigured["alive"] is True and unconfigured["ready"] is False
          and [(row["name"], row["code"]) for row in unconfigured["checks"]
               if row["required"] and not row["passed"]] == [("durable_store_answers", "store_unavailable")]
          and configured["ready"] is True)


def _live_http_checks(check, root):
    """Drive the real transport and read what an operator can find afterwards."""
    import httpx
    fixture = HttpDomainFixture(root)
    with running_http(fixture) as (base, service):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            healthy = client.get("/api/v1/health")
            good = client.post("/api/v1/provisioning", headers=fixture.headers(),
                               json={"record_type": PROVISIONING_REQUEST_VERSION, "operation": "list"})
            check("a_running_service_answers_the_measured_health_question",
                  healthy.status_code == 200
                  and healthy.json()["result"]["record_type"] == HEALTH_RECORD_VERSION
                  and healthy.json()["result"]["ready"] is True
                  and healthy.json()["result"]["readiness_checked"] is True
                  and good.status_code == 200)
            # Known-wrong case: a required dependency that fails must take the
            # machine out of rotation, so the route answers 503 with the same
            # record and names the failed check. A route that answered 200 here
            # would keep the load balancer sending customers to a machine that
            # cannot serve them. The store is made to fail for this one
            # question; nothing in it changes.
            from unittest.mock import patch
            from . import observability
            failed = observability.ReadinessCheck("durable_store_answers", True, False, "store_unavailable")
            with patch.object(observability, "store_readiness", lambda _config: failed):
                unready = client.get("/api/v1/health")
            check("a_service_that_is_not_ready_answers_503_and_names_the_failed_check",
                  unready.status_code == 503
                  and unready.json()["result"]["record_type"] == HEALTH_RECORD_VERSION
                  and unready.json()["result"]["alive"] is True
                  and unready.json()["result"]["ready"] is False
                  and [(row["name"], row["code"]) for row in unready.json()["result"]["checks"]
                       if row["required"] and not row["passed"]]
                  == [("durable_store_answers", "store_unavailable")])
            anonymous = client.get("/api/v1/session")
            wrong = client.get("/api/v1/session",
                               headers={"Authorization": "Bearer WRONG_PROBE_TOKEN_" + PRIVATE_BODY_MARK})
            missing_item = client.post("/api/v1/provisioning", headers=fixture.headers(),
                json={"record_type": PROVISIONING_REQUEST_VERSION, "operation": "manifest",
                      "identity": "skill.absent"})
            unknown = client.get("/api/v1/nowhere/" + PRIVATE_BODY_MARK, headers=fixture.headers())
            references = [response.json()["request_reference"]
                          for response in (anonymous, wrong, missing_item, unknown)]
            check("every_refusal_carries_a_distinct_reference_the_customer_can_read_back",
                  all(valid_reference(value) for value in references)
                  and len(set(references)) == 4
                  and anonymous.status_code == wrong.status_code == 401
                  and missing_item.status_code == unknown.status_code == 404)
            # A successful answer carries no reference, so the field cannot be
            # mistaken for part of a result record.
            check("a_successful_answer_is_unchanged_and_carries_no_refusal_reference",
                  "request_reference" not in good.json() and "request_reference" not in healthy.json())
            journal = service.failure_journal
            listed = journal.recent(limit=10)
            found = {row["request_reference"]: row for row in listed["failures"]}
            check("an_operator_finds_every_one_of_those_refusals_by_its_reference",
                  all(value in found for value in references)
                  and found[references[0]]["route"] == "/api/v1/session"
                  and found[references[0]]["refusal_code"] == "unauthorized"
                  and found[references[0]]["tenant_id"] == ""
                  and found[references[2]]["tenant_id"] == "alpha"
                  and found[references[2]]["refusal_code"] == "item_unavailable"
                  and found[references[2]]["route"] == "/api/v1/provisioning"
                  and found[references[3]]["route"] == UNMATCHED_ROUTE)
            check("the_reference_of_one_refusal_resolves_to_exactly_one_record",
                  journal.detail(references[1])["returned"] == 1
                  and journal.detail(references[1])["failures"][0]["refusal_code"] == "unauthorized")
            check("the_operator_can_narrow_the_journal_to_one_tenant",
                  {row["tenant_id"] for row in journal.recent(limit=10, tenant_id="alpha")["failures"]}
                  == {"alpha"})
            # Known-wrong case for privacy: the refused credential and the
            # private path text a stranger sent must appear nowhere in the store.
            stored = _stored_text(root)
            check("no_credential_and_no_private_request_text_reaches_the_durable_record",
                  PRIVATE_BODY_MARK not in stored
                  and fixture.keys["alpha"].key not in stored
                  and "Authorization" not in stored and "authorization" not in stored
                  and json.dumps(listed) and PRIVATE_BODY_MARK not in json.dumps(listed))


def _deadline_checks(check, root):
    """A health measurement that misses the request deadline answers 503, not ready."""
    import httpx
    import threading
    from unittest.mock import patch
    from . import http as transport
    fixture = HttpDomainFixture(root)
    release = threading.Event()
    measured = transport.readiness_report

    def held(**fields):
        # The measurement stays in flight until this check releases it, so the
        # deadline passes every time, whatever the load on the machine.
        release.wait(30)
        return measured(**fields)
    with patch.object(transport, "readiness_report", held):
        with running_http(fixture, request_timeout_seconds=0.5) as (base, _service):
            try:
                with httpx.Client(base_url=base, trust_env=False, timeout=10) as client:
                    late = client.get("/api/v1/health")
            finally:
                release.set()
    answer = late.json()["result"]
    check("a_health_measurement_that_misses_the_deadline_answers_503_not_ready",
          late.status_code == 503 and answer["record_type"] == HEALTH_RECORD_VERSION
          and answer["alive"] is True and answer["ready"] is False
          and [row["name"] for row in answer["checks"]] == ["readiness_within_deadline"])


def _payload_capture_checks(check, root):
    """The private body of a request is stored only when a host chose that."""
    import httpx
    private = {"record_type": PROVISIONING_REQUEST_VERSION, "operation": "manifest",
               "identity": PRIVATE_BODY_MARK}
    for name, policy, expected in (
            ("metadata_only", ServiceObservabilityPolicy(), False),
            ("opted_in", ServiceObservabilityPolicy(payload_capture=METADATA_AND_REQUEST_BODY), True)):
        directory = root / name
        directory.mkdir()
        fixture = HttpDomainFixture(directory)
        from .http import ServiceHttpApplication
        with running_http(fixture, application_factory=lambda configuration, policy=policy:
                          ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
                                                 observability=policy)) as (base, service):
            with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
                refused = client.post("/api/v1/provisioning", headers=fixture.headers(), json=private)
        stored = _stored_text(directory)
        check(f"a_host_recording_{name}_stores_the_request_body_only_when_it_chose_to",
              refused.status_code == 404
              and refused.json()["error"]["code"] == "item_unavailable"
              and valid_reference(refused.json()["request_reference"])
              and (PRIVATE_BODY_MARK in stored) is expected
              and fixture.keys["alpha"].key not in stored)


def _credential_body_checks(check, root):
    """A body that carries a credential stays out of the record, whatever the host chose.

    Sign-up carries the password of a new account, and promotion redemption
    carries a code that grants paid access to whoever holds it. Body capture was
    written before either address reached this transport, and on September 22,
    2026 it kept their bodies as it keeps any other, so a host that captured
    bodies stored a password and a code as plain text. Both refusals must still
    be recorded, only without the body, and a body that carries no credential
    must still be kept, so the host's choice holds everywhere else.
    """
    import httpx
    from .account_email import SIGNUP_PATH, AccountEmailAdapter
    from .account_email_checks import SIGNUP_REQUEST, SIGNUP_SECRET_VALUE, _Provider, _secrets, _settings
    from .http import PROMOTION_REDEMPTION_PATH, ServiceHttpApplication
    from .promotion_checks import GUESSED_BODY, PREFIX
    from .promotions import PromotionPolicy, PromotionRedemption
    from .request_limits import SOCKET_PEER_SOURCE, ServiceRequestLimits
    capture = ServiceObservabilityPolicy(payload_capture=METADATA_AND_REQUEST_BODY)
    fixture = HttpDomainFixture(root)
    provider = _Provider()
    promotions = PromotionRedemption(fixture.runtime, PromotionPolicy(redemption_enabled=True))
    code = PREFIX + "-" + GUESSED_BODY

    def build(configuration):
        adapter = AccountEmailAdapter(_settings(allow_loopback=True), _secrets,
            public_base_url=configuration.public_base_url, address_limits=configuration.request_limits,
            display_name=configuration.display_name, identity_transport=provider.identity,
            mail_transport=provider.mail)
        return ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
                                      account_email=adapter, promotions=promotions, observability=capture)
    limits = ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE, failures_allowed=50, window_seconds=600)
    with running_http(fixture, application_factory=build, request_limits=limits) as (base, service):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            signup = client.post(SIGNUP_PATH, json={**SIGNUP_REQUEST, "unexpected": True})
            redemption = client.post(PROMOTION_REDEMPTION_PATH, headers=fixture.headers(), json={
                "record_type": "service_promotion_redemption_request/v1", "code": code,
                "request_id": "credential-body"})
            private = client.post("/api/v1/provisioning", headers=fixture.headers(), json={
                "record_type": PROVISIONING_REQUEST_VERSION, "operation": "manifest",
                "identity": PRIVATE_BODY_MARK})
        recorded = {row["route"]: row for row in service.failure_journal.recent(limit=10)["failures"]}
    stored = _stored_text(root)
    check("a_body_that_carries_a_credential_is_never_captured_even_when_the_host_captures_bodies",
          signup.status_code == 400 and redemption.status_code == 403 and private.status_code == 404
          and {SIGNUP_PATH, PROMOTION_REDEMPTION_PATH, "/api/v1/provisioning"} <= set(recorded)
          and "request_body" not in recorded[SIGNUP_PATH]
          and "request_body" not in recorded[PROMOTION_REDEMPTION_PATH]
          and "request_body" in recorded["/api/v1/provisioning"]
          and SIGNUP_SECRET_VALUE not in stored and code not in stored and PRIVATE_BODY_MARK in stored)


def _read_command_checks(check, root):
    """The operator command reads and cannot write, even by mistake."""
    from .http_entrypoint import read_failures
    fixture = HttpDomainFixture(root)
    journal = ServiceFailureJournal(fixture.runtime.config, ("/api/v1/session",),
                                    policy=ServiceObservabilityPolicy(retained_failures=6))
    saved = []
    for tenant in ("alpha", "alpha", "beta"):
        reference = new_request_reference()
        journal.record(reference, route="/api/v1/session", method="GET",
                       refusal_code="unauthorized", status=401, tenant_id=tenant)
        saved.append(reference.value)
    host = root / "host.json"
    host.write_text(json.dumps({"record_type": "service_http_host_configuration/v1",
        "runtime": {"database_path": str(root / "service.db"), "writes_authorized": True},
        "http": {}, "authentication": {}, "manifest_path": "/absent",
        "observability": {"retained_failures": 6}}), encoding="utf-8")
    before = (root / "service.db").read_bytes()
    newest = read_failures(str(host), limit=2)
    one_tenant = read_failures(str(host), tenant="beta")
    one_reference = read_failures(str(host), reference=saved[0])
    check("the_operator_command_answers_the_three_questions_an_operator_asks",
          newest["returned"] == 2 and newest["stored"] == 3
          and one_tenant["returned"] == 1 and one_tenant["failures"][0]["tenant_id"] == "beta"
          and one_reference["returned"] == 1
          and one_reference["failures"][0]["request_reference"] == saved[0])
    check("the_operator_command_changed_nothing_in_the_store",
          (root / "service.db").read_bytes() == before)
    # Known-wrong case: the reader is built with host writes withheld, so a
    # future change that tried to write through it is refused rather than
    # quietly changing a record an operator is reading.
    withheld = ServiceFailureJournal(ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=False),
                                     ("/api/v1/session",), policy=ServiceObservabilityPolicy())
    check("the_read_path_holds_no_write_authority_at_all",
          withheld.record(new_request_reference(), route="/api/v1/session", method="GET",
                          refusal_code="unauthorized", status=401, tenant_id="alpha")["reason"]
          == "host_write_authority_required"
          and _refused(read_failures, str(host), tenant="beta", reference=saved[0]) == "invalid_request"
          and _refused(read_failures, str(host), reference="not-a-reference")
          == "invalid_request_reference")
    # The operator reaches the journal through the command, not through the
    # function. A release once carried this function, its help text and its
    # guide while the command itself was missing from the entry point, so
    # asking for it was refused as an unknown command.
    from contextlib import redirect_stdout
    from io import StringIO
    from ...cli_help import COMMAND_HELP
    from .http_entrypoint import SERVICE_COMMANDS, main
    printed = StringIO()
    try:
        with redirect_stdout(printed):
            status = main(["failures", "--config", str(host), "--limit", "2"])
        answered = json.loads(printed.getvalue())
    except (SystemExit, ValueError):
        status, answered = None, {}
    check("the_failures_command_answers_through_the_service_entry_point",
          status == 0 and answered.get("returned") == 2 and answered.get("stored") == 3
          and answered.get("failures") == newest["failures"]
          and (root / "service.db").read_bytes() == before)
    usage = COMMAND_HELP["service"].splitlines()[0]
    named = set(usage[usage.index("{") + 1:usage.index("}")].split("|"))
    if "loop-engine service smoke" in usage:
        named.add("smoke")
    check("every_service_command_the_help_names_is_one_the_entry_point_accepts",
          named == set(SERVICE_COMMANDS))


def run_checks(check=None):
    """Run every observability check, in its own temporary service directory."""
    tests = []
    if check is None:
        def check(name, passed):
            tests.append({"test": name, "passed": bool(passed),
                          "detail": "real loopback transport and a real durable store; no external provider"})
    for name, function in (("references", _reference_checks), ("record_shape", _record_shape_checks),
                           ("ring", _ring_checks), ("readiness", _readiness_checks),
                           ("live_http", _live_http_checks), ("deadline", _deadline_checks),
                           ("payload_capture", _payload_capture_checks),
                           ("credential_body", _credential_body_checks),
                           ("read_command", _read_command_checks)):
        with tempfile.TemporaryDirectory(prefix="service-observability-" + name + "-") as directory:
            try:
                function(check, Path(directory))
            except Exception:
                # A group that stops part way is a failure with a name, so a
                # missing guard is reported as such instead of ending the run.
                check(f"the_{name}_checks_ran_to_completion", False)
    if not tests:
        return None
    return {"record_type": "service_observability_test/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
