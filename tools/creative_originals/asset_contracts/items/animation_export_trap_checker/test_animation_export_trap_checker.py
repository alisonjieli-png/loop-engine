"""Known answers for clip reading and in-memory known-wrong declarations and exports."""
from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import animation_export_trap_checker as trap  # noqa: E402
import asset_report  # noqa: E402
import gltfio  # noqa: E402

DOOR = ROOT / "fixtures" / "door.gltf"
DECLARATION = json.loads((ROOT / "fixtures" / "door.clips.json").read_text(encoding="utf-8"))


def codes(declaration: dict, document: "dict | None" = None) -> list:
    report = asset_report.Report("test")
    asset = gltfio.load(DOOR) if document is None else gltfio.loads(json.dumps(document))
    declared = trap.read_declaration(declaration, report)
    if declared is not None:
        trap.compare(declared, trap.export_clips(asset), report)
    return report.codes()


class ClipFacts(unittest.TestCase):
    def test_door_clips(self):
        clips = trap.export_clips(gltfio.load(DOOR))
        self.assertEqual([clip["name"] for clip in clips], ["Open", "Close", "HandlePress"])
        self.assertAlmostEqual(clips[0]["length_s"], 1.2, places=5)
        channel = clips[2]["channels"][0]
        self.assertEqual((channel["node_name"], channel["path"], channel["keys"], channel["moving"]),
                         ("DoorHandle", "rotation", 3, True))

    def test_an_asset_specification_can_declare(self):
        spec = {"record_type": "asset_specification/v1", "parts": [],
                "clips": [{"name": "Open", "duration_s": 1.2, "targets": [{"part": "DoorPanel", "path": "rotation"}]}]}
        self.assertEqual(codes(spec), [])


class KnownWrong(unittest.TestCase):
    def test_declared_target_on_the_wrong_node(self):
        declaration = json.loads(json.dumps(DECLARATION))
        declaration["clips"][0]["targets"] = [{"node": "DoorFrame", "path": "rotation"}]
        self.assertEqual(codes(declaration), ["clip_target_missing"])

    def test_declared_duration_tolerance(self):
        declaration = json.loads(json.dumps(DECLARATION))
        declaration["clips"][2]["duration_s"] = 0.44
        self.assertEqual(codes(declaration), [])
        declaration["clips"][2]["duration_s"] = 0.5
        self.assertEqual(codes(declaration), ["clip_duration_mismatch"])

    def test_invalid_declarations(self):
        for broken in ({"record_type": "animation_declaration/v1", "clips": "Open"},
                       {"record_type": "animation_declaration/v1", "clips": [{"name": ""}]},
                       {"record_type": "animation_declaration/v1", "clips": [{"name": "Open", "duration_s": -1}]},
                       {"record_type": "unknown", "clips": []}):
            with self.subTest(declaration=broken):
                self.assertEqual(codes(broken), ["declaration_invalid"])

    def test_channel_outside_the_scene(self):
        document = json.loads(DOOR.read_text(encoding="utf-8"))
        document["nodes"].append({"name": "Loose"})
        document["animations"][2]["channels"][0]["target"]["node"] = 3
        found = codes(DECLARATION, document)
        self.assertIn("channel_target_unresolved", found)
        self.assertIn("clip_target_missing", found)


class ProcedureScripts(unittest.TestCase):
    def test_blender_scripts_parse_and_name_their_inputs(self):
        for name in ("declare_clips_blender.py", "push_actions_to_nla.py"):
            text = (ROOT / "procedure" / name).read_text(encoding="utf-8")
            tree = ast.parse(text)
            functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
            self.assertIn("main", functions)
            self.assertIn('sys.argv.index("--")', text)


if __name__ == "__main__":
    unittest.main()
