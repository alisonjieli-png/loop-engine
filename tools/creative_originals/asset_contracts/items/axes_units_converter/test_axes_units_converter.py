"""Known answers for conventions and conversions, round trips through every convention, and refusals."""
from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import axes_units_converter as axes  # noqa: E402
import gltfio  # noqa: E402

DOOR = ROOT / "fixtures" / "door.gltf"


class Conventions(unittest.TestCase):
    def test_blender_to_gltf_matrix(self):
        q, k, flip = axes.conversion("z_up_right", "gltf")
        self.assertEqual(q, [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
        self.assertEqual((k, flip), (1.0, False))

    def test_left_handed_mirrors_without_reversing_clockwise_faces(self):
        q, _k, flip = axes.conversion("y_up_left_cw", "gltf")
        self.assertLess(axes.determinant(q), 0)
        self.assertFalse(flip)
        _q, _k, flip = axes.conversion("gltf", "z_up_right", unit_m=1.0, target_unit_m=0.01)
        self.assertFalse(flip)

    def test_rotation_about_blender_z_is_rotation_about_gltf_y(self):
        q, _k, _flip = axes.conversion("z_up_right", "gltf")
        half = math.radians(30)
        rotated = axes._quaternion(q, (0.0, 0.0, math.sin(half), math.cos(half)))
        for found, expected in zip(rotated, (0.0, math.sin(half), 0.0, math.cos(half))):
            self.assertAlmostEqual(found, expected, places=9)


class RoundTrips(unittest.TestCase):
    def test_every_convention_round_trips(self):
        original = gltfio.load(DOOR)
        expected = gltfio.node_world_bounds(original)
        with tempfile.TemporaryDirectory() as folder:
            for convention in sorted(axes.CONVENTIONS):
                there, back = Path(folder) / f"{convention}.gltf", Path(folder) / f"{convention}_back.gltf"
                self.assertTrue(axes.convert(DOOR, there, "gltf", convention, unit_m=1.0).as_dict()["facts"])
                report = axes.convert(there, back, convention, "gltf", expected=[1.1, 2.1, 0.15]).as_dict()
                self.assertTrue(report["ok"], report["failures"])
                found = gltfio.node_world_bounds(gltfio.load(back))
                for index, box in expected.items():
                    for corner in range(2):
                        for axis in range(3):
                            self.assertAlmostEqual(found[index][corner][axis], box[corner][axis], places=6)

    def test_unit_conversion_scales_animation_translations(self):
        q, k, flip = axes.conversion("gltf", "gltf", unit_m=0.01)
        document = json.loads(DOOR.read_text(encoding="utf-8"))
        document["nodes"][2]["translation"] = [78.0, 100.0, 2.0]
        converted = axes.convert_document(gltfio.loads(json.dumps(document)), q, k, flip)
        self.assertEqual(converted["nodes"][2]["translation"], [0.78, 1.0, 0.02])


class Refusals(unittest.TestCase):
    def test_quantized_positions_are_refused(self):
        document = {"asset": {"version": "2.0"}, "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}],
                    "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}]}
        builder = gltfio.BufferBuilder(document)
        builder.add([(0, 0, 0), (1, 0, 0), (0, 1, 0)], 5123, "VEC3", bounds=True)
        q, k, flip = axes.conversion("z_up_right")
        with self.assertRaises(gltfio.GltfError) as caught:
            axes.convert_document(gltfio.loads(json.dumps(builder.finish())), q, k, flip)
        self.assertEqual(caught.exception.reason, "conversion_unsupported")

    def test_mismatches_are_named(self):
        self.assertEqual(axes.check(DOOR, [1.1, 2.1, 0.3]).codes(), ["dimensions_mismatch"])
        self.assertEqual(axes.check(DOOR, [0.011, 0.021, 0.0015]).codes(), ["unit_scale_mismatch"])


if __name__ == "__main__":
    unittest.main()
