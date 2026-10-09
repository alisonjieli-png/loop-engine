"""Known answers for the lathe: cylinder volume, poles, shell closure, chaikin ends, refusals."""
import math
import unittest

import lathe_profile as lathe
import meshcheck


class LatheTests(unittest.TestCase):
    def test_closed_cylinder_volume(self):
        mesh = lathe.build_geometry(profile="0,0; 1,0; 1,2; 0,2", segments=256, thickness=0.0, rounding=0)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        expected = 0.5 * 256 * math.sin(2 * math.pi / 256) * 2.0
        self.assertAlmostEqual(meshcheck.signed_volume(mesh["vertices"], mesh["faces"]), expected, places=9)
        self.assertEqual(len(mesh["vertices"]), 2 + 2 * 256)

    def test_shell_is_one_closed_solid(self):
        mesh = lathe.build_geometry()
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]), 2)
        solid = lathe.build_geometry(thickness=0.0)
        self.assertLess(meshcheck.signed_volume(mesh["vertices"], mesh["faces"]),
                        0.5 * meshcheck.signed_volume(solid["vertices"], solid["faces"]))

    def test_tube_wall_without_poles(self):
        mesh = lathe.build_geometry(profile="1,0; 1,1", thickness=0.1, rounding=0, segments=16)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]), 0)

    def test_chaikin_keeps_end_points(self):
        points = lathe.chaikin([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]], 2)
        self.assertEqual(points[0], [0.0, 0.0])
        self.assertEqual(points[-1], [1.0, 1.0])
        self.assertGreater(len(points), 3)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"profile": "0,0"}, {"profile": "0,0; 0,1; 1,1"}, {"profile": "-1,0; 1,1"},
                    {"thickness": 0.01, "angle": 180.0}, {"profile": "0,0; 0.05,0; 0.05,1", "thickness": 0.2}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                lathe.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
