# Review note: Select Python tests for changed files

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a03_ticket_work_tools, model family anthropic. This note is never delivered to a harness.

## Method

One script, `scripts/select_tests.py`, builds a static import graph of the Python files under `--root` with the `ast` module and prints one `selected_tests/v1` JSON object. No project code is imported or run. Import roots are the repository root, `src` when it exists, the parent folder of every top-level package, and any `--import-root`; each test file may also import from its own first non-package folder, as pytest does. Absolute imports mark every package prefix as imported, relative imports resolve against the file's folder, constant `importlib.import_module` and `__import__` calls and `pytest_plugins` strings count as imports, and every package `__init__.py` above a file counts as imported with it. Each test depends on every `conftest.py` in its folder and the folders above it. A breadth-first walk over the reversed graph from each changed file finds the tests that reach it and records the chain in `via`. A deleted file, or the old side of a rename, stays in the graph by module name so its former importers are selected. A changed file that no test imports is matched by file name against the text of the test files, which finds tests that run a script or read a data file by path. Documentation changes need no tests. Anything else that cannot be traced is listed and the result recommends the full suite.

## Authoring basis and sources

Original code and text written for this wave from general knowledge of Python import semantics, of pytest's `conftest.py` and root-folder rules, and of git's unified diff and `--name-status` formats. No outside code or documentation text was copied. Sources cited in the manifest: `catalogue_packages.py` for the package format; `src/loop_engine/reachability_report.py`, a static import closure in this repository whose stated limits (imports inside functions are included, dynamic imports and registry strings are not resolved, and absence from the closure is not proof) this package shares and reports in its `warnings`; `.github/workflows/ci.yml`, whose two `unittest discover` suites were used for the check below; and `AGENTS.md`, whose verification rule is to run the smallest relevant check first and then the owning checks.

On September 24, 2026 a second session ran the script, unchanged, on an export of this repository at revision `1920296c` (1,334 Python files, 115 test files). A change to `src/loop_engine/core/service_runtime/catalogue_packages.py` took 5.3 seconds and selected 20 test files, each with its import chain; a plain text search for the module name finds only one of them. To test the selection against real breakage, the check ran each of the 69 test files of the two CI suites in Bubblewrap with no network, once as committed and once with the changed module made to raise an error on import. 48 files passed as committed; 21 failed already in that sandbox and were left out. With the broken module, 2 of the 48 failed, and both were selected; no broken test file was missed. 10 more selected files still passed. Each of their reported chains was checked hop by hop: each holds an import written inside a function, which those tests did not call, and none runs through a conditional or guarded import. The same check for a change to `src/loop_engine/core/harness_intelligence.py`, a module that many files import at module level, selected 45 of the 69 files; with that module broken, 14 of the 48 files that passed as committed failed, all 14 were selected, and 11 selected files still passed; their chains were checked the same way, with the same finding. Across the two checks, 16 test files broke and none of them was missed. Two changed modules in one repository are a small sample; this is evidence of the direction of the errors, not a measured recall.

## Inputs and outputs

Input: any combination of `--diff FILE` or `--diff -` (a unified diff, git style or plain), `--changed-from FILE` or `-` (plain paths, NUL separated paths or `git diff --name-status` lines) and `--changed PATH ...`, all relative to `--root`. Options: `--import-root`, `--test-pattern` (default `test_*.py`, `*_test.py` and `tests.py`), `--allow-unparsed` and `--max-files` (default 50,000). Output: `status` (`selected`, `none_selected`, `full_suite_recommended`, `no_code_changed` or `refused`), `changed`, `selected_tests` with reasons and chains, `test_paths`, `untraced_changes`, `untested_changes`, `unreadable_files`, `dynamic_import_files`, `warnings`, `import_roots` and `counts`. Exit 0 when tests are selected and every change is traced, or only documentation changed; 1 when the full suite is recommended or no test covers the change; 2 for refused input, such as a path with `..`, an absolute path outside the root, no change named, or two inputs on standard input.

## Effects

Declared effects: `reads_fs`, `writes_fs` and `spawns_process`. The script walks the root without following symbolic links, skips version control, dependency, cache, build and virtual environment folders, and reads Python files of at most 4 MiB each and one diff or list of at most 64 MiB. It writes nothing, makes no network call and calls no model. `writes_fs` is declared only because the tests build a synthetic repository inside `tempfile.TemporaryDirectory()`. The skill tells the reader to run `git diff`, the script and the selected tests, so `spawns_process` is declared.

## Closest existing items

No first-party or staged item selects tests from a change; the scout found none. The nearest items by task are:

- `query_codegraph_change_impact` (planned Codex method): answers change impact from a prebuilt code graph index. This package needs no index; it parses imports on each run and answers only "which test files".
- `extract_test_failures` (wave 5, same assignment): reads the output of the tests this package selects. The two are meant to be used one after the other, and neither repeats the other.

## Positive example

In the synthetic repository of the tests, a change to `src/shop/prices.py` selects `tests/test_prices.py` directly and `tests/test_checkout.py` through `src/shop/checkout.py`, with status `selected` and exit 0. The full result is `examples/selection-output.json`, and a test compares the script output with it.

## Known-wrong example

Choosing tests by matching file names runs only `tests/test_prices.py` after a change to `prices.py` and misses `tests/test_checkout.py`, which imports the changed module through another module. The test `test_known_wrong_name_matching_misses_the_indirect_test` requires the indirect test and its chain `tests/test_checkout.py`, `src/shop/checkout.py`, `src/shop/prices.py`. An earlier draft treated the old side of a rename as an existing file; after a real rename it is gone, so its importers were not selected. The fix keeps such paths in the graph by module name.

## Harness placement and verification state

The folder is copied with exact bytes to `.claude/skills/select-tests-for-changed-files/` (Claude Code), `.agents/skills/select-tests-for-changed-files/` (Codex), `.opencode/skills/select-tests-for-changed-files/` (OpenCode), `.pi/skills/select-tests-for-changed-files/` (Pi) and `.gemini/skills/select-tests-for-changed-files/` (Gemini CLI). The first four roots are recorded as observed in the wave specification; the Gemini CLI root is documented but not observed, so Gemini CLI is listed in `unverified_targets`. Native discovery of this package was not probed. That each harness tells the model where the skill folder is, so it can replace `SKILL_FOLDER`, is unverified.

## Customer requests

- "The full test suite takes forty minutes; which tests should my overnight model run after this change?"
- "Give me only the pytest files that touch the modules in this diff."
- "Did my change break anything that imports it, without running everything?"

## Limits

- Selection is static. Imports by a computed name, plugin entry points, `sys.path` changes at run time, subprocess calls with computed paths and tests that reach code over a network are not traced; files that compute module names are listed in `dynamic_import_files`.
- Name matching in test text can over-select, for example for a common file name. Over-selection is the safe direction.
- An import written inside a function counts as an import, as in the repository's own reachability report. A selected test can therefore pass without ever loading the change; in the two mutation checks above, 21 of the 37 selected files that passed as committed did so. A passing selected test is not proof that the change ran.
- Import roots are inferred; a layout the rules do not cover needs `--import-root`.
- The parser is the running Python's own; a project that uses newer syntax than that interpreter reports unparsed files and, by default, recommends the full suite.
- A plain diff hunk in which a removed line starting with two dashes is directly followed by an added line starting with two plus signs is read as a new file header; git diffs are not affected.
- The selected tests are a first run, not a replacement for the full suite when the step requires it.

## Pre-check history

The earlier session wrote the payload and this note but no `package.json`, and ran no check. The September 24 session wrote the manifest, set every payload file to mode 0644 (they were 0664), and logged every run, failures included, in `packages/select_tests_for_changed_files/PRECHECKS.txt` beside the package folder, because the layout check refuses extra top-level entries inside it. Every `check_package.py check` report is kept in `review/`. The first logged run is a baseline check of the bytes the earlier session left; it was refused because `package.json` was missing.
