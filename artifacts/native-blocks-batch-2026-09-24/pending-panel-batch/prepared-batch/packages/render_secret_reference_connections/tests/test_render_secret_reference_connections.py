import unittest
import json
import subprocess
import sys
import os

class TestRenderSecretConnections(unittest.TestCase):
    def setUp(self):
        self.tool_path = os.path.abspath("tools/render_secret_reference_connections.py")
        # Ensure we can find the tool even if run from different dirs
        self.env = os.environ.copy()

    def run_tool(self, payload: dict) -> dict:
        input_str = json.dumps(payload)
        proc = subprocess.run(
            [sys.executable, self.tool_path],
            input=input_str,
            capture_output=True,
            text=True,
            env=self.env
        )
        return json.loads(proc.stdout)

    def test_success_codex(self):
        payload = {
            "server_id": "test_server",
            "url": "https://test.com",
            "env_var_name": "TEST_VAR",
            "target_profile": "codex"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "success")
        self.assertIn('url = "https://test.com"', result["result"])
        self.assertIn('bearer_token_env_var = "TEST_VAR"', result["result"])

    def test_success_claude(self):
        payload = {
            "server_id": "test_server",
            "url": "https://test.com",
            "env_var_name": "TEST_VAR",
            "target_profile": "claude"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "success")
        self.assertIn('"Authorization": "Bearer ${TEST_VAR}"', result["result"])

    def test_refuse_invalid_url_scheme(self):
        payload = {
            "server_id": "test",
            "url": "http://test.com",
            "env_var_name": "VAR",
            "target_profile": "codex"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "invalid_scheme")

    def test_refuse_userinfo(self):
        payload = {
            "server_id": "test",
            "url": "https://user:pass@test.com",
            "env_var_name": "VAR",
            "target_profile": "codex"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "url_has_userinfo")

    def test_refuse_non_finite(self):
        # Manually construct string to bypass json.dumps standard behavior if needed
        # but we test the tool's ability to catch it in the raw input
        input_str = '{"server_id": "test", "url": "https://t.com", "env_var_name": "V", "target_profile": "codex", "val": NaN}'
        proc = subprocess.run(
            [sys.executable, self.tool_path],
            input=input_str,
            capture_output=True,
            text=True,
            env=self.env
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "non_finite_number")

    def test_refuse_invalid_id(self):
        payload = {
            "server_id": "123_invalid", # starts with number
            "url": "https://test.com",
            "env_var_name": "VAR",
            "target_profile": "codex"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "invalid_server_id")

if __name__ == "__main__":
    unittest.main()
