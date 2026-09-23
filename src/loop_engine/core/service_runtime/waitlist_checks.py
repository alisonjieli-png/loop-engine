"""Waiting list checks over real SQLite records and a real loopback transport.

Every refusal has a check, and every refusal also has a known-wrong case: the
same situation with that one guard removed, which shows the guard is what
refuses. No identity provider, payment provider or mail provider is contacted.
The served page is read from the packaged file, not from a deployment.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
from unittest.mock import patch

from .http import ServiceHttpApplication, ServiceHttpConfiguration
from .http_test_fixtures import HttpDomainFixture, running_http
from .records import ACCESS_MANAGE_SCOPE, ServiceRuntimeError, TenantKeyIssue, TenantRegistration, digest
from .request_limits import UNKNOWN_PEER_KEY, FailedAttemptLimiter, ServiceRequestLimits
from .storage import ServiceCatalogBinding
from .waitlist import (
    ADDRESS_HAS_ACCOUNT, ADDRESS_INVALID, ADDRESS_LISTED, DECISION_VERSION, ENTRY, ERASED_BY_FORGET, FORGET,
    INVITE, INVITED, JOINED, OPERATIONS, RECORD_DELIVERY, RECORD_JOIN, REMOVED, REQUEST_VERSION, SOURCE,
    SOURCE_FLOODED, SOURCE_SECRET_UNAVAILABLE, UNCOUNTED_SOURCE, WAITING,
    ServiceWaitlist, WaitlistAccountDirectory, WaitlistDecision, WaitlistPolicy, WaitlistRequest,
    keyed_source_digest,
)
from .web_pages import WEB_ASSETS, read_packaged_asset

WAITLIST_PATH = "/api/v1/waitlist"
ADMIN_WAITLIST_PATH = "/api/v1/admin/waitlist"
WAITLIST_PAGE = "/waitlist"
DISCOUNT_CODE = "BALTOR-FOUNDING-40"
# The header a host behind its own trusted proxy names as the client address.
PROXY_ADDRESS_HEADER = "Fly-Client-IP"
# Words the public waiting list must not use. The first two name a release
# stage the owner does not want in public words. The rest would promise a date
# to someone whose request has not been read yet.
FORBIDDEN_PAGE_WORDS = ("beta", "pilot", "soon", "shortly", "within", "next week", "next month",
                        "days", "weeks", "guarantee", "immediately", "instantly")
#: The reference a fixture host names for the secret that keys its source
#: digest. The value behind it is made for each run, so this file holds none.
FIXTURE_SECRET_REFERENCE = "env:WAITLIST_FIXTURE_SOURCE_SECRET"


def refused(function, *codes):
    try:
        function()
    except ServiceRuntimeError as error:
        return not codes or error.code in codes
    return False


def answering(secret):
    """A secret resolver that answers the fixture reference alone, the way the host's resolver answers env:NAME."""
    def resolve(reference):
        if reference != FIXTURE_SECRET_REFERENCE:
            raise ServiceRuntimeError("configured_secret_unavailable")
        if isinstance(secret, Exception):
            raise secret
        return secret
    return resolve


def prepared(root, *, directory=None, keyed=True, secret=None, **policy):
    """A waiting list over real records. A keyed fixture names a source secret, as a host that counts must."""
    root.mkdir(parents=True, exist_ok=True)
    fixture = HttpDomainFixture(root)
    fixture.runtime.register_tenant(TenantRegistration("operator", "operator:private", (ACCESS_MANAGE_SCOPE,)))
    fixture.operator_key = fixture.runtime.issue_key(TenantKeyIssue("operator", "local waiting list operator"))
    fixture.source_secret = (secret if secret is not None else secrets.token_hex(32)) if keyed else None
    named = {"source_secret_ref": FIXTURE_SECRET_REFERENCE} if keyed else {}
    fixture.waitlist = ServiceWaitlist(fixture.runtime, WaitlistPolicy(writes_authorized=True, **named, **policy),
                                       account_directory=directory,
                                       secret_resolver=answering(fixture.source_secret) if keyed else None)
    return fixture


def source_rows(runtime):
    """Every stored source record of one service, as the store holds it."""
    catalog = runtime._catalog
    with catalog.store() as store:
        return catalog.rows_all(store, SOURCE)


def source_record_findings(row, address, catalog):
    """Name each way one stored source record gives away the network address it counts.

    The address may not appear anywhere in the record. The record may not be
    named by the address, or by an unkeyed digest of it, and it may not hold
    such a digest. An unkeyed digest of a network address protects nothing:
    every IPv4 address can be hashed in minutes, so a guess confirms itself.
    Only a digest keyed with a secret the store does not hold is allowed.
    """
    text = json.dumps(row, sort_keys=True)
    unkeyed = {"the address itself": address, "the unkeyed record digest": digest([address]),
               "an unkeyed SHA-256 digest": hashlib.sha256(address.encode("utf-8")).hexdigest()}
    return ([name + " in a stored field" for name, value in unkeyed.items() if value in text]
            + ["an identity named by " + name for name, value in unkeyed.items()
               if row.get("record_id") == catalog.identity(SOURCE, value)])


def request(address, note="", source="203.0.113.7"):
    return WaitlistRequest(address, note, source)


def run_checks(check, root):
    fixture = prepared(root)
    waitlist, runtime = fixture.waitlist, fixture.runtime
    operator = runtime.authenticate_key(fixture.operator_key.key)
    customer = runtime.authenticate_key(fixture.keys["alpha"].key)

    accepted = waitlist.join(request("Ada.Lovelace+work@Example.com", "  I want to try it with my own harness  "))
    check("an_address_and_a_note_are_recorded_in_the_waiting_state",
          accepted["state"] == WAITING and accepted["committed"] is True
          and accepted["entry_ref"].startswith("service:"))
    listing = waitlist.inspect(operator)
    entry = listing["entries"][0]
    check("the_operator_sees_the_normalized_address_and_the_trimmed_note",
          listing["matched"] == 1 and entry["email"] == "ada.lovelace+work@example.com"
          and entry["note"] == "I want to try it with my own harness"
          and listing["counts"] == {WAITING: 1, INVITED: 0, JOINED: 0, "declined": 0, REMOVED: 0})
    check("an_ordinary_customer_cannot_read_the_waiting_list",
          refused(lambda: waitlist.inspect(customer), "waitlist_administration_forbidden"))

    # Refusal one: a malformed address.
    for value in ("", "   ", "ada", "ada@", "@example.com", "ada@example", "ada lovelace@example.com",
                  "ada@exa mple.com", "ada@@example.com", "a" * 65 + "@example.com", "ada\n@example.com",
                  "ada@example.com,eve@example.com", "x" * 250 + "@example.com"):
        # An empty value and a value of spaces both strip to nothing, so each
        # keeps a name of its own and a failure names the value that caused it.
        check("malformed_address_refused_" + (value.strip()[:24].replace("\n", " ")
                                              or ("empty" if value == "" else "only_spaces")),
              refused(lambda value=value: waitlist.join(request(value)), ADDRESS_INVALID))
    check("space_around_an_address_is_trimmed_rather_than_refused",
          waitlist.join(request("  Bea@Example.com \n"))["state"] == WAITING
          and waitlist.inspect(operator, states=(WAITING,))["entries"][-1]["email"] == "bea@example.com")
    with patch("loop_engine.core.service_runtime.waitlist._ADDRESS", _AlwaysMatches()):
        check("KNOWN_WRONG_without_the_address_rule_a_malformed_address_is_accepted",
              waitlist.join(request("not an address at all"))["state"] == WAITING)

    # Refusal two: the same address twice.
    check("the_same_address_cannot_be_listed_twice",
          refused(lambda: waitlist.join(request("ADA.lovelace+work@example.com")), ADDRESS_LISTED))
    # Known-wrong case: with the lookup removed the address is still not
    # listed twice, because the write says the record must not exist yet. The
    # request loses its own answer and gets the general one, so the check
    # above fails and the person is told to retry something that cannot work.
    with patch.object(ServiceCatalogBinding, "read", _blind_to(ENTRY)):
        check("KNOWN_WRONG_without_the_existing_entry_lookup_a_duplicate_loses_its_own_answer",
              refused(lambda: waitlist.join(request("ada.lovelace+work@example.com")), "concurrent_update"))

    # Refusal three: an address that already has an account.
    held = prepared(root / "accounts", directory=WaitlistAccountDirectory(
        lambda address: address == "grace@example.com"))
    check("an_address_that_already_has_an_account_is_refused",
          refused(lambda: held.waitlist.join(request("grace@example.com")), ADDRESS_HAS_ACCOUNT))
    check("an_unusable_directory_answer_refuses_instead_of_admitting_the_address",
          refused(lambda: prepared(root / "broken", directory=WaitlistAccountDirectory(
              lambda address: "yes")).waitlist.join(request("grace@example.com")),
              "waitlist_account_directory_unavailable")
          and refused(lambda: prepared(root / "raising", directory=WaitlistAccountDirectory(
              lambda address: (_ for _ in ()).throw(RuntimeError("provider down")))).waitlist.join(
                  request("grace@example.com")), "waitlist_account_directory_unavailable"))
    check("KNOWN_WRONG_without_the_account_directory_that_address_joins_the_list",
          prepared(root / "unheld").waitlist.join(request("grace@example.com"))["state"] == WAITING)
    joined = prepared(root / "joined")
    reference = joined.waitlist.join(request("carol@example.com"))["entry_ref"]
    joined_operator = joined.runtime.authenticate_key(joined.operator_key.key)
    joined.waitlist.decide(joined_operator, WaitlistDecision(INVITE, reference, "invite-1", DISCOUNT_CODE))
    joined.waitlist.decide(joined_operator, WaitlistDecision(RECORD_JOIN, reference, "join-1"))
    check("an_address_whose_own_entry_joined_is_refused_without_any_directory",
          refused(lambda: joined.waitlist.join(request("carol@example.com")), ADDRESS_HAS_ACCOUNT))

    # Refusal four: an obvious flood from one source.
    flood = prepared(root / "flood", accepted_for_each_source=3)
    for index in range(3):
        flood.waitlist.join(request(f"person{index}@example.com", source="198.51.100.4"))
    check("one_source_cannot_send_more_than_its_share_inside_the_window",
          refused(lambda: flood.waitlist.join(request("person3@example.com", source="198.51.100.4")), SOURCE_FLOODED))
    check("another_source_is_not_refused_by_the_first_ones_count",
          flood.waitlist.join(request("person4@example.com", source="198.51.100.9"))["state"] == WAITING)
    check("an_address_without_a_declared_source_records_that_no_count_was_taken",
          flood.waitlist.join(request("person5@example.com", source=""))["source_counted"] == "no_declared_source")
    with patch.object(ServiceWaitlist, "_source_guard", lambda self, store, catalog, req, now: (None, None, "counted")):
        check("KNOWN_WRONG_without_the_source_count_the_flood_is_accepted",
              flood.waitlist.join(request("person6@example.com", source="198.51.100.4"))["state"] == WAITING)
    old = prepared(root / "window", accepted_for_each_source=2, source_window_seconds=60)
    with patch.object(old.runtime, "_clock", lambda: 1000.0):
        old.waitlist.join(request("early0@example.com", source="198.51.100.5"))
        old.waitlist.join(request("early1@example.com", source="198.51.100.5"))
        check("the_window_is_what_refuses_inside_it",
              refused(lambda: old.waitlist.join(request("early2@example.com", source="198.51.100.5")), SOURCE_FLOODED))
    with patch.object(old.runtime, "_clock", lambda: 1000.0 + 61):
        check("a_source_may_send_again_after_its_window_has_passed",
              old.waitlist.join(request("early3@example.com", source="198.51.100.5"))["state"] == WAITING)


def decision_checks(check, root):
    fixture = prepared(root)
    waitlist, runtime = fixture.waitlist, fixture.runtime
    operator = runtime.authenticate_key(fixture.operator_key.key)
    customer = runtime.authenticate_key(fixture.keys["alpha"].key)
    reference = waitlist.join(request("dorothy@example.com"))["entry_ref"]
    version = waitlist.inspect(operator)["entries"][0]["entry_version"]

    check("an_invitation_must_carry_a_discount_code",
          refused(lambda: WaitlistDecision(INVITE, reference, "invite-1"), "waitlist_invitation_discount_required")
          and refused(lambda: WaitlistDecision(INVITE, reference, "invite-1", "no"),
                      "waitlist_invitation_discount_required"))
    check("only_an_invitation_carries_a_discount_code",
          refused(lambda: WaitlistDecision("decline", reference, "decline-1", DISCOUNT_CODE),
                  "invalid_waitlist_decision"))
    check("an_ordinary_customer_cannot_invite_anyone",
          refused(lambda: waitlist.decide(customer, WaitlistDecision(INVITE, reference, "invite-1", DISCOUNT_CODE)),
                  "waitlist_administration_forbidden"))
    check("a_decision_about_an_unknown_entry_is_refused",
          refused(lambda: waitlist.decide(operator, WaitlistDecision(
              INVITE, "service:" + "0" * 64, "invite-2", DISCOUNT_CODE)), "waitlist_entry_not_found"))
    check("a_decision_against_an_older_version_of_the_entry_is_refused",
          refused(lambda: waitlist.decide(operator, WaitlistDecision(
              INVITE, reference, "invite-3", DISCOUNT_CODE, expected_version="0" * 32)), "concurrent_update"))

    invited = waitlist.decide(operator, WaitlistDecision(INVITE, reference, "invite-4", DISCOUNT_CODE,
                                                         expected_version=version))
    check("an_invitation_records_the_state_and_the_discount_the_person_receives",
          invited["state"] == INVITED and invited["replayed"] is False
          and invited["entry"]["discount_code"] == DISCOUNT_CODE
          and invited["entry"]["delivery"] == "not_attempted")
    replay = waitlist.decide(operator, WaitlistDecision(INVITE, reference, "invite-4", DISCOUNT_CODE))
    check("the_same_invitation_identity_never_writes_twice",
          replay["replayed"] is True and replay["state"] == INVITED
          and replay["entry"]["entry_version"] == invited["entry"]["entry_version"])
    check("the_same_identity_with_different_content_is_refused_instead_of_replayed",
          refused(lambda: waitlist.decide(operator, WaitlistDecision(INVITE, reference, "invite-4", "OTHER-CODE")),
                  "waitlist_decision_identity_conflict"))
    check("a_second_invitation_does_not_follow_from_an_invited_entry",
          refused(lambda: waitlist.decide(operator, WaitlistDecision(INVITE, reference, "invite-5", DISCOUNT_CODE)),
                  "waitlist_transition_refused"))
    delivered = waitlist.decide(operator, WaitlistDecision(RECORD_DELIVERY, reference, "delivery-1",
                                                           invitation_ref="message-digest", delivery="sent"))
    check("a_delivered_invitation_is_recorded_without_changing_the_state",
          delivered["state"] == INVITED and delivered["entry"]["delivery"] == "sent"
          and delivered["entry"]["invitation_ref"] == "message-digest")
    joined = waitlist.decide(operator, WaitlistDecision(RECORD_JOIN, reference, "join-1"))
    check("an_invited_person_who_joined_reaches_the_joined_state", joined["state"] == JOINED)
    check("no_decision_follows_from_the_joined_state",
          refused(lambda: waitlist.decide(operator, WaitlistDecision("decline", reference, "decline-2")),
                  "waitlist_transition_refused")
          and refused(lambda: waitlist.decide(operator, WaitlistDecision(RECORD_JOIN, reference, "join-2")),
                      "waitlist_transition_refused"))

    second = waitlist.join(request("elsie@example.com"))["entry_ref"]
    declined = waitlist.decide(operator, WaitlistDecision("decline", second, "decline-3"))
    check("a_waiting_entry_can_be_declined_and_then_nothing_follows",
          declined["state"] == "declined"
          and refused(lambda: waitlist.decide(operator, WaitlistDecision(INVITE, second, "invite-6", DISCOUNT_CODE)),
                      "waitlist_transition_refused"))
    check("the_listing_can_be_read_by_state",
          waitlist.inspect(operator, states=(JOINED,))["matched"] == 1
          and waitlist.inspect(operator, states=("declined",))["entries"][0]["email"] == "elsie@example.com"
          and refused(lambda: waitlist.inspect(operator, states=("unknown",)), "unsupported_waitlist_state"))
    check("a_list_without_write_authority_still_refuses_a_decision",
          refused(lambda: ServiceWaitlist(runtime, WaitlistPolicy()).decide(
              operator, WaitlistDecision("decline", second, "decline-4")), "waitlist_writes_not_authorized")
          and refused(lambda: ServiceWaitlist(runtime, WaitlistPolicy()).join(request("frank@example.com")),
                      "waitlist_writes_not_authorized"))


def _stored_row(fixture, address):
    """The record as the store holds it, not the view an operator reads."""
    catalog = fixture.runtime._catalog
    with catalog.store() as store:
        return catalog.read(store, ENTRY, address)


def removal_checks(check, root):
    """Removal is a real operation, so the page may say the list can erase an address."""
    import json
    fixture = prepared(root)
    waitlist, runtime = fixture.waitlist, fixture.runtime
    operator = runtime.authenticate_key(fixture.operator_key.key)
    customer = runtime.authenticate_key(fixture.keys["alpha"].key)
    address, note = "hedy@example.com", "Please take my address off the list"
    reference = waitlist.join(request(address, note))["entry_ref"]
    check("an_ordinary_customer_cannot_remove_an_entry",
          refused(lambda: waitlist.decide(customer, WaitlistDecision(FORGET, reference, "forget-0")),
                  "waitlist_administration_forbidden")
          and _stored_row(fixture, address)["payload"]["email"] == address)
    removed = waitlist.decide(operator, WaitlistDecision(FORGET, reference, "forget-1"))
    stored = json.dumps(_stored_row(fixture, address), sort_keys=True)
    check("removing_an_entry_erases_the_address_and_the_note_from_the_stored_record",
          removed["state"] == REMOVED and removed["entry"]["email"] == "" and removed["entry"]["note"] == ""
          and address not in stored and note not in stored and "hedy" not in stored
          and _stored_row(fixture, address)["payload"]["address_digest"])
    # Known-wrong case: the same decision with nothing named as erased leaves
    # the address and the note in the record that the state calls removed.
    kept = prepared(root / "kept")
    kept_reference = kept.waitlist.join(request(address, note))["entry_ref"]
    kept_operator = kept.runtime.authenticate_key(kept.operator_key.key)
    with patch("loop_engine.core.service_runtime.waitlist.ERASED_BY_FORGET", ()):
        kept.waitlist.decide(kept_operator, WaitlistDecision(FORGET, kept_reference, "forget-2"))
    check("KNOWN_WRONG_without_the_named_erased_fields_the_removed_record_still_holds_the_address",
          address in json.dumps(_stored_row(kept, address), sort_keys=True))
    check("nothing_follows_a_removal_and_the_listing_counts_it",
          refused(lambda: waitlist.decide(operator, WaitlistDecision(INVITE, reference, "forget-3", DISCOUNT_CODE)),
                  "waitlist_transition_refused")
          and refused(lambda: waitlist.decide(operator, WaitlistDecision(FORGET, reference, "forget-4")),
                      "waitlist_transition_refused")
          and waitlist.inspect(operator, states=(REMOVED,))["matched"] == 1)
    again = waitlist.join(request(address, "I would like to try again"))
    check("a_removed_address_may_ask_again_and_starts_a_new_entry",
          again["state"] == WAITING
          and _stored_row(fixture, address)["payload"]["note"] == "I would like to try again"
          and waitlist.inspect(operator, states=(REMOVED,))["matched"] == 0)

    held = prepared(root / "joined")
    joined_reference = held.waitlist.join(request("ida@example.com"))["entry_ref"]
    joined_operator = held.runtime.authenticate_key(held.operator_key.key)
    held.waitlist.decide(joined_operator, WaitlistDecision(INVITE, joined_reference, "invite-1", DISCOUNT_CODE))
    held.waitlist.decide(joined_operator, WaitlistDecision(RECORD_JOIN, joined_reference, "join-1"))
    check("an_address_that_reached_an_account_is_not_removed_through_the_waiting_list",
          refused(lambda: held.waitlist.decide(joined_operator, WaitlistDecision(FORGET, joined_reference, "forget-5")),
                  "waitlist_transition_refused")
          and _stored_row(held, "ida@example.com")["payload"]["email"] == "ida@example.com")
    declined = prepared(root / "declined")
    declined_reference = declined.waitlist.join(request("jean@example.com"))["entry_ref"]
    declined_operator = declined.runtime.authenticate_key(declined.operator_key.key)
    declined.waitlist.decide(declined_operator, WaitlistDecision("decline", declined_reference, "decline-1"))
    check("a_declined_entry_can_still_be_removed_on_request",
          declined.waitlist.decide(declined_operator, WaitlistDecision(
              FORGET, declined_reference, "forget-6"))["state"] == REMOVED
          and "jean" not in json.dumps(_stored_row(declined, "jean@example.com"), sort_keys=True))


def http_checks(check, root):
    import httpx
    fixture = prepared(root, accepted_for_each_source=3)
    limits = ServiceRequestLimits(client_address_source="socket_peer", failures_allowed=30)
    with running_http(fixture, application_factory=lambda configuration: ServiceHttpApplication(
            fixture.runtime, fixture.provisioning, configuration, waitlist=fixture.waitlist),
            request_limits=limits) as (base, service):
        def join(address, note=""):
            return httpx.post(base + WAITLIST_PATH, trust_env=False, timeout=5,
                              json={"record_type": REQUEST_VERSION, "email": address, "note": note})
        operator = {"Authorization": "Bearer " + fixture.operator_key.key}
        first = join("anne@example.com", "One note")
        check("anyone_can_leave_an_address_without_signing_in",
              first.status_code == 200 and first.json()["result"]["state"] == WAITING
              and first.json()["result"]["source_counted"] == "counted")
        check("the_public_answer_never_repeats_the_address_back",
              "anne@example.com" not in first.text)
        malformed = join("anne at example.com")
        duplicate = join("anne@example.com")
        check("a_malformed_address_and_a_repeated_address_have_their_own_answers",
              malformed.status_code == 400 and malformed.json()["error"]["code"] == ADDRESS_INVALID
              and duplicate.status_code == 409 and duplicate.json()["error"]["code"] == ADDRESS_LISTED)
        flooding = [join(f"flood{index}@example.com").status_code for index in range(4)]
        check("an_obvious_flood_from_one_source_is_refused_with_its_own_answer",
              flooding == [200, 200, 429, 429]
              and join("flood9@example.com").json()["error"]["code"] == SOURCE_FLOODED)
        # The transport counted the loopback peer. The record it left behind
        # is named by the keyed digest of that address and holds nothing else
        # about it.
        counted = source_rows(fixture.runtime)
        check("the_address_the_transport_counted_is_stored_only_as_a_keyed_digest",
              len(counted) == 1 and not source_record_findings(counted[0], "127.0.0.1", fixture.runtime._catalog)
              and counted[0]["record_id"] == fixture.runtime._catalog.identity(
                  SOURCE, keyed_source_digest(fixture.source_secret, "127.0.0.1")))
        unsupported = httpx.post(base + WAITLIST_PATH, trust_env=False, timeout=5,
                                 json={"record_type": "service_waitlist_request/v99", "email": "x@example.com"})
        extra = httpx.post(base + WAITLIST_PATH, trust_env=False, timeout=5,
                           json={"record_type": REQUEST_VERSION, "email": "x@example.com", "tenant_id": "alpha"})
        check("an_unsupported_version_or_an_extra_field_is_refused_before_any_write",
              unsupported.status_code == extra.status_code == 400
              and unsupported.json()["error"]["code"] == "unsupported_waitlist_request"
              and extra.json()["error"]["code"] == "unsupported_waitlist_request")

        anonymous = httpx.get(base + ADMIN_WAITLIST_PATH, trust_env=False, timeout=5)
        customer = httpx.get(base + ADMIN_WAITLIST_PATH, trust_env=False, timeout=5, headers=fixture.headers())
        listed = httpx.get(base + ADMIN_WAITLIST_PATH, trust_env=False, timeout=5, headers=operator)
        check("only_an_operator_can_read_the_addresses_people_left",
              anonymous.status_code == 401 and customer.status_code == 403
              and listed.status_code == 200 and listed.json()["result"]["matched"] == 3
              and "anne@example.com" not in customer.text)
        reference = listed.json()["result"]["entries"][0]["entry_ref"]
        invited = httpx.post(base + ADMIN_WAITLIST_PATH, trust_env=False, timeout=5, headers=operator,
            json={"record_type": DECISION_VERSION, "operation": INVITE, "entry_ref": reference,
                  "request_id": "http-invite-1", "discount_code": DISCOUNT_CODE})
        check("an_operator_invites_one_entry_and_the_discount_travels_with_it",
              invited.status_code == 200 and invited.json()["result"]["state"] == INVITED
              and invited.json()["result"]["entry"]["discount_code"] == DISCOUNT_CODE)
        repeated = httpx.post(base + ADMIN_WAITLIST_PATH, trust_env=False, timeout=5, headers=operator,
            json={"record_type": DECISION_VERSION, "operation": INVITE, "entry_ref": reference,
                  "request_id": "http-invite-1", "discount_code": DISCOUNT_CODE})
        check("repeating_the_same_invitation_request_writes_nothing_new",
              repeated.status_code == 200 and repeated.json()["result"]["replayed"] is True)
        check("the_installed_waiting_list_is_visible_in_the_service_profile",
              httpx.get(base + "/api/v1/capabilities", trust_env=False, timeout=5)
              .json()["result"]["website"]["waitlist_available"] is True)
        page = httpx.get(base + WAITLIST_PAGE, trust_env=False, timeout=5)
        check("the_form_is_served_at_its_own_address",
              page.status_code == 200 and 'id="waitlist-form"' in page.text
              and "frame-ancestors 'none'" in page.headers["content-security-policy"])

    absent = prepared(root / "absent")
    with running_http(absent, application_factory=lambda configuration: ServiceHttpApplication(
            absent.runtime, absent.provisioning, configuration)) as (base, _service):
        answer = httpx.post(base + WAITLIST_PATH, trust_env=False, timeout=5,
                            json={"record_type": REQUEST_VERSION, "email": "anne@example.com"})
        check("a_service_without_a_waiting_list_says_so_instead_of_accepting_an_address",
              answer.status_code == 503 and answer.json()["error"]["code"] == "waitlist_unavailable"
              and httpx.get(base + "/api/v1/capabilities", trust_env=False, timeout=5)
              .json()["result"]["website"]["waitlist_available"] is False)
    # A secret the host names and the service cannot read is a state of the
    # service, not a bad request, so the caller is told to try again later.
    unreadable = prepared(root / "unreadable", secret=ServiceRuntimeError("configured_secret_unavailable"))
    with running_http(unreadable, application_factory=lambda configuration: ServiceHttpApplication(
            unreadable.runtime, unreadable.provisioning, configuration, waitlist=unreadable.waitlist),
            request_limits=ServiceRequestLimits(client_address_source="socket_peer")) as (base, _service):
        answer = httpx.post(base + WAITLIST_PATH, trust_env=False, timeout=5,
                            json={"record_type": REQUEST_VERSION, "email": "rose@example.com"})
        check("an_unreadable_source_secret_answers_as_a_service_state_and_records_nothing",
              answer.status_code == 503 and answer.json()["error"]["code"] == SOURCE_SECRET_UNAVAILABLE
              and _stored_row(unreadable, "rose@example.com") is None)
    undeclared_source_checks(check, root / "undeclared")


def undeclared_source_checks(check, root):
    """A host that declared no client address source counts nobody, and says so.

    The settings that decide this are the host's own request limits. Their
    default states no source, which is the shape the deployed pilot has, so
    this is the case the public endpoint meets first.
    """
    import httpx
    fixture = prepared(root, accepted_for_each_source=5)
    def join(base, index):
        return httpx.post(base + WAITLIST_PATH, trust_env=False, timeout=5,
                          json={"record_type": REQUEST_VERSION, "email": f"open{index}@example.com"})
    with running_http(fixture, application_factory=lambda configuration: ServiceHttpApplication(
            fixture.runtime, fixture.provisioning, configuration, waitlist=fixture.waitlist),
            request_limits=ServiceRequestLimits()) as (base, service):
        answers = [join(base, index) for index in range(7)]
        counted = {answer.json().get("result", {}).get("source_counted") for answer in answers}
        check("with_no_declared_address_source_every_request_records_that_no_count_was_taken",
              service.configuration.request_limits.active is False
              and [answer.status_code for answer in answers] == [200] * 7
              and counted == {UNCOUNTED_SOURCE} and service._address_key(_OnePeer()) == "")
    # Known-wrong case: name the socket peer although the host declared no
    # source. Every public caller then shares one key and the sixth request is
    # refused, which is the collapse the declared-source rule exists to prevent.
    naming = prepared(root / "naming", accepted_for_each_source=5)
    with patch.object(FailedAttemptLimiter, "address_key", _names_the_peer_anyway):
        with running_http(naming, application_factory=lambda configuration: ServiceHttpApplication(
                naming.runtime, naming.provisioning, configuration, waitlist=naming.waitlist),
                request_limits=ServiceRequestLimits()) as (base, _service):
            answers = [join(base, index) for index in range(7)]
            check("KNOWN_WRONG_naming_the_peer_without_a_declared_source_closes_the_form_after_five",
                  [answer.status_code for answer in answers] == [200] * 5 + [429, 429]
                  and answers[5].json()["error"]["code"] == SOURCE_FLOODED)
    # The host that wants the count declares where the address comes from.
    behind = prepared(root / "behind", accepted_for_each_source=2)
    limits = ServiceRequestLimits(client_address_source="header", client_address_header=PROXY_ADDRESS_HEADER)
    with running_http(behind, application_factory=lambda configuration: ServiceHttpApplication(
            behind.runtime, behind.provisioning, configuration, waitlist=behind.waitlist),
            request_limits=limits) as (base, _service):
        def from_proxy(index, address):
            return httpx.post(base + WAITLIST_PATH, trust_env=False, timeout=5,
                              headers={PROXY_ADDRESS_HEADER: address},
                              json={"record_type": REQUEST_VERSION, "email": f"proxied{index}@example.com"})
        first = [from_proxy(index, "198.51.100.30") for index in range(3)]
        other = from_proxy(9, "198.51.100.31")
        check("a_host_that_declares_the_forwarded_address_counts_each_caller_on_its_own",
              [answer.status_code for answer in first] == [200, 200, 429]
              and first[2].json()["error"]["code"] == SOURCE_FLOODED
              and other.status_code == 200 and other.json()["result"]["source_counted"] == "counted")


def host_checks(check, root):
    """A host installs the waiting list from its own configuration, or does not have one."""
    from .http_entrypoint import load_host_application
    from ..harness_intelligence import HarnessIntelligenceDraft, item_from_body
    import json
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    body = "Pinned host-reviewed instruction body"
    (artifacts / "instruction.txt").write_text(body)
    # A host serves only the harness family unless it declares another, so the
    # fixture item is harness material, as in the other host fixtures.
    item = item_from_body(HarnessIntelligenceDraft("skill.host", "skill", "Host-reviewed source",
        "harness_local", "harness:host/v1", "MIT"), body)
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps({"record_type": "host_attested_intelligence_manifest/v1",
        "artifact_root": str(artifacts), "items": [{"reference": item.reference(), "body_path": "instruction.txt",
            "approval_ref": "host-review:fixture",
            "grants": [{"tenant_id": "host", "body_allowed": True, "metering": "required"}]}]}))
    def application(**blocks):
        path = root / ("service-" + str(len(blocks)) + ".json")
        path.write_text(json.dumps({"record_type": "service_http_host_configuration/v1",
            "runtime": {"database_path": str(root / "state.db"), "writes_authorized": True},
            "http": {"public_base_url": "https://app.example", "allowed_hosts": ["app.example"]},
            "authentication": {"modes": ["host_key"]}, "manifest_path": str(manifest_path), **blocks}))
        return load_host_application(str(path))[0]
    check("a_host_without_a_waiting_list_block_installs_no_waiting_list",
          application().waitlist is None)
    installed = application(waitlist={"writes_authorized": True, "accepted_for_each_source": 2})
    check("a_host_that_declares_a_waiting_list_gets_the_list_its_settings_describe",
          isinstance(installed.waitlist, ServiceWaitlist) and installed.waitlist.runtime is installed.runtime
          and installed.waitlist.policy.accepted_for_each_source == 2
          and installed.capabilities()["website"]["waitlist_available"] is True)
    def stops(settings):
        """Any refusal stops the host. An unknown setting is a TypeError, as in every other block."""
        try:
            application(waitlist=settings)
        except Exception:
            return True
        return False
    check("a_waiting_list_block_the_policy_does_not_support_refuses_the_whole_host",
          refused(lambda: application(waitlist={"accepted_for_each_source": 0}), "invalid_waitlist_policy")
          and stops({"source_window_seconds": 1}) and stops({"unknown_setting": True}))
    # The host names the secret that keys the source digest the way it names
    # every other secret: an environment reference that the host's own
    # resolver reads at use. The value never appears in the host file.
    variable, unset = "WAITLIST_HOST_CHECK_SOURCE_SECRET", "WAITLIST_HOST_CHECK_UNSET_SECRET"
    with patch.dict(os.environ, {variable: secrets.token_hex(32)}):
        os.environ.pop(unset, None)
        named, _problem = _attempt(lambda: application(waitlist={
            "writes_authorized": True, "source_secret_ref": "env:" + variable}))
        answer, _problem = _attempt(lambda: named.waitlist.join(WaitlistRequest("host@example.com", "", "198.51.100.70")))
        stored = source_rows(named.runtime) if named is not None else []
        check("a_host_names_its_source_secret_by_an_environment_reference_and_counts_under_it",
              answer is not None and answer["source_counted"] == "counted" and len(stored) == 1
              and stored[0]["record_id"] == named.runtime._catalog.identity(
                  SOURCE, keyed_source_digest(os.environ[variable], "198.51.100.70")))
        missing, _problem = _attempt(lambda: application(waitlist={
            "writes_authorized": True, "source_secret_ref": "env:" + unset}))
        check("a_host_whose_named_secret_is_not_set_refuses_requests_instead_of_counting_without_it",
              missing is not None and refused(lambda: missing.waitlist.join(
                  WaitlistRequest("unset@example.com", "", "198.51.100.71")), SOURCE_SECRET_UNAVAILABLE))
    check("a_source_secret_named_any_other_way_than_an_environment_reference_refuses_the_host",
          refused(lambda: application(waitlist={"source_secret_ref": variable}), "invalid_waitlist_policy")
          and refused(lambda: application(waitlist={"source_secret_ref": "secret:" + variable}),
                      "invalid_waitlist_policy"))


def _attempt(function):
    """Return `(value, None)`, or `(None, the refusal)` so that one check can report it by name."""
    try:
        return function(), None
    except Exception as error:
        return None, error


def _invitation_section(page):
    """The invitation card of the waiting list page, back as a page of its own on September 23, 2026; empty when there is none."""
    marker = '<section class="panel waitlist-card"'
    return page.split(marker, 1)[1].split("</section>", 1)[0].lower() if marker in page else ""


def page_checks(check, _root):
    """The public words: no release stage, and no promise of a date."""
    page = read_packaged_asset("index.html").decode("utf-8")
    section = _invitation_section(page)
    view = lambda name: page.split('<section data-view="' + name + '"', 1)[-1].split("<section data-view=", 1)[0] if '<section data-view="' + name + '"' in page else ""
    invite = view("setup").split('<section class="start-invite"', 1)[-1].split("</section>", 1)[0] if '<section class="start-invite"' in view("setup") else ""
    check("the_invitation_form_leads_the_waiting_list_page_and_get_started_links_to_it",
          bool(section) and '<section class="panel waitlist-card"' in view("waitlist") and 'id="waitlist-form"' in view("waitlist")
          and 'href="/waitlist"' in invite and 'data-start-access="operator"' in view("setup") and 'id="waitlist-form"' not in view("setup"))
    check("KNOWN_WRONG_the_invitation_card_reader_finds_nothing_on_a_page_without_the_card",
          _invitation_section(page.replace('<section class="panel waitlist-card"', '<section class="moved-away"')) == "")
    found = sorted(word for word in FORBIDDEN_PAGE_WORDS if word in section)
    check("the_waiting_list_words_name_no_release_stage_and_promise_no_date", not found)
    check("KNOWN_WRONG_the_word_guard_finds_a_promise_when_the_words_carry_one",
          sorted(word for word in FORBIDDEN_PAGE_WORDS
                 if word in "we will invite you within days of the beta starting") == ["beta", "days", "within"])
    check("the_form_asks_for_an_address_and_an_optional_note_and_says_a_person_decides",
          'id="waitlist-email"' in section and 'id="waitlist-note"' in section
          and "optional" in section and "a person" in section)
    check("the_served_page_and_the_address_table_agree",
          WAITLIST_PAGE in WEB_ASSETS and WEB_ASSETS[WAITLIST_PAGE][0] == "index.html"
          and '"' + WAITLIST_PAGE + '"' in read_packaged_asset("service.js").decode("utf-8"))
    # Every claim on this page has to be backed by something the service does.
    check("the_page_says_an_address_can_be_erased_only_because_an_operation_erases_it",
          "erase" in section and _erasure_claim_is_backed(section, OPERATIONS, ERASED_BY_FORGET))
    check("KNOWN_WRONG_the_erasure_guard_refuses_the_same_words_when_no_operation_erases",
          not _erasure_claim_is_backed(section, (INVITE, "decline"), ()))
    offers = _hidden_until_the_service_answers(page)
    check("no_offer_on_the_page_is_made_before_the_service_says_it_can_be_honoured",
          offers == {"start-invite": True, "start-register": True, "signup-waitlist-link": True,
                     "waitlist-form": True, "waitlist-discount": True})
    check("KNOWN_WRONG_the_hidden_offer_guard_finds_an_offer_that_is_shown_at_once",
          _hidden_until_the_service_answers(
              '<section class="start-invite" id="start-invite" data-start-state="invite">')["start-invite"] is False)
    script = read_packaged_asset("service.js").decode("utf-8")
    check("the_page_shows_each_offer_only_from_the_record_the_service_publishes",
          "waitlist_available" in script and "discount_code" in script and "registration_available" in script
          and all(name in script for name in ("signup-waitlist-link", "waitlist-form", "waitlist-closed",
                                              "waitlist-discount", "data-start-state")))


def _erasure_claim_is_backed(section, operations, erased):
    """The page may say an address can be erased only where an operation erases it."""
    return "erase" not in section or (FORGET in operations and erased == ("email", "note"))


def _hidden_until_the_service_answers(page):
    """For each offering element, whether the served page starts it hidden."""
    import re
    found = {}
    for name in ("start-invite", "start-register", "signup-waitlist-link", "waitlist-form", "waitlist-discount"):
        element = re.search(r"<[a-z]+ [^<>]*\bid=\"" + name + r"\"[^<>]*>", page)
        if element is not None:
            found[name] = re.search(r"\bhidden\b", element.group(0)) is not None
    return found


class _AlwaysMatches:
    """Stands in for the address rule to show what the rule is what refuses."""

    def fullmatch(self, value):
        return self


class _OnePeer:
    """The smallest stand-in for a request: one socket peer and no headers."""

    class _Client:
        host = "198.51.100.77"

    class _Headers:
        @staticmethod
        def getlist(_name):
            return []

    client, headers = _Client(), _Headers()


def _names_the_peer_anyway(self, peer_host, header_values=()):
    """The known-wrong rule: name the socket peer although no source was declared."""
    values = tuple(header_values) if self.settings.client_address_source == "header" else ()
    named = self._canonical(values[0]) if len(values) == 1 else ""
    return named or self._canonical(peer_host) or UNKNOWN_PEER_KEY


def _blind_to(kind):
    original = ServiceCatalogBinding.read

    def read(self, store, requested_kind, logical_identity):
        if requested_kind == kind:
            return None
        return original(self, store, requested_kind, logical_identity)
    return read


def run_all_checks(root):
    tests = []
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "real SQLite records and a real loopback transport; no external provider"})
    for name, function in (("domain", run_checks), ("decisions", decision_checks),
                           ("removal", removal_checks), ("page", page_checks), ("host", host_checks),
                           ("HTTP", http_checks)):
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        function(check, directory)
    # The source record checks live in their own module, which imports the
    # fixtures above, so it is imported here rather than at the top.
    from .waitlist_source_checks import run_source_checks
    (root / "sources").mkdir(parents=True, exist_ok=True)
    run_source_checks(check, root / "sources")
    return {"tests": tests, "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
