"""Encoded delivery admission and final authority; synthetic stores and loopback only."""
from dataclasses import asdict, replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import httpx

from loop_engine.core.provisioning_server import (
    ProvisioningError, ProvisioningMeterRequest, _body_answer, tierless_answer,
)
from loop_engine.core.service_runtime.billing_records import StripeEntitlementPolicy
from loop_engine.core.service_runtime.catalogue_release_checks import bundle_line
from loop_engine.core.service_runtime.catalogue_releases import publish
from loop_engine.core.service_runtime.http import (
    PROTOCOL_ANSWER_RESERVE_BYTES, ServiceHttpApplication, TIERED_PROVISIONING_REQUEST_VERSION,
    _json_bytes, _protocol_cost,
)
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
from loop_engine.core.service_runtime.list_paging import ENVELOPE_RESERVE_BYTES
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from loop_engine.core.service_runtime.runtime import BILLING_POLICY, ENTITLEMENT, STRIPE_SNAPSHOT_SOURCE, USAGE
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
from loop_engine.core.service_runtime.usage_meter import acknowledgment_size_preview
import test_selected_file_delivery as selected


class InlineAdmissionChecks(unittest.TestCase):
    def exercise(self, transport, *, allowed=False, tiered=True):
        with TemporaryDirectory(prefix="inline-size-admission-") as folder:
            text = ('"\\\x01😀' * 3000) if allowed else ('"' * 2048)
            case = HttpDomainFixture(Path(folder), bodies={"skill.alpha": text, "skill.beta": "beta",
                "skill.candidate": "candidate", "skill.large": "large"})
            principal = case.runtime.authenticate_key(case.keys["alpha"].key)
            fields = {"identity": "skill.alpha", "request_id": "inline-size-review"}
            if tiered:
                fields["authority_effects"] = []
            limit = 4096
            if allowed:
                item = case.catalogue.items["skill.alpha"]
                meter = ProvisioningMeterRequest("alpha", fields["request_id"], case.bindings[item.identity])
                preview = _body_answer(SimpleNamespace(tenant_id="alpha"), item, text,
                    case.provisioning.qualification_resolver.resolve(case.bindings[item.identity]),
                    acknowledgment_size_preview(case.runtime, meter))
                if not tiered:
                    preview = tierless_answer(preview)
                # One byte beyond the exact encoded payload plus the existing
                # framing reserve; this is near the admission boundary, not an
                # assertion that reserved bytes are all emitted on the wire.
                limit = 1 + (_protocol_cost(preview) + PROTOCOL_ANSWER_RESERVE_BYTES if transport == "mcp"
                             else len(_json_bytes(preview)) + ENVELOPE_RESERVE_BYTES)
            self.assertEqual(case.runtime.usage_for(principal)["records"], 0)
            with running_http(case, maximum_response_bytes=limit,
                              maximum_inline_body_bytes=max(4096, len(text.encode()))) as (origin, _app), \
                    httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
                headers = case.headers()
                if transport == "http":
                    response = client.post("/api/v1/provisioning", headers=headers, json={
                        "record_type": TIERED_PROVISIONING_REQUEST_VERSION if tiered else "service_provisioning_request/v1",
                        "operation": "read", **fields})
                    output = response.json()
                    value = output.get("result", {})
                    failed = response.status_code != 200
                    code = output.get("error", {}).get("code")
                else:
                    headers.update({"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2026-07-28",
                        "Mcp-Method": "tools/call", "Mcp-Name": "provisioning_read"})
                    response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "provisioning_read", "arguments": fields, "_meta": {
                            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                            "io.modelcontextprotocol/clientCapabilities": {}}}})
                    message = selected.protocol_message(response)
                    output = message.get("result", {}).get("structuredContent", {})
                    value = output.get("result", {})
                    failed = bool(message.get("result", {}).get("isError"))
                    code = output.get("error", {}).get("code")
                self.assertEqual(failed, not allowed)
                if allowed:
                    self.assertEqual(value["body"], text)
                    self.assertTrue(value["metering_acknowledgment"]["committed"])
                    self.assertEqual(case.runtime.usage_for(principal)["records"], 1)
                    self.assertLessEqual(len(response.content), limit)
                else:
                    self.assertEqual(code, "response_limit_exceeded")
                    if transport == "http":
                        self.assertEqual(response.status_code, 413)
                    self.assertEqual(case.runtime.usage_for(principal)["records"], 0,
                                     "predictable encoded-size refusal committed a fresh unit")
                self.assertEqual(case.reads, ["skill.alpha"], "preparation must reuse the already verified body")

    def test_http_encoded_limit_refuses_before_usage(self):
        self.exercise("http")

    def test_mcp_encoded_limit_refuses_before_usage(self):
        self.exercise("mcp")

    def test_http_near_prepared_limit_keeps_exact_bytes_and_actual_ack(self):
        self.exercise("http", allowed=True)

    def test_legacy_http_near_prepared_limit_keeps_tierless_shape(self):
        self.exercise("http", allowed=True, tiered=False)

    def test_mcp_near_prepared_limit_keeps_both_encoded_copies(self):
        self.exercise("mcp", allowed=True)

    def test_removed_encoded_guard_is_detected_for_http_and_mcp(self):
        def removed(app, authentication, view, reservation, _meter, _answer, **_options):
            return app._check_prepared_delivery(authentication, view, reservation)
        for transport in ("http", "mcp"):
            with self.subTest(transport=transport), mock.patch.object(ServiceHttpApplication, "_check_inline_delivery", removed):
                with self.assertRaisesRegex(AssertionError, "predictable encoded-size refusal"):
                    self.exercise(transport)

    def test_removed_ascii_outer_wrapper_bound_is_detected(self):
        def old_utf8_cost(value):
            raw = _json_bytes(value)
            return len(raw) + len(json.dumps(raw.decode(), ensure_ascii=False).encode())
        with mock.patch("loop_engine.core.service_runtime.http._protocol_cost", old_utf8_cost), \
                mock.patch(__name__ + "._protocol_cost", old_utf8_cost):
            with self.assertRaises(AssertionError):
                self.exercise("mcp", allowed=True)


class DeliveryInteractionChecks(selected.SelectedFileDelivery):
    """Re-run inherited selected-file checks alongside these interaction cases."""

    def paid_fixture(self):
        # This is a synthetic stored snapshot-derived grant, not evidence of a
        # payment. Exercise the real compatibility reader and usage CAS.
        runtime = self.case.runtime
        configured = runtime.configure_billing_policy(StripeEntitlementPolicy(("price_old",)))
        with runtime._catalog.store(write=True) as store:
            prior = runtime._catalog.read(store, ENTITLEMENT, "alpha")
            row = runtime._catalog.record(ENTITLEMENT, "alpha", {**prior["payload"],
                "source": STRIPE_SNAPSHOT_SOURCE, "policy_digest": configured["policy_digest"]}, tenant_id="alpha")
            runtime._catalog.commit(store, (row,), (runtime._catalog.guard(prior),))
        return row

    def add_price(self):
        runtime = self.case.runtime
        with runtime._catalog.store() as store:
            previous = runtime._catalog.read(store, BILLING_POLICY, "stripe")
        runtime.configure_billing_policy(StripeEntitlementPolicy(("price_old", "price_new")),
            expected_version=previous["record_version"], preserve_price_additions=True)

    def test_additive_policy_during_selected_read_keeps_exact_grant_and_one_unit(self):
        grant = self.paid_fixture()
        original = self.remote._request
        def add_during_read(*args, **kwargs):
            result = original(*args, **kwargs)
            self.add_price()
            return result
        with mock.patch.object(self.remote, "_request", side_effect=add_during_read):
            with running_http(self.served) as (origin, _app), httpx.Client(base_url=origin, trust_env=False) as client:
                _response, success, body, code = self.request(client, "http")
        self.assertTrue(success, code)
        self.assertEqual(body, selected.BODY)
        self.assertEqual(self.usage(), 1)
        with self.case.runtime._catalog.store() as store:
            self.assertEqual(self.case.runtime._catalog.read(store, ENTITLEMENT, "alpha"), grant)

    def test_final_commit_revalidation_honors_entitlement_revocation_under_v2(self):
        self.paid_fixture()
        self.add_price()
        commit, fired = ServiceCatalogBinding.commit, False
        def revoke(binding, store, records, guards, removals=()):
            nonlocal fired
            if not fired and any(row["artifact_kind"] == USAGE for row in records):
                fired = True
                self.case.runtime.revoke_entitlement("alpha")
            return commit(binding, store, records, guards, removals)
        with mock.patch.object(ServiceCatalogBinding, "commit", revoke):
            with running_http(self.served) as (origin, _app), httpx.Client(base_url=origin, trust_env=False) as client:
                response, success, body, _code = self.request(client, "http")
        self.assertTrue(fired)
        self.assertFalse(success)
        self.assertIsNone(body)
        self.assertNotIn(selected.BODY, response.content)
        self.assertEqual(self.usage(), 0)

    def test_host_callback_errors_and_invalid_guards_cannot_meter_or_leak(self):
        principal = self.case.runtime.authenticate_key(self.case.key.key)
        def broken(*_args):
            raise RuntimeError("private-callback-marker")
        for callback, expected in ((broken, "body_reader_unavailable"), (lambda *_args: [], "invalid_delivery_guards")):
            with self.subTest(expected=expected), self.assertRaises(ProvisioningError) as caught:
                self.served.provisioning.invoke_for_principal(principal, "read", identity=selected.IDENTITY,
                    request_id="callback-review", delivery_check=callback)
            self.assertEqual(caught.exception.code, expected)
            self.assertNotIn("private-callback-marker", str(caught.exception))
            self.assertEqual(self.usage(), 0)

    def test_selected_http_parent_descriptor_limit_refuses_before_selected_body(self):
        entries = [(selected.SELECTED, b"x", "text/markdown", "skill_definition")]
        entries += [(f"entry-{index:03d}.txt", b"x", "text/plain", "other") for index in range(50)]
        bundle = self.case.bundle([bundle_line(selected.IDENTITY, entries)], payloads=(b"x",))
        publish(self.case.context, bundle, expected_release=self.view.release_id)
        view = replace(self.case.view(), body_store=self.remote)
        self.package = view.package_of(selected.IDENTITY)
        self.served.provisioning.install_view(view)
        self.assertGreater(self.package.served_size, 1024)
        self.assertEqual(self.package.file(selected.SELECTED).size_bytes, 1)
        with running_http(self.served, maximum_download_bytes=1024, maximum_inline_body_bytes=1024) as (origin, _app), \
                httpx.Client(base_url=origin, trust_env=False) as client:
            response, success, body, code = self.request(client, "http")
        self.assertFalse(success)
        self.assertIsNone(body)
        self.assertEqual((response.status_code, code), (413, "download_limit_exceeded"))
        self.assertEqual(self.fake.count("GET"), 0)
        self.assertEqual(self.usage(), 0)


class OAuthPolicyInteraction(unittest.TestCase):
    def test_policy_change_after_oauth_snapshot_refuses_commit_then_fresh_retry_succeeds(self):
        import test_oauth_http as oauth
        import time
        case = oauth.HttpOAuthIntegration("test_discovery_dcr_signed_consent_scoped_api_and_real_mcp")
        self.addCleanup(case.doCleanups)
        case.setUp()
        runtime = case.fixture.runtime
        runtime.set_operator_entitlement(case.tenant, valid_until=int(time.time()) + 3600, evidence_ref="synthetic-only")
        original_policy = runtime.configure_billing_policy(StripeEntitlementPolicy(("price_old",)))
        with runtime._catalog.store(write=True) as store:
            prior = runtime._catalog.read(store, ENTITLEMENT, case.tenant)
            grant = runtime._catalog.record(ENTITLEMENT, case.tenant, {**prior["payload"],
                "source": STRIPE_SNAPSHOT_SOURCE, "policy_digest": original_policy["policy_digest"]}, tenant_id=case.tenant)
            runtime._catalog.commit(store, (grant,), (runtime._catalog.guard(prior),))
        token = case.issue(scope="provisioning:metadata provisioning:read usage:read")["access_token"]
        commit, fired = ServiceCatalogBinding.commit, False
        def add_before_usage(binding, store, records, guards, removals=()):
            nonlocal fired
            if not fired and any(row["artifact_kind"] == USAGE for row in records):
                fired = True
                runtime.configure_billing_policy(StripeEntitlementPolicy(("price_old", "price_new")),
                    expected_version=original_policy["record_version"], preserve_price_additions=True)
            return commit(binding, store, records, guards, removals)
        payload = {"record_type": "service_provisioning_request/v1", "operation": "read",
                   "identity": "skill.alpha", "request_id": "oauth-policy-interaction"}
        with mock.patch.object(ServiceCatalogBinding, "commit", add_before_usage):
            refused = case.client.post("/api/v1/download", headers=case.bearer(token), json=payload)
        self.assertTrue(fired)
        self.assertEqual(oauth.safe_error(refused), "concurrent_update")
        self.assertNotIn("APPROVED_ALPHA_BODY", refused.text)
        with runtime._catalog.store() as store:
            self.assertEqual(len(runtime._catalog.rows(store, USAGE, case.tenant)), 0)
            self.assertEqual(runtime._catalog.read(store, ENTITLEMENT, case.tenant), grant)
        accepted = case.client.post("/api/v1/download", headers=case.bearer(token), json=payload)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.content, b"APPROVED_ALPHA_BODY")
        with runtime._catalog.store() as store:
            self.assertEqual(len(runtime._catalog.rows(store, USAGE, case.tenant)), 1)
            self.assertEqual(runtime._catalog.read(store, ENTITLEMENT, case.tenant), grant)


if __name__ == "__main__":
    unittest.main()
