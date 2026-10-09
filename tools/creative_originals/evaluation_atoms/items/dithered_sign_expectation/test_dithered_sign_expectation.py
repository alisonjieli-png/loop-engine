"""Closed form against the normal distribution and seeded Monte Carlo; the undithered sign is the known-wrong."""
from __future__ import annotations

import statistics
import unittest

from dithered_sign_expectation import monte_carlo_sign_expectation, recover_offset, sign_expectation

NORMAL = statistics.NormalDist()


class DitheredSignTests(unittest.TestCase):
    def test_closed_form_matches_normal_distribution(self):
        for x in (-3.0, -0.7, 0.0, 0.2, 1.0, 2.5):
            for sigma in (0.5, 1.0, 3.0):
                with self.subTest(x=x, sigma=sigma):
                    self.assertAlmostEqual(sign_expectation(x, sigma), 2 * NORMAL.cdf(x / sigma) - 1, places=14)

    def test_monte_carlo_agrees_within_four_standard_errors(self):
        for seed, x, sigma, dither in ((1, 0.3, 1.0, "gaussian"), (2, -1.2, 0.8, "gaussian"),
                                       (3, 0.4, 1.0, "uniform"), (4, 0.0, 2.0, "gaussian")):
            with self.subTest(seed=seed, dither=dither):
                result = monte_carlo_sign_expectation(x, sigma, 20000, seed, dither)
                self.assertLess(abs(result["estimate"] - result["exact"]), 4 * result["standard_error"])

    def test_recovery_inverts_the_expectation(self):
        for x in (-2.0, -0.3, 0.0, 0.9, 1.7):
            self.assertAlmostEqual(recover_offset(sign_expectation(x, 1.5), 1.5), x, places=9)
            self.assertAlmostEqual(recover_offset(sign_expectation(x / 2, 1.0, "uniform"), 1.0, "uniform"), x / 2,
                                   places=14)

    def test_undithered_sign_loses_the_magnitude(self):
        undithered = [1.0 if x > 0 else -1.0 for x in (0.3, 0.6)]  # known-wrong: no dither
        self.assertEqual(undithered[0], undithered[1])
        self.assertGreater(sign_expectation(0.6, 1.0) - sign_expectation(0.3, 1.0), 0.2)

    def test_same_seed_same_estimate(self):
        first = monte_carlo_sign_expectation(0.3, 1.0, 5000, 11)
        self.assertEqual(first, monte_carlo_sign_expectation(0.3, 1.0, 5000, 11))

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            sign_expectation(1.0, 0.0)
        with self.assertRaises(ValueError):
            sign_expectation(1.0, 1.0, "laplace")
        with self.assertRaises(ValueError):
            recover_offset(1.0, 1.0)
        with self.assertRaises(ValueError):
            monte_carlo_sign_expectation(0.0, 1.0, 0, 1)
        with self.assertRaises(ValueError):
            monte_carlo_sign_expectation(0.0, 1.0, 10, -1)


if __name__ == "__main__":
    unittest.main()
