"""Run the whole customer journey between two local containers, with no external network.

The drill builds the service image from the working tree, puts real starter
catalogue items behind a host manifest, starts a server container on a private
Docker network that has no route off the machine, creates two tenants with
different grants, and then runs the journey from a separate client container:
health, a refusal without a key, search, selection, manifest, download with
digest verification, installation into the native client layout through
``tools/install_selected_material.py``, and a usage read.

It then removes behaviour on purpose and records what the service does: the
other tenant's item, a revoked key, a body whose bytes no longer match its
reviewed digest, and a restart of the server on the same volume.

Offered, fetched, installed and verified are separate facts. A container that
answers is not a customer who received material, and a file on disk is not a
model that used it. The drill starts no model turn, contacts no provider and
writes no credential into its report. Every container, network and volume it
creates carries a name of this run and is removed before it returns.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

#: This drill states no address vocabulary and no client command of its own. It
#: reads both from the code that owns them: the service runtime decides which
#: address schemes it accepts, and the install tool beside this file owns the
#: client layout profile, its listing command and the subcommands that would
#: start a model turn. Running the file directly puts its own folder first on
#: the import path; the continuous integration run puts `src` and `tools` on
#: PYTHONPATH. The insert below makes both ways work.
_TOOLS_FOLDER = str(Path(__file__).resolve().parent)
if _TOOLS_FOLDER not in sys.path:
    sys.path.insert(0, _TOOLS_FOLDER)

import install_selected_material as install_tool  # noqa: E402
from loop_engine.core.service_runtime.http_auth import validate_public_url  # noqa: E402

REPORT_RECORD_TYPE = "client_journey_container_drill/v1"
SETTINGS_RECORD_TYPE = "client_journey_drill_settings/v1"
TENANT_PLAN_RECORD_TYPE = "client_journey_tenant_plan/v1"
FACTS_RECORD_TYPE = "client_journey_facts/v1"
DECLARED_RECORD_TYPE = "client_journey_declared_conditions/v1"
COMMAND_RESULT_RECORD_TYPE = "client_journey_command_result/v1"
HOST_CONFIGURATION_RECORD_TYPE = "service_http_host_configuration/v1"
MANIFEST_RECORD_TYPE = "host_attested_intelligence_manifest/v1"
PROVISIONING_REQUEST_RECORD_TYPE = "service_provisioning_request/v1"
RETRIEVAL_REQUEST_RECORD_TYPE = "service_retrieval_request/v1"
INSTALL_REPORT_RECORD_TYPE = "native_material_install_report/v1"
ISSUED_KEY_RECORD_TYPE = "issued_service_key/v1"
#: The record versions this drill accepts from the service. A served document
#: of any other version is an unsupported input, so the drill names the version
#: it expects and refuses to read a different one as if it were the same.
SERVED_RETRIEVAL_RECORD_TYPE = "service_retrieval_result/v1"
SERVED_MANIFEST_RECORD_TYPE = "provisioning_manifest/v2"
SERVED_DOWNLOAD_RECORD_TYPE = "service_download/v1"
SERVED_HEALTH_RECORD_TYPE = "service_health/v1"
#: The refusals this drill expects from the service, named once here and
#: compared by name everywhere else.
UNAUTHORIZED_CODE = "unauthorized"
INVALID_HOST_CODE = "invalid_host"
UNEXPECTED_HOST_STATUS = 421
#: A name the host configuration never lists. It is sent as the Host header of
#: one request, so the drill sees what the service does with a name outside the
#: declared list. The reserved `.invalid` top level name can never resolve.
UNEXPECTED_HOST = "not-in-the-declared-list.invalid"
#: The licence identifiers this host accepts. An item that declares anything
#: else, including an unknown or review state, is refused before registration.
ACCEPTED_LICENSES = ("MIT",)
#: Metering is required for every grant, so a body read that is not counted is
#: refused rather than served free of charge.
REQUIRED_METERING = "required"
#: Names of the environment variables that carry a service key inside a
#: container. A key reaches a container through a variable name only: no value
#: is ever written into a command line, a report or a log.
FIRST_TENANT_VARIABLE = "LOOP_ENGINE_SERVICE_KEY"
SECOND_TENANT_VARIABLE = "LOOP_ENGINE_SECOND_TENANT_KEY"
REVOCATION_DRILL_VARIABLE = "LOOP_ENGINE_REVOCATION_DRILL_KEY"
#: The client used for the native layout. Its listing command reads files; the
#: drill never runs a subcommand that would start a model turn.
CLIENT_KIND = "opencode"
NATIVE_LAYOUT_PREFIX = ".opencode/skills"
SERVED_KIND = "skill"
#: The client layout profile is owned by the install tool this drill runs, so
#: the expected listing command and the subcommands that would start a model
#: turn are read from it rather than restated here.
CLIENT_LAYOUT_PROFILE = install_tool.layout_profile_for(CLIENT_KIND)
EXPECTED_LISTING_ARGUMENTS = list(CLIENT_LAYOUT_PROFILE.listing.arguments)
MODEL_TURN_SUBCOMMANDS = tuple(CLIENT_LAYOUT_PROFILE.model_turn_subcommands)
OBSERVED_LISTING_STATE = install_tool.ListingState.OBSERVED.value
#: The two checks that need the client's own listing. When no client executable
#: is supplied there is no listing, so both are named as skipped and neither is
#: counted as passed.
CHECKS_THAT_NEED_THE_CLIENT_LISTING = ("the_client_reports_every_installed_item_under_its_own_name",
                                       "the_client_listing_started_no_model_turn")
#: Files whose content decides what this drill observes. Their hashes go into
#: the report so a later reader can tell which source produced the result.
SOURCE_FILES = (
    "Dockerfile.service",
    "tools/check_client_journey_in_containers.py",
    "tools/install_selected_material.py",
    "src/loop_engine/core/provisioning_server.py",
    "src/loop_engine/core/service_runtime/http.py",
    "src/loop_engine/core/service_runtime/http_auth.py",
    "src/loop_engine/core/service_runtime/http_entrypoint.py",
    "src/loop_engine/core/service_runtime/provisioning.py",
    "src/loop_engine/core/service_runtime/runtime.py",
    "examples/29_intelligence_service/starter-catalogue/items.json",
)
CATALOGUE_DIRECTORY = "examples/29_intelligence_service/starter-catalogue"
CATALOGUE_ITEMS_FILE = "items.json"
#: A resource name of this run. The drill removes names it created and nothing
#: else, so the pattern is narrow and carries a value that no other run shares.
RESOURCE_PREFIX_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
VARIABLE_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
#: Docker never runs without a deadline. These are the ceilings, not measurements.
BUILD_TIMEOUT_SECONDS = 1800.0
DOCKER_TIMEOUT_SECONDS = 180.0
JOURNEY_TIMEOUT_SECONDS = 600.0
READY_TIMEOUT_SECONDS = 90.0
READY_POLL_SECONDS = 0.5
#: Every address of this drill is a default of the settings record below, which
#: owns them. Nothing here names a provider, a deployed host or a public name.
#: The server listens inside a private network, the loopback address belongs to
#: the client container, and the declared public base URL uses the reserved
#: `.invalid` top level name, which can never resolve anywhere.
SERVICE_PORT = 8080
#: The install tool accepts HTTPS or a loopback address. The private network
#: carries plain HTTP, so the client container forwards a loopback port to the
#: server container. The bytes still cross the private network between the two
#: containers; only the address the tool is given is local.
FORWARD_PORT = 8080
LOOPBACK_ADDRESS = "127.0.0.1"
#: A name under the reserved `.invalid` top level name. It can never resolve,
#: anywhere, so the host configuration declares a public base URL that reaches
#: nothing while still satisfying the rule that the URL uses a secure scheme.
UNRESOLVABLE_DRILL_NAME = "client-journey-drill.invalid"
#: The scheme names this drill offers the service's own address owner, and the
#: separator the address syntax puts after a scheme name.
CANDIDATE_SCHEME_NAMES = ("https", "http")
SCHEME_SEPARATOR = "://"


class DrillRefusal(RuntimeError):
    """A stable refusal of this drill. Its text never holds a credential."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


def _refuse_unless(condition, code: str, detail: str = "") -> None:
    if not condition:
        raise DrillRefusal(code, detail)


def schemes_the_service_accepts(validate=validate_public_url, names=CANDIDATE_SCHEME_NAMES):
    """Ask the service's own address owner which scheme it accepts where.

    ``validate_public_url`` in the service runtime decides whether an address is
    usable, and the install tool applies the same rule. This drill states no
    answer of its own. It offers that owner one address for each candidate
    scheme name, once for a public name and once for a loopback address, and
    keeps what the owner accepts. A change at the owner therefore reaches this
    drill as a different result instead of as a stale copy.

    The secure scheme is the one the owner accepts for a public name. The plain
    scheme is the one it accepts for a loopback address and refuses for a public
    name. Exactly one of each is required, so an owner vocabulary this drill
    cannot read is refused before any container is created.
    """
    public, loopback = [], []
    for name in names:
        prefix = name + SCHEME_SEPARATOR
        for address, accepted in ((UNRESOLVABLE_DRILL_NAME, public), (LOOPBACK_ADDRESS, loopback)):
            try:
                validate(prefix + address, permit_loopback=True)
            except ValueError:
                continue
            accepted.append(prefix)
    plain = [prefix for prefix in loopback if prefix not in public]
    _refuse_unless(len(public) == 1 and len(plain) == 1 and set(public) <= set(loopback),
                   "the_service_address_owner_declares_an_unreadable_scheme_vocabulary",
                   ",".join(sorted(set(public) | set(loopback))))
    return public[0], plain[0], tuple(loopback)


def address_the_service_accepts(value, *, permit_loopback=False) -> bool:
    """Whether the service's own address owner accepts this exact address."""
    try:
        validate_public_url(value, permit_loopback=permit_loopback)
    except ValueError:
        return False
    return True


#: The scheme the host configuration declares, the scheme the private network
#: carries, and every scheme the service accepts, all read from that owner.
SECURE_SCHEME, PLAIN_SCHEME, SUPPORTED_SCHEMES = schemes_the_service_accepts()
PRIVATE_NETWORK_SCHEME = PLAIN_SCHEME
DECLARED_PUBLIC_BASE_URL = SECURE_SCHEME + UNRESOLVABLE_DRILL_NAME


# ---------------------------------------------------------------------------
# Running a command
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommandResult:
    """What one external command did. Output stays out of the report."""

    arguments: tuple[str, ...]
    returncode: int
    stdout: str = field(repr=False, default="")
    stderr: str = field(repr=False, default="")
    timed_out: bool = False
    elapsed_seconds: float = 0.0
    record_type: str = COMMAND_RESULT_RECORD_TYPE

    def __post_init__(self):
        _refuse_unless(self.record_type == COMMAND_RESULT_RECORD_TYPE, "unsupported_command_result")

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def json(self):
        """The JSON the command printed, or a refusal.

        A command that prints one document gives it whole, over as many lines
        as it likes. A command that prints progress first ends with its result
        on the last line. Both are read; nothing else is guessed.
        """
        _refuse_unless(self.ok, "command_failed", " ".join(self.arguments[:3]))
        text = self.stdout.strip()
        _refuse_unless(bool(text), "command_printed_nothing", " ".join(self.arguments[:3]))
        for candidate in (text, text.splitlines()[-1]):
            try:
                return json.loads(candidate)
            except ValueError:
                continue
        raise DrillRefusal("command_output_is_not_json", " ".join(self.arguments[:3]))


class SubprocessCommandRunner:
    """Run a real command with a deadline. Every call states its own timeout."""

    def __call__(self, arguments, *, timeout, input_text=None, environment=None) -> CommandResult:
        _refuse_unless(isinstance(timeout, (int, float)) and timeout > 0, "command_needs_a_deadline")
        started = time.monotonic()
        try:
            done = subprocess.run(list(arguments), capture_output=True, text=True, timeout=timeout,
                                  input=input_text, env=environment)
        except subprocess.TimeoutExpired:
            return CommandResult(tuple(arguments), returncode=124, timed_out=True,
                                 elapsed_seconds=round(time.monotonic() - started, 3))
        return CommandResult(tuple(arguments), done.returncode, done.stdout, done.stderr,
                             elapsed_seconds=round(time.monotonic() - started, 3))


# ---------------------------------------------------------------------------
# Typed settings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TenantPlan:
    """One tenant of the drill and the items its grants cover."""

    tenant_id: str
    namespace: str
    key_variable: str
    record_type: str = TENANT_PLAN_RECORD_TYPE

    def __post_init__(self):
        _refuse_unless(self.record_type == TENANT_PLAN_RECORD_TYPE, "unsupported_tenant_plan")
        for value in (self.tenant_id, self.namespace):
            _refuse_unless(isinstance(value, str) and IDENTITY_PATTERN.fullmatch(value), "invalid_tenant_plan")
        _refuse_unless(isinstance(self.key_variable, str) and VARIABLE_PATTERN.fullmatch(self.key_variable),
                       "invalid_key_variable")


@dataclass(frozen=True)
class DrillSettings:
    """One validated drill. Validation has no effect outside this process."""

    repository: Path
    report: Path
    resource_prefix: str
    image_reference: str
    first_tenant: TenantPlan
    second_tenant: TenantPlan
    client_executable_on_this_machine: Path | None = None
    accepted_licenses: tuple[str, ...] = ACCEPTED_LICENSES
    service_port: int = SERVICE_PORT
    forward_port: int = FORWARD_PORT
    loopback_address: str = LOOPBACK_ADDRESS
    private_network_scheme: str = PRIVATE_NETWORK_SCHEME
    declared_public_base_url: str = DECLARED_PUBLIC_BASE_URL
    build_timeout_seconds: float = BUILD_TIMEOUT_SECONDS
    docker_timeout_seconds: float = DOCKER_TIMEOUT_SECONDS
    journey_timeout_seconds: float = JOURNEY_TIMEOUT_SECONDS
    ready_timeout_seconds: float = READY_TIMEOUT_SECONDS
    record_type: str = SETTINGS_RECORD_TYPE

    def __post_init__(self):
        _refuse_unless(self.record_type == SETTINGS_RECORD_TYPE, "unsupported_drill_settings")
        _refuse_unless(isinstance(self.repository, Path) and self.repository.is_absolute(),
                       "repository_must_be_an_absolute_path")
        _refuse_unless(isinstance(self.report, Path) and self.report.is_absolute(),
                       "report_must_be_an_absolute_path")
        _refuse_unless(bool(RESOURCE_PREFIX_PATTERN.fullmatch(self.resource_prefix)), "invalid_resource_prefix")
        _refuse_unless(isinstance(self.image_reference, str) and ":" in self.image_reference
                       and " " not in self.image_reference, "invalid_image_reference")
        _refuse_unless(isinstance(self.first_tenant, TenantPlan) and isinstance(self.second_tenant, TenantPlan),
                       "two_typed_tenant_plans_are_required")
        _refuse_unless(self.first_tenant.tenant_id != self.second_tenant.tenant_id
                       and self.first_tenant.namespace != self.second_tenant.namespace
                       and self.first_tenant.key_variable != self.second_tenant.key_variable,
                       "the_two_tenants_must_differ")
        names = tuple(self.accepted_licenses)
        _refuse_unless(bool(names) and len(set(names)) == len(names)
                       and all(isinstance(name, str) and name == name.strip() and name.isascii()
                               and name.isprintable() for name in names), "invalid_accepted_licenses")
        object.__setattr__(self, "accepted_licenses", names)
        for name in ("build_timeout_seconds", "docker_timeout_seconds", "journey_timeout_seconds",
                     "ready_timeout_seconds"):
            value = getattr(self, name)
            _refuse_unless(isinstance(value, (int, float)) and value > 0, "invalid_timeout", name)
        for name in ("service_port", "forward_port"):
            value = getattr(self, name)
            _refuse_unless(type(value) is int and 1 <= value <= 65535, "invalid_port", name)
        _refuse_unless(self.declared_public_base_url.startswith(SECURE_SCHEME)
                       and self.declared_public_base_url.rstrip("/") == self.declared_public_base_url
                       and address_the_service_accepts(self.declared_public_base_url),
                       "declared_public_base_url_must_be_an_https_origin")
        _refuse_unless(self.private_network_scheme in SUPPORTED_SCHEMES, "unsupported_private_network_scheme")
        _refuse_unless(bool(self.loopback_address) and " " not in self.loopback_address, "invalid_loopback_address")
        if self.client_executable_on_this_machine is not None:
            path = self.client_executable_on_this_machine
            _refuse_unless(isinstance(path, Path) and path.is_absolute(), "client_executable_must_be_absolute")

    @property
    def catalogue(self) -> Path:
        return self.repository / CATALOGUE_DIRECTORY

    def name(self, role: str) -> str:
        return f"{self.resource_prefix}-{role}"

    @property
    def server_host(self) -> str:
        """The name and port the client containers reach on the private network."""
        return f"{self.name('server')}:{self.service_port}"

    @property
    def loopback_host(self) -> str:
        """The address inside the client container that the forwarder listens on."""
        return f"{self.loopback_address}:{self.forward_port}"

    @property
    def server_origin(self) -> str:
        return self.private_network_scheme + self.server_host

    @property
    def loopback_origin(self) -> str:
        return self.private_network_scheme + self.loopback_host

    @property
    def declared_public_host(self) -> str:
        """The host part of the public base URL the host configuration declares."""
        return self.declared_public_base_url.split("//", 1)[1]

    def public_summary(self) -> dict:
        """The settings a report may repeat. No path outside the repository, no key value."""
        return {"record_type": self.record_type, "image_reference": self.image_reference,
                "resource_prefix": self.resource_prefix,
                "accepted_licenses": list(self.accepted_licenses),
                "tenants": [self.first_tenant.tenant_id, self.second_tenant.tenant_id],
                "key_variables": [self.first_tenant.key_variable, self.second_tenant.key_variable,
                                  REVOCATION_DRILL_VARIABLE],
                "client_kind": CLIENT_KIND,
                "client_executable_supplied": self.client_executable_on_this_machine is not None,
                "addresses": {"server_origin": self.server_origin, "loopback_origin": self.loopback_origin,
                              "declared_public_base_url": self.declared_public_base_url},
                "timeouts_seconds": {"build": self.build_timeout_seconds, "docker": self.docker_timeout_seconds,
                                     "journey": self.journey_timeout_seconds, "ready": self.ready_timeout_seconds}}


# ---------------------------------------------------------------------------
# Scripts that run inside a container
# ---------------------------------------------------------------------------

#: Every in-container script reads one JSON plan from standard input, takes the
#: step name as its first argument and prints one JSON object. The step name
#: makes a failed run readable and lets a test drive the drill with a command
#: runner that answers by step.

SEED_SERVER_VOLUME = r'''
import json, os, shutil, sys
from pathlib import Path
plan = json.load(sys.stdin)
root, artifacts = Path("/data"), Path("/data/artifacts")
artifacts.mkdir()
items = []
for row in plan["items"]:
    name = row["reference"]["identity"] + ".md"
    shutil.copyfile("/catalogue/" + row["body_path"], artifacts / name)
    items.append({"reference": row["reference"], "body_path": name,
                  "approval_ref": plan["approval_ref"], "grants": row["grants"]})
(root / "manifest.json").write_text(json.dumps({"record_type": plan["manifest_record_type"],
    "artifact_root": str(artifacts), "items": items}), encoding="utf-8")
(root / "host.json").write_text(json.dumps(plan["host"]), encoding="utf-8")
os.chown(root, 65534, 65534)
os.chmod(root, 0o700)
for path in [artifacts, *sorted(root.rglob("*"))]:
    os.chown(path, 65534, 65534)
    os.chmod(path, 0o700 if path.is_dir() else 0o600)
print(json.dumps({"step": sys.argv[1], "registered_items": len(items),
                  "artifact_root": str(artifacts)}))
'''

SEED_CLIENT_VOLUME = r'''
import json, os, sys
from pathlib import Path
plan = json.load(sys.stdin)
for name in plan["folders"]:
    path = Path("/client") / name
    path.mkdir()
    os.chown(path, 65534, 65534)
    os.chmod(path, 0o700)
os.chown("/client", 65534, 65534)
print(json.dumps({"step": sys.argv[1], "folders": plan["folders"],
                  "entries": sorted(p.name for p in Path("/client").iterdir())}))
'''

LICENCE_REFUSAL_PROBE = r'''
import json, shutil, sys
from pathlib import Path
from loop_engine.core.service_runtime.http_entrypoint import HostLicensePolicy, load_host_manifest
from loop_engine.core.service_runtime.records import ServiceRuntimeError
plan = json.load(sys.stdin)
root = Path("/tmp/licence-probe")
artifacts = root / "artifacts"
artifacts.mkdir(parents=True)
row = plan["item"]
name = row["reference"]["identity"] + ".md"
shutil.copyfile("/catalogue/" + row["body_path"], artifacts / name)
manifest = root / "manifest.json"
manifest.write_text(json.dumps({"record_type": plan["manifest_record_type"], "artifact_root": str(artifacts),
    "items": [{"reference": row["reference"], "body_path": name, "approval_ref": plan["approval_ref"],
               "grants": []}]}), encoding="utf-8")
policy = HostLicensePolicy(accepted_licenses=tuple(plan["accepted_licenses"]))
answer = {"step": sys.argv[1], "declared_license": row["reference"]["license"], "refused": False, "code": None}
try:
    load_host_manifest(str(manifest), license_policy=policy)
except ServiceRuntimeError as error:
    answer.update({"refused": True, "code": error.code})
print(json.dumps(answer))
'''

NETWORK_FACTS = r'''
import json, socket, sys
from pathlib import Path
plan = json.load(sys.stdin)
routes = Path("/proc/net/route").read_text().splitlines()[1:]
default = [line for line in routes if line.split()[1:2] == ["00000000"]]
socket.setdefaulttimeout(plan["resolve_timeout_seconds"])
resolved, failure = None, None
try:
    resolved = socket.getaddrinfo(plan["external_name"], 443)[0][4][0]
except OSError as error:
    failure = type(error).__name__
print(json.dumps({"step": sys.argv[1], "has_default_route": bool(default),
                  "external_name": plan["external_name"], "resolved_to": resolved,
                  "resolution_error": failure}))
'''

PORT_FORWARDER = r'''
import socket, sys, threading
target, port, listen, address = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
server = socket.create_server((address, listen))
def pump(source, sink):
    try:
        while True:
            block = source.recv(65536)
            if not block:
                break
            sink.sendall(block)
    except OSError:
        pass
    finally:
        try:
            sink.shutdown(socket.SHUT_WR)
        except OSError:
            pass
def handle(accepted):
    with accepted:
        try:
            upstream = socket.create_connection((target, port), timeout=30)
        except OSError:
            return
        with upstream:
            worker = threading.Thread(target=pump, args=(accepted, upstream), daemon=True)
            worker.start()
            pump(upstream, accepted)
            worker.join(30)
while True:
    connection, _ = server.accept()
    threading.Thread(target=handle, args=(connection,), daemon=True).start()
'''

JOURNEY_PROBE = r'''
import hashlib, json, os, sys, urllib.error, urllib.request
plan = json.load(sys.stdin)

def call(url, payload, token, host):
    request = urllib.request.Request(url, data=payload)
    if token is not None:
        request.add_header("Authorization", "Bearer " + token)
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    if host is not None:
        request.add_header("Host", host)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=plan["request_timeout_seconds"]) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers

answers = {}
for case in plan["cases"]:
    token = os.environ[case["key_variable"]] if case.get("key_variable") else None
    payload = json.dumps(case["payload"]).encode("utf-8") if case.get("payload") is not None else None
    status, body, headers = call(plan["origins"][case["origin"]] + case["route"], payload, token,
                                 case.get("host"))
    answer = {"status": status, "code": None, "result": None, "record_type": None}
    if status == 200 and case.get("binary"):
        answer["body_sha256"] = hashlib.sha256(body).hexdigest()
        answer["body_bytes"] = len(body)
        answer["digest_header"] = headers.get("X-Content-SHA256")
        answer["record_type_header"] = headers.get("X-Loop-Engine-Record-Type")
    else:
        try:
            document = json.loads(body)
        except ValueError:
            document = {}
        answer["code"] = (document.get("error") or {}).get("code")
        answer["result"] = document.get("result")
        if isinstance(answer["result"], dict):
            answer["record_type"] = answer["result"].get("record_type")
    answers[case["name"]] = answer
print(json.dumps({"step": sys.argv[1], "answers": answers}))
'''

REVOKE_ISSUED_KEY = r'''
import json, sys
from loop_engine.core.service_runtime.records import ServiceRuntimeConfig
from loop_engine.core.service_runtime.runtime import ServiceRuntime
plan = json.load(sys.stdin)
runtime = ServiceRuntime(ServiceRuntimeConfig(plan["database_path"], writes_authorized=True))
print(json.dumps({"step": sys.argv[1], **runtime.revoke_key(plan["tenant_id"], plan["key_id"])}))
'''

TAMPER_SERVED_BODY = r'''
import hashlib, json, sys
from pathlib import Path
plan = json.load(sys.stdin)
body = Path(plan["artifact_root"]) / (plan["identity"] + ".md")
keep = Path(plan["kept_copy"])
if plan["action"] == "tamper":
    original = body.read_bytes()
    keep.write_bytes(original)
    changed = bytearray(original)
    changed[-1] = 0x58 if changed[-1] != 0x58 else 0x59
    body.write_bytes(bytes(changed))
else:
    body.write_bytes(keep.read_bytes())
    keep.unlink()
now = body.read_bytes()
print(json.dumps({"step": sys.argv[1], "action": plan["action"], "size_bytes": len(now),
                  "sha256": hashlib.sha256(now).hexdigest()}))
'''

READ_INSTALLED_FILES = r'''
import hashlib, json, sys
from pathlib import Path
plan = json.load(sys.stdin)
root = Path(plan["project"])
rows = []
for record in plan["installed"]:
    path = root / record["path"]
    present = path.is_file() and not path.is_symlink()
    content = path.read_bytes() if present else b""
    served = content[record["body_offset_bytes"]:]
    rows.append({"identity": record["identity"], "path": record["path"], "present": present,
                 "file_bytes": len(content),
                 "file_sha256": hashlib.sha256(content).hexdigest() if present else None,
                 "served_body_sha256": hashlib.sha256(served).hexdigest() if present else None,
                 "served_body_bytes": len(served)})
print(json.dumps({"step": sys.argv[1], "files": rows,
                  "all_paths": sorted(str(p.relative_to(root)) for p in root.rglob("*"))[:200]}))
'''


# ---------------------------------------------------------------------------
# Selecting real catalogue items
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CatalogueSelection:
    """Real starter catalogue rows, split so the two tenants differ."""

    first_tenant_only: tuple[dict, ...]
    shared: tuple[dict, ...]
    second_tenant_only: tuple[dict, ...]
    refused_license: dict | None

    @property
    def registered(self) -> tuple[dict, ...]:
        return (*self.first_tenant_only, *self.shared, *self.second_tenant_only)

    @property
    def tamper_target(self) -> str:
        return self.first_tenant_only[-1]["reference"]["identity"]

    @property
    def install_identities(self) -> tuple[str, ...]:
        chosen = (*self.first_tenant_only[:-1], *self.shared[:1])
        return tuple(row["reference"]["identity"] for row in chosen)

    def offered_to(self, tenant: str, settings: DrillSettings) -> tuple[str, ...]:
        first = settings.first_tenant.tenant_id
        rows = (self.first_tenant_only if tenant == first else self.second_tenant_only)
        return tuple(sorted(row["reference"]["identity"] for row in (*rows, *self.shared)))


def confined_body_path(catalogue: Path, value) -> Path:
    """The body of a catalogue row, refused unless it stays inside the catalogue.

    The drill copies this name into a container, so it is checked the way the
    service checks the same field before it loads a manifest: a relative name,
    no parent part, no link that leaves the folder, and a real file under the
    catalogue directory. The refusal happens before any container exists.
    """
    _refuse_unless(isinstance(value, str) and value and "\\" not in value,
                   "catalogue_body_path_is_not_supported", str(value)[:64])
    relative = Path(value)
    root = catalogue.resolve()
    target = root / relative
    _refuse_unless(not relative.is_absolute() and ".." not in relative.parts
                   and target.resolve() == target and root in target.parents and target.is_file(),
                   "catalogue_body_path_is_not_confined", value[:64])
    return target


def select_catalogue_items(catalogue: Path, accepted_licenses) -> CatalogueSelection:
    """Take real rows from the starter catalogue in a fixed order.

    Only an item whose declared licence this host accepts can be registered.
    One refused row is kept so the drill can show that the host refuses it.
    """
    document = json.loads((catalogue / CATALOGUE_ITEMS_FILE).read_text(encoding="utf-8"))
    _refuse_unless(isinstance(document.get("items"), list) and document["items"], "catalogue_has_no_items")
    rows = sorted(document["items"], key=lambda row: row["reference"]["identity"])
    for row in rows:
        reference = row["reference"]
        _refuse_unless(IDENTITY_PATTERN.fullmatch(reference["identity"]), "catalogue_identity_is_not_supported")
        _refuse_unless(DIGEST_PATTERN.fullmatch(reference["digest"]), "catalogue_digest_is_not_supported")
        _refuse_unless(reference["kind"] == SERVED_KIND, "catalogue_kind_is_not_served_by_this_drill")
        body = confined_body_path(catalogue, row.get("body_path"))
        content = body.read_bytes()
        _refuse_unless(hashlib.sha256(content).hexdigest() == reference["digest"]
                       and len(content) == reference["size_bytes"], "catalogue_body_does_not_match_its_reference",
                       reference["identity"])
    accepted = [row for row in rows if row["reference"]["license"] in accepted_licenses]
    refused = [row for row in rows if row["reference"]["license"] not in accepted_licenses]
    _refuse_unless(len(accepted) >= 7, "catalogue_has_too_few_accepted_items")
    return CatalogueSelection(tuple(accepted[0:3]), tuple(accepted[3:5]), tuple(accepted[5:7]),
                              refused[0] if refused else None)


def manifest_rows(selection: CatalogueSelection, settings: DrillSettings) -> list:
    """One manifest row for each registered item, with grants that differ by tenant."""
    first, second = settings.first_tenant.tenant_id, settings.second_tenant.tenant_id

    def grants(tenants):
        return [{"tenant_id": name, "body_allowed": True, "metering": REQUIRED_METERING} for name in tenants]

    rows = []
    for row in selection.first_tenant_only:
        rows.append({"reference": row["reference"], "body_path": row["body_path"], "grants": grants([first])})
    for row in selection.shared:
        rows.append({"reference": row["reference"], "body_path": row["body_path"], "grants": grants([first, second])})
    for row in selection.second_tenant_only:
        rows.append({"reference": row["reference"], "body_path": row["body_path"], "grants": grants([second])})
    return rows


def host_configuration(settings: DrillSettings, valid_until: int) -> dict:
    """The host file the server container reads. It names no credential.

    Every address comes from the settings record, which owns them. The service
    answers a request whose Host header is one of these exact values and
    refuses any other.
    """
    tenants = []
    for plan in (settings.first_tenant, settings.second_tenant):
        tenants.append({"tenant_id": plan.tenant_id, "namespace": plan.namespace,
                        "operator_entitlement": {"valid_until": valid_until,
                                                 "evidence_ref": "container_journey_drill:operator_entitlement"}})
    return {"record_type": HOST_CONFIGURATION_RECORD_TYPE,
            "runtime": {"database_path": "/data/service.sqlite3", "writes_authorized": True},
            "http": {"public_base_url": settings.declared_public_base_url,
                     "allowed_hosts": [settings.declared_public_host, settings.server_host,
                                       settings.loopback_host],
                     "allowed_origins": []},
            "authentication": {"modes": ["host_key"]},
            "license_policy": {"record_type": "service_host_license_policy/v1",
                               "accepted_licenses": list(settings.accepted_licenses)},
            "manifest_path": "/data/manifest.json",
            "tenants": tenants}


# ---------------------------------------------------------------------------
# The drill
# ---------------------------------------------------------------------------

def client_commands_in(report: dict) -> list:
    """Every client command the install report recorded, as it holds them.

    The install tool starts one client process at most, for the listing, and
    writes the arguments it used into its listing record. An empty list means
    the run started no client process at all.
    """
    listing = report.get("listing") or {}
    arguments = listing.get("command_arguments")
    return [] if arguments is None else [list(arguments)]


def provisioning_request(operation: str, identity: str, request_id: str | None = None) -> dict:
    payload = {"record_type": PROVISIONING_REQUEST_RECORD_TYPE, "operation": operation, "identity": identity}
    if request_id is not None:
        payload["request_id"] = request_id
    return payload


class ContainerJourneyDrill:
    """Own every container of one run and record what the journey did."""

    def __init__(self, settings: DrillSettings, runner=None):
        _refuse_unless(isinstance(settings, DrillSettings), "typed_drill_settings_are_required")
        self.settings = settings
        self.runner = runner if runner is not None else SubprocessCommandRunner()
        self.checks: list[dict] = []
        self.skipped: list[dict] = []
        self.observations: dict = {}
        self.created: list[tuple[str, str]] = []
        self.calls: list[dict] = []
        self._keys: dict[str, str] = {}
        self._key_identities: dict[str, str] = {}

    # -- recording ---------------------------------------------------------

    def check(self, name: str, passed, detail: str = "") -> bool:
        self.checks.append({"name": name, "passed": bool(passed), "detail": detail})
        return bool(passed)

    def skip(self, name: str, reason: str) -> None:
        self.skipped.append({"name": name, "reason": reason})

    # -- commands ----------------------------------------------------------

    def docker(self, *arguments, timeout=None, input_text=None, environment=None):
        """Run one docker command with a deadline and record that it ran.

        The call log holds the command and its exit code only. Output can carry
        a newly issued key, so no call records its own output. No key value ever
        reaches an argument either: a key travels by variable name.
        """
        deadline = self.settings.docker_timeout_seconds if timeout is None else timeout
        result = self.runner(("docker", *arguments), timeout=deadline, input_text=input_text,
                             environment=environment)
        self.calls.append({"command": " ".join(("docker", *arguments[:3])), "returncode": result.returncode,
                           "timed_out": result.timed_out, "elapsed_seconds": result.elapsed_seconds})
        return result

    def run_in(self, container: str, script: str, step: str, plan: dict, *, timeout=None, user=None):
        """Run one step script inside a container that is already running."""
        options = ["exec", "-i"]
        if user is not None:
            options += ["--user", user]
        result = self.docker(*options, container, "python", "-c", script, step,
                             timeout=timeout, input_text=json.dumps(plan))
        _refuse_unless(result.ok, "step_failed_in_container", step)
        return result.json()

    def run_once(self, script: str, step: str, plan: dict, *, mounts, user=None, network="none", timeout=None):
        """Run one step script in a container that exists only for that step."""
        arguments = ["run", "--rm", "-i", "--network", network, "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m"]
        if user is not None:
            arguments += ["--user", user]
        for mount in mounts:
            arguments += ["--mount", mount]
        arguments += ["--entrypoint", "python", self.settings.image_reference, "-c", script, step]
        result = self.docker(*arguments, timeout=timeout, input_text=json.dumps(plan))
        _refuse_unless(result.ok, "step_failed_in_container", step)
        return result.json()

    # -- owned resources ---------------------------------------------------

    def create_volume(self, role: str) -> str:
        name = self.settings.name(role)
        result = self.docker("volume", "create", "--label", f"loop-engine.drill={self.settings.resource_prefix}", name)
        _refuse_unless(result.ok, "volume_not_created", role)
        self.created.append(("volume", name))
        return name

    def create_network(self, role: str) -> str:
        name = self.settings.name(role)
        result = self.docker("network", "create", "--internal", "--label",
                             f"loop-engine.drill={self.settings.resource_prefix}", name)
        _refuse_unless(result.ok, "network_not_created", role)
        self.created.append(("network", name))
        return name

    def start_container(self, role: str, arguments) -> str:
        name = self.settings.name(role)
        self.created.append(("container", name))
        result = self.docker("run", "--detach", "--name", name, *arguments)
        _refuse_unless(result.ok, "container_not_started", role)
        return name

    def remove_created_resources(self) -> dict:
        """Remove exactly the names this run created, newest first.

        Nothing else is touched. Every name carries the prefix of this run, and
        a name reaches this list only after the drill asked Docker to make it.
        """
        removals = {"container": ("rm", "--force"), "volume": ("volume", "rm"),
                    "network": ("network", "rm"), "image": ("image", "rm")}
        removed, left = [], []
        for kind, name in reversed(self.created):
            _refuse_unless(name.startswith(self.settings.resource_prefix)
                           or name == self.settings.image_reference, "refusing_to_remove_a_foreign_resource", kind)
            result = self.docker(*removals[kind], name, timeout=self.settings.docker_timeout_seconds)
            (removed if result.ok else left).append({"kind": kind, "name": name})
        return {"removed": removed, "still_present": left}

    # -- the journey -------------------------------------------------------

    def wait_for_health(self, container: str, origin: str, key_variable=None) -> dict:
        """Poll the health route until the service answers or the deadline passes."""
        plan = {"origins": {"service": origin}, "request_timeout_seconds": 5,
                "cases": [{"name": "health", "origin": "service", "route": "/api/v1/health",
                           "payload": None, "key_variable": key_variable}]}
        deadline = time.monotonic() + self.settings.ready_timeout_seconds
        last = None
        while True:
            result = self.docker("exec", "-i", container, "python", "-c", JOURNEY_PROBE, "health",
                                 timeout=self.settings.docker_timeout_seconds, input_text=json.dumps(plan))
            if result.ok:
                try:
                    last = result.json()["answers"]["health"]
                except DrillRefusal:
                    last = None
                if last is not None and last.get("status") == 200:
                    return last
            if time.monotonic() >= deadline:
                raise DrillRefusal("service_did_not_become_healthy", json.dumps(last)[:200] if last else "")
            time.sleep(READY_POLL_SECONDS)

    def issue_key(self, container: str, plan: TenantPlan, label: str) -> tuple[str, str]:
        """Issue one key inside the server container and return it with its identity.

        The command prints the new key once. Nothing here writes it to the call
        log, the report or the console; the value reaches a client container
        through a named environment variable only.
        """
        result = self.docker("exec", container, "loop-engine", "service", "issue-key",
                             "--config", "/data/host.json", "--tenant", plan.tenant_id, "--label", label)
        _refuse_unless(result.ok, "key_not_issued", plan.tenant_id)
        issued = result.json()
        _refuse_unless(issued.get("record_type") == ISSUED_KEY_RECORD_TYPE, "unsupported_issued_key_record")
        _refuse_unless(isinstance(issued.get("key"), str) and issued["key"], "issued_key_is_empty")
        _refuse_unless(isinstance(issued.get("key_id"), str) and issued["key_id"], "issued_key_has_no_identity")
        return issued["key"], issued["key_id"]

    def run_journey(self) -> dict:
        settings = self.settings
        selection = select_catalogue_items(settings.catalogue, settings.accepted_licenses)
        self.observations["catalogue"] = {
            "registered_items": len(selection.registered),
            "first_tenant_only": [row["reference"]["identity"] for row in selection.first_tenant_only],
            "shared": [row["reference"]["identity"] for row in selection.shared],
            "second_tenant_only": [row["reference"]["identity"] for row in selection.second_tenant_only],
            "refused_license_item": (selection.refused_license["reference"]["identity"]
                                     if selection.refused_license else None)}

        image_identity = self.build_image()
        network = self.create_network("network")
        self.check("private_network_has_no_external_connectivity", self.network_is_internal(network),
                   "docker network inspect reports Internal")

        server_volume = self.create_volume("server-data")
        client_volume = self.create_volume("client-data")
        self.seed_server_volume(server_volume, selection)
        self.seed_client_volume(client_volume)
        self.probe_refused_license(selection)

        server = self.start_server(network, server_volume)
        first_key, first_key_id = self.issue_key(server, settings.first_tenant, "container journey drill")
        second_key, second_key_id = self.issue_key(server, settings.second_tenant, "container journey drill")
        drill_key, drill_key_id = self.issue_key(server, settings.first_tenant, "revocation drill")
        self._keys = {settings.first_tenant.key_variable: first_key,
                      settings.second_tenant.key_variable: second_key,
                      REVOCATION_DRILL_VARIABLE: drill_key}
        self._key_identities = {settings.first_tenant.key_variable: first_key_id,
                                settings.second_tenant.key_variable: second_key_id,
                                REVOCATION_DRILL_VARIABLE: drill_key_id}
        self.check("every_issued_key_has_its_own_identity",
                   len({first_key_id, second_key_id, drill_key_id}) == 3)

        client = self.start_client(network, client_volume)
        other = self.start_other_tenant_client(network)
        self.check("client_container_has_no_route_off_this_machine", self.network_facts(client))

        server_origin, loopback_origin = settings.server_origin, settings.loopback_origin
        self.wait_for_health(client, server_origin)
        self.start_port_forwarder(client)

        facts = self.customer_journey(client, server_origin, loopback_origin, selection)
        self.refusals(server, client, other, server_origin, selection, drill_key_id)
        self.restart_and_read_usage(server, client, server_origin)
        self.observations["image_identity"] = image_identity
        return facts

    # -- steps -------------------------------------------------------------

    def build_image(self) -> str:
        settings = self.settings
        result = self.docker("build", "--file", str(settings.repository / "Dockerfile.service"),
                             "--tag", settings.image_reference,
                             "--label", f"loop-engine.drill={settings.resource_prefix}",
                             str(settings.repository), timeout=settings.build_timeout_seconds)
        built = self.check("service_image_builds_from_the_working_tree", result.ok,
                           "" if result.ok else "docker build did not succeed")
        _refuse_unless(built, "image_not_built")
        self.created.append(("image", settings.image_reference))
        inspected = self.docker("image", "inspect", settings.image_reference, "--format", "{{.Id}}")
        _refuse_unless(inspected.ok, "image_not_inspected")
        return inspected.stdout.strip()

    def network_is_internal(self, network: str) -> bool:
        result = self.docker("network", "inspect", network, "--format", "{{.Internal}}")
        self.observations["network_internal_flag"] = result.stdout.strip() if result.ok else None
        return result.ok and result.stdout.strip() == "true"

    def network_facts(self, container: str) -> bool:
        answer = self.run_in(container, NETWORK_FACTS, "network-facts",
                             {"external_name": "pypi.org", "resolve_timeout_seconds": 5})
        self.observations["client_network"] = answer
        return answer["has_default_route"] is False and answer["resolved_to"] is None

    def seed_server_volume(self, volume: str, selection: CatalogueSelection) -> None:
        settings = self.settings
        plan = {"items": manifest_rows(selection, settings), "host": host_configuration(settings, int(time.time()) + 86400),
                "approval_ref": "container_journey_drill:host_attested_not_independent_qualification",
                "manifest_record_type": MANIFEST_RECORD_TYPE}
        answer = self.run_once(SEED_SERVER_VOLUME, "seed-server-volume", plan, user="0:0", mounts=(
            f"type=volume,src={volume},dst=/data",
            f"type=bind,src={settings.catalogue},dst=/catalogue,ro"))
        self.observations["server_volume"] = answer
        self.check("the_host_manifest_registers_every_selected_catalogue_item",
                   answer["registered_items"] == len(selection.registered))

    def seed_client_volume(self, volume: str) -> None:
        answer = self.run_once(SEED_CLIENT_VOLUME, "seed-client-volume", {"folders": ["project", "reports"]},
                               user="0:0", mounts=(f"type=volume,src={volume},dst=/client",))
        self.check("the_client_project_folder_starts_empty", answer["entries"] == ["project", "reports"])

    def probe_refused_license(self, selection: CatalogueSelection) -> None:
        """A real catalogue item whose licence is unknown must not reach a manifest."""
        if selection.refused_license is None:
            self.skip("an_item_whose_licence_is_unknown_is_refused_before_registration",
                      "every item in this catalogue declares an accepted licence")
            return
        plan = {"item": selection.refused_license, "accepted_licenses": list(self.settings.accepted_licenses),
                "approval_ref": "container_journey_drill:host_attested_not_independent_qualification",
                "manifest_record_type": MANIFEST_RECORD_TYPE}
        answer = self.run_once(LICENCE_REFUSAL_PROBE, "licence-refusal", plan, mounts=(
            f"type=bind,src={self.settings.catalogue},dst=/catalogue,ro",))
        self.observations["refused_license"] = answer
        self.check("an_item_whose_licence_is_unknown_is_refused_before_registration",
                   answer["refused"] is True and answer["code"] == "item_license_unknown", answer["code"] or "")

    def start_server(self, network: str, volume: str) -> str:
        settings = self.settings
        server = self.start_container("server", (
            "--network", network, "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
            "--mount", f"type=volume,src={volume},dst=/data", settings.image_reference))
        configured = self.docker("exec", server, "loop-engine", "service", "configure", "--config", "/data/host.json")
        _refuse_unless(configured.ok, "host_not_configured")
        answer = configured.json()
        self.observations["configure"] = answer
        self.check("configure_creates_both_tenants_and_their_grant_sets",
                   answer.get("tenants") == [settings.first_tenant.tenant_id, settings.second_tenant.tenant_id]
                   and answer.get("configured_grant_sets") == 2
                   and answer.get("remote_accounts_created") is False)
        return server

    def start_client(self, network: str, volume: str) -> str:
        settings = self.settings
        environment = {**os.environ, settings.first_tenant.key_variable: self._keys[settings.first_tenant.key_variable]}
        arguments = ["--network", network, "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m",
                     "--env", settings.first_tenant.key_variable, "--env", "HOME=/tmp",
                     "--mount", f"type=volume,src={volume},dst=/client",
                     "--mount", f"type=bind,src={settings.repository / 'tools'},dst=/tools,ro"]
        if settings.client_executable_on_this_machine is not None:
            arguments += ["--mount",
                          f"type=bind,src={settings.client_executable_on_this_machine},dst=/usr/local/bin/{CLIENT_KIND},ro"]
        arguments += ["--entrypoint", "python", settings.image_reference, "-c",
                      "import time\nwhile True: time.sleep(3600)"]
        name = settings.name("client")
        self.created.append(("container", name))
        result = self.docker("run", "--detach", "--name", name, *arguments, environment=environment)
        _refuse_unless(result.ok, "container_not_started", "client")
        return name

    def start_other_tenant_client(self, network: str) -> str:
        """A second client container holds the other keys.

        The install tool removes only the key variable it was named from the
        environment of the client process it starts. Keeping the other keys in
        a separate container means no other key can reach that process.
        """
        settings = self.settings
        environment = {**os.environ,
                       settings.second_tenant.key_variable: self._keys[settings.second_tenant.key_variable],
                       REVOCATION_DRILL_VARIABLE: self._keys[REVOCATION_DRILL_VARIABLE]}
        name = settings.name("other-tenant-client")
        self.created.append(("container", name))
        result = self.docker("run", "--detach", "--name", name, "--network", network, "--read-only",
                             "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
                             "--env", settings.second_tenant.key_variable, "--env", REVOCATION_DRILL_VARIABLE,
                             "--entrypoint", "python", settings.image_reference, "-c",
                             "import time\nwhile True: time.sleep(3600)", environment=environment)
        _refuse_unless(result.ok, "container_not_started", "other-tenant-client")
        return name

    def start_port_forwarder(self, client: str) -> None:
        settings = self.settings
        result = self.docker("exec", "--detach", client, "python", "-c", PORT_FORWARDER,
                             settings.name("server"), str(settings.service_port), str(settings.forward_port),
                             settings.loopback_address)
        _refuse_unless(result.ok, "port_forwarder_not_started")
        deadline = time.monotonic() + settings.ready_timeout_seconds
        while True:
            answer = self.probe(client, settings.loopback_origin, "forwarder-ready", [
                {"name": "health", "origin": "service", "route": "/api/v1/health", "payload": None,
                 "key_variable": None}])
            if answer["health"]["status"] == 200:
                return
            _refuse_unless(time.monotonic() < deadline, "loopback_forwarder_did_not_answer")
            time.sleep(READY_POLL_SECONDS)

    def probe(self, container: str, origin: str, step: str, cases, *, extra_origins=None) -> dict:
        origins = {"service": origin}
        origins.update(extra_origins or {})
        answer = self.run_in(container, JOURNEY_PROBE, step,
                             {"origins": origins, "request_timeout_seconds": 20, "cases": cases},
                             timeout=self.settings.journey_timeout_seconds)
        return answer["answers"]

    def customer_journey(self, client: str, server_origin: str, loopback_origin: str,
                         selection: CatalogueSelection) -> dict:
        settings = self.settings
        variable = settings.first_tenant.key_variable
        selected = selection.install_identities
        manifest_target = selected[-1]
        cases = [
            {"name": "health", "origin": "service", "route": "/api/v1/health", "payload": None, "key_variable": None},
            {"name": "usage_without_a_key", "origin": "service", "route": "/api/v1/usage", "payload": None,
             "key_variable": None},
            {"name": "manifest_without_a_key", "origin": "service", "route": "/api/v1/provisioning",
             "key_variable": None, "payload": provisioning_request("manifest", manifest_target)},
            {"name": "download_without_a_key", "origin": "service", "route": "/api/v1/download",
             "key_variable": None,
             "payload": provisioning_request("read", manifest_target,
                                             f"{settings.resource_prefix}-anonymous-read")},
            {"name": "manifest_with_an_unexpected_host_header", "origin": "service",
             "route": "/api/v1/provisioning", "key_variable": variable, "host": UNEXPECTED_HOST,
             "payload": provisioning_request("manifest", manifest_target)},
            {"name": "search", "origin": "service", "route": "/api/v1/retrieval", "key_variable": variable,
             "payload": {"record_type": RETRIEVAL_REQUEST_RECORD_TYPE,
                         "query": "check the work before handing it over", "top_n": 25}},
            {"name": "manifest", "origin": "service", "route": "/api/v1/provisioning", "key_variable": variable,
             "payload": provisioning_request("manifest", manifest_target)},
            {"name": "download", "origin": "service", "route": "/api/v1/download", "key_variable": variable,
             "binary": True,
             "payload": provisioning_request("read", manifest_target,
                                             f"{settings.resource_prefix}-journey-read")},
            {"name": "usage_before_install", "origin": "service", "route": "/api/v1/usage", "payload": None,
             "key_variable": variable},
            {"name": "health_through_the_loopback_forwarder", "origin": "loopback", "route": "/api/v1/health",
             "payload": None, "key_variable": None},
        ]
        answers = self.probe(client, server_origin, "customer-journey", cases,
                             extra_origins={"loopback": loopback_origin})
        self.observations["journey"] = {name: {key: value for key, value in row.items() if key != "result"}
                                        for name, row in answers.items()}

        self.check("health_answers_on_the_private_network_without_a_key",
                   answers["health"]["status"] == 200
                   and (answers["health"]["result"] or {}).get("healthy") is True
                   and answers["health"].get("record_type") == SERVED_HEALTH_RECORD_TYPE)
        self.check("usage_is_refused_without_a_key",
                   answers["usage_without_a_key"]["status"] == 401
                   and answers["usage_without_a_key"]["code"] == UNAUTHORIZED_CODE,
                   str(answers["usage_without_a_key"]["status"]))
        metered = ("manifest_without_a_key", "download_without_a_key")
        self.check("the_metered_routes_are_refused_without_a_key",
                   all(answers[name]["status"] == 401 and answers[name]["code"] == UNAUTHORIZED_CODE
                       for name in metered),
                   json.dumps({name: answers[name]["status"] for name in metered}))
        unexpected = answers["manifest_with_an_unexpected_host_header"]
        self.check("a_request_whose_host_header_is_outside_the_declared_list_is_refused",
                   unexpected["status"] == UNEXPECTED_HOST_STATUS and unexpected["code"] == INVALID_HOST_CODE,
                   unexpected["code"] or str(unexpected["status"]))
        offered = tuple(sorted(hit["reference"]["identity"]
                               for hit in (answers["search"]["result"] or {}).get("hits", [])))
        expected = selection.offered_to(settings.first_tenant.tenant_id, settings)
        self.check("search_offers_exactly_the_items_granted_to_that_tenant", offered == expected,
                   f"offered {len(offered)}")
        self.check("search_never_offers_an_item_of_the_other_tenant",
                   not set(offered) & {row["reference"]["identity"] for row in selection.second_tenant_only})
        self.check("every_selected_identity_was_offered_by_search", set(selected) <= set(offered))

        manifest = answers["manifest"]["result"] or {}
        self.check("the_manifest_names_the_digest_and_size_of_a_selected_item",
                   manifest.get("identity") == manifest_target
                   and bool(DIGEST_PATTERN.fullmatch(str(manifest.get("digest"))))
                   and isinstance(manifest.get("size_bytes"), int) and manifest["size_bytes"] > 0)
        download = answers["download"]
        self.check("the_downloaded_body_matches_the_manifest_digest_and_the_response_header",
                   download["status"] == 200 and download.get("body_sha256") == manifest.get("digest")
                   and download.get("digest_header") == manifest.get("digest")
                   and download.get("body_bytes") == manifest.get("size_bytes"),
                   download.get("digest_header") or str(download["status"]))
        served_versions = {"retrieval": answers["search"].get("record_type"),
                           "manifest": answers["manifest"].get("record_type"),
                           "download": download.get("record_type_header")}
        self.observations["served_record_types"] = served_versions
        self.check("the_service_serves_the_record_versions_this_drill_reads",
                   served_versions == {"retrieval": SERVED_RETRIEVAL_RECORD_TYPE,
                                       "manifest": SERVED_MANIFEST_RECORD_TYPE,
                                       "download": SERVED_DOWNLOAD_RECORD_TYPE},
                   json.dumps(served_versions))
        self.check("the_loopback_forwarder_reaches_the_same_service",
                   answers["health_through_the_loopback_forwarder"]["status"] == 200)

        self.check("plain_http_to_a_non_loopback_host_is_refused_by_the_install_tool",
                   self.install_refuses_plain_http(client, server_origin))
        install = self.install(client, loopback_origin, selected)
        verified = self.verify_installed_files(client, install, answers, selected)
        usage_after = self.probe(client, server_origin, "usage-after-install", [
            {"name": "usage", "origin": "service", "route": "/api/v1/usage", "payload": None,
             "key_variable": variable}])["usage"]
        before = ((answers["usage_before_install"]["result"] or {}).get("totals") or {}).get("provisioned_item", 0)
        after = ((usage_after["result"] or {}).get("totals") or {}).get("provisioned_item", 0)
        self.observations["usage"] = {"before_install": before, "after_install": after}
        self.check("usage_counts_every_downloaded_item", after == before + len(selected),
                   f"{before} then {after}")

        summary = install["summary"]
        listing = install["listing"]
        state = listing["state"]
        self.observations["install"] = {"summary": summary, "listing_state": state,
                                        "client_version": listing.get("client_version"),
                                        "layout_observed_with_this_version": listing.get(
                                            "layout_observed_with_this_version"),
                                        "client_command_arguments": listing.get("command_arguments"),
                                        "model_turns_started": listing.get("model_turns_started"),
                                        "service_refusal": install["service_refusal"]}
        reported = summary["reported_by_client"] if state == OBSERVED_LISTING_STATE else None
        if state == OBSERVED_LISTING_STATE:
            self.check("the_client_reports_every_installed_item_under_its_own_name",
                       summary["reported_by_client"] == len(selected), state)
            # The client command the install run recorded is read back here. A
            # listing subcommand is not a model turn; a run subcommand is.
            self.check("the_client_listing_started_no_model_turn",
                       listing.get("command_arguments") == EXPECTED_LISTING_ARGUMENTS
                       and listing.get("model_turns_started") == 0,
                       json.dumps(listing.get("command_arguments")))
        else:
            for name in CHECKS_THAT_NEED_THE_CLIENT_LISTING:
                self.skip(name, f"the client listing state was {state}")
        return {"record_type": FACTS_RECORD_TYPE,
                "registered_in_the_host_manifest": len(selection.registered),
                "offered_to_the_first_tenant": len(offered),
                "offered_to_the_second_tenant": len(selection.offered_to(settings.second_tenant.tenant_id, settings)),
                "selected_for_install": len(selected),
                "fetched_by_the_install_run": summary["fetched"],
                "installed_in_the_native_client_layout": summary["installed"],
                "verified_against_the_served_digest": verified,
                "reported_by_the_client": reported}

    def install_refuses_plain_http(self, client: str, server_origin: str) -> bool:
        """A negative control: the install tool takes HTTPS or a loopback address only."""
        settings = self.settings
        result = self.docker("exec", client, "python", "/tools/install_selected_material.py",
                             "--origin", server_origin, "--key-variable", settings.first_tenant.key_variable,
                             "--client", CLIENT_KIND, "--target", "/client/project",
                             "--report", "/client/reports/refused-plain-http.json",
                             "--identity", "any_identity", "--authorize-install",
                             timeout=settings.journey_timeout_seconds)
        refusal = {}
        for line in result.stderr.strip().splitlines():
            try:
                refusal = json.loads(line)
            except ValueError:
                continue
        self.observations["install_refusal_without_https"] = {"exit_code": result.returncode,
                                                              "refused": refusal.get("refused")}
        return result.returncode == 2 and refusal.get("refused") == "invalid_origin"

    def install(self, client: str, origin: str, identities) -> dict:
        settings = self.settings
        arguments = ["exec", client, "python", "/tools/install_selected_material.py",
                     "--origin", origin, "--key-variable", settings.first_tenant.key_variable,
                     "--client", CLIENT_KIND, "--target", "/client/project",
                     "--report", "/client/reports/install.json",
                     "--request-prefix", f"{settings.resource_prefix}-install",
                     "--allow-loopback-http", "--authorize-install"]
        if settings.client_executable_on_this_machine is not None:
            arguments += ["--client-executable", f"/usr/local/bin/{CLIENT_KIND}"]
        for identity in identities:
            arguments += ["--identity", identity]
        result = self.docker(*arguments, timeout=settings.journey_timeout_seconds)
        read = self.docker("exec", client, "cat", "/client/reports/install.json")
        _refuse_unless(read.ok, "install_report_not_written")
        report = read.json()
        _refuse_unless(report.get("record_type") == INSTALL_REPORT_RECORD_TYPE, "unsupported_install_report")
        self.check("the_install_run_completed_and_the_service_refused_nothing",
                   report.get("complete") is True and report.get("service_refusal") is None,
                   "" if report.get("complete") else "the install run did not complete")
        summary = report["summary"]
        self.check("every_selected_item_was_offered_fetched_and_installed",
                   summary["selected"] == len(identities) and summary["offered"] == len(identities)
                   and summary["fetched"] == len(identities) and summary["installed"] == len(identities)
                   and summary["refused"] == 0,
                   json.dumps(summary))
        # The install run starts one client process at most, and the report
        # records the arguments it used. The check reads those arguments back
        # rather than trusting the count the report declares beside them.
        recorded = client_commands_in(report)
        self.observations["client_commands_the_install_run_recorded"] = recorded
        self.check("the_install_run_started_no_model_turn",
                   report.get("model_turns_started") == 0
                   and all(not set(command) & set(MODEL_TURN_SUBCOMMANDS) for command in recorded),
                   json.dumps(recorded))
        self.observations["install_exit_code"] = result.returncode
        return report

    def verify_installed_files(self, client: str, install: dict, answers: dict, identities) -> int:
        """Read each installed file back and compare its served part with the service."""
        installed = [item["install"] for item in install["items"] if item.get("install")]
        answer = self.run_in(client, READ_INSTALLED_FILES, "read-installed",
                             {"project": "/client/project", "installed": installed})
        by_identity = {row["identity"]: row for row in answer["files"]}
        self.observations["installed_files"] = answer["files"]
        self.observations["native_paths"] = answer["all_paths"]
        verified = 0
        for record in installed:
            row = by_identity.get(record["identity"], {})
            if (row.get("present") is True and row.get("file_sha256") == record["file_sha256"]
                    and row.get("served_body_sha256") == record["body_sha256"]
                    and row.get("served_body_bytes") == record["body_bytes"]):
                verified += 1
        self.check("every_installed_file_holds_the_served_body_byte_for_byte",
                   verified == len(identities), f"{verified} of {len(identities)}")
        self.check("every_installed_file_sits_in_the_native_client_layout",
                   bool(installed) and all(record["path"].startswith(NATIVE_LAYOUT_PREFIX + "/")
                                           and record["path"].endswith("/SKILL.md") for record in installed))
        manifest = answers["manifest"]["result"] or {}
        target = [record for record in installed if record["identity"] == manifest.get("identity")]
        self.check("the_installed_body_matches_the_digest_the_manifest_named",
                   bool(target) and target[0]["body_sha256"] == manifest.get("digest"))
        return verified

    def refusals(self, server: str, client: str, other: str, server_origin: str,
                 selection: CatalogueSelection, drill_key_id: str) -> None:
        settings = self.settings
        alpha_only = selection.first_tenant_only[0]["reference"]["identity"]
        shared = selection.shared[0]["reference"]["identity"]
        second = settings.second_tenant.key_variable

        answers = self.probe(other, server_origin, "other-tenant", [
            {"name": "other_tenant_manifest", "origin": "service", "route": "/api/v1/provisioning",
             "key_variable": second, "payload": provisioning_request("manifest", alpha_only)},
            {"name": "other_tenant_download", "origin": "service", "route": "/api/v1/download",
             "key_variable": second,
             "payload": provisioning_request("read", alpha_only, f"{settings.resource_prefix}-other-read")},
            {"name": "other_tenant_shared_manifest", "origin": "service", "route": "/api/v1/provisioning",
             "key_variable": second, "payload": provisioning_request("manifest", shared)},
            {"name": "revocation_drill_before", "origin": "service", "route": "/api/v1/usage", "payload": None,
             "key_variable": REVOCATION_DRILL_VARIABLE},
        ])
        self.observations["refusals"] = {name: {key: value for key, value in row.items() if key != "result"}
                                         for name, row in answers.items()}
        self.check("an_item_granted_to_the_other_tenant_is_refused",
                   answers["other_tenant_manifest"]["status"] == 404
                   and answers["other_tenant_manifest"]["code"] == "item_unavailable"
                   and answers["other_tenant_download"]["status"] == 404
                   and answers["other_tenant_download"]["code"] == "item_unavailable",
                   answers["other_tenant_manifest"]["code"] or "")
        self.check("a_shared_item_is_still_served_to_the_other_tenant",
                   answers["other_tenant_shared_manifest"]["status"] == 200
                   and (answers["other_tenant_shared_manifest"]["result"] or {}).get("identity") == shared)

        before = answers["revocation_drill_before"]["status"]
        revoked = self.run_in(server, REVOKE_ISSUED_KEY, "revoke-key",
                              {"database_path": "/data/service.sqlite3",
                               "tenant_id": settings.first_tenant.tenant_id, "key_id": drill_key_id})
        after = self.probe(other, server_origin, "revocation-drill-after", [
            {"name": "revocation_drill_after", "origin": "service", "route": "/api/v1/usage", "payload": None,
             "key_variable": REVOCATION_DRILL_VARIABLE}])["revocation_drill_after"]
        self.observations["revocation"] = {"committed": revoked.get("committed"), "before": before,
                                           "after_status": after["status"], "after_code": after["code"]}
        self.check("a_revoked_key_is_refused_at_the_next_request",
                   before == 200 and revoked.get("revoked") is True and revoked.get("committed") is True
                   and after["status"] == 401 and after["code"] == "unauthorized",
                   f"{before} then {after['status']}")

        self.tampered_body(server, client, server_origin, selection)

    def tampered_body(self, server: str, client: str, server_origin: str, selection: CatalogueSelection) -> None:
        """Change the bytes of one reviewed body, then put them back."""
        settings = self.settings
        identity = selection.tamper_target
        variable = settings.first_tenant.key_variable
        artifact_root = self.observations["server_volume"]["artifact_root"]
        plan = {"artifact_root": artifact_root, "identity": identity, "kept_copy": "/data/kept-original.bin"}
        tampered = self.run_in(server, TAMPER_SERVED_BODY, "tamper-body", {**plan, "action": "tamper"})
        during = self.probe(client, server_origin, "tampered-download", [
            {"name": "tampered_download", "origin": "service", "route": "/api/v1/download", "binary": True,
             "key_variable": variable,
             "payload": provisioning_request("read", identity, f"{settings.resource_prefix}-tampered-read")}])
        restored = self.run_in(server, TAMPER_SERVED_BODY, "restore-body", {**plan, "action": "restore"})
        afterwards = self.probe(client, server_origin, "restored-download", [
            {"name": "restored_download", "origin": "service", "route": "/api/v1/download", "binary": True,
             "key_variable": variable,
             "payload": provisioning_request("read", identity, f"{settings.resource_prefix}-restored-read")}])
        expected = [row["reference"]["digest"] for row in selection.registered
                    if row["reference"]["identity"] == identity][0]
        self.observations["tampered_body"] = {
            "identity": identity, "same_size": tampered["size_bytes"] == restored["size_bytes"],
            "tampered": {key: value for key, value in during["tampered_download"].items() if key != "result"},
            "restored": {key: value for key, value in afterwards["restored_download"].items() if key != "result"}}
        self.check("a_body_whose_bytes_no_longer_match_its_reviewed_digest_is_refused",
                   during["tampered_download"]["status"] == 400
                   and during["tampered_download"]["code"] == "body_integrity_failed",
                   during["tampered_download"]["code"] or str(during["tampered_download"]["status"]))
        self.check("the_restored_body_is_served_again_with_its_reviewed_digest",
                   afterwards["restored_download"]["status"] == 200
                   and afterwards["restored_download"].get("body_sha256") == expected
                   and restored["sha256"] == expected)

    def restart_and_read_usage(self, server: str, client: str, server_origin: str) -> None:
        settings = self.settings
        variable = settings.first_tenant.key_variable
        case = [{"name": "usage", "origin": "service", "route": "/api/v1/usage", "payload": None,
                 "key_variable": variable}]
        before = self.probe(client, server_origin, "usage-before-restart", case)["usage"]
        result = self.docker("restart", server)
        _refuse_unless(result.ok, "server_not_restarted")
        self.wait_for_health(client, server_origin)
        after = self.probe(client, server_origin, "usage-after-restart", case)["usage"]
        totals_before = (before["result"] or {}).get("totals") or {}
        totals_after = (after["result"] or {}).get("totals") or {}
        self.observations["usage_across_restart"] = {"before": totals_before, "after": totals_after,
                                                     "records_before": (before["result"] or {}).get("records"),
                                                     "records_after": (after["result"] or {}).get("records")}
        self.check("the_restarted_server_on_the_same_volume_still_knows_the_usage",
                   before["status"] == 200 and after["status"] == 200 and bool(totals_after)
                   and totals_after == totals_before
                   and totals_after.get("provisioned_item", 0) > 0,
                   json.dumps(totals_after))


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

LIMITATIONS = (
    "Two local containers on a private Docker network. No public name, no certificate and no proxy.",
    "The identity provider, the payment provider and the browser are absent. A key is issued by the host command.",
    "No model turn runs. A file the client lists is material it discovered, not material a model used.",
    "The install tool accepts HTTPS or a loopback address, so the client container forwards a local port to the "
    "server container. The bytes still cross the private network between the two containers.",
    "The host attests the catalogue items. Host attestation is not independent qualification.",
)


#: The two checks whose result decides what the report says about external
#: connectivity. Nothing in the report states that answer on its own.
NETWORK_CHECKS = ("private_network_has_no_external_connectivity",
                  "client_container_has_no_route_off_this_machine")


def source_hashes(repository: Path) -> dict:
    return {name: hashlib.sha256((repository / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def external_network_available(checks) -> bool | None:
    """Derived from the two network checks that ran, or unknown when they did not.

    This is not a statement the drill makes about itself. It is what the two
    checks observed: a private network Docker reports as internal, and a client
    container with no default route and no name resolution.
    """
    passed = {row["name"]: row["passed"] for row in checks}
    if not all(name in passed for name in NETWORK_CHECKS):
        return None
    return not all(passed[name] for name in NETWORK_CHECKS)


def declared_conditions() -> dict:
    """What this drill asks for, kept apart from what it observed.

    These numbers are not measurements. They record that the drill requests no
    model turn and no provider call anywhere, and writes no credential into its
    report. The checks above observe the service; these values describe how the
    drill itself was written. A reader should not mistake one for the other.
    """
    return {"record_type": DECLARED_RECORD_TYPE,
            "model_turns_started": 0,
            "provider_requests": 0,
            "credentials_in_this_report": 0,
            "basis": "declared by this drill, not measured by a check"}


def build_report(settings: DrillSettings, drill: ContainerJourneyDrill, facts, cleanup, failure=None) -> dict:
    checks = drill.checks
    return {"record_type": REPORT_RECORD_TYPE,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "settings": settings.public_summary(),
            "image_identity": drill.observations.get("image_identity"),
            "source_files": source_hashes(settings.repository),
            "facts": facts,
            "declared": declared_conditions(),
            "observations": drill.observations,
            "checks": checks,
            "skipped_checks": drill.skipped,
            "passed": sum(row["passed"] for row in checks), "total": len(checks),
            "all_passed": bool(checks) and all(row["passed"] for row in checks) and failure is None,
            "failure": failure,
            "docker_calls": len(drill.calls),
            "external_network_available_to_the_containers": external_network_available(checks),
            "cleanup": cleanup,
            "limitations": list(LIMITATIONS)}


def run_drill(settings: DrillSettings, runner=None) -> dict:
    drill = ContainerJourneyDrill(settings, runner)
    facts, failure = None, None
    try:
        facts = drill.run_journey()
    except DrillRefusal as refusal:
        failure = {"code": refusal.code, "detail": refusal.detail}
    except Exception as error:  # The type only: the text could repeat container output.
        failure = {"code": "unexpected_error", "detail": type(error).__name__}
    cleanup = drill.remove_created_resources()
    drill.check("every_container_network_volume_and_image_of_this_run_was_removed",
                not cleanup["still_present"], json.dumps(cleanup["still_present"]))
    return build_report(settings, drill, facts, cleanup, failure)


def reserve_report(path: Path) -> int:
    """Create the report exclusively before the drill starts.

    The drill takes several minutes. Checking that a path is free and opening
    it at the end leaves a window in which another writer can take the name,
    and the whole run would then be lost. The name is taken first instead, and
    a placeholder marks it as an unfinished run until the report is written.
    """
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o644)
    except FileExistsError:
        raise DrillRefusal("report_path_exists", str(path)) from None
    except OSError as error:
        raise DrillRefusal("report_path_is_not_usable", type(error).__name__) from None
    write_reserved_report(descriptor, {"record_type": REPORT_RECORD_TYPE, "complete": False})
    return descriptor


def write_reserved_report(descriptor: int, report: dict) -> None:
    """Write the whole report into the descriptor this run reserved."""
    data = (json.dumps(report, indent=1, sort_keys=True) + "\n").encode("utf-8")
    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view):]


def default_settings(repository: Path, report: Path, client_executable=None) -> DrillSettings:
    """Name every resource of this run after one value no other run shares."""
    prefix = "journey-drill-" + uuid.uuid4().hex[:12]
    return DrillSettings(
        repository=repository, report=report, resource_prefix=prefix,
        image_reference=f"loop-engine-service:{prefix}",
        first_tenant=TenantPlan("first-tenant", "first-tenant:private", FIRST_TENANT_VARIABLE),
        second_tenant=TenantPlan("second-tenant", "second-tenant:private", SECOND_TENANT_VARIABLE),
        client_executable_on_this_machine=client_executable)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", required=True, type=Path, help="New report path. It may not exist yet.")
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Working tree the image is built from.")
    parser.add_argument("--client-binary", type=Path, default=None,
                        help="A client executable on this machine to mount read only, so the drill can also "
                             "observe the client's own listing. No subcommand that starts a model turn is run.")
    arguments = parser.parse_args(argv)
    report_path = arguments.report.resolve()
    try:
        settings = default_settings(arguments.repository.resolve(), report_path,
                                    None if arguments.client_binary is None else arguments.client_binary.resolve())
        descriptor = reserve_report(report_path)
    except DrillRefusal as refusal:
        print(json.dumps({"refused": refusal.code, "detail": refusal.detail, "report": str(report_path)}))
        return 2
    try:
        report = run_drill(settings)
        write_reserved_report(descriptor, report)
    finally:
        os.close(descriptor)
    print(json.dumps({"record_type": REPORT_RECORD_TYPE, "all_passed": report["all_passed"],
                      "passed": report["passed"], "total": report["total"],
                      "skipped": len(report["skipped_checks"]), "failure": report["failure"],
                      "facts": report["facts"], "report": str(report_path)}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
