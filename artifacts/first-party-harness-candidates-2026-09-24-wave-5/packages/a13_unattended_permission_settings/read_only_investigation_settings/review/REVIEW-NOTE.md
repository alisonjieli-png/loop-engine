# Review note: read_only_investigation_settings

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a13_unattended_permission_settings (family anthropic). Package version 0.1.0.

## Method

One policy, rendered for four harnesses: a step may read, list and search files and run only `git status`, `git diff`, `git log`, `git show`, `ls`, `pwd` and `wc`, plus the package checker. It may not create, edit or delete files, use network tools, redirect output with `>` or delegate to another agent, and nothing waits for an approval prompt. The companion `AGENTS.md` tells the model what is active, gives a first action (`git status`) and says what to do when something is refused.

The deterministic part lives in `scripts/check_read_only_investigation_settings.py`. It reads the placed settings files (or one document on standard input), models each harness's documented rule order, runs 19 probes (for example `rm -f src/app.py`, `git log > notes.txt`, `curl -s example.invalid`, a web fetch, a delegated task) and prints one JSON object with the decisions, the problems and the known limits. Exit 0 means the files hold the policy, 1 means they do not, 2 means the input was refused. A host can run it after placement, and the model can run it when an action is refused, to see the exact list of allowed commands.

## Authoring basis and sources

Every file is original text written for this package. Repository sources at `a1fc7432`: `catalogue_packages.py` (package format); `opencode_step_composition.py` (OpenCode evaluates the last matching rule, `ask` hangs an unattended step, `task` hands removed tools back to a subagent, a model with `bash` but no `edit` still changed files with `sed -i`); `harness_responses_recipes.py` (the Codex recipe writes `approval_policy = "never"`, `sandbox_mode = "read-only"`, `web_search = "disabled"`); `harness_additional_recipes.py` (Gemini CLI `tools.core`); `harness_opencode_recipe.py` (OpenCode deny-all `permission`); `NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` (settings locations, Codex project config needs a trusted project); `HARNESS-FORKS-2026-09-22.md` (Claude `--bare` with `--settings`, Codex sandbox flags).

Installed packages were read, never run: the Claude Code 2.1.281 binary's embedded settings schema and settings reference (modes `acceptEdits`, `auto`, `bypassPermissions`, `default`, `dontAsk`, `plan`; `Bash(git *)` also matches bare `git`; `Edit(path)` rules cover every file-writing tool while a bare name matches only its own tool; `dontAsk` and headless runs deny instead of asking); the Codex 0.155.1 binary strings (`sandbox_workspace_write`, `network_access`, `web_search` values `live`, `indexed`, `cached`, `disabled`); the OpenCode binary (defaults `"*": "allow"`, `external_directory` ask, `read` of `*.env` ask; `*` becomes `.*` and a final ` *` makes arguments optional; each simple command's text is the shell pattern); the Gemini CLI 0.59.0 bundle schema and bundled docs (`tools.core` is an allowlist of all built-in tools, shell prefixes match on a word boundary, chained commands are split, redirection asks, `ask_user` is a refusal in headless mode, workspace policy files are disabled).

## Inputs and outputs

Inputs: the four settings files at their placed paths, or one document with `--harness`, `--file` or `--stdin`. Output: one JSON object with `passed`, per-file `problems`, `known_limits`, `decisions`, `allowed_commands` and `refused`. Inputs over 1 MiB, non-UTF-8 text, duplicate JSON keys, invalid TOML and paths that leave the root are refused with exit 2.

## Effects

The settings grant reading and the listed commands and refuse everything else. The checker reads files only (`reads_fs`). The tests start the checker with `sys.executable` (`spawns_process`) and write placed copies of the variants inside `tempfile.TemporaryDirectory()` folders (`writes_fs`); nothing in the step itself writes. No network use, no secret reads, no model calls.

## Closest existing items

- Starter candidate `state_the_permissions_and_limits_of_an_assignment`: prose for a person writing a brief. This package is the enforcement itself, as native settings files plus a checker; it does not tell a writer what to say.
- Wave 5 `guard_shell_command_allowlist` (a04 hook): a script that inspects each shell command at run time. This package uses each harness's own permission settings and needs no hook process. They can be combined.
- The gap matrix lists no settings or permission fragment anywhere in the library.

## Positive example

With the Claude Code variant, `git log --oneline -n 5` is allowed by `Bash(git log *)`, while `rm -f src/app.py` finds no allow rule and `dontAsk` refuses it without a prompt. The checker exits 0 for all four variants; Codex reports two known limits and Gemini CLI one.

## Known-wrong example

Remove `Bash(*>*)` from the Claude Code deny list and `git log > notes.txt` is allowed through `Bash(git log *)`, so the step can write a file. Move OpenCode's `"*": "deny"` from the first key to the last and every read is refused, because OpenCode keeps the last matching rule. Both mutations are in the tests, with 17 others, and each makes the checker exit 1.

## Harness placement and verification state

- Claude Code: `.claude/settings.json` by `merge_json_object`; the companion is composed into `AGENTS.md`, which Claude Code reads through the step's `CLAUDE.md` import `@AGENTS.md`. With `claude -p --bare` the host must pass the file with `--settings`. Unverified: whether `dontAsk` also refuses the commands Claude Code treats as read-only by itself, whether `Bash(*>*)` sees a redirection that Claude Code parses separately, and whether the subagent tool is named `Task` or `Agent` (both are denied). Also unverified: that `Read(/**)` starts at the project root for project settings in a run. The installed schema names that root for sandbox paths; its wording for permission rules was not found in the binary.
- Codex: `.codex/config.toml` by `merge_toml_table`. Unverified for project scope; it loads only in a trusted project, otherwise the host passes the same keys in an isolated `CODEX_HOME` or as `--sandbox read-only` and never-ask flags. Known limit: Codex runs any command inside its read-only sandbox instead of refusing it by name.
- OpenCode: `opencode.json` by `merge_json_object`. A merge must keep `"*": "deny"` before the other keys; the checker detects a wrong order. Reads of `.env` files are refused, which keeps OpenCode's own default protection as a refusal instead of a prompt.
- Gemini CLI: `.gemini/settings.json` by `merge_json_object`; the companion goes into `GEMINI.md`. Workspace settings apply only in a trusted folder or with `--skip-trust`. Known limit: prefix matching accepts appended options such as `git log --output=FILE`.
- The checker command names `python3 -I -B`; the host must bind a trusted interpreter, because an earlier independent review showed that a `python3` found first on `PATH` can be replaced.
- Native loading of these files was not observed; the integrator's discovery probes run later.

## Customer requests

- "Let the agent look around my repository overnight but make sure it cannot change anything."
- "Give me Claude Code and OpenCode settings that only allow git status, git diff and git log."
- "How do I stop Codex asking for approval while keeping it read-only?"

## Limits

An allowed command is not safe with every option: the settings stop unlisted commands, not every option of a listed one. This policy adds no rule for reading files outside the workspace, and no probe covers such a read. Codex's read-only sandbox allows it, so a host that must hide files outside the workspace needs its own confinement. The checker models documented rules of one installed version per harness; it proves what the files say, not that a harness loaded them. A settings file is not an operating system sandbox; an unattended host should still confine the process.

Pre-check history: the package tests passed under Python 3.14 and 3.10 before the first `check_package.py` run. Every report is kept in `review/precheck-*.json`. The run at 20:34 UTC was refused by the `layout` check because of an empty file, `review/last-check-output.txt`, left while saving command output; the file was removed and the run at 20:35 UTC passed. The first pass ended with `precheck-20260923T205323400289Z.json`. The command output of the current pass is in `PRECHECKS.txt` beside the package folder (`packages/read_only_investigation_settings/PRECHECKS.txt`), outside the package because the checker refuses extra top-level entries.

## Revision history

1. First pass, September 23, 2026, ending with package digest `7f7597fe38b99b82c508b3f303fda94c602cff7a7e6861687cf9354235a6d154`. Its package folder is kept unchanged as `earlier-attempt-20260923T2053Z.tar.gz` beside `PRECHECKS.txt`.
2. Second pass, the same day, by the same generator, after a fresh read of the installed harness packages. The OpenCode binary sets its `doom_loop` permission, the prompt before a repeated identical tool call, to `ask` by default, and an unanswered prompt stalls an unattended run. The wave's vocabulary rule refuses that key name in payload files, so the checker does not name it. Instead, the OpenCode `permission` object of a base policy must now start with `"*": "deny"`, which overrides every default that asks. The shipped variant already did. A new known-wrong case replaces the catch-all with one deny per tool: the revised checker refuses it, and the first-pass checker, run on the same document from the saved folder, passed it. The variants and the companion did not change. This note now also records the `Read(/**)` root as unverified and states the reading limit precisely.
