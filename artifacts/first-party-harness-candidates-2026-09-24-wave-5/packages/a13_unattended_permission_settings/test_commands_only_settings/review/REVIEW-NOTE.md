# Review note: test_commands_only_settings

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a13_unattended_permission_settings (family anthropic). Package version 0.1.0.

## Method

One policy for a verifying step: the harness may read, list and search files and run only `python3 -m unittest`, `python3 -m pytest`, `python3 -m pyflakes`, `ruff format --check` and `python3 -m black --check`, plus the package checker. Every other command, every file edit, output redirection, web access and delegation are refused, and nothing waits for an approval prompt. The format commands are declared in their check forms, so a verifying step cannot rewrite the code it is judging; a step that is allowed to fix code should use the workspace write package instead.

`scripts/check_test_commands_only_settings.py` runs 22 probes: the five commands in realistic forms, the rewriting forms (`ruff format src`, `python3 -m black src`, `ruff check --fix src`), `git status`, an unlisted script, `pip install`, a chained `rm`, a redirected report, and file edits of source and tests. A Codex settings file found under the root is reported as not covered, with exit 1.

## Authoring basis and sources

Original text and code. Repository sources at `a1fc7432`: `catalogue_packages.py`; `opencode_step_composition.py`, which records that a model changed a test so a gate would pass and that denying edits to tests turned this into an honest blocked report; `harness_additional_recipes.py` (Gemini CLI `tools.core`); `harness_responses_recipes.py` (Codex keys, used to state why Codex is not placed); `NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md`. Installed packages read without running them: the Claude Code 2.1.281 settings schema and reference (rule forms `Bash(cmd *)`, `dontAsk`), the OpenCode binary (the text of each simple command is matched; the last matching rule wins), and the Gemini CLI 0.59.0 bundled docs (`tools.core` is an allowlist of all built-in tools; shell prefixes match on a word boundary; chained commands are split; redirection asks and headless runs refuse it).

## Inputs and outputs

Inputs: placed settings files or one document with `--harness` and `--file` or `--stdin`. Output: one JSON object with each probe's decision, `problems`, `allowed_commands` and `refused`; exit 0, 1 or 2.

## Effects

The step reads files and starts the declared commands (`reads_fs`, `spawns_process`); test code runs with whatever access the host gives the process. The checker reads files only. The tests start the checker with `sys.executable` and write placed copies inside `tempfile.TemporaryDirectory()` folders (`writes_fs`). No network use, no secret reads, no model calls.

## Closest existing items

- None found by the scout. Wave 5 `guard_shell_command_allowlist` (a04 hook) refuses commands at run time with a script and a declared list; this package uses native permission settings with no hook process and also refuses edits.
- Wave 5 `honest_test_changes` (a08 rule) tells a model not to weaken tests; this package makes edits impossible during a verifying step.
- Wave 5 `workspace_write_no_network_settings` allows edits and tests; this package allows tests only.

## Positive example

With the OpenCode variant, `python3 -m pytest -q tests/test_app.py` matches `python3 -m pytest *` and is allowed, `ruff format --check src` is allowed, and `ruff format src` matches only the leading `"*": "deny"` and is refused. The checker exits 0 for the three placed variants with no known limits.

## Known-wrong example

Add `run_shell_command(ruff format)` to the Gemini CLI `tools.core` list and `ruff format src` is allowed, because prefix matching accepts any `ruff format` command; the checker reports `apply_ruff_format` and exits 1. This and 13 other known-wrong variants are in the tests.

## Harness placement and verification state

- Claude Code: `.claude/settings.json` by `merge_json_object`, companion into `AGENTS.md` through the step's `CLAUDE.md` import. Unverified: whether `dontAsk` also refuses the commands Claude Code allows by itself as read-only (for example `git status`); the checker models the rules only. Also unverified: that `Read(/**)` starts at the project root for project settings in a run; the installed schema names that root for sandbox paths, and its wording for permission rules was not found in the binary.
- Codex: not placed. Its project settings cannot refuse a command by name.
- OpenCode: `opencode.json` by `merge_json_object`, `"*": "deny"` first.
- Gemini CLI: `.gemini/settings.json`, companion into `GEMINI.md`, trusted folder or `--skip-trust`.
- The checker command names `python3 -I -B`; the host must bind a trusted interpreter. Native loading was not observed.

## Customer requests

- "The verify step should only be able to run pytest and the formatter check, nothing else."
- "Stop the reviewer agent from quietly fixing the code it is supposed to check."
- "Give me OpenCode and Gemini settings for a lint-only step."

## Limits

A test run executes project code, which can read, write or use the network as far as the host process allows; these settings do not confine it. An allowed command can still take options such as an output file path. Claude Code's built-in allowance for read-only commands is not modeled. The declared commands are a Python default; another project needs a new rendering and review.

Pre-check history: the package tests passed under Python 3.14 and 3.10 before the first `check_package.py` run. Every report is kept in `review/precheck-*.json`; both first-pass runs, `precheck-20260923T204043971437Z.json` and `precheck-20260923T205345228116Z.json`, passed. The command output of the current pass is in `PRECHECKS.txt` beside the package folder (`packages/test_commands_only_settings/PRECHECKS.txt`), outside the package because the checker refuses extra top-level entries.

## Revision history

1. First pass, September 23, 2026, ending with package digest `64135f1f1c9bbb196264c747e2607b1ccc99b4b76b56acecc55a479e3a4f8d25`. Its package folder is kept unchanged as `earlier-attempt-20260923T2053Z.tar.gz` beside `PRECHECKS.txt`.
2. Second pass, the same day, by the same generator, after a fresh read of the installed harness packages. The OpenCode binary sets its `doom_loop` permission, the prompt before a repeated identical tool call, to `ask` by default, and an unanswered prompt stalls an unattended run. The wave's vocabulary rule refuses that key name in payload files, so the checker does not name it. Instead, the OpenCode `permission` object of a base policy must now start with `"*": "deny"`, which overrides every default that asks. The shipped variant already did. A new known-wrong case replaces the catch-all with one deny per tool: the revised checker refuses it, and the first-pass checker, run on the same document from the saved folder, passed it. The variants and the companion did not change. This note now also records the `Read(/**)` root as unverified.
