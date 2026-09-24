import unittest
import json
import subprocess
import sys
import os

class TestDependencyResolver(unittest.TestCase):
    def setUp(self):
        self.tool_path = os.path.join(os.path.dirname(__file__), "..", "tools", "resolve_exact_package_dependency_closure.py")

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
        return json.loads(stdout)

    def test_success_path(self):
        input_data = {
            "requested_ids": ["pkg-a"],
            "records": {
                "pkg-a": {"revision": "1", "digest": "h1", "size": 10, "dependencies": ["pkg-b"], "effects": ["e1"]},
                "pkg-b": {"revision": "1", "digest": "h2", "size": 20, "dependencies": [], "effects": ["e2"]}
            }
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["resolved_dependencies"], ["pkg-b", "pkg-a"])
        self.assertEqual(result["total_size_bytes"], 30)
        self.assertIn("e1", result["effects"])
        self.assertIn("e2", result["effects"])

    def test_missing_record(self):
        input_data = {
            "requested_ids": ["pkg-a"],
            "records": {
                "pkg-a": {"revision": "1", "digest": "h1", "size": 10, "dependencies": ["pkg-missing"]}
            }
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "MISSING_RECORD")

    def test_cycle(self):
        input_data = {
            "requested_ids": ["A"],
            "records": {
                "A": {"revision": "1", "digest": "h1", "size": 10, "dependencies": ["B"]},
                "B": {"revision": "1", "digest": "h2", "size": 10, "dependencies": ["A"]}
            }
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "CYCLE_DETECTED")

    def test_type_error_boolean(self):
        input_data = {
            "requested_ids": ["A"],
            "records": {
                "A": {"revision": "1", "digest": "h1", "size": True}
            }
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "TYPE_ERROR")

    def test_duplicate_key_refusal(self):
        # Since we can't easily pass a raw string with duplicate keys to a dict-based test,
        # we simulate the raw stdin behavior.
        raw_input = '{"requested_ids": ["A"], "records": {"A": {"rev": "1"}}, "requested_ids": ["B"]}'
        process = subprocess.Popen(
            [sys.executable, self.tool_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = process.communicate(input=raw_input)
        result = json.loads(stdout)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "DUPLICATE_KEY")

if __name__ == "__main__":
    unittest.main()
