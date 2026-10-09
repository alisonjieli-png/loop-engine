"""Known answers for the wood ring material: the ring phase, the latewood ramp stop and refused inputs."""
import unittest

import graphcheck
import material_wood_rings as wood


class WoodTests(unittest.TestCase):
    def test_ring_phase_known_answers(self):
        self.assertAlmostEqual(wood.ring_value(0.0125, rings_per_metre=60.0), 0.75)
        self.assertAlmostEqual(wood.ring_value(0.5, rings_per_metre=60.0), 0.0, places=9)
        self.assertAlmostEqual(wood.ring_value(0.01, rings_per_metre=25.0), 0.25)

    def test_latewood_fraction_moves_the_ramp(self):
        for fraction in (0.1, 0.5, 0.8):
            tree = wood.material_graph(latewood_fraction=fraction)["trees"][0]
            ramp = next(node for node in tree["nodes"] if node["name"] == "Ring Ramp")["ramp"]
            self.assertAlmostEqual(ramp["stops"][1][0], 1.0 - fraction)
            self.assertEqual([round(stop[0], 9) for stop in ramp["stops"]],
                             sorted(round(stop[0], 9) for stop in ramp["stops"]))
            self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_one_output_reached_by_the_shader(self):
        tree = wood.material_graph()["trees"][0]
        outputs = [node for node in tree["nodes"] if node["type"] == "ShaderNodeOutputMaterial"]
        self.assertEqual(len(outputs), 1)
        self.assertIn({"from": ["Wood", "BSDF"], "to": ["Output", "Surface"]}, tree["links"])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"latewood_fraction": 0.95}, {"material_name": "  "}, {"earlywood_color": [1.2, 0.0, 0.0]},
                    {"roughness": [0.5, 0.5]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                wood.material_graph(**bad)
        with self.assertRaises(ValueError):
            wood.ring_value(-1.0)


if __name__ == "__main__":
    unittest.main()
