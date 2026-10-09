"""Group residuals that cancel overall are found; an overall-only audit is the known-wrong control."""
from __future__ import annotations

import math
import unittest

import numerics
from multicalibration_audit import multicalibrate, multicalibration_audit

PREDICTIONS = [0.5] * 20
OUTCOMES = [1] * 7 + [0] * 3 + [1] * 3 + [0] * 7
GROUPS = {"g1": list(range(10)), "g2": list(range(10, 20))}


class MulticalibrationTests(unittest.TestCase):
    def test_cancelling_group_errors_are_found(self):
        result = multicalibration_audit(PREDICTIONS, OUTCOMES, GROUPS)
        self.assertTrue(result["calibrated_overall"])
        self.assertFalse(result["multicalibrated"])
        residuals = {row["group"]: row["residual"] for row in result["cells"]}
        self.assertEqual(residuals, {"all": 0.0, "g1": 0.2, "g2": -0.2})

    def test_overall_only_audit_is_caught(self):
        overall_only = multicalibration_audit(PREDICTIONS, OUTCOMES)  # known-wrong: no groups declared
        self.assertTrue(overall_only["multicalibrated"])
        self.assertFalse(multicalibration_audit(PREDICTIONS, OUTCOMES, GROUPS)["multicalibrated"])

    def test_patching_reaches_multicalibration_and_lowers_error(self):
        generator = numerics.seeded_random(21)
        size = 400
        features = numerics.standard_normals(generator, size)
        membership = [generator.random() < 0.4 for _ in range(size)]
        truth = [1 / (1 + math.exp(-(x + (0.8 if member else -0.3)))) for x, member in zip(features, membership)]
        outcomes = [1.0 if generator.random() < t else 0.0 for t in truth]
        predictions = [1 / (1 + math.exp(-x)) for x in features]
        groups = {"members": [i for i in range(size) if membership[i]],
                  "others": [i for i in range(size) if not membership[i]]}
        before = multicalibration_audit(predictions, outcomes, groups, tolerance=0.08, minimum_count=15)
        self.assertFalse(before["multicalibrated"])
        repaired = multicalibrate(predictions, outcomes, groups, tolerance=0.08, minimum_count=15)
        self.assertTrue(repaired["audit"]["multicalibrated"])
        error_before = math.fsum((o - p) ** 2 for o, p in zip(outcomes, predictions))
        error_after = math.fsum((o - p) ** 2 for o, p in zip(outcomes, repaired["predictions"]))
        self.assertLess(error_after, error_before)

    def test_overlapping_groups_edges_and_minimum_count(self):
        result = multicalibration_audit([1.0, 0.0, 0.95], [1, 0, 0], {"a": [0, 2], "b": [2]}, bins=10,
                                        minimum_count=2)
        bins = {(row["group"], row["bin"]): row for row in result["cells"]}
        self.assertIn(("all", 9), bins)
        self.assertEqual(bins[("all", 9)]["count"], 2)
        self.assertFalse(bins[("b", 9)]["violation"], "a single-row cell is below minimum_count")

    def test_invalid_input_is_refused(self):
        bad = [([1.2], [1], None), ([0.5], [1, 0], None), ([0.5, 0.5], [1, 0], {"all": [0]}),
               ([0.5, 0.5], [1, 0], {"g": [0, 0]}), ([0.5, 0.5], [1, 0], {"g": [5]}), ([0.5], [2], None)]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                multicalibration_audit(*args)
        with self.assertRaises(ValueError):
            multicalibration_audit([0.5], [1], None, tolerance=0)


if __name__ == "__main__":
    unittest.main()
