"""Test the service image's default command in an isolated local container.

Only an explicitly named local image is used. The disposable volume contains
an empty catalogue and no credential. No container has external networking.
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


def command(arguments, timeout=60):
    return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=True).stdout


def check_image(image):
    details = json.loads(command(["docker", "image", "inspect", image]))[0]
    checks = []
    def record(name, passed):
        checks.append({"name": name, "passed": bool(passed)})

    record("runtime_user_is_unprivileged", details["Config"]["User"] == "65534:65534")
    record("default_command_starts_the_service", details["Config"]["Entrypoint"] == ["loop-engine"]
           and details["Config"]["Cmd"] == ["service", "serve", "--config", "/data/host.json",
                "--host", "0.0.0.0", "--port", "8080", "--behind-trusted-tls-proxy"])
    common = ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", image]
    doctor = json.loads(command([*common, "doctor", "--format", "json"]))
    record("installed_architecture_passes_without_provider_calls", doctor["ok"] and doctor["provider_calls_made"] == 0)
    smoke = json.loads(command([*common, "service", "smoke"], timeout=120))
    record("installed_protocol_and_service_checks_pass", smoke["all_passed"] and smoke["total"] > 0)

    volume = "loop-engine-fly-test-" + uuid.uuid4().hex
    container = None
    command(["docker", "volume", "create", "--label", "loop-engine.purpose=local-service-check", volume])
    try:
        setup = '''
import json, os
from pathlib import Path
root = Path('/data')
(root / 'artifacts').mkdir()
(root / 'manifest.json').write_text(json.dumps({
    'record_type': 'host_attested_intelligence_manifest/v1',
    'artifact_root': '/data/artifacts', 'items': []}))
(root / 'host.json').write_text(json.dumps({
    'record_type': 'service_http_host_configuration/v1',
    'runtime': {'database_path': '/data/service.sqlite3', 'writes_authorized': True},
    'http': {'public_base_url': 'https://pilot-test.invalid',
             'allowed_hosts': ['pilot-test.invalid', 'localhost:8080'],
             'allowed_origins': ['https://pilot-test.invalid']},
    'authentication': {'modes': ['host_key']}, 'manifest_path': '/data/manifest.json'}))
os.chown(root, 65534, 65534)
os.chmod(root, 0o700)
for path in root.iterdir():
    os.chown(path, 65534, 65534)
    os.chmod(path, 0o700 if path.is_dir() else 0o600)
'''
        command(["docker", "run", "--rm", "--network", "none", "--user", "0:0",
                 "--mount", f"type=volume,src={volume},dst=/data", "--entrypoint", "python", image, "-c", setup])
        container = command(["docker", "run", "--detach", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", "--mount", f"type=volume,src={volume},dst=/data", image]).strip()
        probe = '''
import json, urllib.error, urllib.request
with urllib.request.urlopen('http://localhost:8080/api/v1/health', timeout=2) as response:
    health = json.load(response)['result']
assert health['healthy'] is True and health['readiness_checked'] is False
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
    paths = ("Dockerfile.service", "fly.toml", ".dockerignore", ".github/workflows/fly-pilot.yml",
             "tools/test_fly_deployment.py", "tools/check_fly_service_container.py")
    return {"record_type": "fly_service_container_check/v1", "checked_at": datetime.now(timezone.utc).isoformat(),
            "image_id": details["Id"], "image_reference": image,
            "source_files": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
            "checks": checks, "passed": sum(row["passed"] for row in checks), "total": len(checks),
            "all_passed": all(row["passed"] for row in checks), "service_smoke": smoke,
            "external_provider_calls": 0, "fly_deployed": False, "local_test_volume_removed": True}


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
