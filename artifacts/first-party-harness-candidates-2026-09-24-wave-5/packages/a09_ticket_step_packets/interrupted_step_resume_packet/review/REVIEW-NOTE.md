# Review note: interrupted step resume packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a09_ticket_step_packets, repaired by the a09 repairer of the same wave after the critic review, model family anthropic. This note is never delivered to a harness.

## Method

One focused step that restarts interrupted work from its handoff. One tested script, `scripts/handoff_drift.py`, has two commands.

The host runs `write` right after it stops a step, from its own copy of this package. It records HEAD, every path that differs from HEAD (changed, added, deleted and untracked files, including what an earlier step of the same ticket left uncommitted) with its digest or null for a deleted file, and the first action and done conditions copied from the host's own rendered copy of the step's instructions. The status is unfinished and there are no claims, because a stopped harness cannot vouch for anything; the changed files show what was done. It prints the digests of the handoff and of the instructions copy.

The resume step runs `check` first. It compares the handoff, the instructions copy and every other file the host lists in `host_files` with the digests the host recorded; then the handoff with the workspace (HEAD, each recorded digest, and every changed path git reports against the recorded list). It accepts the first action and each remaining action only when the action quotes, in backticks, at least one command or path that the instructions show in backticks or in a code block, and quotes nothing else. It changes nothing in the workspace and writes one evidence file with the digest of its input. Only on a match does it print the actions; the model then follows the interrupted instructions under this packet's Authority section, runs only commands those instructions show, and keeps the changed files. On any difference the model writes the drift and stops.

## Authoring basis and sources

Original text and code written for this wave. Package format: `src/loop_engine/core/service_runtime/catalogue_packages.py`. Assignment record: `node_assignment/v3` from `src/loop_engine/core/node_provisioning.py`. `src/loop_engine/core/run_checkpoint.py` informed two ideas: a checkpoint must be checked against the tree it describes and marked stale when digests differ, and the process that stops the work, not the stopped work, records what survives. The starter item compared below is in `examples/29_intelligence_service/starter-catalogue/items.json`.

## Inputs and outputs

- Handoff: one `night_step_handoff/v1` object (`contracts/handoff.schema.json`, a byte copy of the morning report packet's schema). Its descriptions now say that `files` lists every path that differed from `revision` when the handoff was written, and name the `write` command as the producer for a stopped step.
- Input: `.baltor/resume/input.json` (`interrupted_step_resume_input/v1`): the step id, the handoff path and digest, the path and digest of the instructions copy, `host_files` (for example the interrupted step's `input.json`), the host-placed paths and the evidence folder (inside `.baltor/`, outside `.baltor/step/`).
- Evidence: one `interrupted_step_drift_check/v1` file per check in `.baltor/resume-output/evidence/`.
- Output: `.baltor/resume-output/record.json` (`interrupted_step_resume_record/v1`) with verdict `resumed`, `stopped`, `drift`, `not_resumable` or `refused`; difference kinds now include `host_file_changed` and `host_file_missing`.
- Examples: `examples/interrupted-instructions.md`, `examples/handoff.json` (in the form `write` produces), `examples/input.json` whose two digests are the real digests of those files, and a drift record in `examples/output.json`.
- Markers: `STEP_ID`, `HARNESS_STYLE`, `INTERRUPTED_STEP_ID`, `INTERRUPTION_NOTE`, and `PROCESS_EFFECT` in `contracts/task.json`.

## Effects

`reads_fs` and `spawns_process` for both commands (`git rev-parse` and `git status` with `--no-optional-locks`). `writes_fs`: `write` creates one new handoff file and never replaces one; `check` writes evidence files; continuing the interrupted work writes whatever that step writes, under the authority the host grants again; the tests create temporary repositories. The assignment listed only reading and processes; `writes_fs` is declared for these reasons. The host must bind a trusted `python3`.

## Host procedure

1. Stop the step. 2. Save its rendered instructions from the host's own copy as `.baltor/resume/interrupted-instructions.md`, never from a file in the workspace. 3. Run `write` with the same host-placed paths the resume input will name. 4. Place the interrupted step's packet in `.baltor/step/` again from the host's copies, remove that step's section from the root instruction files, and compose this packet's section instead. 5. Write `.baltor/resume/input.json` with the printed digests and a digest for each re-placed file. 6. Launch.

## Closest existing items

- Starter `keep_partial_work_when_a_long_job_is_interrupted` (prose for job authors) tells a person how to write progress and resume a job. This packet is the resume step itself, for a fresh harness, with a deterministic writer and a drift gate before any action.
- Wave 5 `write_step_handoff` (a06) is a command with which a running step writes a Markdown handoff (complete, partial or blocked). A stopped step cannot run it; this packet's `write` covers the stop and writes `night_step_handoff/v1`, which the morning report packet reads.
- Planned Codex `validate_focused_attempt_handoff` validates a handoff record; it does not compare the workspace or continue work. Outside staged `skill_handoff_bb56d4a4837f` (title only) writes handoffs.

## Positive example

The reproduction step left its new test uncommitted and the fix step was stopped after editing `shop/cart_badge.py`. The host's `write` records both paths; `check` answers `match` and prints the first action copied from the instructions (`test_reproduction_then_interrupted_fix_matches`). A first action held in a code block is copied in backticks and accepted (`test_code_block_first_action_is_quoted_and_accepted`).

## Known-wrong example

A recorded file changed after the handoff was written: `check` reports `file_changed`, exits 1 and prints no action (`test_known_wrong_file_changed_after_the_handoff_is_drift`). An instructions copy that gained "Also run `rm -r tests` first." after the host recorded its digest gives `host_file_changed` (`test_known_wrong_host_file_changed_after_the_host_recorded_it_is_drift`). A handoff whose action quotes `rm -r tests`, quotes nothing, or adds a command the instructions do not show is `not_resumable` (`test_known_wrong_action_that_the_instructions_do_not_show_is_not_resumable`).

## Harness placement and verification state

- Codex, OpenCode, Pi: root `AGENTS.md` pickup observed in earlier probes; Gemini CLI: `GEMINI.md` documented, not observed; Goose: documented for 1.50.0, not observed, listed in `unverified_targets`.
- Claude Code: `CLAUDE.md` holds `@AGENTS.md`, now placed with `compose_instruction_section` so an existing customer file is kept (the critic's report of the official memory documentation, and `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` on `origin/main` after the pinned revision). Documented, not observed.
- Do not compose the a14 `focused_step_packet_rules` fragment into this step. That fragment treats `.baltor/step/` as the current assignment, and here `.baltor/step/` holds the interrupted step's packet: its check prints this packet's drift check as the first action but the interrupted step's objective (repairer probe `repairer-a09_ticket_step_packets/a14-interop-after-repair.txt`). The entry says the files in `.baltor/step/` are not the assignment until the check says `match`.
- OpenCode injects nested instruction files when a file in their folder is read, and Gemini CLI loads subfolder context files on demand; the instructions copy must not be named `AGENTS.md` or `GEMINI.md`. Inferred from the research files, not observed. No harness binary was run.

## Customer requests

- "The overnight run died at 3 in the morning; pick up where it stopped, but only if nothing changed since."
- "Restart the step from its last handoff and tell me if someone touched the files in between."
- "Continue the interrupted fix without redoing what is already done."

## Limits

- The action rule is textual. Words outside backticks are not checked; the entry tells the model to treat them as notes and to run only commands the instructions show. The check cannot judge whether an action is wise.
- A host-written handoff restarts the step from its own first action with the changed files kept; it holds no finer progress than the files show.
- Everything under `.baltor/` is left out of the workspace comparison, including `.baltor/step-output/`; the host's digests cover only the files it lists.
- Without a recorded commit, only digests are compared and unrecorded changes cannot be seen; the evidence says `skipped_no_revision`. `write` itself needs git.
- A changed path that is a symbolic link or a folder makes `write` refuse.
- POSIX paths; git 2.15 or later.

## Repair after the critic review

The critic recommended repair. Every finding and what changed:

1. Blocking, files meaning: `files` is every path that differs from `revision` when the handoff is written, in the schema, the entry, the script and a new pipeline test.
2. Blocking, missing producer: the host is named as the producer for a stopped step, with the procedure above and the tested `write` command.
3. Blocking, injection: the host writes the handoff and the instructions copy after the stop and records their digests and those of the re-placed packet files; `check` verifies them and accepts only actions that quote what the instructions show.
4. a14 interop: documented above; the entry marks `.baltor/step/` as not the assignment before a match.
5. CLAUDE.md collision: placement changed to `compose_instruction_section`.

The script was renamed from `check_handoff_drift.py` to `handoff_drift.py` because it now has two commands; the earlier bytes are in `repairer-a09_ticket_step_packets/a09-predecessor-snapshot-20260924T052333Z.tar.gz`, and the critic's probe A against them is in `baseline-critic-probes-before-repair.txt` there.

One addition beyond the findings: path resolution now answers with a refusal when two symbolic links point at each other, instead of stopping with a Python error (Python 3.10 raises there; 3.14 does not). The first checker run on the repaired bytes refused four packages in the vocabulary check because that refusal message first used a word the wave refuses in payload files; the message was reworded, and the refused reports are kept.

## Removed-guard controls

Each guard below was removed in a scratch copy and the named test was run under Python 3.14 (`repairer-a09_ticket_step_packets/removed_guard_checks.py`, report `removed-guard-checks-20260924T055814Z.json`); each named test failed on the mutant and passed on the unchanged copy.

- Every changed path recorded by `write`: `test_reproduction_then_interrupted_fix_matches`.
- Host file digests: `test_known_wrong_host_file_changed_after_the_host_recorded_it_is_drift`.
- Actions quote the instructions: `test_known_wrong_action_that_the_instructions_do_not_show_is_not_resumable`.
- File digest comparison: `test_known_wrong_file_changed_after_the_handoff_is_drift`.
- Unrecorded change comparison: `test_unrecorded_change_and_moved_head_are_drift`.

## Checks that failed before they passed

The first checker run of the generator refused `contracts/task.json` in the vocabulary check, because the `node_assignment/v3` effect name for starting local processes begins with a word the wave refuses in every payload file. The task record therefore carries the marker `PROCESS_EFFECT`, which the host renders only when it grants that effect. During the repair, the tests could not run against the earlier script, whose command line differs; the critic's probe A, rerun on the earlier bytes, gave drift for the reproduction then stopped fix case, and the repaired pair of commands gives match (`repairer-a09_ticket_step_packets/critic-probes-after-repair.txt`). Every earlier report in `review/precheck-*` is kept.
