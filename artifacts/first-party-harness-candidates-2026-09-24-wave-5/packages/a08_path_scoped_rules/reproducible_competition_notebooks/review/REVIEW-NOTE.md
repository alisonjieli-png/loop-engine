# Review note: Keep competition notebooks reproducible

Candidate only. Not approved, staged, served or published.

Identity `reproducible_competition_notebooks`, native name `reproducible-competition-notebooks`, wave 5 assignment `a08_path_scoped_rules`, file class `rules_file`, version 0.1.0. Producer: the Claude Code wave 5 generator for this assignment, model family `anthropic`. This text is the repaired version of round 2, written after the wave critic's findings of 2026-09-23. This note is for reviewers. It is never delivered to a harness.

## Method

One path-scoped rule, rendered in four native rule formats that share one identical body. The rule loads on notebooks, `notebooks/` and `experiments/` folders and `train*.py` scripts, and it applies only to notebooks and scripts that train or score a model; the body says that data exploration and web experiment code are outside it. It sets four requirements: a fixed seed, saved folds, no fitting on test rows and one ledger line per run. The seven steps:

1. Read the end of the task's experiment ledger, by default `.baltor/experiments/ledger.jsonl`, and note its line format, the fold file, `folds_sha256` and the seed.
2. Set one `SEED`, the ledger's seed, for `random`, NumPy, the model and samplers.
3. Load folds only from the saved fold file; never make new folds.
4. Fit scalers, encoders, imputers and selectors on each fold's training rows only.
5. Before the run, stage new code files by name, then note `git rev-parse HEAD` and `git diff HEAD -- '*.py' '*.ipynb' | sha256sum`.
6. After the run, complete its planned line or add one in the ledger's format. The seed stays in `config`; `commit`, `diff_sha256`, `folds_sha256`, `fold_scores` and their mean as `score` go beside `config`, never inside it. With no ledger, the model reports these facts instead.
7. Check that the fold file's `sha256sum` equals `folds_sha256` and that no added `fit` call sees test rows.

The rule tells the model to stop and report when there is no fold file or its checksum differs from the ledger, when the task or competition rules ask for fitting on test rows, when two runs with the same seed, data and code score differently, and when the ledger cannot be written. A missing ledger is no longer a stop case: the facts go into the report.

The failure it targets: an unattended model rebuilds folds with a new random split in every notebook, fits a scaler on train and test joined, and reports a better cross-validated score that nobody can reproduce and that may come from leakage or split noise.

## Authoring basis and sources

Original text written for this package from general machine learning practice. No text or code was copied from an outside project.

Repository grounding at revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract this package follows.
- `src/loop_engine/code_nodes/kaggle_executor.py`: the repository's own competition executor builds `KFold` and `StratifiedKFold` with `shuffle=True` and a fixed `random_state`, so its folds repeat.
- `benchmarks/kaggle_competitions/contract.py`: the competition contract refuses a selected target that also appears in the test file; test rows are never a source of target information.
- `tools/candidate_review/ledger.py`: an append-only JSON Lines ledger that refuses an incomplete last line. This rule borrows only its one-object-per-line shape. Correction made in round 2: the producer's note said the experiment ledger follows the same append-only idea, but step 6 completes a planned line in place, because the a06 format refuses a repeated id. The experiment ledger of this rule is therefore not append-only.

Placement basis: `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`, `/home/username/.le-codex-build/integration/docs/research/HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`, section 6 of the wave specification, and the official pages the repairer read on 2026-09-24: Claude Code's memory page (code.claude.com/docs/en/memory), Cline's rules page (docs.cline.bot/features/cline-rules), Cursor's rules page (cursor.com/docs/context/rules) and GitHub's page on repository custom instructions (docs.github.com). These were documentation reads, not observations of native loading.

## Inputs and outputs

Input: the path the harness is working on. Four patterns, the same in every variant: `**/*.ipynb`, `**/notebooks/**`, `**/experiments/**`, `**/train*.py`. Round 2 changed no pattern; it narrowed the scope in the body instead.

Output: behavior plus one ledger line per run, or the same facts in the report when there is no ledger. The rule defines no ledger format of its own. By default it follows the `experiment_ledger/v1` format of the a06 package `pick_next_experiment`: a header line, then one line per experiment with `id`, `status`, `config` and, when done, a numeric `score`. The a06 helper fingerprints `config` without the header's `ignore_keys` and refuses any configuration that already ran, failed runs included. That is why step 6 keeps the seed inside `config` (another seed is another experiment) and puts `commit`, `diff_sha256`, `folds_sha256` and `fold_scores` beside `config`: these values change from run to run without changing the experiment.

Dependencies named in `proposal.dependencies` and the purpose since round 2: a saved fold file made before the run (for example by the a02 package `build_group_stratified_folds`), the ledger format above, git and `sha256sum`.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The steps tell the model to read the ledger and the fold file, to edit notebook or script code, to stage new code files by name with `git add -- PATH`, to update or add a ledger line, and to run `tail`, `sha256sum`, `git rev-parse` and `git diff`. Staging by name follows the a14 fragment `unattended_git_rules`, which forbids `git add -A`, `git add .` and `git stash`. The package holds no code. The checker detects the shell block; the file read and write effects are declared from the text of the steps.

## Closest existing items

- Assignment table: none found. The inventory search for seed, fold, leak, notebook, experiment and ledger found:
  - `audit_data_splits_for_errors_and_leakage` (served starter): an audit of splits for errors, label noise and leakage across splits before trusting a score. It is a one-time audit method; this rule is a standing constraint on every training edit, with a ledger line and a fold checksum.
  - `read_the_train_validation_gap` (served starter): turns a training score and a cross-validated score into a named verdict. It reads scores; this rule governs how they are produced and recorded.
  - `design_a_bounded_product_experiment` (first-party): product experiments, not model training.
- Wave 5 neighbors, kept distinct as section 14 of the specification requires: `build_group_stratified_folds` (a02) builds the fold file and `verify_fold_group_separation` (a15) checks one; this rule builds no folds and sends a missing fold file to a stop report. `baseline_training_packet` (a10) is a whole training step; `rank_experiments_by_fold_scores` (a02), `pick_next_experiment` (a06) and `recompute_claimed_cv_score` (a15) read results; `target_encode_out_of_fold` (a02) is one leakage-safe encoder; `leakage_reviewer` (a05) is a reviewing helper. This rule trains, ranks and reviews nothing.
- The ledger contract across the wave is not settled, and this package cannot settle it alone. State checked in round 2 (`repair-a08_path_scoped_rules/round-2/trials/repair-trials-2-output-1.txt`): the a06 helper reads `experiment_ledger/v1` as above; the a10 step appends `experiment_record/v1` records (`run_id`, `folds.sha256`, `fold_scores`, `mean_score`) with no header line, and the a06 helper refused a ledger holding the a10 example record (exit 2, "the first ledger line must be the header"); the a02 ranker reads one record per run and fold (`run`, `fold`, `score`) and refused a ledger written as step 6 says (exit 2, `ledger_field_missing`), while a one-line conversion of `fold_scores` into one record per fold let it rank the runs (exit 0); the a15 recomputation reads out-of-fold prediction files, not the ledger. This rule follows a06 by default. The integrator must choose one ledger contract, or a documented conversion, before these packages work together.
- Outside staged rules: none of the 445 rule titles concerns seeds, folds or experiment ledgers.
- Duplicate check after round 2: the highest five-word shingle similarity of this package's model-facing text with the 225 first-party bodies and the other 74 wave 5 packages is 0.003 (with `generated_files_stay_unedited`). The checker warns at 0.5 and refuses at 0.8.

## Positive example

Repairer trials, round 2, in a Bubblewrap sandbox with no network, with the a06 helper `experiment_ledger.py` (sha256 `7d2b3f7b...`) bound read-only (`repair-a08_path_scoped_rules/round-2/trials/repair-trials-output-1.txt` in the wave folder):

- N-pos: the ledger holds the a06 header, `E-001` done and `E-002` failed (out of memory), each with the seed in `config` and `commit`, `diff_sha256` and `folds_sha256` beside it. The first action printed the lines; `summary` exited 0 and named `E-001` best. A proposal that repeats `E-001` was refused (exit 1, "already ran or is listed as E-001"). A proposal that copies the best `config` and changes one key, which repeats the failed `E-002` (the critic's case N3), was refused as well (exit 1, "E-002 (status failed)").
- N-code: in a git repository a new notebook was missing from `git diff HEAD -- '*.py' '*.ipynb'` until it was staged by name; after that the hash covered it. A changed tracked ledger left the code hash unchanged. After the single commit of the a14 flow, `git diff START HEAD` over the same paths gave the recorded hash again, so the run's code can be confirmed later from the commit.

## Known-wrong example

- N-kw, the critic's case N1 and N3 as the predecessor's step 5 said: with the commit and the fold checksum inside `config`, the same proposal that repeats the failed `E-002` was appended (exit 0, `"appended": true`). The repaired placement is the only difference between this case and N-pos.
- N-folds: the fold file was rebuilt with seed 123 inside a notebook. Its `sha256sum` differed from the recorded `folds_sha256`, so the first stop case applies instead of comparing scores across different splits.
- The producer's round kept a third case: the line `scaler.fit(pd.concat([train_x, test_x]))`, which step 4 forbids and step 7 asks the model to find among the added `fit` calls.
- N-noledger, the critic's case N2: in a project without a ledger the first action fails (`tail` exit 1). The predecessor then stopped for every matched notebook. The repaired rule goes on and reports the facts, and the scope sentence keeps exploration notebooks out.

## Harness placement and verification state

| Harness | Destination | Activation front matter | Basis |
|---|---|---|---|
| Claude Code | `.claude/rules/reproducible-competition-notebooks.md` | `paths` list | documented: research file, and the official memory page read on 2026-09-24 |
| Cline | `.clinerules/reproducible-competition-notebooks.md` | `paths` list | documented: research file, and the official rules page read on 2026-09-24 |
| Cursor | `.cursor/rules/reproducible-competition-notebooks.mdc` | `description`, `globs`, `alwaysApply: false` | documented: official rules page read on 2026-09-24; kept in `unverified_targets` |
| Copilot | `.github/instructions/reproducible-competition-notebooks.instructions.md` | `applyTo` | documented: official GitHub page read on 2026-09-24; kept in `unverified_targets` |

The licence goes to `.baltor/reproducible-competition-notebooks/LICENSE` for every harness. `wave5.unverified_targets` keeps Cursor and Copilot, now with reasons that cite the official pages and say what stays unverified.

Unverified harness behaviors:

1. Native loading was not observed for any of the four harnesses. No harness binary was run.
2. Cursor's documented example puts a space after each comma in `globs`; this package writes none. How Cursor splits the value was not tested.
3. On GitHub.com, only Copilot cloud agent and Copilot code review read path-specific instruction files, according to GitHub's page.
4. When each harness loads a rule, and whether a notebook edited through a notebook-specific tool counts as reading or editing the `.ipynb` path.
5. Whether a leading `**/` matches zero folders in each harness's glob engine. Python 3.14 `PurePath.full_match` matched all 6 intended sample paths and kept all 4 unrelated paths out.

## Customer requests

- "Make the Kaggle agent log every experiment with its seed, folds and CV scores so I can check them in the morning."
- "Stop my notebook agent from fitting the scaler on the test data."
- "I need a Cursor rule for competition notebooks: fixed seeds, saved folds, no leakage."

## Limits

- The rule is guidance, not a leakage detector. Step 7 is the model's own reading of each `fit` call; a dedicated reviewer or verifier is stronger.
- Some competitions allow unsupervised use of unlabeled test rows. The rule does not decide that case; it sends it to a stop report.
- Hardware nondeterminism (for example some GPU kernels) can make identical seeds give different scores; the rule reports that instead of hiding it.
- The patterns still match every notebook and every `experiments/` folder; only the scope sentence keeps exploration and web experiment code out, so the rule text is loaded there.
- The code hash covers Python and notebook files only. Other code, such as R, SQL or configuration files, and new files that were not staged, are outside it. A notebook's saved outputs are part of its bytes, so a rerun that only changes outputs changes the hash. A folder without git cannot run step 5; the model then has no commit to report.
- A saved fold file must exist before the run. The rule builds none and stops without one.
- A permission fragment that allows only a few commands, such as the a13 data step settings, refuses `tail`, `sha256sum` and `git`; the step then stops and reports.

### Pre-check and review history

- Producer round: the first draft held 283 words, over the 250-word limit, and was tightened in three passes; after checker run 1 had passed, the ledger alignment with a06 changed steps 1 and 5. Checker runs 1 to 3 passed the wave gate with one warning: `reads_fs` and `writes_fs` are declared from the text of the steps and are not found in code.
- Critic round (2026-09-23, recommendation repair): (1) the commit and the fold checksum inside `config` disabled the a06 refusal of repeated configurations, failed runs included; (2) the rule depended on an existing ledger and fold file without saying so, and stopped for every matched notebook in a project without a ledger; (3) a commit alone does not identify code run from uncommitted changes; (4) the ledger contract is not settled across the wave; (5) the note's append-only claim was wrong; (6) the patterns over-trigger.
- Repair round 2 (2026-09-24): step 6 places `commit`, `diff_sha256` and `folds_sha256` beside `config` (finding 1); the purpose and the dependencies name the fold file and the ledger, and a missing ledger now leads to a report instead of a stop (finding 2); step 5 records the commit and a hash of the code diff after staging new code files by name (finding 3); the ledger state across the wave is recorded above for the integrator (finding 4); the append-only claim is corrected (finding 5); the scope sentence says what is outside the rule (finding 6). The first round 2 draft held 288 words; it was tightened to 250 without removing a requirement or a stop case. Every checker run of both rounds is listed in `review/PRECHECKS.txt`, and every report is kept as a `precheck-*.json` file beside this note.
