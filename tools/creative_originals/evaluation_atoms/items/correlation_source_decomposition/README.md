# Within-group and between-group covariance decomposition

Splits the covariance between two columns, for example a score `Y` and a prediction `P`, into the part that comes from agreement inside each group and the part that comes from differences between group means. The split is exact: the computation runs in rational arithmetic, so the two parts add up to the total with no rounding residual.

## When to use it

- A predictor correlates with outcomes across a benchmark, and you want to know whether it ranks items within a task or only tells tasks apart.
- An evaluation pools several sources, and a pooled correlation may hide opposite trends inside the sources.
- You need the law of total variance for a score across seeds, tasks or annotators (`decompose_variance`).

## Formula

With population moments (divide by `n`) and group weights `w_g = n_g / n`:

    Cov(Y, P) = sum_g w_g Cov(Y, P | g)  +  sum_g w_g (mean_g(Y) - mean(Y)) (mean_g(P) - mean(P))
              = within_group             +  between_group

Each input float is converted to its exact rational value with `fractions.Fraction`. All sums and products are exact, so `identity_residual` is `0.0`.

## Assumptions and what it does not establish

- The identity needs population moments. With `n - 1` denominators it fails; the tests show this.
- Each row belongs to one group. The weights are the empirical group sizes.
- The result describes the data at hand. It does not say which grouping is the right one, and a correlation coefficient does not split additively the way covariance does.

## Parameters

| Name | Meaning |
|---|---|
| `y`, `p` | equal-length lists of numbers |
| `groups` | one text or integer label per row |

`decompose_covariance` returns `total_covariance`, `within_group`, `between_group`, `identity_residual`, `total_correlation` (null when a variance is 0), `within_share` and `between_share` (null when the total is 0), `sign_conflict`, and one row per group with its count, weight, means and covariance.

## Example

```python
from correlation_source_decomposition import decompose_covariance

result = decompose_covariance(y=[1, 3, 5, 7], p=[2, 4, 1, 3], groups=["a", "a", "b", "b"])
result["total_covariance"], result["within_group"], result["between_group"]   # 0.0, 1.0, -1.0
```

The overall covariance is zero, yet inside each group `Y` and `P` rise together. The group means move in opposite directions and cancel it.

Command line:

```bash
echo '{"call": "decompose_variance", "arguments": {"y": [1, 2, 3, 4], "groups": ["a", "a", "b", "b"]}}' | python3 correlation_source_decomposition.py
```

## Limits

- Rational arithmetic is exact but slower than floats. Tens of thousands of rows are fine.
- Labels may be text or integers. Booleans are refused.

## Files

- `correlation_source_decomposition.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_correlation_source_decomposition.py`, `test_package.py`: run with `python3 -m unittest`.
