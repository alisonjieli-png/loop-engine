"""Ledoit-Wolf linear shrinkage of a sample covariance toward a scaled identity.

    S      = X_c^T X_c / n                               (X_c: columns centred unless assume_centered)
    mu     = trace(S) / p
    d^2    = ||S - mu I||^2 / p                           (squared Frobenius norm divided by p)
    bbar^2 = (1 / n^2) sum_k ||x_k x_k^T - S||^2 / p
    delta  = min(bbar^2, d^2) / d^2                       (0 when d^2 = 0: S is already a multiple of I)
    Sigma  = delta mu I + (1 - delta) S

The shrunk matrix is positive definite whenever delta > 0, even when there are fewer rows than columns and S is
singular. Ledoit and Wolf show that delta estimates the intensity minimizing the expected Frobenius loss, with a
consistency guarantee as n and p grow; for a fixed small sample it is an estimate, not the oracle value.

    echo '{"call": "ledoit_wolf", "arguments": {"rows": [[1, 2], [2, 1], [3, 4], [4, 3], [5, 7]]}}' | python3 ledoit_wolf_shrinkage.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics


def _centred(rows, assume_centered):
    x = numerics.matrix(rows, "rows", minimum_rows=2)
    if assume_centered:
        return x
    means = [math.fsum(column) / len(x) for column in zip(*x)]
    return [[value - centre for value, centre in zip(row, means)] for row in x]


def _frobenius_squared(a):
    return math.fsum(value * value for row in a for value in row)


def ledoit_wolf(rows, assume_centered=False):
    """The Ledoit-Wolf estimate for a data matrix with one observation per row (at least 2 rows).

    Returns {"covariance", "sample_covariance", "shrinkage", "target_scale", "d_squared", "b_bar_squared",
    "smallest_eigenvalue", "sample_smallest_eigenvalue"}."""
    x = _centred(rows, bool(assume_centered))
    n, p = len(x), len(x[0])
    sample = [[math.fsum(row[i] * row[j] for row in x) / n for j in range(p)] for i in range(p)]
    scale = numerics.trace(sample) / p
    deviation = [[sample[i][j] - (scale if i == j else 0.0) for j in range(p)] for i in range(p)]
    d_squared = _frobenius_squared(deviation) / p
    b_bar_squared = math.fsum(
        _frobenius_squared([[row[i] * row[j] - sample[i][j] for j in range(p)] for i in range(p)]) for row in x
    ) / (n * n * p)
    shrinkage = 0.0 if d_squared == 0 else min(b_bar_squared, d_squared) / d_squared
    covariance = [[(1.0 - shrinkage) * sample[i][j] + (shrinkage * scale if i == j else 0.0) for j in range(p)]
                  for i in range(p)]
    return {"covariance": covariance, "sample_covariance": sample, "shrinkage": shrinkage, "target_scale": scale,
            "d_squared": d_squared, "b_bar_squared": b_bar_squared,
            "smallest_eigenvalue": numerics.symmetric_eigen(covariance)[0][-1],
            "sample_smallest_eigenvalue": numerics.symmetric_eigen(sample)[0][-1]}


def shrink(covariance, shrinkage):
    """Sigma = shrinkage (trace / p) I + (1 - shrinkage) S for a given covariance and intensity in [0, 1]."""
    s = numerics.symmetric_matrix(covariance, "covariance")
    delta = numerics.probability(shrinkage, "shrinkage")
    p = len(s)
    scale = numerics.trace(s) / p
    return [[(1.0 - delta) * s[i][j] + (delta * scale if i == j else 0.0) for j in range(p)] for i in range(p)]


FUNCTIONS = {"ledoit_wolf": ledoit_wolf, "shrink": shrink}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["ledoit_wolf", "shrink", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
