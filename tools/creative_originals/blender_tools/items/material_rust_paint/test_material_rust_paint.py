"""Known answers for the rust material: threshold order, coverage direction, wiring, refusals."""
import unittest

import graphcheck
import material_rust_paint as rust


class RustTests(unittest.TestCase):
    def test_thresholds_are_ordered(self):
        start, full, chip = rust.thresholds(coverage=0.5, chip_width=0.05)
        self.assertLess(chip, start)
        self.assertLess(start, full)
        self.assertAlmostEqual(full - start, 0.04)

    def test_more_coverage_lowers_the_threshold(self):
        self.assertLess(rust.thresholds(coverage=0.9)[0], rust.thresholds(coverage=0.1)[0])

    def test_graph_mixes_three_shaders(self):
        tree = rust.material_graph()["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        bsdfs = [node for node in tree["nodes"] if node["type"] == "ShaderNodeBsdfPrincipled"]
        self.assertEqual(len(bsdfs), 3)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"coverage": 1.5}, {"ao_distance": 0.0}, {"paint_color": "green"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rust.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
