"""Deterministic tests for the standalone qualification lab."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runner import audit_run, load_catalog, render_prompt, select_case


class QualificationLabTests(unittest.TestCase):

    def test_each_case_has_one_complete_bounded_prompt(self):
        catalog = load_catalog()
        self.assertGreaterEqual(len(catalog["cases"]), 6)
        for case in catalog["cases"]:
            prompt = render_prompt(case)
            self.assertIn(case["case_id"], prompt)
            self.assertIn("Return JSON only", prompt)
            self.assertNotIn("final task solution", prompt.lower())

    def test_route_breakout_case_covers_terminal_laws(self):
        case = select_case("route-breakout")
        self.assertIn("bounded_no_progress_breakout", case["invariants"])
        self.assertIn("repair_is_executable_or_rejected", case["invariants"])

    def test_black_box_audit_detects_the_observed_stuck_shape(self):
        value = {
            "run_id": "example", "status": "NOT_YET_PROVEN",
            "solved": False, "passes": 24, "model_calls": 100,
            "final_route": "repair",
            "action_decisions": [
                {"action_kind": "RESEARCH_SOURCE"} for _item in range(8)],
            "project_attempts": [{"deterministic_checks_passed": True}],
            "verification": [{"remaining_gaps": [
                "The same material gap remains."]} for _item in range(4)],
        }
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "result.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            report = audit_run(path)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("POST_PROJECT_RESEARCH_EXCEEDED", codes)
        self.assertIn("VERIFIED_ARTIFACT_STATE_NOT_TERMINAL", codes)
        self.assertIn("REPEATED_VERIFICATION_GAP", codes)


if __name__ == "__main__":
    unittest.main()

