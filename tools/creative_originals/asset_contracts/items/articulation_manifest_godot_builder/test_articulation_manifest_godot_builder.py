"""Known answers for joint motion and forward kinematics, schema agreement, and known-wrong bindings."""
from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import articulation_manifest_godot_builder as articulation  # noqa: E402
import asset_report  # noqa: E402
import gltfio  # noqa: E402
import schema_lite  # noqa: E402

TOOLBOX = gltfio.load(ROOT / "fixtures" / "toolbox.gltf")
MANIFEST = json.loads((ROOT / "fixtures" / "toolbox.articulation.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))


def bound(manifest: dict, document: dict = TOOLBOX.document) -> tuple:
    report = asset_report.Report("test")
    return articulation.read_manifest(manifest, document, report), report.codes()


class Kinematics(unittest.TestCase):
    def test_hinge_keeps_its_pivot_and_turns_the_lid(self):
        joints, codes = bound(MANIFEST)
        self.assertEqual(codes, [])
        lid = articulation.predictions(TOOLBOX.document, joints)[0]
        self.assertEqual(lid["joint"], "lid_hinge")
        for label in ("lower", "upper"):
            for found, expected in zip(lid[label]["world_pivot"], (0.0, 0.25, -0.15)):
                self.assertAlmostEqual(found, expected, places=6)
        matrix = lid["lower"]["world_matrix"]
        self.assertAlmostEqual(matrix[1][1], math.cos(math.radians(-110)), places=6)
        self.assertAlmostEqual(matrix[2][1], math.sin(math.radians(-110)), places=6)

    def test_slider_moves_along_its_axis_and_values_clamp(self):
        joints, _codes = bound(MANIFEST)
        matrices = articulation.pose(TOOLBOX.document, joints, {"tray_slide": 5.0})
        tray = [node["name"] for node in TOOLBOX.items("nodes")].index("Tray")
        self.assertAlmostEqual(matrices[tray][2][3], 0.02 + 0.2, places=6)

    def test_children_follow_their_jointed_parent(self):
        door = gltfio.load(ROOT / "fixtures" / "door.gltf")
        manifest = json.loads((ROOT / "fixtures" / "door.articulation.json").read_text(encoding="utf-8"))
        joints, _codes = bound(manifest, door.document)
        handle = articulation.pose(door.document, joints, {"door_hinge": 90.0})[2]
        self.assertAlmostEqual(handle[0][3], -0.45 + 0.02, places=5)
        self.assertAlmostEqual(handle[2][3], -0.78, places=5)


class KnownWrong(unittest.TestCase):
    def test_rest_outside_limits_and_unit_axis(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["joints"][1]["rest"] = 0.5
        self.assertEqual(bound(manifest)[1], ["limits_invalid"])
        manifest = copy.deepcopy(MANIFEST)
        manifest["joints"][0]["axis"] = [1.0, 1.0, 0.0]
        self.assertEqual(bound(manifest)[1], ["axis_invalid"])

    def test_repeated_joint_names_and_bad_pivots(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["joints"][1]["name"] = "lid_hinge"
        self.assertEqual(bound(manifest)[1], ["joint_name_repeated"])
        manifest = copy.deepcopy(MANIFEST)
        manifest["joints"][0]["pivot"] = [0.0, "low", 0.0]
        self.assertEqual(bound(manifest)[1], ["pivot_invalid"])

    def test_schema_accepts_the_manifests_and_refuses_shape_errors(self):
        self.assertEqual(schema_lite.validate(MANIFEST, SCHEMA), [])
        broken = copy.deepcopy(MANIFEST)
        broken["joints"][0]["kind"] = "hinge"
        self.assertEqual([error["keyword"] for error in schema_lite.validate(broken, SCHEMA)], ["additionalProperties"])


class GodotScripts(unittest.TestCase):
    def test_runtime_script_exposes_the_documented_methods(self):
        text = (ROOT / "godot" / "articulated_asset.gd").read_text(encoding="utf-8")
        for name in ("load_asset", "set_joint", "reset_joints", "build_animation_player", "save_scene", "motion"):
            self.assertIn(f"func {name}(", text)
        self.assertIn('preload("res://articulated_asset.gd")',
                      (ROOT / "godot" / "articulation_probe.gd").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
