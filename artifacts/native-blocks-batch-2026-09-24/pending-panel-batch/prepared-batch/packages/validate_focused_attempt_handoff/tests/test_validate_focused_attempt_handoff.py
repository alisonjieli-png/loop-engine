import unittest
import json
import subprocess
import sys
import os

# Add tools to path so we can import or run it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestValidateHandoff(unittest.TestCase):
    def setUp(self):
        self.tool_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools/validate_focused_attempt_handoff.py'))

    def run_tool(self, input_dict):
        proc = subprocess.Popen(
            [sys.executable, self.tool_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=json.dumps(input_dict))
        return json.loads(stdout)

    def test_valid_case(self):
        valid_input = {
            "task_id": "task-1",
            "attempt_id": 1,
            "objective": "test",
            "first_actions": ["action1"],
            "inputs": {"x": 1},
            "output_paths": ["out.txt"],
            "authority": "auth",
            "events": [{"sequence": 0, "state": "running"}]
        }
        result = self.run_tool(valid_input)
        self.assertEqual(result["status"], "success")
        self.assertIn("test", result["data"]["briefing"])

    def test_sequence_gap(self):
        gap_input = {
            "task_id": "task-1",
            "attempt_id": 1,
            "objective": "test",
            "first_actions": ["action1"],
            "inputs": {},
            "output_paths": [],
            "authority": "auth",
            "events": [
                {"sequence": 0, "state": "running"},
                {"sequence": 2, "state": "running"}
            ]
        }
        result = self.run_tool(gap_input)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "SEQUENCE_GAP")

    def test_duplicate_sequence(self):
        dup_input = {
            "task_id": "task-1",
            "attempt_id": 1,
            "objective": "test",
            "first_actions": ["action1"],
            "inputs": {},
            "output_paths": [],
            "authority": "auth",
            "events": [
                {"sequence": 0, "state": "running"},
                {"sequence": 0, "state": "running"}
            ]
        }
        result = self.run_tool(dup_input)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "DUPLICATE_SEQUENCE")

    def test_accepted_without_evidence(self):
        bad_accepted = {
            "task_id": "task-1",
            "attempt_id": 1,
            "objective": "test",
            "first_actions": ["action1"],
            "inputs": {},
            "output_paths": [],
            "authority": "auth",
            "events": [
                {"sequence": 0, "state": "accepted"}
            ]
        }
        result = self.run_tool(bad_accepted)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "INVALID_STATE")

    def test_boolean_type_rejection(self):
        # attempt_id should be int, not bool
        bool_input = {
            "task_id": "task-1",
            "attempt_id": True,
            "objective": "test",
            "first_actions": ["action1"],
            "inputs": {},
            "output_paths": [],
            "authority": "auth",
            "events": [{"sequence": 0, "state": "running"}]
        }
        result = self.run_tool(bool_input)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "TYPE_MISMATCH")

    def test_non_finite_number(self):
        inf_input = {
            "task_id": "task-1",
            "attempt_id": 1,
            "objective": "test",
            "first_actions": ["action1"],
            "inputs": {"val": float('inf')},
            "output_paths": [],
            "authority": "auth",
            "events": [{"sequence": 0, "state": "running"}]
        }
        result = self.run_tool(inf_input)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "NON_FINITE_NUMBER")

if __name__ == "__main__":
    unittest.main()
