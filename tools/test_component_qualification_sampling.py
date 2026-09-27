"""Checks for the acceptance sampling plan of generated component batches."""
from __future__ import annotations

import math
import random
import unittest

from tools.component_qualification import sampling
from tools.component_qualification.sampling import (
    GeneratorHistory,
    SamplingError,
    SamplingPolicy,
    binomial_cdf,
    clopper_pearson_upper,
    decide,
    draw_sample,
    hypergeometric_cdf,
    plan_for,
)


def _hypergeometric_by_counting(c, population, defective, sample):
    total = math.comb(population, sample)
    return sum(math.comb(defective, x) * math.comb(population - defective, sample - x)
               for x in range(0, min(c, defective, sample) + 1)) / total


class DistributionTests(unittest.TestCase):
    def test_hypergeometric_matches_exact_counting(self):
        for population, defective, sample, c in ((46, 3, 29, 0), (189, 10, 48, 0), (300, 15, 120, 4),
                                                 (1000, 50, 59, 0), (60, 60, 10, 3), (60, 0, 10, 0)):
            self.assertAlmostEqual(hypergeometric_cdf(c, population, defective, sample),
                                   _hypergeometric_by_counting(c, population, defective, sample), places=12)

    def test_binomial_matches_exact_counting(self):
        for n, p, c in ((59, 0.05, 0), (153, 0.01, 3), (20, 0.5, 10)):
            exact = sum(math.comb(n, x) * p ** x * (1 - p) ** (n - x) for x in range(c + 1))
            self.assertAlmostEqual(binomial_cdf(c, n, p), exact, places=12)

    def test_clopper_pearson_upper_bound(self):
        # Zero defects in 59: the classic rule of three is about 3/59; the exact bound is 1 - 0.05 ** (1/59).
        self.assertAlmostEqual(clopper_pearson_upper(0, 59), 1 - 0.05 ** (1 / 59), places=6)
        self.assertEqual(clopper_pearson_upper(5, 5), 1.0)


class PlanTests(unittest.TestCase):
    def test_zero_acceptance_plan_without_history(self):
        plan = plan_for("batch", 5592, GeneratorHistory("line/v1"))
        self.assertEqual((plan.mode, plan.acceptance_number, plan.sample_size), (sampling.ZERO_ACCEPTANCE, 0, 59))
        self.assertLessEqual(plan.consumer_risk_achieved, 0.05)

    def test_every_plan_meets_the_consumer_risk_exactly(self):
        policy = SamplingPolicy()
        for batch_size in (7, 46, 189, 1339, 5592, 40000):
            for sampled, defective in ((0, 0), (300, 0), (300, 3), (900, 18), (300, 14)):
                plan = plan_for("b", batch_size, GeneratorHistory("g", 3, sampled, defective), policy)
                tolerance = max(1, math.ceil(policy.tolerance_defect_rate * batch_size))
                accept_at_tolerance = (0.0 if plan.sample_size >= batch_size else
                                       hypergeometric_cdf(plan.acceptance_number, batch_size, tolerance,
                                                          plan.sample_size))
                self.assertLessEqual(accept_at_tolerance, policy.consumer_risk, (batch_size, sampled, defective))

    def test_known_wrong_plan_is_rejected_by_the_consumer_risk_check(self):
        # Control: a sample one smaller than the plan's no longer meets the consumer's risk.
        plan = plan_for("batch", 5592, GeneratorHistory("line/v1"))
        tolerance = math.ceil(0.05 * 5592)
        self.assertGreater(hypergeometric_cdf(0, 5592, tolerance, plan.sample_size - 1), 0.05)

    def test_observed_rate_raises_the_sample_and_keeps_the_producer_risk(self):
        clean = plan_for("b", 5592, GeneratorHistory("g", 5, 300, 0))
        noisy = plan_for("b", 5592, GeneratorHistory("g", 5, 300, 3))
        self.assertEqual(clean.sample_size, 59)
        self.assertGreater(noisy.sample_size, clean.sample_size)
        self.assertGreater(noisy.acceptance_number, 0)
        self.assertLessEqual(noisy.producer_risk_at_observed_rate, 0.10)

    def test_generator_at_tolerance_is_never_sampled_into_acceptance(self):
        plan = plan_for("b", 5592, GeneratorHistory("g", 5, 300, 15))
        self.assertEqual(plan.mode, sampling.GENERATOR_ABOVE_TOLERANCE)
        verdict = decide(plan, defective=0, decided=plan.sample_size, controls_planted=10, controls_approved=0)
        self.assertEqual(verdict["outcome"], sampling.WITHHELD)
        self.assertTrue(verdict["flag_generator"])

    def test_short_history_is_not_used(self):
        plan = plan_for("b", 5592, GeneratorHistory("g", 1, 20, 0))
        self.assertEqual(plan.mode, sampling.ZERO_ACCEPTANCE)
        self.assertIsNone(plan.observed_rate)

    def test_small_batch_is_reviewed_whole_when_needed(self):
        plan = plan_for("b", 3, GeneratorHistory("g"))
        self.assertEqual(plan.sample_size, 3)
        self.assertTrue(plan.reviews_every_component)

    def test_invalid_inputs_refused(self):
        with self.assertRaises(SamplingError):
            plan_for("b", 0, GeneratorHistory("g"))
        with self.assertRaises(SamplingError):
            SamplingPolicy(tolerance_defect_rate=0.7)
        with self.assertRaises(SamplingError):
            GeneratorHistory("g", 1, 5, 6)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.plan = plan_for("batch", 1000, GeneratorHistory("g"))

    def test_clean_sample_with_passed_controls_is_accepted(self):
        verdict = decide(self.plan, defective=0, decided=self.plan.sample_size, controls_planted=6,
                         controls_approved=0)
        self.assertEqual((verdict["outcome"], verdict["reasons"]), (sampling.ACCEPTED, []))

    def test_one_defect_withholds_a_zero_acceptance_batch(self):
        verdict = decide(self.plan, defective=1, decided=self.plan.sample_size, controls_planted=6,
                         controls_approved=0)
        self.assertEqual(verdict["outcome"], sampling.WITHHELD)
        self.assertIn(sampling.TOO_MANY_DEFECTS, verdict["reasons"])
        self.assertTrue(verdict["flag_generator"])

    def test_an_approved_control_withholds_the_batch(self):
        verdict = decide(self.plan, defective=0, decided=self.plan.sample_size, controls_planted=6,
                         controls_approved=1)
        self.assertEqual(verdict["outcome"], sampling.WITHHELD)
        self.assertIn(sampling.CONTROL_APPROVED, verdict["reasons"])

    def test_a_run_without_controls_is_withheld(self):
        verdict = decide(self.plan, defective=0, decided=self.plan.sample_size, controls_planted=0,
                         controls_approved=0)
        self.assertEqual(verdict["outcome"], sampling.WITHHELD)

    def test_an_undecided_component_counts_as_defective(self):
        verdict = decide(self.plan, defective=0, decided=self.plan.sample_size - 1, controls_planted=6,
                         controls_approved=0)
        self.assertEqual(verdict["counted_defective"], 1)
        self.assertEqual(verdict["outcome"], sampling.WITHHELD)
        self.assertFalse(verdict["sample_complete"])

    def test_history_counts_only_complete_samples(self):
        rows = [{"generator": "g", "sample_complete": True, "sampled": 59, "defective": 1},
                {"generator": "g", "sample_complete": False, "sampled": 59, "defective": 0},
                {"generator": "h", "sample_complete": True, "sampled": 59, "defective": 9}]
        history = GeneratorHistory.from_decisions("g", rows)
        self.assertEqual((history.batches, history.sampled, history.defective), (1, 59, 1))


class SampleTests(unittest.TestCase):
    def test_sample_is_reproducible_from_its_seed_and_unbiased(self):
        population = [f"id-{index:05d}" for index in range(5000)]
        first = draw_sample(population, 59, "seed-0123456789abcdef")
        self.assertEqual(first, draw_sample(reversed(population), 59, "seed-0123456789abcdef"))
        self.assertNotEqual(first, draw_sample(population, 59, "seed-fedcba9876543210"))
        # Every identity is equally likely: over many seeds, the first and last tenth are drawn alike.
        low = high = 0
        for number in range(300):
            chosen = draw_sample(population, 59, f"seed-{number:016d}")
            low += sum(1 for identity in chosen if identity < "id-00500")
            high += sum(1 for identity in chosen if identity >= "id-04500")
        self.assertLess(abs(low - high), 0.15 * (low + high))

    def test_short_seed_refused(self):
        with self.assertRaises(SamplingError):
            draw_sample(["a", "b"], 1, "short")

    def test_random_module_state_is_not_used(self):
        random.seed(1)
        first = draw_sample(["a", "b", "c", "d"], 2, "x" * 16)
        random.seed(2)
        self.assertEqual(first, draw_sample(["a", "b", "c", "d"], 2, "x" * 16))


if __name__ == "__main__":
    unittest.main()
