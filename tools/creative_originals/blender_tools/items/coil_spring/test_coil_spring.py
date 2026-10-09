"""Known answers for the spring: free length, rate formula, closed wire, winding direction, refusals."""
import unittest

import coil_spring as spring
import meshcheck


class SpringTests(unittest.TestCase):
    def test_free_length_and_rate(self):
        report = spring.report()
        self.assertAlmostEqual(report["free_length_m"], 0.004 + 6 * 0.011 + 0.004 + 0.004)
        self.assertAlmostEqual(report["spring_rate_n_per_m"], 79.3e9 * 0.004 ** 4 / (8 * 0.04 ** 3 * 6), places=4)
        self.assertEqual(report["total_turns"], 8.0)
        self.assertAlmostEqual(report["spring_index"], 10.0)

    def test_mesh_height_matches_free_length(self):
        mesh = spring.build_geometry(samples_per_turn=64, wire_sides=16)
        low, high = meshcheck.bounds(mesh["vertices"])
        self.assertAlmostEqual(low[2], 0.0, places=4)
        self.assertAlmostEqual(high[2], spring.report()["free_length_m"], places=4)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])

    def test_left_hand_mirrors_right_hand(self):
        right = spring.build_geometry()
        left = spring.build_geometry(clockwise=True)
        self.assertEqual([[-x, y, z] for x, y, z in right["vertices"]], left["vertices"])
        self.assertGreater(meshcheck.signed_volume(left["vertices"], left["faces"]), 0)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"pitch": 0.003}, {"wire_diameter": 0.03}, {"wire_sides": 2}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                spring.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
