"""Correlation source decomposition: how much of Cov(Y, P) comes from within groups and how much from between them.

    Cov(Y, P) = E_G[Cov(Y, P | G)] + Cov(E[Y | G], E[P | G])

with population moments (divide by n) and the empirical group weights n_g / n. Every input float is converted to its
exact rational value (fractions.Fraction) and the moments are computed in rational arithmetic, so the identity holds
exactly: identity_residual is 0.0, not merely small. Use it to see whether a correlation between a score Y and a
prediction P is carried by differences between groups (tasks, sources, difficulty levels) rather than within them.

    echo '{"call": "decompose_covariance", "arguments": {"y": [1, 3, 5, 7], "p": [2, 4, 1, 3], "groups": ["a", "a", "b", "b"]}}' | python3 correlation_source_decomposition.py
"""
from __future__ import annotations

import math
from fractions import Fraction

import atom_cli
import numerics


def _exact(values, name):
    return [Fraction(value) for value in numerics.vector(values, name)]


def _covariance(xs, ys):
    mean_x = sum(xs, Fraction(0)) / len(xs)
    mean_y = sum(ys, Fraction(0)) / len(ys)
    return sum(((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)), Fraction(0)) / len(xs), mean_x, mean_y


def _label_key(label):
    return (type(label).__name__, label)


def decompose_covariance(y, p, groups):
    """Split the population covariance of y and p into a within-group and a between-group part.

    y, p: equal-length lists of numbers; groups: one text or integer label per row.
    Returns {"total_covariance", "within_group", "between_group", "identity_residual" (exactly 0.0),
    "total_correlation" (null when either variance is 0), "within_share" and "between_share" (null when the total
    is 0), "sign_conflict" (the two parts are non-zero with opposite signs), "groups": [{"group", "count", "weight",
    "mean_y", "mean_p", "covariance"}]}."""
    ys, ps = _exact(y, "y"), _exact(p, "p")
    labels = numerics.labels(groups, "groups")
    if not (len(ys) == len(ps) == len(labels)):
        raise ValueError("y, p and groups must have the same length")
    count = len(ys)
    total, mean_y, mean_p = _covariance(ys, ps)
    members = {}
    for index, label in enumerate(labels):
        members.setdefault(label, []).append(index)
    within, between, rows = Fraction(0), Fraction(0), []
    for label in sorted(members, key=_label_key):
        indices = members[label]
        weight = Fraction(len(indices), count)
        covariance, group_y, group_p = _covariance([ys[i] for i in indices], [ps[i] for i in indices])
        within += weight * covariance
        between += weight * (group_y - mean_y) * (group_p - mean_p)
        rows.append({"group": label, "count": len(indices), "weight": float(weight), "mean_y": float(group_y),
                     "mean_p": float(group_p), "covariance": float(covariance)})
    variance_y = _covariance(ys, ys)[0]
    variance_p = _covariance(ps, ps)[0]
    correlation = None
    if variance_y > 0 and variance_p > 0:
        correlation = float(total) / math.sqrt(float(variance_y) * float(variance_p))
        correlation = max(-1.0, min(1.0, correlation))
    return {"total_covariance": float(total), "within_group": float(within), "between_group": float(between),
            "identity_residual": float(total - within - between), "total_correlation": correlation,
            "within_share": float(within / total) if total != 0 else None,
            "between_share": float(between / total) if total != 0 else None,
            "sign_conflict": within != 0 and between != 0 and (within > 0) != (between > 0), "groups": rows}


def decompose_variance(y, groups):
    """The law of total variance, Var(Y) = E[Var(Y | G)] + Var(E[Y | G]), as decompose_covariance(y, y, groups)."""
    result = decompose_covariance(y, y, groups)
    return {"total_variance": result["total_covariance"], "within_group": result["within_group"],
            "between_group": result["between_group"], "identity_residual": result["identity_residual"],
            "groups": result["groups"]}


FUNCTIONS = {"decompose_covariance": decompose_covariance, "decompose_variance": decompose_variance}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["decompose_covariance", "decompose_variance", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
