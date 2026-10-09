"""Closed forms for 2 by 2 powers, Jacobi cross-checks for the norm, and the eigenvalue-only forecast as known-wrong."""
from __future__ import annotations

import math
import unittest

import numerics
from transient_amplification_profile import spectral_norm, spectral_radius, transient_profile


def _jordan_power_norm(rate, coupling, step):
    """||[[rate, coupling], [0, rate]]^step||_2 in closed form: (sqrt(4a^2 + b^2) + |b|) / 2."""
    a = rate ** step
    b = step * coupling * rate ** (step - 1) if step > 0 else 0.0
    return (math.sqrt(4 * a * a + b * b) + abs(b)) / 2


def _two_by_two_norm(m):
    (p, q), (r, s) = m
    return (math.hypot(p + s, q - r) + math.hypot(p - s, q + r)) / 2


class TransientProfileTests(unittest.TestCase):
    def test_profile_matches_closed_form(self):
        for rate, coupling in ((0.8, 4.0), (0.5, 10.0), (0.95, 0.3), (-0.7, 2.0)):
            profile = transient_profile([[rate, coupling], [0.0, rate]], 25)
            for step, norm in enumerate(profile["norms"]):
                with self.subTest(rate=rate, coupling=coupling, step=step):
                    self.assertAlmostEqual(norm, _jordan_power_norm(rate, coupling, step), delta=1e-12 * max(1, norm))

    def test_stable_but_amplifying(self):
        profile = transient_profile([[0.8, 4.0], [0.0, 0.8]], 40)
        self.assertLess(profile["spectral_radius"], 1.0)
        self.assertTrue(profile["amplifies"])
        self.assertEqual(profile["peak_step"], 4)
        self.assertEqual(profile["settles_below_one_at"], 21)
        self.assertGreaterEqual(profile["gelfand_bound"], profile["spectral_radius"])

    def test_eigenvalue_only_forecast_is_caught(self):
        profile = transient_profile([[0.8, 4.0], [0.0, 0.8]], 6)
        forecast = [0.8 ** step for step in range(7)]  # known-wrong: treats the matrix as if it were normal
        self.assertGreater(max(n - f for n, f in zip(profile["norms"], forecast)), 7.0)

    def test_symmetric_matrices_follow_the_spectral_radius(self):
        a = [[0.5, 0.2, 0.0], [0.2, -0.6, 0.1], [0.0, 0.1, 0.3]]
        values, _vectors = numerics.symmetric_eigen(a)
        radius = max(abs(value) for value in values)
        profile = transient_profile(a, 8)
        for step, norm in enumerate(profile["norms"]):
            self.assertAlmostEqual(norm, radius ** step, places=12)
        self.assertFalse(profile["amplifies"])
        self.assertAlmostEqual(profile["spectral_radius"], radius, places=10)

    def test_spectral_norm_matches_independent_methods(self):
        generator = numerics.seeded_random(5)
        for _trial in range(5):
            m = [numerics.standard_normals(generator, 2) for _ in range(2)]
            self.assertAlmostEqual(spectral_norm(m)["norm"], _two_by_two_norm(m), places=12)
        for _trial in range(5):
            b = [numerics.standard_normals(generator, 4) for _ in range(5)]
            top = numerics.symmetric_eigen(numerics.matmul(numerics.transpose(b), b))[0][0]
            self.assertAlmostEqual(spectral_norm(b)["norm"], math.sqrt(top), places=9)
        self.assertEqual(spectral_norm([[0.0, 0.0], [0.0, 5.0]])["norm"], 5.0)

    def test_spectral_radius_known_polynomials(self):
        companion = [[6.0, -11.0, 6.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]  # roots 1, 2, 3
        result = spectral_radius(companion)
        self.assertAlmostEqual(result["radius"], 3.0, places=10)
        self.assertEqual([round(pair[0], 9) for pair in result["eigenvalues"]], [3.0, 2.0, 1.0])
        angle = 0.7
        rotation = [[0.9 * math.cos(angle), -0.9 * math.sin(angle)], [0.9 * math.sin(angle), 0.9 * math.cos(angle)]]
        self.assertAlmostEqual(spectral_radius(rotation)["radius"], 0.9, places=12)
        self.assertAlmostEqual(spectral_radius([[0.8, 4.0], [0.0, 0.8]])["radius"], 0.8, places=7)

    def test_invalid_input_is_refused(self):
        for bad in ([[1, 2, 3], [4, 5, 6]], [[1, float("nan")], [0, 1]], []):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                transient_profile(bad, 3)
        with self.assertRaises(ValueError):
            transient_profile([[1]], 0)
        with self.assertRaises(ValueError):
            spectral_radius(numerics.identity(9))


if __name__ == "__main__":
    unittest.main()
