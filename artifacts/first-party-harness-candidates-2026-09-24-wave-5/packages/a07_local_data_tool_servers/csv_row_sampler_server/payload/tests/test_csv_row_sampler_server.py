"""Starts csv_row_sampler_server.py as a local process and checks its protocol answers; writes files only inside temporary folders.

Run from the package folder:
    python3 -I -B -m unittest discover -s tests -p "test_*.py" -v
"""
from __future__ import annotations

import csv
import json
import queue
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SERVER = PACKAGE / "server" / "csv_row_sampler_server.py"
CONTRACT = PACKAGE / "contracts" / "sample_csv_rows.input.schema.json"
EXAMPLES = PACKAGE / "examples"
VARIANTS = PACKAGE / "variants"
COMPANION = PACKAGE / "AGENTS.md"
NAME = "csv_row_sampler_server"
NATIVE = "csv-row-sampler-server"
SCRIPT = ".baltor/csv-row-sampler-server/server/csv_row_sampler_server.py"
CLAUDE_ROOT = "${CLAUDE_PROJECT_DIR:-.}"
CURSOR_ROOT = "${workspaceFolder}"
TOOL_NAMES = ["sample_csv_rows"]
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

    def call(self, arguments, name: str = "sample_csv_rows") -> dict:
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


def lines_of(result: dict) -> list[int]:
    return [entry["line"] for entry in result["structuredContent"]["sample"]]


class ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Client(EXAMPLES)
        self.client.initialize()

    def tearDown(self) -> None:
        self.client.close()

    def test_initialize_negotiates_the_protocol_version(self):
        for asked, expected in (("2025-11-25", "2025-11-25"), ("2025-06-18", "2025-06-18"),
                                ("2025-03-26", "2025-03-26"), ("2026-07-28", "2025-11-25"),
                                ("not-a-version", "2025-11-25")):
            result = self.client.request("initialize", {"protocolVersion": asked, "capabilities": {},
                                                        "clientInfo": {"name": "t", "version": "0"}})["result"]
            self.assertEqual(result["protocolVersion"], expected)
            self.assertIn("tools", result["capabilities"])
            self.assertEqual(result["serverInfo"]["name"], NAME)

    def test_tool_list_equals_the_contract_file(self):
        tools = self.client.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["sample_csv_rows"])
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
        self.client.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 5}})
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_protocol_errors_use_json_rpc_codes(self):
        self.client.write(b"{broken json\n")
        self.assertEqual(self.client.receive()["error"]["code"], -32700)
        self.assertEqual(self.client.request("resources/list")["error"]["code"], -32601)
        self.assertEqual(self.client.request("tools/call", {"name": 12})["error"]["code"], -32602)
        self.assertEqual(self.client.request("tools/call", {"name": "profile_csv", "arguments": {}})["error"]["code"],
                         -32602)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_oversized_line_is_refused_and_the_server_continues(self):
        self.client.write(b'{"jsonrpc":"2.0","id":9,"method":"ping","params":{"pad":"'
                          + b"y" * (1024 * 1024) + b'"}}\n')
        self.assertEqual(self.client.receive()["error"]["code"], -32600)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_known_wrong_head_rows_miss_whole_groups(self):
        with (EXAMPLES / "readings.csv").open(encoding="utf-8", newline="") as stream:
            head = [row["site"] for _, row in zip(range(6), csv.DictReader(stream))]
        self.assertEqual(set(head), {"north"})
        result = self.client.call({"path": "readings.csv", "group_by": "site", "per_group": 2, "seed": 7})
        self.assertFalse(result["isError"])
        sample = result["structuredContent"]
        self.assertEqual(sorted(entry["values"]["site"] for entry in sample["sample"]),
                         ["east", "east", "north", "north", "south", "south"])
        self.assertEqual(sample["groups"], [{"value": "north", "rows": 12, "sampled": 2},
                                            {"value": "south", "rows": 8, "sampled": 2},
                                            {"value": "east", "rows": 4, "sampled": 2}])

    def test_same_seed_gives_the_same_pinned_rows(self):
        # The pinned lines were computed separately from the reservoir rule with random.Random(seed).random(),
        # the one generator method whose sequence Python documents as stable across versions. The pre-checks run
        # this test under Python 3.10 and 3.14; other versions were not tested.
        grouped = {"path": "readings.csv", "group_by": "site", "per_group": 2, "seed": 7}
        self.assertEqual(lines_of(self.client.call(grouped)), [3, 12, 21, 22, 23, 25])
        self.assertEqual(lines_of(self.client.call(grouped)), [3, 12, 21, 22, 23, 25])
        self.assertEqual(lines_of(self.client.call({"path": "readings.csv", "rows": 4, "seed": 7})), [11, 14, 17, 21])
        self.assertEqual(lines_of(self.client.call({"path": "readings.csv", "rows": 4, "seed": 1})), [5, 9, 14, 26])

    def test_rows_keep_their_line_and_row_numbers(self):
        result = self.client.call({"path": "readings.csv", "group_by": "status", "per_group": 1, "seed": 3})
        by_id = {entry["values"]["reading_id"]: entry for entry in result["structuredContent"]["sample"]}
        self.assertEqual((by_id["R018"]["line"], by_id["R018"]["row"]), (19, 18))
        self.assertEqual(by_id["R018"]["values"]["note"], "no reading\nreceived")
        self.assertEqual((by_id["R015"]["line"], by_id["R015"]["row"]), (16, 15))

    def test_long_cells_are_cut_and_listed(self):
        result = self.client.call({"path": "readings.csv", "group_by": "status", "per_group": 1,
                                   "max_cell_chars": 20, "columns": ["reading_id", "note"]})
        sample = result["structuredContent"]
        self.assertEqual(sample["columns"], ["reading_id", "status", "note"])
        with (EXAMPLES / "readings.csv").open(encoding="utf-8", newline="") as stream:
            full = next(row["note"] for row in csv.DictReader(stream) if row["reading_id"] == "R015")
        self.assertEqual(sample["shortened_cells"], [{"line": 16, "column": "note", "chars": len(full)}])
        cut = next(entry for entry in sample["sample"] if entry["values"]["reading_id"] == "R015")
        self.assertEqual(cut["values"]["note"], full[:20])

    def test_small_file_returns_every_row(self):
        sample = self.client.call({"path": "readings.csv", "rows": 200})["structuredContent"]
        self.assertEqual(len(sample["sample"]), 24)
        self.assertEqual(sample["rows_read"], 24)

    def test_too_many_groups_is_refused(self):
        result = self.client.call({"path": "readings.csv", "group_by": "reading_id", "max_groups": 10})
        self.assertTrue(result["isError"])
        self.assertIn("max_groups", result["structuredContent"]["error"])

    def test_argument_mistakes_are_tool_errors(self):
        for arguments, word in (({"path": "readings.csv", "per_group": 2}, "group_by"),
                                ({"path": "readings.csv", "group_by": "site", "rows": 5}, "per_group"),
                                ({"path": "readings.csv", "group_by": "region"}, "region"),
                                ({"path": "readings.csv", "rows": 0}, "rows"),
                                ({"path": "readings.csv", "columns": ["temp"]}, "temp"),
                                ({"rows": 5}, "path")):
            result = self.client.call(arguments)
            self.assertTrue(result["isError"], arguments)
            self.assertIn(word, json.dumps(result["structuredContent"]))

    def test_paths_outside_the_root_are_refused(self):
        for path in ("../readings.csv", "/etc/hostname", "absent.csv", ".", "a/../readings.csv"):
            self.assertTrue(self.client.call({"path": path})["isError"], path)

    def test_sample_arguments_file_works(self):
        arguments = json.loads((EXAMPLES / "sample_csv_rows-arguments.json").read_text(encoding="utf-8"))
        result = self.client.call(arguments)
        self.assertFalse(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])


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

    def test_returned_row_limit_is_enforced(self):
        rows = ["group,value"] + [f"g{number // 10:02d},{number}" for number in range(600)]
        (self.root / "groups.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        client = self.start()
        refused = client.call({"path": "groups.csv", "group_by": "group", "per_group": 10, "max_groups": 60})
        self.assertTrue(refused["isError"])
        self.assertIn("500", refused["structuredContent"]["error"])
        allowed = client.call({"path": "groups.csv", "group_by": "group", "per_group": 2, "max_groups": 60})
        self.assertEqual(len(allowed["structuredContent"]["sample"]), 120)

    def test_known_wrong_escapes_cannot_push_an_answer_line_past_256_kib(self):
        # Each backslash takes two bytes in the structured copy and four in the escaped text copy.
        cells = "".join("\\" * 1990 + f"{row:010d}\n" for row in range(80))
        (self.root / "escapes.csv").write_text("v\n" + cells, encoding="utf-8")
        client = self.start()
        for rows, too_large in ((20, False), (30, True)):
            result = client.call({"path": "escapes.csv", "rows": rows, "max_cell_chars": 2000})
            self.assertLessEqual(len(client.last_line), 256 * 1024, rows)
            self.assertEqual(result["isError"], too_large, rows)
        self.assertIn("262144 byte limit", result["structuredContent"]["error"])

    def test_known_wrong_long_group_values_are_cut_and_the_hint_names_group_arguments(self):
        # Group values were never cut: 40 groups of 6,000-character values made a 495,115-byte answer, and the
        # refusal said to lower max_cell_chars, which did not help.
        rows = ["id,comment"] + [f"{number},c{number:02d}" + "z" * 6000 for number in range(40)]
        (self.root / "longgroups.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        client = self.start()
        grouped = {"path": "longgroups.csv", "group_by": "comment", "per_group": 1}
        result = client.call(grouped)
        self.assertFalse(result["isError"])
        self.assertLessEqual(len(client.last_line), 256 * 1024)
        answer = result["structuredContent"]
        self.assertEqual(len(answer["groups"]), 40)
        self.assertTrue(all(len(group["value"]) == 200 and group["chars"] == 6003 for group in answer["groups"]))
        self.assertTrue(any("group values" in note for note in answer["notes"]))
        narrow = client.call({**grouped, "max_cell_chars": 20})["structuredContent"]
        self.assertEqual({len(group["value"]) for group in narrow["groups"]}, {20})
        refused = client.call({**grouped, "max_cell_chars": 2000})
        self.assertTrue(refused["isError"])
        self.assertLessEqual(len(client.last_line), 256 * 1024)
        self.assertIn("max_groups", refused["structuredContent"]["error"])
        self.assertNotIn("Lower rows", refused["structuredContent"]["error"])

    def test_decoding_error_names_the_line(self):
        (self.root / "names.csv").write_bytes(b"name\nalpha\n\xe9t\xe9\n")
        client = self.start()
        refused = client.call({"path": "names.csv"})
        self.assertTrue(refused["isError"])
        self.assertIn("line 3", refused["structuredContent"]["error"])
        latin = client.call({"path": "names.csv", "encoding": "latin-1"})["structuredContent"]
        self.assertIn({"line": 3, "row": 2, "values": {"name": "été"}}, latin["sample"])


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
        self.assertIn("`sample_csv_rows`", text)
        self.assertIn("-s .baltor/csv-row-sampler-server/tests", text)
        self.assertIn("ending in `sample_csv_rows`", text)
        self.assertIn("never instructions", text)
        self.assertIn("OK means the server works but the harness did not start it", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
