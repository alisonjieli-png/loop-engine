import unittest
import json
import subprocess
import sys
import os

# Add current directory to sys.path to allow importing the tool if needed,
# but we will primarily use subprocess to test the CLI behavior.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestAssembleTool(unittest.TestCase):
    def run_tool(self, input_dict):
        input_str = json.dumps(input_dict)
        process = subprocess.Popen(
            [sys.executable, 'tools/assemble_bounded_instruction_sections.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=input_str)
        return json.loads(stdout)

    def test_success_path(self):
        # Test the example provided in the prompt
        input_data = {
            "budget": 100,
            "sections": [
                {"id": "s1", "text": "One", "cost": 10, "mandatory": True, "priority": 1, "predecessors": []},
                {"id": "s2", "text": "Two", "cost": 20, "mandatory": False, "priority": 10, "predecessors": ["s1"]}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_units"], 30)
        self.assertEqual(len(result["selected"]), 2)

    def test_budget_refusal(self):
        input_data = {
            "budget": 5,
            "sections": [
                {"id": "s1", "text": "Too expensive", "cost": 10, "mandatory": True, "priority": 1, "predecessors": []}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_BUDGET_EXCEEDED")

    def test_cycle_refusal(self):
        input_data = {
            "budget": 100,
            "sections": [
                {"id": "a", "text": "A", "cost": 1, "mandatory": False, "priority": 1, "predecessors": ["b"]},
                {"id": "b", "text": "B", "cost": 1, "mandatory": False, "priority": 1, "predecessors": ["a"]}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_CYCLIC_DEPENDENCY")

    def test_type_mismatch(self):
        input_data = {
            "budget": 100,
            "sections": [
                {"id": "s1", "text": "A", "cost": "10", "mandatory": False, "priority": 1, "predecessors": []}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_TYPE_MISMATCH")

    def test_duplicate_id(self):
        input_data = {
            "budget": 100,
            "sections": [
                {"id": "a", "text": "A", "cost": 1, "mandatory": False, "priority": 1, "predecessors": []},
                {"id": "a", "text": "B", "cost": 1, "mandatory": False, "priority": 1, "predecessors": []}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ERR_DUPLICATE_ID")

if __name__ == "__main__":
    unittest.main()
