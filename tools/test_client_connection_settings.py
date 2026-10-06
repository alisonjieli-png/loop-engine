"""The browser copies the service's canonical OAuth resource, never an alias."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/loop_engine/core/service_runtime/web_assets/client-access.js"


class ConnectionEndpointTests(unittest.TestCase):
    def test_endpoint_selection_and_refusals(self):
        record = {"record_type": "service_capabilities/v1", "authorization_server": {
            "record_type": "service_oauth_server_capabilities/v1", "available": True,
            "resource": "https://canonical.example.invalid/mcp"}}
        alias = "https://app.example.invalid"
        cases = [{"record": record, "origin": alias, "expected": record["authorization_server"]["resource"]}]
        for resource in ["http://canonical.example.invalid/mcp", "javascript:alert(1)",
                         "/mcp", "https://u:p@canonical.example.invalid/mcp", "https://canonical.example.invalid/mcp?q=x",
                         "https://canonical.example.invalid/mcp#x", "https://canonical.example.invalid/other",
                         " https://canonical.example.invalid/mcp", "https:\\canonical.example.invalid\\mcp", None]:
            cases.append({"record": {**record, "authorization_server": {**record["authorization_server"], "resource": resource}},
                          "origin": alias, "expected": None})
        for bad in [None, {}, {**record, "record_type": "service_capabilities/v99"},
                    {**record, "authorization_server": {**record["authorization_server"], "record_type": "unknown"}},
                    {**record, "authorization_server": {**record["authorization_server"], "available": "true"}}]:
            cases.append({"record": bad, "origin": alias, "expected": None})
        disabled = {**record, "authorization_server": {**record["authorization_server"], "available": False}}
        cases.append({"record": disabled, "origin": "http://127.0.0.1:8123", "expected": "http://127.0.0.1:8123/mcp"})
        script = """const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8')),sandbox={window:{},URL};
vm.runInNewContext(input.source,sandbox);
const results=input.cases.map(c=>sandbox.window.BaltorClientAccess.protocolEndpoint(c.record,c.origin));
process.stdout.write(JSON.stringify(results));"""
        completed = subprocess.run(["node", "-e", script], input=json.dumps({"source": SOURCE.read_text(), "cases": cases}),
                                   text=True, capture_output=True, timeout=10, check=True)
        self.assertEqual(json.loads(completed.stdout), [case["expected"] for case in cases])


if __name__ == "__main__":
    unittest.main()
