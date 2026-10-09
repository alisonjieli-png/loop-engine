"""Known answers for the gradient world: ramp positions, stop order, wiring, refusals."""
import unittest

import graphcheck
import world_gradient_studio as studio


class GradientTests(unittest.TestCase):
    def test_ramp_positions(self):
        low, middle, high = studio.ramp_positions(0.0, 30.0)
        self.assertAlmostEqual(low, 0.25)
        self.assertAlmostEqual(middle, 0.5)
        self.assertAlmostEqual(high, 0.75)

    def test_stops_are_ordered(self):
        tree = studio.world_graph(horizon_height=10.0, softness=5.0)["trees"][0]
        stops = next(node for node in tree["nodes"] if node["name"] == "Gradient")["ramp"]["stops"]
        positions = [stop[0] for stop in stops]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"horizon_height": 50.0, "softness": 45.0}, {"softness": 0.0}, {"strength": -1.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                studio.world_graph(**bad)


if __name__ == "__main__":
    unittest.main()
