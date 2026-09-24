# Review note: Test run summarizer

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a05_focused_subagents, model family anthropic, repaired on September 24, 2026 by the a05 repairer of the same family after the a05 critic's review. This note is never delivered to a customer.

## Method

A subagent definition plus one tested script. The helper takes one declared test command and runs it through `scripts/summarize_test_run.py`, which starts the command without a shell, keeps at most the first 4 MiB and the last 4 MiB of its output, and prints one JSON object: the exact command, the working folder, the exit status, whether it timed out, the seconds taken, the runner, the counts, the first failure with an excerpt of at most 20 lines, a short tail only when no failure was found, the output size, a result and a reason. The helper returns that object unchanged, so the raw log never reaches the main step. Counting and failure extraction are code, not model judgment. The model's job is to copy the declared command exactly, run one command with a matching shell time limit, and check that the reported command words match.

The script parses pytest, unittest, go test, cargo test, jest and vitest summaries. The result values are `passed`, `failed`, `no_tests`, `unconfirmed`, `timeout`, `interrupted`, `not_started` and `refused`. A run is `passed` only when the exit status is 0, a known runner summary was found, no failure or error was reported, and at least one test was not skipped. Output that no parser recognizes, with exit status 0, is `unconfirmed`, because the script cannot tell that tests ran. A pytest collection-only summary and a run where every test was skipped are `no_tests`. For pytest, the first failure is the first report block of the ERRORS or FAILURES sections in output order, and its name and excerpt come from that same block; the name is completed from the matching short summary line.

## Authoring basis and sources

Original text and code written for this wave. The runner output formats in the tests are synthetic samples written from general knowledge of those tools. Sources at revision a1fc7432:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the file contract this package follows. It lists `executable_tool` among the roles a harness may run, and a package holding one must declare `spawns_process`.
- `docs/guides/native-client-material-loading.md`: records the OpenCode project agent folder `.opencode/agents/<name>.md` as documented and observed with version 1.18.31.
- `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`: measured 45 to 446 percent more prompt tokens per step when item material was placed in a cheap model's step, and a local 7B model that wrote its tool calls as plain text in all 37 steps. It motivates a fixed, short reply produced by code. This package's own effect is unmeasured.

Harness facts added in the repair were read from installed program text or public documentation, and none was run: the Claude Code 2.1.281 Bash tool defaults to 120000 ms and allows at most 600000 ms (`BASH_DEFAULT_TIMEOUT_MS` and `BASH_MAX_TIMEOUT_MS` change them), and on a timeout it sends SIGTERM to the command's process group and to every descendant process, then SIGKILL 1500 ms later; the OpenCode 1.18.32 bash tool defaults to 120000 ms, takes a `timeout` in milliseconds with no upper limit found, starts the command in its own process group and on a timeout stops it with a forced stop 3 seconds later; GitHub's custom agents configuration reference (docs.github.com/en/copilot/reference/custom-agents-configuration, read September 24, 2026) documents `.github/agents/NAME.agent.md`, the `execute` alias for shell tools, the `read` alias and that unknown tool names are ignored.

## Inputs and outputs

Input: the declared test command, or a file and label where it is declared, plus an optional folder and time limit. Output: one JSON object matching `contracts/reply.schema.json`: the full summary, or the short refusal `{"record_type": "test_run_summary/v1", "result": "refused", "reason": "..."}`. Script exit status: 0 passed, 1 any other outcome of an attempted run, 2 refused input.

## Effects

`spawns_process`: the helper runs the script, which starts the declared command. `reads_fs`: the helper may read the file that declares the command, and the test command reads the repository. The script writes no file. The declared test command may write its own caches, which is the caller's authority.

Before anything starts, the script refuses a short list of commands that are plainly not a test run: shell operators written as separate words, shells, wrapper programs such as env, timeout, nice, nohup and xargs, privilege tools, file and deletion tools such as rm, unlink, find and truncate, git and network clients, package installers such as pip, pipx and npx, `python -m pip`, bare `yarn`, and the install, remove, publish and fetch words of common package tools (for example `npm ci`, `npm i`, `pnpm i` and `uv sync`). This guard is not a sandbox. A test runner, a make target or a `run` subcommand such as `uv run` or `poetry run` can still start any program, install packages, write files or use the network. In OpenCode the permission rule allows any words after the script prefix, so on that harness the guard is the only check on what the script starts. Real limits must come from the host: a sandbox, a settings fragment or a permission rule.

On its own time limit, or on SIGTERM, SIGINT or SIGHUP, the script stops the process group it started with SIGKILL, waits for it, and still prints one JSON object (`timeout` or `interrupted`). The default `--timeout` is 540 seconds so that it ends inside a shell tool limit of 600 seconds, and the body tells the helper to set the shell tool's own limit 60 seconds above `--timeout`.

The Claude Code variant grants Bash and Read, and the Copilot variant lists `execute` and `read`. Neither Bash nor `execute` is limited to this one script there; a settings fragment or a hook must narrow it if that matters. The OpenCode variant denies every shell command except the script prefix. The host must bind a trusted `python3`, because an interpreter found first on the search path can be replaced. The tests write no file. They start the script and small Python commands, send SIGTERM to one script process group that they started, and read `/proc` on Linux to find and check the test process; every command a refusal test names is harmless even if the refusal failed.

## Closest existing items

- No served or starter item runs tests and returns a fixed summary.
- Copilot CLI ships a built-in Task agent that runs commands such as tests and builds; GitHub's CLI guide (docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli, read September 24, 2026) says it returns a short summary when they succeed and the whole output when they fail. This helper differs in behavior: its reply is one fixed JSON object with a schema, the counts and exit status come from code, only the first failure is returned even when the run fails, a run with no known summary is `unconfirmed` instead of a pass, and it refuses commands that are plainly not a test run. It also works in Claude Code 2.1.281 and OpenCode 1.18.32, whose built-in agents (Explore, Plan, general-purpose; build, plan, general, explore) include no test runner.
- Pilot `repair_one_failing_test` is a step brief that repairs an existing failing test. It runs a test command as part of a repair and returns prose.
- Wave 5 `extract_test_failures` (a03) is a skill that parses a saved log into a list of all failing tests. This helper runs the command itself, bounds the output, reports counts and only the first failure, and keeps the log out of the main step. Neither restates the other's code.

## Positive example

A real unittest suite with two tests, run through the script, where the check `round(2.675, 2) == 2.68` fails, gives `result: failed`, `runner: unittest`, counts 1 passed and 1 failed, and an excerpt ending with `AssertionError: 2.67 != 2.68`. This case runs for real in the tests, started as `python3 -c` with the suite's code.

## Known-wrong example

A pytest log ends with `3 passed, 1 error in 0.20s`. A model reading the log sees "3 passed" and reports the run as green. The script reports `result: failed`, `errors: 1` and the setup error as the first failure. Further known-wrong cases, each a test: a runner prints failures but exits with status 0 (still `failed`); a log with a setup error and a failure, where pytest prints the ERRORS section first but lists FAILED first in its short summary (name and excerpt must name the same test); output that no parser knows, with exit status 0 (`unconfirmed`, not `passed`); a collection-only summary (`no_tests`); `--timeout` written with a superscript digit (a JSON refusal, not a traceback); and SIGTERM sent to the script's process group, as a harness does at its own time limit (a JSON `interrupted` reply and no test process left running).

## Harness placement and verification state

- Claude Code: variant to `.claude/agents/test-run-summarizer.md`. Documented folder; the keys `name`, `description`, `tools`, `model`, `maxTurns` and `omitClaudeMd` were checked against the agent file parser in the installed Claude Code 2.1.281 program text, read and not run. That program text's change list adds `omitClaudeMd` in 2.1.271: the subagent then runs without the user, project and local CLAUDE.md files, and managed policy files still load. Discovery of this file was not observed.
- OpenCode: variant to `.opencode/agents/test-run-summarizer.md`, basis as for the other a05 packages: documented and observed folder per the guide, keys and last-match permission rules read from the installed OpenCode program text (it embeds version 1.18.32). The pattern `python3 -I -B .baltor/test-run-summarizer/scripts/summarize_test_run.py *` also matches the bare prefix, because a trailing ` *` is optional in that matcher. Unverified.
- Copilot: variant to `.github/agents/test-run-summarizer.agent.md`. The path and the `execute` and `read` aliases are documented by GitHub as cited above. Discovery of this file and any time limit of the Copilot shell tool were not observed; no Copilot surface was run. Unverified.
- Script, test, schema and `LICENSE` go under `.baltor/test-run-summarizer/`. The script path in the body assumes the harness runs commands from the workspace root.

## Customer requests

- "Run the unit tests and just tell me what failed first."
- "I don't want the whole pytest log in my context, give me the counts."
- "Run the test command from the ticket and report the exit code."

## Limits

The middle of a log longer than 8 MiB is not parsed; `output_bytes` shows the full size. Go counts are null without `-v`, because go test prints no pass lines then. Only the first failure is reported. A runner not in the list gives `unconfirmed` or `failed` with null counts and a 15 line tail. The stop-signal path needs the grace time between SIGTERM and SIGKILL (1.5 seconds in Claude Code 2.1.281 and 3 seconds in OpenCode 1.18.32, as read); a harness that sends SIGKILL at once gets no JSON, and the test process group, which runs in its own session, may keep running unless the harness also stops descendant processes, as Claude Code does. One property has no test: that memory stays bounded for a very long log. The tests check only that the end of a log above 8 MiB is still parsed.

History of checks. The first test run of the first draft failed before it passed: the script refused any argument containing a backquote, which wrongly refused a plain argument with backquotes inside it; it now refuses only shell operators written as separate words. A later review of the tests made every refusal test use a command that stays harmless if the refusal breaks. The first draft's mutation log is kept as `review/mutation-check-20260923.txt`.

The September 24 repair answered the a05 critic. Before the script changed, the new known-wrong tests were run against the unchanged script: 10 failed and 1 errored out of 34 (the error was a slicing mistake in one new test, fixed before the repair). After the repair, 35 of 35 tests passed under Python 3.14 and 3.10. In a mutation check run in Bubblewrap without network, 22 single-behavior mutants of the script, 15 for the repaired behavior and 7 for behavior the first draft already had (5 of them repeat first-draft mutants), each made the suite fail; the first run left one survivor (a folder link that leaves the root), which a new test now covers. The log is `review/mutation-check-20260924.txt`. While repairing, one new test briefly checked an environment variable after `unittest.main`, where it never ran; the test was rewritten so that the check is a unittest case and a run without the variable fails.
