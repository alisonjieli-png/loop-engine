"""Known answers for the cross-reference rules and the blockout geometry."""
from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import asset_specification_schema as specification  # noqa: E402
import gltfio  # noqa: E402

CABINET = json.loads((ROOT / "fixtures" / "cabinet_with_drawer.spec.json").read_text(encoding="utf-8"))


def codes(spec: dict) -> list:
    return specification.validate(spec).codes()


class Rules(unittest.TestCase):
    def test_valid_cabinet(self):
        report = specification.validate(CABINET).as_dict()
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["facts"]["depth"], 2)
        self.assertEqual(report["facts"]["roots"], ["Cabinet"])

    def test_joint_type_and_limits(self):
        spec = copy.deepcopy(CABINET)
        spec["joints"][1]["rest"] = 5.0
        self.assertEqual(codes(spec), ["joint_limits_invalid"])
        spec = copy.deepcopy(CABINET)
        spec["joints"][1]["type"] = "continuous"
        self.assertEqual(codes(spec), ["joint_limits_invalid"])
        spec = copy.deepcopy(CABINET)
        spec["joints"][0]["axis"] = [0.0, 0.0, 2.0]
        self.assertEqual(codes(spec), ["joint_axis_not_unit"])

    def test_repeated_names(self):
        spec = copy.deepcopy(CABINET)
        spec["joints"][1]["part"] = "Drawer"
        spec["clips"][1]["name"] = "OpenDrawer"
        spec["materials"][1]["name"] = "Oak"
        self.assertEqual(codes(spec), ["behavior_reference_unknown", "clip_name_repeated", "joint_part_repeated",
                                       "material_name_repeated", "material_unknown"])

    def test_several_roots_is_a_warning(self):
        spec = copy.deepcopy(CABINET)
        spec["parts"][3]["parent"] = None
        report = specification.validate(spec)
        self.assertEqual(report.codes(), [])
        self.assertEqual([warning["code"] for warning in report.warnings], ["several_roots"])

    def test_unreadable_file(self):
        self.assertEqual(specification.check(ROOT / "fixtures" / "absent.spec.json").codes(),
                         ["specification_unreadable"])


class Blockout(unittest.TestCase):
    def test_boxes_pivots_and_range_clips(self):
        asset = gltfio.loads(json.dumps(specification.blockout(CABINET)))
        names = [node["name"] for node in asset.items("nodes")]
        matrices = gltfio.world_matrices(asset.document)
        door = names.index("CabinetDoor")
        self.assertEqual([round(matrices[door][row][3], 6) for row in range(3)], [-0.39, 0.33, 0.26])
        boxes = gltfio.node_world_bounds(asset)
        low, high = boxes[names.index("Drawer")]
        for found, expected in zip(low + high, (-0.35, 0.67, -0.21, 0.35, 0.85, 0.25)):
            self.assertAlmostEqual(found, expected, places=5)
        clips = {clip["name"]: clip for clip in gltfio.animation_clips(asset)}
        self.assertEqual(sorted(clips), ["door_hinge_lower", "drawer_slide_upper"])
        hinge = asset.items("animations")[[a["name"] for a in asset.items("animations")].index("door_hinge_lower")]
        first, last = (gltfio.accessor_values(asset, hinge["samplers"][0]["output"])[i] for i in (0, -1))
        self.assertEqual(first, (0.0, 0.0, 0.0, 1.0))
        self.assertAlmostEqual(last[1], -math.sin(math.radians(55)), places=5)
        self.assertAlmostEqual(last[3], math.cos(math.radians(55)), places=5)

    def test_schema_dialect_and_keywords(self):
        import schema_lite
        self.assertEqual(specification.SCHEMA["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema_lite.unsupported_keywords(specification.SCHEMA), [])


if __name__ == "__main__":
    unittest.main()
