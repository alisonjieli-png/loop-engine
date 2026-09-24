"""Scripted client tests for server/step_packet_server.py over standard input and output."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server" / "step_packet_server.py"
WORKSPACE = ROOT / "examples" / "workspace"
CONTRACTS = ROOT / "contracts"
TOOLS = ("read_step_assignment", "read_step_file", "write_step_result")


def request(request_id, method: str, params=None) -> dict:
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def initialize(version: str = "2025-11-25") -> dict:
    return request(0, "initialize", {"protocolVersion": version, "capabilities": {},
                                     "clientInfo": {"name": "scripted-test", "version": "0.1.0"}})


def exchange(messages, root: Path = WORKSPACE, raw_lines=()) -> tuple[list[dict], subprocess.CompletedProcess]:
    """Send every message as one line, close the input and read every answer line."""
    lines = [json.dumps(message).encode("utf-8") for message in messages] + list(raw_lines)
    finished = subprocess.run([sys.executable, "-I", "-B", str(SERVER), "--root", str(root)],
                              input=b"\n".join(lines) + b"\n", capture_output=True, timeout=60,
                              env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    answers = [json.loads(line) for line in finished.stdout.decode("utf-8").splitlines() if line.strip()]
    return answers, finished


def call(tool: str, arguments, request_id=1) -> dict:
    return request(request_id, "tools/call", {"name": tool, "arguments": arguments})


def load_server():
    spec = importlib.util.spec_from_file_location("server_under_test", SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProtocolTests(unittest.TestCase):
    def test_initialize_answers_a_supported_version_and_never_a_newer_one(self):
        for asked, answered in (("2025-11-25", "2025-11-25"), ("2025-06-18", "2025-06-18"),
                                ("2025-03-26", "2025-03-26"), ("2024-11-05", "2025-11-25"),
                                ("2026-07-28", "2025-11-25")):
            answers, finished = exchange([initialize(asked)])
            self.assertEqual(finished.returncode, 0)
            result = answers[0]["result"]
            self.assertEqual(result["protocolVersion"], answered)
            self.assertIn("tools", result["capabilities"])
            self.assertEqual(result["serverInfo"]["name"], "portable_step_packet_plugin")
            self.assertIn("read_step_assignment", result["instructions"])

    def test_notification_gets_no_answer_and_ping_answers_empty(self):
        answers, _ = exchange([initialize(), {"jsonrpc": "2.0", "method": "notifications/initialized"},
                               request(7, "ping")])
        self.assertEqual([answer["id"] for answer in answers], [0, 7])
        self.assertEqual(answers[1]["result"], {})

    def test_tools_list_equals_the_contract_files(self):
        answers, _ = exchange([initialize(), request(2, "tools/list", {})])
        tools = {tool["name"]: tool for tool in answers[1]["result"]["tools"]}
        self.assertEqual(sorted(tools), sorted(TOOLS))
        for name in TOOLS:
            contract = json.loads((CONTRACTS / f"{name}.input.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(tools[name]["inputSchema"], contract)
            self.assertGreater(len(tools[name]["description"]), 40)

    def test_protocol_errors_have_their_codes(self):
        answers, finished = exchange([request(3, "no/such/method"), [request(4, "ping")],
                                      {"id": 5, "method": "ping"}, {"jsonrpc": "2.0", "id": True, "method": "ping"}],
                                     raw_lines=[b"{not json", b'{"jsonrpc": "2.0", "id": 9, "id": 10, "method": "ping"}'])
        self.assertEqual([answer["error"]["code"] for answer in answers], [-32601, -32600, -32600, -32600, -32700, -32700])
        self.assertEqual([answer["id"] for answer in answers], [3, None, 5, None, None, None])
        self.assertEqual(finished.returncode, 0)

    def test_oversized_line_is_refused_and_the_server_goes_on(self):
        big = b'{"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {"pad": "' + b"x" * (1024 * 1024) + b'"}}'
        answers, _ = exchange([], raw_lines=[big, json.dumps(request(2, "ping")).encode()])
        self.assertEqual((answers[0]["error"]["code"], answers[0]["id"]), (-32600, None))
        self.assertEqual((answers[1]["id"], answers[1]["result"]), (2, {}))

    def test_server_stops_when_input_closes_and_keeps_stdout_for_protocol_lines(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SERVER), "--root", str(WORKSPACE)], input=b"",
                                  capture_output=True, timeout=30, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
        self.assertEqual((finished.returncode, finished.stdout), (0, b""))
        self.assertIn(b"portable_step_packet_plugin", finished.stderr)

    def test_answer_above_the_limit_becomes_a_tool_error(self):
        module = load_server()
        huge = {"content": [{"type": "text", "text": "x" * (300 * 1024)}], "structuredContent": {}, "isError": False}
        line = module.encode(module.result_answer(8, huge))
        self.assertLessEqual(len(line), module.MAX_ANSWER_BYTES)
        answer = json.loads(line)
        self.assertTrue(answer["result"]["isError"])
        self.assertEqual(answer["result"]["structuredContent"]["error"], "answer_too_large")


class ToolTests(unittest.TestCase):
    def test_read_step_assignment_returns_the_card_as_text_and_structure(self):
        answers, _ = exchange([initialize(), call("read_step_assignment", {})])
        result = answers[1]["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
        self.assertEqual(result["structuredContent"]["task"]["node_id"], "newest-release")
        self.assertEqual(result["structuredContent"]["output"]["required_fields"], ["version", "release_date", "change_count"])

    def test_read_step_file_serves_packet_text_and_refuses_escapes(self):
        answers, _ = exchange([call("read_step_file", {"name": "checklist.md"}, 1),
                               call("read_step_file", {"name": "../../CHANGELOG.md"}, 2)])
        self.assertIn("## Before handoff", answers[0]["result"]["structuredContent"]["text"])
        self.assertTrue(answers[1]["result"]["isError"])
        self.assertEqual(answers[1]["result"]["structuredContent"]["error"], "unsafe_path")

    def test_write_step_result_saves_a_good_result_and_refuses_a_wrong_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(WORKSPACE / ".baltor", root / ".baltor")
            good = {"version": "2.4.1", "release_date": "2026-09-18", "change_count": 3}
            answers, _ = exchange([call("write_step_result", {"result": good}, 1),
                                   call("write_step_result", {"result": {"release": "2.4.1"}}, 2)], root=root)
            first, second = answers[0]["result"], answers[1]["result"]
            self.assertFalse(first["isError"])
            saved = json.loads((root / first["structuredContent"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["result"], good)
            self.assertTrue(second["isError"])
            self.assertIn("unknown_field: release", second["structuredContent"]["problems"])
            folder = root / ".baltor/state/portable-step-packet-plugin/results/newest-release"
            self.assertEqual(sorted(os.listdir(folder)), ["result-001.json"])

    def test_invalid_tool_arguments_are_protocol_errors(self):
        answers, _ = exchange([call("no_such_tool", {}, 1), call("read_step_file", {}, 2),
                               call("read_step_file", {"name": "a.md", "mode": "x"}, 3),
                               call("read_step_file", {"name": 7}, 4), call("read_step_file", {"name": ""}, 5),
                               call("read_step_assignment", [], 6), call("write_step_result", {}, 7)])
        self.assertEqual([answer["error"]["code"] for answer in answers], [-32602] * 7)

    def test_missing_step_folder_is_a_tool_error_that_names_the_root(self):
        answers, _ = exchange([call("read_step_assignment", {})], root=ROOT / "examples")
        result = answers[0]["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["error"], "step_folder_missing")

    def test_root_is_found_from_the_placed_server_path(self):
        module = load_server()
        placed = Path("/w/.baltor/plugins/portable-step-packet-plugin/server/step_packet_server.py")
        self.assertEqual(module.default_root(placed, Path("/cwd")), Path("/w"))
        self.assertEqual(module.default_root(Path("/opt/p/server/step_packet_server.py"), Path("/cwd")), Path("/cwd"))


if __name__ == "__main__":
    unittest.main()
