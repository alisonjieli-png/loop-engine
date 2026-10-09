"""Retrieval, interference and convergence tests; the Hebbian rule is the known-wrong control for correlated keys."""
from __future__ import annotations

import unittest

import numerics
from delta_rule_associative_memory import delta_update, least_squares_memory, retrieve, store_pairs


def _orthonormal(generator, count, size):
    basis = []
    while len(basis) < count:
        vector = numerics.standard_normals(generator, size)
        for other in basis:
            projection = numerics.dot(vector, other)
            vector = [v - projection * o for v, o in zip(vector, other)]
        length = numerics.vector_norm(vector)
        if length > 1e-6:
            basis.append([v / length for v in vector])
    return basis


def _unit_rows(generator, count, size):
    rows = []
    for _ in range(count):
        row = numerics.standard_normals(generator, size)
        length = numerics.vector_norm(row)
        rows.append([v / length for v in row])
    return rows


class DeltaRuleTests(unittest.TestCase):
    def test_orthogonal_keys_do_not_interfere(self):
        generator = numerics.seeded_random(3)
        keys = _orthonormal(generator, 4, 6)
        values = [numerics.standard_normals(generator, 3) for _ in keys]
        self.assertLess(store_pairs(keys, values)["max_error"], 1e-12)

    def test_sweeps_converge_to_minimum_norm_memory(self):
        generator = numerics.seeded_random(4)
        keys = _unit_rows(generator, 3, 5)
        values = [numerics.standard_normals(generator, 2) for _ in keys]
        swept = store_pairs(keys, values, sweeps=400)
        reference = least_squares_memory(keys, values)
        self.assertLess(swept["max_error"], 1e-9)
        for row, expected in zip(swept["memory"], reference):
            for value, target in zip(row, expected):
                self.assertAlmostEqual(value, target, places=8)

    def test_latest_pair_is_stored_exactly(self):
        generator = numerics.seeded_random(5)
        memory = [numerics.standard_normals(generator, 4) for _ in range(2)]
        key, value = numerics.standard_normals(generator, 4), [0.5, -1.5]
        updated = delta_update(memory, key, value, 1.0, normalize_by_key_norm=True)
        for got, target in zip(retrieve(updated, key), value):
            self.assertAlmostEqual(got, target, places=12)

    def test_hebbian_crosstalk_is_caught(self):
        keys, values = [[1.0, 0.0], [0.6, 0.8]], [[1.0], [0.0]]
        hebbian = store_pairs(keys, values, rule="hebbian")
        delta = store_pairs(keys, values, sweeps=200)
        self.assertGreater(hebbian["max_error"], 0.5)
        self.assertLess(delta["max_error"], 1e-12)

    def test_unstable_rate_is_refused(self):
        with self.assertRaises(ValueError):
            store_pairs([[1.0, 0.0], [0.6, 0.8]], [[1.0], [0.0]], rate=3.0, sweeps=2000)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            delta_update([[0, 0]], [1, 0, 0], [1])
        with self.assertRaises(ValueError):
            delta_update([[0, 0]], [1, 0], [1], rate=0)
        with self.assertRaises(ValueError):
            store_pairs([[1, 0]], [[1], [2]])
        with self.assertRaises(ValueError):
            store_pairs([[1, 0]], [[1]], rule="oja")
        with self.assertRaises(ValueError):
            least_squares_memory([[1, 0], [2, 0]], [[1], [2]])


if __name__ == "__main__":
    unittest.main()
