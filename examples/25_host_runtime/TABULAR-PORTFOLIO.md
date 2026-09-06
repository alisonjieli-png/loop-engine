# Compare model solutions on public datasets

This example lets Loop Engine select model configurations and run actual
training through a host-owned capability. It uses the same embedding boundary
as the JavaScript repair example. Dataset names do not select a core workflow.

The available solutions are declared scikit-learn pipelines, not arbitrary
model-written Python. The reasoner chooses among the exposed families and
parameters. The host handles training, persistence, and scoring. This tests
tool-based model development; it does not establish unrestricted code generation.

## Download a source

Install the optional data dependencies in your development environment. The
download helper needs pandas and a Parquet reader. From the repository root:

```bash
python examples/25_host_runtime/fetch_openml.py \
  --dataset-id 61 --problem-kind classification \
  --output-dir ./iris-source
```

The output directory must not exist. The helper saves the original metadata,
downloaded Parquet, converted CSV, and a manifest with exact byte digests.
Downloading is explicit host preparation, not an engine-selected action.

The following source configurations support the small demonstration:

| Dataset | OpenML ID | Target | Excluded features |
|---|---:|---|---|
| Titanic | 40945 | `survived` | `boat`, `body`, `name`, `ticket`, `home.dest` |
| House prices | 42165 | `SalePrice` | `Id` |
| Iris flowers | 61 | `class` | None |

For Titanic, `boat` and `body` contain outcome-related information. The other
exclusions are a conservative identifier and feature-availability policy;
they are not all proven target leakage. These choices belong in the input
manifest, not the engine. Row-random splitting can still share family and
ticket-related patterns across partitions, so this is not a family-held-out
generalization study.

For example:

```bash
python examples/25_host_runtime/fetch_openml.py \
  --dataset-id 40945 --problem-kind classification \
  --exclude boat --exclude body --exclude name --exclude ticket \
  --exclude home.dest --output-dir ./titanic-source

python examples/25_host_runtime/fetch_openml.py \
  --dataset-id 42165 --problem-kind regression \
  --exclude Id --output-dir ./housing-source
```

Source identity and license information come from the
[OpenML dataset API](https://docs.openml.org/data/use/). The house-price
record reports its license as `NA`. Keep downloaded rows local and review the
original terms before redistribution. This repository publishes code and
measurement summaries, not these downloaded datasets.

## Run the engine

Provide a preinstalled, immutable Docker image containing Python, NumPy,
pandas, scikit-learn, and joblib. The example's default is a locally available
Loop Engine test image, not a public image that a new installation can pull.
Use your approved image's exact repository digest with `--image`.

```bash
PYTHONPATH=src python examples/25_host_runtime/tabular_portfolio.py \
  --manifest ./iris-source/manifest.json \
  --work-dir ./iris-portfolio \
  --image YOUR_REPOSITORY@sha256:YOUR_IMAGE_DIGEST \
  --authorize-model-calls --allow-source-to-model
```

Configure the selected provider first. `--model-route` and `--model-id` select
an exact route; the defaults match the JavaScript example. No model-call,
pass, total-token, or spending ceiling is added. The separate Docker worker
has resource limits and a command timeout. It has no network or host fallback.

The model can inspect the development profile, propose a batch of explicit
model specifications, and revise them from validation observations. A
classification portfolio includes logistic regression, random forest,
histogram gradient boosting, and a dummy prior baseline. Regression uses
ridge regression in place of logistic regression and a dummy mean baseline.
The model chooses the exposed hyperparameters. Preprocessing and execution
remain trusted host implementations, not model-authored code.

Completion requires successful fits for the baseline and all three declared
non-baseline families. It does not require a particular accuracy or claim that
every fitted model is useful. Inspect the measured validation and test scores.

Saved output includes:

- `input-manifest.json` and `split-manifest.json` for source and split identity.
- `candidate-records/` for selected specifications, fit results, and digests.
- `development-workspace/candidates/` for fitted pipelines and validation predictions.
- `runs/` for the actual engine Run History and model-call accounting.
- `portfolio-freeze.json` for the validation-selected candidate before testing.
- `final-evaluation.json` for the separate held-out evaluation.

The manifest may supply three distinct `split_seeds` and positive
`split_fractions` named `train`, `validation`, and `test` that sum to one.
The small demonstration protocol defaults to three repeats and 60/20/20
fractions. These are experiment settings, not limits on the Loop runtime.

## Evaluation boundaries

The host freezes a test partition before model work. Training and validation
splits use only the remaining development rows. Preprocessing fits on each
training partition. Validation observations may guide further model choices.

After the solve ends, the host freezes the candidate registry and evaluates
the saved pipelines on the test partition. Test results do not return to the
reasoner for tuning. A model's asserted score is not the evaluator.

Candidate selection minimizes mean validation log loss for classification
and mean validation RMSE for regression. Classification also reports accuracy
and, for binary tasks, ROC AUC. Regression reports MAE and R-squared as well.
The house-price RMSE is in original price units, not Kaggle's log-price metric.
Three fits share one held-out population; their averaged scores are not three
independent test populations or a confidence interval.

These are familiar datasets and local evaluation splits. Their scores are not
Kaggle submissions, leaderboard grades, or evidence of unseen-task solving.
Comparing several models on the final test set is descriptive; selecting the
test-set winner and reporting it as an unbiased estimate would be misleading.

See [embedding Loop Engine](../../docs/guides/embedding-loop-engine.md) for
the host trust boundary and permissions. Model-call authority does not grant
arbitrary host commands, network access from training, or publication.
