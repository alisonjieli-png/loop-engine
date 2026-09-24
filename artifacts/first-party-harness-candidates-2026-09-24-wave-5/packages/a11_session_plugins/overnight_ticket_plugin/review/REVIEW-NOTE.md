# Review note: overnight_ticket_plugin

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a11_session_plugins, model family
anthropic. This note is never delivered to a customer harness.

## Method

One session kit for tickets worked overnight, one ticket per fresh harness
session. Three parts work together:

1. A session start hook (`scripts/session_start.py`) reads the night queue,
   the night ticket list and the per-ticket result records, and adds one
   short message to the new session: the next open ticket and its position,
   that ticket's acceptance criteria and check command, the counts of closed
   tickets and the handoff written by the most recently closed ticket.
2. A night status command prints the same state as JSON on request
   (`scripts/night_status.py`). It writes nothing.
3. A ticket closer agent runs the ticket's check command itself, lists the
   changed files with `git status` and writes exactly one result record per
   ticket through `scripts/close_ticket.py`.

`close_ticket.py` refuses: a ticket that is not the next open ticket, a
second record, `fixed` without passing evidence, `fixed` without the
ticket's own check command, `skipped` with changed files, `blocked` without
a usable handoff, unsafe paths, secret-shaped text, and any closing while a
result record has a problem. The deterministic rules live in the scripts;
the prose tells the model what to run, what to read and when to stop.

## Authoring basis and sources

Original text and code written for this package under the repository MIT
licence. No outside text or code was copied. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package
  file contract this package follows.
- `case-studies/overnight-cheap-model-with-and-without-baltor/DESIGN.md`: a
  queue of steps worked overnight, each in a fresh harness, with crash and
  resume; it shaped the queue position and the resume hint.
- `src/loop_engine/core/node_provisioning.py`: one fresh folder per step.

Plugin layout facts come from the research file
`HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md` in the Codex integration
worktree and from the Codex plugin candidate `focused_brief_plugin`, whose
SessionStart hook ran natively on Claude Code 2.1.280. That research file
documents `.cursor-plugin/plugin.json` for rules, agents, commands and hooks,
and says a Cursor `sessionStart` hook cannot block startup. The remaining
Cursor names (`hooks.json` with `version: 1` and timeouts in seconds, the
`additional_context` output, `CURSOR_PROJECT_DIR` and `${CURSOR_PLUGIN_ROOT}`)
follow Cursor pages that an earlier run of this generator read on 2026-09-23.
No copy of those pages is saved here, so a reviewer should treat them as
unverified until the integrator's probe runs.

The queue format is not invented here. The wave 5 package `plan_night_queue`
writes `.baltor/night/queue.json` as `night_queue/v1` with an ordered `items`
list (`position`, `id`, `title` and planning fields) and a `held` list, and
reads the ticket list `.baltor/night/tickets.json` (`night_tickets/v1`). This
plugin reads those same shapes and ignores fields it does not use.

## Inputs and outputs

Inputs: the queue, the optional ticket list and the records under
`.baltor/state/overnight-ticket-plugin/results/`. The closer reads one draft
on standard input (`contracts/ticket-result-draft.schema.json`).

Outputs: the hook prints one JSON object in the harness's own shape; the
status script prints one JSON summary; the closer writes one
`overnight_ticket_result/v1` record (`contracts/ticket-result-record.schema.json`,
proposed here) and prints its path and SHA-256. Each record stores the
SHA-256 of the queue bytes it was written for, so a record left from another
night is reported as `record_from_another_queue` and never counts as
progress. Exit codes: 0 done, 1 rule failed, 2 refused input.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The hook and the status
script only read. The closer creates one file under
`.baltor/state/overnight-ticket-plugin/results/` with exclusive create. The
agent runs `git status --porcelain`, the status script, the ticket's check
command and the closer. Tests write only in temporary folders. No network,
no model call, no secret read. Hook commands start `python3 -I -B`; the host
must bind a trusted interpreter, because an earlier independent review showed
that a `python3` found first on `PATH` can be replaced.

## Closest existing items

- `focused_brief_plugin` (Codex candidate, Claude Code only): a startup hook
  with fixed guidance text, a brief structure checker command and an advisory
  reviewer agent. It keeps no state across sessions. This plugin reads night
  state, names a specific next ticket and writes per-ticket records.
- `validate_focused_attempt_handoff` (planned Codex method): validates one
  handoff; this plugin shows the last one and writes per-ticket records.
- `carry_earlier_decisions_forward_without_the_whole_transcript` (starter text
  skill): advice on carrying decisions forward; no files or scripts.

Wave 5 boundaries: `plan_night_queue` builds the queue and this plugin only
reads it; `write_step_handoff` writes one step's handoff note while work
continues; `record_blocker` files a blocker; `night_preflight` checks the
night before it starts; `morning_report_packet` compiles the night and
`verify_morning_report_claims` checks that report. This plugin plans nothing,
compiles no report and checks no report. It shows live state and writes the
final record of each ticket.

## Positive example

With `examples/night/` as the workspace, the Claude Code hook answers
`Next ticket: 2 of 3, T-102: Totals row counts refunds twice.`, the two
acceptance criteria, `The ticket's check command: python3 -m unittest
tests.test_totals`, the counts and the T-101 handoff. Sending
`examples/ticket-result-draft.json` to the closer in a copy of that workspace
writes `T-102.json` as blocked and names `T-103` as next.

## Known-wrong example

A small model finishes T-1, its own test run exits 1, and it asks for the
outcome `fixed`. The closer answers exit 1 with `fixed_with_failing_evidence`
and writes nothing (`test_fixed_with_a_failing_check_is_refused`). A model
that ran a different, passing test instead of the ticket's check command gets
`fixed_without_ticket_check`. A model that jumps to T-2 while T-1 is open
gets `ticket_not_next_in_queue`.

## Harness placement and verification state

- Claude Code: the plugin folder goes to
  `.baltor/plugins/overnight-ticket-plugin/` (plugin_directory_binding) and is
  bound with `claude --plugin-dir .baltor/plugins/overnight-ticket-plugin`.
  Binding and SessionStart context were observed on Claude Code 2.1.280 for a
  different plugin; this plugin was not run. The hook command uses the
  documented `${CLAUDE_PLUGIN_ROOT}`; the command and agent bodies use the
  workspace-relative placed path, which assumes the shell starts in the
  workspace root.
- Cursor: same folder with the `variants/cursor/` files. Listed in
  `unverified_targets`: expansion of `${CURSOR_PLUGIN_ROOT}` in a plugin hook
  command, the subagent front matter (`model`, `readonly`) and local plugin
  activation are not documented on the pages read and were not observed.
- No harness binary was run for this package.

## Customer requests

- "Each night my agent should pick up the next ticket and know what the last
  session left behind."
- "Show me which tickets got fixed overnight and which ones are stuck."
- "Before the agent moves on, make it run the ticket's test and write down
  proof that the ticket is really done."

## Limits

The record format is a proposal. The morning report packet of this wave reads
a queue with a `tickets` list, while the planning package writes `items`; the
integrator must settle one queue shape for both. `closed_at` uses the machine
clock. Two sessions closing the same ticket at once produce one record, and
the second gets `record_exists`. Secret shapes are generic and cannot catch
every secret. Ticket text in the session message is marked as data, but a
hostile ticket list could still mislead a model; the host owns the ticket
source.

### Pre-check history

The earlier draft of this package (digest `d5bdd7c8...`) read its own queue
shape with `tickets` and `night_id`. It passed the checker, but it conflicted
with the queue that `plan_night_queue` writes, so it was replaced. The first
report of that draft was refused for an empty helper file in `review/`; the
file was removed and the second report passed. The next version (digest
`f6027db7...`) was refused once for file modes, then passed.

The third run of this generator found one more conflict with the planning
step: `plan_night_queue` copies a missing ticket title as an empty string,
and version `f6027db7...` refused a title outside 1 to 200 characters, so
one untitled ticket would have stopped the whole night. The title is now
display text: any string up to 2,000 characters is read and shortened to 200
for display, and a ticket without a title is named by its id. Two new tests
cover it; with the old rule put back in a scratch copy, both failed, and
with the repair all 49 tests pass. Reports for each version stay in
`review/precheck-*.json`.
