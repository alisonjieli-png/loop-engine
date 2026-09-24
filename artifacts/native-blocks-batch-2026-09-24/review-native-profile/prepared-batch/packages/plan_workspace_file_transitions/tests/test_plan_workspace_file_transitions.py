import unittest
import json
import subprocess
import sys
import os

class TestPlanTransitions(unittest.TestCase):
    def setUp(self):
        self.script_path = os.path.join(os.path.dirname(__file__), "..", "tools", "plan_workspace_file_transitions.py")
        # Ensure the script is executable or we run via python
        self.cmd = [sys.executable, self.script_path]

    def run_tool(self, input_dict):
        input_str = json.dumps(input_dict)
        proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=input_str)
        return json.loads(stdout)

    def test_provided_examples(self):
        # Test the logic from examples/input.json
        # Note: The example output in the prompt has a conflict for src/main.py 
        # because current=A, desired=D, but base=A. Wait, if base=A, current=A, desired=D, 
        # that is an UPDATE, not a conflict. 
        # Let's re-read: "Permit updates/deletes only if current equals base; 
        # changed or foreign current bytes are conflicts."
        # In example: base=A, current=A, desired=D -> This is an UPDATE.
        # The example output provided in the prompt says "conflict" for src/main.py.
        # Let's check the prompt's example logic: "base=A,current=A,desired=C is update".
        # So the example output in the prompt might have a typo or my reading is off.
        # Let's follow the text rules: base=A, current=A, desired=D => update.
        
        input_data = {
            "base": {"src/main.py": "sha256-aaa", "README.md": "sha256-bbb"},
            "current": {"src/main.py": "sha256-aaa", "README.md": "sha256-ccc"},
            "desired": {"src/main.py": "sha256-ddd", "README.md": "sha256-ccc", "docs/api.md": "sha256-eee"}
        }
        result = self.run_tool(input_data)
        self.assertEqual(result["status"], "success")
        
        # Find src/main.py transition
        main_trans = next(t for t in result["transitions"] if t["path"] == "src/main.py")
        self.assertEqual(main_trans["op"], "update")
        self.assertEqual(main_trans["expected_digest"], "sha256-aaa")

    def test_acceptance_cases(self):
        # Case 1: base=A, current=B, desired=C -> conflict
        res1 = self.run_tool({"base": {"f": "A"}, "current": {"f": "B"}, "desired": {"f": "C"}})
        self.assertEqual(res1["transitions"][0]["op"], "conflict")
        
        # Case 2: base=A, current=A, desired=C -> update
        res2 = self.run_tool({"base": {"f": "A"}, "current": {"f": "A"}, "desired": {"f": "C"}})
        self.assertEqual(res2["transitions"][0]["op"], "update")
        
        # Case 3: base=null, current=B, desired=C -> conflict
        res3 = self.run_tool({"base": {}, "current": {"f": "B"}, "desired": {"f": "C"}})
        self.assertEqual(res3["transitions"][0]["op"], "conflict")
        
        # Case 4: base=A, current=B, desired=B -> noop
        res4 = self.run_tool({"base": {"f": "A"}, "current": {"f": "B"}, "desired": {"f": "B"}})
        self.assertEqual(res4["transitions"][0]["op"], "noop")

    def test_refusals(self):
        # Duplicate key
        dup_input = '{"base": {"a": "1", "a": "2"}, "current": {}, "desired": {}}'
        proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        stdout, _ = proc.communicate(input=dup_input)
        res = json.loads(stdout)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["error"]["code"], "DUPLICATE_KEY")

        # Unsafe path
        unsafe_input = {"base": {"../secret.txt": "A"}, "current": {}, "desired": {}}
        res = self.run_tool(unsafe_input)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["error"]["code"], "UNSAFE_PATH")

        # Type mismatch (boolean instead of string)
        type_input = {"base": {"f.txt": True}, "current": {}, "desired": {}}
        res = self.run_tool(type_input)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["error"]["code"], "TYPE_MISMATCH")

if __name__ == "__main__":
    unittest.main()
