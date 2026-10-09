"""Blind labels follow the stated shuffle; grouping is an equivalence relation, unlike tolerance matching."""
from __future__ import annotations

import random
import unittest

from behavioral_equivalence_relabeling import blind_labels, blind_report, equivalence_classes


def _independent_labels(names, seed):
    generator, items = random.Random(seed), sorted(names)
    for position in range(len(items) - 1, 0, -1):
        other = min(int(generator.random() * (position + 1)), position)
        items[position], items[other] = items[other], items[position]
    width = len(str(len(items)))
    return {name: f"candidate_{index + 1:0{width}d}" for index, name in enumerate(items)}


def _within(a, b, tolerance):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


class RelabelingTests(unittest.TestCase):
    def test_labels_follow_the_stated_shuffle(self):
        names = [f"method_{i}" for i in range(12)]
        for seed in range(4):
            with self.subTest(seed=seed):
                self.assertEqual(blind_labels(names, seed)["mapping"], _independent_labels(names, seed))

    def test_labels_hide_the_name_order(self):
        names = [f"m{i}" for i in range(12)]
        mapping = blind_labels(names, 1)["mapping"]
        by_label = [name for name, _label in sorted(mapping.items(), key=lambda row: row[1])]
        self.assertNotEqual(by_label, sorted(names))
        key = blind_labels(names, 1)["key"]
        self.assertEqual({key[label]: label for label in key}, mapping)

    def test_identical_behaviour_groups_and_rounding(self):
        result = equivalence_classes({"A": [1, 2, 3], "B": [1, 2, 3], "C": [1, 2, 4]})
        self.assertEqual([row["members"] for row in result["classes"]], [["A", "B"], ["C"]])
        rounded = equivalence_classes({"x": [0.1 + 0.2], "y": [0.3]}, decimals=9)
        self.assertEqual(rounded["class_count"], 1)
        exact = equivalence_classes({"x": [0.1 + 0.2], "y": [0.3]})  # known-wrong for floats: exact equality
        self.assertEqual(exact["class_count"], 2)

    def test_tolerance_matching_is_not_transitive(self):
        outputs = {"a": [0.0], "b": [0.008], "c": [0.016]}
        self.assertTrue(_within(outputs["a"], outputs["b"], 0.01) and _within(outputs["b"], outputs["c"], 0.01))
        self.assertFalse(_within(outputs["a"], outputs["c"], 0.01), "a tolerance cannot define classes")
        classes = equivalence_classes(outputs, decimals=2)["classes"]
        members = [row["members"] for row in classes]
        self.assertEqual(sorted(sum(members, [])), ["a", "b", "c"])
        for row in classes:
            values = {round(outputs[name][0], 2) for name in row["members"]}
            self.assertEqual(len(values), 1)

    def test_blind_report_uses_labels(self):
        report = blind_report({"A": [1, 2, 3], "B": [1, 2, 3], "C": [1, 2, 4]}, 5)
        flat = [label for row in report["classes"] for label in row["members"]]
        self.assertTrue(all(label.startswith("candidate_") for label in flat))
        self.assertEqual(sorted(report["key"][label] for label in report["classes"][0]["members"]), ["A", "B"])

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            equivalence_classes({"a": [1, 2], "b": [1]})
        with self.assertRaises(ValueError):
            equivalence_classes({"a": [float("nan")]})
        with self.assertRaises(ValueError):
            blind_labels(["a", "a"], 1)
        with self.assertRaises(ValueError):
            equivalence_classes({})


if __name__ == "__main__":
    unittest.main()
