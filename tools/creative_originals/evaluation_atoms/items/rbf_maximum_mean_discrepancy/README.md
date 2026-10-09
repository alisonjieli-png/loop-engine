# Maximum mean discrepancy with an RBF kernel

Measures how different two samples of vectors are with the kernel maximum mean discrepancy (MMD) under a Gaussian kernel. It provides the biased and unbiased estimators of MMD squared, the median-distance bandwidth, and a seeded permutation test.

## When to use it

- Check whether two sets of model outputs, embeddings or inputs come from the same distribution.
- Compare a generated sample with a reference sample without choosing histogram bins.
- Monitor inputs for drift (keeping in mind that input drift and concept drift are different things).

## Formula

    k(x, y) = exp(-||x - y||^2 / (2 sigma^2))
    biased:   MMD^2 = mean k(x_i, x_j) + mean k(y_i, y_j) - 2 mean k(x_i, y_j)        (all pairs)
    unbiased: the same with the diagonal pairs i = j left out of the first two means

The biased form is never negative. The unbiased form has the right expectation and can be negative; do not clamp or square-root it. `sigma` defaults to the median of the positive pairwise distances of the pooled sample. The permutation test reports `p = (1 + #{permuted >= observed}) / (1 + B)`.

## Assumptions and what it does not establish

- Under the null hypothesis the pooled rows are exchangeable.
- The bandwidth must be fixed before permuting; the median heuristic on the pooled sample is.
- A small p-value says the distributions differ. It does not say how, or whether the difference matters for a task.

## Parameters

| Name | Meaning |
|---|---|
| `x_rows`, `y_rows` | samples of equal dimension, up to 5000 rows each |
| `bandwidth` | `sigma > 0`, or null for the median heuristic |
| `unbiased` | use the unbiased estimator (needs 2 rows per sample) |
| `permutations`, `seed` | permutation count and non-negative integer seed |

## Example

```python
from rbf_maximum_mean_discrepancy import mmd_squared

mmd_squared([[0], [1]], [[2], [3]], bandwidth=1)["mmd_squared"]                   # 1.1624
mmd_squared([[0], [1]], [[0], [1]], bandwidth=1, unbiased=True)["mmd_squared"]    # -0.3935
```

Command line:

```bash
echo '{"call": "permutation_test", "arguments": {"x_rows": [[0], [0.2], [0.1]], "y_rows": [[2], [2.1], [1.9]], "permutations": 99, "seed": 1}}' | python3 rbf_maximum_mean_discrepancy.py
```

## Limits

- Quadratic in the pooled sample size.
- One Gaussian kernel; test power depends on the bandwidth.

## Files

- `rbf_maximum_mean_discrepancy.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_rbf_maximum_mean_discrepancy.py`, `test_package.py`: run with `python3 -m unittest`.
