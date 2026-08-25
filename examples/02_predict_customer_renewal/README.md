# Predict customer renewal

This example creates a small customer dataset, trains a deterministic tabular
workflow, writes predictions, and grades them against a hidden holdout.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/02_predict_customer_renewal/run.py
```

- Network or model: none
- External effects: writes `example-output/customer-renewal/`
- Shows: an artifact, local validation, hidden-answer grading, and run cost
- Does not show: production data quality or external benchmark performance
