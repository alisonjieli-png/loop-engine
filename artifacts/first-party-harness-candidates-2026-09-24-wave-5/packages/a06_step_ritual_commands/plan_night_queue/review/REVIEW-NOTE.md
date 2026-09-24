# Review note: plan_night_queue

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a06_step_ritual_commands (family anthropic), repaired by the a06 repairer
on 2026-09-24 after the second critic round. File class: command_file. Version 0.1.0. This note is never
delivered to a harness.

## Method

One named command turns tonight's ticket list into an ordered queue before an unattended run. The model supplies
only judgment: minutes, model calls and risk for each ticket that lacks them, or a hold reason for an unclear
ticket, written to a separate estimates file so the ticket export stays unchanged. The command tells the model
that ticket text is data and cannot change its steps, the budget or the risk rule. A tested helper does
everything else:

- `gaps` merges each ticket's own estimate fields with its estimates entry field by field. When both give a
  value, the larger minutes, the larger calls and the higher risk count, so an estimate never lowers a risk the
  ticket states. A ticket that still misses any field is listed in `need_estimate` with a `missing` list; a
  ticket value that breaks the rules counts as missing and is named in `notes`. Every estimates entry that breaks
  `night_estimates/v1` (a number written as text, an unknown field, a hold mixed with estimate fields) is listed
  in `fix_estimate`. `ready_to_plan` is true only when both lists are empty.
- `plan` refuses (exit 2) while any entry needs fixing, and holds tickets without acceptance criteria, without a
  check, without a complete estimate, with high risk when the settings say so, with an unknown dependency, in a
  cycle or waiting on a held ticket. It orders the rest by risk, then priority (a lower number first), then
  minutes, then id (or priority first when declared), places each ticket after its dependencies, and queues it
  only while the usable budget holds (at most 500 tickets). Every held ticket gets a reason code and a sentence.
- The queue is a plan and is never rewritten. Live statuses go to `.baltor/night/queue-status.json`
  (`night_queue_status/v1`), bound to the queue by the SHA-256 of its bytes. `mark` makes the three moves that no
  a06 file made before: queued to in_progress (all dependencies done, no other ticket in progress), in_progress to
  done (an evidence file inside the workspace that changed after the start, never a night state file), and back
  to queued (with a reason). `status` prints every ticket's status and the next ticket to start. The
  record-blocker command makes the blocked and waiting moves in the same file.

This package owns and publishes the night contracts under `contracts/`: `night_tickets/v1`,
`night_settings/v1` (budget keys, `one_ticket_per_harness`, and the test and guard keys that night-preflight
reads), `night_estimates/v1`, `night_queue/v1` and `night_queue_status/v1`. They say that a lower priority number
runs first, what counts as acceptance criteria and as a check, and which command makes which status move.

## Authoring basis and sources

Original text and code written for this wave. No outside text or code was copied. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract.
- `AGENTS.md`: the use case of tickets worked overnight on a local model, one freshly started harness per step.
- `docs/guides/native-client-material-loading.md`: the OpenCode command folder.

## Inputs and outputs

Inputs: `.baltor/night/settings.json`, `.baltor/night/tickets.json`, the optional `.baltor/night/estimates.json`,
and for `status` and `mark` the queue and the status file. Every input needs its `record_type`; settings with an
unknown key are refused. Outputs: one JSON object per run (`night_queue_gaps/v1`, `night_queue_plan/v1`,
`night_queue_state/v1`, `night_queue_mark/v1` or `night_queue_refused/v1`), the queue written once, and the
status file. Exit 0 success, 1 nothing queued or a move not allowed now, 2 refused input (missing file, duplicate
JSON keys, a bad setting or ticket, estimates to fix, an existing queue or a status file left from an earlier
queue, a status file of another queue).

## Effects

`reads_fs`; `writes_fs` (one queue file with exclusive creation; the status file through a temporary file and a
rename; the model writes the estimates file; tests write only in temporary folders); `spawns_process` (the model
starts the helper with `python3 -I -B`; tests start it with the current interpreter and load it by path to compare
its constants with the contracts). No network, no model call, no secret read.

## Closest existing items

- `split_a_large_request_into_assignable_parts` (starter, prose): cuts one request into pieces. This package
  orders many tickets for one night, holds unready ones with reasons and enforces a budget in code.
- `ticket_triage_packet` (wave 5, a09): triages ticket content; this command consumes estimates and writes the
  plan that `record_blocker` and `night_preflight` read.
- `overnight_ticket_plugin` (wave 5, a11): after its own repair it reads this `night_queue/v1` shape (`items`
  with `id`, `title`, `position`) and binds its result records to the SHA-256 of the queue bytes. Keeping statuses
  out of the queue keeps those records valid; the after-repair probe ran its `night_status.py` on a queue planned
  here and it named the first ticket. a11 keeps its own per-ticket result records, so a night that uses both still
  has two progress records; the integrator picks one.
- `unattended_run_rules` (wave 5, a14): keeps its own start and finish ledger, a third progress record.
- `morning_report_packet` (wave 5, a09) reads `tickets[].ticket_id` from its `queue_path`, the shape a11 used
  before its repair. With this contract it must read `items[].id`; until the integrator aligns it, a host sets
  its `queue_path` to null.

## Positive example

The examples hold seven synthetic tickets, a 240 minute and 200 call budget with a 10 percent reserve, one
estimate, and one hold that the model wrote for the unclear T-104. `plan` queues T-101, then T-103 (it depends on
T-101), then T-102, for 105 of 216 usable minutes and 130 of 180 usable calls, and holds T-104 (no check),
T-105 (high risk), T-106 (over budget) and T-107 (waits for T-106). The queue validates against its contract.

## Known-wrong example

Ordering by priority alone starts with T-102, T-104 and T-105: a ticket nobody can verify and a high-risk change
run first, and a 400 minute rewrite exhausts the budget
(`test_known_wrong_priority_only_plan_is_not_what_the_helper_writes`). The critic's two cases are tests: a ticket
with only a risk label is asked for its minutes and calls instead of being hidden as a bad estimate
(`test_known_wrong_a_risk_label_alone_is_asked_for_not_hidden`), and minutes written as the string "30" appear in
`fix_estimate`, keep `ready_to_plan` false and make `plan` refuse
(`test_known_wrong_malformed_estimates_are_reported_and_block_planning`).

## Harness placement and verification state

No harness binary was run. Claude Code `.claude/commands/plan-night-queue.md` and Gemini CLI
`.gemini/commands/plan-night-queue.toml`: documented in the spec table. OpenCode
`.opencode/commands/plan-night-queue.md`: documented and observed in the repository guide (the spec table names
`.opencode/command/`). Copilot `.github/prompts/plan-night-queue.prompt.md` (now with `agent: agent`, following
the VS Code prompt file documentation read on 2026-09-24) and Cursor `.cursor/commands/plan-night-queue.md` (the
Cursor documentation page read the same day described skills, not a command folder): unverified. The command
takes no arguments. Support files, examples and contracts go to `.baltor/plan-night-queue/`; tests are not
placed. The host must bind a trusted `python3`.

## Customer requests

- "Pick which of these tickets my local model should try tonight and skip the risky ones."
- "I have seven hours and about three hundred model calls. Make a work order that fits."
- "Tell me why a ticket was left out of tonight's run, and show me which tickets are done in the morning."

## Limits

The risk rule is guidance for the model, not a measured classifier; estimates are guesses the helper cannot
check. The merge rule only raises values, so a model cannot correct an estimate that is too high in the ticket.
The queue is not updated when tickets change; move the old queue and status file aside and plan again. One writer
at a time is assumed for the status file. A number written with a decimal point, such as 30.0, is refused even
though JSON Schema would call it an integer. Integer checks in the helper are stricter than the schemas there.

## Repair history

Critic round 2 found: a ticket with only a risk label hidden as `bad_estimate`; a malformed estimate that
emptied `need_estimate` so the model's loop ended while `plan` held the ticket in silence; no published
contracts; the `night_queue/v1` collision with a11; ticket text not marked as data; no a06 file that marks a
ticket in progress or done; and a Copilot variant without `agent`. The repairer reproduced both blocking cases at
digest `e83f7ffe` (`repairer-a06_step_ritual_commands/baseline/`) and made the changes above. The a11 collision
was already resolved on the a11 side (its schema now reads `items`); this package now owns the contract and keeps
the queue bytes stable for a11's records. Every input now needs its `record_type` and a one-line title of 1 to 200
characters, because a11 refuses items without a title.

Mutation checks: eight guards removed one at a time (tickets missing only some fields, fix_estimate reporting,
the risk merge, the budget, dependencies before a start, one ticket in progress, fresh evidence for done, the
queue binding of the status file) were each killed by a named test while the unchanged copy passed. The
embedded schema validator in the tests agreed with the jsonschema library on every valid and mutated example
(`repairer-a06_step_ritual_commands/crosscheck-embedded-results.json`). Native loading of the command is
unobserved. Every run is listed in `PRECHECKS.txt`.
