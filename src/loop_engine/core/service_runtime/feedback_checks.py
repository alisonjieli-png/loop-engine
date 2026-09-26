"""Feedback checks over real SQLite records and a real loopback transport.

Every refusal has a check, and the four known-wrong cases the package names
have a control each: a rating without a download, a request over the bound, a
search gap that stores query text, and a second rating that does not replace
the first. Each control removes one guard and shows that the guard is what
refuses. No identity provider, payment provider or mail provider is contacted.
"""
from __future__ import annotations

import json
from unittest.mock import patch

from .feedback import (
    ASK_FOR_MATERIAL_LINE, DESCRIPTION_INVALID, DESCRIPTION_LIMIT, GAP_HOLDS_QUERY_TEXT, GAP_KIND, GAP_SCHEMA,
    NOTE_LIMIT, NOTE_TOO_LONG, RATING_KIND, RATING_REQUIRES_DOWNLOAD, RATING_VALUE_INVALID, REQUEST_IDENTITY_CONFLICT,
    REQUEST_KIND, STAFF_VIEW_VERSION, ServiceFeedback, assert_metadata_only, feedback_rows, search_gap_payload,
)
from .http_test_fixtures import HttpDomainFixture, running_http
from .records import ACCESS_MANAGE_SCOPE, ServiceRuntimeError, TenantKeyIssue, TenantRegistration, canonical
from .storage import ServiceCatalogBinding

PROVISIONING_PATH, DOWNLOAD_PATH, RETRIEVAL_PATH = "/api/v1/provisioning", "/api/v1/download", "/api/v1/retrieval"
ADMIN_FEEDBACK_PATH = "/api/v1/admin/feedback"
REQUEST_VERSION = "service_provisioning_request/v2"
QUERY = "a query nobody stores anywhere"


def refused(function, *codes):
    try:
        function()
    except ServiceRuntimeError as error:
        return not codes or error.code in codes
    return False


def prepared(root):
    root.mkdir(parents=True, exist_ok=True)
    fixture = HttpDomainFixture(root)
    fixture.runtime.register_tenant(TenantRegistration("operator", "operator:private", (ACCESS_MANAGE_SCOPE,)))
    fixture.operator_key = fixture.runtime.issue_key(TenantKeyIssue("operator", "local feedback operator"))
    fixture.keys["operator"] = fixture.operator_key
    fixture.feedback = ServiceFeedback(fixture.runtime)
    return fixture


def rows_of(runtime, kind):
    with runtime._catalog.store() as store:
        return runtime._catalog.rows_all(store, kind)


def run_checks(check, root):
    fixture = prepared(root)
    runtime, feedback = fixture.runtime, fixture.feedback
    alpha = runtime.authenticate_key(fixture.keys["alpha"].key)
    operator = runtime.authenticate_key(fixture.operator_key.key)
    alpha_digest = fixture.bindings["skill.alpha"].body_digest
    large_digest = fixture.bindings["skill.large"].body_digest
    rate = lambda **fields: feedback.rate(alpha, {"identity": "skill.alpha", "expected_digest": alpha_digest,
                                                  "value": "useful", **fields})

    # Refusal one: a rating of an item the account never downloaded.
    check("a_rating_without_a_download_is_refused", refused(rate, RATING_REQUIRES_DOWNLOAD)
          and rows_of(runtime, RATING_KIND) == [])
    with patch.object(ServiceFeedback, "_downloaded", lambda self, store, tenant, item, body: True):
        check("KNOWN_WRONG_without_the_download_check_a_rating_of_an_unread_item_is_recorded",
              rate()["committed"] is True and len(rows_of(runtime, RATING_KIND)) == 1)
    with runtime._catalog.store(write=True) as store:
        held = rows_of(runtime, RATING_KIND)[0]
        runtime._catalog.commit(store, (), (runtime._catalog.guard(held),), removals=(held["record_id"],))
    check("the_known_wrong_rating_was_removed_before_the_real_cases", rows_of(runtime, RATING_KIND) == [])

    # The account downloads the item, and the usage record is what a rating needs.
    fixture.provisioning.invoke(fixture.keys["alpha"].key, "read", identity="skill.alpha", request_id="download-1")
    first = rate(note="  Saved me the source review.  ")
    check("a_rating_after_a_download_is_recorded_with_the_trimmed_note",
          first["committed"] is True and first["replaced"] is False and first["revision"] == 1
          and rows_of(runtime, RATING_KIND)[0]["payload"]["note"] == "Saved me the source review."
          and rows_of(runtime, RATING_KIND)[0]["payload"]["record_type"] == "catalogue_item_rating/v1")
    check("a_rating_of_a_revision_the_account_did_not_download_is_refused",
          refused(lambda: rate(expected_digest="f" * 64), RATING_REQUIRES_DOWNLOAD)
          and refused(lambda: feedback.rate(alpha, {"identity": "skill.large", "expected_digest": large_digest,
                                                    "value": "useful"}), RATING_REQUIRES_DOWNLOAD))
    check("a_rating_value_outside_useful_and_not_useful_is_refused",
          refused(lambda: rate(value="great"), RATING_VALUE_INVALID)
          and refused(lambda: rate(value=True), RATING_VALUE_INVALID))
    check("a_note_over_its_bound_or_with_control_characters_is_refused",
          refused(lambda: rate(note="x" * (NOTE_LIMIT + 1)), NOTE_TOO_LONG)
          and refused(lambda: rate(note="a\x00b"), NOTE_TOO_LONG)
          and refused(lambda: rate(note=["not", "text"]), NOTE_TOO_LONG))
    check("a_rating_with_a_field_outside_its_shape_is_refused",
          refused(lambda: rate(query="the text of a search"), "invalid_request")
          and refused(lambda: feedback.rate(alpha, {"identity": "skill.alpha", "value": "useful"}), "invalid_request"))
    second = rate(value="not_useful")
    held = rows_of(runtime, RATING_KIND)
    check("a_second_rating_of_the_same_item_replaces_the_first",
          second["replaced"] is True and second["revision"] == 2 and len(held) == 1
          and held[0]["payload"]["value"] == "not_useful" and held[0]["payload"]["note"] == "")
    # Known-wrong case: with the record keyed by anything but the account and
    # the item, a second rating is a second row and the first one stays.
    original_record, original_read = ServiceCatalogBinding.record, ServiceCatalogBinding.read

    def keyed_by_time(self, kind, logical_identity, payload, *, tenant_id=""):
        if kind == RATING_KIND:
            logical_identity = (logical_identity, payload["at"], payload["revision"])
        return original_record(self, kind, logical_identity, payload, tenant_id=tenant_id)

    def never_held(self, store, kind, logical_identity):
        return None if kind == RATING_KIND else original_read(self, store, kind, logical_identity)
    with patch.object(ServiceCatalogBinding, "record", keyed_by_time), \
            patch.object(ServiceCatalogBinding, "read", never_held):
        rate(value="useful")
    check("KNOWN_WRONG_keyed_by_time_a_second_rating_does_not_replace_the_first",
          len(rows_of(runtime, RATING_KIND)) == 2)
    with runtime._catalog.store(write=True) as store:
        extra = [row for row in rows_of(runtime, RATING_KIND) if row["record_id"] != held[0]["record_id"]]
        runtime._catalog.commit(store, (), tuple(runtime._catalog.guard(row) for row in extra),
                                removals=tuple(row["record_id"] for row in extra))
    check("the_known_wrong_second_row_was_removed", len(rows_of(runtime, RATING_KIND)) == 1)

    # Refusal two: a request for material over its bound.
    ask = lambda request_id, description: feedback.request_material(alpha, {"request_id": request_id,
                                                                            "description": description})
    check("a_request_over_the_bound_is_refused",
          refused(lambda: ask("req-1", "x" * (DESCRIPTION_LIMIT + 1)), DESCRIPTION_INVALID)
          and rows_of(runtime, REQUEST_KIND) == [])
    check("an_empty_request_or_one_that_is_not_text_is_refused",
          refused(lambda: ask("req-1", "   "), DESCRIPTION_INVALID) and refused(lambda: ask("req-1", 7), DESCRIPTION_INVALID))
    with patch("loop_engine.core.service_runtime.feedback.DESCRIPTION_LIMIT", DESCRIPTION_LIMIT * 10):
        check("KNOWN_WRONG_with_the_bound_raised_an_oversized_request_is_recorded",
              ask("req-0", "x" * (DESCRIPTION_LIMIT + 1))["committed"] is True)
    accepted = ask("req-1", "  A hook that refuses a commit without a changelog line.  ")
    repeated = ask("req-1", "A hook that refuses a commit without a changelog line.")
    check("a_request_is_recorded_once_and_a_retry_with_the_same_identity_repeats_it",
          accepted["committed"] is True and accepted["repeated"] is False and repeated["repeated"] is True
          and repeated["request_id_digest"] == accepted["request_id_digest"]
          and sum(1 for row in rows_of(runtime, REQUEST_KIND) if row["payload"]["description"].startswith("A hook")) == 1
          and rows_of(runtime, REQUEST_KIND)[0]["payload"]["record_type"] == "material_request/v1")
    check("the_same_request_identity_with_other_text_is_a_conflict",
          refused(lambda: ask("req-1", "Something else entirely."), REQUEST_IDENTITY_CONFLICT))
    check("a_request_with_a_field_outside_its_shape_is_refused",
          refused(lambda: feedback.request_material(alpha, {"request_id": "req-2", "description": "x", "query": "y"}),
                  "invalid_request"))

    # Refusal three: a search gap that would store query text.
    search = {"query": QUERY, "mode": "hybrid", "top_n": 5,
              "filters": {"harness_kind": {"equals": "hook"}, "step_functions": {"any_of": ["acting", "building"]},
                          "size_bytes": {"at_most": 4096}, "purpose": {"equals": QUERY}}}
    outcome = feedback.record_search_gap(search)
    stored = rows_of(runtime, GAP_KIND)
    text = canonical(stored[0]) if stored else ""
    check("a_search_gap_is_counted_with_the_filters_the_mode_the_hour_and_no_query_text",
          outcome["recorded"] is True and len(stored) == 1 and QUERY not in text and "query" not in stored[0]["payload"]
          and stored[0]["payload"]["record_type"] == GAP_SCHEMA and stored[0]["payload"]["hit_count"] == 0
          and stored[0]["payload"]["mode"] == "hybrid"
          and stored[0]["payload"]["filters"] == {"harness_kind": ["equals:hook"], "purpose": ["equals:other"],
                                                  "size_bytes": ["at_most:4096"],
                                                  "step_functions": ["any_of:acting", "any_of:building"]}
          and stored[0]["attributes"]["tenant_id"] == "" and "tenant_id" not in stored[0]["payload"])
    check("a_second_search_gap_in_the_same_hour_adds_to_the_count",
          feedback.record_search_gap(search)["searches"] == 2 and len(rows_of(runtime, GAP_KIND)) == 1)
    check("a_gap_payload_that_carries_the_query_is_refused_by_the_guard",
          refused(lambda: assert_metadata_only({"query": QUERY}, QUERY), GAP_HOLDS_QUERY_TEXT)
          and refused(lambda: assert_metadata_only({"note": "about " + QUERY}, QUERY), GAP_HOLDS_QUERY_TEXT))
    original_payload = search_gap_payload

    def with_query(fields, now):
        payload = original_payload(fields, now)
        return {**payload, "query": fields["query"]}
    with patch("loop_engine.core.service_runtime.feedback.search_gap_payload",
               lambda fields, now: assert_metadata_only(with_query(fields, now), fields.get("query"))):
        check("a_builder_that_adds_the_query_is_refused_and_nothing_is_written",
              feedback.record_search_gap({**search, "mode": "lexical"})["reason"] == GAP_HOLDS_QUERY_TEXT
              and len(rows_of(runtime, GAP_KIND)) == 1)
    with patch("loop_engine.core.service_runtime.feedback.search_gap_payload", with_query):
        feedback.record_search_gap({**search, "mode": "lexical"})
    check("KNOWN_WRONG_without_the_guard_a_search_gap_stores_the_query_text",
          any(QUERY in canonical(row) for row in rows_of(runtime, GAP_KIND)))
    with runtime._catalog.store(write=True) as store:
        extra = [row for row in rows_of(runtime, GAP_KIND) if QUERY in canonical(row)]
        runtime._catalog.commit(store, (), tuple(runtime._catalog.guard(row) for row in extra),
                                removals=tuple(row["record_id"] for row in extra))
    check("the_known_wrong_gap_row_was_removed", not any(QUERY in canonical(row) for row in rows_of(runtime, GAP_KIND)))

    # Staff read everything; a customer reads nothing.
    view = feedback.staff_view(operator)
    check("an_operator_with_the_administration_scope_reads_ratings_requests_and_gaps",
          view["record_type"] == STAFF_VIEW_VERSION and view["ratings"] == {
              "useful": 0, "not_useful": 1, "items": [{"item_identity": "skill.alpha", "useful": 0,
                                                       "not_useful": 1, "notes": []}]}
          and len(view["material_requests"]) == 2
          and any(row["description"].startswith("A hook") and row["state"] == "open" and row["tenant_id"] == "alpha"
                  for row in view["material_requests"])
          and len(view["search_gaps"]) == 1 and view["search_gaps"][0]["searches"] == 2
          and "query" not in view["search_gaps"][0])
    check("a_customer_cannot_read_the_feedback_view",
          refused(lambda: feedback.staff_view(alpha), "account_administration_forbidden"))
    everything = feedback_rows(runtime)
    check("the_report_reads_every_feedback_record_of_the_host",
          len(everything[RATING_KIND]) == 1 and len(everything[REQUEST_KIND]) == 2 and len(everything[GAP_KIND]) == 1)


def http_checks(check, root):
    import httpx
    fixture = prepared(root)
    alpha_digest = fixture.bindings["skill.alpha"].body_digest
    large_digest = fixture.bindings["skill.large"].body_digest
    with running_http(fixture) as (base, _service):
        post = lambda path, body, tenant="alpha": httpx.post(base + path, json=body, headers=fixture.headers(tenant),
                                                             trust_env=False)
        rate = lambda **fields: post(PROVISIONING_PATH, {"record_type": REQUEST_VERSION, "operation": "rate",
                                                         "identity": "skill.alpha", "expected_digest": alpha_digest,
                                                         "value": "useful", **fields})
        before = rate()
        check("over_http_a_rating_without_a_download_answers_409",
              before.status_code == 409 and before.json()["error"]["code"] == RATING_REQUIRES_DOWNLOAD)
        downloaded = post(DOWNLOAD_PATH, {"record_type": REQUEST_VERSION, "operation": "read", "identity": "skill.alpha",
                                          "expected_digest": alpha_digest, "request_id": "http-download-1"})
        rated = rate(note="Worked in the first step.")
        check("over_http_a_rating_after_a_download_is_recorded",
              downloaded.status_code == 200 and rated.status_code == 200
              and rated.json()["result"]["record_type"] == "catalogue_item_rating_result/v1"
              and rated.json()["result"]["committed"] is True and rated.json()["operation"] == "rate")
        other = post(PROVISIONING_PATH, {"record_type": REQUEST_VERSION, "operation": "rate", "identity": "skill.large",
                                         "expected_digest": large_digest, "value": "not_useful"})
        check("over_http_a_rating_of_another_item_the_account_did_not_download_answers_409",
              other.status_code == 409 and other.json()["error"]["code"] == RATING_REQUIRES_DOWNLOAD)
        old = post(PROVISIONING_PATH, {"record_type": "service_provisioning_request/v1", "operation": "rate",
                                       "identity": "skill.alpha", "expected_digest": alpha_digest, "value": "useful"})
        check("over_http_the_first_request_version_predates_feedback_and_is_refused",
              old.status_code == 400 and old.json()["error"]["code"] == "unsupported_version")
        asked = post(PROVISIONING_PATH, {"record_type": REQUEST_VERSION, "operation": "request_material",
                                         "request_id": "http-req-1", "description": "A rules file for Terraform reviews."})
        check("over_http_a_request_for_material_is_recorded",
              asked.status_code == 200 and asked.json()["result"]["record_type"] == "material_request_result/v1"
              and asked.json()["result"]["state"] == "open")
        too_long = post(PROVISIONING_PATH, {"record_type": REQUEST_VERSION, "operation": "request_material",
                                            "request_id": "http-req-2", "description": "x" * (DESCRIPTION_LIMIT + 1)})
        check("over_http_a_request_over_the_bound_answers_400",
              too_long.status_code == 400 and too_long.json()["error"]["code"] == DESCRIPTION_INVALID)
        listing = post(PROVISIONING_PATH, {"record_type": REQUEST_VERSION, "operation": "list"})
        check("the_provisioning_operations_still_answer_beside_the_feedback_operations",
              listing.status_code == 200 and listing.json()["result"]["record_type"] == "provisioning_list/v3")
        found = post(RETRIEVAL_PATH, {"record_type": "service_retrieval_request/v2", "query": "alpha reference"})
        # Lexical mode, because the hybrid mode's character similarity always finds something close.
        missed = post(RETRIEVAL_PATH, {"record_type": "service_retrieval_request/v2", "query": QUERY, "mode": "lexical",
                                       "library_tiers": ["verified"]})
        gaps = rows_of(fixture.runtime, GAP_KIND)
        check("a_search_that_finds_nothing_says_in_one_line_that_the_customer_can_ask_for_material",
              missed.status_code == 200 and missed.json()["result"]["hits"] == []
              and missed.json()["result"]["ask_for_material"] == ASK_FOR_MATERIAL_LINE
              and found.status_code == 200 and found.json()["result"]["hits"]
              and "ask_for_material" not in found.json()["result"])
        check("the_search_that_found_nothing_is_counted_without_its_text_or_its_account",
              len(gaps) == 1 and QUERY not in canonical(gaps[0]) and gaps[0]["payload"]["mode"] == "lexical"
              and gaps[0]["payload"]["library_tiers"] == ["verified"] and gaps[0]["attributes"]["tenant_id"] == "")
        staff = httpx.get(base + ADMIN_FEEDBACK_PATH, headers=fixture.headers("operator"), trust_env=False)
        customer = httpx.get(base + ADMIN_FEEDBACK_PATH, headers=fixture.headers("alpha"), trust_env=False)
        check("over_http_the_operator_reads_the_feedback_view_and_a_customer_is_refused",
              staff.status_code == 200 and staff.json()["result"]["record_type"] == STAFF_VIEW_VERSION
              and staff.json()["result"]["ratings"]["useful"] == 1
              and staff.json()["result"]["material_requests"][0]["description"] == "A rules file for Terraform reviews."
              and customer.status_code == 403 and customer.json()["error"]["code"] == "account_administration_forbidden")
        queried = httpx.get(base + ADMIN_FEEDBACK_PATH + "?all=1", headers=fixture.headers("operator"), trust_env=False)
        check("the_feedback_view_takes_no_query_parameters", queried.status_code == 400)


def run_all_checks(root):
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "real SQLite records and a real loopback transport; no external provider"})
    for name, function in (("domain", run_checks), ("HTTP", http_checks)):
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        function(check, directory)
    return {"tests": tests, "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}


if __name__ == "__main__":
    import sys
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix="service-feedback-") as directory:
        report = run_all_checks(Path(directory))
    print(json.dumps(report, indent=1))
    sys.exit(0 if report["all_passed"] else 1)
