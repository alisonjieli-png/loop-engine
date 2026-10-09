"""Known answers for the concrete material: optional seam branch, wiring, refusals."""
import unittest

import graphcheck
import material_concrete as concrete


class ConcreteTests(unittest.TestCase):
    def test_board_lines_add_the_seam_branch(self):
        plain = concrete.material_graph(board_lines=False)["trees"][0]
        seams = concrete.material_graph(board_lines=True)["trees"][0]
        self.assertEqual(len(plain["nodes"]), 13)
        self.assertEqual(len(seams["nodes"]), 18)
        for tree in (plain, seams):
            self.assertEqual(graphcheck.tree_problems(tree), [])
        units = next(node for node in seams["nodes"] if node["name"] == "Board Units")
        self.assertEqual(units["inputs"]["Value_001"], 0.15)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"aggregate_amount": 0.9}, {"board_width": 0.0}, {"material_name": " "}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                concrete.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
