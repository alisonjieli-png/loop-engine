# Review note: Map a repository layout compactly

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a03_ticket_work_tools, model family anthropic. This note is never delivered to a harness.

## Method

One script, `scripts/map_layout.py`, lists the entries of a repository without reading file contents and prints one `repository_layout/v1` JSON object. Every file gets one category from its name and the names of the folders above it: generated (lock files, minified files, protocol buffer output, compiled files, and everything inside a build output folder), test, config, docs, source, data, asset or other. Each folder takes the category that holds most of its files, so a Python package named `data` or `settings` is still source. Folders named `build`, `dist`, `out`, `coverage`, `vendor` and similar are counted as generated and not expanded; a `target` folder is generated only beside `Cargo.toml`, `pom.xml` or `build.sbt`. Version control, dependency, cache and virtual environment folders (including any folder that holds `pyvenv.cfg`) are listed as skipped and never walked. Symbolic links are counted and never followed. The tree is chosen breadth first and cut to `--max-lines` lines with explicit "more folders here" markers, while every count stays exact. Names that look like secrets (`.env` files, key and certificate files, credential JSON names) are listed so the model knows not to open them; their contents are never read.

## Authoring basis and sources

Original code and text written for this wave from general knowledge of common repository conventions. No outside code or text was copied. The category rules are conventions, not facts about any particular repository. Sources cited in the manifest: `catalogue_packages.py` for the package format, and `src/loop_engine/core/component_inventory.py`, which lists a repository's material without guessing semantics; this package takes the same stance, labeling folders by counted file names only.

## Inputs and outputs

Input: `--root` (default: the current folder) and optional `--focus FOLDER`, or a path list with `--paths-from FILE` (inside the root) or `--paths-from -`, one path per line or NUL separated as `git ls-files -z` prints them. Options: `--max-depth` (default 3), `--max-lines` (default 60) and `--max-entries` (default 200,000, at most 2,000,000). Output: `status` (`ok`, `no_source_found` or `refused`), `totals` by category, `languages`, `key_files` (readme, build and config, continuous integration), `largest_source_folders`, `largest_test_folders`, `tree`, `omitted_tree_folders`, `folders` (up to 400 records), `skipped`, `sensitive_files` and `notes`. Exit 0 when source or test files exist, 1 when none do, 2 for refused input: more entries than allowed, an unsafe or quoted path in the list, or a focus that leaves the root or is a symbolic link. The script refuses rather than cuts its input.

## Effects

Declared effects: `reads_fs`, `writes_fs` and `spawns_process`. The script lists folder entries under the root and checks for `pyvenv.cfg`, and in list mode reads one list file or standard input; it never reads other file contents, writes nothing, makes no network call and calls no model. `writes_fs` is declared only because the tests build synthetic trees inside `tempfile.TemporaryDirectory()`; the script itself writes no file. The skill tells the reader to run the script, optionally after `git ls-files`, so `spawns_process` is declared.

## Closest existing items

- `query_codegraph_change_impact` (planned Codex method): answers which symbols a change affects from a code graph. This package needs no index and no parser; it maps folders and counts.
- `repository_scout` (wave 5, a05, subagent definition): a read-only helper agent that answers questions by opening files. This package prints a map and never opens a file; neither ranks files for a ticket, as the wave boundary requires.
- `inventory_file_digests` (format pilot 1, skill with scripts): lists files with SHA-256 digests for integrity. This package gives categories and counts for orientation and computes no digest.

## Positive example

For the synthetic path list in the tests (an `app` package, `tests`, `docs`, `dist`, `node_modules` and `scripts`), the result shows `app/ [source] 5 files`, `tests/ [test] 2 files`, `dist/ [generated] 1 file; build output, not expanded` and `node_modules` as skipped, with 12 counted files. The full result is `examples/layout-output.json`, and a test compares the script output with it.

On September 24, 2026 a second session ran the script, unchanged, on a read-only checkout of this repository at revision `1920296c` (4,315 files in 897 folders). It finished in 0.4 seconds, printed 99 lines, named `src/loop_engine` and `src/loop_engine/core` as the largest source folders and `tools` as the folder with the most test files, grouped 14 cache folders into one skipped line, and left 187 deeper folders for `--focus`. That run is one observation on one repository, not a measured benefit. Reading that output as a small model would, the session found one gap: a line such as `... 9 more folders here` did not say which folder to pass to `--focus`, so the reader had to rebuild the path from indentation. The line now names the exact value, for example `use --focus src/loop_engine to open them`, quoted when the name needs it, or says to raise `--max-lines` when the hidden folders sit at the top. The test `test_hidden_folder_lines_name_the_exact_focus_value` fails on the earlier script.

## Known-wrong example

A repository holds `src/shop/prices.py` and a built copy at `build/lib/shop/prices.py`. A search for `def parse_price` can find the copy first, and an edit there is overwritten by the next build. The test `test_known_wrong_generated_copy_is_not_offered_as_source` requires `build` and `build/lib` to be generated, no `build` path among the largest source folders, and no expanded `lib/` line under `build/`. A first draft of the script failed this case: `build/lib` was listed as a source folder. The fix makes folders inside a build output folder inherit its generated mark and counts their files as generated.

## Harness placement and verification state

The folder is copied with exact bytes to `.claude/skills/map-repository-layout/` (Claude Code), `.agents/skills/map-repository-layout/` (Codex), `.opencode/skills/map-repository-layout/` (OpenCode), `.pi/skills/map-repository-layout/` (Pi) and `.gemini/skills/map-repository-layout/` (Gemini CLI). The first four roots are recorded as observed in the wave specification; the Gemini CLI root is documented but not observed, so Gemini CLI is listed in `unverified_targets`. Native discovery of this package was not probed. That each harness tells the model where the skill folder is, so it can replace `SKILL_FOLDER`, is unverified.

## Customer requests

- "Give my local model a map of this repo so it stops reading every file."
- "Which folders are source, which are tests, and which are build output?"
- "Show me where the code lives in this monorepo without walking node_modules."

## Limits

- Categories come from names and extensions. A folder of generated code with ordinary names, or a hand-written file named like a lock file, is misjudged.
- In list mode nothing on disk is read, so a virtual environment with an unusual folder name is not recognized.
- The map says where kinds of files are; it does not say which file a task needs. That choice stays with the model and its notes.
- Very large trees are refused above `--max-entries`; `--focus` or the tracked-file list is the way through.
- Another draft counted `security.py` as documentation because the name rule for `SECURITY.md` ignored the extension; the rule now applies only to Markdown, text and similar names.

## Pre-check history

Every `check_package.py check` report is kept in `review/`. The earlier session summarized its runs in `review/PRECHECKS.txt`, which stays in place. The September 24 session logged every run, failures included, in `packages/map_repository_layout/PRECHECKS.txt` beside the package folder, because the layout check refuses extra top-level entries inside it. That log starts with a baseline check of the bytes the earlier session left, which was refused because the recorded digests of four files no longer matched the edited files.
