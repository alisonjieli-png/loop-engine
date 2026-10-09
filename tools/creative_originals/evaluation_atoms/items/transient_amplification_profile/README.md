# Transient amplification profile of a linear update

Computes how much a linear update `x_(h+1) = A x_h` can amplify a state over `h` steps: the spectral norm `||A^h||_2` for every step up to a horizon. It reports the peak, the step after which the norm stays below 1, the spectral radius, and an upper bound on the spectral radius from the norms themselves.

## When to use it

- An iterative method, a recurrent update, an optimizer's linearization or a feedback loop has eigenvalues inside the unit circle, and you want to know whether perturbations still grow before they decay.
- You need the worst-case gain at a specific number of steps, not only the long-run rate.
- You want to show that "stable eigenvalues" and "no amplification" are different claims.

## Formula

    norms[h] = ||A^h||_2 = sqrt(largest eigenvalue of (A^h)^T A^h)
    peak_step = argmax_h norms[h]
    gelfand_bound = min over h >= 1 of norms[h]^(1/h)     (always >= the spectral radius)

Each norm comes from power iteration on `B^T B` with two deterministic starting vectors; the Rayleigh quotient is the estimate. The spectral radius comes from the characteristic polynomial (Faddeev-LeVerrier) and simultaneous root iteration (Durand-Kerner).

For `A = [[0.8, 4], [0, 0.8]]` the spectral radius is 0.8, yet `||A^4||_2 = 8.2124`. The closed form for this family is `(sqrt(4a^2 + b^2) + |b|) / 2` with `a = 0.8^h` and `b = 4 h 0.8^(h-1)`. The norm first stays below 1 from step 21.

## Assumptions and what it does not establish

- The same `A` applies at every step. Time-varying or nonlinear updates are out of scope.
- Norms are Euclidean. A different norm, for example one weighted by a problem's natural scaling, gives a different profile.
- A profile computed up to a horizon says nothing about steps beyond it, except through the spectral radius.

## Parameters

| Name | Meaning |
|---|---|
| `matrix` | square `A`, at most 60 rows (`spectral_norm` accepts any rectangular matrix) |
| `horizon` | number of steps, 1 to 5000 |
| `iterations`, `tolerance` | power iteration limits for `spectral_norm` (defaults 2000 and 1e-15) |

`transient_profile` returns `norms`, `peak_norm`, `peak_step`, `amplifies`, `settles_below_one_at`, `spectral_radius` (null above 8 rows), `gelfand_bound` and `converged`.

## Example

```python
from transient_amplification_profile import transient_profile

profile = transient_profile([[0.8, 4], [0, 0.8]], horizon=30)
profile["spectral_radius"], profile["peak_step"], round(profile["peak_norm"], 4)   # 0.8, 4, 8.2124
profile["settles_below_one_at"]                                                     # 21
```

Command line:

```bash
echo '{"call": "transient_profile", "arguments": {"matrix": [[0.8, 4], [0, 0.8]], "horizon": 30}}' | python3 transient_amplification_profile.py
```

## Limits

- Dense matrix powers: meant for up to about 60 rows and horizons of a few thousand steps.
- Power iteration is slow when the top two singular values nearly coincide; check `converged`.
- Eigenvalues are limited to 8 rows. A repeated eigenvalue is accurate to about `1e-8`.

## Files

- `transient_amplification_profile.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_transient_amplification_profile.py`, `test_package.py`: run with `python3 -m unittest`.
