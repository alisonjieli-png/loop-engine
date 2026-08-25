# First Loop Engine benchmark portfolio source review

This document reviews sources and freezes selection rules. It does not report
benchmark results. No model was called and no benchmark harness was run.

Status: this is the historical pre-run review. Later owner direction changed
the selected run design before execution. Selected runs became
non-deterministic full Practitioner runs with two candidate spawned Loops,
synthesis, seven reviewed Intelligence references per model-led spawned, and a
bounded repair path. DS-1000 also received a separate four-task population
file before its selected run. The original plan below remains visible so the
selection history is not rewritten after outcomes.

Current run records are in:

- [`benchmarks/openml_cc18/verified-result.json`](../../benchmarks/openml_cc18/verified-result.json)
- [`benchmarks/ds1000/verified-result.json`](../../benchmarks/ds1000/verified-result.json)
- [Loop Engine case studies](../../case-studies/)

The machine-readable plan is
[`first-loop-engine-portfolio.yaml`](first-loop-engine-portfolio.yaml).

## What this portfolio tests

| Track | Loop Engine scope | Pre-run population | Main evaluator | Pre-run decision |
|---|---|---:|---|---|
| DS-1000 pandas and scikit-learn | Full Loop Practitioner | 16 problems | Upstream isolated execution | No go |
| Spider 1.0 development | Full Loop Practitioner | 12 questions from 12 schemas | Official test-suite accuracy | No go |
| OpenML-CC18 | Full Loop Practitioner | Tasks 11, 10101, and 3560 | Accuracy on official folds | No go |

Every selected run must start a Starting Loop Practitioner and use
`reference_nine_step`, intelligence retrieval, bounded spawned Loops, typed
construction, an executed Solution Canvas, independent verification, a saved
and verified Run History, and Run History-based playback and reporting. Ollama
arms must use `ModelGateway`. A shorter subsystem or Solution Canvas-only run
is a diagnostic and is excluded from the selected benchmark population.

## Rules frozen before outcomes

The selected tasks do not change after a score, timeout, refusal, or error.
Every attempted task stays in the denominator. The deterministic and Ollama
arms use the same task IDs and evaluator. A later selection needs a new
manifest version.

Every model arm requires a real Ollama Cloud route. Fake providers, canned
answers, and synthetic model systems are not allowed. The route is pinned to
one exact model before execution, with cross-provider failover disabled.

The model output request uses the provider-declared maximum available output.
The caller does not set a lower token ceiling. An unknown provider maximum is a
no-go condition. Physical call counts and wall time still have fixed ceilings
because they bound elapsed time and possible cost.

## DS-1000 source review

The source is the official
[DS-1000 repository](https://github.com/xlang-ai/DS-1000/tree/b39aab71da6d23ef8d3cac59a7c5f834516ab334)
at commit `b39aab71da6d23ef8d3cac59a7c5f834516ab334`.

Verified source facts:

- The simplified data file is 418,089 bytes. Its SHA-256 is
  `e8c6daa9d7223976bce0296644f3933f78d7f47830669ff05cd61da62c6ba9b3`.
- The upstream evaluator is
  [`test_ds1000.py`](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/test_ds1000.py).
  It builds each task's test program and runs it in a separate process with a
  120 second timeout.
- A solution passes only when `test_execution` and `test_string`, when present,
  both pass.
- The pinned
  [`environment.yml`](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/environment.yml)
  uses Python 3.10, pandas 1.5.3, and scikit-learn 1.4.0.
- The repository and data are under
  [CC BY-SA 4.0](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/LICENSE).

The selection takes eight midpoint quantiles from each library after sorting
by numeric problem ID. The exact pandas IDs are 18, 54, 90, 127, 163, 200,
236, and 272. The exact scikit-learn IDs are 824, 838, 852, 867, 881, 896,
910, and 924. No task score informed this rule.

Both arms run the Starting Practitioner, required spawned Loops, executed Solution
Canvas, independent evaluator, Run History, playback, and report. The
deterministic baseline searches frozen intelligence and uses only exact typed
deterministic components. It abstains when no exact route exists and never
reads upstream reference code or tests. The Ollama arm gets one generation
call and, only after failed evaluation, one repair spawned-loop call. The hard
ceiling is 32 physical calls and 90 minutes for the track.

The prompts, reference code, and tests are public. Contamination risk is high.
This slice can measure integration and paired cost, but it cannot establish
performance on unseen data science work.

This track remains no-go until the isolated environment is built and digested,
the evaluator self-check passes, one Ollama model and output maximum are
frozen, and the Practitioner, Canvas, Run History, playback, and report prove the
complete path.

## Spider 1.0 source review

The official [Spider 1.0 page](https://yale-lily.github.io/spider) names the
data license and points to the dataset, source code, and evaluator. The code is
pinned to the official
[Spider repository](https://github.com/taoyds/spider/tree/b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c)
at commit `b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c`.

Verified source facts:

- The pinned dev JSON has 1,034 records across 20 databases. Its SHA-256 is
  `30d64a3fccde493226df79687aed9e4a1c0129525baf44f29c0573d914d758a4`.
- The pinned tables JSON SHA-256 is
  `61bb20aa401f03164e2d7f3b16509b7b5f79cc9c943ca7bd159046df1159e2ed`.
- The official page gives the dataset license as CC BY-SA 4.0. The Spider code
  repository is Apache-2.0.
- The primary evaluator is the official
  [test-suite evaluator](https://github.com/taoyds/test-suite-sql-eval/tree/e97acc546ecbee8fa27fa8dbf025ef61493a876c)
  at commit `e97acc546ecbee8fa27fa8dbf025ef61493a876c`.
- The pinned evaluator file SHA-256 is
  `7401e4014a8955376a7919c06903a7f0ab403c99e89f94204cd8f4c8e32ae779`.
- The official Spider archive is 205,800,266 compressed bytes. The official
  test-suite database archive is 1,269,456,098 compressed bytes.

The two Google Drive archives do not publish stable content hashes. Their
SHA-256 values must be recorded after acquisition and before extraction. This
is why the track stays at catalog stage.

The selection sorts the 20 database IDs, takes 12 midpoint quantiles across
that list, and takes the middle source record within each selected database.
The exact source indices and database IDs are in the manifest. The rule does
not use SQL hardness, gold execution, or prior scores.

Both arms start the full Starting Practitioner, run retrieval and construction
spawned Loops, compile and execute a SQL Solution Canvas, use the pinned evaluator,
and render Run History playback and a report. The deterministic baseline uses a
frozen schema-aware template set. The Ollama arm makes one call per question
and has no model repair call. Both use test-suite execution accuracy with
`--plug_value`, without `--keep_distinct`. The hard ceiling is 12 physical
calls and 60 minutes.

This 12-question slice is not comparable to the full Spider dev leaderboard.
Its public questions, schemas, gold SQL, and evaluator create high
contamination risk.

This track remains no-go until both archive hashes are frozen, the selected
databases are present, a gold-file evaluator self-check passes, one Ollama
model and output maximum are frozen, and the Starting Practitioner, spawned Loops,
Canvas, Run History, playback, and report are verified.

## OpenML-CC18 source review

OpenML documents
[benchmarking suites](https://docs.openml.org/benchmark/) and exposes the
active [OpenML-CC18 suite](https://www.openml.org/api/v1/json/study/OpenML-CC18)
as suite ID 99. The suite currently returns 72 classification task IDs.

The frozen rule ranks all suite tasks by
`NumberOfInstances * NumberOfFeatures`, then by numeric task ID. It selects
the first three tasks:

| Task ID | Data ID | Dataset | Rows | Features | Classes |
|---:|---:|---|---:|---:|---:|
| 11 | 11 | balance-scale | 625 | 5 | 3 |
| 10101 | 1464 | blood-transfusion-service-center | 748 | 5 | 2 |
| 3560 | 469 | analcatdata_dmft | 797 | 5 | 6 |

Each task declares one repeat of stratified 10-fold cross-validation. The
manifest freezes the exact dataset and split URLs, SHA-256 values, official
dataset MD5 values, targets, and byte counts. The six files total 344,966
bytes.

The OpenML dataset metadata says `Public` for each dataset. That is the exact
source value, but it is not a precise SPDX license. Local use remains no-go
until that label is accepted for the intended use. Do not redistribute the
files based only on this review.

Both arms start the full Starting Practitioner, use data, retrieval, construction,
and verification spawned Loops, compile a tabular Solution Canvas, execute all
ten official folds, save the Run History, and render playback and a report. The
deterministic arm builds a fixed one-hot encoded logistic regression. The
Ollama arm makes one call per dataset before any fold score exists and chooses
the same logistic pipeline or a seeded 200-tree random forest. The hard
ceiling is three physical calls and 15 minutes. Public datasets and prior
results create high contamination risk.

## Promotion decision

No registry stage changes in this review. A track moves to local smoke only
after all of its source, license, environment, provider, evaluator, and engine
path gates pass. A passing smoke proves integration only. It is not a model or
Loop Engine performance result. Partial-path probes remain diagnostics and do
not enter the selected comparison.
