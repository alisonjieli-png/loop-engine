"""Known answers for the bounce: free-fall arcs, rebound heights, contact timing and refused inputs."""
import math
import unittest

import anim_bounce as bounce


class BounceTests(unittest.TestCase):
    def test_arcs_follow_free_fall(self):
        result = bounce.keyframes(squash=0.0, drop_height=2.0, gravity=9.81, fps=24.0, radius=0.25)
        height = result["channels"][0]
        first = math.sqrt(2 * 2.0 / 9.81)
        for time in (0.05, 0.2, 0.4, first * 0.95):
            expected = 0.25 + 2.0 - 0.5 * 9.81 * time * time
            self.assertAlmostEqual(bounce.evaluate(height, 1 + time * 24.0), expected, places=6)
        rebound = 2.0 * 0.65 ** 2
        speed = math.sqrt(2 * 9.81 * rebound)
        for time in (0.1, 0.3):
            expected = 0.25 + speed * time - 0.5 * 9.81 * time * time
            self.assertAlmostEqual(bounce.evaluate(height, 1 + (first + time) * 24.0), expected, places=6)

    def test_rebound_heights_and_contacts(self):
        report = bounce.keyframes(restitution=0.5, bounces=3, min_height=0.0001)["report"]
        self.assertEqual(report["apex_heights_m"], [2.0, 0.5, 0.125, 0.03125])
        self.assertEqual(report["contacts"], 4)
        timeline = bounce.bounce_timeline(restitution=0.5, bounces=3, min_height=0.0001)
        self.assertAlmostEqual(timeline[1][1], math.sqrt(4.0 / 9.81))
        self.assertEqual([kind for kind, _time, _height in timeline],
                         ["apex", "contact", "apex", "contact", "apex", "contact", "apex", "contact"])

    def test_min_height_stops_the_bounce(self):
        report = bounce.keyframes(restitution=0.5, bounces=10, min_height=0.2)["report"]
        self.assertEqual(report["apex_heights_m"], [2.0, 0.5])

    def test_squash_lowers_contact_and_scales(self):
        result = bounce.keyframes(squash=0.2)
        contact = result["channels"][0]["keys"][1][1]
        self.assertAlmostEqual(contact, 0.25 - 0.25 * 0.2)
        scale_z = next(channel for channel in result["channels"] if channel["data_path"] == "scale"
                       and channel["index"] == 2)
        self.assertAlmostEqual(min(value for _frame, value in scale_z["keys"]), 0.8)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"restitution": 1.0}, {"bounces": 0}, {"fps": 0.5}, {"measure_radius": "no"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                bounce.keyframes(**bad)


if __name__ == "__main__":
    unittest.main()
