# Review note: deny_env_file_reads_settings

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a13_unattended_permission_settings (family anthropic). Package version 0.1.0.

## Method

A refusal-only fragment that is merged on top of whatever base settings a step uses. It refuses reading, searching, printing and editing any file whose name starts with `.env` (so `.env`, `.env.local`, `.env.example` and `.envrc` at any depth) and any file ending in `.pem`, `.key`, `.p12` or `.pfx`. It grants nothing, so it cannot widen a base policy, and it never asks, so it cannot stall a run. `.env.example` is refused on purpose: the request is that a step never sees credentials even by accident, and example files sometimes hold real values. A step that needs a setting reports the variable name instead.

`scripts/check_deny_env_file_reads_settings.py` runs 13 refusal probes and 6 pass-through probes (`src/environment.py`, `docs/env-setup.md`, `python3 -m pytest -q` and others must not be refused, which catches patterns that are too wide). For the fragment alone it also checks that nothing is granted. In a placed workspace it checks only the refusals, because the merged base decides the rest; that is where it catches a merge that lost a refusal.

## Authoring basis and sources

Original text and code. The wave specification asks for patterns such as `**/.env*`, `**/*.pem` and `**/*.key` instead of literal credential paths; no credential path is named. Repository sources at `a1fc7432`: `catalogue_packages.py`; `opencode_step_composition.py` (last matching rule wins); `harness_additional_recipes.py` (Gemini CLI settings); `harness_confinement.py` (the host clears the environment, which complements file refusals); `NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md`. Installed packages read without running them: Claude Code 2.1.281 (deny rules win over allow rules; `Read(path)` rules cover reads and `Edit(path)` rules cover every file-writing tool); the OpenCode binary (default rules ask before reading `*.env` and `*.env.*` and allow `*.env.example`; read and edit patterns are worktree-relative paths; shell patterns are each simple command's text); Gemini CLI 0.59.0 (the `read_file` tool refuses a path matched by the configured ignore patterns, `context.fileFiltering.customIgnoreFilePaths` names extra ignore files resolved from the project root, `write_file` does not check ignore patterns, and `grep_search` accepts a `no_ignore` argument); Codex 0.155.1 (`deny_read` appears only in managed requirements).

## Inputs and outputs

Inputs: placed settings files (and, for Gemini CLI, the placed ignore file), or one document with `--harness`, `--file` or `--stdin` and `--ignore-file`. Output: one JSON object with decisions, `problems`, `known_limits` and `refused`; exit 0, 1 or 2.

## Effects

The settings only refuse. The checker reads files (`reads_fs`). The tests start the checker with `sys.executable` (`spawns_process`) and write placed and merged copies inside `tempfile.TemporaryDirectory()` folders (`writes_fs`). The tests name example files but create no file with a secret value; no secret-shaped text exists anywhere in the package. No network use, no model calls.

## Closest existing items

- Starter candidate `keep_secrets_out_of_source_and_settings`: prose about storing references instead of secret values. This package enforces that a step cannot open the files where those values live.
- Starter candidate `refuse_secrets_and_unsafe_paths_in_generated_files`: checks generated output for secret shapes; this package stops the input side.
- No settings fragment exists in the library.

## Positive example

Merged into a base Claude Code policy that allows `Read(/**)` and `Bash(cat *)`, the fragment's `Read(**/.env*)` and `Bash(*.env*)` deny rules win, so `.env` cannot be read and `cat .env` is refused, while `src/app.py` stays readable. The tests merge it with a base for each placed harness and the checker exits 0.

## Known-wrong example

Merge the OpenCode fragment first and an open base second, so the base's `read: {"*": "allow"}` lands after the refusals. OpenCode keeps the last matching rule, so `.env` becomes readable. The checker reports `read_env_file`, `edit_env_file` and `print_env_file` and exits 1. The same merge in the other order passes. Nine more known-wrong variants are in the tests.

## Harness placement and verification state

- Claude Code: `.claude/settings.json` by `merge_json_object`; deny rules hold in any merge order. Unverified: that `Read` deny rules also stop the Grep and Glob tools, and how `Bash(*.env*)` is matched against a command Claude Code parses. A command merely containing `.env`, `.pem` or `.key` text (for example a Python call to `.keys()`) is also refused.
- OpenCode: `opencode.json` by `merge_json_object`; the fragment's keys must come after the base's patterns. Unverified: whether the grep tool searches inside hidden env files; its patterns are search terms, not paths, so this fragment cannot scope it.
- Gemini CLI: `.gemini/settings.json` by `merge_json_object` plus the ignore file copied to `.baltor/deny-env-file-reads-settings/ignore-patterns.txt`; companion into `GEMINI.md`; trusted folder or `--skip-trust`. Known limits: edits of these files and shell commands that print them are not refused by this variant, and `grep_search` with `no_ignore` can search them. The step's base settings must keep such commands out.
- Codex: not placed; no project key refuses reading a named file.
- Native loading was not observed. The checker command names `python3 -I -B`; the host must bind a trusted interpreter.

## Customer requests

- "Make sure the agent can never read my .env file, even if it tries."
- "Hide our certificate and key files from Claude Code and OpenCode."
- "Add a credentials block to whatever settings the step already has."

## Limits

These are harness refusals, not an operating system sandbox: code that an allowed command runs (for example a test that loads `.env`) can still read the file, and a harness without shell refusals can print it. Environment variables already set in the process are not covered; the host should start the harness with a cleared environment. File names outside the listed patterns are not covered.

Pre-check history: while writing the tests I found that my first wrong-order merge placed the base's top-level deny rule last, which would have hidden the problem; before the test first ran it was changed to use an open base and to check both orders. All tests passed under Python 3.14 and 3.10 before the first `check_package.py` run. Every report is kept in `review/precheck-*.json`; the one first-pass run, `precheck-20260923T205235094880Z.json`, passed. The command output of the current pass is in `PRECHECKS.txt` beside the package folder (`packages/deny_env_file_reads_settings/PRECHECKS.txt`), outside the package because the checker refuses extra top-level entries.

## Revision history

1. First pass, September 23, 2026, ending with package digest `6604b3efc66a172c3f12c2e96787ee6fdd1f03409a059767a57ec229384aa756`. Its package folder is kept unchanged as `earlier-attempt-20260923T2053Z.tar.gz` beside `PRECHECKS.txt`.
2. Second pass, the same day, by the same generator. The checker engine is shared by the five settings packages of this set. It gained one rule for base policies: an OpenCode `permission` object must start with `"*": "deny"`, because the OpenCode binary sets its `doom_loop` permission, the prompt before a repeated identical tool call, to `ask` by default. That rule does not apply to this refusal-only fragment; its OpenCode check returns before the rule, and the base settings it is merged into decide such defaults. The variants, the ignore file, the companion and the tests did not change, so only the script bytes and the package digest differ from the first pass.
