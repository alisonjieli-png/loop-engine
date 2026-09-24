"""Tests for scripts/verify_report_claims.py; they read the shipped examples and write no file.

Run from the package root: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_report_claims.py"
PASSING_LOG = "examples/evidence/t201-after-run.txt"
GATE = "examples/evidence/t202-gate.json"
FAILING_LOG = "examples/evidence/t205-after-run.txt"
FAILING_GATE = "examples/evidence/t208-gate.json"
NIGHT = "examples/night-morning-report.json"

SPEC = importlib.util.spec_from_file_location("verify_report_claims", SCRIPT)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(report="-", stdin="", extra=()):
    data = stdin if isinstance(stdin, bytes) else stdin.encode("utf-8")
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(ROOT), "--report", report,
                           *extra], input=data, capture_output=True, timeout=60)
    return done.returncode, json.loads(done.stdout.decode("utf-8"))


def one_claim(evidence, status="verified") -> str:
    return json.dumps({"items": [{"id": "T-9", "status": status, "evidence": evidence}]})


def problems(result: dict) -> set:
    return {problem["problem"] for item in result["unsupported"] for problem in item["problems"]}


def reasons(result: dict) -> set:
    return {reason["reason"] for item in result["needs_reading"] for reason in item["reasons"]}


def night_report(**changes) -> str:
    document = json.loads((ROOT / NIGHT).read_text(encoding="utf-8"))
    document.update(changes)
    return json.dumps(document)


class Examples(unittest.TestCase):
    def test_json_report_passes(self):
        code, result = run("examples/night-report.json")
        self.assertEqual((code, result["verdict"], result["supported"]), (0, "pass", ["T-201", "T-202"]), result)
        self.assertEqual([item["item"] for item in result["not_claims"]], ["T-203", "T-204"])
        self.assertEqual(result["unbound"], [])

    def test_markdown_table_report_passes(self):
        code, result = run("examples/night-report.md")
        self.assertEqual((code, result["format"], result["supported"]), (0, "markdown_table", ["T-201", "T-202"]))

    def test_overclaimed_report_lists_every_unsupported_claim(self):
        code, result = run("examples/night-report-overclaimed.json")
        self.assertEqual((code, result["verdict"]), (1, "fail"))
        found = {item["item"]: {problem["problem"] for problem in item["problems"]} for item in result["unsupported"]}
        self.assertEqual(found, {
            "T-205": {"exit_code_contradicted", "no_passing_gate_evidence"},
            "T-206": {"no_evidence"},
            "T-207": {"digest_mismatch", "no_passing_gate_evidence"},
            "T-208": {"evidence_shows_failure", "no_passing_gate_evidence"}})
        self.assertEqual(result["supported"], ["T-201"])
        self.assertEqual([problem["problem"] for problem in result["report_problems"]], ["count_mismatch"])

    def test_night_morning_report_passes_and_reads_the_reproduction_record(self):
        code, result = run(NIGHT)
        self.assertEqual((code, result["format"], result["supported"]),
                         (0, "night_morning_report_v1", ["T-104/t-104-verification"]), result)
        self.assertEqual([item["item"] for item in result["not_claims"]], ["T-105/t-105-triage", "T-106/t-106-fix"])
        self.assertEqual(result["unbound"][0]["item"], "T-104/t-104-verification")
        self.assertEqual(result["report_problems"], [])
        self.assertEqual([row["shows"] for row in result["evidence"]], ["reproduced", "pass"])
        self.assertEqual(result["warnings"], [])


class NightReport(unittest.TestCase):
    def test_complete_entry_whose_record_shows_a_failure(self):
        document = json.loads(night_report())
        document["complete"][0]["claims"][1]["evidence"] = FAILING_GATE
        code, result = run(stdin=json.dumps(document))
        self.assertEqual(code, 1)
        self.assertEqual(problems(result), {"evidence_shows_failure", "no_passing_gate_evidence"})
        failure = [problem for problem in result["unsupported"][0]["problems"]
                   if problem["problem"] == "evidence_shows_failure"][0]
        self.assertEqual(failure["claim"], "The relevant and full test runs passed after the fix.")

    def test_ticket_counts_and_final_steps(self):
        document = json.loads(night_report())
        document["counts"]["tickets_complete"] = 2
        code, result = run(stdin=json.dumps(document))
        self.assertEqual((code, [item["problem"] for item in result["report_problems"]]), (1, ["count_mismatch"]))
        self.assertIn("tickets_complete", result["report_problems"][0]["detail"])
        document = json.loads(night_report())
        document["tickets"][0]["final_step_id"] = "t-104-release"
        code, result = run(stdin=json.dumps(document))
        self.assertEqual((code, [item["problem"] for item in result["report_problems"]]),
                         (1, ["ticket_final_step_not_complete"]))

    def test_counts_that_differ_from_the_lists(self):
        code, result = run(stdin=night_report(counts={"complete": 2, "blocked": 1, "unfinished": 1,
                                                      "unsupported_claims": 0, "problems": 0}))
        self.assertEqual((code, [item["problem"] for item in result["report_problems"]]), (1, ["count_mismatch"]))

    def test_require_digests_refuses_unbound_citations(self):
        code, result = run(NIGHT, extra=("--require-digests",))
        self.assertEqual((code, result["verdict"]), (1, "fail"))
        self.assertIn("digest_not_cited", problems(result))

    def test_missing_handoff_is_a_problem(self):
        document = json.loads(night_report())
        document["complete"][0]["handoff"] = "examples/handoffs/t-104-gone.json"
        code, result = run(stdin=json.dumps(document))
        self.assertEqual((code, problems(result)), (1, {"handoff_missing"}))

    def test_handoff_files_that_changed_after_the_handoff(self):
        handoff = json.loads((ROOT / "examples/handoffs/t-104-verification.json").read_text(encoding="utf-8"))
        self.assertEqual(TOOL.compare_handoff(ROOT, "h.json", handoff, {}), ([], []))
        handoff["files"] = [{"path": GATE, "sha256": "0" * 64}, {"path": PASSING_LOG, "sha256": None},
                            {"path": "examples/evidence/gone.txt", "sha256": None}]
        found, reading = TOOL.compare_handoff(ROOT, "h.json", handoff, {})
        self.assertEqual(found, [])
        self.assertEqual([(entry["reason"], entry["path"]) for entry in reading],
                         [("changed_since_handoff", GATE), ("changed_since_handoff", PASSING_LOG)])
        handoff["status"] = "unfinished"
        found, _reading = TOOL.compare_handoff(ROOT, "h.json", handoff, {})
        self.assertEqual([entry["problem"] for entry in found], ["handoff_status_differs"])
        found, reading = TOOL.compare_handoff(ROOT, "h.json", {"status": "complete"}, {})
        self.assertEqual((found, [entry["reason"] for entry in reading]), ([], ["handoff_not_checked"]))

    def test_note_whose_file_is_missing_is_a_warning(self):
        code, result = run(stdin=night_report(notes=[{"text": "T-107 waits for a decision.",
                                                      "evidence": "examples/evidence/t107-note.txt"}]))
        self.assertEqual(code, 0, result)
        self.assertTrue(any("note 1 cites examples/evidence/t107-note.txt" in warning
                            for warning in result["warnings"]))

    def test_other_record_version_is_refused(self):
        code, result = run(stdin=night_report(record_type="night_morning_report/v2"))
        self.assertEqual((code, result["reason"]), (2, "unsupported_report_version"))

    def test_record_without_its_lists_is_refused(self):
        document = json.loads(night_report())
        del document["complete"]
        code, result = run(stdin=json.dumps(document))
        self.assertEqual((code, result["reason"]), (2, "bad_report"))


class Claims(unittest.TestCase):
    def test_citation_without_a_digest_is_unbound_but_can_pass(self):
        code, result = run(stdin=one_claim([{"path": PASSING_LOG, "exit_code": 0}]))
        self.assertEqual((code, result["supported"]), (0, ["T-9"]), result)
        self.assertEqual(result["unbound"], [{"item": "T-9", "paths": [PASSING_LOG]}])
        code, result = run(stdin=one_claim([{"path": PASSING_LOG, "exit_code": 0}]), extra=("--require-digests",))
        self.assertEqual((code, problems(result)), (1, {"digest_not_cited", "no_passing_gate_evidence"}))

    def test_cited_exit_code_that_the_log_contradicts(self):
        code, result = run(stdin=one_claim([{"path": PASSING_LOG, "sha256": digest(PASSING_LOG), "exit_code": 1}]))
        self.assertEqual(code, 1)
        self.assertIn("exit_code_contradicted", problems(result))
        evidence = [{"path": PASSING_LOG, "sha256": digest(PASSING_LOG), "exit_code": 1, "expect_exit": 0}]
        code, result = run(stdin=one_claim(evidence))
        self.assertIn("exit_code_failed", problems(result))

    def test_exit_code_that_the_gate_record_contradicts(self):
        code, result = run(stdin=one_claim([{"path": GATE, "sha256": digest(GATE), "exit_code": 2}]))
        self.assertEqual((code, problems(result)), (1, {"exit_code_contradicted", "no_passing_gate_evidence"}))

    def test_exit_zero_in_the_report_is_not_proof_on_its_own(self):
        path = "examples/night-report.md"
        code, result = run(stdin=one_claim([{"path": path, "sha256": digest(path), "exit_code": 0}]))
        self.assertEqual((code, problems(result)), (1, {"no_passing_gate_evidence"}))

    def test_expected_failure_citation(self):
        evidence = [{"path": FAILING_LOG, "sha256": digest(FAILING_LOG), "expect_exit": 1},
                    {"path": PASSING_LOG, "sha256": digest(PASSING_LOG)}]
        code, result = run(stdin=one_claim(evidence))
        self.assertEqual((code, result["supported"]), (0, ["T-9"]), result)
        code, result = run(stdin=one_claim([{"path": PASSING_LOG, "sha256": digest(PASSING_LOG), "expect_exit": 1}]))
        self.assertIn("expected_failure_not_shown", problems(result))
        code, result = run(stdin=one_claim([{"path": FAILING_LOG, "sha256": digest(FAILING_LOG), "expect_exit": 1}]))
        self.assertEqual(problems(result), {"no_passing_gate_evidence"})

    def test_missing_and_unsafe_evidence(self):
        code, result = run(stdin=one_claim([{"path": "examples/evidence/t999.txt", "sha256": "0" * 64}]))
        self.assertIn("evidence_missing", problems(result))
        code, result = run(stdin=one_claim([{"path": "../night.txt", "sha256": "0" * 64}]))
        self.assertIn("evidence_path_unsafe", problems(result))
        code, result = run(stdin=one_claim([{"path": str(Path(sys.executable).resolve()), "sha256": "0" * 64}]))
        self.assertIn("evidence_path_unsafe", problems(result))
        code, result = run(stdin=one_claim([{"sha256": "0" * 64}]))
        self.assertIn("evidence_path_missing", problems(result))

    def test_malformed_digest_and_exit_values(self):
        code, result = run(stdin=one_claim([{"path": PASSING_LOG, "sha256": "abc", "exit_code": 0}]))
        self.assertIn("digest_malformed", problems(result))
        code, result = run(stdin=one_claim([{"path": PASSING_LOG, "sha256": digest(PASSING_LOG), "exit_code": "0"}]))
        self.assertIn("exit_code_malformed", problems(result))
        code, result = run(stdin=one_claim([{"path": PASSING_LOG, "expect_exit": "1"}]))
        self.assertIn("expect_exit_malformed", problems(result))

    def test_status_words(self):
        code, result = run(stdin=one_claim([], status="\u2705 done"))
        self.assertEqual(problems(result), {"no_evidence"})
        code, result = run(stdin=one_claim([], status="rolled out"))
        self.assertEqual((code, result["verdict"]), (0, "pass"))
        self.assertTrue(any("--claim-word rolled_out" in warning for warning in result["warnings"]))
        code, result = run(stdin=one_claim([], status="rolled out"), extra=("--claim-word", "rolled out"))
        self.assertEqual((code, problems(result)), (1, {"no_evidence"}))
        code, result = run(stdin=one_claim([], status="not done"))
        self.assertEqual((code, result["not_claims"][0]["status"]), (0, "not_done"))

    def test_test_change_only_needs_reading(self):
        evidence = [{"path": GATE, "sha256": digest(GATE)}]
        code, result = run(stdin=one_claim(evidence, status="verified_by_test_change"))
        self.assertEqual((code, result["verdict"], reasons(result)), (1, "review", {"only_tests_changed"}), result)

    def test_failing_run_without_a_stated_expectation_needs_reading(self):
        evidence = [{"path": FAILING_LOG, "text": "The new test failed before the fix."},
                    {"path": GATE, "sha256": digest(GATE)}]
        code, result = run(stdin=one_claim(evidence))
        self.assertEqual((code, result["verdict"], reasons(result)), (1, "review", {"evidence_shows_failure"}))
        reason = result["needs_reading"][0]["reasons"][0]
        self.assertEqual((reason["path"], reason["claim"]), (FAILING_LOG, "The new test failed before the fix."))
        code, result = run(stdin=one_claim([dict(evidence[0], expect_exit=1), evidence[1]]))
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)

    def test_passing_citation_of_a_reproduction_record_is_contradicted(self):
        record = "examples/evidence/t104-reproduction.json"
        evidence = [{"path": record, "exit_code": 0}, {"path": GATE, "sha256": digest(GATE)}]
        code, result = run(stdin=one_claim(evidence))
        self.assertEqual((code, problems(result)), (1, {"exit_code_contradicted"}))

    def test_repeated_item_is_a_warning(self):
        item = {"id": "T-9", "status": "blocked"}
        code, result = run(stdin=json.dumps([item, item]))
        self.assertTrue(any("appears 2 times" in warning for warning in result["warnings"]))

    def test_evidence_file_limit(self):
        saved, TOOL.MAX_EVIDENCE_FILES = TOOL.MAX_EVIDENCE_FILES, 1
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                code = TOOL.main(["--root", str(ROOT), "--report", "examples/night-report.json"])
        finally:
            TOOL.MAX_EVIDENCE_FILES = saved
        self.assertEqual((code, json.loads(output.getvalue())["reason"]), (2, "too_many_evidence_files"))


class Records(unittest.TestCase):
    def outcome(self, record: dict) -> str:
        return TOOL.record_outcome(record)["outcome"]

    def test_record_signals(self):
        self.assertEqual(self.outcome({"exit_code": 0}), "pass")
        self.assertEqual(self.outcome({"exit_code": 3}), "fail")
        self.assertEqual(self.outcome({"passed": False}), "fail")
        self.assertEqual(self.outcome({"verdict": "pass"}), "pass")
        self.assertEqual(self.outcome({"conclusion": "failure"}), "fail")
        self.assertEqual(self.outcome({"checks": [{"passed": True}, {"passed": False}]}), "fail")
        self.assertEqual(self.outcome({"failed_checks": ["full_tests_pass"], "verdict": "ready_for_review"}), "fail")
        self.assertEqual(self.outcome({"summary": "all good"}), "unknown")

    def test_a_stated_verdict_outranks_the_exit_code(self):
        seen = TOOL.record_outcome({"verdict": "failing_test_recorded", "exit_code": 1})
        self.assertEqual((seen["outcome"], seen["exit_code"]), ("unknown", 1))
        self.assertIn("failing_test_recorded", seen["unknown_word"])

    def test_junit_xml(self):
        passing = '<?xml version="1.0"?><testsuite><testcase name="a"/><testcase name="b"><skipped/></testcase></testsuite>'
        failing = '<testsuites><testsuite><testcase name="a"><failure message="x"/></testcase></testsuite></testsuites>'
        self.assertEqual(TOOL.observe(passing.encode())["outcome"], "pass")
        self.assertEqual(TOOL.observe(failing.encode())["outcome"], "fail")
        declared = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><testsuite/>'
        self.assertEqual(TOOL.observe(declared.encode())["outcome"], "unreadable")

    def test_unreadable_evidence_is_a_problem(self):
        data = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><testsuite/>'
        cache = {"report.xml": (data, TOOL.observe(data), None)}
        entry = TOOL.citation({"path": "report.xml", "sha256": hashlib.sha256(data).hexdigest()})
        checked = TOOL.check_citation(ROOT, entry, None, cache, False)
        self.assertEqual(([item["problem"] for item in checked["problems"]], checked["shows_pass"]),
                         (["evidence_unreadable"], False))

    def test_reproduction_records(self):
        base = {"record_type": "ticket_reproduction_run/v1", "test_name": "test_x"}
        self.assertEqual(self.outcome(dict(base, verdict="failing_test_recorded", exit_code=1)), "reproduced")
        self.assertEqual(self.outcome(dict(base, verdict="failing_test_recorded", exit_code=0)), "fail")
        self.assertEqual(self.outcome(dict(base, verdict="test_passed", exit_code=0)), "fail")
        self.assertEqual(self.outcome(dict(base, verdict="product_code_changed", exit_code=None)), "fail")

    def test_counts_that_are_not_whole_numbers_are_not_compared(self):
        report = {"items": [{"id": "T-9", "status": "blocked"}], "counts": {"blocked": "one", "total": 1}}
        code, result = run(stdin=json.dumps(report))
        self.assertEqual((code, result["report_problems"]), (0, []))
        self.assertTrue(any("counts.blocked" in warning for warning in result["warnings"]))

    def test_go_json_lines(self):
        lines = ('{"Action":"run","Package":"shop","Test":"TestA"}\n{"Action":"pass","Package":"shop","Test":"TestA"}\n'
                 '{"Action":"fail","Package":"shop"}\n')
        self.assertEqual(TOOL.observe(lines.encode())["outcome"], "fail")
        self.assertEqual(TOOL.observe(b'{"Action":"pass","Package":"shop"}\n{"Action":"pass","Package":"cart"}\n'
                                      )["outcome"], "pass")


class Summaries(unittest.TestCase):
    def test_failure_lines(self):
        for line in ("FAILED (failures=1, errors=2)", "FAILED (skipped=1, unexpected successes=1)",
                     "--- FAIL: TestSlug (0.00s)", "FAIL\texample.com/slug\t0.01s",
                     "test result: FAILED. 3 passed; 1 failed;", "Tests:       1 failed, 7 passed, 8 total",
                     "      Tests  1 failed | 7 passed (8)", "  2 failing", "5 examples, 1 failure",
                     "80% tests passed, 1 tests failed out of 5", "Failed!  - Failed:     1, Passed:     4",
                     "[INFO] BUILD FAILURE", "BUILD FAILED in 2s", "========= 2 errors in 0.20s =========",
                     "1 failed, 5 passed in 0.12s"):
            self.assertEqual(TOOL.text_outcome(line + "\n")[0], "fail", line)

    def test_success_lines(self):
        for line in ("OK (skipped=1)", "ok  \texample.com/slug\t0.012s", "test result: ok. 4 passed; 0 failed;",
                     "Tests:       8 passed, 8 total", "      Tests  8 passed (8)", "  8 passing (12ms)",
                     "5 examples, 0 failures", "100% tests passed, 0 tests failed out of 5",
                     "Passed!  - Failed:     0, Passed:     5", "[INFO] BUILD SUCCESS", "BUILD SUCCESSFUL in 3s",
                     "============ 12 passed in 0.31s ============", "11 passed, 1 xfailed in 0.40s"):
            self.assertEqual(TOOL.text_outcome(line + "\n")[0], "pass", line)
        for line in ("ok then, moving on", "Ran 5 tests in 0.001s", "no tests ran in 0.01s"):
            self.assertEqual(TOOL.text_outcome(line + "\n")[0], "unknown", line)

    def test_a_failure_anywhere_wins(self):
        self.assertEqual(TOOL.text_outcome("1 failed in 0.1s\n3 passed in 0.2s\n")[0], "fail")


class Markdown(unittest.TestCase):
    def test_columns_are_chosen_by_word_priority(self):
        table = ("| Ticket | Files changed | Status | Evidence |\n|---|---|---|---|\n"
                 "| T-1 | `src/a.py` | done | `a.txt` exit 0 |\n")
        items = TOOL.markdown_items(table)
        self.assertEqual((items[0]["item"], items[0]["citations"][0]["path"]), ("T-1", "a.txt"))
        self.assertEqual(items[0]["citations"][0]["exit_code"], 0)

    def test_links_and_backticked_digests(self):
        cell = "[log](logs/t1.txt) sha256: `" + "a" * 64 + "`; `logs/t2.txt` `exit 0`"
        cited = TOOL.cell_citations(cell)
        self.assertEqual([entry["path"] for entry in cited], ["logs/t1.txt", "logs/t2.txt"])
        self.assertEqual((cited[0]["sha256"], cited[1]["exit_code"]), ("a" * 64, 0))

    def test_rows_without_an_id_column(self):
        items = TOOL.markdown_items("| Status | Evidence |\n|---|---|\n| done | `a.txt` exit 0 |\n")
        self.assertEqual(items[0]["item"], "row 1")


class Refused(unittest.TestCase):
    def test_report_without_claims(self):
        code, result = run(stdin="# Night\n\nAll tickets went well.\n")
        self.assertEqual((code, result["reason"]), (2, "no_claims_found"))
        code, result = run(stdin=json.dumps({"items": []}))
        self.assertEqual((code, result["reason"]), (2, "no_claims_found"))

    def test_report_that_is_not_json(self):
        code, result = run(stdin="{ not json")
        self.assertEqual((code, result["reason"]), (2, "bad_report"))

    def test_report_path_outside_root(self):
        code, result = run("../report.json")
        self.assertEqual((code, result["reason"]), (2, "path_outside_root"))

    def test_bytes_that_are_not_utf8(self):
        code, result = run(stdin=b"\xff\xfe")
        self.assertEqual((code, result["reason"]), (2, "input_not_utf8"))

    def test_input_above_the_size_bound(self):
        code, result = run(stdin=b"x" * (TOOL.MAX_INPUT_BYTES + 1))
        self.assertEqual((code, result["reason"]), (2, "input_too_large"))

    def test_missing_argument_still_prints_json(self):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT)], capture_output=True, timeout=60)
        self.assertEqual((done.returncode, json.loads(done.stdout)["reason"]), (2, "bad_arguments"))


if __name__ == "__main__":
    unittest.main()
