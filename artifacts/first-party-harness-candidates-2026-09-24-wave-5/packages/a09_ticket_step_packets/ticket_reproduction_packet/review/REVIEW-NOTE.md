# Review note: ticket reproduction step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a09_ticket_step_packets, repaired by the a09 repairer of the same wave after the critic review, model family anthropic. This note is never delivered to a harness.

## Method

One focused step that turns the behavior reported in a ticket into one new test that fails on the current code, records that failure, and changes no product code. The model writes the test, because that needs judgment. A tested script, `scripts/record_reproduction_run.py`, does everything that should not depend on the model: it lists changed files with git; it refuses to run the test while a file outside the declared test prefixes is changed (`product_code_changed`) or while another file under those prefixes is changed (`other_test_files_changed`), because the step may change `test_file` and nothing else; it checks that the test file exists, has a change, and holds the exact test name as a whole word on a line that is not a comment; it runs the host's test command without a shell under a time limit; and it writes a new evidence file per run with the exit code, the digest of the full output, the last part of the output, the digest of the test file and the digest of the step input as it was read. A non-zero exit is recorded as `nonzero_exit_recorded`; the model then quotes the failing line and judges whether the failure is the reported behavior or a broken test. The entry routes every verdict to one action.

## Authoring basis and sources

Original text and code written for this wave. Package format: `src/loop_engine/core/service_runtime/catalogue_packages.py`. Assignment record: `node_assignment/v3` from `src/loop_engine/core/node_provisioning.py`, kind `build`, mode `hybrid`. The rule that a check must be seen failing on a known-wrong subject follows `src/loop_engine/core/independent_failure_review.py`. The pilot template `artifacts/harness-intelligence-format-pilot-2026-09-22/context/repair-one-failing-test/codex/work/AGENTS.md` and the starter items in `examples/29_intelligence_service/starter-catalogue/items.json` were read to state the difference below.

## Inputs and outputs

- Input: `.baltor/step/input.json` (`ticket_reproduction_input/v1`): ticket id and path, the test file and exact test name chosen by triage, the expected behavior, test path prefixes, the test command as an argument list, a time limit, the paths the host placed, and the evidence folder, which must lie inside `.baltor/` and outside `.baltor/step/`. The step reads the input and never edits it.
- Evidence: one `ticket_reproduction_run/v1` file per recorder run in `.baltor/step-output/evidence/`, never overwritten, so failed attempts stay beside the final one. Each records `input_sha256`.
- Output: `.baltor/step-output/output.json` (`ticket_reproduction_record/v1`) with status `reproduced`, `not_reproduced` or `blocked`, the quoted failure line, every evidence file and the model's explanation.
- Markers: `STEP_ID`, `HARNESS_STYLE`, `TICKET_ID`, `TRIAGE_STEP_ID`, `REPOSITORY_NOTES`, and `PROCESS_EFFECT` in `contracts/task.json`.

## Effects

`reads_fs`, `writes_fs` (the test file, and the output and evidence files under `.baltor/step-output/`), and `spawns_process` (the recorder, which runs `git status` with `--no-optional-locks` and the host's test command). No network, no package install, no commit. The Authority section asks the host for write access to `test_file` and `.baltor/step-output/` only, so the packet folder `.baltor/step/`, and with it `input.json`, can be read-only. The host compares `input_sha256` in every evidence file with the digest of the input it wrote and refuses the step when they differ. The tests create temporary git repositories inside a temporary directory. The recorder runs exactly the argument list in the host's input; the host must render the input from its own allowlist and bind a trusted `python3`, because a `python3` found first on `PATH` can be replaced.

## Closest existing items

- Pilot `repair_one_failing_test` repairs a failure that already exists. This packet creates the failing test and is forbidden to repair anything.
- Starter `write_a_regression_test_that_pins_a_defect` (prose) covers the whole cycle from report to fix for a person. This packet is only the first half, as a bounded step with a recorder that makes the failure evidence independent of the model's account, and change gates that stop product and other test edits.
- Starter `reduce_a_failure_to_a_minimal_reproduction` shrinks an existing failure; outside staged `skill_bug_reproduction_brief_c7eb2ef9dbad` (title only) writes a brief, not a test.
- Wave 5 `verify_fail_then_pass_evidence` (a12) later checks the pair of runs; `extract_test_failures` (a03) parses runner output. Neither writes or records the first failing run.

## Positive example

`examples/input.json` and `examples/output.json`: the new test `test_badge_uses_singular_for_one_item` fails with `AssertionError: '1 items' != '1 item'`. The example also keeps a first attempt that failed with a NameError from a misspelled call, which the model correctly judged to be a broken test. The test `test_every_run_keeps_its_own_evidence_file` reproduces both runs.

## Known-wrong example

The model edits `shop/cart_badge.py` so that the new test fails. The recorder refuses to run the test, writes verdict `product_code_changed` with `ran` false, and exits 1 (`test_known_wrong_product_change_is_not_a_reproduction`). If the model also adds that file to `host_placed_paths` in the input, the recorder cannot see the edit, but the evidence records the digest of the edited input, which differs from the host's digest (`test_product_change_hidden_by_editing_the_input_shows_in_the_input_digest`). A helper edited under `tests/` gives `other_test_files_changed` (`test_other_test_file_change_is_not_run`), and a test name that appears only in a comment gives `test_name_not_in_file` (`test_name_only_in_a_comment_is_not_a_test`).

## Harness placement and verification state

- Codex, OpenCode, Pi: root `AGENTS.md` pickup observed in earlier probes; Gemini CLI: `GEMINI.md` documented, not observed; Goose: `AGENTS.md` documented for 1.50.0, not observed, listed in `unverified_targets`.
- Claude Code: `CLAUDE.md` holds `@AGENTS.md` and is now placed with `compose_instruction_section`, so an existing customer `CLAUDE.md` keeps its content and gains the import line. The critic reported from the official memory documentation (fetched September 23, 2026) that only `CLAUDE.md` loads when both files exist; `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` (on `origin/main` after the pinned revision) records the same. The import is documented, not observed.
- The script is placed at `.baltor/ticket-reproduction-packet/scripts/`, and the command in the entry assumes the harness starts in the workspace root. Tests are not placed in the step.
- The step writes nothing under `.baltor/step/`, so it composes with the a14 `focused_step_packet_rules` fragment, whose rule 7 forbids edits there (repairer probe `repairer-a09_ticket_step_packets/a14-interop-after-repair.txt`). The host moves `.baltor/step-output/` to its night archive after the step.
- No harness binary was run. Whether each harness allows the recorder command under its default permissions is unverified.

## Customer requests

- "Write a failing test for bug T-88 first; do not touch the code yet."
- "Show me proof that the rounding problem is real before the agent tries to fix it."
- "Reproduce the issue from this ticket as a unit test and save the failing output."

## Limits

- The recorder cannot tell an assertion failure from a broken test or a failure elsewhere; the verdict name says only that the exit was not zero. `output_mentions_test_name` is a hint, not proof. That judgment stays with the model and the later verification.
- The name check is textual: a name inside a string or a docstring still counts.
- A test runner that exits 0 on failure, or non-zero for unrelated reasons, will mislead the exit code. The host's command must run only the new test.
- The change check needs git and the workspace root at the top of the worktree; it refuses otherwise. Files that git ignores are invisible to it.
- Byte caches (`__pycache__`, `.pytest_cache`, `.pyc`) are ignored and listed as ignored; other build outputs count as changes and can block the step.
- An edited input is detected by the host's digest comparison, not by the recorder.
- POSIX only: the time limit stops the whole process group.

## Repair after the critic review

The critic recommended repair. Every finding and what changed:

1. Blocking, writable input: the entry forbids editing `.baltor/step/`; the write grant is narrowed to `test_file` and `.baltor/step-output/`; the recorder refuses an evidence folder inside `.baltor/step/`; every evidence file and the printed summary record `input_sha256`.
2. Blocking, routing: step 4 now names an action for every verdict. `product_code_changed` and `other_test_files_changed` say "change back by hand each listed file that you changed" and never revert another file; a test that could fail only after a product change gives status `blocked`; the repeated failure rule now names "the same import, name, syntax or collection error".
3. Verdict name: `failing_test_recorded` is now `nonzero_exit_recorded`, and the name check is a whole-word match on a line that is not a comment.
4. Other files under the test prefixes: now a gate with its own verdict.
5. a14 rule 7: output and evidence moved to `.baltor/step-output/`.
6. CLAUDE.md collision: placement changed to `compose_instruction_section`.

One addition beyond the findings: path resolution now answers with a refusal when two symbolic links point at each other, instead of stopping with a Python error (Python 3.10 raises there; 3.14 does not). The first checker run on the repaired bytes refused four packages in the vocabulary check because that refusal message first used a word the wave refuses in payload files; the message was reworded, and the refused reports are kept.

## Removed-guard controls

Each guard below was removed in a scratch copy of the payload and the named test was run under Python 3.14 (`repairer-a09_ticket_step_packets/removed_guard_checks.py`, report `removed-guard-checks-20260924T055814Z.json`, which also reruns the two generator controls on the repaired bytes); each named test failed on the mutant and passed on the unchanged copy. The packaged script keeps every guard.

- Product change gate: `test_known_wrong_product_change_is_not_a_reproduction`.
- Passing run verdict: `test_passing_test_is_reported_and_not_forced`.
- Other test files gate: `test_other_test_file_change_is_not_run`.
- Comment line filter: `test_name_only_in_a_comment_is_not_a_test`.
- Whole-word name match: `test_longer_name_does_not_count_as_the_name`.
- Input digest in the evidence: `test_product_change_hidden_by_editing_the_input_shows_in_the_input_digest`.
- Evidence folder outside `.baltor/step/`: `test_evidence_inside_the_packet_folder_is_refused`.

## Checks that failed before they passed

The first checker run of the generator refused `contracts/task.json` in the vocabulary check, because the `node_assignment/v3` effect name for starting local processes begins with a word the wave refuses in every payload file. The task record therefore carries the marker `PROCESS_EFFECT`, which the host renders to that effect name only when it grants it. The effect is still declared in `package.json`.

A self-review after the first passing run found that a small model could read the `product_code_changed` problem as a request to revert files; the entry was changed then, and the repair above made the routing complete.

During the repair, the new tests were first run against the earlier script: 6 of 15 failed there (`repairer-a09_ticket_step_packets/known-wrong-before-repair/reproduction-new-tests-on-old-script.txt`), and all 15 pass on the repaired script under Python 3.14 and 3.10. A local count found the new entry at 452 words, above the limit of 450, and lines were shortened before the checker ran. Every earlier report in `review/precheck-*` is kept.
