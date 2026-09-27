"""The weekly number's record shape and refusals, from recorded fixture answers and no network.

The fixture answers have the shape the providers gave on September 25 and 26,
2026 (the identity provider's user listing, the live billing account's list
objects, the service's public health and capabilities records, the daily
job's counts and journal, and the deployment evidence records), with fixture
addresses and fixture identifiers. No credential value is real: every
fixture value is built at run time from its prefix, so no key-shaped literal
enters the repository.
"""
from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import weekly_number as tool  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 9, 26, 12, 40, tzinfo=UTC)
IDENTITY_VALUE = "sb_" + "secret_" + "F" * 30
BILLING_VALUE = "rk_" + "live_" + "F" * 30
TEST_MODE_VALUE = "rk_" + "test_" + "F" * 30
MANIFEST = {"record_type": "operator_credential_references/v1", "api_keys": {
    "supabase-secret": {"service": "supabase", "account": "abcdefghijklmnopqrst", "purpose": "secret-api",
                        "environment": "FIXTURE_IDENTITY", "required_prefixes": ["sb_secret_"],
                        "value_pattern": "sb_secret_[A-Za-z0-9_-]{20,128}"},
    "stripe-live": {"service": "stripe", "account": "acct_fixture", "purpose": "runtime-live-api",
                    "environment": "FIXTURE_BILLING", "required_prefixes": ["rk_live_", "sk_live_"],
                    "value_pattern": "(rk|sk)_live_[A-Za-z0-9]{24,250}"}}}
ENVIRONMENT = {"FIXTURE_IDENTITY": IDENTITY_VALUE, "FIXTURE_BILLING": BILLING_VALUE}


def epoch(moment):
    return int(moment.timestamp())


def identity_users():
    """Eighteen accounts, nine confirmed: two on September 20 and sixteen check journeys on September 24."""
    users = []
    for index in range(2):
        made = datetime(2026, 9, 20, 13, 31, index, tzinfo=UTC)
        users.append({"id": f"fixture-user-{index}", "email": f"person{index}@fixture.example",
                      "created_at": made.isoformat().replace("+00:00", "Z"),
                      "email_confirmed_at": (made + timedelta(minutes=3)).isoformat().replace("+00:00", "Z"),
                      "aud": "authenticated", "role": "authenticated"})
    for index in range(16):
        made = datetime(2026, 9, 24, 10, 34, index, tzinfo=UTC)
        confirmed = (made + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S.901234567Z") if index < 7 else None
        users.append({"id": f"fixture-check-{index}", "email": f"baltor-check-{index:08x}@inbox.example",
                      "created_at": made.strftime("%Y-%m-%dT%H:%M:%S.123456Z"), "email_confirmed_at": confirmed,
                      "aud": "authenticated", "role": "authenticated"})
    return users


def billing_answers(livemode=True):
    session_time = epoch(datetime(2026, 9, 21, 13, 5, tzinfo=UTC))
    sessions = [{"id": "cs_live_fixture0000000001", "object": "checkout.session", "status": "expired",
                 "created": session_time, "livemode": livemode, "mode": "subscription", "payment_status": "unpaid"},
                {"id": "cs_live_fixture0000000002", "object": "checkout.session", "status": "open",
                 "created": session_time + 600, "livemode": livemode, "mode": "subscription", "payment_status": "unpaid"}]
    return {"/v1/subscriptions": {"object": "list", "data": [], "has_more": False, "url": "/v1/subscriptions"},
            "/v1/customers": {"object": "list", "data": [], "has_more": False, "url": "/v1/customers"},
            "/v1/checkout/sessions": {"object": "list", "data": sessions, "has_more": False,
                                      "url": "/v1/checkout/sessions"}}


HEALTH = {"record_type": "service_http_result/v1", "operation": "health", "result": {
    "record_type": "service_health/v2", "alive": True, "ready": True, "readiness_checked": True,
    "checks": [{"name": "durable_store_answers", "required": True, "passed": True, "code": ""}],
    "catalogue_release": {"record_type": "service_catalogue_view/v1", "source": "store",
                          "release_id": "856bff51fac2bf8f4d70b181a8b129d4fdaa5624dffe020db06ce5239724053f",
                          "content_digest": "d0f4f7ea64ae0406f398ff0e358a3999bb27c65d2172d1254bb647d92aac757d",
                          "items": 6398, "withdrawn_left_out": 0, "catalogue_state_revision": 22,
                          "built_at": epoch(datetime(2026, 9, 26, 5, 54, 13, tzinfo=UTC))}}}
CAPABILITIES = {"record_type": "service_http_result/v1", "operation": "capabilities", "result": {
    "record_type": "service_capabilities/v1", "api_version": "v1",
    "website": {"display_name": "Baltor", "registration_available": True},
    "library": {"served_items": 6398}, "billing": {"webhook": True, "checkout": True, "portal": True}}}


def many_users(count):
    """Fixture accounts made one a minute from September 22, 2026, every third one confirmed."""
    users = []
    for index in range(count):
        made = datetime(2026, 9, 22, 8, 0, tzinfo=UTC) + timedelta(minutes=index)
        confirmed = (made + timedelta(minutes=5)).isoformat().replace("+00:00", "Z") if index % 3 == 0 else None
        users.append({"id": f"fixture-user-{index:05d}", "email": f"person{index}@fixture.example",
                      "created_at": made.isoformat().replace("+00:00", "Z"), "email_confirmed_at": confirmed,
                      "aud": "authenticated", "role": "authenticated"})
    return users


def paged_identity(users, page_cap, *, total_header=True, reported=None, shift_after_first_page=False):
    """An identity provider that returns at most page_cap rows a page, whatever size is asked for.

    With shift_after_first_page an account made between two reads pushes the listing down
    by one row, so the last row of a page appears again at the head of the next one.
    """
    def answer(query):
        page = int(query.get("page", ["1"])[0])
        start = (page - 1) * page_cap - (1 if shift_after_first_page and page > 1 else 0)
        rows = users[start:start + page_cap]
        response_headers = {"Content-Type": "application/json"}
        if total_header:
            response_headers["X-Total-Count"] = str(len(users) if reported is None else reported)
        return 200, response_headers, json.dumps({"users": rows, "aud": "authenticated"}).encode()
    return answer


def identity_pages_asked(transport):
    return [urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["page"][0]
            for _method, url, _headers in transport.asked if tool.IDENTITY_USERS_PATH in url]


class Transport:
    """Answers like the providers, keyed by path, and records every request it was asked."""

    def __init__(self, answers=None, statuses=None, dynamic=None):
        self.answers = {"/auth/v1/admin/users": {"users": identity_users(), "aud": "authenticated"},
                        "/api/v1/health": HEALTH, "/api/v1/capabilities": CAPABILITIES, **billing_answers(),
                        **(answers or {})}
        self.statuses, self.dynamic, self.asked = statuses or {}, dynamic or {}, []

    def __call__(self, method, url, headers):
        parts = urllib.parse.urlsplit(url)
        self.asked.append((method, url, dict(headers)))
        if parts.path in self.statuses:
            return self.statuses[parts.path], {}, b""
        if parts.path in self.dynamic:
            return self.dynamic[parts.path](urllib.parse.parse_qs(parts.query))
        body = self.answers.get(parts.path)
        if body is None:
            return 404, {}, b""
        response_headers = {"Content-Type": "application/json"}
        if parts.path == "/auth/v1/admin/users":
            # The identity provider names the whole count in this header, as the real answer did.
            response_headers["X-Total-Count"] = str(len(body["users"]))
        return 200, response_headers, json.dumps(body).encode()


def commit_time(revision):
    """The fixture commit is always forty minutes before the deployment it produced."""
    return {"2cc06eb7810d3d3088bad30a0cc42fbfa005d4a3": datetime(2026, 9, 25, 21, 42, 20, tzinfo=UTC),
            "cd0794772a9d1da35b074457f88a4272f58ed57c": datetime(2026, 9, 25, 22, 43, tzinfo=UTC),
            "bcd05095b204ee1b7e455f92c82cf8158f480ba0": datetime(2026, 9, 10, 10, 0, tzinfo=UTC)}.get(revision)


def birth_time(folder):
    return {"2026-09-26-10": datetime(2026, 9, 26, 10, 17, 1, tzinfo=UTC)}.get(folder.name)


def write_fixture_folders(root):
    releases = root / "releases"
    releases.mkdir()
    (releases / "pilot-release-12.json").write_text(json.dumps({"record_type": "pilot_release_record/v1",
                                                                 "source_revision": "0d1f883b"}), "utf-8")
    for number, revision, deployed, failed in (
            (23, "bcd05095b204ee1b7e455f92c82cf8158f480ba0", "2026-09-10T10:34:04Z", None),
            (35, "2cc06eb7810d3d3088bad30a0cc42fbfa005d4a3", "2026-09-25T22:22:20Z", []),
            (36, "cd0794772a9d1da35b074457f88a4272f58ed57c", "2026-09-25T23:23:00Z", [{"run": 1}, {"run": 2}])):
        record = {"record_type": "deployment_evidence/v1", "fly_release": number, "source_revision": revision,
                  "deployed_at": deployed, "image_digest": "sha256:" + "0" * 64}
        if failed is not None:
            record["failed_first_attempts"] = failed
        (releases / f"pilot-release-{number}.json").write_text(json.dumps(record), "utf-8")
    daily = root / "daily"
    slot = daily / "2026-09-26-10"
    slot.mkdir(parents=True)
    (slot / "counts.json").write_text(json.dumps({
        "record_type": "daily_library_release_counts/v1", "day": "2026-09-26-10", "exported": 2000,
        "passed_prechecks": 1660, "reviewed": 1660, "review_calls": 139, "approved": 1586, "rejected": 45,
        "left_out": 29, "published": True, "checked_live": True}), "utf-8")
    journal = [("2026-09-26T10:17:24Z", "export", "done"), ("2026-09-26T10:32:48Z", "prechecks", "done"),
               ("2026-09-26T10:33:37Z", "calibrate", "batch-of-12 status: qualified"),
               ("2026-09-26T10:33:37Z", "calibrate", "done"), ("2026-09-26T11:37:49Z", "review", "done"),
               ("2026-09-26T11:52:02Z", "write", "done"), ("2026-09-26T11:52:13Z", "combine", "done"),
               ("2026-09-26T11:52:24Z", "bundle", "done"), ("2026-09-26T11:55:32Z", "publish", "done"),
               ("2026-09-26T11:55:34Z", "check", "done"), ("2026-09-26T11:55:34Z", "counts", "done")]
    (slot / "journal.jsonl").write_text("".join(json.dumps({"at": at, "stage": stage, "note": note}) + "\n"
                                                for at, stage, note in journal), "utf-8")
    old = daily / "2026-09-01"
    old.mkdir()
    (old / "counts.json").write_text(json.dumps({"record_type": "daily_library_release_counts/v1", "day": "2026-09-01",
                                                 "approved": 5, "published": True}), "utf-8")
    (old / "journal.jsonl").write_text(json.dumps({"at": "2026-09-01T10:00:00Z", "stage": "counts", "note": "done"}) + "\n",
                                       "utf-8")
    return releases, daily


class Run:
    def __init__(self, root, *, environment=ENVIRONMENT, transport=None, resolver=None, now=NOW, origin="https://service.example"):
        self.transport = Transport() if transport is None else transport
        self.output = root / "records"
        releases, daily = write_fixture_folders(root) if not (root / "releases").exists() else (root / "releases", root / "daily")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.code = tool.main(["--output-folder", str(self.output), "--release-records", str(releases),
                                   "--library-daily", str(daily), "--origin", origin],
                                  environment=environment, transport=self.transport,
                                  resolver=resolver or (lambda reference: (None, "keyring_not_asked")),
                                  now=now, manifest=MANIFEST, commit_time=commit_time, birth_time=birth_time)
        self.stdout, self.stderr = out.getvalue(), err.getvalue()
        self.records = sorted(self.output.glob("*.json")) if self.output.exists() else []
        self.record = json.loads(self.records[-1].read_text("utf-8")) if self.records else None


class WeeklyNumberRecordTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_the_record_has_the_declared_shape_from_the_recorded_answers(self):
        run = Run(self.root)
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual([path.name for path in run.records], ["weekly-number-2026-09-26-1.json"])
        record = run.record
        self.assertEqual(record["record_type"], "weekly_number/v1")
        self.assertEqual(record["window"], {"from": "2026-09-19T12:40:00Z", "to": "2026-09-26T12:40:00Z", "days": 7})
        self.assertTrue(record["complete"])
        self.assertEqual({name: row["status"] for name, row in record["sources"].items()},
                         {"identity": "read", "billing": "read", "public": "read", "releases": "read", "library": "read"})
        accounts = record["counts"]["accounts"]
        self.assertEqual((accounts["total"], accounts["confirmed"], accounts["check_journey_total"],
                          accounts["check_journey_confirmed"], accounts["made_this_week"], accounts["confirmed_this_week"]),
                         (18, 9, 16, 7, 18, 9))
        self.assertEqual(accounts["made_by_day"], {"2026-09-20": 2, "2026-09-24": 16})
        self.assertEqual(accounts["data_start"], "2026-09-20T13:31:00Z")
        self.assertEqual((accounts["reported_total"], accounts["deleted"], accounts["unreadable_dates"]), (18, 0, 0))
        billing = record["counts"]["billing"]
        self.assertEqual((billing["paying_subscriptions"], billing["customers_total"], billing["checkout_sessions_started"],
                          billing["checkout_sessions_finished"], billing["checkout_sessions_started_this_week"]),
                         (0, 0, 2, 0, 2))
        self.assertEqual(billing["checkout_sessions_by_status"], {"open": 1, "complete": 0, "expired": 1})
        self.assertEqual(record["sources"]["billing"], {"status": "read", "requests": 3, "reference": "stripe-live",
                                                        "write_requests": 0, "charges_made": 0})
        library = record["counts"]["library"]
        self.assertEqual((library["packages_served"], library["items_in_release"], library["active_release_id"][:8],
                          library["built_at"], library["service_ready"]), (6398, 6398, "856bff51", "2026-09-26T05:54:13Z", True))
        releases = record["cycle_times"]["releases"]
        self.assertEqual((releases["records_read"], releases["count_this_week"], releases["latest_release"],
                          releases["failed_first_attempts_this_week"]), (3, 2, 36, 2))
        self.assertEqual(releases["commit_to_live_minutes"], {"known": 2, "median": 40.0, "min": 40.0, "max": 40.0})
        slots = record["cycle_times"]["library"]
        self.assertEqual((slots["slots_read"], slots["count_this_week"], slots["approved_this_week"], slots["published_this_week"]),
                         (2, 1, 1586, 1))
        self.assertEqual(slots["start_to_served_minutes"]["median"], 98.5)
        self.assertEqual(slots["review_minutes"]["median"], 64.2)
        self.assertEqual(slots["slots_this_week"][0]["start_source"], "folder_birth_time")
        self.assertEqual(record["counts"]["visitors"]["status"], "not_measured")
        self.assertEqual(record["physical_model_calls"], 0)
        self.assertEqual(record["previous_records"], [])
        self.assertIn("staff page", " ".join(record["not_in_this_command"]))

    def test_the_record_holds_no_address_identifier_or_credential(self):
        run = Run(self.root)
        text = run.records[-1].read_text("utf-8")
        for forbidden in ("@", "fixture.example", "cs_live", "fixture-user", IDENTITY_VALUE, BILLING_VALUE, "Bearer"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn(IDENTITY_VALUE, run.stdout)
        self.assertNotIn(BILLING_VALUE, run.stdout)

    def test_the_credentials_travel_in_headers_and_the_billing_account_only_sees_reads(self):
        run = Run(self.root)
        methods = {method for method, _url, _headers in run.transport.asked}
        self.assertEqual(methods, {"GET"})
        identity = [headers for _m, url, headers in run.transport.asked if "/auth/v1/admin/users" in url]
        billing = [(url, headers) for _m, url, headers in run.transport.asked if url.startswith("https://api.stripe.com/")]
        self.assertEqual(len(identity), 1)
        self.assertEqual(identity[0]["apikey"], IDENTITY_VALUE)
        self.assertEqual(len(billing), 3)
        for url, headers in billing:
            self.assertEqual(headers["Authorization"], "Bearer " + BILLING_VALUE)
            self.assertNotIn(BILLING_VALUE, url)
        self.assertIn("status=all", billing[0][0])

    def test_every_count_that_may_mix_check_journeys_carries_its_mark(self):
        run = Run(self.root)
        for name in ("accounts", "billing"):
            self.assertIs(run.record["counts"][name]["mixes_test_journeys"], True)
            self.assertIn("cannot be told apart", run.record["counts"][name]["note"])
        self.assertIs(run.record["counts"]["library"]["mixes_test_journeys"], False)
        unmarked = json.loads(json.dumps(run.record))
        del unmarked["counts"]["accounts"]["mixes_test_journeys"]
        with self.assertRaises(tool.Refusal) as refused:
            tool.refuse_unmarked_mixed_counts(unmarked)
        self.assertEqual(refused.exception.code, "mixed_count_without_a_mark")
        tool.refuse_unmarked_mixed_counts(run.record)

    def test_no_rate_is_presented_as_measured_before_a_week_of_data(self):
        run = Run(self.root)
        rates = run.record["funnel_rates"]
        self.assertEqual(rates["visitors_to_accounts"]["status"], "not_measured")
        self.assertEqual((rates["accounts_to_paying"]["status"], rates["accounts_to_paying"]["days_of_data"]),
                         ("not_measured", 4))
        self.assertEqual(rates["accounts_to_paying"]["assumed_in_plan_percent"], 10)
        self.assertEqual(rates["checkout_started_to_finished"]["status"], "not_measured")
        self.assertIn("not measured", run.stdout)
        later = Run(self.root, now=NOW + timedelta(days=14))
        self.assertEqual(later.record["funnel_rates"]["accounts_to_paying"],
                         {"days_of_data": 18, "numerator": 0, "denominator": 2, "assumed_in_plan_percent": 10,
                          "status": "measured", "percent": 0.0})
        self.assertEqual(tool.rate_entry(6, 1, 10)["status"], "not_measured")
        self.assertEqual(tool.rate_entry(7, 1, 10)["percent"], 10.0)
        with self.assertRaises(tool.Refusal) as refused:
            tool.refuse_early_rates({"accounts_to_paying": {"status": "measured", "days_of_data": 3, "percent": 50.0}})
        self.assertEqual(refused.exception.code, "rate_presented_before_a_week_of_data")

    def test_the_table_is_plain_text_with_the_marks(self):
        run = Run(self.root)
        lines = run.stdout.splitlines()
        self.assertTrue(lines[0].startswith("Weekly number, window 2026-09-19T12:40:00Z to 2026-09-26T12:40:00Z (7 days)"))
        joined = "\n".join(lines)
        for expected in ("accounts made", "18", "mixed: 16 match the check journey prefix", "paying subscriptions",
                         "packages served", "6,398", "releases to Fly", "commit to live median 40.0 minutes over 2",
                         "library slots run", "start to served median 98.5 minutes", "visitors", "rate accounts to paying",
                         "record: "):
            self.assertIn(expected, joined)
        self.assertNotIn(chr(0x2014), joined)

    def test_a_second_run_writes_a_new_name_and_names_the_earlier_record(self):
        first, second = Run(self.root), Run(self.root)
        self.assertEqual((first.code, second.code), (0, 0))
        self.assertEqual([path.name for path in second.records],
                         ["weekly-number-2026-09-26-1.json", "weekly-number-2026-09-26-2.json"])
        self.assertEqual(second.record["previous_records"], ["weekly-number-2026-09-26-1.json"])
        self.assertEqual(json.loads(second.records[0].read_text("utf-8"))["previous_records"], [])


class IdentityListingTests(unittest.TestCase):
    """The account listing is read whole, whatever page size the provider allows."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_the_listing_follows_the_reported_total_when_the_provider_caps_a_page(self):
        # The known-wrong case: 120 accounts, a provider that returns at most 50 a page whatever
        # size is asked for, and the whole count in its header. A reader that stops at the first
        # short page reports 50 accounts and calls the record complete.
        transport = Transport(dynamic={tool.IDENTITY_USERS_PATH: paged_identity(many_users(120), 50)})
        run = Run(self.root, transport=transport)
        self.assertEqual(run.code, 0, run.stderr)
        accounts = run.record["counts"]["accounts"]
        self.assertEqual((accounts["total"], accounts["reported_total"], accounts["confirmed"]), (120, 120, 40))
        self.assertEqual(run.record["sources"]["identity"]["requests"], 3)
        self.assertEqual(identity_pages_asked(run.transport), ["1", "2", "3"])

    def test_without_the_total_header_only_an_empty_page_ends_the_listing(self):
        transport = Transport(dynamic={tool.IDENTITY_USERS_PATH: paged_identity(many_users(120), 50, total_header=False)})
        run = Run(self.root, transport=transport)
        self.assertEqual(run.code, 0, run.stderr)
        accounts = run.record["counts"]["accounts"]
        self.assertEqual((accounts["total"], accounts["reported_total"]), (120, None))
        self.assertEqual(identity_pages_asked(run.transport), ["1", "2", "3", "4"])

    def test_a_row_repeated_across_pages_is_counted_once(self):
        # An account made between two reads shifts the listing by one row.
        transport = Transport(dynamic={tool.IDENTITY_USERS_PATH: paged_identity(many_users(120), 50,
                                                                                 shift_after_first_page=True)})
        run = Run(self.root, transport=transport)
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual(run.record["counts"]["accounts"]["total"], 120)
        self.assertEqual(identity_pages_asked(run.transport), ["1", "2", "3"])

    def test_a_listing_shorter_than_the_reported_total_makes_identity_unavailable(self):
        transport = Transport(dynamic={tool.IDENTITY_USERS_PATH: paged_identity(many_users(18), 50, reported=20)})
        run = Run(self.root, transport=transport)
        self.assertEqual(run.code, 1)
        self.assertFalse(run.record["complete"])
        self.assertEqual(run.record["sources"]["identity"],
                         {"status": "unavailable", "code": "listing_shorter_than_the_reported_total",
                          "reference": "supabase-secret"})
        self.assertEqual(run.record["counts"]["accounts"],
                         {"status": "unavailable", "code": "listing_shorter_than_the_reported_total"})
        self.assertIn("INCOMPLETE", run.stdout)
        self.assertEqual(run.record["counts"]["billing"]["checkout_sessions_started"], 2)

    def test_a_deleted_account_is_counted_apart(self):
        # The real run of September 26, 2026 found two accounts the provider marks deleted and
        # still lists; the reported total includes them, so total keeps them and deleted names them.
        users = many_users(3)
        users[1]["deleted_at"] = "2026-09-25T09:00:00Z"
        counts = tool.account_counts(users, tool.Window(NOW - timedelta(days=7), NOW))
        self.assertEqual((counts["total"], counts["deleted"], counts["confirmed"]), (3, 1, 1))
        run = Run(self.root, transport=Transport(dynamic={tool.IDENTITY_USERS_PATH: paged_identity(users, 50)}))
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual((run.record["counts"]["accounts"]["total"], run.record["counts"]["accounts"]["deleted"]), (3, 1))
        self.assertIn("mixed: 0 match the check journey prefix; 1 marked deleted and still listed", run.stdout)


#: Release 38 as the release workflow recorded it on September 27, 2026, with the fields this reader uses.
PILOT_RELEASE_38 = {"record_type": "pilot_release_record/v1", "release": 38, "deployed_at": "2026-09-27T01:19:33Z",
                    "source_revision": "13caeb2039c28681e8c8793cfede80255e6f033a",
                    "image": "registry.fly.io/baltor-pilot@sha256:" + "e" * 64,
                    "rollback_image": "registry.fly.io/baltor-pilot@sha256:" + "7" * 64,
                    "ci_run": 36284690803, "deploy_run": 36285062623}


class ReleaseRecordVersionTests(unittest.TestCase):
    """Both named release record versions are read through their own fields; any other type refuses the source.

    Until September 27, 2026 the reader skipped every record that was not deployment_evidence/v1, so releases
    38 to 40, recorded as pilot_release_record/v1, were missing and the weekly number stopped at release 37.
    """

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.releases = Path(self.folder.name)
        self.window = tool.Window(datetime(2026, 9, 21, 6, 0, tzinfo=UTC), datetime(2026, 9, 28, 6, 0, tzinfo=UTC))

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, record):
        (self.releases / name).write_text(json.dumps(record), "utf-8")

    def write_both_versions(self):
        self.write("pilot-release-37.json", {"record_type": "deployment_evidence/v1", "fly_release": 37,
                                             "deployed_at": "2026-09-26T13:25:00Z", "source_revision": "43b421f8",
                                             "failed_first_attempts": [{"revision": "edcc77a3"}]})
        for number, deployed in ((38, "2026-09-27T01:19:33Z"), (39, "2026-09-27T03:58:55Z"), (40, "2026-09-27T05:11:34Z")):
            self.write(f"pilot-release-{number}.json", dict(PILOT_RELEASE_38, release=number, deployed_at=deployed))
        # The September 20 to 23 records of the same type carry no deployment time; they are left out by name.
        self.write("pilot-release-12.json", {"record_type": "pilot_release_record/v1", "release": 12,
                                             "fly_release_version": 14, "observed_at": "2026-09-23T03:40:00Z"})

    def test_both_versions_are_read_and_the_latest_release_is_40(self):
        self.write_both_versions()
        releases = tool.read_releases(self.releases, self.window, commit_time=lambda revision: None)
        self.assertEqual(releases["latest_release"], 40)
        self.assertEqual((releases["records_read"], releases["count_this_week"]), (4, 4))
        self.assertEqual(releases["records_by_type"], {"deployment_evidence/v1": 1, "pilot_release_record/v1": 3})
        self.assertEqual([row["fly_release"] for row in releases["releases_this_week"]], [37, 38, 39, 40])
        self.assertEqual(releases["left_out"], [{"record": "pilot-release-12.json",
                                                 "record_type": "pilot_release_record/v1",
                                                 "reason": "no deployment time"}])

    def test_a_fact_the_version_does_not_record_stays_unknown(self):
        self.write_both_versions()
        releases = tool.read_releases(self.releases, self.window, commit_time=lambda revision: None)
        failed = {row["fly_release"]: row["failed_first_attempts"] for row in releases["releases_this_week"]}
        self.assertEqual(failed, {37: 1, 38: None, 39: None, 40: None})
        self.assertEqual((releases["failed_first_attempts_this_week"],
                          releases["releases_with_failed_first_attempts_recorded"]), (1, 1))

    def test_each_version_is_read_through_its_own_fields_only(self):
        # A release number under the other version's field name is not borrowed across versions.
        self.write("pilot-release-41.json", {"record_type": "pilot_release_record/v1", "fly_release": 41,
                                             "deployed_at": "2026-09-27T07:00:00Z"})
        self.write("pilot-release-42.json", {"record_type": "deployment_evidence/v1", "release": 42,
                                             "deployed_at": "2026-09-27T08:00:00Z"})
        releases = tool.read_releases(self.releases, self.window, commit_time=lambda revision: None)
        self.assertEqual([row["fly_release"] for row in releases["releases_this_week"]], [None, None])
        self.assertIsNone(releases["latest_release"])

    def test_an_unknown_record_type_refuses_the_release_source_by_name(self):
        self.write_both_versions()
        self.write("pilot-release-41.json", dict(PILOT_RELEASE_38, record_type="pilot_release_record/v2", release=41))
        with self.assertRaises(tool.Refusal) as refused:
            tool.read_releases(self.releases, self.window, commit_time=lambda revision: None)
        self.assertEqual((refused.exception.code, refused.exception.fields), ("release_record_type_unknown",
                                                                             {"record": "pilot-release-41.json"}))
        for shape in ([1, 2], {"release": 41}):
            with self.subTest(shape=shape), self.assertRaises(tool.Refusal):
                self.write("pilot-release-41.json", shape)
                tool.read_releases(self.releases, self.window, commit_time=lambda revision: None)

    def test_the_weekly_record_marks_the_refused_source_and_the_table_says_why(self):
        root = self.releases / "run"
        root.mkdir()
        folders = write_fixture_folders(root)
        (folders[0] / "pilot-release-41.json").write_text(json.dumps({"record_type": "release_note/v9"}), "utf-8")
        run = Run(root)
        self.assertEqual(run.code, 1, run.stderr)  # the record is written and marked incomplete
        self.assertEqual(run.record["sources"]["releases"], {"status": "unavailable", "code": "release_record_type_unknown",
                                                             "record": "pilot-release-41.json"})
        self.assertFalse(run.record["complete"])
        self.assertIn("unavailable: release_record_type_unknown", run.stdout)

    def test_the_table_names_the_latest_release(self):
        run = Run(self.releases)
        self.assertIn("latest release 36; commit to live median 40.0 minutes over 2", run.stdout)

    def test_the_committed_release_records_reach_release_40(self):
        releases = tool.read_releases(tool.RELEASE_RECORDS, self.window, commit_time=lambda revision: None)
        self.assertGreaterEqual(releases["latest_release"], 40)
        read = {row["fly_release"] for row in releases["releases_this_week"]}
        self.assertLessEqual({38, 39, 40}, read)
        self.assertGreaterEqual(releases["records_by_type"].get("pilot_release_record/v1", 0), 3)


class WeeklyNumberRefusalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_a_missing_credential_refuses_before_any_request_and_names_the_reference_only(self):
        for environment, reference, variable in (({"FIXTURE_BILLING": BILLING_VALUE}, "supabase-secret", "FIXTURE_IDENTITY"),
                                                 ({"FIXTURE_IDENTITY": IDENTITY_VALUE}, "stripe-live", "FIXTURE_BILLING"),
                                                 ({}, "supabase-secret", "FIXTURE_IDENTITY"),
                                                 ({"FIXTURE_IDENTITY": "", "FIXTURE_BILLING": BILLING_VALUE}, "supabase-secret",
                                                  "FIXTURE_IDENTITY")):
            with self.subTest(reference=reference):
                run = Run(self.root, environment=environment,
                          resolver=lambda name: (None, "workstation_keyring_locked"))
                self.assertEqual(run.code, 2)
                self.assertIn("refused: credential_missing", run.stderr)
                self.assertIn("reference=" + reference, run.stderr)
                self.assertIn("environment=" + variable, run.stderr)
                self.assertIn("workstation_keyring_locked", run.stderr)
                self.assertNotIn(IDENTITY_VALUE, run.stderr + run.stdout)
                self.assertNotIn(BILLING_VALUE, run.stderr + run.stdout)
                self.assertEqual(run.transport.asked, [])
                self.assertEqual(run.records, [])

    def test_the_keyring_is_asked_only_for_what_the_environment_lacks(self):
        asked = []

        def resolver(reference):
            asked.append(reference)
            return IDENTITY_VALUE, ""
        run = Run(self.root, environment={"FIXTURE_BILLING": BILLING_VALUE}, resolver=resolver)
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual(asked, ["supabase-secret"])

    def test_a_test_mode_key_under_the_live_reference_is_refused(self):
        run = Run(self.root, environment={"FIXTURE_IDENTITY": IDENTITY_VALUE, "FIXTURE_BILLING": TEST_MODE_VALUE})
        self.assertEqual(run.code, 2)
        self.assertIn("refused: credential_shape_refused reference=stripe-live", run.stderr)
        self.assertNotIn(TEST_MODE_VALUE, run.stderr)
        self.assertEqual(run.transport.asked, [])
        self.assertEqual(run.records, [])

    def test_a_write_request_is_refused_before_the_transport_is_asked(self):
        transport = Transport()
        with self.assertRaises(tool.Refusal) as refused:
            tool.request(transport, "POST", "https://api.stripe.com/v1/subscriptions", {})
        self.assertEqual(refused.exception.code, "write_request_refused")
        with self.assertRaises(tool.Refusal):
            tool.request(transport, "GET", "http://api.stripe.com/v1/subscriptions", {})
        self.assertEqual(transport.asked, [])

    def test_a_sandbox_row_in_the_live_answer_makes_billing_unavailable_and_the_record_says_so(self):
        run = Run(self.root, transport=Transport(answers=billing_answers(livemode=False)))
        self.assertEqual(run.code, 1)
        self.assertFalse(run.record["complete"])
        self.assertEqual(run.record["sources"]["billing"]["code"], "sandbox_row_in_live_answer")
        self.assertEqual(run.record["counts"]["billing"], {"status": "unavailable", "code": "sandbox_row_in_live_answer"})
        self.assertEqual(run.record["funnel_rates"]["accounts_to_paying"]["reason"], "a source was unavailable")
        self.assertIn("INCOMPLETE", run.stdout)
        self.assertEqual(run.record["counts"]["accounts"]["total"], 18)

    def test_a_refused_provider_answer_keeps_its_status_code_and_never_its_body(self):
        run = Run(self.root, transport=Transport(statuses={"/auth/v1/admin/users": 401}))
        self.assertEqual(run.code, 1)
        self.assertEqual(run.record["sources"]["identity"], {"status": "unavailable", "code": "http_401",
                                                             "reference": "supabase-secret"})
        self.assertEqual(run.record["counts"]["billing"]["checkout_sessions_started"], 2)

    def test_raw_content_is_refused_from_the_record_text(self):
        for text in ("person@fixture.example", "key " + BILLING_VALUE, "cus_" + "A" * 14, "Bearer token"):
            with self.subTest(text=text):
                with self.assertRaises(tool.Refusal):
                    tool.refuse_raw_content(text, [BILLING_VALUE])
        tool.refuse_raw_content(json.dumps({"reference": "supabase-secret", "total": 18}), [BILLING_VALUE])

    def test_provider_times_are_read_in_every_shape_the_providers_use(self):
        self.assertEqual(tool.parse_time("2026-09-24T10:34:04.901234567Z"), datetime(2026, 9, 24, 10, 34, 4, 901234, tzinfo=UTC))
        self.assertEqual(tool.parse_time("2026-09-20T13:31:44Z"), datetime(2026, 9, 20, 13, 31, 44, tzinfo=UTC))
        # The identity provider sends a variable number of fractional digits; the real run of
        # September 26, 2026 left two accounts undated until these shapes were read.
        self.assertEqual(tool.parse_time("2026-09-24T10:34:04.90123+00:00"), datetime(2026, 9, 24, 10, 34, 4, 901230, tzinfo=UTC))
        self.assertEqual(tool.parse_time("2026-09-24T10:34:04.9Z"), datetime(2026, 9, 24, 10, 34, 4, 900000, tzinfo=UTC))
        self.assertEqual(tool.parse_time("2026-09-24 10:34:04.12+00:00"), datetime(2026, 9, 24, 10, 34, 4, 120000, tzinfo=UTC))
        self.assertEqual(tool.parse_time("2026-09-20T09:31:44-04:00"), datetime(2026, 9, 20, 13, 31, 44, tzinfo=UTC))
        self.assertEqual(tool.parse_time(1790423653), datetime(2026, 9, 26, 11, 54, 13, tzinfo=UTC))
        for unreadable in (None, "", "yesterday", True, {"at": 1}):
            self.assertIsNone(tool.parse_time(unreadable))

    def test_the_repository_manifest_names_both_references(self):
        manifest = tool.load_manifest()
        for reference in tool.CREDENTIAL_REFERENCES:
            binding = tool.credential_binding(reference, manifest)
            self.assertTrue(binding.environment_name.isupper())
            self.assertTrue(binding.prefixes)
        self.assertEqual(tool.identity_origin(tool.credential_binding("supabase-secret", manifest)),
                         "https://" + manifest["api_keys"]["supabase-secret"]["account"] + ".supabase.co")
        with self.assertRaises(tool.Refusal):
            tool.credential_binding("stripe-live", {"record_type": "operator_credential_references/v1", "api_keys": {}})

    def test_the_cron_entry_runs_every_monday_at_six_ten_utc_in_the_shape_of_the_other_entries(self):
        entry = tool.cron_entry()
        self.assertTrue(entry.startswith("10 1,2 * * 1 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "))
        self.assertIn(" bash -lc '[ \"$(date -u +\\%H)\" = 06 ] || exit 0; R=/home/username/loop-engine; ", entry)
        self.assertIn('[ -f "$R/tools/weekly_number.py" ] || R=/home/username/.le-agent-weekly-number; cd "$R" && ', entry)
        self.assertIn("/home/username/loop-engine/.venv/bin/python tools/weekly_number.py'", entry)
        self.assertTrue(entry.endswith(" >> /home/username/.le-ci-tmp/weekly-number-cron.log 2>&1"))
        self.assertEqual(entry.count("'"), 2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tool.main(["--print-cron"]), 0)
        self.assertEqual(out.getvalue().strip(), entry)


if __name__ == "__main__":
    unittest.main()
