---
name: "detect-weakened-test-assertions"
description: "Scan a diff of test files for removed assertions, added skip or expected-failure marks, widened tolerances and deleted test functions, and report each with its location."
license: MIT
compatibility: "Python 3.10 or later, standard library only. Reads a unified diff such as the output of git diff."
metadata:
  version: "0.1.0"
---
# Detect weakened test assertions

A change can make a test suite pass by making the tests ask for less. The bundled script reads the diff and lists every place where a test check was removed, switched off, loosened or rewritten, with its file and line. It judges only what the diff shows.

## When to use it

Use it on any change that touches test files, before a ticket is reported as fixed. It matters most when nobody watched the change being made.

## First action

From the repository root, run the script on the diff. SKILL_DIR is the folder that holds this file. If you do not know it, run `ls -d .*/skills/detect-weakened-test-assertions` and use the folder it prints.

```bash
git diff --no-ext-diff --no-textconv -U10 HEAD | python3 -I -B SKILL_DIR/scripts/detect_weakened_tests.py --diff -
```

## Steps

1. If the task names a base revision, use it instead of HEAD. If the task gives a saved diff file, pass its path to `--diff` instead. Keep `-U10`: ten lines of context let the script see checks that span several lines.
2. Run the command and read the JSON it prints.
3. Copy `verdict`, `warnings` and every item of `weakening` and `review` (kind, path, lines and texts) into your answer.
4. For each `review` item, quote the ticket sentence that asks for the new behavior, or write "no reason found".
5. Answer every item in [references/checklist.md](references/checklist.md).

## Checks

- Exit 0, verdict `pass`: no test check was removed, switched off, loosened or rewritten.
- Exit 1, verdict `fail`: at least one `weakening` item. [references/signals.md](references/signals.md) explains each kind.
- Exit 1, verdict `review`: checks, parameter cases or test names changed, and each change needs a stated reason.
- Exit 2, verdict `refused`: the diff could not be read; `reason` says why.
- A warning that a changed line sits inside a statement that starts above the diff context means the diff needs more context lines. Make it again with a larger `-U` value.

## Done when

The verdict and every finding with its location are in your answer, and each review item has a quoted reason or "no reason found".

## Stop and report when

- The verdict is `fail`. Do not restore, rewrite or delete tests yourself unless your task says so.
- A review item has no reason in the ticket.
- The warning says no test file changed, but you know the change touched tests. Run again with `--test-glob` for their folder.

## Known-wrong example

A test expects `order_total(rows) == 11`, the code returns 10, and a step changes the test to `== 10` so the suite passes. The script reports `assertion_rewritten` with both lines and exits 1, so the change cannot be reported as a plain fix.
