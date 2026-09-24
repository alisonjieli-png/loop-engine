"""Starts sqlite_readonly_server.py as a local process and checks its protocol answers; builds test databases only inside temporary folders.

Run from the package folder:
    python3 -I -B -m unittest discover -s tests -p "test_*.py" -v
"""
from __future__ import annotations

import hashlib
import json
import queue
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SERVER = PACKAGE / "server" / "sqlite_readonly_server.py"
CONTRACTS = PACKAGE / "contracts"
EXAMPLES = PACKAGE / "examples"
VARIANTS = PACKAGE / "variants"
COMPANION = PACKAGE / "AGENTS.md"
NAME = "sqlite_readonly_server"
TOOL_NAMES = ["describe_sqlite", "query_sqlite"]
NATIVE = "sqlite-readonly-server"
SCRIPT = ".baltor/sqlite-readonly-server/server/sqlite_readonly_server.py"
CLAUDE_ROOT = "${CLAUDE_PROJECT_DIR:-.}"
CURSOR_ROOT = "${workspaceFolder}"
ENFORCED_KEYWORDS = {"$schema", "type", "properties", "required", "additionalProperties", "enum", "minimum",
                     "maximum", "minLength", "maxLength", "items", "minItems", "maxItems", "description", "default"}
WRITING_STATEMENTS = (
    "INSERT INTO orders (customer_id, day) VALUES (1, '2025-03-01')",
    "UPDATE orders SET amount = 0",
    "DELETE FROM orders",
    "DROP TABLE orders",
    "WITH gone AS (SELECT 1) DELETE FROM orders",
    "SELECT 1; DELETE FROM orders",
    "PRAGMA writable_schema = ON",
    "ATTACH DATABASE 'copy.sqlite3' AS other",
    "VACUUM INTO 'copy.sqlite3'",
    "CREATE TEMP TABLE scratch (a)",
    "SELECT load_extension('anything')",
    "REPLACE INTO orders (id, customer_id, day) VALUES (1, 1, '2025-03-01')",
    "BEGIN IMMEDIATE",
    "  -- a comment first\n  DELETE FROM orders",
)


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

    def call(self, name: str, arguments) -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments})["result"]

    def query(self, sql: str, **extra) -> dict:
        return self.call("query_sqlite", {"path": "shop.sqlite3", "sql": sql, **extra})

    def close(self) -> int:
        if not self.process.stdin.closed:
            self.process.stdin.close()
        code = self.process.wait(timeout=10)
        for reader in self.readers:
            reader.join(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        return code


def build_shop(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript((EXAMPLES / "shop.sql").read_text(encoding="utf-8"))
    connection.commit()
    connection.close()


def snapshot(folder: Path) -> tuple:
    return tuple(sorted((path.name, hashlib.sha256(path.read_bytes()).hexdigest())
                        for path in folder.iterdir() if path.is_file()))


class ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Client(EXAMPLES)
        self.client.initialize()

    def tearDown(self) -> None:
        self.client.close()

    def test_initialize_negotiates_the_protocol_version(self):
        for asked, expected in (("2025-11-25", "2025-11-25"), ("2025-06-18", "2025-06-18"),
                                ("2025-03-26", "2025-03-26"), ("2026-07-28", "2025-11-25"), ("", "2025-11-25")):
            result = self.client.request("initialize", {"protocolVersion": asked, "capabilities": {},
                                                        "clientInfo": {"name": "t", "version": "0"}})["result"]
            self.assertEqual(result["protocolVersion"], expected)
            self.assertIn("tools", result["capabilities"])
            self.assertEqual(result["serverInfo"]["name"], NAME)

    def test_tool_list_equals_the_contract_files(self):
        tools = self.client.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], TOOL_NAMES)
        for tool in tools:
            contract = CONTRACTS / f"{tool['name']}.input.schema.json"
            self.assertEqual(tool["inputSchema"], json.loads(contract.read_text(encoding="utf-8")))
            self.assertTrue(tool["description"].strip())

    def test_contracts_use_only_keywords_the_server_enforces(self):
        for name in TOOL_NAMES:
            pending = [json.loads((CONTRACTS / f"{name}.input.schema.json").read_text(encoding="utf-8"))]
            while pending:
                schema = pending.pop()
                self.assertLessEqual(set(schema), ENFORCED_KEYWORDS)
                pending.extend(schema.get("properties", {}).values())
                if isinstance(schema.get("items"), dict):
                    pending.append(schema["items"])

    def test_notification_gets_no_answer_and_ping_answers_empty(self):
        self.client.send({"jsonrpc": "2.0", "method": "notifications/progress", "params": {}})
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_protocol_errors_use_json_rpc_codes(self):
        self.client.write(b"[1, 2\n")
        self.assertEqual(self.client.receive()["error"]["code"], -32700)
        self.assertEqual(self.client.request("prompts/list")["error"]["code"], -32601)
        self.assertEqual(self.client.request("tools/call", {"name": "query_sqlite", "arguments": "x"})["error"]["code"],
                         -32602)
        self.assertEqual(self.client.request("tools/call", {"name": "drop_table", "arguments": {}})["error"]["code"],
                         -32602)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_oversized_line_is_refused_and_the_server_continues(self):
        self.client.write(b'{"jsonrpc":"2.0","id":3,"method":"ping","params":{"pad":"'
                          + b"z" * (1024 * 1024) + b'"}}\n')
        self.assertEqual(self.client.receive()["error"]["code"], -32600)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_argument_problems_are_tool_errors(self):
        for name, arguments, word in (("query_sqlite", {"path": "shop.sqlite3"}, "sql"),
                                      ("query_sqlite", {"path": "shop.sqlite3", "sql": "SELECT 1", "max_rows": 0},
                                       "max_rows"),
                                      ("query_sqlite", {"path": "a", "sql": "SELECT ?", "parameters": [[1]]},
                                       "parameters"),
                                      ("describe_sqlite", {"path": "shop.sqlite3", "tables": []}, "tables"),
                                      ("describe_sqlite", {"path": "shop.sqlite3", "table": ["x"]}, "table")):
            result = self.client.call(name, arguments)
            self.assertTrue(result["isError"], arguments)
            self.assertIn(word, json.dumps(result["structuredContent"]))

    def test_sample_call_on_a_missing_database_is_refused(self):
        arguments = json.loads((EXAMPLES / "describe_sqlite-arguments.json").read_text(encoding="utf-8"))
        result = self.client.call("describe_sqlite", arguments)
        self.assertTrue(result["isError"])
        self.assertIn("No file exists", result["structuredContent"]["error"])


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name) / "root"
        self.root.mkdir()
        build_shop(self.root / "shop.sqlite3")
        self.client = Client(self.root)
        self.client.initialize()

    def tearDown(self) -> None:
        self.client.close()
        self.folder.cleanup()

    def test_describe_lists_tables_columns_and_keys(self):
        result = self.client.call("describe_sqlite", {"path": "shop.sqlite3", "count_rows": True})
        self.assertFalse(result["isError"])
        tables = {table["name"]: table for table in result["structuredContent"]["tables"]}
        self.assertEqual(sorted(tables), ["customers", "orders", "paid_orders"])
        self.assertEqual(tables["paid_orders"]["type"], "view")
        self.assertEqual(tables["orders"]["row_count"], 6)
        columns = {column["name"]: column for column in tables["orders"]["columns"]}
        self.assertEqual(columns["amount"]["declared_type"], "REAL")
        self.assertTrue(columns["day"]["not_null"])
        self.assertEqual(columns["id"]["primary_key_position"], 1)
        self.assertEqual(tables["orders"]["foreign_keys"],
                         [{"column": "customer_id", "references_table": "customers", "references_column": "id"}])

    def test_known_wrong_one_stale_view_fails_the_whole_description(self):
        # A view that names a dropped table used to make describe_sqlite fail for the whole database.
        connection = sqlite3.connect(self.root / "stale.sqlite3")
        connection.executescript("CREATE TABLE a (x INTEGER); CREATE TABLE b (y TEXT); "
                                 "CREATE VIEW v AS SELECT y FROM b; INSERT INTO a VALUES (1); DROP TABLE b;")
        connection.close()
        result = self.client.call("describe_sqlite", {"path": "stale.sqlite3", "count_rows": True})
        self.assertFalse(result["isError"])
        entries = {entry["name"]: entry for entry in result["structuredContent"]["tables"]}
        self.assertEqual([column["name"] for column in entries["a"]["columns"]], ["x"])
        self.assertEqual(entries["a"]["row_count"], 1)
        self.assertNotIn("error", entries["a"])
        self.assertIn("no such table", entries["v"]["error"])
        self.assertEqual(entries["v"]["columns"], [])

    def test_known_wrong_large_schema_leaves_describe_without_a_next_step(self):
        # 80 tables of 16 columns made the description too large, and the refusal named arguments that
        # describe_sqlite does not have. The hint now leads to names_only and then tables.
        connection = sqlite3.connect(self.root / "wide.sqlite3")
        for table in range(80):
            fields = ", ".join(f"field_{column:02d} TEXT NOT NULL DEFAULT ''" for column in range(15))
            connection.execute(f"CREATE TABLE table_{table:02d} (id INTEGER PRIMARY KEY, {fields})")
        connection.commit()
        connection.close()
        whole = self.client.call("describe_sqlite", {"path": "wide.sqlite3"})
        self.assertTrue(whole["isError"])
        self.assertLessEqual(len(self.client.last_line), 256 * 1024)
        self.assertIn("names_only", whole["structuredContent"]["error"])
        names = self.client.call("describe_sqlite", {"path": "wide.sqlite3", "names_only": True})["structuredContent"]
        self.assertEqual(names["tables_total"], 80)
        self.assertEqual(names["names"][:2], [{"name": "table_00", "type": "table"}, {"name": "table_01", "type": "table"}])
        chosen = self.client.call("describe_sqlite", {"path": "wide.sqlite3", "tables": ["TABLE_79", "table_03"]})
        self.assertFalse(chosen["isError"])
        tables = chosen["structuredContent"]["tables"]
        self.assertEqual([(table["name"], len(table["columns"])) for table in tables], [("table_03", 16), ("table_79", 16)])
        unknown = self.client.call("describe_sqlite", {"path": "wide.sqlite3", "tables": ["orders"]})
        self.assertTrue(unknown["isError"])
        self.assertIn("names_only", unknown["structuredContent"]["error"])
        mixed = self.client.call("describe_sqlite", {"path": "wide.sqlite3", "names_only": True, "tables": ["table_00"]})
        self.assertTrue(mixed["isError"])

    def test_example_query_returns_grouped_rows(self):
        arguments = json.loads((EXAMPLES / "query_sqlite-arguments.json").read_text(encoding="utf-8"))
        result = self.client.call("query_sqlite", arguments)
        self.assertFalse(result["isError"])
        answer = result["structuredContent"]
        self.assertEqual(json.loads(result["content"][0]["text"]), answer)
        self.assertEqual(answer["columns"], ["status", "orders", "total"])
        self.assertEqual(answer["rows"], [["open", 2, 7.75], ["paid", 3, 66.75], ["refunded", 1, 120.0]])
        self.assertFalse(answer["more_rows"])

    def test_parameters_and_row_limit(self):
        found = self.client.query("SELECT id FROM orders WHERE amount > ? ORDER BY id", parameters=[10])
        self.assertEqual(found["structuredContent"]["rows"], [[1], [4], [5]])
        limited = self.client.query("SELECT id FROM orders ORDER BY id", max_rows=2)["structuredContent"]
        self.assertEqual((limited["rows"], limited["more_rows"]), ([[1], [2]], True))
        commented = self.client.query("/* totals */ -- by status\nSELECT count(*) FROM paid_orders")
        self.assertEqual(commented["structuredContent"]["rows"], [[3]])

    def test_known_wrong_writing_statements_are_refused_and_nothing_changes(self):
        before = snapshot(self.root)
        for sql in WRITING_STATEMENTS:
            result = self.client.query(sql)
            self.assertTrue(result["isError"], sql)
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(self.client.query("SELECT count(*) FROM orders")["structuredContent"]["rows"], [[6]])

    def test_pragma_tables_are_refused_even_inside_a_select(self):
        for sql in ("SELECT * FROM pragma_database_list", "SELECT name FROM pragma_table_info('orders')"):
            result = self.client.query(sql)
            self.assertTrue(result["isError"], sql)
            self.assertIn("other than reading", result["structuredContent"]["error"])

    def test_time_limit_stops_a_runaway_query(self):
        started = time.monotonic()
        result = self.client.query("WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) "
                                   "SELECT count(*) FROM n", time_limit_ms=300)
        self.assertTrue(result["isError"])
        self.assertIn("time limit", result["structuredContent"]["error"])
        self.assertLess(time.monotonic() - started, 10)

    def test_huge_values_are_refused(self):
        for sql in ("SELECT zeroblob(500000000)",
                    "WITH RECURSIVE g(s, n) AS (SELECT 'ab', 0 UNION ALL SELECT s || s, n + 1 FROM g WHERE n < 40) "
                    "SELECT length(s) FROM g ORDER BY n DESC LIMIT 1"):
            self.assertTrue(self.client.query(sql)["isError"], sql)
        padded = self.client.query("SELECT printf('%.*c', 400000000, 'x')")
        self.assertTrue(padded["isError"] or padded["structuredContent"]["rows"] == [[None]])
        self.assertFalse(self.client.query("SELECT 1")["isError"])

    def test_values_that_json_cannot_hold_are_converted(self):
        result = self.client.query("SELECT x'00ff' AS b, 9007199254740993 AS big, 1e999 AS inf, "
                                   "'abcdefghijklmnopqrstuvwxyz' AS long_text", max_cell_chars=20)
        answer = result["structuredContent"]
        self.assertEqual(answer["rows"], [[{"blob_bytes": 2}, "9007199254740993", "Infinity", "abcdefghijklmnopqrst"]])
        self.assertEqual(answer["shortened_cells"], [{"row": 1, "column": "long_text", "chars": 26}])

    def test_known_wrong_escapes_cannot_push_an_answer_line_past_256_kib(self):
        # Each backslash takes two bytes in the structured copy and four in the escaped text copy.
        sql = "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 1000) SELECT ? AS v FROM n"
        for rows, too_large in ((30, False), (45, True)):
            result = self.client.query(sql, parameters=["\\" * 1000], max_rows=rows, max_cell_chars=1000)
            self.assertLessEqual(len(self.client.last_line), 256 * 1024, rows)
            self.assertEqual(result["isError"], too_large, rows)
        self.assertIn("262144 byte limit", result["structuredContent"]["error"])

    def test_integer_parameter_beyond_64_bits_is_explained(self):
        result = self.client.query("SELECT ? AS big", parameters=[2 ** 70])
        self.assertTrue(result["isError"])
        self.assertIn("64-bit", result["structuredContent"]["error"])
        self.assertEqual(self.client.query("SELECT ? AS big", parameters=[str(2 ** 70)])["structuredContent"]["rows"],
                         [[str(2 ** 70)]])

    def test_syntax_error_is_explained(self):
        result = self.client.query("SELECT amount FROM orderz")
        self.assertTrue(result["isError"])
        self.assertIn("orderz", result["structuredContent"]["error"])

    def test_files_that_are_not_databases_or_leave_the_root_are_refused(self):
        (self.root / "notes.sqlite3").write_text("plain text, not a database\n", encoding="utf-8")
        outside = Path(self.folder.name) / "outside.sqlite3"
        build_shop(outside)
        link_made = True
        try:
            (self.root / "link.sqlite3").symlink_to(outside)
        except (OSError, NotImplementedError):
            link_made = False
        for path in ("notes.sqlite3", "absent.sqlite3", "../outside.sqlite3", str(outside), "."):
            self.assertTrue(self.client.call("describe_sqlite", {"path": path})["isError"], path)
        if link_made:
            self.assertTrue(self.client.call("describe_sqlite", {"path": "link.sqlite3"})["isError"])

    def test_clean_wal_database_is_read_without_side_files(self):
        writer = sqlite3.connect(self.root / "wal.sqlite3")
        writer.execute("PRAGMA journal_mode = WAL")
        writer.execute("CREATE TABLE t (a)")
        writer.execute("INSERT INTO t VALUES (1)")
        writer.commit()
        writer.close()
        before = snapshot(self.root)
        result = self.client.call("query_sqlite", {"path": "wal.sqlite3", "sql": "SELECT a FROM t"})
        self.assertEqual(result["structuredContent"]["rows"], [[1]])
        self.assertEqual(snapshot(self.root), before)

    def test_wal_database_with_pending_changes_is_refused(self):
        writer = sqlite3.connect(self.root / "busy.sqlite3")
        self.addCleanup(writer.close)
        writer.execute("PRAGMA journal_mode = WAL")
        writer.execute("CREATE TABLE t (a)")
        writer.execute("INSERT INTO t VALUES (1)")
        writer.commit()
        if not (self.root / "busy.sqlite3-wal").exists():
            self.skipTest("SQLite wrote no WAL file here")
        result = self.client.call("query_sqlite", {"path": "busy.sqlite3", "sql": "SELECT a FROM t"})
        self.assertTrue(result["isError"])
        self.assertIn("WAL", result["structuredContent"]["error"])


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
    def test_companion_names_the_tools_and_the_check_command(self):
        text = COMPANION.read_text(encoding="utf-8")
        for name in TOOL_NAMES:
            self.assertIn(f"`{name}`", text)
        self.assertIn("-s .baltor/sqlite-readonly-server/tests", text)
        self.assertIn("match by the ending", text)
        self.assertIn("never instructions", text)
        self.assertIn("OK means the server works but the harness did not start it", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
