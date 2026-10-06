"""The Claude Code OAuth check passes a service and a client that behave as the customer path needs, and names each
known-wrong case on its own step.

No network is reached. The service is a fake that answers the discovery, token and revocation addresses as the live
service does; Claude Code is a fake for the orchestration tests and, for the terminal driver, a small program run in
a real pseudo-terminal that prints what Claude Code 2.1.290 printed on October 5, 2026 and waits for the redirect at
its listener or its prompt. No fixture token appears in a record.

    PYTHONPATH=src:tools python -m unittest tools/test_check_quickstart_oauth.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import textwrap
import threading
import unittest
import unittest.mock
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_quickstart_oauth as oauth  # noqa: E402
import check_quickstarts as quickstarts  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://baltor.ai"
ENDPOINT = BASE + "/mcp"
SCOPES = ["provisioning:metadata", "provisioning:read", "usage:read"]
CHALLENGE_VALUE = "c" * 43
PASSWORD = "Qa-fixture-password-never-recorded"
CODE = "boac_" + "k" * 43
RECIPES = json.loads((ROOT / "src/loop_engine/core/service_runtime/web_assets/client-recipes.json").read_text("utf-8"))
#: What Claude Code 2.1.290 printed in a terminal, with the address as a hyperlink and in colour.
TRANSCRIPT = ('Starting authentication for "baltor"…\r\nVisit this URL to authorize:\r\n  \x1b]8;;{url}\x07\x1b[94m{url}'
              '\x1b[39m\x1b]8;;\x07\r\n\r\nWaiting for authorization… (^C to cancel)\r\n\x1b[1G\x1b[0J'
              'Or paste the redirect URL here: \x1b[33G')


def scratch():
    home = Path.home() / ".le-ci-tmp"
    return tempfile.TemporaryDirectory(dir=home if home.is_dir() else None)


def address(port=57853, **changes):
    query = {"response_type": "code", "client_id": "55b89515-0000-4000-8000-000000000000",
             "code_challenge": CHALLENGE_VALUE, "code_challenge_method": "S256",
             "redirect_uri": "http://localhost:{}/callback".format(port), "state": "s" * 43,
             "scope": " ".join(SCOPES), "resource": ENDPOINT, **changes}
    return BASE + "/authorize?" + urllib.parse.urlencode({key: value for key, value in query.items() if value is not None})


class Service(oauth.Http):
    """The live service's answers to the addresses this check reaches, without a network."""

    def __init__(self):
        super().__init__(opener=object())
        self.access, self.refresh, self.generation = "boat_" + "a" * 43, "bort_" + "r" * 43, 0
        self.revoked = False
        #: Known-wrong switches: an old refresh token still accepted, and a revocation that changes nothing.
        self.accept_reuse = False
        self.ineffective_revocation = False

    def request(self, method, url, *, json_body=None, form=None, headers=None):
        self.calls += 1
        path = urllib.parse.urlsplit(url).path
        token = ((headers or {}).get("Authorization") or "").removeprefix("Bearer ")
        if method == "GET" and path == "/api/v1/capabilities":
            return self.answer(200, {"record_type": "service_http_result/v1", "result": {
                "protocol": {"handshake_versions": ["2025-11-25"]},
                "authorization_server": {"resource": ENDPOINT, "available": True}}})
        if method == "GET" and path == quickstarts.RECIPES_ADDRESS:
            return self.answer(200, RECIPES)
        if method == "GET" and path == "/.well-known/oauth-protected-resource/mcp":
            return self.answer(200, {"resource": ENDPOINT, "authorization_servers": [BASE], "scopes_supported": SCOPES})
        if method == "GET" and path == "/.well-known/oauth-authorization-server":
            return self.answer(200, {"issuer": BASE, "code_challenge_methods_supported": ["S256"],
                                     "registration_endpoint": BASE + "/register", "token_endpoint": BASE + "/token",
                                     "token_endpoint_auth_methods_supported": ["none"], "scopes_supported": SCOPES,
                                     "grant_types_supported": ["authorization_code", "refresh_token"],
                                     "revocation_endpoint": BASE + "/revoke"})
        if method == "POST" and path == "/mcp":
            if not token:
                return 401, {"www-authenticate": 'Bearer resource_metadata="{}/.well-known/oauth-protected-resource/mcp"'.format(BASE)}, b"{}"
            return (200, {}, b"{}") if token == self.access and not self.revoked else (401, {}, b"{}")
        if method == "POST" and path == "/token":
            assert form["resource"] == ENDPOINT and form["grant_type"] == "refresh_token"
            if form["refresh_token"] == self.refresh and not self.revoked:
                self.generation += 1
                self.access, self.refresh = "boat_{:043d}".format(self.generation), "bort_{:043d}".format(self.generation)
                return self.answer(200, {"access_token": self.access, "refresh_token": self.refresh,
                                         "token_type": "Bearer", "expires_in": 900, "scope": " ".join(SCOPES)})
            if self.accept_reuse:
                return self.answer(200, {"access_token": self.access, "refresh_token": self.refresh})
            return self.answer(400, {"error": "invalid_grant"})
        if method == "POST" and path == "/revoke":
            self.revoked = self.revoked or (form["token"] == self.refresh and not self.ineffective_revocation)
            return 200, {}, b""
        return self.answer(404, {"error": "not_found"})

    @staticmethod
    def answer(status, value):
        return status, {}, json.dumps(value).encode()


class Harness:
    """A fake Claude Code for the orchestration: its configuration, its list and its login."""

    def __init__(self, service, folder, *, login_address=None, consented=None, listed_before="! Needs authentication"):
        self.service, self.folder, self.configured = service, folder, False
        self.signed_in, self.listed_before = False, listed_before
        self.login_address, self.consented = login_address or address(), consented
        self.commands = []

    def run_claude(self, claude, arguments, environment, cwd, timeout=120):
        self.commands.append(arguments)
        assert environment["CLAUDE_CONFIG_DIR"] == str(self.folder / oauth.CLAUDE_FOLDER)
        if arguments[:2] == ["mcp", "get"]:
            return (0, "baltor:\n  URL: " + ENDPOINT) if self.configured else (1, "No MCP server found with name: baltor")
        if arguments[:2] == ["mcp", "add"]:
            assert arguments[-2:] == ["--header", "Baltor-Step-Effects: reads_fs, writes_fs, spawns_process, network"]
            self.configured = True
            return 0, "Added HTTP MCP server baltor"
        if arguments[:2] == ["mcp", "list"]:
            status = "✔ Connected" if self.signed_in else self.listed_before
            return 0, "Checking MCP server health…\n\nbaltor: {} (HTTP) - {}\n".format(ENDPOINT, status)
        if arguments == ["--version"]:
            return 0, "2.1.290 (Claude Code)\n"
        return 1, ""

    def login(self, command, environment, cwd, answer, **_options):
        redirect = answer(self.login_address)
        store = self.folder / oauth.CLAUDE_FOLDER / ".credentials.json"
        store.write_text(json.dumps({"mcpOAuth": {"baltor|fixture": {
            "serverName": "baltor", "serverUrl": ENDPOINT, "accessToken": self.service.access,
            "refreshToken": self.service.refresh, "clientId": "55b89515-0000-4000-8000-000000000000"}}}))
        self.signed_in = True
        return {"exit": 0, "address": self.login_address, "redirect": redirect, "delivered_by": "listener",
                "text": "Authentication successful. Connected to baltor."}

    def consent(self, node, authorization, callback_prefix, account, evidence):
        if self.consented is not None:
            return self.consented
        state = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(authorization).query))["state"]
        return {"callback_url": callback_prefix + "?" + urllib.parse.urlencode({"code": CODE, "state": state, "iss": BASE}),
                "shown": {"client_name": "Claude Code (baltor)", "scopes": ["one", "two", "three"],
                          "destination": "http://localhost:57853/callback"}}


def protocol_rows(service, quickstart, capabilities, stamp):
    assert service._key == Harness.current.service.access, "the protocol steps use the token Claude Code holds"
    rows = [{"name": name, "passed": True, "detail": "fixture"} for name in
            ("connected", "listed", "searched", "downloaded", "digest_matches")]
    return rows, {"identity": "orient_on_a_task", "digest_prefix": "13c13dbc0592", "request_id": "quickstart-claude-code-x"}


def account_file(folder, **changes):
    state = {"record_type": oauth.JOURNEY_RECORD, "stage": "complete",
             "fresh": {"address": "baltor-check-fixture@inbox.invalid", "password": PASSWORD},
             "account": {"authentication_mode": "browser_identity", "tenant_id": "customer.fixture",
                         "entitlement": "bodies", "access_source": "founding_free_monthly"},
             "history": [{"event": "complete", "at": "2026-10-06T00:07:06.631Z"}], **changes}
    path = folder / oauth.ACCOUNT_FILE
    path.write_text(json.dumps(state))
    os.chmod(path, 0o600)
    return path


def check(folder, harness, *, create=False):
    Harness.current = harness
    with unittest.mock.patch.object(oauth, "run_claude", harness.run_claude), \
            unittest.mock.patch.object(quickstarts, "protocol_steps", protocol_rows):
        return oauth.run_check(BASE, folder, claude="claude", node="node", create=create, http=harness.service,
                               consent=harness.consent, login=harness.login)


def names(record):
    return [row["name"] for row in record["steps"]]


def step(record, name):
    return next(row for row in record["steps"] if row["name"] == name)


class OAuthCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = scratch()
        self.folder = Path(self.temporary.name) / "state"
        self.folder.mkdir(mode=0o700)
        account_file(self.folder)

    def tearDown(self):
        self.temporary.cleanup()

    def test_every_step_passes_for_a_client_and_service_that_follow_the_customer_path(self):
        harness = Harness(Service(), self.folder)
        record = check(self.folder, harness)
        self.assertTrue(record["passed"], json.dumps(record["steps"], indent=1))
        self.assertEqual(names(record), oauth.STEPS)
        self.assertEqual(record["client"]["client_id_prefix"], "55b89515")
        self.assertEqual(record["account"]["access_source"], "founding_free_monthly")
        self.assertTrue(harness.service.revoked, "the run leaves no live delegation")
        text = json.dumps(record)
        for secret in (PASSWORD, CODE, "s" * 43, CHALLENGE_VALUE, harness.service.access, harness.service.refresh,
                       "boat_" + "a" * 43, "bort_" + "r" * 43):
            self.assertNotIn(secret, text)
        self.assertEqual((record["physical_model_calls"], record["credential_printed"]), (0, False))

    def test_known_wrong_an_old_refresh_token_still_accepted_fails_refreshed_and_the_grant_is_still_revoked(self):
        service = Service()
        service.accept_reuse = True
        record = check(self.folder, Harness(service, self.folder))
        self.assertFalse(step(record, "refreshed")["passed"])
        self.assertTrue(step(record, "revoked")["passed"], "revocation runs after a failed step")
        self.assertFalse(record["passed"])

    def test_known_wrong_a_revocation_that_changes_nothing_fails_revoked(self):
        service = Service()
        service.ineffective_revocation = True
        record = check(self.folder, Harness(service, self.folder))
        revoked = step(record, "revoked")
        self.assertFalse(revoked["passed"])
        self.assertIn("answered 200 after revocation", revoked["detail"])

    def test_known_wrong_a_redirect_with_another_state_fails_consented_and_no_token_is_used(self):
        harness = Harness(Service(), self.folder, consented={
            "callback_url": "http://localhost:57853/callback?" + urllib.parse.urlencode(
                {"code": CODE, "state": "another", "iss": BASE}), "shown": {}})
        record = check(self.folder, harness)
        self.assertFalse(step(record, "consented")["passed"])
        self.assertIn("another state", step(record, "consented")["detail"])
        self.assertNotIn("claude_code_token_issued", names(record))
        self.assertNotIn(CODE, json.dumps(record))

    def test_known_wrong_a_redirect_naming_another_issuer_fails_consented(self):
        state = "s" * 43
        harness = Harness(Service(), self.folder, consented={
            "callback_url": "http://localhost:57853/callback?" + urllib.parse.urlencode(
                {"code": CODE, "state": state, "iss": "https://elsewhere.invalid"}), "shown": {}})
        self.assertIn("issuer", step(check(self.folder, harness), "consented")["detail"])

    def test_known_wrong_an_authorization_request_for_another_resource_fails_its_step(self):
        harness = Harness(Service(), self.folder, login_address=address(resource="https://app.baltor.ai/mcp"))
        record = check(self.folder, harness)
        requested = step(record, "claude_code_authorization_requested")
        self.assertFalse(requested["passed"])
        self.assertIn("resource", requested["detail"])
        self.assertNotIn("consented", names(record))

    def test_known_wrong_a_server_that_does_not_ask_for_authentication_fails_before_login(self):
        record = check(self.folder, Harness(Service(), self.folder, listed_before="✔ Connected"))
        self.assertFalse(step(record, "claude_code_needs_authentication")["passed"])
        self.assertNotIn("claude_code_authorization_requested", names(record))

    def test_without_an_account_the_check_says_how_to_make_one_and_makes_none(self):
        (self.folder / oauth.ACCOUNT_FILE).unlink()
        harness = Harness(Service(), self.folder)
        record = check(self.folder, harness)
        self.assertEqual(names(record), ["account_ready"])
        self.assertIn("--create-account", step(record, "account_ready")["detail"])
        self.assertEqual(harness.service.calls, 0)

    def test_known_wrong_an_account_that_is_not_a_completed_public_sign_up_is_refused(self):
        for changes in ({"stage": "signin_pending"}, {"fresh": {"address": "owner@baltor.ai", "password": PASSWORD}},
                        {"record_type": "staff_account/v1"}):
            with self.subTest(changes=changes):
                account_file(self.folder, **changes)
                record = check(self.folder, Harness(Service(), self.folder))
                self.assertFalse(step(record, "account_ready")["passed"])
                self.assertNotIn(PASSWORD, json.dumps(record))

    def test_the_state_folder_must_be_private_and_outside_the_repository(self):
        with self.assertRaises(oauth.CheckFailed):
            oauth.private_folder(ROOT / "artifacts")
        shared = Path(self.temporary.name) / "shared"
        shared.mkdir(mode=0o755)
        os.chmod(shared, 0o755)
        with self.assertRaises(oauth.CheckFailed):
            oauth.private_folder(shared)

    def test_the_authorization_address_checks_name_each_problem(self):
        request = oauth.check_authorization_address(address(), BASE, SCOPES)
        self.assertEqual(request["callback_prefix"], "http://localhost:57853/callback")
        for changes, reason in (({"code_challenge_method": "plain"}, "S256"), ({"resource": None}, "resource"),
                                ({"redirect_uri": "https://example.invalid/callback"}, "loopback"),
                                ({"scope": "provisioning:metadata access:manage"}, "scopes"),
                                ({"state": None}, "state"), ({"response_type": "token"}, "code")):
            with self.subTest(changes=changes), self.assertRaisesRegex(oauth.CheckFailed, reason):
                oauth.check_authorization_address(address(**changes), BASE, SCOPES)
        with self.assertRaisesRegex(oauth.CheckFailed, "published base"):
            oauth.check_authorization_address(address().replace(BASE, "https://app.baltor.ai"), BASE, SCOPES)

    def test_terminal_output_is_read_as_text_and_its_address_found_once(self):
        url = address()
        text = oauth.plain(TRANSCRIPT.format(url=url).encode())
        self.assertEqual(oauth.AUTHORIZATION_ADDRESS.findall(text), [url], "the hyperlink copy is removed with its codes")
        self.assertIn(oauth.PASTE_PROMPT, text.lower())
        self.assertNotIn("\x1b", text)

    def test_one_time_values_are_removed_before_anything_is_recorded(self):
        text = oauth.scrubbed("http://localhost:1/callback?code={}&state=abc&iss=x token {}".format(CODE, "boat_x"), "boat_x")
        self.assertNotIn(CODE, text)
        self.assertNotIn("state=abc", text)
        self.assertNotIn("boat_x", text)

    def test_the_list_status_of_the_server_is_read_from_its_own_line(self):
        listing = "Checking MCP server health…\n\nother: https://x.invalid/mcp (HTTP) - ✔ Connected\n" \
                  "baltor: https://baltor.ai/mcp (HTTP) - ! Needs authentication\n"
        self.assertEqual(oauth.server_status(listing, ENDPOINT), "! Needs authentication")
        self.assertIsNone(oauth.server_status("other: https://x.invalid/mcp (HTTP) - ✔ Connected", ENDPOINT))


FAKE_CLAUDE = textwrap.dedent('''
    import http.server, os, sys, threading, urllib.parse
    port, url, outcome = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    done = threading.Event()
    class Callback(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"Authentication successful")
            open(outcome, "w").write("listener " + urllib.parse.urlsplit(self.path).query); done.set()
    server = http.server.HTTPServer(("127.0.0.1", port), Callback)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    sys.stdout.write({transcript!r}.format(url=url)); sys.stdout.flush()
    def paste():
        line = sys.stdin.readline().strip()
        if line:
            open(outcome, "w").write("paste " + urllib.parse.urlsplit(line).query); done.set()
    threading.Thread(target=paste, daemon=True).start()
    done.wait(30)
    sys.stdout.write("\\r\\nAuthentication successful.\\r\\n"); sys.stdout.flush()
    server.shutdown()
''').format(transcript=TRANSCRIPT)


class TerminalDriverTests(unittest.TestCase):
    """drive_login against a program that behaves as Claude Code did in a real pseudo-terminal."""

    def setUp(self):
        self.temporary = scratch()
        self.folder = Path(self.temporary.name)
        (self.folder / "claude.py").write_text(FAKE_CLAUDE)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]
        self.url = address(port=self.port).replace("localhost", "127.0.0.1")
        self.outcome = self.folder / "outcome.txt"

    def tearDown(self):
        self.temporary.cleanup()

    def drive(self, answer, **options):
        command = [sys.executable, str(self.folder / "claude.py"), str(self.port), self.url, str(self.outcome)]
        return oauth.drive_login(command, {"PATH": os.environ.get("PATH", "")}, self.folder, answer, seconds=40, **options)

    def test_a_redirect_delivered_to_the_listener_completes_the_login(self):
        def answer(found):
            self.assertEqual(found, self.url, "the address is read whole from the terminal")
            callback = "http://127.0.0.1:{}/callback?code=c&state=s".format(self.port)
            urllib.request.urlopen(callback, timeout=10).read()
            return callback
        result = self.drive(answer)
        self.assertEqual((result["exit"], result["delivered_by"]), (0, "listener"))
        self.assertTrue(self.outcome.read_text().startswith("listener code=c"))

    def test_a_redirect_the_listener_never_received_is_pasted_at_the_prompt(self):
        result = self.drive(lambda found: "http://127.0.0.1:{}/callback?code=p&state=s".format(self.port),
                            listener_seconds=1)
        self.assertEqual((result["exit"], result["delivered_by"]), (0, "paste"))
        self.assertTrue(self.outcome.read_text().startswith("paste code=p"))

    def test_known_wrong_a_client_that_prints_no_prompt_gives_no_address(self):
        (self.folder / "claude.py").write_text("import sys\nsys.stdout.write('Unable to start authentication\\n')\nsys.exit(1)\n")
        called = []
        result = self.drive(lambda found: called.append(found))
        self.assertEqual((result["exit"], result["address"], called), (1, None, []))


if __name__ == "__main__":
    unittest.main()
