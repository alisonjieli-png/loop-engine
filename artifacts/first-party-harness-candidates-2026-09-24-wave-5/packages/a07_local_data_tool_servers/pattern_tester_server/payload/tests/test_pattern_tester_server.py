"""Starts pattern_tester_server.py as a local process and checks its protocol answers; writes files only inside temporary folders.

Run from the package folder:
    python3 -I -B -m unittest discover -s tests -p "test_*.py" -v
"""
from __future__ import annotations

import json
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SERVER = PACKAGE / "server" / "pattern_tester_server.py"
CONTRACT = PACKAGE / "contracts" / "test_pattern.input.schema.json"
EXAMPLES = PACKAGE / "examples"
VARIANTS = PACKAGE / "variants"
COMPANION = PACKAGE / "AGENTS.md"
NAME = "pattern_tester_server"
NATIVE = "pattern-tester-server"
SCRIPT = ".baltor/pattern-tester-server/server/pattern_tester_server.py"
CLAUDE_ROOT = "${CLAUDE_PROJECT_DIR:-.}"
CURSOR_ROOT = "${workspaceFolder}"
TOOL_NAMES = ["test_pattern"]
ENFORCED_KEYWORDS = {"$schema", "type", "properties", "required", "additionalProperties", "enum", "minimum",
                     "maximum", "minLength", "maxLength", "items", "minItems", "maxItems", "uniqueItems",
                     "description", "default"}


class Client:
    """A scripted protocol client that talks to the server over its standard input and output."""

    def __init__(self, root: Path) -> None:
        self.process = subprocess.Popen([sys.executable, "-I", "-B", str(SERVER), "--root", str(root)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.answers: queue.Queue = queue.Queue()
        self.diagnostics: list[bytes] = []
        self.readers = [threading.Thread(target=self._read_answers, daemon=True),
                        threading.Thread(target=self._read_diagnostics, daemon=True)]
        for reader in self.readers:
            reader.start()
        self.last_id = 0
        self.last_line = b""

    def _read_answers(self) -> None:
        for line in self.process.stdout:
            self.answers.put(line)
        self.answers.put(None)

    def _read_diagnostics(self) -> None:
        for line in self.process.stderr:
            self.diagnostics.append(line)

    def write(self, data: bytes) -> None:
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def send(self, message: dict) -> None:
        self.write(json.dumps(message).encode("utf-8") + b"\n")

    def receive(self, timeout: float = 30.0) -> dict:
        line = self.answers.get(timeout=timeout)
        if line is None:
            raise AssertionError(f"the server closed its output: {b''.join(self.diagnostics)[-600:]!r}")
        self.last_line = line
        return json.loads(line)

    def request(self, method: str, params=None) -> dict:
        self.last_id += 1
        message = {"jsonrpc": "2.0", "id": self.last_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        answer = self.receive()
        if answer.get("id") != self.last_id:
            raise AssertionError(f"answer for another request: {answer}")
        return answer

    def initialize(self, version: str = "2025-11-25") -> dict:
        answer = self.request("initialize", {"protocolVersion": version, "capabilities": {},
                                             "clientInfo": {"name": "scripted-test", "version": "0.1.0"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return answer

    def call(self, arguments) -> dict:
        return self.request("tools/call", {"name": "test_pattern", "arguments": arguments})["result"]

    def close(self) -> int:
        if not self.process.stdin.closed:
            self.process.stdin.close()
        code = self.process.wait(timeout=10)
        for reader in self.readers:
            reader.join(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        return code


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


class ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Client(EXAMPLES)
        self.client.initialize()

    def tearDown(self) -> None:
        self.client.close()

    def test_initialize_negotiates_the_protocol_version(self):
        for asked, expected in (("2025-11-25", "2025-11-25"), ("2025-06-18", "2025-06-18"),
                                ("2025-03-26", "2025-03-26"), ("2026-07-28", "2025-11-25"), (7, "2025-11-25")):
            result = self.client.request("initialize", {"protocolVersion": asked, "capabilities": {},
                                                        "clientInfo": {"name": "t", "version": "0"}})["result"]
            self.assertEqual(result["protocolVersion"], expected)
            self.assertIn("tools", result["capabilities"])
            self.assertEqual(result["serverInfo"]["name"], NAME)

    def test_tool_list_equals_the_contract_file(self):
        tools = self.client.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["test_pattern"])
        self.assertEqual(tools[0]["inputSchema"], json.loads(CONTRACT.read_text(encoding="utf-8")))
        self.assertTrue(tools[0]["description"].strip())

    def test_contract_uses_only_keywords_the_server_enforces(self):
        pending = [json.loads(CONTRACT.read_text(encoding="utf-8"))]
        while pending:
            schema = pending.pop()
            self.assertLessEqual(set(schema), ENFORCED_KEYWORDS)
            pending.extend(schema.get("properties", {}).values())
            if isinstance(schema.get("items"), dict):
                pending.append(schema["items"])

    def test_notification_gets_no_answer_and_ping_answers_empty(self):
        self.client.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}})
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_protocol_errors_use_json_rpc_codes(self):
        self.client.write(b"\xff\xfe not utf-8\n")
        self.assertEqual(self.client.receive()["error"]["code"], -32700)
        self.assertEqual(self.client.request("tools/run")["error"]["code"], -32601)
        self.assertEqual(self.client.request("tools/call", {"name": "test_pattern", "arguments": 5})["error"]["code"],
                         -32602)
        self.assertEqual(self.client.request("tools/call", {"name": "test_regex", "arguments": {}})["error"]["code"],
                         -32602)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_oversized_line_is_refused_and_the_server_continues(self):
        self.client.write(b'{"jsonrpc":"2.0","id":8,"method":"ping","params":{"pad":"'
                          + b"p" * (1024 * 1024) + b'"}}\n')
        self.assertEqual(self.client.receive()["error"]["code"], -32600)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_sample_arguments_pass_with_groups_and_replacement(self):
        result = self.client.call(example("test_pattern-arguments.json"))
        self.assertFalse(result["isError"])
        answer = result["structuredContent"]
        self.assertEqual(json.loads(result["content"][0]["text"]), answer)
        self.assertTrue(answer["passed"])
        self.assertEqual(answer["group_names"], ["year", "month", "day"])
        first = answer["results"][0]
        self.assertEqual((first["named"], first["replaced"]),
                         ({"year": "2025", "month": "03", "day": "01"}, "01.03.2025"))

    def test_known_wrong_search_mode_accepts_values_a_rule_must_reject(self):
        wrong = example("known-wrong-search-arguments.json")
        answer = self.client.call(wrong)["structuredContent"]
        self.assertFalse(answer["passed"])
        self.assertEqual([item["index"] for item in answer["false_matches"]], [0, 1, 2])
        self.assertTrue(any("fullmatch" in note for note in answer["notes"]))
        self.assertTrue(any("ASCII" in note for note in answer["notes"]))
        repaired = dict(wrong, pattern="[0-9]{4}-[0-9]{2}-[0-9]{2}", mode="fullmatch")
        self.assertTrue(self.client.call(repaired)["structuredContent"]["passed"])

    def test_misses_are_listed(self):
        answer = self.client.call({"pattern": "[0-9]{4}-[0-9]{2}-[0-9]{2}",
                                   "should_match": ["2025-03-01", "2025-3-1"]})["structuredContent"]
        self.assertFalse(answer["passed"])
        self.assertEqual(answer["misses"], [{"index": 1, "text": "2025-3-1"}])

    def test_findall_and_replacement_of_every_match(self):
        found = self.client.call({"pattern": "[0-9]+(?:[.,][0-9]+)?", "mode": "findall",
                                  "examples": ["paid 12,50 and 3.25 on 2025"]})["structuredContent"]["results"][0]
        self.assertEqual(found["match_count"], 3)
        self.assertEqual([item["matched_text"] for item in found["matches"]], ["12,50", "3.25", "2025"])
        spaced = self.client.call({"pattern": "\\s+", "mode": "search", "replacement": " ",
                                   "examples": ["a  b\t c"]})["structuredContent"]["results"][0]
        self.assertEqual(spaced["replaced"], "a b c")

    def test_flags_change_the_answer(self):
        arguments = {"pattern": "paid", "should_match": ["PAID"]}
        self.assertFalse(self.client.call(arguments)["structuredContent"]["passed"])
        self.assertTrue(self.client.call(dict(arguments, flags=["IGNORECASE"]))["structuredContent"]["passed"])

    def test_pattern_and_replacement_errors_are_explained(self):
        broken = self.client.call({"pattern": "([0-9]", "examples": ["1"]})
        self.assertTrue(broken["isError"])
        self.assertIsNotNone(broken["structuredContent"]["position"])
        missing_group = self.client.call({"pattern": "([0-9])", "replacement": "\\2", "examples": ["1"]})
        self.assertTrue(missing_group["isError"])
        self.assertIn("replacement", missing_group["structuredContent"]["error"])

    def test_argument_limits_are_tool_errors(self):
        for arguments, word in (({"pattern": "a"}, "at least one text"),
                                ({"pattern": "a", "examples": ["x"] * 101}, "examples"),
                                ({"pattern": "a", "examples": ["x" * 10001]}, "examples"),
                                ({"pattern": "a" * 2001, "examples": ["x"]}, "pattern"),
                                ({"pattern": "a", "examples": ["x"], "flags": ["UNICODE"]}, "flags"),
                                ({"pattern": "a", "examples": ["x"], "time_limit_ms": 50}, "time_limit_ms"),
                                ({"examples": ["x"]}, "pattern")):
            result = self.client.call(arguments)
            self.assertTrue(result["isError"], arguments)
            self.assertIn(word, json.dumps(result["structuredContent"]))

    def test_texts_without_expectations_give_no_verdict(self):
        answer = self.client.call({"pattern": "[a-z]+", "examples": ["abc"]})["structuredContent"]
        self.assertIsNone(answer["passed"])
        self.assertTrue(any("should_match" in note for note in answer["notes"]))

    def test_known_wrong_escapes_cannot_push_an_answer_line_past_256_kib(self):
        # Each backslash takes two bytes in the structured copy and four in the escaped text copy.
        pattern = "(.{80})" * 20
        for count, too_large in ((20, False), (25, True)):
            result = self.client.call({"pattern": pattern, "examples": ["\\" * 1600] * count})
            self.assertLessEqual(len(self.client.last_line), 256 * 1024, count)
            self.assertEqual(result["isError"], too_large, count)
        self.assertIn("262144 byte limit", result["structuredContent"]["error"])

    def test_long_texts_are_shortened_in_the_answer(self):
        entry = self.client.call({"pattern": "a+", "examples": ["a" * 500]})["structuredContent"]["results"][0]
        self.assertEqual((len(entry["text"]), entry["text_chars"]), (80, 500))

    def test_lone_surrogate_still_gets_an_answer(self):
        self.client.write(b'{"jsonrpc":"2.0","id":90,"method":"tools/call","params":{"name":"test_pattern",'
                          b'"arguments":{"pattern":"b","examples":["a\\ud800b"]}}}\n')
        answer = self.client.receive()
        self.assertEqual(answer["id"], 90)
        self.assertFalse(answer["result"]["isError"])

    @unittest.skipUnless(hasattr(signal, "setitimer"), "no timer signal on this platform")
    def test_time_limit_stops_a_backtracking_pattern(self):
        started = time.monotonic()
        result = self.client.call({"pattern": "(a+)+$", "mode": "search", "examples": ["a" * 40 + "b"],
                                   "time_limit_ms": 300})
        self.assertTrue(result["isError"])
        self.assertIn("time limit", result["structuredContent"]["error"])
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(self.client.request("ping")["result"], {})


class LifecycleTests(unittest.TestCase):
    def test_server_exits_when_input_closes(self):
        client = Client(EXAMPLES)
        client.initialize()
        self.assertEqual(client.close(), 0)

    def test_root_is_never_read(self):
        client = Client(PACKAGE / "no-such-folder")
        try:
            client.initialize()
            self.assertFalse(client.call({"pattern": "a", "should_match": ["a"]})["isError"])
        finally:
            self.assertEqual(client.close(), 0)


def launch(prefix: str | None = None) -> list[str]:
    """Launch arguments after python3: a relative script path, or one under a harness variable for the root."""
    if prefix is None:
        return ["-I", "-B", SCRIPT, "--root", "."]
    return ["-I", "-B", f"{prefix}/{SCRIPT}", "--root", prefix]


def expand(value: str, variables: dict) -> str:
    """Expands ${NAME} and ${NAME:-default} as the Claude Code and Cursor documentation describe them."""
    def one(match):
        if match.group(1) in variables:
            return variables[match.group(1)]
        return match.group(0) if match.group(2) is None else match.group(2)
    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}", one, value)


def start_and_list(arguments: list, folder: Path):
    """Starts the server with these arguments in folder; returns the listed tool names, or None without an answer."""
    messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                            "clientInfo": {"name": "launch-test", "version": "0.1.0"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
    finished = subprocess.run([sys.executable, *arguments], cwd=folder, capture_output=True, timeout=60,
                              input="".join(json.dumps(message) + "\n" for message in messages).encode("utf-8"))
    lines = finished.stdout.decode("utf-8").splitlines()
    if finished.returncode != 0 or len(lines) != 2:
        return None
    return [tool["name"] for tool in json.loads(lines[1])["result"]["tools"]]


@unittest.skipUnless(VARIANTS.is_dir(), "harness variants are placed at their own destinations")
class VariantTests(unittest.TestCase):
    def read(self, *parts: str):
        return json.loads(VARIANTS.joinpath(*parts).read_text(encoding="utf-8"))

    def test_every_variant_starts_this_server_locally(self):
        self.assertEqual(self.read("claude_code", ".mcp.json"),
                         {"mcpServers": {NAME: {"command": "python3", "args": launch(CLAUDE_ROOT)}}})
        self.assertEqual(self.read("cursor", "mcp.json"),
                         {"mcpServers": {NAME: {"command": "python3", "args": launch(CURSOR_ROOT)}}})
        self.assertEqual(self.read("gemini_cli", "settings.json"),
                         {"mcpServers": {NATIVE: {"command": "python3", "args": launch()}}})
        self.assertEqual(self.read("opencode", "opencode.json"),
                         {"mcp": {NAME: {"type": "local", "command": ["python3", *launch()], "cwd": ".",
                                         "enabled": True}}})
        codex = VARIANTS.joinpath("codex", "config.toml").read_text(encoding="utf-8")
        self.assertEqual(codex, f"[mcp_servers.{NAME}]\ncommand = \"python3\"\nargs = {json.dumps(launch())}\n")
        try:
            import tomllib
        except ImportError:
            return
        self.assertEqual(tomllib.loads(codex), {"mcp_servers": {NAME: {"command": "python3", "args": launch()}}})

    def test_known_wrong_gemini_server_key_with_underscores(self):
        # Gemini CLI splits a tool's full name mcp_<server>_<tool> at the first underscore after mcp_, so an
        # underscore in the server key makes its policy rules miss this server. The key is the hyphenated name.
        keys = list(self.read("gemini_cli", "settings.json")["mcpServers"])
        self.assertEqual(keys, [NATIVE])
        self.assertNotIn("_", keys[0])
        self.assertNotEqual(keys[0], NAME)

    def test_launch_path_names_this_server_file(self):
        self.assertEqual(Path(launch()[2]).name, SERVER.name)

    def test_expanded_launch_lines_start_the_server_from_a_subfolder(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / "workspace"
            placed = workspace / SCRIPT
            placed.parent.mkdir(parents=True)
            placed.write_bytes(SERVER.read_bytes())
            (workspace / "sub").mkdir()
            claude = self.read("claude_code", ".mcp.json")["mcpServers"][NAME]["args"]
            cursor = self.read("cursor", "mcp.json")["mcpServers"][NAME]["args"]
            for arguments, variables in ((claude, {"CLAUDE_PROJECT_DIR": str(workspace)}),
                                         (cursor, {"workspaceFolder": str(workspace)})):
                expanded = [expand(item, variables) for item in arguments]
                self.assertEqual(Path(expanded[2]), placed)
                self.assertEqual(start_and_list(expanded, workspace / "sub"), TOOL_NAMES)
            # Known-wrong: the relative launch line answers only when the server starts in the workspace root.
            self.assertEqual(start_and_list(launch(), workspace), TOOL_NAMES)
            self.assertIsNone(start_and_list(launch(), workspace / "sub"))
            # Claude Code sets CLAUDE_PROJECT_DIR for the server, not for itself; without it the default keeps "."
            self.assertEqual([expand(item, {}) for item in claude], launch("."))


@unittest.skipUnless(COMPANION.is_file(), "the companion is composed into the root instruction file")
class CompanionTests(unittest.TestCase):
    def test_companion_names_the_tool_and_the_check_command(self):
        text = COMPANION.read_text(encoding="utf-8")
        self.assertIn("`test_pattern`", text)
        self.assertIn("-s .baltor/pattern-tester-server/tests", text)
        self.assertIn("ending in `test_pattern`", text)
        self.assertIn("also matches before a final line break", text)
        self.assertIn("OK means the server works but the harness did not start it", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
