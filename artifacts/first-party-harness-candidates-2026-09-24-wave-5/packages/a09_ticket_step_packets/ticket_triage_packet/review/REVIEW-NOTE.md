# Review note: ticket triage step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a09_ticket_step_packets, repaired by the a09 repairer of the same wave after the critic review, model family anthropic. This note is never delivered to a harness.

## Method

One focused step that sorts one ticket into go, hold or split before any code changes, for a night of unattended work on a small model. The step reads the ticket and a few repository files, compares the work with limits the host declares (allowed path prefixes, a file limit, and a plain list of things unavailable tonight), and returns one `ticket_triage_decision/v1` object as its final answer. Every sentence of the ticket that states a wanted result lands once: word for word in `acceptance` when a test or a command can prove it, or as a question in `open_questions` when nothing can. The decision rule is ordered: any open question or need gives hold; two or more separable changes give split; a change that fits the limits gives go; anything else gives hold with a question that names the broken limit. A go names the files to read and the first test to write, with a command as a list of strings that the reproduction step can run without a shell. The step changes no file and runs no command, so its only effect is reading.

## Authoring basis and sources

Original text written for this wave. The packet follows `catalogue_package/v1` (`src/loop_engine/core/service_runtime/catalogue_packages.py`) and the task packet layout of the wave 5 specification. `contracts/task.json` has exactly the `node_assignment/v3` fields of `src/loop_engine/core/node_provisioning.py`, with kind `reason`, because the deliverable is an answer, not a file. `src/loop_engine/core/instance_instructions.py` informed the rule that an instruction file describes authority and never grants it. The closest starter item is in `examples/29_intelligence_service/starter-catalogue/items.json`. The Codex focused step packet example (review worktree, September 23) and the pilot step template `repair_one_failing_test` were read for shape only; no text was copied.

## Inputs and outputs

- Input: `.baltor/step/input.json` (`ticket_triage_input/v1`): ticket id and path, allowed path prefixes, maximum files changed, the list of things unavailable tonight, and `test_command_example`, one existing single-test command as a list of strings.
- Output: the final answer, one JSON object (`ticket_triage_decision/v1`) that holds every key in every decision. The output schema encodes the cross-field rules with `if` and `then`: a go needs a first test, an acceptance statement, a file to read, and empty `needs`, `parts` and `open_questions`; a hold needs a question or a need and a null `first_test`; a split needs two parts, a null `first_test`, and empty `open_questions` and `needs`. `first_test.command` is a list of strings, the program first, the same form as `test_command` of `ticket_reproduction_input/v1`, so the host copies it without conversion.
- Examples: `examples/ticket.md` with `examples/input.json` and the go answer `examples/output.json`, and the known-wrong case as a made-up ticket `examples/hold-ticket.md` with `examples/hold-input.json` and the hold answer `examples/hold-output.json`. Acceptance statements in both answers are copied word for word from their ticket files.
- Markers the host renders: `STEP_ID`, `HARNESS_STYLE`, `TICKET_ID`, `TICKET_PATH`, `REPOSITORY_NOTES`.

## Effects

`reads_fs` only. The entry tells the model to use reading and searching tools and to create, edit or delete nothing. There is no shell block and no script, so `spawns_process` is not declared. A harness such as Codex may read files through its own shell tool; that is the harness's mechanism for reading, and the host's sandbox should allow only read commands for this step.

## Closest existing items

- Starter `questions_to_ask_before_starting_work` (question set): thirteen general questions asked before any work. This packet is not a question list. It is a bounded step with a typed three-way decision, a declared list of unavailable capabilities, a first test to write and a schema the host can check. It asks only the questions that the ticket leaves open.
- Wave 5 `plan_night_queue` (a06 command) orders many tickets against a budget; this packet decides for one ticket whether it may enter that queue. Wave 5 `extract_ticket_acceptance_criteria` (a03 script) parses a ticket into criteria; this packet can use its output but also judges readiness.
- Outside staged `skill_to_tickets_5346ffd803e8` (title only) turns work into tickets; it does not judge overnight readiness.

## Positive example

`examples/ticket.md` (T-104) says a cart badge shows "1 items" for one item and lists two expected results. Both are checkable, the change fits `shop/` and `tests/`, needs nothing unavailable, and the answer in `examples/output.json` is go with `tests/test_cart_badge.py`, the test `test_badge_uses_singular_for_one_item` and a command as a list of strings.

## Known-wrong example

A ticket with one checkable line and one vague line, answered go with the vague line dropped in silence. `examples/hold-ticket.md` (T-131) adds "The badge should load faster." The correct answer, `examples/hold-output.json`, keeps the checkable line in `acceptance`, turns the vague one into an open question and answers hold. The schema now refuses a go or a split that still lists an open question, a hold that omits the `first_test` key, and a go whose command is one shell string. These were run with the Python `jsonschema` validator (Draft 2020-12) and each was refused, as were the earlier four known-wrong answers (a go without a first test, a go with needs, a hold with no question and no need, a split with one part); both examples validate. A go that drops a vague line and also writes no question for it still matches the schema: finding the vague line is the model's judgment, which the entry, `node_context.md`, the checklist and the hold example now state.

## Harness placement and verification state

- Codex: root `AGENTS.md` pickup observed in earlier probes (pilot discovery record and the Codex packet pickup probe, Codex 0.155.1). Composed with `compose_instruction_section`.
- Claude Code: `CLAUDE.md` holds only `@AGENTS.md`, now placed with `compose_instruction_section` instead of `copy_exact_bytes`. The host adds the import line once to an existing `CLAUDE.md`, or creates the file when none exists, and never replaces a customer's file. The critic reported from the official memory documentation (fetched September 23, 2026) that Claude Code reads only `CLAUDE.md` files when both exist; `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` (on `origin/main` after the pinned revision) records the same for Claude Code 2.1.280. The import is documented; no probe observed it for this packet.
- OpenCode and Pi: root `AGENTS.md` observed in earlier probes. Pi 0.73.1 was observed to ignore `node_context.md` on its own, which is why reading the step files is the first action.
- Gemini CLI: `GEMINI.md` is documented, not observed. `AGENTS.md` is not placed for Gemini, to avoid a second copy if the context file names are widened.
- Goose: `AGENTS.md` is documented for Goose 1.50.0, not observed; listed in `unverified_targets`.
- Files under `.baltor/step/` are read on purpose; no harness loads them by itself. No harness binary was run for this packet. The a14 `focused_step_packet_rules` check accepts the rendered packet (repairer probe `repairer-a09_ticket_step_packets/a14-interop-after-repair.txt`).

## Customer requests

- "Before I leave, tell me which of these tickets the agent can finish overnight without me."
- "Check whether T-231 is clear enough to hand to the local model, and what test it should write first."
- "Sort the backlog items into ready, needs an answer from me, and too big."

## Limits

- The decision is a judgment by the model. The host or a person accepts it; a schema match is not acceptance.
- The schema cannot see a wanted result that the model neither copied nor asked about. The word for word rule lets a reviewer compare `acceptance` with the ticket text line by line.
- The list of unavailable things is plain text from the host, so matching needs to judgment is not exact.
- A split is not worked tonight; turning parts into tickets is a separate step.
- The step cannot confirm that the proposed test command runs; the reproduction step does that.

## Repair after the critic review

The critic recommended repair. Every finding and what changed:

1. Blocking, decision rule: step 1 now copies provable statements word for word and turns every other wanted result into an open question; step 4 is an ordered rule in which any open question or need gives hold; `node_context.md` Acceptance says a go has no open question and no need; the output schema adds `open_questions` `maxItems` 0 to go, and to split together with `needs` `maxItems` 0, so the rule is the same for both answers that are not hold.
2. "In its own words": now "word for word into `acceptance`", and the example acceptance lines are copied from the new example ticket files.
3. Hold and split keys: the Assignment says every answer holds every key and `first_test` is null for hold and split; `node_context.md`, the checklist and the new hold example show it.
4. Command form: `first_test.command` and `test_command_example` are lists of strings, the program first, matching the reproduction input.
5. CLAUDE.md collision: placement changed to `compose_instruction_section`, as described above.

The critic's probes before the repair are in `repairer-a09_ticket_step_packets/baseline-critic-probes-before-repair.txt`; the snapshot of the earlier bytes is `repairer-a09_ticket_step_packets/a09-predecessor-snapshot-20260924T052333Z.tar.gz`.

## Checks that failed before they passed

The generator's checker runs passed. During the repair, a count with the checker's own word count function (repairer helper `repairer-a09_ticket_step_packets/words.py`) found the new entry at 477 words, above the limit of 450; lines were shortened to 448 words before the first checker run on the repaired bytes. The known-wrong answers were run against the earlier schema first: a go with an open question and a go with a shell string command both matched it (`repairer-a09_ticket_step_packets/known-wrong-before-repair/triage-schema-on-old-contract.txt`). Every earlier report in `review/precheck-*` is kept.
