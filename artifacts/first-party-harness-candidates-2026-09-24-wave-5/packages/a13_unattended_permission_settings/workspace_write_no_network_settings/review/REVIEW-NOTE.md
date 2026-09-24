# Review note: workspace_write_no_network_settings

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a13_unattended_permission_settings (family anthropic). Package version 0.1.0.

## Method

One policy for an unattended fix step, rendered for four harnesses: the step may create and edit files inside the workspace and run `python3 -m pytest`, `python3 -m unittest`, `git status` and `git diff`. It may not change `.git`, `.claude`, `.codex`, `.gemini`, `.opencode`, `.baltor` or `opencode.json`, touch files outside the workspace, redirect output, reach the network, install packages, push, or delegate to another agent. Nothing waits for an approval prompt, so an overnight run is refused instead of stalled. Protecting the harness settings matters because a step that could rewrite them could widen its own permissions for the next step.

`scripts/check_workspace_write_no_network_settings.py` models each harness's rule order and runs 26 probes, including edits of each protected path, `git diff > .claude/settings.json`, `python3 -m pip install`, `git push`, a network connection made by test code and a settings file written by test code. It prints one JSON object and exits 0, 1 or 2 as in the other packages of this set.

## Authoring basis and sources

Original text and code. Repository sources at `a1fc7432`: `catalogue_packages.py` (format); `opencode_step_composition.py` (last matching rule wins; `ask` hangs unattended steps; a model changed a test to make a gate pass, which is why edits and commands are scoped); `harness_responses_recipes.py` (Codex never-ask keys); `harness_additional_recipes.py` (Gemini CLI `tools.core`); `harness_confinement.py` (the host's cleared, confined process environment, which this package relies on where a harness has no sandbox); `NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` and `HARNESS-FORKS-2026-09-22.md` (settings locations, trust, flags).

Installed packages read without running them: the Claude Code 2.1.281 settings schema (`sandbox.enabled`, `failIfUnavailable` exits at startup when the sandbox cannot start, `allowUnsandboxedCommands: false` ignores the escape parameter, `autoAllowBashIfSandboxed` defaults to true and would allow every sandboxed command, `sandbox.filesystem.denyWrite` is merged with `Edit(...)` deny rules, and `network.strictAllowlist` is ignored in project settings, so an empty `allowedDomains` relies on refusal in `dontAsk` and headless runs); Codex 0.155.1 strings (`[sandbox_workspace_write] network_access`, `writable_roots`, and an embedded note that never asking does not enable the network); the OpenCode binary (edit patterns are paths relative to the worktree; defaults ask for folders outside it); the Gemini CLI 0.59.0 schema and bundled docs.

## Inputs and outputs

Inputs: placed settings files, or one document on `--file` or `--stdin` with `--harness`. Output: one JSON object with the decision for each probe, `problems`, `known_limits`, `allowed_commands`, `writable_paths` and `refused`. Oversized, non-UTF-8, duplicate-key or escaping inputs are refused with exit 2.

## Effects

The settings grant workspace edits and the listed commands. The step therefore writes files (`writes_fs`) and starts test processes (`spawns_process`). The checker only reads (`reads_fs`). The tests start the checker with `sys.executable` and write placed copies inside `tempfile.TemporaryDirectory()` folders. No network use, no secret reads, no model calls.

## Closest existing items

- None found by the scout for this method. The nearest is the starter candidate `state_the_permissions_and_limits_of_an_assignment`, which is prose for a brief writer; this package is enforceable native settings plus a checker.
- Wave 5 `guard_workspace_file_writes` (a04 hook) refuses writes outside the workspace or on protected paths at run time with a script; this package does the same with each harness's own permission settings and adds the network rule. They can be combined.
- Wave 5 `read_only_investigation_settings` is the no-write sibling; this package allows edits and test runs.

## Positive example

With the Claude Code variant, `Edit(/**)` allows `src/app.py`, `Edit(/.claude/**)` refuses `.claude/settings.json` because a deny rule wins, and `python3 -m pytest -q` runs inside a sandbox with no allowed network domains. The checker exits 0 for all four variants and lists the known limits of Codex, OpenCode and Gemini CLI.

## Known-wrong example

Set `sandbox.autoAllowBashIfSandboxed` to true in the Claude Code variant and `python3 scripts/deploy.py` becomes allowed, because every sandboxed command is then allowed without a rule. Set `network_access = true` in the Codex variant and `curl` is allowed. Both are in the 21 known-wrong cases of the tests and make the checker exit 1.

## Harness placement and verification state

- Claude Code: `.claude/settings.json` by `merge_json_object`; companion into `AGENTS.md`, read through the step's `CLAUDE.md` import. Unverified: that project settings may set `failIfUnavailable`, that the sandbox starts inside the host's own bubblewrap confinement, and that `dontAsk` refuses a host outside `allowedDomains` without a prompt. With `failIfUnavailable` a missing sandbox stops the harness at startup, by design. Also unverified: that `Read(/**)`, `Edit(/**)` and the protected `Edit(/...)` rules start at the project root for project settings in a run; the installed schema names that root for sandbox paths, and its wording for permission rules was not found in the binary. `sandbox.network.strictAllowlist: true` would refuse hosts outside `allowedDomains` without any prompt, but the 2.1.281 schema says it is honored only from user, managed or command-line `--settings` settings and ignored in `.claude/settings.json`. A host that passes this file with `--settings` may add it.
- Codex: `.codex/config.toml` by `merge_toml_table`; unverified for project scope and trusted projects only. Known limits: the whole workspace is writable, so protected folders and a test that rewrites a settings file are not refused; unlisted commands run inside the sandbox.
- OpenCode: `opencode.json` by `merge_json_object`, with `"*": "deny"` kept first. Known limit: no process sandbox, so code run by a test command can use the network or write a protected file unless the host confines the harness.
- Gemini CLI: `.gemini/settings.json` by `merge_json_object`, companion into `GEMINI.md`, trusted folder or `--skip-trust`. Known limits: `write_file` and `replace` cannot be limited to folders in `settings.json`, and test code is not confined.
- The checker command names `python3 -I -B`; the host must bind a trusted interpreter.

## Customer requests

- "Let my local model fix tickets overnight, but it must never reach the internet or wait for me to click approve."
- "Allow edits and pytest, block pip install and git push."
- "Stop the agent from editing its own .claude settings."

## Limits

Running tests runs code the step may edit, so network and file confinement of that code needs an operating system sandbox: the Claude Code sandbox, the Codex sandbox or the host. Option-level abuse of an allowed command is not refused. The checker proves what the files say, not that a harness loaded them.

Pre-check history: the package tests passed under Python 3.14 and 3.10 before the first `check_package.py` run. Every report is kept in `review/precheck-*.json`. The run at 20:34 UTC was refused by the `layout` check because of an empty file, `review/last-check-output.txt`, left while saving command output; the file was removed and the run at 20:35 UTC passed. The first pass ended with `precheck-20260923T205337494408Z.json`. The command output of the current pass is in `PRECHECKS.txt` beside the package folder (`packages/workspace_write_no_network_settings/PRECHECKS.txt`), outside the package because the checker refuses extra top-level entries.

## Revision history

1. First pass, September 23, 2026, ending with package digest `11893cbac060b05de9a112a68ee126d79412bbdad1f728a316c32c05ebc2fc15`. Its package folder is kept unchanged as `earlier-attempt-20260923T2053Z.tar.gz` beside `PRECHECKS.txt`.
2. Second pass, the same day, by the same generator, after a fresh read of the installed harness packages. The OpenCode binary sets its `doom_loop` permission, the prompt before a repeated identical tool call, to `ask` by default, and an unanswered prompt stalls an unattended run. The wave's vocabulary rule refuses that key name in payload files, so the checker does not name it. Instead, the OpenCode `permission` object of a base policy must now start with `"*": "deny"`, which overrides every default that asks. The shipped variant already did. A new known-wrong case replaces the catch-all with one deny per tool: the revised checker refuses it, and the first-pass checker, run on the same document from the saved folder, passed it. The variants and the companion did not change. The same read confirmed the `strictAllowlist` rule above, which the first pass had recorded, and this note now names `--settings` as the way a host can use it.
