"""The ridge penalty that weight decay induces through a frozen linear transform.

A model predicts X beta with beta = A w, where A (k by m, full row rank, k <= m) is frozen and only w is trained with
the penalty ridge * ||w||^2. The fitted beta equals the generalized ridge estimate

    beta = argmin ||y - X beta||^2 + ridge * beta^T P beta,   P = (A A^T)^(-1)

because the smallest ||w||^2 with A w = beta is beta^T (A A^T)^(-1) beta and the trained w lies in the row space of
A. Duplicating every column (A = [I, I]) gives P = I / 2, so the effective penalty halves; scaling A by c divides
the penalty by c^2.

    echo '{"call": "induced_penalty", "arguments": {"transform": [[1, 0, 1, 0], [0, 1, 0, 1]]}}' | python3 ridge_penalty_from_linear_transform.py
"""
from __future__ import annotations

import atom_cli
import numerics


def _transform(transform):
    a = numerics.matrix(transform, "transform")
    if len(a) > len(a[0]):
        raise ValueError("transform must have at most as many rows as columns to have full row rank")
    gram = numerics.matmul(a, numerics.transpose(a))
    try:
        numerics.cholesky(gram, "transform times its transpose")
    except ValueError:
        raise ValueError("transform must have full row rank") from None
    return a, gram


def _data(features, targets, width):
    x = numerics.matrix(features, "features", minimum_columns=width)
    if len(x[0]) != width:
        raise ValueError(f"features must have {width} columns")
    y = numerics.vector(targets, "targets", minimum_length=len(x), maximum_length=len(x))
    return x, y


def _ridge(ridge):
    value = numerics.finite_number(ridge, "ridge")
    if value <= 0:
        raise ValueError("ridge must be positive")
    return value


def induced_penalty(transform):
    """P = (A A^T)^(-1) for a full-row-rank transform A, with its eigenvalues (the per-direction penalty scales).

    Returns {"penalty_matrix", "eigenvalues" (descending), "rows", "columns"}."""
    a, gram = _transform(transform)
    inverse = numerics.inverse(gram)
    size = len(inverse)
    penalty = [[(inverse[i][j] + inverse[j][i]) / 2.0 for j in range(size)] for i in range(size)]
    values, _vectors = numerics.symmetric_eigen(penalty)
    return {"penalty_matrix": penalty, "eigenvalues": values, "rows": len(a), "columns": len(a[0])}


def fit_through_transform(features, targets, transform, ridge):
    """Ridge regression in the trainable space: w = argmin ||y - X A w||^2 + ridge ||w||^2, and beta = A w.

    features: n rows of k numbers; targets: n numbers; transform: k by m full-row-rank matrix; ridge > 0.
    Returns {"weights": w, "coefficients": beta}."""
    a, _gram = _transform(transform)
    x, y = _data(features, targets, len(a))
    design = numerics.matmul(x, a)
    weights = numerics.least_squares(design, y, _ridge(ridge))
    return {"weights": weights, "coefficients": numerics.matvec(a, weights)}


def fit_generalized_ridge(features, targets, penalty_matrix, ridge):
    """beta = (X^T X + ridge P)^(-1) X^T y for a symmetric positive semidefinite penalty matrix P.

    Returns {"coefficients": beta}."""
    p = numerics.symmetric_matrix(penalty_matrix, "penalty_matrix")
    values, _vectors = numerics.symmetric_eigen(p)
    if values[-1] < -1e-9 * max(1.0, abs(values[0])):
        raise ValueError("penalty_matrix must be positive semidefinite")
    x, y = _data(features, targets, len(p))
    strength = _ridge(ridge)
    xt = numerics.transpose(x)
    system = numerics.add(numerics.matmul(xt, x), numerics.scale(p, strength))
    return {"coefficients": numerics.solve(system, numerics.matvec(xt, y))}


def compile_penalty(features, targets, transform, ridge):
    """Both routes side by side: the induced penalty, the coefficients from training w, the coefficients from the
    generalized ridge with P = (A A^T)^(-1), and the largest absolute difference between them."""
    penalty = induced_penalty(transform)
    through = fit_through_transform(features, targets, transform, ridge)
    direct = fit_generalized_ridge(features, targets, penalty["penalty_matrix"], ridge)
    difference = max(abs(p - q) for p, q in zip(through["coefficients"], direct["coefficients"]))
    return {"penalty_matrix": penalty["penalty_matrix"], "eigenvalues": penalty["eigenvalues"],
            "coefficients_via_weights": through["coefficients"], "coefficients_via_penalty": direct["coefficients"],
            "max_abs_difference": difference}


FUNCTIONS = {"induced_penalty": induced_penalty, "fit_through_transform": fit_through_transform,
             "fit_generalized_ridge": fit_generalized_ridge, "compile_penalty": compile_penalty}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["induced_penalty", "fit_through_transform", "fit_generalized_ridge", "compile_penalty", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
