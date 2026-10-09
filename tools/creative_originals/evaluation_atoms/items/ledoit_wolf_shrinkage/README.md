# Ledoit-Wolf covariance shrinkage

Shrinks a sample covariance toward a multiple of the identity with the Ledoit-Wolf intensity. The result is well conditioned and positive definite even when there are fewer observations than variables, where the sample covariance itself is singular.

## When to use it

- You estimate a covariance of metrics, features or embedding dimensions from a few runs and need to invert it (Mahalanobis distances, whitening, generalized least squares, portfolio weights).
- The number of variables is close to or above the number of observations.
- You want a data-driven intensity instead of an arbitrary ridge term.

## Formula

With `X_c` the centred data (n rows, p columns):

    S      = X_c^T X_c / n
    mu     = trace(S) / p
    d^2    = ||S - mu I||_F^2 / p
    bbar^2 = (1 / n^2) sum_k ||x_k x_k^T - S||_F^2 / p
    delta  = min(bbar^2, d^2) / d^2
    Sigma  = delta mu I + (1 - delta) S

`delta` is 0 when `S` is already a multiple of the identity.

## Assumptions and what it does not establish

- Observations are i.i.d. with finite fourth moments. Ledoit and Wolf prove that `delta` is a consistent estimate of the intensity that minimizes the expected Frobenius loss as `n` and `p` grow.
- For a fixed small sample, `delta` is an estimate. It is not guaranteed to beat the sample covariance on every sample.
- The tests check the formula against an exact rational implementation, scale and rotation behaviour, and positive definiteness.

## Parameters

| Name | Meaning |
|---|---|
| `rows` | observations, one per row, at least 2 |
| `assume_centered` | skip subtracting column means |
| `covariance`, `shrinkage` | (`shrink`) apply a given intensity in `[0, 1]` |

`ledoit_wolf` returns the shrunk `covariance`, the `sample_covariance`, `shrinkage`, `target_scale` (`mu`), `d_squared`, `b_bar_squared`, and the smallest eigenvalues before and after.

## Example

```python
from ledoit_wolf_shrinkage import ledoit_wolf

result = ledoit_wolf([[1, 2, 3, 4, 5], [2, 1, 0, 1, 2], [0, 0, 1, 3, 1]])
result["sample_smallest_eigenvalue"], result["smallest_eigenvalue"]   # about 0 and 0.571
```

Command line:

```bash
echo '{"call": "ledoit_wolf", "arguments": {"rows": [[1, 2], [2, 1], [3, 4], [4, 3], [5, 7]]}}' | python3 ledoit_wolf_shrinkage.py
```

## Limits

- One target, the scaled identity.
- Dense p by p matrices: p up to a few hundred.

## Files

- `ledoit_wolf_shrinkage.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_ledoit_wolf_shrinkage.py`, `test_package.py`: run with `python3 -m unittest`.
