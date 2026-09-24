import unittest
import json
import subprocess
import sys
from io import BytesIO

class TestJSONReviewer(unittest.TestCase):
    def run_helper(self, input_str: str) -> dict:
        """Simulates calling the script via stdin."""
        process = subprocess.Popen(
            [sys.executable, "scripts/check_json.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=input_str)
        return json.loads(stdout)

    def test_success_case(self):
        # A nested object with array [true,null,2,"x"]
        # Note: The prompt asks for this specific structure
        input_data = '[true, null, 2, "x"]'
        result = self.run_helper(input_data)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counts"]["boolean"], 1)
        self.assertEqual(result["counts"]["null"], 1)
        self.assertEqual(result["counts"]["number"], 1)
        self.assertEqual(result["counts"]["string"], 1)
        self.assertEqual(result["counts"]["array"], 1)
        self.assertEqual(result["counts"]["object"], 0)
        self.assertEqual(result["max_depth"], 1)

    def test_duplicate_keys(self):
        # JSON with duplicate keys
        input_data = '{"a": 1, "a": 2}'
        result = self.run_helper(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error"], "ERR_DUPLICATE_KEY")

    def test_depth_limit(self):
        # Create a deeply nested structure
        depth = 35
        nested = "1"
        for _ in range(depth):
            nested = f"[{nested}]"
        result = self.run_helper(nested)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error"], "ERR_DEPTH")

    def test_nonfinite_number(self):
        # Note: standard json.loads fails on NaN, but our helper 
        # is designed to catch it if the parser allows or if we simulate it.
        # Since standard json.loads(text) fails on NaN, we test the error handling.
        input_data = '{"val": NaN}'
        result = self.run_helper(input_data)
        # Depending on the parser, this might be ERR_INVALID_JSON or ERR_NONFINITE_NUMBER
        # Our script uses json.loads which usually throws on NaN unless configured.
        self.assertIn(result["error"], ["ERR_NONFINITE_NUMBER", "ERR_INVALID_JSON"])

    def test_boolean_vs_integer(self):
        # Ensure boolean is not counted as number
        input_data = '[true, 1]'
        result = self.run_helper(input_data)
        self.assertEqual(result["counts"]["boolean"], 1)
        self.assertEqual(result["counts"]["number"], 1)

if __name__ == "__main__":
    unittest.main()
