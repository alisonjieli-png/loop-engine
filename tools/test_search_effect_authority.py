"""Search effect selection through the real HTTP and protocol boundaries.

All service state is temporary. Requests stay on loopback. No model, body,
subprocess tool, provider or network effect is executed by searched material.
"""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import httpx

from loop_engine.core.harness_intelligence import (
    HarnessIntelligenceDraft,
    item_from_body,
)
from loop_engine.core.provisioning_server import (
    ProvisioningGrant,
    ProvisioningItemBinding,
)
from loop_engine.core.service_runtime.catalogue_search import ReleaseSearchIndex
from loop_engine.core.service_runtime.http import RETRIEVAL_REQUEST_VERSION
from loop_engine.core.service_runtime.http_test_fixtures import (
    HttpDomainFixture,
    running_http,
)
from loop_engine.core.service_runtime.protocol_checks import _protocol_client
from loop_engine.core.service_runtime.records import TenantKeyIssue


class SearchEffectAuthority(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        folder = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="search-effect-authority-"))
        self.fixture = HttpDomainFixture(Path(folder))
        for identity in ("tool.allowed", "tool.private", "tool.metadata_only"):
            body = "Zebrafish deterministic planner " + identity
            item = item_from_body(HarnessIntelligenceDraft(identity, "tool", body, "harness_local",
                "fixture:" + identity + "/v1", "MIT", ("spawns_process",)), body)
            self.fixture.catalogue.register(item)
            self.fixture.bodies[item.identity] = body
            self.fixture.bindings[item.identity] = ProvisioningItemBinding.from_item(item)
        self.fixture.runtime.set_grants("alpha", tuple(ProvisioningGrant("alpha", self.fixture.bindings[name], allowed)
            for name, allowed in (("tool.allowed", True), ("tool.metadata_only", False))))
        self.fixture.runtime.set_grants("beta", ())
        self.base, self.service = self.stack.enter_context(running_http(self.fixture))
        self.client = self.stack.enter_context(httpx.Client(base_url=self.base, headers=self.fixture.headers(),
                                                          trust_env=False, timeout=5))

    def tearDown(self):
        self.assertEqual(self.fixture.reads, [], "metadata selection must never read a body")
        self.assertEqual(self.fixture.usage()["records"], 0, "metadata selection is not metered")

    def search(self, **fields):
        return self.client.post("/api/v1/retrieval", json={"record_type": RETRIEVAL_REQUEST_VERSION,
            "query": "Zebrafish deterministic planner", "mode": "lexical", "top_n": 10, **fields})

    def test_search_can_select_an_authorized_effectful_item(self):
        selected = self.client.post("/api/v1/provisioning", json={"record_type":"service_provisioning_request/v1",
            "operation":"list", "authority_effects":["spawns_process"]})
        self.assertEqual(selected.status_code, 200)
        self.assertEqual({row["identity"] for row in selected.json()["result"]["items"]},
                         {"tool.allowed", "tool.metadata_only"})
        found = self.search(authority_effects=["spawns_process"])
        self.assertEqual(found.status_code, 200, found.text)
        hits = found.json()["result"]["hits"]
        self.assertEqual({row["reference"]["identity"] for row in hits}, {"tool.allowed", "tool.metadata_only"})
        self.assertEqual({row["reference"]["identity"]:row["body_allowed"] for row in hits},
                         {"tool.allowed": True, "tool.metadata_only": False})
        self.assertNotIn("tool.private", found.text)
        self.assertFalse(found.json()["result"]["bodies_loaded"])

    def test_omitted_empty_or_insufficient_effects_remain_withheld(self):
        for fields in ({}, {"authority_effects":[]}, {"authority_effects":["reads_fs"]}):
            with self.subTest(fields=fields):
                result = self.search(**fields)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["result"]["hits"], [])

    def test_unknown_and_malformed_effects_refuse_before_indexing(self):
        with patch.object(ReleaseSearchIndex, "rank", side_effect=AssertionError("invalid request reached ranking")):
            for effects in (["not_an_effect"], ["spawns_process", "spawns_process"], "spawns_process", [True], [{}], None):
                with self.subTest(effects=effects):
                    result = self.search(query="Nothingmatchesanyindex", authority_effects=effects)
                    self.assertEqual(result.status_code, 400)
                    self.assertEqual(result.json()["error"]["code"], "invalid_request")

    def test_unknown_authority_and_tenant_fields_are_not_selectors(self):
        for name, value in (("tenant_id", "beta"), ("allow_execution", True), ("grant", "tool.private")):
            result = self.search(authority_effects=["spawns_process"], **{name:value})
            self.assertEqual(result.status_code, 400)
            self.assertEqual(result.json()["error"]["code"], "unknown_request_field")

    def test_request_version_is_advertised_and_old_or_future_requests_refuse(self):
        self.assertEqual(RETRIEVAL_REQUEST_VERSION, "service_retrieval_request/v2")
        capabilities = self.client.get("/api/v1/capabilities").json()["result"]["retrieval"]
        self.assertEqual(capabilities["request_record_type"], RETRIEVAL_REQUEST_VERSION)
        self.assertEqual(capabilities["authority_effects"], "metadata_eligibility_only")
        for version in ("service_retrieval_request/v1", "service_retrieval_request/v99", None):
            result = self.search(record_type=version)
            self.assertEqual(result.status_code, 400)
            self.assertEqual(result.json()["error"]["code"], "unsupported_version")

    def test_effect_selection_does_not_broaden_grants_or_scopes(self):
        no_grants = self.client.post("/api/v1/retrieval", headers=self.fixture.headers("beta"),
            json={"record_type":RETRIEVAL_REQUEST_VERSION,"query":"Zebrafish", "authority_effects":["spawns_process"]})
        self.assertEqual(no_grants.status_code, 200)
        self.assertEqual(no_grants.json()["result"]["hits"], [])
        key = self.fixture.runtime.issue_key(TenantKeyIssue("alpha", "no metadata", scopes=("usage:read",)))
        no_scope = self.client.post("/api/v1/retrieval", headers={"Authorization":"Bearer " + key.key},
            json={"record_type":RETRIEVAL_REQUEST_VERSION,"query":"Zebrafish", "authority_effects":["spawns_process"]})
        self.assertEqual(no_scope.status_code, 403)
        self.assertNotIn("tool.allowed", no_scope.text)

        metadata = self.fixture.runtime.issue_key(TenantKeyIssue("alpha", "metadata only", scopes=("provisioning:metadata",)))
        headers = {"Authorization":"Bearer " + metadata.key}
        selected = self.client.post("/api/v1/retrieval", headers=headers,
            json={"record_type":RETRIEVAL_REQUEST_VERSION,"query":"Zebrafish", "authority_effects":["spawns_process"]})
        self.assertEqual(selected.status_code, 200)
        self.assertTrue(selected.json()["result"]["hits"])
        self.assertTrue(all(not hit["body_allowed"] for hit in selected.json()["result"]["hits"]))
        denied = self.client.post("/api/v1/download", headers=headers, json={
            "record_type":"service_provisioning_request/v1", "operation":"read", "identity":"tool.allowed",
            "request_id":"denied-download", "authority_effects":["spawns_process"]})
        self.assertEqual(denied.status_code, 403)

    def test_disabled_tenant_is_refused(self):
        self.fixture.runtime.set_tenant_enabled("beta", False)
        result = self.client.post("/api/v1/retrieval", headers=self.fixture.headers("beta"),
            json={"record_type":RETRIEVAL_REQUEST_VERSION,"query":"Zebrafish", "authority_effects":["spawns_process"]})
        self.assertEqual(result.status_code, 401)
        self.assertNotIn("tool.allowed", result.text)

    def test_unrelated_query_and_unchanged_ranking(self):
        result = self.search(query="Absentquasarword", authority_effects=["spawns_process"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["result"]["hits"], [])
        for mode in ("lexical", "hybrid"):
            selected = self.search(mode=mode, authority_effects=["spawns_process"]).json()["result"]["hits"]
            extra = self.search(mode=mode, authority_effects=["spawns_process", "reads_fs"]).json()["result"]["hits"]
            self.assertEqual(selected, extra, "irrelevant effect must not change ranking or scores")

    def test_inflight_grant_change_still_refuses_selected_metadata(self):
        original = ReleaseSearchIndex.rank
        def remove_after_rank(index, *args, **kwargs):
            result = original(index, *args, **kwargs)
            self.fixture.runtime.set_grants("alpha", ())
            return result
        with patch.object(ReleaseSearchIndex, "rank", remove_after_rank):
            result = self.search(authority_effects=["spawns_process"])
        self.assertNotEqual(result.status_code, 200)
        self.assertEqual(result.json()["error"]["code"], "disclosure_grant_changed")
        self.assertNotIn("tool.allowed", result.text)

    def test_protocol_schema_and_calls_share_the_same_selection(self):
        async def exercise():
            for mode in ("legacy", "2026-07-28"):
                async with _protocol_client(self.base, self.fixture, mode) as client:
                    tools = await client.list_tools()
                    search = next(tool for tool in tools.tools if tool.name == "intelligence_search")
                    self.assertEqual(search.input_schema["properties"]["authority_effects"]["type"], "array")
                    result = await client.call_tool("intelligence_search", {"query":"Zebrafish", "authority_effects":["spawns_process"]})
                    self.assertFalse(result.is_error, str(result))
                    self.assertEqual({hit["reference"]["identity"] for hit in result.structured_content["result"]["hits"]},
                                     {"tool.allowed", "tool.metadata_only"})
                    omitted = await client.call_tool("intelligence_search", {"query":"Zebrafish"})
                    self.assertFalse(omitted.is_error)
                    self.assertEqual(omitted.structured_content["result"]["hits"], [])
                    refused = await client.call_tool("intelligence_search", {"query":"Absentquasarword", "authority_effects":["made_up"]})
                    self.assertTrue(refused.is_error)
                    injected = await client.call_tool("intelligence_search", {"query":"Zebrafish", "authority_effects":["spawns_process"], "tenant_id":"beta"})
                    self.assertTrue(injected.is_error)
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
