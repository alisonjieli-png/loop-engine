"""Offline OAuth domain and pinned SDK controls. No provider calls or real credentials."""
from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator
from mcp.server.auth.provider import AuthorizationParams, AuthorizeError, RefreshToken, RegistrationError, TokenError
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.datastructures import FormData
from starlette.requests import Request

from loop_engine.catalog.protocol import StoreBusy
from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.service_runtime import account_origin
from loop_engine.core.service_runtime.browser_identity import VerifiedIdentity
from loop_engine.core.service_runtime.http_auth import AuthenticatedHttpRequest, BROWSER_IDENTITY_AUTHENTICATION
from loop_engine.core.service_runtime.oauth_authorization import (
    ACCESS, CLIENT, CODE, GRANT, HOSTED_CLIENT_REDIRECTS, LIMITS, OPENAI_CALLBACK_PREFIX, REFRESH, REQUEST,
    OAuthAuthorizationPolicy, OAuthAuthorizationProvider, same_redirect,
)
from loop_engine.core.service_runtime.records import (
    DEFAULT_SCOPES, ServiceCommitUnknown, ServiceRuntimeConfig, ServiceRuntimeError, SubjectBindingRequest, TenantRegistration,
)
from loop_engine.core.service_runtime.runtime import ServiceRuntime
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding


def form_request(fields):
    body = urlencode(fields).encode()
    sent = False
    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}
    return Request({"type": "http", "method": "POST", "path": "/token", "query_string": b"",
                    "headers": [(b"content-type", b"application/x-www-form-urlencoded")], "scheme": "https",
                    "server": ("baltor.example.test", 443)}, receive)


class OAuthAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="oauth-domain-")
        self.addCleanup(self.directory.cleanup)
        self.now = int(time.time())
        self.config = ServiceRuntimeConfig(str(Path(self.directory.name) / "catalog.sqlite"), writes_authorized=True)
        self.runtime = ServiceRuntime(self.config, clock=lambda: self.now)
        self.policy = OAuthAuthorizationPolicy(
            "https://baltor.example.test", "https://baltor.example.test/mcp", "https://identity.example.test/auth/v1",
            "https://baltor.example.test/oauth/consent", redirect_uri_prefixes=(OPENAI_CALLBACK_PREFIX,))
        self.provider = OAuthAuthorizationProvider(self.runtime, self.policy)
        self.runtime.register_tenant(TenantRegistration("synthetic", "synthetic-namespace"))
        self.binding = SubjectBindingRequest("synthetic", self.policy.identity_issuer, "synthetic-subject")
        self.runtime.bind_subject(self.binding)
        account_origin.record_origin(self.runtime, self.policy.identity_issuer, "synthetic-subject", account_origin.SIGNUP_ORIGIN)
        principal = self.runtime.authenticate_subject(self.policy.identity_issuer, "synthetic-subject")
        self.authentication = AuthenticatedHttpRequest(principal, "synthetic-browser-session", BROWSER_IDENTITY_AUTHENTICATION,
            self.now + 3600, DEFAULT_SCOPES, VerifiedIdentity("synthetic-subject", "", account_origin.SIGNUP_ORIGIN))
        self.callback = OPENAI_CALLBACK_PREFIX + "synthetic-callback"
        self.client = OAuthClientInformationFull(client_id="synthetic-client", client_name="Synthetic MCP client",
            token_endpoint_auth_method="none", redirect_uris=[self.callback], scope=" ".join(DEFAULT_SCOPES),
            grant_types=["authorization_code", "refresh_token"], response_types=["code"])
        await self.provider.register_client(self.client)
        self.verifier = "v" * 64
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip("=")

    async def pending(self, scopes=None):
        url = await self.provider.authorize(self.client, AuthorizationParams(state="synthetic-state", scopes=scopes or list(DEFAULT_SCOPES),
            code_challenge=self.challenge, redirect_uri=self.callback, redirect_uri_provided_explicitly=True,
            resource=self.policy.resource_url))
        return parse_qs(urlsplit(url).query)["authorization_id"][0]

    async def code(self, scopes=None):
        redirect = await self.provider.approve_consent(await self.pending(scopes), self.authentication)
        values = parse_qs(urlsplit(redirect).query)
        self.assertEqual(values["state"], ["synthetic-state"])
        self.assertEqual(values["iss"], [self.policy.issuer_url])
        return values["code"][0]

    async def issue(self, scopes=None):
        code = await self.code(scopes)
        loaded = await self.provider.load_authorization_code(self.client, code)
        return await self.provider.exchange_authorization_code(self.client, loaded)

    def rows(self, kind):
        with self.runtime._catalog.store() as store:
            return store.query(IntelligenceQuery(artifact_kinds=(kind,)))

    def token_form(self, code, **changes):
        return {"grant_type": "authorization_code", "client_id": self.client.client_id, "code": code,
                "redirect_uri": self.callback, "code_verifier": self.verifier, "resource": self.policy.resource_url, **changes}

    async def test_consent_issue_and_restart_preserve_exact_subject_scope_resource(self):
        pending = await self.pending()
        description = await self.provider.inspect_consent(pending)
        self.assertEqual(description["resource"], self.policy.resource_url)
        self.assertNotIn("tenant_id", description)
        tokens = await self.issue(["provisioning:metadata"])
        reopened = OAuthAuthorizationProvider(ServiceRuntime(self.config, clock=lambda: self.now), self.policy)
        context = await reopened.access_context(tokens.access_token)
        self.assertEqual(reopened.resolve_access(tokens.access_token).scopes, context.scopes)
        self.assertEqual((context.principal.tenant_id, context.subject, context.resource),
                         ("synthetic", "synthetic-subject", self.policy.resource_url))
        self.assertEqual(context.scopes, ("provisioning:metadata",))
        self.assertEqual(context.principal.entitlement, "metadata", "OAuth does not create a paid entitlement")

    async def test_authorization_rejects_wrong_resource_and_redirect(self):
        params = AuthorizationParams(state="synthetic-state", scopes=list(DEFAULT_SCOPES), code_challenge=self.challenge,
            redirect_uri=self.callback, redirect_uri_provided_explicitly=True, resource="https://wrong.example/mcp")
        with self.assertRaises(AuthorizeError) as caught:
            await self.provider.authorize(self.client, params)
        self.assertEqual(caught.exception.error, "invalid_target")
        params.resource = self.policy.resource_url
        params.redirect_uri = "https://unapproved.example/callback"
        with self.assertRaises(AuthorizeError):
            await self.provider.authorize(self.client, params)

    async def test_registration_refuses_secrets_unapproved_redirects_and_admin_scopes(self):
        for changes in ({"token_endpoint_auth_method": "client_secret_post", "client_secret": "synthetic-client-secret"},
                        {"redirect_uris": ["https://unapproved.example/callback"]}, {"scope": "access:manage"}):
            with self.subTest(fields=list(changes)):
                client = self.client.model_copy(update={"client_id": "other-client", **changes})
                with self.assertRaises(RegistrationError):
                    await self.provider.register_client(client)

    async def test_openai_callback_family_is_one_literal_segment(self):
        for suffix in ("id/child", "id?next=evil", "id#fragment", "%2fmalicious", "", "x" * 129):
            self.assertFalse(self.policy.permits_redirect(OPENAI_CALLBACK_PREFIX + suffix))
        self.assertFalse(self.policy.permits_redirect("https://chatgpt.com.evil.example/connector/oauth/id"))
        self.assertTrue(self.policy.permits_redirect(OPENAI_CALLBACK_PREFIX + "valid_callback-id"))

    async def test_policy_lists_are_copied_and_unsupported_redirect_policies_fail(self):
        scopes = list(DEFAULT_SCOPES)
        policy = replace(self.policy, allowed_scopes=scopes)
        scopes.append("access:manage")
        self.assertNotIn("access:manage", policy.allowed_scopes)
        with self.assertRaises(ServiceRuntimeError):
            replace(policy, redirect_uri_prefixes=("https://unapproved.example/",))
        with self.assertRaises(ServiceRuntimeError):
            replace(policy, issuer_url="https://baltor.example.test:99999")
        with self.assertRaises(ServiceRuntimeError) as version:
            replace(policy, record_type="service_oauth_authorization_policy/v2")
        self.assertEqual(version.exception.code, "unsupported_oauth_policy_version")
        self.assertEqual(OAuthAuthorizationPolicy(**json.loads(json.dumps(policy.to_dict()))), policy)

    async def test_native_loopback_random_ports_keep_literal_hosts_and_paths(self):
        policy = replace(self.policy, native_loopback_paths=("/oauth/callback",))
        for uri in ("http://localhost:31415/oauth/callback", "http://127.0.0.1:65535/oauth/callback",
                    "http://[::1]:48000/oauth/callback", "http://localhost/oauth/callback"):
            self.assertTrue(policy.permits_redirect(uri))
        for uri in ("https://localhost:31415/oauth/callback", "http://localhost.evil.example/oauth/callback",
                    "http://localhost@evil.example/oauth/callback", "http://user@localhost:3000/oauth/callback",
                    "http://@localhost:3000/oauth/callback", "http://localhost:3000/oauth/callback?",
                    "http://localhost:3000/oauth/callback#",
                    "http://127.0.0.2:3000/oauth/callback", "http://192.0.2.1:3000/oauth/callback",
                    "http://[::2]:3000/oauth/callback", "http://localhost:0/oauth/callback",
                    "http://localhost:65536/oauth/callback", "http://localhost:3000/other",
                    "http://localhost:3000/oauth/../callback", "http://localhost:3000/oauth/%2e%2e/callback",
                    "http://localhost:3000/oauth/callback?next=outside", "http://localhost:3000/oauth/callback#fragment",
                    "http://localhost:3000//oauth/callback", "http://localhost:3000/oauth\\callback"):
            self.assertFalse(policy.permits_redirect(uri), "a nonliteral native callback was accepted")
        for path in ("//callback", "/oauth/../callback", "/oauth/%2e%2e/callback", "/callback?next=x"):
            with self.assertRaises(ServiceRuntimeError):
                replace(policy, native_loopback_paths=(path,))

    async def test_documented_hosted_callbacks_are_exact_addresses(self):
        """Each hosted client's callback, as its own documentation names it on October 9, 2026, and nothing near it."""
        from loop_engine.core.service_runtime.oauth_http import client_redirect_policy
        policy = replace(self.policy, **client_redirect_policy())
        self.assertEqual([row[1] for row in HOSTED_CLIENT_REDIRECTS], [
            "https://chatgpt.com/connector_platform_oauth_redirect", "https://claude.ai/api/mcp/auth_callback",
            "https://www.cursor.com/agents/mcp/oauth/callback", "https://vscode.dev/redirect",
            "https://insiders.vscode.dev/redirect"])
        self.assertEqual(policy.redirect_uri_prefixes, (OPENAI_CALLBACK_PREFIX,), "no hosted callback is a prefix")
        # Every row cites a source the guide lists with its address and the digest of the bytes read.
        guide = (Path(__file__).resolve().parents[1] / "docs/guides/chatgpt-app.md").read_text(encoding="utf-8")
        sources = dict(re.findall(r"^\| (S\d+) \| [^|]+ \| <https://[^>\s]+> \| ([0-9a-f]{16}) \|$", guide, re.MULTILINE))
        for client, address, source in HOSTED_CLIENT_REDIRECTS:
            self.assertIn(source, sources, client)
            self.assertTrue(policy.permits_redirect(address), address)
            host, path = urlsplit(address).hostname, urlsplit(address).path
            for wrong in ("http://" + host + path,                                           # http, not https
                          f"https://{host}.evil.example{path}", f"https://evil{host}{path}",  # lookalike hosts
                          f"https://evil.{host}{path}", f"https://evil.example{path}",        # hosts not named
                          f"https://evil.example/{host}{path}", f"https://{host.upper()}{path}",
                          f"https://user@{host}{path}", f"https://{host}@evil.example{path}",  # userinfo tricks
                          f"https://{host}:8443{path}", f"https://{host}:443{path}",           # port tricks
                          f"https://{host}{path}/", f"https://{host}{path}/next", f"https://{host}{path}x",  # paths
                          f"https://{host}{path.rsplit('/', 1)[0]}", f"https://{host}/x/..{path}",
                          f"https://{host}{path}?next=https://evil.example", f"https://{host}{path}#x"):
                self.assertFalse(policy.permits_redirect(wrong), wrong)
        # A further exact OpenAI address from the host file joins the list; it never becomes a prefix either.
        extended = replace(self.policy, **client_redirect_policy(("https://platform.openai.com/apps-manage/oauth",)))
        self.assertTrue(extended.permits_redirect("https://platform.openai.com/apps-manage/oauth"))
        self.assertFalse(extended.permits_redirect("https://platform.openai.com/apps-manage/oauth/x"))
        with self.assertRaises(ServiceRuntimeError, msg="an exact address may not bring a query of its own"):
            replace(self.policy, redirect_uris=("https://claude.ai/api/mcp/auth_callback?iss=x",))

    async def test_loopback_root_path_and_codex_callback_identifier(self):
        from loop_engine.core.service_runtime.oauth_http import client_redirect_policy
        policy = replace(self.policy, **client_redirect_policy())
        # Codex's rule: URL-safe Base64 of the first nine bytes of the SHA-256 of the server address, no padding.
        codex = base64.urlsafe_b64encode(hashlib.sha256(b"https://baltor.ai/mcp").digest()[:9]).decode().rstrip("=")
        self.assertEqual(codex, "F9ZByiiojchq")
        for uri in ("http://127.0.0.1/", "http://127.0.0.1:33418/", "http://127.0.0.1:33418", "http://[::1]:5000/",
                    "http://localhost:5000/", "http://localhost:3118/callback", "http://localhost:8787/callback",
                    "http://127.0.0.1:19876/mcp/oauth/callback", "http://127.0.0.1:53682/callback",
                    "http://127.0.0.1:53682/callback/" + codex, "http://127.0.0.1/callback/" + codex):
            self.assertTrue(policy.permits_redirect(uri), uri)
        for uri in ("http://127.0.0.1:33418//", "http://127.0.0.1:33418/?", "http://127.0.0.1:33418/?x=1",
                    "http://127.0.0.1:33418/#", "https://127.0.0.1:33418/", "http://127.0.0.2:33418/",
                    "http://user@127.0.0.1:33418/", "http://127.0.0.1@evil.example/", "http://127.0.0.1:0/",
                    "http://127.0.0.1:65536/", "http://127.0.0.1.evil.example/", "http://localhost.evil.example:5000/",
                    "http://127.0.0.1:53682/callback/" + codex[:-1], "http://127.0.0.1:53682/callback/" + codex + "X",
                    "http://127.0.0.1:53682/callback/F9ZByiio$chq", "http://127.0.0.1:53682/callback/" + codex + "/",
                    "http://127.0.0.1:53682/callback/" + codex + "/x", "http://127.0.0.1:53682/callbacks/" + codex,
                    "http://127.0.0.1:53682/oauth/callback/" + codex, "http://127.0.0.1:53682/x/callback/" + codex,
                    "http://127.0.0.1:53682/" + codex, "http://127.0.0.1:53682/callback/" + codex + "?x=1",
                    "http://127.0.0.1:53682/callback/" + codex + "#x", "https://127.0.0.1:53682/callback/" + codex,
                    "http://evil.example/callback/" + codex, "http://127.0.0.1:53682/callback%2F" + codex,
                    "http://127.0.0.1:53682/callback/%2e%2e%2fabcdef", "http://127.0.0.1:53682//callback/" + codex):
            self.assertFalse(policy.permits_redirect(uri), uri)
        # Known wrong: the rules main served before October 9 refused VS Code's root, Codex's identifier and Claude.
        before = replace(self.policy, native_loopback_paths=("/callback", "/oauth/callback", "/auth/callback",
                                                             "/mcp/oauth/callback"))
        for uri in ("http://127.0.0.1:33418/", "http://127.0.0.1:53682/callback/" + codex,
                    "https://claude.ai/api/mcp/auth_callback"):
            self.assertFalse(before.permits_redirect(uri), uri)
        for paths in (("/",), ("/callback/",), ("callback",), ("/a/../callback",), ("/a//callback",), ("",)):
            with self.assertRaises(ServiceRuntimeError, msg=str(paths)):
                replace(policy, native_loopback_callback_id_paths=paths)

    async def test_a_loopback_redirect_matches_on_any_port_and_on_nothing_else(self):
        from mcp.shared.auth import InvalidRedirectUriError
        from pydantic import AnyUrl
        from loop_engine.core.service_runtime.oauth_http import client_redirect_policy
        for requested, registered in (("http://127.0.0.1:51004/", "http://127.0.0.1/"),
                                      ("http://127.0.0.1:51004/", "http://127.0.0.1:33418/"),
                                      ("http://127.0.0.1:51004/", "http://127.0.0.1:33418"),
                                      ("http://localhost:4000/callback", "http://localhost:3118/callback"),
                                      ("http://[::1]:4000/callback", "http://[::1]/callback"),
                                      (AnyUrl("http://127.0.0.1:51004/"), AnyUrl("http://127.0.0.1/")),
                                      ("https://claude.ai/api/mcp/auth_callback", "https://claude.ai/api/mcp/auth_callback")):
            self.assertTrue(same_redirect(requested, registered), requested)
        for requested, registered in (("http://127.0.0.1:51004/other", "http://127.0.0.1/"),
                                      ("http://localhost:51004/", "http://127.0.0.1/"),
                                      ("http://[::1]:51004/", "http://127.0.0.1/"),
                                      ("http://127.0.0.2:51004/", "http://127.0.0.2/"),
                                      ("https://127.0.0.1:51004/", "https://127.0.0.1/"),
                                      ("https://vscode.dev:8443/redirect", "https://vscode.dev/redirect"),
                                      ("https://claude.ai:443/api/mcp/auth_callback", "https://claude.ai/api/mcp/auth_callback"),
                                      ("http://127.0.0.1:51004/?x=1", "http://127.0.0.1/"),
                                      ("http://user@127.0.0.1:51004/", "http://127.0.0.1/"),
                                      ("http://127.0.0.1:0/", "http://127.0.0.1/"),
                                      ("http://127.0.0.1:51004/callback/" + "A" * 12, "http://127.0.0.1/callback/" + "B" * 12)):
            self.assertFalse(same_redirect(requested, registered), requested)
        # A client registered the way VS Code registers is authorized on the port its listener took.
        provider = OAuthAuthorizationProvider(self.runtime, replace(self.policy, **client_redirect_policy()))
        vscode = self.client.model_copy(update={"client_id": "vscode-client", "client_name": "Visual Studio Code",
            "redirect_uris": ["https://insiders.vscode.dev/redirect", "https://vscode.dev/redirect", "http://127.0.0.1/",
                              "http://127.0.0.1:33418/"]})
        await provider.register_client(vscode)
        held = await provider.get_client("vscode-client")
        listening = AnyUrl("http://127.0.0.1:51004/")
        self.assertEqual(held.validate_redirect_uri(listening), listening)
        with self.assertRaises(InvalidRedirectUriError, msg="known wrong: the SDK's exact comparison refuses the port"):
            OAuthClientInformationFull.validate_redirect_uri(held, listening)
        for wrong in ("http://127.0.0.1:51004/other", "http://localhost:51004/", "https://vscode.dev:8443/redirect"):
            with self.assertRaises(InvalidRedirectUriError, msg=wrong):
                held.validate_redirect_uri(AnyUrl(wrong))
        url = await provider.authorize(held, AuthorizationParams(state="synthetic-state", scopes=list(DEFAULT_SCOPES),
            code_challenge=self.challenge, redirect_uri=listening, redirect_uri_provided_explicitly=True,
            resource=self.policy.resource_url))
        redirect = await provider.approve_consent(parse_qs(urlsplit(url).query)["authorization_id"][0], self.authentication)
        self.assertTrue(redirect.startswith("http://127.0.0.1:51004/?"), redirect)
        self.assertEqual(parse_qs(urlsplit(redirect).query)["iss"], [self.policy.issuer_url])
        with self.assertRaises(AuthorizeError, msg="a path the client did not register"):
            await provider.authorize(held, AuthorizationParams(state="synthetic-state", scopes=list(DEFAULT_SCOPES),
                code_challenge=self.challenge, redirect_uri=AnyUrl("http://127.0.0.1:51004/other"),
                redirect_uri_provided_explicitly=True, resource=self.policy.resource_url))

    async def test_consent_is_explicit_single_use_and_denial_mints_no_code(self):
        pending = await self.pending()
        before = len(self.rows(CODE))
        redirect = await self.provider.deny_consent(pending, self.authentication)
        self.assertEqual(parse_qs(urlsplit(redirect).query)["error"], ["access_denied"])
        self.assertEqual(parse_qs(urlsplit(redirect).query)["iss"], [self.policy.issuer_url])
        self.assertEqual(len(self.rows(CODE)), before)
        with self.assertRaises(AuthorizeError):
            await self.provider.approve_consent(pending, self.authentication)

    async def test_service_key_or_expired_browser_cannot_approve(self):
        for auth in (replace(self.authentication, mode="host_key"), replace(self.authentication, expires_at=self.now)):
            with self.assertRaises(AuthorizeError):
                await self.provider.approve_consent(await self.pending(), auth)

    async def test_revoked_browser_session_cannot_approve_pending_request(self):
        pending = await self.pending()
        self.runtime.revoke_browser_session(self.authentication.principal,
            hashlib.sha256(self.authentication.credential.encode()).hexdigest(), self.now + 3600)
        with self.assertRaises(AuthorizeError):
            await self.provider.approve_consent(pending, self.authentication)

    async def test_pending_and_code_expiry_are_inclusive(self):
        pending = await self.pending()
        self.now += self.policy.authorization_lifetime_seconds
        with self.assertRaises(AuthorizeError):
            await self.provider.inspect_consent(pending)
        code = await self.code()
        self.now += self.policy.code_lifetime_seconds
        self.assertIsNone(await self.provider.load_authorization_code(self.client, code))

    async def test_single_use_code_and_client_binding(self):
        raw = await self.code()
        wrong = self.client.model_copy(update={"client_id": "other-client"})
        self.assertIsNone(await self.provider.load_authorization_code(wrong, raw))
        code = await self.provider.load_authorization_code(self.client, raw)
        await self.provider.exchange_authorization_code(self.client, code)
        self.assertIsNone(await self.provider.load_authorization_code(self.client, raw))
        with self.assertRaises(TokenError):
            await self.provider.exchange_authorization_code(self.client, code)
        self.assertEqual(len(self.rows(GRANT)), 1)

    async def test_atomic_racing_exchanges_create_one_grant(self):
        code = await self.provider.load_authorization_code(self.client, await self.code())
        outcomes = await asyncio.gather(self.provider.exchange_authorization_code(self.client, code),
                                        self.provider.exchange_authorization_code(self.client, code), return_exceptions=True)
        self.assertEqual(sum(isinstance(value, OAuthToken) for value in outcomes), 1)
        self.assertEqual(len(self.rows(GRANT)), 1)

    async def test_refresh_rotates_and_cannot_expand_scope(self):
        first = await self.issue(["provisioning:metadata"])
        refresh = await self.provider.load_refresh_token(self.client, first.refresh_token)
        with self.assertRaises(TokenError):
            await self.provider.exchange_refresh_token(self.client, refresh, ["provisioning:read"])
        second = await self.provider.exchange_refresh_token(self.client, refresh, ["provisioning:metadata"])
        self.assertIsNone(await self.provider.load_refresh_token(self.client, first.refresh_token))
        self.assertIsNone(await self.provider.load_access_token(first.access_token))
        self.assertIsNotNone(await self.provider.load_access_token(second.access_token))
        with self.assertRaises(TokenError):
            await self.provider.exchange_refresh_token(self.client, refresh, ["provisioning:metadata"])

    async def test_revocation_covers_access_and_refresh(self):
        tokens = await self.issue()
        await self.provider.revoke_token(await self.provider.load_access_token(tokens.access_token))
        self.assertIsNone(await self.provider.load_access_token(tokens.access_token))
        self.assertIsNone(await self.provider.load_refresh_token(self.client, tokens.refresh_token))

    async def test_disabled_tenant_or_subject_is_refused_on_each_access(self):
        tokens = await self.issue()
        self.runtime.set_tenant_enabled("synthetic", False)
        self.assertIsNone(await self.provider.load_access_token(tokens.access_token))
        self.runtime.set_tenant_enabled("synthetic", True)
        self.runtime.revoke_subject(self.binding)
        self.assertIsNone(await self.provider.load_access_token(tokens.access_token))
        self.assertIsNone(await self.provider.load_refresh_token(self.client, tokens.refresh_token))

    async def test_origin_record_is_required_after_issuance(self):
        tokens = await self.issue()
        original = self.runtime._catalog.read
        def without_origin(store, kind, identity):
            return None if kind == account_origin.ORIGIN else original(store, kind, identity)
        with mock.patch.object(ServiceCatalogBinding, "read", lambda binding, store, kind, identity: without_origin(store, kind, identity)):
            self.assertIsNone(await self.provider.load_access_token(tokens.access_token))

    async def test_raw_credentials_are_not_persisted(self):
        code = await self.code()
        loaded = await self.provider.load_authorization_code(self.client, code)
        tokens = await self.provider.exchange_authorization_code(self.client, loaded)
        with self.runtime._catalog.store() as store:
            records = json.dumps(store.query(IntelligenceQuery()))
        for raw in (code, tokens.access_token, tokens.refresh_token, self.authentication.credential):
            self.assertFalse(raw in records, "raw credential reached a persistent record")

    async def test_unknown_commit_returns_no_tokens_and_consumed_code_is_not_replayed(self):
        code = await self.provider.load_authorization_code(self.client, await self.code())
        original = ServiceCatalogBinding.commit
        def lose_ack(binding, store, records, guards, removals=()):
            result = original(binding, store, records, guards, removals)
            if any(row['artifact_kind'] == GRANT for row in records):
                raise ServiceCommitUnknown()
            return result
        with mock.patch.object(ServiceCatalogBinding, "commit", lose_ack):
            with self.assertRaises(ServiceCommitUnknown):
                await self.provider.exchange_authorization_code(self.client, code)
        self.assertEqual(len(self.rows(GRANT)), 1)
        with self.assertRaises(TokenError):
            await self.provider.exchange_authorization_code(self.client, code)

    async def test_a_committed_refresh_is_delivered_while_another_authorization_commits(self):
        """Known wrong (October 5 review, N1): an authorization that committed the shared counter between a refresh's
        commit and its read-back made the refresh answer commit_unknown after the old token pair had rotated away."""
        tokens = await self.issue()
        loaded = await self.provider.load_refresh_token(self.client, tokens.refresh_token)
        params = AuthorizationParams(state="synthetic-state", scopes=list(DEFAULT_SCOPES), code_challenge=self.challenge,
            redirect_uri=self.callback, redirect_uri_provided_explicitly=True, resource=self.policy.resource_url)
        state, outcomes = {"victim": None, "armed": False, "other": None}, []
        def other_authorization():
            try:
                asyncio.run(self.provider.authorize(self.client, params))
                outcomes.append("authorized")
            except ServiceRuntimeError as error:
                outcomes.append(error.code)
        real_apply, real_get = SQLiteRecordStore.apply_batch, SQLiteRecordStore.get
        def apply_batch(store, batch):
            acknowledgment = real_apply(store, batch)
            if state["other"] is None and state["victim"] in (None, threading.current_thread()):
                state["victim"], state["armed"] = threading.current_thread(), True
            return acknowledgment
        def get(store, identity, version=None):
            if state["armed"] and threading.current_thread() is state["victim"]:
                state["armed"], state["other"] = False, threading.Thread(target=other_authorization)
                state["other"].start()
                state["other"].join(timeout=0.5)
            return real_get(store, identity, version)
        with mock.patch.object(SQLiteRecordStore, "apply_batch", apply_batch), mock.patch.object(SQLiteRecordStore, "get", get):
            refreshed = await self.provider.exchange_refresh_token(self.client, loaded, list(DEFAULT_SCOPES))
            await asyncio.to_thread(state["other"].join, 10)
        self.assertEqual(outcomes, ["authorized"])
        self.assertIsNone(await self.provider.load_refresh_token(self.client, tokens.refresh_token))
        self.assertIsNotNone(await self.provider.load_refresh_token(self.client, refreshed.refresh_token))
        self.assertIsNotNone(await self.provider.load_access_token(refreshed.access_token))

    def params(self):
        return AuthorizationParams(state="synthetic-state", scopes=list(DEFAULT_SCOPES), code_challenge=self.challenge,
            redirect_uri=self.callback, redirect_uri_provided_explicitly=True, resource=self.policy.resource_url)

    def counter(self):
        with self.runtime._catalog.store() as store:
            return self.provider._read(store, LIMITS, self.provider.policy_id)[1]

    def stored(self):
        return {kind: len(self.rows(kind)) for kind in (CLIENT, REQUEST, CODE, GRANT, ACCESS, REFRESH)}

    def staged(self, other):
        """Patch the commit so that the first write to commit first runs `other` on another thread (joined for 0.5 s)."""
        state = {"victim": None, "thread": None}
        original = ServiceCatalogBinding.commit
        def commit(binding, *args, **kwargs):
            if state["victim"] is None:
                state["victim"], state["thread"] = threading.current_thread(), threading.Thread(target=other)
                state["thread"].start()
                state["thread"].join(timeout=0.5)
            return original(binding, *args, **kwargs)
        return mock.patch.object(ServiceCatalogBinding, "commit", commit), state

    async def test_an_oauth_write_waits_for_another_clients_write_instead_of_refusing(self):
        """Known wrong (October 5 review, c): every OAuth write that adds records read the one counter row outside any
        lock and committed under its version guard with no retry, so a write that another write overtook answered 409
        concurrent_update: 186 of 200 concurrent authorizations and 29 of 32 refreshes of different grants."""
        tokens = await self.issue()
        loaded = await self.provider.load_refresh_token(self.client, tokens.refresh_token)
        for name, write in (("authorization", lambda: self.provider.authorize(self.client, self.params())),
                            ("refresh", lambda: self.provider.exchange_refresh_token(self.client, loaded, list(DEFAULT_SCOPES)))):
            with self.subTest(write=name):
                outcomes = []
                def other_authorization():
                    try:
                        asyncio.run(self.provider.authorize(self.client, self.params()))
                        outcomes.append("authorized")
                    except ServiceRuntimeError as error:
                        outcomes.append(error.code)
                patched, state = self.staged(other_authorization)
                with patched:
                    await write()
                    await asyncio.to_thread(state["thread"].join, 10)
                self.assertEqual(outcomes, ["authorized"])
        self.assertEqual(self.counter()["records"], sum(self.stored().values()))

    async def test_concurrent_authorizations_and_refreshes_of_different_grants_all_succeed(self):
        from concurrent.futures import ThreadPoolExecutor
        issued = [await self.issue() for _ in range(16)]
        asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(16))
        async def refresh(tokens):
            loaded = await self.provider.load_refresh_token(self.client, tokens.refresh_token)
            return await self.provider.exchange_refresh_token(self.client, loaded, list(DEFAULT_SCOPES))
        outcomes = await asyncio.gather(*(self.provider.authorize(self.client, self.params()) for _ in range(64)),
                                        *(refresh(tokens) for tokens in issued), return_exceptions=True)
        self.assertEqual([type(value).__name__ for value in outcomes if isinstance(value, BaseException)], [])
        self.assertEqual(self.counter()["records"], sum(self.stored().values()))

    async def test_read_contention_is_not_invalid_token(self):
        tokens = await self.issue()
        with mock.patch.object(SQLiteRecordStore, "get", side_effect=StoreBusy("synthetic busy read")):
            with self.assertRaises(ServiceRuntimeError) as caught:
                await self.provider.load_access_token(tokens.access_token)
        self.assertEqual(caught.exception.code, "store_busy")

    async def test_storage_ceiling_refuses_before_new_request(self):
        constrained = OAuthAuthorizationProvider(self.runtime, replace(self.policy, max_records=1, max_clients=1))
        before = len(self.rows(GRANT))
        with self.assertRaises(ServiceRuntimeError) as caught:
            await constrained.authorize(self.client, AuthorizationParams(state="synthetic-state", scopes=list(DEFAULT_SCOPES),
                code_challenge=self.challenge, redirect_uri=self.callback, redirect_uri_provided_explicitly=True,
                resource=self.policy.resource_url))
        self.assertEqual(caught.exception.code, "oauth_storage_limit")
        self.assertEqual(len(self.rows(GRANT)), before)

    async def test_dead_rows_free_capacity_and_the_counter_counts_what_is_stored(self):
        """Known wrong (October 5 review, a): the counter only ever grew. At a 12-record ceiling the third
        authorization was refused, so was a refresh of a valid grant, and after every grant was revoked and expired,
        new authorizations stayed refused for good with every dead row still stored."""
        self.provider = OAuthAuthorizationProvider(self.runtime, replace(self.policy, max_records=12, max_clients=2))
        issued = [await self.issue() for _ in range(3)]
        tokens = issued[0]
        for _ in range(3):  # At the ceiling, each refresh frees the pair it replaces.
            loaded = await self.provider.load_refresh_token(self.client, tokens.refresh_token)
            tokens = await self.provider.exchange_refresh_token(self.client, loaded, list(DEFAULT_SCOPES))
        self.assertIsNotNone(await self.provider.load_access_token(tokens.access_token))
        self.assertEqual(self.counter()["records"], sum(self.stored().values()))
        self.assertEqual(self.counter()["records"], 10)
        for held in (tokens, *issued[1:]):
            await self.provider.revoke_token(RefreshToken(token=held.refresh_token, client_id=self.client.client_id,
                                                          scopes=list(DEFAULT_SCOPES), expires_at=None))
        self.now += self.policy.refresh_lifetime_seconds + 1
        self.authentication = replace(self.authentication, expires_at=self.now + 3600)
        fresh = await self.issue()
        self.assertIsNotNone(await self.provider.load_access_token(fresh.access_token))
        self.assertEqual(self.stored(), {CLIENT: 1, REQUEST: 0, CODE: 1, GRANT: 1, ACCESS: 1, REFRESH: 1})
        self.assertEqual(self.counter(), {**self.counter(), "records": 5, "clients": 1})

    async def test_unused_dynamic_clients_free_registration_after_their_first_authorization_lifetime(self):
        """Known wrong (October 5 review, a): every registration counted for good, so anonymous /register at 10 a
        minute closed registration permanently after max_clients (128) clients, still refused ten years later."""
        self.provider = OAuthAuthorizationProvider(self.runtime, replace(self.policy, max_clients=4))
        def client(name):
            return self.client.model_copy(update={"client_id": name})
        connected = await self.issue()
        for name in ("pending-client", "idle-1", "idle-2"):
            await self.provider.register_client(client(name))
        self.now += 10
        with self.assertRaises(ServiceRuntimeError) as full:  # Every other client is new or holds a live grant.
            await self.provider.register_client(client("refused"))
        self.assertEqual(full.exception.code, "oauth_storage_limit")
        self.now += self.policy.authorization_lifetime_seconds - 20
        await self.provider.authorize(client("pending-client"), self.params())
        self.now += 100
        await self.provider.register_client(client("later"))
        present = {name: await self.provider.get_client(name) is not None
                   for name in ("synthetic-client", "pending-client", "idle-1", "idle-2", "later")}
        self.assertEqual(present, {"synthetic-client": True, "pending-client": True, "idle-1": False, "idle-2": False, "later": True})
        self.assertEqual(self.counter()["clients"], 3)
        await self.provider.register_client(self.client)  # The same metadata again is the same client.
        self.assertEqual((self.counter()["clients"], len(self.rows(CLIENT))), (3, 3))
        loaded = await self.provider.load_refresh_token(self.client, connected.refresh_token)
        self.assertIsNotNone(await self.provider.exchange_refresh_token(self.client, loaded, list(DEFAULT_SCOPES)))

    async def test_a_removal_pass_that_finds_no_room_waits_in_proportion_to_what_it_read(self):
        from loop_engine.core.service_runtime import oauth_authorization as oauth
        constrained = OAuthAuthorizationProvider(self.runtime, replace(self.policy, max_records=1, max_clients=1))
        scans = []
        original = ServiceCatalogBinding.rows
        def rows(binding, store, kind, tenant_id):
            scans.append(kind)
            return original(binding, store, kind, tenant_id)
        async def refused():
            with self.assertRaises(ServiceRuntimeError) as caught:
                await constrained.authorize(self.client, self.params())
            self.assertEqual(caught.exception.code, "oauth_storage_limit")
            return len(scans)
        with mock.patch.object(ServiceCatalogBinding, "rows", rows):
            first = await refused()
            self.assertGreater(first, 0, "a write at the ceiling looks for rows it can remove")
            self.assertEqual(await refused(), 2 * first, "reading one row is cheap enough to repeat at once")
            with mock.patch.object(oauth, "RECLAIM_RETRY_SECONDS_PER_ROW", 30):  # The cost of 10,000 rows, for one.
                third = await refused()
                self.now += 29
                fourth = await refused()
                self.now += 1
                fifth = await refused()
        self.assertEqual((third, fourth, fifth), (3 * first, 3 * first, 4 * first))

    async def test_sdk_pkce_and_redirect_controls_before_domain_exchange(self):
        raw = await self.code()
        handler = TokenHandler(self.provider, ClientAuthenticator(self.provider))
        for changes in ({"code_verifier": "w" * 64}, {"redirect_uri": OPENAI_CALLBACK_PREFIX + "other"}):
            fields = self.token_form(raw, **changes)
            self.provider.validate_token_request(fields)
            response = await handler.handle(form_request(fields))
            self.assertEqual(response.status_code, 400)
        fields = self.token_form(raw)
        self.provider.validate_token_request(fields)
        self.assertEqual((await handler.handle(form_request(fields))).status_code, 200)

    async def test_resource_guard_rejects_missing_wrong_and_duplicate_fields(self):
        raw = await self.code()
        fields = self.token_form(raw)
        for form in ({key: value for key, value in fields.items() if key != "resource"},
                     {**fields, "resource": "https://wrong.example/mcp"},
                     FormData([*fields.items(), ("resource", self.policy.resource_url)])):
            with self.assertRaises(TokenError):
                self.provider.validate_token_request(form)
        self.assertEqual(len(self.rows(GRANT)), 0)
        with self.assertRaises(TokenError) as unsupported:
            await self.provider.exchange_identity_assertion(self.client, None)
        self.assertEqual(unsupported.exception.error, "unsupported_grant_type")

    async def test_known_wrong_unwrapped_sdk_ignores_token_resource(self):
        fields = self.token_form(await self.code(), resource="https://wrong.example/mcp")
        with self.assertRaises(TokenError):
            self.provider.validate_token_request(fields)
        # This pins the observed SDK 2.2.0 gap and proves why the mandatory wrapper matters.
        response = await TokenHandler(self.provider, ClientAuthenticator(self.provider)).handle(form_request(fields))
        self.assertEqual(response.status_code, 200, "reassess the wrapper when the SDK fixes resource validation")


if __name__ == "__main__":
    unittest.main()
