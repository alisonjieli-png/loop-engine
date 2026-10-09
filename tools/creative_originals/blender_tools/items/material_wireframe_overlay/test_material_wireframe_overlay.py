"""Known answers for the wireframe overlay: line mix with fading, wiring, refusals."""
import unittest

import graphcheck
import material_wireframe_overlay as wire


class WireframeTests(unittest.TestCase):
    def test_line_mix(self):
        self.assertEqual(wire.line_mix(1.0, 0.0), 1.0)
        self.assertEqual(wire.line_mix(0.0, 0.5), 0.0)
        self.assertAlmostEqual(wire.line_mix(1.0, 1.0, fade_grazing=0.4), 0.6)

    def test_graph_uses_the_wireframe_node(self):
        tree = wire.material_graph(use_pixel_size=False)["trees"][0]
        node = next(node for node in tree["nodes"] if node["type"] == "ShaderNodeWireframe")
        self.assertFalse(node["properties"]["use_pixel_size"])
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"line_width": 0.0}, {"fade_grazing": 1.5}, {"use_pixel_size": "yes"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                wire.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
