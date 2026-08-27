# Three-model ensemble

Build a linear model, a neural-network model, and a tree model, then
ensemble them, through the canonical Loop runtime.

Run:

```bash
python3 examples/18_three_model_ensemble/run.py
```

The example:

- generates a small deterministic synthetic classification dataset;
- splits it once and shares the same immutable split across all models;
- trains the three models as independent Spawned Loops;
- ensembles their probability predictions;
- reports per-member and ensemble metrics;
- verifies the ensemble is not silently worse than every member;
- records the whole run on a LoopLedger.

No network, no external service, no model calls.
