"""Known answers for the metal library: table lookups, luminance order, naming, refusals."""
import unittest

import graphcheck
import material_metal_f0_library as metals


class MetalTests(unittest.TestCase):
    def test_table_lookups(self):
        self.assertEqual(metals.reflectance("gold"), [1.0, 0.77, 0.34])
        self.assertTrue(all(0.0 < value <= 1.0 for row in metals.METALS.values() for value in row))
        with self.assertRaises(ValueError):
            metals.reflectance("unobtainium")

    def test_silver_reflects_more_than_iron(self):
        silver = metals.material_graph(metal="silver")["report"]["f0_luminance"]
        iron = metals.material_graph(metal="iron")["report"]["f0_luminance"]
        self.assertGreater(silver, iron)

    def test_naming_and_wiring(self):
        tree = metals.material_graph(metal="copper")["trees"][0]
        self.assertEqual(tree["name"], "Baltor Copper")
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"metal": "steel"}, {"roughness_variation": 0.9}, {"brushed": -0.5}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                metals.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
