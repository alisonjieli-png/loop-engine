"""Known answers for the fence: post and bay counts, picket outlines, closed parts, refusals."""
import unittest

import meshcheck
import picket_fence as fence


class FenceTests(unittest.TestCase):
    def test_posts_and_bays(self):
        report = fence.build_geometry(points="0,0,0; 5,0,0", post_spacing=2.0)["report"]
        self.assertEqual(report["posts"], 4)
        self.assertEqual(report["rails"], 6)
        report = fence.build_geometry(points="0,0,0; 4,0,0; 4,4,0", post_spacing=2.0)["report"]
        self.assertEqual(report["posts"], 5, "the corner post is shared")
        self.assertAlmostEqual(report["path_length_m"], 8.0)

    def test_picket_outlines(self):
        for top in ("pointed", "flat", "round", "dog_ear"):
            outline = fence.picket_outline(0.1, 1.0, top)
            area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(outline, outline[1:] + outline[:1])) / 2
            self.assertGreater(area, 0.08, top)
            self.assertAlmostEqual(max(y for _x, y in outline), 1.0)

    def test_parts_are_closed(self):
        mesh = fence.build_geometry(top="round")
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        report = mesh["report"]
        parts = report["posts"] + report["rails"] + report["pickets"]
        self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]), 2 * parts)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"points": "0,0,0; 0.1,0,0"}, {"top": "spiky"}, {"points": "1,2,3"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                fence.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
