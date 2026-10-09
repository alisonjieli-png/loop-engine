"""Covariance intersection stays conservative for every cross-correlation; independent fusion is the known-wrong."""
from __future__ import annotations

import math
import unittest

import numerics
from covariance_intersection_fusion import conservative_margin, covariance_intersection, independent_fusion


def _random_positive_definite(generator, size):
    rows = [numerics.standard_normals(generator, size) for _ in range(size)]
    product = numerics.matmul(rows, numerics.transpose(rows))
    return [[product[i][j] + (0.5 if i == j else 0.0) for j in range(size)] for i in range(size)]


def _random_contraction(generator, size, strength):
    """A matrix with spectral norm equal to ``strength`` (at most 1)."""
    rows = [numerics.standard_normals(generator, size) for _ in range(size)]
    values, _vectors = numerics.symmetric_eigen(numerics.matmul(numerics.transpose(rows), rows))
    factor = strength / math.sqrt(values[0])
    return numerics.scale(rows, factor)


def _fused_error_covariance(a, b, cross, omega):
    """True covariance of C (omega A^-1 e_a + (1 - omega) B^-1 e_b) when Cov(e_a, e_b) = cross."""
    a_info, b_info = numerics.inverse(a), numerics.inverse(b)
    covariance = numerics.inverse(numerics.add(numerics.scale(a_info, omega), numerics.scale(b_info, 1 - omega)))
    gain_a = numerics.scale(numerics.matmul(covariance, a_info), omega)
    gain_b = numerics.scale(numerics.matmul(covariance, b_info), 1 - omega)
    terms = [numerics.matmul(numerics.matmul(gain_a, a), numerics.transpose(gain_a)),
             numerics.matmul(numerics.matmul(gain_b, b), numerics.transpose(gain_b)),
             numerics.matmul(numerics.matmul(gain_a, cross), numerics.transpose(gain_b)),
             numerics.matmul(numerics.matmul(gain_b, numerics.transpose(cross)), numerics.transpose(gain_a))]
    total = terms[0]
    for term in terms[1:]:
        total = numerics.add(total, term)
    return total


class CovarianceIntersectionTests(unittest.TestCase):
    def test_duplicate_is_returned_unchanged_for_every_omega(self):
        mean, covariance = [1.0, -2.0, 0.5], [[2.0, 0.3, 0.1], [0.3, 1.0, -0.2], [0.1, -0.2, 1.5]]
        for omega in (None, 0.0, 0.3, 0.5, 1.0):
            with self.subTest(omega=omega):
                fused = covariance_intersection(mean, covariance, mean, covariance, omega=omega)
                for row, expected in zip(fused["covariance"], covariance):
                    for value, target in zip(row, expected):
                        self.assertAlmostEqual(value, target, places=12)
                for value, target in zip(fused["mean"], mean):
                    self.assertAlmostEqual(value, target, places=12)

    def test_conservative_for_any_cross_correlation(self):
        generator = numerics.seeded_random(41)
        for trial in range(12):
            size = 2 + trial % 2
            a, b = _random_positive_definite(generator, size), _random_positive_definite(generator, size)
            lower_a, lower_b = numerics.cholesky(a), numerics.cholesky(b)
            contraction = _random_contraction(generator, size, [0.0, 0.5, 0.99, 1.0][trial % 4])
            cross = numerics.matmul(numerics.matmul(lower_a, contraction), numerics.transpose(lower_b))
            fused = covariance_intersection([0.0] * size, a, [0.0] * size, b)
            actual = _fused_error_covariance(a, b, cross, fused["omega"])
            with self.subTest(trial=trial):
                self.assertTrue(conservative_margin(fused["covariance"], actual)["conservative"])

    def test_independent_fusion_is_caught_when_errors_are_shared(self):
        covariance = [[2.0, 0.5], [0.5, 1.0]]
        naive = independent_fusion([0, 0], covariance, [0, 0], covariance)["covariance"]
        # a duplicate shares its error exactly: the true fused error covariance is the covariance itself
        self.assertFalse(conservative_margin(naive, covariance)["conservative"])
        robust = covariance_intersection([0, 0], covariance, [0, 0], covariance)["covariance"]
        self.assertTrue(conservative_margin(robust, covariance)["conservative"])

    def test_omega_minimizes_the_objective(self):
        a, b = [[2.0, 1.0], [1.0, 2.0]], [[1.0, 0.0], [0.0, 3.0]]
        for criterion in ("trace", "determinant"):
            best = covariance_intersection([0, 0], a, [1, 0], b, criterion=criterion)
            for omega in (0.0, 0.1, 0.3, 0.45, 0.55, 0.7, 0.9, 1.0):
                with self.subTest(criterion=criterion, omega=omega):
                    other = covariance_intersection([0, 0], a, [1, 0], b, criterion=criterion, omega=omega)
                    self.assertLessEqual(best["objective"], other["objective"] + 1e-12)

    def test_one_dimension_keeps_the_better_estimate(self):
        fused = covariance_intersection([0.0], [[1.0]], [3.0], [[4.0]])
        self.assertEqual(fused["omega"], 1.0)
        self.assertEqual(fused["covariance"], [[1.0]])

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            covariance_intersection([0, 0], [[1, 2], [2, 1]], [0, 0], [[1, 0], [0, 1]])
        with self.assertRaises(ValueError):
            covariance_intersection([0], [[1]], [0, 0], [[1, 0], [0, 1]])
        with self.assertRaises(ValueError):
            covariance_intersection([0], [[1]], [0], [[1]], omega=1.5)
        with self.assertRaises(ValueError):
            covariance_intersection([0], [[1]], [0], [[1]], criterion="volume")


if __name__ == "__main__":
    unittest.main()
