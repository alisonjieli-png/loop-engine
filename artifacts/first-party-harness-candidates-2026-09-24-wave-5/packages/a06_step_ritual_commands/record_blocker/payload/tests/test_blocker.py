"""Tests for scripts/blocker.py, the status contract it writes and the command variants. Effects: writes only inside temporary folders; starts the script with the current interpreter."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "blocker.py"
EXAMPLES = PAYLOAD / "examples"
CONTRACTS = PAYLOAD / "contracts"
VARIANTS = PAYLOAD / "variants"
PLACED_SCRIPT = ".baltor/record-blocker/scripts/blocker.py"
HEADINGS = ("## Purpose", "## First action", "## Steps", "## Output", "## Stop and report when")

# A JSON Schema 2020-12 subset validator. Unknown keywords raise, so nothing is skipped in silence.
SCHEMA_KEYWORDS = frozenset({
    "$schema", "$id", "$defs", "$ref", "$comment", "title", "description", "default", "examples",
    "type", "enum", "const", "properties", "required", "additionalProperties", "propertyNames",
    "minProperties", "maxProperties", "items", "minItems", "maxItems", "uniqueItems", "minLength",
    "maxLength", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "anyOf",
    "oneOf", "allOf", "not", "if", "then", "else"})


def is_type(value, name: str) -> bool:
    checks = {"object": lambda: isinstance(value, dict), "array": lambda: isinstance(value, list),
              "string": lambda: isinstance(value, str), "boolean": lambda: isinstance(value, bool),
              "null": lambda: value is None,
              "integer": lambda: (isinstance(value, int) and not isinstance(value, bool))
              or (isinstance(value, float) and value.is_integer()),
              "number": lambda: isinstance(value, (int, float)) and not isinstance(value, bool)}
    return checks[name]()


def same(left, right) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def schema_errors(instance, schema, root=None, where="$") -> list:
    root = schema if root is None else root
    if schema is True:
        return []
    if schema is False:
        return [f"{where}: no value is allowed"]
    unknown = set(schema) - SCHEMA_KEYWORDS
    if unknown:
        raise ValueError(f"unsupported schema keywords {sorted(unknown)}")
    errors = []
    if "$ref" in schema:
        target = root
        for part in [piece for piece in schema["$ref"][1:].split("/") if piece]:
            target = target[part]
        errors += schema_errors(instance, target, root, where)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(is_type(instance, name) for name in names):
            return errors + [f"{where}: expected type {schema['type']}"]
    if "const" in schema and not same(instance, schema["const"]):
        errors.append(f"{where}: must equal {schema['const']!r}")
    if "enum" in schema and not any(same(instance, option) for option in schema["enum"]):
        errors.append(f"{where}: must be one of {schema['enum']!r}")
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        errors += [f"{where}: missing {name}" for name in schema.get("required", []) if name not in instance]
        for name, value in instance.items():
            if name in properties:
                errors += schema_errors(value, properties[name], root, f"{where}.{name}")
            elif "additionalProperties" in schema:
                errors += schema_errors(value, schema["additionalProperties"], root, f"{where}.{name}")
            if "propertyNames" in schema:
                errors += schema_errors(name, schema["propertyNames"], root, f"{where} key {name!r}")
        if len(instance) < schema.get("minProperties", 0) or len(instance) > schema.get("maxProperties", 10 ** 9):
            errors.append(f"{where}: property count out of range")
    if isinstance(instance, list):
        for index, item in enumerate(instance):
            if "items" in schema:
                errors += schema_errors(item, schema["items"], root, f"{where}[{index}]")
        if len(instance) < schema.get("minItems", 0) or len(instance) > schema.get("maxItems", 10 ** 9):
            errors.append(f"{where}: item count out of range")
        if schema.get("uniqueItems") and any(same(instance[i], instance[j]) for i in range(len(instance))
                                             for j in range(i + 1, len(instance))):
            errors.append(f"{where}: items are not unique")
    if isinstance(instance, str):
        if not schema.get("minLength", 0) <= len(instance) <= schema.get("maxLength", 10 ** 9):
            errors.append(f"{where}: length out of range")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{where}: does not match {schema['pattern']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if instance < schema.get("minimum", -float("inf")) or instance > schema.get("maximum", float("inf")) \
                or instance <= schema.get("exclusiveMinimum", -float("inf")) \
                or instance >= schema.get("exclusiveMaximum", float("inf")):
            errors.append(f"{where}: number out of range")
    for part in schema.get("allOf", []):
        errors += schema_errors(instance, part, root, where)
    if "anyOf" in schema and all(schema_errors(instance, part, root, where) for part in schema["anyOf"]):
        errors.append(f"{where}: matches none of anyOf")
    if "oneOf" in schema and sum(not schema_errors(instance, part, root, where) for part in schema["oneOf"]) != 1:
        errors.append(f"{where}: does not match exactly one of oneOf")
    if "not" in schema and not schema_errors(instance, schema["not"], root, where):
        errors.append(f"{where}: matches a schema it must not match")
    if "if" in schema:
        branch = "then" if not schema_errors(instance, schema["if"], root, where) else "else"
        errors += schema_errors(instance, schema.get(branch, True), root, where)
    return errors



def contract(name: str) -> dict:
    return json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))


def run(root: Path, *arguments: str) -> tuple[int, dict]:
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments, "--root", str(root)],
                              capture_output=True, text=True, timeout=60)
    return finished.returncode, json.loads(finished.stdout)


def record_text(ticket: str, error_block: list, log_line: str = "", needed: str = "- The fixture helper.",
                extra: list | None = None) -> str:
    lines = [f"# Blocker: {ticket}", "", "## Ticket", ticket, "", "## Step", "fix-month-end-filter", "",
             "## What was tried", "- Ran the tests twice with a changed fixture path.", "", "## Exact error",
             *(["```text", *error_block, "```"] if error_block else []), *([log_line] if log_line else []), "",
             "## Needed", needed, "", "## From whom", "The ticket author.", ""]
    return "\n".join(lines + (extra or []))


class BlockerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.night = self.root / ".baltor" / "night"
        self.night.mkdir(parents=True)
        for name in ("queue.json", "queue-status.json"):
            (self.night / name).write_bytes((EXAMPLES / name).read_bytes())

    def tearDown(self) -> None:
        self.folder.cleanup()

    def status(self) -> dict:
        return json.loads((self.night / "queue-status.json").read_text(encoding="utf-8"))

    def statuses(self) -> dict:
        tickets = self.status()["tickets"]
        return {item["id"]: tickets.get(item["id"], {}).get("status", "queued")
                for item in json.loads((self.night / "queue.json").read_text(encoding="utf-8"))["items"]}

    def record(self, ticket: str = "T-101") -> Path:
        return self.night / "blockers" / f"{ticket}.md"

    def settings(self, one_ticket_per_harness: bool) -> None:
        (self.night / "settings.json").write_text(json.dumps({
            "record_type": "night_settings/v1", "time_minutes": 240, "model_calls": 200,
            "one_ticket_per_harness": one_ticket_per_harness}), encoding="utf-8")

    def write_log(self, relative: str, text: str) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return relative

    def test_filed_record_blocks_the_ticket_holds_dependents_and_names_the_next(self) -> None:
        queue_bytes = (self.night / "queue.json").read_bytes()
        code, result = run(self.root, "new")
        self.assertEqual((code, result["ticket"], result["created"]), (0, "T-101", True))
        self.assertIn("## Exact error", self.record().read_text(encoding="utf-8"))
        self.record().write_text((EXAMPLES / "blocker-example.md").read_text(encoding="utf-8"), encoding="utf-8")
        code, result = run(self.root, "file")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["waiting"], ["T-103", "T-108"])
        self.assertEqual(result["next"]["id"], "T-102")
        self.assertIsNone(result["continue_with"])
        self.assertIn("one_ticket_per_harness is true", result["not_started_because"])
        self.assertEqual(self.statuses(), {"T-101": "blocked", "T-103": "waiting", "T-108": "waiting",
                                           "T-102": "queued"})
        status = self.status()
        self.assertEqual(schema_errors(status, contract("night-queue-status")), [])
        self.assertEqual(status["tickets"]["T-101"]["blocker"], ".baltor/night/blockers/T-101.md")
        self.assertEqual(status["tickets"]["T-101"]["changes"][-1]["from"], "in_progress")
        self.assertEqual(status["tickets"]["T-108"]["waits_for"], "T-101")
        self.assertEqual((self.night / "queue.json").read_bytes(), queue_bytes)
        self.assertEqual(status["queue_sha256"], hashlib.sha256(queue_bytes).hexdigest())

    def test_one_session_mode_starts_the_next_ticket_unless_told_not_to(self) -> None:
        self.settings(False)
        run(self.root, "new")
        self.record().write_text((EXAMPLES / "blocker-example.md").read_text(encoding="utf-8"), encoding="utf-8")
        code, result = run(self.root, "file", "--no-start")
        self.assertEqual((code, result["continue_with"], result["not_started_because"]), (0, None, "--no-start was given"))
        (self.night / "queue-status.json").write_bytes((EXAMPLES / "queue-status.json").read_bytes())
        code, result = run(self.root, "file")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["continue_with"]["id"], "T-102")
        self.assertEqual(self.statuses()["T-102"], "in_progress")
        self.assertEqual(schema_errors(self.status(), contract("night-queue-status")), [])

    def test_known_wrong_next_ticket_waits_for_dependencies_and_work_in_progress(self) -> None:
        self.settings(False)
        code, result = run(self.root, "new", "--ticket", "T-102")
        self.assertEqual(code, 0, result)
        self.record("T-102").write_text(record_text("T-102", ["AssertionError: header row is empty"]), encoding="utf-8")
        code, result = run(self.root, "file", "--ticket", "T-102")
        self.assertEqual(code, 0, result)
        self.assertIsNone(result["next"])
        self.assertIsNone(result["continue_with"])
        self.assertEqual(self.statuses(), {"T-101": "in_progress", "T-103": "queued", "T-108": "queued",
                                           "T-102": "blocked"})
        code, result = run(self.root, "new")
        self.assertEqual((code, result["ticket"]), (0, "T-101"))
        status = self.status()
        stamp = status["tickets"]["T-101"]["changes"][0]["at"]
        status["tickets"] = {
            "T-101": {"status": "done", "evidence": "src/report/month_filter.py", "changes": [
                {"from": "queued", "to": "in_progress", "at": stamp, "by": "host"},
                {"from": "in_progress", "to": "done", "at": stamp, "by": "host", "evidence": "src/report/month_filter.py"}]},
            "T-103": {"status": "in_progress", "changes": [{"from": "queued", "to": "in_progress", "at": stamp, "by": "host"}]}}
        (self.night / "queue-status.json").write_text(json.dumps(status), encoding="utf-8")
        self.record("T-108").parent.mkdir(parents=True, exist_ok=True)
        run(self.root, "new", "--ticket", "T-108")
        self.record("T-108").write_text(record_text("T-108", ["NameError: quarter_rule"]), encoding="utf-8")
        code, result = run(self.root, "file", "--ticket", "T-108")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["next"]["id"], "T-102")
        self.assertIsNone(result["continue_with"])
        self.assertEqual(result["not_started_because"], "T-103 is still in progress")
        self.assertEqual(sum(1 for value in self.statuses().values() if value == "in_progress"), 1)

    def test_known_wrong_record_with_a_paraphrased_error_changes_nothing(self) -> None:
        run(self.root, "new")
        before = (self.night / "queue-status.json").read_bytes()
        self.record().write_text("\n".join([
            "# Blocker: T-101", "", "## Ticket", "T-101", "", "## Step", "fix-month-end-filter", "",
            "## What was tried", "- Ran the tests.", "", "## Exact error", "It failed with some import problem.", "",
            "## Needed", "- (fill in: the file, permission, decision or fix that would let the work go on)", "",
            "## From whom", "", ""]), encoding="utf-8")
        code, result = run(self.root, "file")
        self.assertEqual(code, 1)
        self.assertFalse(result["filed"])
        findings = "\n".join(result["findings"])
        self.assertIn("no pasted error lines", findings)
        self.assertIn("(fill in", findings)
        self.assertIn("From whom is empty", findings)
        self.assertEqual((self.night / "queue-status.json").read_bytes(), before)

    def test_known_wrong_saved_log_must_be_a_real_log(self) -> None:
        run(self.root, "new")
        before = (self.night / "queue-status.json").read_bytes()
        old = self.write_log(".baltor/night/logs/old-run.txt", "Traceback from last week\n")
        os.utime(self.root / old, (time.time() - 30 * 86400, time.time() - 30 * 86400))
        self.write_log(".baltor/night/logs/empty.txt", "")
        cases = {".baltor/night/blockers/T-101.md": "it is this blocker record",
                 ".baltor/night/queue.json": "night settings, ticket, queue or status file",
                 ".baltor/night/logs/empty.txt": "it is empty",
                 old: "last changed before this ticket started",
                 ".baltor/night/logs/missing.txt": "does not exist as a file"}
        for path, expected in cases.items():
            with self.subTest(path):
                self.record().write_text(record_text("T-101", [], f"See `{path}`."), encoding="utf-8")
                code, result = run(self.root, "file")
                self.assertEqual(code, 1, result)
                self.assertIn(expected, "\n".join(result["findings"]))
                self.assertEqual((self.night / "queue-status.json").read_bytes(), before)

    def test_a_saved_log_can_replace_or_back_the_pasted_error(self) -> None:
        run(self.root, "new")
        log = self.write_log(".baltor/night/logs/t-101-tests.txt",
                             "Traceback (most recent call last):\nModuleNotFoundError: No module named 'report_fixtures'\n")
        self.record().write_text(record_text("T-101", ["It failed with some import problem."], f"Full output: `{log}`."),
                                 encoding="utf-8")
        code, result = run(self.root, "file", "--no-start")
        self.assertEqual(code, 1)
        self.assertIn("does not appear in the saved log", "\n".join(result["findings"]))
        self.record().write_text(record_text("T-101", ["ModuleNotFoundError: No module named 'report_fixtures'"],
                                             f"Full output: `{log}`."), encoding="utf-8")
        code, result = run(self.root, "file", "--no-start")
        self.assertEqual(code, 0, result)

    def test_step_files_choose_the_ticket_and_new_never_replaces_a_record(self) -> None:
        step = self.root / ".baltor" / "step"
        step.mkdir(parents=True)
        (step / "task.json").write_text(json.dumps({"node_id": "T-102", "objective": "Fix the header row."}),
                                        encoding="utf-8")
        code, result = run(self.root, "new")
        self.assertEqual((code, result["ticket"]), (0, "T-102"))
        self.record("T-102").write_text("# kept\n", encoding="utf-8")
        code, result = run(self.root, "new")
        self.assertFalse(result["created"])
        self.assertEqual(self.record("T-102").read_text(encoding="utf-8"), "# kept\n")

    def test_unknown_blocked_unsafe_or_unnamed_tickets_are_refused(self) -> None:
        for ticket, expected in (("T-999", "not in the queue"), ("../T-101", "letters, digits")):
            code, result = run(self.root, "new", "--ticket", ticket)
            self.assertEqual(code, 2)
            self.assertIn(expected, result["reason"])
        run(self.root, "new")
        self.record().write_text((EXAMPLES / "blocker-example.md").read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(run(self.root, "file", "--no-start")[0], 0)
        code, result = run(self.root, "file", "--ticket", "T-101")
        self.assertEqual(code, 2)
        self.assertIn("is blocked", result["reason"])
        code, result = run(self.root, "new")
        self.assertEqual(code, 2)
        self.assertIn("pass --ticket", result["reason"])
        status = self.status()
        status["queue_sha256"] = "0" * 64
        (self.night / "queue-status.json").write_text(json.dumps(status), encoding="utf-8")
        code, result = run(self.root, "new", "--ticket", "T-102")
        self.assertEqual(code, 2)
        self.assertIn("belongs to another queue", result["reason"])
        (self.night / "queue.json").unlink()
        code, result = run(self.root, "new", "--ticket", "T-102")
        self.assertEqual(code, 2)
        self.assertIn("no queue", result["reason"])

    def test_extra_or_repeated_headings_are_findings(self) -> None:
        run(self.root, "new")
        text = record_text("T-101", ["ModuleNotFoundError: No module named 'report_fixtures'"],
                           extra=["## Notes", "- The fix is probably simple.", ""])
        self.record().write_text(text, encoding="utf-8")
        code, result = run(self.root, "file")
        self.assertEqual(code, 1)
        self.assertIn("second or unknown heading", "\n".join(result["findings"]))

    def test_examples_follow_the_contracts(self) -> None:
        queue = json.loads((EXAMPLES / "queue.json").read_text(encoding="utf-8"))
        status = json.loads((EXAMPLES / "queue-status.json").read_text(encoding="utf-8"))
        self.assertEqual(schema_errors(queue, contract("night-queue")), [])
        self.assertEqual(schema_errors(status, contract("night-queue-status")), [])
        self.assertEqual(status["queue_sha256"], hashlib.sha256((EXAMPLES / "queue.json").read_bytes()).hexdigest())
        self.assertNotEqual(schema_errors({**status, "tickets": {"T-101": {"status": "blocked", "changes": [
            {"from": "queued", "to": "blocked", "at": "2026-09-23T21:00:00Z", "by": "record-blocker"}]}}},
            contract("night-queue-status")), [])

    def test_every_variant_names_the_placed_script_and_the_headings(self) -> None:
        variants = sorted(path for path in VARIANTS.rglob("*") if path.is_file())
        self.assertEqual(len(variants), 5)
        for path in variants:
            text = path.read_text(encoding="utf-8")
            for expected in (PLACED_SCRIPT, "# Record a blocker and move on", "continue_with", ".baltor/night/logs/",
                             ".baltor/record-blocker/examples/blocker-example.md"):
                self.assertIn(expected, text, path.name)
            for heading in HEADINGS:
                self.assertIn(heading, text.splitlines(), f"{path.name} lacks {heading}")
        markers = {"claude_code": "$ARGUMENTS", "opencode": "$ARGUMENTS", "gemini_cli": "{{args}}"}
        for harness in ("claude_code", "opencode", "gemini_cli", "copilot", "cursor"):
            text = next((VARIANTS / harness).iterdir()).read_text(encoding="utf-8")
            for marker in ("$ARGUMENTS", "{{args}}"):
                self.assertEqual(marker in text, markers.get(harness) == marker, f"{harness} {marker}")
        copilot = (VARIANTS / "copilot" / "record-blocker.prompt.md").read_text(encoding="utf-8")
        self.assertIn("\nagent: agent\n", copilot.split("---")[1] + "\n")
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
