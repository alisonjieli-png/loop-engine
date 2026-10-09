"""Known answers for the text format parser and in-memory known-wrong files."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import godot_scene_linter as linter  # noqa: E402

PROJECT = ROOT / "fixtures" / "project"


class Parser(unittest.TestCase):
    def test_multi_line_values_strings_and_header_arrays(self):
        text = ('[gd_scene format=3]\n\n[sub_resource type="ArrayMesh" id="Mesh_1"]\n_surfaces = [{\n"name": "a ] b",\n'
                '"aabb": AABB(0, 0, 0, 1, 1, 1)\n}]\n\n; a comment line\n[node name="Root" type="Node3D" '
                'groups=["doors", "props"]]\nmetadata/label = "say \\"hi\\" [ok]"\n')
        sections = linter.parse(text)
        self.assertEqual([section["kind"] for section in sections], ["gd_scene", "sub_resource", "node"])
        self.assertEqual(sections[1]["properties"][0][0], "_surfaces")
        self.assertTrue(sections[1]["properties"][0][1].endswith("}]"))
        self.assertEqual(sections[2]["attributes"]["groups"], '["doors", "props"]')
        self.assertEqual(sections[2]["properties"][0][1], '"say \\"hi\\" [ok]"')

    def test_unbalanced_values_are_refused_with_their_line(self):
        with self.assertRaises(linter.ParseError) as caught:
            linter.parse('[gd_scene format=3]\n\n[node name="A" type="Node"]\nposition = Vector3(1, 2\n')
        self.assertEqual(caught.exception.line, 4)
        with self.assertRaises(linter.ParseError):
            linter.parse('key = 1\n')


class Rules(unittest.TestCase):
    def test_room_knows_the_nodes_of_its_instances(self):
        paths = linter.node_paths(PROJECT / "scenes" / "room.tscn", PROJECT)
        self.assertIn("DoorA/Panel/Handle", paths)
        self.assertIn("DoorB/Timer", paths)

    def test_godot3_ids_are_read(self):
        report = linter.lint(PROJECT / "scenes" / "godot3_door.tscn").as_dict()
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual([warning["code"] for warning in report["warnings"]], ["godot3_format"])

    def test_without_a_project_files_are_not_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "lonely.tscn"
            scene.write_text('[gd_scene format=3]\n\n[ext_resource type="Script" path="res://missing.gd" id="1"]\n\n'
                             '[node name="A" type="Node"]\nscript = ExtResource("1")\n', encoding="utf-8")
            report = linter.lint(scene)
            self.assertEqual(report.codes(), [])
            self.assertEqual([warning["code"] for warning in report.warnings], ["project_root_unknown"])

    def test_repeated_ids_and_missing_resource_section(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            material = Path(folder) / "m.tres"
            material.write_text('[gd_resource type="StandardMaterial3D" format=3]\n\n[sub_resource type="Gradient" '
                                'id="g"]\n\n[sub_resource type="Gradient" id="g"]\n', encoding="utf-8")
            self.assertEqual(linter.lint(material).codes(), ["resource_section_missing", "sub_resource_id_repeated"])


if __name__ == "__main__":
    unittest.main()
