# Review note: Extract failures from test output

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a03_ticket_work_tools, model family anthropic. This note is never delivered to a harness.

## Method

One script, `scripts/extract_failures.py`, reads test runner output and prints one `test_failures/v1` JSON object. It recognizes pytest text output in the long, short, line, native and no-traceback modes, unittest text output in the Python 3.10 and Python 3.11 and later header styles, JUnit XML, and a bare Python traceback. For each failure it keeps the test id, the kind (failed, error, crash or unexpected success), the phase for setup, teardown, collection and import errors, the exception name, a message bounded to 8 lines and 1,200 characters, the first project frame and the outermost project test frame. The first project frame is found by reading frames from the innermost outward and skipping frames under `site-packages`, `dist-packages`, virtual environment folders, the standard library and pseudo files. For a chained exception the last exception of the chain is reported and the first one is kept in `cause`. In pytest's long mode a frame's function is taken from the `def` line of its source excerpt, because the location line does not name it. A failure block with no traceback, such as a strict unexpected pass, keeps its own text as the message. When no project frame is found, a note says why and what to rerun. Captured output sections and `system-out` elements are never read into the result. A `consistency` block compares the number of extracted failures and errors with the counts in the runner's own summary line, so a parser miss is visible instead of silent. The model decides only what to fix; everything deterministic is in the script.

## Authoring basis and sources

Original code and text written for this wave. No outside code or documentation text was copied. The output formats were observed on this machine on September 23, 2026 by running pytest 9.1.1 on Python 3.14.4 (`--tb=auto`, `short`, `line`, `native`, `no` and `--junitxml`) and `python -m unittest -v` on Python 3.14.4 and 3.10.20 against a synthetic project in a temporary folder that was deleted afterwards. The test fixtures reproduce those shapes with synthetic paths under `/srv/shop`. On September 24, 2026 a second session repeated the runs on a new synthetic project with seven failures of different kinds (a library frame, a fixture error at setup, a parametrized case, a chained exception, a strict unexpected pass, captured output and a plain assertion): pytest 9.1.1 with `--tb=auto`, `long`, `short`, `line`, `native` and `no`, with `-v -rA`, with `-x` and with `--junitxml`, a collection error, a passing run and a run with no tests, and `python -m unittest -v` on Python 3.14.4 and 3.10.20 with subtests, an import error, a `setUpClass` error, an expected failure and an unexpected success. `consistency.matches` was true in every run. Four defects were found and fixed, each with a test that fails on the earlier script: the message of a chained exception came from the first exception while the name came from the last; long-mode frames had no function name; a strict unexpected pass showed the summary text cut to `[XPASS(strict)] ...`; and the unittest `passed` total was 0 when one test passed, because failing subtests and a `setUpClass` error were subtracted as tests. Python 3.10 also names an unexpected success only on its verbose progress line, which the script now reads. The Java stack frame shape inside JUnit XML follows the common `at package.Class.method(File.java:line)` form; no Java runner was run here, so that path is tested only against a hand-written fixture. Sources cited in the manifest: the catalogue package contract (`catalogue_packages.py`) for the package format, and `src/loop_engine/core/independent_evidence.py`, whose rule that an absence of dissent is not agreement is the rule this script follows when it reports output with no recognizable result as `no_result_found` with exit 1, never as a pass.

## Inputs and outputs

Input: test output on standard input (`-`, the default) or a file path that must stay inside `--root` (default: the current folder). Options: `--format auto|pytest|unittest|junit`, `--project-root` (default: the current folder), `--max-failures` (default 25, at most 1,000) and `--max-bytes` (default 64 MiB, at most 256 MiB). Output: one JSON object with `status` (`failures_found`, `no_failures`, `no_tests_ran`, `no_result_found` or `refused`), `format`, `totals`, `consistency`, `failures`, `omitted_failures` and `notes`. Exit 0 for a finished run with no failure, 1 for failures, errors, no tests or no usable result, 2 for refused input.

## Effects

Declared effects: `reads_fs` and `spawns_process`. The script reads standard input or one regular file below `--root`; it refuses `..`, paths that leave the root directly or through a symbolic link, and anything that is not a regular file, and it opens the file with no-follow and non-blocking flags before checking its type. It writes no file, makes no network call and calls no model. The skill tells the reader to run the project's tests and the script, which starts processes. The tests start the script with `sys.executable` and pass data on standard input; they write nothing. XML input that declares a document type or an entity is refused before parsing.

## Closest existing items

- `read_a_failure_report_and_name_the_first_wrong_value` (starter, text skill): a prose method for walking from the reported failure to the first wrong value. This package does not replace that reasoning. It produces the input that method needs, the first project frame for every failure, from logs of any length, and it checks its own count against the runner's summary.
- `test_run_summarizer` (wave 5, a05, subagent definition): a read-only helper agent that summarizes a test run in prose. This package is a deterministic script with exact counts; the subagent could call it.
- `verify_fail_then_pass_evidence` (wave 5, a12, verifier): checks that a test failed before a change and passed after it. This package only extracts failures from one run and makes no before and after claim.

## Positive example

For the short-mode pytest output in the tests, the script returns two failures. `tests/test_prices.py::test_comma` has exception `ValueError`, message `ValueError: invalid literal for int() with base 10: '3,50'` and first project frame `src/shop/prices.py` line 7 in `_to_cents`; `consistency.matches` is true. The full result is `examples/pytest-short-output.json`, and a test compares the script output with it byte for byte after parsing.

## Known-wrong example

A pytest log whose last printed frame is `/usr/lib/python3.12/site-packages/tablekit/frame.py:880` with `KeyError: 'day'`. A model that reads only the end of the log edits the library or the last frame. The test `test_known_wrong_library_frame_is_never_named_first` requires the first project frame to be `src/shop/report.py` line 22 and never a `site-packages` path.

## Harness placement and verification state

The whole folder is copied with exact bytes to `.claude/skills/extract-test-failures/` (Claude Code), `.agents/skills/extract-test-failures/` (Codex), `.opencode/skills/extract-test-failures/` (OpenCode), `.pi/skills/extract-test-failures/` (Pi) and `.gemini/skills/extract-test-failures/` (Gemini CLI). The first four skill roots are recorded as observed in the wave specification; the Gemini CLI root is documented in the placement research file and was not observed, so Gemini CLI is listed in `unverified_targets`. Native discovery of this package was not probed in any harness. The commands use `SKILL_FOLDER`; that the harness tells the model where the skill folder is, so the model can write the real path, is unverified for every harness in this package.

## Customer requests

- "My overnight run failed with a 4,000 line pytest log; which tests broke and where should I look first?"
- "Summarize the JUnit report from CI into the failing tests and the line in our code."
- "The unittest output is too long for my local model; give it only the failures."

## Limits

- Tested formats: pytest 9.1.1 text and JUnit XML, unittest text from Python 3.10 and 3.14. Other runners, pytest plug-ins that change the report (for example parallel workers or custom reporters) and older pytest versions were not tested.
- In pytest line mode the failures carry no block header, so each printed message is paired with the summary item whose message it starts with; two failures with the same cut summary message are paired in printed order.
- Line mode prints only the crash location. When that location is library code, `first_project_frame` is null and a note asks for a rerun with `--tb=short`.
- The unittest `passed` total subtracts each failing test once and leaves out class and module fixture errors, which the runner does not count as tests. A `setUpModule` failure was checked on real output of Python 3.14.4 and 3.10.20: the module's tests are not counted as run, the error has phase `module setup`, and `passed` stayed exact.
- Without `-v`, Python 3.10 does not name an unexpected success; the count stays exact and a note asks for `-v`.
- A frame is a project frame by path rules. A project stored under a folder named `site-packages`, or a vendored library inside the project, is misjudged. `--project-root` narrows the rule for absolute paths.
- Java library prefixes are a fixed list; JUnit XML from tools other than pytest was tested only with a hand-written fixture.
- Messages are bounded; the runner's full output stays the authority for detail.

## Pre-check history

Every `check_package.py check` report is kept in `review/`. The earlier session summarized its runs in `review/PRECHECKS.txt`, which stays in place. The September 24 session logged every run, failures included, in `packages/extract_test_failures/PRECHECKS.txt` beside the package folder, because the layout check refuses extra top-level entries inside it. That log starts with a baseline check of the bytes the earlier session left, which was refused because the recorded digests no longer matched the edited files.
