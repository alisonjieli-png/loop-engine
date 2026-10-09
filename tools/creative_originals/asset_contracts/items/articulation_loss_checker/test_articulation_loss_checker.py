"""Known answers for joint facts, and in-memory known-wrong exports and tolerances."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import articulation_loss_checker as loss  # noqa: E402
import asset_report  # noqa: E402
import gltfio  # noqa: E402

REFERENCE = gltfio.load(ROOT / "fixtures" / "door_reference.gltf")
MANIFEST = json.loads((ROOT / "fixtures" / "door_reference.articulation.json").read_text(encoding="utf-8"))


def codes(document: dict, extras: bool = True, tolerance_m: float = 0.001) -> list:
    report = asset_report.Report("test")
    joints = loss.read_joints(MANIFEST, report)
    loss.compare(joints, gltfio.loads(json.dumps(document)), REFERENCE, extras, tolerance_m, 0.5, report)
    return report.codes()


class Facts(unittest.TestCase):
    def test_reference_facts(self):
        facts = loss.joint_facts(REFERENCE, MANIFEST["joints"][1])
        self.assertEqual((facts["present"], facts["parent"], facts["has_geometry"]), (True, "DoorPanel", True))
        for found, expected in zip(facts["world_pivot"], (0.33, 1.0, 0.02)):
            self.assertAlmostEqual(found, expected, places=5)
        self.assertEqual([round(value, 6) for value in facts["world_axis"]], [0.0, 0.0, 1.0])
        self.assertEqual(facts["extras"]["limits"], [-35.0, 0.0])


class KnownWrong(unittest.TestCase):
    def setUp(self):
        self.document = copy.deepcopy(REFERENCE.document)

    def test_pivot_tolerance(self):
        self.document["nodes"][1]["translation"][0] = -0.4495
        self.assertEqual(codes(self.document), [])
        self.document["nodes"][1]["translation"][0] = -0.447
        self.assertEqual(codes(self.document), ["pivot_moved"])

    def test_node_without_geometry_and_repeated_names(self):
        broken = copy.deepcopy(self.document)
        del broken["nodes"][2]["mesh"]
        self.assertIn("joint_node_without_geometry", codes(broken))
        broken = copy.deepcopy(self.document)
        broken["nodes"][0]["name"] = "DoorPanel"
        self.assertIn("joint_node_ambiguous", codes(broken))

    def test_extras_optional_by_default(self):
        for node in self.document["nodes"]:
            node.pop("extras", None)
        self.assertEqual(codes(self.document, extras=False), [])
        self.assertEqual(codes(self.document, extras=True), ["joint_extras_missing"])

    def test_unreadable_reference(self):
        report = loss.check(ROOT / "fixtures" / "door_reference.gltf", ROOT / "fixtures" / "door_reference.articulation.json",
                            ROOT / "fixtures" / "absent.gltf")
        self.assertEqual(report.codes(), ["reference_unreadable"])


if __name__ == "__main__":
    unittest.main()
