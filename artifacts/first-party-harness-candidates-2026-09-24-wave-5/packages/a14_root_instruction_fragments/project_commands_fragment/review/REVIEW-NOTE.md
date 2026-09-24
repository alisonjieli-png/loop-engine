# Review note: Project commands and layout fragment

Candidate only. Not approved, staged, served or published.

This note is for the independent review panel. It is never delivered to a harness.

## Method

A fill-in instruction section that every fresh step of one project can include. The host renders eight markers from the project's own declared values before launch:

| Marker | What the host fills in |
|---|---|
| `BUILD_COMMAND`, `TEST_COMMAND`, `LINT_COMMAND`, `FORMAT_COMMAND` | One-line commands run from the workspace root, or the word `none` |
| `TEST_ONE_FILE_COMMAND` | A one-line command with the literal word `FILE` where the test file path goes, or `none` |
| `SOURCE_DIRS`, `TEST_DIRS` | Comma-separated workspace-relative folders |
| `PROTECTED_PATHS` | Comma-separated paths or glob patterns the step must never edit, or `none` |

The rendered section tells a small model exactly which commands exist, where to look first, what never to edit, to run the tests for the file it will change before its first edit, and to run format, lint, build and all tests in that order after its last edit, reporting each exit code. A command written as `none` is skipped and reported, never replaced by a guess.

`tests/test_filled_values.py` states the host's side of the contract in code: every marker gets exactly one value; each value is one line without backticks or double braces; no command value installs or fetches anything; the one-file command names `FILE`. The filled example `examples/filled-values.json` renders to a complete section.

## Authoring basis and sources

Original text and code, MIT. Repository files at `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format.
- `artifacts/harness-intelligence-format-pilot-2026-09-22/context/README.md`: every marker is rendered from a validated contract before installation, and a file with an unfilled marker stops as `unrendered_step_input`.
- `artifacts/harness-intelligence-format-pilot-2026-09-22/context/repair-one-failing-test/codex/work/AGENTS.md`: a pilot step template that names an approved test command as a marker.
- `src/loop_engine/core/instance_instructions.py`: an instruction file describes authority and never grants it, and a hand-written instruction file is never silently replaced; hence the compose operation.

No outside text or code was copied or paraphrased.

## Inputs and outputs

Input: the eight values above, supplied by the host. Output: one rendered Markdown section of about 250 words, composed into the step's instruction file. The model's own outputs are the command results it reports.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The section tells the model to search the source folders, run the project's commands (a formatter rewrites files) and edit code. The test file only reads package files. No network, no model call, no secret.

## Closest existing items

- Scout result: none found.
- Pilot `repair_one_failing_test` (first-party candidate): one repair method whose template carries an approved test command marker. This section is not a method for one task; it is the project-level command and layout table that any step can include.
- Wave 5 a13 `test_commands_only_settings`: enforces allowed commands in harness settings. This section tells the model which commands to use; the settings enforce it.
- Wave 5 a06 `night_preflight`: runs the test command once before a night to confirm it works. This section does not run anything by itself.
- Wave 5 a03 `map_repository_layout` prints a measured map; wave 5 a08 `generated_files_stay_unedited` is a path-scoped rule. This section carries the host's declared folders and protected paths instead.

## Positive example

With the example values, rule 1 renders to "All tests: `python3 -m unittest discover -s tests -v`" and rule 4 to "Never edit these paths: requirements.lock, src/generated/, migrations/applied/." A step that fixes `src/parse.py` runs `python3 -m unittest -v tests/test_parse.py` first, notes one failing test that already failed, edits the file, then runs compile, the full tests, and reports lint and format as skipped because they are `none`.

## Known-wrong example

Without the section, a small model in a unittest project guesses `pytest`, gets "command not found", then tries to install it. With the section it has no reason to guess. On the host side the render test refuses a missing `PROTECTED_PATHS` value, a two-line `TEST_COMMAND`, a backtick in `LINT_COMMAND`, a `BUILD_COMMAND` that installs a package, and a one-file command without `FILE`.

## Harness placement and verification state

- The rendered `AGENTS.md` is composed into the step's root `AGENTS.md` for codex, opencode and pi (observed), goose (documented in `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` of the shared checkout) and kimi_cli (unverified).
- Claude Code gets `CLAUDE.md` holding `@AGENTS.md` (file observed, import documented). Gemini CLI gets `GEMINI.md`, a byte copy of `AGENTS.md` (documented), rendered with the same values.
- `LICENSE` goes to `.baltor/project-commands-fragment/LICENSE`. The test and the example are not placed.
- Not observed: a harness reading the rendered section, a Kimi CLI project `AGENTS.md`, and the compiler rendering and composing both `AGENTS.md` and `GEMINI.md` with identical values.

## Customer requests

- "How do I tell every agent step which command runs the tests in my repo?"
- "The agent keeps editing the lock file and generated code. Where do I say it must not?"
- "Stop my local model from guessing build commands."

## Limits

- The section is only as true as the host's values. Nothing here runs the commands to prove them; a06 `night_preflight` does that.
- Folder and path lists are prose; how a glob in `PROTECTED_PATHS` is read is up to the model. Enforcement belongs to settings (a13) and guard hooks (a04).
- Commands are run from the workspace root; a project that needs another folder must write that into the command.
- No measurement shows that the section improves outcomes.

## Pre-check history

Every command output is kept in `review/PRECHECKS.txt`, and every checker report in `review/precheck-*.json`; the newest report is the gate record.

- Round 1: fill and check passed (package digest `83b28dde`) with one warning: `spawns_process` and `writes_fs` are declared but not detected. The section tells the model to run the project's commands and a formatter rewrites files, which a static scan of an inline command list cannot see; the declaration stays.
- Mutation check: removing the lint marker from `AGENTS.md`, and removing the install refusal from the render contract, each made its named test fail (2 of 2).
- Edit after round 1: rule 5 says to run all tests when the one-file command is `none`, so the baseline run never depends on a missing command.
- Final round: fill and check passed with the same warning (package digest `26312c51`); 4 tests ran under Python 3.14 and 3.10 in the sandbox. The check was run once more after this history was written.
