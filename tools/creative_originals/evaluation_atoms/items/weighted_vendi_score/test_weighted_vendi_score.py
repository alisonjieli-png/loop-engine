"""Property tests for the weighted Vendi score, with an unweighted implementation as the known-wrong control."""
from __future__ import annotations

import math
import unittest

import numerics
from weighted_vendi_score import vendi_from_features, weighted_vendi_score


def _random_units(seed, members, dimension):
    generator = numerics.seeded_random(seed)
    rows = []
    for _ in range(members):
        row = numerics.standard_normals(generator, dimension)
        length = numerics.vector_norm(row)
        rows.append([value / length for value in row])
    return rows


def _gram(rows):
    return [[numerics.dot(a, b) for b in rows] for a in rows]


def _unweighted_vendi(similarity):
    """Known-wrong for weighted sets: the plain Vendi score counts every row as one equally weighted member."""
    size = len(similarity)
    values, _vectors = numerics.symmetric_eigen([[value / size for value in row] for row in similarity])
    positive = [value for value in values if value > 1e-12]
    return math.exp(-math.fsum(value * math.log(value) for value in positive))


def _split(rows, weights, member, clone_weights):
    """Replace ``member`` by identical clones carrying ``clone_weights`` (which sum to its weight)."""
    new_rows = [row for index, row in enumerate(rows) if index != member] + [rows[member]] * len(clone_weights)
    new_weights = [weight for index, weight in enumerate(weights) if index != member] + list(clone_weights)
    return new_rows, new_weights


class WeightedVendiTests(unittest.TestCase):
    def test_orthogonal_members_count(self):
        for size in range(1, 7):
            with self.subTest(size=size):
                self.assertAlmostEqual(weighted_vendi_score(numerics.identity(size))["score"], size, places=12)

    def test_clone_split_with_conserved_weight_is_invariant(self):
        for seed in range(5):
            rows = _random_units(seed, 5, 3)
            generator = numerics.seeded_random(100 + seed)
            weights = [0.2 + generator.random() for _ in rows]
            total = math.fsum(weights)
            weights = [value / total for value in weights]
            parts = [0.1 + generator.random() for _ in range(3)]
            clone_weights = [weights[2] * part / math.fsum(parts) for part in parts]
            split_rows, split_weights = _split(rows, weights, 2, clone_weights)
            for order in (0.5, 1.0, 2.0):
                with self.subTest(seed=seed, order=order):
                    before = weighted_vendi_score(_gram(rows), weights, order)["score"]
                    after = weighted_vendi_score(_gram(split_rows), split_weights, order)["score"]
                    self.assertAlmostEqual(before, after, places=9)

    def test_unweighted_implementation_is_caught_by_the_clone_property(self):
        rows = _random_units(7, 4, 3)
        split_rows, _weights = _split(rows, [0.25] * 4, 0, [0.125, 0.125])
        before, after = _unweighted_vendi(_gram(rows)), _unweighted_vendi(_gram(split_rows))
        self.assertGreater(abs(before - after), 0.01, "the control must violate the clone property")
        weighted_before = weighted_vendi_score(_gram(rows))["score"]
        self.assertAlmostEqual(before, weighted_before, places=12, msg="equal weights reduce to the plain score")

    def test_order_monotone_and_bounded(self):
        similarity = _gram(_random_units(11, 6, 4))
        scores = [weighted_vendi_score(similarity, order=order)["score"] for order in (0.0, 0.5, 1.0, 2.0, 5.0)]
        for left, right in zip(scores, scores[1:]):
            self.assertGreaterEqual(left + 1e-12, right)
        self.assertGreaterEqual(scores[-1], 1.0 - 1e-12)
        self.assertLessEqual(scores[0], 6.0 + 1e-12)

    def test_zero_weight_member_is_removed_and_weights_are_scale_free(self):
        rows = _random_units(3, 4, 3)
        with_zero = weighted_vendi_score(_gram(rows), [0.3, 0.3, 0.4, 0.0])["score"]
        without = weighted_vendi_score(_gram(rows[:3]), [0.3, 0.3, 0.4])["score"]
        self.assertAlmostEqual(with_zero, without, places=10)
        scaled = weighted_vendi_score(_gram(rows[:3]), [3, 3, 4])["score"]
        self.assertAlmostEqual(scaled, without, places=12)

    def test_features_route_matches_kernel_route(self):
        features = [[1.0, 2.0, 0.0], [0.0, 1.0, 1.0], [2.0, 0.0, 1.0]]
        units = [[value / numerics.vector_norm(row) for value in row] for row in features]
        self.assertAlmostEqual(vendi_from_features(features, [1, 2, 3])["score"],
                               weighted_vendi_score(_gram(units), [1, 2, 3])["score"], places=12)

    def test_invalid_input_is_refused(self):
        cases = [([[1, 0.2], [0.3, 1]], None), ([[2, 0], [0, 1]], None), ([[1, 2], [2, 1]], None),
                 ([[1, 0], [0, 1]], [1, -1]), ([[1, 0], [0, 1]], [0, 0]), ([[1, 0], [0, 1]], [1])]
        for similarity, weights in cases:
            with self.subTest(similarity=similarity, weights=weights), self.assertRaises(ValueError):
                weighted_vendi_score(similarity, weights)
        with self.assertRaises(ValueError):
            weighted_vendi_score([[1]], order=-1)
        with self.assertRaises(ValueError):
            vendi_from_features([[0, 0], [1, 0]])


if __name__ == "__main__":
    unittest.main()
