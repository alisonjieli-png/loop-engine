"""Exact rational reference, invariances, and the singular sample covariance as the known-wrong control."""
from __future__ import annotations

import math
import unittest
from fractions import Fraction

import numerics
from ledoit_wolf_shrinkage import ledoit_wolf, shrink


def _reference(rows):
    x = [[Fraction(v) for v in row] for row in rows]
    n, p = len(x), len(x[0])
    means = [sum(column) / n for column in zip(*x)]
    x = [[v - m for v, m in zip(row, means)] for row in x]
    s = [[sum(row[i] * row[j] for row in x) / n for j in range(p)] for i in range(p)]
    mu = sum(s[i][i] for i in range(p)) / p
    d2 = sum((s[i][j] - (mu if i == j else 0)) ** 2 for i in range(p) for j in range(p)) / p
    b2 = sum(sum((row[i] * row[j] - s[i][j]) ** 2 for i in range(p) for j in range(p)) for row in x) / (n * n * p)
    delta = min(b2, d2) / d2
    return delta, [[(1 - delta) * s[i][j] + (delta * mu if i == j else 0) for j in range(p)] for i in range(p)]


def _rotation(angle):
    return [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]


class LedoitWolfTests(unittest.TestCase):
    def test_matches_exact_rational_reference(self):
        generator = numerics.seeded_random(14)
        for trial in range(6):
            rows = [[round(v, 3) for v in numerics.standard_normals(generator, 3)] for _ in range(5 + trial)]
            delta, covariance = _reference(rows)
            result = ledoit_wolf(rows)
            with self.subTest(trial=trial):
                self.assertAlmostEqual(result["shrinkage"], float(delta), places=12)
                for row, expected in zip(result["covariance"], covariance):
                    for value, target in zip(row, expected):
                        self.assertAlmostEqual(value, float(target), places=12)

    def test_singular_sample_covariance_becomes_positive_definite(self):
        rows = [[1, 2, 3, 4, 5], [2, 1, 0, 1, 2], [0, 0, 1, 3, 1]]
        result = ledoit_wolf(rows)
        self.assertLess(abs(result["sample_smallest_eigenvalue"]), 1e-12, "the known-wrong estimate is singular")
        self.assertGreater(result["smallest_eigenvalue"], 0.1)
        numerics.cholesky(result["covariance"])

    def test_scale_and_rotation_behave(self):
        rows = [[1, 2], [2, 1], [3, 4], [4, 3], [5, 7]]
        base = ledoit_wolf(rows)
        scaled = ledoit_wolf([[3 * v for v in row] for row in rows])
        self.assertAlmostEqual(scaled["shrinkage"], base["shrinkage"], places=12)
        for row, expected in zip(scaled["covariance"], base["covariance"]):
            for value, target in zip(row, expected):
                self.assertAlmostEqual(value, 9 * target, places=10)
        rotation = _rotation(0.4)
        rotated = ledoit_wolf([numerics.matvec(rotation, row) for row in rows])
        self.assertAlmostEqual(rotated["shrinkage"], base["shrinkage"], places=10)
        expected = numerics.matmul(numerics.matmul(rotation, base["covariance"]), numerics.transpose(rotation))
        for row, target_row in zip(rotated["covariance"], expected):
            for value, target in zip(row, target_row):
                self.assertAlmostEqual(value, target, places=10)

    def test_seeded_frobenius_error_against_identity_truth(self):
        generator = numerics.seeded_random(77)
        shrunk_error = sample_error = 0.0
        for _trial in range(8):
            rows = [numerics.standard_normals(generator, 10) for _ in range(15)]
            result = ledoit_wolf(rows)
            truth = numerics.identity(10)
            shrunk_error += numerics.frobenius_norm(numerics.subtract(result["covariance"], truth))
            sample_error += numerics.frobenius_norm(numerics.subtract(result["sample_covariance"], truth))
        self.assertLess(shrunk_error, sample_error)

    def test_shrink_and_spherical_input(self):
        self.assertEqual(shrink([[2, 1], [1, 4]], 0.5), [[2.5, 0.5], [0.5, 3.5]])
        spherical = ledoit_wolf([[1, 0], [-1, 0], [0, 1], [0, -1]])
        self.assertEqual(spherical["shrinkage"], 0.0)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            ledoit_wolf([[1, 2]])
        with self.assertRaises(ValueError):
            ledoit_wolf([[1, 2], [3]])
        with self.assertRaises(ValueError):
            shrink([[1, 0], [0, 1]], 1.5)


if __name__ == "__main__":
    unittest.main()
