"""Tests for scripts/extract_failures.py. Effects: starts the script as a subprocess with data on standard input; writes no files.

The fixtures follow the shape of real pytest 9, unittest (Python 3.10 and 3.14) and
JUnit XML output, rewritten with synthetic paths under /srv/shop.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "extract_failures.py"
EXAMPLE = PAYLOAD / "examples" / "pytest-short-output.json"

PYTEST_LONG = """============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /srv/shop
collected 6 items

tests/test_prices.py .FF.FE                                              [100%]

==================================== ERRORS ====================================
______________________ ERROR at setup of test_uses_broken ______________________

    @pytest.fixture
    def broken():
>       raise RuntimeError("fixture exploded")
E       RuntimeError: fixture exploded

tests/test_prices.py:21: RuntimeError
=================================== FAILURES ===================================
__________________________________ test_comma __________________________________

    def test_comma():
>       assert parse_price("3,50") == 350
               ^^^^^^^^^^^^^^^^^^^

tests/test_prices.py:9:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src/shop/prices.py:3: in parse_price
    return _to_cents(text.strip())
           ^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

text = '3,50'

    def _to_cents(text):
        whole, _, frac = text.partition(".")
>       return int(whole) * 100 + int(frac or 0)
               ^^^^^^^^^^
E       ValueError: invalid literal for int() with base 10: '3,50'

src/shop/prices.py:7: ValueError
------------------------------ Captured stdout call ------------------------------
debug line one that must not reach the result
_________________________________ test_padding _________________________________

    def test_padding():
>       assert parse_price(" 2.05 ") == 250
E       AssertionError: assert 205 == 250
E        +  where 205 = parse_price(' 2.05 ')

tests/test_prices.py:12: AssertionError
_________________________ TestBulk.test_many[1.5-150] __________________________

self = <test_prices.TestBulk object at 0x7f00aa00bb00>, text = '1.5'
cents = 150

    @pytest.mark.parametrize("text,cents", [("1.00", 100), ("1.5", 150)])
    def test_many(self, text, cents):
>       assert parse_price(text) == cents
E       AssertionError: assert 105 == 150
E        +  where 105 = parse_price('1.5')

tests/test_prices.py:17: AssertionError
=========================== short test summary info ============================
FAILED tests/test_prices.py::test_comma - ValueError: invalid literal for int...
FAILED tests/test_prices.py::test_padding - AssertionError: assert 205 == 250
FAILED tests/test_prices.py::TestBulk::test_many[1.5-150] - AssertionError: a...
ERROR tests/test_prices.py::test_uses_broken - RuntimeError: fixture exploded
===================== 3 failed, 2 passed, 1 error in 0.02s =====================
"""

PYTEST_SHORT = """=================================== FAILURES ===================================
__________________________________ test_comma __________________________________
tests/test_prices.py:9: in test_comma
    assert parse_price("3,50") == 350
           ^^^^^^^^^^^^^^^^^^^
src/shop/prices.py:3: in parse_price
    return _to_cents(text.strip())
           ^^^^^^^^^^^^^^^^^^^^^^^
src/shop/prices.py:7: in _to_cents
    return int(whole) * 100 + int(frac or 0)
           ^^^^^^^^^^
E   ValueError: invalid literal for int() with base 10: '3,50'
_________________________________ test_padding _________________________________
tests/test_prices.py:12: in test_padding
    assert parse_price(" 2.05 ") == 250
E   AssertionError: assert 205 == 250
E    +  where 205 = parse_price(' 2.05 ')
=========================== short test summary info ============================
FAILED tests/test_prices.py::test_comma - ValueError: invalid literal for int...
FAILED tests/test_prices.py::test_padding - AssertionError: assert 205 == 250
========================= 2 failed, 4 passed in 0.02s ==========================
"""

PYTEST_LINE = """rootdir: /srv/shop
=================================== FAILURES ===================================
E   ValueError: invalid literal for int() with base 10: '3,50'
/srv/shop/src/shop/prices.py:7: ValueError: invalid literal for int() with base 10: '3,50'
E   AssertionError: assert 205 == 250
     +  where 205 = parse_price(' 2.05 ')
/srv/shop/tests/test_prices.py:12: AssertionError: assert 205 == 250
=========================== short test summary info ============================
FAILED tests/test_prices.py::test_comma - ValueError: invalid literal for int...
FAILED tests/test_prices.py::test_padding - AssertionError: assert 205 == 250
2 failed, 4 passed in 0.01s
"""

PYTEST_LINE_XPASS = """rootdir: /srv/shop
=================================== FAILURES ===================================
E   ValueError: invalid literal for int() with base 10: '3,50'
/srv/shop/src/shop/prices.py:3: ValueError: invalid literal for int() with base 10: '3,50'
[XPASS(strict)] known
[XPASS(strict)] known
E   AssertionError: assert 1 == 2
     +  where 1 = parse_price('0.01')
----------------------------- Captured stdout call -----------------------------
tests/debug_helper_test.py:9: note printed by the code under test
/srv/shop/tests/test_prices.py:40: AssertionError: assert 1 == 2
=========================== short test summary info ============================
FAILED tests/test_prices.py::test_comma - ValueError: invalid literal for int...
FAILED tests/test_prices.py::test_strict_pass - [XPASS(strict)] known
FAILED tests/test_prices.py::test_prints - AssertionError: assert 1 == 2
3 failed, 1 passed in 0.03s
"""

PYTEST_NATIVE = """rootdir: /srv/shop
=================================== FAILURES ===================================
__________________________________ test_comma __________________________________
Traceback (most recent call last):
  File "/usr/lib/python3.12/site-packages/_pytest/runner.py", line 361, in from_call
    result: TResult | None = func()
  File "/usr/lib/python3.12/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/srv/shop/tests/test_prices.py", line 9, in test_comma
    assert parse_price("3,50") == 350
  File "/srv/shop/src/shop/prices.py", line 3, in parse_price
    return _to_cents(text.strip())
  File "/srv/shop/src/shop/prices.py", line 7, in _to_cents
    return int(whole) * 100 + int(frac or 0)
           ~~~^^^^^^^
ValueError: invalid literal for int() with base 10: '3,50'
=========================== short test summary info ============================
FAILED tests/test_prices.py::test_comma - ValueError: invalid literal for int...
========================= 1 failed, 5 passed in 0.03s ==========================
"""

PYTEST_LIBRARY_LAST = """rootdir: /srv/shop
=================================== FAILURES ===================================
_________________________________ test_report __________________________________
tests/test_report.py:14: in test_report
    build_report(rows)
src/shop/report.py:22: in build_report
    return table.pivot(index="day")
/usr/lib/python3.12/site-packages/tablekit/frame.py:880: in pivot
    raise KeyError(index)
E   KeyError: 'day'
=========================== short test summary info ============================
FAILED tests/test_report.py::test_report - KeyError: 'day'
========================= 1 failed, 9 passed in 0.40s ==========================
"""

PYTEST_SUMMARY_ONLY = """=========================== short test summary info ============================
FAILED tests/test_prices.py::test_comma - ValueError: invalid literal for int...
ERROR tests/test_prices.py::test_uses_broken - RuntimeError: fixture exploded
===================== 1 failed, 4 passed, 1 error in 0.01s =====================
"""

UNITTEST_314 = """tests.test_missing (unittest.loader._FailedTest.tests.test_missing) ... ERROR
test_padding (tests.test_prices.PriceTests.test_padding) ... FAIL
test_plain (tests.test_prices.PriceTests.test_plain) ... ok
test_sub (tests.test_prices.PriceTests.test_sub) ...
  test_sub (tests.test_prices.PriceTests.test_sub) (text='1.5') ... FAIL

======================================================================
ERROR: tests.test_missing (unittest.loader._FailedTest.tests.test_missing)
----------------------------------------------------------------------
ImportError: Failed to import test module: tests.test_missing
Traceback (most recent call last):
  File "/usr/lib/python3.14/unittest/loader.py", line 426, in _find_test_path
    module = self._get_module_from_name(name)
  File "/srv/shop/tests/test_missing.py", line 1, in <module>
    import shop.nothing_here
ModuleNotFoundError: No module named 'shop.nothing_here'


======================================================================
FAIL: test_padding (tests.test_prices.PriceTests.test_padding)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/srv/shop/tests/test_prices.py", line 13, in test_padding
    self.assertEqual(parse_price(" 2.05 "), 250)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 205 != 250

======================================================================
FAIL: test_sub (tests.test_prices.PriceTests.test_sub) (text='1.5')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/srv/shop/tests/test_prices.py", line 18, in test_sub
    self.assertEqual(parse_price(text), cents)
AssertionError: 105 != 150

----------------------------------------------------------------------
Ran 4 tests in 0.001s

FAILED (failures=2, errors=1)
"""

UNITTEST_310 = """======================================================================
ERROR: test_comma (tests.test_prices.PriceTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/srv/shop/tests/test_prices.py", line 10, in test_comma
    self.assertEqual(parse_price("3,50"), 350)
  File "/srv/shop/shop/prices.py", line 3, in parse_price
    return _to_cents(text.strip())
  File "/srv/shop/shop/prices.py", line 7, in _to_cents
    return int(whole) * 100 + int(frac or 0)
ValueError: invalid literal for int() with base 10: '3,50'

----------------------------------------------------------------------
Ran 3 tests in 0.000s

FAILED (errors=1)
"""

PYTEST_CHAINED_LONG = """rootdir: /srv/shop
=================================== FAILURES ===================================
_________________________________ test_lookup __________________________________

    def test_lookup():
        try:
>           {}["missing"]
E           KeyError: 'missing'

tests/test_report.py:15: KeyError

The above exception was the direct cause of the following exception:

    def test_lookup():
        try:
            {}["missing"]
        except KeyError as error:
>           raise ValueError("lookup failed for the report") from error
E           ValueError: lookup failed for the report

tests/test_report.py:17: ValueError
_______________________________ test_strict_pass _______________________________
[XPASS(strict)] known bug in the parser
=========================== short test summary info ============================
FAILED tests/test_report.py::test_lookup - ValueError: lookup failed for the...
FAILED tests/test_report.py::test_strict_pass - [XPASS(strict)] known bug i...
========================= 2 failed, 3 passed in 0.02s ==========================
"""

PYTEST_LINE_CHAINED_AND_LIBRARY = """rootdir: /srv/shop
=================================== FAILURES ===================================
E   KeyError: 'day'
/srv/shop/vendor/site-packages/tablekit/frame.py:2: KeyError: 'day'
E   KeyError: 'missing'

The above exception was the direct cause of the following exception:
E   ValueError: lookup failed for the report
/srv/shop/tests/test_report.py:17: ValueError: lookup failed for the report
=========================== short test summary info ============================
FAILED tests/test_report.py::test_day_key - KeyError: 'day'
FAILED tests/test_report.py::test_lookup - ValueError: lookup failed for the...
2 failed in 0.02s
"""

UNITTEST_310_VERBOSE = """test_missing (unittest.loader._FailedTest) ... ERROR
test_ok (tests.test_prices.PriceTests) ... ok
test_sub (tests.test_prices.PriceTests) ... test_surprise (tests.test_prices.PriceTests) ... unexpected success
test_wrong (tests.test_prices.PriceTests) ... FAIL

======================================================================
ERROR: test_missing (unittest.loader._FailedTest)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_missing
Traceback (most recent call last):
  File "/srv/shop/tests/test_missing.py", line 1, in <module>
    import shop.nothing_here
ModuleNotFoundError: No module named 'shop.nothing_here'


======================================================================
ERROR: setUpClass (tests.test_prices.NeedsDatabase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/srv/shop/tests/test_prices.py", line 40, in setUpClass
    raise RuntimeError("no database")
RuntimeError: no database

======================================================================
FAIL: test_sub (tests.test_prices.PriceTests) (text='0.5')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/srv/shop/tests/test_prices.py", line 22, in test_sub
    self.assertEqual(to_cents(text), cents)
AssertionError: 5 != 50

======================================================================
FAIL: test_sub (tests.test_prices.PriceTests) (text='2.5')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/srv/shop/tests/test_prices.py", line 22, in test_sub
    self.assertEqual(to_cents(text), cents)
AssertionError: 205 != 250

======================================================================
FAIL: test_wrong (tests.test_prices.PriceTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/srv/shop/tests/test_prices.py", line 17, in test_wrong
    self.assertEqual(to_cents("0.5"), 50)
AssertionError: 5 != 50

----------------------------------------------------------------------
Ran 5 tests in 0.001s

FAILED (failures=3, errors=2, unexpected successes=1)
"""

UNITTEST_OK = """test_plain (tests.test_prices.PriceTests.test_plain) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.000s

OK
"""

JUNIT_PYTEST = """<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests"><testsuite name="pytest" errors="1" failures="1" skipped="1" tests="4" time="0.025"><testcase classname="tests.test_prices" name="test_plain" time="0.000" /><testcase classname="tests.test_prices" name="test_comma" time="0.000"><failure message="ValueError: invalid literal for int() with base 10: '3,50'">def test_comma():
&gt;       assert parse_price("3,50") == 350

tests/test_prices.py:9:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src/shop/prices.py:3: in parse_price
    return _to_cents(text.strip())
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
&gt;       return int(whole) * 100 + int(frac or 0)
E       ValueError: invalid literal for int() with base 10: '3,50'

src/shop/prices.py:7: ValueError</failure></testcase><testcase classname="tests.test_prices" name="test_later" time="0.000"><skipped message="not ready" /></testcase><testcase classname="tests.test_prices" name="test_uses_broken" time="0.000"><error message="failed on setup with &quot;RuntimeError: fixture exploded&quot;">@pytest.fixture
    def broken():
&gt;       raise RuntimeError("fixture exploded")
E       RuntimeError: fixture exploded

tests/test_prices.py:21: RuntimeError</error></testcase><system-out>a very long captured log that must not appear</system-out></testsuite></testsuites>
"""

JUNIT_JAVA = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="shop.PriceParserTest" tests="2" failures="1" errors="0" skipped="0">
  <testcase name="parsesComma" classname="shop.PriceParserTest" time="0.01">
    <failure message="expected: &lt;350&gt; but was: &lt;35&gt;" type="org.opentest4j.AssertionFailedError">org.opentest4j.AssertionFailedError: expected: &lt;350&gt; but was: &lt;35&gt;
	at org.junit.jupiter.api.AssertionUtils.fail(AssertionUtils.java:151)
	at org.junit.jupiter.api.Assertions.assertEquals(Assertions.java:562)
	at shop.PriceParser.check(PriceParser.java:40)
	at shop.PriceParserTest.parsesComma(PriceParserTest.java:17)
</failure>
  </testcase>
  <testcase name="parsesDot" classname="shop.PriceParserTest" time="0.01"/>
</testsuite>
"""


class ExtractFailures(unittest.TestCase):
    def run_script(self, data, *arguments):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments],
                              input=data.encode("utf-8") if isinstance(data, str) else data,
                              capture_output=True, cwd=str(PAYLOAD), timeout=60)
        return done.returncode, json.loads(done.stdout.decode("utf-8"))

    def test_pytest_long_output_keeps_every_failure_and_leaves_logs_out(self):
        code, result = self.run_script(PYTEST_LONG, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "failures_found")
        self.assertEqual(result["format"], "pytest")
        self.assertEqual(result["totals"]["failed"], 3)
        self.assertEqual(result["totals"]["errors"], 1)
        self.assertTrue(result["consistency"]["matches"])
        ids = [item["id"] for item in result["failures"]]
        self.assertIn("tests/test_prices.py::TestBulk::test_many[1.5-150]", ids)
        comma = next(item for item in result["failures"] if item["id"].endswith("::test_comma"))
        self.assertEqual(comma["exception"], "ValueError")
        self.assertEqual(comma["first_project_frame"], {"path": "src/shop/prices.py", "line": 7,
                                                        "function": "_to_cents"})
        self.assertEqual(comma["test_frame"]["path"], "tests/test_prices.py")
        broken = next(item for item in result["failures"] if item["kind"] == "error")
        self.assertEqual(broken["phase"], "setup")
        self.assertEqual(broken["id"], "tests/test_prices.py::test_uses_broken")
        self.assertNotIn("debug line one", json.dumps(result))

    def test_pytest_short_output_matches_the_example_file(self):
        code, result = self.run_script(PYTEST_SHORT)
        self.assertEqual(code, 1)
        expected = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(result, expected)

    def test_pytest_line_mode_pairs_messages_with_summary_ids(self):
        code, result = self.run_script(PYTEST_LINE, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        first, second = result["failures"]
        self.assertEqual(first["id"], "tests/test_prices.py::test_comma")
        self.assertEqual(first["first_project_frame"]["path"], "src/shop/prices.py")
        self.assertEqual(second["message"], "AssertionError: assert 205 == 250")

    def test_line_mode_keeps_ids_aligned_after_a_strict_unexpected_pass(self):
        code, result = self.run_script(PYTEST_LINE_XPASS, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        self.assertTrue(result["consistency"]["matches"])
        by_id = {item["id"]: item for item in result["failures"]}
        self.assertEqual(by_id["tests/test_prices.py::test_comma"]["first_project_frame"]["path"], "src/shop/prices.py")
        prints = by_id["tests/test_prices.py::test_prints"]
        self.assertEqual(prints["message"], "AssertionError: assert 1 == 2")
        self.assertEqual((prints["first_project_frame"]["path"], prints["first_project_frame"]["line"]),
                         ("tests/test_prices.py", 40))
        strict = by_id["tests/test_prices.py::test_strict_pass"]
        self.assertEqual((strict["message"], strict["first_project_frame"]), ("[XPASS(strict)] known", None))
        self.assertNotIn("note printed", json.dumps(result))
        self.assertNotIn("debug_helper", json.dumps(result))

    def test_native_traceback_skips_runner_frames(self):
        code, result = self.run_script(PYTEST_NATIVE, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        frame = result["failures"][0]["first_project_frame"]
        self.assertEqual(frame, {"path": "src/shop/prices.py", "line": 7, "function": "_to_cents"})

    def test_known_wrong_library_frame_is_never_named_first(self):
        code, result = self.run_script(PYTEST_LIBRARY_LAST)
        self.assertEqual(code, 1)
        frame = result["failures"][0]["first_project_frame"]
        self.assertEqual(frame["path"], "src/shop/report.py")
        self.assertEqual(frame["line"], 22)
        self.assertNotIn("site-packages", frame["path"])

    def test_summary_only_output_still_lists_ids(self):
        code, result = self.run_script(PYTEST_SUMMARY_ONLY)
        self.assertEqual(code, 1)
        self.assertEqual(len(result["failures"]), 2)
        self.assertTrue(result["consistency"]["matches"])
        self.assertIn("notes", result["failures"][0])

    def test_passing_and_empty_pytest_runs(self):
        code, result = self.run_script("tests/test_a.py ....\n============ 4 passed in 0.01s ============\n")
        self.assertEqual((code, result["status"]), (0, "no_failures"))
        code, result = self.run_script("============ no tests ran in 0.01s ============\n")
        self.assertEqual((code, result["status"]), (1, "no_tests_ran"))

    def test_unittest_new_format_with_import_error_and_subtest(self):
        code, result = self.run_script(UNITTEST_314, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        self.assertEqual(result["format"], "unittest")
        self.assertTrue(result["consistency"]["matches"])
        missing = result["failures"][0]
        self.assertEqual((missing["id"], missing["phase"]), ("tests.test_missing", "import"))
        self.assertEqual(missing["exception"], "ModuleNotFoundError")
        self.assertEqual(missing["first_project_frame"]["path"], "tests/test_missing.py")
        sub = result["failures"][2]
        self.assertEqual(sub["id"], "tests.test_prices.PriceTests.test_sub")
        self.assertEqual(sub["subtest"], "(text='1.5')")
        self.assertEqual(sub["message"], "AssertionError: 105 != 150")

    def test_unittest_old_format_names_the_deepest_project_frame(self):
        code, result = self.run_script(UNITTEST_310, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        item = result["failures"][0]
        self.assertEqual(item["id"], "tests.test_prices.PriceTests.test_comma")
        self.assertEqual(item["first_project_frame"], {"path": "shop/prices.py", "line": 7, "function": "_to_cents"})
        self.assertEqual(result["totals"]["errors"], 1)

    def test_chained_exception_reports_the_last_one_and_keeps_the_cause(self):
        code, result = self.run_script(PYTEST_CHAINED_LONG, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        self.assertTrue(result["consistency"]["matches"])
        lookup = next(item for item in result["failures"] if item["id"].endswith("::test_lookup"))
        self.assertEqual(lookup["exception"], "ValueError")
        self.assertEqual(lookup["message"], "ValueError: lookup failed for the report")
        self.assertEqual(lookup["cause"], "KeyError: 'missing'")
        self.assertEqual(lookup["first_project_frame"], {"path": "tests/test_report.py", "line": 17,
                                                         "function": "test_lookup"})
        self.assertIn("chained exceptions", lookup["notes"][0])

    def test_strict_unexpected_pass_keeps_its_full_reason(self):
        code, result = self.run_script(PYTEST_CHAINED_LONG, "--project-root", "/srv/shop")
        strict = next(item for item in result["failures"] if item["id"].endswith("::test_strict_pass"))
        self.assertEqual(strict["message"], "[XPASS(strict)] known bug in the parser")
        self.assertIsNone(strict["first_project_frame"])
        self.assertIn("expected failure (strict)", strict["notes"][0])

    def test_line_mode_chain_and_library_only_frames(self):
        code, result = self.run_script(PYTEST_LINE_CHAINED_AND_LIBRARY, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        by_id = {item["id"]: item for item in result["failures"]}
        day = by_id["tests/test_report.py::test_day_key"]
        self.assertIsNone(day["first_project_frame"])
        self.assertIn("outside the project", day["notes"][0])
        lookup = by_id["tests/test_report.py::test_lookup"]
        self.assertEqual((lookup["exception"], lookup["cause"]), ("ValueError", "KeyError: 'missing'"))
        self.assertEqual(lookup["message"], "ValueError: lookup failed for the report")

    def test_unittest_counts_each_failing_test_once_and_names_unexpected_successes(self):
        code, result = self.run_script(UNITTEST_310_VERBOSE, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        self.assertTrue(result["consistency"]["matches"])
        self.assertEqual(result["totals"]["passed"], 1)
        kinds = {item["id"]: item["kind"] for item in result["failures"]}
        self.assertEqual(kinds["tests.test_prices.PriceTests.test_surprise"], "unexpected_success")
        setup = next(item for item in result["failures"] if item.get("phase") == "class setup")
        self.assertEqual(setup["id"], "tests.test_prices.NeedsDatabase.setUpClass")
        self.assertEqual(result["notes"], [])

    def test_unittest_passing_run(self):
        code, result = self.run_script(UNITTEST_OK)
        self.assertEqual((code, result["status"], result["totals"]["passed"]), (0, "no_failures", 1))

    def test_junit_xml_from_pytest(self):
        code, result = self.run_script(JUNIT_PYTEST)
        self.assertEqual(code, 1)
        self.assertEqual(result["format"], "junit")
        self.assertEqual(result["totals"], {"tests": 4, "failed": 1, "errors": 1, "skipped": 1, "passed": 1})
        comma = result["failures"][0]
        self.assertEqual(comma["id"], "tests.test_prices.test_comma")
        self.assertEqual(comma["first_project_frame"]["path"], "src/shop/prices.py")
        self.assertNotIn("very long captured log", json.dumps(result))

    def test_junit_xml_with_java_frames(self):
        code, result = self.run_script(JUNIT_JAVA)
        self.assertEqual(code, 1)
        item = result["failures"][0]
        self.assertEqual(item["exception"], "org.opentest4j.AssertionFailedError")
        self.assertEqual(item["first_project_frame"]["function"], "shop.PriceParser.check")

    def test_xml_with_a_document_type_is_refused(self):
        data = '<?xml version="1.0"?><!DOCTYPE t [<!ENTITY a "aaaa">]><testsuite><testcase name="x"/></testsuite>\n'
        code, result = self.run_script(data)
        self.assertEqual((code, result["status"]), (2, "refused"))

    def test_unrecognized_output_is_not_a_pass(self):
        code, result = self.run_script("/usr/bin/python3: No module named pytest\n")
        self.assertEqual((code, result["status"]), (1, "no_result_found"))

    def test_crash_traceback_is_reported(self):
        text = ("Traceback (most recent call last):\n"
                '  File "/srv/shop/src/shop/cli.py", line 4, in <module>\n'
                "    import yaml\n"
                "ModuleNotFoundError: No module named 'yaml'\n")
        code, result = self.run_script(text, "--project-root", "/srv/shop")
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"][0]["kind"], "crash")
        self.assertEqual(result["failures"][0]["first_project_frame"]["path"], "src/shop/cli.py")

    def test_bounds_and_paths_are_refused(self):
        code, result = self.run_script("x" * 64, "--max-bytes", "10")
        self.assertEqual((code, result["status"]), (2, "refused"))
        code, result = self.run_script("", "../outside.txt")
        self.assertEqual((code, result["status"]), (2, "refused"))
        code, result = self.run_script("", str(PAYLOAD / "SKILL.md"), "--root", str(PAYLOAD / "scripts"))
        self.assertEqual((code, result["status"]), (2, "refused"))

    def test_reads_a_file_inside_the_root(self):
        code, result = self.run_script("", "SKILL.md", "--root", str(PAYLOAD))
        self.assertEqual((code, result["status"]), (1, "no_result_found"))

    def test_max_failures_keeps_exact_counts(self):
        code, result = self.run_script(PYTEST_LONG, "--max-failures", "1")
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["omitted_failures"], 3)
        self.assertEqual(result["consistency"]["extracted"], 4)

    def test_skill_file_names_this_script(self):
        text = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/extract_failures.py", text)
        self.assertIn("examples/pytest-short-output.json", text)


if __name__ == "__main__":
    unittest.main()
