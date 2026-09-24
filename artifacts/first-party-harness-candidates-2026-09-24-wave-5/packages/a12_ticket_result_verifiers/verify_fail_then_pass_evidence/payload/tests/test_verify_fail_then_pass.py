"""Tests for scripts/verify_fail_then_pass.py; they read the shipped examples and write no file.

Run from the package root: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_fail_then_pass.py"
NEW_TEST = "tests/test_dates.py::test_rejects_day_32"

SPEC = importlib.util.spec_from_file_location("verify_fail_then_pass", SCRIPT)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def example(name: str) -> str:
    return (ROOT / "examples" / name).read_text(encoding="utf-8")


def run(before="examples/before-run.txt", after="examples/after-run.txt", diff="examples/change.diff",
        tests=(NEW_TEST,), stdin="", extra=()):
    arguments = [sys.executable, "-I", "-B", str(SCRIPT), "--root", str(ROOT), "--before", before,
                 "--after", after, "--diff", diff]
    for test in tests:
        arguments += ["--test", test]
    data = stdin if isinstance(stdin, bytes) else stdin.encode("utf-8")
    done = subprocess.run(arguments + list(extra), input=data, capture_output=True, timeout=60)
    return done.returncode, json.loads(done.stdout.decode("utf-8"))


def failed_checks(result: dict) -> set:
    return {item["check"] for item in result.get("failures", [])}


PYTEST_NINE = """\
tests/a_test.py::test_ok PASSED                                           [ 10%]
tests/a_test.py::test_skipped SKIPPED (not here)                          [ 20%]
tests/a_test.py::test_xfail XFAIL (known)                                 [ 30%]
tests/a_test.py::test_param[x[1]] PASSED                                  [ 40%]
tests/a_test.py::test_param[a b] FAILED                                   [ 50%]
tests/a_test.py::TestUnit::test_sub PASSED                                [ 60%]
SUBPASSED(i=0)                   [ 60%]
tests/a_test.py::TestUnit::test_sub SUBFAILED(i=1)                   [ 60%]
tests/a_test.py::test_fixture_broke ERROR                                 [ 70%]
=========================== short test summary info ============================
XPASS tests/a_test.py::test_xpass - known
FAILED tests/a_test.py::test_param[a b] - AssertionError: assert [1] == [2]
SUBFAILED(i=1) tests/a_test.py::TestUnit::test_sub - AssertionError: 1 != 0
"""

UNITTEST_310 = """\
test_error (test_ut.TestUnit) ... ERROR
test_ok (test_ut.TestUnit)
First docstring line. ... ok
test_sub (test_ut.TestUnit) ... test_xfail (test_ut.TestUnit) ... expected failure
test_skip (test_ut.TestUnit) ... skipped 'skip it'
FAIL: test_sub (test_ut.TestUnit) (i=1)
Ran 5 tests in 0.001s
"""

UNITTEST_314 = """\
test_error (test_ut.TestUnit.test_error) ... ERROR
test_sub (test_ut.TestUnit.test_sub) ...
  test_sub (test_ut.TestUnit.test_sub) (i=1) ... FAIL
test_xpass (test_ut.TestUnit.test_xpass) ... unexpected success
test_ok (test_ut.TestUnit.test_ok) ... ok
"""


class PositiveExample(unittest.TestCase):
    def test_shipped_example_passes(self):
        code, result = run()
        self.assertEqual(code, 0, result)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["compared_previously_passing"], 3)
        self.assertEqual(result["new_tests"][0]["added_at"], "tests/test_dates.py:16")

    def test_short_test_id_is_matched(self):
        code, result = run(tests=("test_rejects_day_32",))
        self.assertEqual(code, 0, result)

    def test_error_before_passes_with_a_warning(self):
        before = example("before-run.txt").replace("test_rejects_day_32 FAILED", "test_rejects_day_32 ERROR")
        before = before.replace("FAILED tests/test_dates.py", "ERROR tests/test_dates.py")
        code, result = run(before="-", stdin=before)
        self.assertEqual(code, 0, result)
        self.assertTrue(any("errored before the fix" in warning for warning in result["warnings"]))


class KnownWrongCases(unittest.TestCase):
    def test_new_test_that_never_failed_is_refused(self):
        code, result = run(before="-", stdin=example("after-run.txt"))
        self.assertEqual(code, 1)
        self.assertIn("new_test_failed_before", failed_checks(result))

    def test_new_test_still_failing_after_the_fix(self):
        after = example("after-run.txt").replace("test_rejects_day_32 PASSED", "test_rejects_day_32 FAILED")
        code, result = run(after="-", stdin=after)
        self.assertEqual(code, 1)
        self.assertIn("new_test_passes_after", failed_checks(result))

    def test_previously_passing_test_that_now_fails(self):
        after = example("after-run.txt").replace("test_sums_rows PASSED", "test_sums_rows FAILED")
        code, result = run(after="-", stdin=after)
        self.assertEqual(code, 1)
        self.assertIn("no_previously_passing_test_fails", failed_checks(result))
        self.assertEqual(result["regressions"]["newly_failing"], ["tests/test_totals.py::test_sums_rows"])

    def test_previously_passing_test_missing_after(self):
        after = "\n".join(line for line in example("after-run.txt").splitlines() if "test_sums_rows" not in line)
        code, result = run(after="-", stdin=after + "\n")
        self.assertEqual(code, 1)
        self.assertEqual(result["regressions"]["missing_after"], ["tests/test_totals.py::test_sums_rows"])

    def test_previously_passing_test_now_skipped(self):
        after = example("after-run.txt").replace("test_parses_day_first PASSED", "test_parses_day_first SKIPPED (slow)")
        code, result = run(after="-", stdin=after)
        self.assertEqual(code, 1)
        self.assertEqual(result["regressions"]["now_skipped"], ["tests/test_dates.py::test_parses_day_first"])

    def test_diff_that_changes_only_tests(self):
        diff = example("change.diff")
        only_tests = diff[diff.index("diff --git a/tests/"):]
        code, result = run(diff="-", stdin=only_tests)
        self.assertEqual(code, 1)
        self.assertIn("diff_changes_non_test_file", failed_checks(result))

    def test_diff_that_does_not_add_the_new_test(self):
        diff = example("change.diff")
        only_fix = diff[:diff.index("diff --git a/tests/")]
        code, result = run(diff="-", stdin=only_fix)
        self.assertEqual(code, 1)
        self.assertIn("diff_adds_new_test", failed_checks(result))

    def test_before_run_holding_only_the_new_test(self):
        before = "tests/test_dates.py::test_rejects_day_32 FAILED [100%]\n"
        code, result = run(before="-", stdin=before)
        self.assertEqual(code, 1)
        self.assertIn("baseline_has_other_tests", failed_checks(result))

    def test_other_new_failure_after(self):
        after = example("after-run.txt") + "tests/test_dates.py::test_new_helper FAILED [100%]\n"
        code, result = run(after="-", stdin=after)
        self.assertEqual(code, 1)
        self.assertIn("no_new_failures_after", failed_checks(result))

    def test_test_skipped_before_and_failing_after_is_a_new_failure(self):
        before = example("before-run.txt") + "tests/test_totals.py::test_rounds_half_up SKIPPED (needs locale)\n"
        after = example("after-run.txt") + "tests/test_totals.py::test_rounds_half_up FAILED [100%]\n"
        result = TOOL.judge(before, after, example("change.diff"), [NEW_TEST])
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("no_new_failures_after", failed_checks(result))
        self.assertEqual(result["regressions"]["new_failures_after"], ["tests/test_totals.py::test_rounds_half_up"])

    def test_test_failing_before_and_after_is_only_a_warning(self):
        before = example("before-run.txt") + "tests/test_totals.py::test_rounds_half_up FAILED [100%]\n"
        after = example("after-run.txt") + "tests/test_totals.py::test_rounds_half_up FAILED [100%]\n"
        result = TOOL.judge(before, after, example("change.diff"), [NEW_TEST])
        self.assertEqual(result["verdict"], "pass", result)
        self.assertEqual(result["still_failing"], ["tests/test_totals.py::test_rounds_half_up"])
        self.assertTrue(any("failed both before and after" in warning for warning in result["warnings"]))

    def test_outputs_of_two_different_runners(self):
        unittest_before = ("test_parses_day_first (tests.test_dates.DateTests.test_parses_day_first) ... ok\n"
                           "test_rejects_day_32 (tests.test_dates.DateTests.test_rejects_day_32) ... FAIL\n")
        code, result = run(before="-", stdin=unittest_before, tests=("test_rejects_day_32",))
        self.assertEqual(code, 1)
        self.assertIn("same_runner_format", failed_checks(result))

    def test_quiet_pytest_output_gets_a_hint(self):
        quiet = ("..F.                                                                     [100%]\n"
                 "=========================== short test summary info ============================\n"
                 "FAILED tests/test_dates.py::test_rejects_day_32 - Failed: DID NOT RAISE\n"
                 "1 failed, 3 passed in 0.05s\n")
        code, result = run(before="-", stdin=quiet)
        self.assertEqual(code, 1)
        failure = [item for item in result["failures"] if item["check"] == "baseline_has_other_tests"][0]
        self.assertIn("-v or -rA", failure["detail"])


class RefusedInput(unittest.TestCase):
    def test_unrecognized_output(self):
        code, result = run(before="-", stdin="all good, trust me\n")
        self.assertEqual((code, result["verdict"], result["reason"]), (2, "refused", "no_test_results"))

    def test_path_outside_root(self):
        code, result = run(before="../outside.txt")
        self.assertEqual((code, result["reason"]), (2, "path_outside_root"))

    def test_absolute_path_outside_root(self):
        code, result = run(before=str(Path(sys.executable).resolve()))
        self.assertEqual((code, result["reason"]), (2, "path_outside_root"))

    def test_missing_file(self):
        code, result = run(after="examples/no-such-file.txt")
        self.assertEqual((code, result["reason"]), (2, "input_missing"))

    def test_bytes_that_are_not_utf8(self):
        code, result = run(before="-", stdin=b"\xff\xfe\x00")
        self.assertEqual((code, result["reason"]), (2, "input_not_utf8"))

    def test_input_above_the_size_bound(self):
        code, result = run(before="-", stdin=b"x" * (TOOL.MAX_INPUT_BYTES + 1))
        self.assertEqual((code, result["reason"]), (2, "input_too_large"))

    def test_two_inputs_from_standard_input(self):
        code, result = run(before="-", after="-")
        self.assertEqual((code, result["reason"]), (2, "bad_arguments"))

    def test_missing_test_argument_still_prints_json(self):
        code, result = run(tests=())
        self.assertEqual((code, result["reason"]), (2, "bad_arguments"))

    def test_combined_diff_of_a_merge(self):
        code, result = run(diff="-", stdin="diff --cc tests/test_a.py\nindex 1111111,2222222..3333333\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@@ -1,1 -1,1 +1,1 @@@\n- a\n -b\n++c\n")
        self.assertEqual((code, result["reason"]), (2, "combined_diff"))

    def test_unreadable_diff(self):
        code, result = run(diff="-", stdin="this is not a diff\n")
        self.assertEqual((code, result["reason"]), (2, "unreadable_diff"))

    def test_ambiguous_short_id(self):
        results = {"tests/a_test.py::test_x": "failed", "tests/b_test.py::test_x": "passed"}
        with self.assertRaises(TOOL.Refused) as caught:
            TOOL.match_requested("test_x", results, "pytest")
        self.assertEqual(caught.exception.reason, "ambiguous_test_id")


class Parsers(unittest.TestCase):
    def test_pytest_nine_lines(self):
        results = TOOL.parse_pytest(PYTEST_NINE)
        self.assertEqual(results["tests/a_test.py::test_skipped"], "skipped")
        self.assertEqual(results["tests/a_test.py::test_xfail"], "xfailed")
        self.assertEqual(results["tests/a_test.py::test_xpass"], "xpassed")
        self.assertEqual(results["tests/a_test.py::test_param[x[1]]"], "passed")
        self.assertEqual(results["tests/a_test.py::test_param[a b]"], "failed")
        self.assertEqual(results["tests/a_test.py::TestUnit::test_sub"], "failed")
        self.assertEqual(results["tests/a_test.py::test_fixture_broke"], "error")

    def test_unittest_python_310_and_314(self):
        old = TOOL.parse_unittest(UNITTEST_310)
        self.assertEqual(old, {"test_ut.TestUnit.test_error": "error", "test_ut.TestUnit.test_ok": "passed",
                               "test_ut.TestUnit.test_xfail": "xfailed", "test_ut.TestUnit.test_skip": "skipped",
                               "test_ut.TestUnit.test_sub": "failed"})
        new = TOOL.parse_unittest(UNITTEST_314)
        self.assertEqual(new["test_ut.TestUnit.test_sub"], "failed")
        self.assertEqual(new["test_ut.TestUnit.test_xpass"], "xpassed")
        self.assertEqual(new["test_ut.TestUnit.test_ok"], "passed")

    def test_go_verbose_and_json(self):
        verbose = "=== RUN   TestParse\n    --- PASS: TestParse/empty_input (0.00s)\n--- FAIL: TestParse (0.00s)\n"
        self.assertEqual(TOOL.parse_go(verbose), {"TestParse/empty_input": "passed", "TestParse": "failed"})
        events = '{"Action":"run","Test":"TestA"}\n{"Action":"pass","Package":"p","Test":"TestA","Elapsed":0}\n'
        self.assertEqual(TOOL.parse_go(events), {"TestA": "passed"})

    def test_cargo_lines(self):
        text = "running 3 tests\ntest dates::parses ... ok\ntest dates::rejects ... FAILED\n" \
               "test dates::slow ... ignored\ntest result: FAILED. 1 passed; 1 failed; 1 ignored\n"
        self.assertEqual(TOOL.parse_cargo(text), {"dates::parses": "passed", "dates::rejects": "failed",
                                                  "dates::slow": "skipped"})

    def test_junit_xml(self):
        text = ('<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="s">'
                '<testcase classname="tests.test_dates" name="test_ok"/>'
                '<testcase classname="tests.test_dates" name="test_bad"><failure message="x"/></testcase>'
                '<testcase classname="tests.test_dates" name="test_xf"><skipped type="pytest.xfail"/></testcase>'
                '</testsuite></testsuites>')
        self.assertEqual(TOOL.parse_output(text, "auto", "sample"),
                         ("junit", {"tests.test_dates.test_ok": "passed", "tests.test_dates.test_bad": "failed",
                                    "tests.test_dates.test_xf": "xfailed"}))

    def test_junit_with_declarations_is_refused(self):
        with self.assertRaises(TOOL.Refused):
            TOOL.parse_junit('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><testsuite/>')

    def test_a_repeated_test_id_keeps_its_most_severe_result(self):
        rerun = "tests/a_test.py::test_x FAILED [ 50%]\ntests/a_test.py::test_x PASSED [100%]\n"
        self.assertEqual(TOOL.parse_pytest(rerun), {"tests/a_test.py::test_x": "failed"})

    def test_parameter_cases_are_grouped(self):
        results = {"t/a_test.py::test_p[1]": "failed", "t/a_test.py::test_p[2]": "passed"}
        ids, how = TOOL.match_requested("t/a_test.py::test_p", results, "pytest")
        self.assertEqual((ids, how), (["t/a_test.py::test_p[1]", "t/a_test.py::test_p[2]"], "parameter_cases"))
        self.assertEqual(TOOL.group_outcome(ids, results, "before"), "failed")
        self.assertEqual(TOOL.group_outcome(ids, results, "after"), "failed")


class DiffParsing(unittest.TestCase):
    def test_git_extended_headers(self):
        text = (
            'diff --git "a/docs/caf\\303\\251.md" "b/docs/caf\\303\\251.md"\n'
            "new file mode 100644\nindex 0000000..e69de29\n"
            "diff --git a/old name.py b/new name.py\nsimilarity index 100%\n"
            "rename from old name.py\nrename to new name.py\n"
            "diff --git a/logo.png b/logo.png\nindex 1111111..2222222 100644\n"
            "Binary files a/logo.png and b/logo.png differ\n"
            "diff --git a/gone.py b/gone.py\ndeleted file mode 100644\n--- a/gone.py\n+++ /dev/null\n"
            "@@ -1 +0,0 @@\n-x = 1\n\\ No newline at end of file\n"
        )
        files = TOOL.parse_diff(text)
        self.assertEqual([(item.path, item.change) for item in files],
                         [("docs/caf\u00e9.md", "added"), ("new name.py", "renamed"), ("logo.png", "modified"),
                          ("gone.py", "deleted")])
        self.assertTrue(files[2].binary)

    def test_hunk_longer_than_its_header_is_refused(self):
        text = "--- a/x.py\n+++ b/x.py\n@@ -1,1 +1,1 @@\n-a\n+b\n+c\n"
        files = TOOL.parse_diff(text)
        self.assertEqual(len(files[0].hunks[0]["lines"]), 2)
        with self.assertRaises(TOOL.Refused):
            TOOL.parse_diff("--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,2 @@\n-a\n")
        with self.assertRaises(TOOL.Refused):
            TOOL.parse_diff("--- a/x.py\n+++ b/x.py\n@@ -1,1 +1,2 @@\n-a\n-b\n+c\n+d\n")

    def test_go_subtest_and_parameter_case_are_found(self):
        diff = ("--- a/parse_test.go\n+++ b/parse_test.go\n@@ -3,0 +4,1 @@\n"
                '+\tt.Run("empty input", func(t *testing.T) {\n')
        found = TOOL.find_added_definition("TestParse/empty_input", "go", TOOL.parse_diff(diff), [], "")
        self.assertEqual(found["how"], "go_subtest")
        diff = ("--- a/tests/test_p.py\n+++ b/tests/test_p.py\n@@ -3,0 +4,1 @@\n"
                '+    ("2025-13-01", None),\n')
        found = TOOL.find_added_definition("tests/test_p.py::test_p[2025-13-01]", "pytest", TOOL.parse_diff(diff), [],
                                           "2025-13-01")
        self.assertEqual(found["how"], "parameter_case")


class Patterns(unittest.TestCase):
    def test_glob_segments(self):
        self.assertTrue(TOOL.glob_regex("src/**/*.py").match("src/a.py"))
        self.assertTrue(TOOL.glob_regex("src/**/*.py").match("src/x/y/a.py"))
        self.assertFalse(TOOL.glob_regex("*.py").match("src/a.py"))
        self.assertTrue(TOOL.glob_regex("checks/{unit,e2e}/**").match("checks/e2e/a.py"))
        with self.assertRaises(TOOL.Refused):
            TOOL.glob_regex("../outside/**")

    def test_test_paths(self):
        self.assertTrue(TOOL.is_test_path("pkg/parse_test.go", []))
        self.assertTrue(TOOL.is_test_path("web/app.spec.ts", []))
        self.assertFalse(TOOL.is_test_path("src/latest_report.py", []))
        self.assertTrue(TOOL.is_test_path("checks/probe_dates.py", [TOOL.glob_regex("checks/**")]))


if __name__ == "__main__":
    unittest.main()
