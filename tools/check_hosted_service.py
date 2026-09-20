"""Qualify a declared private diagnostic catalogue over real HTTPS and MCP.

Credentials resolve from this workstation's system keyring and never appear in
the report. This is a transport and disclosure check, not a customer task or
paid-release benchmark. One selected body read records service usage.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("redirect_refused")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--isolated-account", required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--authorize-metered-read", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    origin = urllib.parse.urlsplit(args.origin)
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.path not in ("", "/") or origin.query or origin.fragment
            or not args.authorize_metered_read or args.output.exists()):
        parser.error("HTTPS origin, one explicit read approval and a new report path are required")
    import secretstorage
    collection = secretstorage.get_default_collection(secretstorage.dbus_init())
    def credential(account):
        items = list(collection.search_items({"application": "loop-engine", "service": origin.hostname,
                                              "account": account, "purpose": "service-access"}))
        if len(items) != 1:
            raise RuntimeError("named_credential_unavailable")
        return items[0].get_secret().decode()
    owner, isolated = credential(args.account), credential(args.isolated_account)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())
    calls = 0
    def request(path, key=None, body=None, headers=None):
        nonlocal calls
        fields = {"Accept": "application/json", **(headers or {})}
        if key:
            fields["Authorization"] = "Bearer " + key
        if body is not None:
            fields["Content-Type"] = "application/json"
        selected = urllib.request.Request(args.origin.rstrip("/") + path,
            None if body is None else json.dumps(body).encode(), fields)
        calls += 1
        try:
            response = opener.open(selected, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(2_000_000)
            return response.status, json.loads(data)

    checks = []
    request_id = None
    usage_before = None
    usage_after = None
    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})
    def provision(operation="list", **fields):
        return {"record_type": "service_provisioning_request/v1", "operation": operation, **fields}
    try:
        status, health = request("/api/v1/health")
        check("public_health_responds", status == 200 and health["result"]["healthy"] is True)
        status, _ = request("/api/v1/session")
        check("missing_key_refuses", status == 401)
        status, _ = request("/api/v1/session", "invalid-diagnostic-credential")
        check("wrong_key_refuses", status == 401)
        status, identity = request("/api/v1/session", owner)
        check("owner_identity_is_server_bound", status == 200 and identity["result"]["principal"]["tenant_id"] == args.account)
        status, listing = request("/api/v1/provisioning", owner, provision())
        check("owner_can_list_selected_identity", status == 200 and any(row["identity"] == args.identity for row in listing["result"]["items"]))
        status, listing = request("/api/v1/provisioning", isolated, provision())
        check("isolated_tenant_has_no_owner_grants", status == 200 and listing["result"]["items"] == [])
        status, search = request("/api/v1/retrieval", owner, {"record_type": "service_retrieval_request/v1",
                                "query": args.query, "mode": "lexical", "top_n": 3})
        check("search_returns_references_without_loading_bodies", status == 200 and search["result"]["hits"]
              and search["result"]["bodies_loaded"] is False)
        _, before = request("/api/v1/usage", owner)
        usage_before = before["result"]["records"]
        request_id = "hosted-check-" + uuid.uuid4().hex
        body_request = provision("read", identity=args.identity, expected_digest=args.digest, request_id=request_id)
        status, first = request("/api/v1/provisioning", owner, body_request)
        check("selected_body_has_the_expected_digest", status == 200
              and hashlib.sha256(first["result"]["body"].encode()).hexdigest() == args.digest)
        status, repeated = request("/api/v1/provisioning", owner, body_request)
        check("exact_retry_retains_one_durable_acknowledgment", status == 200
              and first["result"]["metering_acknowledgment"] == repeated["result"]["metering_acknowledgment"]
              and first["result"]["metering_acknowledgment"]["durability"] == "durable")
        _, after = request("/api/v1/usage", owner)
        usage_after = after["result"]["records"]
        check("two_read_requests_add_one_usage_record", after["result"]["records"] == before["result"]["records"] + 1)
        status, _ = request("/api/v1/provisioning", isolated, provision("read", identity=args.identity,
                                                                        request_id="isolated-" + request_id))
        check("another_tenant_cannot_read_the_body", status in (403, 404))
        status, stale = request("/api/v1/provisioning", owner, provision("read", identity=args.identity,
            expected_digest="0" * 64, request_id="stale-" + request_id))
        check("changed_digest_refuses", status == 404 and stale.get("error", {}).get("code") == "item_unavailable"
              and "body" not in stale and "result" not in stale)
        _, after_refusals = request("/api/v1/usage", owner)
        check("refused_reads_do_not_add_usage", after_refusals["result"]["records"] == after["result"]["records"])
        status, _ = request("/api/v1/session", owner, headers={"Origin": "https://untrusted.invalid"})
        check("unexpected_browser_origin_refuses", status == 403)
        # The official SDK runs in the project environment. The credential crosses
        # only an anonymous pipe, not command arguments, a file or tool output.
        code = '''
import asyncio,json,sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
settings=json.load(sys.stdin)
async def run():
    async with streamablehttp_client(settings['origin']+'/mcp',headers={'Authorization':'Bearer '+settings['key']}) as streams:
        async with ClientSession(streams[0],streams[1]) as session:
            init=await session.initialize()
            tools=await session.list_tools()
            search=await session.call_tool('intelligence_search',{'query':settings['query']})
            print(json.dumps({'protocol':init.protocolVersion,'tool_count':len(tools.tools),
                'search_ok':not search.isError and bool(search.structuredContent['result']['hits']),
                'bodies_loaded':search.structuredContent['result']['bodies_loaded']}))
asyncio.run(run())
'''
        executable = Path(__file__).resolve().parents[1] / ".venv/bin/python"
        outcome = subprocess.run([str(executable), "-c", code], input=json.dumps({
            "origin": args.origin.rstrip("/"), "key": owner, "query": args.query}),
            capture_output=True, text=True, timeout=60, env={"PATH": os.environ["PATH"]})
        protocol = json.loads(outcome.stdout) if outcome.returncode == 0 else {}
        check("official_MCP_client_initializes_over_real_HTTPS", outcome.returncode == 0
              and protocol.get("protocol") == "2025-11-25" and protocol.get("tool_count") == 5)
        check("MCP_search_returns_permitted_references", protocol.get("search_ok") is True
              and protocol.get("bodies_loaded") is False)
    except Exception as error:
        checks.append({"name": "remaining_checks_interrupted", "passed": False, "error_type": type(error).__name__})
    report = {"record_type": "hosted_service_transport_qualification/v1",
        "checked_at": datetime.now(timezone.utc).isoformat(), "origin": args.origin,
        "accounts": [args.account, args.isolated_account], "identity": args.identity, "digest": args.digest,
        "metered_read_request_id": request_id, "usage_records_before": usage_before,
        "usage_records_after": usage_after, "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "checks": checks, "passed": sum(row["passed"] for row in checks), "executed": len(checks),
        "planned_checks": 16, "all_passed": len(checks) == 16 and all(row["passed"] for row in checks),
        "http_calls": calls, "physical_model_calls": 0, "hosted_harness_used": False,
        "supabase_qualified": False, "stripe_runtime_qualified": False, "paid_release_qualified": False,
        "limits": "Private host-attested diagnostic material only; not a full-system customer-task benchmark."}
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ("passed", "executed", "planned_checks", "all_passed", "origin")}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
