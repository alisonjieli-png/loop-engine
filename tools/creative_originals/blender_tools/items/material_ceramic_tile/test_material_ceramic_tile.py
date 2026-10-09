"""Known answers for the tile material: the edge mask in grout, bevel and centre, wiring, refusals."""
import unittest

import graphcheck
import material_ceramic_tile as tile


class TileTests(unittest.TestCase):
    def test_edge_mask(self):
        self.assertEqual(tile.edge_mask(0.1, 0.1), 1.0)
        self.assertEqual(tile.edge_mask(0.0, 0.1), 0.0)
        self.assertEqual(tile.edge_mask(0.2001, 0.1), 0.0)
        middle = tile.edge_mask(0.002 + 0.003, 0.1)
        self.assertAlmostEqual(middle, 0.5)

    def test_graph_is_wired(self):
        tree = tile.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        self.assertEqual(len(tree["nodes"]), 19)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"tile_size": 0.01, "bevel": 0.006}, {"orientation": "diagonal"}, {"glaze_a": [2, 0, 0]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                tile.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
