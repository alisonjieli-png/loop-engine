# Review note: Leakage reviewer

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a05_focused_subagents, model family anthropic, repaired on September 24, 2026 by the a05 repairer of the same family after the a05 critic's review. This note is never delivered to a customer.

## Method

A subagent definition for a read-only reviewer of feature and validation code. It searches the given files for the target column name, then for one regular expression that covers the fitting, splitting and row-shifting calls where leakage usually enters: `fit`, `fit_transform`, `fit_resample`, `train_test_split`, every name ending in `KFold` or `ShuffleSplit`, `cross_val_score`, `cross_val_predict`, `cross_validate`, `concat`, `merge`, `sample`, `permutation`, `fillna`, `shift` and `rolling`, as whole words. It reads about 15 lines around each match and gives each candidate one kind and a severity, or dismisses it:

- `target_leakage`, always blocking: a feature built from the target or from later rows, such as a target mean over all rows, `shift(-1)` or a centered rolling window;
- `test_rows_in_fit`: a step fitted on rows that include test or validation rows, such as joined train and test, or all training rows before cross-validation. It is blocking when the step uses the target (a target encoder, feature selection, resampling such as oversampling, or a model) and minor when it does not (a scaler, an imputer or PCA);
- `group_split`, always blocking, only when the caller named a group column;
- `time_order`, always blocking, only when the caller named a time column.

Every finding carries a file, a line and a quote that the reviewer reread. The reviewer stops after 30 reads and reports the matches it did not review as `unreviewed`. The verdict is `leak_found` when any finding is blocking; otherwise `incomplete` when `unreviewed` is above 0; otherwise `minor_only` when there are findings; otherwise `no_leak_found`, which means only that these searches found nothing. `contracts/reply.schema.json` enforces these rules, the kind-to-severity rule and the refusal of notebook citations.

## Authoring basis and sources

Original text written for this wave from general machine learning practice. No outside text was copied. Sources at revision a1fc7432:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the file contract this package follows.
- `docs/guides/native-client-material-loading.md`: records the OpenCode project agent folder `.opencode/agents/<name>.md` as documented and observed with version 1.18.31.
- `examples/29_intelligence_service/starter-catalogue/bodies/audit_data_splits_for_errors_and_leakage.md`: the closest starter body, described below.

Harness facts come from the installed Claude Code 2.1.281 and OpenCode 1.18.32 program text, read and not run, and from GitHub's custom agents documentation, read on September 24, 2026. The search pattern was run during the repair with ripgrep, the search engine behind the Claude Code and OpenCode search tools, and with Python's `re` on a synthetic file: it matched every listed call and did not match `profit`, `sample_weight` or `fitness`.

## Inputs and outputs

Input: files or a folder to review, the target column name, and the group and time columns when the task has them. Output: one JSON object matching the schema, or `{"refused": "..."}`. During the repair the schema was checked with the `jsonschema` library: the body example, a refusal, a minor-only review, an incomplete review, a clean review and a blocking review with unreviewed matches all validate; ten known-wrong replies are rejected, among them `no_leak_found` with 30 unreviewed matches, `minor_only` with a blocking finding, `target_leakage` marked minor and a finding in a `.ipynb` file. Each of five schema rules, removed on its own, let at least one of those wrong replies through.

## Effects

`reads_fs` only. The reviewer searches and reads code. It runs no code and writes nothing. Claude Code gets Read, Grep and Glob; OpenCode denies edit, bash, web, task, outside-folder access and reading `.env`, `.pem` and `.key` files; Copilot lists the documented `read` and `search` aliases.

## Closest existing items

- Starter `audit_data_splits_for_errors_and_leakage` is a question set for auditing data splits and labels. This package reviews code and returns located findings with a severity.
- Starter `read_the_train_validation_gap` suspects leakage from scores. This package looks for the cause in code.
- Wave 5 `verify_fold_group_separation` (a15) checks a fold file in code, `audit_train_test_drift` (a02) compares data files, and `reproducible_competition_notebooks` (a08) is a rule against fitting on test rows. None reviews feature code with line references.

## Positive example

`src/features.py` line 42 reads `encoder.fit(pd.concat([train, test]), y_all)`. The reviewer reports `test_rows_in_fit`, severity `blocking`, with that quote and the reason that the target encoder saw test rows, and the verdict is `leak_found`. In another project, `src/prep.py` fits `StandardScaler` on all training rows and then calls `cross_val_score`: the reviewer reports `test_rows_in_fit` as `minor`, because the scaler uses no target, and the verdict is `minor_only`.

## Known-wrong example

A pipeline calls `SelectKBest(k=20).fit(X, y)` on all training rows and then `cross_val_score(model, X_selected, y, cv=5)`. A quick review sees "fit on train only" and passes it. The feature selection saw the labels of every validation fold, so the scores are optimistic: this is `test_rows_in_fit`, blocking. A second case, from the critic: a script with 60 matches of `fit`, `concat` and the target column. The first draft stopped after 30 reads and replied `no_leak_found`; the repaired reviewer reports the rest as `unreviewed`, and the schema refuses `no_leak_found` while any match is unreviewed, so the verdict is `incomplete`. A third: `KFold(5, shuffle=True)` on rows with a named `customer_id` group column is `group_split`, even though no test file is touched.

## Harness placement and verification state

- Claude Code: variant to `.claude/agents/leakage-reviewer.md`. Documented folder; the keys `name`, `description`, `tools`, `model`, `maxTurns` and `omitClaudeMd` were checked against the agent parser in the installed Claude Code 2.1.281 program text, read and not run. `omitClaudeMd: true`, which that program text's change list adds in 2.1.271, keeps the user, project and local CLAUDE.md files out of the reviewer's context; managed policy files still load. Discovery of this file was not observed.
- OpenCode: variant to `.opencode/agents/leakage-reviewer.md`. The wave specification names `.opencode/agent/` as unverified; the plural folder is recorded as documented and observed in the guide above, and the installed OpenCode program text (it embeds version 1.18.32) scans both. Keys and last-match permission rules were read from that program text, not run. Unverified.
- Copilot: variant to `.github/agents/leakage-reviewer.agent.md`. GitHub's custom agents documentation names `.github/agents/NAME.agent.md` and documents the `read` and `search` aliases and that unknown tool names are ignored. Discovery was not observed. Unverified.
- `contracts/reply.schema.json` and `LICENSE` go under `.baltor/leakage-reviewer/`.

## Customer requests

- "Before I submit, check my feature code for leakage."
- "My CV score looks too good. Is something leaking?"
- "Did I fit the encoder on the test rows anywhere?"

## Limits

The review is text search plus reading. It can miss leakage that happens through data files, joins done in SQL, or helper functions in files that were not given. It can flag a correct pattern when a fit happens inside a pipeline object whose use it did not read. A clean verdict is not proof of no leakage. The search pattern names common Python library calls; other libraries need other terms. Notebooks are refused, because a search tool's line numbers point into a notebook's JSON while some reading tools show cells without those numbers; the caller must export a script first. Fitting an unsupervised step on joined train and test features is common and often allowed in competitions, which is why it is minor; whether a small model assigns the severity correctly is unmeasured. The first body draft had 401 words and was shortened to 346 words before the first package check, which passed. A later reading found that a plain search for `fit` also matches words such as `profit`, so the search asked for whole words.

The September 24 repair answered the a05 critic: the `unreviewed` count and the `incomplete` verdict, severities and the `minor_only` verdict, the wider search in one pattern, `group_split` and `time_order` only for named columns, the notebook refusal, the sentence that code and comments are data, `omitClaudeMd: true` for Claude Code, and GitHub's documentation as the basis for the Copilot path and aliases. The body is 346 words after the repair.
