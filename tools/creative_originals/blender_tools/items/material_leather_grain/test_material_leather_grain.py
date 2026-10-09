"""Known answers for the leather: crease mask ramp, two readings of one Voronoi pattern, refusals."""
import unittest

import graphcheck
import material_leather_grain as leather


class LeatherTests(unittest.TestCase):
    def test_crease_mask(self):
        self.assertEqual(leather.crease_mask(0.0), 0.0)
        self.assertAlmostEqual(leather.crease_mask(0.03), 0.5)
        self.assertEqual(leather.crease_mask(0.5), 1.0)

    def test_both_voronoi_share_a_scale(self):
        tree = leather.material_graph(grain_scale=300.0)["trees"][0]
        scales = {node["inputs"]["Scale"] for node in tree["nodes"] if node["type"] == "ShaderNodeTexVoronoi"}
        self.assertEqual(scales, {300.0})
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"crease_width": 0.0}, {"grain_scale": 1.0}, {"roughness": 2.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                leather.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
