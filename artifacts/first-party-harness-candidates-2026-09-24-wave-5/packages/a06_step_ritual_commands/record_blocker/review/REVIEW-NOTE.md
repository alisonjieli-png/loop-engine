# Review note: record_blocker

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a06_step_ritual_commands (family anthropic), repaired by the a06 repairer
on 2026-09-24 after the second critic round. File class: command_file. Version 0.1.0. This note is never
delivered to a harness.

## Method

One named command turns "I am stuck" into a checked record and a status change, so an unattended night keeps
moving instead of stalling or retrying without end. The command states when to use it: a needed file, permission,
decision or tool is missing, the same error returned after a changed approach, or the ticket's time is spent. A
tested helper chooses the ticket (`--ticket`, else the step's `node_id` when the queue holds it, else the single
ticket in progress), creates `.baltor/night/blockers/<ticket>.md` from a fixed template and never replaces it.
The model fills in what was tried, the exact error, what is needed and from whom.

The check refuses a repeated or unknown heading and a template line left in place. Exact error needs pasted lines
in a code block, a saved log path in backticks, or both. A saved log must be a nonempty regular file inside the
workspace that is not the record itself, not another blocker record, not a step input, not a night settings,
ticket, queue or status file, not a file of this command, and not older than the ticket's recorded start. When
both are given, every pasted line must appear in the saved log, so a paraphrase next to a real log is refused.

Only a passing record changes anything, and only the status file `.baltor/night/queue-status.json`
(`night_queue_status/v1`, the contract that `plan_night_queue` publishes). The queue itself is never rewritten.
The ticket becomes blocked with a link to the record; queued tickets that depend on it, directly or through
others, become waiting. `next` names the first queued ticket by position whose dependencies are all done.
`continue_with` names it and marks it in progress only when `.baltor/night/settings.json` says
`one_ticket_per_harness` is false, no other ticket is in progress and `--no-start` is not given; otherwise
`not_started_because` gives the reason. With no settings file, an unreadable one or a missing key, one ticket per
harness is assumed and nothing is started, which fits the default design of one freshly started harness per step:
the host starts the next ticket.

## Authoring basis and sources

Original text and code written for this wave. No outside text or code was copied. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract.
- `docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md`: a failure becomes a typed
  next action and the reason for ending is recorded.
- `src/loop_engine/core/node_provisioning.py`: the `node_id` field read from `task.json`.
- `docs/guides/native-client-material-loading.md`: the OpenCode command folder.

`contracts/night-queue.schema.json` (SHA-256 `3bfd64a9bf8b7a636068756b3319de20398cffddef1ba5efd27d25a79e993f15`)
and `contracts/night-queue-status.schema.json` (SHA-256
`a4238f345ed8ffd7c68d28cbe91ee2b1a0abd7612318596990eae6c64f6bd33c`) are byte copies of the contracts that
`plan_night_queue` owns; the integrator keeps one copy. `examples/queue.json` and `examples/queue-status.json`
were produced by running the repaired `plan_queue.py plan` and `mark` on synthetic tickets, not written by hand.

## Inputs and outputs

Inputs: the queue, the optional status file, the optional settings file, the optional `.baltor/step/task.json`,
the record the model writes and any saved log it cites. Outputs: one JSON object per run (`blocker_new/v1`,
`blocker_check/v1`, `blocker_filed/v1` or `blocker_refused/v1`), the record file and the status file. Exit 0
success, 1 the record check failed (nothing changed), 2 refused input (no queue, a queue that is not
`night_queue/v1`, a status file of another queue, an unknown, unsafe or already blocked ticket, no ticket named).

## Effects

`reads_fs`; `writes_fs` (one new record with exclusive creation; the status file through a temporary file and a
rename; tests write only in temporary folders); `spawns_process` (the model starts the helper with
`python3 -I -B`; tests start it with the current interpreter). No network, no model call, no secret read, nothing
deleted.

## Closest existing items

- `deliver_the_best_available_result_when_blocked` (starter, prose): finish every safe part and state the limits.
  This package records the blocker in a checked form and moves the night on.
- `diagnose_a_stall_and_change_strategy` (starter, prose): decide whether to keep trying; this command runs once
  the decision is to stop this ticket.
- Wave 5: `write_step_handoff` (a06) ends any step and writes a `night_step_handoff/v1` record without touching the
  queue status; `plan_night_queue` (a06) owns the queue and the status contract and makes the start, done and
  release moves. `unattended_run_rules` (a14) records blocked tickets in its own ledger with
  `finish --status blocked --needs`, and `overnight_ticket_plugin` (a11) writes its own per-ticket result records
  bound to the queue bytes. Because this command leaves the queue bytes unchanged, a11's records stay valid; the
  after-repair probe ran a11's `night_status.py` after a blocker was filed and it still read the queue. The wave
  still has three places that can record a blocked ticket; the integrator chooses one.

## Positive example

`examples/queue.json` has T-101 in progress (in `examples/queue-status.json`), T-103 depending on T-101, T-108
depending on T-103, and T-102. Filing `examples/blocker-example.md` marks T-101 blocked and T-103 and T-108
waiting, names T-102 as `next`, and starts nothing because one ticket per harness is assumed. With
`one_ticket_per_harness` false, T-102 becomes the `continue_with` ticket.

## Known-wrong example

A record that says "It failed with some import problem.", leaves a template line under Needed and names nobody
under From whom exits 1 with three findings and the status file bytes stay identical. The critic's cases are
tests: blocking queued T-102 while T-101 is in progress starts nothing, because T-103 and T-108 wait for T-101
and T-101 is still in progress; with T-103 in progress, `next` T-102 is named but not started
(`test_known_wrong_next_ticket_waits_for_dependencies_and_work_in_progress`). A record that cites itself, the
queue, an empty file, a missing file or a log older than the ticket's start as its saved log exits 1
(`test_known_wrong_saved_log_must_be_a_real_log`), and a paraphrase next to a real log exits 1
(`test_a_saved_log_can_replace_or_back_the_pasted_error`).

## Harness placement and verification state

No harness binary was run. Claude Code `.claude/commands/record-blocker.md` and Gemini CLI
`.gemini/commands/record-blocker.toml`: documented in the spec table. OpenCode `.opencode/commands/record-blocker.md`:
documented and observed in the repository guide (the spec table names `.opencode/command/`). Copilot
`.github/prompts/record-blocker.prompt.md` (now with `agent: agent` and `argument-hint`, following the VS Code
prompt file documentation read on 2026-09-24) and Cursor `.cursor/commands/record-blocker.md` (the Cursor page
read the same day described skills, not a command folder): unverified. `$ARGUMENTS` and `{{args}}` are vendor
documented, not recorded in a repository research file; the sentence that holds them reads correctly when empty.
The example record and the contracts go to `.baltor/record-blocker/`; the queue and status examples and the tests
are not placed. The host must bind a trusted `python3`.

## Customer requests

- "When the agent gets stuck on a ticket, have it write down why and go to the next one."
- "I want the exact error and who can unblock it, not a summary."
- "Skip the tickets that depend on the one that failed, and never run two tickets at once."

## Limits

The check cannot tell a pasted error from an invented one when no saved log is given, and it cannot tell a real
log from one the model wrote itself. The change-time rule needs the ticket's start in the status file. The helper
assumes one writer at a time. A host that runs one ticket per harness starts the ticket that `next` names, and
marks finished tickets done with `plan_queue.py mark`, or dependent tickets never become startable.

## Repair history

Critic round 2 found: a next ticket chosen by position alone, which started T-103 before T-101 finished and left
two tickets in progress; the record accepted as its own saved log; an automatic start that conflicted with one
freshly started harness per step, with no field a small model could check; the retry for a missing ticket id in
conflict with the exit-2 stop rule; overlapping blocked-ticket records and an incompatible queue schema in a11
and a14; a Copilot variant without `agent`; and a Markdown example with role `other`. The repairer reproduced the
cases at digest `ac9bd4a5` (`repairer-a06_step_ritual_commands/baseline/`) and made the changes above. The model
now reads one field, `continue_with`, instead of judging its step files; the First action section names the one
allowed repeat with `--ticket` and the stop rule excepts it; the example record is placed, referenced from step 6
and has role `skill_reference`.

Mutation checks: eight guards removed one at a time (dependencies for `next`, work in progress, one ticket per
harness, self-cited and blocker-record logs, empty logs, the pasted-line comparison, the record check before the
status change, waiting dependents) were each killed by a named test while the unchanged copy passed. Native
loading of the command is unobserved. Every run is listed in `PRECHECKS.txt`.
