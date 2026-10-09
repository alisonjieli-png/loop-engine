# Split conformal prediction intervals

Turns any point predictor into prediction intervals with a finite-sample coverage guarantee. It uses residuals on a held-out calibration set and the exact quantile index `ceil((n + 1)(1 - alpha))`, optionally separately per group, and includes a seeded coverage check.

## When to use it

- A regression model, an estimator of cost or latency, or a score predictor needs honest intervals without distributional assumptions.
- You want the coverage guarantee to hold inside each group (task type, language, user segment): use the Mondrian form.
- You want to verify the guarantee on held-out data before relying on it.

## Formula

    r_i = |y_i - yhat_i|               for the n calibration points
    k   = ceil((n + 1)(1 - alpha))
    q   = the k-th smallest r_i        (unbounded when k > n)
    interval = [yhat - q, yhat + q]

`k` is computed in exact rational arithmetic from the decimal value of `alpha`. Under exchangeability, coverage is at least `1 - alpha`, and below `1 - alpha + 1/(n + 1)` when the residuals have no ties. With `n = 50` and `alpha = 0.1` the expected coverage is `46/51 = 0.902`.

## Assumptions and what it does not establish

- Calibration and test points are exchangeable, and the predictor was not fitted on the calibration points.
- The guarantee is marginal: averaged over inputs, not for each input.
- Under distribution shift the guarantee does not hold; see `adaptive_conformal_inference` for an online alternative.

## Parameters

| Name | Meaning |
|---|---|
| `scores` | non-conformity scores for `conformal_quantile` |
| `calibration_predictions`, `calibration_targets` | held-out predictions and true values |
| `test_predictions` | where intervals are wanted |
| `alpha` | miscoverage level in `(0, 1)` |
| `calibration_groups`, `test_groups` | optional group labels (both or neither) |
| `repetitions`, `calibration_size`, `test_size`, `noise`, `seed` | the seeded coverage simulation |

## Example

```python
from split_conformal_intervals import conformal_quantile, coverage_simulation

conformal_quantile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.1)["quantile"]       # 10, not 9
coverage_simulation(400, 50, 100, 0.1, 1.0, seed=1)                        # mean coverage 0.897, expected 0.902
```

Command line:

```bash
echo '{"call": "split_conformal", "arguments": {"calibration_predictions": [1, 2, 3], "calibration_targets": [1.5, 2.5, 2], "test_predictions": [10], "alpha": 0.25}}' | python3 split_conformal_intervals.py
```

## Limits

- Symmetric, constant-width intervals per group (absolute residuals).
- Few calibration points can give unbounded intervals.

## Files

- `split_conformal_intervals.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_split_conformal_intervals.py`, `test_package.py`: run with `python3 -m unittest`.
