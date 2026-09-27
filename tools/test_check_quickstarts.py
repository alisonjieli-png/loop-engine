"""The quickstart check passes a service that answers as the pages say, and names each known-wrong answer.

A fixture service answers on this machine, in the shapes the live service uses: the direct interface for the
Pi extension and the Baltor Harness page, and the protocol endpoint, in event-stream frames, for Claude Code,
Codex and OpenCode. It serves the committed client recipes at the address the Get set up page reads them from.
Each known-wrong case changes one answer or one page and requires its named step to fail. No network is
reached, and the fixture key never appears in a record.

    PYTHONPATH=src:tools python -m unittest tools/test_check_quickstarts.py
"""
from __future__ import annotations

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_quickstarts as tool  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KEY = "le_fixture_key_that_must_never_be_recorded"
BODY = "# Review inputs\n\nRead every input once before you hand the work over.\n"
DIGEST = hashlib.sha256(BODY.encode("utf-8")).hexdigest()
IDENTITY = "review_inputs_before_handing_over"
VERSION = "2025-11-25"
TOOLS = ("provisioning_discover", "provisioning_list", "provisioning_manifest", "provisioning_read", "intelligence_search")
PUBLISHED_BASE = "https://baltor.ai"
RECIPES_FILE = ROOT / "src/loop_engine/core/service_runtime/web_assets/client-recipes.json"
PI_EXTENSION = ROOT / "src/loop_engine/core/service_runtime/web_assets/pi/baltor.ts"
HARNESS_PAGE = ROOT / "docs/guides/quickstart-baltor-harness.md"
#: A two-file package the protocol read delivers one file per page, as a small answer limit makes it do.
PACKAGE_FILES = (("SKILL.md", b"# Review inputs\n\nRead every input once before you hand the work over.\n",
                  "text/markdown", "skill_definition"),
                 ("assets/checklist.bin", b"\x00\x01\xffchecklist", "application/octet-stream", "skill_asset"))
PACKAGE_ROWS = [{"path": path, "digest": hashlib.sha256(data).hexdigest(), "size_bytes": len(data),
                 "media_type": media, "role": role} for path, data, media, role in PACKAGE_FILES]
PACKAGE_DOCUMENT = json.dumps({"record_type": "catalogue_package/v1", "files": PACKAGE_ROWS},
                              sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
PACKAGE_DIGEST = hashlib.sha256(PACKAGE_DOCUMENT).hexdigest()


def committed_recipes():
    """A fresh copy of the reviewed recipes the Get set up page shows, so a test can change one without leaking."""
    return json.loads(RECIPES_FILE.read_text(encoding="utf-8"))


class State:
    """What the fixture answers, with the one change a known-wrong case makes."""

    def __init__(self, **changes):
        self.wrong_digest = False
        self.no_search_tool = False
        self.refuse_session = False
        self.no_hits = False
        self.refuse_tool_calls = False
        self.json_protocol = False
        #: A tool that answers the bare retrieval or body record instead of the `service_http_result/v1` wrapper.
        self.bare_tool_answers = False
        #: A direct answer that is the bare session, retrieval or manifest record instead of the wrapper.
        self.bare_direct_answers = False
        #: The record type a direct answer is wrapped in; the live service uses `service_http_result/v1`.
        self.direct_wrapper_type = "service_http_result/v1"
        #: A search answer that says it loaded bodies, on both paths.
        self.loads_bodies = False
        #: The recipes record served at /assets/client-recipes.json, or None for an address that is not served.
        self.recipes = committed_recipes()
        #: A protocol answer whose event-stream frame holds text that is not JSON.
        self.garbled_protocol = False
        #: A download whose connection closes before any answer, as a cut-off proxy or a restarted Machine leaves it.
        self.drop_download = False
        #: A session answered with a redirect to a sign-in page instead of the session record.
        self.redirect_session = False
        #: Every body sent to the direct search and manifest addresses, in order, so a test can read what was asked.
        self.retrieval_requests = []
        self.manifest_requests = []
        #: The record type of the manifest answer; the served Pi extension refuses any other than version 3.
        self.manifest_record_type = "provisioning_manifest/v3"
        #: The protocol search offers a package, and the protocol read answers its files one page at a time.
        self.package_read = False
        #: One package file arrives with other bytes than its digest names.
        self.wrong_package_file = False
        #: The file_offset of every package page the protocol read was asked for, in order.
        self.package_offsets = []
        self.__dict__.update(changes)


def wrapped(operation, value):
    """The `service_http_result/v1` wrapper every live answer carries; its `result` holds the record."""
    return {"record_type": "service_http_result/v1", "operation": operation, "result": value,
            "execution": {"runtime_type": "Loop", "loop_id": "fixture-loop", "profile": "intelligence.search@1.0.0",
                          "mode": "deterministic", "model_calls": 0, "definition_digest": "0" * 64}}


def hit():
    return {"reference": {"identity": IDENTITY, "body_digest": DIGEST, "size_bytes": len(BODY.encode())},
            "size_bytes": len(BODY.encode()), "library_tier": "verified", "library_tier_label": "Verified",
            "body_allowed": True, "score": 1.0}


def capabilities():
    return {"record_type": "service_capabilities/v1",
            "protocol": {"transport": "streamable_http", "versions": [VERSION, "2026-07-28"],
                         "handshake_versions": [VERSION], "per_request_versions": ["2026-07-28"]},
            "library": {"served_items": 1},
            "retrieval": {"request_record_type": "service_retrieval_request/v2"},
            "delivery": {"inline_body_bytes": 16384, "download_bytes": 1048576,
                         "download_endpoint": "/api/v1/download", "body_format": "utf8_text"}}


class Handler(BaseHTTPRequestHandler):
    state: State = State()

    def log_message(self, *args):
        pass

    def _send(self, status, body=b"", content_type="application/json", headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, value, headers=None):
        self._send(status, json.dumps(value).encode(), headers=headers)

    def _refused(self, status, code):
        self._json(status, {"record_type": "service_http_error/v1", "error": {"code": code}})

    def _authorized(self):
        if self.headers.get("Authorization") != "Bearer " + KEY:
            self._refused(401, "unauthorized")
            return False
        return True

    def _direct(self, operation, value):
        """One direct answer, wrapped as the live service wraps it unless the case under test says otherwise."""
        if self.state.bare_direct_answers:
            return self._json(200, value)
        return self._json(200, {**wrapped(operation, value), "record_type": self.state.direct_wrapper_type})

    def do_GET(self):
        if self.path == "/assets/client-recipes.json":
            # A public file of the website, served without a key, as the live service serves it.
            if self.state.recipes is None:
                return self._refused(404, "route_unavailable")
            return self._json(200, self.state.recipes)
        if not self._authorized():
            return
        if self.path == "/api/v1/session":
            if self.state.redirect_session:
                return self._send(302, b"", "text/html", {"Location": "/sign-in"})
            if self.state.refuse_session:
                return self._refused(401, "unauthorized")
            return self._direct("session", {
                "record_type": "service_session/v1", "authentication_mode": "host_key",
                "principal": {"tenant_id": "fixture", "scopes": ["provisioning:metadata", "provisioning:read", "usage:read"]}})
        if self.path == "/api/v1/capabilities":
            return self._json(200, wrapped("capabilities", capabilities()))
        self._refused(404, "route_unavailable")

    def do_POST(self):
        if not self._authorized():
            return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/api/v1/retrieval":
            self.state.retrieval_requests.append(payload)
            if payload.get("record_type") != "service_retrieval_request/v2":
                return self._refused(400, "unsupported_version")
            return self._direct("retrieval", self._search(payload))
        if self.path == "/api/v1/provisioning":
            self.state.manifest_requests.append(payload)
            if payload.get("operation") != "manifest" or payload.get("identity") != IDENTITY:
                return self._refused(404, "item_unavailable")
            return self._direct("manifest", {
                "record_type": self.state.manifest_record_type, "identity": IDENTITY, "digest": DIGEST,
                "size_bytes": len(BODY.encode()), "body_allowed": True})
        if self.path == "/api/v1/download":
            if self.state.drop_download:
                self.close_connection = True
                return None
            if not payload.get("request_id"):
                return self._refused(400, "request_identity_required")
            if payload.get("identity") != IDENTITY:
                return self._refused(404, "item_unavailable")
            served = (BODY + "changed\n") if self.state.wrong_digest else BODY
            return self._send(200, served.encode(), "application/octet-stream", {
                "X-Content-SHA256": DIGEST, "X-Loop-Engine-Record-Type": "service_download/v1",
                "X-Loop-Engine-Library-Tier": "Verified"})
        if self.path == "/mcp":
            return self._protocol(payload)
        self._refused(404, "route_unavailable")

    def _search(self, payload):
        if payload.get("record_type") not in ("service_retrieval_request/v2", None):
            return {"record_type": "service_retrieval_result/v1", "hits": [], "bodies_loaded": False}
        return {"record_type": "service_retrieval_result/v1", "hits": [] if self.state.no_hits else [hit()],
                "bodies_loaded": bool(self.state.loads_bodies), "catalogue_release": "fixture"}

    def _protocol(self, message):
        method = message.get("method")
        if method == "notifications/initialized":
            return self._send(202)
        if self.state.garbled_protocol:
            return self._send(200, b"event: message\r\ndata: {not json\r\n\r\n", "text/event-stream")
        if method != "initialize" and self.headers.get("MCP-Protocol-Version") != VERSION:
            return self._json(400, {"jsonrpc": "2.0", "id": message.get("id"),
                                    "error": {"code": -32000, "message": "The MCP-Protocol-Version header is required"}})
        if method == "initialize":
            result = {"protocolVersion": VERSION, "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "fixture", "version": "1.0.0"}}
        elif method == "tools/list":
            names = [name for name in TOOLS if not (self.state.no_search_tool and name == "intelligence_search")]
            result = {"tools": [{"name": name, "inputSchema": {"type": "object"}} for name in names]}
        elif method == "tools/call":
            name, arguments = message["params"]["name"], message["params"].get("arguments") or {}
            if self.state.refuse_tool_calls:
                refused = {"record_type": "service_http_error/v1", "error": {"code": "insufficient_scope"}}
                result = {"content": [{"type": "text", "text": json.dumps(refused)}], "structuredContent": refused, "isError": True}
            elif name == "intelligence_search" and self.state.package_read:
                package_hit = {**hit(), "reference": {"identity": IDENTITY, "body_digest": PACKAGE_DIGEST,
                                                      "size_bytes": len(PACKAGE_DOCUMENT)},
                               "size_bytes": len(PACKAGE_DOCUMENT)}
                found = {"record_type": "service_retrieval_result/v1", "hits": [package_hit], "bodies_loaded": False,
                         "catalogue_release": "fixture"}
                output = wrapped("retrieval", found)
                result = {"content": [{"type": "text", "text": json.dumps(output)}], "structuredContent": output, "isError": False}
            elif name == "provisioning_read" and self.state.package_read and arguments.get("identity") == IDENTITY:
                offset = arguments.get("file_offset", 0)
                self.state.package_offsets.append(offset)
                path, data, media, role = PACKAGE_FILES[offset]
                if self.state.wrong_package_file and offset == 1:
                    data = data + b"changed"
                row = {"path": path, "digest": PACKAGE_ROWS[offset]["digest"], "size_bytes": PACKAGE_ROWS[offset]["size_bytes"],
                       "media_type": media, "role": role, "encoding": "base64",
                       "content": base64.b64encode(data).decode("ascii")}
                record = {"record_type": "provisioning_package_read/v1", "identity": IDENTITY, "digest": PACKAGE_DIGEST,
                          "size_bytes": len(PACKAGE_DOCUMENT), "metered": True,
                          "package": {"body_form": "package", "package_digest": PACKAGE_DIGEST, "files": PACKAGE_ROWS},
                          "selection": {"file_offset": offset}, "files": [row], "omitted": [],
                          "next_file_offset": offset + 1 if offset + 1 < len(PACKAGE_FILES) else None}
                output = wrapped("read", record)
                result = {"content": [{"type": "text", "text": json.dumps(output)}], "structuredContent": output, "isError": False}
            elif name == "intelligence_search":
                found = self._search({"record_type": "service_retrieval_request/v2", **arguments})
                output = found if self.state.bare_tool_answers else wrapped("retrieval", found)
                result = {"content": [{"type": "text", "text": json.dumps(output)}], "structuredContent": output, "isError": False}
            elif name == "provisioning_read" and arguments.get("identity") == IDENTITY and arguments.get("request_id"):
                served = (BODY + "changed\n") if self.state.wrong_digest else BODY
                body = {"record_type": "provisioning_body/v3", "identity": IDENTITY, "digest": DIGEST,
                        "size_bytes": len(BODY.encode()), "body": served, "metered": True, "library_tier_label": "Verified"}
                output = body if self.state.bare_tool_answers else wrapped("read", body)
                result = {"content": [{"type": "text", "text": json.dumps(output)}], "structuredContent": output, "isError": False}
            else:
                refused = {"record_type": "service_http_error/v1", "error": {"code": "item_unavailable"}}
                result = {"content": [{"type": "text", "text": json.dumps(refused)}], "structuredContent": refused, "isError": True}
        else:
            return self._json(400, {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32601, "message": "unknown"}})
        answer = {"jsonrpc": "2.0", "id": message.get("id"), "result": result}
        if self.state.json_protocol:
            return self._json(200, answer)
        frame = "event: message\r\ndata: " + json.dumps(answer) + "\r\n\r\n"
        self._send(200, frame.encode(), "text/event-stream")


class FixtureService:
    def __init__(self, state=None):
        Handler.state = state or State()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return "http://127.0.0.1:{}".format(self.server.server_address[1])

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def run(state=None, **changes):
    with FixtureService(state) as origin:
        return tool.run_all(origin, KEY, published_base=PUBLISHED_BASE, repository=ROOT, **changes)


def step(record, quickstart, name):
    row = next(row for row in record["quickstarts"] if row["id"] == quickstart)
    return next(item for item in row["steps"] if item["name"] == name)


def row(record, quickstart):
    return next(row for row in record["quickstarts"] if row["id"] == quickstart)


class QuickstartCheckTests(unittest.TestCase):
    def test_every_quickstart_passes_against_a_service_that_answers_as_the_pages_say(self):
        record = run()
        self.assertTrue(record["passed"], json.dumps(record["quickstarts"], indent=1))
        self.assertEqual(record["quickstarts_passed"], 5)
        self.assertEqual(record["usage_records_added"], 5)
        self.assertEqual(len(set(record["request_ids"])), 5, "each download uses a new request identity")
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertEqual(row(record, quickstart)["wire_path"], "protocol")
            self.assertTrue(step(record, quickstart, "digest_matches")["passed"])
        self.assertTrue(step(record, "pi", "manifest_matches")["passed"])
        self.assertEqual(row(record, "baltor-harness")["wire_path"], "direct")
        for quickstart in tool.QUICKSTARTS:
            self.assertTrue(step(record, quickstart.id, "page_matches_the_published_recipe")["passed"], quickstart.id)
        self.assertEqual((record["recipes_status"], record["recipes_record_type"]), (200, "website_client_recipes/v2"))
        self.assertEqual(record["recipes_reviewed_at"], committed_recipes()["reviewed_at"])
        self.assertFalse(record["body_text_kept"])
        self.assertNotIn(BODY, json.dumps(record))

    def test_the_protocol_answers_are_read_as_json_too(self):
        record = run(State(json_protocol=True))
        self.assertTrue(record["passed"], json.dumps(record["quickstarts"], indent=1))

    def test_the_record_names_the_catalogue_release_the_search_answered(self):
        record = run()
        self.assertEqual(record["catalogue_release"], "fixture")
        for quickstart in ("claude-code", "pi", "baltor-harness"):
            self.assertEqual(row(record, quickstart)["catalogue_release"], "fixture")

    def test_known_wrong_a_tool_answer_without_the_result_wrapper_fails_searched(self):
        # The first live run of September 26, 2026 read the hits off the wrapper and reported no hit. A tool
        # that answers the bare record is not the live service, and the step names the wrapper it expected.
        record = run(State(bare_tool_answers=True))
        self.assertFalse(record["passed"])
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(step(record, quickstart, "listed")["passed"])
            searched = step(record, quickstart, "searched")
            self.assertFalse(searched["passed"])
            self.assertIn("service_http_result/v1", searched["detail"])
            self.assertIsNone(row(record, quickstart)["request_id"], "nothing is downloaded after a failed search")
        for quickstart in ("pi", "baltor-harness"):
            self.assertTrue(row(record, quickstart)["passed"], "the direct interface is not affected")
        self.assertEqual(record["usage_records_added"], 2)

    def test_known_wrong_a_body_whose_digest_differs_fails_digest_matches_on_every_path(self):
        record = run(State(wrong_digest=True))
        self.assertFalse(record["passed"])
        for quickstart in ("claude-code", "codex", "opencode", "pi", "baltor-harness"):
            self.assertTrue(step(record, quickstart, "downloaded")["passed"])
            self.assertFalse(step(record, quickstart, "digest_matches")["passed"], quickstart)

    def test_a_package_read_is_followed_page_by_page_and_checked_file_by_file(self):
        state = State(package_read=True)
        record = run(state)
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(row(record, quickstart)["passed"], quickstart)
            self.assertIn("2 of 2 files in 2 pages", step(record, quickstart, "downloaded")["detail"])
        self.assertEqual(state.package_offsets, [0, 1] * 3, "each protocol quickstart asks for both pages")

    def test_known_wrong_a_package_file_with_other_bytes_fails_digest_matches(self):
        record = run(State(package_read=True, wrong_package_file=True))
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(step(record, quickstart, "downloaded")["passed"])
            failed = step(record, quickstart, "digest_matches")
            self.assertFalse(failed["passed"], quickstart)
            self.assertIn("assets/checklist.bin", failed["detail"])

    def test_known_wrong_a_tool_list_without_the_search_tool_fails_listed(self):
        record = run(State(no_search_tool=True))
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(step(record, quickstart, "connected")["passed"])
            listed = step(record, quickstart, "listed")
            self.assertFalse(listed["passed"])
            self.assertIn("intelligence_search", listed["detail"])
            self.assertFalse(row(record, quickstart)["passed"])
        self.assertTrue(row(record, "pi")["passed"], "the direct interface is not affected")

    def test_known_wrong_a_refused_session_fails_connected_and_downloads_nothing(self):
        record = run(State(refuse_session=True))
        for quickstart in ("pi", "baltor-harness"):
            connected = step(record, quickstart, "connected")
            self.assertFalse(connected["passed"])
            self.assertIn("401", connected["detail"])
            self.assertEqual([item["name"] for item in row(record, quickstart)["steps"]],
                             ["page_names_the_published_base", "page_documents_the_first_search",
                              "page_matches_the_published_recipe", "connected"])
        self.assertEqual(record["usage_records_added"], 3, "the three protocol paths still download")

    def test_known_wrong_a_direct_answer_without_the_result_wrapper_fails_connected(self):
        # Both paths answer the wrapper. A direct answer that is the bare record is not the live service either.
        record = run(State(bare_direct_answers=True))
        for quickstart in ("pi", "baltor-harness"):
            connected = step(record, quickstart, "connected")
            self.assertFalse(connected["passed"])
            self.assertIn("service_http_result/v1", connected["detail"])
            self.assertIsNone(row(record, quickstart)["request_id"])
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(row(record, quickstart)["passed"], "the protocol path is not affected")

    def test_known_wrong_a_direct_answer_in_another_wrapper_fails_connected(self):
        # A wrapper that carries a `result` under another record type is refused by its name, not only a bare record.
        record = run(State(direct_wrapper_type="service_result/v1"))
        for quickstart in ("pi", "baltor-harness"):
            connected = step(record, quickstart, "connected")
            self.assertFalse(connected["passed"])
            self.assertIn("'service_result/v1'", connected["detail"])
        self.assertEqual(record["usage_records_added"], 3, "only the three protocol paths download")

    def test_known_wrong_a_search_that_loaded_bodies_fails_searched_on_every_path(self):
        # A search never loads a body; an answer that says it did is not the documented search, on either path.
        record = run(State(loads_bodies=True))
        self.assertEqual(record["usage_records_added"], 0)
        for quickstart in tool.QUICKSTARTS:
            searched = step(record, quickstart.id, "searched")
            self.assertFalse(searched["passed"], quickstart.id)
            self.assertIn("loaded a body", searched["detail"])

    def test_known_wrong_a_search_with_no_hit_fails_searched_and_downloads_nothing(self):
        record = run(State(no_hits=True))
        self.assertFalse(record["passed"])
        self.assertEqual(record["usage_records_added"], 0)
        for quickstart in ("claude-code", "pi", "baltor-harness"):
            self.assertFalse(step(record, quickstart, "searched")["passed"])
            self.assertIsNone(row(record, quickstart)["request_id"])

    def test_known_wrong_a_connection_without_a_retrieval_is_not_a_pass(self):
        # Roadmap S-6.202: a check that reports connected without a retrieval must fail.
        record = run(State(refuse_tool_calls=True))
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(step(record, quickstart, "connected")["passed"])
            self.assertTrue(step(record, quickstart, "listed")["passed"])
            self.assertFalse(step(record, quickstart, "searched")["passed"])
            self.assertFalse(row(record, quickstart)["passed"])
        self.assertFalse(record["passed"])

    def test_known_wrong_a_snippet_naming_another_address_fails_the_page_step(self):
        # Roadmap S-6.202: a snippet that names an address other than the published base must fail a named check.
        page = (ROOT / "docs/guides/quickstart-claude-code.md").read_text(encoding="utf-8")
        changed = page.replace("https://baltor.ai/mcp", "https://app.baltor.ai/mcp")
        self.assertNotEqual(page, changed)
        record = run(page_texts={"claude-code": changed})
        found = step(record, "claude-code", "page_names_the_published_base")
        self.assertFalse(found["passed"])
        self.assertIn("https://app.baltor.ai/mcp", found["detail"])
        self.assertFalse(row(record, "claude-code")["passed"])
        self.assertTrue(row(record, "codex")["passed"])

    def test_known_wrong_a_page_that_drops_the_first_search_fails_its_page_step(self):
        page = (ROOT / "docs/guides/quickstart-pi.md").read_text(encoding="utf-8")
        record = run(page_texts={"pi": page.replace("`review inputs`", "`review the inputs`")})
        self.assertFalse(step(record, "pi", "page_documents_the_first_search")["passed"])

    def test_known_wrong_a_page_whose_configuration_differs_from_the_recipe_fails_its_page_step(self):
        # The Codex table is compared as the text Get set up renders, so one changed value fails it.
        page = (ROOT / "docs/guides/quickstart-codex.md").read_text(encoding="utf-8")
        changed = page.replace("tool_timeout_sec = 45", "tool_timeout_sec = 30")
        self.assertNotEqual(page, changed)
        record = run(page_texts={"codex": changed})
        found = step(record, "codex", "page_matches_the_published_recipe")
        self.assertFalse(found["passed"])
        self.assertIn("codex configuration", found["detail"])
        self.assertFalse(row(record, "codex")["passed"])
        self.assertTrue(row(record, "claude-code")["passed"])

    def test_known_wrong_a_json_value_of_another_type_fails_the_page_step(self):
        # `true` and `1` compare equal in Python; the page step compares the JSON text of both values instead.
        page = (ROOT / "docs/guides/quickstart-opencode.md").read_text(encoding="utf-8")
        changed = page.replace('"enabled": true', '"enabled": 1')
        self.assertNotEqual(page, changed)
        record = run(page_texts={"opencode": changed})
        self.assertFalse(step(record, "opencode", "page_matches_the_published_recipe")["passed"])

    def test_known_wrong_a_page_without_the_verification_command_fails_its_page_step(self):
        page = (ROOT / "docs/guides/quickstart-claude-code.md").read_text(encoding="utf-8")
        changed = page.replace("```bash\nclaude mcp list\n```", "```bash\nclaude mcp get baltor\n```")
        self.assertNotEqual(page, changed)
        record = run(page_texts={"claude-code": changed})
        found = step(record, "claude-code", "page_matches_the_published_recipe")
        self.assertFalse(found["passed"])
        self.assertIn("claude mcp list", found["detail"])

    def test_known_wrong_a_recipe_the_service_changed_fails_the_page_that_repeats_it(self):
        # The live Get set up page moved and the quickstart did not: the nightly check names the page that is behind.
        recipes = committed_recipes()
        opencode = next(recipe for recipe in recipes["recipes"] if recipe["id"] == "opencode")
        opencode["configuration"]["mcp"]["baltor"]["oauth"] = True
        record = run(State(recipes=recipes))
        self.assertFalse(step(record, "opencode", "page_matches_the_published_recipe")["passed"])
        for quickstart in ("claude-code", "codex", "pi", "baltor-harness"):
            self.assertTrue(row(record, quickstart)["passed"], quickstart)

    def test_known_wrong_a_service_that_publishes_no_recipes_fails_every_page_step(self):
        for recipes in (None, {**committed_recipes(), "record_type": "website_client_recipes/v1"}):
            with self.subTest(recipes=None if recipes is None else recipes["record_type"]):
                record = run(State(recipes=recipes))
                self.assertFalse(record["passed"])
                for quickstart in tool.QUICKSTARTS:
                    found = step(record, quickstart.id, "page_matches_the_published_recipe")
                    self.assertFalse(found["passed"])
                    self.assertIn("publishes no", found["detail"])

    def test_the_committed_pages_repeat_the_committed_recipes(self):
        # Checked on every push without the network: a recipe change that leaves a quickstart behind fails here.
        recipes = committed_recipes()
        for quickstart in tool.QUICKSTARTS:
            recipe = tool.published_recipe(recipes, quickstart.id)
            with self.subTest(quickstart=quickstart.id):
                self.assertIsNotNone(recipe)
                text = (ROOT / quickstart.page).read_text(encoding="utf-8")
                self.assertEqual(tool.recipe_disagreement(text, recipe, PUBLISHED_BASE + "/mcp"), "")

    def test_the_toml_text_is_the_table_the_get_set_up_page_renders(self):
        codex = tool.published_recipe(committed_recipes(), "codex")
        self.assertEqual(tool.toml_text(tool.filled(codex["configuration"], "https://baltor.ai/mcp")),
                         '[mcp_servers.baltor]\nurl = "https://baltor.ai/mcp"\n'
                         'bearer_token_env_var = "BALTOR_SERVICE_TOKEN"\nstartup_timeout_sec = 20\ntool_timeout_sec = 45')
        # Settings come before inner tables, a key that is not bare is quoted, and only a whole placeholder is filled.
        self.assertEqual(tool.toml_text({"a": {"x y": True, "inner": {"k": "{{ENDPOINT}}/v"}}, "top": 1}),
                         'top = 1\n\n[a]\n"x y" = true\n\n[a.inner]\nk = "{{ENDPOINT}}/v"')
        self.assertEqual(tool.filled({"url": "{{ENDPOINT}}", "list": ["{{ENDPOINT}}"]}, "E"), {"url": "E", "list": ["E"]})

    def test_the_committed_pages_name_the_published_base_and_the_first_search(self):
        for quickstart in tool.QUICKSTARTS:
            text = (ROOT / quickstart.page).read_text(encoding="utf-8")
            with self.subTest(page=quickstart.page):
                addresses = tool.snippet_addresses(text)
                self.assertTrue(any(address.startswith(PUBLISHED_BASE + "/") for address in addresses))
                self.assertEqual(tool.foreign_service_addresses(addresses, PUBLISHED_BASE), [])
                self.assertTrue(tool.documents_first_search(text))

    def test_addresses_outside_the_service_are_not_held_to_the_published_base(self):
        addresses = ["https://opencode.ai/config.json", "https://github.com/alisonjieli-png/loop-engine",
                     "https://baltor.ai/mcp", "https://app.baltor.ai/api/v1/session", "https://other.invalid/assets/pi/baltor.ts"]
        self.assertEqual(tool.foreign_service_addresses(addresses, PUBLISHED_BASE),
                         ["https://app.baltor.ai/api/v1/session", "https://other.invalid/assets/pi/baltor.ts"])

    def test_the_record_is_written_under_a_new_name_and_never_holds_the_credential(self):
        record = run()
        from datetime import datetime, timezone
        now = datetime(2026, 9, 26, 5, 40, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory(dir=Path.home() / ".le-ci-tmp" if (Path.home() / ".le-ci-tmp").is_dir() else None) as folder:
            first = tool.write_record(record, Path(folder), now)
            second = tool.write_record(record, Path(folder), now)
            self.assertEqual(first.name, "quickstart-check-2026-09-26.json")
            self.assertEqual(second.name, "quickstart-check-2026-09-26-2.json")
            text = first.read_text(encoding="utf-8")
            self.assertNotIn(KEY, text)
            self.assertEqual(json.loads(text)["record_type"], "quickstart_live_check/v1")
            self.assertFalse(json.loads(text)["credential_printed"])

    def test_a_refused_protocol_answer_is_scrubbed_of_the_credential(self):
        class Opener:
            """Answers the capabilities, then refuses everything and echoes the key back, as a broken proxy might."""

            def open(self, request, timeout=0):
                import io
                import urllib.error
                if request.full_url.endswith("/api/v1/capabilities"):
                    answer = io.BytesIO(json.dumps(wrapped("capabilities", capabilities())).encode())
                    answer.status, answer.headers = 200, {"Content-Type": "application/json"}
                    return answer
                raise urllib.error.HTTPError(request.full_url, 401, "refused", {"Content-Type": "application/json"},
                                             io.BytesIO(json.dumps({"error": {"code": "unauthorized", "echo": KEY}}).encode()))
        record = tool.run_all("https://fixture.invalid", KEY, published_base=PUBLISHED_BASE, repository=ROOT, opener=Opener())
        self.assertFalse(record["passed"])
        self.assertNotIn(KEY, json.dumps(record))
        self.assertIn("[credential suppressed]", step(record, "claude-code", "connected")["detail"])

    def test_the_protocol_reader_understands_event_stream_frames_and_errors(self):
        frame = b'event: message\r\ndata: {"jsonrpc":"2.0","id":"a","result":{"tools":[]}}\r\n\r\n'
        self.assertEqual(tool.protocol_result(200, "text/event-stream", frame, "a"), {"tools": []})
        self.assertEqual(tool.protocol_result(200, "application/json", b'{"jsonrpc":"2.0","id":"a","result":{"x":1}}', "a"), {"x": 1})
        with self.assertRaises(tool.StepFailed):
            tool.protocol_result(200, "application/json", b'{"jsonrpc":"2.0","id":"a","error":{"code":-32000,"message":"no"}}', "a")
        with self.assertRaises(tool.StepFailed):
            tool.protocol_result(200, "application/json", b'{"jsonrpc":"2.0","id":"other","result":{}}', "a")

    def test_known_wrong_an_unreachable_service_fails_every_quickstart_and_is_still_recorded(self):
        # A nightly run during an outage must leave a dated record that says so. Before this test the first
        # refused connection raised out of the check, so the run ended in a traceback and wrote no record.
        import socket
        from datetime import datetime, timezone
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        record = tool.run_all(f"http://127.0.0.1:{port}", KEY, published_base=PUBLISHED_BASE, repository=ROOT)
        self.assertFalse(record["passed"])
        self.assertEqual(record["quickstarts_passed"], 0)
        self.assertIsNone(record["capabilities_status"])
        self.assertIn("did not complete", record["capabilities_error"])
        self.assertIn("did not complete", record["recipes_error"])
        self.assertEqual((record["usage_records_added"], record["request_ids_not_confirmed"]), (0, []))
        for quickstart in tool.QUICKSTARTS:
            self.assertFalse(step(record, quickstart.id, "connected")["passed"], quickstart.id)
            self.assertFalse(step(record, quickstart.id, "page_matches_the_published_recipe")["passed"], quickstart.id)
        for quickstart in ("pi", "baltor-harness"):
            self.assertIn("GET /api/v1/session did not complete", step(record, quickstart, "connected")["detail"])
        self.assertNotIn(KEY, json.dumps(record))
        with tempfile.TemporaryDirectory(dir=Path.home() / ".le-ci-tmp" if (Path.home() / ".le-ci-tmp").is_dir() else None) as folder:
            path = tool.write_record(record, Path(folder), datetime(2026, 9, 26, 5, 40, tzinfo=timezone.utc))
            self.assertFalse(json.loads(path.read_text(encoding="utf-8"))["passed"])

    def test_known_wrong_a_protocol_answer_that_is_not_json_fails_connected(self):
        record = run(State(garbled_protocol=True))
        self.assertFalse(record["passed"])
        for quickstart in ("claude-code", "codex", "opencode"):
            connected = step(record, quickstart, "connected")
            self.assertFalse(connected["passed"])
            self.assertIn("not JSON", connected["detail"])
        for quickstart in ("pi", "baltor-harness"):
            self.assertTrue(row(record, quickstart)["passed"], "the direct interface is not affected")
        with self.assertRaises(tool.StepFailed):
            tool._tool_output({"content": [{"type": "text", "text": "not json"}]}, "intelligence_search")

    def test_known_wrong_a_download_cut_off_before_its_answer_fails_downloaded_and_is_not_confirmed(self):
        # The service may have recorded the unit before the connection closed, so the request identity is kept
        # as not confirmed instead of being counted as a usage record or as none.
        record = run(State(drop_download=True))
        self.assertFalse(record["passed"])
        for quickstart in ("pi", "baltor-harness"):
            downloaded = step(record, quickstart, "downloaded")
            self.assertFalse(downloaded["passed"])
            self.assertIn("POST /api/v1/download did not complete", downloaded["detail"])
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(row(record, quickstart)["passed"], "the protocol path is not affected")
        self.assertEqual(record["usage_records_added"], 3)
        self.assertEqual(sorted(record["request_ids_not_confirmed"]),
                         sorted(row(record, quickstart)["request_id"] for quickstart in ("pi", "baltor-harness")))

    def test_known_wrong_a_redirected_session_is_refused_not_followed(self):
        record = run(State(redirect_session=True))
        for quickstart in ("pi", "baltor-harness"):
            connected = step(record, quickstart, "connected")
            self.assertFalse(connected["passed"])
            self.assertIn("redirect_refused", connected["detail"])
        for quickstart in ("claude-code", "codex", "opencode"):
            self.assertTrue(row(record, quickstart)["passed"], "the protocol path is not affected")

    def test_known_wrong_each_direct_path_sends_the_search_its_own_client_sends(self):
        # The Pi extension searches in the mode its source names and asks for a manifest by identity alone; the
        # Baltor Harness page's curl command is sent as the page shows it. Before this test both paths sent one
        # lexical search of five results, so a broken hybrid search on the live service passed the Pi quickstart.
        extension = PI_EXTENSION.read_text(encoding="utf-8")
        self.assertEqual(tool.EXTENSION_SEARCH_MODE, re.search(r'const SEARCH_MODE = "([^"]+)";', extension).group(1))
        self.assertEqual(tool.MANIFEST_RECORD, re.search(r'const MANIFEST_RECORD = "([^"]+)";', extension).group(1))
        state = State()
        record = run(state)
        self.assertTrue(record["passed"], json.dumps(record["quickstarts"], indent=1))
        documented = tool.documented_request(HARNESS_PAGE.read_text(encoding="utf-8"), "/api/v1/retrieval")
        self.assertEqual(documented["query"], tool.QUERY)
        self.assertIn(documented, state.retrieval_requests, "the page's own search request is sent unchanged")
        self.assertEqual([request["mode"] for request in state.retrieval_requests].count(tool.EXTENSION_SEARCH_MODE), 1)
        self.assertEqual([sorted(request) for request in state.manifest_requests], [["identity", "operation", "record_type"]])

    def test_known_wrong_a_manifest_of_another_version_fails_manifest_matches(self):
        record = run(State(manifest_record_type="provisioning_manifest/v2"))
        shown = step(record, "pi", "manifest_matches")
        self.assertFalse(shown["passed"])
        self.assertIn("provisioning_manifest/v3", shown["detail"])
        self.assertIsNone(row(record, "pi")["request_id"], "nothing is downloaded after a refused manifest")
        self.assertTrue(row(record, "baltor-harness")["passed"], "the page's curl path reads no manifest")

    def test_known_wrong_a_page_whose_search_request_names_another_version_fails_searched(self):
        page = HARNESS_PAGE.read_text(encoding="utf-8")
        wrong = page.replace('"record_type":"service_retrieval_request/v2"', '"record_type":"service_retrieval_request/v9"')
        self.assertNotEqual(page, wrong)
        record = run(page_texts={"baltor-harness": wrong})
        searched = step(record, "baltor-harness", "searched")
        self.assertFalse(searched["passed"])
        self.assertIn("400", searched["detail"])
        self.assertTrue(row(record, "pi")["passed"], "the extension path does not read the page's command")

    def test_known_wrong_a_page_whose_download_drops_the_expected_digest_fails_downloaded_before_sending(self):
        page = HARNESS_PAGE.read_text(encoding="utf-8")
        wrong = page.replace(',"expected_digest":"SELECTED-DIGEST"', "")
        self.assertNotEqual(page, wrong)
        record = run(page_texts={"baltor-harness": wrong})
        downloaded = step(record, "baltor-harness", "downloaded")
        self.assertFalse(downloaded["passed"])
        self.assertIn("expected_digest", downloaded["detail"])
        self.assertIsNone(row(record, "baltor-harness")["request_id"], "a request the page cannot bind is never sent")
        self.assertEqual(record["request_ids_not_confirmed"], [])

    def test_main_refuses_an_origin_that_is_not_https(self):
        with self.assertRaises(SystemExit) as refused:
            tool.main(["--origin", "http://127.0.0.1:8080"])
        self.assertEqual(refused.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
