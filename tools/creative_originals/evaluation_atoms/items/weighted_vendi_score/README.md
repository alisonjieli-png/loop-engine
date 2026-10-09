# Weighted Vendi score

Computes the effective number of distinct members in a set, given a similarity matrix or feature rows, with optional weights per member. A score of 3 means the set is as diverse as 3 completely dissimilar, equally weighted members.

## When to use it

- Compare the diversity of generated samples, candidate solutions, prompts or ensemble members.
- Score a set where some members are duplicates or carry more weight than others (sampling frequencies, mixture weights, vote counts).
- Check that deduplication does not change a diversity number: with conserved weights, duplicates do not inflate it.

## Formula

Normalize the weights to `w` with sum 1 and let `D = diag(w)`. With `K` the similarity matrix,

    lambda = eigenvalues of D^(1/2) K D^(1/2)        (they sum to 1 because K has a unit diagonal)
    score_q = exp(H_q(lambda))
    H_1 = -sum lambda_i log lambda_i                 (Shannon)
    H_q = log(sum lambda_i^q) / (1 - q)              (Renyi, q != 1)
    H_0 = log(number of positive eigenvalues)

With equal weights this is the plain Vendi score `exp(H(eig(K / n)))`.

## Assumptions and what it does not establish

- `K` must be a valid kernel: symmetric, positive semidefinite and `k(x, x) = 1`. Inputs that break this raise `ValueError`.
- The nonzero eigenvalues equal those of `sum_i w_i phi_i phi_i^T` for unit feature vectors `phi_i`. Splitting a member into identical clones whose weights add up to its weight therefore leaves the score unchanged. Giving each clone a full share of weight does change it.
- The score reflects the kernel only. It does not measure quality, correctness, coverage of a target distribution or usefulness.

## Parameters

| Name | Meaning |
|---|---|
| `similarity` | n by n symmetric positive semidefinite matrix with ones on the diagonal |
| `weights` | n non-negative numbers with a positive sum; equal weights when omitted |
| `order` | Renyi order `q >= 0`; 1 by default |
| `features` | (`vendi_from_features`) n non-zero rows, scored under cosine similarity |

The result holds `score`, `order`, the normalized `eigenvalues`, the normalized `weights` and `members`.

## Example

```python
from weighted_vendi_score import weighted_vendi_score

clones = [[1, 1, 0], [1, 1, 0], [0, 0, 1]]
weighted_vendi_score(clones, weights=[0.25, 0.25, 0.5])["score"]   # 2.0: the clones count once
weighted_vendi_score(clones)["score"]                              # 1.8899: equal weights give the clones more mass
```

Command line:

```bash
echo '{"call": "weighted_vendi_score", "arguments": {"similarity": [[1, 0.5], [0.5, 1]]}}' | python3 weighted_vendi_score.py
```

## Limits

- Dense eigendecomposition by Jacobi rotations, meant for at most a few hundred members.
- Eigenvalues at or below `1e-12` count as zero. This matters for orders below 1.
- `vendi_from_features` uses cosine similarity. Other kernels must be computed first and passed as `similarity`.

## Files

- `weighted_vendi_score.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_weighted_vendi_score.py`, `test_package.py`: run with `python3 -m unittest`.
