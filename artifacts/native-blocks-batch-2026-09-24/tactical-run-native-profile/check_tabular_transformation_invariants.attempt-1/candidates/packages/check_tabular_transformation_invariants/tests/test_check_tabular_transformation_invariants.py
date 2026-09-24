import unittest
import json
import subprocess
import sys
import os

# Add current dir to sys.path to allow importing the tool if needed, 
# though we will primarily use subprocess to simulate the real environment.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestTabularInvariants(unittest.TestCase):
    def run_tool(self, input_data):
        cmd = [sys.executable, "tools/check_tabular_transformation_invariants.py"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(input=json.dumps(input_data))
        return json.loads(stdout)

    def test_success_case(self):
        payload = {
            "before": [{"id": "row1", "score": 10, "tag": "A"}],
            "after": [{"id": "row1", "score": 10, "tag": "A"}],
            "contract": {
                "id_field": "id",
                "preserved_fields": ["tag"],
                "integer_total_fields": ["score"]
            }
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "success")

    def test_id_mismatch(self):
        payload = {
            "before": [{"id": "row1"}],
            "after": [{"id": "row2"}],
            "contract": {"id_field": "id"}
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "ID_SET_MISMATCH")

    def test_type_strict_equality(self):
        # true should not equal 1
        payload = {
            "before": [{"id": "r1", "p": True}],
            "after": [{"id": "r1", "p": 1}],
            "contract": {
                "id_field": "id",
                "preserved_fields": ["p"]
            }
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["violations"][0]["type"], "PRESERVED_FIELD_CHANGED")

    def test_integer_sum_mismatch(self):
        payload = {
            "before": [{"id": "1", "v": 10}, {"id": "2", "v": 20}],
            "after": [{"id": "1", "v": 10}, {"id": "2", "v": 21}],
            "contract": {
                "id_field": "id",
                "integer_total_fields": ["v"]
            }
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "TOTAL_SUM_MISMATCH")

    def test_boolean_in_integer_field(self):
        payload = {
            "before": [{"id": "1", "v": True}],
            "after": [{"id": "1", "v": True}],
            "contract": {
                "id_field": "id",
                "integer_total_fields": ["v"]
            }
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "NON_INTEGER_VALUE")

    def test_duplicate_keys_refusal(self):
        # We simulate duplicate keys by passing a raw string to the tool
        # because json.dumps won't produce them.
        cmd = [sys.executable, "tools/check_tabular_transformation_invariants.py"]
        raw_input = '{"before": [{"id": "1", "a": 1, "a": 2}], "after": [], "contract": {"id_field": "id"}}'
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, _ = proc.communicate(input=raw_input)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "DUPLICATE_KEY")

if __name__ == "__main__":
    unittest.main()
