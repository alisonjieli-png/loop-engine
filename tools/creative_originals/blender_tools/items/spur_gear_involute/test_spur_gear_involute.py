"""Known answers for the involute gear: diameters, involute function, tooth thickness, closed solid, refusals."""
import math
import unittest

import meshcheck
import spur_gear_involute as gear


class GearTests(unittest.TestCase):
    def test_involute_function(self):
        self.assertAlmostEqual(gear.involute(math.radians(20.0)), 0.014904383867336446, places=12)
        self.assertEqual(gear.involute(0.0), 0.0)

    def test_standard_diameters(self):
        report = gear.build_geometry(teeth=20, module=0.005, bore_diameter=0.0)["report"]
        self.assertAlmostEqual(report["pitch_diameter_m"], 0.1)
        self.assertAlmostEqual(report["tip_diameter_m"], 0.11)
        self.assertAlmostEqual(report["root_diameter_m"], 0.0875)
        self.assertAlmostEqual(report["base_diameter_m"], 0.1 * math.cos(math.radians(20.0)))

    def test_outline_stays_between_root_and_tip(self):
        points = gear.outline(teeth=24, module=0.004)
        radii = [math.hypot(x, y) for x, y in points]
        self.assertAlmostEqual(max(radii), 0.004 * 26 / 2)
        self.assertGreaterEqual(min(radii), 0.004 * 21.5 / 2 - 1e-12)
        angles = [math.atan2(y, x) % (2 * math.pi) for x, y in points]
        turns = sum(1 for a, b in zip(angles, angles[1:] + angles[:1]) if b < a - 1e-9)
        self.assertEqual(turns, 1, "the outline winds once around the axis")

    def test_tooth_thickness_on_pitch_circle(self):
        z, m = 30, 0.002
        size = gear.dimensions(z, m, 20.0)
        half = math.pi / (2 * z) + gear.involute(math.radians(20)) - gear.involute(
            math.acos(size["base_radius"] / size["pitch_radius"]))
        self.assertAlmostEqual(2 * half * size["pitch_radius"], math.pi * m / 2)

    def test_closed_with_and_without_bore(self):
        for bore in (0.0, 0.03):
            mesh = gear.build_geometry(bore_diameter=bore)
            self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
            self.assertEqual(meshcheck.problems(mesh["vertices"], mesh["faces"]), [])
            expected_euler = 2 if bore == 0.0 else 0
            self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]), expected_euler)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"bore_diameter": 0.2}, {"teeth": 5}, {"backlash": 0.02}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                gear.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
