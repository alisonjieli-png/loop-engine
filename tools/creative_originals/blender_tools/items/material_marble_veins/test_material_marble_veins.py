"""Known answers for the marble veins: the vein mask, sharpness, graph wiring and refused inputs."""
import unittest

import graphcheck
import material_marble_veins as marble


class MarbleTests(unittest.TestCase):
    def test_vein_mask_known_answers(self):
        self.assertAlmostEqual(marble.vein_mask(0.0, 0.0), 1.0)
        self.assertAlmostEqual(marble.vein_mask(0.2, 0.0, vein_frequency=2.5), 0.0)
        self.assertAlmostEqual(marble.vein_mask(1.0 / 8.0, 0.0, vein_frequency=4.0), 0.0)
        self.assertAlmostEqual(marble.vein_mask(0.25, 0.0, vein_frequency=4.0), 1.0, places=9)

    def test_sharpness_thins_veins(self):
        wide = marble.vein_mask(0.02, 0.0, sharpness=2.0)
        thin = marble.vein_mask(0.02, 0.0, sharpness=20.0)
        self.assertGreater(wide, thin)

    def test_graph_is_wired(self):
        tree = marble.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        self.assertIn({"from": ["Marble", "BSDF"], "to": ["Output", "Surface"]}, tree["links"])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"sharpness": 0.5}, {"material_name": ""}, {"vein_color": [0.1, 0.1]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                marble.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
