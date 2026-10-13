"""Negative controls for roadmap selection, coverage, and artifact freshness."""
from __future__ import annotations

import copy
from contextlib import redirect_stdout
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_continuation_status as tool
import build_development_tracker as tracker_tool


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load(tool.ROADMAP.read_text("utf-8"))

    def step(self, identity):
        return next(row for row in self.data["steps"] if row["id"] == identity)

    def subtask_plan(self):
        self.data["continuation"].pop("working_schedule", None)
        for step in self.data["steps"]:
            step.pop("subtasks", None)
        tasks = []
        for parent_id, suffix in (("S-6.4", "first"), ("S-6.5", "second")):
            parent = self.step(parent_id)
            parent.update(status="ready", depends_on=[], authority_requirements=[])
            row = {"id": parent_id + "." + suffix, "title": "Check " + suffix, "status": "ready",
                   "completion_status": "offline_verified", "depends_on": [], "acceptance": "A recorded check passes.",
                   "procedure": ["Run the scoped check."], "next_action": "Run the scoped check.",
                   "evidence": "", "comment": "A planning record, not a running worker."}
            parent["subtasks"] = [row]
            tasks.append(row)
        # The ordered subtasks deliberately disagree with eligible parent order.
        self.data["continuation"]["execution_order"] = [row["id"] for row in reversed(tasks)]
        return tasks

    def next_output(self):
        with tempfile.TemporaryDirectory() as directory:
            roadmap = Path(directory) / "roadmap.yaml"
            roadmap.write_text(yaml.safe_dump(self.data, sort_keys=False), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(tool.main(["--roadmap", str(roadmap), "--next"]), 0)
            return json.loads(output.getvalue())

    def test_views_and_next_choose_the_same_subtask_despite_opposing_parent_order(self):
        first, second = self.subtask_plan()
        parents = [row["id"] for row in tool.eligible_steps(self.data)]
        self.assertLess(parents.index("S-6.4"), parents.index("S-6.5"))
        expected = "Next eligible subtask: " + second["id"] + ": " + second["title"]
        tracker = tracker_tool.build(yaml.safe_dump(self.data).encode())
        self.assertTrue(expected in tracker_tool.render(tracker), "tracker ignored the declared subtask order")
        self.assertTrue(expected in tool.render(self.data, "fixture"), "continuation selected a parent instead of the ordered subtask")
        self.assertEqual(self.next_output(), {"subtasks": [second["id"]]})
        self.assertNotEqual(self.next_output(), {"subtasks": [first["id"]]})

    def test_blocked_or_retired_subtasks_do_not_fall_back_to_ready_parents(self):
        first, second = self.subtask_plan()
        for status in ("blocked", "superseded"):
            second["status"] = status
            self.assertEqual(self.next_output(), {"subtasks": [first["id"]]})
            first["status"] = status
            self.assertEqual(self.next_output(), {"subtasks": []})
            self.assertTrue("No eligible subtask is recorded." in tool.render(self.data, "fixture"))
            first["status"] = "ready"

    def test_parent_selection_is_used_only_without_any_subtasks(self):
        self.subtask_plan()
        for step in self.data["steps"]:
            step.pop("subtasks", None)
        self.data["continuation"]["execution_order"] = []
        expected = {track: [row["id"] for row in tool.eligible_steps(self.data, track=track)]
                    for track in ("launch", "improvement")}
        self.assertEqual(self.next_output(), expected)
        self.assertIn("- Launch: S-6.4:", tool.render(self.data, "fixture"))

    def test_subtask_next_waits_for_exact_completion_and_never_reopens_completed_work(self):
        first, second = self.subtask_plan()
        first.update(status="offline_verified", completion_status="published", evidence="Local checks passed.")
        second["depends_on"] = [first["id"]]
        self.assertEqual(self.next_output(), {"subtasks": [first["id"]]})
        first["status"] = "published"
        self.assertEqual(self.next_output(), {"subtasks": [second["id"]]})
        second.update(status="offline_verified", evidence="Scoped result verified.")
        self.assertEqual(self.next_output(), {"subtasks": []})

    def test_invalid_subtask_graph_refuses_instead_of_selecting_a_parent(self):
        _first, second = self.subtask_plan()
        second["depends_on"] = ["S-missing.task"]
        with self.assertRaises(tool.PlanError):
            tool.next_work(self.data)

    def test_recorded_work_is_not_labelled_as_live_worker_telemetry(self):
        rendered = tool.render(self.data, "fixture")
        self.assertTrue("## Recorded work in progress" in rendered)
        self.assertTrue("not live worker telemetry" in rendered)

    def test_real_plan_preserves_every_initiative_and_has_valid_dependencies(self):
        rows = tool.validate(self.data)
        self.assertIn("S-0.5", rows)
        self.assertIn("S-6.24", rows)

    def test_owner_actions_are_complete_separate_preparation_records(self):
        actions = self.data["continuation"]["owner_actions"]
        self.assertGreaterEqual(len(actions), 15)
        self.assertTrue(all(row["instructions"] and row["return_fields"] and row["safety"] for row in actions))
        self.assertFalse(any("authorized" in row for row in actions))

    def test_owner_actions_reject_unknown_fields_references_and_cycles(self):
        for field, value in (("extra_authority", True), ("steps", ["unknown"]),
                             ("depends_on", ["OWNER-01"]), ("phase", "verified")):
            data = copy.deepcopy(self.data)
            data["continuation"]["owner_actions"][0][field] = value
            with self.assertRaises(tool.PlanError):
                tool.validate(data)

    def test_unknown_dependency_and_cycle_are_refused(self):
        for dependencies in (["missing"], ["S-6.1"]):
            data = copy.deepcopy(self.data)
            next(row for row in data["steps"] if row["id"] == "S-6.17")["depends_on"] = dependencies
            with self.assertRaises(tool.PlanError):
                tool.validate(data)

    def test_omitting_a_legacy_initiative_is_refused(self):
        for stream in self.data["continuation"]["workstreams"]:
            stream["legacy_steps"] = [key for key in stream["legacy_steps"] if key != "S-0.5"]
        with self.assertRaisesRegex(tool.PlanError, "unassigned"):
            tool.validate(self.data)

    def test_failed_dependency_is_not_selected_despite_ready_status(self):
        self.step("S-6.17")["status"] = "building"
        self.step("S-6.4")["status"] = "ready"
        self.assertNotIn("S-6.4", [row["id"] for row in tool.eligible_steps(self.data)])
        self.step("S-6.17").update(status="offline_verified", evidence="observed planning checks")
        self.assertEqual(tool.eligible_steps(self.data)[0]["id"], "S-6.4")

    def test_missing_dependency_evidence_prevents_selection(self):
        self.step("S-6.17").update(status="published", evidence="")
        self.assertNotIn("S-6.4", [row["id"] for row in tool.eligible_steps(self.data)])

    def test_pending_authority_is_not_treated_as_elapsed_approval(self):
        for row in self.data["steps"]:
            row.update(status="offline_verified", evidence="a fixture verification record")
        self.step("S-6.15")["status"] = "ready"
        self.assertNotIn("S-6.15", [row["id"] for row in tool.eligible_steps(self.data)])
        decision = next(row for row in self.data["continuation"]["decisions"] if row["id"] == "hosting_authority")
        decision.update(state="authorized", evidence="exact declared deployment authority")
        self.assertIn("S-6.15", [row["id"] for row in tool.eligible_steps(self.data)])

    def test_transitive_dependency_failure_is_not_hidden_by_a_direct_pass(self):
        self.step("S-6.17").update(status="building")
        self.step("S-6.4").update(status="offline_verified", evidence="a component check")
        self.step("S-6.5").update(status="ready")
        self.assertNotIn("S-6.5", [row["id"] for row in tool.eligible_steps(self.data)])

    def test_published_steps_alone_do_not_pass_a_launch_gate(self):
        gate = self.data["continuation"]["launch_gates"][0]
        for identity in gate["steps"]:
            self.step(identity).update(status="published", evidence="a component check")
        self.assertIn("Not verified", tool.gate_status(self.data, gate))

    def test_stale_generated_view_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "view.md"
            output.write_text("stale", "utf-8")
            self.assertEqual(tool.main(["--output", str(output), "--check"]), 1)
            self.assertEqual(tool.main(["--output", str(output)]), 0)
            self.assertEqual(tool.main(["--output", str(output), "--check"]), 0)

    def test_repository_view_is_current(self):
        self.assertEqual(tool.main(["--check"]), 0)

    def test_active_work_is_visible_without_becoming_an_eligible_dependency(self):
        self.step("S-6.4").update(status="building", evidence="Local store proof only",
                                next_local_work="Verify restore before hosted qualification")
        rendered = tool.render(self.data, "fixture")
        active = rendered.split("## Recorded work in progress", 1)[1].split("## Release gates", 1)[0]
        self.assertIn("| S-6.4 | Local store proof only | Verify restore before hosted qualification |", active)
        self.assertNotIn("S-6.4", [row["id"] for row in tool.eligible_steps(self.data)])
        self.assertIn("Not verified", rendered)

    def test_completed_work_is_not_presented_as_active(self):
        self.step("S-6.4").update(status="offline_verified", evidence="A local fixture")
        active = tool.render(self.data, "fixture").split("## Recorded work in progress", 1)[1].split("## Release gates", 1)[0]
        self.assertNotIn("| S-6.4 |", active)

    def test_delivery_packages_expand_existing_work_without_accepting_claims(self):
        plan = self.data["continuation"]
        self.assertGreaterEqual(len(plan["delivery_batches"]), 16)
        self.assertGreaterEqual(sum(len(row["actions"]) for row in plan["delivery_batches"]), 128)
        self.assertGreaterEqual(sum(len(row["verification_cases"]) for row in plan["delivery_batches"]), 80)
        rendered = tool.render(self.data, "fixture")
        self.assertIn("## Delivery packages", rendered)
        self.assertIn("## Launch benefit drafts", rendered)
        # An emptied gate list would satisfy the statement below while proving
        # that no gate had been read, so the population is named first.
        self.assertGreaterEqual(len(plan["launch_gates"]), 1)
        self.assertTrue(all("Not verified" in tool.gate_status(self.data, gate) for gate in plan["launch_gates"]))

    def test_delivery_package_refuses_unknown_owners_cycles_and_missing_controls(self):
        for field, value in (("steps", ["missing"]), ("depends_on", ["D-01"]),
                             ("depends_on", ["unknown"]), ("adversarial", ""),
                             ("authority_note", ""), ("actions", []), ("state", "done")):
            data = copy.deepcopy(self.data)
            data["continuation"]["delivery_batches"][0][field] = value
            with self.assertRaises(tool.PlanError):
                tool.validate(data)

    def test_delivery_cases_require_real_owners_discriminators_and_explicit_proof_level(self):
        for field, value in (("owning_paths", []), ("owning_paths", ["../outside"]),
                             ("owning_paths", ["missing/source.py"]), ("rollback", ""), ("verification_cases", [])):
            data=copy.deepcopy(self.data);data["continuation"]["delivery_batches"][0][field]=value
            with self.assertRaises(tool.PlanError):tool.validate(data)
        for field, value in (("negative_control", ""), ("proof_level", "passed"), ("status", "complete"), ("id", "unbound")):
            data=copy.deepcopy(self.data);data["continuation"]["delivery_batches"][0]["verification_cases"][0][field]=value
            with self.assertRaises(tool.PlanError):tool.validate(data)

    def test_delivery_cases_cannot_duplicate_an_identifier(self):
        row=self.data["continuation"]["delivery_batches"][0]
        row["verification_cases"].append(copy.deepcopy(row["verification_cases"][0]))
        with self.assertRaises(tool.PlanError):tool.validate(self.data)

    def test_launch_claim_cannot_be_promoted_by_changing_a_status_word(self):
        for field, value in (("state", "verified"), ("evidence_needed", ""), ("steps", ["unknown"]),
                             ("savings_percent", 50)):
            data = copy.deepcopy(self.data)
            data["continuation"]["launch_benefits"][0][field] = value
            with self.assertRaises(tool.PlanError):
                tool.validate(data)


if __name__ == "__main__":
    unittest.main()
