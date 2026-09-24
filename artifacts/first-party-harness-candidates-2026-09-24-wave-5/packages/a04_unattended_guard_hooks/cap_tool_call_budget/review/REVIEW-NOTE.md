# Review note: cap_tool_call_budget

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a04_unattended_guard_hooks (model family anthropic), September 23, 2026. Repaired on September 24, 2026 by the wave 5 repairer of the same assignment and model family, after the findings of an independent critic. This note is never delivered to a customer harness.

## Method

One method: before each tool call, count the calls the hook lets through in the current step, and refuse every further call once the count reaches the declared `max_tool_calls`. The refusal tells the agent to stop new work and write its handoff to the declared `handoff_path`, what to put in it, and how many handoff calls remain. After the ceiling, file reads and writes of that exact path stay allowed up to `max_handoff_calls` (default 5). Without that exception the agent could not follow the instruction to write its handoff. The handoff path must resolve to itself: a symbolic link anywhere on it removes the exception, so the handoff cannot be used to keep editing another file. When that allowance is also used, or is zero, the refusal says to finish and put the handoff in the final message. Counting is serialised with a file lock, so parallel tool calls cannot pass the ceiling. A new `step_id` in the policy starts a new count, so a reused workspace does not inherit an older step's usage.

Ending the session: refusals are counted in `refused_calls`. In Claude Code, the refusal that brings the count to `max_refused_calls` (1 to 100, default 5) also answers `"continue": false` with a `stopReason`; the hook reference documents that this ends Claude's work and takes precedence over the permission decision. Handoff calls are not refusals, so the default leaves room to write the handoff first. Cursor and Copilot document no answer that ends the session from a tool call, so there the hook keeps refusing, and each refusal costs one more model turn until the harness's own limits end the run.

Answers: Claude Code and Copilot get the empty object `{}` for an allowed call, which leaves the decision to the harness's own permission settings. Cursor's hook page requires `permission` in every answer and blocks the action on an answer that does not match its schema. The first version answered `{}` there, which could have blocked every call from the first one; an allowed call now gets `{"permission": "allow"}`.

The package places a default policy at `.baltor/step/cap-tool-call-budget.json` (step `default-step`, 200 calls, handoff `.baltor/step/handoff.md`, 5 handoff calls, 5 refused calls). Installed as delivered, the hook therefore counts against a generous ceiling instead of refusing every call. The host replaces the file with the step's own budget and a new `step_id` before launch and can validate it with `--check-policy`.

The guard fails closed: malformed input, a missing or invalid policy, an unreadable state file, a state folder behind a symbolic link or an internal error refuses the call and tells the agent to stop and report.

## Authoring basis and sources

Original code and text. Sources at the pinned revision: `catalogue_packages.py` (package format), `night_budget.py` (budget the whole night and keep room to report), `tools/overnight_queue.py` (one call ceiling across all work) and the starter item `state_the_permissions_and_limits_of_an_assignment` (limits are numbers, and reaching one stops the work). Claude Code fields, the `continue` and `stopReason` output fields and the statement that `PreToolUse` fires for tool calls inside subagents follow https://code.claude.com/docs/en/hooks, read on September 24, 2026. Cursor `preToolUse`, `tool_name` values, `failClosed` and `permission` were read from a snapshot of Cursor's hook page in the locally cloned outside project madebywild/agent-harness (`docs/cursor-hooks.md`, revision 2ecf44f), for names only, and checked against Cursor's hook page on September 24, 2026. Copilot names match GitHub's hooks configuration reference as read on September 24, 2026.

## Inputs and outputs

Input: one event as JSON on standard input (at most 1 MiB), the policy `.baltor/step/cap-tool-call-budget.json` (record `tool_call_budget_policy/v1` with `step_id`, `max_tool_calls`, `handoff_path`, `max_handoff_calls` and `max_refused_calls`) and the state `.baltor/state/cap-tool-call-budget/state.json` (record `tool_call_budget_state/v1` with `calls_used`, `handoff_calls_used`, `refused_calls`). Arguments: `--harness`, optional `--root` and `--policy`, and `--check-policy` for the host. Output: one JSON object, exit 0: the allowed answer of the harness, its refusal, or in Claude Code a refusal that also ends the session.

## Effects

Reads standard input, the policy and the state. Writes only inside `.baltor/state/cap-tool-call-budget/` (state by atomic replace, a lock file), creating folders one level at a time and refusing a symbolic link. Declared: `reads_fs`, `writes_fs`, `spawns_process`. No network, no program started, no transcript read.

## Closest existing items

None found in the inventory. The starter item `retry_with_backoff_inside_a_declared_budget` limits retries of one operation; `night_budget.py` shares wall-clock time between steps inside this repository's runtime. The staged outside title "Token Budget Advisor" is a text skill about tokens; its body was not read. None stops a customer harness at a call ceiling while keeping the handoff reachable.

## Positive example

With 40 of 40 calls used, a `Write` to `.baltor/step/handoff.md` gets `{}` (in Cursor `{"permission": "allow"}`).

## Known-wrong example

With 40 of 40 calls used, `python3 -m pytest -q` must be refused. A cap that also refuses the handoff write leaves the agent unable to do what the refusal asks. The critic found three more wrong cases, now tested: the Cursor answer `{}` for an allowed call, the missing default policy, which left an installed hook refusing every call, and a hook that never ended a session that kept calling tools after the ceiling.

## Harness placement and verification state

Claude Code: `.claude/settings.json`, `PreToolUse` with matcher `*`, merged; documented, not observed here. The matcher also covers `Monitor`, `PowerShell` and calls made inside subagents. Cursor: `.cursor/hooks.json`, `preToolUse` for every tool with `failClosed: true`; unverified. Copilot: `.github/hooks/cap-tool-call-budget.json`, `preToolUse`; documented, unverified. The default policy goes to `.baltor/step/cap-tool-call-budget.json` for all three. The samples run with `--root examples/budget-spent`, a small synthetic workspace whose counter is at the ceiling, and use the checker's sandbox path `/work`. No harness binary was run.

## Customer requests

- "Stop my overnight agent after 60 tool calls and make it write a handoff."
- "A small model keeps repeating the same tool calls; cap them per step and end the run."
- "Limit how much work one step can do before it has to hand over."

## Limits

The count and the policy are files in the workspace, so the cap holds only while the agent cannot change them. An agent that can edit `.baltor/step/cap-tool-call-budget.json` or delete the state file resets its own count. Pair this hook with the workspace write guard of this wave, which protects `.baltor`, and with the shell command allowlist, which refuses shell writes. The write guard's policy must list the handoff path in `writable_globs`; its delivered default does. The count includes calls that another hook later refuses, because hooks for one call run side by side. Claude Code documents that tool calls inside subagents run the same hooks, so they count; for Cursor and Copilot that is unverified. A ceiling bounds calls, not tokens, time or money. Without `fcntl` (Windows) the count is not locked. In a Claude Code worktree session the handoff path points into the main checkout, which Claude Code's own worktree isolation blocks, so a capped agent there finishes with its final message instead. Check history: every checker run is recorded in `review/PRECHECKS.txt`; the repair's mutant runs and the failing run of the new tests against the earlier hook are kept in `repairer-a04_unattended_guard_hooks/successor-work/` of the wave folder.
