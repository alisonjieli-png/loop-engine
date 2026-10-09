"""Covariance intersection: fuse two estimates whose error cross-correlation is unknown, without overconfidence.

    C^-1 = omega A^-1 + (1 - omega) B^-1
    c    = C (omega A^-1 a + (1 - omega) B^-1 b),     omega in [0, 1]

omega minimizes trace(C) (or det(C)). Both objectives are convex in omega, so their derivatives are non-decreasing
and omega is found by bisection on the sign of the derivative, to about 1e-16. For every omega in [0, 1] and every
joint error covariance whose diagonal blocks are A and B, C minus the true covariance of the fused error is positive
semidefinite, so the fused estimate never claims more certainty than it has. Fusing an estimate with an exact
duplicate of itself returns it unchanged; the independence (Kalman) rule would halve its covariance.

    echo '{"call": "covariance_intersection", "arguments": {"mean_a": [0], "covariance_a": [[1]], "mean_b": [3], "covariance_b": [[4]]}}' | python3 covariance_intersection_fusion.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

def _estimate(mean, covariance, label):
    m = numerics.vector(mean, f"mean_{label}")
    c = numerics.symmetric_matrix(covariance, f"covariance_{label}")
    if len(c) != len(m):
        raise ValueError(f"covariance_{label} must be {len(m)} by {len(m)}")
    numerics.cholesky(c, f"covariance_{label}")
    return m, c


def _fused(a, a_info, b, b_info, omega):
    information = numerics.add(numerics.scale(a_info, omega), numerics.scale(b_info, 1.0 - omega))
    covariance = numerics.inverse(information)
    size = len(covariance)
    covariance = [[(covariance[i][j] + covariance[j][i]) / 2.0 for j in range(size)] for i in range(size)]
    weighted = [omega * p + (1.0 - omega) * q for p, q in zip(numerics.matvec(a_info, a), numerics.matvec(b_info, b))]
    return numerics.matvec(covariance, weighted), covariance


def _objective(covariance, criterion):
    return numerics.trace(covariance) if criterion == "trace" else math.log(numerics.determinant(covariance))


def covariance_intersection(mean_a, covariance_a, mean_b, covariance_b, criterion="trace", omega=None):
    """Fuse (a, A) and (b, B) by covariance intersection.

    criterion: "trace" or "determinant", the size measure of C minimized over omega in [0, 1].
    omega: a fixed weight in [0, 1] instead of the search.
    Returns {"mean", "covariance", "omega", "objective"} where objective is trace(C) or log det(C)."""
    a, a_cov = _estimate(mean_a, covariance_a, "a")
    b, b_cov = _estimate(mean_b, covariance_b, "b")
    if len(a) != len(b):
        raise ValueError("the two estimates differ in dimension")
    if criterion not in ("trace", "determinant"):
        raise ValueError("criterion is 'trace' or 'determinant'")
    a_info, b_info = numerics.inverse(a_cov), numerics.inverse(b_cov)
    difference = numerics.subtract(a_info, b_info)

    def slope(weight):
        """d/d omega of the objective: -trace(C D C) for the trace, -trace(C D) for log det; non-decreasing."""
        covariance = _fused(a, a_info, b, b_info, weight)[1]
        product = numerics.matmul(covariance, difference)
        return -numerics.trace(numerics.matmul(product, covariance) if criterion == "trace" else product)

    if omega is not None:
        weight = numerics.probability(omega, "omega")
    else:
        scale = max(1.0, max(abs(value) for row in a_info + b_info for value in row))
        at_zero, at_one = slope(0.0), slope(1.0)
        if abs(at_zero) <= 1e-13 * scale and abs(at_one) <= 1e-13 * scale:
            weight = 0.5  # the objective is flat: every omega gives the same covariance
        elif at_zero >= 0.0:
            weight = 0.0
        elif at_one <= 0.0:
            weight = 1.0
        else:
            low, high = 0.0, 1.0
            for _ in range(200):
                middle = (low + high) / 2.0
                if slope(middle) < 0.0:
                    low = middle
                else:
                    high = middle
                if high - low <= 1e-16:
                    break
            weight = (low + high) / 2.0
    mean, covariance = _fused(a, a_info, b, b_info, weight)
    return {"mean": mean, "covariance": covariance, "omega": weight, "objective": _objective(covariance, criterion)}


def independent_fusion(mean_a, covariance_a, mean_b, covariance_b):
    """The fusion that assumes independent errors: C = (A^-1 + B^-1)^-1, c = C (A^-1 a + B^-1 b).

    Correct only when the two errors are uncorrelated; shown for comparison. Returns {"mean", "covariance"}."""
    a, a_cov = _estimate(mean_a, covariance_a, "a")
    b, b_cov = _estimate(mean_b, covariance_b, "b")
    if len(a) != len(b):
        raise ValueError("the two estimates differ in dimension")
    a_info, b_info = numerics.inverse(a_cov), numerics.inverse(b_cov)
    covariance = numerics.inverse(numerics.add(a_info, b_info))
    weighted = [p + q for p, q in zip(numerics.matvec(a_info, a), numerics.matvec(b_info, b))]
    return {"mean": numerics.matvec(covariance, weighted), "covariance": covariance}


def conservative_margin(claimed_covariance, actual_covariance):
    """The smallest eigenvalue of claimed minus actual; non-negative means the claimed covariance is conservative.

    Returns {"smallest_eigenvalue", "conservative"} with a tolerance of 1e-10 times the scale of the inputs."""
    claimed = numerics.symmetric_matrix(claimed_covariance, "claimed_covariance")
    actual = numerics.symmetric_matrix(actual_covariance, "actual_covariance")
    if len(claimed) != len(actual):
        raise ValueError("the two covariances differ in dimension")
    values, _vectors = numerics.symmetric_eigen(numerics.subtract(claimed, actual))
    scale = max(1.0, max(abs(value) for row in claimed + actual for value in row))
    return {"smallest_eigenvalue": values[-1], "conservative": values[-1] >= -1e-10 * scale}


FUNCTIONS = {"covariance_intersection": covariance_intersection, "independent_fusion": independent_fusion,
             "conservative_margin": conservative_margin}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["covariance_intersection", "independent_fusion", "conservative_margin", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
