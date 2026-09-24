---
name: "verify-fail-then-pass-evidence"
description: "Check two saved test outputs and a diff to confirm that the named new test failed before the fix, passes after it, and that no previously passing test now fails."
license: MIT
compatibility: "Python 3.10 or later, standard library only. Reads saved output of pytest, python -m unittest, go test, cargo test or a JUnit XML report."
metadata:
  version: "0.1.0"
---
# Verify fail-then-pass test evidence

A new test proves a fix only when it failed before the fix, passes after it, and every test that passed before still passes. The bundled script checks this from saved files. It runs no tests.

## When to use it

Use it after a fix step and before anyone calls the ticket done. You need:

- BEFORE: the saved test output from before the fix, with the new test already written;
- AFTER: the saved output of the same test command after the fix;
- DIFF: the diff of the whole change from the base revision, new test and fix together;
- the id of each new test, as the runner prints it.

## First action

From the workspace root, run the script. SKILL_DIR is the folder that holds this file. If you do not know it, run `ls -d .*/skills/verify-fail-then-pass-evidence` and use the folder it prints.

```bash
python3 -I -B SKILL_DIR/scripts/verify_fail_then_pass.py --before BEFORE --after AFTER --diff DIFF --test NEW_TEST_ID
```

## Steps

1. Replace BEFORE, AFTER and DIFF with relative paths, and NEW_TEST_ID with an id such as `tests/test_dates.py::test_rejects_day_32`.
2. Add one more `--test` for each other new test.
3. Run the command and read the one JSON object it prints.
4. Copy `verdict`, `failures` and `warnings` into your answer word for word.
5. Answer every item in [references/checklist.md](references/checklist.md).

## Checks

- Exit 0, verdict `pass`: every check passed.
- Exit 1, verdict `fail`: each item in `failures` names the check that failed.
- Exit 2, verdict `refused`: an input could not be read; `reason` says why.
- If you doubt the script, run its tests: `python3 -I -B -m unittest discover -s SKILL_DIR/tests -v`.

## Done when

Your answer holds the verdict, the failures, the warnings and one reply for each checklist item.

## Stop and report when

- The script exits 2. Do not retype or edit an output to make it readable.
- `same_runner_format` or `baseline_has_other_tests` failed. Ask for BEFORE and AFTER saved from the same command; do not run the tests again yourself unless your task allows it.
- The verdict is `fail`. Do not change tests, outputs or the diff to turn it into a pass.
- Your test runner is not in [references/runner-formats.md](references/runner-formats.md).

## Known-wrong example

A step writes the new test after the fix, runs the suite once and saves that passing output as BEFORE. The new test was never seen failing, so nothing shows that it can catch the defect. The script fails `new_test_failed_before`.
