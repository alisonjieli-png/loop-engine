"""Maximum mean discrepancy (MMD) between two samples with a Gaussian (RBF) kernel, and a permutation test.

    k(x, y) = exp(-||x - y||^2 / (2 sigma^2))
    biased MMD^2   = mean_(i,j) k(x_i, x_j) + mean_(i,j) k(y_i, y_j) - 2 mean_(i,j) k(x_i, y_j)
    unbiased MMD^2 = same with the diagonal terms k(x_i, x_i), k(y_j, y_j) left out of the first two means

The biased form is never negative and is 0 for identical samples. The unbiased form has expectation equal to the
population MMD^2 and can be negative; it must not be clamped or square-rooted. sigma defaults to the median of the
pairwise distances of the pooled sample (zero distances excluded). The permutation test reshuffles the pooled sample
with a seeded Fisher-Yates shuffle and reports p = (1 + #{permuted >= observed}) / (1 + B), which is a valid p-value
for the hypothesis that both samples come from one distribution.

    echo '{"call": "mmd_squared", "arguments": {"x_rows": [[0], [1]], "y_rows": [[2], [3]], "bandwidth": 1}}' | python3 rbf_maximum_mean_discrepancy.py
"""
from __future__ import annotations

import math
import statistics

import atom_cli
import numerics


def _samples(x_rows, y_rows, minimum):
    x = numerics.matrix(x_rows, "x_rows", minimum_rows=minimum, maximum_rows=5000)
    y = numerics.matrix(y_rows, "y_rows", minimum_rows=minimum, maximum_rows=5000)
    if len(x[0]) != len(y[0]):
        raise ValueError("the two samples differ in dimension")
    return x, y


def _squared_distance(a, b):
    return math.fsum((p - q) * (p - q) for p, q in zip(a, b))


def median_bandwidth(rows):
    """The median of the pairwise Euclidean distances between distinct rows (zero distances excluded)."""
    points = numerics.matrix(rows, "rows", minimum_rows=2, maximum_rows=5000)
    distances = [math.sqrt(_squared_distance(points[i], points[j]))
                 for i in range(len(points)) for j in range(i + 1, len(points))]
    positive = [value for value in distances if value > 0]
    if not positive:
        raise ValueError("all rows are identical; the median heuristic is undefined")
    return statistics.median(positive)


def _bandwidth(bandwidth, pooled):
    if bandwidth is None:
        return median_bandwidth(pooled)
    value = numerics.finite_number(bandwidth, "bandwidth")
    if value <= 0:
        raise ValueError("bandwidth must be positive")
    return value


def _kernel_matrix(points, sigma):
    scale = 2.0 * sigma * sigma
    return [[math.exp(-_squared_distance(a, b) / scale) for b in points] for a in points]


def _statistic(kernel, first, second, unbiased):
    m, n = len(first), len(second)
    if unbiased:
        xx = math.fsum(kernel[i][j] for i in first for j in first if i != j) / (m * (m - 1))
        yy = math.fsum(kernel[i][j] for i in second for j in second if i != j) / (n * (n - 1))
    else:
        xx = math.fsum(kernel[i][j] for i in first for j in first) / (m * m)
        yy = math.fsum(kernel[i][j] for i in second for j in second) / (n * n)
    xy = math.fsum(kernel[i][j] for i in first for j in second) / (m * n)
    return xx + yy - 2.0 * xy


def mmd_squared(x_rows, y_rows, bandwidth=None, unbiased=False):
    """MMD^2 between two samples of equal dimension (the unbiased form needs at least 2 rows in each).

    Returns {"mmd_squared", "bandwidth", "estimator" ("biased" or "unbiased")}."""
    x, y = _samples(x_rows, y_rows, 2 if unbiased else 1)
    sigma = _bandwidth(bandwidth, x + y)
    kernel = _kernel_matrix(x + y, sigma)
    first, second = list(range(len(x))), list(range(len(x), len(x) + len(y)))
    return {"mmd_squared": _statistic(kernel, first, second, bool(unbiased)), "bandwidth": sigma,
            "estimator": "unbiased" if unbiased else "biased"}


def permutation_test(x_rows, y_rows, bandwidth=None, permutations=200, seed=0):
    """Permutation p-value for "both samples come from one distribution", using the biased MMD^2.

    Returns {"statistic", "p_value", "permutations", "bandwidth"}."""
    x, y = _samples(x_rows, y_rows, 1)
    permutations = numerics.integer(permutations, "permutations", minimum=1, maximum=100000)
    pooled = x + y
    sigma = _bandwidth(bandwidth, pooled)
    kernel = _kernel_matrix(pooled, sigma)
    indices = list(range(len(pooled)))
    observed = _statistic(kernel, indices[:len(x)], indices[len(x):], False)
    generator = numerics.seeded_random(seed)
    exceed = 0
    for _ in range(permutations):
        order = numerics.shuffled(generator, indices)
        if _statistic(kernel, order[:len(x)], order[len(x):], False) >= observed - 1e-12:
            exceed += 1
    return {"statistic": observed, "p_value": (1 + exceed) / (1 + permutations), "permutations": permutations,
            "bandwidth": sigma}


FUNCTIONS = {"mmd_squared": mmd_squared, "permutation_test": permutation_test, "median_bandwidth": median_bandwidth}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["mmd_squared", "permutation_test", "median_bandwidth", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
