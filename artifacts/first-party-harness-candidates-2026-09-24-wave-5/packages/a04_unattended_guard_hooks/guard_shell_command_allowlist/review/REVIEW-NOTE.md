# Review note: guard_shell_command_allowlist

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a04_unattended_guard_hooks (model family anthropic), September 23, 2026. Repaired on September 24, 2026 by the wave 5 repairer of the same assignment and model family, after the findings of an independent critic. This note is never delivered to a customer harness.

## Method

One method: before each shell command, split the command line into its simple commands and refuse the tool call when any part does not start with an entry of the step allowlist.

The hook also refuses shell syntax it does not check: redirection to a file, command substitution, backticks, process substitution, background jobs, subshells, here-documents and lines that continue over several lines. It refuses every word that bash would expand into text the guard cannot see: `$NAME`, `${...}` and `$[...]` (also inside double quotes), `$'...'`, `$"..."` and unquoted braces. For an entry with refused arguments, unquoted `*`, `?` and `[` are refused after the start, because a file name can expand into a refused option.

A refused option also matches its `=value` form and an abbreviated long option (`--outp` for `--output`). For a two-character option such as `-o`, any single-dash word that holds its letter is refused, which covers `-ofile`, `-o/tmp/x`, `-o../x` and the group `-uo`. Programs that run another program (`env`, `xargs`, `sudo`, `bash`, `timeout` and others) and shell builtins that change how later commands run (`export`, `alias`, `hash`, `set` and others) are refused even when a policy lists them. The policy validator refuses such entries, start tokens that hold shell characters, and variable names that choose a program or its configuration, such as `PATH`, `HOME`, `LD_PRELOAD`, `GIT_DIR` and `RIPGREP_CONFIG_PATH`.

Covered calls: Claude Code `Bash` and `Monitor` (a Monitor command is checked like a Bash line, and a Monitor call that opens a WebSocket is refused) and `PowerShell` (always refused, because the parser reads POSIX shell only); Cursor `beforeShellExecution`, or `preToolUse` for the `Shell` tool; Copilot `bash` (`powershell` is refused).

Answers: Claude Code and Copilot get the empty object `{}` for an allowed call. That leaves the decision to the harness's own permission settings, so there the guard can only narrow what the harness would do. Cursor's hook page requires `permission` in every answer and blocks the action on an answer that does not match its schema, so in Cursor an allowed call gets `{"permission": "allow"}`.

The package places a conservative default allowlist at `.baltor/step/guard-shell-command-allowlist.json`: `pwd`, `ls`, `git status`, `git diff`, `git log`, `rg` and `find`, with the options that write files or start programs refused (for `rg` these are `--pre`, `--search-zip`, `-z` and `--hostname-bin`). Installed as delivered, the hook therefore allows inspection commands only. The host replaces the file with the step's own list before launch and can validate it with `--check-policy`.

## Authoring basis and sources

Original code and text written for this package. The shell reading rules are ordinary POSIX shell knowledge, restated in code; no outside code was copied. Repository sources at the pinned revision: `catalogue_packages.py` (package format), the starter item `state_the_permissions_and_limits_of_an_assignment` (list the commands a worker may run), and `harness_confinement.py` (declared, cleared environment).

Claude Code event and answer fields follow the hook reference, https://code.claude.com/docs/en/hooks. The tools reference, https://code.claude.com/docs/en/tools-reference, read on September 24, 2026, lists the `Monitor` input fields `command`, `timeout_ms` and `ws` and says to match `Bash|PowerShell` in hooks that inspect shell commands. Cursor field names were read from a snapshot of Cursor's hook page inside the locally cloned outside project madebywild/agent-harness (`docs/cursor-hooks.md`, revision 2ecf44f, lines 504 to 535 and 689 to 721) and checked against Cursor's hook page on September 24, 2026, for names only. Copilot names match GitHub's hooks configuration reference as read on September 24, 2026. The `rg --hostname-bin` option, which starts a program, was found in the help text of the installed ripgrep 15.1.0.

## Inputs and outputs

Input: one hook event as JSON on standard input, at most 1 MiB, plus the policy file `.baltor/step/guard-shell-command-allowlist.json` (record `shell_command_allowlist/v1`, at most 256 KiB). Arguments: `--harness`, optional `--root` and `--policy`, and `--check-policy` for the host to validate a policy before launch (exit 0 valid, 1 refused). Output: exactly one JSON object on standard output, exit 0: the allowed answer of the harness or its refusal. A missing `--harness` exits 2, which Claude Code and Cursor treat as blocking.

## Effects

Reads standard input and one policy file. Writes nothing to disk, makes no network call, starts no program and reads no transcript. Declared effects: `reads_fs`, `spawns_process` (the harness starts the hook; the tests start it too). The tests write nothing. The host must bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Closest existing items

The Codex candidate `focused_brief_plugin` holds the only first-party hook, a startup context hook that never refuses anything. The starter item `state_the_permissions_and_limits_of_an_assignment` tells a writer to list allowed commands; it is prose a model may ignore, while this hook enforces the list outside the model. The wave 5 settings fragment `test_commands_only_settings` expresses one fixed list of test commands as native harness permission rules, with no hook process; this hook reads a per-step list and refuses shell syntax, expansions, options and launchers by its own tested rules. The staged outside titles "Safety Guard: Prevent Destructive Operations" and "GateGuard" are text skills; their bodies were not read.

## Positive example

`python3 -m pytest -q tests 2>&1` with the example policy gets `{}`. `git status && git diff --stat` also passes, because both parts are listed. With the delivered default, `rg TODO src` and `find . -name '*.py'` pass.

## Known-wrong example

`git status && rm -rf build` must be refused: a guard that only checks the first program would pass it. `find . -name '*.tmp' -delete` must be refused although `find` is listed. The critic showed that the first version passed `find . -name '*.tmp' {-delete,}` and `find . -name '*.tmp' ${UNSET_NAME:--delete}`, which bash turns into `-delete`, and let `rm -rf build` through the Monitor tool and `Remove-Item` through PowerShell. All of these are refused now, and each has a test.

## Harness placement and verification state

Claude Code: `.claude/settings.json` hook `PreToolUse` with matcher `Bash|PowerShell|Monitor`, merged; documented in the hook and tools references, not observed on this machine. Cursor: `.cursor/hooks.json` event `beforeShellExecution` with `failClosed: true`; unverified, including whether an allow answer also skips Cursor's own approval prompt. Copilot: `.github/hooks/guard-shell-command-allowlist.json` event `preToolUse`, input `toolName` and `toolArgs`, answer `permissionDecision`; documented, unverified. The default policy goes to `.baltor/step/guard-shell-command-allowlist.json` for all three. The companion `AGENTS.md` is composed into the step's `AGENTS.md`; Claude Code reads it through the step's `CLAUDE.md` import line. No harness binary was run. The samples use the checker's sandbox path `/work`.

## Customer requests

- "Only let the overnight agent run pytest and git read commands."
- "Stop my coding agent from chaining a delete after an allowed command."
- "I want a list of commands the agent may run, and a refusal it can understand."

## Limits

The list limits programs and options, not paths. A listed reader such as `rg`, `find`, `ls` or `git diff --no-index` reads any path its arguments name, including private files in the home folder; run the harness in an operating system sandbox when that matters. A listed test runner or interpreter runs whatever code the workspace holds. The guard checks the words of a command, not what the shell resolves them to: a shell function or alias with a listed name, set up by the harness or a shell profile, runs instead of the program. Programs such as git also run commands named in their own configuration files; pair this hook with the workspace write guard, which keeps the agent out of `.git` and the harness folders. Commands that other harness features run, such as hook commands and shell lines inside skill or command files, are not seen. Claude Code treats a hook timeout as a non-blocking error, so the hook limits itself to 8 seconds.

Check history: every checker run is recorded in `review/PRECHECKS.txt`. The critic's probe is `critic-a04_unattended_guard_hooks/probe_shell_guard.py`. The repair's probes, mutant runs and the failing run of the new tests against the earlier hook are kept in `repairer-a04_unattended_guard_hooks/` of the wave folder. One earlier mutant (the old attached-value rule) survived because the group rule already covered every case it covered; the two rules were merged into one.
