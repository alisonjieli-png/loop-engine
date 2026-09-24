import unittest
import json
import io
import sys
from tools.assemble_bounded_instruction_sections import solve

class TestAssembleSections(unittest.TestCase):
    def run_tool(self, input_data):
        # If input_data is a dict, convert to JSON string
        if isinstance(input_data, dict):
            input_str = json.dumps(input_data)
        else:
            input_str = input_data
            
        # Mock stdin
        sys.stdin = io.StringIO(input_str)
        
        # Capture stdout
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        solve()
        
        output_str = sys.stdout.getvalue().strip()
        sys.stdout = old_stdout
        return json.loads(output_str)

    def test_success_case(self):
        input_data = {
            "budget": 20,
            "sections": [
                {"id": "s1", "text": "A", "cost": 5, "priority": 10, "mandatory": True},
                {"id": "s2", "text": "B", "cost": 5, "priority": 5, "mandatory": False, "predecessors": ["s1"]},
                {"id": "s3", "text": "C", "cost": 15, "priority": 100, "mandatory": False}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["total_units"], 10)
        self.assertIn("s1", [x["id"] for x in result["selected_sections"]])
        self.assertIn("s2", [x["id"] for x in result["selected_sections"]])
        self.assertNotIn("s3", [x["id"] for x in result["selected_sections"]])

    def test_mandatory_over_budget(self):
        input_data = {
            "budget": 5,
            "sections": [
                {"id": "s1", "text": "A", "cost": 6, "priority": 1, "mandatory": True}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["code"], "ERR_MANDATORY_OVER_BUDGET")

    def test_cyclic_constraint(self):
        input_data = {
            "budget": 100,
            "sections": [
                {"id": "s1", "text": "A", "cost": 1, "priority": 1, "predecessors": ["s2"]},
                {"id": "s2", "text": "B", "cost": 1, "priority": 1, "predecessors": ["s1"]}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["code"], "ERR_CYCLIC_CONSTRAINT")

    def test_type_mismatch_boolean(self):
        # cost is boolean instead of int
        input_data = {
            "budget": 10,
            "sections": [
                {"id": "s1", "text": "A", "cost": True, "priority": 1}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["code"], "ERR_TYPE_MISMATCH")

    def test_duplicate_key(self):
        # Manual string to ensure duplicate key is passed to parser
        input_str = '{"budget": 10, "budget": 20, "sections": []}'
        result = self.run_tool(input_str)
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["code"], "ERR_DUPLICATE_KEY")

    def test_unicode_byte_offsets(self):
        # "🚀" is 4 bytes in UTF-8
        input_data = {
            "budget": 10,
            "sections": [
                {"id": "u1", "text": "🚀", "cost": 1, "priority": 1},
                {"id": "u2", "text": "A", "cost": 1, "priority": 1}
            ]
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "SUCCESS")
        # u1 is [0, 4], u2 is [4, 5]
        self.assertEqual(result["selected_sections"][0]["byte_range"], [0, 4])
        self.assertEqual(result["selected_sections"][1]["byte_range"], [4, 5])

if __name__ == "__main__":
    unittest.main()
