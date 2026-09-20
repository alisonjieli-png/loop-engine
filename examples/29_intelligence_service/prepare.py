"""Prepare an explicit local service example without credentials or network.

This example owns only a newly created directory selected by the operator.
It uses canonical catalogue references and the existing host configuration.
The example review is host-attested, not independent qualification or payment.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import time

from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
from loop_engine.core.provisioning_server import METERING_POLICIES
from loop_engine.core.service_runtime.http import ServiceHttpConfiguration
from loop_engine.core.service_runtime.http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION

BODY = """# Review supplied material

Name the supplied source and its exact revision. Separate observations from
assumptions. If material is missing or contradictory, retain that uncertainty
and request the specific missing evidence. Check the task's output contract
before treating a candidate as complete. These instructions grant no effects.
"""


@dataclass(frozen=True)
class PreparationRequest:
    directory: Path
    public_origin: str = "http://127.0.0.1:8000"
    allow_write: bool = False
    operator_access_seconds: int = 0


def prepare(request):
    if not isinstance(request, PreparationRequest) or request.allow_write is not True:
        raise ValueError("explicit preparation write authority is required")
    root = request.directory
    if (not isinstance(root, Path) or not root.is_absolute() or root.resolve() != root
            or root.exists() or not root.parent.is_dir()):
        raise ValueError("choose one new absolute directory beneath an existing non-symbolic-link parent")
    if type(request.operator_access_seconds) is not int or not 0 <= request.operator_access_seconds <= 86400:
        raise ValueError("example operator access is between zero and one day")
    from urllib.parse import urlsplit
    http = ServiceHttpConfiguration(request.public_origin, (urlsplit(request.public_origin).netloc,),
                                    allow_loopback_http=True)
    item = item_from_body(HarnessIntelligenceDraft("example.review_inputs", "instruction_file",
        "Review supplied material and preserve missing evidence", "context_intelligence",
        "example:review-inputs@1", "MIT"), BODY)
    root.mkdir()
    artifacts = root / "artifacts"
    artifacts.mkdir()
    (root / "state").mkdir()
    (artifacts / "review-inputs.md").write_text(BODY, encoding="utf-8")
    manifest = {"record_type": MANIFEST_VERSION, "artifact_root": str(artifacts), "items": [{
        "reference": item.reference(), "body_path": "review-inputs.md",
        "approval_ref": "example_host_attestation:not_independent_qualification",
        "grants": [{"tenant_id": "demo", "body_allowed": True, "metering": METERING_POLICIES[0]}]}]}
    tenant = {"tenant_id": "demo", "namespace": "demo:private"}
    if request.operator_access_seconds:
        tenant["operator_entitlement"] = {"valid_until": int(time.time()) + request.operator_access_seconds,
                                           "evidence_ref": "operator_authorized_local_example_not_payment"}
    from dataclasses import asdict
    configuration = {"record_type": HOST_CONFIGURATION_VERSION,
        "runtime": {"database_path": str(root / "state" / "service.db"), "writes_authorized": True},
        "http": asdict(http), "authentication": {"modes": ["host_key"]},
        "manifest_path": str(root / "manifest.json"), "tenants": [tenant]}
    for name, value in (("manifest.json", manifest), ("host.json", configuration)):
        with (root / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
    return {"record_type": "service_example_preparation/v1", "configuration": str(root / "host.json"),
            "example_review": "host_attested", "remote_accounts_created": False,
            "credentials_created": False, "operator_body_access_seconds": request.operator_access_seconds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--public-origin", default="http://127.0.0.1:8000")
    parser.add_argument("--allow-write", action="store_true")
    parser.add_argument("--operator-access-seconds", type=int, default=0)
    args = parser.parse_args()
    result = prepare(PreparationRequest(args.directory, args.public_origin, args.allow_write, args.operator_access_seconds))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
