"""Known answers for the brick material: orientation swizzle, course count, sizes in metres, refusals."""
import unittest

import graphcheck
import material_brick_procedural as brick


class BrickMaterialTests(unittest.TestCase):
    def test_orientation_routes_axes(self):
        for orientation, axes in (("wall_xz", ["X", "Z", "Y"]), ("floor_xy", ["X", "Y", "Z"]),
                                  ("wall_yz", ["Y", "Z", "X"])):
            tree = brick.material_graph(orientation=orientation)["trees"][0]
            routed = [link["from"][1] for link in tree["links"] if link["to"][0] == "Wall Plane"]
            self.assertEqual(routed, axes)
            self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_sizes_are_metres(self):
        tree = brick.material_graph(brick_width=0.3, row_height=0.1)["trees"][0]
        bricks = next(node for node in tree["nodes"] if node["name"] == "Bricks")
        self.assertEqual(bricks["inputs"]["Scale"], 1.0)
        self.assertEqual(bricks["inputs"]["Brick Width"], 0.3)
        self.assertEqual(brick.courses(2.4), 32)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"mortar_size": 0.05}, {"orientation": "ceiling"}, {"grime": 2.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                brick.material_graph(**bad)
        with self.assertRaises(ValueError):
            brick.courses(-1.0)


if __name__ == "__main__":
    unittest.main()
