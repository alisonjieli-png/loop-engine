"""Real loopback acceptance for the hosted service transports.

These checks use durable domain records, actual HTTP sockets, official protocol
client streams and locally signed identity tokens. No remote provider is called
and no local fixture is represented as live Supabase or payment qualification.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch

from .http import PROVISIONING_REQUEST_VERSION, RETRIEVAL_REQUEST_VERSION
from .http_auth import ServiceHttpAuthentication
from .http_test_fixtures import HttpDomainFixture, running_http, running_key_set
from .records import SubjectBindingRequest


def provisioning_request(operation="list", **fields):
    return {"record_type": PROVISIONING_REQUEST_VERSION, "operation": operation, **fields}


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
            from .http import WEB_ASSETS
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
                  capabilities["protocol"]["versions"] == ["2025-11-25"]
                  and capabilities["protocol"]["transport"] == "streamable_http"
                  and capabilities["retrieval"]["semantic_embedding_model_installed"] is False
                  and session["principal"]["tenant_id"] == "alpha")
            missing = httpx.get(base + "/api/v1/session", trust_env=False)
            wrong = client.get("/api/v1/session", headers={"Authorization": "Bearer WRONG_FIXTURE_TOKEN"})
            check("missing_and_wrong_credentials_refuse_without_secret_echo",
                  missing.status_code == wrong.status_code == 401
                  and "WRONG_FIXTURE_TOKEN" not in wrong.text and not fixture.reads)
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
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    fixture = HttpDomainFixture(root)
    with running_http(fixture) as (base, _service):
        async with streamablehttp_client(base + "/mcp", headers=fixture.headers()) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                check("official_client_uses_real_StreamableHTTP_with_the_exact_supported_profile",
                      initialized.protocolVersion == "2025-11-25" and len(tools.tools) == 5)
                found = await session.call_tool("intelligence_search", {"query": "alpha"})
                check("protocol_search_returns_typed_authorized_references_without_bodies",
                      not found.isError and found.structuredContent["result"]["hits"]
                      and found.structuredContent["result"]["bodies_loaded"] is False
                      and "skill.beta" not in str(found.structuredContent))
                first = await session.call_tool("provisioning_read", {"identity": "skill.alpha", "request_id": "cross-transport"})
                async with httpx.AsyncClient(trust_env=False) as client:
                    repeat = await client.post(base + "/api/v1/provisioning", headers=fixture.headers(),
                        json=provisioning_request("read", identity="skill.alpha", request_id="cross-transport"))
                check("HTTP_and_protocol_share_the_same_domain_and_idempotent_usage_identity",
                      not first.isError and first.structuredContent["result"]["metering_acknowledgment"]
                      == repeat.json()["result"]["metering_acknowledgment"] and fixture.usage()["records"] == 1)
                refused = await session.call_tool("provisioning_read", {"identity": "skill.beta", "request_id": "private"})
                injected = await session.call_tool("provisioning_list", {"tenant_id": "beta"})
                check("protocol_refusals_hide_cross_tenant_items_and_reject_authority_injection",
                      refused.isError and injected.isError and "PRIVATE_BETA_BODY" not in str(refused)
                      and fixture.usage()["records"] == 1)
                from ..retrieval import Retriever
                original = Retriever.search
                def revoke_after_ranking(retriever, *args, **kwargs):
                    result = original(retriever, *args, **kwargs)
                    fixture.runtime.set_grants("alpha", ())
                    return result
                with patch.object(Retriever, "search", revoke_after_ranking):
                    revoked = await session.call_tool("intelligence_search", {"query": "Alpha"})
                check("protocol_search_shares_the_completion_authorization_guard",
                      revoked.isError and revoked.structuredContent["error"]["code"] == "disclosure_grant_changed"
                      and "skill.alpha" not in str(revoked))
        async with httpx.AsyncClient(trust_env=False) as client:
            request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2026-07-28", "capabilities": {}, "clientInfo": {"name": "unsupported", "version": "1"}}}
            wrong = await client.post(base + "/mcp", headers=fixture.headers(), json=request)
            check("remote_protocol_refuses_unqualified_versions_without_silent_negotiation",
                  wrong.status_code == 400 and wrong.json()["error"]["code"] == "unsupported_protocol_version")


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
                early = session(token(third_key, "second"))
                time.sleep(1.1)
                same_identifier = session(token(third_key, "second"))
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
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    fixture = HttpDomainFixture(root)
    entered, release = threading.Event(), threading.Event()
    def wait(_item):
        entered.set()
        if not release.wait(3):
            raise RuntimeError("bounded fixture release did not arrive")
    fixture.before_read = wait
    with running_http(fixture, request_timeout_seconds=2) as (base, _service):
        try:
            async with streamablehttp_client(base + "/mcp", headers=fixture.headers()) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    pending = asyncio.create_task(session.call_tool("provisioning_read",
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
                    repeated = await session.call_tool("provisioning_read",
                        {"identity": "skill.alpha", "request_id": "cancelled-once"})
                    check("real_protocol_cancellation_does_not_replay_or_duplicate_uncertain_metering",
                          cancelled and entered.is_set() and reads_before_retry == 1
                          and len(fixture.reads) == 2 and not repeated.isError and fixture.usage()["records"] == 1)
        finally:
            release.set()


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
    for name, function in (("protocol", _protocol_checks), ("cancellation", _cancellation_checks)):
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
    from .account_email_checks import run_checks as account_email_checks
    def account_check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "injected provider transports and owned loopback listeners; no provider is contacted"})
    with tempfile.TemporaryDirectory(prefix="service-account-email-") as directory:
        account_email_checks(account_check, Path(directory))
    return {"tests": tests, "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
