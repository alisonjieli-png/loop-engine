"""Known answers for the recovered facts, the tolerance rule and the unit and axis hints."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import asset_report  # noqa: E402
import gltf_semantic_recovery as recovery  # noqa: E402
import gltfio  # noqa: E402

DOOR = ROOT / "fixtures" / "door.gltf"
SPEC = json.loads((ROOT / "fixtures" / "door.spec.json").read_text(encoding="utf-8"))


def codes_for(spec: dict) -> list:
    report = asset_report.Report("test")
    recovery.compare(recovery.recover(gltfio.load(DOOR)), spec, report)
    return report.codes()


class RecoveredFacts(unittest.TestCase):
    def test_door_parts(self):
        facts = recovery.recover(gltfio.load(DOOR))
        parts = {part["name"]: part for part in facts["parts"]}
        self.assertEqual(sorted(parts), ["DoorFrame", "DoorHandle", "DoorPanel"])
        self.assertEqual(parts["DoorHandle"]["parent"], "DoorPanel")
        for found, expected in zip(parts["DoorPanel"]["dimensions_m"], (0.9, 2.0, 0.04)):
            self.assertAlmostEqual(found, expected, places=5)
        for found, expected in zip(parts["DoorPanel"]["subtree_dimensions_m"], (0.9, 2.0, 0.08)):
            self.assertAlmostEqual(found, expected, places=5)
        self.assertEqual([clip["name"] for clip in facts["clips"]], ["Open", "Close", "HandlePress"])
        self.assertAlmostEqual(facts["clips"][2]["length_s"], 0.4, places=5)

    def test_tolerance_is_honoured(self):
        spec = copy.deepcopy(SPEC)
        spec["parts"][1]["dimensions_m"] = [0.903, 2.0, 0.04]
        self.assertEqual(codes_for(spec), [])
        spec["parts"][1]["dimensions_m"] = [0.906, 2.0, 0.04]
        self.assertEqual(codes_for(spec), ["part_dimensions_mismatch"])

    def test_subtree_measure(self):
        spec = copy.deepcopy(SPEC)
        spec["parts"][1].update(measure="subtree", dimensions_m=[0.9, 2.0, 0.08])
        self.assertEqual(codes_for(spec), [])


class Hints(unittest.TestCase):
    def test_unit_factors(self):
        self.assertIn("centimetres", recovery.dimension_hint([1.0, 2.0, 0.5], [100.0, 200.0, 50.0], 0.005))
        self.assertIn("inches", recovery.dimension_hint([1.0, 2.0, 0.5], [39.37, 78.74, 19.685], 0.005))
        self.assertIn("1/100", recovery.dimension_hint([1.0, 2.0, 0.5], [0.01, 0.02, 0.005], 0.005))

    def test_axis_swap_and_no_hint(self):
        self.assertIn("swapped", recovery.dimension_hint([1.1, 2.1, 0.15], [1.1, 0.15, 2.1], 0.005))
        self.assertEqual(recovery.dimension_hint([1.0, 2.0, 0.5], [1.3, 2.0, 0.5], 0.005), "")


class KnownWrongSpecifications(unittest.TestCase):
    def test_invalid_specifications_are_refused(self):
        for broken in ({"record_type": "something_else", "parts": []},
                       {"record_type": "asset_specification/v1", "parts": [{"name": "A", "pivot_m": [0, 0]}]},
                       {"record_type": "asset_specification/v1", "parts": [], "clips": {}}):
            with self.subTest(spec=broken):
                report = asset_report.Report("test")
                self.assertIsNone(recovery.read_specification(broken, report))
                self.assertEqual(report.codes(), ["specification_invalid"])

    def test_duplicate_part_names_are_ambiguous(self):
        document = json.loads(DOOR.read_text(encoding="utf-8"))
        document["nodes"][2]["name"] = "DoorPanel"
        report = asset_report.Report("test")
        recovery.compare(recovery.recover(gltfio.loads(json.dumps(document))), SPEC, report)
        self.assertIn("part_ambiguous", report.codes())


if __name__ == "__main__":
    unittest.main()
