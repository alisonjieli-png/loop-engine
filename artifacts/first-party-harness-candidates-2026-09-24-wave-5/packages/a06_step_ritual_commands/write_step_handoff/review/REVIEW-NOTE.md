# Review note: write_step_handoff

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a06_step_ritual_commands (family anthropic), repaired by the a06 repairer
on 2026-09-24 after the second critic round. File class: command_file. Version 0.1.0. This note is never
delivered to a harness.

## Method

One named command ends a focused step. The model runs a helper that creates `.baltor/handoffs/<step-id>.md`
from a fixed template, fills six sections (objective, status, done, remaining, open questions, first action for
the next harness), then runs the helper's check until it passes. The helper decides everything that code can
decide:

- the step id comes from `.baltor/step/task.json` (`node_id`) and must be an identifier of at most 64
  characters, the same rule as the shared handoff contract;
- the note keeps exactly the title `# Step handoff: <step-id>` and the six headings, once each and in order;
  a repeated heading, any other heading, loose text before the first heading, a fenced code block or a hidden
  comment is a finding, so no claim can sit where the check does not look;
- every Done line cites at least one regular file inside the workspace that this step wrote or changed; the
  workspace root, a folder, a step input under `.baltor/step/`, a handoff note or record under
  `.baltor/handoffs/`, a file of this command, the note itself and, when `.baltor/step/task.json` exists, a
  file last changed before that file was placed (2 seconds of tolerance) are findings;
- the status is one line (complete, partial or blocked) and agrees with Remaining;
- the first action is one line with exactly one command or path in backticks, at most 300 characters;
- list items stay at or below 500 characters and 50 lines, and the note at or below 500 words.

Only a note without findings gets its record: `.baltor/handoffs/<step-id>.json` in the `night_step_handoff/v1`
shape that the wave 5 morning report and resume packets read. Complete stays complete, partial becomes
unfinished, blocked stays blocked. Each Done line becomes a claim with its first evidence path, every evidence
file is listed with its SHA-256 (files above 256 MiB are left out and named in `record_notes`), a blocked note
gives the blocker reason from its first Remaining line and the question from its first open question, and
`revision` is null because the helper starts no process. The ticket id is `--ticket` when given, else the step id
when `.baltor/night/queue.json` holds a ticket with that id, else null. The record is rewritten by each passing
check through a temporary file and a rename; a failing check leaves the last record as it was.

## Authoring basis and sources

Original text and code written for this wave. No outside text or code was copied. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract this package follows.
- `src/loop_engine/core/node_provisioning.py`: the `node_assignment/v3` fields; the helper reads `node_id` and
  `objective`.
- `docs/guides/native-client-material-loading.md`: the OpenCode command folder.

`contracts/night-step-handoff.schema.json` is a byte copy of `contracts/handoff.schema.json` in the wave 5 a09
packets `morning_report_packet` and `interrupted_step_resume_packet` (same producer family, same wave, SHA-256
`8fe6068db4a32ea1e19143e141fa82fa2401f3ac66ac73d8eb47b7de16b284f2`). The a09 packets own that contract; the
integrator keeps one copy.

## Inputs and outputs

Inputs: `.baltor/step/task.json` when present, or `--step-id`; the note the model writes; the optional night
queue for the ticket id. Outputs: one JSON object per run (`step_handoff_init/v1`, `step_handoff_check/v1` or
`step_handoff_refused/v1`), the note, and on a pass the record. Exit 0 success, 1 check failed (no record
written), 2 refused input (missing or unsafe step id, a path that leaves the workspace, a note over 256 KiB,
text that is not UTF-8, a `--ticket` that the queue does not hold, a record path that is a symbolic link).

## Effects

`reads_fs` (task file, note, evidence files and their digests, the queue); `writes_fs` (init creates one note
with exclusive creation; a passing check writes the record through a temporary file and a rename; tests write
only in temporary folders); `spawns_process` (the command tells the model to start the helper with
`python3 -I -B`; tests start it with the current interpreter). No network, no model call, no secret read,
nothing deleted.

## Closest existing items

- `hand_over_a_result_its_consumer_can_use` (starter, prose): shapes a final result for its consumer. This
  package is narrower and executable: one step's state for the next fresh harness, with evidence checked on disk.
- `validate_focused_attempt_handoff` (Codex plan, not generated): validates a supplied JSON handoff with attempt
  ids and ordered events. This package writes a short Markdown note and derives the shared JSON record from it.
- Wave 5 boundaries: `morning_report_packet` (a09) compiles a night of `night_step_handoff/v1` records and
  `interrupted_step_resume_packet` (a09) resumes from one; this command writes one such record per step.
  `verify_morning_report_claims` (a12) checks a finished report. `record_blocker` (a06) files a blocked night
  ticket and moves the queue status; this command ends any step, blocked or not, without touching the queue.

## Positive example

`examples/task.json` names step `fix-month-end-filter`. `init` creates the note; the model writes
`examples/handoff-example.md` (status partial, two Done lines citing a test file, the changed source file and a
saved test log, one remaining item, one first action with one command). With those three files present the check
exits 0 and writes an unfinished record that validates against the contract
(`test_init_uses_the_step_files_and_the_filled_example_passes`).

## Known-wrong example

A note says `complete`, lists "Fixed the date parser." with no file, cites `logs/test-run.txt` that does not
exist, still lists remaining work, and ends with "Continue the work." The check exits 1 with four findings and
writes no record (`test_known_wrong_note_claims_results_without_evidence`). The critic's placed probes are now
test cases that each exit 1 without a record: the workspace root `.` as evidence, `.baltor/step/task.json` as
evidence, a folder, a file unchanged since before the step, a second `## Done` heading after the first action,
an extra `## Notes` heading, a first action with four backticked items, a fenced block and a hidden comment
(`test_known_wrong_placed_notes_from_the_review_are_refused`).

## Harness placement and verification state

No harness binary was run.

| Harness | Destination | Basis |
|---|---|---|
| Claude Code | `.claude/commands/write-step-handoff.md` | documented (spec table) |
| Gemini CLI | `.gemini/commands/write-step-handoff.toml` | documented (spec table) |
| OpenCode | `.opencode/commands/write-step-handoff.md` | documented and observed in the repository guide |
| Copilot | `.github/prompts/write-step-handoff.prompt.md` | unverified |
| Cursor | `.cursor/commands/write-step-handoff.md` | unverified |

The spec table names `.opencode/command/`; the repository guide records `.opencode/commands/` as documented and
observed, so this package uses `commands/`. The Copilot variant now carries `agent: agent` and `argument-hint`;
the VS Code prompt file documentation, read by the repairer on 2026-09-24, says a prompt runs in the current
agent unless `agent` is set and accepts `ask`, `agent`, `plan` or a custom agent. The Cursor documentation page
for commands, read the same day, described skills and no project command folder, so the Cursor path stays
unverified. `$ARGUMENTS` (Claude Code, OpenCode) and `{{args}}` (Gemini CLI) are vendor documented, not
recorded in a repository research file; the sentence that holds them reads correctly when no argument is given.
Support files go to `.baltor/write-step-handoff/`; `examples/task.json` and the tests are not placed. The host
must bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Customer requests

- "Before you stop, leave a note so the next session knows exactly where to start."
- "My overnight agent keeps saying it finished things it did not do. Make it show proof."
- "Give each fresh agent a one-line first step from the previous one, and let the morning report read it."

## Limits

The check proves that each evidence file exists and changed during the step, not that it proves the claim; a
reviewer or verifier still reads it. The change-time rule needs `.baltor/step/task.json` placed at the start of
the step and a workspace clock that agrees with it; without the task file the rule is skipped. Headings and
statuses are English words. The 500-word default is a choice, not a measurement. The note is not scanned for
secrets. `revision` is always null, so the resume check compares file digests only. `done_when` is always an
empty list because the note has no such section.

## Repair history

Critic round 2 (critic-a06_step_ritual_commands-r2) found: evidence rules that accepted the workspace root, the
step's own task file, duplicate and unknown headings and a four-action first action; no `night_step_handoff/v1`
record for the a09 consumers; a Copilot variant without `agent`; an example that broke its own first-action
rule; an ambiguous retry against the exit-2 stop rule and a dangling argument sentence; no finding for an empty
Objective; unmentioned placed examples; and a Markdown example with role `other`. The repairer reproduced every
probe at digest `477f0c20` (`repairer-a06_step_ritual_commands/baseline/`), then changed the helper, template,
example, variants, tests and manifest as described above. The example's first action now holds one command; the
First action section names the one allowed repeat with `--step-id`, and the stop rule excepts it; the example
note is placed, referenced from step 8 and has role `skill_reference`; `examples/task.json` is no longer placed.

Integration evidence from `repairer-a06_step_ritual_commands/after-probe-results.json`: the a09
`check_handoff_drift.py` read an unfinished a06 record (verdict `match`) and reported `drift` after an evidence
file changed; the a09 `compile_morning_report.py` listed a complete a06 record as complete with no problems.

Pre-check history of this round: the first static run refused `scripts/step_handoff.py` and the test file under
`safety_static` (`hidden_comment`), because the detector and its test held a literal comment opener; the
detector now uses the pattern `<!-{2}` and the test assembles the opener at run time. That refused report is kept
in `review/`. Mutation checks: seven guards removed one at a time (folder and root, step inputs, unchanged files,
repeated headings, unknown headings, several first-action items, the partial status mapping) were each killed by
a named test while the unchanged copy passed. Native loading of the command in any harness is unobserved. Every
run is listed in `PRECHECKS.txt`.
