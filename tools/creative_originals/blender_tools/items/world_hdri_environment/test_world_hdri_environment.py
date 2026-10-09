"""Known answers for the HDRI world: equirectangular lookup, backdrop branch, refusals."""
import unittest

import graphcheck
import world_hdri_environment as hdri


class HdriTests(unittest.TestCase):
    def test_equirect_lookup(self):
        self.assertEqual(hdri.equirect_pixel([1.0, 0.0, 0.0], 400, 200), (200, 100))
        self.assertEqual(hdri.equirect_pixel([0.0, 1.0, 0.0], 400, 200), (100, 100))
        self.assertEqual(hdri.equirect_pixel([0.0, 0.0, 1.0], 400, 200)[1], 0)
        self.assertEqual(hdri.equirect_pixel([0.0, -1.0, 0.0], 400, 200, rotation=180.0), (100, 100))
        with self.assertRaises(ValueError):
            hdri.equirect_pixel([0.0, 0.0, 0.0], 4, 2)

    def test_backdrop_modes(self):
        plain = hdri.world_graph()["trees"][0]
        solid = hdri.world_graph(backdrop="solid")["trees"][0]
        self.assertEqual(len(solid["nodes"]) - len(plain["nodes"]), 3)
        for tree in (plain, solid):
            self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"image_path": "sky.txt"}, {"backdrop": "blur"}, {"saturation": 3.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                hdri.world_graph(**bad)


if __name__ == "__main__":
    unittest.main()
