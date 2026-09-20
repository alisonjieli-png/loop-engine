"""Verify the local service preparation through its actual domain entry point.

The example creates only temporary local records and a first-party instruction
body. It never calls a model, creates a cloud resource, or claims that a host
attestation is independent qualification.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json

from prepare import PreparationRequest, prepare
from loop_engine.core.service_runtime.http_entrypoint import configure_host, load_host_application
from loop_engine.core.service_runtime.records import TenantKeyIssue


def main():
    checks = []
    with TemporaryDirectory(prefix="loop-service-example-") as temporary:
        directory = Path(temporary) / "service"
        prepared = prepare(PreparationRequest(directory, allow_write=True, operator_access_seconds=3600))
        configuration = prepared["configuration"]
        installed = configure_host(configuration)
        application, _settings = load_host_application(configuration)
        issued = application.runtime.issue_key(TenantKeyIssue("demo", "local example check"))
        listing = application.provisioning.invoke(issued.key, "list")
        body = application.provisioning.invoke(issued.key, "read", identity="example.review_inputs", request_id="example-once")
        checks.append(installed["tenants"] == ["demo"] and len(listing["items"]) == 1)
        checks.append(hashlib.sha256(body["body"].encode()).hexdigest() == body["digest"])
        application.runtime.set_grants("demo", ())
        restarted, _settings = load_host_application(configuration)
        checks.append(not restarted.provisioning.invoke(issued.key, "list")["items"])
        try:
            prepare(PreparationRequest(directory, allow_write=True))
            checks.append(False)
        except ValueError:
            checks.append(True)
    result = {"record_type": "service_example_checks/v1", "passed": sum(checks), "total": len(checks),
              "all_passed": all(checks), "external_provider_calls": 0, "provider_qualified": False}
    print(json.dumps(result))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
