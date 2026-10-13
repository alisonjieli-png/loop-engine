"""Bounded native OpenCode qualification with local fixtures, never a model call.

Runs the actual installed binary under the customer cgroup/Bubblewrap profile.
The scripted model and service callbacks cannot access any provider or account.
Evidence identifies these as fixture responses, not task-solving model proof.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import tempfile
from unittest import mock

from loop_engine.core.harness_process import HarnessProcessRequest, HarnessProcessSpec, run_workspace_harness_process
from loop_engine.core.opencode_customer import CustomerFile, CustomerOperationBudget, EFFECTS, OpenCodeCustomerBoundary
from loop_engine.core.harness_customer_resources import CustomerResourceScope
from test_opencode_customer import fixture_catalog, response


BODY = b"def total(values):\n    return sum(int(value) for value in values)\n"
DIGEST = hashlib.sha256(BODY).hexdigest()
IDENTITY = "offline_sum_fixture"
CANARY = "harmless-per-unit-customer-canary"


def http_fixture(method, path, payload):
    if path == "/api/v1/capabilities":
        value = {"record_type": "service_capabilities/v1", "api_version": "v1",
            "retrieval": {"request_record_type": "service_retrieval_request/v2", "modes": ["lexical"], "returns_bodies": False},
            "library": {"provisioning_request_record_types": ["service_provisioning_request/v2"], "step_effects": sorted(EFFECTS)},
            "delivery": {"download_endpoint": "/api/v1/download", "package_files": "download_by_path",
                "body_format": "utf8_text", "download_bytes": 65536},
            "limits": {"request_bytes": 65536, "response_bytes": 65536, "search_results": 5}}
        operation = "capabilities"
    elif path == "/api/v1/retrieval":
        value = {"record_type": "service_retrieval_result/v1", "bodies_loaded": False, "hits": [{
            "reference": {"record_type": "provisioning_item_binding/v1", "identity": IDENTITY, "source_layer": "code_intelligence",
                "source_ref": "offline-native-fixture", "body_digest": DIGEST, "descriptor_digest": "a" * 64},
            "package": None, "kind": "code", "purpose": "Sum integer values in an offline qualification fixture.",
            "library_tier": "verified", "declared_effects": ["pure"], "effects_to_declare": [], "body_allowed": True}]}
        operation = "retrieval"
    elif path == "/api/v1/provisioning":
        if payload.get("identity") != IDENTITY or payload.get("expected_digest") != DIGEST:
            raise ValueError("fixture binding refused")
        value = {"record_type": "provisioning_manifest/v3", "identity": IDENTITY, "digest": DIGEST,
                 "size_bytes": len(BODY), "body_allowed": True, "library_tier": "verified", "declared_effects": ["pure"]}
        operation = "manifest"
    elif path == "/api/v1/download":
        if payload.get("identity") != IDENTITY or payload.get("expected_digest") != DIGEST:
            raise ValueError("fixture binding refused")
        return {"status": 200, "headers": {"Content-Type": "text/plain", "X-Loop-Engine-Record-Type": "service_download/v1",
                "X-Content-SHA256": DIGEST}, "body_base64": base64.b64encode(BODY).decode()}
    else:
        raise ValueError("no external transport exists")
    raw = json.dumps({"record_type": "service_http_result/v1", "operation": operation, "result": value}).encode()
    return {"status": 200, "headers": {"Content-Type": "application/json"}, "body_base64": base64.b64encode(raw).decode()}


def mcp_fixture(method, params):
    if method == "initialize":
        return {"result": {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                           "serverInfo": {"name": "offline-fixture", "version": "1"}}}
    if method == "notifications/initialized":
        return {"result": {}}
    if method == "tools/list":
        return {"result": {"tools": [{"name": name, "description": "Offline fixture only.",
                                      "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}}
                                     for name in ("intelligence_search", "provisioning_read")]}}
    if method == "tools/call" and params.get("name") == "intelligence_search":
        return {"result": {"content": [{"type": "text", "text": json.dumps({"identity": IDENTITY, "digest": DIGEST})}]}}
    raise ValueError("fixture MCP operation refused")


def tool_answer(index, name, arguments):
    return response(None, [{"id": "offline-call-" + str(index), "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)}}])


def run(binary, output):
    output.mkdir(mode=0o700)  # Exclusive creation preserves previous attempts.
    evidence = {"record_type": "opencode_customer_offline_qualification/v1", "model_calls": 0,
                "external_service_requests": 0, "provider_or_account_credentials": False,
                "scripted_fixture_model_ceiling": 10, "service_fixture_ceiling": 32, "operation_seconds": 90,
                "attempts": [], "assertions": [], "limits": ["Scripted responses establish mechanics, not model task-solving.",
                "Staging verifies arbitrary component bytes; this is not native skill installation.",
                "Selected output is an untrusted byte snapshot; the independent grader decides acceptance."]}
    source_root = Path(__file__).resolve().parents[1]
    paths = [source_root / "src/loop_engine/core" / name for name in
        ("harness_process.py", "harness_process_relay.py", "harness_customer_resources.py", "opencode_customer.py", "opencode_customer_recipe.py")]
    evidence["source_sha256"] = {str(path.relative_to(source_root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    def check(name, condition):
        evidence["assertions"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)
    try:
        spec = HarnessProcessSpec("opencode.customer_confined", "1.17.9", (str(binary),), (str(binary),),
                                  "opencode_customer", catalog=fixture_catalog())
        evidence["spec_digest"] = spec.digest
        budget = CustomerOperationBudget(10, 32, 90)
        script = """import json, os, pathlib, socket
p=pathlib.Path('/work')
needle=b'harmless-per-unit-customer-canary'
env_keys=[key for key,value in os.environ.items() if needle.decode() in value]
proc_matches=[]
for target in pathlib.Path('/proc').glob('[0-9]*/environ'):
    try:
        if needle in target.read_bytes(): proc_matches.append({'pid':target.parent.name,'comm':(target.parent/'comm').read_text().strip()})
    except OSError: pass
s=socket.socket(); s.settimeout(.2)
try:
    s.connect(('1.1.1.1',443)); network=True
except OSError: network=False
finally: s.close()
scope={}; exec((p/'stage/body').read_bytes(),scope)
(p/'result.json').write_text(json.dumps({'total':scope['total']([3,5,8]),'canary_leaked':bool(env_keys or proc_matches),'canary_environment_keys':env_keys,'canary_proc_matches':proc_matches,'outside_network':network}))
"""
        import shlex
        first_command = ("python3 /relay/opencode_customer_recipe.py search sum --limit 1 --output selection && "
            f"python3 /relay/opencode_customer_recipe.py fetch --identity {IDENTITY} --digest {DIGEST} "
            "--request-id offline-one --selection selection/selection.json --output stage && "
            "python3 -c " + shlex.quote(script))
        with tempfile.TemporaryDirectory(prefix="native-offline-", dir=output) as folder:
            prior = ()
            original_command = CustomerResourceScope.command
            def canary_command(scope, command, seconds):
                args = original_command(scope, command, seconds)
                args.insert(args.index("--"), "--setenv=BALTOR_UNIT_TEST_CANARY=" + CANARY)
                return args
            for phase in ("use", "revise", "recover"):
                count = 0
                def fixture_model(body):
                    nonlocal count
                    count += 1
                    if phase == "use" and count == 1:
                        return tool_answer(count, "baltor_intelligence_search", {"query": "sum"})
                    if count == (2 if phase == "use" else 1):
                        command = first_command if phase == "use" else "python3 -c " + shlex.quote(
                            "import pathlib,json; p=pathlib.Path('/work'); scope={}; exec((p/'stage/body').read_bytes(),scope); "
                            "(p/'result.json').write_text(json.dumps({'total':scope['total']([3,5,8,13])}))")
                        return tool_answer(count, "bash", {"command": command, "description": "Run the bounded offline fixture."})
                    return response("ready")
                boundary = OpenCodeCustomerBoundary(budget, mcp_fixture, EFFECTS, files=prior,
                    artifact_paths=("selection/selection.json", "stage/body", "stage/receipt.json", "result.json"), http=http_fixture)
                request = HarnessProcessRequest(spec, "Complete the offline fixture using the declared tools, then say ready.",
                    "fixture", 1024, 256, 25, folder, context_capacity=32768, socket_directory="/tmp")
                with mock.patch.object(CustomerResourceScope, "command", canary_command):
                    result = run_workspace_harness_process(request, fixture_model, boundary)
                evidence["attempts"].append({"phase": phase, "ok": result.ok, "errors": result.errors,
                    "exit_code": result.exit_code, "timed_out": result.timed_out, "elapsed_seconds": result.elapsed_seconds,
                    "process_identity": result.process_identity, "fixture_model_responses": count,
                    "resources": boundary.resources.verified, "cleanup_confirmed": boundary.resources.cleanup_confirmed,
                    "stdout": result.stdout, "stderr": result.stderr,
                    "exchanges": [{"request_digest": row.request_digest, "response_digest": row.response_digest,
                                   "broker_called": row.broker_called, "error_code": row.error_code,
                                   "refused_fixture_request": json.loads(row.request_json) if row.error_code else None}
                                  for row in result.exchanges]})
                check(phase + " native process completed", result.ok)
                check(phase + " resource cleanup confirmed", boundary.resources.cleanup_confirmed)
                files = {item.path: item.body for item in boundary.captured}
                check(phase + " exact staged bytes", files.get("stage/body") == BODY)
                receipt = json.loads(files["stage/receipt.json"])
                check(phase + " deterministic client receipt complete", receipt["complete"] and receipt["selected_digest"] == DIGEST)
                result_value = json.loads(files["result.json"])
                evidence["attempts"][-1]["fixture_result"] = result_value
                check(phase + " independent result", result_value["total"] == (16 if phase == "use" else 29))
                if phase == "use":
                    check("per-unit environment and proc canary absent", result_value["canary_leaked"] is False)
                    check("outside network unavailable", result_value["outside_network"] is False)
                prior = tuple(CustomerFile(path, body) for path, body in files.items())
        evidence["budget_attempts"] = budget.attempts
        evidence["passed"] = True
    except Exception as error:
        evidence["passed"] = False
        evidence["error"] = type(error).__name__ + ": " + str(error)
    finally:
        (output / "report.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"passed": evidence["passed"], "attempts": len(evidence["attempts"]),
                      "assertions": len(evidence["assertions"]), "report": str(output / "report.json")}))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    raise SystemExit(run(options.binary, options.output))
