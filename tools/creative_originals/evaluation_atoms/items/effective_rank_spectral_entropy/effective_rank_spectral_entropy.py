"""Effective rank of a representation matrix: how many directions its variance actually uses.

With singular values sigma_1 >= ... >= sigma_r of the matrix (rows are samples, columns are features):

    effective_rank      = exp(H(p)),  p_i = sigma_i / sum_j sigma_j          (Roy and Vetterli)
    participation_ratio = (sum sigma_i^2)^2 / sum sigma_i^4                 (on the eigenvalues sigma_i^2)
    stable_rank         = sum sigma_i^2 / sigma_1^2

All three equal k for k equal non-zero singular values and 1 for a rank-one matrix. Singular values come from the
eigenvalues of the smaller Gram matrix (A^T A or A A^T) by Jacobi rotations. Option center subtracts column means
first, which is usual for representations.

    echo '{"call": "spectral_dimensions", "arguments": {"matrix": [[2, 0, 0], [0, 1, 0], [0, 0, 1]]}}' | python3 effective_rank_spectral_entropy.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

#: Singular values at or below this fraction of the largest count as zero.
RELATIVE_CUTOFF = 1e-12


def singular_values(matrix, center=False):
    """The singular values of a matrix (descending), computed from the smaller Gram matrix."""
    a = numerics.matrix(matrix, "matrix")
    if center:
        means = [math.fsum(column) / len(a) for column in zip(*a)]
        a = [[value - mean for value, mean in zip(row, means)] for row in a]
    gram = (numerics.matmul(numerics.transpose(a), a) if len(a[0]) <= len(a)
            else numerics.matmul(a, numerics.transpose(a)))
    values = numerics.symmetric_eigen(gram)[0]
    sigma = [math.sqrt(max(value, 0.0)) for value in values]
    top = sigma[0] if sigma else 0.0
    return [value if top > 0 and value > RELATIVE_CUTOFF * top else 0.0 for value in sigma]


def spectral_dimensions(matrix, center=False):
    """Effective rank, participation ratio and stable rank of a non-zero matrix.

    Returns {"singular_values", "effective_rank", "participation_ratio", "stable_rank", "numerical_rank"}."""
    sigma = singular_values(matrix, center)
    positive = [value for value in sigma if value > 0]
    if not positive:
        raise ValueError("the matrix is zero (after centring); its dimensions are undefined")
    total = math.fsum(positive)
    shares = [value / total for value in positive]
    entropy = -math.fsum(share * math.log(share) for share in shares)
    squares = [value * value for value in positive]
    return {"singular_values": sigma, "effective_rank": math.exp(entropy),
            "participation_ratio": math.fsum(squares) ** 2 / math.fsum(s * s for s in squares),
            "stable_rank": math.fsum(squares) / squares[0], "numerical_rank": len(positive)}


FUNCTIONS = {"spectral_dimensions": spectral_dimensions, "singular_values": singular_values}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["RELATIVE_CUTOFF", "singular_values", "spectral_dimensions", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
