"""Tests for scripts/verify_criteria_evidence.py; they read the shipped examples and write no file.

Run from the package root: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_criteria_evidence.py"
CRITERIA = "examples/criteria.md"

SPEC = importlib.util.spec_from_file_location("verify_criteria_evidence", SCRIPT)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def run(criteria=CRITERIA, evidence="examples/evidence.json", stdin="", extra=()):
    data = stdin if isinstance(stdin, bytes) else stdin.encode("utf-8")
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(ROOT), "--criteria", criteria,
                           "--evidence", evidence, *extra], input=data, capture_output=True, timeout=60)
    return done.returncode, json.loads(done.stdout.decode("utf-8"))


def shipped_entries() -> list:
    return json.loads((ROOT / "examples" / "evidence.json").read_text(encoding="utf-8"))["evidence"]


def with_entries(entries) -> str:
    return json.dumps({"evidence": entries})


def problems(result: dict) -> set:
    return {item["problem"] for item in result["evidence_problems"]}


class Positive(unittest.TestCase):
    def test_shipped_example_passes(self):
        code, result = run()
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)
        self.assertEqual([row["id"] for row in result["criteria"]], ["AC-1", "AC-2", "AC-3", "AC-4"])
        self.assertEqual(result["counts"]["covered"], 4)

    def test_json_criteria_with_ids(self):
        criteria = json.dumps({"criteria": [{"id": "AC-1", "text": "lower case"}, {"id": "AC-2", "text": "spaces"},
                                            {"id": "AC-3", "text": "suite passes"}, {"id": "AC-4", "text": "log"}]})
        code, result = run(criteria="-", stdin=criteria)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)

    def test_criteria_from_the_ticket_extractor_output(self):
        document = {"record_type": "ticket_criteria/v1", "status": "ok", "title": "Slugs",
                    "acceptance_criteria": [{"id": "AC-1", "text": "lower case", "checkable": True},
                                            {"id": "AC-2", "text": "spaces", "checkable": True},
                                            {"id": "AC-3", "text": "suite passes", "checkable": True},
                                            {"id": "AC-4", "text": "change log", "checkable": True},
                                            {"id": "AC-5", "text": "feels faster", "checkable": False}]}
        code, result = run(criteria="-", stdin=json.dumps(document))
        self.assertEqual((code, result["uncovered"]), (1, ["AC-5"]))

    def test_json_criteria_without_ids_are_numbered(self):
        code, result = run(criteria="-", stdin=json.dumps(["Slugs are lower case.", "Spaces collapse."]))
        self.assertEqual(code, 1)
        self.assertEqual(result["uncovered"], ["C1", "C2"])
        self.assertEqual(len(result["unknown_criteria"]), 4)


class KnownWrong(unittest.TestCase):
    def test_ticked_box_without_evidence(self):
        entries = [entry for entry in shipped_entries() if entry.get("criterion") != "AC-4"]
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["verdict"], result["uncovered"]), (1, "fail", ["AC-4"]))
        self.assertIn("AC-4 is ticked but has no evidence that holds up", result["warnings"])

    def test_citing_the_failing_run_contradicts_the_criterion(self):
        entries = shipped_entries()
        entries[0]["output"] = "examples/test-run-before.txt"
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual(code, 1)
        self.assertEqual(result["contradicted"], ["AC-1", "AC-2"])
        self.assertIn("test_failed", problems(result))

    def test_nonzero_exit_code_contradicts(self):
        entries = shipped_entries()
        entries[1]["exit_code"] = 1
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["contradicted"]), (1, ["AC-3"]))

    def test_digest_mismatch_and_missing_file(self):
        entries = shipped_entries()
        entries[1]["sha256"] = hashlib.sha256(b"other bytes").hexdigest()
        entries[2]["path"] = "examples/no-such-changelog.txt"
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["uncovered"]), (1, ["AC-3", "AC-4"]))
        self.assertEqual(problems(result), {"digest_mismatch", "file_missing"})

    def test_malformed_digest(self):
        entries = shipped_entries()
        entries[2]["sha256"] = "abc"
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["uncovered"]), (1, ["AC-4"]))
        self.assertIn("bad_digest", problems(result))

    def test_text_that_the_file_does_not_contain(self):
        entries = shipped_entries()
        entries[2]["contains"] = "redirect table"
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["uncovered"]), (1, ["AC-4"]))

    def test_unknown_criterion_and_note_entries(self):
        entries = shipped_entries() + [{"criterion": "AC-9", "kind": "file", "path": "examples/changelog.txt"},
                                       {"criterion": "AC-1", "kind": "note", "text": "checked by hand"}]
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual(code, 1)
        self.assertEqual(result["unknown_criteria"], [{"entry": 3, "criterion": "AC-9"}])
        self.assertIn("unknown_kind", problems(result))

    def test_test_not_found_and_output_outside_root(self):
        entries = shipped_entries()
        entries[0]["test"] = "tests/test_slugs.py::test_never_written"
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual(result["uncovered"], ["AC-1", "AC-2"])
        self.assertIn("test_not_found", problems(result))
        entries[0].update(test="test_joins_words", output="../outside.txt")
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertIn("path_outside_root", problems(result))

    def test_command_without_saved_output_is_not_evidence(self):
        entries = shipped_entries()
        del entries[1]["output"], entries[1]["sha256"]
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["uncovered"]), (1, ["AC-3"]))
        self.assertIn("output_not_cited", problems(result))

    def test_command_exit_zero_whose_output_shows_a_failure(self):
        entries = shipped_entries()
        entries[1].update(output="examples/test-run-before.txt")
        del entries[1]["sha256"]
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["contradicted"]), (1, ["AC-3"]))
        self.assertIn("output_shows_failure", problems(result))

    def test_command_nonzero_exit_whose_output_shows_a_pass(self):
        entries = shipped_entries()
        entries[1].update(exit_code=1, expect_exit=1)
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["contradicted"]), (1, ["AC-3"]))
        self.assertIn("output_shows_pass", problems(result))

    def test_command_exit_code_that_its_record_contradicts(self):
        entries = shipped_entries()
        entries[1].update(command="python3 tools/check_style.py src", exit_code=0, output="examples/style-check.json")
        del entries[1]["sha256"]
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)
        entries[1].update(exit_code=3, expect_exit=3)
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual((code, result["contradicted"]), (1, ["AC-3"]))
        self.assertIn("exit_code_contradicted", problems(result))

    def test_entry_without_criteria(self):
        entries = shipped_entries() + [{"kind": "file", "path": "examples/changelog.txt"}]
        code, result = run(evidence="-", stdin=with_entries(entries))
        self.assertEqual(code, 0, result)
        self.assertIn("no_criterion_named", problems(result))


class Parsing(unittest.TestCase):
    def test_markdown_forms(self):
        text = ("# Ticket\n\n## Definition of done\n\n1. [R2] Handles empty input\n2) AC3. Keeps digits\n"
                "   - detail line\n3. Logs one line\n\n## Other\n\n- [ ] not a criterion\n")
        rows = TOOL.markdown_criteria(text)
        self.assertEqual([(row["id"], row["text"]) for row in rows],
                         [("R2", "Handles empty input"), ("AC3", "Keeps digits"), (None, "Logs one line")])

    def test_checkbox_items_without_a_section(self):
        rows = TOOL.markdown_criteria("Plan\n\n- [x] first\n- [ ] second\n- plain note\n")
        self.assertEqual([(row["text"], row["ticked"]) for row in rows], [("first", True), ("second", False)])

    def test_skipped_and_ambiguous_tests(self):
        results = {"t/test_a.py::test_x": "skipped", "t/test_b.py::test_x": "passed"}
        with self.assertRaises(TOOL.Refused):
            TOOL.match_test("test_x", results, "pytest")
        self.assertEqual(TOOL.match_test("t/test_a.py::test_x", results, "pytest"), ["t/test_a.py::test_x"])

    def test_skipped_test_is_not_evidence(self):
        cached = {"saved-run.txt": ("pytest", {"tests/test_slugs.py::test_tabs": "skipped"})}
        entry = {"criterion": "AC-2", "kind": "test", "test": "test_tabs", "output": "saved-run.txt"}
        state, problem, _detail = TOOL.judge_entry(entry, ROOT, "auto", cached)
        self.assertEqual((state, problem), ("invalid", "test_not_passed"))

    def test_a_repeated_test_id_keeps_its_most_severe_result(self):
        rerun = "tests/test_slugs.py::test_tabs FAILED [ 50%]\ntests/test_slugs.py::test_tabs PASSED [100%]\n"
        self.assertEqual(TOOL.parse_pytest(rerun), {"tests/test_slugs.py::test_tabs": "failed"})

    def test_junit_xml_outputs(self):
        text = ('<testsuite><testcase classname="tests.test_slugs" name="test_tabs"/>'
                '<testcase classname="tests.test_slugs" name="test_digits"><failure message="x"/></testcase></testsuite>')
        self.assertEqual(TOOL.parse_output(text, "auto"),
                         ("junit", {"tests.test_slugs.test_tabs": "passed", "tests.test_slugs.test_digits": "failed"}))
        with self.assertRaises(TOOL.Refused):
            TOOL.parse_junit('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><testsuite/>')

    def test_unittest_and_go_outputs(self):
        runner, results = TOOL.parse_output("test_ok (pkg.T.test_ok) ... ok\nRan 1 test in 0.001s\n", "auto")
        self.assertEqual((runner, results), ("unittest", {"pkg.T.test_ok": "passed"}))
        runner, results = TOOL.parse_output("--- PASS: TestSlug (0.00s)\n--- FAIL: TestTabs (0.00s)\n", "auto")
        self.assertEqual((runner, results), ("go", {"TestSlug": "passed", "TestTabs": "failed"}))


class Refused(unittest.TestCase):
    def test_no_criteria(self):
        code, result = run(criteria="-", stdin="Just a paragraph with no list.\n")
        self.assertEqual((code, result["reason"]), (2, "no_criteria_found"))

    def test_duplicate_ids(self):
        code, result = run(criteria="-", stdin="## Acceptance criteria\n- AC-1: a\n- AC-1: b\n")
        self.assertEqual((code, result["reason"]), (2, "duplicate_criterion_id"))

    def test_evidence_that_is_not_json(self):
        code, result = run(evidence="-", stdin="AC-1 done, trust me\n")
        self.assertEqual((code, result["reason"]), (2, "bad_evidence"))

    def test_evidence_object_without_an_evidence_list(self):
        code, result = run(evidence="-", stdin=json.dumps({"entries": [{"criterion": "AC-1", "kind": "file"}]}))
        self.assertEqual((code, result["reason"]), (2, "bad_evidence"))

    def test_two_inputs_from_standard_input(self):
        code, result = run(criteria="-", evidence="-")
        self.assertEqual((code, result["reason"]), (2, "bad_arguments"))

    def test_missing_and_outside_files(self):
        code, result = run(criteria="examples/missing.md")
        self.assertEqual((code, result["reason"]), (2, "input_missing"))
        code, result = run(criteria=str(Path(sys.executable).resolve()))
        self.assertEqual((code, result["reason"]), (2, "path_outside_root"))

    def test_bytes_that_are_not_utf8(self):
        code, result = run(criteria="-", stdin=b"\xff\xfe")
        self.assertEqual((code, result["reason"]), (2, "input_not_utf8"))

    def test_input_above_the_size_bound(self):
        code, result = run(criteria="-", stdin=b"x" * (TOOL.MAX_INPUT_BYTES + 1))
        self.assertEqual((code, result["reason"]), (2, "input_too_large"))


if __name__ == "__main__":
    unittest.main()
