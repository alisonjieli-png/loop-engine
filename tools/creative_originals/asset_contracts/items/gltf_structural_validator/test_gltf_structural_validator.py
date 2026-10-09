"""Known answers for the shared glTF reader and in-memory known-wrong controls for codes no fixture covers."""
from __future__ import annotations

import copy
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gltf_structural_validator as validator  # noqa: E402
import gltfio  # noqa: E402

CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
GOOD = ROOT / "fixtures" / "good_door.gltf"


def codes(document: dict) -> list:
    return validator.validate(gltfio.loads(json.dumps(document))).codes()


class ReaderKnownAnswers(unittest.TestCase):
    def test_matrix_column_padding(self):
        self.assertEqual(gltfio.element_size(5121, "MAT2"), 8)
        self.assertEqual(gltfio.element_size(5121, "MAT3"), 12)
        self.assertEqual(gltfio.element_size(5123, "MAT3"), 24)
        self.assertEqual(gltfio.element_size(5126, "MAT4"), 64)

    def test_quaternion_quarter_turn_about_y(self):
        half = 2 ** -0.5
        matrix = gltfio.compose((1.0, 2.0, 3.0), (0.0, half, 0.0, half), (2.0, 2.0, 2.0))
        moved = gltfio.transform_point(matrix, (1.0, 0.0, 0.0))
        for found, expected in zip(moved, (1.0, 2.0, 1.0)):
            self.assertAlmostEqual(found, expected, places=6)

    def test_column_major_matrix(self):
        node = {"matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 5, 6, 7, 1]}
        self.assertEqual([row[3] for row in gltfio.node_local_matrix(node)[:3]], [5.0, 6.0, 7.0])

    def test_repeated_key_is_refused(self):
        with self.assertRaises(gltfio.GltfError) as caught:
            gltfio.strict_json('{"asset": {"version": "2.0"}, "asset": {}}')
        self.assertEqual(caught.exception.reason, "json_duplicate_key")

    def test_door_facts(self):
        report = validator.validate_file(GOOD).as_dict()
        self.assertTrue(report["ok"])
        self.assertEqual(report["facts"]["triangles"], 60)
        self.assertEqual(report["facts"]["scene_bounds"], {"min": [-0.55, 0.0, -0.075], "max": [0.55, 2.1, 0.075]})


class ContainerTests(unittest.TestCase):
    def test_glb_container_reads_like_the_gltf(self):
        document = json.loads(GOOD.read_text(encoding="utf-8"))
        binary = gltfio.decode_data_uri(document["buffers"][0].pop("uri"))
        text = json.dumps(document).encode()
        text += b" " * (-len(text) % 4)
        binary += b"\x00" * (-len(binary) % 4)
        body = struct.pack("<II", len(text), 0x4E4F534A) + text + struct.pack("<II", len(binary), 0x004E4942) + binary
        glb = struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body
        report = validator.validate(gltfio.loads(glb)).as_dict()
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["facts"]["container"], "glb")
        self.assertEqual(report["facts"]["triangles"], 60)
        with self.assertRaises(gltfio.GltfError):
            gltfio.loads(glb[:-4])


class InMemoryKnownWrong(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(GOOD.read_text(encoding="utf-8"))

    def test_header_and_extensions(self):
        broken = copy.deepcopy(self.document)
        broken["asset"] = {"version": "1.0"}
        self.assertIn("asset_version_unsupported", codes(broken))
        broken = copy.deepcopy(self.document)
        broken["extensionsRequired"] = ["KHR_draco_mesh_compression"]
        self.assertIn("extension_required_not_used", codes(broken))

    def test_references_and_values(self):
        broken = copy.deepcopy(self.document)
        broken["nodes"][0]["mesh"] = 9
        broken["meshes"][1]["primitives"][0]["material"] = 7
        broken["materials"][2]["pbrMetallicRoughness"]["metallicFactor"] = 2.0
        broken["scenes"][0]["nodes"] = [0, 1]
        found = codes(broken)
        for code in ("mesh_reference_invalid", "material_reference_invalid", "material_value_invalid",
                     "scene_node_not_root"):
            self.assertIn(code, found)

    def test_animation_sampler_rules(self):
        broken = copy.deepcopy(self.document)
        broken["animations"][0]["samplers"][0]["interpolation"] = "SMOOTH"
        broken["animations"][1]["channels"][0]["target"]["path"] = "colour"
        found = codes(broken)
        self.assertIn("animation_interpolation_invalid", found)
        self.assertIn("animation_target_invalid", found)

    def test_unreadable_inputs(self):
        report = validator.validate_file(ROOT / "fixtures" / "missing.gltf")
        self.assertEqual(report.codes(), ["file_unreadable"])
        self.assertEqual(validator.validate(gltfio.loads('{"asset": {"version": "2.0"}, "nodes": {}}')).codes(),
                         ["property_type_invalid"])

    def test_contract_lists_every_code_the_tool_can_emit(self):
        self.assertEqual(sorted(CARD["contract"]["failures_detected"]), sorted(validator.FAILURES))


if __name__ == "__main__":
    unittest.main()
