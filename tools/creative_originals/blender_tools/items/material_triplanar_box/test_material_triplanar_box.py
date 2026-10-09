"""Known answers for the triplanar material: texture size, image choice, wiring, refusals."""
import unittest

import graphcheck
import material_triplanar_box as tri


class TriplanarTests(unittest.TestCase):
    def test_texture_size_scales_coordinates(self):
        tree = tri.material_graph(texture_size=0.25)["trees"][0]
        scale = next(node for node in tree["nodes"] if node["name"] == "Texture Size")["inputs"]["Scale"]
        self.assertEqual(scale, [4.0, 4.0, 4.0])
        self.assertEqual(tri.repeats(3.0, texture_size=0.5), 6.0)

    def test_image_choice(self):
        self.assertEqual(tri.material_graph()["images"][0]["source"], "GENERATED")
        image = tri.material_graph(image_path="//maps/stone.png")["images"][0]
        self.assertEqual((image["source"], image["name"]), ("FILE", "stone.png"))

    def test_box_projection(self):
        tree = tri.material_graph()["trees"][0]
        node = next(node for node in tree["nodes"] if node["name"] == "Box Projection")
        self.assertEqual(node["properties"]["projection"], "BOX")
        self.assertEqual(graphcheck.tree_problems(tree), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"image_path": "notes.txt"}, {"texture_size": 0.0}, {"grid_resolution": 8}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                tri.material_graph(**bad)
        with self.assertRaises(ValueError):
            tri.repeats(-1.0)


if __name__ == "__main__":
    unittest.main()
