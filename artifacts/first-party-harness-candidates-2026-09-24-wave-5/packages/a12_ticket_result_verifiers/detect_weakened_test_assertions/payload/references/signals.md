# What the script looks for

| Kind | Verdict | Meaning |
|---|---|---|
| `assertion_removed` | fail | A removed check with no similar check added in the same hunk, or a check turned into a line that checks nothing. A check turned into a comment counts as removed. |
| `assertion_made_trivial` | fail | A check replaced by one that is always true, such as `assert True`, `assert x == 1 or True`, `self.assertTrue(True)`, `assertEqual(a, a)` or `expect(true).toBe(true)`. |
| `early_exit_added` | fail | A new bare `return` placed before a check in the same block, so the check never runs. |
| `skip_mark_added` | fail | A new skip, such as `pytest.mark.skip`, `pytest.skip()`, `unittest.skip`, `self.skipTest()`, `it.skip`, `xit`, `test.todo`, `t.Skip()`, `#[ignore]`, `@Disabled`, `@Ignore`, `[Ignore]` or `markTestSkipped()`. A condition such as `skipUnless` still counts. |
| `expected_failure_mark_added` | fail | A new expected failure: `pytest.mark.xfail`, `unittest.expectedFailure`, `test.failing` or `#[should_panic]`. |
| `deselection_added` | fail | A new focus or filter that leaves tests out: `it.only`, `fit`, `--deselect`, `-k "not ..."`, `collect_ignore`, `testPathIgnorePatterns` or `--ignore=`. |
| `tolerance_widened` | fail | A tolerance that accepts more results: a larger `rel`, `abs`, `rtol`, `atol`, `delta`, `epsilon`, `tol` or `tolerance`, or fewer `places`, `decimal` or `digits`. Positional forms of `toBeCloseTo`, `assertAlmostEqual`, `InDelta`, `approx` and `assert_allclose` count too. |
| `parameter_case_removed` | fail | Fewer cases in a `pytest.mark.parametrize`, `parameterized.expand` or `test.each` list, including a case turned into a comment, or the whole list removed. |
| `test_function_deleted` | fail | A removed test definition with no similar name added in the same hunk. |
| `test_file_deleted` | fail | A deleted test file. |
| `assertion_rewritten` | review | A check replaced by a similar but different check, such as a new expected value. |
| `tolerance_introduced` | review | An exact check replaced by an approximate one. |
| `parameter_case_changed` | review | A parameter case whose values changed, or a parameter list the script cannot count. |
| `test_function_renamed` | review | A test definition replaced by a similar name. |

## How lines are compared

- Test files are the files in folders named test, tests, testing, `__tests__`, spec, specs or e2e, and files named like `test_x.py`, `x_test.go`, `x.spec.ts` or `XTest.java`. Add others with `--test-glob`, or scan every file with `--all-files`.
- Test settings such as `pyproject.toml`, `pytest.ini`, `package.json`, Jest or Vitest settings and CI workflow files are scanned for deselection only.
- Lines are grouped into statements: a statement goes on while a bracket stays open, so a check written over several lines is one check. In JavaScript, Go, Java and similar files, a brace that ends a line opens a block, and each statement inside it stands alone.
- A statement that shares unchanged lines on both sides of the diff was changed in place. A statement that was only removed is paired with a similar added statement in the same hunk; a pair is a rewrite and a removed check without a pair is a removal.
- A statement removed in one place and added unchanged in another place of the same file has moved and is not reported. Changes to spaces are ignored.
- Comment lines and the text inside strings are not checks.
- Check lines are found by names such as `assert`, `assertEqual`, `expect(`, `pytest.raises`, `t.Fatalf`, `require.`, `Assert.` and `assert_eq!`. A project helper such as `check_total()` is not recognized.
- When a changed line sits inside a statement whose first line is above the diff context, the script cannot see the whole statement and says so in `warnings`. Make the diff again with more context.
