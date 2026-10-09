"""Known answers for the L-shaped stairs: rises, winder outlines, mirror, closed parts, refused inputs."""
import math
import unittest

import meshcheck
import stairs_l_shaped as stairs


class LShapedTests(unittest.TestCase):
    def test_total_rises(self):
        winders = stairs.build_geometry(first_steps=4, second_steps=3, corner="winders", rise=0.2)
        landing = stairs.build_geometry(first_steps=4, second_steps=3, corner="landing", rise=0.2)
        self.assertEqual(winders["report"]["total_rises"], 10)
        self.assertEqual(landing["report"]["total_rises"], 8)
        self.assertAlmostEqual(meshcheck.bounds(winders["vertices"])[1][2], 2.0)

    def test_winders_tile_the_corner_square(self):
        outlines = stairs.winder_outlines(1.2)
        total = 0.0
        for outline in outlines:
            area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(outline, outline[1:] + outline[:1])) / 2.0
            self.assertGreater(abs(area), 0.0)
            total += abs(area)
        self.assertAlmostEqual(total, 1.2 * 1.2)
        self.assertAlmostEqual(outlines[0][2][1], 1.2 * math.tan(math.radians(30)))

    def test_left_turn_mirrors_right(self):
        right = stairs.build_geometry(turn="right")
        left = stairs.build_geometry(turn="left")
        self.assertEqual([[-x, y, z] for x, y, z in right["vertices"]], left["vertices"])
        self.assertEqual(meshcheck.closed_problems(left["faces"]), [])
        self.assertGreater(meshcheck.signed_volume(left["vertices"], left["faces"]), 0)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"corner": "spiral"}, {"turn": "up"}, {"tread_thickness": 0.25, "rise": 0.2}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                stairs.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
