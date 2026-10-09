"""Known answers for the neon tube: core whitening ramp, wiring, refusals."""
import unittest

import graphcheck
import material_neon_emission as neon


class NeonTests(unittest.TestCase):
    def test_core_colour_ramp(self):
        colour = [1.0, 0.0, 0.5]
        self.assertEqual(neon.core_color(0.6, color=colour), colour)
        hot = neon.core_color(0.0, color=colour, core_whiteness=1.0)
        self.assertEqual(hot, [1.0, 1.0, 1.0])
        half = neon.core_color(0.3, color=colour, core_whiteness=1.0)
        self.assertAlmostEqual(half[1], 0.5)

    def test_graph_mixes_glow_and_glass(self):
        tree = neon.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        types = {node["type"] for node in tree["nodes"]}
        self.assertTrue({"ShaderNodeEmission", "ShaderNodeBsdfGlass", "ShaderNodeMixShader"} <= types)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"strength": -1.0}, {"core_whiteness": 1.5}, {"color": [1.0, 0.0]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                neon.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
