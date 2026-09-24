# Review note: Detect weakened test assertions

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a12_ticket_result_verifiers, model family anthropic. An earlier pass of the same generator wrote the first version on September 23, 2026; this pass reviewed it, rebuilt its core comparison and checked it again. The earlier bytes are kept in `packages/detect_weakened_test_assertions/earlier-attempt-20260924T0101Z.tar.gz`. This note is never delivered to a harness.

## Method

One detection method over a unified diff. The script keeps only test files (and test settings, which it scans for deselection only). It groups the lines of each side of every hunk into statements: a statement goes on while a bracket stays open, the text inside strings and comments is ignored, and in C-like files a brace that ends a line opens a block whose statements stand alone. A statement that shares unchanged lines on both sides was changed in place; statements that were only removed or only added cancel when they moved, and are otherwise paired by `difflib.SequenceMatcher` with a floor of 0.5 inside one hunk. A pair of checks is a rewrite, or a trivial check when the new one is always true; a removed check without a pair is a removal. Tolerances are compared per hunk by name and value over whole statements, including positional arguments. Parameter lists of `pytest.mark.parametrize`, `parameterized.expand` and `test.each` are counted. A new bare `return` before a check in the same block is an early exit. Test definitions are paired the same way, so a rename is told apart from a deletion, and the checks inside a deleted test are counted with it. Ten kinds are weakening (verdict `fail`), four need a stated reason (verdict `review`); both exit 1, a clean diff exits 0, and unreadable input exits 2.

## Authoring basis and sources

Original text and code, written for this wave, MIT like the repository. No outside text or code was copied. Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `src/loop_engine/core/overnight_outcome.py`: its comment records a live run that "fixed" a failing test by changing `== 11` to `== 10` and reported plain `verified`. The package's known-wrong example is that case; the script reports it as `assertion_rewritten` and exits 1.
- `examples/29_intelligence_service/starter-catalogue/bodies/prove_a_check_can_fail_when_the_behaviour_is_removed.md`: the closest prose method.

The skip, expected-failure, focus and tolerance forms of pytest, unittest, Jest, Vitest, Go testing, testify, Rust, JUnit, NUnit, xUnit and PHPUnit are written from general knowledge. The tests build most diffs with `difflib.unified_diff`, a producer independent of the parser, and `git apply --numstat --summary` parses both shipped example diffs. In this pass the script also read the diffs of 200 real commits of the repository's history, 80 of them limited to test files and 120 with `--all-files`, with no error; its findings there were plausible (conditional skips added, messages dropped from checks, tests renamed), and one false early exit it raised on a nested helper was repaired before this note.

## Inputs and outputs

Inputs: `--diff` (a path below `--root` or `-` for standard input, at most 64 MiB of UTF-8), optional `--test-glob` and `--all-files`. A combined diff of a merge is refused with `combined_diff`. Output: one JSON object with `verdict`, `weakening` and `review` lists (kind, path, old and new line numbers, old and new statement text, detail), `counts` per kind, `warnings`, the scanned files and the digest of the input.

## Effects

`reads_fs`: the script reads the named diff, refusing `..`, paths that resolve outside `--root`, non-regular files and oversized input. `spawns_process`: `SKILL.md` tells the reader to run `git diff` and `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret.

## Closest existing items

- `prove_a_check_can_fail_when_the_behaviour_is_removed` (starter, prose): proves one new check can fail. This package inspects a change for checks that were taken away or loosened.
- `honest_test_changes` (wave 5, a08, rules file): tells the model not to weaken tests while it works. This package detects weakening after the change, whether or not the rule was followed; the pair is prevent and detect.
- `isolate_a_flaky_test_before_trusting_it` (starter, prose): about tests that change result without a code change, not about edits to tests.
- `check_diff_allowed_paths` (a12) refuses deleting test files as a scope rule; this package reads inside the test files.
- A search of `scout/existing-inventory.tsv` found no executable detector of weakened tests.

## Positive example

`examples/honest-test-change.diff` fixes `src/totals.py` and adds a new test with two assertions to `tests/test_totals.py`. The verdict is pass and the source file is counted as not scanned.

## Known-wrong example

`examples/weakened-tests.diff` changes `assert order_total(rows) == 11` to `== 10` (review, lines 8 to 8), adds `@pytest.mark.skip` (new line 11), removes `assert order_total([]) == 0` (old line 14), widens `pytest.approx(1.5, rel=1e-6)` to `rel=0.5` (line 18), and deletes `test_average_of_empty_list_raises` (old line 21) with its `pytest.raises` check. The script reports all five with their lines and exits 1. The tests add the forms the first version missed: an expected value on its own line inside a multi-line check, a tolerance on its own line, a parameter case removed or turned into a comment, `assert f() == 1 or True`, a bare `return` before a check, and an `expect` line removed from inside a JavaScript callback.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/detect-weakened-test-assertions/`, `.agents/skills/detect-weakened-test-assertions/` (Codex), `.opencode/skills/detect-weakened-test-assertions/`, `.pi/skills/detect-weakened-test-assertions/` and `.gemini/skills/detect-weakened-test-assertions/`. Basis: specification section 6 marks the first four skill folders observed and the Gemini CLI folder documented. No harness binary was run. A host-style walkthrough (recorded in `PRECHECKS.txt`) copied the folder to `.opencode/skills/detect-weakened-test-assertions/` inside a fresh git repository, found it with the discovery command of `SKILL.md`, and ran the first action as written: an unchanged tree passed, and after the expected value inside a multi-line `assertEqual` changed and a skip mark was added, the script reported `assertion_rewritten` and `skip_mark_added`. Unverified: whether each harness gives the model the folder path for SKILL_DIR (the entry gives an `ls -d .*/skills/...` fallback), and whether a harness asks before running a pipe of `git` into `python3`.

## Customer requests

- "Did the agent make the tests pass by loosening them?"
- "List every assertion that was removed or skipped in last night's branch."
- "Flag any test change that looks like cheating before I merge."

## Limits

Recognition is by statement patterns, not by a parser for each language. A project helper such as `check_total()`, a case dropped from a Go table of structs or from a list defined above the test, a `return` inside an `if`, and a swallowed exception are not found; the checklist covers them. A statement whose first line lies above the diff context cannot be read; the script warns and the entry asks for `git diff -U10`, which the first action already uses. Pairing is inside one hunk, so a check rewritten far away shows as one removal plus one new check. The script cannot decide whether a rewritten expectation is right; that is why rewrites exit 1 with a `review` verdict instead of passing.

Checks that failed before they passed. Earlier pass, as its own note recorded: none of its 20 first tests failed, and a mutation pass over 17 guards killed every one. This pass: the baseline check (run 1 in `PRECHECKS.txt`) refused the package because it had no `package.json`. Probes then showed that the line-based version passed a changed expected value on its own line, a widened tolerance on its own line, a shortened expected list, a dropped parameter case, an early `return` and `assert True`; the statement grouping and three new kinds fix them. On the repository's history the first early exit rule flagged a `return None` inside a nested helper; the rule now needs the check in the same block. The first mutation run of this pass left the block guard alive, because the test had no check at the return's own depth in a later block; the test was strengthened and the mutant now fails it. Every other new guard, and two inherited ones, failed a named test when removed.
