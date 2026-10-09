# Ridge penalty induced by a frozen linear transform

Computes the penalty matrix that weight decay on trainable weights `w` places on the effective coefficients `beta = A w` when `A` is frozen. It also fits both routes on your data and reports how far apart the coefficients are, which is zero up to rounding.

## When to use it

- A linear model or a linear head is reparameterized: several trainable copies of a weight, a frozen projection, a factorized layer with one factor frozen.
- You want to know what explicit penalty the weight decay you set actually applies, per direction.
- You want to replace an overparameterized training setup by an equivalent generalized ridge fit, or check that two setups are equivalent.

## Formula

With `A` of shape k by m and full row rank (k <= m), training `w` with `ridge * ||w||^2` gives the same `beta` as

    beta = argmin ||y - X beta||^2 + ridge * beta^T P beta,    P = (A A^T)^-1

The smallest `||w||^2` with `A w = beta` is `beta^T (A A^T)^-1 beta`, and the trained `w` lies in the row space of `A`. Consequences:

- `A = [I, I]` (every column duplicated) gives `P = I / 2`: the effective penalty halves.
- `c` stacked copies of `I` give `P = I / c`.
- `A = c I` gives `P = I / c^2`.

## Assumptions and what it does not establish

- `A` is frozen and has full row rank. A rank-deficient `A` raises `ValueError`.
- Only `w` is trained, with squared error and the penalty `ridge * ||w||^2`, `ridge > 0`.
- The tool shows equivalence of fitted coefficients. It does not say which penalty generalizes better.

## Parameters

| Name | Meaning |
|---|---|
| `transform` | the frozen matrix `A`, k rows by m columns |
| `features` | n rows of k numbers (`X`) |
| `targets` | n numbers (`y`) |
| `penalty_matrix` | k by k symmetric positive semidefinite `P` for `fit_generalized_ridge` |
| `ridge` | penalty strength, positive |

## Example

```python
from ridge_penalty_from_linear_transform import induced_penalty, compile_penalty

induced_penalty([[1, 0, 1, 0], [0, 1, 0, 1]])["penalty_matrix"]    # [[0.5, 0], [0, 0.5]]
compile_penalty([[1, 0], [0, 1], [1, 1]], [1, 2, 4], [[1, 1, 0], [0, 1, 1]], 0.7)["max_abs_difference"]   # about 4e-16
```

Command line:

```bash
echo '{"call": "induced_penalty", "arguments": {"transform": [[1, 2, 3]]}}' | python3 ridge_penalty_from_linear_transform.py
```

## Limits

- Dense linear algebra for small k and m (tens).
- Squared error only for the fitting routes. The penalty identity itself does not depend on the loss.
- Rounding differences of order `1e-15` between the two routes are expected.

## Files

- `ridge_penalty_from_linear_transform.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_ridge_penalty_from_linear_transform.py`, `test_package.py`: run with `python3 -m unittest`.
