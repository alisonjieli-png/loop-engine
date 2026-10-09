"""Known spectra, invariances and the eigenvalue-entropy variant as the known-wrong control."""
from __future__ import annotations

import math
import unittest

import numerics
from effective_rank_spectral_entropy import singular_values, spectral_dimensions


def _eigenvalue_entropy_rank(matrix):
    """Known-wrong: entropy of the normalized eigenvalues sigma^2 instead of the singular values."""
    squares = [value * value for value in singular_values(matrix) if value > 0]
    shares = [value / sum(squares) for value in squares]
    return math.exp(-sum(share * math.log(share) for share in shares))


def _rotation(angle):
    return [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]


class EffectiveRankTests(unittest.TestCase):
    def test_equal_singular_values_give_their_count(self):
        for k in range(1, 6):
            matrix = [[1.0 if i == j else 0.0 for j in range(6)] for i in range(k)]
            result = spectral_dimensions(matrix)
            for key in ("effective_rank", "participation_ratio", "stable_rank"):
                self.assertAlmostEqual(result[key], k, places=12)

    def test_closed_form_singular_values(self):
        generator = numerics.seeded_random(2)
        for _trial in range(5):
            rows = [numerics.standard_normals(generator, 2) for _ in range(4)]
            gram = numerics.matmul(numerics.transpose(rows), rows)
            trace, determinant = gram[0][0] + gram[1][1], numerics.determinant(gram)
            root = math.sqrt(max(trace * trace / 4 - determinant, 0.0))
            expected = [math.sqrt(trace / 2 + root), math.sqrt(max(trace / 2 - root, 0.0))]
            for got, target in zip(singular_values(rows), expected):
                self.assertAlmostEqual(got, target, places=10)

    def test_invariance_to_rotation_and_scale(self):
        rows = [[1.0, 2.0], [3.0, 1.0], [0.5, -1.0], [2.0, 2.0]]
        base = spectral_dimensions(rows)
        rotated = [numerics.matvec(_rotation(0.9), row) for row in rows]
        scaled = [[7.0 * value for value in row] for row in rows]
        for other in (spectral_dimensions(rotated), spectral_dimensions(scaled)):
            for key in ("effective_rank", "participation_ratio", "stable_rank"):
                self.assertAlmostEqual(other[key], base[key], places=10)

    def test_eigenvalue_entropy_is_caught(self):
        matrix = [[2, 0, 0], [0, 1, 0], [0, 0, 1]]
        self.assertAlmostEqual(spectral_dimensions(matrix)["effective_rank"], 2 ** 1.5, places=12)
        self.assertGreater(abs(_eigenvalue_entropy_rank(matrix) - 2 ** 1.5), 0.4)

    def test_centering_removes_the_mean_direction(self):
        rows = [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]
        self.assertEqual(spectral_dimensions(rows, center=True)["numerical_rank"], 1)
        shifted = [[x + 10.0, y - 4.0] for x, y in [[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]]]
        self.assertAlmostEqual(spectral_dimensions(shifted, center=True)["effective_rank"], 2.0, places=10)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(ValueError):
            spectral_dimensions([[0, 0], [0, 0]])
        with self.assertRaises(ValueError):
            spectral_dimensions([[1, 2]], center=True)
        with self.assertRaises(ValueError):
            spectral_dimensions([[1, 2], [3]])


if __name__ == "__main__":
    unittest.main()
