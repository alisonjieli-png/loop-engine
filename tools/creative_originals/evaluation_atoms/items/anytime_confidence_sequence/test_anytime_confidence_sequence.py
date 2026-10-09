"""Seeded coverage over all times, an independent capital computation, and the peeking interval as known-wrong."""
from __future__ import annotations

import math
import unittest

from anytime_confidence_sequence import (betting_sequence, coverage_simulation, hoeffding_sequence,
                                         pointwise_wilson_sequence)

DATA = [1, 0] * 50


def _never_rejected(values, alpha, cap, points):
    """Independent reading of the betting rule: grid points never rejected at any time t."""
    threshold = math.log(1 / alpha) + math.log(2)
    stakes, total, squares = [], 0.0, 0.25
    for step, value in enumerate(values, start=1):
        variance = squares / step
        stakes.append(min(cap, math.sqrt(2 * math.log(2 / alpha) / (variance * step * math.log(1 + step)))))
        total += value
        squares += (value - (0.5 + total) / (step + 1)) ** 2
    kept = []
    for m in points:
        plus = minus = 0.0
        ok = True
        for value, stake in zip(values, stakes):
            plus += math.log1p(min(stake, cap / m) * (value - m))
            minus += math.log1p(-min(stake, cap / (1 - m)) * (value - m))
            if max(plus, minus) >= threshold:
                ok = False
                break
        if ok:
            kept.append(m)
    return kept


class ConfidenceSequenceTests(unittest.TestCase):
    def test_hoeffding_matches_independent_running_intersection(self):
        low, high, total = 0.0, 1.0, 0
        for step, value in enumerate(DATA, start=1):
            total += value
            radius = math.sqrt(math.log(2 * step * (step + 1) / 0.05) / (2 * step))
            low, high = max(low, total / step - radius), min(high, total / step + radius)
        final = hoeffding_sequence(DATA, 0.05)["final"]
        self.assertAlmostEqual(final[0], low, places=14)
        self.assertAlmostEqual(final[1], high, places=14)

    def test_betting_interval_contains_every_never_rejected_mean(self):
        result = betting_sequence(DATA, 0.05)
        points = [(index + 0.5) / 2000 for index in range(2000)]
        kept = _never_rejected([float(v) for v in DATA], 0.05, 0.5, points)
        self.assertTrue(kept)
        self.assertLessEqual(result["final"][0], kept[0])
        self.assertGreaterEqual(result["final"][1], kept[-1])
        self.assertLess(result["final"][1] - result["final"][0], kept[-1] - kept[0] + 0.02)

    def test_coverage_holds_at_all_times(self):
        self.assertTrue(coverage_simulation("hoeffding", 0.3, 200, 200, 0.1, 1)["within_alpha"])
        betting = coverage_simulation("betting", 0.3, 100, 40, 0.1, 2, grid=50)
        self.assertLessEqual(betting["miscoverage"], 0.1)

    def test_peeking_at_a_fixed_sample_interval_is_caught(self):
        peeking = coverage_simulation("pointwise_wilson", 0.3, 200, 200, 0.1, 3)
        self.assertGreater(peeking["miscoverage"], 0.3, "checking a fixed-time interval at every step fails often")

    def test_betting_is_tighter_than_hoeffding_on_lopsided_data(self):
        ones = [1] * 30
        self.assertGreater(betting_sequence(ones, 0.05)["final"][0], hoeffding_sequence(ones, 0.05)["final"][0])

    def test_scaling_and_monotone_intervals(self):
        scaled = hoeffding_sequence([3, 5, 4, 6, 2, 5, 5, 4], 0.1, lower_bound=0, upper_bound=10)
        unit = hoeffding_sequence([0.3, 0.5, 0.4, 0.6, 0.2, 0.5, 0.5, 0.4], 0.1)
        for got, expected in zip(scaled["final"], unit["final"]):
            self.assertAlmostEqual(got, 10 * expected, places=12)
        for key, sign in (("lower", 1), ("upper", -1)):
            series = scaled[key]
            self.assertTrue(all(sign * (b - a) >= 0 for a, b in zip(series, series[1:])))
        self.assertEqual(pointwise_wilson_sequence([0], 0.1)["final"][0], 0.0)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            hoeffding_sequence([0.5, 1.5], 0.1)
        with self.assertRaises(ValueError):
            hoeffding_sequence([0.5], 0.0)
        with self.assertRaises(ValueError):
            betting_sequence([0.5], 0.1, grid=5)
        with self.assertRaises(ValueError):
            coverage_simulation("normal", 0.3, 10, 10, 0.1, 1)


if __name__ == "__main__":
    unittest.main()
