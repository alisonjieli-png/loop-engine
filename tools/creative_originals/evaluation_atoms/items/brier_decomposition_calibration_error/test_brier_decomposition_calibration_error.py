"""The five-term identity is exact; the three-term form is the known-wrong control for binned forecasts."""
from __future__ import annotations

import unittest

import numerics
from brier_decomposition_calibration_error import brier_decomposition, expected_calibration_error


def _three_term(result):
    """Known-wrong for binned continuous forecasts: REL - RES + UNC."""
    return result["reliability"] - result["resolution"] + result["uncertainty"]


class BrierTests(unittest.TestCase):
    def test_identity_is_exact_on_random_forecasts(self):
        generator = numerics.seeded_random(31)
        for bins in (1, 3, 10, 50):
            forecasts = numerics.uniforms(generator, 300)
            outcomes = [1.0 if generator.random() < f else 0.0 for f in forecasts]
            with self.subTest(bins=bins):
                result = brier_decomposition(forecasts, outcomes, bins)
                self.assertLess(abs(result["identity_residual"]), 1e-14)

    def test_three_term_form_is_caught(self):
        result = brier_decomposition([0.12, 0.18, 0.85, 0.95], [0, 1, 1, 1], bins=2)
        self.assertAlmostEqual(result["brier"], 0.17795, places=14)
        self.assertGreater(abs(_three_term(result) - result["brier"]), 0.01)

    def test_single_bin_and_perfect_calibration(self):
        single = brier_decomposition([0.2, 0.4, 0.9], [0, 1, 1], bins=1)
        self.assertEqual(single["resolution"], 0.0)
        self.assertAlmostEqual(single["reliability"], (0.5 - 2 / 3) ** 2, places=14)
        calibrated = expected_calibration_error([0.25] * 4 + [0.75] * 4, [1, 0, 0, 0, 1, 1, 1, 0], bins=4)
        self.assertEqual(calibrated["ece"], 0.0)

    def test_sharp_correct_forecasts(self):
        result = brier_decomposition([1.0, 0.0], [1, 0])
        self.assertEqual((result["brier"], result["reliability"]), (0.0, 0.0))
        self.assertEqual(result["resolution"], result["uncertainty"])

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            brier_decomposition([0.5], [0.5])
        with self.assertRaises(ValueError):
            brier_decomposition([1.5], [1])
        with self.assertRaises(ValueError):
            brier_decomposition([0.5, 0.5], [1])
        with self.assertRaises(ValueError):
            expected_calibration_error([0.5], [1], bins=0)


if __name__ == "__main__":
    unittest.main()
