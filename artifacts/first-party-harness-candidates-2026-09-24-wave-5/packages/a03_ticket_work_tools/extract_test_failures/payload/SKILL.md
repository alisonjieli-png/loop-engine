---
name: "extract-test-failures"
description: "Parse pytest, unittest or JUnit XML output into a short list of failing tests with the assertion message and the first project frame, leaving out passing noise and long logs."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---
# Extract failures from test output

A long test log hides the few lines you need. This skill reduces it to one JSON list: each failing test, its exception, its message and the project line to open first.

## When to use it

Use it after any pytest, unittest or JUnit XML test run, before you read the log or change code.

## First action

Run the tests from the workspace root and pipe their output into the script. `SKILL_FOLDER` is the folder that holds this file. If you do not know its path, run `ls -d .*/skills/extract-test-failures` and use the folder it prints.

```bash
python3 -m pytest -q 2>&1 | python3 -I -B SKILL_FOLDER/scripts/extract_failures.py -
```

For unittest, use `python3 -m unittest -v 2>&1` before the pipe. For a JUnit XML report, give its path instead of `-`. The result has the shape of `examples/pytest-short-output.json`.

## Steps

1. Read `status`. `failures_found` lists failures. `no_failures` means the run passed.
2. For each item in `failures`, read `id`, `exception`, `message` and `first_project_frame`. A chained exception also has `cause`, the first exception of the chain.
3. Open `first_project_frame.path` at `first_project_frame.line` before any other file. It is the deepest frame in project code; library and standard library frames are already skipped. When it is null, do what the item's `notes` say, for example rerun that test with `--tb=short`.
4. Fix one failure at a time. Rerun only that test id, for example `python3 -m pytest -q "tests/test_prices.py::test_comma"` or `python3 -m unittest shop_tests.PriceTests.test_comma`, then run the script again.
5. Keep the JSON result with your step notes.

## Checks

- Exit status: 0 means no failure, 1 means failures or no usable result, 2 means the input was refused.
- `consistency.matches` is true, so the list agrees with the runner's own summary counts.
- `omitted_failures` is 0, or your notes record how many failures the list left out. Do not rerun the whole suite only to list more.

## Done when

Every failure you will fix in this step is listed with a message and a first project frame, and `consistency.matches` is true.

## Stop and report when

- `status` is `no_result_found` or `no_tests_ran`. The tests did not run; report the first 20 lines of the raw output.
- `consistency.matches` is false.
- The script exits with status 2.

## Known-wrong example

A log ends with `KeyError: 'day'` raised in `site-packages/tablekit/frame.py`. Editing that library file, or the last frame printed, is wrong. The script names `src/shop/report.py` line 22, the project line that passed the bad key.
