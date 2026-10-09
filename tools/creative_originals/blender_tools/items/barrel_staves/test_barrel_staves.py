"""Known answers for the barrel: bilge profile, part count, closed solids, volume, refusals."""
import math
import unittest

import barrel_staves as barrel
import meshcheck


class BarrelTests(unittest.TestCase):
    def test_profile_is_widest_at_mid_height(self):
        p = barrel.parameters()
        self.assertAlmostEqual(barrel.radius_at(0.0, p), 0.28)
        self.assertAlmostEqual(barrel.radius_at(0.45, p), 0.34)
        self.assertAlmostEqual(barrel.radius_at(0.9, p), 0.28)

    def test_parts_are_closed(self):
        mesh = barrel.build_geometry(staves=10, hoops=2, rows=4)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        euler = meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"])
        self.assertEqual(euler, 2 * 10 + 0 * 2 + 2 * 2)

    def test_volume_between_cylinders(self):
        report = barrel.build_geometry()["report"]
        low = math.pi * 0.28 ** 2 * 0.9 * 1000
        high = math.pi * 0.34 ** 2 * 0.9 * 1000
        self.assertTrue(low < report["outer_volume_litres"] < high)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"bilge_radius": 0.2}, {"hoops": 12, "hoop_width": 0.1}, {"staves": 5}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                barrel.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
