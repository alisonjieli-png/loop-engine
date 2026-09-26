"""The weekly number: accounts, subscriptions, checkout sessions, packages served and cycle times (roadmap S-6.204).

One read-only command turns the counts-only measurement of September 25,
2026 into a dated record. It reads:

- accounts made and confirmed, from the identity provider's administration
  interface (credential reference supabase-secret);
- paying subscriptions, customers and checkout sessions, from the live
  billing account (credential reference stripe-live), with read requests
  only, so no charge and no change can happen;
- packages served and the active catalogue release, from the public health
  and capabilities records of the live service;
- the release cycle times from the pilot-release records in this repository
  and the library cycle times from the daily job's folders on this machine.

Credentials come only through tools/operator_credentials.py. The command
runs under `operator_credentials.py run --ref stripe-live --ref
supabase-secret`, which places the values in its environment, or it resolves
them itself from the system keyring through the same module. No value is
printed and none enters the record. A missing credential refuses the whole
run before any request and names the reference, never the value.

The record holds counts and dates only: no address, no customer identifier
and no raw provider answer. Every count that may mix engineering's own
check journeys with customer accounts carries a mark that says so. A funnel
rate is presented as measured only when its sources hold a full week of data;
until then the record says how many days exist.

Current behaviour: the counts and cycle times above, one dated record under
artifacts/weekly-number and one plain table. Planned and not in this command:
the visitor count (a request counter with a retention rule) and the staff
page that shows the week and its trend.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
RECORD_TYPE = "weekly_number/v1"
IDENTITY_REFERENCE = "supabase-secret"
BILLING_REFERENCE = "stripe-live"
CREDENTIAL_REFERENCES = (IDENTITY_REFERENCE, BILLING_REFERENCE)
PUBLIC_ORIGIN = "https://baltor.ai"
BILLING_ORIGIN = "https://api.stripe.com"
IDENTITY_HOST_SUFFIX = ".supabase.co"
IDENTITY_USERS_PATH = "/auth/v1/admin/users"
HEALTH_PATH, CAPABILITIES_PATH = "/api/v1/health", "/api/v1/capabilities"
RELEASE_RECORDS = ROOT / "artifacts/architecture-audit-2026-09-19"
RELEASE_RECORD_TYPE = "deployment_evidence/v1"
LIBRARY_DAILY = Path("/home/username/baltor-library/daily")
LIBRARY_COUNTS_TYPES = ("daily_library_release_counts/v1", "daily_library_release_counts/v2")
OUTPUT_FOLDER = ROOT / "artifacts/weekly-number"
WINDOW_DAYS = 7
IDENTITY_PAGE_SIZE = 1000
BILLING_PAGE_SIZE = 100
MAXIMUM_PAGES = 50
MAXIMUM_RESPONSE_BYTES = 8_000_000
TIMEOUT_SECONDS = 30
#: The live journey checks make their accounts with this local-part prefix
#: (tools/check_live_account_journeys.mjs). Other engineering accounts cannot
#: be told apart from customers by their fields, so the count stays marked.
CHECK_JOURNEY_PREFIX = "baltor-check-"
PAYING_STATUSES = ("active", "trialing", "past_due")
SESSION_STATUSES = ("open", "complete", "expired")
#: The ninety-day plan of September 25, 2026 assumed these until measured.
PLAN_ASSUMED_PERCENT = {"visitors_to_accounts": 2, "accounts_to_paying": 10}
MIXED_COUNT_ROWS = ("accounts", "billing")
ACCOUNTS_NOTE = ("The identity provider holds customer accounts, the owner's and engineering's own accounts and "
                 "the accounts the live journey checks make. Accounts whose address starts with " + CHECK_JOURNEY_PREFIX
                 + " are counted apart; the rest cannot be told apart by their fields.")
BILLING_NOTE = ("The live billing account holds every checkout session and subscription, including the ones "
                "engineering started to prove the live checkout on September 21, 2026; a session or customer made "
                "by a check cannot be told apart from a customer by its fields.")
VISITORS_NOTE = "No visitor count exists. The request counter with its retention rule is planned work under S-6.204."
NOT_IN_THIS_COMMAND = ("the visitor count: requests to customer pages by distinct address, metadata only, "
                       "kept under the retention rule",
                       "the staff page that shows the week and its trend; the record is written for it")
CRON_LOG = "/home/username/.le-ci-tmp/weekly-number-cron.log"
CRON_TMP = "/home/username/.le-ci-tmp/weekly-number"
CRON_FALLBACK_TREE = "/home/username/.le-agent-weekly-number"
RAW_CONTENT_PATTERNS = (r"@", r"\b(?:sk|rk|pk)_(?:live|test)_", r"\bsb_(?:secret|publishable)_", r"\bsbp_",
                        r"\bwhsec_", r"\b(?:cus|sub|cs|pi|price|prod|acct)_[A-Za-z0-9]{8,}", r"Bearer ")


class Refusal(Exception):
    """A typed refusal: one code and the reference or field it names, never a value."""

    def __init__(self, code, **fields):
        super().__init__(code)
        self.code, self.fields = code, fields

    def __str__(self):
        return "refused: " + self.code + "".join(f" {name}={value}" for name, value in self.fields.items())


class SourceFailure(Exception):
    """One source could not be read. The record keeps the code, never the provider's body."""


# Time.

def parse_time(value):
    """A provider or record time as an aware UTC datetime; None when unreadable."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    match = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\.(\d+))?(.*)$", text)
    if match:
        # Providers send any number of fractional digits; Python 3.10 reads exactly six.
        fraction = (match.group(2) or "").ljust(6, "0")[:6]
        text = match.group(1) + "." + fraction + match.group(3)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_of(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d")


def minutes_between(start, end):
    if start is None or end is None or end < start:
        return None
    return round((end - start).total_seconds() / 60, 1)


def summary(values):
    """Median, smallest and largest of the known values, with how many were known."""
    known = [value for value in values if isinstance(value, (int, float))]
    if not known:
        return {"known": 0}
    return {"known": len(known), "median": round(statistics.median(known), 1), "min": min(known), "max": max(known)}


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    def holds(self, moment):
        return moment is not None and self.start <= moment < self.end

    def as_record(self):
        return {"from": iso(self.start), "to": iso(self.end), "days": WINDOW_DAYS}


# Transport: reads only, no redirects, no proxies, bounded answers.

class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def http_transport(method, url, headers):
    """One bounded request; returns the status, the headers and the body bytes."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())
    selected = urllib.request.Request(url, headers=headers, method=method)
    try:
        with opener.open(selected, timeout=TIMEOUT_SECONDS) as response:
            return response.status, dict(response.headers), response.read(MAXIMUM_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        with error:
            return error.code, dict(error.headers), b""
    except (urllib.error.URLError, TimeoutError, OSError):
        raise SourceFailure("connection_failed") from None


def request(transport, method, url, headers):
    """Send one read. Anything but a GET over HTTPS is refused before the transport is asked."""
    if method != "GET":
        raise Refusal("write_request_refused", method=method)
    if urllib.parse.urlsplit(url).scheme != "https":
        raise Refusal("insecure_origin_refused")
    status, response_headers, body = transport(method, url, dict(headers))
    if len(body) > MAXIMUM_RESPONSE_BYTES:
        raise SourceFailure("response_too_large")
    if status != 200:
        raise SourceFailure("http_" + str(status))
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise SourceFailure("answer_not_json") from None
    return value, {str(name).lower(): value for name, value in response_headers.items()}


# Credentials: references and environment names only.

@dataclass(frozen=True)
class CredentialBinding:
    reference: str
    environment_name: str
    prefixes: tuple
    pattern: str | None
    account: str


def load_manifest():
    import operator_credentials
    return operator_credentials.references()


def credential_binding(reference, manifest):
    entries = manifest.get("api_keys") if isinstance(manifest, dict) else None
    spec = entries.get(reference) if isinstance(entries, dict) else None
    if not isinstance(spec, dict) or not isinstance(spec.get("environment"), str) or not spec["environment"]:
        raise Refusal("credential_reference_unknown", reference=reference)
    return CredentialBinding(reference, spec["environment"], tuple(spec.get("required_prefixes") or ()),
                             spec.get("value_pattern"), str(spec.get("account") or ""))


def accepted_shape(value, binding):
    if not isinstance(value, str) or not value or not value.isascii() or re.search(r"[\x00-\x1f\x7f]", value):
        return False
    if binding.prefixes and not any(value.startswith(prefix) for prefix in binding.prefixes):
        return False
    try:
        return binding.pattern is None or re.fullmatch(binding.pattern, value) is not None
    except re.error:
        return False


def keyring_resolver(reference):
    """The value from the system keyring through operator_credentials, or None with a reason."""
    try:
        import operator_credentials
        return operator_credentials.resolve(reference), ""
    except Exception as error:  # noqa: BLE001 - the helper's sanitized code is the only detail kept
        code = str(error) if error.__class__.__name__ == "CredentialError" else "keyring_unavailable"
        return None, code


def resolve_credentials(manifest, environment, resolver):
    """Every reference must resolve before any request; the refusal names the reference and its variable."""
    values = {}
    for reference in CREDENTIAL_REFERENCES:
        binding = credential_binding(reference, manifest)
        value, reason = environment.get(binding.environment_name) or None, "not_in_environment"
        if value is None:
            value, reason = resolver(reference)
        if not isinstance(value, str) or not value:
            raise Refusal("credential_missing", reference=reference, environment=binding.environment_name,
                          reason=reason or "not_in_environment",
                          hint="run under tools/operator_credentials.py run --ref " + " --ref ".join(CREDENTIAL_REFERENCES))
        if not accepted_shape(value, binding):
            raise Refusal("credential_shape_refused", reference=reference, environment=binding.environment_name)
        values[reference] = (value, binding)
    return values


# Identity: accounts made and confirmed.

def is_check_journey(address):
    return isinstance(address, str) and address.lower().startswith(CHECK_JOURNEY_PREFIX)


def identity_origin(binding):
    if not re.fullmatch(r"[a-z0-9]{20}", binding.account):
        raise SourceFailure("identity_project_reference_unreadable")
    return "https://" + binding.account + IDENTITY_HOST_SUFFIX


def read_identity(transport, credential, binding, window):
    """Every account, page by page.

    The provider names the whole count in a header and may cap a page below
    the size asked for, so the listing follows that total. Without the header
    only an empty page ends it, since a short page could be the provider's own
    cap. A row seen twice, when an account made between two reads shifts the
    listing by one, is counted once. A listing shorter than the reported total
    is refused rather than recorded as a smaller number.
    """
    headers = {"apikey": credential, "Authorization": "Bearer " + credential, "Accept": "application/json"}
    origin, users, seen, requests, reported_total = identity_origin(binding), [], set(), 0, None
    for page in range(1, MAXIMUM_PAGES + 1):
        url = f"{origin}{IDENTITY_USERS_PATH}?page={page}&per_page={IDENTITY_PAGE_SIZE}"
        body, answer_headers = request(transport, "GET", url, headers)
        requests += 1
        rows = body.get("users") if isinstance(body, dict) else body
        if not isinstance(rows, list):
            raise SourceFailure("answer_shape_unreadable")
        count = answer_headers.get("x-total-count")
        if reported_total is None and isinstance(count, str) and count.strip().isdigit():
            reported_total = int(count.strip())
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = row.get("id")
            if isinstance(key, str) and key:
                if key in seen:
                    continue
                seen.add(key)
            users.append(row)
        if not rows or (reported_total is not None and len(users) >= reported_total):
            break
    else:
        raise SourceFailure("too_many_pages")
    counts = account_counts(users, window)
    counts["reported_total"] = reported_total
    if reported_total is not None and counts["total"] < reported_total:
        raise SourceFailure("listing_shorter_than_the_reported_total")
    return counts, requests


def account_counts(users, window):
    counts = {"total": 0, "confirmed": 0, "deleted": 0, "made_this_week": 0, "confirmed_this_week": 0,
              "check_journey_total": 0, "check_journey_confirmed": 0, "check_journey_this_week": 0,
              "unreadable_dates": 0}
    made_by_day, confirmed_by_day, earliest = {}, {}, None
    for user in users:
        made, confirmed = parse_time(user.get("created_at")), parse_time(user.get("email_confirmed_at"))
        check = is_check_journey(user.get("email"))
        counts["total"] += 1
        counts["deleted"] += int(bool(user.get("deleted_at")))
        counts["check_journey_total"] += int(check)
        if made is None:
            counts["unreadable_dates"] += 1
        else:
            made_by_day[day_of(made)] = made_by_day.get(day_of(made), 0) + 1
            earliest = made if earliest is None or made < earliest else earliest
            if window.holds(made):
                counts["made_this_week"] += 1
                counts["check_journey_this_week"] += int(check)
        if confirmed is not None:
            counts["confirmed"] += 1
            counts["check_journey_confirmed"] += int(check)
            confirmed_by_day[day_of(confirmed)] = confirmed_by_day.get(day_of(confirmed), 0) + 1
            counts["confirmed_this_week"] += int(window.holds(confirmed))
    return {**counts, "made_by_day": dict(sorted(made_by_day.items())),
            "confirmed_by_day": dict(sorted(confirmed_by_day.items())),
            "data_start": iso(earliest) if earliest else None,
            "mixes_test_journeys": True, "note": ACCOUNTS_NOTE}


# Billing: reads only.

def read_billing(transport, credential, window):
    headers = {"Authorization": "Bearer " + credential, "Accept": "application/json"}
    requests = 0

    def listing(path, query):
        nonlocal requests
        rows, after = [], None
        for _page in range(MAXIMUM_PAGES):
            fields = dict(query, limit=BILLING_PAGE_SIZE)
            if after:
                fields["starting_after"] = after
            body, _headers = request(transport, "GET", BILLING_ORIGIN + path + "?" + urllib.parse.urlencode(fields), headers)
            requests += 1
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
                raise SourceFailure("answer_shape_unreadable")
            if any(row.get("livemode") is not True for row in data):
                raise SourceFailure("sandbox_row_in_live_answer")
            rows.extend(data)
            if not body.get("has_more"):
                return rows
            after = data[-1].get("id") if data else None
            if not isinstance(after, str) or not after:
                raise SourceFailure("pagination_cursor_unreadable")
        raise SourceFailure("too_many_pages")

    subscriptions = listing("/v1/subscriptions", {"status": "all"})
    customers = listing("/v1/customers", {})
    sessions = listing("/v1/checkout/sessions", {})
    return billing_counts(subscriptions, customers, sessions, window), requests


def billing_counts(subscriptions, customers, sessions, window):
    by_status, earliest = {}, None
    for row in subscriptions:
        status = str(row.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    sessions_by_status = {status: 0 for status in SESSION_STATUSES}
    counts = {"paying_subscriptions": sum(by_status.get(status, 0) for status in PAYING_STATUSES),
              "subscriptions_total": len(subscriptions), "subscriptions_by_status": dict(sorted(by_status.items())),
              "customers_total": len(customers), "customers_this_week": 0,
              "checkout_sessions_started": len(sessions), "checkout_sessions_finished": 0,
              "checkout_sessions_started_this_week": 0, "checkout_sessions_finished_this_week": 0}
    for row in subscriptions + customers + sessions:
        made = parse_time(row.get("created"))
        earliest = made if made is not None and (earliest is None or made < earliest) else earliest
    for row in customers:
        counts["customers_this_week"] += int(window.holds(parse_time(row.get("created"))))
    for row in sessions:
        status, made = str(row.get("status") or "unknown"), parse_time(row.get("created"))
        sessions_by_status[status] = sessions_by_status.get(status, 0) + 1
        finished = status == "complete"
        counts["checkout_sessions_finished"] += int(finished)
        counts["checkout_sessions_started_this_week"] += int(window.holds(made))
        counts["checkout_sessions_finished_this_week"] += int(finished and window.holds(made))
    counts["checkout_sessions_by_status"] = sessions_by_status
    counts["data_start"] = iso(earliest) if earliest else None
    counts["paying_statuses"] = list(PAYING_STATUSES)
    counts["mixes_test_journeys"] = True
    counts["note"] = BILLING_NOTE
    return counts


# The public records of the live service.

def result_of(body):
    if isinstance(body, dict) and body.get("record_type") == "service_http_result/v1":
        return body.get("result") if isinstance(body.get("result"), dict) else {}
    return body if isinstance(body, dict) else {}


def read_public(transport, origin):
    health = result_of(request(transport, "GET", origin + HEALTH_PATH, {"Accept": "application/json"})[0])
    capabilities = result_of(request(transport, "GET", origin + CAPABILITIES_PATH, {"Accept": "application/json"})[0])
    if health.get("record_type") != "service_health/v2" or capabilities.get("record_type") != "service_capabilities/v1":
        raise SourceFailure("record_type_unreadable")
    release = health.get("catalogue_release") if isinstance(health.get("catalogue_release"), dict) else {}
    library = capabilities.get("library") if isinstance(capabilities.get("library"), dict) else {}
    website = capabilities.get("website") if isinstance(capabilities.get("website"), dict) else {}
    billing = capabilities.get("billing") if isinstance(capabilities.get("billing"), dict) else {}
    built = parse_time(release.get("built_at"))
    return {"packages_served": library.get("served_items"), "active_release_id": release.get("release_id"),
            "content_digest": release.get("content_digest"), "items_in_release": release.get("items"),
            "withdrawn_left_out": release.get("withdrawn_left_out"), "built_at": iso(built) if built else None,
            "catalogue_state_revision": release.get("catalogue_state_revision"),
            "service_ready": health.get("ready") is True,
            "registration_available": website.get("registration_available") is True,
            "checkout_available": billing.get("checkout") is True,
            "mixes_test_journeys": False,
            "note": "Public records, no account involved. The served count is the active release's item count."}, 2


# Release cycle times from the pilot-release records.

def git_commit_time(revision, repository=ROOT):
    try:
        completed = subprocess.run(["git", "-C", str(repository), "show", "-s", "--format=%ct", revision],
                                   capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = completed.stdout.strip().splitlines()
    if completed.returncode != 0 or not lines or not lines[0].strip().isdigit():
        return None
    return datetime.fromtimestamp(int(lines[0].strip()), timezone.utc)


def read_releases(folder, window, commit_time=git_commit_time):
    rows = []
    for path in sorted(folder.glob("pilot-release-*.json")):
        try:
            record = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(record, dict) or record.get("record_type") != RELEASE_RECORD_TYPE:
            continue
        deployed = parse_time(record.get("deployed_at"))
        if deployed is None:
            continue
        revision = record.get("source_revision")
        committed = commit_time(revision) if isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{7,64}", revision) else None
        failed = record.get("failed_first_attempts")
        rows.append({"fly_release": record.get("fly_release"), "deployed_at": iso(deployed),
                     "source_revision": revision[:12] if isinstance(revision, str) else None,
                     "commit_to_live_minutes": minutes_between(committed, deployed),
                     "failed_first_attempts": len(failed) if isinstance(failed, list) else None,
                     "_deployed": deployed})
    this_week = [row for row in rows if window.holds(row["_deployed"])]
    failed_known = [row["failed_first_attempts"] for row in this_week if row["failed_first_attempts"] is not None]
    numbers = [row["fly_release"] for row in rows if isinstance(row["fly_release"], int)]
    return {"records_read": len(rows), "latest_release": max(numbers) if numbers else None,
            "count_this_week": len(this_week),
            "commit_to_live_minutes": summary([row["commit_to_live_minutes"] for row in this_week]),
            "failed_first_attempts_this_week": sum(failed_known),
            "releases_with_failed_first_attempts_recorded": len(failed_known),
            "releases_this_week": [{name: value for name, value in row.items() if not name.startswith("_")}
                                   for row in this_week]}


# Library cycle times from the daily job's folders.

def folder_birth_time(folder):
    """The folder's creation time from the file system, which the daily job makes at its start."""
    try:
        completed = subprocess.run(["stat", "-c", "%W", str(folder)], capture_output=True, text=True,
                                   timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = completed.stdout.strip()
    if completed.returncode != 0 or not text.isdigit() or int(text) <= 0:
        return None
    return datetime.fromtimestamp(int(text), timezone.utc)


def read_journal(path):
    """The stages the daily job finished, in order, with their times."""
    finished = []
    try:
        lines = path.read_text("utf-8").splitlines()
    except OSError:
        return finished
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("note") == "done" and isinstance(entry.get("stage"), str):
            moment = parse_time(entry.get("at"))
            if moment is not None:
                finished.append((entry["stage"], moment))
    return finished


def read_library(folder, window, birth_time=folder_birth_time):
    slots = []
    for counts_path in sorted(folder.glob("*/counts.json")):
        slot = counts_path.parent
        try:
            counts = json.loads(counts_path.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(counts, dict) or counts.get("record_type") not in LIBRARY_COUNTS_TYPES:
            continue
        stages = read_journal(slot / "journal.jsonl")
        done = {stage: moment for stage, moment in stages}
        born = birth_time(slot)
        started = born or (stages[0][1] if stages else None)
        finished = done.get("counts") or (stages[-1][1] if stages else None)
        stage_minutes, previous = {}, started
        for stage, moment in stages:
            stage_minutes[stage] = minutes_between(previous, moment)
            previous = moment
        slots.append({"slot": counts.get("day"), "started_at": iso(started) if started else None,
                      "start_source": "folder_birth_time" if born else "first_journal_entry",
                      "served_at": iso(done["publish"]) if "publish" in done else None,
                      "finished_at": iso(finished) if finished else None,
                      "start_to_served_minutes": minutes_between(started, done.get("publish")),
                      "start_to_finished_minutes": minutes_between(started, finished),
                      "review_minutes": minutes_between(done.get("calibrate"), done.get("review")),
                      "stage_minutes": stage_minutes,
                      **{name: counts.get(name) for name in ("exported", "passed_prechecks", "reviewed", "review_calls",
                                                              "approved", "rejected", "left_out")},
                      "published": counts.get("published") is True, "checked_live": counts.get("checked_live") is True,
                      "_finished": finished})
    this_week = [slot for slot in slots if window.holds(slot["_finished"])]

    def total(name):
        return sum(slot[name] for slot in this_week if isinstance(slot.get(name), int))

    return {"slots_read": len(slots), "count_this_week": len(this_week),
            "exported_this_week": total("exported"), "approved_this_week": total("approved"),
            "rejected_this_week": total("rejected"),
            "published_this_week": sum(1 for slot in this_week if slot["published"]),
            "checked_live_this_week": sum(1 for slot in this_week if slot["checked_live"]),
            "start_to_served_minutes": summary([slot["start_to_served_minutes"] for slot in this_week]),
            "review_minutes": summary([slot["review_minutes"] for slot in this_week]),
            "slots_this_week": [{name: value for name, value in slot.items() if not name.startswith("_")}
                                for slot in this_week]}


# Funnel rates, presented as measured only after a week of data.

def days_of_data(window, *starts):
    parsed = [parse_time(start) for start in starts]
    if not parsed or any(moment is None for moment in parsed):
        return 0
    return max(0, min((window.end - moment).days for moment in parsed))


def rate_entry(days, numerator, denominator, assumed=None):
    entry = {"days_of_data": days, "numerator": numerator, "denominator": denominator}
    if assumed is not None:
        entry["assumed_in_plan_percent"] = assumed
    if numerator is None or denominator is None:
        entry.update(status="not_measured", reason="a source was unavailable")
    elif days < WINDOW_DAYS:
        entry.update(status="not_measured",
                     reason=f"{days} days of data; a rate is presented as measured only after {WINDOW_DAYS} days")
    elif not denominator:
        entry.update(status="measured", percent=None, reason="nothing to divide by")
    else:
        entry.update(status="measured", percent=round(100 * numerator / denominator, 1))
    return entry


def funnel_rates(accounts, billing, window):
    rates = {"visitors_to_accounts": {"status": "not_measured", "days_of_data": 0, "reason": VISITORS_NOTE,
                                      "assumed_in_plan_percent": PLAN_ASSUMED_PERCENT["visitors_to_accounts"]}}
    accounts = accounts if isinstance(accounts, dict) and accounts.get("status") != "unavailable" else None
    billing = billing if isinstance(billing, dict) and billing.get("status") != "unavailable" else None
    identity_days = days_of_data(window, accounts["data_start"]) if accounts else 0
    billing_days = days_of_data(window, billing["data_start"]) if billing else 0
    customers = (accounts["confirmed"] - accounts["check_journey_confirmed"]) if accounts else None
    rates["accounts_to_paying"] = rate_entry(min(identity_days, billing_days) if accounts and billing else 0,
                                             billing["paying_subscriptions"] if billing else None, customers,
                                             PLAN_ASSUMED_PERCENT["accounts_to_paying"])
    rates["checkout_started_to_finished"] = rate_entry(billing_days,
                                                       billing["checkout_sessions_finished"] if billing else None,
                                                       billing["checkout_sessions_started"] if billing else None)
    return rates


# The named checks the record must pass before it is written.

def refuse_early_rates(rates):
    """A rate presented as measured before a week of data is refused."""
    for name, entry in rates.items():
        if entry.get("status") == "measured" and int(entry.get("days_of_data") or 0) < WINDOW_DAYS:
            raise Refusal("rate_presented_before_a_week_of_data", rate=name, days=entry.get("days_of_data"))


def refuse_unmarked_mixed_counts(record):
    """A count that may mix check journeys with customer accounts must carry its mark."""
    counts = record.get("counts") if isinstance(record, dict) else None
    for name in MIXED_COUNT_ROWS:
        row = counts.get(name) if isinstance(counts, dict) else None
        if not isinstance(row, dict) or row.get("status") == "unavailable":
            continue
        if row.get("mixes_test_journeys") is not True or not isinstance(row.get("note"), str) or not row["note"]:
            raise Refusal("mixed_count_without_a_mark", count=name)


def refuse_raw_content(text, values=()):
    """Neither a credential nor an address nor a provider identifier may enter the record."""
    for value in values:
        if value and value in text:
            raise Refusal("credential_in_record")
    for pattern in RAW_CONTENT_PATTERNS:
        if re.search(pattern, text):
            raise Refusal("raw_content_in_record", pattern=pattern)


# The record.

def read_source(name, reader, sources):
    try:
        counts, requests = reader()
    except SourceFailure as failure:
        sources[name] = {"status": "unavailable", "code": str(failure)}
        return {"status": "unavailable", "code": str(failure)}
    except Refusal as refusal:
        sources[name] = {"status": "unavailable", "code": refusal.code}
        return {"status": "unavailable", "code": refusal.code}
    sources[name] = {"status": "read", "requests": requests}
    return counts


def measure(credentials, transport, window, now, *, origin=PUBLIC_ORIGIN, release_records=RELEASE_RECORDS,
            library_daily=LIBRARY_DAILY, previous_records=(), commit_time=git_commit_time,
            birth_time=folder_birth_time):
    identity_value, identity_binding = credentials[IDENTITY_REFERENCE]
    billing_value, _billing_binding = credentials[BILLING_REFERENCE]
    sources = {}
    accounts = read_source("identity", lambda: read_identity(transport, identity_value, identity_binding, window), sources)
    sources["identity"]["reference"] = IDENTITY_REFERENCE
    billing = read_source("billing", lambda: read_billing(transport, billing_value, window), sources)
    sources["billing"].update(reference=BILLING_REFERENCE, write_requests=0, charges_made=0)
    public = read_source("public", lambda: read_public(transport, origin), sources)
    sources["public"]["origin"] = origin
    try:
        releases = read_releases(release_records, window, commit_time)
        sources["releases"] = {"status": "read", "records": releases["records_read"],
                               "folder": str(release_records.relative_to(ROOT)) if release_records.is_relative_to(ROOT)
                               else str(release_records)}
    except OSError as error:
        releases = {"status": "unavailable", "code": error.__class__.__name__}
        sources["releases"] = {"status": "unavailable", "code": error.__class__.__name__}
    try:
        library = read_library(library_daily, window, birth_time)
        sources["library"] = {"status": "read", "slots": library["slots_read"], "folder": str(library_daily)}
    except OSError as error:
        library = {"status": "unavailable", "code": error.__class__.__name__}
        sources["library"] = {"status": "unavailable", "code": error.__class__.__name__}
    complete = all(row.get("status") == "read" for row in sources.values())
    return {"record_type": RECORD_TYPE, "recorded_at": iso(now), "window": window.as_record(),
            "complete": complete, "sources": sources,
            "counts": {"accounts": accounts, "billing": billing, "library": public,
                       "visitors": {"status": "not_measured", "reason": VISITORS_NOTE}},
            "cycle_times": {"releases": releases, "library": library},
            "funnel_rates": funnel_rates(accounts, billing, window),
            "no_raw_content": True, "credential_printed": False, "physical_model_calls": 0,
            "previous_records": list(previous_records), "not_in_this_command": list(NOT_IN_THIS_COMMAND),
            "measured_by": "tools/weekly_number.py"}


def new_record_path(folder, moment):
    folder.mkdir(parents=True, exist_ok=True)
    stem = "weekly-number-" + day_of(moment)
    for index in range(1, 1000):
        candidate = folder / f"{stem}-{index}.json"
        if not candidate.exists():
            return candidate
    raise Refusal("no_free_record_name", folder=str(folder))


def existing_records(folder):
    try:
        return sorted(path.name for path in folder.glob("weekly-number-*.json"))
    except OSError:
        return []


# The table.

def _cell(value):
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.1f}"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return str(value)


def table(record):
    counts, cycles, rates = record["counts"], record["cycle_times"], record["funnel_rates"]
    accounts, billing, library = counts["accounts"], counts["billing"], counts["library"]
    releases, slots = cycles["releases"], cycles["library"]
    rows = []

    def row(measure, week, all_time, note):
        rows.append((measure, _cell(week), _cell(all_time), note))

    if accounts.get("status") == "unavailable":
        row("accounts", None, None, "unavailable: " + accounts["code"])
    else:
        row("accounts made", accounts["made_this_week"], accounts["total"],
            f"mixed: {accounts['check_journey_total']} match the check journey prefix"
            + (f"; {accounts['deleted']} marked deleted and still listed" if accounts.get("deleted") else ""))
        row("accounts confirmed", accounts["confirmed_this_week"], accounts["confirmed"], "mixed")
    if billing.get("status") == "unavailable":
        row("billing", None, None, "unavailable: " + billing["code"])
    else:
        row("paying subscriptions", None, billing["paying_subscriptions"], "mixed; active, trialing or past due")
        row("customers", billing["customers_this_week"], billing["customers_total"], "mixed")
        row("checkout sessions started", billing["checkout_sessions_started_this_week"],
            billing["checkout_sessions_started"], "mixed")
        row("checkout sessions finished", billing["checkout_sessions_finished_this_week"],
            billing["checkout_sessions_finished"], "mixed")
    if library.get("status") == "unavailable":
        row("packages served", None, None, "unavailable: " + library["code"])
    else:
        release = str(library.get("active_release_id") or "")[:8]
        row("packages served", None, library["packages_served"],
            f"release {release}, built {library.get('built_at') or '-'}")
    if releases.get("status") == "unavailable":
        row("releases to Fly", None, None, "unavailable: " + releases["code"])
    else:
        minutes = releases["commit_to_live_minutes"]
        note = (f"commit to live median {minutes['median']} minutes over {minutes['known']}"
                if minutes.get("known") else "commit to live unknown")
        row("releases to Fly", releases["count_this_week"], releases["records_read"],
            f"{note}; {releases['failed_first_attempts_this_week']} failed first attempts")
    if slots.get("status") == "unavailable":
        row("library slots run", None, None, "unavailable: " + slots["code"])
    else:
        minutes = slots["start_to_served_minutes"]
        note = (f"start to served median {minutes['median']} minutes over {minutes['known']}"
                if minutes.get("known") else "start to served unknown")
        row("library slots run", slots["count_this_week"], slots["slots_read"],
            f"{note}; {slots['approved_this_week']} approved this week")
    row("visitors", None, None, "not measured: no request counter exists")
    for name, entry in rates.items():
        if entry.get("status") == "measured":
            note = f"measured over {entry['days_of_data']} days of data"
            row("rate " + name.replace("_", " "), None, f"{entry['percent']} percent" if entry.get("percent") is not None
                else "no denominator", note)
        else:
            row("rate " + name.replace("_", " "), None, None, "not measured: " + entry.get("reason", ""))
    widths = [max(len(line[index]) for line in [("measure", "this week", "all time", "note")] + rows) for index in range(3)]
    lines = [f"Weekly number, window {record['window']['from']} to {record['window']['to']} "
             f"({record['window']['days']} days), recorded {record['recorded_at']}"
             + ("" if record["complete"] else ", INCOMPLETE: a source was unavailable")]
    header = ("measure", "this week", "all time", "note")
    for line in [header] + rows:
        lines.append(f"{line[0]:<{widths[0]}}  {line[1]:>{widths[1]}}  {line[2]:>{widths[2]}}  {line[3]}")
    return "\n".join(lines)


# The cron entry.

def cron_entry(repository="/home/username/loop-engine", fallback=CRON_FALLBACK_TREE):
    """The crontab line for every Monday at 06:10 UTC.

    cron on this machine runs in the system's local time (America/New_York) and
    has no time zone of its own for an entry, so the entry fires at 01:10 and
    02:10 local time on Mondays and a guard lets only the run at 06:10 UTC go
    on, through both daylight saving settings. This is the pattern the cron
    manual gives for a task in another time zone. The command runs from the
    shared checkout once the tool is merged there, and from the worktree that
    wrote it until then, in the shape of the quickstart check's entry.
    """
    python = repository + "/.venv/bin/python"
    command = (f'[ "$(date -u +\\%H)" = 06 ] || exit 0; R={repository}; [ -f "$R/tools/weekly_number.py" ] || R={fallback}; '
               f'cd "$R" && echo "$(date -u +\\%FT\\%TZ) $R" && {python} tools/weekly_number.py')
    return (f"10 1,2 * * 1 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus TMPDIR={CRON_TMP} bash -lc '{command}'"
            f" >> {CRON_LOG} 2>&1")


def main(argv=None, *, environment=None, transport=None, resolver=None, now=None, manifest=None,
         commit_time=git_commit_time, birth_time=folder_birth_time):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-folder", type=Path, default=OUTPUT_FOLDER)
    parser.add_argument("--release-records", type=Path, default=RELEASE_RECORDS)
    parser.add_argument("--library-daily", type=Path, default=LIBRARY_DAILY)
    parser.add_argument("--origin", default=PUBLIC_ORIGIN)
    parser.add_argument("--print-cron", action="store_true", help="print the crontab line and stop")
    args = parser.parse_args(argv)
    if args.print_cron:
        print(cron_entry())
        return 0
    environment = os.environ if environment is None else environment
    transport = http_transport if transport is None else transport
    resolver = keyring_resolver if resolver is None else resolver
    now = datetime.now(timezone.utc) if now is None else now
    try:
        credentials = resolve_credentials(load_manifest() if manifest is None else manifest, environment, resolver)
    except Refusal as refusal:
        print(str(refusal), file=sys.stderr)
        return 2
    window = Window(now - timedelta(days=WINDOW_DAYS), now)
    record = measure(credentials, transport, window, now, origin=args.origin, release_records=args.release_records,
                     library_daily=args.library_daily, previous_records=existing_records(args.output_folder),
                     commit_time=commit_time, birth_time=birth_time)
    text = json.dumps(record, indent=1) + "\n"
    try:
        refuse_raw_content(text, [value for value, _binding in credentials.values()])
        refuse_unmarked_mixed_counts(record)
        refuse_early_rates(record["funnel_rates"])
        path = new_record_path(args.output_folder, now)
    except Refusal as refusal:
        print(str(refusal), file=sys.stderr)
        return 2
    path.write_text(text, "utf-8")
    print(table(record))
    print("record: " + str(path))
    return 0 if record["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
