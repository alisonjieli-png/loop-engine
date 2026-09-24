# Review note: Keep test changes honest

Candidate only. Not approved, staged, served or published.

Identity `honest_test_changes`, native name `honest-test-changes`, wave 5 assignment `a08_path_scoped_rules`, file class `rules_file`, version 0.1.0. Producer: the Claude Code wave 5 generator for this assignment, model family `anthropic`. This text is the repaired version of round 2, written after the wave critic's findings of 2026-09-23. This note is for reviewers. It is never delivered to a harness.

## Method

One path-scoped rule, rendered in four native rule formats that share one identical body. The rule loads when the harness works on test files, test folders, snapshots or test settings. Its core instruction: repair the code, not the test, and never weaken, skip, exclude or delete a test to pass a check. A new test must fail before the fix and pass after it. The five steps:

1. Run the test file the step will change with the project's test command and keep the summary line. This line is the baseline for the check. If nothing fails, for example while writing tests for new behavior, go to step 3.
2. Decide whether the code or the test is wrong. Change a test only when the task or a specification says the expected behavior changed, and quote that line.
3. Write a test for the defect or the new behavior and see it fail for the expected reason.
4. Repair the code until the new and the old tests pass.
5. Check, in two parts: rerun step 1 and compare the summary lines, and read `git diff` of every changed test file and test setting, including the test sections of `pyproject.toml`, `setup.cfg`, `tox.ini` and `package.json`. Without a step 2 quote, passed plus failed must not fall, the skipped, deselected and expected-failure counts must not rise, and the diff must not drop or loosen an assertion, or add a skip or expected-failure marker, an exclusion, a `try` around a checked call or a snapshot change.

The count comparison catches the moves that change what runs (a skip or expected-failure marker, a deselection in settings, a deleted test). The diff reading catches the moves that keep the counts (a loosened assertion, a caught error, a regenerated snapshot) and every exclusion written in settings. The step 2 quote exempts both parts, so a task that removes a feature together with its tests can still finish; without a quote, neither part may show a weakening.

The rule tells the model to stop and report when the test contradicts the task or the documentation, when the failure comes from the environment, the network or timing, and when the new test cannot be made to fail before the fix.

## Authoring basis and sources

Original text written for this package from general testing practice. No text or code was copied from an outside project.

Repository grounding at revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract this package follows.
- `src/loop_engine/core/independent_failure_review.py`: the repository decides whether the work, the check or the environment is wrong before any repair, and a revised check must still fail on a known-wrong subject; otherwise the original failure stands.
- `AGENTS.md`: the repository's working cycle says to write the check for the known-wrong case before the repair and never to weaken a check to make it pass.
- `examples/29_intelligence_service/starter-catalogue/bodies/review_a_failed_check_before_repairing_the_work.md`, `prove_a_check_can_fail_when_the_behaviour_is_removed.md` and, added in round 2, `test_driven_change_red_green_refactor.md`: the three closest items (see below).

Placement basis: `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`, `/home/username/.le-codex-build/integration/docs/research/HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`, section 6 of the wave specification, and the official pages the repairer read on 2026-09-24: Claude Code's memory page (code.claude.com/docs/en/memory), Cline's rules page (docs.cline.bot/features/cline-rules), Cursor's rules page (cursor.com/docs/context/rules) and GitHub's page on repository custom instructions (docs.github.com). These were documentation reads, not observations of native loading.

## Inputs and outputs

Input: the path the harness is working on. Fourteen patterns, the same in every variant: `**/tests/**`, `**/test/**`, `**/__tests__/**`, `**/spec/**`, `**/test_*.py`, `**/*_test.*`, `**/*.test.*`, `**/*.spec.*`, `**/conftest.py`, `**/pytest.ini`, `**/jest.config.*`, `**/vitest.config.*`, `**/__snapshots__/**`, `**/*.snap`. Round 2 changed no pattern. Settings files such as `pyproject.toml` are not patterns, because they also hold unrelated settings; the rule reaches them through the step 5 diff reading once it is loaded.

Output: behavior. A step that follows the rule produces a code repair plus a new test that failed first, two summary lines that show no weakening, or a stop report with the failure text and the reason.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The steps tell the model to run the project's test command (the example is `python3 -m pytest` on one test file), to write a test and repair code, and to run `git diff`. The package holds no code. The checker detects the shell block; the file read and write effects are declared from the text of the steps.

## Closest existing items

- `test_driven_change_red_green_refactor` (served starter item; the critic named it as missing from the producer's note): an on-demand method for implementing one bounded requirement. It proves the requirement is not met with a failing test, makes the smallest change, refactors while the test stays green, runs the full suites and records the evidence. Overlap: the red test before the change, which this rule's step 3 also requires. Difference: this package is not a whole-task method. It is a short path-scoped rule that loads whenever a test file is read or edited, in any step, and its content is what the served item does not cover: the concrete ways a model hides a failure (skip and expected-failure markers, deselection or exclusion in settings, a caught error, a regenerated snapshot) and a mechanical check that compares the runner's counts before and after.
- `review_a_failed_check_before_repairing_the_work` (starter, named in the assignment): a longer on-demand method that classifies a failed check into four explanations, says never to delete a case, lower a threshold or skip a test, and requires a changed check to fail on a known wrong version. Overlap: the prohibition on weakening and the decision in step 2. Difference: this rule adds the settings, snapshot and caught-error cases, the count comparison and the diff reading, and loads by path instead of on request.
- Together these two items cover most of the principle. A reviewer who judges the path-scoped delivery, the named concealment moves and the count check to be too small a difference may reject this package as a variant; the producer and the repairer judged the difference enough, because a small model loads this rule exactly when it touches a test and gets one mechanical check instead of a method to recall.
- `prove_a_check_can_fail_when_the_behaviour_is_removed` (starter, named in the assignment): proves a new check can fail by removing the behavior it guards, for one run. Difference: this rule does not remove behavior; it requires a new test to fail against the unrepaired code, which is the natural failing state of a bug fix.
- `repair_one_failing_test` (format pilot 1): a placeholder step template for repairing one known failure within a declared scope. It is a whole step brief; this rule is a standing constraint on any edit of a test file in any step.
- `reconcile_snapshot_changes` (wave 1): compares data exports; it is unrelated to test snapshots despite the name.
- Wave 5 neighbors, kept distinct as section 14 of the specification requires: `detect_weakened_test_assertions` (a12) scans a finished diff and reports removed assertions, skip marks and widened tolerances; this rule prevents them inside the step and detects nothing by itself. `ticket_reproduction_packet` (a09) is a whole step that turns a ticket into one failing test.
- Outside staged rules: test framework conventions (Jest, Vitest, Playwright, Cypress, JUnit assertions, Pester) by title; none of those titles concerns keeping a failing test intact.
- Duplicate check after round 2: the highest five-word shingle similarity of this package's model-facing text with the 225 first-party bodies and the other 74 wave 5 packages is 0.005 (with `applied_migrations_stay_unchanged`). The checker warns at 0.5 and refuses at 0.8.

## Positive example

Repairer trial H-pos, round 2, in a Bubblewrap sandbox with no network and pytest 9.1.1 bound read-only (`repair-a08_path_scoped_rules/round-2/trials/repair-trials-output-1.txt` in the wave folder). `calc.add` subtracts instead of adding. Step 1 printed `1 failed, 1 passed`. The new test `test_add_negative` failed first (`2 failed, 1 passed`), the code was repaired, and step 5 printed `3 passed`: passed plus failed rose from 2 to 3, and the skipped, deselected and expected-failure counts stayed 0. The test diff removed no line. A second run with no failing test printed `2 passed` in step 1, so the step went to step 3, as the repaired first action says.

## Known-wrong example

Each case starts from the same `1 failed, 1 passed` baseline:

- H-kw1, the critic's case H1: `addopts = "--deselect tests/test_calc.py::test_add"` added to `pyproject.toml`. pytest printed `1 passed, 1 deselected` and exited 0. The predecessor's check read only changed test files and passed. The repaired count comparison fails (passed plus failed fell, deselected rose), and the diff reading shows the added setting.
- H-kw2 and H-kw3: a skip marker and an expected-failure marker on the failing test. The counts show `1 skipped` and `1 xfailed`, so the comparison fails.
- H-kw4: the assertion loosened to `assert add(2, 2) is not None`. The counts stay `2 passed`, so only the diff reading catches it: the removed assertion has no equal or stricter replacement.
- H-kw5: the checked call wrapped in `try` and `except AssertionError: pass`. The counts stay `2 passed`; the diff reading shows the added `try`.
- H-kw6: `addopts = "--ignore=tests/test_calc.py"`. With the file named on the command line, pytest still ran it (`1 failed, 1 passed`), so the count comparison passed, while the whole suite printed `no tests ran`. Only the diff reading of `pyproject.toml` catches this exclusion. This is why step 5 has two parts.

## Harness placement and verification state

| Harness | Destination | Activation front matter | Basis |
|---|---|---|---|
| Claude Code | `.claude/rules/honest-test-changes.md` | `paths` list | documented: research file, and the official memory page read on 2026-09-24 |
| Cline | `.clinerules/honest-test-changes.md` | `paths` list | documented: research file, and the official rules page read on 2026-09-24 |
| Cursor | `.cursor/rules/honest-test-changes.mdc` | `description`, `globs`, `alwaysApply: false` | documented: official rules page read on 2026-09-24; kept in `unverified_targets` |
| Copilot | `.github/instructions/honest-test-changes.instructions.md` | `applyTo` | documented: official GitHub page read on 2026-09-24; kept in `unverified_targets` |

The licence goes to `.baltor/honest-test-changes/LICENSE` for every harness. `wave5.unverified_targets` keeps Cursor and Copilot, now with reasons that cite the official pages and say what stays unverified.

Unverified harness behaviors:

1. Native loading was not observed for any of the four harnesses. No harness binary was run.
2. Cursor's documented example puts a space after each comma in `globs`; this package writes none. How Cursor splits the value was not tested.
3. On GitHub.com, only Copilot cloud agent and Copilot code review read path-specific instruction files, according to GitHub's page.
4. When each harness loads a rule. A model that only runs the test command and edits `pyproject.toml` without reading a test file may never load the rule.
5. Whether a leading `**/` matches zero folders in each harness's glob engine. Python 3.14 `PurePath.full_match` matched all 14 intended sample paths and kept all 5 unrelated paths out (for example `src/contest.py` and `src/attest.py`).

## Customer requests

- "The agent made CI green by skipping the failing tests. Never let it do that again."
- "Rule for Copilot: when a test fails, fix the code, and write a failing test first for every bug."
- "Don't let Claude regenerate snapshots or deselect tests in pyproject.toml just to make the build pass."

## Limits

- The rule is guidance, not enforcement. The a12 detector or a review is the check after the fact.
- Step 2 depends on the model's judgment of whether the test is wrong; the rule narrows it by requiring a quoted line from the task or a specification.
- The count comparison covers only what the step 1 command runs. An exclusion that the named file bypasses, such as `--ignore` in H-kw6, is caught only by the diff reading.
- The summary words differ between runners; the rule names the counts in pytest's terms (passed, failed, skipped, deselected, expected failure), and the model must map another runner's words to them.
- `**/spec/**` also matches folders of API specifications that are not tests; the rule would load there without harm but without use.
- The step 1 example command is for Python projects; other projects use their own runner, as the step says.

### Pre-check and review history

- Producer round: the first draft held 271 words, over the 250-word limit, and was tightened in three passes; checker runs 1 to 3 passed the wave gate with one warning: `reads_fs` and `writes_fs` are declared from the text of the steps and are not found in code.
- Critic round (2026-09-23, recommendation repair): (1) the check missed an exclusion written in a settings file outside the 14 patterns, such as `--deselect` in `pyproject.toml`; (2) the written check covered only removed assertions; (3) the note did not name the served `test_driven_change_red_green_refactor`; (4) the first action assumed a failing test.
- Repair round 2 (2026-09-24): step 5 compares the runner's counts and reads the diff of every changed test file and test setting (finding 1); the check names skip and expected-failure markers, exclusions, a `try` around a checked call and snapshot changes (finding 2); the closest items above name both neighbors with the difference (finding 3); step 1 always records the baseline and sends a step with no failing test to step 3 (finding 4). While repairing, the repairer found that jumping to step 3 would have skipped the baseline the check needs, so step 1 now always runs. The first round 2 draft held 303 words; it was tightened to 250 without removing a step, a check or a stop case. After the first round 2 check run had passed, the repairer found a second gap in its own draft: the step 2 quote exempted only the diff reading, so a task that removes a feature and its tests could never pass the count comparison. Step 5 now puts both parts under the quote, and the package was filled and checked again; the earlier report is kept. Every checker run of both rounds is listed in `review/PRECHECKS.txt`, and every report is kept as a `precheck-*.json` file beside this note.
