"""Split conformal prediction intervals with the finite-sample quantile index, plus group-conditional (Mondrian) form.

From n calibration residuals r_i = |y_i - yhat_i|, the interval for a new point is yhat +- q with

    q = the k-th smallest residual,  k = ceil((n + 1)(1 - alpha))      (infinite when k > n)

If calibration and test points are exchangeable, P(y in [yhat - q, yhat + q]) >= 1 - alpha, and below
1 - alpha + 1/(n + 1) when residuals have no ties. The index k is computed in exact rational arithmetic from the
decimal value of alpha, so floating-point products such as 10 * 0.9 cannot shift it. Mondrian intervals compute q
separately within each group, which gives the same guarantee within every group.

    echo '{"call": "conformal_quantile", "arguments": {"scores": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "alpha": 0.1}}' | python3 split_conformal_intervals.py
"""
from __future__ import annotations

import math
from fractions import Fraction

import atom_cli
import numerics


def _alpha(alpha):
    value = numerics.probability(alpha, "alpha", open_low=True, open_high=True)
    return Fraction(repr(value))


def conformal_quantile(scores, alpha):
    """The conformal quantile of non-conformity scores: the ceil((n + 1)(1 - alpha))-th smallest, or infinite.

    Returns {"quantile" (null when infinite), "infinite", "index" (1-based k), "n"}."""
    values = sorted(numerics.vector(scores, "scores"))
    level = _alpha(alpha)
    index = math.ceil((len(values) + 1) * (1 - level))
    if index > len(values):
        return {"quantile": None, "infinite": True, "index": index, "n": len(values)}
    return {"quantile": values[index - 1], "infinite": False, "index": index, "n": len(values)}


def _labels(groups, size, name):
    if groups is None:
        return [None] * size
    values = numerics.labels(groups, name)
    if len(values) != size:
        raise ValueError(f"{name} must have one label per row")
    return values


def split_conformal(calibration_predictions, calibration_targets, test_predictions, alpha,
                    calibration_groups=None, test_groups=None):
    """Intervals [yhat - q, yhat + q] for test predictions; q per group when groups are given.

    Returns {"intervals": [[lower, upper]] with null bounds when infinite, "quantiles": {group: q or null}}."""
    predictions = numerics.vector(calibration_predictions, "calibration_predictions")
    targets = numerics.vector(calibration_targets, "calibration_targets", minimum_length=len(predictions),
                              maximum_length=len(predictions))
    tests = numerics.vector(test_predictions, "test_predictions", minimum_length=0)
    if (calibration_groups is None) != (test_groups is None):
        raise ValueError("give both calibration_groups and test_groups, or neither")
    calibration_labels = _labels(calibration_groups, len(predictions), "calibration_groups")
    test_labels = _labels(test_groups, len(tests), "test_groups")
    residuals = {}
    for label, prediction, target in zip(calibration_labels, predictions, targets):
        residuals.setdefault(label, []).append(abs(target - prediction))
    quantiles = {label: conformal_quantile(values, alpha)["quantile"] for label, values in residuals.items()}
    intervals = []
    for label, prediction in zip(test_labels, tests):
        if label not in quantiles:
            raise ValueError(f"test group {label!r} has no calibration rows")
        q = quantiles[label]
        intervals.append([None, None] if q is None else [prediction - q, prediction + q])
    names = {str(label) if label is not None else "all": q for label, q in quantiles.items()}
    return {"intervals": intervals, "quantiles": names}


def coverage(intervals, targets):
    """Fraction of targets inside their interval (a null bound is unbounded) and the mean finite width."""
    if not isinstance(intervals, list):
        raise ValueError("intervals is a list of [lower, upper]")
    values = numerics.vector(targets, "targets", minimum_length=len(intervals), maximum_length=len(intervals))
    hits, widths = 0, []
    for index, (pair, target) in enumerate(zip(intervals, values)):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"intervals[{index}] must be [lower, upper]")
        lower = -math.inf if pair[0] is None else numerics.finite_number(pair[0], f"intervals[{index}][0]")
        upper = math.inf if pair[1] is None else numerics.finite_number(pair[1], f"intervals[{index}][1]")
        hits += lower <= target <= upper
        if math.isfinite(lower) and math.isfinite(upper):
            widths.append(upper - lower)
    return {"coverage": hits / len(values), "mean_width": math.fsum(widths) / len(widths) if widths else None,
            "count": len(values)}


def coverage_simulation(repetitions, calibration_size, test_size, alpha, noise, seed):
    """Seeded check on y = 2x + noise * N(0, 1), x ~ U(0, 1), predictor 2x: mean coverage over repetitions.

    Returns {"mean_coverage", "expected" (k / (n + 1) for continuous residuals), "repetitions"}."""
    repetitions = numerics.integer(repetitions, "repetitions", minimum=1, maximum=10000)
    calibration_size = numerics.integer(calibration_size, "calibration_size", minimum=1, maximum=100000)
    test_size = numerics.integer(test_size, "test_size", minimum=1, maximum=100000)
    noise = numerics.finite_number(noise, "noise")
    generator = numerics.seeded_random(seed)
    total = 0.0
    for _ in range(repetitions):
        def draw(count):
            xs = numerics.uniforms(generator, count)
            errors = numerics.standard_normals(generator, count)
            return [2 * x for x in xs], [2 * x + noise * e for x, e in zip(xs, errors)]
        cal_predictions, cal_targets = draw(calibration_size)
        test_predictions, test_targets = draw(test_size)
        result = split_conformal(cal_predictions, cal_targets, test_predictions, alpha)
        total += coverage(result["intervals"], test_targets)["coverage"]
    index = math.ceil((calibration_size + 1) * (1 - _alpha(alpha)))
    expected = 1.0 if index > calibration_size else index / (calibration_size + 1)
    return {"mean_coverage": total / repetitions, "expected": expected, "repetitions": repetitions}


FUNCTIONS = {"conformal_quantile": conformal_quantile, "split_conformal": split_conformal, "coverage": coverage,
             "coverage_simulation": coverage_simulation}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["conformal_quantile", "split_conformal", "coverage", "coverage_simulation", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
