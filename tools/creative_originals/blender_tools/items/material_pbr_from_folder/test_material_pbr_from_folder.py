"""Known answers for PBR detection: synonyms, DirectX normals, gloss, duplicates, the graph, refusals."""
import unittest

import graphcheck
import material_pbr_from_folder as pbr


class PbrTests(unittest.TestCase):
    def test_demo_classification(self):
        found = pbr.classify(pbr.DEMO_FILES)
        self.assertEqual(found["channels"], {"base_color": "rock_wall_basecolor.png", "roughness":
                                             "rock_wall_roughness.png", "normal": "rock_wall_normal_dx.png",
                                             "height": "rock_wall_height.png", "ao": "rock_wall_ao.png"})
        self.assertEqual(found["normal_convention"], "directx")
        self.assertEqual(found["ignored"], ["rock_wall_preview.txt"])

    def test_synonyms_and_camel_case(self):
        found = pbr.classify(["metalAlbedo.jpg", "metal_Metalness.png", "metal_Gloss.tif", "metal_normalGL.png"])
        self.assertEqual(found["channels"]["base_color"], "metalAlbedo.jpg")
        self.assertEqual(found["channels"]["roughness_from_gloss"], "metal_Gloss.tif")
        self.assertEqual(found["normal_convention"], "opengl")
        self.assertEqual(pbr.tokens("wallBaseColor_2K.png"), ["wall", "base", "color", "2k"])

    def test_duplicates_are_reported(self):
        found = pbr.classify(["a_albedo.png", "b_diffuse.png"])
        self.assertEqual(found["duplicates"], ["b_diffuse.png"])

    def test_graph_for_the_demo(self):
        graph = pbr.material_graph()
        tree = graph["trees"][0]
        self.assertEqual(graphcheck.tree_problems(tree), [])
        self.assertEqual(len(graph["images"]), 5)
        self.assertIn({"from": ["Displacement", "Displacement"], "to": ["Output", "Displacement"]}, tree["links"])
        self.assertTrue(any(node["name"] == "Flip Green" for node in tree["nodes"]))

    def test_known_wrong_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            pbr.material_graph(["notes.txt", "readme.md"])
        for bad in ({"folder": "  "}, {"uv_scale": 0.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pbr.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
