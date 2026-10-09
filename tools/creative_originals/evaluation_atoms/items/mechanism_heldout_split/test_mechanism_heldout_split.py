"""Held-out mechanisms never leak; a random task-level split is the known-wrong control that does."""
from __future__ import annotations

import random
import unittest

import numerics
from mechanism_heldout_split import group_k_folds, leakage, split_by_mechanism

TASKS = [{"id": f"q{i}", "mechanism": f"gen{i % 5}"} for i in range(30)]


def _independent_selection(mechanisms, fraction, seed):
    generator, items = random.Random(seed), sorted(mechanisms)
    for position in range(len(items) - 1, 0, -1):
        other = min(int(generator.random() * (position + 1)), position)
        items[position], items[other] = items[other], items[position]
    return sorted(items[:max(1, min(len(items) - 1, int(fraction * len(items) + 0.5)))])


class MechanismSplitTests(unittest.TestCase):
    def test_selection_follows_the_stated_rule(self):
        for seed in range(5):
            for fraction in (0.2, 0.4, 0.5):
                with self.subTest(seed=seed, fraction=fraction):
                    result = split_by_mechanism(TASKS, fraction, seed)
                    self.assertEqual(result["test_mechanisms"],
                                     _independent_selection({t["mechanism"] for t in TASKS}, fraction, seed))

    def test_no_mechanism_on_both_sides(self):
        result = split_by_mechanism(TASKS, 0.4, 3)
        check = leakage(TASKS, result["train_ids"], result["test_ids"])
        self.assertEqual(check["leaked_mechanisms"], [])
        self.assertEqual(sorted(result["train_ids"] + result["test_ids"]), sorted(t["id"] for t in TASKS))

    def test_random_task_split_is_caught(self):
        generator = numerics.seeded_random(4)
        shuffled = numerics.shuffled(generator, [t["id"] for t in TASKS])
        train, test = shuffled[:20], shuffled[20:]  # known-wrong: split tasks, not mechanisms
        self.assertTrue(leakage(TASKS, train, test)["leaked_mechanisms"])

    def test_folds_partition_and_balance(self):
        tasks = TASKS + [{"id": f"extra{i}", "mechanism": "gen0"} for i in range(4)]
        result = group_k_folds(tasks, 3)
        flat = [identity for fold in result["folds"] for identity in fold]
        self.assertEqual(sorted(flat), sorted(t["id"] for t in tasks))
        seen = {}
        for index, mechanisms in enumerate(result["fold_mechanisms"]):
            for mechanism in mechanisms:
                self.assertNotIn(mechanism, seen)
                seen[mechanism] = index
        self.assertLessEqual(max(result["fold_sizes"]) - min(result["fold_sizes"]), 10)

    def test_small_known_folds(self):
        tasks = [{"id": "t1", "mechanism": "m1"}, {"id": "t2", "mechanism": "m1"}, {"id": "t3", "mechanism": "m2"},
                 {"id": "t4", "mechanism": "m3"}, {"id": "t5", "mechanism": "m3"}, {"id": "t6", "mechanism": "m3"}]
        self.assertEqual(group_k_folds(tasks, 2)["folds"], [["t4", "t5", "t6"], ["t1", "t2", "t3"]])

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            split_by_mechanism([{"id": "a", "mechanism": "m"}], 0.5, 1)
        with self.assertRaises(ValueError):
            split_by_mechanism(TASKS + [{"id": "q0", "mechanism": "gen9"}], 0.5, 1)
        with self.assertRaises(ValueError):
            split_by_mechanism(TASKS, 1.0, 1)
        with self.assertRaises(ValueError):
            leakage(TASKS, ["q0"], ["nope"])
        with self.assertRaises(ValueError):
            group_k_folds(TASKS, 6)


if __name__ == "__main__":
    unittest.main()
