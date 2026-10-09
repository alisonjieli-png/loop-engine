"""Known answers for the height fog: exponential falloff, noise range, closed box, refusals."""
import math
import unittest

import fog_volume_height as fog
import meshcheck


class FogTests(unittest.TestCase):
    def test_exponential_falloff(self):
        self.assertAlmostEqual(fog.density_at(0.0, density=0.5, breakup=0.0), 0.5)
        self.assertAlmostEqual(fog.density_at(2.0, density=0.5, falloff=2.0, breakup=0.0), 0.5 / math.e)
        self.assertAlmostEqual(fog.density_at(-1.0, density=0.5, breakup=0.0), 0.5)

    def test_noise_scales_density(self):
        self.assertAlmostEqual(fog.density_at(0.0, 1.0, density=1.0, breakup=0.5), 1.5)
        self.assertAlmostEqual(fog.density_at(0.0, 0.0, density=1.0, breakup=0.5), 0.5)

    def test_box(self):
        mesh = fog.build_geometry(size=[4.0, 2.0, 3.0])
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertAlmostEqual(meshcheck.signed_volume(mesh["vertices"], mesh["faces"]), 24.0)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"falloff": 0.0}, {"anisotropy": 1.0}, {"size": [1.0, 1.0]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                fog.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
