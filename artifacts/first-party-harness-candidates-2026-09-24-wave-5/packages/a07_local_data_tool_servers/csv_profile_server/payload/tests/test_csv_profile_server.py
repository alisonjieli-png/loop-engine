"""Starts csv_profile_server.py as a local process and checks its protocol answers; writes files only inside temporary folders.

Run from the package folder:
    python3 -I -B -m unittest discover -s tests -p "test_*.py" -v
"""
from __future__ import annotations

import hashlib
import json
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SERVER = PACKAGE / "server" / "csv_profile_server.py"
CONTRACT = PACKAGE / "contracts" / "profile_csv.input.schema.json"
EXAMPLES = PACKAGE / "examples"
VARIANTS = PACKAGE / "variants"
COMPANION = PACKAGE / "AGENTS.md"
NAME = "csv_profile_server"
NATIVE = "csv-profile-server"
SCRIPT = ".baltor/csv-profile-server/server/csv_profile_server.py"
CLAUDE_ROOT = "${CLAUDE_PROJECT_DIR:-.}"
CURSOR_ROOT = "${workspaceFolder}"
TOOL_NAMES = ["profile_csv"]
ENFORCED_KEYWORDS = {"$schema", "type", "properties", "required", "additionalProperties", "enum", "minimum",
                     "maximum", "minLength", "maxLength", "items", "minItems", "maxItems", "uniqueItems",
                     "description", "default"}


class Client:
    """A scripted protocol client that talks to the server over its standard input and output."""

    def __init__(self, root: Path, *extra: str) -> None:
        self.process = subprocess.Popen([sys.executable, "-I", "-B", str(SERVER), "--root", str(root), *extra],
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

    def call(self, arguments, name: str = "profile_csv") -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments})["result"]

    def close(self) -> int:
        if not self.process.stdin.closed:
            self.process.stdin.close()
        code = self.process.wait(timeout=10)
        for reader in self.readers:
            reader.join(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        return code


def columns_of(result: dict) -> dict:
    return {column["name"]: column for column in result["structuredContent"]["columns"]}


class ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Client(EXAMPLES)
        self.client.initialize()

    def tearDown(self) -> None:
        self.client.close()

    def test_initialize_negotiates_the_protocol_version(self):
        for asked, expected in (("2025-11-25", "2025-11-25"), ("2025-06-18", "2025-06-18"),
                                ("2025-03-26", "2025-03-26"), ("2026-07-28", "2025-11-25"),
                                ("1999-01-01", "2025-11-25")):
            result = self.client.request("initialize", {"protocolVersion": asked, "capabilities": {},
                                                        "clientInfo": {"name": "t", "version": "0"}})["result"]
            self.assertEqual(result["protocolVersion"], expected)
            self.assertIn("tools", result["capabilities"])
            self.assertEqual(result["serverInfo"]["name"], NAME)

    def test_tool_list_equals_the_contract_file(self):
        tools = self.client.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["profile_csv"])
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
        self.client.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 99}})
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_protocol_errors_use_json_rpc_codes(self):
        self.client.write(b"this is not json\n")
        self.assertEqual(self.client.receive()["error"]["code"], -32700)
        self.assertEqual(self.client.request("no/such/method")["error"]["code"], -32601)
        self.assertEqual(self.client.request("tools/call", {"arguments": {}})["error"]["code"], -32602)
        self.assertEqual(self.client.request("tools/call", {"name": "no_such_tool", "arguments": {}})["error"]["code"],
                         -32602)
        self.assertEqual(self.client.request("tools/call", {"name": "profile_csv", "arguments": []})["error"]["code"],
                         -32602)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_oversized_line_is_refused_and_the_server_continues(self):
        self.client.write(b'{"jsonrpc":"2.0","id":77,"method":"ping","params":{"pad":"'
                          + b"x" * (1024 * 1024) + b'"}}\n')
        self.assertEqual(self.client.receive()["error"]["code"], -32600)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_profile_reports_types_counts_and_record_lines(self):
        result = self.client.call({"path": "orders.csv"})
        self.assertFalse(result["isError"])
        profile = result["structuredContent"]
        self.assertEqual(json.loads(result["content"][0]["text"]), profile)
        self.assertEqual(profile["file"]["sha256"], hashlib.sha256((EXAMPLES / "orders.csv").read_bytes()).hexdigest())
        self.assertEqual(profile["rows_profiled"], 12)
        self.assertTrue(profile["complete"])
        self.assertEqual(profile["file"]["delimiter"], ",")
        self.assertEqual(profile["width_problems"],
                         {"rows_with_missing_fields": 1, "rows_with_extra_fields": 0, "first_lines": [12]})
        columns = columns_of(result)
        self.assertEqual((columns["order_id"]["inferred_type"], columns["order_id"]["distinct"]), ("integer", 12))
        self.assertEqual(columns["order_date"]["nonconforming_examples"], [{"line": 6, "value": "03/04/2025"}])
        self.assertEqual(columns["currency"]["whitespace_padded"], 1)
        self.assertEqual(columns["status"]["top_values"][0], {"value": "paid", "count": 9})
        self.assertEqual((columns["note"]["empty"], columns["note"]["missing_field"]), (8, 1))
        amount = columns["amount"]
        self.assertEqual(amount["top_values"][0], {"value": "19.99", "count": 3})
        self.assertEqual(amount["numeric_range"], ["0.50", "120"])

    def test_known_wrong_head_view_hides_the_broken_amounts(self):
        head = self.client.call({"path": "orders.csv", "max_rows": 2})["structuredContent"]
        self.assertFalse(head["complete"])
        self.assertEqual(next(c for c in head["columns"] if c["name"] == "amount")["inferred_type"], "decimal")
        amount = columns_of(self.client.call({"path": "orders.csv"}))["amount"]
        self.assertEqual((amount["inferred_type"], amount["dominant_type"]), ("mixed", "decimal"))
        self.assertEqual([(item["line"], item["value"]) for item in amount["nonconforming_examples"]],
                         [(4, "N/A"), (7, "12,50")])

    def test_include_values_false_hides_every_data_value(self):
        result = self.client.call({"path": "orders.csv", "include_values": False})
        self.assertFalse(result["isError"])
        for column in result["structuredContent"]["columns"]:
            self.assertNotIn("top_values", column)
            self.assertNotIn("numeric_range", column)
            self.assertTrue(all(set(item) == {"line"} for item in column["nonconforming_examples"]))
        text = result["content"][0]["text"]
        for value in ("N/A", "19.99", "03/04/2025", "first order"):
            self.assertNotIn(value, text)

    def test_column_selection_and_unknown_names(self):
        chosen = self.client.call({"path": "orders.csv", "columns": ["status"]})
        self.assertEqual(list(columns_of(chosen)), ["status"])
        unknown = self.client.call({"path": "orders.csv", "columns": ["price"]})
        self.assertTrue(unknown["isError"])
        self.assertIn("price", unknown["structuredContent"]["error"])

    def test_argument_problems_are_tool_errors(self):
        for arguments, word in (({"path": "orders.csv", "top_values": 99}, "top_values"),
                                ({"path": "orders.csv", "colour": "red"}, "colour"),
                                ({}, "path"), ({"path": "orders.csv", "delimiter": ":"}, "delimiter")):
            result = self.client.call(arguments)
            self.assertTrue(result["isError"], arguments)
            self.assertIn(word, json.dumps(result["structuredContent"]))

    def test_paths_outside_the_root_are_refused(self):
        for path in ("../orders.csv", "/etc/hostname", "missing.csv", ".", "sub/../orders.csv"):
            result = self.client.call({"path": path})
            self.assertTrue(result["isError"], path)

    def test_sample_arguments_file_works(self):
        arguments = json.loads((EXAMPLES / "profile_csv-arguments.json").read_text(encoding="utf-8"))
        result = self.client.call(arguments)
        self.assertFalse(result["isError"])
        self.assertLessEqual(len(columns_of(result)["amount"]["top_values"]), 3)


class TemporaryFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name) / "root"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.folder.cleanup()

    def start(self) -> Client:
        client = Client(self.root)
        self.addCleanup(client.close)
        client.initialize()
        return client

    def test_symbolic_link_out_of_the_root_is_refused(self):
        outside = Path(self.folder.name) / "outside.csv"
        outside.write_text("a,b\n1,2\n", encoding="utf-8")
        (self.root / "inside.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        try:
            (self.root / "link.csv").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links cannot be made here")
        client = self.start()
        self.assertTrue(client.call({"path": "link.csv"})["isError"])
        self.assertFalse(client.call({"path": "inside.csv"})["isError"])

    def test_decoding_error_names_the_line(self):
        (self.root / "names.csv").write_bytes(b"name\nalpha\nbeta\n\xff\xfeomega\n")
        client = self.start()
        refused = client.call({"path": "names.csv"})
        self.assertTrue(refused["isError"])
        self.assertIn("line 4", refused["structuredContent"]["error"])
        self.assertFalse(client.call({"path": "names.csv", "encoding": "latin-1"})["isError"])

    def test_semicolon_file_is_detected(self):
        (self.root / "semi.csv").write_text("id;price\n1;2,50\n2;3,75\n", encoding="utf-8")
        profile = self.start().call({"path": "semi.csv"})["structuredContent"]
        self.assertEqual(profile["file"]["delimiter"], ";")
        self.assertEqual([column["name"] for column in profile["columns"]], ["id", "price"])

    def test_wide_file_needs_a_column_list(self):
        names = [f"c{number}" for number in range(101)]
        (self.root / "wide.csv").write_text(",".join(names) + "\n" + ",".join("1" for _ in names) + "\n",
                                            encoding="utf-8")
        client = self.start()
        refused = client.call({"path": "wide.csv"})
        self.assertTrue(refused["isError"])
        self.assertEqual(refused["structuredContent"]["column_count"], 101)
        self.assertFalse(client.call({"path": "wide.csv", "columns": ["c0", "c100"]})["isError"])

    def test_known_wrong_non_ascii_values_leak_through_shapes_when_values_are_hidden(self):
        # The earlier shape table mapped only ASCII letters and digits, so with include_values false the shapes
        # still showed Chinese, Cyrillic, Greek and Arabic values whole and accented Latin values in part.
        arabic_name = "\u0645\u062d\u0645\u062f"
        arabic_city = "\u0627\u0644\u0642\u0627\u0647\u0631\u0629"
        rows = [["name", "city", "note", "code"],
                ["张伟", "北京", "糖尿病", "１２３"],
                ["Иван Петров", "Москва", "гипертония", "\u0663\u0664\u0665"],
                ["Ελένη Παππά", "Αθήνα", "άσθμα", "a\u00a0b\u3000c"],
                ["Zoë Müller", "Zürich", "e\u0301t\u00e9", "\U0001f600 ok"],
                [arabic_name, arabic_city, "ok", "N/A"],
                ["张伟", "北京", "糖尿病", "１２３"]]
        (self.root / "people.csv").write_text("\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8")
        client = self.start()
        hidden = client.call({"path": "people.csv", "include_values": False})
        self.assertFalse(hidden["isError"])
        line = client.last_line.decode("utf-8")
        self.assertEqual([character for character in line if ord(character) > 127], [])
        for row in rows[1:]:
            for value in row:
                if value not in ("ok", "N/A"):
                    self.assertNotIn(value, line)
        shapes = {column["name"]: [item["shape"] for item in column["top_shapes"]]
                  for column in hidden["structuredContent"]["columns"]}
        self.assertEqual(shapes["name"][0], "aa")
        self.assertIn("Aaaa Aaaaaa", shapes["name"])
        self.assertIn("999", shapes["code"])
        shown = client.call({"path": "people.csv"})
        self.assertIn("Москва", shown["content"][0]["text"])

    def test_known_wrong_wide_header_is_scanned_in_linear_time(self):
        # Counting each name with header.count took 21 seconds for 40,000 columns and could pass a client timeout.
        names = [f"f{number}" for number in range(40000)]
        (self.root / "wide40000.csv").write_text(",".join(names) + "\n" + ",".join("1" for _ in names) + "\n",
                                                 encoding="utf-8")
        client = self.start()
        started = time.monotonic()
        result = client.call({"path": "wide40000.csv", "columns": ["f0", "f39999"]})
        self.assertLess(time.monotonic() - started, 8.0)
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["column_count"], 40000)
        self.assertEqual([column["name"] for column in result["structuredContent"]["columns"]], ["f0", "f39999"])

    def test_answer_size_is_bounded(self):
        names = [f"column_{number}" for number in range(100)]
        rows = [",".join(names)]
        for row in range(30):
            rows.append(",".join(f"value {row:02d} {column:03d} " + "x" * 48 for column in range(100)))
        (self.root / "large.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        result = self.start().call({"path": "large.csv", "top_values": 20})
        self.assertTrue(result["isError"])
        self.assertIn("byte limit", result["structuredContent"]["error"])
        self.assertLess(len(result["content"][0]["text"]), 2000)

    def test_known_wrong_escapes_cannot_push_an_answer_line_past_256_kib(self):
        # Each backslash takes two bytes in the structured copy and four in the escaped text copy.
        sizes = ((20, False), (30, True))
        for columns, _ in sizes:
            names = [f"c{index}" for index in range(columns)]
            rows = [",".join(names)] + [",".join("\\" * 58 + f"{row:02d}" for _ in names) for row in range(20)]
            (self.root / f"escapes-{columns}.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        client = self.start()
        for columns, too_large in sizes:
            result = client.call({"path": f"escapes-{columns}.csv", "top_values": 20})
            self.assertLessEqual(len(client.last_line), 256 * 1024, columns)
            self.assertEqual(result["isError"], too_large, columns)
        self.assertIn("262144 byte limit", result["structuredContent"]["error"])

    def test_file_size_limit_is_refused(self):
        (self.root / "big.csv").write_bytes(b"a\n" + b"1\n" * (600 * 1024))
        client = Client(self.root, "--max-file-mib", "1")
        self.addCleanup(client.close)
        client.initialize()
        result = client.call({"path": "big.csv"})
        self.assertTrue(result["isError"])
        self.assertIn("limit", result["structuredContent"]["error"])


class LifecycleTests(unittest.TestCase):
    def test_server_exits_when_input_closes(self):
        client = Client(EXAMPLES)
        client.initialize()
        self.assertEqual(client.close(), 0)

    def test_missing_root_stops_at_start(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SERVER), "--root", str(PACKAGE / "no-such-folder")],
                                  input=b"", capture_output=True, timeout=30)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(finished.stdout, b"")


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
        self.assertIn("`profile_csv`", text)
        self.assertIn("-s .baltor/csv-profile-server/tests", text)
        self.assertIn("ends in `profile_csv`", text)
        self.assertIn("never instructions", text)
        self.assertIn("OK means the server works but the harness did not start it", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
