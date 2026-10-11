"""Selected-file delivery must finish integrity/authority checks before paid usage.

Real HTTP and MCP hit the same native service/usage store and signed loopback
object-store engine. Every failure starts with a fresh synthetic account; a
prior month's/item's idempotent charge cannot conceal premature metering.
"""
from dataclasses import replace
import asyncio
import base64
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import time
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import httpx

from loop_engine.core.service_runtime.catalogue_release_checks import Fixture, bundle_line
from loop_engine.core.service_runtime.catalogue_releases import publish
from loop_engine.core.service_runtime.catalogue_object_store import ObjectStoreBodyStore
from loop_engine.core.service_runtime.http import TIERED_PROVISIONING_REQUEST_VERSION
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.object_store_fake import ObjectStoreFake
from loop_engine.core.service_runtime.runtime import USAGE

BODY = b"SELECTED_FILE_CONTENT_IS_PRIVATE_TO_THE_AUTHORIZED_FIXTURE\n"
OTHER = b"another exact package file\n"
IDENTITY, SELECTED = "selected.reference", "SKILL.md"


def protocol_message(response):
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        lines = [line[5:].strip() for line in response.text.splitlines() if line.startswith("data:")]
        return json.loads(lines[-1]) if lines else {}
    return response.json()


class SelectedFileDelivery(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory(prefix="selected-file-delivery-")
        self.addCleanup(self.folder.cleanup)
        self.case = Fixture(Path(self.folder.name))
        self.tenant = "alpha"
        line = bundle_line(IDENTITY, [(SELECTED, BODY, "text/markdown", "skill_definition"),
                                     ("notes.txt", OTHER, "text/plain", "other")])
        self.bundle = self.case.bundle([line], payloads=(BODY, OTHER))
        publish(self.case.context, self.bundle)
        self.fake = ObjectStoreFake(access_key_id="BALTORLOCALTEST", secret_access_key="synthetic-loopback-only",
                                    bucket="selected-file-test").start()
        self.addCleanup(self.fake.close)
        self.remote = ObjectStoreBodyStore(self.fake.endpoint, "selected-file-test",
            access_key_id_ref="env:LOCAL_TEST_ID", secret_access_key_ref="env:LOCAL_TEST_SECRET",
            secret_resolver={"env:LOCAL_TEST_ID": "BALTORLOCALTEST",
                             "env:LOCAL_TEST_SECRET": "synthetic-loopback-only"}.__getitem__)
        self.addCleanup(self.remote.close)
        view = self.case.view()
        self.package = view.package_of(IDENTITY)
        for entry, payload in zip(self.package.files, (BODY, OTHER)):
            self.fake.objects[self.remote.object_key(entry.digest)] = payload
        self.view = replace(view, body_store=self.remote)
        self.served = type("Served", (), {"runtime": self.case.runtime,
                                           "provisioning": self.case.binding(self.view)})()

    def usage(self):
        with self.case.runtime._catalog.store() as store:
            return len(self.case.runtime._catalog.rows(store, USAGE, self.tenant))

    def request(self, client, transport, **changes):
        fields = {"identity": IDENTITY, "path": SELECTED, "expected_digest": self.package.served_digest,
                  "request_id": "selected-file-" + transport, "authority_effects": [], **changes}
        if fields.get("path") is None:
            fields.pop("path")
        headers = {"Authorization": "Bearer " + self.case.key.key}
        if transport == "http":
            response = client.post("/api/v1/download", headers=headers, json={
                "record_type": TIERED_PROVISIONING_REQUEST_VERSION, "operation": "read", **fields})
            success = response.status_code == 200
            answer = {} if success else response.json()
            return response, success, response.content if success else None, answer.get("error", {}).get("code")
        headers.update({"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2026-07-28",
                        "Mcp-Method": "tools/call", "Mcp-Name": "provisioning_read"})
        response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "provisioning_read", "arguments": fields,
                       "_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                                 "io.modelcontextprotocol/clientCapabilities": {}}}})
        message = protocol_message(response)
        answer = message.get("result", {}).get("structuredContent", {})
        success = response.status_code == 200 and "result" in answer and not message.get("result", {}).get("isError")
        files = answer.get("result", {}).get("files", [])
        body = files[0]["content"].encode() if success and files else None
        return response, success, body, answer.get("error", {}).get("code") or message.get("error", {}).get("code")

    def failure_before_meter(self, transport, fault):
        if fault == "corrupt":
            entry = self.package.file(SELECTED)
            self.fake.objects[self.remote.object_key(entry.digest)] = b"!" * len(BODY)
            expected_code = "body_digest_mismatch"
        else:
            original = self.remote._request
            def revoke_after_read(*args, **kwargs):
                result = original(*args, **kwargs)
                self.case.runtime.revoke_key("alpha", self.case.key.key_id)
                return result
            self.remote._request = revoke_after_read
            expected_code = "unauthorized"
        self.assertEqual(self.usage(), 0)
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            response, success, body, code = self.request(client, transport)
        self.assertFalse(success)
        self.assertIsNone(body)
        self.assertNotIn(BODY, response.content)
        self.assertNotIn(b"!" * 30, response.content)
        self.assertEqual(self.usage(), 0, "Failed selected-file delivery consumed a paid unit")
        self.assertEqual(code, expected_code)
        self.assertEqual(self.fake.count("GET"), 1)

    def test_http_corrupt_file_has_no_paid_unit(self):
        self.failure_before_meter("http", "corrupt")

    def test_mcp_corrupt_file_has_no_paid_unit(self):
        self.failure_before_meter("mcp", "corrupt")

    def test_http_key_revoked_during_file_read_has_no_paid_unit(self):
        self.failure_before_meter("http", "revoke")

    def test_mcp_key_revoked_during_file_read_has_no_paid_unit(self):
        self.failure_before_meter("mcp", "revoke")

    def test_successful_http_and_mcp_are_exact_and_meter_once(self):
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            for transport in ("http", "mcp", "http"):
                response, success, body, code = self.request(client, transport)
                self.assertTrue(success, code)
                self.assertEqual(body, BODY)
                self.assertEqual(self.usage(), 1)
                if transport == "mcp":
                    record = protocol_message(response)["result"]["structuredContent"]["result"]
                    self.assertIs(record["metering_acknowledgment"]["committed"], True,
                                  "A response-size preview must never escape as a real acknowledgment")
        self.assertEqual(self.fake.count("GET"), 3)

    def test_wrong_parent_and_missing_path_are_refused_without_body_work(self):
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            for transport in ("http", "mcp"):
                for fields in ({"expected_digest": "f" * 64}, {"path": "missing.txt"}):
                    _response, success, body, code = self.request(client, transport, **fields)
                    self.assertFalse(success)
                    self.assertIsNone(body)
                    self.assertIn(code, ("item_unavailable", "package_file_not_found"))
                    self.assertEqual(self.usage(), 0)
        self.assertEqual(self.fake.count("GET"), 0)

    def test_mcp_page_integrity_failure_withholds_earlier_files_without_metering(self):
        later = self.package.file("notes.txt")
        self.fake.objects[self.remote.object_key(later.digest)] = b"!" * len(OTHER)
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            response, success, body, code = self.request(client, "mcp", path=None, file_offset=0)
        self.assertFalse(success)
        self.assertIsNone(body)
        self.assertEqual(code, "body_digest_mismatch")
        self.assertNotIn(BODY.decode(), response.text)
        self.assertEqual(self.fake.count("GET"), 2)
        self.assertEqual(self.usage(), 0)

    def test_oversize_selected_http_file_refuses_before_storage_work(self):
        big = BODY * 200
        line = bundle_line(IDENTITY, [(SELECTED, big, "text/markdown", "skill_definition"),
                                     ("notes.txt", OTHER, "text/plain", "other")])
        bundle = self.case.bundle([line], payloads=(big, OTHER))
        publish(self.case.context, bundle, expected_release=self.view.release_id)
        view = replace(self.case.view(), body_store=self.remote)
        self.package = view.package_of(IDENTITY)
        self.served.provisioning.install_view(view)
        self.assertLess(self.package.served_size, 1024)
        with running_http(self.served, maximum_download_bytes=1024, maximum_inline_body_bytes=1024) as (origin, _service), \
                httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            response, success, body, code = self.request(client, "http")
        self.assertFalse(success)
        self.assertIsNone(body)
        self.assertEqual((response.status_code, code), (413, "download_limit_exceeded"))
        self.assertEqual(self.fake.count("GET"), 0)
        self.assertEqual(self.usage(), 0)

    def test_free_access_and_exhausted_quota_keep_paid_units_zero(self):
        from loop_engine.core.provisioning_server import ProvisioningItemBinding
        from loop_engine.core.service_runtime.public_good import PublicGoodGrant, PublicGoodLimits
        from loop_engine.core.service_runtime.access import (
            ServiceAccessAdministration, ServiceAccessRequest, ServiceAccessSession, ServiceClientAccessPolicy,
        )
        from loop_engine.core.service_runtime.records import DEFAULT_SCOPES, SubjectTenantRegistration
        binding = ProvisioningItemBinding.from_item(self.view.catalogue.items[IDENTITY])
        grant = PublicGoodGrant(binding, self.view.item_versions[IDENTITY],
            self.view.qualification_resolver.resolve(binding).approval_ref, "synthetic-rights", (4,),
            "Synthetic selected-file quota proof", int(time.time()) + 120, useful_paths=(SELECTED,))
        self.served.provisioning.public_good.configure(self.view, (grant,), limits=PublicGoodLimits(requests_per_window=1))
        # A genuinely unpaid account, not an operator-revoked one: a free
        # overlay must not silently undo an explicit access revocation.
        issuer, subject = "https://identity.example.test/auth/v1", "free-selected-subject"
        self.case.runtime.ensure_subject_tenant(SubjectTenantRegistration(issuer, subject, "customer",
                                                                          follows_active_release=True))
        principal = self.case.runtime.authenticate_subject(issuer, subject)
        self.tenant = principal.tenant_id
        session = ServiceAccessSession(principal.authentication_record_id, hashlib.sha256(subject.encode()).hexdigest(),
                                       int(time.time()) + 3600, DEFAULT_SCOPES)
        access = ServiceAccessAdministration(self.case.runtime, ServiceClientAccessPolicy(writes_authorized=True))
        issued = access.apply(principal, ServiceAccessRequest("issue", "synthetic-free-key", self.tenant,
            label="Synthetic free account", scopes=DEFAULT_SCOPES, lifetime_seconds=3600), session=session)
        self.case.key = SimpleNamespace(key=issued["token"])
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            _response, success, body, code = self.request(client, "http")
            self.assertTrue(success, code)
            self.assertEqual(body, BODY)
            self.assertEqual(self.fake.count("GET"), 1)
            _response, success, body, code = self.request(client, "mcp", request_id="next-free-request")
            self.assertFalse(success)
            self.assertIsNone(body)
            self.assertEqual(code, "public_good_rate_limited")
        self.assertEqual(self.fake.count("GET"), 1)
        self.assertEqual(self.usage(), 0)

    def test_actor_disabled_during_storage_read_has_no_unit(self):
        original = self.remote._request
        def disable_after_read(*args, **kwargs):
            result = original(*args, **kwargs)
            self.case.runtime.set_tenant_enabled("alpha", False)
            return result
        self.remote._request = disable_after_read
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            response, success, body, code = self.request(client, "http")
        self.assertFalse(success)
        self.assertIsNone(body)
        self.assertEqual(code, "unauthorized")
        self.assertNotIn(BODY, response.content)
        self.assertEqual(self.usage(), 0)

    def test_post_commit_revocation_withholds_bytes_without_faking_a_refund(self):
        original = self.case.runtime.record_usage
        def revoke_after_commit(*args, **kwargs):
            acknowledgement = original(*args, **kwargs)
            self.case.runtime.revoke_key("alpha", self.case.key.key_id)
            return acknowledgement
        with mock.patch.object(self.case.runtime, "record_usage", side_effect=revoke_after_commit):
            with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
                response, success, body, code = self.request(client, "http")
        self.assertFalse(success)
        self.assertIsNone(body)
        self.assertEqual(code, "unauthorized")
        self.assertNotIn(BODY, response.content)
        self.assertEqual(self.usage(), 1, "An actually committed unit must not be reported as absent")

    def test_unknown_commit_withholds_bytes_and_retry_keeps_one_unit(self):
        from loop_engine.core.service_runtime.records import ServiceCommitUnknown
        original = self.case.runtime.record_usage
        def lose_confirmation(*args, **kwargs):
            original(*args, **kwargs)
            raise ServiceCommitUnknown()
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            with mock.patch.object(self.case.runtime, "record_usage", side_effect=lose_confirmation):
                response, success, body, code = self.request(client, "http")
            self.assertFalse(success)
            self.assertIsNone(body)
            self.assertEqual(code, "meter_commit_unknown")
            self.assertNotIn(BODY, response.content)
            self.assertEqual(self.usage(), 1)
            _response, success, body, _code = self.request(client, "http")
            self.assertTrue(success)
            self.assertEqual(body, BODY)
            self.assertEqual(self.usage(), 1)

    def test_transport_cannot_supply_a_delivery_check_or_transaction_guards(self):
        with running_http(self.served) as (origin, _service), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            for transport in ("http", "mcp"):
                for field in ("delivery_check", "delivery_guards", "authority_guards"):
                    _response, success, body, _code = self.request(client, transport, **{field: []})
                    self.assertFalse(success)
                    self.assertIsNone(body)
        self.assertEqual(self.fake.count("GET"), 0)
        self.assertEqual(self.usage(), 0)

    def test_oauth_revoked_after_snapshot_cannot_commit_a_new_unit(self):
        from mcp.server.auth.provider import AuthorizationParams
        from mcp.shared.auth import OAuthClientInformationFull
        from loop_engine.core.provisioning_server import ProvisioningItemBinding, ProvisioningMeterRequest
        from loop_engine.core.service_runtime import account_origin
        from loop_engine.core.service_runtime.browser_identity import VerifiedIdentity
        from loop_engine.core.service_runtime.http_auth import (
            AuthenticatedHttpRequest, BROWSER_IDENTITY_AUTHENTICATION, ServiceHttpAuthentication,
            ServiceHttpAuthenticator,
        )
        from loop_engine.core.service_runtime.oauth_authorization import OAuthAuthorizationPolicy, OAuthAuthorizationProvider
        from loop_engine.core.service_runtime.records import DEFAULT_SCOPES, SubjectBindingRequest, ServiceRuntimeError
        async def exercise():
            runtime = self.case.runtime
            issuer = "https://identity.example.test/auth/v1"
            subject = "selected-oauth-subject"
            runtime.bind_subject(SubjectBindingRequest("alpha", issuer, subject))
            account_origin.record_origin(runtime, issuer, subject, account_origin.SIGNUP_ORIGIN)
            principal = runtime.authenticate_subject(issuer, subject)
            browser = AuthenticatedHttpRequest(principal, "synthetic-browser-only", BROWSER_IDENTITY_AUTHENTICATION,
                int(time.time()) + 3600, DEFAULT_SCOPES, VerifiedIdentity(subject, "", account_origin.SIGNUP_ORIGIN))
            policy = OAuthAuthorizationPolicy("https://service.example.test", "https://service.example.test/mcp",
                                               issuer, "https://service.example.test/oauth/consent",
                                               native_loopback_paths=("/oauth/callback",))
            provider = OAuthAuthorizationProvider(runtime, policy)
            callback = "http://127.0.0.1:43111/oauth/callback"
            client = OAuthClientInformationFull(client_id="selected-file-oauth", client_name="Synthetic file check",
                token_endpoint_auth_method="none", redirect_uris=[callback], scope=" ".join(DEFAULT_SCOPES),
                grant_types=["authorization_code", "refresh_token"], response_types=["code"])
            await provider.register_client(client)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(b"v" * 64).digest()).decode().rstrip("=")
            pending = await provider.authorize(client, AuthorizationParams(state="synthetic", scopes=list(DEFAULT_SCOPES),
                code_challenge=challenge, redirect_uri=callback, redirect_uri_provided_explicitly=True,
                resource=policy.resource_url))
            pending_id = parse_qs(urlsplit(pending).query)["authorization_id"][0]
            approved = await provider.approve_consent(pending_id, browser)
            code = parse_qs(urlsplit(approved).query)["code"][0]
            tokens = await provider.exchange_authorization_code(client, await provider.load_authorization_code(client, code))
            auth = ServiceHttpAuthenticator(runtime, ServiceHttpAuthentication(), oauth_authorization=provider)
            snapshot = auth.authenticate("Bearer " + tokens.access_token)
            await provider.revoke_token(await provider.load_access_token(tokens.access_token))
            request = ProvisioningMeterRequest("alpha", "selected-oauth-unit",
                                               ProvisioningItemBinding.from_item(self.view.catalogue.items[IDENTITY]))
            code = None
            try:
                runtime.record_usage(request, snapshot.principal,
                                     guards=getattr(getattr(snapshot, "oauth_context", None), "authority_guards", ()))
            except ServiceRuntimeError as error:
                code = error.code
            self.assertEqual(self.usage(), 0, "Revoked OAuth delegation committed a new usage unit")
            self.assertIn(code, ("concurrent_update", "unauthorized"))
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
