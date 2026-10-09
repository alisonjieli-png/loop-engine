# Brier score decomposition and expected calibration error

Splits the Brier score of probability forecasts into reliability (calibration), resolution (discrimination), uncertainty (base rate), and two within-bin terms that make the split exact when forecasts are grouped into bins. It also computes the expected calibration error.

## When to use it

- Two models have similar Brier scores and you want to know whether one is worse calibrated or less discriminating.
- You report calibration on bins and want the reported terms to add up to the score.
- You need ECE next to a proper score instead of on its own.

## Formula

With equal-width bins `k`, bin means `fbar_k`, `obar_k`, counts `n_k` and overall rate `obar`:

    BS  = (1/N) sum (f_i - o_i)^2
    REL = (1/N) sum_k n_k (fbar_k - obar_k)^2
    RES = (1/N) sum_k n_k (obar_k - obar)^2
    UNC = obar (1 - obar)
    WBV = (1/N) sum_i (f_i - fbar_k)^2
    WBC = (2/N) sum_i (f_i - fbar_k)(o_i - obar_k)
    BS  = REL - RES + UNC + WBV - WBC
    ECE = sum_k (n_k / N) |fbar_k - obar_k|

The three-term form `REL - RES + UNC` is exact only when every forecast in a bin is the same.

## Assumptions and what it does not establish

- Outcomes are 0 or 1; forecasts are probabilities of 1.
- All binned quantities depend on the bins. ECE in particular is biased upward when bins hold few forecasts.
- No intervals or tests are computed.

## Parameters

| Name | Meaning |
|---|---|
| `forecasts` | probabilities in `[0, 1]` |
| `outcomes` | 0 or 1, same length |
| `bins` | number of equal-width bins, default 10 |

## Example

```python
from brier_decomposition_calibration_error import brier_decomposition

r = brier_decomposition([0.12, 0.18, 0.85, 0.95], [0, 1, 1, 1], bins=2)
r["brier"]                                                            # 0.17795
r["reliability"] - r["resolution"] + r["uncertainty"]                 # 0.19125, not the score
r["within_bin_variance"], r["within_bin_covariance"]                  # 0.0017, 0.015
```

Command line:

```bash
echo '{"call": "expected_calibration_error", "arguments": {"forecasts": [0.1, 0.1, 0.9, 0.9], "outcomes": [0, 1, 1, 1]}}' | python3 brier_decomposition_calibration_error.py
```

## Limits

- Equal-width bins only.
- Binary outcomes only.

## Files

- `brier_decomposition_calibration_error.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_brier_decomposition_calibration_error.py`, `test_package.py`: run with `python3 -m unittest`.
