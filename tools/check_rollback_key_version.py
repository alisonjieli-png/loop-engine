"""Rollback drill: an older service image must refuse customer-issued keys.

A customer-issued key is valid only while its owner's sign-in stays enabled.
A server that predates that rule cannot apply it, so it has to refuse the key
record entirely. This drill writes service state with one code version, reads
it with the real installed code of an older image, and records what happened.
It contacts no provider, starts containers without a network and never writes
a credential into its report.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPORT_VERSION = "rollback_key_version_drill/v1"
WORK = "/work"

PRODUCER = """
import sys
from pathlib import Path
from loop_engine.core.service_runtime.access_checks import customer_prepared
from loop_engine.core.service_runtime.access import ServiceAccessRequest
from loop_engine.core.service_runtime.records import SubjectBindingRequest
root = Path(sys.argv[1])
fixture = customer_prepared(root)
issued = fixture.client_access.apply(fixture.customers["customer-a"], ServiceAccessRequest(
    "issue", "rollback-device", "alpha", label="Rollback drill", scopes=("provisioning:metadata",),
    lifetime_seconds=3600), session=fixture.customer_sessions["customer-a"])
fixture.runtime.revoke_subject(SubjectBindingRequest("alpha", "https://identity.example", "customer-a"))
(root / "customer.key").write_text(issued["token"])
(root / "host.key").write_text(fixture.keys["alpha"].key)
"""

READER = """
import json, sys
from pathlib import Path
from loop_engine.core.service_runtime.records import ServiceRuntimeConfig, ServiceRuntimeError
from loop_engine.core.service_runtime.runtime import ServiceRuntime
root = Path(sys.argv[1])
runtime = ServiceRuntime(ServiceRuntimeConfig(str(root / "service.db")))
result = {}
for name in ("customer", "host"):
    try:
        runtime.authenticate_key((root / (name + ".key")).read_text())
        result[name] = "accepted"
    except ServiceRuntimeError as error:
        result[name] = "refused:" + error.code
print(json.dumps(result, sort_keys=True))
"""


def run(command, **options):
    return subprocess.run(command, capture_output=True, text=True, timeout=300, **options)


def in_image(image, script, folder):
    """Run a script with the image's installed package; no network, caller's user."""
    return run(["docker", "run", "--rm", "--network", "none", "--user", f"{os.getuid()}:{os.getgid()}",
                "--volume", f"{folder}:{WORK}", "--entrypoint", "python", image, "-c", script, WORK])


def in_source(script, folder, repository):
    environment = {**os.environ, "PYTHONPATH": str(repository / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    return run([sys.executable, "-c", script, str(folder)], env=environment)


def image_identity(image):
    done = run(["docker", "image", "inspect", image, "--format", "{{.Id}}"])
    return done.stdout.strip() if done.returncode == 0 else None


def observed(done):
    if done.returncode != 0:
        return {"error": "reader_failed", "exit_code": done.returncode}
    return json.loads(done.stdout.strip().splitlines()[-1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--older-image", required=True, help="Image of the release a rollback would return to.")
    parser.add_argument("--unfixed-image", help="Optional image of the release candidate without the version change.")
    parser.add_argument("--output", required=True, type=Path, help="New report path; an existing file is refused.")
    options = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    checks, cases = [], {}

    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})

    with tempfile.TemporaryDirectory(prefix="rollback-key-version-") as directory:
        fixed = Path(directory) / "fixed"
        fixed.mkdir()
        produced = in_source(PRODUCER, fixed, repository)
        check("current_source_writes_the_service_state", produced.returncode == 0)
        cases["current_source_read_by_current_source"] = observed(in_source(READER, fixed, repository))
        cases["current_source_read_by_older_image"] = observed(in_image(options.older_image, READER, fixed))
        check("current_server_refuses_a_key_whose_owner_was_disabled",
              cases["current_source_read_by_current_source"].get("customer") == "refused:unauthorized")
        check("older_image_refuses_the_customer_key_record",
              cases["current_source_read_by_older_image"].get("customer") == "refused:unsupported_or_corrupt_record")
        check("older_image_still_accepts_a_host_issued_key",
              cases["current_source_read_by_older_image"].get("host") == "accepted")
        if options.unfixed_image:
            unfixed = Path(directory) / "unfixed"
            unfixed.mkdir()
            control = in_image(options.unfixed_image, PRODUCER, unfixed)
            check("unfixed_candidate_writes_the_service_state", control.returncode == 0)
            cases["unfixed_candidate_read_by_older_image"] = observed(in_image(options.older_image, READER, unfixed))
            # Known-wrong control: without the version change the older image
            # honors a key whose owner was disabled. The drill must see that.
            check("drill_detects_the_defect_in_the_unfixed_candidate",
                  cases["unfixed_candidate_read_by_older_image"].get("customer") == "accepted")
    source = repository / "src" / "loop_engine" / "core" / "service_runtime"
    report = {"record_type": REPORT_VERSION, "observed_at": datetime.now(timezone.utc).isoformat(),
              "older_image": {"reference": options.older_image, "identity": image_identity(options.older_image)},
              "unfixed_image": ({"reference": options.unfixed_image, "identity": image_identity(options.unfixed_image)}
                                if options.unfixed_image else None),
              "source": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                         for name in ("access.py", "runtime.py", "records.py")},
              "cases": cases, "checks": checks, "passed": sum(row["passed"] for row in checks),
              "total": len(checks), "all_passed": all(row["passed"] for row in checks),
              "provider_requests": 0, "container_network": "none",
              "limitations": ["Local fixture state, not the deployed volume.",
                              "The older image is identified by its local reference and image identity."]}
    with options.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=1, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"all_passed": report["all_passed"], "passed": report["passed"], "total": report["total"]}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
