"""Known answers for the catenary: anchors, arc length, symmetric sag, closed tube, refusals."""
import math
import unittest

import catenary_cable as cable
import meshcheck


class CatenaryTests(unittest.TestCase):
    def test_curve_meets_both_anchors(self):
        points, _numbers = cable.curve(start=[1.0, 2.0, 5.0], end=[7.0, -1.0, 3.0], slack=1.1)
        for got, want in ((points[0], [1.0, 2.0, 5.0]), (points[-1], [7.0, -1.0, 3.0])):
            for a, b in zip(got, want):
                self.assertAlmostEqual(a, b, places=7)

    def test_arc_length_matches_slack(self):
        points, numbers = cable.curve(start=[0.0, 0.0, 0.0], end=[10.0, 0.0, 2.0], slack=1.2, segments=1000)
        length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        self.assertAlmostEqual(length, 1.2 * math.hypot(10.0, 2.0), places=3)
        self.assertAlmostEqual(numbers["length_m"], 1.2 * math.hypot(10.0, 2.0), places=9)

    def test_level_span_sags_symmetrically(self):
        points, numbers = cable.curve(start=[0.0, 0.0, 0.0], end=[10.0, 0.0, 0.0], slack=1.05, segments=10)
        self.assertAlmostEqual(points[5][2], numbers["lowest_point_z_m"], places=9)
        self.assertAlmostEqual(points[2][2], points[8][2], places=9)
        a = numbers["parameter_a_m"]
        self.assertAlmostEqual(2 * a * math.sinh(5.0 / a), 10.5, places=6)

    def test_tube_is_closed(self):
        mesh = cable.build_geometry()
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"start": [0.0, 0.0, 0.0], "end": [0.0, 0.0, 5.0]}, {"slack": 1.0}, {"segments": 2}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cable.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
