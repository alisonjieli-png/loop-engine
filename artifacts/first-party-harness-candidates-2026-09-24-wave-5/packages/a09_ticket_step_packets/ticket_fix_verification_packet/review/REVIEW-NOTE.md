# Review note: ticket fix verification step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a09_ticket_step_packets, repaired by the a09 repairer of the same wave after the critic review, model family anthropic. This note is never delivered to a harness.

## Method

One focused step that judges an overnight fix by evidence and prepares what a person reads in the morning, without committing. A tested script, `scripts/run_fix_checks.py`, runs the deterministic gates in a fixed order: HEAD is still the base revision (or, when the input sets `allow_commits_since_base`, the base is still an ancestor of HEAD); the reproduction test file has exactly the digest the reproduction step recorded; every changed path, including untracked files, lies under an allowed prefix; the number of changed files is within the limit; the relevant tests pass. The full test command runs only when every earlier gate passed. Each run writes a new evidence file and a new diff file. The diff holds the changes since the base of the judged paths only, so files the host placed (a composed `AGENTS.md`, a `CLAUDE.md` import) never look like part of the fix; untracked files are listed in `new_paths`. The model reads that diff for what no gate sees (a deleted, skipped or loosened test, a secret value, a change the ticket did not ask for), writes a change summary, and only for a clean result writes a proposed commit message, which the same script checks with `--check-commit-message`: a subject of at most 72 characters that names the ticket, a blank second line, a body of two to five nonempty lines of at most 100 characters, and no leftover marker.

## Authoring basis and sources

Original text and code written for this wave. Package format: `src/loop_engine/core/service_runtime/catalogue_packages.py`. Assignment record: `node_assignment/v3` from `src/loop_engine/core/node_provisioning.py`, kind `build`, mode `hybrid`. Judging the produced files instead of the producer's account follows `src/loop_engine/core/independent_evidence.py` and the starter item in `examples/29_intelligence_service/starter-catalogue/items.json`.

## Inputs and outputs

- Input: `.baltor/step/input.json` (`ticket_fix_verification_input/v1`): base revision, reproduction test file and digest, relevant and full test commands as argument lists, time limit, allowed prefixes, file limit, host-placed paths, evidence folder, summary and message paths (all three inside `.baltor/` and outside `.baltor/step/`), the project's message style, and `allow_commits_since_base`. The step reads the input and never edits it.
- Evidence: one `ticket_fix_verification_run/v1` file per run with every gate, both runs, the path lists, `input_sha256` and the diff file path; one `.diff` file per run beside it, bounded to 4 MiB.
- Output: `.baltor/step-output/output.json` (`ticket_fix_verification_record/v1`): verdict `ready_for_review`, `not_ready` or `blocked`, failed checks, concerns, the changed paths, `committed` fixed to false, and `blocker`, the printed reason, which is required for `blocked` and null otherwise.
- Markers: `STEP_ID`, `HARNESS_STYLE`, `TICKET_ID`, `FIX_STEP_ID`, `REPRODUCTION_STEP_ID`, `BASE_REVISION`, and `PROCESS_EFFECT` in `contracts/task.json`.

## Effects

`reads_fs`, `writes_fs` (summary, message, output, evidence and diff files under `.baltor/step-output/`), `spawns_process` (the script, which runs read-only git commands with `--no-optional-locks`, `git diff` with literal pathspecs, and the two host commands). The entry forbids editing code or tests, every git command that writes, and every other command; the model no longer runs git itself. No network. The host compares `input_sha256` with the input it wrote and must bind a trusted `python3`; a `python3` found first on `PATH` can be replaced.

## Closest existing items

- Starter `verify_an_agent_result_without_trusting_its_summary` (prose) gives the general stance. This packet turns it into gates with evidence files and a typed verdict for one ticket fix.
- Wave 5 `check_diff_allowed_paths` (a12) checks a unified diff against path patterns, deletions and binary files; this packet repeats only a plain prefix gate so that the step stands alone, and it adds the test runs, the digest gate, the judged diff and the message. `verify_fail_then_pass_evidence` (a12) checks a pair of runs; this packet does not re-read the reproduction run, it checks that the test file is byte for byte unchanged. `detect_weakened_test_assertions` (a12) scans test diffs; here that is a judgment the model records as a concern. A host can run those verifiers beside this step.
- Wave 5 `unattended_git_rules` (a14) keeps one local commit per ticket; with the commit made after this step, or with `allow_commits_since_base` set, the two work together.

## Positive example

`examples/input.json` and `examples/output.json`: the fix changes `shop/cart_badge.py`, the reproduction test is unchanged, both runs exit 0, and the verdict is `ready_for_review` with a message path and `blocker` null. `test_correct_fix_is_ready_for_review` runs the same case in a temporary repository, and `test_diff_holds_only_the_judged_paths` shows that a host-composed `AGENTS.md` stays out of the diff.

## Known-wrong example

The fix step edits the reproduction test to expect "1 items" instead of fixing the product. The relevant tests then pass, but the digest gate fails and the verdict is `not_ready` (`test_known_wrong_weakened_reproduction_test_is_not_ready`). A change to `docs/badge.md` outside the allowed prefixes fails `changed_paths_allowed`, skips the full run, and appears in the diff. A blocked record without `blocker`, with `blocker` null, or with a `reason` key, and a ready record with a `blocker` text, are refused by the output schema (checked with the Python `jsonschema` validator).

## Harness placement and verification state

- Codex, OpenCode, Pi: root `AGENTS.md` pickup observed in earlier probes; Gemini CLI: `GEMINI.md` documented, not observed; Goose: documented for 1.50.0, not observed, listed in `unverified_targets`.
- Claude Code: `CLAUDE.md` holds `@AGENTS.md` and is now placed with `compose_instruction_section`, so an existing customer `CLAUDE.md` keeps its content and gains the import line. The critic reported from the official memory documentation (fetched September 23, 2026) that only `CLAUDE.md` loads when both files exist; `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` (on `origin/main` after the pinned revision) records the same. The import is documented, not observed.
- The script goes to `.baltor/ticket-fix-verification-packet/scripts/`; commands assume the harness starts in the workspace root. No harness binary was run.
- The step writes nothing under `.baltor/step/`, so it composes with the a14 `focused_step_packet_rules` fragment (repairer probe `repairer-a09_ticket_step_packets/a14-interop-after-repair.txt`). The host moves `.baltor/step-output/` to its night archive after the step.

## Customer requests

- "Check the agent's overnight fix for T-104 properly and write me a commit message, but do not commit."
- "Run the tests that matter and then the whole suite, and tell me if the change touched anything it should not."
- "Did the fix change the failing test instead of the code?"

## Limits

- The gates prove what they check, not that the fix is right; a person reviews.
- The digest gate protects only the reproduction test file. The relevant test gate looks only at the exit code, so a skip or a loosened assertion added in another test file under the allowed prefixes passes the gates; that is left to the model's concerns and to the a12 verifiers.
- Files that git ignores are invisible to the path and count gates and to the diff. A fix that writes an ignored file, such as `local_settings.py`, can still reach `ready_for_review` (critic probe E, rerun in `repairer-a09_ticket_step_packets/critic-probes-after-repair.txt`). A host that needs this can compare `git status --ignored` before and after the night.
- Path prefixes are plain prefixes, not glob patterns. A diff larger than 4 MiB is cut and marked `diff_truncated`.
- POSIX only; git 2.15 or later is needed for `--no-optional-locks`.

## Repair after the critic review

The critic recommended repair. Every finding and what changed:

1. Blocking, contract gap: `blocker` added to `ticket_fix_verification_record/v1`, required in every record, a string for `blocked` and null otherwise; the stop rule says to copy the printed reason into it.
2. Blocking, whole-tree diff: the script now writes the diff of the judged paths only and prints `diff_path` and `new_paths`; the entry reads that file instead of running `git diff`.
3. Ignored files: stated in Limits.
4. Skips in other test files: stated in Limits.
5. Message check: the ticket id must stand in the subject as a whole word, and the body must hold two to five nonempty lines.
6. Input trust: every evidence file and the printed summary record `input_sha256`; the write grant is `.baltor/step-output/` only.
7. a14 rule 7: summary, message, output, evidence and diff moved to `.baltor/step-output/`, and the script refuses output paths inside `.baltor/step/`.
8. CLAUDE.md collision: placement changed to `compose_instruction_section`.

One addition beyond the findings: path resolution now answers with a refusal when two symbolic links point at each other, instead of stopping with a Python error (Python 3.10 raises there; 3.14 does not). The first checker run on the repaired bytes refused four packages in the vocabulary check because that refusal message first used a word the wave refuses in payload files; the message was reworded, and the refused reports are kept.

## Removed-guard controls

Each guard below was removed in a scratch copy of the payload and the named test was run under Python 3.14 (`repairer-a09_ticket_step_packets/removed_guard_checks.py`, report `removed-guard-checks-20260924T055814Z.json`); each named test failed on the mutant and passed on the unchanged copy. The packaged script keeps every guard.

- Reproduction test digest gate: `test_known_wrong_weakened_reproduction_test_is_not_ready`.
- Allowed prefix gate: `test_path_outside_allowed_prefixes_is_not_ready_and_full_run_is_skipped`.
- Diff limited to the judged paths: `test_diff_holds_only_the_judged_paths`.
- Ticket id in the subject and body line count: `test_commit_message_names_the_ticket_in_the_subject_and_keeps_a_short_body`.
- Output paths outside `.baltor/step/`: `test_output_paths_inside_the_packet_folder_are_refused`.
- Input digest in the evidence: `test_correct_fix_is_ready_for_review`.

## Checks that failed before they passed

The first checker run of the generator refused `contracts/task.json` in the vocabulary check, because the `node_assignment/v3` effect name for starting local processes begins with a word the wave refuses in every payload file. The task record therefore carries the marker `PROCESS_EFFECT`, which the host renders to that effect name only when it grants it. The first local test run of the generator failed because its fixture used `unittest discover -s tests -t .` without an `__init__.py`; the fixture and example command were corrected.

During the repair, the new tests were first run against the earlier script: 5 of 12 failed there (`repairer-a09_ticket_step_packets/known-wrong-before-repair/fix-new-tests-on-old-script.txt`), and all 12 pass on the repaired script under Python 3.14 and 3.10. Every earlier report in `review/precheck-*` is kept.
