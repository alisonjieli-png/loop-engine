"""The law of total covariance holds exactly; sample (n - 1) denominators are the known-wrong that breaks it."""
from __future__ import annotations

import math
import unittest
from fractions import Fraction

import numerics
from correlation_source_decomposition import decompose_covariance, decompose_variance


def _sample_covariance(xs, ys):
    """Known-wrong ingredient: an n - 1 denominator inside the decomposition."""
    if len(xs) < 2:
        return Fraction(0)
    mx, my = sum(map(Fraction, xs)) / len(xs), sum(map(Fraction, ys)) / len(ys)
    return sum((Fraction(x) - mx) * (Fraction(y) - my) for x, y in zip(xs, ys)) / (len(xs) - 1)


class DecompositionTests(unittest.TestCase):
    def test_identity_is_exact_on_random_floats(self):
        generator = numerics.seeded_random(9)
        for trial in range(20):
            size = 3 + trial
            y = numerics.standard_normals(generator, size)
            p = [value * 0.3 + noise for value, noise in zip(y, numerics.standard_normals(generator, size))]
            groups = [numerics.random_index(generator, 4) for _ in range(size)]
            with self.subTest(trial=trial):
                result = decompose_covariance(y, p, groups)
                self.assertEqual(result["identity_residual"], 0.0)
                self.assertAlmostEqual(result["total_covariance"], numerics.covariance(y, p, ddof=0), places=12)

    def test_sample_denominators_break_the_identity(self):
        y, p, groups = [1, 3, 5, 7, 2], [2, 4, 1, 3, 9], ["a", "a", "b", "b", "b"]
        total = _sample_covariance(y, p)
        weights = {"a": Fraction(2, 5), "b": Fraction(3, 5)}
        within = sum(weights[g] * _sample_covariance([y[i] for i in range(5) if groups[i] == g],
                                                     [p[i] for i in range(5) if groups[i] == g]) for g in weights)
        means = {g: (sum(Fraction(y[i]) for i in range(5) if groups[i] == g) / (5 * weights[g]),
                     sum(Fraction(p[i]) for i in range(5) if groups[i] == g) / (5 * weights[g])) for g in weights}
        my, mp = sum(map(Fraction, y)) / 5, sum(map(Fraction, p)) / 5
        between = sum(weights[g] * (means[g][0] - my) * (means[g][1] - mp) for g in weights)
        self.assertNotEqual(total - within - between, 0)
        self.assertEqual(decompose_covariance(y, p, groups)["identity_residual"], 0.0)

    def test_extreme_groupings(self):
        y, p = [1, 2, 3, 5], [2, 4, 7, 1]
        pooled = decompose_covariance(y, p, ["one"] * 4)
        self.assertEqual((pooled["between_group"], pooled["within_group"]), (0.0, pooled["total_covariance"]))
        singletons = decompose_covariance(y, p, [0, 1, 2, 3])
        self.assertEqual((singletons["within_group"], singletons["between_group"]),
                         (0.0, singletons["total_covariance"]))

    def test_hidden_opposite_signs(self):
        result = decompose_covariance([1, 3, 5, 7], [2, 4, 1, 3], ["a", "a", "b", "b"])
        self.assertEqual((result["total_covariance"], result["within_group"], result["between_group"]), (0.0, 1.0, -1.0))
        self.assertTrue(result["sign_conflict"])
        self.assertIsNone(result["within_share"])

    def test_variance_special_case_and_correlation(self):
        result = decompose_variance([1, 2, 3, 4], ["a", "a", "b", "b"])
        self.assertEqual((result["total_variance"], result["within_group"], result["between_group"]), (1.25, 0.25, 1.0))
        correlation = decompose_covariance([1, 2, 3], [2, 4, 7], ["x", "y", "x"])["total_correlation"]
        expected = numerics.covariance([1, 2, 3], [2, 4, 7]) / math.sqrt(numerics.variance([1, 2, 3]) *
                                                                       numerics.variance([2, 4, 7]))
        self.assertAlmostEqual(correlation, expected, places=12)
        self.assertIsNone(decompose_covariance([1, 1], [2, 3], ["a", "b"])["total_correlation"])

    def test_invalid_input_is_refused(self):
        for args in (([1, 2], [1], ["a", "a"]), ([1, 2], [1, 2], ["a"]), ([1, 2], [1, 2], ["a", True]),
                     ([], [], []), ([1, float("inf")], [1, 2], ["a", "b"])):
            with self.subTest(args=args), self.assertRaises(ValueError):
                decompose_covariance(*args)


if __name__ == "__main__":
    unittest.main()
