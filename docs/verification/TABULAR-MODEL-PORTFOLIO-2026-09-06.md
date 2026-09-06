# Tabular model portfolios on three public datasets

Loop Engine selected model configurations and completed real training on
Iris, Titanic, and house prices through the host embedding API. Each dataset
produced four candidates, including a dummy baseline, with three fitted
pipelines per candidate. All 36 fits completed. The three solves used 33
physical calls to `ollama_cloud / cloud.default / deepseek-v4-flash:0731`.

These are familiar datasets chosen for a small demonstration. The host supplied
the executable scikit-learn pipelines; the reasoner chose their exposed
hyperparameters. This is not an unseen-task benchmark or a comparison between
language models. The [compact evidence](../evidence/TABULAR-MODEL-PORTFOLIO-2026-09-06.json)
retains every candidate configuration, measured score, failure, and record reference.

## Sources and evaluation protocol

Dataset identities and license fields come from the saved OpenML metadata
snapshots linked below. Original metadata, Parquet, and converted CSV files
remain local with verified hashes.

| Dataset and metadata | Rows | Features used | Target | Source license field |
|---|---:|---:|---|---|
| [Iris, ID 61](https://www.openml.org/api/v1/json/data/61) | 150 | 4 | `class` | Public |
| [Titanic, ID 40945](https://www.openml.org/api/v1/json/data/40945) | 1,309 | 8 | `survived` | Public |
| [House prices, ID 42165](https://www.openml.org/api/v1/json/data/42165) | 1,460 | 79 | `SalePrice` | NA |

Titanic excludes `boat`, `body`, `name`, `ticket`, and `home.dest`. Boat and body
information is related to the outcome. The other exclusions are a declared
identifier and availability policy. House prices excludes `Id`. Titanic's
row-random split can still share family-related patterns between partitions;
this is not a family-held-out study.

The host sealed one test partition before model work. Three repeated
train/validation splits used seeds 1729, 1730, and 1731 on the remaining rows.
Preprocessing and estimator fitting used only each repeat's training rows.

| Dataset | Train rows per repeat | Validation rows per repeat | Shared test rows |
|---|---:|---:|---:|
| Iris | 90 | 30 | 30 |
| Titanic | 785 | 262 | 262 |
| House prices | 876 | 292 | 292 |

Classification selection minimized mean validation log loss. Regression
selection minimized mean validation RMSE. After each solve ended, the host
froze the candidate registry and selected candidate before test predictions
or scoring. Test observations were never returned to the reasoner.

Each reported score is the arithmetic mean of scores from three separately
fitted pipelines on the same test rows. It is not an ensemble score, three
independent test populations, or a confidence interval. All candidate test
scores are shown, but they do not determine the selected result.

## Classification results

Lower log loss is better. Higher accuracy and ROC AUC are better. ROC AUC here
is the binary Titanic metric; no multiclass AUC was calculated for Iris.

| Dataset | Family | Selected by validation | Validation log loss | Test log loss | Test accuracy | Test ROC AUC |
|---|---|---|---:|---:|---:|---:|
| Iris | Dummy prior | No | 1.098612 | 1.098612 | 0.333333 | n/a |
| Iris | Logistic regression | No | 0.185532 | 0.194867 | 0.944444 | n/a |
| Iris | Random forest | Yes | 0.176676 | 0.169902 | 0.911111 | n/a |
| Iris | Histogram gradient boosting | No | 0.740988 | 0.980787 | 0.900000 | n/a |
| Titanic | Dummy prior | No | 0.664881 | 0.664881 | 0.618321 | 0.500000 |
| Titanic | Logistic regression | Yes | 0.479056 | 0.463493 | 0.779898 | 0.839866 |
| Titanic | Random forest | No | 0.557442 | 0.546281 | 0.809160 | 0.851667 |
| Titanic | Histogram gradient boosting | No | 0.535474 | 0.502142 | 0.811705 | 0.855905 |

Selection follows the declared loss, not whichever secondary metric looks
best. Titanic's logistic regression had lower validation log loss, while the
boosting candidate later had higher test accuracy and AUC.

## House-price regression results

RMSE and MAE are in original price units; lower is better. Higher R-squared
is better. These are local split scores, not Kaggle's log-price metric.

| Family | Selected by validation | Validation RMSE | Test RMSE | Test MAE | Test R-squared |
|---|---|---:|---:|---:|---:|
| Dummy mean | No | 79,009.93 | 89,116.27 | 61,014.39 | -0.000962 |
| Ridge regression | No | 34,704.03 | 33,605.18 | 19,367.51 | 0.857470 |
| Random forest | No | 33,169.99 | 39,941.65 | 21,286.62 | 0.798851 |
| Histogram gradient boosting | Yes | 28,812.22 | 34,881.36 | 18,681.63 | 0.846410 |

Ridge had a lower test RMSE than the validation-selected boosting model.
The report keeps the boosting selection. Switching the reported winner after
seeing test scores would use the test set for model selection.

## Calls, failures, and saved history

Every solve reached `COMPLETED_VERIFIED` in two passes, with no supplied
`TaskFeedback` and no generated Python project. Completion checked that the
required model families had fitted artifacts. It did not require a minimum
predictive score. Training, prediction, and scoring ran in the pinned Docker
worker with no network or host fallback.

| Dataset | Physical model calls | Input tokens | Output tokens | Solve seconds |
|---|---:|---:|---:|---:|
| Iris | 12 | 249,667 | 22,644 | 101.162 |
| Titanic | 10 | 233,193 | 19,864 | 97.414 |
| House prices | 11 | 275,705 | 27,143 | 122.003 |

Accounting is complete: 758,565 input and 69,651 output tokens, totaling
828,216. Invoiced cost remains unknown. Solve times exclude source preparation
and final scoring. The runs overlapped, so their sum is not campaign wall time.

Iris recovered one `output_validation_failed` model attempt. It also recorded
`stage_evidence_degraded` because one model execution could not be joined to
its stage occurrence. Its stage attribution is incomplete even though model
usage and the saved outcome are accounted for. Housing rejected one attempt
to select the hidden host verifier as a tool, then continued with a valid
action. No fitting attempt failed, and no operator supplied repair feedback.

Canonical saved-run verification confirms intact histories and bound outcomes
for all three runs: 960 events for Iris, 923 for Titanic, and 990 for housing.
The evidence export contains their run IDs, event heads, product digests, and
local archive references.

## Verification and reproduction

An independent read-only audit checked the source and split hashes, sealed
holdout, all candidate artifacts, copied fitted pipelines, prediction sets,
and validation-selected winners. All 36 validation prediction sets and 36 test
prediction sets matched their expected row and class order. Separate arithmetic
recomputed every metric and aggregate within an absolute/relative tolerance of
`1e-10`. No model objects were loaded into the auditing host.

The source-preparation tests passed 8/8. Portfolio checks passed 5/5, including
real Docker training/scoring and rejection of changed sources, model artifacts,
and incomplete or reordered predictions. The combined example suite passed
13/13 in 18.094 seconds with zero model calls. Redirect validation occurs
before dispatch, and source copies are rechecked against their admitted hashes.
The three downloads preceded the redirect fix. Their saved source hashes still
match, but the helper's exact code digest at download time was not recorded.
The 64 MiB download bound does not bound decompressed dataframe memory.

The [portfolio example](../../examples/25_host_runtime/TABULAR-PORTFOLIO.md)
documents the commands, schemas, exclusions, and required ML image. The frozen
runner digest is `87d084f6bf04ef5d04c70b2fce85f541bbf11a39c33a3c4a57eb8bd7c52854ef`.
The image is a local test image, not a published image available to every new
installation. Raw datasets, fitted models, predictions, and private prompts
remain local. No Kaggle submission or leaderboard grade was produced.
