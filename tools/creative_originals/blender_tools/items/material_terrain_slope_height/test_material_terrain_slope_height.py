"""Known answers for the terrain blend: grass on flat low ground, rock on steep, snow high and flat."""
import math
import unittest

import graphcheck
import material_terrain_slope_height as terrain


class TerrainBlendTests(unittest.TestCase):
    def test_layers(self):
        self.assertEqual(terrain.layer_weights(1.0, 0.0), [1.0, 0.0, 0.0])
        steep = terrain.layer_weights(math.cos(math.radians(60.0)), 0.0)
        self.assertEqual(steep[1], 1.0)
        snowy = terrain.layer_weights(1.0, 10.0)
        self.assertEqual(snowy[2], 1.0)
        cliff = terrain.layer_weights(math.cos(math.radians(70.0)), 10.0)
        self.assertEqual(cliff[2], 0.0)

    def test_weights_sum_to_one(self):
        for z in (0.2, 0.6, 0.9):
            for height in (0.0, 2.0, 2.4):
                self.assertAlmostEqual(sum(terrain.layer_weights(z, height, 0.3)), 1.0)

    def test_graph_is_wired(self):
        self.assertEqual(graphcheck.tree_problems(terrain.material_graph()["trees"][0]), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"rock_slope": 88.0, "slope_blend": 10.0}, {"snow_blend": 0.0}, {"grass_color": [1, 1]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                terrain.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
