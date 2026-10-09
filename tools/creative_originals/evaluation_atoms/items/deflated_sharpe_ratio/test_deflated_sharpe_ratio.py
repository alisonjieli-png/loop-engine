"""Closed forms, the expected-maximum approximation, seeded null calibration and the undeflated PSR as known-wrong."""
from __future__ import annotations

import math
import statistics
import unittest

import numerics
from deflated_sharpe_ratio import (deflated_sharpe_ratio, expected_maximum_of_normals, expected_maximum_sharpe,
                                   probabilistic_sharpe_ratio, sharpe_moments)

NORMAL = statistics.NormalDist()


class DeflatedSharpeTests(unittest.TestCase):
    def test_psr_closed_forms(self):
        self.assertEqual(probabilistic_sharpe_ratio(0.1, 101, 0, 3, 0.1), 0.5)
        self.assertAlmostEqual(probabilistic_sharpe_ratio(0.1, 101), NORMAL.cdf(1 / math.sqrt(1.005)), places=15)
        self.assertAlmostEqual(probabilistic_sharpe_ratio(0.1, 101, -1, 6), NORMAL.cdf(1 / math.sqrt(1.1125)), places=15)
        self.assertLess(probabilistic_sharpe_ratio(0.1, 50), probabilistic_sharpe_ratio(0.1, 500))

    def test_moments_match_independent_formulas(self):
        returns = [0.01, -0.005, 0.02, 0.0, 0.015, -0.01, 0.012, 0.007]
        result = sharpe_moments(returns)
        self.assertAlmostEqual(result["sharpe"], statistics.mean(returns) / statistics.stdev(returns), places=14)
        centre = statistics.mean(returns)
        m2 = statistics.pvariance(returns)
        m3 = sum((r - centre) ** 3 for r in returns) / len(returns)
        self.assertAlmostEqual(result["skewness"], m3 / m2 ** 1.5, places=12)

    def test_expected_maximum_approximation(self):
        self.assertAlmostEqual(expected_maximum_of_normals(2), 1 / math.sqrt(math.pi), places=12)
        for trials in (10, 100, 1000):
            with self.subTest(trials=trials):
                self.assertLess(abs(expected_maximum_sharpe(trials, 1.0) - expected_maximum_of_normals(trials)), 0.05)
        self.assertAlmostEqual(expected_maximum_sharpe(10, 4.0), 2 * expected_maximum_sharpe(10, 1.0), places=14)

    def test_psr_is_calibrated_under_the_null(self):
        generator = numerics.seeded_random(3)
        hits = 0
        for _ in range(400):
            moments = sharpe_moments(numerics.standard_normals(generator, 60))
            hits += probabilistic_sharpe_ratio(moments["sharpe"], 60, moments["skewness"], moments["kurtosis"]) > 0.95
        self.assertLess(abs(hits / 400 - 0.05), 0.03)

    def test_undeflated_psr_after_selection_is_caught(self):
        generator = numerics.seeded_random(4)
        undeflated = deflated = 0
        for _ in range(60):
            series = [numerics.standard_normals(generator, 60) for _ in range(20)]
            sharpes = [sharpe_moments(s)["sharpe"] for s in series]
            best = max(range(20), key=lambda index: sharpes[index])
            result = deflated_sharpe_ratio(series[best], 20, numerics.variance(sharpes))
            undeflated += result["undeflated"] > 0.95
            deflated += result["deflated"] > 0.95
        self.assertGreater(undeflated / 60, 0.3, "the best of 20 noise strategies looks significant without deflation")
        self.assertLess(deflated / 60, 0.1)

    def test_more_trials_deflate_more(self):
        returns = [0.01, -0.005, 0.02, 0.0, 0.015, -0.01, 0.012, 0.007]
        values = [deflated_sharpe_ratio(returns, n, 0.04)["deflated"] for n in (2, 10, 100, 1000)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            sharpe_moments([1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            expected_maximum_sharpe(1, 1.0)
        with self.assertRaises(ValueError):
            probabilistic_sharpe_ratio(2.0, 50, 5.0, 3.0)
        with self.assertRaises(ValueError):
            probabilistic_sharpe_ratio(0.1, 1)


if __name__ == "__main__":
    unittest.main()
