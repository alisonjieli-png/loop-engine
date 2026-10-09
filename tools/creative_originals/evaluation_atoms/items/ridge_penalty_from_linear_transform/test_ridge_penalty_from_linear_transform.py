"""The induced penalty matches fitted coefficients directly; a compiler that forgets the inverse is caught."""
from __future__ import annotations

import unittest

import numerics
from ridge_penalty_from_linear_transform import (compile_penalty, fit_generalized_ridge, fit_through_transform,
                                                 induced_penalty)

FEATURES = [[1, 0], [0, 1], [1, 1], [2, -1], [0.5, 3]]
TARGETS = [1, 2, 4, 0.5, 6]


def _stacked_identity(copies, size=2):
    return [[1.0 if column % size == row else 0.0 for column in range(copies * size)] for row in range(size)]


def _wrong_penalty(transform):
    """Known-wrong compiler: A A^T instead of its inverse (duplication would double the penalty)."""
    return numerics.matmul(transform, numerics.transpose(transform))


class RidgeCompilerTests(unittest.TestCase):
    def assertVectorsClose(self, left, right, places=10):
        self.assertEqual(len(left), len(right))
        for p, q in zip(left, right):
            self.assertAlmostEqual(p, q, places=places)

    def test_duplicating_columns_divides_the_penalty(self):
        for copies in (1, 2, 3, 4):
            with self.subTest(copies=copies):
                transform = _stacked_identity(copies)
                penalty = induced_penalty(transform)["penalty_matrix"]
                self.assertVectorsClose(sum(penalty, []), [1 / copies, 0, 0, 1 / copies], places=14)
                through = fit_through_transform(FEATURES, TARGETS, transform, 1.2)["coefficients"]
                plain = fit_generalized_ridge(FEATURES, TARGETS, numerics.identity(2), 1.2 / copies)["coefficients"]
                self.assertVectorsClose(through, plain)

    def test_wrong_compiler_fails_the_duplication_check(self):
        transform = _stacked_identity(2)
        wrong = _wrong_penalty(transform)
        through = fit_through_transform(FEATURES, TARGETS, transform, 1.0)["coefficients"]
        via_wrong = fit_generalized_ridge(FEATURES, TARGETS, wrong, 1.0)["coefficients"]
        self.assertGreater(max(abs(p - q) for p, q in zip(through, via_wrong)), 1e-3)

    def test_random_transforms_agree_on_fitted_coefficients(self):
        generator = numerics.seeded_random(2026)
        for trial in range(6):
            rows, columns = 3, 3 + trial
            transform = [numerics.standard_normals(generator, columns) for _ in range(rows)]
            features = [numerics.standard_normals(generator, rows) for _ in range(8)]
            targets = numerics.standard_normals(generator, 8)
            ridge = 0.1 + generator.random()
            with self.subTest(trial=trial):
                result = compile_penalty(features, targets, transform, ridge)
                self.assertLess(result["max_abs_difference"], 1e-9)

    def test_scaling_the_transform_divides_by_the_square(self):
        penalty = induced_penalty([[3, 0], [0, 3]])["penalty_matrix"]
        self.assertVectorsClose(sum(penalty, []), [1 / 9, 0, 0, 1 / 9], places=14)

    def test_trained_weights_lie_in_the_row_space(self):
        transform = [[1, 1, 0], [0, 1, 1]]
        weights = fit_through_transform(FEATURES, TARGETS, transform, 0.5)["weights"]
        projector = numerics.matmul(numerics.transpose(transform),
                                    numerics.matmul(induced_penalty(transform)["penalty_matrix"], transform))
        self.assertVectorsClose(numerics.matvec(projector, weights), weights)

    def test_invalid_input_is_refused(self):
        for transform in ([[1, 1], [2, 2]], [[1], [2]], [[0, 0, 0]]):
            with self.subTest(transform=transform), self.assertRaises(ValueError):
                induced_penalty(transform)
        with self.assertRaises(ValueError):
            fit_through_transform(FEATURES, TARGETS, [[1, 0], [0, 1]], 0)
        with self.assertRaises(ValueError):
            fit_through_transform(FEATURES, TARGETS[:3], [[1, 0], [0, 1]], 1)
        with self.assertRaises(ValueError):
            fit_generalized_ridge(FEATURES, TARGETS, [[1, 2], [2, 1]], 1)


if __name__ == "__main__":
    unittest.main()
