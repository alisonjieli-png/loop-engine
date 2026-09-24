# Review note: require_tests_before_stop

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a04_unattended_guard_hooks (model family anthropic), September 23, 2026. This note is never delivered to a customer harness.

## Method

One method: record, after each tool call, whether a source file was edited or the declared test command ran, as ordered sequence numbers in one state file. When the agent tries to finish, block the finish once if the last source edit comes after the last test run, and name the test command. A second attempt to finish for the same changes is let through and counted in `finishes_without_tests`, so a morning report can show it. Claude Code's `stop_hook_active` flag is also honoured. The gate therefore cannot keep an agent running without end, even when the model ignores the reminder. A test run that fails still counts, because running the tests and reading the result is the requirement; an interrupted or refused run does not count. A new `step_id` in the policy starts a clean record, so a reused workspace does not carry an older step's edits.

The gate fails open. When it cannot read its event, policy or state, it lets the finish happen and writes one line to standard error. Blocking a finish without knowing whether it already blocked could keep the agent running without end. A bad registration also exits 0: in Claude Code, exit status 2 at a finish would block it.

## Authoring basis and sources

Original code and text. Sources at the pinned revision: `catalogue_packages.py` (package format) and the served starter item `verify_the_requested_output` (check the result itself before reporting completion). Claude Code events `PostToolUse`, `PostToolUseFailure` and `Stop`, the `stop_hook_active` input and the `{"decision": "block", "reason": ...}` answer follow https://code.claude.com/docs/en/hooks. Cursor names (`afterShellExecution`, `afterFileEdit`, `stop` with `status`, answer `followup_message`) were read from a snapshot of Cursor's hook page in the locally cloned outside project madebywild/agent-harness (`docs/cursor-hooks.md`, revision 2ecf44f), for names only. Copilot `postToolUse`, `agentStop` and the `toolResult.resultType` field are the producer's reading of GitHub's hook reference and of the same project's event mapping notes.

## Inputs and outputs

Input: one event as JSON on standard input (at most 1 MiB), the policy `.baltor/step/require-tests-before-stop.json` (record `tests_before_stop_policy/v1`: `step_id`, `test_commands`, `source_globs`, `ignore_globs`) and the state `.baltor/state/require-tests-before-stop/state.json` (record `tests_before_stop_state/v1`). Arguments: `--harness`, `--event` (needed for Copilot, whose events carry no name), optional `--root` and `--policy`. Output: one JSON object, exit 0: `{}`, or the block answer of the harness.

## Effects

Reads standard input, the policy and the state. Writes only inside `.baltor/state/require-tests-before-stop/` (state file by atomic replace, and a lock file), creating the folders one level at a time and refusing a symbolic link on the way. Declared: `reads_fs`, `writes_fs`, `spawns_process`. No network, no program started, no transcript read, no file contents copied: the state holds at most 20 relative paths.

## Closest existing items

The served starter item `verify_the_requested_output` is prose asking the model to verify before claiming completion; this hook makes the harness hold the finish when the tests were not rerun. The pilot candidate `repair_one_failing_test` repairs a test, and the wave 5 verifier `verify_fail_then_pass_evidence` checks evidence after the fact; neither acts at the moment of finishing. The Codex `focused_brief_plugin` hook only adds context at startup.

## Positive example

Edit `src/app.py`, run `python3 -m pytest -q`, then finish: the answer is `{}`. With `cd src && python3 -m pytest` or `PYTHONPATH=src python3 -m pytest`, the run still counts.

## Known-wrong example

Edit `src/app.py`, then finish without a test run. The first finish must be blocked with the command named; the second must pass. A mutant that blocks every time fails four tests, and one that counts any shell command as a test fails the command test.

## Harness placement and verification state

Claude Code: `.claude/settings.json` with `PostToolUse` (matcher `Bash|Write|Edit|MultiEdit|NotebookEdit`), `PostToolUseFailure` (matcher `Bash`) and `Stop`, merged; documented, not observed here. Cursor: `.cursor/hooks.json` with `afterShellExecution`, `afterFileEdit` and `stop`; unverified, and Cursor's own follow-up limit also applies. Copilot: `.github/hooks/require-tests-before-stop.json` with `postToolUse` and `agentStop`; unverified, including whether `agentStop` honours a block answer. No harness binary was run.

## Customer requests

- "Don't let the agent say it is done until it has rerun the tests after its last change."
- "My overnight agent keeps stopping right after editing code without testing."
- "Remind the agent once to run pytest, but never trap it."

## Limits

Edits made by shell commands are not seen; pair this hook with the shell command allowlist so shell commands cannot write files. A test command is recognised by its first words, so a narrow run such as one test file also counts; declare longer starts when that matters. The hook proves that the command ran, not that the tests passed. Check history is in `review/PRECHECKS.txt`.
