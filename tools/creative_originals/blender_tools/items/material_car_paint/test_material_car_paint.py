"""Known answers for the car paint: flake normals are unit length, flip ramp ends, wiring, refusals."""
import math
import unittest

import graphcheck
import material_car_paint as paint


class CarPaintTests(unittest.TestCase):
    def test_flake_normals(self):
        self.assertEqual(paint.flake_normal([0.0, 0.0, 1.0], [0.5, 0.5, 0.5], 0.3), [0.0, 0.0, 1.0])
        tilted = paint.flake_normal([0.0, 0.0, 1.0], [1.0, 0.5, 0.5], 0.4)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in tilted)), 1.0)
        self.assertGreater(tilted[0], 0.0)
        with self.assertRaises(ValueError):
            paint.flake_normal([0.0, 0.0, 1.0], [0.5, 0.5, 0.0], 2.0)

    def test_flip_ramp_holds_both_colours(self):
        tree = paint.material_graph(base_color=[0.1, 0.2, 0.3], flip_color=[0.0, 0.0, 0.1])["trees"][0]
        ramp = next(node for node in tree["nodes"] if node["name"] == "Flip")["ramp"]
        self.assertEqual(ramp["stops"][0][1], [0.1, 0.2, 0.3, 1.0])
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"flake_scale": 1.0}, {"metallic": 1.5}, {"base_color": [0.1, 0.2]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                paint.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
