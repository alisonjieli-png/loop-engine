"""Known answers for the straight flight: height, length, comfort formula, closed parts, refused inputs."""
import unittest

import meshcheck
import stairs_straight as stairs


class StraightStairTests(unittest.TestCase):
    def test_height_and_run(self):
        mesh = stairs.build_geometry(steps=10, rise=0.18, going=0.25, nosing=0.02, stringers=False)
        low, high = meshcheck.bounds(mesh["vertices"])
        self.assertAlmostEqual(high[2], 1.8)
        self.assertAlmostEqual(high[1], 2.5)
        self.assertAlmostEqual(low[1], -0.02)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]), 2 * 20)

    def test_comfort_formula(self):
        report = stairs.comfort(0.17, 0.29)
        self.assertAlmostEqual(report["two_rise_plus_going_m"], 0.63)
        self.assertTrue(report["comfortable"])
        self.assertFalse(stairs.comfort(0.22, 0.25)["comfortable"])
        self.assertAlmostEqual(stairs.comfort(0.2, 0.2)["pitch_degrees"], 45.0)

    def test_stringer_profile_stays_above_the_floor(self):
        for steps, depth in ((1, 0.3), (5, 0.1), (12, 0.6)):
            profile = stairs.stringer_profile(steps, 0.175, 0.28, depth)
            self.assertGreaterEqual(min(z for _y, z in profile), 0.0)
            self.assertAlmostEqual(max(z for _y, z in profile), steps * 0.175)
            self.assertGreaterEqual(len(profile), 3)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"tread_thickness": 0.2, "rise": 0.15}, {"steps": 0}, {"going": 0.05}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                stairs.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
