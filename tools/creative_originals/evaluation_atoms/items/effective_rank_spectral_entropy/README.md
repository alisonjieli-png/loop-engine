# Effective rank, participation ratio and stable rank

Measures how many directions a matrix of representations actually uses. All three measures equal `k` when the matrix has `k` equal non-zero singular values and 1 when it has rank one, and they differ in how they weigh an uneven spectrum.

## When to use it

- Detect collapse of embeddings or hidden states (most variance in a few directions).
- Compare the dimensionality of representations from two models or two training stages.
- Track a single number for "how spread out" a set of feature vectors is.

## Formula

With singular values `sigma_i`:

    effective_rank      = exp(-sum p_i log p_i),   p_i = sigma_i / sum_j sigma_j
    participation_ratio = (sum sigma_i^2)^2 / sum sigma_i^4
    stable_rank         = sum sigma_i^2 / max sigma_i^2

Singular values are the square roots of the eigenvalues of the smaller Gram matrix, found by Jacobi rotations. `center` subtracts column means first.

## Assumptions and what it does not establish

- Feature scales matter: rescaling one feature changes the measures. Scaling the whole matrix or rotating it does not.
- Values at or below `1e-12` times the largest singular value count as zero.
- A high effective rank does not mean the directions are useful for any task.

## Parameters

| Name | Meaning |
|---|---|
| `matrix` | rows are samples, columns are features |
| `center` | subtract column means before the decomposition |

## Example

```python
from effective_rank_spectral_entropy import spectral_dimensions

spectral_dimensions([[2, 0, 0], [0, 1, 0], [0, 0, 1]])
# effective_rank 2.828 (= 2^1.5), participation_ratio 2.0, stable_rank 1.5
```

Command line:

```bash
echo '{"call": "spectral_dimensions", "arguments": {"matrix": [[1, 2], [3, 4], [5, 6]], "center": true}}' | python3 effective_rank_spectral_entropy.py
```

## Limits

- Dense Gram matrices: the smaller dimension should stay below a few hundred.
- Nearly rank-deficient matrices are sensitive to the zero cutoff.

## Files

- `effective_rank_spectral_entropy.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_effective_rank_spectral_entropy.py`, `test_package.py`: run with `python3 -m unittest`.
