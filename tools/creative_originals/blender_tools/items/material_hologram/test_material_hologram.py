"""Known answers for the hologram: scanline phase, wiring, refusals."""
import unittest

import graphcheck
import material_hologram as holo


class HologramTests(unittest.TestCase):
    def test_scanlines(self):
        self.assertEqual(holo.scanline(0.0), 0.0)
        self.assertEqual(holo.scanline(0.024, line_density=40.0, line_width=0.25), 1.0)
        self.assertEqual(holo.scanline(0.01, line_density=40.0, line_width=0.25), 0.0)

    def test_graph_is_wired(self):
        tree = holo.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"line_width": 0.95}, {"line_density": 0.0}, {"glitch": 2.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                holo.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
