import unittest
import json
import subprocess
import sys
import os

# Add current dir to sys.path to allow importing tools if needed, 
# but we will use subprocess to test the CLI behavior as requested.
class TestValidateHandoff(unittest.TestCase):
    def setUp(self):
        self.tool_path = os.path.join(os.path.dirname(__file__), "..", "tools", "validate_focused_attempt_handoff.py")

    def run_tool(self, input_data):
        input_str = json.dumps(input_data)
        process = subprocess.Popen(
            [sys.executable, self.tool_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=input_str)
        return stdout, stderr

    def test_valid_handoff(self):
        valid_input = {
            "task_id": "t1",
            "attempt_id": "a1",
            "objective": "obj",
            "first_actions": ["act1"],
            "immutable_inputs": {},
            "required_output_paths": ["p1"],
            "authority_reference": "auth",
            "events": [{"sequence_number": 0, "state": "running"}]
        }
        stdout, stderr = self.run_tool(valid_input)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["briefing"]["first_action"], "act1")

    def test_sequence_gap(self):
        gap_input = {
            "task_id": "t1", "attempt_id": "a1", "objective": "obj", "first_actions": ["act1"],
            "immutable_inputs": {}, "required_output_paths": ["p1"], "authority_reference": "auth",
            "events": [
                {"sequence_number": 0, "state": "running"},
                {"sequence_number": 2, "state": "running"}
            ]
        }
        stdout, stderr = self.run_tool(gap_input)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_SEQUENCE_GAP")

    def test_duplicate_sequence(self):
        dupe_input = {
            "task_id": "t1", "attempt_id": "a1", "objective": "obj", "first_actions": ["act1"],
            "immutable_inputs": {}, "required_output_paths": ["p1"], "authority_reference": "auth",
            "events": [
                {"sequence_number": 0, "state": "running"},
                {"sequence_number": 0, "state": "running"}
            ]
        }
        stdout, stderr = self.run_tool(dupe_input)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_SEQUENCE_DUPE")

    def test_boolean_type_mismatch(self):
        # JSON standard allows true/false, but we reject them for sequence_number
        bool_input = {
            "task_id": "t1", "attempt_id": "a1", "objective": "obj", "first_actions": ["act1"],
            "immutable_inputs": {}, "required_output_paths": ["p1"], "authority_reference": "auth",
            "events": [{"sequence_number": True, "state": "running"}]
        }
        stdout, stderr = self.run_tool(bool_input)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_TYPE_MISMATCH")

    def test_candidate_self_accept(self):
        self_accept = {
            "task_id": "t1", "attempt_id": "a1", "objective": "obj", "first_actions": ["act1"],
            "immutable_inputs": {}, "required_output_paths": ["p1"], "authority_reference": "auth",
            "events": [
                {"sequence_number": 0, "state": "candidate", "validator_id": "v1"},
                {"sequence_number": 1, "state": "accepted", "validator_id": "v1", "evidence_digest": "d1"}
            ]
        }
        stdout, stderr = self.run_tool(self_accept)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_INVALID_STATE")
        self.assertEqual(result["reason"], "candidate_self_accept")

if __name__ == "__main__":
    unittest.main()
