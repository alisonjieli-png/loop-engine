# Review note: data_step_scoped_write_settings

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a13_unattended_permission_settings (family anthropic). Package version 0.1.0.

## Method

One policy for a data cleaning or data preparation step, with a fixed folder convention: input tables in `data/raw/`, results in `data/output/`, reports in `reports/`. The harness may read everything in the workspace, may create and edit files only under `data/output/` and `reports/`, may not create or change Python files anywhere, and may run only `ls`, `wc`, `head` and scripts started as `python3 -I -B` from `.baltor/` (package support files) or the harness skill folder. Commands that contain `..` or redirect with `>` are refused, so a script written into the output folder cannot be started by walking out of `.baltor/`, and a shell command cannot copy or redirect over raw data. Nothing waits for an approval prompt.

`scripts/check_data_step_scoped_write_settings.py` runs 30 probes: reads of raw data and source, writes to output, nested output and reports, edits of raw data, source, a top-level file and the harness settings, a Python file in the output folder, a write outside the workspace, the allowed commands, inline Python, a script started without `-I -B`, `.baltor/../data/output/helper.py`, `cp` over raw data, a redirection into raw data, and network tools.

## Authoring basis and sources

Original text and code. Repository sources at `a1fc7432`: `catalogue_packages.py`; `opencode_step_composition.py` (per-path `edit` patterns are the layer observed to hold, the last matching rule wins, `ask` hangs unattended steps); `harness_additional_recipes.py` and `harness_responses_recipes.py` (used to state why Gemini CLI and Codex are not placed); `harness_confinement.py` (the host confinement that must keep `data/raw/` read-only for scripts); `NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md`. Installed packages read without running them: the Claude Code 2.1.281 settings reference (`Edit(path)` covers every file-writing tool; `/**` paths start at the project root; a deny rule wins over an allow rule); the OpenCode binary (edit patterns are paths relative to the worktree, `*` crosses folders, the last matching rule wins); the Gemini CLI 0.59.0 docs (settings narrow only shell commands by argument; workspace policy files are disabled).

## Inputs and outputs

Inputs: placed settings files or one document with `--harness` and `--file` or `--stdin`. Output: one JSON object with decisions, `problems`, `known_limits`, `writable_paths` (`data/output/`, `reports/`) and `refused`; exit 0, 1 or 2.

## Effects

The step reads files, writes under the two output folders and starts declared scripts (`reads_fs`, `writes_fs`, `spawns_process`). The checker only reads. The tests start the checker with `sys.executable` and write placed copies inside `tempfile.TemporaryDirectory()` folders. No network use, no secret reads, no model calls.

## Closest existing items

- None found by the scout for settings. Wave 5 `raw_data_stays_read_only` (a08 rule) tells a model not to edit raw data; this package makes the harness refuse it. Wave 5 `cleaning_apply_packet` (a10) is the step that writes a cleaned copy; this package is the permission setting for such a step. Wave 5 `verify_cleaned_copy_change_log` (a15) checks the result afterwards. The four can be used together.

## Positive example

With the OpenCode variant, `data/output/orders_clean.csv` matches `data/output/*` and is writable, while `data/output/helper.py` also matches the later `*.py` deny and is refused, because OpenCode keeps the last matching rule. `python3 -I -B .opencode/skills/example-table-skill/scripts/clean_table.py --input data/raw/orders.csv --output data/output/orders.csv` is allowed. Both placed variants pass with one known limit.

## Known-wrong example

Remove `Bash(*..*)` from the Claude Code deny list and `python3 -I -B .baltor/../data/output/helper.py` matches the allowed `.baltor/` script prefix, so a script the step wrote into the output folder can run. The checker reports `run_script_from_output` and exits 1. This and 11 other known-wrong variants are in the tests.

## Harness placement and verification state

- Claude Code: `.claude/settings.json` by `merge_json_object`, companion into `AGENTS.md` through the step's `CLAUDE.md` import. Unverified: that `/data/output/**` resolves from the project root for project settings in a run; the settings reference in the installed binary says so for sandbox paths and uses `Edit(/**)` as a workspace rule.
- OpenCode: `opencode.json` by `merge_json_object`, `"*": "deny"` first.
- Codex: not placed. `workspace-write` makes the whole workspace writable, and `read-only` would refuse the output folder too.
- Gemini CLI: not placed. `write_file` and `replace` cannot be limited to folders in `settings.json`.
- Known limit on both placed harnesses: a declared script writes wherever its arguments point. The host must keep `data/raw/` read-only at the operating system level for a full guarantee.
- The checker command names `python3 -I -B`; the host must bind a trusted interpreter. Native loading was not observed.

## Customer requests

- "Clean this CSV overnight but never touch the original file."
- "The agent can only write to data/output and reports, nowhere else."
- "Stop the data step from editing my pipeline code."

## Limits

The folder names are a fixed convention; a project with other names needs a new rendering and review. Scripts are trusted to honour their output arguments. Reads are not limited, so raw data and source code are visible to the step. Pair with `deny_env_file_reads_settings` to hide credential files.

Pre-check history: the first test run failed one known-wrong case because my expected marker named the wrong probe (the mutation itself was refused correctly); the marker was corrected and all tests passed under Python 3.14 and 3.10 before the first `check_package.py` run. Every report is kept in `review/precheck-*.json`; both first-pass runs, `precheck-20260923T204554369739Z.json` and `precheck-20260923T205350780425Z.json`, passed. The command output of the current pass is in `PRECHECKS.txt` beside the package folder (`packages/data_step_scoped_write_settings/PRECHECKS.txt`), outside the package because the checker refuses extra top-level entries.

## Revision history

1. First pass, September 23, 2026, ending with package digest `6a99702d3a11ff26d4f210355496e48037a56f561ceb862a1170333dec512f98`. Its package folder is kept unchanged as `earlier-attempt-20260923T2053Z.tar.gz` beside `PRECHECKS.txt`.
2. Second pass, the same day, by the same generator, after a fresh read of the installed harness packages. The OpenCode binary sets its `doom_loop` permission, the prompt before a repeated identical tool call, to `ask` by default, and an unanswered prompt stalls an unattended run. The wave's vocabulary rule refuses that key name in payload files, so the checker does not name it. Instead, the OpenCode `permission` object of a base policy must now start with `"*": "deny"`, which overrides every default that asks. The shipped variant already did. A new known-wrong case replaces the catch-all with one deny per tool: the revised checker refuses it, and the first-pass checker, run on the same document from the saved folder, passed it. The variants and the companion did not change.
