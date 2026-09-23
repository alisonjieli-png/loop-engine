"""What the waiting list flood guard keeps about a network address, and for how long.

Moved out of `waitlist_checks.py` on September 22, 2026, when the checks for
removing a source record with no time left pushed that module past the
800-line cap. The fixtures stay in `waitlist_checks.py` and are imported here.

The published privacy notice says the guard keeps the times of recent
requests under a keyed one-way digest of the sending address, never the
address itself, and removes them once the counting window has passed. Each
clause has a check over real records, and a known-wrong case beside it shows
that the check finds the defect it names. No external service is contacted.
"""
from __future__ import annotations

import hashlib
import uuid
from unittest.mock import patch

from .records import ServiceRuntimeError, digest
from .waitlist import (SOURCE, SOURCE_SCHEMA, SOURCE_SECRET_UNAVAILABLE, SOURCE_SECRET_UNUSABLE,
                       UNKEYED_SOURCE, WAITING, ServiceWaitlist, WaitlistPolicy, keyed_source_digest)
from .waitlist_checks import (_attempt, _stored_row, prepared, refused, request, source_record_findings,
                              source_rows)


def counts_outside_window(rows, now, window_seconds):
    """Every stored count that is older than the window at `now`."""
    return [value for row in rows for value in row["payload"].get("accepted", [])
            if value <= now - window_seconds]


def _plant(fixture, kind, logical_identity, payload):
    """Write one record the way an earlier release would have, for a refusal check."""
    catalog = fixture.runtime._catalog
    row = catalog.record(kind, logical_identity, payload)
    with catalog.store(write=True) as store:
        catalog.commit(store, (row,), (catalog.guard(None, row["record_id"]),))


def _empties_instead_of_removing(catalog, store, now, window_seconds):
    """The known-wrong sweep of the earlier release: trim every record, remove none.

    A record with no time left keeps its version and an empty list, and a
    record that is already empty is left alone.
    """
    oldest, changed, guards = now - window_seconds, [], []
    for row in catalog.rows_all(store, SOURCE):
        payload = ServiceWaitlist._source_payload(row)
        kept = [value for value in payload["accepted"] if value > oldest]
        if kept != payload["accepted"]:
            changed.append({**row, "record_version": uuid.uuid4().hex, "payload": {**payload, "accepted": kept}})
            guards.append(catalog.guard(row))
    if changed:
        catalog.commit(store, changed, guards)
    return {"trimmed": len(changed), "removed": 0}


def _moments(fixture, joins):
    for moment, email, source in joins:
        with patch.object(fixture.runtime, "_clock", lambda moment=moment: moment):
            fixture.waitlist.join(request(email, source=source))


def source_privacy_checks(check, root):
    """Each clause of the published sentence about source records, over real records."""
    address = "198.51.100.23"
    keyed = prepared(root / "keyed", accepted_for_each_source=3)
    keyed.waitlist.join(request("kay@example.com", source=address))
    catalog, rows = keyed.runtime._catalog, source_rows(keyed.runtime)
    check("no_stored_source_record_holds_the_address_or_an_unkeyed_digest_of_it",
          len(rows) == 1 and not source_record_findings(rows[0], address, catalog)
          and rows[0]["record_id"] == catalog.identity(SOURCE, keyed_source_digest(keyed.source_secret, address))
          and set(rows[0]["payload"]) == {"record_type", "accepted", "window_seconds"})
    # Known-wrong cases: a record named by the address itself, as the first
    # version of this record was, and records that carry the address or an
    # unkeyed digest of it in a field. The named check finds every one.
    named = prepared(root / "named", accepted_for_each_source=3)
    with patch("loop_engine.core.service_runtime.waitlist.keyed_source_digest", lambda _secret, key: key):
        named.waitlist.join(request("una@example.com", source=address))
    planted = [(row, named.runtime._catalog) for row in source_rows(named.runtime)] + [
        ({**rows[0], "payload": {**rows[0]["payload"], **field}}, catalog) for field in (
            {"note": "from " + address}, {"source_digest": digest([address])},
            {"source_digest": hashlib.sha256(address.encode("utf-8")).hexdigest()})]
    check("KNOWN_WRONG_a_source_record_that_gives_away_the_address_is_found_in_every_form",
          len(planted) == 4 and all(source_record_findings(row, address, owner) for row, owner in planted))

    # A host that names no secret takes no count, exactly as a host that
    # declares no address source does. It never falls back to a plain digest.
    secretless = prepared(root / "secretless", keyed=False, accepted_for_each_source=2)
    answers = [_attempt(lambda index=index: secretless.waitlist.join(
        request(f"open{index}@example.com", source=address)))[0] for index in range(3)]
    check("a_host_that_names_no_secret_takes_no_count_and_keeps_nothing_about_the_address",
          [answer and answer["source_counted"] for answer in answers] == [UNKEYED_SOURCE] * 3
          and source_rows(secretless.runtime) == [])
    fallback = prepared(root / "fallback", keyed=False, accepted_for_each_source=2)
    with patch.object(ServiceWaitlist, "_keyed_source", lambda self, key: digest([key])):
        fell = [fallback.waitlist.join(request(f"fell{index}@example.com", source=address)) for index in range(2)]
    fallen = source_rows(fallback.runtime)
    check("KNOWN_WRONG_a_plain_digest_fallback_counts_and_keeps_a_digest_anyone_can_recompute",
          [answer["source_counted"] for answer in fell] == ["counted", "counted"] and len(fallen) == 1
          and bool(source_record_findings(fallen[0], address, fallback.runtime._catalog)))

    # A secret the host names but the service cannot read, or one too short to
    # key a digest, refuses the request before anything is written. Counting
    # under a weaker digest instead would break the promise without a sign.
    unreadable = prepared(root / "unreadable", secret=ServiceRuntimeError("configured_secret_unavailable"))
    check("a_named_secret_that_cannot_be_read_refuses_the_request_before_any_write",
          refused(lambda: unreadable.waitlist.join(request("rose@example.com", source=address)),
                  SOURCE_SECRET_UNAVAILABLE)
          and _stored_row(unreadable, "rose@example.com") is None and source_rows(unreadable.runtime) == [])
    short = prepared(root / "short", secret="a-secret-too-short-to-key")
    check("a_secret_too_short_to_key_a_digest_is_refused_instead_of_used",
          refused(lambda: short.waitlist.join(request("sam@example.com", source=address)), SOURCE_SECRET_UNUSABLE)
          and _stored_row(short, "sam@example.com") is None and source_rows(short.runtime) == [])

    # The reader requires the current record version. A first version record
    # anywhere in the collection refuses the request before any write, because
    # this release will not rewrite or count a record it was not written for.
    first_version = {"record_type": "service_waitlist_source/v1", "source_digest": digest(["198.51.100.60"]),
                     "accepted": [], "window_seconds": 3600, "updated_at": 0}
    versioned = prepared(root / "version")
    _plant(versioned, SOURCE, "198.51.100.60", first_version)
    check("a_first_version_source_record_is_refused_before_any_write",
          refused(lambda: versioned.waitlist.join(request("vera@example.com", source="198.51.100.61")),
                  "unsupported_or_corrupt_record")
          and _stored_row(versioned, "vera@example.com") is None)
    lenient = prepared(root / "lenient")
    _plant(lenient, SOURCE, "198.51.100.60", first_version)
    with patch.object(ServiceWaitlist, "_source_payload", staticmethod(lambda row: row["payload"])):
        check("KNOWN_WRONG_a_reader_that_takes_any_version_admits_the_first_version",
              lenient.waitlist.join(request("vera@example.com", source="198.51.100.61"))["state"] == WAITING)
    # The current version holds its times and nothing else. A record of that
    # version that carries one more field is refused rather than read around,
    # so no writer can add something about the address unnoticed.
    widened = prepared(root / "widened")
    _plant(widened, SOURCE, keyed_source_digest(widened.source_secret, "198.51.100.62"),
           {"record_type": SOURCE_SCHEMA, "accepted": [], "window_seconds": 3600, "source_address": "198.51.100.62"})
    check("a_source_record_that_carries_any_other_field_is_refused_before_any_write",
          refused(lambda: widened.waitlist.join(request("xena@example.com", source="198.51.100.63")),
                  "unsupported_or_corrupt_record")
          and _stored_row(widened, "xena@example.com") is None)

    # The published notice promises one hour. A longer window would keep the
    # times of an address past that promise, so the policy refuses it.
    check("a_window_longer_than_the_published_hour_is_refused",
          refused(lambda: WaitlistPolicy(source_window_seconds=3601), "invalid_waitlist_policy")
          and WaitlistPolicy(source_window_seconds=3600).source_window_seconds == 3600)


def source_removal_checks(check, root):
    """Nothing about an address outlives the window, and no record is left behind with nothing in it.

    Every request to join removes the counts that have left the window from
    every source record, and removes a record with no count left. The retention
    task does the same when nobody joins.
    """
    windowed = prepared(root / "window", accepted_for_each_source=3, source_window_seconds=60)
    joins = ((1000.0, "early0@example.com", "198.51.100.40"), (1000.0, "early1@example.com", "198.51.100.41"),
             (1030.0, "middle@example.com", "198.51.100.41"), (1061.0, "later@example.com", "198.51.100.42"))
    _moments(windowed, joins)
    kept = source_rows(windowed.runtime)
    check("no_source_record_keeps_a_count_after_its_window",
          counts_outside_window(kept, 1061.0, 60) == []
          and sorted(tuple(row["payload"]["accepted"]) for row in kept) == [(1030.0,), (1061.0,)]
          and all(set(row["payload"]) == {"record_type", "accepted", "window_seconds"} for row in kept))
    gone = windowed.runtime._catalog.identity(SOURCE, keyed_source_digest(windowed.source_secret, "198.51.100.40"))
    check("a_source_record_with_no_time_left_is_removed_not_emptied",
          len(kept) == 2 and gone not in {row["record_id"] for row in kept})
    # Known-wrong cases: without the sweep a count outlives its window, and the
    # sweep of the earlier release left the first source's record behind with
    # an empty list instead of removing it.
    unswept = prepared(root / "unswept", accepted_for_each_source=3, source_window_seconds=60)
    with patch.object(ServiceWaitlist, "_forget_expired_sources", lambda self, store, catalog, now: 0):
        _moments(unswept, joins)
    check("KNOWN_WRONG_without_the_sweep_a_count_outlives_its_window",
          counts_outside_window(source_rows(unswept.runtime), 1061.0, 60) != [])
    emptied = prepared(root / "emptied", accepted_for_each_source=3, source_window_seconds=60)
    with patch("loop_engine.core.service_runtime.waitlist.forget_expired_sources", _empties_instead_of_removing):
        _moments(emptied, joins)
    check("KNOWN_WRONG_a_sweep_that_empties_instead_of_removing_leaves_a_record_with_nothing_in_it",
          [tuple(row["payload"]["accepted"]) for row in source_rows(emptied.runtime)].count(()) == 1)

    # A record that the earlier release left empty is removed by the next
    # request, whichever source that request comes from.
    legacy = prepared(root / "legacy", source_window_seconds=60)
    _plant(legacy, SOURCE, keyed_source_digest(legacy.source_secret, "198.51.100.50"),
           {"record_type": SOURCE_SCHEMA, "accepted": [], "window_seconds": 60})
    legacy.waitlist.join(request("lee@example.com", source="198.51.100.51"))
    remaining = source_rows(legacy.runtime)
    check("a_source_record_an_earlier_release_left_empty_is_removed_by_the_next_request",
          [row["record_id"] for row in remaining] == [legacy.runtime._catalog.identity(
              SOURCE, keyed_source_digest(legacy.source_secret, "198.51.100.51"))]
          and len(remaining[0]["payload"]["accepted"]) == 1)

    # When nobody joins, the retention task removes the same records on its
    # own schedule, with the installed window, or with one hour, the longest
    # window the notice allows, when no list is installed.
    from .retention import sweep_retention
    quiet = prepared(root / "quiet", source_window_seconds=60)
    _moments(quiet, ((1000.0, "quiet@example.com", "198.51.100.70"),))
    with patch.object(quiet.runtime, "_clock", lambda: 1059.0):
        early = sweep_retention(quiet.runtime, waitlist=quiet.waitlist)
    with patch.object(quiet.runtime, "_clock", lambda: 1060.0):
        late = sweep_retention(quiet.runtime, waitlist=quiet.waitlist)
    check("the_retention_task_removes_source_times_when_nobody_joins",
          early["waitlist_sources"]["removed"] == 0 and late["waitlist_sources"]["removed"] == 1
          and source_rows(quiet.runtime) == [])
    unlisted = prepared(root / "unlisted", source_window_seconds=60)
    _moments(unlisted, ((1000.0, "unlisted@example.com", "198.51.100.71"),))
    with patch.object(unlisted.runtime, "_clock", lambda: 1000.0 + 3599):
        within_hour = sweep_retention(unlisted.runtime)
    with patch.object(unlisted.runtime, "_clock", lambda: 1000.0 + 3600):
        after_hour = sweep_retention(unlisted.runtime)
    check("without_an_installed_list_the_times_are_removed_after_one_hour",
          within_hour["waitlist_sources"]["removed"] == 0 and after_hour["waitlist_sources"]["removed"] == 1
          and source_rows(unlisted.runtime) == [])


def run_source_checks(check, root):
    """Run both groups, each in its own folder under `root`."""
    for name, function in (("privacy", source_privacy_checks), ("removal", source_removal_checks)):
        folder = root / name
        folder.mkdir(parents=True, exist_ok=True)
        function(check, folder)
