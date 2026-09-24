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
    # The ranking seam is the view's reusable index since catalogue releases.
    from .catalogue_search import ReleaseSearchIndex
    for change in ("revoke", "replace", "entitlement"):
        folder = root / change
        folder.mkdir()
        fixture = HttpDomainFixture(folder)
        principal = fixture.runtime.authenticate_key(fixture.keys["alpha"].key)
        grants, _guard = fixture.runtime.grant_snapshot(principal)
        original = ReleaseSearchIndex.rank

        def mutate_after_ranking(index, *args, **kwargs):
            result = original(index, *args, **kwargs)
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
                with patch.object(ReleaseSearchIndex, "rank", mutate_after_ranking):
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
    from .protocol_checks import run_checks as protocol_checks
    protocol_checks(check)
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
    from .account_origin_checks import run_checks as account_origin_checks
    with tempfile.TemporaryDirectory(prefix="service-account-origin-") as directory:
        account_origin_checks(check, Path(directory))
    from .account_administration_checks import run_checks as account_administration_checks
    with tempfile.TemporaryDirectory(prefix="service-account-administration-") as directory:
        account_administration_checks(check, Path(directory))
    from .staff_sign_up_link_checks import run_checks as staff_sign_up_link_checks
    with tempfile.TemporaryDirectory(prefix="service-staff-sign-up-links-") as directory:
        staff_sign_up_link_checks(check, Path(directory))
    from .waitlist_checks import run_all_checks as waiting_list_checks
    with tempfile.TemporaryDirectory(prefix="service-waitlist-") as directory:
        for row in waiting_list_checks(Path(directory))["tests"]:
            check(row["test"], row["passed"])
    from .observability_checks import run_checks as observability_checks
    observability_checks(check)
    from .retention_checks import run_checks as retention_checks
    with tempfile.TemporaryDirectory(prefix="service-retention-") as directory:
        retention_checks(check, Path(directory))
    from .catalogue_serving_checks import run_checks as catalogue_serving_checks
    with tempfile.TemporaryDirectory(prefix="service-catalogue-serving-") as directory:
        catalogue_serving_checks(check, Path(directory))
    from .web_surface_checks import run_checks as web_surface_checks
    with tempfile.TemporaryDirectory(prefix="service-web-surfaces-") as directory:
        web_surface_checks(check, Path(directory))
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
