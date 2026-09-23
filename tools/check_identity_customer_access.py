"""Qualify a real identity provider against a temporary local service.

Requires explicit disposable-user creation and cleanup authority. Admin-confirmed
test identities send no email and do not prove confirmation or recovery delivery.
Secrets stay in memory and the selected environment; reports contain no tokens.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
import uuid


class QualificationFailure(RuntimeError):
    """Sanitized failed-check identity, never an external response body."""


def user_body(value):
    return value.get("user", value) if isinstance(value, dict) else {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acknowledge-disposable-user-effects", action="store_true")
    parser.add_argument("--service-origin")
    parser.add_argument("--fly-app")
    parser.add_argument("--acknowledge-hosted-account-effects", action="store_true")
    args = parser.parse_args(argv)
    if not args.acknowledge_disposable_user_effects:
        parser.error("explicit disposable identity creation and cleanup authority is required")
    if not re.fullmatch(r"[a-z]{20}", args.project_ref):
        parser.error("an exact Supabase project reference is required")
    if bool(args.service_origin) != bool(args.fly_app) or (args.service_origin and not args.acknowledge_hosted_account_effects):
        parser.error("a hosted target needs an exact origin, Fly app and explicit account-effect authority")
    if args.service_origin:
        from urllib.parse import urlsplit
        origin = urlsplit(args.service_origin)
        if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
                or origin.path or origin.query or origin.fragment or not re.fullmatch(r"[a-z0-9-]{1,63}", args.fly_app)):
            parser.error("the hosted target must be an exact HTTPS origin and application identity")
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        parser.error("use an existing report folder and an unused report path")
    admin, publishable = os.environ.get("SUPABASE_SECRET_KEY", ""), os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    if (not re.fullmatch(r"sb_secret_[A-Za-z0-9_-]{20,128}", admin)
            or not re.fullmatch(r"sb_publishable_[A-Za-z0-9_-]{20,128}", publishable)):
        parser.error("named modern server and publishable credential references are required")
    import httpx
    from loop_engine.core.service_runtime.access import ServiceAccessAdministration, ServiceClientAccessPolicy
    from loop_engine.core.service_runtime.browser_identity import BrowserIdentityAdapter, BrowserIdentityConfiguration, read_identity_user
    from loop_engine.core.service_runtime.http import ServiceHttpApplication
    from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
    from loop_engine.core.service_runtime.records import SubjectBindingRequest
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    root = Path(__file__).resolve().parents[1]
    sources = [root / "src/loop_engine/core/service_runtime" / name for name in (
        "access.py", "records.py", "runtime.py", "storage.py", "provisioning.py", "http.py", "http_auth.py", "browser_identity.py")]
    sources.extend((Path(__file__).resolve(), root / "tools/identity_qualification_host.py"))
    snapshot = lambda: {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    before, run_id = snapshot(), uuid.uuid4().hex
    expected_sources = {path: value for path, value in before.items() if path.startswith("src/loop_engine/core/service_runtime/")}
    project = "https://" + args.project_ref + ".supabase.co"
    tests, users, secrets_used = [], [], [admin, publishable]
    calls = {"operator_provider_requests": 0, "identity_user_reads": 0, "key_set_reads": 0}
    failure, cleanup_failed, unknown_creation = None, False, False
    hosted_preparation_attempted, hosted_source = False, None
    started = time.monotonic()

    def check(name, passed):
        tests.append({"name": name, "passed": bool(passed)})
        if not passed:
            raise QualificationFailure(name)

    with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as provider:
        def remote(method, path, *, privileged=False, body=None):
            calls["operator_provider_requests"] += 1
            if calls["operator_provider_requests"] > 40:
                raise QualificationFailure("operator_request_limit")
            headers = {"apikey": admin if privileged else publishable}
            if privileged:
                headers["Authorization"] = "Bearer " + admin
            return provider.request(method, project + "/auth/v1" + path, headers=headers, json=body)

        try:
            if args.service_origin:
                from identity_qualification_host import operate
                public = provider.get(args.service_origin + "/api/v1/capabilities")
                available = public.json().get("result", {}).get("website", {}) if public.status_code == 200 else {}
                check("hosted_account_adapters_are_installed_without_public_registration", available.get("client_access_available") is True
                      and available.get("browser_identity_available") is True and available.get("registration_available") is False)
                asset = provider.get(args.service_origin + "/assets/client-access.js")
                check("hosted_client_asset_matches_the_tested_source", asset.status_code == 200
                      and asset.content == (root / "src/loop_engine/core/service_runtime/web_assets/client-access.js").read_bytes())
            public_keys = remote("GET", "/.well-known/jwks.json")
            check("provider_exposes_supported_asymmetric_signing_keys", public_keys.status_code == 200
                  and any(key.get("alg") in ("RS256", "ES256") for key in public_keys.json().get("keys", [])))
            for slot in range(2):
                email = "baltor-qualification-" + run_id + "-" + str(slot) + "@example.invalid"
                password = secrets.token_urlsafe(36)
                secrets_used.append(password)
                try:
                    created = remote("POST", "/admin/users", privileged=True, body={"email": email, "password": password,
                        "email_confirm": True, "app_metadata": {"baltor_qualification": run_id},
                        "user_metadata": {"tenant_id": "alpha", "role": "administrator", "email_verified": True}})
                except httpx.HTTPError:
                    unknown_creation = True
                    raise QualificationFailure("user_creation_outcome_unknown_do_not_repeat") from None
                check("disposable_user_created_" + str(slot), created.status_code in (200, 201))
                user = user_body(created.json())
                check("provider_user_identity_is_valid_" + str(slot), isinstance(user.get("id"), str) and bool(re.fullmatch(r"[a-f0-9-]{36}", user["id"])))
                users.append({"id": user["id"], "email": email, "deleted": False})
                check("created_user_is_bound_to_this_test_" + str(slot), user.get("email") == email and user.get("app_metadata", {}).get("baltor_qualification") == run_id)
                signed = remote("POST", "/token?grant_type=password", body={"email": email, "password": password})
                check("real_password_sign_in_" + str(slot), signed.status_code == 200 and isinstance(signed.json().get("access_token"), str))
                users[-1]["token"] = signed.json()["access_token"]
                secrets_used.extend(value for key, value in signed.json().items() if key in ("access_token", "refresh_token") and isinstance(value, str))
            with ExitStack() as stack:
                directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="baltor-real-identity-")))
                fixture = HttpDomainFixture(directory, operator_access=False)
                def identity_read(request):
                    calls["identity_user_reads"] += 1
                    return read_identity_user(request)
                identity = BrowserIdentityAdapter(fixture.runtime, BrowserIdentityConfiguration(project,
                    "env:SUPABASE_PUBLISHABLE_KEY", "qualified-test", registration_enabled=True, allow_network=True),
                    lambda _: publishable, starter_bindings=(fixture.bindings["skill.alpha"],), transport=identity_read)
                fetch_keys = identity._verifier._keys.fetch_data
                def counted_keys():
                    calls["key_set_reads"] += 1
                    return fetch_keys()
                identity._verifier._keys.fetch_data = counted_keys
                manager = ServiceAccessAdministration(fixture.runtime, ServiceClientAccessPolicy(writes_authorized=True))
                sample_identity, sample_query = "skill.alpha", "alpha"
                if args.service_origin:
                    hosted_preparation_attempted = True
                    prepared = operate(application=args.fly_app, origin=args.service_origin, issuer=project + "/auth/v1",
                        run_id=run_id, subjects=[user["id"] for user in users], operation="prepare", expected_sources=expected_sources)
                    hosted_source = prepared["source_sha256"]
                    check("hosted_backend_matches_selected_source", all(before.get(path) == value for path, value in hosted_source.items()))
                    base = args.service_origin
                    sample_identity, sample_query = prepared["sample_identity"], prepared["sample_query"]
                    calls["identity_user_reads"], calls["key_set_reads"] = None, None
                else:
                    base, _application = stack.enter_context(running_http(fixture, application_factory=lambda config:
                        ServiceHttpApplication(fixture.runtime, fixture.provisioning, config, browser_identity=identity, client_access=manager)))
                with httpx.Client(base_url=base, timeout=20, follow_redirects=False, trust_env=False) as client:
                    headers = [{"Authorization": "Bearer " + user["token"]} for user in users]
                    activation = {"record_type": "service_account_activation_request/v1"}
                    tenants = []
                    for slot in range(2):
                        response = (client.get("/api/v1/session", headers=headers[slot]) if args.service_origin else
                                    client.post("/api/v1/account/activate", headers=headers[slot], json=activation))
                        check("real_identity_activates_server_owned_account_" + str(slot), response.status_code == 200)
                        result = response.json()["result"]
                        tenants.append(result["principal"]["tenant_id"] if args.service_origin else result["tenant_id"])
                    check("real_identities_cannot_choose_or_share_a_tenant", tenants[0] != tenants[1] and "alpha" not in tenants)
                    duplicate = client.post("/api/v1/account/activate", headers=headers[0], json=activation)
                    if args.service_origin:
                        check("hosted_public_account_admission_remains_closed", duplicate.status_code == 400)
                    else:
                        check("real_account_activation_is_idempotent", duplicate.status_code == 200 and duplicate.json()["result"]["created"] is False)
                    body = {"record_type": "service_client_access_request/v1", "operation": "issue", "request_id": run_id,
                            "label": "Disposable qualification client", "scopes": ["provisioning:metadata"], "lifetime_seconds": 600}
                    issued = client.post("/api/v1/account/access", headers=headers[0], json=body)
                    check("real_identity_can_issue_a_scoped_client_key", issued.status_code == 200 and issued.json()["result"]["committed"] is True)
                    key = issued.json()["result"]; token = key["token"]; secrets_used.append(token)
                    duplicate = client.post("/api/v1/account/access", headers=headers[0], json=body)
                    check("retry_never_replays_the_secret", duplicate.status_code == 200 and duplicate.json()["result"]["token"] is None)
                    foreign = client.post("/api/v1/account/access", headers=headers[1], json={"record_type": "service_client_access_request/v1",
                        "operation": "revoke", "request_id": run_id, "key_id": key["key"]["key_id"]})
                    check("real_other_identity_cannot_revoke_the_key", foreign.status_code == 404)
                    client_headers = {"Authorization": "Bearer " + token}
                    denied = client.post("/api/v1/account/access", headers=client_headers, json=body)
                    check("client_key_cannot_mint_more_credentials", denied.status_code == 403)
                    async def protocol():
                        async with httpx2.AsyncClient(headers=client_headers, timeout=30) as http:
                            async with Client(streamable_http_client(base + "/mcp", http_client=http), mode="legacy") as session:
                                check("issued_key_connects_through_the_real_protocol_sdk", session.protocol_version == "2025-11-25")
                                found = await session.call_tool("intelligence_search", {"query": sample_query, "mode": "lexical"})
                                result = found.structured_content or json.loads(next(item.text for item in found.content if item.type == "text"))
                                check("issued_key_retrieves_only_permitted_reference_metadata", not found.is_error
                                      and len(result["result"]["hits"]) == 1 and result["result"]["hits"][0]["reference"]["identity"] == sample_identity
                                      and result["result"]["hits"][0]["body_allowed"] is False)
                    asyncio.run(protocol())
                    foreign_scope = client.post("/api/v1/download", headers=client_headers, json={"record_type": "service_provisioning_request/v1",
                        "operation": "read", "identity": sample_identity, "request_id": run_id})
                    check("metadata_key_cannot_download_bodies", foreign_scope.status_code == 403 and fixture.reads == [])
                    if args.service_origin:
                        operate(application=args.fly_app, origin=args.service_origin, issuer=project + "/auth/v1",
                            run_id=run_id, subjects=[user["id"] for user in users], operation="revoke_first", expected_sources=expected_sources)
                    else:
                        fixture.runtime.revoke_subject(SubjectBindingRequest(tenants[0], project + "/auth/v1", users[0]["id"]))
                    check("local_subject_revocation_invalidates_its_existing_key", client.get("/api/v1/session", headers=client_headers).status_code == 401)
                    signed_out = client.post("/api/v1/account/logout", headers=headers[1], json={"record_type":"service_browser_logout_request/v1"})
                    check("real_browser_token_can_be_revoked_locally", signed_out.status_code == 200
                          and client.get("/api/v1/session", headers=headers[1]).status_code == 401)
        except QualificationFailure as error:
            failure = str(error)
        except Exception as error:
            failure = "unexpected_" + type(error).__name__
        finally:
            if hosted_preparation_attempted:
                try:
                    operate(application=args.fly_app, origin=args.service_origin, issuer=project + "/auth/v1",
                        run_id=run_id, subjects=[user["id"] for user in users], operation="cleanup", expected_sources=expected_sources)
                except Exception:
                    cleanup_failed = True
            for user in users:
                try:
                    current = remote("GET", "/admin/users/" + user["id"], privileged=True)
                    value = user_body(current.json()) if current.status_code == 200 else {}
                    if value.get("email") != user["email"] or value.get("app_metadata", {}).get("baltor_qualification") != run_id:
                        cleanup_failed = True
                        continue
                    deleted = remote("DELETE", "/admin/users/" + user["id"], privileged=True, body={"should_soft_delete": True})
                    user["deleted"] = deleted.status_code == 200
                    cleanup_failed |= not user["deleted"]
                except Exception:
                    cleanup_failed = True
    after = snapshot()
    report = {"record_type": "identity_customer_access_qualification/v1", "observed_at": datetime.now(timezone.utc).isoformat(),
        "project_url": project, "run_id": run_id, "scope": "real identity provider with " + ("the selected hosted service" if args.service_origin else "temporary local service") + " and diagnostic material",
        "service_origin": args.service_origin, "hosted_preparation_attempted": hosted_preparation_attempted,
        "hosted_source_sha256": hosted_source,
        "source_before": before, "source_after": after, "source_unchanged": before == after,
        "checks": tests, "passed": sum(row["passed"] for row in tests), "total": len(tests),
        "all_passed": failure is None and not cleanup_failed and not unknown_creation and before == after,
        "failure": failure, "provider_requests": calls, "elapsed_seconds": time.monotonic() - started,
        "disposable_accounts": [{"user_id": user["id"], "soft_deleted": user["deleted"]} for user in users],
        "cleanup_failed": cleanup_failed, "unknown_creation_outcome": unknown_creation,
        "email_sent": False, "email_confirmation_tested": False, "public_registration_enabled": False,
        "deployed_host_qualified": bool(args.service_origin) and failure is None and not cleanup_failed,
        "model_calls": 0, "payments_created": False,
        "limitations": ["Administratively confirmed test identities do not qualify email confirmation, recovery or real customer onboarding.",
            "Provider account deletion reconciliation is separate from the tested local subject revocation.",
            "Diagnostic material and protocol retrieval do not prove native harness loading or useful task completion."]}
    encoded = json.dumps(report, indent=2) + "\n"
    if any(value and value in encoded for value in secrets_used):
        raise QualificationFailure("secret_in_report_refused")
    with output.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    print(json.dumps({key: report[key] for key in ("passed", "total", "all_passed", "failure", "cleanup_failed", "unknown_creation_outcome")}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
