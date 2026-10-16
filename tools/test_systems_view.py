"""The staff Systems view shows recorded facts only, to staff only, with every result state kept apart.

Kind: development check over the generated record, its generator, the real service over loopback HTTP and the page
script under Node. It opens no connection outside loopback, calls no provider and needs no credential. Roadmap
S-6.35.11: the systems portal of October 14, 2026 served invented projections and unmeasured pass labels without
access control; this view must label every result by source revision, environment, attempt and record, keep pending,
skipped, failed and unknown checks apart, and refuse anyone who is not staff at the service itself.

Each rule has a known-wrong case beside it:

- the committed record is what the generator writes now, and a changed copy is reported as stale;
- every number of every row and entry is copied from the record the row cites, and an invented number is caught;
- a word the reading table does not name is unknown, never passed, and each of the five states is read as itself;
- every release record and every recorded attempt is kept, earlier failures included;
- the current deployment statement is compared field by field with the newest release record, and a changed
  revision is reported as differing;
- no projection, forecast, revenue or investor word appears, and the generator refuses one;
- a staff role that reads service diagnostics reads the view; signed-out requests, ordinary accounts, a host key, a
  forged header, the analytics role and a signed-out staff session are refused, and removing the role table lets the
  analytics role through;
- the answers are never cached, queries are strict, unavailable evidence is refused rather than filled in, and the
  record is served at no public address;
- the page lists each state in its own list, labels the live reading with its read time, and sends a signed-out answer
  to sign-in.

Run:

    PYTHONPATH=src:tools python -m unittest tools/test_systems_view.py
"""
from __future__ import annotations

from contextlib import ExitStack
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import build_systems_view as tool  # noqa: E402
from loop_engine.core.service_runtime import systems_view, web_pages  # noqa: E402
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

RECORD = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "systems_view.json"
SCHEMA = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "systems_view.schema.json"
SCRIPT = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets" / "systems-view.js"
PAGE = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets" / "index.html"
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")
#: The words the October 14 portal used and this view must never carry.
FORBIDDEN = re.compile(r"\b(?:ARR|MRR|projections?|projected|forecasts?|investors?|revenue|runway|valuation)\b",
                       re.IGNORECASE)


def committed():
    return json.loads(RECORD.read_text("utf-8"))


def numbers(value):
    """Every number a value carries: its numeric fields and every number written in its text."""
    found = []

    def walk(item):
        if isinstance(item, bool) or item is None:
            return
        if isinstance(item, (int, float)):
            found.append(str(item))
        elif isinstance(item, str):
            found.extend(match.group(0).replace(",", "") for match in NUMBER.finditer(item))
        elif isinstance(item, dict):
            for part in item.values():
                walk(part)
        elif isinstance(item, list):
            for part in item:
                walk(part)
    walk(value)
    return found


def invented_numbers(record):
    """(where, number) for each number of a row or entry that the record it cites does not hold."""
    cache = {}

    def source(path):
        if path not in cache:
            raw = (ROOT / path).read_text("utf-8")
            # A record's own path names its folder date, and a number may be written with thousands separators.
            cache[path] = "\n".join((path, raw, raw.replace(",", "")))
        return cache[path]

    problems = []
    for row in record["rows"]:
        text = source(row["evidence"])
        for number in numbers({name: row[name] for name in ("check", "observed", "attempt", "at")}):
            if number not in text:
                problems.append((row["entry"] + row["pointer"], number))
    for entry in record["entries"]:
        texts = [source(entry["evidence"]), *(source(path) for path in entry["also_recorded_in"])]
        for number in numbers({name: entry[name] for name in ("title", "number", "at", "rollback", "edge", "catalogue")}):
            if not any(number in text for text in texts):
                problems.append((entry["id"], number))
    statement = source(record["current_deployment"]["statement"])
    for number in numbers(record["current_deployment"]["stated"]):
        if number not in statement:
            problems.append(("current_deployment", number))
    return problems


def resolve(document, pointer):
    """The value a JSON pointer names in a document, or KeyError."""
    value = document
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


class GeneratedRecord(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.built = tool.build()
        cls.record = committed()

    def test_the_committed_record_is_current(self):
        self.assertEqual(tool.render(self.built), RECORD.read_text("utf-8"),
                         "run python tools/build_systems_view.py and commit the record")
        self.assertEqual(tool.main(["--check"]), 0)

    def test_a_changed_copy_is_reported_as_stale(self):
        with tempfile.TemporaryDirectory(prefix="systems-view-") as folder:
            output = Path(folder) / "systems_view.json"
            output.write_text(tool.render(self.built), "utf-8")
            self.assertEqual(tool.main(["--output", str(output), "--check"]), 0)
            # KNOWN_WRONG: one recorded state edited by hand is a stale record.
            output.write_text(tool.render(self.built).replace('"state": "failed"', '"state": "passed"', 1), "utf-8")
            self.assertEqual(tool.main(["--output", str(output), "--check"]), 1)

    def test_the_record_matches_its_schema_and_the_schema_refuses_known_wrong_records(self):
        tool.validate(self.record)
        schema = SCHEMA.read_text("utf-8")
        value, digest = systems_view.checked_record(RECORD.read_bytes(), schema)
        self.assertEqual(value["record_type"], systems_view.RECORD_TYPE)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        wrong_state = copy.deepcopy(self.record)
        wrong_state["rows"][0]["state"] = "ok"
        no_record = copy.deepcopy(self.record)
        del no_record["rows"][0]["evidence"]
        merged = copy.deepcopy(self.record)
        merged["states"] = ["passed", "not passed"]
        later = dict(self.record, record_type="service_systems_view/v2")
        # KNOWN_WRONG: each record below is refused by the generator and by the service that reads it.
        for name, wrong in (("a state outside the five", wrong_state), ("a row without its record", no_record),
                            ("merged states", merged), ("a later version", later)):
            with self.subTest(name):
                with self.assertRaises(ServiceRuntimeError):
                    systems_view.checked_record(json.dumps(wrong).encode(), schema)
                with self.assertRaises(tool.BuildError):
                    tool.validate(wrong)

    def test_every_release_record_is_an_entry_with_its_copies(self):
        evidence = {entry["evidence"] for entry in self.record["entries"]}
        copies = {path for entry in self.record["entries"] for path in entry["also_recorded_in"]}
        for path in sorted(ROOT.glob(tool.RELEASE_RECORDS)):
            self.assertIn(path.relative_to(ROOT).as_posix(), evidence)
        for path in sorted(ROOT.glob("artifacts/release-[0-9]*/release.json")):
            self.assertIn(path.relative_to(ROOT).as_posix(), evidence | copies)
        numbers_seen = [entry["number"] for entry in self.record["entries"] if entry["kind"] == "application_release"]
        self.assertEqual(len(numbers_seen), len(set(numbers_seen)))
        self.assertTrue({45, 46, 48} <= set(numbers_seen), "releases recorded only in their own folders are kept")

    def test_every_number_is_copied_from_the_record_it_cites(self):
        self.assertEqual(invented_numbers(self.record), [])
        # KNOWN_WRONG: a row that claims more checks than its record holds is caught.
        wrong = copy.deepcopy(self.record)
        row = next(item for item in wrong["rows"] if item["entry"] == "fly-release-93")
        row["observed"] = "Checks: 120117 of 120117"
        self.assertIn(("fly-release-93" + row["pointer"], "120117"), invented_numbers(wrong))

    def test_each_row_names_its_revision_environment_attempt_time_and_record(self):
        fields = {"entry", "check", "state", "observed", "source_revision", "revision_basis", "environment_or_host",
                  "attempt", "at", "evidence", "pointer"}
        entries = {entry["id"] for entry in self.record["entries"]}
        for row in self.record["rows"]:
            with self.subTest(row=row["entry"] + row["pointer"]):
                self.assertEqual(set(row), fields)
                self.assertIn(row["entry"], entries)
                self.assertIn(row["state"], systems_view.STATES)
                self.assertTrue(row["environment_or_host"])
                path = ROOT / row["evidence"]
                self.assertTrue(path.is_file(), row["evidence"])
                if path.suffix == ".json" and row["pointer"]:
                    resolve(json.loads(path.read_text("utf-8")), row["pointer"])

    def test_earlier_attempts_are_kept_beside_later_ones(self):
        rows = self.record["rows"]

        def states(entry, prefix):
            return [row["state"] for row in rows if row["entry"] == entry and row["pointer"].startswith(prefix)]
        self.assertEqual(states("fly-release-93", "/deployment_attempts/"), ["failed", "passed"])
        self.assertEqual(states("fly-release-93", "/edge_attempts/"), ["failed", "failed"])
        self.assertEqual([state for state in (states("fly-release-93", "/checks/live_matrix_attempt_0"))],
                         ["failed", "failed", "failed"])
        self.assertEqual(states("fly-release-8", "/workflow_history/"), ["passed", "failed", "passed"])
        self.assertEqual(len(states("fly-release-93", "/retained_failed_attempts/")),
                         len(json.loads((ROOT / tool.AUDIT / "pilot-release-93.json").read_text())["retained_failed_attempts"]))
        community = [row["state"] for row in rows if row["entry"] == "publication-community-release-2-2026-09-25"]
        self.assertEqual(community, ["failed", "failed", "failed", "passed"])

    def test_each_state_is_read_as_itself_and_an_unnamed_word_is_never_passed(self):
        def state(value, **options):
            found = tool.Readings()
            for readings in tool.read_object(value, **options).values():
                found.extend(readings)
            return tool.worst(found.states)
        self.assertEqual(state({"conclusion": "success"}), "passed")
        self.assertEqual(state({"conclusion": "failure"}), "failed")
        self.assertEqual(state({"conclusion": "planned"}), "pending")
        self.assertEqual(state({"conclusion": "skipped_separately_gated"}), "skipped")
        self.assertEqual(state({"conclusion": "looks_fine"}), "unknown")
        self.assertEqual(state({"passed": 3, "total": 4}), "failed")
        self.assertEqual(state({"passed": 4, "total": 4}), "passed")
        self.assertEqual(state({"passed": None}), "unknown")
        self.assertEqual(state({"passed": 9, "total": None, "all_passed": True}), "passed")
        self.assertEqual(state({"passed": 9, "total": 9, "functional_passed": False}), "failed")
        self.assertEqual(state({"problems": 0}), "passed")
        self.assertEqual(state({"metadata_fetch_errors": 21}), "failed")
        self.assertEqual(state({"viewports": [1440, 390]}), "unknown")
        self.assertEqual(state({"service": [6, 8]}, flat=True), "failed")
        # KNOWN_WRONG: only the reading table turns a word into a state; adding the word changes the reading.
        with mock.patch.dict(tool.WORD_STATES, {"looks_fine": "passed"}):
            self.assertEqual(state({"conclusion": "looks_fine"}), "passed")
        self.assertEqual(self.record["states"], ["passed", "failed", "pending", "skipped", "unknown"])
        self.assertEqual({row["state"] for row in self.record["rows"]} - set(systems_view.STATES), set())

    def test_a_row_whose_environment_is_not_stated_is_never_labelled_production(self):
        not_stated = [row for row in self.record["rows"] if row["environment_or_host"] == tool.NOT_STATED]
        self.assertTrue(not_stated)
        local = [row for row in self.record["rows"] if row["pointer"].startswith("/checks/local_browser")]
        self.assertTrue(local and all(row["environment_or_host"] == tool.LOCAL for row in local))
        hosted = [row for row in self.record["rows"] if row["check"] == "Hosted website acceptance"]
        self.assertTrue(hosted and all(tool.HOSTNAME.match(row["environment_or_host"]) for row in hosted))

    def test_the_current_deployment_statement_is_compared_with_the_newest_release_record(self):
        current = self.record["current_deployment"]
        self.assertEqual(current["newest_release_entry"], "fly-release-93")
        self.assertEqual(set(current["comparison"].values()), {"agrees"})

        class Changed(tool.Builder):
            def statement_text(self, path):
                text = super().statement_text(path)
                return text.replace(current["stated"]["source_revision"], "0" * 40, 1)
        # KNOWN_WRONG: a section that names another revision is reported as differing, not overwritten.
        changed = Changed(ROOT).build()["current_deployment"]
        self.assertEqual(changed["comparison"]["source_revision"], "differs")
        self.assertEqual(changed["comparison"]["release"], "agrees")

    def test_no_projection_forecast_revenue_or_investor_word_appears(self):
        page = PAGE.read_text("utf-8")
        start = page.index('<section data-view="systems"')
        view = page[start:page.index("\n    </section>\n", start)]
        for name, text in (("record", RECORD.read_text("utf-8")), ("page script", SCRIPT.read_text("utf-8")),
                           ("view", view), ("service module", Path(systems_view.__file__).read_text("utf-8"))):
            with self.subTest(name=name):
                self.assertIsNone(FORBIDDEN.search(text))
        # KNOWN_WRONG: the generator refuses a row that carries one of the words.
        builder = tool.Builder(ROOT)
        original = builder.application_release

        def projected(number, held):
            original(number, held)
            if number == 93:
                builder.rows[-1]["observed"] = "Projected ARR"
        builder.application_release = projected
        with self.assertRaises(tool.BuildError):
            builder.build()
        # KNOWN_WRONG: and a row that carries an email address, which a diagnostics role may not read.
        addressed = tool.Builder(ROOT)
        first = addressed.application_release

        def with_address(number, held):
            first(number, held)
            if number == 93:
                addressed.rows[-1]["observed"] = "Checked by someone@example.com"
        addressed.application_release = with_address
        with self.assertRaises(tool.BuildError):
            addressed.build()
        self.assertIsNone(tool.EMAIL.search(RECORD.read_text("utf-8")))

    def test_regeneration_lists_the_record_with_its_freshness_check(self):
        import regenerate_all
        view = next(item for item in regenerate_all.VIEWS if item.name == "systems-view")
        self.assertIn(RECORD.relative_to(ROOT).as_posix(), view.outputs)
        self.assertIn("tools/build_systems_view.py", view.command)
        self.assertIn("test_systems_view", view.ci_check)


class StaffAccess(unittest.TestCase):
    """The real service over loopback HTTP, with staff signed in through an owned loopback key set."""

    @classmethod
    def setUpClass(cls):
        import httpx
        from loop_engine.core.service_runtime.account_administration_checks import _Staff
        from loop_engine.core.service_runtime.account_origin_checks import signed_identity
        from loop_engine.core.service_runtime.http import ServiceHttpApplication
        from loop_engine.core.service_runtime.http_test_fixtures import running_http
        from loop_engine.core.service_runtime.records import ACCESS_MANAGE_SCOPE, TenantKeyIssue, TenantRegistration
        # ExitStack rather than enterClassContext, which Python 3.10 lacks; continuous integration runs 3.10 to 3.12.
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        folder = Path(cls.stack.enter_context(tempfile.TemporaryDirectory(prefix="systems-access-")))
        cls.identity = cls.stack.enter_context(signed_identity(folder / "http", operator_access=False))
        cls.staff = _Staff(cls.identity)
        runtime = cls.identity.fixture.runtime
        runtime.register_tenant(TenantRegistration("host-administrator", "host:administrator", (ACCESS_MANAGE_SCOPE,)))
        cls.host_key = runtime.issue_key(TenantKeyIssue("host-administrator", "host administration")).key

        def create(config):
            return ServiceHttpApplication(runtime, cls.identity.fixture.provisioning, config,
                                          browser_identity=cls.staff.adapter,
                                          account_administration=cls.staff.administration)
        cls.base, _service = cls.stack.enter_context(running_http(cls.identity.fixture, application_factory=create))
        cls.client = cls.stack.enter_context(httpx.Client(trust_env=False, timeout=30))

    def get(self, subject=None, query="", *, token=None, **headers):
        credential = token or (self.identity.token(subject) if subject else None)
        sent = {**({"Authorization": "Bearer " + credential} if credential else {}), **headers}
        return self.client.get(self.base + systems_view.PATH + query, headers=sent)

    def test_superadmin_and_developer_read_the_overview_with_a_labelled_live_reading(self):
        record = committed()
        for subject in (self.staff.superadmin, self.staff.developer):
            answer = self.get(subject)
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertEqual(answer.headers["cache-control"], "no-store")
            body = answer.json()
            self.assertEqual(body["execution"]["runtime_type"], "Loop")
            result = body["result"]
            self.assertEqual(result["record_type"], systems_view.RESULT_VERSION)
            self.assertEqual(result["states"], list(systems_view.STATES))
            self.assertEqual(result["live"]["record_type"], systems_view.LIVE_VERSION)
            self.assertRegex(result["live"]["read_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertIs(result["live"]["health"]["alive"], True)
            self.assertEqual(result["current_deployment"], record["current_deployment"])
            self.assertEqual(result["newest"]["entry"]["id"], "fly-release-93")
            self.assertEqual(len(result["entries"]), len(record["entries"]))
            self.assertIsNone(tool.EMAIL.search(json.dumps(result)), "no personal detail reaches a diagnostics role")

    def test_state_pages_hold_only_their_own_state_and_page_on(self):
        record = committed()
        for state in systems_view.STATES:
            expected = [row for row in record["rows"] if row["state"] == state]
            seen, page = [], 1
            while True:
                result = self.get(self.staff.superadmin, f"?state={state}&page={page}").json()["result"]
                self.assertEqual({row["state"] for row in result["rows"]} - {state}, set())
                seen += result["rows"]
                if not result["has_next"]:
                    break
                page += 1
            with self.subTest(state=state):
                self.assertEqual([(row["entry"], row["pointer"], row["check"]) for row in seen],
                                 [(row["entry"], row["pointer"], row["check"]) for row in expected])

    def test_an_entry_answer_holds_every_row_with_its_earlier_attempts(self):
        record = committed()
        result = self.get(self.staff.developer, "?entry=fly-release-93").json()["result"]
        self.assertEqual(len(result["rows"]), sum(row["entry"] == "fly-release-93" for row in record["rows"]))
        self.assertIn("failed", {row["state"] for row in result["rows"] if row["pointer"].startswith("/deployment_attempts")})
        self.assertIn(result["entry"]["evidence"], {item["path"] for item in result["sources"]})

    def test_signed_out_requests_are_refused_and_asked_to_sign_in(self):
        answer = self.get()
        self.assertEqual(answer.status_code, 401)
        self.assertEqual(answer.json()["error"]["code"], "unauthorized")
        self.assertIn("www-authenticate", answer.headers)
        self.assertNotIn("current_deployment", answer.text)

    def test_an_ordinary_account_a_host_key_and_a_forged_header_are_refused(self):
        customer = self.get(self.staff.customer)
        host = self.get(token=self.host_key)
        forged_role = self.get(self.staff.customer, **{"X-Staff-Role": "superadmin", "X-Forwarded-User": "owner@example.com"})
        forged_token = self.get(token="forged.token.value")
        self.assertEqual([customer.status_code, host.status_code, forged_role.status_code], [403, 403, 403])
        self.assertEqual({answer.json()["error"]["code"] for answer in (customer, host, forged_role)}, {"staff_role_required"})
        self.assertEqual(forged_token.status_code, 401)
        foreign = self.get(self.staff.superadmin, Origin="https://foreign.invalid")
        self.assertEqual((foreign.status_code, foreign.json()["error"]["code"]), (403, "invalid_origin"))

    def test_the_analytics_role_is_refused_and_the_role_table_is_what_refuses_it(self):
        answer = self.get(self.staff.analytics)
        self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (403, "account_administration_forbidden"))
        from loop_engine.core.service_runtime import account_administration, account_policy
        # KNOWN_WRONG: with every permission granted to every role, analytics reads the view.
        with mock.patch.object(account_administration, "permissions_for",
                               lambda role: frozenset(account_policy.PERMISSIONS)):
            self.assertEqual(self.get(self.staff.analytics).status_code, 200)

    def test_a_signed_out_staff_session_is_refused(self):
        token = self.identity.token(self.staff.developer, jti="systems-sign-out")
        self.assertEqual(self.get(token=token).status_code, 200)
        signed_out = self.client.post(self.base + "/api/v1/account/logout", headers={"Authorization": "Bearer " + token},
                                      json={"record_type": "service_browser_logout_request/v1"})
        self.assertEqual(signed_out.status_code, 200, signed_out.text)
        self.assertEqual(self.get(token=token).status_code, 401)

    def test_queries_are_strict(self):
        for query, status, code in (("?state=bogus", 400, "invalid_systems_query"), ("?page=2", 400, "invalid_systems_query"),
                                    ("?state=failed&page=0", 400, "invalid_systems_query"),
                                    ("?state=failed&state=passed", 400, "unknown_request_field"),
                                    ("?entry=fly-release-93&state=failed", 400, "invalid_systems_query"),
                                    ("?other=1", 400, "invalid_systems_query"),
                                    ("?entry=no-such-entry", 404, "systems_entry_not_found")):
            with self.subTest(query=query):
                answer = self.get(self.staff.superadmin, query)
                self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (status, code))
        # A refused caller learns nothing about the query either: the role is checked first.
        self.assertEqual(self.get(self.staff.analytics, "?entry=no-such-entry").status_code, 403)

    def test_unavailable_evidence_is_refused_not_invented(self):
        with mock.patch.object(systems_view, "packaged_record",
                               side_effect=ServiceRuntimeError("systems_record_unavailable")):
            answer = self.get(self.staff.superadmin)
        self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (503, "systems_record_unavailable"))
        with self.assertRaises(ServiceRuntimeError):
            systems_view.checked_record(b"{not json", SCHEMA.read_text("utf-8"))

    def test_the_record_is_served_at_no_public_address(self):
        for path in ("/systems_view.json", "/assets/systems_view.json", "/assets/systems_view.schema.json",
                     "/src/loop_engine/core/service_runtime/systems_view.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(self.base + path).status_code, 404)
        self.assertFalse([name for name, (packaged, _media) in web_pages.WEB_ASSETS.items()
                          if "systems_view" in packaged or "systems_view" in name])
        from loop_engine.core.service_runtime.static_site_export import static_addresses
        exported = static_addresses(include_model_details=False)
        self.assertIn("/admin/systems", exported)
        self.assertFalse([address for address in exported if "systems_view" in address or address.startswith("/api/")])
        page = self.client.get(self.base + "/admin/systems")
        self.assertEqual(page.status_code, 200)
        self.assertIn('<meta name="robots" content="noindex">', page.text)
        for recorded in ("pilot-release-93", "38708447261", "718c83e8-f624-4a5b-b4b7-a417b657c852"):
            self.assertNotIn(recorded, page.text, "the page shell carries no recorded fact")


SCENARIO = r"""
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const [script, fixtures] = process.argv.slice(1);
const answers = JSON.parse(fs.readFileSync(fixtures, 'utf8'));
const nodes = {};
const make = (tag, text = '') => ({tag, textContent:text, children:[], dataset:{}, hidden:false, disabled:false, className:'',
  listeners:{}, append(...parts) { this.children.push(...parts); }, replaceChildren(...parts) { this.children = parts; },
  addEventListener(type, listener) { this.listeners[type] = listener; }, focus() {}});
const $ = id => nodes[id] ??= make('node');
const context = vm.createContext({window:{}, document:{getElementById:$, createElement:tag => make(tag)}, URLSearchParams});
vm.runInContext(fs.readFileSync(script, 'utf8'), context);
const requests = [], messages = {};
let state = {connected:false}, signIns = 0, refuse = null;
const view = context.window.BaltorSystemsView.create({
  request:async path => { requests.push(path); if (refuse) throw refuse; const query = new URLSearchParams(path.split('?')[1] || '');
    if (query.get('state')) return answers.states[query.get('state')]; if (query.get('entry')) return answers.entry; return answers.overview; },
  element:(tag, text, className) => Object.assign(make(tag, text), {className:className || ''}),
  message:(id, text, failure) => { messages[id] = {text, failure}; }, said:error => error.message, failureState:() => 'refused',
  current:() => state, signIn:() => { signIns++; }});
const settle = () => new Promise(resolve => setTimeout(resolve, 0));
(async () => {
  view.show(); await settle();
  assert.equal(requests.length, 0, 'a signed-out view asks the service for nothing');
  assert.equal($('systems-login').hidden, false); assert.match(messages['systems-message'].text, /Sign in/);
  state = {connected:true, staff:false, permitted:false}; view.connectionChanged(); await settle();
  assert.equal(requests.length, 0); assert.equal(messages['systems-message'].failure, 'refused');
  state = {connected:true, staff:true, permitted:false}; view.connectionChanged(); await settle();
  assert.equal(requests.length, 0); assert.match(messages['systems-message'].text, /role does not include/);
  state = {connected:true, staff:true, permitted:true}; view.connectionChanged();
  for (let turn = 0; turn < 20; turn++) await settle();
  assert.deepEqual(requests, ['/api/v1/admin/systems', ...['failed', 'pending', 'skipped', 'unknown', 'passed']
    .map(name => '/api/v1/admin/systems?state=' + name + '&page=1')]);
  assert.equal($('systems-view').hidden, false);
  for (const name of ['failed', 'pending', 'skipped', 'unknown', 'passed']) {
    const drawn = $('systems-state-' + name).children;
    const rows = drawn.filter(item => item.tag === 'article');
    assert.ok(rows.every(item => item.dataset.state === name), name + ' holds only its own rows');
    assert.equal(rows.length, answers.states[name].rows.length);
    if (!rows.length) assert.equal(drawn[0].textContent, 'None recorded in this state.');
    assert.equal($('systems-more-' + name).hidden, answers.states[name].has_next !== true);
  }
  assert.match($('systems-live-note').textContent, /^Live: .* read at \d{4}-\d{2}-\d{2}T/);
  assert.equal($('systems-current-facts').children.length, Object.keys(answers.overview.current_deployment.stated).length);
  assert.equal($('systems-entries').children.length, answers.overview.entries.length);
  const first = $('systems-state-failed').children[0];
  assert.match(first.children[3].textContent, /Revision: .* · Environment: .* · Attempt: .* · Time: /);
  assert.match(first.children[4].textContent, /^Record: artifacts\//);
  refuse = Object.assign(new Error('Service refused the request: unauthorized.'), {status:401});
  $('refresh-systems').listeners.click(); for (let turn = 0; turn < 5; turn++) await settle();
  assert.equal(signIns, 1, 'a signed-out answer opens sign-in'); assert.equal($('systems-login').hidden, false);
  assert.equal($('systems-view').hidden, true, 'nothing recorded stays on screen after a refusal');
  console.log('systems view scenario passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


@unittest.skipUnless(shutil.which("node"), "the page script check runs the real script under Node")
class SystemsPage(unittest.TestCase):

    def fixtures(self, folder):
        live = systems_view.live_reading({"alive": True, "ready": True, "checks": [
            {"name": "durable_store_answers", "required": True, "passed": True, "code": ""}],
            "service_version": "unknown", "release_reference": "", "catalogue_release": None}, "2026-10-16T12:00:00Z")
        answers = {"overview": systems_view.staff_view({"view": "overview"}, live=live),
                   "entry": systems_view.staff_view({"view": "entry", "entry": "fly-release-93"}),
                   "states": {state: systems_view.staff_view({"view": "state", "state": state, "page": 1})
                              for state in systems_view.STATES}}
        path = Path(folder) / "answers.json"
        path.write_text(json.dumps(answers), "utf-8")
        return path

    def run_scenario(self, script):
        with tempfile.TemporaryDirectory(prefix="systems-page-") as folder:
            return subprocess.run(["node", "-e", SCENARIO, str(script), str(self.fixtures(folder))], cwd=ROOT,
                                  text=True, capture_output=True, timeout=60)

    def test_the_page_lists_each_state_separately_labels_the_live_reading_and_signs_in_again(self):
        result = self.run_scenario(SCRIPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("systems view scenario passed", result.stdout)

    def test_a_script_that_merges_the_states_is_refused(self):
        source = SCRIPT.read_text("utf-8")
        merged = source.replace('const target = $("systems-state-" + state);', 'const target = $("systems-state-failed");')
        self.assertNotEqual(merged, source)
        with tempfile.TemporaryDirectory(prefix="systems-page-wrong-") as folder:
            wrong = Path(folder) / "systems-view.js"
            wrong.write_text(merged, "utf-8")
            result = self.run_scenario(wrong)
        # KNOWN_WRONG: drawing every state into one list fails the scenario.
        self.assertNotEqual(result.returncode, 0)

    def test_the_page_has_one_systems_view_with_one_heading_and_five_state_lists(self):
        page = PAGE.read_text("utf-8")
        self.assertEqual(page.count('<section data-view="systems"'), 1)
        start = page.index('<section data-view="systems"')
        view = page[start:page.index("\n    </section>\n", start)]
        self.assertEqual(view.count("<h1"), 1)
        self.assertEqual(re.findall(r'id="systems-state-([a-z]+)"', view), ["failed", "pending", "skipped", "unknown", "passed"])
        self.assertIn('data-after-login="/admin/systems"', view)
        self.assertIn('<script defer src="/assets/systems-view.js"></script>', page)
        self.assertIn('href="/admin/systems" data-page="systems"', page)
        script = (ROOT / "src/loop_engine/core/service_runtime/web_assets/service.js").read_text("utf-8")
        self.assertIn('"/admin/systems":"systems"', script)
        self.assertEqual(web_pages.WEB_ASSETS["/admin/systems"], ("index.html", web_pages.HTML_MEDIA_TYPE))
        from loop_engine.core.service_runtime.web_site_map import load_site_map
        listed = next(page for page in load_site_map().pages if page.address == "/admin/systems")
        self.assertEqual((listed.view, listed.title, listed.indexed), ("systems", "Systems", False))


if __name__ == "__main__":
    unittest.main()
