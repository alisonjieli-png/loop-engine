"""Known answers for the weave: over-under parity, thread profile, wiring, refusals."""
import unittest

import graphcheck
import material_fabric_weave as fabric


class WeaveTests(unittest.TestCase):
    def test_parity_alternates(self):
        self.assertEqual(fabric.weave_at(0.5 / 60, 0.5 / 60)[0], "warp")
        self.assertEqual(fabric.weave_at(1.5 / 60, 0.5 / 60)[0], "weft")
        self.assertEqual(fabric.weave_at(1.5 / 60, 1.5 / 60)[0], "warp")

    def test_profile_peaks_mid_thread(self):
        _top, middle = fabric.weave_at(0.5 / 60, 0.2 / 60)
        _top, edge = fabric.weave_at(0.02 / 60, 0.2 / 60)
        self.assertAlmostEqual(middle, 1.0)
        self.assertLess(edge, 0.1)

    def test_graph_is_wired(self):
        tree = fabric.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"threads": 0.5}, {"sheen": -0.1}, {"weft_color": [0.0, 0.0, 1.5]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                fabric.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
