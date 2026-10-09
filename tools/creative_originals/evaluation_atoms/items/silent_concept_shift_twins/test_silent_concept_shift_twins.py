"""Proof by construction that input-only drift statistics cannot separate the twins, while a joint statistic can."""
from __future__ import annotations

import math
import unittest

import numerics
from silent_concept_shift_twins import generate_twins, joint_statistics, silent_shift_report


def _projection_histogram(rows, direction, edges):
    counts = [0] * (len(edges) + 1)
    for row in rows:
        value = numerics.dot(row, direction)
        counts[sum(1 for edge in edges if value > edge)] += 1
    return counts


def _rbf_mmd(a, b):
    def kernel(p, q):
        return math.exp(-0.5 * sum((x - y) ** 2 for x, y in zip(p, q)))
    aa = math.fsum(kernel(p, q) for p in a for q in a) / len(a) ** 2
    bb = math.fsum(kernel(p, q) for p in b for q in b) / len(b) ** 2
    ab = math.fsum(kernel(p, q) for p in a for q in b) / (len(a) * len(b))
    return aa + bb - 2 * ab


def _input_only_monitor(a, b):
    """Known-wrong drift monitor: flags drift only when an input statistic moves."""
    gaps = [abs(numerics.mean([r[k] for r in a]) - numerics.mean([r[k] for r in b])) for k in range(len(a[0]))]
    return max(gaps) > 1e-9 or abs(_rbf_mmd(a, b)) > 1e-9


class SilentShiftTests(unittest.TestCase):
    def test_marginal_multisets_are_identical(self):
        for seed, dimension, labels in ((1, 1, False), (2, 3, False), (3, 2, True)):
            twins = generate_twins(25, dimension, seed, labels=labels)
            reference, shifted = twins["reference"], twins["shifted"]
            with self.subTest(seed=seed, labels=labels):
                self.assertEqual(sorted(map(tuple, reference["inputs"])), sorted(map(tuple, shifted["inputs"])))
                self.assertEqual(sorted(reference["targets"]), sorted(shifted["targets"]))

    def test_permutation_invariant_input_statistics_cannot_tell(self):
        twins = generate_twins(30, 2, 7)
        a, b = twins["reference"]["inputs"], twins["shifted"]["inputs"]
        direction = numerics.standard_normals(numerics.seeded_random(99), 2)
        self.assertEqual(_projection_histogram(a, direction, [-1.0, 0.0, 1.0]),
                         _projection_histogram(b, direction, [-1.0, 0.0, 1.0]))
        for k in range(2):
            column_a, column_b = sorted(r[k] for r in a), sorted(r[k] for r in b)
            self.assertEqual(column_a, column_b)
            self.assertEqual(numerics.variance(column_a), numerics.variance(column_b))
        self.assertAlmostEqual(_rbf_mmd(a, b), 0.0, places=12)
        self.assertFalse(_input_only_monitor(a, b), "the known-wrong monitor sees no drift")

    def test_joint_relationship_flips_exactly(self):
        report = silent_shift_report(40, 3, 11)
        self.assertTrue(report["input_statistics_identical"])
        self.assertEqual(report["joint_covariance_sum_max_abs"], 0.0)
        self.assertTrue(report["joint_sign_flipped"])
        self.assertEqual(report["joint_covariance_shifted"], [-v for v in report["joint_covariance_reference"]])

    def test_a_model_fitted_on_the_reference_fails_on_the_twin(self):
        twins = generate_twins(60, 1, 5, noise=0.2, slope=[1.5])
        def fit(rows, targets):
            return numerics.dot([r[0] for r in rows], targets) / numerics.dot([r[0] for r in rows], [r[0] for r in rows])
        slope = fit(twins["reference"]["inputs"], twins["reference"]["targets"])
        def error(data):
            return math.fsum((t - slope * r[0]) ** 2 for r, t in zip(data["inputs"], data["targets"])) / len(data["targets"])
        self.assertGreater(error(twins["shifted"]), 10 * error(twins["reference"]))
        self.assertAlmostEqual(slope, 1.5, delta=0.2)

    def test_given_slope_and_joint_statistics(self):
        twins = generate_twins(2, 1, 0, noise=0.0, slope=[2.0])
        covariance = joint_statistics(twins["reference"]["inputs"], twins["reference"]["targets"])["covariance"][0]
        x = [r[0] for r in twins["reference"]["inputs"]]
        self.assertAlmostEqual(covariance, 2.0 * numerics.variance(x, 0), places=14)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            generate_twins(0, 1, 1)
        with self.assertRaises(ValueError):
            generate_twins(5, 2, 1, slope=[1.0])
        with self.assertRaises(ValueError):
            generate_twins(5, 2, 1, noise=-1)
        with self.assertRaises(ValueError):
            generate_twins(5, 2, -3)


if __name__ == "__main__":
    unittest.main()
