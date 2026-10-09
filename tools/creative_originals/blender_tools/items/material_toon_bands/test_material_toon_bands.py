"""Known answers for the toon bands: ramp stops, band of a normal, wiring, refusals."""
import unittest

import graphcheck
import material_toon_bands as toon


class ToonTests(unittest.TestCase):
    def test_band_stops(self):
        stops = toon.band_stops([1.0, 1.0, 1.0], [0.0, 0.0, 0.0], 4)
        self.assertEqual([stop[0] for stop in stops], [0.0, 0.25, 0.5, 0.75])
        self.assertEqual(stops[0][1], [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(stops[-1][1], [1.0, 1.0, 1.0, 1.0])

    def test_band_of_a_normal(self):
        light = [0.0, 0.0, 1.0]
        self.assertEqual(toon.band_index([0.0, 0.0, 1.0], light_direction=light, bands=3), 2)
        self.assertEqual(toon.band_index([0.0, 0.0, -1.0], light_direction=light, bands=3), 0)
        self.assertEqual(toon.band_index([1.0, 0.0, 0.0], light_direction=light, bands=3), 1)

    def test_graph_emits(self):
        tree = toon.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        self.assertIn({"from": ["Flat Colour", "Emission"], "to": ["Output", "Surface"]}, tree["links"])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"light_direction": [0.0, 0.0, 0.0]}, {"bands": 1}, {"rim_width": 1.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                toon.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
