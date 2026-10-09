# Dithered sign expectation and its inverse

Computes the average of one-bit readings `sign(x + noise)` as an exact function of `x`, for Gaussian or uniform noise. It checks the formula against a seeded Monte Carlo estimate and inverts it, so a mean of dithered signs gives back `x`.

## When to use it

- A signal is reduced to one bit (a sign, a pass or fail, an above-threshold flag) and you want to keep its magnitude in the average.
- You compress gradients or votes to signs and need the expected value of the compressed quantity.
- You want a known-answer check for a one-bit estimator before trusting it.

## Formula

    Gaussian dither N(0, sigma^2):  E[sign(x + sigma Z)] = 2 Phi(x / sigma) - 1 = erf(x / (sigma sqrt 2))
    Uniform dither U(-a, a):        E[sign(x + a U)]     = x / a when |x| <= a, sign(x) otherwise
    Inverse (Gaussian):             x = sigma Phi^-1((m + 1) / 2)
    Monte Carlo standard error:     sqrt((1 - m^2) / N)

Without dither, `sign(x)` is 1 for every positive `x` and the magnitude is gone.

## Assumptions and what it does not establish

- The noise is independent of `x` and between draws, with the stated distribution and a known scale.
- The Monte Carlo estimate is a consistency check at a fixed seed. Agreement within a few standard errors is expected, not guaranteed.
- Inverting near `m = -1` or `m = 1` is ill-conditioned because the curve is flat there.

## Parameters

| Name | Meaning |
|---|---|
| `x` | the offset |
| `sigma` | Gaussian standard deviation, or uniform half-width `a`; positive |
| `dither` | `"gaussian"` (default) or `"uniform"` |
| `samples`, `seed` | Monte Carlo size (1 to 2,000,000) and non-negative integer seed |
| `mean_sign` | observed mean for `recover_offset` |

## Example

```python
from dithered_sign_expectation import sign_expectation, recover_offset, monte_carlo_sign_expectation

sign_expectation(1, 1)                       # 0.6826894921370859
recover_offset(0.6826894921370859, 1)        # 1.0
monte_carlo_sign_expectation(0.3, 1, 20000, 8)["estimate"]   # 0.2365, exact 0.2358, standard error 0.0069
```

Command line:

```bash
echo '{"call": "recover_offset", "arguments": {"mean_sign": 0.5, "sigma": 2}}' | python3 dithered_sign_expectation.py
```

## Limits

- Gaussian and uniform dither only.
- Seeded draws come from `random.Random.random()` and the Box-Muller transform, so a seed gives the same draws on every Python version.

## Files

- `dithered_sign_expectation.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_dithered_sign_expectation.py`, `test_package.py`: run with `python3 -m unittest`.
