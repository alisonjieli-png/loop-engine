"""Silent concept-shift twins: two datasets with identical input and target marginals and opposite relationships.

Antithetic construction. Draw inputs x_i (standard normal, dimension d), a slope w and noise e_i1, e_i2 ~ N(0, s^2):

    reference rows:  (x_i,  w.x_i + e_i1)   and   (-x_i, -w.x_i + e_i2)
    shifted rows:    (x_i, -w.x_i + e_i2)   and   (-x_i,  w.x_i + e_i1)       (rows then shuffled)

Both datasets hold the same multiset of inputs and the same multiset of targets, so every statistic of the inputs
alone, or of the targets alone, takes exactly the same value on both: an input-only drift monitor cannot see the
shift. The relationship flips: every input-target covariance of the shifted twin is exactly the negative of the
reference one (input means are exactly 0, and each shifted product is the negative of a reference product).
With labels=true the targets become 1{y > 0}; label multisets also match and the covariances still flip.

    echo '{"call": "silent_shift_report", "arguments": {"n_pairs": 50, "dimension": 2, "seed": 3}}' | python3 silent_concept_shift_twins.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics


def generate_twins(n_pairs, dimension, seed, noise=0.5, slope=None, labels=False):
    """Two datasets of 2 n_pairs rows each: {"reference": {"inputs", "targets"}, "shifted": {"inputs", "targets"},
    "slope"}. The slope is drawn as a seeded unit vector when omitted. Draw order: slope, inputs, noise, shuffle."""
    n_pairs = numerics.integer(n_pairs, "n_pairs", minimum=1, maximum=50000)
    dimension = numerics.integer(dimension, "dimension", minimum=1, maximum=100)
    noise = numerics.finite_number(noise, "noise")
    if noise < 0:
        raise ValueError("noise must be non-negative")
    generator = numerics.seeded_random(seed)
    if slope is None:
        direction = numerics.standard_normals(generator, dimension)
        length = numerics.vector_norm(direction)
        w = [value / length for value in direction]
    else:
        w = numerics.vector(slope, "slope", minimum_length=dimension, maximum_length=dimension)
    inputs = [numerics.standard_normals(generator, dimension) for _ in range(n_pairs)]
    noises = [numerics.standard_normals(generator, 2) for _ in range(n_pairs)]
    reference_rows, shifted_rows = [], []
    for x, (first, second) in zip(inputs, noises):
        signal = numerics.dot(w, x)
        up, down = signal + noise * first, -signal + noise * second
        negative = [-value for value in x]
        reference_rows += [(x, up), (negative, down)]
        shifted_rows += [(x, down), (negative, up)]
    shifted_rows = numerics.shuffled(generator, shifted_rows)

    def pack(rows):
        targets = [(1.0 if y > 0 else 0.0) if labels else y for _x, y in rows]
        return {"inputs": [list(x) for x, _y in rows], "targets": targets}

    return {"reference": pack(reference_rows), "shifted": pack(shifted_rows), "slope": w}


def _ks(a, b):
    """Two-sample Kolmogorov-Smirnov statistic: the largest gap between the two empirical distribution functions."""
    a, b = sorted(a), sorted(b)
    i = j = 0
    gap = 0.0
    for value in sorted(set(a) | set(b)):
        while i < len(a) and a[i] <= value:
            i += 1
        while j < len(b) and b[j] <= value:
            j += 1
        gap = max(gap, abs(i / len(a) - j / len(b)))
    return gap


def _marginal(a, b):
    return {"mean_gap": abs(numerics.mean(a) - numerics.mean(b)),
            "variance_gap": abs(numerics.variance(a, 0) - numerics.variance(b, 0)), "ks": _ks(a, b)}


def input_only_statistics(inputs_a, inputs_b):
    """Per-feature mean gap, variance gap and two-sample KS statistic between two input tables, with their maxima."""
    a = numerics.matrix(inputs_a, "inputs_a")
    b = numerics.matrix(inputs_b, "inputs_b")
    if len(a[0]) != len(b[0]):
        raise ValueError("the two input tables differ in width")
    features = [_marginal([row[k] for row in a], [row[k] for row in b]) for k in range(len(a[0]))]
    return {"features": features, "max_mean_gap": max(f["mean_gap"] for f in features),
            "max_variance_gap": max(f["variance_gap"] for f in features), "max_ks": max(f["ks"] for f in features)}


def target_only_statistics(targets_a, targets_b):
    """Mean gap, variance gap and KS statistic between two target lists."""
    return _marginal(numerics.vector(targets_a, "targets_a"), numerics.vector(targets_b, "targets_b"))


def joint_statistics(inputs, targets):
    """Population covariance of each input feature with the target."""
    x = numerics.matrix(inputs, "inputs")
    y = numerics.vector(targets, "targets", minimum_length=len(x), maximum_length=len(x))
    return {"covariance": [numerics.covariance([row[k] for row in x], y, ddof=0) for k in range(len(x[0]))]}


def silent_shift_report(n_pairs, dimension, seed, noise=0.5, labels=False):
    """Generate twins and compare them by input-only, target-only and joint statistics.

    Returns {"input_max_ks", "input_max_mean_gap", "input_max_variance_gap", "target_ks", "target_mean_gap",
    "input_statistics_identical", "joint_covariance_reference", "joint_covariance_shifted",
    "joint_covariance_sum_max_abs", "joint_sign_flipped"}."""
    twins = generate_twins(n_pairs, dimension, seed, noise, None, labels)
    reference, shifted = twins["reference"], twins["shifted"]
    inputs = input_only_statistics(reference["inputs"], shifted["inputs"])
    targets = target_only_statistics(reference["targets"], shifted["targets"])
    before = joint_statistics(reference["inputs"], reference["targets"])["covariance"]
    after = joint_statistics(shifted["inputs"], shifted["targets"])["covariance"]
    total = max(abs(p + q) for p, q in zip(before, after))
    return {"input_max_ks": inputs["max_ks"], "input_max_mean_gap": inputs["max_mean_gap"],
            "input_max_variance_gap": inputs["max_variance_gap"], "target_ks": targets["ks"],
            "target_mean_gap": targets["mean_gap"],
            "input_statistics_identical": inputs["max_ks"] == 0 and inputs["max_mean_gap"] == 0
            and inputs["max_variance_gap"] == 0,
            "joint_covariance_reference": before, "joint_covariance_shifted": after,
            "joint_covariance_sum_max_abs": total,
            "joint_sign_flipped": all(math.copysign(1.0, p) == -math.copysign(1.0, q) for p, q in zip(before, after)
                                      if p != 0)}


FUNCTIONS = {"generate_twins": generate_twins, "input_only_statistics": input_only_statistics,
             "target_only_statistics": target_only_statistics, "joint_statistics": joint_statistics,
             "silent_shift_report": silent_shift_report}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["generate_twins", "input_only_statistics", "target_only_statistics", "joint_statistics",
           "silent_shift_report", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
