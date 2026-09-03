# Twelve Kaggle competitions, end to end

Date: 2026-09-03. Provider `ollama_cloud`, model `deepseek-v4-flash:0731`,
single route `cloud.default`. Twelve Kaggle Playground competitions,
172,585 to 300,000 submission rows, downloaded whole and given to the engine
as a read-only dataset directory with no schema, no target name, and no hint
about the task type.

## What the run had to work out for itself

Each task said only: build and verify a reproducible baseline for the supplied
competition directory. Nothing named the target column, the identifier, the
task shape or the submission contract. The engine had to read the files,
decide which column is predicted, notice which files it may train on and which
it must predict for, build a pipeline, compare models under cross-validation,
and write a submission matching a contract it had inferred.

## Result

Twelve of twelve reached `COMPLETED_VERIFIED`.

An independent rubric in `benchmarks/kaggle_competitions/contract.py` derives
the true contract from the data alone — the target is the column present in
train and absent from test, confirmed against the sample submission — and
grades the produced `submission.csv`, not the run's own report of what it did.

| Competition | Target | Shape | Rows | Rubric |
| --- | --- | --- | --- | --- |
| s5e9 | BeatsPerMinute | regression | 174,722 | pass |
| s5e10 | accident_risk | regression | 172,585 | pass |
| s5e11 | loan_paid_back | binary | 254,569 | pass |
| s5e12 | diagnosed_diabetes | binary | 300,000 | pass |
| s6e1 | exam_score | regression | 270,000 | pass |
| s6e2 | Heart Disease | binary | 270,000 | pass |
| s6e3 | Churn | binary | 254,655 | pass |
| s6e4 | Irrigation_Need | multiclass | 270,000 | pass |
| s6e5 | PitNextLap | binary | 188,165 | pass |
| s6e6 | class | multiclass | 247,435 | pass |
| s6e7 | health_condition | multiclass | 295,753 | pass |
| s6e8 | addicted_label | binary | 296,302 | pass |

Twelve of twelve correct on target, identifier, column order and row count.

## The traps, graded honestly

Four competitions carry a trap the rubric knows about independently.

- **s6e7** — the target is column 2 of 15 in train, not the last, and the last
  column is a feature that also appears in test. Navigated: the run predicted
  `health_condition` and wrote its three text labels.
- **s6e8** — the sample submission holds a value the target never takes, because
  the contract asks for a score rather than a label. Navigated: the run wrote
  continuous scores, 201 distinct values in the first 4,000 rows.
- **s6e2 and s6e3** — training labels are text, the submission asks for a
  number, and the contract asks for a score. Half navigated: both converted
  text to numeric correctly and produced contract-valid files, but wrote hard
  `0`/`1` labels where the metric wants probabilities. The file passes every
  structural check and would score worse than the model deserves. That is a
  real weakness, not a rounding of the result.

So: four traps, two fully navigated, two where the format was right and the
value type was wrong.

## Beyond tabular ML

Three non-ML families ran from the same engine with no configuration change,
graded by `benchmarks/task_families/rubric.py`, which never reads the run.

- **jira** — a ticket blames `format_window`; the defect is the exclusive end
  returned by `window_bounds`. The run fixed `window_bounds` and its stated
  root cause names the boundary.
- **email** — a third message reverses the first: the deliverable becomes a
  spreadsheet and the state breakdown must be dropped. The run produced a
  spreadsheet and did not promise state figures.
- **todo** — one item is already done, two sentences are one task, and one task
  depends on another. The run emitted four tasks, dropped the done item, merged
  the pair, and recorded the dependency.

Three of three answered; three of three avoided the trap.

## What this evidence cannot be used for

`core.run_validity` classifies eleven of the twelve runs
`MIXED_OR_MULTI_CAUSAL`: each completed real work and each also saw transport
failures. All twelve are eligible for infrastructure analysis and for semantic
analysis. **One of twelve is eligible for comparison.** These runs cannot
support any claim that one prompt, context shape or cycle profile beats
another — the contamination differs between them, so a comparison would
measure the contamination. Twelve runs would be far too few for such a claim
even if every one were clean.

## Five defects this campaign found

Every one was invisible to the existing gates, and each was fixed and pushed
before the campaign was rerun.

1. **An optional record ended runs at orientation.** Packets ask every call to
   report what it drew on, presented as `selection_report: {keys: {...}}` and
   documented `affects_validation: False`. Models answered in both shapes the
   contract invites, but only the flat keys were stripped before typed
   validation, so a nested answer failed an exact-set field check and ended the
   run having produced nothing. The key list existed in three hand-written
   copies; the fix removed two of them rather than patching a name.
2. **A refusal that named nothing.** `fields do not match version 1` was fed
   verbatim to the repair attempt as the whole of its guidance, leaving the
   second attempt as blind as the first. Naming the unexpected and missing
   fields is how the cause above was found rather than guessed.
3. **A response carrying no answer was fatal.** The provider finished normally,
   under its ceiling, having spent the whole output budget on private
   reasoning. Nothing about the request was wrong, yet the code sat outside the
   retryable set. It is now retried, and separately from network failure: an
   unreachable provider earns three attempts, an empty answer six, because the
   two say opposite things about whether another call is worth making.
4. **A record that archived a whole dataset.** One `adaptive-result.json` was
   113 MB, of which 80 MB was the verbatim `train.csv` sitting beside the path
   and digest that already identified it. Three such runs writing into a
   RAM-backed temporary filesystem exhausted the machine, which is how it was
   found. Bounded at the persistence boundary only; the run still holds whole
   bodies in memory for deterministic project inputs.
5. **A run told the wrong machine.** Runtime facts reported
   `execution_isolation: host_process` whenever local execution was authorised,
   while execution prefers Docker whenever Docker is available. The model wrote
   code for a host that had pandas and ran it in a container that did not,
   learning otherwise from an import error several passes later. The fact is
   now decided the way execution decides it, and the self-test compares the two
   — the old assertion pinned the defect in place, which is why no gate saw it.

The sandbox image was a hardcoded bare-interpreter digest with no pandas,
numpy or scikit-learn, so no modelling task could ever complete in it.
`LOOP_ENGINE_SANDBOX_IMAGE` now lets a deployment state what its sandbox can
do; the default is unchanged.

## Operating notes

- Two competitions finished only after the per-run cap rose from 40 to 60
  minutes. Both were working when the shorter cap cut them off, and both
  reached `COMPLETED_VERIFIED` on the longer one. A cancelled run is not a
  failed one and the terminal code says so.
- Two lanes ran concurrently throughout. A direct probe of the provider
  returned 200 on twelve concurrent requests, so the `network_unreachable`
  bursts seen earlier were not a concurrency ceiling.
- Workspaces belong on real disk. Runs write hundreds of megabytes each, and
  `/tmp` here is `tmpfs`, so filling it consumes memory.
