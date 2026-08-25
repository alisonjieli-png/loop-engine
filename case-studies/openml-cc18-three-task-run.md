# OpenML-CC18 three-task run

Status: `completed`

## Task and population

Loop Engine trained and evaluated classifiers for three tasks from the active
OpenML-CC18 suite. The population was fixed before any score was read. The
selection ranked all 72 suite tasks by `NumberOfInstances * NumberOfFeatures`,
then by task ID, and took the first three:

| Task | Dataset | Rows | Input features | Classes |
|---:|---|---:|---:|---:|
| 11 | balance-scale | 625 | 4 | 3 |
| 10101 | blood-transfusion-service-center | 748 | 4 | 2 |
| 3560 | analcatdata_dmft | 797 | 4 | 6 |

Each task used its official stratified ten-fold split. The independent
evaluator was `sklearn.metrics.accuracy_score`. Higher accuracy is better.
Dataset and split hashes are frozen in the
[benchmark plan](../docs/benchmarks/first-loop-engine-portfolio.yaml).

## Full Loop Engine path

Each task started one Starting Practitioner in `non_deterministic` mode with the
`practitioner.reference_nine_step` profile. The Starting Practitioner
completed all nine steps.
It queried deterministic Intelligence Loops. It spawned two non-deterministic
candidate Practitioners, a non-deterministic synthesis Practitioner, a
deterministic verifier, and one repair Practitioner when the evaluator path
failed. Retrieved Code Intelligence and Connected Solution Loops performed the
selected work.

```text
Starting Practitioner
├── Queried Intelligence search Loops
├── Spawned logistic candidate Practitioner
├── Spawned random-forest candidate Practitioner
├── Spawned synthesis Practitioner
├── Retrieved Code Intelligence Loops
├── Connected Solution Loops in the Canvas
├── Spawned deterministic verifier
└── Spawned repair Practitioner when required
```

Every spawning and Spawned Loop used the same Loop runtime. Role,
relationship, mode, and
step profile remained separate properties.

## Intelligence used

Every model-led spawned Loop consumed seven distinct reviewed references:

1. first principles;
2. alternatives and analogy;
3. missing information;
4. failure and adversarial risks;
5. cost and resource discipline;
6. verification and evaluation;
7. output contract and format.

The selector queried Context Intelligence, Code Intelligence, Previous Run
and Solution Intelligence, and User Feedback Intelligence. Empty layer results stayed
visible. Benchmark-specific Code Intelligence supplied admitted callables for
data loading, official fold handling, both candidate pipelines, evaluation,
Canvas compilation, and Canvas execution. Exported portfolio records contain
references and digests, not full bodies.

## Solution Canvas

The selected method for all three tasks was a seeded random forest. Each task
compiled and executed a typed Solution Canvas across all ten official folds.
Saved Canvas JSON and Mermaid views are under the selected campaign's task
folders.

## Result

| Task | Selected method | Mean accuracy | Calls | Repair |
|---:|---|---:|---:|---|
| 11 | seeded random forest | 0.823963 | 3 | no |
| 10101 | seeded random forest | 0.754036 | 3 | no |
| 3560 | seeded random forest | 0.219636 | 4 | yes |

All three tasks produced valid prediction artifacts and valid scores, and all
three stayed in the denominator. No quality acceptance threshold was declared,
so none is labeled quality-accepted. The frozen three-task mean was 0.599212.
This average combines different classification tasks and is only a compact
summary of this exact population.

The selected run made 10 physical calls. Nine calls reported 8,766 input
tokens and 5,163 output tokens, or 13,929 known tokens. One failed HTTP 500
call did not report usage, so selected-run total tokens remain unknown. The
full packet made 12 calls including two excluded diagnostics. Its known
subtotal was 16,418 tokens, with two calls of unknown usage. Provider cost is
unknown. The selected campaign took 247.44 seconds.

Task 3560 preserved its failed synthesis call, failed intermediate execution,
and failed initial evaluation. Its authorized repair Loop selected the fixed
random-forest method and completed the task. No provider failover occurred.

## Run History and playback

The saved Run Histories contain 697, 697, and 851 events. All three hash chains
verify. Reports and playback views were regenerated from the saved Run Histories.

- [Verified result](../benchmarks/openml_cc18/verified-result.json)
- [Campaign result](../benchmarks/openml_cc18/artifacts/openml-cc18-full-20260825T1505Z/campaign-result.json)
- [Independent saved-result check](../benchmarks/openml_cc18/artifacts/openml-cc18-full-20260825T1505Z/saved-verification.json)
- [Task 11 playback](../benchmarks/openml_cc18/artifacts/openml-cc18-full-20260825T1505Z/tasks/task-11/playback.txt)
- [Task 10101 playback](../benchmarks/openml_cc18/artifacts/openml-cc18-full-20260825T1505Z/tasks/task-10101/playback.txt)
- [Task 3560 playback](../benchmarks/openml_cc18/artifacts/openml-cc18-full-20260825T1505Z/tasks/task-3560/playback.txt)

Recheck the saved files without fitting a model or making a provider call:

```bash
python3 benchmarks/openml_cc18/verify.py
```

## Limits

This is a three-task smoke population, not the complete 72-task OpenML-CC18
suite. It does not establish that the selected method is competitive with
AutoML systems, tuned baselines, or published suite results. The dataset
metadata uses the literal license label `Public`, not a precise SPDX license.
The run used one model and one provider. It does not establish a general
success rate, a cost advantage, or superiority over another harness.
