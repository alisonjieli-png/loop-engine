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
    entries.append({{"name": name, "description": "fixture", "location": str(path.resolve()), "content": content}})
rendered = json.dumps(entries)
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
        self.assertEqual(self.usage_records(), 3)
        self.assertEqual(report["summary"], {"selected": 3, "offered": 3, "fetched": 3, "installed": 3,
                                             "written_by_this_run": 3, "already_present_identical": 0,
                                             "reported_by_client": 3, "refused": 0})

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
                    observed = report["items"][0]["client_report"]
                    self.assertEqual((code, observed["reported"], observed[field]), (1, True, False))

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
            request = tool.InstallRequest(
                origin=base, key_variable=KEY_VARIABLE, client_kind="opencode", target=self.project,
                report=self.folder / "report.json", identities=("skill.alpha",), authorized=True,
                allow_loopback_http=True, client_command=(str(self.client),),
                limits=tool.TransferLimits(listing_timeout_seconds=1.0))
            descriptor = tool.reserve_report(request.report)
            try:
                report = tool.install_selected_material(request, self.key, descriptor)
            finally:
                os.close(descriptor)
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
                     ((), {}, "exactly_one_of_query_or_identities_required"),
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

    def test_client_kinds_come_from_the_recipes_registry(self):
        self.assertLessEqual(set(tool.CLIENT_LAYOUT_PROFILES), set(tool.registered_client_kinds()))
        with running_http(self.fixture) as (base, _service):
            for kind, expected in (("codex", "client_has_no_layout_profile"), ("unheard-of", "unknown_client_kind")):
                with self.subTest(kind=kind):
                    with self.assertRaises(tool.InstallRefusal) as refused:
                        tool.InstallRequest(origin=base, key_variable=KEY_VARIABLE, client_kind=kind,
                                            target=self.project, report=self.folder / "r.json",
                                            identities=("skill.alpha",), authorized=True, allow_loopback_http=True)
                    self.assertEqual(refused.exception.code, expected)

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
    ("download status and record type", lambda: _removed("require_successful_download", lambda *_a, **_k: None),
     "InstallChecks.test_service_refusal_writes_nothing_and_keeps_its_code"),
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
                self.assertTrue(intact.wasSuccessful() and intact.testsRun == 1, (intact.failures, intact.errors))
                with removal():
                    mutated = run_named_check(check)
                self.assertTrue(mutated.failures, "the check did not notice the removed guard: " + guard)
                self.assertEqual(mutated.errors, [], "the mutant crashed instead of failing an assertion")


if __name__ == "__main__":
    unittest.main()
