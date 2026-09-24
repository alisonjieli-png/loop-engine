---
name: "select-tests-for-changed-files"
description: "List the test files that import, directly or through local modules, the Python files changed in a diff, so a step runs the narrowest relevant tests before the full suite."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---
# Select Python tests for changed files

After a change, run the tests that can see it first. The script reads the imports of every Python file, without running any of them, and follows them from each test to the changed files.

## When to use it

Use it after you edit Python files and before you run tests, when the full suite is slow or its output is too long for your working notes.

## First action

Pipe the current diff into the script from the repository root. `SKILL_FOLDER` is the folder that holds this file. If you do not know its path, run `ls -d .*/skills/select-tests-for-changed-files` and use the folder it prints.

```bash
git diff HEAD | python3 -I -B SKILL_FOLDER/scripts/select_tests.py --root . --diff -
```

New files that git does not track yet are not in the diff; add each one with `--changed PATH`. Without git, name every changed file that way. The result has the shape of `examples/selection-output.json`.

## Steps

1. Read `status`.
2. If it is `selected`, run only `test_paths` with the project's own test command, for example `python3 -m pytest -q tests/test_prices.py tests/test_checkout.py`.
3. If it is `full_suite_recommended`, read the reason in `untraced_changes`, then run the full suite.
4. When a selected test fails, read its `reasons[].via`; it is the import chain from the test to your change.
5. If the step requires it, run the full suite after the selected tests pass.
6. Record `test_paths`, `untested_changes` and the test results in your step notes.

## Checks

- Exit status: 0 means run `test_paths` first; 1 means run the full suite now; 2 means the input was refused.
- Every changed file in `changed` has `tests` above 0, has kind `documentation`, or appears in `untested_changes` or `untraced_changes`.
- `warnings` is empty, or each warning is copied into your notes.

## Done when

The selected tests ran and their result is in your notes, together with any changed file that no test covers.

## Stop and report when

- `status` is `full_suite_recommended` and the full suite cannot run in this step.
- `status` is `none_selected`: no test imports the change. Report it; do not claim the change is tested.
- The script exits with status 2.

## Known-wrong example

After editing `src/shop/prices.py`, running only `tests/test_prices.py` because the names match misses `tests/test_checkout.py`, which imports `shop.checkout`, which imports `shop.prices`. The script selects both and prints that chain in `via`.
