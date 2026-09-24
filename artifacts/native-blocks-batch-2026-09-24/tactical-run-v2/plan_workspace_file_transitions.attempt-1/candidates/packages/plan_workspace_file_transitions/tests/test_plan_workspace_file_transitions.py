import unittest
import json
import io
import sys
from tools.plan_workspace_file_transitions import solve

class TestPlanWorkspace(unittest.TestCase):
    def run_tool(self, input_dict):
        input_str = json.dumps(input_dict)
        sys.stdin = io.StringIO(input_str)
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        solve()
        
        output = sys.stdout.getvalue().strip()
        sys.stdout = old_stdout
        sys.stdin = sys.stdin # reset is handled by StringIO in real test but here we just mock
        return json.loads(output)

    def test_acceptance_cases(self):
        # Using the logic from fixtures/acceptance.json
        cases = [
            {"base": {"f": "A"}, "current": {"f": "B"}, "desired": {"f": "C"}, "exp": "conflict"},
            {"base": {"f": "A"}, "current": {"f": "A"}, "desired": {"f": "C"}, "exp": "update"},
            {"base": {"f": None}, "current": {"f": "B"}, "desired": {"f": "C"}, "exp": "conflict"},
            {"base": {"f": "A"}, "current": {"f": "B"}, "desired": {"f": "B"}, "exp": "noop"},
            {"base": {"f": "A"}, "current": {"f": "A"}, "desired": {"f": "A"}, "exp": "noop"},
            {"base": {"f": "A"}, "current": {"f": "A"}, "desired": {"f": None}, "exp": "delete"},
            {"base": {"f": None}, "current": {"f": None}, "desired": {"f": "A"}, "exp": "create"},
        ]
        
        for case in cases:
            res = self.run_tool(case["input"])
            self.assertIn("success", res)
            action = res["success"][0]["action"]
            self.assertEqual(action, case["exp"], f"Failed case: {case['name'] if 'name' in case else case['input']}")

    def test_unsafe_paths(self):
        # Test directory/file collision (case fold)
        case = {
            "base": {"file.txt": "A"},
            "current": {"file.txt": "A", "FILE.txt": "A"},
            "desired": {"file.txt": "A"}
        }
        res = self.run_tool(case)
        self.assertEqual(res["refused"]["code"], "CASE_COLLISION")

        # Test unsafe path
        case_unsafe = {
            "base": {"../secret.txt": "A"},
            "current": {"../secret.txt": "A"},
            "desired": {"../secret.txt": "A"}
        }
        res = self.run_tool(case_unsafe)
        self.assertEqual(res["refused"]["code"], "UNSAFE_PATH")

    def test_type_mismatch(self):
        # Boolean where string expected
        case = {
            "base": {"f": True},
            "current": {"f": True},
            "desired": {"f": "A"}
        }
        res = self.run_tool(case)
        self.assertEqual(res["refused"]["code"], "TYPE_MISMATCH")

    def test_missing_keys(self):
        case = {"base": {}}
        res = self.run_tool(case)
        self.assertEqual(res["refused"]["code"], "MISSING_KEYS")

if __name__ == "__main__":
    unittest.main()
