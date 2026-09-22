"""Test the service image's default command in an isolated local container.

Only an explicitly named local image is used. The disposable volume contains
an empty catalogue and no credential. No container has external networking.

The deployment workflow runs this check with the runner's own Python and no
installed package, so it imports nothing from the repository.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
#: Where the release copies the reviewed catalogue, and the repository files the
#: image is built from. The host configuration on the volume points at the first.
IMAGE_CATALOGUE_ROOT = "/opt/baltor/catalogue"
IMAGE_MANIFEST_PATH = IMAGE_CATALOGUE_ROOT + "/manifest.json"
CATALOGUE_MANIFEST = "examples/29_intelligence_service/starter-catalogue/host-release/manifest.json"
REVIEW_RECORD = "examples/29_intelligence_service/starter-catalogue/reviews.json"
#: The service runs as this identity, so the packaged catalogue is owned by it
#: and carries no write bit for anyone.
SERVICE_USER = 65534
#: The command the image runs when it is started without one. It binds every
#: address and declares a trusted proxy in front of the service.
DEFAULT_COMMAND = ["service", "serve", "--config", "/data/host.json",
                   "--host", "0.0.0.0", "--port", "8080", "--behind-trusted-tls-proxy"]
HOST_CONFIGURATION_RECORD_TYPE = "service_http_host_configuration/v1"
MANIFEST_RECORD_TYPE = "host_attested_intelligence_manifest/v1"
#: Where the hosted service reads each caller's address. A service bound to
#: every address behind a trusted proxy refuses to start until its host file
#: names the header that proxy writes on every request, because the socket peer
#: is then the proxy and every caller would share one count of refused sign-in
#: attempts. The host file on the Fly volume names the Fly proxy's header, so
#: every host file this check writes names the same one, and the image starts
#: here the way it starts in production.
FLY_REQUEST_LIMITS = {"record_type": "service_request_limits/v1",
                      "client_address_source": "header", "client_address_header": "Fly-Client-IP"}


def command(arguments, timeout=60):
    return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=True).stdout


def default_command_host_configuration():
    """The host file of the default command check: an empty catalogue and no tenant.

    Its public origin is a name under the reserved `.invalid` top level name,
    which can never resolve anywhere.
    """
    origin = "https://pilot-test.invalid"
    return {"record_type": HOST_CONFIGURATION_RECORD_TYPE,
            "runtime": {"database_path": "/data/service.sqlite3", "writes_authorized": True},
            "http": {"public_base_url": origin,
                     "allowed_hosts": ["pilot-test.invalid", "localhost:8080"],
                     "allowed_origins": [origin],
                     "request_limits": dict(FLY_REQUEST_LIMITS)},
            "authentication": {"modes": ["host_key"]}, "manifest_path": "/data/manifest.json"}


def packaged_catalogue_host_configuration(tenants):
    """The host file of the packaged catalogue check.

    It names the manifest inside the image and registers exactly the tenants
    that manifest grants to, each with an operator entitlement that is not a
    payment. Its public origin is a name under the reserved `.invalid` top
    level name, which can never resolve anywhere.
    """
    origin = "https://catalogue-test.invalid"
    return {"record_type": HOST_CONFIGURATION_RECORD_TYPE,
            "runtime": {"database_path": "/data/state/service.db", "writes_authorized": True},
            "http": {"public_base_url": origin,
                     "allowed_hosts": ["catalogue-test.invalid", "localhost:8080"],
                     "allowed_origins": [origin],
                     "request_limits": dict(FLY_REQUEST_LIMITS)},
            "authentication": {"modes": ["host_key"]},
            "manifest_path": IMAGE_MANIFEST_PATH,
            "tenants": [{"tenant_id": name, "namespace": name + ":private",
                         "operator_entitlement": {"valid_until": 4102444800,
                                                  "evidence_ref": "local_container_check_not_payment"}}
                        for name in tenants]}


def without_client_address_source(configuration):
    """The known-wrong host file: the same file without the client address statement."""
    changed = json.loads(json.dumps(configuration))
    del changed["http"]["request_limits"]
    return changed


#: Seed a disposable volume with an empty catalogue and one host file. The host
#: file arrives as text, so this script states no setting of its own.
EMPTY_CATALOGUE_VOLUME = '''
import json, os
from pathlib import Path
root = Path("/data")
(root / "artifacts").mkdir()
(root / "manifest.json").write_text(json.dumps({{
    "record_type": {manifest_record_type!r},
    "artifact_root": "/data/artifacts", "items": []}}))
(root / "host.json").write_text({host!r})
os.chown(root, {user}, {user})
os.chmod(root, 0o700)
for path in root.iterdir():
    os.chown(path, {user}, {user})
    os.chmod(path, 0o700 if path.is_dir() else 0o600)
'''


def seed_empty_catalogue_volume(image, volume, configuration):
    setup = EMPTY_CATALOGUE_VOLUME.format(manifest_record_type=MANIFEST_RECORD_TYPE,
                                          host=json.dumps(configuration), user=SERVICE_USER)
    command(["docker", "run", "--rm", "--network", "none", "--user", "0:0",
             "--mount", f"type=volume,src={volume},dst=/data", "--entrypoint", "python", image, "-c", setup])


def check_image(image):
    details = json.loads(command(["docker", "image", "inspect", image]))[0]
    checks = []
    def record(name, passed):
        checks.append({"name": name, "passed": bool(passed)})

    record("runtime_user_is_unprivileged", details["Config"]["User"] == "65534:65534")
    record("default_command_starts_the_service", details["Config"]["Entrypoint"] == ["loop-engine"]
           and details["Config"]["Cmd"] == DEFAULT_COMMAND)
    common = ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", image]
    doctor = json.loads(command([*common, "doctor", "--format", "json"]))
    record("installed_architecture_passes_without_provider_calls", doctor["ok"] and doctor["provider_calls_made"] == 0)
    smoke = json.loads(command([*common, "service", "smoke"], timeout=120))
    record("installed_protocol_and_service_checks_pass", smoke["all_passed"] and smoke["total"] > 0)

    volume = "loop-engine-fly-test-" + uuid.uuid4().hex
    container = None
    command(["docker", "volume", "create", "--label", "loop-engine.purpose=local-service-check", volume])
    try:
        seed_empty_catalogue_volume(image, volume, default_command_host_configuration())
        container = command(["docker", "run", "--detach", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", "--mount", f"type=volume,src={volume},dst=/data", image]).strip()
        probe = '''
import json, urllib.error, urllib.request
with urllib.request.urlopen('http://localhost:8080/api/v1/health', timeout=2) as response:
    health = json.load(response)['result']
assert health['record_type'] == 'service_health/v2'
assert health['alive'] is True and health['ready'] is True and health['readiness_checked'] is True
assert all(row['passed'] for row in health['checks'] if row['required'])
try:
    urllib.request.urlopen('http://localhost:8080/api/v1/session', timeout=2)
except urllib.error.HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError('Session endpoint accepted an unauthenticated request')
print('default service responds and refuses unauthenticated access')
'''
        deadline = time.monotonic() + 30
        while True:
            observed = subprocess.run(["docker", "exec", container, "python", "-c", probe],
                                      capture_output=True, text=True, timeout=10)
            if observed.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("The default container command did not pass the local health and authentication probe")
            time.sleep(0.2)
        record("default_server_and_health_host_work_with_the_volume", True)
        record("default_server_refuses_unauthenticated_session_access", True)
        command(["docker", "restart", container])
        deadline = time.monotonic() + 30
        while True:
            observed = subprocess.run(["docker", "exec", container, "python", "-c", probe],
                                      capture_output=True, text=True, timeout=10)
            if observed.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("The restarted service did not pass the local probe")
            time.sleep(0.2)
        record("service_restarts_with_the_same_volume_and_configuration", True)
    finally:
        if container is not None:
            command(["docker", "rm", "--force", container])
        command(["docker", "volume", "rm", volume])
    check_refusal_without_client_address_source(image, record)
    catalogue = check_packaged_catalogue(image, record)
    paths = ("Dockerfile.service", "fly.toml", ".dockerignore", ".github/workflows/fly-pilot.yml",
             "tools/test_fly_deployment.py", "tools/check_fly_service_container.py",
             "tools/build_host_catalogue_manifest.py", CATALOGUE_MANIFEST, REVIEW_RECORD)
    return {"record_type": "fly_service_container_check/v1", "checked_at": datetime.now(timezone.utc).isoformat(),
            "image_id": details["Id"], "image_reference": image,
            "source_files": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
            "checks": checks, "passed": sum(row["passed"] for row in checks), "total": len(checks),
            "all_passed": all(row["passed"] for row in checks), "service_smoke": smoke,
            "packaged_catalogue": catalogue,
            "external_provider_calls": 0, "fly_deployed": False, "local_test_volume_removed": True}


def check_refusal_without_client_address_source(image, record):
    """Start the image's own command with the known-wrong host file and require it to stop.

    The file is the default command check's host file with the client address
    statement removed and nothing else changed. The service must stop before
    it serves anyone and name the missing setting. A service that started
    anyway would serve the public with no limit on refused sign-in attempts,
    and the default command check above would then prove nothing about the
    statement it now carries.
    """
    volume = "loop-engine-fly-refusal-test-" + uuid.uuid4().hex
    container = None
    command(["docker", "volume", "create", "--label", "loop-engine.purpose=local-service-check", volume])
    try:
        seed_empty_catalogue_volume(image, volume, without_client_address_source(default_command_host_configuration()))
        container = command(["docker", "run", "--detach", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", "--mount", f"type=volume,src={volume},dst=/data", image]).strip()
        try:
            stopped_with = int(command(["docker", "wait", container], timeout=90).strip())
        except subprocess.TimeoutExpired:
            stopped_with = None
        # The complaint is read for the name of the missing setting only. It is
        # not copied into the report.
        complaint = subprocess.run(["docker", "logs", container], capture_output=True, text=True, timeout=30).stderr
        record("default_command_refuses_a_public_binding_without_a_client_address_source",
               stopped_with == 2 and '"request_limits"' in complaint)
    finally:
        if container is not None:
            command(["docker", "rm", "--force", container])
        command(["docker", "volume", "rm", volume])


def check_packaged_catalogue(image, record):
    """Start the image against a host configuration that names the packaged manifest.

    The disposable volume holds only the host configuration and the service
    state. The catalogue itself is in the image. No container has external
    networking. The one-time local key is written inside the container, is read
    only inside the container, and is destroyed with the volume; it never
    reaches this program, its report or its output.
    """
    review = json.loads((ROOT / REVIEW_RECORD).read_text("utf-8"))
    approved = sorted(row["identity"] for row in review["rows"] if row["outcome"] == "approved")
    rejected = sorted(row["identity"] for row in review["rows"] if row["outcome"] == "rejected")
    packaged = json.loads((ROOT / CATALOGUE_MANIFEST).read_text("utf-8"))
    if sorted(row["reference"]["identity"] for row in packaged["items"]) != approved:
        raise RuntimeError("The generated manifest and the review record disagree about the approved set")
    # The disposable host registers exactly the tenants the packaged manifest
    # grants to, so the check exercises the release's own grants rather than a
    # tenant invented here.
    tenants = sorted({grant["tenant_id"] for row in packaged["items"] for grant in row["grants"]})
    if not tenants:
        raise RuntimeError("The packaged manifest grants no tenant, so nothing could be served")
    subject = tenants[0]

    ownership = '''
import json, os, stat
from pathlib import Path
root = Path({root!r})
rows = sorted(root.rglob("*"))
files = [path for path in rows if path.is_file()]
print(json.dumps({{
    "present": (root / "manifest.json").is_file(),
    "files": len(files),
    "owned_by_the_service_user": all(path.stat().st_uid == {user} and path.stat().st_gid == {user}
                                     for path in [root, *rows]),
    "no_write_bit_anywhere": all(not path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
                                 for path in [root, *rows]),
    "no_symbolic_links": all(not path.is_symlink() for path in rows),
}}))
'''.format(root=IMAGE_CATALOGUE_ROOT, user=SERVICE_USER)
    common = ["docker", "run", "--rm", "--network", "none", "--read-only",
              "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", "--entrypoint", "python", image]
    layout = json.loads(command([*common, "-c", ownership]))
    record("release_catalogue_is_packaged_read_only_for_the_service_user",
           layout["present"] and layout["files"] == len(approved) + 1
           and layout["owned_by_the_service_user"] and layout["no_write_bit_anywhere"]
           and layout["no_symbolic_links"])

    setup = '''
import os
from pathlib import Path
root = Path("/data")
(root / "state").mkdir()
(root / "host.json").write_text({host!r})
os.chown(root, {user}, {user})
os.chmod(root, 0o700)
for path in root.rglob("*"):
    os.chown(path, {user}, {user})
    os.chmod(path, 0o700 if path.is_dir() else 0o600)
'''.format(host=json.dumps(packaged_catalogue_host_configuration(tenants)), user=SERVICE_USER)
    issue = '''
import json, os
from loop_engine.core.service_runtime.http_entrypoint import configure_host, load_host_application
from loop_engine.core.service_runtime.records import TenantKeyIssue
outcome = configure_host("/data/host.json")
application, _configuration = load_host_application("/data/host.json")
issued = application.runtime.issue_key(TenantKeyIssue({subject!r}, "local container check", None))
# The one-time key is written for the probe inside this container only. It is
# never printed, never returned and is destroyed with the disposable volume.
handle = os.open("/data/state/check.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(handle, "w") as stream:
    stream.write(issued.key)
print(json.dumps({{"configured_grant_sets": outcome["configured_grant_sets"],
                   "tenants": outcome["tenants"]}}))
'''.format(subject=subject)
    probe = '''
import json, urllib.error, urllib.request
approved = json.load(open({manifest!r}))
approved = sorted(row["reference"]["identity"] for row in approved["items"])
rejected = {rejected!r}
with open("/data/state/check.key") as stream:
    key = stream.read()
def call(path, body=None):
    fields = {{"Accept": "application/json", "Authorization": "Bearer " + key}}
    if body is not None:
        fields["Content-Type"] = "application/json"
    selected = urllib.request.Request("http://localhost:8080" + path,
        None if body is None else json.dumps(body).encode(), fields)
    try:
        response = urllib.request.urlopen(selected, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read(4_000_000))
status, health = call("/api/v1/health")
assert status == 200 and health["result"]["healthy"] is True
status, capabilities = call("/api/v1/capabilities")
assert status == 200, capabilities
status, listing = call("/api/v1/provisioning",
    {{"record_type": "service_provisioning_request/v1", "operation": "list"}})
assert status == 200, listing
offered = sorted(row["identity"] for row in listing["result"]["items"])
# An item that declares an effect is withheld from a request that holds no
# authority for it. Both lists are drawn from the registered catalogue, so
# their union is what the host registered from the packaged manifest.
withheld = sorted(row["identity"] for row in listing["result"]["withheld"])
registered = sorted(offered + withheld)
status, found = call("/api/v1/retrieval",
    {{"record_type": "service_retrieval_request/v1", "query": {query!r}, "mode": "lexical", "top_n": 50}})
assert status == 200, found
hits = sorted(hit["reference"]["identity"] for hit in found["result"]["hits"])
unreachable = []
for identity in rejected:
    code, _refusal = call("/api/v1/provisioning", {{"record_type": "service_provisioning_request/v1",
        "operation": "read", "identity": identity, "request_id": "rejected-" + identity}})
    unreachable.append(code in (403, 404))
selected = approved[0]
status, body = call("/api/v1/provisioning", {{"record_type": "service_provisioning_request/v1",
    "operation": "read", "identity": selected, "request_id": "approved-" + selected}})
print(json.dumps({{
    "registered_is_exactly_the_approved_set": registered == approved,
    "offered_items": len(offered),
    "withheld_for_undeclared_authority": len(withheld),
    "no_rejected_item_is_offered": not (set(registered) & set(rejected)),
    "search_returns_only_approved_items": bool(hits) and not (set(hits) & set(rejected)),
    "search_hits": len(hits),
    "every_rejected_item_is_unreachable_by_direct_address": all(unreachable),
    "an_approved_body_is_served": status == 200 and len(body["result"]["body"]) > 0,
    "capabilities_record_type": capabilities["result"]["record_type"],
    "bodies_loaded_by_search": found["result"]["bodies_loaded"],
}}))
'''.format(manifest=IMAGE_MANIFEST_PATH, rejected=rejected, query="duplicate records")

    volume = "loop-engine-catalogue-test-" + uuid.uuid4().hex
    container = None
    command(["docker", "volume", "create", "--label", "loop-engine.purpose=local-catalogue-check", volume])
    try:
        mount = f"type=volume,src={volume},dst=/data"
        command(["docker", "run", "--rm", "--network", "none", "--user", "0:0", "--mount", mount,
                 "--entrypoint", "python", image, "-c", setup])
        configured = json.loads(command(["docker", "run", "--rm", "--network", "none",
            "--user", f"{SERVICE_USER}:{SERVICE_USER}", "--mount", mount,
            "--entrypoint", "python", image, "-c", issue], timeout=180))
        record("host_setup_reads_the_packaged_manifest_and_grants_its_items",
               configured["configured_grant_sets"] == len(tenants) and configured["tenants"] == tenants)
        container = command(["docker", "run", "--detach", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", "--mount", mount, image]).strip()
        deadline, observed = time.monotonic() + 60, None
        while True:
            observed = subprocess.run(["docker", "exec", container, "python", "-c", probe],
                                      capture_output=True, text=True, timeout=60)
            if observed.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("The service did not answer with the packaged catalogue: "
                                   + observed.stderr.strip()[-400:])
            time.sleep(0.5)
        answered = json.loads(observed.stdout)
        record("the_service_starts_against_the_packaged_manifest", True)
        record("only_the_approved_items_are_registered_for_a_granted_tenant",
               answered["registered_is_exactly_the_approved_set"] and answered["no_rejected_item_is_offered"])
        record("search_returns_the_approved_items_and_loads_no_body",
               answered["search_returns_only_approved_items"] and answered["bodies_loaded_by_search"] is False)
        record("no_rejected_item_is_reachable_by_search_or_by_direct_address",
               answered["every_rejected_item_is_unreachable_by_direct_address"]
               and answered["no_rejected_item_is_offered"])
        record("an_approved_body_is_served_from_the_image_not_from_the_volume",
               answered["an_approved_body_is_served"])
    finally:
        if container is not None:
            command(["docker", "rm", "--force", container])
        command(["docker", "volume", "rm", volume])
    return {"record_type": "packaged_catalogue_check/v1", "artifact_root": IMAGE_CATALOGUE_ROOT,
            "manifest_path": IMAGE_MANIFEST_PATH, "approved_items": len(approved),
            "rejected_items_present_in_the_image": 0, "rejected_identities": rejected,
            "offered_items": answered["offered_items"],
            "withheld_for_undeclared_authority": answered["withheld_for_undeclared_authority"],
            "search_hits": answered["search_hits"],
            "capabilities_record_type": answered["capabilities_record_type"],
            "review_record": REVIEW_RECORD, "local_test_volume_removed": True,
            "one_time_local_key_left_the_container": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    if options.output.exists():
        parser.error("Refusing to overwrite a previous check report")
    try:
        report = check_image(options.image)
    except Exception as error:
        report = {"record_type": "fly_service_container_check/v1",
                  "checked_at": datetime.now(timezone.utc).isoformat(),
                  "image_reference": options.image, "all_passed": False,
                  "error_type": type(error).__name__, "fly_deployed": False,
                  "completion_state": "failed_check", "passed": None, "total": None}
    with options.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": report["passed"], "total": report["total"],
                      "service_passed": report.get("service_smoke", {}).get("passed"),
                      "service_total": report.get("service_smoke", {}).get("total"),
                      "fly_deployed": False, "output": str(options.output)}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
