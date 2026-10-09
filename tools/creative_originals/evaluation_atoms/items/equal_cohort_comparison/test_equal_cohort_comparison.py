"""Cohort means against the two misleading shortcuts (own rows, missing as zero) used as known-wrong controls."""
from __future__ import annotations

import math
import unittest

from equal_cohort_comparison import compare_on_common_cohort

SCORES = {"a": {"r1": 0.9, "r2": 0.8, "r3": None}, "b": {"r1": 0.7, "r2": 0.6, "r3": 0.1, "r4": 0.2}}


def _own_row_means(scores):
    """Known-wrong: each candidate averaged over the rows it happened to score."""
    return {c: math.fsum(v for v in rows.values() if v is not None) / sum(v is not None for v in rows.values())
            for c, rows in scores.items()}


def _missing_as_zero(scores, universe):
    """Known-wrong: a missing score counted as 0 on the declared universe."""
    return {c: math.fsum((rows.get(row) or 0.0) for row in universe) / len(universe) for c, rows in scores.items()}


class EqualCohortTests(unittest.TestCase):
    def test_cohort_means_and_coverage(self):
        result = compare_on_common_cohort(SCORES, reference="b")
        self.assertEqual(result["cohort"], ["r1", "r2"])
        self.assertAlmostEqual(result["means"]["a"], 0.85, places=12)
        self.assertAlmostEqual(result["means"]["b"], 0.65, places=12)
        self.assertEqual(result["coverage"]["a"], {"scored": 2, "universe": 4, "fraction": 0.5})
        self.assertEqual(result["excluded_rows"], {"r3": ["a"], "r4": ["a"]})
        self.assertAlmostEqual(result["paired_differences"]["a"]["mean_difference"], 0.2, places=12)

    def test_shortcuts_are_caught(self):
        result = compare_on_common_cohort(SCORES)
        own = _own_row_means(SCORES)
        zero = _missing_as_zero(SCORES, ["r1", "r2", "r3", "r4"])
        self.assertGreater(abs(own["b"] - result["means"]["b"]), 0.2, "own-row means compare different rows")
        self.assertGreater(abs(zero["a"] - result["means"]["a"]), 0.4, "missing as zero mixes in the failure rate")
        self.assertAlmostEqual(own["a"] - own["b"], 0.45, places=12)
        self.assertAlmostEqual(result["means"]["a"] - result["means"]["b"], 0.2, places=12)

    def test_order_does_not_matter(self):
        reordered = {"b": dict(reversed(list(SCORES["b"].items()))), "a": dict(reversed(list(SCORES["a"].items())))}
        self.assertEqual(compare_on_common_cohort(reordered)["means"], compare_on_common_cohort(SCORES)["means"])

    def test_empty_cohort_is_reported_not_scored(self):
        result = compare_on_common_cohort({"a": {"r1": None}, "b": {"r1": 1.0}})
        self.assertFalse(result["comparable"])
        self.assertEqual((result["means"], result["ranking"]), ({"a": None, "b": None}, []))

    def test_lower_is_better_ranking_and_declared_universe(self):
        result = compare_on_common_cohort(SCORES, universe=["r1", "r2", "r3", "r4", "r5"], higher_is_better=False)
        self.assertEqual(result["ranking"], ["b", "a"])
        self.assertEqual(result["coverage"]["b"]["fraction"], 0.8)
        self.assertEqual(result["excluded_rows"]["r5"], ["a", "b"])

    def test_invalid_input_is_refused(self):
        bad = [({"a": {"r1": float("nan")}},), ({"a": {"r9": 1}}, ["r1"]), ({"a": {"r1": 1}}, ["r1", "r1"]),
               ({},), ({"a": [1, 2]},), ({"a": {"r1": True}},)]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                compare_on_common_cohort(*args)
        with self.assertRaises(ValueError):
            compare_on_common_cohort(SCORES, reference="c")


if __name__ == "__main__":
    unittest.main()
