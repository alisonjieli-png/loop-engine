# Review note: Unattended run operating rules

Candidate only. Not approved, staged, served or published.

This note is for the independent review panel. It is never delivered to a harness.

## Method

A composable instruction section for runs that nobody watches, such as tickets worked overnight on a local model. It sets these rules: tickets come only from the list in the assignment (or only this step's ticket), one ticket at a time, only actions that can be undone inside the workspace, a checkpoint after every ticket with saved check output, a blocker record instead of a question to an absent person, and a stop after the last listed ticket.

The rules that code can decide live in `scripts/ticket_ledger.py`, not in prose:

- `start --ticket KEY` refuses while another ticket is open and refuses a ticket that already has a finish line, so a restarted harness cannot silently redo or abandon work.
- `finish --ticket KEY --status done|blocked|skipped --summary TEXT` closes the open ticket. `done` needs at least one evidence file. `blocked` needs `--needs`, which names what is needed and from whom.
- Every evidence file must be a nonempty file inside `.baltor/state/unattended-run-rules/` (after links are resolved), written after the ticket's start line (with two seconds of tolerance for coarse file system clocks), not named by an earlier finish line, and not the ledger or its lock file. So the instruction file itself, an old test log or the previous ticket's log cannot pass as proof.
- `start` and `finish` hold an exclusive lock on `ledger.lock` while they read and append, and `status` holds a shared lock. A command that waits longer than `--lock-timeout` (default 10 seconds) is refused with `ledger_busy`, which does not stop the run.
- `status` lists the open ticket, the counts and the last 100 finished tickets, so a model can see which listed tickets are left.
- Every refusal carries a `next` field with the action to take, and `"stop_run": true` when the ledger itself cannot be trusted. An unexpected file system error is also answered as one JSON object.

The judgment rules (what can be undone, when a choice is safe) stay in the section, because only the model can apply them.

## Authoring basis and sources

Original text and code, MIT, written for this wave. Repository files at `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format.
- `tools/overnight_queue.py`: an unattended queue never blocks because nobody can answer, and a resumed run skips finished work instead of redoing it.
- `docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md`: a run ends for a recorded reason, and each failure becomes a typed next action.
- `examples/29_intelligence_service/starter-catalogue/bodies/resolve_missing_information.md`: the closest served item.
- `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`: added material cost 45 to 446 percent more prompt tokens per step and helped nothing on that population, so the always-loaded text stays within the class limit (349 words).

The lock uses `fcntl.flock` from the Python standard library. No outside text or code was copied or paraphrased.

## Inputs and outputs

Inputs: ticket keys (1 to 64 letters, digits, dots, dashes or underscores), one-line summaries and needs of at most 500 characters, and evidence paths relative to the workspace root. Output: one JSON answer per command, the append-only file `.baltor/state/unattended-run-rules/ledger.jsonl` holding `unattended_ticket_ledger_line/v1` start and finish lines, and the empty lock file `ledger.lock` beside it. The ledger is bounded to 1 MiB.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The script reads the ledger and evidence files, creates its folder and lock file and appends lines with a no-follow open. The model runs the script as a process. The rules tell the model to save check output to files. The tests write only inside temporary folders. No network, no model call, no secret, no deletion.

## Closest existing items

- Starter `resolve_missing_information` (served): resolves each missing fact and asks the person when only the person can answer. This section covers the case where no person can answer before the run ends: make a safe reversible choice and record the assumption, or finish the ticket as blocked and move on.
- Wave 5 a06 `record_blocker` (command candidate): writes a full blocker record and marks the ticket blocked. Here the ledger holds a one-line blocker entry with an evidence file; the two can be used together.
- Wave 5 a06 `write_step_handoff` and a09 `morning_report_packet`: a handoff and a report. The ledger is a sequencing record that they can read, not a report.
- Wave 5 a14 `unattended_git_rules`: git operations for the same runs; its blocking rule saves the git answer in this section's state folder, so the ledger accepts it as evidence.
- Wave 5 a14 `focused_step_packet_rules`: when both are composed into one step, rule 2 here (only this step's ticket without a list) agrees with its rule that the objective is the only goal.

## Positive example

For ticket ABC-12 the model runs `start --ticket ABC-12`, fixes the date parser, saves the test output in `.baltor/state/unattended-run-rules/ABC-12-checks.txt`, and runs `finish --ticket ABC-12 --status done --summary "Fixed the date parser" --evidence .baltor/state/unattended-run-rules/ABC-12-checks.txt`. The ledger then holds one start line and one finish line, and `status` shows no open ticket and ABC-12 as done. With no further ticket on the list, the model reports that answer and stops. The test `test_finish_command_of_the_section_works_as_written` runs the finish command exactly as the section writes it.

## Known-wrong example

After a crash and restart, a model starts ABC-13 while ABC-12 is still open. `start --ticket ABC-13` exits 1 with code `another_ticket_open`, writes nothing, and its `next` field says to finish ABC-12 first (`test_second_ticket_while_one_is_open_is_refused`). A second known-wrong case: the model finishes a ticket as done with `--evidence AGENTS.md`. The ledger refuses it with `evidence_outside_state_folder` (`test_instruction_file_as_evidence_is_refused`). The tests also refuse: done without evidence, an empty evidence file, evidence written before the ticket started, evidence already used by an earlier ticket, the ledger as evidence, a link in the state folder that points at a workspace file or leaves the workspace, blocked without needs, a finished ticket started again, finishing a ticket that is not open, a state folder that is a link, a malformed ledger, a bad ticket key, a two-line summary, and a write while another command holds the lock. Twelve rounds of two simultaneous starts must open exactly one ticket and leave a readable ledger.

## Harness placement and verification state

- `AGENTS.md` is composed into the step's root `AGENTS.md` for codex, opencode and pi (observed on this machine in recorded probes), goose (documented in `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` of the shared checkout) and kimi_cli (unverified).
- Claude Code gets `CLAUDE.md` holding `@AGENTS.md` (the file is observed, the import is documented). Gemini CLI gets `GEMINI.md`, a byte copy of `AGENTS.md` (documented).
- The script and `LICENSE` go to `.baltor/unattended-run-rules/`. Tests are not placed.
- Not observed anywhere: a harness following this section or running the script, Kimi CLI reading a project `AGENTS.md`, and the compiler composing the one-line `CLAUDE.md` import into an existing `CLAUDE.md` (it should keep a single import line).
- The section starts the script as `python3 -I -B`. The host must bind a trusted interpreter, because an earlier independent review showed that a `python3` found first on `PATH` can be replaced.

## Customer requests

- "My agent works tickets overnight. How do I stop it from starting a new ticket when the last one crashed halfway?"
- "When the agent gets stuck at 2am I want a note saying what it needs, not a question nobody sees."
- "Rules for a local model working alone that keep it from doing anything I cannot undo."

## Limits

- Text does not enforce itself. The section cannot stop a model from deploying or deleting data; pair it with permission settings and guard hooks (wave 5 a13 and a04).
- The ledger trusts the model to call it. It checks where, when and how often an evidence file was used, not what the file says: a model can still write a file that claims a pass.
- The file time check uses the machine clock and file modification times; a clock that jumps backwards, or a file touched after the ticket started, defeats it.
- Where Python has no `fcntl` module (Windows), the ledger runs without the lock and assumes one writer. Tested with Python 3.14 and 3.10 on Linux only; Windows paths and interpreters are untested.
- The ticket list is read by the model from its assignment; the ledger does not check that a started ticket is on that list.
- No measurement shows that the section improves outcomes.

## Pre-check history

Every command output is kept in `review/PRECHECKS.txt`, and every checker report in `review/precheck-*.json`; the newest report is the gate record.

- Generation rounds (2026-09-23): fill and check passed with no warning for package digests `e9159957`, `ecf4f9d3` and `74e147c0`; 16 tests on Python 3.14 and 3.10; 5 of 5 mutants caught.
- Independent critic (2026-09-23, recommendation repair): the rules said "go on to the next ticket" without saying where tickets come from or when the run ends; "save every change" was unclear; the instruction file itself passed as evidence and one evidence file passed for two tickets; the ledger had no lock, and simultaneous starts could leave an inconsistent ledger that stops the night; the git section's "answer attached" did not fit a one-line summary; rule 4 forbade deleting the model's own scratch files.
- Repair (2026-09-24): rules 2 and 10 (ticket list, stop after the last ticket), rule 7 (saving means written to the file; commits belong to the git section), rule 5 (deletion limited to files that existed before the ticket), rule 8 (a long error or answer goes in a file passed with `--evidence`), the evidence rules and the lock in the script. The repairer also found that two simultaneous starts could crash with a Python traceback while both created the state folder; folder creation now accepts a folder that appears at the same moment, and any file system error is answered as JSON. In a stress run of 60 rounds of three simultaneous starts and one status, the predecessor ledger failed 57 rounds and the repaired ledger failed none.
- Repair checks: the first repair check passed (digest `c14a0baa`, 23 tests). A mutation run then showed that the section text test missed a wrong evidence path, so it was replaced by `test_finish_command_of_the_section_works_as_written`; 9 of 9 mutants of this package are caught by their named tests (37 of 37 across the assignment), and 12 of the repaired tests fail against the predecessor payload. The final fill and check are recorded in `review/PRECHECKS.txt`.
