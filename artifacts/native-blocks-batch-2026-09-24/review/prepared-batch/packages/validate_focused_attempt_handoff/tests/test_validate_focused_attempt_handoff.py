import unittest
import json
import sys
import io
from tools.validate_focused_attempt_handoff import main

class TestHandoffValidation(unittest.TestCase):
    def run_tool(self, input_dict):
        input_str = json.dumps(input_dict)
        sys.stdin = io.StringIO(input_str)
        
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        main()
        
        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
        
        return json.loads(captured_output.getvalue())

    def test_valid_handoff(self):
        payload = {
            "task_id": "task-1",
            "attempt_id": 5,
            "objective": "test",
            "first_actions": ["init"],
            "immutable_inputs": {"key": "val"},
            "required_output_paths": ["res.json"],
            "authority_reference": "auth-1",
            "event_records": [
                {"sequence": 0, "state": "running"},
                {"sequence": 1, "state": "accepted", "validator_identity": "auth-2", "evidence_digest": "hash"}
            ]
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "success")
        self.assertIn("First Action: init", result["briefing"])
        self.assertEqual(result["validated_state"]["last_sequence"], 1)

    def test_sequence_gap(self):
        payload = {
            "task_id": "task-1",
            "attempt_id": 5,
            "objective": "test",
            "first_actions": ["init"],
            "immutable_inputs": {},
            "required_output_paths": [],
            "authority_reference": "auth-1",
            "event_records": [
                {"sequence": 0, "state": "running"},
                {"sequence": 2, "state": "running"}
            ]
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error"], "SEQUENCE_GAP:2")

    def test_duplicate_sequence(self):
        payload = {
            "task_id": "task-1",
            "attempt_id": 5,
            "objective": "test",
            "first_actions": ["init"],
            "immutable_inputs": {},
            "required_output_paths": [],
            "authority_reference": "auth-1",
            "event_records": [
                {"sequence": 0, "state": "running"},
                {"sequence": 0, "state": "running"}
            ]
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error"], "DUPLICATE_SEQUENCE:0")

    def test_self_acceptance(self):
        payload = {
            "task_id": "task-1",
            "attempt_id": 5,
            "objective": "test",
            "first_actions": ["init"],
            "immutable_inputs": {},
            "required_output_paths": [],
            "authority_reference": "auth-1",
            "event_records": [
                {"sequence": 0, "state": "accepted", "validator_identity": "auth-1", "evidence_digest": "hash"}
            ]
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error"], "SELF_ACCEPTANCE_PROHIBITED")

    def test_boolean_instead_of_int(self):
        # attempt_id is expected to be int, but we pass True
        payload = {
            "task_id": "task-1",
            "attempt_id": True,
            "objective": "test",
            "first_actions": ["init"],
            "immutable_inputs": {},
            "required_output_paths": [],
            "authority_reference": "auth-1",
            "event_records": [{"sequence": 0, "state": "running"}]
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error"], "TYPE_MISMATCH:attempt_id_expected_int_not_bool")

    def test_duplicate_keys_in_json(self):
        # We simulate the raw string to test the custom parser
        raw_input = '{"task_id": "T1", "task_id": "T2", "attempt_id": 1, "objective": "o", "first_actions": [], "immutable_inputs": {}, "required_output_paths": [], "authority_reference": "A", "event_records": []}'
        sys.stdin = io.StringIO(raw_input)
        captured_output = io.StringIO()
        sys.stdout = captured_output
        main()
        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
        result = json.loads(captured_output.getvalue())
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error"], "DUPLICATE_KEY:task_id")

if __name__ == "__main__":
    unittest.main()
