# Review note: log_tool_activity

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a04_unattended_guard_hooks (model family anthropic), September 23, 2026. This note is never delivered to a customer harness.

## Method

One method: after each tool call, append one JSON line of at most 1024 bytes to the step's activity log. The line has six fields: `record_type` (`tool_activity/v1`), `time` (UTC, seconds), `harness`, `tool` (at most 64 printable characters), `target` and `outcome`. The target is a root-relative path for file tools (`[outside workspace]` for paths outside the root), or, for shell tools, the program and at most two short word arguments. For every other tool it is empty. The outcome is `ok`, `failed`, `interrupted`, `timeout`, `denied` or `unknown`. Tool results, file contents, command output and search patterns are never written. A shell argument is dropped, with everything after it, when it holds `=`, a space or a character other than letters, digits, dots, underscores and hyphens, starts with a digit, or is longer than 24 characters. So a morning report can count what the agent did without holding what it read.

The log stops at a size limit (default 4 MiB, `--max-log-bytes` from 4096 to 64 MiB). It adds exactly one `log_full` line; the decision uses the largest possible line, so nothing is written after the marker. Appends are whole single writes under a file lock. The logger fails open: every problem gives exit status 0, the answer `{}` and one line on standard error, so it can never block the agent.

## Authoring basis and sources

Original code and text. Sources at the pinned revision: `catalogue_packages.py` (package format) and the overnight case study design `case-studies/overnight-cheap-model-with-and-without-baltor/DESIGN.md`, which scans every tool call after a run. It also draws on `tools/overnight_queue.py`, an overnight queue that must never block. Claude Code events `PostToolUse` and `PostToolUseFailure` and the `tool_response.interrupted` and `is_interrupt` fields follow https://code.claude.com/docs/en/hooks; `PostToolUseFailure` was not observed on this machine. The Cursor names `postToolUse`, `postToolUseFailure` and `failure_type` were read from a snapshot of Cursor's hook page in the locally cloned outside project madebywild/agent-harness (`docs/cursor-hooks.md`, revision 2ecf44f), for names only. The Copilot `toolResult.resultType` values are the producer's reading of GitHub's hook reference.

## Inputs and outputs

Input: one event as JSON on standard input (at most 1 MiB). Arguments: `--harness`, optional `--event`, `--root` and `--max-log-bytes`. No policy file. Output: `{}` on standard output and a new line in `.baltor/state/log-tool-activity/activity.jsonl`.

## Effects

Reads standard input and, only when the log is near its limit, the last 256 bytes of its own log to find the full marker. Writes only inside `.baltor/state/log-tool-activity/`, creating folders one level at a time. It refuses a symbolic link in the folder path and opens the log without following a link. Declared: `reads_fs`, `writes_fs`, `spawns_process`. The first pre-check run refused the package because `reads_fs` was missing: the log tail read and the tests' file reads use it. The declaration was corrected; the check was not changed. No network, no program started, no transcript read even when the event names one. Some personal data can reach the log through file paths; the harness user's email address, which Cursor events carry, is never written.

## Closest existing items

None found in the inventory. The Codex `focused_brief_plugin` hook adds startup context and records nothing. The wave 5 packet `morning_report_packet` compiles a report and `verify_morning_report_claims` checks one; this hook only produces the raw per-call lines they can count.

## Positive example

A `Bash` call running `python3 -m pytest -q tests` adds a line with target `python3 -m pytest` and outcome `ok`, and none of its output.

## Known-wrong example

A logger that copies `tool_input` would write `mytool --token=VALUE upload` or a file's contents into the log. This one writes `mytool` and `src/app.py`. The tests pass a marker string through commands, contents and results, and fail if it reaches the log. A mutant that treats shell tools as file tools fails two tests; one without the size decision fails the full-log test.

## Harness placement and verification state

Claude Code: `.claude/settings.json` with `PostToolUse` and `PostToolUseFailure`, matcher `*`, merged; documented, not observed here. Cursor: `.cursor/hooks.json` with `postToolUse` and `postToolUseFailure`; unverified. Copilot: `.github/hooks/log-tool-activity.json` with `postToolUse`; unverified. For a logger, the "refused" samples are events the logger declines to record, and they still exit 0. The samples use the checker's sandbox path `/work`; the tests rewrite it. No harness binary was run.

## Customer requests

- "Keep a log of every tool call my overnight agent made, but no file contents."
- "I want to count test runs and failed commands in the morning."
- "Record what the agent touched without storing secrets from its commands."

## Limits

A short secret passed as a plain word argument, such as a seven-letter password after the program name, can still appear as a target word; the command head rule lowers this risk but cannot remove it. Paths are recorded, so a path that is itself sensitive is recorded too. Calls refused before they ran are recorded only where the harness sends an after-call failure event. Check history is in `review/PRECHECKS.txt`.
