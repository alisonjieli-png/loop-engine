"""Brier score decomposition (reliability, resolution, uncertainty and two within-bin terms) and calibration error.

For probability forecasts f_i of binary outcomes o_i, grouped into B equal-width bins k (bin index
min(floor(f B), B - 1)), with bin means fbar_k, obar_k, counts n_k and the overall outcome rate obar:

    BS  = (1/N) sum (f_i - o_i)^2
    REL = (1/N) sum_k n_k (fbar_k - obar_k)^2           reliability (lower is better)
    RES = (1/N) sum_k n_k (obar_k - obar)^2             resolution (higher is better)
    UNC = obar (1 - obar)                               uncertainty of the outcomes
    WBV = (1/N) sum_i (f_i - fbar_k(i))^2               within-bin variance of the forecasts
    WBC = (2/N) sum_i (f_i - fbar_k(i)) (o_i - obar_k(i)) within-bin covariance
    BS  = REL - RES + UNC + WBV - WBC                   exactly

The familiar three-term form REL - RES + UNC is exact only when every forecast in a bin is the same; the two extra
terms make it exact for binned continuous forecasts. ECE = sum_k (n_k / N) |fbar_k - obar_k|.

    echo '{"call": "brier_decomposition", "arguments": {"forecasts": [0.1, 0.1, 0.9, 0.9], "outcomes": [0, 1, 1, 1]}}' | python3 brier_decomposition_calibration_error.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics


def _inputs(forecasts, outcomes, bins):
    f = numerics.vector(forecasts, "forecasts")
    o = numerics.vector(outcomes, "outcomes", minimum_length=len(f), maximum_length=len(f))
    if any(value < 0 or value > 1 for value in f):
        raise ValueError("forecasts must lie in [0, 1]")
    if any(value not in (0.0, 1.0) for value in o):
        raise ValueError("outcomes must be 0 or 1")
    return f, o, numerics.integer(bins, "bins", minimum=1, maximum=10000)


def _binned(f, o, bins):
    members = {}
    for index, value in enumerate(f):
        members.setdefault(min(int(math.floor(value * bins)), bins - 1), []).append(index)
    rows = []
    for position in sorted(members):
        indices = members[position]
        rows.append({"bin": position, "count": len(indices),
                     "mean_forecast": math.fsum(f[i] for i in indices) / len(indices),
                     "mean_outcome": math.fsum(o[i] for i in indices) / len(indices), "_indices": indices})
    return rows


def brier_decomposition(forecasts, outcomes, bins=10):
    """BS with its five-term decomposition on equal-width bins.

    Returns {"brier", "reliability", "resolution", "uncertainty", "within_bin_variance", "within_bin_covariance",
    "identity_residual" (BS minus the five-term sum), "bins": [{bin, count, mean_forecast, mean_outcome}]}."""
    f, o, bins = _inputs(forecasts, outcomes, bins)
    n = len(f)
    rows = _binned(f, o, bins)
    rate = math.fsum(o) / n
    brier = math.fsum((p - q) ** 2 for p, q in zip(f, o)) / n
    reliability = math.fsum(r["count"] * (r["mean_forecast"] - r["mean_outcome"]) ** 2 for r in rows) / n
    resolution = math.fsum(r["count"] * (r["mean_outcome"] - rate) ** 2 for r in rows) / n
    uncertainty = rate * (1.0 - rate)
    variance = math.fsum((f[i] - r["mean_forecast"]) ** 2 for r in rows for i in r["_indices"]) / n
    covariance = 2.0 * math.fsum((f[i] - r["mean_forecast"]) * (o[i] - r["mean_outcome"])
                                 for r in rows for i in r["_indices"]) / n
    residual = brier - (reliability - resolution + uncertainty + variance - covariance)
    return {"brier": brier, "reliability": reliability, "resolution": resolution, "uncertainty": uncertainty,
            "within_bin_variance": variance, "within_bin_covariance": covariance, "identity_residual": residual,
            "bins": [{key: value for key, value in r.items() if key != "_indices"} for r in rows]}


def expected_calibration_error(forecasts, outcomes, bins=10):
    """ECE = sum over bins of (count / N) |mean forecast - mean outcome| on equal-width bins; also the maximum gap.

    Returns {"ece", "max_gap", "bins"}."""
    f, o, bins = _inputs(forecasts, outcomes, bins)
    rows = _binned(f, o, bins)
    gaps = [abs(r["mean_forecast"] - r["mean_outcome"]) for r in rows]
    return {"ece": math.fsum(r["count"] / len(f) * gap for r, gap in zip(rows, gaps)), "max_gap": max(gaps),
            "bins": [{key: value for key, value in r.items() if key != "_indices"} for r in rows]}


FUNCTIONS = {"brier_decomposition": brier_decomposition, "expected_calibration_error": expected_calibration_error}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["brier_decomposition", "expected_calibration_error", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
