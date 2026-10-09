"""Known answers for edge wear: flat areas keep paint, sharp edges with noise wear through, refusals."""
import unittest

import graphcheck
import material_edge_wear as wear


class EdgeWearTests(unittest.TestCase):
    def test_flat_keeps_paint(self):
        self.assertEqual(wear.wear_mask(1.0, 1.0), 0.0)

    def test_edges_wear_where_noise_is_high(self):
        self.assertEqual(wear.wear_mask(0.7, 0.9), 1.0)
        self.assertEqual(wear.wear_mask(0.7, 0.1), 0.0)

    def test_more_wear_amount_wears_more(self):
        light = wear.wear_mask(0.95, 0.6, wear_amount=0.2)
        heavy = wear.wear_mask(0.95, 0.6, wear_amount=0.9)
        self.assertLess(light, heavy)

    def test_graph_is_wired(self):
        self.assertEqual(graphcheck.tree_problems(wear.material_graph()["trees"][0]), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"wear_width": 0.0}, {"sensitivity": 0.0}, {"metal_color": "steel"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                wear.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
