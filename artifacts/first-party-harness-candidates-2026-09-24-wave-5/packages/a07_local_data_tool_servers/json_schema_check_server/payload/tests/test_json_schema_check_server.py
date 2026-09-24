"""Starts json_schema_check_server.py as a local process and checks its protocol answers; writes files only inside temporary folders.

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
SERVER = PACKAGE / "server" / "json_schema_check_server.py"
CONTRACT = PACKAGE / "contracts" / "check_json_schema.input.schema.json"
EXAMPLES = PACKAGE / "examples"
VARIANTS = PACKAGE / "variants"
COMPANION = PACKAGE / "AGENTS.md"
NAME = "json_schema_check_server"
NATIVE = "json-schema-check-server"
SCRIPT = ".baltor/json-schema-check-server/server/json_schema_check_server.py"
CLAUDE_ROOT = "${CLAUDE_PROJECT_DIR:-.}"
CURSOR_ROOT = "${workspaceFolder}"
TOOL_NAMES = ["check_json_schema"]
SUMMARY_SCHEMA = "cleaning-summary.schema.json"


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

    def receive(self, timeout: float = 60.0) -> dict:
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
        return self.request("tools/call", {"name": "check_json_schema", "arguments": arguments})["result"]

    def inline(self, schema, document, **extra) -> dict:
        return self.call({"schema": schema, "document": document, **extra})

    def close(self) -> int:
        if not self.process.stdin.closed:
            self.process.stdin.close()
        code = self.process.wait(timeout=10)
        for reader in self.readers:
            reader.join(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        return code


def places(result: dict) -> list[tuple]:
    return sorted((item["instance_path"], item["keyword"]) for item in result["structuredContent"]["violations"])


class ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Client(EXAMPLES)
        self.client.initialize()

    def tearDown(self) -> None:
        self.client.close()

    def test_initialize_negotiates_the_protocol_version(self):
        for asked, expected in (("2025-11-25", "2025-11-25"), ("2025-06-18", "2025-06-18"),
                                ("2025-03-26", "2025-03-26"), ("2026-07-28", "2025-11-25"), (None, "2025-11-25")):
            result = self.client.request("initialize", {"protocolVersion": asked, "capabilities": {},
                                                        "clientInfo": {"name": "t", "version": "0"}})["result"]
            self.assertEqual(result["protocolVersion"], expected)
            self.assertIn("tools", result["capabilities"])
            self.assertEqual(result["serverInfo"]["name"], NAME)

    def test_tool_list_equals_the_contract_file(self):
        tools = self.client.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["check_json_schema"])
        self.assertEqual(tools[0]["inputSchema"], json.loads(CONTRACT.read_text(encoding="utf-8")))
        self.assertTrue(tools[0]["description"].strip())

    def test_contract_uses_only_keywords_the_server_checks(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        result = self.client.inline(contract, {"document_path": "x.json", "schema_path": "y.json"})
        self.assertFalse(result["isError"], result["structuredContent"])
        self.assertTrue(result["structuredContent"]["valid"])

    def test_notification_gets_no_answer_and_ping_answers_empty(self):
        self.client.send({"jsonrpc": "2.0", "method": "notifications/roots/list_changed"})
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_protocol_errors_use_json_rpc_codes(self):
        self.client.write(b'{"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {"x": NaN}}\n')
        self.assertEqual(self.client.receive()["error"]["code"], -32700)
        self.assertEqual(self.client.request("completion/complete")["error"]["code"], -32601)
        self.assertEqual(self.client.request("tools/call", {"name": ["check_json_schema"]})["error"]["code"], -32602)
        self.assertEqual(self.client.request("tools/call", "text")["error"]["code"], -32602)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_oversized_line_is_refused_and_the_server_continues(self):
        self.client.write(b'{"jsonrpc":"2.0","id":4,"method":"ping","params":{"pad":"'
                          + b"q" * (1024 * 1024) + b'"}}\n')
        self.assertEqual(self.client.receive()["error"]["code"], -32600)
        self.assertEqual(self.client.request("ping")["result"], {})

    def test_sample_arguments_file_passes(self):
        arguments = json.loads((EXAMPLES / "check_json_schema-arguments.json").read_text(encoding="utf-8"))
        result = self.client.call(arguments)
        self.assertFalse(result["isError"])
        answer = result["structuredContent"]
        self.assertEqual(json.loads(result["content"][0]["text"]), answer)
        self.assertEqual((answer["valid"], answer["violation_count"], answer["schema"]["draft"]), (True, 0, "2020-12"))

    def test_known_wrong_document_reports_every_violation(self):
        result = self.client.call({"document_path": "cleaning-summary-wrong.json", "schema_path": SUMMARY_SCHEMA})
        self.assertFalse(result["isError"])
        self.assertFalse(result["structuredContent"]["valid"])
        self.assertEqual(places(result), sorted([
            ("/table", "pattern"), ("/rows_out", "type"), ("/rules/0/id", "pattern"), ("/rules/0/status", "enum"),
            ("/rules/1/column", "minLength"), ("/rules/1/changed", "minimum"), ("/held_rows/0", "required"),
            ("/finished_at", "format"), ("/notes", "additionalProperties")]))
        rule = next(item for item in result["structuredContent"]["violations"] if item["instance_path"] == "/rules/0/id")
        self.assertEqual(rule["schema_path"], "/properties/rules/items/$ref/properties/id/pattern")

    def test_violation_list_is_bounded_but_counted(self):
        answer = self.client.call({"document_path": "cleaning-summary-wrong.json", "schema_path": SUMMARY_SCHEMA,
                                   "max_violations": 2})["structuredContent"]
        self.assertEqual((len(answer["violations"]), answer["violation_count"], answer["more_violations"]),
                         (2, 9, True))

    def test_known_wrong_escapes_cannot_push_an_answer_line_past_256_kib(self):
        # Each backslash takes two bytes in the structured copy and four in the escaped text copy.
        for count, too_large in ((100, False), (150, True)):
            document = {"\\" * 190 + f"{index:010d}": index for index in range(count)}
            result = self.client.call({"schema": {"additionalProperties": False}, "document": document,
                                       "max_violations": 1000})
            self.assertLessEqual(len(self.client.last_line), 256 * 1024, count)
            self.assertEqual(result["isError"], too_large, count)
        self.assertIn("262144 byte limit", result["structuredContent"]["error"])

    def test_known_wrong_mistyped_keyword_is_refused_not_skipped(self):
        schema = {"type": "object", "properties": {"rows": {"type": "integer", "minimun": 1}}}
        refused = self.client.inline(schema, {"rows": 0})
        self.assertTrue(refused["isError"])
        unchecked = refused["structuredContent"]["unchecked"]
        self.assertEqual(unchecked[0]["schema_path"], "/properties/rows/minimun")
        self.assertIn("minimum", unchecked[0]["reason"])
        allowed = self.client.inline(schema, {"rows": 0}, allow_unchecked=True)["structuredContent"]
        self.assertTrue(allowed["valid"])
        self.assertEqual(allowed["unchecked"][0]["keyword"], "minimun")

    def test_combinations_and_constants(self):
        one_of = {"oneOf": [{"type": "integer"}, {"minimum": 0}]}
        self.assertEqual(places(self.client.inline(one_of, 3)), [("", "oneOf")])
        self.assertTrue(self.client.inline(one_of, -3)["structuredContent"]["valid"])
        any_of = self.client.inline({"anyOf": [{"type": "string"}, {"type": "null"}]}, 1)["structuredContent"]
        self.assertEqual(any_of["violations"][0]["keyword"], "anyOf")
        self.assertEqual(len(any_of["violations"][0]["alternatives"]), 2)
        self.assertEqual(places(self.client.inline({"not": {"type": "string"}}, "x")), [("", "not")])
        conditional = {"if": {"properties": {"kind": {"const": "paid"}}}, "then": {"required": ["amount"]},
                       "else": {"required": ["reason"]}}
        self.assertEqual(places(self.client.inline(conditional, {"kind": "paid"})), [("", "required")])
        self.assertEqual(places(self.client.inline(conditional, {"kind": "held", "reason": "x"})), [])
        self.assertEqual(places(self.client.inline({"const": 1}, True)), [("", "const")])
        self.assertEqual(places(self.client.inline({"uniqueItems": True}, [1, 1.0])), [("", "uniqueItems")])
        self.assertEqual(places(self.client.inline({"uniqueItems": True}, [1, True])), [])

    def test_decimal_multiple_of(self):
        self.assertTrue(self.client.inline({"multipleOf": 0.01}, 19.99)["structuredContent"]["valid"])
        self.assertFalse(self.client.inline({"multipleOf": 0.01}, 19.995)["structuredContent"]["valid"])

    def test_known_wrong_python_pattern_rules_pass_values_ecma_262_rejects(self):
        # With Python's re rules, $ also matched before a final line break, \S accepted no-break and ideographic
        # spaces and . accepted a carriage return, so these values passed although JSON Schema (ECMA-262) rejects them.
        def valid(pattern, value):
            result = self.client.inline({"type": "string", "pattern": pattern}, value)
            self.assertFalse(result["isError"], result["structuredContent"])
            return result["structuredContent"]["valid"]
        for pattern, value in (("^[0-9]{5}$", "12345\n"), ("^[A-Z]{2}$", "DE\n"), ("^\\S+$", "a\u00a0b"),
                               ("^\\S+$", "a\u3000b"), ("^a.b$", "a\rb"), ("^a.b$", "a\u2028b"),
                               ("^\\d+$", "\u0661\u0662"), ("^\\w+$", "\u00e9"), ("^\\s$", "\u200b"),
                               ("^[^\\S]$", "a")):
            self.assertFalse(valid(pattern, value), (pattern, value))
        for pattern, value in (("^[0-9]{5}$", "12345"), ("^a.b$", "axb"), ("^\\s$", "\ufeff"),
                               ("^\\s$", "\u00a0"), ("^[^\\S]+$", " \u00a0"), ("^[\\S\\s]+$", "a\nb"),
                               ("^\\cJ$", "\n"), ("^[^]$", "\n"), ("^\\u{1F600}$", "\U0001f600"),
                               ("^(?<year>[0-9]{4})$", "2025")):
            self.assertTrue(valid(pattern, value), (pattern, value))
        names = {"type": "object", "patternProperties": {"^x_[a-z]+$": {"type": "integer"}},
                 "additionalProperties": False}
        self.assertEqual(places(self.client.inline(names, {"x_ok": 1, "x_bad\n": 2})),
                         [("/x_bad\n", "additionalProperties")])

    def test_patterns_that_cannot_keep_their_meaning_are_refused(self):
        for pattern in ("\\p{L}", "(a)\\1", "(?i)abc", "(?P<n>a)", "a*+", "\\Aabc", "abc\\Z", "(?<=a+)b", "[a",
                        "\\k<n>"):
            result = self.client.inline({"pattern": pattern}, "abc")
            self.assertTrue(result["isError"], pattern)
            self.assertIn("pattern", result["structuredContent"]["schema_problems"][0], pattern)

    def test_known_wrong_unchecked_keyword_reached_through_a_reference(self):
        # The skip list was keyed by the path of the check, so a keyword listed as unchecked ran anyway when a
        # $ref led to it, and a remote $ref behind a local $ref stopped with an internal error.
        draft7 = {"$schema": "http://json-schema.org/draft-07/schema#",
                  "definitions": {"pair": {"type": "array", "prefixItems": [{"type": "string"}]}},
                  "properties": {"direct": {"type": "array", "prefixItems": [{"type": "string"}]},
                                 "viaref": {"$ref": "#/definitions/pair"}}}
        answer = self.client.inline(draft7, {"direct": [1], "viaref": [1]}, allow_unchecked=True)["structuredContent"]
        self.assertTrue(answer["valid"], answer["violations"])
        self.assertEqual(sorted(item["schema_path"] for item in answer["unchecked"]),
                         ["/definitions/pair/prefixItems", "/properties/direct/prefixItems"])
        remote = {"$defs": {"a": {"$ref": "other.json"}}, "properties": {"x": {"$ref": "#/$defs/a"}}}
        answer = self.client.inline(remote, {"x": 1}, allow_unchecked=True)
        self.assertFalse(answer["isError"], answer["structuredContent"])
        self.assertEqual([item["schema_path"] for item in answer["structuredContent"]["unchecked"]], ["/$defs/a/$ref"])
        hidden = {"examples": [{"type": "string", "pattern": "^a$"}], "$ref": "#/examples/0"}
        self.assertEqual(places(self.client.inline(hidden, "a\n")), [("", "pattern")])
        self.assertTrue(self.client.inline(hidden, "a")["structuredContent"]["valid"])

    def test_known_wrong_multiple_of_large_numbers(self):
        # Decimal arithmetic with 28 digits called 10**30 impossible to check against multipleOf 1.
        self.assertTrue(self.client.inline({"multipleOf": 1}, 10 ** 30)["structuredContent"]["valid"])
        self.assertEqual(places(self.client.inline({"multipleOf": 2}, 10 ** 30 + 1)), [("", "multipleOf")])
        self.assertTrue(self.client.inline({"multipleOf": 0.1}, 0.3)["structuredContent"]["valid"])
        self.assertTrue(self.client.inline({"multipleOf": 1e-308}, 1e308)["structuredContent"]["valid"])
        self.assertEqual(places(self.client.inline({"multipleOf": 0.1}, 0.35)), [("", "multipleOf")])

    def test_local_references_and_cycles(self):
        tree = {"$defs": {"node": {"type": "object", "required": ["v"], "properties": {
            "v": {"type": "integer"}, "kids": {"type": "array", "items": {"$ref": "#/$defs/node"}}}}},
            "$ref": "#/$defs/node"}
        self.assertEqual(places(self.client.inline(tree, {"v": 1, "kids": [{"v": 2, "kids": [{"v": "x"}]}]})),
                         [("/kids/0/kids/0/v", "type")])
        cycle = self.client.inline({"$ref": "#"}, 1)
        self.assertTrue(cycle["isError"])
        self.assertIn("circle", cycle["structuredContent"]["error"])
        nowhere = self.client.inline({"$ref": "#/$defs/missing"}, 1)
        self.assertTrue(nowhere["isError"])
        remote = self.client.inline({"$ref": "other.json#/a"}, 1)
        self.assertTrue(remote["isError"])
        self.assertEqual(remote["structuredContent"]["unchecked"][0]["keyword"], "$ref")

    def test_draft_07_tuple_items_and_reference_siblings(self):
        draft7 = "http://json-schema.org/draft-07/schema#"
        tuple_schema = {"$schema": draft7, "items": [{"type": "integer"}], "additionalItems": False}
        self.assertEqual(places(self.client.inline(tuple_schema, [1, 2])), [("/1", "false")])
        siblings = {"$schema": draft7, "definitions": {"a": {"type": "string"}}, "$ref": "#/definitions/a",
                    "maxLength": 1}
        refused = self.client.inline(siblings, "abc")
        self.assertTrue(refused["isError"])
        self.assertIn("ignores", refused["structuredContent"]["unchecked"][0]["reason"])
        self.assertTrue(self.client.inline({"$schema": "http://json-schema.org/draft-04/schema#"}, 1)["isError"])

    def test_formats_and_their_switch(self):
        schema = {"type": "object", "properties": {"day": {"format": "date"}, "id": {"format": "uuid"}}}
        document = {"day": "2025-02-30", "id": "not-a-uuid"}
        self.assertEqual(places(self.client.inline(schema, document)), [("/day", "format"), ("/id", "format")])
        self.assertTrue(self.client.inline(schema, document, check_formats=False)["structuredContent"]["valid"])
        self.assertTrue(self.client.inline({"format": "hostname"}, "x")["isError"])

    def test_schema_that_is_not_well_formed_is_refused(self):
        for schema in ({"type": "integr"}, {"minimum": "5"}, {"pattern": "("}, {"required": "name"},
                       {"items": [{"type": "string"}]}, {"allOf": []}):
            result = self.client.inline(schema, 1)
            self.assertTrue(result["isError"], schema)
            self.assertTrue(result["structuredContent"]["schema_problems"], schema)

    def test_argument_mistakes_are_tool_errors(self):
        for arguments, word in (({"schema": {}}, "document"), ({"document": 1}, "schema"),
                                ({"schema": {}, "document": 1, "document_path": "a.json"}, "exactly one"),
                                ({"schema": {}, "document": 1, "jsonl": True}, "jsonl"),
                                ({"schema": {}, "document": 1, "max_violations": 0}, "max_violations"),
                                ({"schema": 3, "document": 1}, "schema"),
                                ({"schema": {}, "document": 1, "strict": True}, "strict")):
            result = self.client.call(arguments)
            self.assertTrue(result["isError"], arguments)
            self.assertIn(word, json.dumps(result["structuredContent"]))

    def test_paths_outside_the_root_are_refused(self):
        for path in ("../cleaning-summary.json", "/etc/hostname", "absent.json", ".", "a/../x.json"):
            self.assertTrue(self.client.call({"document_path": path, "schema": True})["isError"], path)


class TemporaryFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name) / "root"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.folder.cleanup()

    def start(self, *extra: str) -> Client:
        client = Client(self.root, *extra)
        self.addCleanup(client.close)
        client.initialize()
        return client

    def test_json_lines_report_the_line_of_each_violation(self):
        (self.root / "rows.jsonl").write_text('{"id": 1}\n{"id": "two"}\n\n{"id": 4}\n', encoding="utf-8")
        answer = self.start().call({"document_path": "rows.jsonl", "jsonl": True,
                                    "schema": {"properties": {"id": {"type": "integer"}}}})["structuredContent"]
        self.assertEqual(answer["documents_checked"], 3)
        self.assertEqual([(item["line"], item["instance_path"]) for item in answer["violations"]], [(2, "/id")])

    def test_broken_documents_are_refused_with_a_reason(self):
        (self.root / "broken.jsonl").write_text('{"id": 1}\n{"id": 2,}\n', encoding="utf-8")
        (self.root / "twice.json").write_text('{"id": 1, "id": 2}\n', encoding="utf-8")
        (self.root / "nan.json").write_text('{"id": NaN}\n', encoding="utf-8")
        (self.root / "deep.json").write_text("[" * 200 + "]" * 200 + "\n", encoding="utf-8")
        client = self.start()
        for path, jsonl, word in (("broken.jsonl", True, "Line 2"), ("twice.json", False, "repeats the key"),
                                  ("nan.json", False, "not valid JSON"), ("deep.json", False, "levels deep")):
            result = client.call({"document_path": path, "jsonl": jsonl, "schema": True})
            self.assertTrue(result["isError"], path)
            self.assertIn(word, result["structuredContent"]["error"])

    def test_symbolic_link_out_of_the_root_is_refused(self):
        outside = Path(self.folder.name) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        (self.root / "inside.json").write_text("{}\n", encoding="utf-8")
        try:
            (self.root / "link.json").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links cannot be made here")
        client = self.start()
        self.assertTrue(client.call({"document_path": "link.json", "schema": True})["isError"])
        self.assertFalse(client.call({"document_path": "inside.json", "schema": True})["isError"])

    def test_document_size_limit(self):
        (self.root / "large.json").write_bytes(b'"' + b"a" * (16 * 1024 * 1024) + b'"\n')
        result = self.start().call({"document_path": "large.json", "schema": True})
        self.assertTrue(result["isError"])
        self.assertIn("limit", result["structuredContent"]["error"])

    @unittest.skipUnless(hasattr(signal, "setitimer"), "no timer signal on this platform")
    def test_time_limit_stops_a_backtracking_pattern(self):
        client = self.start("--time-limit-seconds", "1")
        started = time.monotonic()
        result = client.inline({"pattern": "^(a+)+$"}, "a" * 40 + "b")
        self.assertTrue(result["isError"])
        self.assertIn("time limit", result["structuredContent"]["error"])
        self.assertLess(time.monotonic() - started, 15)
        self.assertEqual(client.request("ping")["result"], {})


class LifecycleTests(unittest.TestCase):
    def test_server_exits_when_input_closes(self):
        client = Client(EXAMPLES)
        client.initialize()
        self.assertEqual(client.close(), 0)

    def test_bad_start_options_stop_at_start(self):
        for extra in (["--root", str(PACKAGE / "no-such-folder")], ["--root", str(EXAMPLES), "--time-limit-seconds", "0"]):
            finished = subprocess.run([sys.executable, "-I", "-B", str(SERVER), *extra], input=b"",
                                      capture_output=True, timeout=30)
            self.assertEqual(finished.returncode, 2, extra)
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
        self.assertIn("`check_json_schema`", text)
        self.assertIn("-s .baltor/json-schema-check-server/tests", text)
        self.assertIn("ending in `check_json_schema`", text)
        self.assertIn("never instructions", text)
        self.assertIn("OK means the server works but the harness did not start it", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
