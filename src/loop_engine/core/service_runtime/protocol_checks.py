"""Protocol endpoint checks for the hosted service, in both protocol eras.

These checks drive the official protocol client over real Streamable HTTP
against a loopback service built from durable domain records: the
2025-11-25 handshake era and the 2026-07-28 per-request era, version
negotiation and refusal, and the versions a host configuration serves. No
remote provider is called. They moved out of http_checks.py on September 22,
2026, when the second era took that module past the size cap; the protocol
edge now has its own check module, and http_checks.self_test runs it.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch

from .http_checks import provisioning_request
from .http_test_fixtures import HttpDomainFixture, running_http


#: The per-request protocol version these checks qualify.
_PER_REQUEST = "2026-07-28"


@asynccontextmanager
async def _protocol_client(base, fixture, mode, tenant="alpha"):
    """The official protocol client over real Streamable HTTP, carrying one fixture key.

    `mode` is the client's own choice: "legacy" for the initialize handshake,
    "auto" to probe discovery and fall back, or a per-request version.
    """
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    async with httpx2.AsyncClient(headers=fixture.headers(tenant), trust_env=False, timeout=10) as http:
        async with Client(streamable_http_client(base + "/mcp", http_client=http), mode=mode) as client:
            yield client


def _protocol_message(answer):
    """The one protocol message in an answer sent as JSON or as one event stream, or None."""
    if answer.headers.get("content-type", "").startswith("text/event-stream"):
        data = [line[5:].strip() for line in answer.text.splitlines() if line.startswith("data:")]
        return json.loads(data[-1]) if data else None
    try:
        return answer.json()
    except ValueError:
        return None


async def _protocol_checks(check, root):
    """The official client in each kind of protocol version, over real sockets, on one shared domain.

    The handshake checks keep the names they had when 2025-11-25 was the only
    version served. The same domain guarantees are checked again at 2026-07-28,
    where a client names its version on every request instead.
    """
    import httpx
    fixture = HttpDomainFixture(root)
    # The completion guard check revokes every grant; each era starts from these.
    grants, _guard = fixture.runtime.grant_snapshot(fixture.runtime.authenticate_key(fixture.keys["alpha"].key))
    with running_http(fixture) as (base, service):
        eras = (("legacy", "2025-11-25", {
                     "profile": "official_client_uses_real_StreamableHTTP_with_the_exact_supported_profile",
                     "search": "protocol_search_returns_typed_authorized_references_without_bodies",
                     "shared": "HTTP_and_protocol_share_the_same_domain_and_idempotent_usage_identity",
                     "refusals": "protocol_refusals_hide_cross_tenant_items_and_reject_authority_injection",
                     "completion": "protocol_search_shares_the_completion_authorization_guard",
                     "reference": "a_protocol_tool_refusal_carries_a_reference_the_operator_finds"}),
                (_PER_REQUEST, _PER_REQUEST, {
                     "profile": "official_client_uses_the_per_request_version_without_a_handshake",
                     "search": "per_request_search_returns_typed_authorized_references_without_bodies",
                     "shared": "per_request_protocol_shares_the_same_domain_and_idempotent_usage_identity",
                     "refusals": "per_request_refusals_hide_cross_tenant_items_and_reject_authority_injection",
                     "completion": "per_request_search_shares_the_completion_authorization_guard",
                     "reference": "a_per_request_tool_refusal_carries_a_reference_the_operator_finds"}))
        for mode, expected, names in eras:
            fixture.runtime.set_grants("alpha", grants)
            records = fixture.usage()["records"]
            async with _protocol_client(base, fixture, mode) as client:
                tools = await client.list_tools()
                check(names["profile"], client.protocol_version == expected and len(tools.tools) == 5)
                found = await client.call_tool("intelligence_search", {"query": "alpha"})
                check(names["search"],
                      not found.is_error and found.structured_content["result"]["hits"]
                      and found.structured_content["result"]["bodies_loaded"] is False
                      and "skill.beta" not in str(found.structured_content))
                request_id = "cross-transport-" + expected
                first = await client.call_tool("provisioning_read", {"identity": "skill.alpha", "request_id": request_id})
                async with httpx.AsyncClient(trust_env=False) as direct:
                    repeat = await direct.post(base + "/api/v1/provisioning", headers=fixture.headers(),
                        json=provisioning_request("read", identity="skill.alpha", request_id=request_id))
                check(names["shared"],
                      not first.is_error and first.structured_content["result"]["metering_acknowledgment"]
                      == repeat.json()["result"]["metering_acknowledgment"]
                      and fixture.usage()["records"] == records + 1)
                refused = await client.call_tool("provisioning_read", {"identity": "skill.beta", "request_id": "private"})
                injected = await client.call_tool("provisioning_list", {"tenant_id": "beta"})
                check(names["refusals"],
                      refused.is_error and injected.is_error and "PRIVATE_BETA_BODY" not in str(refused)
                      and fixture.usage()["records"] == records + 1)
                # A refusal of a protocol tool is a refused request too. The
                # harness that made it reads the same kind of reference a web
                # refusal carries, and the operator finds it under the protocol
                # address with the account that made the call.
                from .observability import valid_reference
                named = refused.structured_content.get("request_reference")
                logged = service.failure_journal.detail(named)["failures"] if valid_reference(named) else []
                check(names["reference"],
                      valid_reference(named) and len(logged) == 1 and logged[0]["route"] == "/mcp"
                      and logged[0]["method"] == "POST" and logged[0]["tenant_id"] == "alpha"
                      and logged[0]["refusal_code"] == refused.structured_content["error"]["code"])
                from .catalogue_search import ReleaseSearchIndex
                original = ReleaseSearchIndex.rank
                def revoke_after_ranking(index, *args, **kwargs):
                    result = original(index, *args, **kwargs)
                    fixture.runtime.set_grants("alpha", ())
                    return result
                with patch.object(ReleaseSearchIndex, "rank", revoke_after_ranking):
                    revoked = await client.call_tool("intelligence_search", {"query": "Alpha"})
                check(names["completion"],
                      revoked.is_error and revoked.structured_content["error"]["code"] == "disclosure_grant_changed"
                      and "skill.alpha" not in str(revoked))
        # A client that asks the service which kind of version it serves is
        # given the per-request version, and a tool list at that version tells
        # it how long it may reuse the list and that no one else may.
        fixture.runtime.set_grants("alpha", grants)
        async with _protocol_client(base, fixture, "auto") as client:
            tools = await client.list_tools()
            check("an_automatic_client_selects_the_per_request_version_through_discovery",
                  client.protocol_version == _PER_REQUEST and len(tools.tools) == 5)
            from .http import PROTOCOL_CACHE_SCOPE, PROTOCOL_CACHE_TTL_MS
            check("per_request_tool_list_carries_private_cache_hints",
                  tools.ttl_ms == PROTOCOL_CACHE_TTL_MS and tools.cache_scope == PROTOCOL_CACHE_SCOPE == "private")


async def _negotiation_checks(check, root):
    """Protocol version selection over real sockets, on a fixture no other check has changed."""
    import httpx
    fixture = HttpDomainFixture(root)
    with running_http(fixture) as (base, _service):
        async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
            async def rpc(method, params, version=None, identity=1, headers=(), http_method="POST"):
                sent = [*fixture.headers().items(), ("Accept", "application/json, text/event-stream"),
                        *((("MCP-Protocol-Version", version),) if version else ()), *headers]
                answer = await client.request(http_method, base + "/mcp", headers=sent, json={
                    "jsonrpc": "2.0", "id": identity, "method": method, "params": params})
                return answer, _protocol_message(answer)
            def per_request(method, params=None, version=_PER_REQUEST):
                """A request in the per-request form: its version in the header and in the message."""
                return {**(params or {}), "_meta": {"io.modelcontextprotocol/protocolVersion": version,
                                                   "io.modelcontextprotocol/clientCapabilities": {}}}
            def error_of(message):
                return (message or {}).get("error") or {}
            # The 2025-11-25 lifecycle: when the server does not support the
            # version a client asks for in initialize, it MUST answer with
            # another version it supports, and the client decides whether to
            # disconnect. This endpoint refused such a request with 400 until
            # September 22, 2026, which broke every client that asks for a
            # newer version first. A version the protocol library knows but
            # this release has not qualified is answered the same way, so
            # handing the choice to the library, which would accept 2025-06-18,
            # fails this check too.
            offered = {}
            for requested in ("2099-01-01", "2026-07-28", "2025-06-18"):
                answer, message = await rpc("initialize", {"protocolVersion": requested, "capabilities": {},
                                                           "clientInfo": {"name": "negotiation", "version": "1"}})
                offered[requested] = (answer.status_code, ((message or {}).get("result") or {}).get("protocolVersion"))
            check("initialize_for_an_unsupported_version_is_answered_with_a_supported_version",
                  offered == {requested: (200, "2025-11-25") for requested in offered})
            # An initialize selects the handshake even when it carries the
            # per-request version in its header, which is what the 2026-07-28
            # revision requires of a server that serves both kinds.
            answer, message = await rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                                       "clientInfo": {"name": "negotiation", "version": "1"}}, _PER_REQUEST)
            check("an_initialize_selects_the_handshake_whatever_version_header_it_carries",
                  answer.status_code == 200 and ((message or {}).get("result") or {}).get("protocolVersion") == "2025-11-25")
            # Negotiation is not permission to serve the unsupported version:
            # every later request names the negotiated version and is refused
            # before any domain work when it names another one or none.
            reads, records = len(fixture.reads), fixture.usage()["records"]
            refused = [await rpc("tools/call", {"name": "provisioning_read", "arguments": {
                           "identity": "skill.alpha", "request_id": "negotiation-refused"}}, version, identity=2)
                       for version in ("2099-01-01", "2025-06-18", None)]
            check("a_request_naming_an_unsupported_version_is_refused_before_any_effect",
                  [answer.status_code for answer, _message in refused] == [400, 400, 400]
                  and len(fixture.reads) == reads and fixture.usage()["records"] == records)
            # The refusal is the one the 2026-07-28 revision defines: -32022
            # with every version this service serves, newest first, so that a
            # client can choose one and retry. The protocol library's own
            # refusal lists only the per-request versions it speaks.
            unknown, unknown_message = await rpc("tools/list", per_request("tools/list", version="2099-01-01"),
                                                 "2099-01-01", identity=5, headers=(("Mcp-Method", "tools/list"),))
            check("an_unserved_version_is_answered_with_every_served_version_newest_first",
                  unknown.status_code == 400 and error_of(unknown_message).get("code") == -32022
                  and error_of(unknown_message).get("data") == {"supported": ["2026-07-28", "2025-11-25"],
                                                                 "requested": "2099-01-01"}
                  and unknown_message.get("id") == 5
                  and [error_of(message).get("code") for _answer, message in refused] == [-32022, -32022, -32020])
            # A header that is missing, repeated or not a version at all is a
            # header fault, and a value that is not a version is not repeated.
            repeated, repeated_message = await rpc("tools/list", {}, "2025-11-25", identity=6,
                                                   headers=(("MCP-Protocol-Version", _PER_REQUEST),))
            malformed, malformed_message = await rpc("tools/list", {}, "2025-11-25 PROBE", identity=7)
            check("a_missing_repeated_or_malformed_version_header_is_a_header_fault",
                  repeated.status_code == malformed.status_code == 400
                  and error_of(repeated_message).get("code") == error_of(malformed_message).get("code") == -32020
                  and "PROBE" not in malformed.text)
            # One POST endpoint in both kinds: no stream to open, no session to end.
            opened, _ = await rpc("tools/list", {}, "2025-11-25", identity=8, http_method="GET")
            ended, _ = await rpc("tools/list", {}, _PER_REQUEST, identity=9, http_method="DELETE")
            check("the_protocol_endpoint_answers_only_POST",
                  opened.status_code == ended.status_code == 405
                  and opened.headers.get("allow") == ended.headers.get("allow") == "POST")
            check("no_refused_protocol_request_reached_the_domain",
                  len(fixture.reads) == reads and fixture.usage()["records"] == records)
            # Discovery answers at the per-request version with every served
            # version, newest first, and says how long and for whom it may be kept.
            found, discovery = await rpc("server/discover", per_request("server/discover"), _PER_REQUEST,
                                         identity=10, headers=(("Mcp-Method", "server/discover"),))
            result = (discovery or {}).get("result") or {}
            check("discovery_lists_every_served_version_newest_first",
                  found.status_code == 200 and result.get("supportedVersions") == ["2026-07-28", "2025-11-25"]
                  and result.get("resultType") == "complete" and result.get("cacheScope") == "private"
                  and result.get("ttlMs") == 300_000 and "tools" in result.get("capabilities", {}))
            # The guards above must not be satisfiable by refusing everything:
            # the negotiated version still lists and calls tools end to end.
            listed_answer, listed = await rpc("tools/list", {}, "2025-11-25", identity=3)
            called_answer, called = await rpc("tools/call", {"name": "intelligence_search",
                                                             "arguments": {"query": "alpha"}}, "2025-11-25", identity=4)
            check("the_negotiated_version_still_lists_and_calls_tools_end_to_end",
                  listed_answer.status_code == called_answer.status_code == 200
                  and len(((listed or {}).get("result") or {}).get("tools", ())) == 5
                  and ((called or {}).get("result") or {}).get("isError") is False
                  and bool(called["result"]["structuredContent"]["result"]["hits"]))


async def _configured_version_checks(check, root):
    """A host that serves fewer versions, the host record that says so, and the library it needs."""
    import httpx
    import mcp.types.version as library_versions
    from .http import HTTP_CONFIGURATION_RECORD_TYPE, ServiceHttpConfiguration
    origin, hosts = "http://127.0.0.1:8000", ("127.0.0.1:8000",)
    def refuses(**fields):
        try:
            ServiceHttpConfiguration(origin, hosts, allow_loopback_http=True, **fields)
        except (TypeError, ValueError):
            return True
        return False
    # Version 1 pinned one version. Reading it as "serve both" would widen
    # what a host file meant, so it is refused rather than read.
    check("the_http_record_refuses_version_one_and_versions_this_release_has_not_qualified",
          HTTP_CONFIGURATION_RECORD_TYPE == "service_http_configuration/v2"
          and refuses(record_type="service_http_configuration/v1") and refuses(protocol_version="2025-11-25")
          and refuses(protocol_versions=()) and refuses(protocol_versions=("2025-06-18",))
          and refuses(protocol_versions=("2025-11-25", "2025-11-25")) and refuses(protocol_versions="2025-11-25")
          and ServiceHttpConfiguration(origin, hosts, allow_loopback_http=True,
                                       protocol_versions=["2026-07-28", "2025-11-25"]).protocol_versions
          == ("2025-11-25", "2026-07-28"))
    for served in (("2025-11-25",), (_PER_REQUEST,)):
        folder = root / served[0]
        folder.mkdir()
        fixture = HttpDomainFixture(folder)
        with running_http(fixture, protocol_versions=served) as (base, service):
            async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
                protocol = (await client.get(base + "/api/v1/capabilities")).json()["result"]["protocol"]
                headers = {**fixture.headers(), "Accept": "application/json, text/event-stream"}
                if served == ("2025-11-25",):
                    refused = await client.post(base + "/mcp", headers={
                        **headers, "MCP-Protocol-Version": _PER_REQUEST, "Mcp-Method": "tools/list"}, json={
                        "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": {
                            "io.modelcontextprotocol/protocolVersion": _PER_REQUEST,
                            "io.modelcontextprotocol/clientCapabilities": {}}}})
                    async with _protocol_client(base, fixture, "auto") as automatic:
                        listed = await automatic.list_tools()
                        chosen = automatic.protocol_version
                    check("a_host_serving_only_the_handshake_refuses_the_per_request_version_and_clients_fall_back",
                          protocol["versions"] == ["2025-11-25"] and protocol["per_request_versions"] == []
                          and refused.status_code == 400 and refused.json()["error"]["code"] == -32022
                          and refused.json()["error"]["data"]["supported"] == ["2025-11-25"]
                          and chosen == "2025-11-25" and len(listed.tools) == 5)
                else:
                    refused = await client.post(base + "/mcp", headers=headers, json={
                        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                            "protocolVersion": "2025-11-25", "capabilities": {},
                            "clientInfo": {"name": "per-request-only", "version": "1"}}})
                    async with _protocol_client(base, fixture, "auto") as automatic:
                        listed = await automatic.list_tools()
                        chosen = automatic.protocol_version
                    check("a_host_serving_only_the_per_request_version_names_it_when_it_refuses_an_initialize",
                          protocol["versions"] == [_PER_REQUEST] and protocol["handshake_versions"] == []
                          and refused.status_code == 400 and refused.json()["error"]["code"] == -32022
                          and refused.json()["error"]["data"] == {"supported": [_PER_REQUEST], "requested": "2025-11-25"}
                          and chosen == _PER_REQUEST and len(listed.tools) == 5)
            if served == (_PER_REQUEST,):
                # The binding is validated where it is used: a protocol
                # library that cannot serve a configured version refuses the
                # application instead of answering at another version.
                with patch.object(library_versions, "MODERN_PROTOCOL_VERSIONS", ()):
                    try:
                        service._sdk_server()
                        library_refused = False
                    except ValueError:
                        library_refused = True
                check("an_installed_library_that_cannot_serve_a_configured_version_refuses_the_application",
                      library_refused)
                check("protocol_messages_record_no_trace_spans_without_a_telemetry_setting",
                      service._sdk_server().middleware == [])


async def _cancellation_checks(check, root):
    """A cancelled read in each kind of version: never replayed, never charged twice."""
    for mode, name in (("legacy", "real_protocol_cancellation_does_not_replay_or_duplicate_uncertain_metering"),
                       (_PER_REQUEST, "per_request_cancellation_does_not_replay_or_duplicate_uncertain_metering")):
        folder = root / mode
        folder.mkdir()
        fixture = HttpDomainFixture(folder)
        entered, release = threading.Event(), threading.Event()
        def wait(_item, entered=entered, release=release):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("bounded fixture release did not arrive")
        fixture.before_read = wait
        with running_http(fixture, request_timeout_seconds=2) as (base, _service):
            try:
                async with _protocol_client(base, fixture, mode) as client:
                    pending = asyncio.create_task(client.call_tool("provisioning_read",
                        {"identity": "skill.alpha", "request_id": "cancelled-once"}))
                    deadline = time.monotonic() + 1
                    while not entered.is_set() and time.monotonic() < deadline:
                        await asyncio.sleep(0.005)
                    pending.cancel()
                    cancelled = False
                    try:
                        await pending
                    except asyncio.CancelledError:
                        cancelled = True
                    release.set()
                    deadline = time.monotonic() + 1
                    while fixture.usage()["records"] == 0 and time.monotonic() < deadline:
                        await asyncio.sleep(0.005)
                    reads_before_retry = len(fixture.reads)
                    fixture.before_read = None
                    repeated = await client.call_tool("provisioning_read",
                        {"identity": "skill.alpha", "request_id": "cancelled-once"})
                    check(name, cancelled and entered.is_set() and reads_before_retry == 1
                          and len(fixture.reads) == 2 and not repeated.is_error
                          and fixture.usage()["records"] == 1)
            finally:
                release.set()


def run_checks(check):
    """Run every protocol check group, each in its own temporary folder."""
    for name, function in (("protocol", _protocol_checks), ("negotiation", _negotiation_checks),
                           ("configured_versions", _configured_version_checks),
                           ("cancellation", _cancellation_checks)):
        with tempfile.TemporaryDirectory(prefix="service-http-" + name + "-") as directory:
            asyncio.run(function(check, Path(directory)))
