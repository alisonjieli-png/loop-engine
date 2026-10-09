"""Negative controls for the development tracker generated from the roadmap."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_development_tracker as tool


def dump(data):
    return yaml.safe_dump(data, sort_keys=False).encode()


class DevelopmentTrackerTests(unittest.TestCase):
    def setUp(self):
        self.raw = tool.ROADMAP.read_bytes()
        self.data = yaml.safe_load(self.raw)

    def test_every_live_step_lands_in_exactly_one_lane(self):
        tracker = tool.build(self.raw)
        placed = [row["id"] for rows in tracker["lanes"].values() for row in rows]
        live = [row["id"] for row in self.data["steps"] if row["status"] not in tool.RETIRED]
        self.assertEqual(sorted(placed), sorted(live))
        self.assertEqual(len(placed), len(set(placed)))

    def test_a_step_waits_until_every_dependency_is_done(self):
        data = copy.deepcopy(self.data)
        rows = {row["id"]: row for row in data["steps"]}
        first, second = data["steps"][0], data["steps"][1]
        first["status"], second["status"], second["depends_on"] = "building", "ready", [first["id"]]
        tracker = tool.build(dump(data))
        waiting = {row["id"]: row for row in tracker["lanes"]["waiting"]}
        self.assertIn(second["id"], waiting)
        self.assertEqual(waiting[second["id"]]["waiting_on"], [first["id"]])
        first["status"] = "offline_verified"
        tracker = tool.build(dump(data))
        self.assertIn(second["id"], [row["id"] for row in tracker["lanes"]["next"]])
        self.assertIn(first["id"], rows)

    def test_unknown_status_dependency_and_duplicate_are_refused(self):
        for change in ("status", "dependency", "duplicate"):
            data = copy.deepcopy(self.data)
            if change == "status":
                data["steps"][0]["status"] = "mostly_done"
            elif change == "dependency":
                data["steps"][0]["depends_on"] = ["S-NOT-A-STEP"]
            else:
                data["steps"].append(copy.deepcopy(data["steps"][0]))
            with self.assertRaises(tool.TrackerError):
                tool.build(dump(data))

    def test_a_package_that_names_an_unknown_step_is_refused(self):
        data = copy.deepcopy(self.data)
        data["continuation"]["delivery_batches"][0]["steps"].append("S-NOT-A-STEP")
        with self.assertRaises(tool.TrackerError):
            tool.build(dump(data))

    def test_a_gate_is_met_only_when_every_step_is_done(self):
        data = copy.deepcopy(self.data)
        gate = data["continuation"]["launch_gates"][0]
        for row in data["steps"]:
            if row["id"] in gate["steps"]:
                row["status"] = "live_qualified"
        met = {row["id"]: row["met"] for row in tool.build(dump(data))["launch_gates"]}
        self.assertTrue(met[gate["id"]])
        next(row for row in data["steps"] if row["id"] == gate["steps"][0])["status"] = "building"
        met = {row["id"]: row["met"] for row in tool.build(dump(data))["launch_gates"]}
        self.assertFalse(met[gate["id"]])

    def test_check_fails_when_the_committed_tracker_is_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            markdown, data = Path(folder, "tracker.md"), Path(folder, "tracker.json")
            with patch.object(tool, "MARKDOWN", markdown), patch.object(tool, "DATA", data), \
                    patch.object(tool, "ROOT", Path(folder)):
                self.assertEqual(tool.main([]), 0)
                self.assertEqual(tool.main(["--check"]), 0)
                markdown.write_text(markdown.read_text("utf-8") + "hand edit\n", "utf-8")
                self.assertEqual(tool.main(["--check"]), 1)

    def test_the_tracker_never_invents_state(self):
        tracker = tool.build(self.raw)
        self.assertEqual(tracker["source"], "docs/roadmap/roadmap.yaml")
        self.assertTrue(tracker["source_fingerprint"].startswith("sha256:"))
        counts = sum(len(rows) for rows in tracker["lanes"].values())
        self.assertEqual(counts, sum(tracker["counts"].values()))

    def subtask_plan(self):
        data = copy.deepcopy(self.data)
        for step in data["steps"]:
            step.pop("subtasks", None)
        parent = data["steps"][0]
        identifier = parent["id"] + ".test"
        parent["subtasks"] = [{"id": identifier, "title": "Publish the qualified files", "status": "offline_verified",
            "completion_status": "published", "depends_on": [], "acceptance": "Exact files are served to a permitted customer.",
            "procedure": ["Check exact bytes.", "Publish the approved delta.", "Read the files back."],
            "next_action": "Publish after the live preflight.", "evidence": "Local qualification passed; publication has not run.",
            "comment": "Local checks do not establish a live release."}]
        data["continuation"]["execution_order"] = [identifier]
        return data, parent, identifier

    def test_local_subtask_does_not_complete_a_publication_goal(self):
        data, parent, identifier = self.subtask_plan()
        tracker = tool.build(dump(data))
        self.assertEqual(tracker["record_type"], "development_tracker/v2")
        task = tracker["execution"][0]
        self.assertEqual(task["id"], identifier)
        self.assertFalse(task["complete"])
        self.assertEqual(task["owner_step"], parent["id"])
        self.assertIn("Publish after the live preflight.", tool.render(tracker))
        parent["subtasks"][0]["status"] = "published"
        self.assertTrue(tool.build(dump(data))["execution"][0]["complete"])

    def test_subtask_evidence_unknown_dependency_and_cycle_are_refused(self):
        for change in ("evidence", "dependency", "cycle", "duplicate", "status", "order"):
            data, parent, identifier = self.subtask_plan()
            row = parent["subtasks"][0]
            if change == "evidence": row["evidence"] = ""
            elif change == "dependency": row["depends_on"] = ["missing"]
            elif change == "cycle": row["depends_on"] = [identifier]
            elif change == "duplicate": parent["subtasks"].append(copy.deepcopy(row))
            elif change == "status": row["status"] = "mostly_done"
            elif change == "order": data["continuation"]["execution_order"] = ["missing"]
            with self.subTest(change=change), self.assertRaises(tool.TrackerError):
                tool.build(dump(data))

    def test_dependency_waits_for_its_declared_completion_scope(self):
        data, parent, identifier = self.subtask_plan()
        second = copy.deepcopy(parent["subtasks"][0])
        second.update(id=parent["id"]+".next", title="Measure the served release", status="ready", depends_on=[identifier],
                      evidence="", completion_status="live_qualified")
        parent["subtasks"].append(second)
        data["continuation"]["execution_order"].append(second["id"])
        tracker = tool.build(dump(data))
        self.assertEqual(tracker["execution"][1]["waiting_on"], [identifier])
        parent["subtasks"][0]["status"] = "published"
        self.assertEqual(tool.build(dump(data))["execution"][1]["waiting_on"], [])

    def test_publication_does_not_stand_in_for_live_qualification(self):
        data, parent, _identifier = self.subtask_plan()
        parent["subtasks"][0].update(status="published", completion_status="live_qualified")
        self.assertFalse(tool.build(dump(data))["execution"][0]["complete"])

    def test_subtask_sections_have_single_blank_separators(self):
        data, _parent, _identifier = self.subtask_plan()
        self.assertNotIn("\n\n\n", tool.render(tool.build(dump(data))))

    def test_completed_subtask_with_unfinished_dependency_is_refused(self):
        data, parent, identifier = self.subtask_plan()
        other = copy.deepcopy(parent["subtasks"][0])
        other.update(id=parent["id"]+".other", status="published", depends_on=[identifier])
        parent["subtasks"].append(other)
        data["continuation"]["execution_order"].append(other["id"])
        with self.assertRaises(tool.TrackerError):
            tool.build(dump(data))


if __name__ == "__main__":
    unittest.main()
