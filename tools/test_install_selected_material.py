"""Checks for tools/install_selected_material.py against a real local service.

The service is the loopback HTTP fixture with durable records. The client is a
small fixture program that lists skills the way OpenCode 1.17.9 and 1.18.31
were observed to list them. No model turn, provider call or external network
request happens. One optional check asks the real client binary for its
listing only.

MutantControls removes one guard at a time in memory and requires that the
named check of that guard then fails. The MUTANTS table lists every guard that
has such a control. Source files are never changed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import install_selected_material as tool  # noqa: E402
from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, KINDS, item_from_body  # noqa: E402
from loop_engine.core.provisioning_server import (  # noqa: E402
    ProvisioningError, ProvisioningGrant, ProvisioningItemBinding,
)
from loop_engine.core.service_runtime.http import ServiceHttpApplication  # noqa: E402
from loop_engine.core.service_runtime.http_auth import ServiceHttpAuthentication  # noqa: E402
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http  # noqa: E402
from loop_engine.core.service_runtime.provisioning import DurableProvisioningBinding  # noqa: E402
from loop_engine.core.service_runtime.records import TenantKeyIssue  # noqa: E402

KEY_VARIABLE = "NATIVE_INSTALL_FIXTURE_KEY"
HOSTILE_IDENTITY = "../../outside/evil"
REVIEW_BODY = "# Review inputs\n\nRead every input file before use.\r\nKeep this line ending.\n\n---\nname: inner\n---\n"
BODIES = {
    "skill.alpha": "APPROVED_ALPHA_BODY", "skill.beta": "PRIVATE_BETA_BODY",
    "skill.candidate": "UNAPPROVED_CANDIDATE_BODY", "skill.large": "LARGE_BODY_" * 2048,
    "skill.review_inputs": REVIEW_BODY, HOSTILE_IDENTITY: "HOSTILE_IDENTITY_BODY",
}

FAKE_CLIENT = '''#!{python}
"""Fixture client: lists project skills in the observed listing format."""
import json
import os
from pathlib import Path
import sys
import time

here = Path(__file__).resolve().parent
behaviour = json.loads((here / "behaviour.json").read_text())
with (here / "invocations.jsonl").open("a") as stream:
    stream.write(json.dumps({{"arguments": sys.argv[1:], "cwd": os.getcwd(),
                             "watched_variable_present": behaviour["watched_variable"] in os.environ,
                             "settings_present": "OPENCODE_CONFIG_CONTENT" in os.environ}}) + "\\n")
if sys.argv[1:] == ["--version"]:
    print(behaviour.get("version", "0.0.0"))
    sys.exit(0)
if "run" in sys.argv[1:]:
    sys.exit(97)
mode, names = behaviour["mode"], behaviour.get("names", [])
if mode == "fail":
    sys.exit(3)
if mode == "hang":
    time.sleep(60)
for relative in behaviour.get("creates", []):
    (Path.cwd() / relative).write_text("written by the client process\\n")
entries = [{{"name": "built-in", "description": "fixture", "location": "<built-in>", "content": "x"}}]
if mode == "nul_location":
    entries.append({{"name": "hostile", "description": "fixture",
                     "location": "/absent/" + chr(0) + "/SKILL.md", "content": "x"}})
for path in sorted(Path.cwd().glob(".opencode/skills/*/SKILL.md")):
    text = path.read_bytes().decode("utf-8")
    end = text.find("\\n---\\n", 4)
    name = json.loads([line[6:] for line in text[4:end].splitlines() if line.startswith("name: ")][0])
    content = text[end + 5:]
    if mode == "omit" and name in names:
        continue
    if mode == "alter" and name in names:
        content += "ALTERED"
    if mode == "rename" and name in names:
        name = "another-name"
    if mode == "surrogate_name" and name in names:
        name = chr(0xd800) + "-name"
    if mode == "rewrite" and name in names:
        path.write_text(text + "REWRITTEN BY THE CLIENT PROCESS\\n")
    entries.append({{"name": name, "description": "fixture", "location": str(path.resolve()), "content": content}})
rendered = "[" * 60000 + "]" * 60000 if mode == "deep" else json.dumps(entries)
sys.stdout.write(rendered[:len(rendered) // 2] if mode == "cut" else rendered)
'''


def write_fake_client(folder: Path) -> Path:
    folder.mkdir()
    program = folder / "fixture-client"
    program.write_text(FAKE_CLIENT.format(python=sys.executable))
    program.chmod(0o755)
    set_client_behaviour(program, "discover")
    return program


def set_client_behaviour(program: Path, mode: str, names=(), version="1.18.31", creates=()) -> None:
    (program.parent / "behaviour.json").write_text(json.dumps(
        {"mode": mode, "names": list(names), "version": version, "creates": list(creates),
         "watched_variable": KEY_VARIABLE}))


def client_invocations(program: Path) -> list:
    log = program.parent / "invocations.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def add_item(fixture, identity: str, kind: str, body: str, source_layer="context_intelligence") -> None:
    item = item_from_body(HarnessIntelligenceDraft(identity, kind, "Alpha reference " + identity, source_layer,
                                                   "fixture:" + identity + "/v1", "MIT"), body)
    fixture.catalogue.register(item)
    fixture.bodies[identity] = body
    fixture.bindings[identity] = ProvisioningItemBinding.from_item(item)


def grant(fixture, identities, *, body_allowed=True, tenant="alpha") -> None:
    fixture.runtime.set_grants(tenant, tuple(ProvisioningGrant(tenant, fixture.bindings[identity], body_allowed)
                                             for identity in identities))


class TamperingProvisioning(DurableProvisioningBinding):
    """The real binding, with one change to the body read result after the service verified it."""

    def __init__(self, fixture, change):
        super().__init__(fixture.runtime, fixture.catalogue, fixture.provisioning.qualification_resolver,
                         fixture.provisioning.body_reader)
        self.change = change

    def invoke_for_principal(self, principal, operation, **fields):
        value = super().invoke_for_principal(principal, operation, **fields)
        return self.change(value) if operation == "read" else value


def tampered_service(fixture, change):
    return lambda configuration: ServiceHttpApplication(
        fixture.runtime, TamperingProvisioning(fixture, change), configuration, ServiceHttpAuthentication())


def same_length_other_text(value):
    other = value["body"].swapcase()
    return {**value, "body": other, "digest": hashlib.sha256(other.encode()).hexdigest()}


def refuse_the_read(_value):
    raise ProvisioningError("body disclosure is not authorized", "body_forbidden")


class UnsupportedCapabilities(ServiceHttpApplication):
    def capabilities(self):
        return {**super().capabilities(), "api_version": "v2"}


def files_under(folder: Path) -> list:
    return sorted(str(path.relative_to(folder)) for path in folder.rglob("*"))


@contextmanager
def recording_server(respond):
    """A loopback server that records what reaches it and whether a credential came with it."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def _handle(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            seen.append({"method": self.command, "path": self.path,
                         "carried_authorization": "Authorization" in self.headers})
            respond(self)

        do_GET = do_POST = _handle

        def log_message(self, *_arguments):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_port, seen
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)


def answer(handler, status: int, data: bytes = b"{}", location: str = "") -> None:
    handler.send_response(status)
    if location:
        handler.send_header("Location", location)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def write_protection_observed() -> bool:
    """True when a folder without the write permission really refuses a new file here.

    A process that may write anywhere, for example the machine administrator,
    cannot show the refusal, so the checks that need it are skipped instead of
    passing for the wrong reason.
    """
    folder = Path(tempfile.mkdtemp(prefix="native-install-probe-"))
    inner = folder / "closed"
    try:
        inner.mkdir(0o555)
        try:
            (inner / "file").write_text("x")
            return False
        except OSError:
            return True
    finally:
        inner.chmod(0o755)
        shutil.rmtree(folder, ignore_errors=True)


WRITE_PROTECTION_OBSERVED = write_protection_observed()

# ---------------------------------------------------------------------------
# A service under the check's own control
#
# The real local service answers correctly, so it cannot show what the tool
# does with a faulty or hostile answer. These responses are written here and
# served from the loopback address only. No provider or external host is used.
# ---------------------------------------------------------------------------

SCRIPTED_IDENTITY = "skill.scripted"
SCRIPTED_BODY = b"Scripted body.\n"
SCRIPTED_DIGEST = hashlib.sha256(SCRIPTED_BODY).hexdigest()
CONNECTION_CLOSED_ERRORS = {"BrokenPipeError", "ConnectionResetError", "OSError", "TimeoutError"}


def scripted_capabilities(**delivery_changes) -> dict:
    delivery = {"download_endpoint": tool.DOWNLOAD_ROUTE, "body_format": tool.SUPPORTED_BODY_FORMAT,
                "download_bytes": 64 * 1024 * 1024}
    delivery.update(delivery_changes)
    return {"record_type": tool.CAPABILITIES_RECORD_TYPE, "api_version": tool.SUPPORTED_API_VERSION,
            "delivery": delivery}


def scripted_manifest(**changes) -> dict:
    value = {"record_type": tool.MANIFEST_RECORD_TYPE, "identity": SCRIPTED_IDENTITY, "kind": "skill",
             "purpose": "Scripted purpose", "digest": SCRIPTED_DIGEST, "size_bytes": len(SCRIPTED_BODY),
             "license": "MIT", "body_allowed": True, "source_layer": "context_intelligence",
             "source_ref": "fixture:scripted/v1", "qualification_basis": "host_attested"}
    value.update(changes)
    return value


def scripted_result(value: dict) -> bytes:
    return json.dumps({"record_type": tool.RESULT_VERSION, "result": value}).encode("utf-8")


def served_body(handler, data: bytes, digest: str, record_type: str) -> None:
    handler.send_response(200)
    handler.send_header(tool.RECORD_TYPE_HEADER, record_type)
    handler.send_header(tool.DIGEST_HEADER, digest)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class ScriptedService:
    """One scripted answer for each route, and what the tool sent to get it."""

    def __init__(self, **script):
        self.capabilities = script.get("capabilities", scripted_capabilities())
        self.manifest = script.get("manifest", scripted_manifest())
        self.raw_manifest = script.get("raw_manifest")
        self.hits = script.get("hits", [])
        self.retrieval = script.get("retrieval")
        self.download = script.get("download")
        self.watched_report = script.get("watched_report")
        self.seen = []
        self.report_when_asked = {}
        self.handler_errors = []

    def retrieval_result(self) -> dict:
        if self.retrieval is not None:
            return self.retrieval
        return {"record_type": tool.RETRIEVAL_RESULT_RECORD_TYPE, "bodies_loaded": False, "hits": self.hits}

    def record(self, path: str) -> None:
        self.seen.append(path)
        if self.watched_report is not None and self.watched_report.exists():
            text = self.watched_report.read_text()
            self.report_when_asked[path] = json.loads(text) if text.strip() else None


@contextmanager
def running_script(service: ScriptedService):
    """Serve the scripted answers on a loopback port for the length of one check."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def do_GET(self):
            service.record(self.path)
            answer(self, 200, scripted_result(service.capabilities))

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            service.record(self.path)
            if self.path == tool.RETRIEVAL_ROUTE:
                return answer(self, 200, scripted_result(service.retrieval_result()))
            if self.path == tool.PROVISIONING_ROUTE:
                return answer(self, 200, service.raw_manifest or scripted_result(service.manifest))
            if service.download is not None:
                return service.download(self)
            served_body(self, SCRIPTED_BODY, SCRIPTED_DIGEST, tool.DOWNLOAD_RECORD_TYPE)

        def log_message(self, *_arguments):
            pass

    class Server(ThreadingHTTPServer):
        def handle_error(self, *_arguments):
            # A check that stops reading closes the connection on purpose. The name is kept,
            # so that a mistake in a scripted answer cannot pass as a closed connection.
            service.handler_errors.append(sys.exc_info()[0].__name__)

    server = Server(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_port
    finally:
        server.shutdown()
        server.server_close()
        worker.join(5)


class ServiceCase(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="native-install-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.project = self.folder / "project"
        self.project.mkdir()
        self.outside = self.folder / "outside"
        self.outside.mkdir()
        (self.folder / "service").mkdir()
        self.fixture = HttpDomainFixture(self.folder / "service", bodies=dict(BODIES))
        self.client = write_fake_client(self.folder / "client")
        self.key = self.fixture.keys["alpha"].key
        self.use_key(self.key)
        self.reports = 0

    def use_key(self, key: str) -> None:
        patcher = mock.patch.dict(os.environ, {KEY_VARIABLE: key})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.key = key

    def install(self, base, *selection, target=None, report=None, client=None, options=(), authorize=True,
                key_variable=KEY_VARIABLE):
        """Run the command line entry point. Returns exit code, report and everything printed."""
        self.reports += 1
        report = report or self.folder / ("report-%d.json" % self.reports)
        earlier = report.read_bytes() if report.exists() else None
        arguments = ["--origin", base, "--key-variable", key_variable, "--client", "opencode",
                     "--target", str(target or self.project), "--report", str(report),
                     "--client-executable", str(client or self.client), "--allow-loopback-http",
                     *selection, *options]
        if authorize:
            arguments.append("--authorize-install")
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            try:
                code = tool.main(arguments)
            except SystemExit as stop:
                code = stop.code
        text = report.read_text() if report.exists() else ""
        self.assertNotIn(self.key, text + output.getvalue(), "the service key reached a report or the output")
        if earlier is not None:  # The path was taken before this run. Nothing of this run belongs there.
            return code, None, output.getvalue()
        return code, (json.loads(text) if text else None), output.getvalue()

    def run_with_limits(self, base, limits, *identities, client=None):
        """Run one journey with other bounds. The command line does not carry bounds."""
        self.reports += 1
        request = tool.InstallRequest(
            origin=base, key_variable=KEY_VARIABLE, client_kind="opencode", target=self.project,
            report=self.folder / ("report-%d.json" % self.reports), identities=identities, authorized=True,
            allow_loopback_http=True, client_command=(str(client or self.client),), limits=limits)
        descriptor = tool.reserve_report(request.report)
        try:
            report = tool.install_selected_material(request, self.key, descriptor)
        finally:
            os.close(descriptor)
        self.assertNotIn(self.key, request.report.read_text(), "the service key reached a report")
        return report

    def usage_records(self, tenant="alpha") -> int:
        return self.fixture.usage(tenant)["records"]

    def skill_file(self, name: str) -> Path:
        return self.project / ".opencode" / "skills" / name / "SKILL.md"


class InstallChecks(ServiceCase):
    def test_selected_bodies_are_installed_and_reported_by_the_client(self):
        grant(self.fixture, ("skill.alpha", "skill.large", "skill.review_inputs"))
        with running_http(self.fixture) as (base, _service):
            code, report, output = self.install(base, "--query", "alpha reference")
        self.assertEqual(code, 0, output)
        self.assertTrue(report["complete"] and report["all_selected_installed_and_reported"])
        self.assertEqual(report["model_turns_started"], 0)
        self.assertEqual(report["selection"]["query_characters"], len("alpha reference"))
        self.assertNotIn("alpha reference", json.dumps(report["selection"]))
        self.assertEqual(report["key"], {"source": "environment_variable", "variable_name": KEY_VARIABLE,
                                         "value_recorded": False})
        self.assertEqual({item["identity"] for item in report["items"]},
                         {"skill.alpha", "skill.large", "skill.review_inputs"})
        for item in report["items"]:
            body = BODIES[item["identity"]].encode()
            record = item["install"]
            data = (self.project / record["path"]).read_bytes()
            self.assertEqual(item["facts"], {"offered": True, "fetched": True, "installed": True,
                                             "reported_by_client": True})
            self.assertEqual(record["record_type"], "native_material_install_record/v1")
            self.assertEqual((record["body_sha256"], record["body_bytes"]),
                             (hashlib.sha256(body).hexdigest(), len(body)))
            self.assertEqual(data[record["body_offset_bytes"]:], body, "the served body is not verbatim")
            self.assertEqual((record["file_sha256"], record["file_bytes"]),
                             (hashlib.sha256(data).hexdigest(), len(data)))
            self.assertEqual(item["fetch"]["header_digest"], record["body_sha256"])
            self.assertEqual(item["offer"]["digest"], record["body_sha256"])
            self.assertTrue(item["client_report"]["content_matches_served_body"])
            self.assertTrue(data.startswith(b'---\nname: "' + record["native_name"].encode() + b'"\ndescription: "'))
            self.assertIs(record["file_unchanged_at_end_of_run"], True)
        self.assertEqual(self.usage_records(), 3)
        self.assertEqual(report["summary"], {"selected": 3, "offered": 3, "fetched": 3, "installed": 3,
                                             "written_by_this_run": 3, "already_present_identical": 0,
                                             "listed_at_installed_path": 3, "reported_by_client": 3,
                                             "refused": 0})
        self.assertEqual(report["mode"], "install")

    def test_header_digest_mismatch_is_refused(self):
        change = lambda value: {**value, "digest": "0" * 64}  # noqa: E731
        with running_http(self.fixture, application_factory=tampered_service(self.fixture, change)) as (base, _):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual(code, 1)
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]),
                         ("verification", "body_differs_from_header_digest"))
        self.assertEqual(item["facts"], {"offered": True, "fetched": False, "installed": False,
                                         "reported_by_client": None})
        self.assertEqual(item["fetch"]["outcome"], "rejected_by_verification")
        self.assertEqual(files_under(self.project), [])

    def test_body_that_differs_from_manifest_is_refused(self):
        factory = tampered_service(self.fixture, same_length_other_text)
        with running_http(self.fixture, application_factory=factory) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual(code, 1)
        self.assertEqual(item["fetch"]["header_digest"], hashlib.sha256(b"approved_alpha_body").hexdigest())
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]),
                         ("verification", "body_differs_from_manifest_digest"))
        self.assertFalse(item["facts"]["installed"])
        self.assertEqual(files_under(self.project), [])

    def test_changed_body_under_a_true_header_and_a_longer_body_are_refused(self):
        cases = ((lambda value: {**value, "body": value["body"].swapcase()}, "body_differs_from_header_digest"),
                 (lambda value: {**value, "body": value["body"] + "MORE"}, "download_exceeds_declared_size"))
        for change, expected in cases:
            with self.subTest(expected=expected):
                factory = tampered_service(self.fixture, change)
                with running_http(self.fixture, application_factory=factory) as (base, _service):
                    code, report, _output = self.install(base, "--identity", "skill.alpha")
                self.assertEqual((code, report["items"][0]["refusal"]["code"]), (1, expected))
                self.assertEqual(files_under(self.project), [])

    def test_service_refusal_writes_nothing_and_keeps_its_code(self):
        with running_http(self.fixture, application_factory=tampered_service(self.fixture, refuse_the_read)) as (base, _):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual(code, 1)
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"], item["refusal"]["detail"]),
                         ("fetch", "service_refused", "403:body_forbidden"))
        self.assertEqual(item["fetch"]["outcome"], "refused_by_service")
        self.assertEqual(item["facts"], {"offered": True, "fetched": False, "installed": False,
                                         "reported_by_client": None})
        self.assertEqual(files_under(self.project), [])

    def test_body_the_key_may_not_read_is_refused_before_fetch(self):
        with running_http(self.fixture) as (base, _service):
            # Another tenant's item and an unapproved candidate are not offered at all.
            code, report, _output = self.install(base, "--identity", "skill.beta", "--identity", "skill.candidate")
            self.assertEqual(code, 1)
            for item in report["items"]:
                self.assertEqual(item["facts"], {"offered": False, "fetched": False, "installed": False,
                                                 "reported_by_client": None})
                self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"], item["refusal"]["detail"]),
                                 ("offer", "service_refused", "404:item_unavailable"))
            # A grant without body permission, then a key without the read scope.
            grant(self.fixture, ("skill.alpha",), body_allowed=False)
            code, denied, _output = self.install(base, "--identity", "skill.alpha")
            grant(self.fixture, ("skill.alpha",))
            self.use_key(self.fixture.runtime.issue_key(TenantKeyIssue(
                "alpha", "metadata only", scopes=("provisioning:metadata", "usage:read"))).key)
            scoped_code, scoped, _output = self.install(base, "--identity", "skill.alpha")
        for outcome, observed in ((code, denied), (scoped_code, scoped)):
            item = observed["items"][0]
            self.assertEqual(outcome, 1)
            self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]), ("offer", "body_not_permitted"))
            self.assertEqual(item["facts"]["offered"], True)
            self.assertIsNone(item["fetch"], "a download was attempted for a body the key may not read")
            self.assertEqual(observed["http_calls"], 2)
        self.assertEqual((self.fixture.reads, self.usage_records(), files_under(self.project)), ([], 0, []))

    def test_kind_without_a_native_location_is_refused_before_fetch(self):
        add_item(self.fixture, "instruction.house_rules", "instruction_file", "Follow the house rules.\n")
        add_item(self.fixture, "tool.copy", "tool", "{}", source_layer="code_intelligence")
        grant(self.fixture, ("instruction.house_rules", "tool.copy"))
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "instruction.house_rules", "--identity", "tool.copy")
        self.assertEqual(code, 1)
        for item in report["items"]:
            self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]), ("offer", "kind_has_no_native_location"))
            self.assertEqual((item["facts"]["offered"], item["facts"]["fetched"], item["fetch"]), (True, False, None))
        self.assertEqual((self.fixture.reads, self.usage_records(), files_under(self.project)), ([], 0, []))
        self.assertEqual(report["listing"]["state"], "nothing_installed")

    def test_identity_without_native_name_is_refused_before_any_item_request(self):
        grant(self.fixture, (HOSTILE_IDENTITY,))
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--query", "alpha reference")
            refused_code, _none, _text = self.install(base, "--identity", HOSTILE_IDENTITY)
        item = report["items"][0]
        self.assertEqual((code, item["identity"]), (1, HOSTILE_IDENTITY))
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]), ("selection", "identity_has_no_native_name"))
        self.assertEqual(report["http_calls"], 2, "a manifest or body was requested for an unusable identity")
        self.assertEqual(refused_code, 2)
        self.assertEqual([path for path in files_under(self.folder) if "evil" in path], [])
        self.assertEqual((files_under(self.project), files_under(self.outside)), ([], []))
        self.assertEqual((self.fixture.reads, self.usage_records()), ([], 0))

    def test_symbolic_link_in_path_is_refused(self):
        places = ((".opencode",), (".opencode", "skills"), (".opencode", "skills", "skill-alpha"),
                  (".opencode", "skills", "skill-alpha", "SKILL.md"))
        with running_http(self.fixture) as (base, _service):
            for parts in places:
                with self.subTest(link=parts[-1]):
                    shutil.rmtree(self.project)
                    self.project.joinpath(*parts[:-1]).mkdir(parents=True)
                    destination = self.outside / "SKILL.md" if parts[-1] == "SKILL.md" else self.outside
                    self.project.joinpath(*parts).symlink_to(destination)
                    code, report, _output = self.install(base, "--identity", "skill.alpha")
                    item = report["items"][0]
                    self.assertEqual(code, 1)
                    self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]),
                                     ("placement", "symbolic_link_refused"))
                    self.assertEqual(files_under(self.outside), [], "a file was written through a symbolic link")
                    self.assertEqual((self.fixture.reads, self.usage_records()), ([], 0))
            link = self.folder / "project-link"
            link.symlink_to(self.project)
            code, report, _output = self.install(base, "--identity", "skill.alpha", target=link)
        self.assertEqual((code, report), (2, None))

    def test_different_existing_file_is_refused_before_fetch(self):
        target = self.skill_file("skill-alpha")
        target.parent.mkdir(parents=True)
        target.write_text("---\nname: skill-alpha\ndescription: Mine\n---\nMy own skill.\n")
        before = target.read_bytes()
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual(code, 1)
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]), ("placement", "different_file_exists"))
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual((self.fixture.reads, self.usage_records(), item["fetch"]), ([], 0, None))

    def test_two_identities_with_one_native_name_never_share_a_file(self):
        add_item(self.fixture, "skill.review.inputs", "skill", "A different body under a colliding name.\n")
        grant(self.fixture, ("skill.review_inputs", "skill.review.inputs"))
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.review_inputs",
                                                 "--identity", "skill.review.inputs")
        first, second = report["items"]
        self.assertEqual((code, first["native_name"], second["native_name"]),
                         (1, "skill-review-inputs", "skill-review-inputs"))
        self.assertTrue(first["facts"]["installed"])
        self.assertEqual((second["refusal"]["stage"], second["refusal"]["code"], second["fetch"]),
                         ("placement", "different_file_exists", None))
        self.assertEqual(self.skill_file("skill-review-inputs").read_bytes()[first["install"]["body_offset_bytes"]:],
                         REVIEW_BODY.encode())
        self.assertEqual(self.usage_records(), 1)

    def test_identical_existing_file_is_accepted_without_another_read(self):
        with running_http(self.fixture) as (base, _service):
            first_code, first, _output = self.install(base, "--identity", "skill.alpha")
            target = self.skill_file("skill-alpha")
            before = (target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns)
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual((first_code, code), (0, 0))
        self.assertEqual(item["facts"], {"offered": True, "fetched": False, "installed": True,
                                         "reported_by_client": True})
        self.assertEqual(item["fetch"], {"outcome": "not_needed_identical_file_present", "request_id": None})
        self.assertEqual((item["install"]["written_by_this_run"], item["install"]["already_present_identical"]),
                         (False, True))
        self.assertEqual(item["install"]["file_sha256"], first["items"][0]["install"]["file_sha256"])
        self.assertEqual((target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns), before)
        self.assertEqual(self.usage_records(), 1)

    def test_item_the_client_omits_is_not_reported(self):
        set_client_behaviour(self.client, "omit", names=("skill-alpha",))
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha", "--identity", "skill.large")
        facts = {item["identity"]: item["facts"] for item in report["items"]}
        self.assertEqual(code, 1)
        self.assertEqual(facts["skill.alpha"], {"offered": True, "fetched": True, "installed": True,
                                                "reported_by_client": False})
        self.assertEqual(facts["skill.large"]["reported_by_client"], True)
        self.assertFalse(report["all_selected_installed_and_reported"])

    def test_changed_content_or_name_in_the_listing_does_not_pass(self):
        with running_http(self.fixture) as (base, _service):
            for mode, field in (("alter", "content_matches_served_body"), ("rename", "name_matches")):
                with self.subTest(mode=mode):
                    set_client_behaviour(self.client, mode, names=("skill-alpha",))
                    code, report, _output = self.install(base, "--identity", "skill.alpha")
                    item = report["items"][0]
                    observed = item["client_report"]
                    self.assertEqual((code, observed["reported"], observed[field]), (1, True, False))
                    # The headline fact needs the path, the name and the content. A path alone is not enough.
                    self.assertIs(item["facts"]["reported_by_client"], False)
                    self.assertEqual((report["summary"]["listed_at_installed_path"],
                                      report["summary"]["reported_by_client"]), (1, 0))

    def test_a_client_that_rewrites_the_installed_file_is_not_accepted(self):
        set_client_behaviour(self.client, "rewrite", names=("skill-alpha",))
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        target = self.skill_file("skill-alpha")
        self.assertEqual(code, 1)
        # The listing still claimed the served content. The file on disk is what decides.
        self.assertIs(item["client_report"]["content_matches_served_body"], True)
        self.assertIs(item["install"]["file_unchanged_at_end_of_run"], False)
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]),
                         ("placement", "file_changed_after_install"))
        self.assertFalse(report["all_selected_installed_and_reported"])
        self.assertNotEqual(hashlib.sha256(target.read_bytes()).hexdigest(), item["install"]["file_sha256"])

    def test_an_existing_file_under_another_header_of_the_same_length_is_refused(self):
        header, _truncated = tool.render_skill_header("skill-alpha", "Alpha reference skill.alpha")
        other = header.replace(b'"Alpha reference', b'"alpha reference')
        self.assertEqual((len(other), other == header), (len(header), False))
        target = self.skill_file("skill-alpha")
        target.parent.mkdir(parents=True)
        target.write_bytes(other + BODIES["skill.alpha"].encode())
        before = target.read_bytes()
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual(code, 1)
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]), ("placement", "different_file_exists"))
        self.assertEqual((item["fetch"], self.fixture.reads, self.usage_records()), (None, [], 0))
        self.assertEqual(target.read_bytes(), before)

    @unittest.skipUnless(WRITE_PROTECTION_OBSERVED, "this process may write into a folder without the permission")
    def test_a_target_that_cannot_take_the_file_is_refused_before_the_metered_read(self):
        self.addCleanup(self.project.chmod, 0o755)
        self.project.chmod(0o555)
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual(code, 1)
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]),
                         ("placement", "target_folder_not_writable"))
        self.assertEqual((item["fetch"], self.fixture.reads, self.usage_records()), (None, [], 0))
        self.assertEqual(files_under(self.project), [])

    def test_a_listing_over_the_bound_is_unknown(self):
        with running_http(self.fixture) as (base, _service):
            report = self.run_with_limits(base, tool.TransferLimits(maximum_listing_bytes=1), "skill.alpha")
        item = report["items"][0]
        self.assertEqual(report["listing"]["state"], "listing_too_large")
        self.assertIs(item["facts"]["installed"], True)
        self.assertIsNone(item["facts"]["reported_by_client"])
        self.assertIs(report["all_selected_installed_and_reported"], False)

    def test_a_location_the_platform_cannot_resolve_is_no_match(self):
        set_client_behaviour(self.client, "nul_location")
        with running_http(self.fixture) as (base, _service):
            code, report, output = self.install(base, "--identity", "skill.alpha")
        self.assertEqual((code, report["complete"]), (0, True), output)
        self.assertEqual(report["listing"]["state"], "observed")
        self.assertIs(report["items"][0]["facts"]["reported_by_client"], True)

    def test_a_name_that_utf8_cannot_carry_still_leaves_a_complete_report(self):
        set_client_behaviour(self.client, "surrogate_name", names=("skill-alpha",))
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual((code, report["complete"]), (1, True))
        self.assertEqual(report["listing"]["state"], "observed")
        self.assertEqual(item["client_report"]["reported_name"], "\ud800-name")
        self.assertIs(item["client_report"]["name_matches"], False)
        self.assertIs(item["facts"]["reported_by_client"], False)

    def test_a_listing_that_is_nested_too_deeply_is_unknown(self):
        set_client_behaviour(self.client, "deep")
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        self.assertEqual((code, report["complete"]), (1, True))
        self.assertEqual(report["listing"]["state"], "listing_unreadable")
        self.assertIsNone(report["items"][0]["facts"]["reported_by_client"])
        self.assertIsNone(report["interrupted_by"])

    def test_an_error_outside_the_typed_refusals_keeps_what_is_already_known(self):
        def stop_the_run(*_arguments, **_fields):
            raise RuntimeError("something outside the typed refusals")

        with running_http(self.fixture) as (base, _service):
            with mock.patch.object(tool, "observe_client_listing", stop_the_run):
                try:
                    code, report, output = self.install(base, "--identity", "skill.alpha")
                except Exception as error:  # A run that raises instead of recording must fail here.
                    self.fail("the run raised %s instead of writing a report" % type(error).__name__)
        item = report["items"][0]
        self.assertEqual(code, 1, output)
        self.assertIs(report["complete"], False)
        self.assertEqual(report["interrupted_by"], {"code": "unexpected_error", "detail": "RuntimeError"})
        # What was already recorded is kept, including the install record of the file on disk.
        self.assertIs(item["facts"]["installed"], True)
        self.assertEqual(item["install"]["body_sha256"],
                         hashlib.sha256(BODIES["skill.alpha"].encode()).hexdigest())
        self.assertEqual(report["summary"]["installed"], 1)
        self.assertIs(report["all_selected_installed_and_reported"], False)
        self.assertIn("unexpected_error", output)

    def test_a_preview_reads_no_body_and_writes_no_file(self):
        grant(self.fixture, ("skill.alpha", "skill.large"))
        with running_http(self.fixture) as (base, _service):
            code, report, output = self.install(base, "--query", "alpha reference",
                                                options=("--preview",), authorize=False)
        self.assertEqual(code, 0, output)
        self.assertEqual(report["mode"], "preview_without_body_read_or_file_write")
        self.assertEqual(len(report["items"]), 2)
        for item in report["items"]:
            self.assertEqual(item["facts"], {"offered": True, "fetched": False, "installed": False,
                                             "reported_by_client": None})
            self.assertEqual((item["preview"]["record_type"], item["preview"]["metered_body_read_needed"]),
                             ("native_material_install_preview/v1", True))
            self.assertTrue(item["preview"]["path"].startswith(".opencode/skills/"))
        self.assertEqual(report["listing"]["state"], "preview_only_no_client_process")
        self.assertEqual((self.fixture.reads, self.usage_records(), files_under(self.project)), ([], 0, []))
        self.assertEqual(client_invocations(self.client), [])

    def test_unreadable_listing_is_unknown_and_never_read_as_not_reported(self):
        states = (("cut", "listing_unreadable"), ("fail", "listing_command_failed"))
        with running_http(self.fixture) as (base, _service):
            for mode, state in states:
                with self.subTest(mode=mode):
                    set_client_behaviour(self.client, mode)
                    code, report, _output = self.install(base, "--identity", "skill.alpha")
                    self.assertEqual((code, report["listing"]["state"]), (1, state))
                    self.assertTrue(report["items"][0]["facts"]["installed"])
                    self.assertIsNone(report["items"][0]["facts"]["reported_by_client"])
            code, report, _output = self.install(base, "--identity", "skill.alpha",
                                                 client=self.folder / "no-such-client")
        self.assertEqual((code, report["listing"]["state"]), (1, "client_executable_not_usable"))

    def test_listing_that_does_not_finish_is_stopped(self):
        set_client_behaviour(self.client, "hang")
        with running_http(self.fixture) as (base, _service):
            report = self.run_with_limits(base, tool.TransferLimits(listing_timeout_seconds=1.0), "skill.alpha")
        self.assertEqual(report["listing"]["state"], "listing_timed_out")
        self.assertIsNone(report["items"][0]["facts"]["reported_by_client"])

    def test_listing_process_never_receives_the_service_key(self):
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        calls = client_invocations(self.client)
        self.assertEqual(code, 0)
        self.assertEqual([call["arguments"] for call in calls], [["--version"], ["debug", "skill", "--pure"]])
        self.assertTrue(all(call["watched_variable_present"] is False for call in calls))
        self.assertTrue(all(call["settings_present"] and call["cwd"] == str(self.project.resolve()) for call in calls))
        self.assertEqual(report["listing"]["command_arguments"], ["debug", "skill", "--pure"])
        self.assertEqual((report["listing"]["client_version"], report["listing"]["layout_observed_with_this_version"]),
                         ("1.18.31", True))

    def test_files_the_client_process_adds_to_the_project_are_shown(self):
        set_client_behaviour(self.client, "discover", creates=(".opencode/.gitignore",))
        with running_http(self.fixture) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
            _code, quiet, _output = self.install(base, "--identity", "skill.alpha")
        self.assertEqual(code, 0)
        self.assertEqual(report["listing"]["paths_created_by_the_client_process"], [".opencode/.gitignore"])
        self.assertEqual(quiet["listing"]["paths_created_by_the_client_process"], [])

    def test_unobserved_client_version_is_flagged(self):
        set_client_behaviour(self.client, "discover", version="9.0.0")
        with running_http(self.fixture) as (base, _service):
            _code, report, _output = self.install(base, "--identity", "skill.alpha")
        self.assertEqual((report["listing"]["client_version"], report["listing"]["layout_observed_with_this_version"]),
                         ("9.0.0", False))

    def test_existing_report_is_refused_before_any_request(self):
        report = self.folder / "kept.json"
        report.write_text("an earlier report\n")
        with running_http(self.fixture) as (base, _service):
            code, _report, output = self.install(base, "--identity", "skill.alpha", report=report)
            missing_folder, _none, _text = self.install(base, "--identity", "skill.alpha",
                                                        report=self.folder / "absent" / "report.json")
        self.assertEqual((code, missing_folder), (2, 2))
        self.assertIn("report_path_not_new", output)
        self.assertEqual(report.read_text(), "an earlier report\n")
        self.assertEqual((self.fixture.reads, self.usage_records(), files_under(self.project)), ([], 0, []))

    def test_key_is_taken_only_from_the_named_variable(self):
        with running_http(self.fixture) as (base, _service):
            pasted, report, output = self.install(base, "--query", self.key)
            self.assertEqual((pasted, report), (2, None))
            self.assertIn("key_on_command_line", output)
            unset, report, output = self.install(base, "--identity", "skill.alpha", key_variable="NATIVE_INSTALL_UNSET")
            self.assertEqual((unset, report), (2, None))
            self.assertNotIn("NATIVE_INSTALL_UNSET", output)
            shaped, report, output = self.install(base, "--identity", "skill.alpha", key_variable="not-a-name")
            self.assertEqual((shaped, report), (2, None))
            self.assertNotIn("not-a-name", output)
            # A key typed after a wrong option is refused without being repeated to the terminal.
            mistyped, report, output = self.install(base, "--identity", "skill.alpha", options=("--key", self.key))
            self.assertEqual((mistyped, report), (2, None))
            self.assertIn("invalid_arguments", output)
            self.use_key("bad key\r\nX-Injected: 1")
            unusable, report, output = self.install(base, "--identity", "skill.alpha")
        self.assertEqual((unusable, report), (2, None))
        self.assertIn("key_value_not_usable", output)
        self.assertEqual((self.fixture.reads, files_under(self.project)), ([], []))

    def test_unsupported_service_capabilities_refuse_before_authenticated_requests(self):
        factory = lambda configuration: UnsupportedCapabilities(  # noqa: E731
            self.fixture.runtime, self.fixture.provisioning, configuration, ServiceHttpAuthentication())
        with running_http(self.fixture, application_factory=factory) as (base, _service):
            code, report, _output = self.install(base, "--identity", "skill.alpha")
        self.assertEqual(code, 1)
        self.assertEqual(report["service_refusal"]["code"], "unsupported_service_capabilities")
        self.assertEqual((report["http_calls"], report["items"], files_under(self.project)), (1, [], []))

    def test_redirect_is_refused_and_the_key_stays_with_the_named_origin(self):
        direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with running_http(self.fixture) as (base, _service), \
                recording_server(lambda handler: answer(handler, 200)) as (elsewhere, seen_elsewhere):
            def redirecting(handler):
                if handler.path == tool.CAPABILITIES_ROUTE:  # The contract check passes, so the key is sent next.
                    answer(handler, 200, direct.open(base + handler.path, timeout=5).read())
                else:
                    answer(handler, 302, b"", elsewhere + handler.path)
            with recording_server(redirecting) as (front, _seen):
                code, report, _output = self.install(front, "--identity", "skill.alpha")
        item = report["items"][0]
        self.assertEqual(code, 1)
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]), ("offer", "redirect_refused"))
        self.assertEqual(seen_elsewhere, [], "a request followed a redirect to another origin")
        self.assertEqual(files_under(self.project), [])

    def test_proxy_settings_in_the_environment_are_ignored(self):
        with recording_server(lambda handler: answer(handler, 502)) as (proxy, seen_by_proxy), \
                running_http(self.fixture) as (base, _service):
            with mock.patch.dict(os.environ, {"http_proxy": proxy, "HTTP_PROXY": proxy, "all_proxy": proxy}):
                for name in ("no_proxy", "NO_PROXY"):
                    os.environ.pop(name, None)
                code, _report, output = self.install(base, "--identity", "skill.alpha")
        self.assertEqual(seen_by_proxy, [], "the key travelled through a proxy named in the environment")
        self.assertEqual(code, 0, output)

    def test_invocation_is_refused_before_effects(self):
        with running_http(self.fixture) as (base, _service):
            cases = ((("--identity", "skill.alpha"), {"authorize": False}, "install_not_authorized"),
                     (("--identity", "skill.alpha"), {"options": ("--preview",)},
                      "preview_excludes_authorize_install"),
                     ((), {}, "exactly_one_of_query_or_identities_required"),
                     (("--query", "   "), {}, "invalid_query"),
                     (("--query", "x" * 5000), {}, "invalid_query"),
                     (("--identity", "skill.alpha", "--query", "alpha"), {}, "exactly_one_of_query_or_identities_required"),
                     (("--identity", "skill.alpha", "--identity", "skill.alpha"), {}, "duplicate_identity"),
                     (("--identity", "skill.alpha", "--top-n", "3"), {}, "invalid_search_limit"),
                     (("--identity", "skill.alpha"), {"options": ("--request-prefix", "bad prefix")}, "invalid_request_prefix"),
                     (("--identity", "skill.alpha"), {"target": self.folder / "absent"}, "target_not_a_real_directory"))
            for selection, changes, expected in cases:
                with self.subTest(expected=expected):
                    code, report, output = self.install(base, *selection, **changes)
                    self.assertEqual((code, report), (2, None))
                    self.assertIn(expected, output)
            for origin in (base + "/", base + "/path", base.replace("http://", "http://user:pw@"),
                           "http://service.example", "ftp://127.0.0.1"):
                with self.subTest(origin=origin):
                    code, report, output = self.install(origin, "--identity", "skill.alpha")
                    self.assertEqual((code, report), (2, None))
                    self.assertIn("invalid_origin", output)
        self.assertEqual((self.fixture.reads, self.usage_records(), files_under(self.project)), ([], 0, []))

    def test_a_client_registry_version_this_tool_does_not_know_is_refused(self):
        # The packaged registry must stay a version this tool states that it reads.
        self.assertIn(tool.read_client_registry()["record_type"], tool.SUPPORTED_CLIENT_REGISTRY_RECORD_TYPES)
        for record_type in tool.SUPPORTED_CLIENT_REGISTRY_RECORD_TYPES:
            with self.subTest(record_type=record_type):
                registry = {"record_type": record_type, "recipes": [{"id": "opencode"}]}
                with mock.patch.object(tool, "read_client_registry", lambda registry=registry: registry):
                    self.assertEqual(tool.registered_client_kinds(), ("opencode",))
        for record_type in ("website_client_recipes/v9", None):
            with self.subTest(record_type=record_type):
                registry = {"recipes": [{"id": "opencode"}]}
                if record_type is not None:
                    registry["record_type"] = record_type
                with mock.patch.object(tool, "read_client_registry", lambda registry=registry: registry):
                    with self.assertRaises(tool.InstallRefusal) as refused:
                        tool.registered_client_kinds()
                self.assertEqual(refused.exception.code, "unsupported_client_registry_version")
        for broken in ([], {"record_type": tool.SUPPORTED_CLIENT_REGISTRY_RECORD_TYPES[0]}):
            with self.subTest(registry=broken):
                with mock.patch.object(tool, "read_client_registry", lambda broken=broken: broken):
                    with self.assertRaises(tool.InstallRefusal) as refused:
                        tool.registered_client_kinds()
                self.assertEqual(refused.exception.code, "client_registry_unreadable")

    def test_client_kinds_come_from_the_recipes_registry(self):
        self.assertLessEqual(set(tool.CLIENT_LAYOUT_PROFILES), set(tool.registered_client_kinds()))
        # Every recipe client kind now carries a layout profile; a kind the
        # recipes registry does not name is refused before anything else.
        self.assertEqual(set(tool.CLIENT_LAYOUT_PROFILES), set(tool.registered_client_kinds()))
        with running_http(self.fixture) as (base, _service):
            for kind in ("unheard-of", "gemini-cli", "pi"):
                with self.subTest(kind=kind):
                    with self.assertRaises(tool.InstallRefusal) as refused:
                        tool.InstallRequest(origin=base, key_variable=KEY_VARIABLE, client_kind=kind,
                                            target=self.project, report=self.folder / "r.json",
                                            identities=("skill.alpha",), authorized=True, allow_loopback_http=True)
                    self.assertEqual(refused.exception.code, "unknown_client_kind")

    def test_same_request_prefix_repeats_the_same_read_without_new_usage(self):
        second = self.folder / "second-project"
        second.mkdir()
        with running_http(self.fixture) as (base, _service):
            options = ("--request-prefix", "retry-one")
            _code, first, _output = self.install(base, "--identity", "skill.alpha", options=options)
            _code, again, _output = self.install(base, "--identity", "skill.alpha", options=options, target=second)
        self.assertEqual(first["items"][0]["fetch"]["request_id"], again["items"][0]["fetch"]["request_id"])
        self.assertTrue(again["items"][0]["facts"]["fetched"])
        self.assertEqual(self.usage_records(), 1)


class ScriptedServiceChecks(unittest.TestCase):
    """What the tool does with an answer the real local service never gives."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="native-install-scripted-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.project = self.folder / "project"
        self.project.mkdir()
        self.report = self.folder / "report.json"
        self.absent_client = self.folder / "no-such-client"
        self.key = "scripted-service-key-0123456789"
        patcher = mock.patch.dict(os.environ, {KEY_VARIABLE: self.key})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_tool(self, base, *selection):
        """The command line entry point, as an operator runs it."""
        arguments = ["--origin", base, "--key-variable", KEY_VARIABLE, "--client", "opencode",
                     "--target", str(self.project), "--report", str(self.report),
                     "--client-executable", str(self.absent_client), "--allow-loopback-http",
                     "--authorize-install", *(selection or ("--identity", SCRIPTED_IDENTITY))]
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            try:
                code = tool.main(arguments)
            except SystemExit as stop:
                code = stop.code
        text = self.report.read_text() if self.report.exists() else ""
        self.assertNotIn(self.key, text + output.getvalue(), "the service key reached a report or the output")
        return code, (json.loads(text) if text.strip() else None), output.getvalue()

    def run_with_limits(self, base, limits):
        request = tool.InstallRequest(
            origin=base, key_variable=KEY_VARIABLE, client_kind="opencode", target=self.project,
            report=self.report, identities=(SCRIPTED_IDENTITY,), authorized=True, allow_loopback_http=True,
            client_command=(str(self.absent_client),), limits=limits)
        descriptor = tool.reserve_report(request.report)
        try:
            return tool.install_selected_material(request, self.key, descriptor)
        finally:
            os.close(descriptor)

    def refused_item(self, service, *selection, stage="offer", code="unsupported_service_record", detail=None):
        """Run one journey and require the named refusal, with nothing written."""
        with running_script(service) as base:
            exit_code, report, output = self.run_tool(base, *selection)
        item = report["items"][0]
        refusal = item["refusal"] or {}  # A run that does not refuse must fail here, not raise.
        self.assertEqual((exit_code, report["complete"]), (1, True), output)
        self.assertEqual((refusal.get("stage"), refusal.get("code")), (stage, code))
        if detail is not None:
            self.assertEqual(refusal.get("detail"), detail)
        self.assertEqual(files_under(self.project), [])
        self.assertLessEqual(set(service.handler_errors), CONNECTION_CLOSED_ERRORS, service.handler_errors)
        return report

    def test_a_download_under_another_record_type_is_refused(self):
        def wrong_record_type(handler):
            served_body(handler, SCRIPTED_BODY, SCRIPTED_DIGEST, "service_download/v2")
        report = self.refused_item(ScriptedService(download=wrong_record_type), stage="verification")
        self.assertEqual(report["items"][0]["fetch"]["outcome"], "rejected_by_verification")

    def test_a_manifest_for_another_identity_is_refused(self):
        service = ScriptedService(manifest=scripted_manifest(identity="skill.other"))
        self.refused_item(service)
        self.assertNotIn(tool.DOWNLOAD_ROUTE, service.seen)

    def test_a_manifest_of_another_record_version_is_refused(self):
        service = ScriptedService(manifest=scripted_manifest(record_type="provisioning_manifest/v99"))
        self.refused_item(service)
        self.assertNotIn(tool.DOWNLOAD_ROUTE, service.seen)

    def test_a_manifest_that_declares_more_than_the_allowance_is_refused(self):
        service = ScriptedService(manifest=scripted_manifest(size_bytes=10 ** 12))
        self.refused_item(service, code="body_exceeds_download_allowance")
        self.assertNotIn(tool.DOWNLOAD_ROUTE, service.seen)

    def test_an_offer_that_changed_between_the_search_and_the_manifest_is_refused(self):
        service = ScriptedService(hits=[{"reference": {"identity": SCRIPTED_IDENTITY, "body_digest": "1" * 64}}])
        self.refused_item(service, "--query", "scripted", code="offer_changed_between_search_and_manifest")
        self.assertNotIn(tool.DOWNLOAD_ROUTE, service.seen)

    def test_text_that_utf8_cannot_carry_is_refused_before_any_body_read(self):
        for field in ("license", "source_ref", "qualification_basis", "purpose"):
            with self.subTest(field=field):
                self.report = self.folder / ("surrogate-%s.json" % field)
                service = ScriptedService(raw_manifest=scripted_result(
                    scripted_manifest(**{field: "text \ud800 here"})))
                self.refused_item(service, detail="text_does_not_encode_as_utf8")
                self.assertNotIn(tool.DOWNLOAD_ROUTE, service.seen)

    def test_a_digest_header_that_is_missing_or_doubled_is_refused(self):
        def no_digest(handler):
            handler.send_response(200)
            handler.send_header(tool.RECORD_TYPE_HEADER, tool.DOWNLOAD_RECORD_TYPE)
            handler.send_header("Content-Length", str(len(SCRIPTED_BODY)))
            handler.end_headers()
            handler.wfile.write(SCRIPTED_BODY)

        def two_digests(handler):
            handler.send_response(200)
            handler.send_header(tool.RECORD_TYPE_HEADER, tool.DOWNLOAD_RECORD_TYPE)
            handler.send_header(tool.DIGEST_HEADER, SCRIPTED_DIGEST)
            handler.send_header(tool.DIGEST_HEADER, "0" * 64)
            handler.send_header("Content-Length", str(len(SCRIPTED_BODY)))
            handler.end_headers()
            handler.wfile.write(SCRIPTED_BODY)

        for name, download in (("missing", no_digest), ("doubled", two_digests)):
            with self.subTest(header=name):
                self.report = self.folder / ("digest-%s.json" % name)
                self.refused_item(ScriptedService(download=download), stage="verification",
                                  code="digest_header_missing_or_malformed")

    def test_a_body_of_another_size_than_the_manifest_declares_is_refused(self):
        service = ScriptedService(manifest=scripted_manifest(size_bytes=len(SCRIPTED_BODY) + 100))
        self.refused_item(service, stage="verification", code="body_size_differs_from_manifest")

    def test_a_service_record_nested_too_deeply_is_refused(self):
        deep = b'{"record_type": "' + tool.RESULT_VERSION.encode() + b'", "result": ' \
               + b"[" * 100_000 + b"]" * 100_000 + b"}"
        report = self.refused_item(ScriptedService(raw_manifest=deep))
        self.assertIsNone(report["interrupted_by"])

    def test_capabilities_that_name_another_body_format_are_refused(self):
        service = ScriptedService(capabilities=scripted_capabilities(body_format="binary"))
        with running_script(service) as base:
            code, report, _output = self.run_tool(base)
        self.assertEqual((code, report["complete"]), (1, True))
        self.assertEqual(report["service_refusal"],
                         {"code": "unsupported_service_capabilities", "detail": "body_format"})
        self.assertEqual((report["items"], report["http_calls"], service.seen),
                         ([], 1, [tool.CAPABILITIES_ROUTE]))

    def test_a_search_that_claims_to_have_loaded_bodies_is_refused(self):
        service = ScriptedService(retrieval={
            "record_type": tool.RETRIEVAL_RESULT_RECORD_TYPE, "bodies_loaded": True,
            "hits": [{"reference": {"identity": SCRIPTED_IDENTITY, "body_digest": SCRIPTED_DIGEST}}]})
        with running_script(service) as base:
            code, report, _output = self.run_tool(base, "--query", "scripted")
        self.assertEqual((code, report["complete"]), (1, True))
        self.assertEqual(report["service_refusal"], {"code": "unsupported_service_record", "detail": ""})
        self.assertEqual((report["items"], files_under(self.project)), ([], []))

    def test_a_json_response_over_the_bound_is_refused(self):
        padded = scripted_result(scripted_manifest(purpose="x" * 200_000))
        service = ScriptedService(raw_manifest=padded)
        with running_script(service) as base:
            report = self.run_with_limits(base, tool.TransferLimits(maximum_json_bytes=50_000))
        item = report["items"][0]
        self.assertEqual((item["refusal"]["stage"], item["refusal"]["code"]), ("offer", "response_too_large"))
        self.assertEqual((report["complete"], files_under(self.project)), (True, []))

    def test_a_body_longer_than_the_declared_size_stops_at_the_bound(self):
        sent = []

        def endless(handler):
            handler.send_response(200)
            handler.send_header(tool.RECORD_TYPE_HEADER, tool.DOWNLOAD_RECORD_TYPE)
            handler.send_header(tool.DIGEST_HEADER, SCRIPTED_DIGEST)
            handler.end_headers()  # No declared length: the service keeps sending until it is stopped.
            try:
                for _block in range(48):
                    handler.wfile.write(b"A" * 65536)
                    sent.append(65536)
            except OSError:
                pass  # The tool stopped reading at its bound and closed the connection.

        report = self.refused_item(ScriptedService(download=endless), stage="verification",
                                   code="download_exceeds_declared_size")
        # The read stops at the declared size plus one byte, whatever the service keeps sending.
        self.assertEqual(report["items"][0]["fetch"]["body_bytes"], len(SCRIPTED_BODY) + 1)

    def test_a_response_that_arrives_too_slowly_is_refused(self):
        body = b"B" * 40

        def drip(handler):
            handler.send_response(200)
            handler.send_header(tool.RECORD_TYPE_HEADER, tool.DOWNLOAD_RECORD_TYPE)
            handler.send_header(tool.DIGEST_HEADER, hashlib.sha256(body).hexdigest())
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            try:
                for index in range(len(body)):
                    handler.wfile.write(body[index:index + 1])
                    handler.wfile.flush()
                    time.sleep(0.1)
            except OSError:
                pass

        service = ScriptedService(manifest=scripted_manifest(digest=hashlib.sha256(body).hexdigest(),
                                                             size_bytes=len(body)), download=drip)
        with running_script(service) as base:
            report = self.run_with_limits(base, tool.TransferLimits(response_deadline_seconds=0.5))
        refusal = report["items"][0]["refusal"] or {}
        self.assertEqual((refusal.get("stage"), refusal.get("code")), ("fetch", "response_deadline_passed"))
        self.assertEqual((report["complete"], files_under(self.project)), (True, []))

    def test_a_dropped_connection_keeps_the_request_identity_and_stays_unknown(self):
        def drop(handler):
            handler.close_connection = True
            handler.connection.close()

        with running_script(ScriptedService(download=drop)) as base:
            code, report, _output = self.run_tool(base)
        item = report["items"][0]
        refusal, fetch = item["refusal"] or {}, item["fetch"] or {}
        self.assertEqual((code, report["complete"]), (1, True))
        self.assertEqual((refusal.get("stage"), refusal.get("code")), ("fetch", "service_unreachable"))
        self.assertEqual(fetch.get("outcome"), "unknown_no_response_received")
        self.assertTrue(str(fetch.get("request_id")).startswith(report["request_prefix"] + "-"))
        self.assertEqual((fetch.get("body_sha256"), fetch.get("http_status")), (None, None))
        self.assertEqual(files_under(self.project), [])

    def test_the_report_names_the_selection_and_the_request_before_they_are_sent(self):
        service = ScriptedService(watched_report=self.report)
        with running_script(service) as base:
            code, report, output = self.run_tool(base)
        self.assertEqual(code, 1, output)  # There is no client binary, so nothing is reported.
        at_manifest = service.report_when_asked.get(tool.PROVISIONING_ROUTE) or {}
        at_download = service.report_when_asked.get(tool.DOWNLOAD_ROUTE) or {}
        # Before the first authenticated request the report already names the run.
        self.assertEqual(at_manifest.get("request_prefix"), report["request_prefix"])
        self.assertEqual(at_manifest.get("selection", {}).get("identities"), [SCRIPTED_IDENTITY])
        self.assertEqual((at_manifest.get("complete"), at_manifest.get("items")), (False, []))
        # Before the metered read the report already names the request that can be repeated.
        pending = (at_download.get("items") or [{}])[0].get("fetch") or {}
        self.assertEqual(pending.get("outcome"), "unknown_no_response_received")
        self.assertEqual(pending.get("request_id"), report["items"][0]["fetch"]["request_id"])


class PathAndProfileChecks(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="native-install-paths-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.root = self.folder / "project"
        self.root.mkdir()
        self.outside = self.folder / "outside"
        self.outside.mkdir()

    def refused_parts(self, hostile):
        for parts in hostile:
            with self.subTest(parts=parts):
                for action in (lambda: tool.write_confined_file(self.root, parts, b"x"),
                               lambda: tool.read_confined_file(self.root, parts, 10)):
                    with self.assertRaises(tool.InstallRefusal) as refused:
                        action()
                    self.assertEqual(refused.exception.code, "path_traversal_refused")
        self.assertEqual(files_under(self.folder), ["outside", "project"])

    def test_traversal_and_absolute_parts_are_refused(self):
        # Every hostile path stays inside the temporary folder, so a removed guard cannot reach further.
        self.refused_parts((("..", "escape.md"), ("skills", "..", "..", "escape.md"),
                            (str(self.outside), "escape.md"), ("..", "outside", "escape.md")))

    def test_separators_empty_and_foreign_anchors_are_refused(self):
        self.refused_parts((("a/b", "escape.md"), ("a\\b", "escape.md"), ("", "escape.md"), (".", "escape.md"),
                            ("C:\\temp", "escape.md"), ("C:", "escape.md"), ("nul\x00", "escape.md"), ()))

    def test_write_never_replaces_a_different_file(self):
        parts = (".opencode", "skills", "one", "SKILL.md")
        self.assertIs(tool.write_confined_file(self.root, parts, b"first"), True)
        self.assertIs(tool.write_confined_file(self.root, parts, b"first"), False)
        for other in (b"other", b"first and more", b""):
            with self.subTest(other=other):
                with self.assertRaises(tool.InstallRefusal) as refused:
                    tool.write_confined_file(self.root, parts, other)
                self.assertEqual(refused.exception.code, "different_file_exists")
        self.assertEqual(self.root.joinpath(*parts).read_bytes(), b"first")

    def test_a_file_where_a_folder_belongs_and_a_folder_where_the_file_belongs_are_refused(self):
        (self.root / ".opencode").write_text("a file")
        with self.assertRaises(tool.InstallRefusal) as refused:
            tool.write_confined_file(self.root, (".opencode", "skills", "one", "SKILL.md"), b"x")
        self.assertEqual(refused.exception.code, "path_component_not_a_directory")
        (self.root / "folder" / "SKILL.md").mkdir(parents=True)
        with self.assertRaises(tool.InstallRefusal) as refused:
            tool.write_confined_file(self.root, ("folder", "SKILL.md"), b"x")
        self.assertEqual(refused.exception.code, "existing_path_not_a_regular_file")

    def test_bytes_that_are_not_text_are_refused(self):
        def offered(data):
            digest = hashlib.sha256(data).hexdigest()
            item = tool.OfferedItem("skill.bytes", "skill", "Purpose", digest, len(data), "MIT", True,
                                    "context_intelligence", "fixture:skill.bytes/v1", "host_attested")
            return item, tool.DownloadedBody(data, digest, tool.DOWNLOAD_RECORD_TYPE, 200)
        self.assertEqual(tool.verify_downloaded_body(*offered("café\n".encode())),
                         hashlib.sha256("café\n".encode()).hexdigest())
        with self.assertRaises(tool.InstallRefusal) as refused:
            tool.verify_downloaded_body(*offered(b"\xff\xfe not text"))
        self.assertEqual(refused.exception.code, "body_is_not_utf8_text")

    def test_bounds_outside_the_allowed_range_are_refused(self):
        for changes in ({"request_timeout_seconds": 0}, {"request_timeout_seconds": 601},
                        {"response_deadline_seconds": -1}, {"response_deadline_seconds": float("inf")},
                        {"maximum_json_bytes": 0}, {"maximum_body_bytes": True},
                        {"maximum_listing_bytes": -1}, {"listing_timeout_seconds": "30"}):
            with self.subTest(changes=changes):
                with self.assertRaises(tool.InstallRefusal) as refused:
                    tool.TransferLimits(**changes)
                self.assertEqual(refused.exception.code, "invalid_limits")
        limits = tool.TransferLimits()
        self.assertEqual((limits.request_timeout_seconds, limits.response_deadline_seconds), (30.0, 300.0))

    def test_a_platform_without_confined_file_operations_is_refused(self):
        # The tool opens every folder without following a link. A platform without that
        # is refused before any file access. This is the refusal that Windows would meet.
        with mock.patch.object(tool, "NO_FOLLOW_FLAG", None):
            with self.assertRaises(tool.InstallRefusal) as refused:
                tool.require_confined_file_operations()
        self.assertEqual(refused.exception.code, "confined_file_operations_unavailable")
        self.assertIsInstance(tool.require_confined_file_operations(), int)

    def test_native_names_follow_the_documented_rule(self):
        self.assertEqual(tool.native_name("skill.clean_supplier_names"), "skill-clean-supplier-names")
        self.assertEqual(tool.native_name("Skill.Alpha-2"), "skill-alpha-2")
        for identity in ("", "a..b", "-a", "a-", "a/b", "../x", "a b", "caf\u00e9", "a" * 65, None, "a.b" * 80):
            with self.subTest(identity=identity):
                with self.assertRaises(tool.InstallRefusal) as refused:
                    tool.native_name(identity)
                self.assertEqual(refused.exception.code, "identity_has_no_native_name")

    def test_generated_header_is_one_safe_line_and_bounded(self):
        header, truncated = tool.render_skill_header("one", 'Line one\nline: "two" # three\x00\u2028 end')
        self.assertEqual(header.decode(),
                         '---\nname: "one"\ndescription: "Line one line: \\"two\\" # three end"\n---\n')
        self.assertFalse(truncated)
        header, truncated = tool.render_skill_header("one", "x" * 3000)
        self.assertTrue(truncated)
        self.assertEqual(len(json.loads(header.decode().split("description: ", 1)[1].split("\n", 1)[0])), 1024)
        with self.assertRaises(tool.InstallRefusal):
            tool.render_skill_header("one", "\x00\n")

    def test_profile_refuses_a_model_turn_listing_command(self):
        profile = tool.OPENCODE_PROFILE
        self.assertNotIn("run", profile.listing.arguments + profile.version_arguments)
        for arguments in (("run", "list the skills"), ("debug", "run")):
            with self.subTest(arguments=arguments):
                with self.assertRaises(tool.InstallRefusal) as refused:
                    tool.ClientLayoutProfile(
                        client_kind=profile.client_kind, executable_name=profile.executable_name,
                        locations=profile.locations, unplaced_kinds=profile.unplaced_kinds,
                        listing=tool.ListingCommand(arguments=arguments),
                        version_arguments=profile.version_arguments,
                        model_turn_subcommands=profile.model_turn_subcommands,
                        observed_client_versions=profile.observed_client_versions)
                self.assertEqual(refused.exception.code, "model_turn_command_refused")

    def test_profile_names_every_served_kind_exactly_once(self):
        profile = tool.OPENCODE_PROFILE
        named = [location.served_kind for location in profile.locations] + [kind for kind, _ in profile.unplaced_kinds]
        self.assertEqual(sorted(named), sorted(KINDS))
        with self.assertRaises(tool.InstallRefusal):
            tool.ClientLayoutProfile(
                client_kind="opencode", executable_name="opencode", locations=profile.locations,
                unplaced_kinds=profile.unplaced_kinds[:-1], listing=profile.listing,
                version_arguments=profile.version_arguments,
                model_turn_subcommands=profile.model_turn_subcommands,
                observed_client_versions=profile.observed_client_versions)


REAL_CLIENT = shutil.which(tool.OPENCODE_PROFILE.executable_name)


@unittest.skipUnless(REAL_CLIENT, "the real client binary is not installed")
class RealClientListing(ServiceCase):
    """Optional: asks the installed client for its listing only. No model turn."""

    def test_real_client_reports_the_installed_skill_with_the_served_content(self):
        with running_http(self.fixture) as (base, _service):
            code, report, output = self.install(base, "--identity", "skill.review_inputs", "--identity", "2026",
                                                client=Path(REAL_CLIENT))
        item, numeric = report["items"]
        # A bare numeric name is dropped by the client. The generated header quotes the name.
        self.assertEqual((numeric["client_report"]["reported_name"], numeric["facts"]["reported_by_client"]),
                         ("2026", True))
        self.assertEqual(report["listing"]["state"], "observed", output)
        self.assertEqual(report["listing"]["command_arguments"], ["debug", "skill", "--pure"])
        self.assertEqual(item["client_report"], {
            "reported": True, "reported_name": "skill-review-inputs", "name_matches": True,
            "reported_content_sha256": hashlib.sha256(REVIEW_BODY.encode()).hexdigest(),
            "content_matches_served_body": True})
        self.assertEqual((code, report["model_turns_started"]), (0, 0))
        # Whatever the client itself added stays outside the installed skill folder and is shown.
        added = report["listing"]["paths_created_by_the_client_process"]
        self.assertIsInstance(added, list)
        self.assertFalse([path for path in added if path.startswith(".opencode/skills/")], added)

    def setUp(self):
        super().setUp()
        add_item(self.fixture, "2026", "skill", "A numeric identity.\n")
        grant(self.fixture, ("skill.review_inputs", "2026"))


@contextmanager
def _removed(name, replacement):
    with mock.patch.object(tool, name, replacement):
        yield


def _follow_links():
    return _removed("NO_FOLLOW_FLAG", 0)


def _truncating_report(path):
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    except OSError:
        raise tool.InstallRefusal(tool.RefusalCode.REPORT_PATH_NOT_USABLE) from None
    tool._write_report(descriptor, {"record_type": tool.REPORT_RECORD_TYPE, "complete": False})
    return descriptor


#: guard removed in memory -> the named check that must then fail.
MUTANTS = (
    ("header digest comparison", lambda: _removed("require_header_digest", lambda *_a, **_k: None),
     "InstallChecks.test_header_digest_mismatch_is_refused"),
    ("manifest digest comparison", lambda: _removed("require_manifest_digest", lambda *_a, **_k: None),
     "InstallChecks.test_body_that_differs_from_manifest_is_refused"),
    ("download status", lambda: _removed("require_download_status", lambda *_a, **_k: None),
     "InstallChecks.test_service_refusal_writes_nothing_and_keeps_its_code"),
    ("download record type", lambda: _removed("require_download_record_type", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_download_under_another_record_type_is_refused"),
    ("body permission before fetch", lambda: _removed("require_body_permitted", lambda *_a, **_k: None),
     "InstallChecks.test_body_the_key_may_not_read_is_refused_before_fetch"),
    ("identity to native name rule", lambda: _removed("native_name", lambda identity: identity),
     "InstallChecks.test_identity_without_native_name_is_refused_before_any_item_request"),
    ("traversal and absolute path refusal", lambda: _removed("validate_relative_parts", lambda *_a, **_k: None),
     "PathAndProfileChecks.test_traversal_and_absolute_parts_are_refused"),
    ("symbolic link refusal", _follow_links, "InstallChecks.test_symbolic_link_in_path_is_refused"),
    ("real target folder", lambda: _removed("real_target_directory", lambda target: target.resolve()),
     "InstallChecks.test_symbolic_link_in_path_is_refused"),
    ("different existing file before fetch", lambda: _removed("refuse_different_existing_file", lambda *_a, **_k: False),
     "InstallChecks.test_different_existing_file_is_refused_before_fetch"),
    ("identical file needs no read", lambda: _removed("refuse_different_existing_file", lambda *_a, **_k: False),
     "InstallChecks.test_identical_existing_file_is_accepted_without_another_read"),
    ("different existing file at write", lambda: _removed("require_identical_existing", lambda *_a, **_k: None),
     "PathAndProfileChecks.test_write_never_replaces_a_different_file"),
    ("reported comes from the client listing",
     lambda: _removed("listing_entry_for", lambda _entries, listing, path: {listing.location_field: path}),
     "InstallChecks.test_item_the_client_omits_is_not_reported"),
    ("key withheld from the client process",
     lambda: _removed("client_process_environment", lambda _name, settings: {**os.environ, **dict(settings)}),
     "InstallChecks.test_listing_process_never_receives_the_service_key"),
    ("new report path", lambda: _removed("reserve_report", _truncating_report),
     "InstallChecks.test_existing_report_is_refused_before_any_request"),
    ("key never on the command line", lambda: _removed("refuse_key_on_command_line", lambda *_a, **_k: None),
     "InstallChecks.test_key_is_taken_only_from_the_named_variable"),
    ("argument values are never repeated",
     lambda: mock.patch.object(tool.QuietArgumentParser, "error", argparse.ArgumentParser.error),
     "InstallChecks.test_key_is_taken_only_from_the_named_variable"),
    ("shortened options are refused", lambda: _removed("OPTION_ABBREVIATIONS_ALLOWED", True),
     "InstallChecks.test_key_is_taken_only_from_the_named_variable"),
    ("service contract handshake", lambda: _removed("require_supported_service", lambda _capabilities: 1 << 30),
     "InstallChecks.test_unsupported_service_capabilities_refuse_before_authenticated_requests"),
    ("redirect refusal",
     lambda: _removed("service_opener", lambda: urllib.request.build_opener(urllib.request.ProxyHandler({}))),
     "InstallChecks.test_redirect_is_refused_and_the_key_stays_with_the_named_origin"),
    ("environment proxies ignored",
     lambda: _removed("service_opener", lambda: urllib.request.build_opener(tool._RefuseRedirect())),
     "InstallChecks.test_proxy_settings_in_the_environment_are_ignored"),
    ("declared text format", lambda: _removed("require_declared_text_format", lambda *_a, **_k: None),
     "PathAndProfileChecks.test_bytes_that_are_not_text_are_refused"),
    ("model turn subcommand refusal", lambda: _removed("refuse_model_turn_subcommand", lambda *_a, **_k: None),
     "PathAndProfileChecks.test_profile_refuses_a_model_turn_listing_command"),
    ("manifest answers for the asked identity",
     lambda: _removed("require_manifest_identity", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_manifest_for_another_identity_is_refused"),
    ("manifest record version", lambda: _removed("require_manifest_record_type", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_manifest_of_another_record_version_is_refused"),
    ("download allowance before the read",
     lambda: _removed("require_within_download_allowance", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_manifest_that_declares_more_than_the_allowance_is_refused"),
    ("offer unchanged between search and manifest",
     lambda: _removed("require_offer_unchanged", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_an_offer_that_changed_between_the_search_and_the_manifest_is_refused"),
    ("manifest text that utf8 can carry", lambda: _removed("require_encodable_text", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_text_that_utf8_cannot_carry_is_refused_before_any_body_read"),
    ("nesting depth is a parse failure", lambda: _removed("JSON_PARSE_ERRORS", (ValueError,)),
     "ScriptedServiceChecks.test_a_service_record_nested_too_deeply_is_refused"),
    ("a listing that does not parse",
     lambda: _removed("parse_listing_entries", lambda data: json.loads(data.decode("utf-8"))),
     "InstallChecks.test_a_listing_that_is_nested_too_deeply_is_unknown"),
    ("capabilities body format", lambda: _removed("require_supported_body_format", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_capabilities_that_name_another_body_format_are_refused"),
    ("search returns references only", lambda: _removed("require_references_only", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_search_that_claims_to_have_loaded_bodies_is_refused"),
    ("bounded json response", lambda: _removed("require_bounded_response", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_json_response_over_the_bound_is_refused"),
    ("bounded read", lambda: _removed("read_bounded", lambda response, _bound, _deadline: response.read()),
     "ScriptedServiceChecks.test_a_body_longer_than_the_declared_size_stops_at_the_bound"),
    ("whole response deadline", lambda: _removed("require_within_deadline", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_response_that_arrives_too_slowly_is_refused"),
    ("pending fetch record before the read",
     lambda: _removed("record_pending_fetch", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_a_dropped_connection_keeps_the_request_identity_and_stays_unknown"),
    ("selection recorded before the first request",
     lambda: _removed("record_selection_before_any_request", lambda *_a, **_k: None),
     "ScriptedServiceChecks.test_the_report_names_the_selection_and_the_request_before_they_are_sent"),
    ("listing bound", lambda: _removed("listing_exceeds_bound", lambda *_a, **_k: False),
     "InstallChecks.test_a_listing_over_the_bound_is_unknown"),
    ("header of an existing file",
     lambda: _removed("existing_header_is_the_generated_one", lambda *_a, **_k: True),
     "InstallChecks.test_an_existing_file_under_another_header_of_the_same_length_is_refused"),
    ("name and content decide the headline fact",
     lambda: _removed("reported_with_same_name_and_content", lambda report: report["reported"] is True),
     "InstallChecks.test_changed_content_or_name_in_the_listing_does_not_pass"),
    ("the installed file is read again after the client process",
     lambda: _removed("installed_file_is_unchanged", lambda *_a, **_k: True),
     "InstallChecks.test_a_client_that_rewrites_the_installed_file_is_not_accepted"),
    ("placement is possible before the read",
     lambda: _removed("require_writable_placement", lambda *_a, **_k: None),
     "InstallChecks.test_a_target_that_cannot_take_the_file_is_refused_before_the_metered_read"),
    ("a location the platform cannot resolve",
     lambda: _removed("location_is_the_installed_file",
                      lambda location, wanted: isinstance(location, str) and os.path.isabs(location)
                      and os.path.realpath(location) == wanted),
     "InstallChecks.test_a_location_the_platform_cannot_resolve_is_no_match"),
    ("every character of the report is written as an escape",
     lambda: _removed("REPORT_ASCII_ONLY", False),
     "InstallChecks.test_a_name_that_utf8_cannot_carry_still_leaves_a_complete_report"),
    ("supported client registry version",
     lambda: _removed("require_supported_client_registry", lambda *_a, **_k: None),
     "InstallChecks.test_a_client_registry_version_this_tool_does_not_know_is_refused"),
    ("a preview makes no metered read and writes no file",
     lambda: _removed("preview_stops_here", lambda *_a, **_k: False),
     "InstallChecks.test_a_preview_reads_no_body_and_writes_no_file"),
    ("what is known when something unexpected stops the run",
     lambda: _removed("UNEXPECTED_ERRORS", (tool.InstallRefusal,)),
     "InstallChecks.test_an_error_outside_the_typed_refusals_keeps_what_is_already_known"),
)


def run_named_check(name: str) -> unittest.TestResult:
    result = unittest.TestResult()
    unittest.defaultTestLoader.loadTestsFromName(name, sys.modules[__name__]).run(result)
    return result


class MutantControls(unittest.TestCase):
    """Each guard is removed in memory. Its named check must pass before and fail after."""

    def test_each_removed_guard_fails_its_named_check(self):
        for guard, removal, check in MUTANTS:
            with self.subTest(guard=guard, check=check):
                intact = run_named_check(check)
                if intact.skipped:
                    # A skipped check proves nothing here. It is reported as skipped, not as passed.
                    self.skipTest("the named check is skipped on this machine: " + intact.skipped[0][1])
                self.assertTrue(intact.wasSuccessful() and intact.testsRun == 1, (intact.failures, intact.errors))
                with removal():
                    mutated = run_named_check(check)
                self.assertTrue(mutated.failures, "the check did not notice the removed guard: " + guard)
                self.assertEqual(mutated.errors, [], "the mutant crashed instead of failing an assertion")


if __name__ == "__main__":
    unittest.main()
