"""Known answers for the tinted glass: Beer-Lambert round trip, thickness scaling, wiring, refusals."""
import math
import unittest

import graphcheck
import material_glass_tinted as glass


class GlassTests(unittest.TestCase):
    def test_reference_thickness_reproduces_the_tint(self):
        tint = [0.45, 0.8, 0.6]
        result = glass.transmittance(0.05, tint=tint, reference_thickness=0.05)
        self.assertEqual(glass.parameters()["reference_thickness"], 0.5)
        for got, want in zip(result, tint):
            self.assertAlmostEqual(got, want, places=12)

    def test_twice_the_thickness_squares_the_transmittance(self):
        result = glass.transmittance(0.1, tint=[0.5, 0.9, 0.7], reference_thickness=0.05)
        for got, want in zip(result, [0.25, 0.81, 0.49]):
            self.assertAlmostEqual(got, want, places=12)

    def test_clear_glass_absorbs_nothing(self):
        self.assertEqual(glass.absorption([1.0, 1.0, 1.0], 0.01), (0.0, [1.0, 1.0, 1.0]))
        density, colour = glass.absorption([math.exp(-1.0), 1.0, 1.0], 1.0)
        self.assertAlmostEqual(density, 1.0)
        self.assertAlmostEqual(colour[0], 0.0)

    def test_graph_has_surface_and_volume(self):
        tree = glass.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        targets = {link["to"][1] for link in tree["links"] if link["to"][0] == "Output"}
        self.assertEqual(targets, {"Surface", "Volume"})

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"tint": [0.0, 0.5, 0.5]}, {"ior": 0.9}, {"reference_thickness": 0.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                glass.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
