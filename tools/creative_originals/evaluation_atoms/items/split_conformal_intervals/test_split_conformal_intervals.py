"""Exact quantile index, seeded held-out coverage, and the uncorrected empirical quantile as the known-wrong."""
from __future__ import annotations

import math
import unittest

import numerics
from split_conformal_intervals import conformal_quantile, coverage, coverage_simulation, split_conformal


def _naive_interval_coverage(generator, calibration_size, test_size, alpha):
    """Known-wrong: the plain empirical (1 - alpha) quantile, index ceil(n (1 - alpha)), no (n + 1) correction."""
    residuals = sorted(abs(e) for e in numerics.standard_normals(generator, calibration_size))
    q = residuals[math.ceil(calibration_size * (1 - alpha) - 1e-12) - 1]
    test = numerics.standard_normals(generator, test_size)
    return sum(abs(e) <= q for e in test) / test_size


class ConformalTests(unittest.TestCase):
    def test_quantile_index(self):
        self.assertEqual(conformal_quantile(list(range(1, 10)), 0.1)["quantile"], 9.0)
        self.assertEqual(conformal_quantile(list(range(1, 10)), 0.2)["quantile"], 8.0)
        self.assertTrue(conformal_quantile(list(range(1, 10)), 0.05)["infinite"])
        self.assertEqual(conformal_quantile(list(range(1, 11)), 0.1)["index"], 10)
        self.assertEqual(conformal_quantile([5.0, 1.0, 3.0], 0.5)["quantile"], 3.0)

    def test_seeded_coverage_matches_theory(self):
        result = coverage_simulation(400, 50, 100, 0.1, 1.0, 1)
        self.assertAlmostEqual(result["expected"], 46 / 51, places=14)
        self.assertLess(abs(result["mean_coverage"] - result["expected"]), 0.012)

    def test_uncorrected_quantile_is_caught(self):
        generator = numerics.seeded_random(5)
        naive = sum(_naive_interval_coverage(generator, 20, 200, 0.1) for _ in range(300)) / 300
        corrected = coverage_simulation(300, 20, 200, 0.1, 1.0, 5)["mean_coverage"]
        self.assertLess(naive, 0.9 - 0.005, "the uncorrected quantile under-covers with 20 calibration points")
        self.assertGreater(corrected, 0.9 - 0.01)

    def test_mondrian_groups_get_their_own_quantile(self):
        generator = numerics.seeded_random(8)
        size = 400
        groups = ["quiet" if generator.random() < 0.5 else "noisy" for _ in range(2 * size)]
        noise = [(0.2 if g == "quiet" else 2.0) * e for g, e in zip(groups, numerics.standard_normals(generator, 2 * size))]
        predictions = [0.0] * (2 * size)
        targets = noise
        result = split_conformal(predictions[:size], targets[:size], predictions[size:], 0.1, groups[:size], groups[size:])
        for label in ("quiet", "noisy"):
            rows = [i for i in range(size) if groups[size + i] == label]
            got = coverage([result["intervals"][i] for i in rows], [targets[size + i] for i in rows])["coverage"]
            with self.subTest(group=label):
                self.assertGreater(got, 0.83)
        pooled = split_conformal(predictions[:size], targets[:size], predictions[size:], 0.1)
        noisy_rows = [i for i in range(size) if groups[size + i] == "noisy"]
        pooled_noisy = coverage([pooled["intervals"][i] for i in noisy_rows], [targets[size + i] for i in noisy_rows])
        self.assertLess(pooled_noisy["coverage"], 0.88, "a pooled quantile under-covers the noisy group")

    def test_coverage_counts_unbounded_intervals(self):
        self.assertEqual(coverage([[0, 1], [None, None], [2, 3]], [0.5, 100, 4])["coverage"], 2 / 3)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            conformal_quantile([1, 2], 0)
        with self.assertRaises(ValueError):
            split_conformal([1, 2], [1], [1], 0.1)
        with self.assertRaises(ValueError):
            split_conformal([1, 2], [1, 2], [1], 0.1, calibration_groups=["a", "a"])
        with self.assertRaises(ValueError):
            split_conformal([1, 2], [1, 2], [1], 0.1, ["a", "a"], ["b"])


if __name__ == "__main__":
    unittest.main()
