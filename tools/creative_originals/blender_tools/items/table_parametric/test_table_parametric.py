"""Known answers for the table: overall size, part count per style, rounded corners, refusals."""
import unittest

import meshcheck
import table_parametric as table


class TableTests(unittest.TestCase):
    def test_overall_size(self):
        for style in ("tapered", "round", "turned"):
            mesh = table.build_geometry(length=1.2, width=0.8, height=0.72, leg_style=style)
            low, high = meshcheck.bounds(mesh["vertices"])
            self.assertAlmostEqual(high[0] - low[0], 1.2, places=9)
            self.assertAlmostEqual(high[1] - low[1], 0.8, places=9)
            self.assertAlmostEqual(high[2], 0.72)
            self.assertAlmostEqual(low[2], 0.0)
            self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [], style)
            self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]), 2 * 9)

    def test_rounded_rectangle(self):
        outline = table.rounded_rectangle(2.0, 1.0, 0.2, 8)
        self.assertEqual(len(outline), 4 * 9)
        area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(outline, outline[1:] + outline[:1])) / 2
        self.assertAlmostEqual(area, 2.0 - (4 - 3.14) * 0.04, delta=0.003)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"corner_radius": 0.5}, {"leg_inset": 0.5}, {"leg_style": "cabriole"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                table.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
