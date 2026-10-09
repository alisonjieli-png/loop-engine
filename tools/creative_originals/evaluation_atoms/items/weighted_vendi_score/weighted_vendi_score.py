"""Weighted Vendi score: the effective number of distinct members of a weighted set under a similarity kernel.

    score_q = exp(H_q(lambda)),  lambda = eigenvalues of D^(1/2) K D^(1/2)

K is a positive semidefinite similarity matrix with a unit diagonal and D the diagonal matrix of the weights
normalized to sum to 1, so the eigenvalues sum to 1. H_q is the Renyi entropy of order q (Shannon entropy at q = 1,
log of the count of positive eigenvalues at q = 0). With equal weights this is the Vendi score of the plain set.

Properties the tests check: n mutually orthogonal members with equal weights score n; identical members score 1;
splitting one member into identical clones whose weights sum to its weight leaves the score unchanged, because
the nonzero eigenvalues equal those of sum_i w_i phi_i phi_i^T for unit features phi_i.

    echo '{"call": "weighted_vendi_score", "arguments": {"similarity": [[1, 0], [0, 1]]}}' | python3 weighted_vendi_score.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

#: Eigenvalues at or below this value count as zero (they are rounding noise of a positive semidefinite matrix).
EIGEN_FLOOR = 1e-12


def _weights(weights, size):
    if weights is None:
        return [1.0 / size] * size
    values = numerics.vector(weights, "weights", minimum_length=size, maximum_length=size)
    if any(value < 0 for value in values):
        raise ValueError("weights must be non-negative")
    total = math.fsum(values)
    if total <= 0:
        raise ValueError("weights must have a positive sum")
    return [value / total for value in values]


def _entropy_score(eigenvalues, order):
    positive = [value for value in eigenvalues if value > 0]
    if order == 0:
        return float(len(positive))
    if order == 1:
        return math.exp(-math.fsum(value * math.log(value) for value in positive))
    return math.exp(math.log(math.fsum(value ** order for value in positive)) / (1.0 - order))


def weighted_vendi_score(similarity, weights=None, order=1.0):
    """The Vendi score of a weighted set: exp of the order-q entropy of the eigenvalues of D^(1/2) K D^(1/2).

    similarity: symmetric positive semidefinite matrix with a unit diagonal (n by n).
    weights: n non-negative numbers with a positive sum, normalized internally; equal weights when omitted.
    order: the Renyi order q >= 0 (1 is the Shannon form).
    Returns {"score", "order", "eigenvalues" (normalized, descending), "weights" (normalized), "members"}."""
    kernel = numerics.symmetric_matrix(similarity, "similarity")
    size = len(kernel)
    if any(abs(kernel[i][i] - 1.0) > 1e-9 for i in range(size)):
        raise ValueError("similarity must have a unit diagonal")
    order = numerics.finite_number(order, "order")
    if order < 0:
        raise ValueError("order must be non-negative")
    normalized = _weights(weights, size)
    kernel_values, _vectors = numerics.symmetric_eigen(kernel)
    if kernel_values[-1] < -1e-9 * size:
        raise ValueError("similarity must be positive semidefinite")
    roots = [math.sqrt(value) for value in normalized]
    scaled = [[roots[i] * kernel[i][j] * roots[j] for j in range(size)] for i in range(size)]
    values, _vectors = numerics.symmetric_eigen(scaled)
    clipped = [value if value > EIGEN_FLOOR else 0.0 for value in values]
    total = math.fsum(clipped)
    eigenvalues = [value / total for value in clipped]
    return {"score": _entropy_score(eigenvalues, order), "order": order, "eigenvalues": eigenvalues,
            "weights": normalized, "members": size}


def vendi_from_features(features, weights=None, order=1.0):
    """The weighted Vendi score under the cosine similarity of feature rows (each row is scaled to unit length).

    features: n rows of equal length, none of them all zero. Returns the weighted_vendi_score result plus
    "similarity", the cosine matrix that was scored."""
    rows = numerics.matrix(features, "features")
    units = []
    for index, row in enumerate(rows):
        length = numerics.vector_norm(row)
        if length == 0:
            raise ValueError(f"features[{index}] is all zero")
        units.append([value / length for value in row])
    similarity = [[min(1.0, max(-1.0, numerics.dot(a, b))) for b in units] for a in units]
    for i in range(len(similarity)):
        similarity[i][i] = 1.0
    result = weighted_vendi_score(similarity, weights, order)
    result["similarity"] = similarity
    return result


FUNCTIONS = {"weighted_vendi_score": weighted_vendi_score, "vendi_from_features": vendi_from_features}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["EIGEN_FLOOR", "weighted_vendi_score", "vendi_from_features", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
