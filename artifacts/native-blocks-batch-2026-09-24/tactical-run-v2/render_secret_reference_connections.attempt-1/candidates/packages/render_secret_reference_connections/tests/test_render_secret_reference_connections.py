import unittest
import json
import subprocess
import sys
from io import BytesIO

class TestRenderSecretConnections(unittest.TestCase):
    def run_tool(self, input_data):
        """Helper to run the tool via subprocess to simulate real environment."""
        # We use sys.executable to run the current python interpreter
        process = subprocess.Popen(
            [sys.executable, "tools/render_secret_reference_connections.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # If input_data is a string (raw), we pass it directly
        # If it's a dict, we serialize it
        if isinstance(input_data, dict):
            input_str = json.dumps(input_data)
        else:
            input_str = input_data
            
        stdout, stderr = process.communicate(input=input_str)
        return json.loads(stdout)

    def test_success_claude(self):
        payload = {
            "server_id": "test-server",
            "url": "https://mcp.example.com",
            "env_var_name": "MY_SECRET",
            "target_profile": "claude"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["authorization"], "Bearer ${MY_SECRET}")
        self.assertEqual(result["data"]["url"], "https://mcp.example.com")

    def test_success_codex(self):
        payload = {
            "server_id": "test_server",
            "url": "https://mcp.example.com",
            "env_var_name": "MY_SECRET",
            "target_profile": "codex"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["bearer_token_env_var"], "MY_SECRET")

    def test_refuse_userinfo(self):
        payload = {
            "server_id": "test",
            "url": "https://user:pass@mcp.com",
            "env_var_name": "KEY",
            "target_profile": "claude"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "URL_HAS_USERINFO")

    def test_refuse_fragment(self):
        payload = {
            "server_id": "test",
            "url": "https://mcp.com#section",
            "env_var_name": "KEY",
            "target_profile": "claude"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "URL_HAS_FRAGMENT")

    def test_refuse_duplicate_keys(self):
        # Using raw string to ensure duplicate keys are passed to the parser
        raw_input = '{"server_id": "a", "server_id": "b", "url": "https://x.com", "env_var_name": "K", "target_profile": "claude"}'
        result = self.run_tool(raw_input)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "DUPLICATE_KEY")

    def test_refuse_non_finite(self):
        # JSON standard doesn't strictly allow NaN, but many parsers do. 
        # Our tool must explicitly reject it.
        raw_input = '{"server_id": "a", "url": "https://x.com", "env_var_name": "K", "target_profile": "claude", "val": NaN}'
        # Note: Python's json.loads handles NaN by default, so we check if our logic catches it.
        # We must use a string that contains NaN.
        result = self.run_tool(raw_input)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "NON_FINITE_NUMBER")

    def test_invalid_env_name(self):
        payload = {
            "server_id": "test",
            "url": "https://mcp.com",
            "env_var_name": "123_INVALID", # Starts with number
            "target_profile": "claude"
        }
        result = self.run_tool(payload)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "INVALID_ENV_VAR_NAME")

if __name__ == "__main__":
    unittest.main()
