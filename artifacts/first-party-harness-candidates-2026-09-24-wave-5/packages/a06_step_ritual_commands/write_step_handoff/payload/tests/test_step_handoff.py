"""Tests for scripts/step_handoff.py, its record contract and the command variants. Effects: writes only inside temporary folders; starts the script with the current interpreter."""
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
SCRIPT = PAYLOAD / "scripts" / "step_handoff.py"
EXAMPLES = PAYLOAD / "examples"
VARIANTS = PAYLOAD / "variants"
CONTRACT = PAYLOAD / "contracts" / "night-step-handoff.schema.json"
PLACED_SCRIPT = ".baltor/write-step-handoff/scripts/step_handoff.py"
PLACED_EXAMPLE = ".baltor/write-step-handoff/examples/handoff-example.md"
HEADINGS = ("## Purpose", "## First action", "## Steps", "## Output", "## Stop and report when")
NOTE = ".baltor/handoffs/fix-month-end-filter.md"
RECORD = ".baltor/handoffs/fix-month-end-filter.json"
OPENER = "<!" + "-" * 2  # assembled, so this file holds no comment opener

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


def run(root: Path, *arguments: str) -> tuple[int, dict]:
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments, "--root", str(root)],
                              capture_output=True, text=True, timeout=60)
    return finished.returncode, json.loads(finished.stdout)


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def note(done: list, status: str = "complete", remaining: str = "none", questions: str = "none",
         first: str = "Run `python3 -m unittest -v`.", extra: list | None = None, objective: str = "Fix it.") -> str:
    lines = ["# Step handoff: fix-month-end-filter", "", "## Objective", objective, "", "## Status", status, "",
             "## Done", *done, "", "## Remaining", remaining, "", "## Open questions", questions, "",
             "## First action for the next harness", first, ""]
    return "\n".join(lines + (extra or []))


class StepHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        write(self.root, ".baltor/step/task.json", (EXAMPLES / "task.json").read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.folder.cleanup()

    def check(self, *arguments: str) -> tuple[int, dict]:
        return run(self.root, "check", *arguments)

    def record(self) -> dict:
        return json.loads((self.root / RECORD).read_text(encoding="utf-8"))

    def test_init_uses_the_step_files_and_the_filled_example_passes(self) -> None:
        code, result = run(self.root, "init")
        self.assertEqual(code, 0)
        self.assertTrue(result["created"])
        self.assertEqual(result["path"], NOTE)
        self.assertIn("Make the monthly report include rows dated", (self.root / NOTE).read_text(encoding="utf-8"))
        for evidence in ("tests/test_month_filter.py", "src/report/month_filter.py",
                         ".baltor/evidence/fix-month-end-filter-tests.txt"):
            write(self.root, evidence, f"synthetic evidence for {evidence}\n")
        (self.root / NOTE).write_text((EXAMPLES / "handoff-example.md").read_text(encoding="utf-8"), encoding="utf-8")
        code, result = self.check()
        self.assertEqual(code, 0, result)
        self.assertTrue(result["passed"])
        self.assertEqual((result["status"], result["done_items"]), ("partial", 2))
        self.assertEqual((result["record_path"], result["record_status"]), (RECORD, "unfinished"))
        record = self.record()
        self.assertEqual(schema_errors(record, json.loads(CONTRACT.read_text(encoding="utf-8"))), [])
        self.assertEqual((record["step_id"], record["ticket_id"], record["status"]),
                         ("fix-month-end-filter", None, "unfinished"))
        self.assertEqual([claim["evidence"] for claim in record["claims"]],
                         ["tests/test_month_filter.py", "src/report/month_filter.py"])
        digest = hashlib.sha256((self.root / "src/report/month_filter.py").read_bytes()).hexdigest()
        self.assertIn({"path": "src/report/month_filter.py", "sha256": digest}, record["files"])
        self.assertEqual(len(record["files"]), 3)
        self.assertTrue(record["first_action"].startswith("Run `python3 -m unittest tests.test_month_filter -v`"))
        self.assertEqual(len(record["remaining_actions"]), 1)
        self.assertIsNone(record["blocker"])

    def test_known_wrong_note_claims_results_without_evidence(self) -> None:
        write(self.root, NOTE, note(["- Fixed the date parser.", "- All tests pass, see `logs/test-run.txt`."],
                                    remaining="- Write the missing tests.", first="Continue the work."))
        code, result = self.check()
        self.assertEqual(code, 1)
        findings = "\n".join(result["findings"])
        self.assertIn("names no file in backticks that this step wrote or changed", findings)
        self.assertIn("logs/test-run.txt does not exist", findings)
        self.assertIn("a complete step has nothing remaining", findings)
        self.assertIn("First action holds 0 items in backticks", findings)
        self.assertIsNone(result["record_path"])
        self.assertFalse((self.root / RECORD).exists())

    def test_known_wrong_placed_notes_from_the_review_are_refused(self) -> None:
        write(self.root, "README.md", "unrelated file that this step did not change\n")
        old = time.time() - 3600
        os.utime(self.root / "README.md", (old, old))
        write(self.root, "src/report/month_filter.py", "changed by this step\n")
        cases = {
            "workspace root": (note(["- Fixed the month-end bug `.`"]), ". is a folder"),
            "step input": (note(["- Fixed the bug and all tests pass `.baltor/step/task.json`"]), "is a step input"),
            "folder": (note(["- Fixed the report code in `src/report`"]), "src/report is a folder"),
            "unchanged file": (note(["- Documented the fix in `README.md`"]), "was last changed before this step"),
            "second Done heading": (note(["- Fixed `src/report/month_filter.py`"], extra=[
                "## Done", "- Also rewrote the quarter filter and every test passes.", ""]),
                "'## Done' appears a second time"),
            "unknown heading": (note(["- Fixed `src/report/month_filter.py`"], extra=[
                "## Notes", "- Deployed the fix and closed the ticket.", ""]), "unknown heading '## Notes'"),
            "four actions": (note(["- Fixed `src/report/month_filter.py`"],
                                  first="Run `make clean` then `make all` then edit `src/a.py` and `src/b.py`."),
                             "First action holds 4 items in backticks"),
            "code block": (note(["- Fixed `src/report/month_filter.py`"], extra=[
                "```", "- A claim hidden in a code block", "```", ""]), "fenced code block"),
            "hidden comment": (note(["- Fixed `src/report/month_filter.py` " + OPENER + " and deployed it --" + ">"]),
                               "hidden comment"),
        }
        for label, (text, expected) in cases.items():
            with self.subTest(label):
                (self.root / NOTE).parent.mkdir(parents=True, exist_ok=True)
                (self.root / NOTE).write_text(text, encoding="utf-8")
                code, result = self.check()
                self.assertEqual(code, 1, result)
                self.assertIn(expected, "\n".join(result["findings"]))
                self.assertFalse((self.root / RECORD).exists())

    def test_unfilled_template_fails_the_check(self) -> None:
        run(self.root, "init")
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any("(fill in" in finding for finding in result["findings"]))
        self.assertTrue(any("Status is one line" in finding for finding in result["findings"]))

    def test_init_never_replaces_an_existing_note(self) -> None:
        run(self.root, "init")
        (self.root / NOTE).write_text("# kept by the step\n", encoding="utf-8")
        code, result = run(self.root, "init")
        self.assertEqual(code, 0)
        self.assertFalse(result["created"])
        self.assertEqual((self.root / NOTE).read_text(encoding="utf-8"), "# kept by the step\n")

    def test_evidence_outside_the_workspace_and_the_note_itself_are_findings(self) -> None:
        write(self.root, NOTE, note(["- Copied the log to `../outside.txt`.", f"- Wrote `{NOTE}`."],
                                    status="partial", remaining="- Fix the quarter filter.", first=f"Read `{NOTE}`."))
        code, result = self.check()
        self.assertEqual(code, 1)
        findings = "\n".join(result["findings"])
        self.assertIn("../outside.txt is outside the workspace", findings)
        self.assertIn("cannot be its own evidence", findings)

    def test_blocked_step_writes_a_blocked_record(self) -> None:
        write(self.root, NOTE, note(["- none"], status="**blocked**",
                                    remaining="- The test database file is missing, so no test can run.",
                                    questions="- Where is the test database kept? The ticket author knows.",
                                    first="Read `.baltor/step/task.json`."))
        code, result = self.check()
        self.assertEqual(code, 0, result)
        self.assertEqual((result["status"], result["record_status"]), ("blocked", "blocked"))
        record = self.record()
        self.assertEqual(schema_errors(record, json.loads(CONTRACT.read_text(encoding="utf-8"))), [])
        self.assertEqual(record["claims"], [])
        self.assertEqual(record["blocker"], {"reason": "The test database file is missing, so no test can run.",
                                             "question": "Where is the test database kept? The ticket author knows.",
                                             "evidence": None})

    def test_complete_step_takes_its_ticket_from_the_night_queue(self) -> None:
        write(self.root, "src/report/month_filter.py", "changed by this step\n")
        write(self.root, NOTE, note(["- Fixed the end date in `src/report/month_filter.py`."]))
        code, result = self.check("--ticket", "T-999")
        self.assertEqual(code, 0, result)
        self.assertEqual(self.record()["ticket_id"], "T-999")
        write(self.root, ".baltor/night/queue.json", json.dumps({"record_type": "night_queue/v1", "items": [
            {"position": 1, "id": "fix-month-end-filter", "title": "Month filter", "status": "queued"}]}))
        code, result = self.check()
        self.assertEqual(code, 0, result)
        record = self.record()
        self.assertEqual((record["ticket_id"], record["status"]), ("fix-month-end-filter", "complete"))
        self.assertEqual(schema_errors(record, json.loads(CONTRACT.read_text(encoding="utf-8"))), [])
        code, result = self.check("--ticket", "T-999")
        self.assertEqual(code, 2)
        self.assertIn("is not in .baltor/night/queue.json", result["reason"])

    def test_a_failing_check_after_a_pass_keeps_the_last_record(self) -> None:
        write(self.root, "src/report/month_filter.py", "changed by this step\n")
        write(self.root, NOTE, note(["- Fixed the end date in `src/report/month_filter.py`."]))
        self.assertEqual(self.check()[0], 0)
        before = (self.root / RECORD).read_bytes()
        write(self.root, NOTE, note(["- Fixed the end date and deployed it."]))
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertIsNone(result["record_path"])
        self.assertEqual((self.root / RECORD).read_bytes(), before)

    def test_empty_objective_and_unsafe_step_ids_are_reported(self) -> None:
        write(self.root, "src/report/month_filter.py", "changed by this step\n")
        write(self.root, NOTE, note(["- Fixed `src/report/month_filter.py`."], objective=""))
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertIn("Objective is empty", "\n".join(result["findings"]))
        for step_id in ("../escape", "x" * 65):
            code, result = run(self.root, "init", "--step-id", step_id)
            self.assertEqual(code, 2)
            self.assertTrue(result["refused"])
        (self.root / ".baltor" / "step" / "task.json").unlink()
        code, result = run(self.root, "init")
        self.assertEqual(code, 2)
        self.assertIn("pass --step-id", result["reason"])

    def test_record_contract_is_the_shared_night_handoff_schema(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["title"], "night_step_handoff/v1")
        self.assertEqual(set(contract["properties"]["status"]["enum"]), {"complete", "blocked", "unfinished"})
        text = SCRIPT.read_text(encoding="utf-8")
        for mapping in ('"complete": "complete"', '"partial": "unfinished"', '"blocked": "blocked"'):
            self.assertIn(mapping, text)
        write(self.root, "src/report/month_filter.py", "changed by this step\n")
        write(self.root, NOTE, note(["- Fixed `src/report/month_filter.py`."]))
        self.assertEqual(self.check()[0], 0)
        self.assertEqual(set(self.record()), set(contract["required"]))

    def test_every_variant_names_the_placed_script_and_the_headings(self) -> None:
        variants = sorted(path for path in VARIANTS.rglob("*") if path.is_file())
        self.assertEqual(len(variants), 5)
        for path in variants:
            text = path.read_text(encoding="utf-8")
            self.assertIn(PLACED_SCRIPT, text, path.name)
            self.assertIn(PLACED_EXAMPLE, text, path.name)
            self.assertIn("# Write a step handoff note", text, path.name)
            self.assertIn("exactly one command or one file path", text, path.name)
            for heading in HEADINGS:
                self.assertIn(heading, text.splitlines(), f"{path.name} lacks {heading}")
        markers = {"claude_code": "$ARGUMENTS", "opencode": "$ARGUMENTS", "gemini_cli": "{{args}}"}
        for harness in ("claude_code", "opencode", "gemini_cli", "copilot", "cursor"):
            text = next((VARIANTS / harness).iterdir()).read_text(encoding="utf-8")
            for marker in ("$ARGUMENTS", "{{args}}"):
                self.assertEqual(marker in text, markers.get(harness) == marker, f"{harness} {marker}")
        copilot = (VARIANTS / "copilot" / "write-step-handoff.prompt.md").read_text(encoding="utf-8")
        self.assertIn("\nagent: agent\n", copilot.split("---")[1] + "\n")
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
