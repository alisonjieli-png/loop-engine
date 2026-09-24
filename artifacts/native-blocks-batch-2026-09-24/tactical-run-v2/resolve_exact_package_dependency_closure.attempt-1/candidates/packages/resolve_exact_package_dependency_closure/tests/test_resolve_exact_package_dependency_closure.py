import unittest
import json
import sys
import io
from tools.resolve_exact_package_dependency_closure import resolve

class TestResolveDependency(unittest.TestCase):
    def test_success_path(self):
        available = {
            "base@1": {"digest": "h1", "size": 10, "effects": ["fs"], "dependencies": []},
            "mid@1": {"digest": "h2", "size": 20, "effects": ["net"], "dependencies": [{"id": "base", "rev": "1", "digest": "h1"}]},
            "top@1": {"digest": "h3", "size": 30, "effects": [], "dependencies": [{"id": "mid", "rev": "1", "digest": "h2"}]}
        }
        requested = [{"id": "top", "rev": "1", "digest": "h3"}]
        
        # We test the logic function directly
        result = resolve(available, requested)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["dependencies"]), 3)
        self.assertEqual(result["total_size_bytes"], 60)
        self.assertIn("fs", result["effects"])
        self.assertIn("net", result["effects"])
        # Check topological order: base -> mid -> top
        self.assertEqual(result["dependencies"][0]["id"], "base")
        self.assertEqual(result["dependencies"][1]["id"], "mid")
        self.assertEqual(result["dependencies"][2]["id"], "top")

    def test_missing_record(self):
        available = {"A@1": {"digest": "h1", "dependencies": [{"id": "B", "rev": "1", "digest": "h2"}]}}
        requested = [{"id": "A", "rev": "1", "digest": "h1"}]
        with self.assertRaises(ValueError) as cm:
            resolve(available, requested)
        self.assertEqual(str(cm.exception), "MISSING_RECORD")

    def test_digest_mismatch(self):
        available = {"A@1": {"digest": "h1"}}
        requested = [{"id": "A", "rev": "1", "digest": "wrong"}]
        with self.assertRaises(ValueError) as cm:
            resolve(available, requested)
        self.assertEqual(str(cm.exception), "DIGEST_MISMATCH")

    def test_cycle(self):
        available = {
            "A@1": {"digest": "h1", "dependencies": [{"id": "B", "rev": "1", "digest": "h2"}]},
            "B@1": {"digest": "h2", "dependencies": [{"id": "A", "rev": "1", "digest": "h1"}]}
        }
        requested = [{"id": "A", "rev": "1", "digest": "h1"}]
        with self.assertRaises(ValueError) as cm:
            resolve(available, requested)
        self.assertEqual(str(cm.exception), "CYCLE_DETECTED")

    def test_identity_collision(self):
        # Two different revisions of 'A' requested in one go
        available = {
            "A@1": {"digest": "h1"},
            "A@2": {"digest": "h2"}
        }
        requested = [
            {"id": "A", "rev": "1", "digest": "h1"},
            {"id": "A", "rev": "2", "digest": "h2"}
        ]
        with self.assertRaises(ValueError) as cm:
            resolve(available, requested)
        self.assertEqual(str(cm.exception), "IDENTITY_COLLISION")

    def test_cli_integration(self):
        # Simulate stdin/stdout
        input_json = json.dumps({
            "available_packages": {
                "A@1": {"digest": "h1", "size": 5}
            },
            "requested_identities": [{"id": "A", "rev": "1", "digest": "h1"}]
        })
        sys.stdin = io.StringIO(input_json)
        
        captured_stdout = io.StringIO()
        sys.stdout = captured_stdout
        
        # Import main from the module
        import tools.resolve_exact_package_dependency_closure as tool
        tool.main()
        
        output = json.loads(captured_stdout.getvalue())
        self.assertEqual(output["status"], "success")
        self.assertEqual(output["total_size_bytes"], 5)

if __name__ == "__main__":
    unittest.main()
