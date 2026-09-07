# Prepare CSV competition data and a local submission file

These helpers extend the [tabular portfolio example](TABULAR-PORTFOLIO.md).
They cover competitions with `train.csv`, `test.csv`, and
`sample_submission.csv`, an explicit target, and one tabular prediction
contract. They do not support arbitrary competition layouts. In particular,
TrafficFlowBench needs a separate multi-task data adapter.

## Authorized acquisition

`prepare_kaggle.py` checks that the configured account already entered the
exact requested competition. It requires a complete file listing containing
the three expected CSVs. The Kaggle CLI and credentials must already be
configured. Credentials are not copied into the manifest.

```bash
python examples/25_host_runtime/prepare_kaggle.py --help
```

A download requires `--competition`, a new `--output-dir`, `--target`,
`--problem-kind classification|regression`, `--selection-metric`, and
`--authorize-download`. Repeated `--exclude` arguments declare non-feature
columns. Review the exact competition's current terms before granting access.
The flag does not join a competition or accept new terms.

The helper records access metadata, source pages, file sizes, digests, columns,
and row counts, then writes a `tabular_portfolio_input/v1` manifest for the
portfolio example. Downloads and source pages belong in a private data
workspace, not Git. Acquisition is host preparation, not autonomous dataset
selection or evidence of task completion.

## Refit a frozen selection

`competition_prediction.py` consumes `competition_prediction_request/v1`.
It requires absolute, digest-bound paths for the frozen validation selection,
its separate local evaluation, training data, test data, and submission
template. Declare the exact columns, feature roles, identifier, target,
problem kind, refit seed, and prediction kind.

Supported prediction kinds are `label`, `regression`, `positive_probability`,
and `class_probabilities`. Probability outputs require the corresponding
positive label or column-to-class map. The helper rejects a changed source,
invalid winner, target leakage into features, incompatible schema, or
incomplete identifier set before refitting.

```bash
python examples/25_host_runtime/competition_prediction.py \
  --manifest /absolute/path/prediction-request.json \
  --output-dir /absolute/new/competition-prediction \
  --authorize-local-compute
```

Use the pinned image and dependency setup documented in the portfolio guide.
The full-data estimator is a new fit of the frozen recipe. It does not replace
the earlier sealed holdout measurement. Training and prediction run in
separate Docker workspaces, and the predictor has no training labels.
The controller does not deserialize the trained estimator.

The output includes `submission.csv` and `submission-record.json`. The
formatter checks identifiers, template order, class vocabulary, finite values,
and probability shape. It makes no model call and does not submit to Kaggle.
A valid local CSV is not an external score.

```bash
python -m unittest discover \
  -s examples/25_host_runtime -p test_competition_prediction.py
```

For a multi-task capstone, use the
[TrafficFlowBench experiment plan](../../docs/benchmarks/TRAFFICFLOWBENCH-NATIVE-OPENCODE-PLAN.md)
and its evaluator restrictions before designing another adapter.
