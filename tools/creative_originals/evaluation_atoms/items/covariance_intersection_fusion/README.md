# Covariance intersection fusion

Fuses two estimates (a mean and a covariance each) whose errors may be correlated in an unknown way. The fused covariance never claims more certainty than the evidence supports, for any cross-correlation.

## When to use it

- Two sources may share inputs: two agents that read the same report, two models trained on overlapping data, two sensors with a common calibration.
- An estimate may reach you twice through different paths and you cannot prove it did not.
- You want a fused estimate that stays consistent even in the worst case, and you accept that it is wider than the independence rule.

## Formula

    C^-1 = omega A^-1 + (1 - omega) B^-1
    c    = C (omega A^-1 a + (1 - omega) B^-1 b)

`omega` in `[0, 1]` minimizes `trace(C)` (default) or `det(C)`. Both objectives are convex in `omega`. Their derivatives, `-trace(C D C)` and `-trace(C D)` with `D = A^-1 - B^-1`, are non-decreasing, so `omega` is found by bisection to about `1e-16`.

`independent_fusion` gives the independence rule `C = (A^-1 + B^-1)^-1` for comparison. `conservative_margin` reports the smallest eigenvalue of claimed minus actual covariance.

## Assumptions and what it does not establish

- Each input covariance describes its own estimate's error honestly. An optimistic input stays optimistic after fusion.
- The guarantee: for every `omega` in `[0, 1]` and every cross-covariance consistent with `A` and `B`, `C` minus the true covariance of the fused error is positive semidefinite.
- Fusing an estimate with an exact duplicate returns it unchanged. The independence rule would halve its covariance.
- It does not detect outliers or inconsistent inputs, and it is wider than necessary when the errors really are independent.

## Parameters

| Name | Meaning |
|---|---|
| `mean_a`, `mean_b` | the two estimates, vectors of equal length d |
| `covariance_a`, `covariance_b` | d by d positive definite covariances |
| `criterion` | `"trace"` (default) or `"determinant"` |
| `omega` | optional fixed weight in `[0, 1]`; skips the search |

The result holds `mean`, `covariance`, `omega` and `objective` (`trace(C)` or `log det(C)`).

## Example

```python
from covariance_intersection_fusion import covariance_intersection, independent_fusion

a, A = [0, 0], [[1, 0], [0, 4]]
b, B = [1, 1], [[4, 0], [0, 1]]
covariance_intersection(a, A, b, B)        # omega 0.5, covariance [[1.6, 0], [0, 1.6]], mean [0.2, 0.8]
independent_fusion(a, A, a, A)["covariance"]   # [[0.5, 0], [0, 2]]: a duplicate counted twice
```

Command line:

```bash
echo '{"call": "covariance_intersection", "arguments": {"mean_a": [0], "covariance_a": [[1]], "mean_b": [3], "covariance_b": [[4]]}}' | python3 covariance_intersection_fusion.py
```

## Limits

- Two estimates per call. Fusing more by repeated calls stays conservative but is not the joint optimum.
- Dense matrices for small dimensions (tens).
- In one dimension the trace criterion always keeps the better single estimate (`omega` is 0 or 1).

## Files

- `covariance_intersection_fusion.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_covariance_intersection_fusion.py`, `test_package.py`: run with `python3 -m unittest`.
