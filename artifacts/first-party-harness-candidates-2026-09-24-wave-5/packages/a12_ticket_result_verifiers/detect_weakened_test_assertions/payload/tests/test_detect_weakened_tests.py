"""Tests for scripts/detect_weakened_tests.py; they read the shipped examples and write no file.

Most diffs here are made by difflib.unified_diff, a producer independent of the parser.
Run from the package root: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import difflib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "detect_weakened_tests.py"

SPEC = importlib.util.spec_from_file_location("detect_weakened_tests", SCRIPT)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def run(*arguments, stdin=""):
    data = stdin if isinstance(stdin, bytes) else stdin.encode("utf-8")
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(ROOT), *arguments],
                          input=data, capture_output=True, timeout=60)
    return done.returncode, json.loads(done.stdout.decode("utf-8"))


def change(path: str, old: str, new: str, context: int = 3) -> str:
    lines = difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile="a/" + path, tofile="b/" + path,
                                 lineterm="", n=context)
    return "\n".join(lines) + "\n"


def kinds(result: dict) -> list:
    return sorted(item["kind"] for item in result.get("weakening", []) + result.get("review", []))


def check(path: str, old: str, new: str, *extra, context: int = 3):
    return run("--diff", "-", *extra, stdin=change(path, old, new, context))


class Examples(unittest.TestCase):
    def test_honest_change_passes(self):
        code, result = run("--diff", "examples/honest-test-change.diff")
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)
        self.assertEqual(result["files"]["not_scanned"], 1)

    def test_weakened_example_is_refused_with_locations(self):
        code, result = run("--diff", "examples/weakened-tests.diff")
        self.assertEqual((code, result["verdict"]), (1, "fail"))
        self.assertEqual(kinds(result), ["assertion_removed", "assertion_rewritten", "skip_mark_added",
                                         "test_function_deleted", "tolerance_widened"])
        rewritten = result["review"][0]
        self.assertEqual((rewritten["old_line"], rewritten["new_line"]), (8, 8))
        self.assertEqual(rewritten["new_text"], "assert order_total(rows) == 10")
        removed = [item for item in result["weakening"] if item["kind"] == "assertion_removed"][0]
        self.assertEqual((removed["path"], removed["old_line"]), ("tests/test_totals.py", 14))


class Python(unittest.TestCase):
    OLD = "def test_total():\n    rows = make_rows()\n    assert total(rows) == 11\n    assert len(rows) == 2\n"

    def test_changed_expected_value_needs_a_reason(self):
        code, result = check("tests/test_a.py", self.OLD, self.OLD.replace("== 11", "== 10"))
        self.assertEqual((code, result["verdict"], kinds(result)), (1, "review", ["assertion_rewritten"]))

    def test_commented_out_assertion_is_a_removal(self):
        code, result = check("tests/test_a.py", self.OLD, self.OLD.replace("    assert len", "    # assert len"))
        self.assertEqual(kinds(result), ["assertion_removed"])

    def test_whitespace_and_moves_are_not_findings(self):
        moved = "def test_total():\n    rows = make_rows()\n    assert len(rows) == 2\n    assert total(rows)  ==  11\n"
        code, result = check("tests/test_a.py", self.OLD, moved)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)

    def test_marks_and_places(self):
        new = "@unittest.expectedFailure\n" + self.OLD
        self.assertEqual(kinds(check("tests/test_a.py", self.OLD, new)[1]), ["expected_failure_mark_added"])
        old = "def test_mean(self):\n    self.assertAlmostEqual(mean(v), 0.5, places=7)\n"
        new = "def test_mean(self):\n    self.assertAlmostEqual(mean(v), 0.5, places=2)\n"
        self.assertEqual(kinds(check("tests/test_m.py", old, new)[1]), ["tolerance_widened"])

    def test_tolerance_constant_and_exact_check_made_approximate(self):
        old, new = "TOLERANCE = 0.01\n", "TOLERANCE = 0.5\n"
        self.assertEqual(kinds(check("tests/conftest.py", old, new)[1]), ["tolerance_widened"])
        old = "def test_share(self):\n    self.assertEqual(share(1, 3), 0.33)\n"
        new = "def test_share(self):\n    self.assertAlmostEqual(share(1, 3), 0.33)\n"
        self.assertEqual(kinds(check("tests/test_s.py", old, new)[1]), ["tolerance_introduced"])

    def test_renamed_and_deleted_functions(self):
        old = "def test_total():\n    assert total([1]) == 1\n\n\ndef test_empty():\n    assert total([]) == 0\n"
        new = "def test_total_of_one_row():\n    assert total([1]) == 1\n"
        code, result = check("tests/test_a.py", old, new)
        self.assertEqual(kinds(result), ["test_function_deleted", "test_function_renamed"])
        deleted = result["weakening"][0]
        self.assertIn("assertion lines inside it: 1", deleted["detail"])

    def test_style_and_format_values_are_not_tolerances(self):
        old = ("STYLE = dict(margin=8)\n\n\ndef test_label():\n    text = fmt(0.5, precision=2)\n"
               "    assert text == \"0.50\"\n")
        new = old.replace("margin=8", "margin=16").replace("precision=2", "precision=1").replace('"0.50"', '"0.5"')
        code, result = check("tests/test_view.py", old, new)
        self.assertEqual((code, kinds(result)), (1, ["assertion_rewritten"]))

    def test_tolerance_names_with_a_suffix_count_on_any_line(self):
        old, new = "ABS_TOL = 1e-9\nsettings = load(default_tolerance=0.01)\n", \
            "ABS_TOL = 1e-3\nsettings = load(default_tolerance=0.1)\n"
        self.assertEqual(kinds(check("tests/conftest.py", old, new)[1]), ["tolerance_widened", "tolerance_widened"])

    def test_model_fit_is_not_a_focus_mark(self):
        new = self.OLD + "\n\ndef test_fit():\n    model.fit(rows, labels)\n    assert model.score(rows) > 0.9\n"
        code, result = check("tests/test_a.py", self.OLD, new)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)


class MultiLineChecks(unittest.TestCase):
    CALL = ("class T(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(\n"
            "            order_total(rows),\n            11,\n        )\n")

    def test_expected_value_on_its_own_line_needs_a_reason(self):
        code, result = check("tests/test_a.py", self.CALL, self.CALL.replace("11,", "10,"))
        self.assertEqual((code, kinds(result)), (1, ["assertion_rewritten"]))
        self.assertEqual(result["review"][0]["new_text"], "self.assertEqual( order_total(rows), 10, )")

    def test_tolerance_on_its_own_line_is_widened(self):
        old = "def test_mean():\n    assert mean(v) == pytest.approx(\n        1.5,\n        rel=1e-6,\n    )\n"
        code, result = check("tests/test_m.py", old, old.replace("rel=1e-6", "rel=0.5"))
        self.assertEqual((code, kinds(result)), (1, ["tolerance_widened"]))

    def test_head_above_the_context_gives_a_warning_and_more_context_finds_it(self):
        old = "\n".join(f"line_{number} = {number}" for number in range(12)) + "\n" + self.CALL.replace(
            "            order_total(rows),\n", "            order_total(\n                rows,\n            ),\n")
        new = old.replace("            11,\n", "            10,\n")
        code, result = check("tests/test_h.py", old, new)
        self.assertEqual((code, result["verdict"]), (0, "pass"))
        self.assertTrue(any("-U10" in warning for warning in result["warnings"]))
        code, result = check("tests/test_h.py", old, new, context=10)
        self.assertEqual((code, kinds(result)), (1, ["assertion_rewritten"]))

    def test_docstring_text_is_not_a_check(self):
        old = 'def test_doc():\n    """We assert the (odd case\n    across lines.\n    """\n    assert f() == 1\n'
        code, result = check("tests/test_d.py", old, old.replace("across lines.", "over two lines."))
        self.assertEqual((code, result["verdict"], result["warnings"]), (0, "pass", []), result)


class NewWeakeningKinds(unittest.TestCase):
    CASES = ('@pytest.mark.parametrize("value, expected", [\n    (1, 1),\n    (2, 4),\n    (3, 9),\n])\n'
             "def test_square(value, expected):\n    assert square(value) == expected\n")

    def test_parameter_case_removed_or_commented_out(self):
        for new in (self.CASES.replace("    (3, 9),\n", ""), self.CASES.replace("    (3, 9),\n", "    # (3, 9),\n")):
            code, result = check("tests/test_p.py", self.CASES, new)
            self.assertEqual((code, kinds(result)), (1, ["parameter_case_removed"]))
            self.assertIn("(3, 9)", result["weakening"][0]["detail"])
        old = '@pytest.mark.parametrize("x", [1, 2, 3])\ndef test_x(x):\n    assert f(x)\n'
        code, result = check("tests/test_p.py", old, old.replace("[1, 2, 3]", "[1, 2]"))
        self.assertEqual((code, kinds(result)), (1, ["parameter_case_removed"]))

    def test_parameter_case_changed_needs_a_reason_and_an_added_case_passes(self):
        code, result = check("tests/test_p.py", self.CASES, self.CASES.replace("(3, 9)", "(3, 10)"))
        self.assertEqual((code, kinds(result)), (1, ["parameter_case_changed"]))
        code, result = check("tests/test_p.py", self.CASES, self.CASES.replace("    (3, 9),\n", "    (3, 9),\n    (4, 16),\n"),
                             context=10)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)

    def test_check_made_always_true(self):
        old = "def test_x():\n    assert f() == 1\n"
        for new in ("def test_x():\n    assert f() == 1 or True\n", "def test_x():\n    assert True\n"):
            code, result = check("tests/test_x.py", old, new)
            self.assertEqual((code, kinds(result)), (1, ["assertion_made_trivial"]))
        old = "class T(unittest.TestCase):\n    def test_x(self):\n        self.assertEqual(f(), 3)\n"
        code, result = check("tests/test_x.py", old, old.replace("self.assertEqual(f(), 3)", "self.assertTrue(True)"))
        self.assertEqual((code, kinds(result)), (1, ["assertion_made_trivial"]))

    def test_bare_return_before_a_check(self):
        old = "def test_x():\n    value = f()\n    assert value == 1\n"
        code, result = check("tests/test_x.py", old, old.replace("    value = f()\n", "    value = f()\n    return\n"))
        self.assertEqual((code, kinds(result)), (1, ["early_exit_added"]))
        self.assertEqual(result["weakening"][0]["new_line"], 3)

    def test_return_of_a_nested_function_is_not_an_early_exit(self):
        old = ("class T(unittest.TestCase):\n    def test_missing(self):\n        value = 1\n"
               "        with self.assertRaises(KeyError):\n            load(value)\n")
        new = old.replace("        value = 1\n", "        value = 1\n\n        def load(key):\n            return None\n")
        code, result = check("tests/test_x.py", old, new)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)
        old = "def test_rows():\n    rows = load()\n    if rows:\n        assert len(rows) == 2\n"
        new = ("def test_rows():\n    def load():\n        return\n    rows = load()\n    if rows:\n"
               "        assert len(rows) == 2\n")
        code, result = check("tests/test_rows.py", old, new)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)

    def test_return_in_a_helper_before_the_next_test_is_not_an_early_exit(self):
        old = "def make(flag):\n    value = 1\n\n\ndef test_x():\n    assert make(True) == 1\n"
        new = old.replace("    value = 1\n", "    value = 1\n    if flag:\n        return\n")
        code, result = check("tests/test_x.py", old, new)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)


class OtherLanguages(unittest.TestCase):
    JS = ('describe("cart", () => {\n  it("counts items", () => {\n    const cart = makeCart();\n'
          "    expect(cart.count()).toBe(2);\n    expect(cart.total()).toBe(11);\n  });\n});\n")

    def test_javascript_expect_removed_inside_a_callback_body(self):
        code, result = check("web/cart.test.js", self.JS, self.JS.replace("    expect(cart.total()).toBe(11);\n", ""))
        self.assertEqual((code, kinds(result)), (1, ["assertion_removed"]))
        self.assertEqual(result["weakening"][0]["old_line"], 5)

    def test_javascript_object_literal_value_changed(self):
        old = 'it("maps", () => {\n  expect(build()).toEqual({\n    a: 1,\n    b: 2,\n  });\n});\n'
        code, result = check("web/map.test.js", old, old.replace("b: 2", "b: 3"))
        self.assertEqual((code, kinds(result)), (1, ["assertion_rewritten"]))

    def test_javascript_skip_focus_and_digits(self):
        old = "it('adds', () => {\n  expect(add(0.1, 0.2)).toBeCloseTo(0.3, 5);\n});\n"
        new = "it.only('adds', () => {\n  expect(add(0.1, 0.2)).toBeCloseTo(0.3, 1);\n});\nxit('later', () => {});\n"
        found = kinds(check("web/add.test.js", old, new)[1])
        self.assertIn("deselection_added", found)
        self.assertIn("skip_mark_added", found)
        self.assertIn("tolerance_widened", found)

    def test_go_skip_delta_and_deleted_test(self):
        old = ("func TestMean(t *testing.T) {\n\tassert.InDelta(t, 1.0, mean(v), 0.01)\n}\n\n"
               "func TestEmpty(t *testing.T) {\n\tif mean(nil) != 0 {\n\t\tt.Fatalf(\"want 0\")\n\t}\n}\n")
        new = "func TestMean(t *testing.T) {\n\tt.Skip(\"slow\")\n\tassert.InDelta(t, 1.0, mean(v), 0.5)\n}\n"
        found = kinds(check("stats/mean_test.go", old, new)[1])
        self.assertEqual(found, ["skip_mark_added", "test_function_deleted", "tolerance_widened"])

    def test_rust_attributes(self):
        old = "#[test]\nfn parses() {\n    assert_eq!(parse(\"1\"), 1);\n}\n"
        new = "#[test]\n#[ignore]\nfn parses() {\n    assert_eq!(parse(\"1\"), 1);\n}\n"
        self.assertEqual(kinds(check("src/parse_tests.rs", old, new)[1]), ["skip_mark_added"])
        gone = "fn parses() {\n    assert_eq!(parse(\"1\"), 1);\n}\n"
        code, result = check("src/parse_tests.rs", old, gone)
        self.assertEqual(kinds(result), ["test_function_deleted"])
        self.assertIn("parses", result["weakening"][0]["detail"])

    def test_configuration_deselection(self):
        old = "[tool.pytest.ini_options]\naddopts = \"-q\"\n"
        new = "[tool.pytest.ini_options]\naddopts = \"-q -k 'not slow_total'\"\n"
        self.assertEqual(kinds(check("pyproject.toml", old, new)[1]), ["deselection_added"])
        old = "jobs:\n  test:\n    steps:\n      - run: pytest -q\n"
        new = "jobs:\n  test:\n    steps:\n      - run: pytest -q --deselect tests/test_a.py::test_total\n"
        self.assertEqual(kinds(check(".github/workflows/ci.yml", old, new)[1]), ["deselection_added"])
        old, new = "[pytest]\naddopts = -q\n", "[pytest]\naddopts = -q --ignore=tests/test_slow.py\n"
        self.assertEqual(kinds(check("tests/pytest.ini", old, new)[1]), ["deselection_added"])

    def test_runner_flags_inside_a_test_body_are_not_deselection(self):
        old = "def test_cli():\n    result = run_cli([\"src\"])\n    assert result.code == 0\n"
        new = old + "\n\ndef test_cli_ignores_build():\n    result = run_cli([\"--ignore=build\", \"src\"])\n" \
                    "    assert result.code == 0\n"
        code, result = check("tests/test_cli.py", old, new)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)


class Files(unittest.TestCase):
    def test_deleted_test_file(self):
        diff = ("diff --git a/tests/test_old.py b/tests/test_old.py\ndeleted file mode 100644\n"
                "--- a/tests/test_old.py\n+++ /dev/null\n@@ -1,4 +0,0 @@\n-def test_a():\n-    assert a()\n"
                "-def test_b():\n-    assert b()\n")
        code, result = run("--diff", "-", stdin=diff)
        self.assertEqual(kinds(result), ["test_file_deleted"])
        self.assertIn("2 test definitions", result["weakening"][0]["detail"])

    def test_reordered_functions_keep_their_skip_mark(self):
        first = "@pytest.mark.skip(reason=\"slow\")\ndef test_a():\n    assert a() == 1\n"
        second = ("def test_b():\n    rows = make_rows()\n    value = b(rows)\n    assert value == 2\n"
                  "    assert len(rows) == 3\n")
        diff = change("tests/test_ab.py", first + "\n\n" + second, second + "\n\n" + first)
        self.assertIn("+@pytest.mark.skip", diff)
        code, result = run("--diff", "-", stdin=diff)
        self.assertEqual((code, result["verdict"]), (0, "pass"), result)

    def test_test_file_renamed_out_of_the_test_folders_is_still_scanned(self):
        diff = ("diff --git a/tests/test_total.py b/src/total_examples.py\nsimilarity index 80%\n"
                "rename from tests/test_total.py\nrename to src/total_examples.py\n"
                "--- a/tests/test_total.py\n+++ b/src/total_examples.py\n@@ -1,3 +1,2 @@\n"
                " def test_total():\n     rows = make_rows()\n-    assert total(rows) == 11\n")
        code, result = run("--diff", "-", stdin=diff)
        self.assertEqual((code, kinds(result)), (1, ["assertion_removed"]))

    def test_files_outside_the_test_paths(self):
        old, new = "def check_total():\n    assert total() == 1\n", "def check_total():\n    pass\n"
        code, result = check("checks/total_checks.py", old, new)
        self.assertEqual((code, result["verdict"]), (0, "pass"))
        self.assertTrue(result["warnings"])
        code, result = check("checks/total_checks.py", old, new, "--test-glob", "checks/**")
        self.assertEqual(kinds(result), ["assertion_removed"])
        code, result = check("checks/total_checks.py", old, new, "--all-files")
        self.assertEqual(kinds(result), ["assertion_removed"])


class Refused(unittest.TestCase):
    def test_unreadable_diff(self):
        code, result = run("--diff", "-", stdin="the tests are fine\n")
        self.assertEqual((code, result["reason"]), (2, "unreadable_diff"))

    def test_combined_diff_of_a_merge(self):
        code, result = run("--diff", "-", stdin="diff --cc tests/test_a.py\nindex 1111111,2222222..3333333\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@@ -1,1 -1,1 +1,1 @@@\n- a\n -b\n++c\n")
        self.assertEqual((code, result["reason"]), (2, "combined_diff"))

    def test_hunk_longer_than_its_header(self):
        diff = "--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1,1 +1,2 @@\n-a\n-b\n+c\n+d\n"
        code, result = run("--diff", "-", stdin=diff)
        self.assertEqual((code, result["reason"]), (2, "unreadable_diff"))

    def test_path_outside_root(self):
        code, result = run("--diff", "../change.diff")
        self.assertEqual((code, result["reason"]), (2, "path_outside_root"))
        code, result = run("--diff", str(Path(sys.executable).resolve()))
        self.assertEqual((code, result["reason"]), (2, "path_outside_root"))

    def test_bytes_that_are_not_utf8(self):
        code, result = run("--diff", "-", stdin=b"\xff\xfe")
        self.assertEqual((code, result["reason"]), (2, "input_not_utf8"))

    def test_input_above_the_size_bound(self):
        code, result = run("--diff", "-", stdin=b"x" * (TOOL.MAX_INPUT_BYTES + 1))
        self.assertEqual((code, result["reason"]), (2, "input_too_large"))

    def test_missing_argument_still_prints_json(self):
        code, result = run()
        self.assertEqual((code, result["reason"]), (2, "bad_arguments"))


if __name__ == "__main__":
    unittest.main()
