"""Known answers for the soap bubble: drainage gradient, swirl range, wiring, refusals."""
import unittest

import graphcheck
import material_soap_bubble as bubble


class BubbleTests(unittest.TestCase):
    def test_drainage_gradient(self):
        self.assertEqual(bubble.thickness_at(1.0), 250.0)
        self.assertEqual(bubble.thickness_at(0.0), 900.0)
        self.assertEqual(bubble.thickness_at(0.5), 575.0)

    def test_swirl_and_floor(self):
        self.assertEqual(bubble.thickness_at(1.0, 1.0), 430.0)
        self.assertEqual(bubble.thickness_at(1.0, 0.0, top_thickness=50.0, swirl=200.0), 0.0)

    def test_graph_is_wired(self):
        tree = bubble.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        self.assertIn({"from": ["Not Negative", "Value"], "to": ["Film", "Thin Film Thickness"]}, tree["links"])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"film_ior": 0.9}, {"top_thickness": -1.0}, {"swirl_scale": 0.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                bubble.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
