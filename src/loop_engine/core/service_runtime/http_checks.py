"""Real loopback acceptance for the hosted service transports.

These checks use durable domain records, actual HTTP sockets, official protocol
client streams and locally signed identity tokens. No remote provider is called
and no local fixture is represented as live Supabase or payment qualification.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch

from .http import PROMOTION_REDEMPTION_PATH, PROVISIONING_REQUEST_VERSION, RETRIEVAL_REQUEST_VERSION
from .http_auth import ServiceHttpAuthentication
from .http_test_fixtures import HttpDomainFixture, running_http, running_key_set
from .records import SubjectBindingRequest


#: The per-request protocol version these checks qualify.
_PER_REQUEST = "2026-07-28"


def provisioning_request(operation="list", **fields):
    return {"record_type": PROVISIONING_REQUEST_VERSION, "operation": operation, **fields}


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


def _web_checks(check, root):
    import httpx
    fixture = HttpDomainFixture(root)
    with running_http(fixture, maximum_inline_body_bytes=128, maximum_response_bytes=8192) as (base, _service):
        with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False, timeout=3) as client:
            public = httpx.get(base + "/app", trust_env=False)
            script = httpx.get(base + "/assets/service.js", trust_env=False)
            check("packaged_public_workspace_loads_without_exposing_private_source",
                  public.status_code == script.status_code == 200
                  and "Intelligence workspace" in public.text
                  and "frame-ancestors 'none'" in public.headers["content-security-policy"]
                  and public.headers["referrer-policy"] == "no-referrer"
                  and "localStorage" not in script.text
                  and httpx.get(base + "/assets/../http_entrypoint.py", trust_env=False).status_code != 200)
            # A page that points at an address the server does not serve sends
            # the reader to a refusal. Every internal address in the page must
            # resolve to a served address or to an interface path.
            #
            # Both attributes are read, not only href. A script or an image the
            # service does not serve is worse than a broken link, because the
            # request falls through to the interface router and comes back as a
            # refusal rather than a missing file, so the page loads and then
            # quietly does nothing. This check scanned href alone until
            # September 21, 2026, and a page shipped with a script tag pointing
            # at an address that answered 401.
            from importlib.resources import files
            import re as _re
            page = files("loop_engine").joinpath("core", "service_runtime", "web_assets", "index.html").read_text("utf-8")
            from .web_pages import WEB_ASSETS
            linked = {value for value in _re.findall(r'(?:href|src)="(/[^"#?]*)"', page)}
            unserved = sorted(value for value in linked
                              if value not in WEB_ASSETS and not value.startswith("/api/")
                              and not value.startswith("/.well-known/") and value != "/mcp")
            check("every_internal_address_on_the_page_is_served", not unserved)
            # The addresses are read from the page; a page that names none
            # would pass the check above without proving anything.
            check("the_page_names_internal_addresses_of_both_kinds",
                  len(linked) >= 2
                  and any(_re.findall(r'src="(/[^"#?]*)"', page))
                  and any(_re.findall(r'href="(/[^"#?]*)"', page)))
            # An address the service does not serve is a missing page, not a
            # credential problem. The router authenticated first until
            # September 21, 2026, so every unknown address answered 401
            # unauthorized: a mistyped address, a stale bookmark and a client
            # calling the wrong path all sent the reader looking for a
            # credential fault that did not exist.
            unknown_page = httpx.get(base + "/no-such-page", trust_env=False)
            unknown_api = httpx.post(base + "/api/v1/no-such-route", json={}, trust_env=False)
            wrong_method = httpx.get(base + "/api/v1/retrieval", trust_env=False)
            check("an_address_the_service_does_not_serve_answers_missing_not_unauthorized",
                  unknown_page.status_code == unknown_api.status_code == wrong_method.status_code == 404
                  and unknown_api.json()["error"]["code"] == "route_unavailable"
                  and "www-authenticate" not in unknown_page.headers)
            # A reader who arrives in a browser needs a sentence and a way
            # back, not a record shape.
            browser = httpx.get(base + "/no-such-page", trust_env=False,
                                headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
            check("a_missing_address_tells_a_reader_what_happened_and_where_to_go",
                  browser.status_code == 404
                  and browser.headers["content-type"].startswith("text/html")
                  and 'href="/"' in browser.text and 'href="/docs"' in browser.text
                  and "route_unavailable" not in browser.text
                  and "frame-ancestors 'none'" in browser.headers["content-security-policy"])
            # The guard above must not be satisfiable by answering 404
            # everywhere: an address the service does serve still asks who is
            # calling, and a public page still loads.
            check("an_address_the_service_serves_still_asks_who_is_calling",
                  httpx.get(base + "/api/v1/session", trust_env=False).status_code == 401
                  and httpx.get(base + "/app", trust_env=False).status_code == 200)
            # The table consulted before authentication and the branches that
            # answer must name the same addresses. A route added to one and
            # not the other is either unreachable or unauthenticated, and
            # neither shows up in any other check.
            import inspect as _inspect
            from . import http as _http
            source = _inspect.getsource(_http.ServiceHttpApplication._web_route)
            answered = set(_re.findall(r'path == "(/[^"]+)"', source))
            for group in _re.findall(r'path in \(([^)]*)\)', source):
                answered.update(_re.findall(r'"(/[^"]+)"', group))
            for name, value in vars(_http).items():
                if isinstance(value, str) and value.startswith("/api/") and name in source:
                    answered.add(value)
            check("the_route_table_names_every_address_the_router_answers",
                  len(answered) >= 10 and answered == set(_http.API_ROUTES))
            # The check above compares two lists in one file. This one asks the
            # running service, because the two can only disagree in a way a
            # customer feels. Between the route table landing ahead of
            # authentication on September 21, 2026 and this check, sign-up,
            # password recovery and promotion redemption were answered by
            # `_web_route` and absent from `API_ROUTES`, so all three replied
            # `route_unavailable`: creating an account, recovering a password
            # and redeeming a code were unreachable while every other check
            # stayed green. Each address must carry its own real refusal. Here
            # no account email adapter is installed, so sign-up and recovery
            # report that state, and promotion redemption asks who is calling.
            reachable = {path: httpx.post(base + path, json={}, trust_env=False)
                         for path in ("/api/v1/account/signup", "/api/v1/account/recovery",
                                      PROMOTION_REDEMPTION_PATH)}
            near_miss = httpx.post(base + "/api/v1/account/signup-typo", json={}, trust_env=False)
            check("an_address_the_router_answers_is_reachable_over_a_real_socket",
                  {answer.json()["error"]["code"] for answer in reachable.values()}
                  == {"account_email_unavailable", "unauthorized"}
                  and near_miss.json()["error"]["code"] == "route_unavailable")
            notices = httpx.get(base + "/assets/third-party-notices.txt", trust_env=False)
            check("packaged_browser_library_is_served_with_its_licence_terms",
                  notices.status_code == 200 and "MIT License" in notices.text and "Supabase" in notices.text
                  and notices.headers["content-type"].startswith("text/plain")
                  and "/assets/third-party-notices.txt" in public.text)
            own_origin = client.options("/api/v1/session", headers={"Origin": base})
            check("declared_service_origin_can_use_its_own_workspace",
                  own_origin.status_code == 204 and own_origin.headers["access-control-allow-origin"] == base)
            capabilities = client.get("/api/v1/capabilities").json()["result"]
            session = client.get("/api/v1/session").json()["result"]
            check("real_HTTP_profiles_and_durable_identity_are_inspectable",
                  capabilities["protocol"]["versions"] == ["2025-11-25", "2026-07-28"]
                  and capabilities["protocol"]["handshake_versions"] == ["2025-11-25"]
                  and capabilities["protocol"]["per_request_versions"] == ["2026-07-28"]
                  and capabilities["protocol"]["transport"] == "streamable_http"
                  and capabilities["retrieval"]["semantic_embedding_model_installed"] is False
                  and session["principal"]["tenant_id"] == "alpha")
            missing = httpx.get(base + "/api/v1/session", trust_env=False)
            wrong = client.get("/api/v1/session", headers={"Authorization": "Bearer WRONG_FIXTURE_TOKEN"})
            check("missing_and_wrong_credentials_refuse_without_secret_echo",
                  missing.status_code == wrong.status_code == 401
                  and "WRONG_FIXTURE_TOKEN" not in wrong.text and not fixture.reads)
            # A refusal used to carry a code and nothing else, so a customer
            # who mistyped a token read "unauthorized" and had to guess what
            # to do. Every refusal now states what happened and what to do
            # next, whatever produced it, and neither sentence repeats
            # anything from the request.
            refusals = [
                httpx.get(base + "/api/v1/session", trust_env=False),
                client.post("/api/v1/retrieval", json={"record_type": RETRIEVAL_REQUEST_VERSION, "query": ""}),
                client.post("/api/v1/retrieval", json={"record_type": RETRIEVAL_REQUEST_VERSION,
                                                       "query": "alpha", "mode": "telepathy"}),
                client.post("/api/v1/provisioning", json={"record_type": "service_provisioning_request/v0",
                                                          "operation": "list"}),
                client.post("/api/v1/provisioning", json=provisioning_request("list", surprise="FIXTURE_ECHO_PROBE")),
                client.post("/api/v1/retrieval", json={"record_type": RETRIEVAL_REQUEST_VERSION,
                                                       "query": "alpha", "FIXTURE_ECHO_PROBE": 1}),
                client.post("/api/v1/provisioning", content=b"not json",
                            headers={"Content-Type": "application/json"}),
                client.post("/api/v1/provisioning", json=[1, 2, 3]),
                client.post("/api/v1/provisioning", content=b"{}", headers={"Content-Type": "text/plain"}),
                client.post("/api/v1/provisioning", json=provisioning_request("read", identity="skill.beta",
                                                                             request_id="fixture-refusal-1")),
                httpx.post(base + "/api/v1/no-such-route", json={}, trust_env=False),
            ]
            errors = [answer.json()["error"] for answer in refusals]
            check("every_refusal_states_what_happened_and_what_to_do_next",
                  len(errors) == 11 and all(answer.status_code >= 400 for answer in refusals)
                  and all(len(error.get("message", "").split()) >= 5
                          and len(error.get("next_action", "").split()) >= 5
                          and error["message"].endswith(".") and error["next_action"].endswith(".")
                          and error["code"].replace("_", " ") not in error["message"].lower()
                          for error in errors)
                  and len({error["code"] for error in errors}) >= 7)
            check("a_refusal_never_repeats_the_caller_s_own_text_back_to_them",
                  not any("FIXTURE_ECHO_PROBE" in answer.text or "telepathy" in answer.text
                          or "skill.beta" in answer.text for answer in refusals))
            # The guard above must not be satisfiable by one sentence used for
            # everything: a wrong credential and a malformed search are
            # different problems and need different next actions.
            unauthorized = next(error for error in errors if error["code"] == "unauthorized")
            check("different_refusals_carry_different_next_actions",
                  len({error.get("next_action", "") for error in errors}) >= 5
                  and "token" in unauthorized.get("next_action", "").lower())
            listed = client.post("/api/v1/provisioning", json=provisioning_request()).json()["result"]
            search = client.post("/api/v1/retrieval", json={"record_type": RETRIEVAL_REQUEST_VERSION,
                "query": "alpha", "mode": "hybrid"}).json()["result"]
            check("metadata_and_retrieval_never_disclose_another_tenant_or_candidate",
                  {item["identity"] for item in listed["items"]} == {"skill.alpha", "skill.large"}
                  and {item["reference"]["identity"] for item in search["hits"]} <= {"skill.alpha", "skill.large"}
                  and bool(search["hits"]) and all(item["reference"]["record_type"] == "provisioning_item_binding/v1"
                                                 for item in search["hits"])
                  and not fixture.reads and search["bodies_loaded"] is False
                  and "skill.beta" not in json.dumps(search) and "skill.candidate" not in json.dumps(search))
            manifest = client.post("/api/v1/provisioning", json=provisioning_request("manifest", identity="skill.alpha"))
            check("manifest_retains_exact_body_identity_without_loading_or_metering",
                  manifest.status_code == 200 and manifest.json()["result"]["digest"]
                  == hashlib.sha256(fixture.bodies["skill.alpha"].encode()).hexdigest()
                  and not fixture.reads and fixture.usage()["records"] == 0)
            body_request = provisioning_request("read", identity="skill.alpha", request_id="web-same")
            first = client.post("/api/v1/provisioning", json=body_request).json()["result"]
            repeated = client.post("/api/v1/provisioning", json=body_request).json()["result"]
            check("real_HTTP_exact_retries_share_one_durable_usage_acknowledgment",
                  first["body"] == fixture.bodies["skill.alpha"]
                  and first["metering_acknowledgment"] == repeated["metering_acknowledgment"]
                  and first["metering_acknowledgment"]["durability"] == "durable"
                  and fixture.usage()["records"] == 1)
            reads_before = len(fixture.reads)
            stale = client.post("/api/v1/provisioning", json=provisioning_request("read", identity="skill.alpha",
                request_id="stale-selection", expected_digest="0" * 64))
            check("selected_digest_mismatch_refuses_before_body_read_and_metering",
                  stale.status_code == 404 and len(fixture.reads) == reads_before and fixture.usage()["records"] == 1)
            large = provisioning_request("read", identity="skill.large", request_id="large-download")
            inline = client.post("/api/v1/provisioning", json=large)
            check("large_body_requires_separate_download_without_premature_charge",
                  inline.status_code == 413 and inline.json()["error"]["code"] == "download_required"
                  and fixture.usage()["records"] == 1)
            download = client.post("/api/v1/download", json=large)
            check("authorized_download_has_exact_bytes_and_digest_outside_protocol_payload",
                  download.status_code == 200 and download.content == fixture.bodies["skill.large"].encode()
                  and download.headers["x-content-sha256"] == hashlib.sha256(download.content).hexdigest()
                  and download.headers["x-loop-engine-record-type"] == "service_download/v1")
            before = fixture.usage()["records"]
            fixture.bodies["skill.alpha"] = "ALTERED_BODY_FIXTURE"
            corrupt = client.post("/api/v1/provisioning", json=provisioning_request("read",
                identity="skill.alpha", request_id="corrupted"))
            check("changed_body_refuses_before_a_new_charge_or_disclosure",
                  corrupt.status_code != 200 and "ALTERED_BODY_FIXTURE" not in corrupt.text
                  and fixture.usage()["records"] == before)
            host = client.get("/api/v1/session", headers={"Host": "untrusted.example"})
            origin = client.get("/api/v1/session", headers={"Origin": "https://untrusted.example"})
            allowed = client.options("/api/v1/session", headers={"Origin": "http://127.0.0.1:5173"})
            check("Host_and_Origin_boundaries_refuse_cross_origin_browser_access",
                  host.status_code == 421 and origin.status_code == 403
                  and allowed.status_code == 204 and allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173")
            injected = client.post("/api/v1/provisioning", json=provisioning_request(tenant_id="beta"))
            duplicate = client.post("/api/v1/retrieval", content='{"query":"one","query":"two"}',
                                    headers={"Content-Type": "application/json"})
            old = client.post("/api/v1/provisioning", json={"record_type": "service_provisioning_request/v0", "operation": "list"})
            oversized = client.post("/api/v1/retrieval", json={"query": "x" * 70_000})
            check("unknown_authority_fields_duplicate_JSON_versions_and_oversize_requests_refuse",
                  injected.status_code == duplicate.status_code == old.status_code == 400
                  and oversized.status_code == 413)
            fixture.runtime.set_tenant_enabled("alpha", False)
            revoked = client.post("/api/v1/download", json=large)
            check("tenant_revocation_reauthorizes_even_a_previously_valid_download",
                  revoked.status_code == 401 and "LARGE_BODY_" not in revoked.text)


def _retrieval_snapshot_checks(check, root):
    import httpx
    from ..retrieval import Retriever
    for change in ("revoke", "replace", "entitlement"):
        folder = root / change
        folder.mkdir()
        fixture = HttpDomainFixture(folder)
        principal = fixture.runtime.authenticate_key(fixture.keys["alpha"].key)
        grants, _guard = fixture.runtime.grant_snapshot(principal)
        original = Retriever.search

        def mutate_after_ranking(retriever, *args, **kwargs):
            result = original(retriever, *args, **kwargs)
            if change == "entitlement":
                fixture.runtime.revoke_entitlement("alpha")
            else:
                fixture.runtime.set_grants("alpha", ())
                if change == "replace":
                    fixture.runtime.set_grants("alpha", grants)
            return result

        payload = {"record_type": RETRIEVAL_REQUEST_VERSION, "query": "Alpha"}
        with running_http(fixture) as (base, _service):
            with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False) as client:
                with patch.object(Retriever, "search", mutate_after_ranking):
                    response = client.post("/api/v1/retrieval", json=payload)
                following = client.post("/api/v1/retrieval", json=payload)
        check("retrieval_completion_refuses_in_flight_" + change,
              response.status_code == 403
              and response.json()["error"]["code"] == "disclosure_grant_changed"
              and "hits" not in response.text and "skill.alpha" not in response.text
              and not fixture.reads and fixture.usage()["records"] == 0)
        hits = following.json().get("result", {}).get("hits", [])
        check("fresh_retrieval_uses_current_authority_after_" + change,
              following.status_code == 200
              and (not hits if change == "revoke" else bool(hits))
              and (change != "entitlement" or all(not row["body_allowed"] for row in hits)))


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
                from ..retrieval import Retriever
                original = Retriever.search
                def revoke_after_ranking(retriever, *args, **kwargs):
                    result = original(retriever, *args, **kwargs)
                    fixture.runtime.set_grants("alpha", ())
                    return result
                with patch.object(Retriever, "search", revoke_after_ranking):
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


def _identity_checks(check, root):
    import httpx
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    fixture = HttpDomainFixture(root)
    with running_key_set() as (issuer_base, key_set):
        issuer, audience = issuer_base + "/issuer", "https://intelligence.example/mcp"
        fixture.runtime.bind_subject(SubjectBindingRequest("alpha", issuer, "known-subject"))
        first_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        second_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        def public_key(key, kid):
            return {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": kid, "alg": "RS256", "use": "sig"}
        key_set["keys"] = [public_key(first_key, "first")]
        def configuration(http_configuration):
            nonlocal audience
            audience = http_configuration.public_base_url + "/mcp"
            return ServiceHttpAuthentication(modes=("external_jwt",), issuer=issuer,
                jwks_url=issuer_base + "/jwks", audience=audience, required_scopes=("provisioning:metadata",),
                allow_loopback_issuer=True, minimum_key_refresh_seconds=1)
        def token(key=first_key, kid="first", **changes):
            claims = {"iss": issuer, "aud": audience, "sub": "known-subject", "exp": int(time.time()) + 300,
                      "iat": int(time.time()), "scope": "provisioning:metadata provisioning:read usage:read",
                      "tenant_id": "beta", **changes}
            return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})
        with running_http(fixture, authentication=configuration) as (base, service):
            with httpx.Client(base_url=base, trust_env=False, timeout=3) as client:
                def session(credential):
                    return client.get("/api/v1/session", headers={"Authorization": "Bearer " + credential})
                accepted = session(token())
                metadata = client.get("/.well-known/oauth-protected-resource/mcp")
                challenge = client.get("/api/v1/session")
                check("external_resource_discovery_points_to_the_configured_identity_provider_without_issuing_tokens",
                      metadata.status_code == 200 and metadata.json()["authorization_servers"] == [issuer]
                      and metadata.json()["resource"] == base + "/mcp"
                      and challenge.status_code == 401 and "resource_metadata=" in challenge.headers["www-authenticate"])
                check("external_token_uses_verified_subject_mapping_not_its_tenant_claim",
                      accepted.status_code == 200 and accepted.json()["result"]["principal"]["tenant_id"] == "alpha")
                narrow = token(scope="provisioning:metadata")
                identity = session(narrow)
                denied = client.post("/api/v1/provisioning", headers={"Authorization": "Bearer " + narrow},
                    json=provisioning_request("read", identity="skill.alpha", request_id="not-permitted"))
                check("external_token_scope_cannot_inherit_broader_durable_user_permissions",
                      identity.status_code == 200 and identity.json()["result"]["principal"]["scopes"] == ["provisioning:metadata"]
                      and denied.status_code == 403 and not fixture.reads)
                rejected = [session(token(**changes)) for changes in (
                    {"aud": "wrong-audience"}, {"iss": "https://wrong-issuer.example"},
                    {"sub": "unmapped-subject"}, {"exp": int(time.time()) - 30}, {"scope": "unrelated"})]
                symmetric = jwt.encode({"iss": issuer, "aud": audience, "sub": "known-subject", "exp": int(time.time()) + 60},
                                       "local-untrusted-fixture-secret-long-enough", algorithm="HS256", headers={"kid": "first"})
                check("wrong_issuer_audience_subject_expiry_scope_and_algorithm_refuse",
                      all(row.status_code in (401, 403) for row in rejected) and session(symmetric).status_code == 401)
                # Anonymous callers choose the key identifier. A burst of unknown
                # identifiers may cause one provider read, never one per request.
                reads = key_set["requests"]
                forged = [session(token(second_key, "unknown-" + str(index))) for index in range(6)]
                check("forged_key_identifiers_cannot_force_a_key_set_read_per_request",
                      all(row.status_code == 401 for row in forged) and key_set["requests"] - reads <= 1)
                # Known-wrong control: a clock on which the pause has always
                # passed is the unbounded behavior, and the count must show it.
                keys, ticks, reads = service.authenticator._keys, iter(range(10**6, 10**9, 3600)), key_set["requests"]
                keys.clock = lambda: next(ticks)
                for index in range(4):
                    session(token(second_key, "unpaused-" + str(index)))
                check("removed_key_refresh_pause_is_detected", key_set["requests"] - reads >= 4)
                del keys.clock
                keys.last_attempt = None
                key_set["keys"] = [public_key(second_key, "second")]
                rotated = session(token(second_key, "second"))
                check("unknown_key_identifier_refreshes_only_the_configured_key_endpoint",
                      rotated.status_code == 200 and key_set["requests"] >= 2
                      and set(key_set["paths"]) == {"/jwks"})
                third_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                key_set["keys"] = [public_key(third_key, "second")]
                # The pause is a length of time, not a moment of this machine's
                # clock. Waiting for real time to pass let a loaded machine
                # cross the pause before the first request and hide the refusal
                # this check exists to show, so both moments are named here.
                moment = [keys.last_attempt if keys.last_attempt is not None else 0.0]
                keys.clock = lambda: moment[0]
                early = session(token(third_key, "second"))
                moment[0] += service.authentication.minimum_key_refresh_seconds + 0.1
                same_identifier = session(token(third_key, "second"))
                del keys.clock
                check("key_rotation_inside_the_pause_is_refused_not_guessed", early.status_code == 401)
                check("same_identifier_key_rotation_refreshes_after_signature_failure",
                      same_identifier.status_code == 200)
                fixture.runtime.revoke_subject(SubjectBindingRequest("alpha", issuer, "known-subject"))
                check("external_subject_revocation_is_durable_and_checked_on_the_next_request",
                      session(token(third_key, "second")).status_code == 401)


def _request_limit_checks(check, root):
    """The failed-attempt limit over real sockets, where the peer is always the loopback address."""
    import httpx
    from .request_limits import LIMIT_REACHED_CODE, ServiceRequestLimits
    wrong = {"Authorization": "Bearer WRONG_FIXTURE_TOKEN"}
    (root / "peer").mkdir()
    fixture = HttpDomainFixture(root / "peer")
    limits = ServiceRequestLimits(client_address_source="socket_peer", failures_allowed=3)
    with running_http(fixture, request_limits=limits) as (base, service):
        reached, authenticate = [], service._authenticate_request
        service._authenticate_request = lambda request: (reached.append(request.url.path), authenticate(request))[1]
        with httpx.Client(base_url=base, trust_env=False, timeout=3) as client:
            # The host configured no address header, so rotating forged ones changes nothing.
            forged = [client.get("/api/v1/session", headers={**wrong, "Fly-Client-IP": "203.0.113." + str(index),
                                                             "X-Forwarded-For": "203.0.113." + str(index)})
                      for index in range(1, 5)]
            over, wait = forged[-1], forged[-1].headers.get("retry-after", "")
            check("real_HTTP_attempt_over_the_failure_limit_gets_429_and_Retry_After_before_authentication",
                  [row.status_code for row in forged] == [401, 401, 401, 429] and len(reached) == 3
                  and over.json()["error"]["code"] == LIMIT_REACHED_CODE
                  and wait.isdigit() and 1 <= int(wait) <= 60
                  and over.json()["error"].get("details", {}).get("retry_after_seconds") == int(wait)
                  and over.headers["cache-control"] == "no-store" and "WRONG_FIXTURE_TOKEN" not in over.text)
            protocol = client.post("/mcp", headers={**fixture.headers(), "Accept": "application/json, text/event-stream"},
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25",
                      "capabilities": {}, "clientInfo": {"name": "limited", "version": "1"}}})
            check("real_protocol_route_shares_the_failed_attempt_limit_and_public_routes_stay_open",
                  protocol.status_code == 429 and "retry-after" in protocol.headers
                  and client.get("/api/v1/session", headers=fixture.headers()).status_code == 429
                  and client.get("/api/v1/health").status_code == 200 and len(reached) == 3)
            started = service.request_limiter.clock
            service.request_limiter.clock = lambda: started() + 61
            check("real_HTTP_limit_ends_when_the_window_has_passed",
                  client.get("/api/v1/session", headers=fixture.headers()).status_code == 200)
    (root / "proxy").mkdir()
    fixture = HttpDomainFixture(root / "proxy")
    limits = ServiceRequestLimits(client_address_source="header", client_address_header="Fly-Client-IP",
                                  failures_allowed=2)
    with running_http(fixture, request_limits=limits) as (base, service):
        with httpx.Client(base_url=base, trust_env=False, timeout=3) as client:
            def through_proxy(address, credential, *more):
                return client.get("/api/v1/session", headers=[*credential.items(), ("Fly-Client-IP", address),
                                                              *(("Fly-Client-IP", value) for value in more)]).status_code
            first = [through_proxy("198.51.100.10", wrong) for _attempt in range(3)]
            repeated = [through_proxy("203.0.113.9", wrong, "203.0.113." + str(index)) for index in range(20, 23)]
            check("real_HTTP_configured_proxy_header_separates_clients_and_a_repeated_header_names_nobody",
                  first == [401, 401, 429] and through_proxy("198.51.100.20", fixture.headers()) == 200
                  and repeated == [401, 401, 429] and through_proxy("203.0.113.9", fixture.headers()) == 200
                  and sorted(service.request_limiter._failures) == ["127.0.0.1", "198.51.100.10"])


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


def unrun_service_check_modules(sources=None):
    """Return the check modules of this service that no suite runs.

    A check module that nothing imports passes forever and proves nothing. The
    observability checks were in that state after the September 22 merges:
    written, documented and cited by the operator guide, and run by no suite,
    because the one call to them was lost in a merge without a conflict.

    A module counts as run when the suite registration names it, or when a
    module that runs imports one of its entry points from this folder and calls
    it: `self_test`, a public function whose name starts with `run_`, or one
    whose name ends in `_checks`. An import alone does not count, because a
    merge can drop the call and keep the import beside it, and calling a
    fixture or reading a constant runs none of the module's checks. Only the
    source is read, so nothing is executed to answer the question. `sources`
    replaces the text of named modules, so a check can ask the question of a
    known-wrong folder.
    """
    import ast
    from importlib.resources import files
    from ..._conformance_scan import _registered_test_modules
    package = files("loop_engine")
    folder = package.joinpath("core", "service_runtime")
    modules = {entry.name[:-3] for entry in folder.iterdir() if entry.name.endswith(".py")}
    prefix = "core.service_runtime."
    suite = ast.parse(package.joinpath("_self_test.py").read_text("utf-8"))
    run = {name[len(prefix):] for name in _registered_test_modules(suite)
           if name.startswith(prefix) and name[len(prefix):] in modules}

    def entry_point(imported):
        return imported == "self_test" or (not imported.startswith("_")
            and (imported.startswith("run_") or imported.endswith("_checks")))
    pending = list(run)
    while pending:
        name = pending.pop()
        tree = ast.parse((sources or {}).get(name) or folder.joinpath(name + ".py").read_text("utf-8"))
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module in modules \
                    and node.module not in run \
                    and any(entry_point(alias.name) and (alias.asname or alias.name) in called
                            for alias in node.names):
                run.add(node.module)
                pending.append(node.module)
    return sorted(name for name in modules - run if name.endswith("_checks"))


def self_test():
    try:
        import mcp, httpx, uvicorn, jwt
    except ImportError as error:
        return {"tests": [{"test": "remote_HTTP_optional_dependencies_not_installed", "passed": None,
            "not_tested": True, "outcome": "NOT_APPLICABLE", "missing_optional_dependencies": [error.name],
            "detail": "The serving integration requires its declared optional dependency set."}]}
    tests = []
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed), "detail": "real loopback transport; no external provider"})
    for name, function in (("web", _web_checks), ("identity", _identity_checks),
                           ("retrieval_snapshot", _retrieval_snapshot_checks),
                           ("request_limits", _request_limit_checks)):
        with tempfile.TemporaryDirectory(prefix="service-http-" + name + "-") as directory:
            function(check, Path(directory))
    for name, function in (("protocol", _protocol_checks), ("negotiation", _negotiation_checks),
                           ("configured_versions", _configured_version_checks),
                           ("cancellation", _cancellation_checks)):
        with tempfile.TemporaryDirectory(prefix="service-http-" + name + "-") as directory:
            asyncio.run(function(check, Path(directory)))
    from .http_boundary_checks import run_checks
    with tempfile.TemporaryDirectory(prefix="service-http-boundaries-") as directory:
        run_checks(check, Path(directory))
    from .request_limit_checks import run_checks as request_limit_checks
    def limit_check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "injected clock and the real application through ASGI; no socket, no external provider"})
    with tempfile.TemporaryDirectory(prefix="service-request-limits-") as directory:
        request_limit_checks(limit_check, Path(directory))
    from .access_checks import run_all_checks
    for row in run_all_checks()["tests"]:
        check(row["test"], row["passed"])
    from .browser_identity_checks import run_checks as identity_account_checks
    with tempfile.TemporaryDirectory(prefix="service-browser-identity-") as directory:
        identity_account_checks(check, Path(directory))
    from .promotion_checks import run_http_checks as promotion_transport_checks
    with tempfile.TemporaryDirectory(prefix="service-promotions-http-") as directory:
        promotion_transport_checks(check, Path(directory))
    from .account_email_checks import run_checks as account_email_checks
    def account_check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "injected provider transports and owned loopback listeners; no provider is contacted"})
    with tempfile.TemporaryDirectory(prefix="service-account-email-") as directory:
        account_email_checks(account_check, Path(directory))
    from .waitlist_checks import run_all_checks as waiting_list_checks
    with tempfile.TemporaryDirectory(prefix="service-waitlist-") as directory:
        for row in waiting_list_checks(Path(directory))["tests"]:
            check(row["test"], row["passed"])
    from .observability_checks import run_checks as observability_checks
    observability_checks(check)
    check("every_service_check_module_is_run_by_a_suite", not unrun_service_check_modules())
    # Known-wrong case for the guard above: a merge can drop the call and keep
    # the import beside it. Nothing then runs the module, and the import alone
    # must not count as running it.
    from importlib.resources import files
    source = files("loop_engine").joinpath("core", "service_runtime", "http_checks.py").read_text("utf-8")
    dropped = source.replace("    observability_checks(check)\n", "", 1)
    check("a_check_module_imported_but_never_called_is_named_as_unrun",
          dropped != source and "observability_checks" in unrun_service_check_modules({"http_checks": dropped}))
    return {"tests": tests, "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
