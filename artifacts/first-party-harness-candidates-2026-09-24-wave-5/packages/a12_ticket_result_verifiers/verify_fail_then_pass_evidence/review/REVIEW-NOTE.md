# Review note: Verify fail-then-pass test evidence

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a12_ticket_result_verifiers, model family anthropic. An earlier pass of the same generator wrote the first version on September 23, 2026; this pass reviewed it, changed it and checked it again. The earlier bytes are kept in `packages/verify_fail_then_pass_evidence/earlier-attempt-20260924T0101Z.tar.gz`. This note is never delivered to a harness.

## Method

One verifier method. The script reads three saved files: the test output from before a fix (with the new test already written), the output of the same command after the fix, and the unified diff of the whole change. It returns one JSON verdict built from eight named checks: the new test failed before (`new_test_failed_before`), it passes after (`new_test_passes_after`), the diff adds its definition (`diff_adds_new_test`), both outputs come from the same runner (`same_runner_format`), the before run holds other passing tests to compare (`baseline_has_other_tests`), no previously passing test now fails, is missing or is skipped (`no_previously_passing_test_fails`), no other test fails after the fix that did not fail before (`no_new_failures_after`), and at least one changed file is not a test (`diff_changes_non_test_file`). Exit 0 is pass, 1 is fail, 2 is refused input. The checklist holds the judgments code cannot make, such as whether the failure text matches the reported defect.

## Authoring basis and sources

Original text and code, written for this wave, MIT like the repository. No outside text or code was copied. Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `src/loop_engine/core/overnight_outcome.py`: the overnight classifier grades a gate before and after the work, refuses credit when the gate was green before any work (`already_green`), and flags a pass where every changed file is a test (`verified_by_test_change`). This package applies the same two ideas to saved per-test output.
- `examples/29_intelligence_service/starter-catalogue/bodies/write_a_regression_test_that_pins_a_defect.md`: the closest prose method.

Runner formats were observed on this machine. In this pass a probe project under `generator-a12-work/probe/proj` (a git repository with a base commit, a new failing test and a fix) produced real outputs of pytest 9.1.1 with `-v`, `-rA` and `-q`, pytest's JUnit XML writer, and `python -m unittest -v` on Python 3.14.4 and 3.10.20, plus a real `git diff`. Every same-runner pair gave pass; quiet output and a unittest before run with a pytest after run gave fail. Go and Cargo are not installed here, so the `go test` and `cargo test` parsers follow the documented line formats and are unverified against a live run.

## Inputs and outputs

Inputs: `--before`, `--after` and `--diff` paths below `--root` (default the current folder; one input may be `-` for standard input), one or more `--test` ids, optional `--format` and `--test-glob`. Each input is at most 64 MiB of UTF-8. A combined diff of a merge is refused with `combined_diff`. Output: one JSON object with `verdict`, `failures`, `warnings`, `checks`, `new_tests`, `regressions` (`newly_failing`, `missing_after`, `now_skipped`, `new_failures_after`), `still_failing`, `counts`, `diff` and the SHA-256 digest of every input.

## Effects

`reads_fs`: the script reads the three named files, refusing `..`, paths that resolve outside `--root`, non-regular files and oversized input. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The tests read the shipped examples or pass text to the `judge` function and write no file.

## Closest existing items

- `write_a_regression_test_that_pins_a_defect` (starter, prose): tells a person how to write a regression test and see it fail. This package writes no test; it judges saved evidence and returns a machine verdict.
- `test_driven_change_red_green_refactor` (served, prose) and `prove_a_check_can_fail_when_the_behaviour_is_removed` (starter, prose): the practice, with no executable part.
- Wave 5 neighbours: `ticket_reproduction_packet` (a09) creates the failing test and records one run; `ticket_fix_verification_packet` (a09) runs the tests after a fix; the pilot `repair_one_failing_test` repairs an existing failure; `extract_test_failures` (a03) lists failures of one run; `detect_weakened_test_assertions` (a12) reads test edits. This package compares two saved runs and a diff, and runs nothing. A search of `scout/existing-inventory.tsv` found no executable verifier for this in software change and testing.

## Positive example

The shipped example: `examples/before-run.txt` shows `tests/test_dates.py::test_rejects_day_32` FAILED with three other tests passing; `examples/after-run.txt` shows all four passing; `examples/change.diff` changes `src/dates.py` and adds the test at `tests/test_dates.py:16`. The verdict is pass with three previously passing tests compared. `git apply --numstat --summary` parses the example diff.

## Known-wrong example

The same command with the passing after output given as BEFORE fails `new_test_failed_before`: the test was never seen failing. Further known-wrong cases in the tests: a test that still fails after the fix; a previously passing test that now fails, goes missing or is skipped; a test that was skipped before and fails after; outputs of two runners; quiet output; a diff that changes only tests; a diff without the new test; a before run that holds only the new test; an extra failing test after the fix.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/verify-fail-then-pass-evidence/`, `.agents/skills/verify-fail-then-pass-evidence/` (Codex), `.opencode/skills/verify-fail-then-pass-evidence/`, `.pi/skills/verify-fail-then-pass-evidence/` and `.gemini/skills/verify-fail-then-pass-evidence/`. Basis: specification section 6 marks the first four skill folders observed and the Gemini CLI folder documented (`HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`). No harness binary was run for this package. A host-style walkthrough (recorded in `PRECHECKS.txt`) copied the folder to `.claude/skills/verify-fail-then-pass-evidence/` inside a copy of the probe project, found it with the discovery command of `SKILL.md`, and ran the first action as written on the real pytest outputs and git diff: pass, and fail with `new_test_failed_before` when the after output was given as BEFORE. Unverified: whether each harness tells the model the folder path it needs for SKILL_DIR (the entry gives an `ls -d .*/skills/...` fallback), and whether a harness asks for permission before `python3` runs from a skill folder.

## Customer requests

- "Did the new test really fail before the overnight fix, or was it written afterwards?"
- "Check that the fix did not break any test that used to pass."
- "Give me a yes or no on whether this bug fix has real test evidence."

## Limits

Only per-test result lines are read; a runner without them (quiet pytest, Jest's default output) fails `baseline_has_other_tests` with a hint, or is refused when no line is found. A test that prints inside its own result line can hide that line. Definition search covers Python, Go, Rust, Java, Kotlin, C#, PHP, JavaScript and TypeScript title strings, Ruby and Elixir `it` or `test` blocks and GoogleTest; other languages fail `diff_adds_new_test` and need the checklist. Test file detection is by path, so an unusual layout needs `--test-glob`. The script cannot tell whether BEFORE really ran without the fix.

Checks that failed before they passed. Earlier pass, as its own note recorded: the first mutation pass found no test for `new_test_passes_after`, for the absolute path escape or for the size bound, and real pytest 9 and Python 3.10 output shapes broke the first parsers; both were repaired. This pass: the baseline check (run 1 in `PRECHECKS.txt`) refused `inventory`, because the test file had changed after the last report and the digests were stale. Review then found that a test skipped or marked expected to fail before the fix and failing after it was not reported; `no_new_failures_after` now covers it. Outputs of two different runners produced a misleading "missing after" failure; the new `same_runner_format` check names the cause. Every new guard was removed once in a temporary copy and its named test failed; four inherited guards were removed the same way and their tests failed too.
