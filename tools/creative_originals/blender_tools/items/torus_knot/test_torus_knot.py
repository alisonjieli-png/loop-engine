"""Known answers for the torus knot: curve points, closed genus-one tube, crossing number, refusals."""
import math
import unittest

import meshcheck
import torus_knot as knot


class KnotTests(unittest.TestCase):
    def test_curve_lies_on_the_torus(self):
        for t in (0.0, 0.7, 2.9, 5.1):
            x, y, z = knot.knot_point(t, 2, 3, 1.0, 0.4)
            self.assertAlmostEqual((math.hypot(x, y) - 1.0) ** 2 + z * z, 0.16)

    def test_tube_is_closed_genus_one(self):
        mesh = knot.build_geometry(samples=64, sides=6)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]), 0)
        self.assertGreater(meshcheck.signed_volume(mesh["vertices"], mesh["faces"]), 0.0)

    def test_frames_close_without_twist(self):
        points = [knot.knot_point(2 * math.pi * i / 200, 2, 3, 1.0, 0.42) for i in range(200)]
        tangents, normals, _mismatch = knot.transported_frames(points)
        for tangent, normal in zip(tangents, normals):
            self.assertAlmostEqual(sum(a * b for a, b in zip(tangent, normal)), 0.0, places=6)
        self.assertGreater(sum(a * b for a, b in zip(normals[0], normals[-1])), 0.95)

    def test_crossing_number(self):
        self.assertEqual(knot.build_geometry()["report"]["crossing_number"], 3)
        self.assertEqual(knot.build_geometry(p=3, q=5, samples=64)["report"]["crossing_number"], 10)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"p": 2, "q": 4}, {"minor_radius": 1.2}, {"sides": 2}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                knot.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
