"""The staff Systems record holds recorded facts only, with every result state kept apart.

Kind: development check over the generated record and its generator. It opens no connection, calls no provider and
needs no credential. Roadmap
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
- no projection, forecast, revenue or investor word appears, and the generator refuses one.

Run:

    PYTHONPATH=src:tools python -m unittest tools/test_systems_view.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import build_systems_view as tool  # noqa: E402
from loop_engine.core.service_runtime import systems_view  # noqa: E402
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

RECORD = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "systems_view.json"
SCHEMA = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "systems_view.schema.json"
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
        for name, text in (("record", RECORD.read_text("utf-8")),
                           ("service module", Path(systems_view.__file__).read_text("utf-8"))):
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


if __name__ == "__main__":
    unittest.main()
