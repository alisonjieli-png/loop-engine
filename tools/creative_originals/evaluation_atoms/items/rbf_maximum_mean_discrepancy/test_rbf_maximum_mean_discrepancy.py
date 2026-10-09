"""Closed forms, sign behaviour of both estimators, permutation p-value calibration, and clamping as known-wrong."""
from __future__ import annotations

import math
import unittest

import numerics
from rbf_maximum_mean_discrepancy import median_bandwidth, mmd_squared, permutation_test


def _normal_rows(generator, count, shift=0.0):
    return [[value + shift] for value in numerics.standard_normals(generator, count)]


class MmdTests(unittest.TestCase):
    def test_closed_forms(self):
        e = math.exp
        cross = (2 * e(-2) + e(-4.5) + e(-0.5)) / 4
        self.assertAlmostEqual(mmd_squared([[0]], [[1]], 1)["mmd_squared"], 2 - 2 * e(-0.5), places=15)
        self.assertAlmostEqual(mmd_squared([[0], [1]], [[2], [3]], 1)["mmd_squared"],
                               (2 + 2 * e(-0.5)) / 2 - 2 * cross, places=15)
        self.assertAlmostEqual(mmd_squared([[0], [1]], [[2], [3]], 1, True)["mmd_squared"],
                               2 * e(-0.5) - 2 * cross, places=15)

    def test_biased_is_non_negative_and_unbiased_can_be_negative(self):
        generator = numerics.seeded_random(6)
        negatives = 0
        for _trial in range(20):
            x, y = _normal_rows(generator, 6), _normal_rows(generator, 6)
            self.assertGreaterEqual(mmd_squared(x, y, 1.0)["mmd_squared"], -1e-15)
            negatives += mmd_squared(x, y, 1.0, True)["mmd_squared"] < 0
        self.assertGreater(negatives, 0, "clamping at zero would hide these values")

    def test_symmetry_and_identical_samples(self):
        x, y = [[0, 1], [2, 2], [1, -1]], [[1, 1], [0, 0]]
        self.assertAlmostEqual(mmd_squared(x, y)["mmd_squared"], mmd_squared(y, x)["mmd_squared"], places=14)
        self.assertEqual(mmd_squared(x, x, 1.0)["mmd_squared"], 0.0)

    def test_permutation_test_detects_a_shift(self):
        generator = numerics.seeded_random(4)
        x, y, z = _normal_rows(generator, 20), _normal_rows(generator, 20, 1.5), _normal_rows(generator, 20)
        self.assertLess(permutation_test(x, y, None, 200, 1)["p_value"], 0.02)
        self.assertGreater(permutation_test(x, z, None, 200, 1)["p_value"], 0.05)

    def test_null_p_values_are_calibrated(self):
        generator = numerics.seeded_random(10)
        small = 0
        for replication in range(40):
            x, y = _normal_rows(generator, 8), _normal_rows(generator, 8)
            small += permutation_test(x, y, 1.0, 39, replication)["p_value"] <= 0.1
        self.assertLessEqual(small / 40, 0.1 + 0.15)

    def test_median_bandwidth(self):
        self.assertEqual(median_bandwidth([[0], [1], [3]]), 2.0)
        self.assertEqual(median_bandwidth([[0, 0], [3, 4], [0, 0]]), 5.0)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            mmd_squared([[0]], [[1]], unbiased=True)
        with self.assertRaises(ValueError):
            mmd_squared([[0]], [[1, 2]])
        with self.assertRaises(ValueError):
            mmd_squared([[0]], [[1]], bandwidth=0)
        with self.assertRaises(ValueError):
            median_bandwidth([[1], [1]])


if __name__ == "__main__":
    unittest.main()
