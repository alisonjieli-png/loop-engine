# Review note: Check a diff against allowed paths

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a12_ticket_result_verifiers, model family anthropic. An earlier pass of the same generator wrote the first version on September 23, 2026; this pass reviewed it, changed it and checked it again. The earlier bytes are kept in `packages/check_diff_allowed_paths/earlier-attempt-20260924T0101Z.tar.gz`. This note is never delivered to a harness.

## Method

One verifier method: compare the files a step changed with the path patterns the step was allowed to change, plus categories a small step should never change without saying so. The script parses a unified diff by its hunk counts (so a content line that starts with `---` or `+++` is never mistaken for a header), reads git's extended headers (new, deleted, renamed and copied files, modes, binary markers and binary literal sizes, submodule pointers) and applies nine rules: `outside_allowed_paths`, `unsafe_path`, `test_file_deleted`, `binary_file`, `large_file`, `lock_file`, `generated_file`, `symlink` and `submodule`. A second input, `--untracked`, takes the output of `git ls-files --others --exclude-standard`, because `git diff HEAD` does not show new untracked files; each new file is checked like an added file, and its first bytes are read to find binary content, links and size. `--permit` moves one named category to a `permitted` list that stays in the output. Files the host placed for the step are left out with `--ignore` patterns, and the folder of the skill itself is always left out, so a harness that places this skill inside the repository does not see its own files flagged; both go to an `ignored` list with their reason. Exit 0 pass, 1 fail, 2 refused.

## Authoring basis and sources

Original text and code, written for this wave, MIT like the repository. No outside text or code was copied. Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows; its placement path rule (no `..`, no `.git`, no absolute path) is also the `unsafe_path` rule here.
- `examples/29_intelligence_service/starter-catalogue/bodies/review_a_change_for_what_is_missing.md`: the closest prose method.

Git's diff header forms (quoted paths with octal escapes, a trailing tab after paths with spaces, `Binary files ... differ`, `GIT binary patch` with `literal` sizes, `Subproject commit` lines, modes 120000 and 160000) are written from general knowledge of git output. In this pass they were checked against real output: a probe repository under `generator-a12-work/probe/repo2` held a rename with a space in the name, a deleted test, a lock file edit, a mode change, a new symbolic link, a new binary file and a generated Go file, and `git diff --cached` with and without `--binary` produced every finding expected, with the mode change as a warning. `git apply --numstat --summary` parses both shipped example diffs. The three diff parsers of this assignment also read 120 real diffs of the repository's history without an error; the only refusals were combined diffs of merge commits.

## Inputs and outputs

Inputs: `--diff` and `--untracked` (either may be `-` for standard input, at least one is required), allowed patterns from `--allow` or `--allow-file` (text lines, a JSON list or an `allowed_paths` object), optional `--permit`, `--ignore`, `--max-file-bytes` (default 262144), `--max-file-lines` (default 2000), `--test-glob`, `--generated-glob` and `--root`. A name without wildcards means one file or everything below one folder, as `src` or `src/`. Each input is at most 64 MiB of UTF-8. Output: one JSON object with `verdict`, `findings` (rule, path, detail), `permitted`, `ignored`, `warnings`, `files`, the patterns used, the limits and the digest of each input.

## Effects

`reads_fs`: the script reads the named inputs and the first bytes of each listed new file, all below `--root`, refusing `..` and paths that resolve outside it. `spawns_process`: `SKILL.md` tells the reader to run `git diff`, `git ls-files` and `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The `git diff` command uses `--no-ext-diff --no-textconv` so that no external diff program configured in the repository runs.

## Closest existing items

- `review_a_change_for_what_is_missing` (starter, prose): a person looks for absent work. This package checks present work against a declared scope and returns a machine verdict.
- Wave 5 neighbours: `guard_workspace_file_writes` (a04) refuses writes at the moment a tool call happens; this package checks the finished diff, including files written by commands the hook never saw. `generated_files_stay_unedited` (a08) is a rule for the model; this package is the check after the fact. The a09 `ticket_fix_verification_packet` checks changed paths against prefixes inside its own run; this package is a separate step that also finds lock, generated, binary, large and deleted test files. `detect_weakened_test_assertions` (a12) reads what changed inside test files; this package only refuses deleting or moving them.
- A search of `scout/existing-inventory.tsv` found no executable scope check for a diff.

## Positive example

`examples/scoped-change.diff` changes `src/slugs.py` and adds a test to `tests/test_slugs.py`; with `examples/allowed-paths.json` the verdict is pass. The same diff passes with `--allow src --allow ./tests`.

## Known-wrong example

`examples/out-of-scope.diff` holds the same fix plus a settings edit, the deletion of `tests/test_legacy_slugs.py` (the test that expected the old behavior), a `package-lock.json` bump and a new binary `assets/banner.png`. The script reports `outside_allowed_paths` for all four, plus `test_file_deleted`, `lock_file` and `binary_file`, and does not report the two allowed files.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/check-diff-allowed-paths/`, `.agents/skills/check-diff-allowed-paths/` (Codex), `.opencode/skills/check-diff-allowed-paths/`, `.pi/skills/check-diff-allowed-paths/` and `.gemini/skills/check-diff-allowed-paths/`. Basis: specification section 6 marks the first four skill folders observed and the Gemini CLI folder documented. No harness binary was run. A host-style walkthrough (recorded in `PRECHECKS.txt`) copied the folder to `.agents/skills/check-diff-allowed-paths/` inside a copy of the probe repository, found it with the discovery command of `SKILL.md`, and ran the first action and step 3 as written: the diff run reported the deleted test, the lock file and the binary file, and the untracked run left out the skill's own files and flagged the other new files. Unverified: whether each harness gives the model the folder path for SKILL_DIR (the entry gives an `ls -d .*/skills/...` fallback), and whether a harness asks before running a pipe of `git` into `python3`.

## Customer requests

- "Make sure the overnight agent only touched the files the ticket allowed."
- "Fail the step if it deleted a test or changed the lock file."
- "Did the fix sneak in a big generated file or a binary?"

## Limits

The script trusts the diff it is given; a diff made from the wrong base hides changes, and the checklist asks about it. Generated files are found by common path patterns and by markers visible in the diff hunks; a generated file whose marker lies outside the hunks and whose path is unusual needs `--generated-glob`. Binary detection for new files uses a NUL byte in the first 8 KiB, as git does, so a text file in an unusual encoding can count as binary. Patterns have no character classes. A combined diff of a merge is refused with `combined_diff`.

Checks that failed before they passed. Earlier pass, as its own note recorded: the first design took only a diff, which lets a new untracked file outside the scope pass, so `--untracked` was added; the first mutation pass found that skipping new files already shown in the diff had no test, and one was added. This pass: the baseline check (run 1 in `PRECHECKS.txt`) refused the package because it had no `package.json`. Review found three gaps a small model would hit: `--allow src` matched only a file named `src`, so plain names now mean a file or a folder; `git status --short` lines such as ` M src/a.py` were read as file names, so they are now refused with `status_line_in_untracked_list`; and a merge diff gave an unclear hunk error, so it is now refused with `combined_diff`. The walkthrough design then showed that the untracked run would flag the skill's own files whenever a harness places the skill inside the repository; `--ignore` and the own-folder rule were added before the walkthrough ran. Each new guard was removed once in a temporary copy and its named test failed; four inherited rules were removed the same way and their tests failed too.
