# Review note: night_preflight

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a06_step_ritual_commands (family anthropic), repaired by the a06 repairer
on 2026-09-24 after the second critic round. File class: command_file. Version 0.1.0. This note is never
delivered to a harness.

## Method

One named command, run in the harness and with the model that will work through the night, decides go or no-go
before a person leaves. A tested helper runs five checks and writes a new report every time:

1. `structured_tool_calls`: `probe` writes a fresh random nonce and prints it. `check` passes only when that exact
   nonce comes back, within 15 minutes (adjustable from 1 to 120), and only once. A model that writes its tool
   call as text never runs the probe and never sees the nonce; an invented value matches no probe file.
2. `budgets`: `.baltor/night/settings.json` has `record_type` `night_settings/v1`, no unknown key, and whole
   numbers in range for `time_minutes` and `model_calls`.
3. `guards`: every path in `guard_files` exists inside the workspace and is not empty; a JSON file must be one
   nonempty object. Recognized files get a content check. `.claude/settings.json` and
   `.claude/settings.local.json` fail with `defaultMode` `bypassPermissions` or an allow rule for every shell
   command (`Bash`, `Bash(*)`, `Bash(:*)`, `Bash(**)`), and hold a guard when they have deny rules, hook commands,
   an enabled sandbox or the default mode `dontAsk` or `plan`. `.cursor/hooks.json` and `.github/hooks/<name>.json`
   hold a guard when a hook entry names a command. `opencode.json` fails when `permission` or `permission.bash` is
   the plain word `allow`, and holds a guard when any rule says `deny`. `.gemini/settings.json` holds a guard with a
   nonempty tool list or a hook command. A recognized file without a guard fails, and the check fails when no listed
   file is a recognized guard file that holds one. Other files are reported as present with their content not
   checked. These shapes are the ones the wave 5 guard packages a04 and a13 write.
4. `queue`: `.baltor/night/queue.json` is a `night_queue/v1` queue; a status file, when present, must be
   `night_queue_status/v1` bound to that queue's SHA-256; at least one ticket is queued or in progress.
5. `test_command`: the declared argument list runs without a shell, from the workspace root, in its own process
   group, with its timeout. Only the last 64 KiB of output are kept in memory and saved; the saved file starts with
   the argument list, the exit status and the total output size. When the timeout passes, the whole process group
   is stopped, so programs the test started do not keep running into the night.

`probe` also prints `will_run`: the argument list, folder, timeout, expected exit status and the program it
resolves to. The command tells the model to show it to the person before running `check`, because a permission
prompt for the helper does not show the test command. The report records the same object under `test_command`
and the per-file guard results under `guard_files`. The model only runs two commands and reports.

## Authoring basis and sources

Original text and code written for this wave. No outside text or code was copied. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract.
- `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`: a local 7B model wrote its tool calls
  as plain text in all 37 of its steps; the nonce round trip is built to catch that before a night starts.
- `docs/guides/native-client-material-loading.md`: the OpenCode command folder.

The guard shapes follow the wave 5 packages `guard_shell_command_allowlist` (a04: Claude Code, Cursor and Copilot
hook files) and the a13 settings packages (Claude Code permissions, OpenCode `permission`, Gemini CLI tool lists).
The settings, queue and status formats are the contracts that `plan_night_queue` publishes.

## Inputs and outputs

Inputs: the settings file, the guard files, the queue and the optional status file. Outputs: one JSON object per
run (`night_preflight_probe/v1`, `night_preflight_report/v1` or `night_preflight_refused/v1`) and new files under
`.baltor/state/night-preflight/`: probe, used marker, report and test output tail. Exit 0 go, 1 no-go, 2 refused
input (an unusable root or state folder). Missing or unversioned settings are a no-go, not a crash.

## Effects

`reads_fs`; `writes_fs` (new state files only, each created exclusively; tests write only in temporary folders);
`spawns_process` (the helper starts the declared test command and, on a timeout, stops its process group; the model
starts the helper with `python3 -I -B`). The helper makes no network call and no model call and reads no secret.
The test command inherits the environment and whatever network the host allows; the host sandbox governs that.

## Closest existing items

- `measure_the_environment_before_relying_on_it` (starter, prose): measure capacity before planning. This package
  is an executable gate for one moment, the start of an unattended run, with a fixed report and a go rule.
- Wave 5: `detect_text_written_tool_calls` (a03) scans transcripts after the fact; this package proves a live
  round trip before the night and reads no transcript. The a04 and a13 packages write guard files; this package
  checks that such files are present and not permissive, not that the harness enforces them.

## Positive example

With the example settings, a Claude Code settings file with one deny rule, the example queue and a test program
that exits 0, `probe` then `check --nonce <printed value>` exits 0 with decision `go`, and the saved report has
the keys of `examples/report-go.json`, including the test command it ran.

## Known-wrong example

A model that never ran the probe calls `check --nonce 0123456789ab` and gets no-go with `structured_tool_calls`
failed. The critic's cases are tests: a guard file `{}`, a Claude Code settings file with `bypassPermissions` and
`Bash(*)`, one that allows `Bash` next to a deny rule, and one with only a narrow allow rule each give no-go under
`guards` (`test_known_wrong_empty_or_permissive_guard_files_are_no_go`); the report now names the test program
(`test_known_wrong_report_without_the_command_is_fixed`).

## Harness placement and verification state

No harness binary was run. Claude Code `.claude/commands/night-preflight.md` and Gemini CLI
`.gemini/commands/night-preflight.toml`: documented in the spec table. OpenCode
`.opencode/commands/night-preflight.md`: documented and observed in the repository guide (the spec table names
`.opencode/command/`). Copilot `.github/prompts/night-preflight.prompt.md` now sets `agent: agent`: the VS Code
prompt file documentation, read by the repairer on 2026-09-24, says a prompt runs in the current agent unless
`agent` is set, and this command is only its tool calls. Cursor `.cursor/commands/night-preflight.md`: the Cursor
page read the same day described skills, not a command folder. Both stay unverified. The command takes no
arguments. The script goes to `.baltor/night-preflight/`; the examples and tests are not placed. The host must
bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Customer requests

- "Before I go to bed, make sure the local model can actually use its tools."
- "Check that my tests run and the budget and guards are in place, then say go or no-go."
- "Tell me exactly which test command the check is going to run before it runs it."

## Limits

The round trip shows that whoever ran the command in this session made two tool calls and used the first result;
it does not prove the model will keep doing so for hours. The guard check reads configuration; it does not prove
that the harness loads or enforces it, and Gemini CLI and OpenCode key names can differ by version. The check
cannot tell which harness will run tonight, so a guard file for another harness can satisfy it. Stopping the
process group needs a POSIX system; elsewhere only the test process is stopped. Programs the test started in a
new session of their own are not stopped. Model availability and provider quota are not checked.

## Repair history

Critic round 2 found: a `guards` check that passed `{}` and a Claude Code file with `bypassPermissions` and
`Bash(*)`; a report that did not name the test command, folder or timeout; a permission prompt that shows only the
helper call; the whole test output held in memory and processes left running after a timeout; a queue check tied
to a shape a11 used to contradict; and a Copilot variant without `agent`. The repairer reproduced the cases at
digest `fffdf7f6` (`repairer-a06_step_ritual_commands/baseline/`) and made the changes above. The queue shape is
now settled: a11 reads the same `items` shape, and this package reads the status file that keeps statuses out of
the queue.

Mutation checks: eight guards removed one at a time (required guard content, the allow-all rule, stopping the
process group, the test command in the report, the probe file for a nonce, the test exit status, the output tail
limit, the queue binding of the status file) were each killed by a named test while the unchanged copy passed.
Native loading of the command is unobserved. Every run is listed in `PRECHECKS.txt`.
