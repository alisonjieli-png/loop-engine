"""Fast checks for the container journey drill, with an injected command runner.

No Docker call is made here. A recorded runner answers every command the drill
sends, so one test run takes a second instead of several minutes.

Each mutant test removes one piece of service behaviour from the recorded
answers and states which named check must turn red. A check that still passes
without the behaviour it claims to prove would not be a check.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import check_client_journey_in_containers as drill  # noqa: E402
from loop_engine.core.service_runtime.http import ServiceHttpConfiguration  # noqa: E402
from loop_engine.core.service_runtime.http_entrypoint import public_binding_refusal  # noqa: E402
from loop_engine.core.service_runtime.request_limits import (  # noqa: E402
    HEADER_SOURCE, REQUEST_LIMITS_RECORD_TYPE)

REPOSITORY = Path(__file__).resolve().parents[1]
REPORT = Path("/nonexistent/container-journey-report.json")


def image_default_command():
    """The command the service image runs when it is started without one."""
    for line in (REPOSITORY / "Dockerfile.service").read_text("utf-8").splitlines():
        if line.startswith("CMD "):
            return json.loads(line[len("CMD "):])
    raise AssertionError("Dockerfile.service names no default command")


def refusal_of_the_image_command(host):
    """What the service's own start rule says about this host file under the image's command.

    The server container runs the image's default command, so the binding and
    the trusted proxy flag are read from the Dockerfile, and the address
    statement is read by the service's own transport settings record.
    """
    arguments = image_default_command()
    transport = ServiceHttpConfiguration(**host["http"])
    return public_binding_refusal(arguments[arguments.index("--host") + 1],
                                  "--behind-trusted-tls-proxy" in arguments, transport.request_limits)


def settings(**changes):
    base = {"repository": REPOSITORY, "report": REPORT, "resource_prefix": "journey-drill-test",
            "image_reference": "loop-engine-service:journey-drill-test",
            "first_tenant": drill.TenantPlan("first-tenant", "first-tenant:private", drill.FIRST_TENANT_VARIABLE),
            "second_tenant": drill.TenantPlan("second-tenant", "second-tenant:private", drill.SECOND_TENANT_VARIABLE),
            "ready_timeout_seconds": 1.0}
    base.update(changes)
    return drill.DrillSettings(**base)


FIRST_KEY = "le_first-tenant-key-value-that-never-reaches-a-report"
SECOND_KEY = "le_second-tenant-key-value-that-never-reaches-a-report"
DRILL_KEY = "le_revocation-drill-key-value-that-never-reaches-a-report"


class RecordedDocker:
    """Answer every docker command of one drill from a prepared world.

    The world holds the served bodies and the rules the service applies. A
    mutant test changes one rule and nothing else.
    """

    def __init__(self, selection, *, world=None):
        self.selection = selection
        self.calls = []
        self.deadlines = []
        self.environments = []
        self.created = {"container": [], "volume": [], "network": [], "image": []}
        self.removed = {"container": [], "volume": [], "network": [], "image": []}
        self.bodies = {}
        self.digests = {}
        for row in selection.registered:
            body = (REPOSITORY / drill.CATALOGUE_DIRECTORY / row["body_path"]).read_bytes()
            self.bodies[row["reference"]["identity"]] = body
            self.digests[row["reference"]["identity"]] = row["reference"]["digest"]
        self.installed = {}
        self.usage = 0.0
        self.revoked = set()
        self.tampered = set()
        # The host file the drill seeded, and every container whose own command
        # stopped before it served anyone.
        self.host_file = None
        self.stopped = set()
        self.world = {
            "network_internal": True, "has_default_route": False, "resolves_external_name": False,
            "refuses_without_a_key": True, "serves_the_correct_body": True,
            "refuses_the_other_tenants_item": True, "refuses_a_revoked_key": True,
            "refuses_a_tampered_body": True, "keeps_usage_across_a_restart": True,
            "installs_the_served_body": True, "refuses_plain_http_to_a_non_loopback_host": True,
            "refuses_an_unknown_licence": True, "the_client_lists_installed_material": True,
            "refuses_an_unexpected_host": True, "serves_the_supported_record_versions": True,
            "the_client_listing_avoids_a_model_turn": True,
            "client_listing_state": drill.OBSERVED_LISTING_STATE,
        }
        self.world.update(world or {})

    # -- the runner interface ---------------------------------------------

    def __call__(self, arguments, *, timeout, input_text=None, environment=None):
        arguments = list(arguments)
        self.calls.append(arguments)
        self.deadlines.append(timeout)
        self.environments.append(environment)
        assert arguments[0] == "docker", arguments[0]
        stdout = self._answer(arguments[1:], input_text)
        if stdout is None:
            return drill.CommandResult(tuple(arguments), 1, "", "unknown command")
        if isinstance(stdout, tuple):
            code, stdout, stderr = stdout
            return drill.CommandResult(tuple(arguments), code, stdout, stderr)
        return drill.CommandResult(tuple(arguments), 0, stdout, "")

    # -- answering ---------------------------------------------------------

    def _answer(self, arguments, input_text):
        head = arguments[0]
        if head == "build":
            self.created["image"].append(arguments[arguments.index("--tag") + 1])
            return "built"
        if head == "image" and arguments[1] == "inspect":
            return "sha256:" + "1" * 64
        if head == "image" and arguments[1] == "rm":
            self.removed["image"].append(arguments[2])
            return "untagged"
        if head == "volume" and arguments[1] == "create":
            self.created["volume"].append(arguments[-1])
            return arguments[-1]
        if head == "volume" and arguments[1] == "rm":
            self.removed["volume"].append(arguments[2])
            return arguments[2]
        if head == "network" and arguments[1] == "create":
            self.created["network"].append(arguments[-1])
            return arguments[-1]
        if head == "network" and arguments[1] == "inspect":
            return "true" if self.world["network_internal"] else "false"
        if head == "network" and arguments[1] == "rm":
            self.removed["network"].append(arguments[2])
            return arguments[2]
        if head == "rm":
            self.removed["container"].append(arguments[2])
            return arguments[2]
        if head == "restart":
            if not self.world["keeps_usage_across_a_restart"]:
                self.usage = 0.0
            return arguments[1]
        if head == "run":
            return self._run(arguments, input_text)
        if head == "exec":
            return self._exec(arguments, input_text)
        return None

    def _run(self, arguments, input_text):
        if "--detach" in arguments:
            name = arguments[arguments.index("--name") + 1]
            self.created["container"].append(name)
            # A container started without its own entry point runs the image's
            # default command, which applies the service's start rule to the
            # seeded host file and stops before serving anyone when it refuses.
            if "--entrypoint" not in arguments and (self.host_file is None
                                                    or refusal_of_the_image_command(self.host_file)):
                self.stopped.add(name)
            return "container-" + name
        return self._step(arguments, input_text)

    @staticmethod
    def _exec_target(arguments):
        """The container a docker exec names, after its options."""
        index = 1
        while arguments[index].startswith("-"):
            index += 2 if arguments[index] == "--user" else 1
        return arguments[index]

    def _exec(self, arguments, input_text):
        if self._exec_target(arguments) in self.stopped:
            return (1, "", "container is not running")
        if "loop-engine" in arguments and "issue-key" in arguments:
            tenant = arguments[arguments.index("--tenant") + 1]
            label = arguments[arguments.index("--label") + 1]
            key = DRILL_KEY if label == "revocation drill" else (
                FIRST_KEY if tenant == "first-tenant" else SECOND_KEY)
            return json.dumps({"record_type": "issued_service_key/v1", "tenant_id": tenant,
                               "key_id": hashlib.sha256(key.encode()).hexdigest()[:32],
                               "key": key, "expires_at": None})
        if "loop-engine" in arguments and "configure" in arguments:
            return json.dumps({"record_type": "service_host_setup/v1",
                               "tenants": ["first-tenant", "second-tenant"],
                               "configured_grant_sets": 2, "remote_accounts_created": False})
        if any(argument.endswith("install_selected_material.py") for argument in arguments):
            return self._install(arguments)
        if "cat" in arguments:
            return json.dumps(self._install_report())
        if "--detach" in arguments:
            return "forwarder"
        return self._step(arguments, input_text)

    # -- one step script ---------------------------------------------------

    def _step(self, arguments, input_text):
        step = arguments[-1]
        plan = json.loads(input_text) if input_text else {}
        if step in ("seed-server-volume",):
            self.artifact_root = "/data/artifacts"
            self.host_file = plan["host"]
            return json.dumps({"step": step, "registered_items": len(plan["items"]),
                               "artifact_root": self.artifact_root})
        if step == "seed-client-volume":
            return json.dumps({"step": step, "folders": plan["folders"], "entries": sorted(plan["folders"])})
        if step == "licence-refusal":
            refused = self.world["refuses_an_unknown_licence"]
            return json.dumps({"step": step, "declared_license": plan["item"]["reference"]["license"],
                               "refused": refused, "code": "item_license_unknown" if refused else None})
        if step == "network-facts":
            return json.dumps({"step": step, "has_default_route": self.world["has_default_route"],
                               "external_name": plan["external_name"],
                               "resolved_to": "203.0.113.7" if self.world["resolves_external_name"] else None,
                               "resolution_error": None if self.world["resolves_external_name"] else "gaierror"})
        if step == "revoke-key":
            self.revoked.add(plan["key_id"])
            return json.dumps({"step": step, "committed": True, "key_id": plan["key_id"], "revoked": True})
        if step in ("tamper-body", "restore-body"):
            identity = plan["identity"]
            if plan["action"] == "tamper":
                self.tampered.add(identity)
            else:
                self.tampered.discard(identity)
            body = self.bodies[identity]
            served = body if plan["action"] == "restore" else body[:-1] + b"X"
            return json.dumps({"step": step, "action": plan["action"], "size_bytes": len(served),
                               "sha256": hashlib.sha256(served).hexdigest()})
        if step == "read-installed":
            return json.dumps({"step": step, "files": self._installed_files(plan["installed"]),
                               "all_paths": sorted(self.installed)})
        return self._probe(step, plan)

    def _installed_files(self, records):
        rows = []
        for record in records:
            content = self.installed.get(record["path"])
            present = content is not None
            served = content[record["body_offset_bytes"]:] if present else b""
            rows.append({"identity": record["identity"], "path": record["path"], "present": present,
                         "file_bytes": len(content) if present else 0,
                         "file_sha256": hashlib.sha256(content).hexdigest() if present else None,
                         "served_body_sha256": hashlib.sha256(served).hexdigest() if present else None,
                         "served_body_bytes": len(served)})
        return rows

    # -- the service -------------------------------------------------------

    def _grants(self, tenant):
        first = {row["reference"]["identity"] for row in self.selection.first_tenant_only}
        second = {row["reference"]["identity"] for row in self.selection.second_tenant_only}
        shared = {row["reference"]["identity"] for row in self.selection.shared}
        return (first if tenant == "first-tenant" else second) | shared

    def _tenant_of(self, variable):
        return {drill.FIRST_TENANT_VARIABLE: "first-tenant", drill.SECOND_TENANT_VARIABLE: "second-tenant",
                drill.REVOCATION_DRILL_VARIABLE: "first-tenant"}[variable]

    def _key_of(self, variable):
        return {drill.FIRST_TENANT_VARIABLE: FIRST_KEY, drill.SECOND_TENANT_VARIABLE: SECOND_KEY,
                drill.REVOCATION_DRILL_VARIABLE: DRILL_KEY}[variable]

    def _probe(self, step, plan):
        answers = {}
        for case in plan.get("cases", []):
            answers[case["name"]] = self._one_request(case)
        return json.dumps({"step": step, "answers": answers})

    def _served_version(self, supported: str) -> str:
        """The record version the service serves, or another one in the mutant."""
        if self.world["serves_the_supported_record_versions"]:
            return supported
        name, _, version = supported.rpartition("/")
        return f"{name}/{version}-changed"

    def _one_request(self, case):
        answer = self._answered(case)
        result = answer.get("result")
        answer.setdefault("record_type", result.get("record_type") if isinstance(result, dict) else None)
        return answer

    def _answered(self, case):
        route, variable = case["route"], case.get("key_variable")
        if case.get("host") is not None and self.world["refuses_an_unexpected_host"]:
            return {"status": 421, "code": "invalid_host", "result": None}
        if route == "/api/v1/health":
            return {"status": 200, "code": None,
                    "result": {"record_type": self._served_version("service_health/v2"), "alive": True,
                               "ready": True, "readiness_checked": True}}
        if variable is None:
            if self.world["refuses_without_a_key"]:
                return {"status": 401, "code": "unauthorized", "result": None}
            # A service that hands the same material to a caller with no key at
            # all. The route is answered as if the first tenant had asked.
            variable = drill.FIRST_TENANT_VARIABLE
        key_id = hashlib.sha256(self._key_of(variable).encode()).hexdigest()[:32]
        if key_id in self.revoked and self.world["refuses_a_revoked_key"]:
            return {"status": 401, "code": "unauthorized", "result": None}
        tenant = self._tenant_of(variable)
        if route == "/api/v1/usage":
            return {"status": 200, "code": None,
                    "result": {"record_type": "durable_tenant_usage/v1", "tenant_id": tenant,
                               "records": int(self.usage), "totals": {"provisioned_item": self.usage},
                               "durability": "durable"}}
        if route == "/api/v1/retrieval":
            hits = [{"reference": {"identity": identity}} for identity in sorted(self._grants(tenant))]
            return {"status": 200, "code": None,
                    "result": {"record_type": self._served_version("service_retrieval_result/v1"), "hits": hits}}
        identity = case["payload"]["identity"]
        if identity not in self._grants(tenant) and self.world["refuses_the_other_tenants_item"]:
            return {"status": 404, "code": "item_unavailable", "result": None}
        if identity not in self.bodies:
            return {"status": 404, "code": "item_unavailable", "result": None}
        body, digest = self.bodies[identity], self.digests[identity]
        if route == "/api/v1/provisioning":
            return {"status": 200, "code": None,
                    "result": {"record_type": self._served_version("provisioning_manifest/v2"),
                               "tenant_id": tenant, "identity": identity, "digest": digest,
                               "size_bytes": len(body), "kind": drill.SERVED_KIND, "body_allowed": True}}
        if identity in self.tampered:
            if self.world["refuses_a_tampered_body"]:
                return {"status": 400, "code": "body_integrity_failed", "result": None}
            body = body[:-1] + b"X"
        if not self.world["serves_the_correct_body"]:
            body = body + b"extra"
        self.usage += 1
        return {"status": 200, "code": None, "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body), "digest_header": hashlib.sha256(body).hexdigest(),
                "record_type_header": self._served_version("service_download/v1")}

    # -- the install tool --------------------------------------------------

    def _install(self, arguments):
        origin = arguments[arguments.index("--origin") + 1]
        if not origin.startswith(drill.PRIVATE_NETWORK_SCHEME + drill.LOOPBACK_ADDRESS):
            if self.world["refuses_plain_http_to_a_non_loopback_host"]:
                return (2, "", json.dumps({"refused": "invalid_origin", "detail": ""}))
            return (0, json.dumps({"record_type": drill.INSTALL_REPORT_RECORD_TYPE}), "")
        self._records = []
        for index, argument in enumerate(arguments):
            if argument == "--identity":
                identity = arguments[index + 1]
                body = self.bodies[identity]
                if not self.world["installs_the_served_body"]:
                    body = body + b"\n"
                header = ("---\nname: " + json.dumps(identity.replace("_", "-")) + "\n---\n").encode("utf-8")
                path = drill.NATIVE_LAYOUT_PREFIX + "/" + identity.replace("_", "-") + "/SKILL.md"
                self.installed[path] = header + body
                self.usage += 1
                self._records.append({"record_type": "native_material_install_record/v1", "identity": identity,
                                      "kind": drill.SERVED_KIND, "native_name": identity.replace("_", "-"),
                                      "body_sha256": self.digests[identity],
                                      "body_bytes": len(self.bodies[identity]), "path": path,
                                      "file_sha256": hashlib.sha256(header + body).hexdigest(),
                                      "file_bytes": len(header + body), "body_offset_bytes": len(header),
                                      "written_by_this_run": True, "already_present_identical": False,
                                      "file_unchanged_at_end_of_run": True})
        return json.dumps({"installed": len(self._records)})

    def _install_report(self):
        listed = self.world["the_client_lists_installed_material"]
        state = self.world["client_listing_state"]
        observed = state == drill.OBSERVED_LISTING_STATE
        # The arguments the install tool records for the client process it ran.
        # Without a listing there is no client process and no arguments at all.
        arguments = list(drill.EXPECTED_LISTING_ARGUMENTS)
        if not self.world["the_client_listing_avoids_a_model_turn"]:
            arguments = [drill.MODEL_TURN_SUBCOMMANDS[0], "--model", "a-model-name"]
        return {"record_type": drill.INSTALL_REPORT_RECORD_TYPE, "complete": True, "mode": "install",
                "service_refusal": None, "model_turns_started": 0,
                "items": [{"identity": record["identity"], "install": record,
                           "facts": {"offered": True, "fetched": True, "installed": True,
                                     "reported_by_client": listed}, "refusal": None,
                           "client_report": None} for record in self._records],
                "listing": {"record_type": "native_client_listing_observation/v1", "client_kind": drill.CLIENT_KIND,
                            "state": state, "model_turns_started": 0, "client_version": "1.18.31",
                            "layout_observed_with_this_version": True,
                            "command_arguments": arguments if observed else None,
                            "entries": len(self._records)},
                "summary": {"selected": len(self._records), "offered": len(self._records),
                            "fetched": len(self._records), "installed": len(self._records),
                            "written_by_this_run": len(self._records), "already_present_identical": 0,
                            "listed_at_installed_path": len(self._records) if listed else 0,
                            "reported_by_client": len(self._records) if listed else 0, "refused": 0},
                "all_selected_installed_and_reported": listed and observed}


def run_with(world=None, **changes):
    chosen = settings(**changes)
    selection = drill.select_catalogue_items(chosen.catalogue, chosen.accepted_licenses)
    runner = RecordedDocker(selection, world=world)
    report = drill.run_drill(chosen, runner)
    return report, runner


def failing(report):
    return sorted(row["name"] for row in report["checks"] if not row["passed"])


class DrillRecordTest(unittest.TestCase):
    """The typed settings refuse an unsupported request before any effect."""

    def test_an_unsupported_settings_record_version_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            settings(record_type="client_journey_drill_settings/v2")
        self.assertEqual(caught.exception.code, "unsupported_drill_settings")

    def test_an_unsupported_tenant_plan_version_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            drill.TenantPlan("first-tenant", "first-tenant:private", drill.FIRST_TENANT_VARIABLE,
                             record_type="client_journey_tenant_plan/v2")
        self.assertEqual(caught.exception.code, "unsupported_tenant_plan")

    def test_two_tenants_that_are_the_same_are_refused(self):
        same = drill.TenantPlan("first-tenant", "first-tenant:private", drill.FIRST_TENANT_VARIABLE)
        with self.assertRaises(drill.DrillRefusal) as caught:
            settings(second_tenant=same)
        self.assertEqual(caught.exception.code, "the_two_tenants_must_differ")

    def test_a_relative_report_path_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            settings(report=Path("report.json"))
        self.assertEqual(caught.exception.code, "report_must_be_an_absolute_path")

    def test_a_licence_state_cannot_be_an_accepted_licence(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            settings(accepted_licenses=("MIT", "MIT"))
        self.assertEqual(caught.exception.code, "invalid_accepted_licenses")

    def test_a_command_result_of_an_unknown_version_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            drill.CommandResult(("docker",), 0, record_type="client_journey_command_result/v2")
        self.assertEqual(caught.exception.code, "unsupported_command_result")

    def test_a_command_without_a_deadline_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            drill.SubprocessCommandRunner()(("true",), timeout=None)
        self.assertEqual(caught.exception.code, "command_needs_a_deadline")

    def test_a_port_outside_the_supported_range_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            settings(service_port=0)
        self.assertEqual(caught.exception.code, "invalid_port")

    def test_a_declared_public_base_url_without_https_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            settings(declared_public_base_url="http://client-journey-drill.invalid")
        self.assertEqual(caught.exception.code, "declared_public_base_url_must_be_an_https_origin")

    def test_the_settings_record_owns_every_address_the_drill_uses(self):
        chosen = settings()
        self.assertEqual(chosen.server_host, "journey-drill-test-server:8080")
        self.assertEqual(chosen.loopback_host, "127.0.0.1:8080")
        self.assertEqual(chosen.server_origin, "http://journey-drill-test-server:8080")
        self.assertEqual(chosen.loopback_origin, "http://127.0.0.1:8080")
        self.assertEqual(chosen.declared_public_host, "client-journey-drill.invalid")

    def test_the_host_configuration_allows_exactly_the_hosts_the_drill_sends(self):
        chosen = settings()
        allowed = drill.host_configuration(chosen, 1)["http"]["allowed_hosts"]
        self.assertEqual(allowed, [chosen.declared_public_host, chosen.server_host, chosen.loopback_host])

    def test_a_client_address_header_the_service_would_refuse_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            settings(client_address_header="Not A Header")
        self.assertEqual(caught.exception.code, "invalid_client_address_header")

    def test_the_host_configuration_states_where_each_callers_address_comes_from(self):
        stated = drill.host_configuration(settings(), 1)["http"]["request_limits"]
        self.assertEqual(stated, {"record_type": REQUEST_LIMITS_RECORD_TYPE, "client_address_source": HEADER_SOURCE,
                                  "client_address_header": drill.CLIENT_ADDRESS_HEADER})

    def test_the_image_command_serves_this_host_configuration_only_with_the_statement(self):
        """The service's own start rule accepts the drill's host file and refuses it without the statement.

        The known-wrong case is the same file with the client address
        statement removed. The image's command must refuse it and name the
        missing setting, or the drill's own host file would prove nothing.
        """
        configuration = drill.host_configuration(settings(), 1)
        self.assertEqual(refusal_of_the_image_command(configuration), "")
        del configuration["http"]["request_limits"]
        self.assertIn("request_limits", refusal_of_the_image_command(configuration))


class SchemeVocabularyTest(unittest.TestCase):
    """The drill reads its address vocabulary from the service, not from itself."""

    def test_the_schemes_come_from_the_service_address_owner(self):
        secure, plain, supported = drill.schemes_the_service_accepts()
        self.assertEqual((secure, plain), (drill.SECURE_SCHEME, drill.PLAIN_SCHEME))
        self.assertEqual(sorted(supported), sorted(drill.SUPPORTED_SCHEMES))
        for prefix in supported:
            self.assertTrue(prefix.endswith(drill.SCHEME_SEPARATOR), prefix)
        self.assertIn(secure, supported)
        self.assertIn(plain, supported)
        self.assertTrue(drill.address_the_service_accepts(drill.DECLARED_PUBLIC_BASE_URL))
        self.assertFalse(drill.address_the_service_accepts(plain + drill.UNRESOLVABLE_DRILL_NAME))

    def test_an_owner_that_accepts_every_scheme_everywhere_is_refused(self):
        with self.assertRaises(drill.DrillRefusal) as caught:
            drill.schemes_the_service_accepts(validate=lambda value, *, permit_loopback=False: value)
        self.assertEqual(caught.exception.code,
                         "the_service_address_owner_declares_an_unreadable_scheme_vocabulary")

    def test_an_owner_that_accepts_no_scheme_at_all_is_refused(self):
        def refuse(value, *, permit_loopback=False):
            raise ValueError("no scheme is accepted")

        with self.assertRaises(drill.DrillRefusal) as caught:
            drill.schemes_the_service_accepts(validate=refuse)
        self.assertEqual(caught.exception.code,
                         "the_service_address_owner_declares_an_unreadable_scheme_vocabulary")

    def test_the_private_network_address_is_the_one_the_install_tool_refuses(self):
        """This is why the client container forwards a local port to the server."""
        chosen = settings()
        self.assertTrue(drill.address_the_service_accepts(chosen.loopback_origin, permit_loopback=True))
        self.assertFalse(drill.address_the_service_accepts(chosen.server_origin, permit_loopback=True))


class CatalogueBodyPathTest(unittest.TestCase):
    """A row that names a body outside the catalogue is refused before any container."""

    def select(self, body_path):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            catalogue = root / "catalogue"
            (catalogue / "bodies").mkdir(parents=True)
            body = catalogue / "bodies" / "one.md"
            body.write_bytes(b"one reviewed body\n")
            (root / "outside.md").write_bytes(b"a file the catalogue does not own\n")
            if body_path == "bodies/link.md":
                (catalogue / "bodies" / "link.md").symlink_to(root / "outside.md")
            row = {"reference": {"identity": "one_item", "kind": drill.SERVED_KIND, "license": "MIT",
                                 "digest": hashlib.sha256(body.read_bytes()).hexdigest(),
                                 "size_bytes": len(body.read_bytes())},
                   "body_path": body_path}
            (catalogue / drill.CATALOGUE_ITEMS_FILE).write_text(json.dumps({"items": [row]}), encoding="utf-8")
            return drill.select_catalogue_items(catalogue, ("MIT",))

    def refusal_for(self, body_path):
        with self.assertRaises(drill.DrillRefusal) as caught:
            self.select(body_path)
        return caught.exception.code

    def test_a_body_inside_the_catalogue_passes_the_path_check(self):
        """The known-good case reaches the later count check, so the path was accepted."""
        self.assertEqual(self.refusal_for("bodies/one.md"), "catalogue_has_too_few_accepted_items")

    def test_a_body_path_that_climbs_out_of_the_catalogue_is_refused(self):
        self.assertEqual(self.refusal_for("../outside.md"), "catalogue_body_path_is_not_confined")

    def test_a_body_path_that_is_a_link_out_of_the_catalogue_is_refused(self):
        self.assertEqual(self.refusal_for("bodies/link.md"), "catalogue_body_path_is_not_confined")

    def test_an_absolute_body_path_is_refused(self):
        self.assertEqual(self.refusal_for("/etc/hostname"), "catalogue_body_path_is_not_confined")

    def test_a_body_path_that_names_no_file_is_refused(self):
        self.assertEqual(self.refusal_for("bodies/missing.md"), "catalogue_body_path_is_not_confined")

    def test_a_body_path_that_is_not_text_is_refused(self):
        self.assertEqual(self.refusal_for(None), "catalogue_body_path_is_not_supported")


class ReportReservationTest(unittest.TestCase):
    """The report name is taken before the drill starts, not after it finishes."""

    def test_the_report_name_is_taken_before_the_drill_starts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "container-journey.json"
            descriptor = drill.reserve_report(path)
            try:
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                                 {"record_type": drill.REPORT_RECORD_TYPE, "complete": False})
                with self.assertRaises(drill.DrillRefusal) as caught:
                    drill.reserve_report(path)
                self.assertEqual(caught.exception.code, "report_path_exists")
                drill.write_reserved_report(descriptor, {"record_type": drill.REPORT_RECORD_TYPE, "all_passed": True})
                self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["all_passed"])
            finally:
                os.close(descriptor)

    def test_a_shorter_report_leaves_no_tail_of_a_longer_one(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "container-journey.json"
            descriptor = drill.reserve_report(path)
            try:
                drill.write_reserved_report(descriptor, {"record_type": drill.REPORT_RECORD_TYPE,
                                                         "detail": "x" * 4000})
                drill.write_reserved_report(descriptor, {"record_type": drill.REPORT_RECORD_TYPE})
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                                 {"record_type": drill.REPORT_RECORD_TYPE})
            finally:
                os.close(descriptor)

    def test_a_report_path_whose_folder_does_not_exist_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(drill.DrillRefusal) as caught:
                drill.reserve_report(Path(folder) / "no-such-folder" / "report.json")
            self.assertEqual(caught.exception.code, "report_path_is_not_usable")


class CatalogueSelectionTest(unittest.TestCase):
    """The drill takes real catalogue rows and checks them before any container."""

    def setUp(self):
        self.settings = settings()
        self.selection = drill.select_catalogue_items(self.settings.catalogue, self.settings.accepted_licenses)

    def test_every_registered_body_matches_its_reference(self):
        for row in self.selection.registered:
            body = (REPOSITORY / drill.CATALOGUE_DIRECTORY / row["body_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), row["reference"]["digest"])
            self.assertEqual(len(body), row["reference"]["size_bytes"])

    def test_the_two_tenants_are_offered_different_items(self):
        first = self.selection.offered_to("first-tenant", self.settings)
        second = self.selection.offered_to("second-tenant", self.settings)
        self.assertNotEqual(set(first), set(second))
        self.assertTrue(set(first) & set(second), "the drill needs at least one shared item")

    def test_the_selection_keeps_one_item_whose_licence_is_not_accepted(self):
        self.assertIsNotNone(self.selection.refused_license)
        self.assertNotIn(self.selection.refused_license["reference"]["license"], self.settings.accepted_licenses)

    def test_the_tamper_target_is_not_installed(self):
        self.assertNotIn(self.selection.tamper_target, self.selection.install_identities)

    def test_every_grant_requires_metering(self):
        rows = drill.manifest_rows(self.selection, self.settings)
        self.assertTrue(rows)
        for row in rows:
            for grant in row["grants"]:
                self.assertEqual(grant["metering"], drill.REQUIRED_METERING)

    def test_the_host_configuration_names_both_tenants_and_no_credential(self):
        configuration = drill.host_configuration(self.settings, 1)
        self.assertEqual([row["tenant_id"] for row in configuration["tenants"]],
                         ["first-tenant", "second-tenant"])
        text = json.dumps(configuration)
        for key in (FIRST_KEY, SECOND_KEY, DRILL_KEY):
            self.assertNotIn(key, text)
        self.assertNotIn("le_", text)


class HealthyRunTest(unittest.TestCase):
    """With every behaviour in place, the drill passes and cleans up."""

    @classmethod
    def setUpClass(cls):
        cls.report, cls.runner = run_with()

    def test_every_check_passes(self):
        self.assertEqual(failing(self.report), [])
        self.assertTrue(self.report["all_passed"])
        self.assertIsNone(self.report["failure"])

    def test_the_image_command_serves_the_host_file_the_drill_seeded(self):
        self.assertIsNotNone(self.runner.host_file)
        self.assertEqual(self.runner.stopped, set())

    def test_offered_fetched_installed_and_verified_are_separate_facts(self):
        facts = self.report["facts"]
        for name in ("registered_in_the_host_manifest", "offered_to_the_first_tenant", "selected_for_install",
                     "fetched_by_the_install_run", "installed_in_the_native_client_layout",
                     "verified_against_the_served_digest", "reported_by_the_client"):
            self.assertIn(name, facts)
        self.assertGreater(facts["registered_in_the_host_manifest"], facts["offered_to_the_first_tenant"])
        self.assertGreater(facts["offered_to_the_first_tenant"], facts["selected_for_install"])
        self.assertEqual(facts["verified_against_the_served_digest"], facts["selected_for_install"])

    def test_a_declared_value_never_sits_among_the_observed_facts(self):
        """A number nobody measured belongs in the declared block, not in the facts."""
        facts, declared = self.report["facts"], self.report["declared"]
        for name in ("model_turns_started", "provider_requests", "credentials_in_this_report"):
            self.assertNotIn(name, facts)
            self.assertEqual(declared[name], 0)
        self.assertEqual(declared["record_type"], drill.DECLARED_RECORD_TYPE)
        self.assertIn("not measured", declared["basis"])

    def test_the_report_names_the_image_identity_and_the_source_hashes(self):
        self.assertTrue(self.report["image_identity"].startswith("sha256:"))
        self.assertEqual(sorted(self.report["source_files"]), sorted(drill.SOURCE_FILES))
        for value in self.report["source_files"].values():
            self.assertTrue(drill.DIGEST_PATTERN.fullmatch(value))

    def test_no_key_value_reaches_the_report(self):
        text = json.dumps(self.report)
        for key in (FIRST_KEY, SECOND_KEY, DRILL_KEY):
            self.assertNotIn(key, text)
        self.assertEqual(self.report["declared"]["credentials_in_this_report"], 0)

    def test_no_key_value_reaches_a_command_line(self):
        for arguments in self.runner.calls:
            joined = " ".join(arguments)
            for key in (FIRST_KEY, SECOND_KEY, DRILL_KEY):
                self.assertNotIn(key, joined)

    def test_a_key_reaches_a_container_by_variable_name_only(self):
        started = [row for row in self.runner.calls if row[1:2] == ["run"] and "--detach" in row]
        client = [row for row in started if row[row.index("--name") + 1].endswith("-client")][0]
        self.assertIn(drill.FIRST_TENANT_VARIABLE, client)
        self.assertNotIn(drill.SECOND_TENANT_VARIABLE, client)
        self.assertNotIn(drill.REVOCATION_DRILL_VARIABLE, client)

    def test_the_other_keys_stay_out_of_the_container_that_runs_the_client(self):
        started = [row for row in self.runner.calls if row[1:2] == ["run"] and "--detach" in row]
        other = [row for row in started if "other-tenant-client" in row[row.index("--name") + 1]][0]
        self.assertIn(drill.SECOND_TENANT_VARIABLE, other)
        self.assertIn(drill.REVOCATION_DRILL_VARIABLE, other)
        self.assertNotIn(drill.FIRST_TENANT_VARIABLE, other)

    def test_every_docker_call_carries_a_deadline(self):
        self.assertTrue(self.runner.deadlines)
        for deadline in self.runner.deadlines:
            self.assertIsInstance(deadline, (int, float))
            self.assertGreater(deadline, 0)

    def test_every_created_resource_was_removed_and_nothing_else(self):
        for kind in ("container", "volume", "network", "image"):
            self.assertTrue(self.runner.created[kind], kind)
            self.assertEqual(sorted(self.runner.created[kind]), sorted(self.runner.removed[kind]), kind)
        self.assertEqual(self.report["cleanup"]["still_present"], [])

    def test_every_created_name_carries_the_prefix_of_this_run(self):
        prefix = self.report["settings"]["resource_prefix"]
        for kind in ("container", "volume", "network"):
            for name in self.runner.created[kind]:
                self.assertTrue(name.startswith(prefix), name)
        for name in self.runner.created["image"]:
            self.assertIn(prefix, name)

    def test_the_private_network_is_created_without_external_connectivity(self):
        created = [row for row in self.runner.calls if row[1:3] == ["network", "create"]]
        self.assertEqual(len(created), 1)
        self.assertIn("--internal", created[0])

    def test_the_drill_never_runs_a_client_subcommand_that_starts_a_model_turn(self):
        for arguments in self.runner.calls:
            for subcommand in drill.MODEL_TURN_SUBCOMMANDS:
                self.assertNotIn(f"{drill.CLIENT_KIND} {subcommand}", " ".join(arguments))
            self.assertNotIn("--model", arguments)
        self.assertEqual(self.report["declared"]["model_turns_started"], 0)
        self.assertEqual(self.report["declared"]["provider_requests"], 0)

    def test_the_client_command_the_install_run_recorded_is_the_listing_command(self):
        recorded = self.report["observations"]["client_commands_the_install_run_recorded"]
        self.assertEqual(recorded, [drill.EXPECTED_LISTING_ARGUMENTS])
        self.assertEqual(self.report["observations"]["install"]["client_command_arguments"],
                         drill.EXPECTED_LISTING_ARGUMENTS)
        for command in recorded:
            self.assertFalse(set(command) & set(drill.MODEL_TURN_SUBCOMMANDS))

    def test_the_served_record_versions_are_read_back_and_named(self):
        served = self.report["observations"]["served_record_types"]
        self.assertEqual(served, {"retrieval": drill.SERVED_RETRIEVAL_RECORD_TYPE,
                                  "manifest": drill.SERVED_MANIFEST_RECORD_TYPE,
                                  "download": drill.SERVED_DOWNLOAD_RECORD_TYPE})

    def test_the_install_tool_is_told_a_variable_name_and_not_a_key(self):
        installs = [row for row in self.runner.calls
                    if any(argument.endswith("install_selected_material.py") for argument in row)]
        self.assertEqual(len(installs), 2)
        for arguments in installs:
            self.assertIn("--key-variable", arguments)
            self.assertEqual(arguments[arguments.index("--key-variable") + 1], drill.FIRST_TENANT_VARIABLE)


class MutantTest(unittest.TestCase):
    """Remove one behaviour and name the check that must fail.

    Each case is a known-wrong service. A drill whose checks still pass here
    would be proving nothing.
    """

    def assert_mutant_fails(self, removed, *expected_checks):
        report, _runner = run_with({removed: False})
        self.assertFalse(report["all_passed"], f"removing {removed} left every check green")
        for expected_check in expected_checks:
            self.assertIn(expected_check, failing(report),
                          f"removing {removed} did not fail {expected_check}; failed {failing(report)}")

    def test_a_service_that_answers_without_a_key(self):
        """The free route and both metered routes are shown without a key."""
        self.assert_mutant_fails("refuses_without_a_key", "usage_is_refused_without_a_key",
                                 "the_metered_routes_are_refused_without_a_key")

    def test_a_service_that_answers_a_host_outside_the_declared_list(self):
        self.assert_mutant_fails("refuses_an_unexpected_host",
                                 "a_request_whose_host_header_is_outside_the_declared_list_is_refused")

    def test_a_service_that_changes_a_record_version_it_serves(self):
        self.assert_mutant_fails("serves_the_supported_record_versions",
                                 "the_service_serves_the_record_versions_this_drill_reads")

    def test_an_install_run_whose_client_command_starts_a_model_turn(self):
        self.assert_mutant_fails("the_client_listing_avoids_a_model_turn",
                                 "the_install_run_started_no_model_turn",
                                 "the_client_listing_started_no_model_turn")

    def test_a_service_that_serves_a_body_that_does_not_match_its_digest(self):
        self.assert_mutant_fails("serves_the_correct_body",
                                 "the_downloaded_body_matches_the_manifest_digest_and_the_response_header")

    def test_a_service_that_serves_the_other_tenants_item(self):
        self.assert_mutant_fails("refuses_the_other_tenants_item",
                                 "an_item_granted_to_the_other_tenant_is_refused")

    def test_a_service_that_still_honors_a_revoked_key(self):
        self.assert_mutant_fails("refuses_a_revoked_key", "a_revoked_key_is_refused_at_the_next_request")

    def test_a_service_that_serves_a_tampered_body(self):
        self.assert_mutant_fails("refuses_a_tampered_body",
                                 "a_body_whose_bytes_no_longer_match_its_reviewed_digest_is_refused")

    def test_a_server_that_forgets_the_usage_when_it_restarts(self):
        self.assert_mutant_fails("keeps_usage_across_a_restart",
                                 "the_restarted_server_on_the_same_volume_still_knows_the_usage")

    def test_an_install_that_writes_something_other_than_the_served_body(self):
        self.assert_mutant_fails("installs_the_served_body",
                                 "every_installed_file_holds_the_served_body_byte_for_byte")

    def test_an_install_tool_that_accepts_plain_http_to_a_non_loopback_host(self):
        self.assert_mutant_fails("refuses_plain_http_to_a_non_loopback_host",
                                 "plain_http_to_a_non_loopback_host_is_refused_by_the_install_tool")

    def test_a_host_that_registers_an_item_whose_licence_is_unknown(self):
        self.assert_mutant_fails("refuses_an_unknown_licence",
                                 "an_item_whose_licence_is_unknown_is_refused_before_registration")

    def test_a_private_network_that_has_external_connectivity(self):
        self.assert_mutant_fails("network_internal", "private_network_has_no_external_connectivity")

    def test_a_container_that_keeps_a_route_off_this_machine(self):
        report, _runner = run_with({"has_default_route": True})
        self.assertIn("client_container_has_no_route_off_this_machine", failing(report))

    def test_a_container_that_can_resolve_an_external_name(self):
        report, _runner = run_with({"resolves_external_name": True})
        self.assertIn("client_container_has_no_route_off_this_machine", failing(report))

    def test_a_client_that_does_not_list_the_installed_material(self):
        report, _runner = run_with({"the_client_lists_installed_material": False})
        self.assertIn("the_client_reports_every_installed_item_under_its_own_name", failing(report))

    def test_a_host_file_that_does_not_state_where_each_callers_address_comes_from(self):
        """The image's own command refuses to serve it, so the drill stops at the server.

        This is the drill's own known-wrong configuration rather than a changed
        service: the same host file with the client address statement removed.
        The recorded server applies the service's real start rule, so the drill
        cannot pass unless the file it writes carries the statement. In a real
        run the stopped server can surface one step later, at key issuance.
        """
        stated = drill.host_configuration

        def unstated(chosen, valid_until):
            configuration = stated(chosen, valid_until)
            del configuration["http"]["request_limits"]
            return configuration

        with mock.patch.object(drill, "host_configuration", unstated):
            report, runner = run_with()
        self.assertFalse(report["all_passed"])
        self.assertEqual(report["failure"]["code"], "host_not_configured")
        self.assertEqual(runner.stopped, {settings().name("server")})


class RefusalTest(unittest.TestCase):
    """A step the drill cannot complete is recorded, not hidden."""

    def test_a_failed_build_stops_the_run_and_still_cleans_up(self):
        chosen = settings()
        selection = drill.select_catalogue_items(chosen.catalogue, chosen.accepted_licenses)

        class FailingBuild(RecordedDocker):
            def _answer(self, arguments, input_text):
                if arguments[0] == "build":
                    return (1, "", "build failed")
                return super()._answer(arguments, input_text)

        runner = FailingBuild(selection)
        report = drill.run_drill(chosen, runner)
        self.assertFalse(report["all_passed"])
        self.assertEqual(report["failure"]["code"], "image_not_built")
        self.assertIn("service_image_builds_from_the_working_tree", failing(report))
        self.assertEqual(report["cleanup"]["still_present"], [])

    def test_a_step_that_fails_inside_a_container_is_recorded(self):
        chosen = settings()
        selection = drill.select_catalogue_items(chosen.catalogue, chosen.accepted_licenses)

        class FailingSeed(RecordedDocker):
            def _step(self, arguments, input_text):
                if arguments[-1] == "seed-server-volume":
                    return (1, "", "no permission")
                return super()._step(arguments, input_text)

        runner = FailingSeed(selection)
        report = drill.run_drill(chosen, runner)
        self.assertEqual(report["failure"]["code"], "step_failed_in_container")
        self.assertEqual(report["failure"]["detail"], "seed-server-volume")
        self.assertEqual(sorted(runner.created["volume"]), sorted(runner.removed["volume"]))

    def test_the_drill_refuses_to_remove_a_resource_it_did_not_create(self):
        chosen = settings()
        selection = drill.select_catalogue_items(chosen.catalogue, chosen.accepted_licenses)
        instance = drill.ContainerJourneyDrill(chosen, RecordedDocker(selection))
        instance.created.append(("volume", "someone-elses-volume"))
        with self.assertRaises(drill.DrillRefusal) as caught:
            instance.remove_created_resources()
        self.assertEqual(caught.exception.code, "refusing_to_remove_a_foreign_resource")

    def test_a_service_that_never_becomes_healthy_is_recorded(self):
        chosen = settings()
        selection = drill.select_catalogue_items(chosen.catalogue, chosen.accepted_licenses)

        class NeverHealthy(RecordedDocker):
            def _one_request(self, case):
                if case["route"] == "/api/v1/health":
                    return {"status": 503, "code": "unavailable", "result": None}
                return super()._one_request(case)

        report = drill.run_drill(chosen, NeverHealthy(selection))
        self.assertEqual(report["failure"]["code"], "service_did_not_become_healthy")

    def test_output_that_is_not_json_is_refused_rather_than_guessed(self):
        result = drill.CommandResult(("docker", "exec", "server"), 0, "not json")
        with self.assertRaises(drill.DrillRefusal) as caught:
            result.json()
        self.assertEqual(caught.exception.code, "command_output_is_not_json")

    def test_a_document_printed_over_several_lines_is_read_whole(self):
        result = drill.CommandResult(("docker", "exec", "server"), 0, '{\n "complete": true\n}\n')
        self.assertEqual(result.json(), {"complete": True})

    def test_a_result_printed_after_progress_lines_is_read_from_the_last_line(self):
        result = drill.CommandResult(("docker", "exec", "server"), 0, 'building\n{"complete": true}\n')
        self.assertEqual(result.json(), {"complete": True})

    def test_a_command_that_timed_out_is_not_read_as_a_result(self):
        result = drill.CommandResult(("docker", "build"), 124, "", "", timed_out=True)
        self.assertFalse(result.ok)
        with self.assertRaises(drill.DrillRefusal) as caught:
            result.json()
        self.assertEqual(caught.exception.code, "command_failed")


class ReportShapeTest(unittest.TestCase):
    """The report states what the drill does not prove."""

    @classmethod
    def setUpClass(cls):
        cls.report, _runner = run_with()

    def test_the_limitations_are_kept_with_the_result(self):
        text = " ".join(self.report["limitations"]).lower()
        for expected in ("model turn", "identity provider", "loopback", "independent qualification"):
            self.assertIn(expected, text)

    def test_the_report_states_that_no_container_had_external_network(self):
        self.assertFalse(self.report["external_network_available_to_the_containers"])

    def test_the_report_counts_the_checks_it_ran(self):
        self.assertEqual(self.report["total"], len(self.report["checks"]))
        self.assertEqual(self.report["passed"], sum(row["passed"] for row in self.report["checks"]))
        self.assertGreaterEqual(self.report["total"], 30)

    def test_a_skipped_check_is_named_and_never_counted_as_passed(self):
        """Without a client executable there is no listing, so two checks cannot run.

        Both must be named, neither may appear among the checks, and neither may
        be added to the count. A run whose only missing piece is the client
        executable still passes, so `all_passed` stays true beside the skips.
        """
        state = drill.install_tool.ListingState.EXECUTABLE_NOT_FOUND.value
        report, _runner = run_with({"client_listing_state": state})
        names = [row["name"] for row in report["checks"]]
        skipped = [row["name"] for row in report["skipped_checks"]]
        self.assertEqual(sorted(skipped), sorted(drill.CHECKS_THAT_NEED_THE_CLIENT_LISTING))
        for name in drill.CHECKS_THAT_NEED_THE_CLIENT_LISTING:
            self.assertNotIn(name, names)
        for row in report["skipped_checks"]:
            self.assertIn(state, row["reason"])
        self.assertEqual(report["total"], len(names))
        self.assertEqual(report["passed"], report["total"])
        self.assertTrue(report["all_passed"])
        self.assertIsNone(report["facts"]["reported_by_the_client"])

    def test_the_report_derives_external_connectivity_from_the_checks_that_ran(self):
        """The report does not declare the answer. It reads the two network checks."""
        self.assertFalse(self.report["external_network_available_to_the_containers"])
        report, _runner = run_with({"network_internal": False})
        self.assertTrue(report["external_network_available_to_the_containers"])
        self.assertIsNone(drill.external_network_available([]))

    def test_the_settings_in_the_report_repeat_no_value_of_a_key(self):
        summary = self.report["settings"]
        self.assertEqual(summary["key_variables"],
                         [drill.FIRST_TENANT_VARIABLE, drill.SECOND_TENANT_VARIABLE,
                          drill.REVOCATION_DRILL_VARIABLE])
        self.assertNotIn("key\":", json.dumps(summary).replace("key_variables", ""))

    def test_the_report_can_be_written_as_json(self):
        json.dumps(copy.deepcopy(self.report), sort_keys=True)


if __name__ == "__main__":
    unittest.main()
