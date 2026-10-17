"""Real loopback checks for the Connect binding of existing library tools.

The browser origin may differ, but a bearer credential, existing item grants,
exact digest and step effects still decide delivery. No external calls.
"""
from contextlib import ExitStack
import copy
from pathlib import Path
import tempfile
import unittest

import httpx

from loop_engine.core.service_runtime import openapi_tool_server as tool
from loop_engine.core.service_runtime.http import API_ROUTES, PROTOCOL_INSTRUCTIONS, PROTOCOL_TOOL_DESCRIPTIONS
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http


class OpenApiToolServerChecks(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.fixture = HttpDomainFixture(root)
        self.base, self.service = self.stack.enter_context(running_http(self.fixture))
        self.client = self.stack.enter_context(httpx.Client(base_url=self.base, timeout=10))
        self.origin = "https://customer-tool.example"

    def headers(self, tenant="alpha"):
        return {**self.fixture.headers(tenant), "Origin": self.origin}

    def test_public_document_matches_the_existing_tools_and_all_routes(self):
        response = self.client.get(tool.DOCUMENT_PATH, headers={"Origin": self.origin})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        self.assertNotIn("access-control-allow-credentials", response.headers)
        document = response.json()
        self.assertEqual(tool.document_problems(document, API_ROUTES, self.service.tool_server_tools(), self.base), [])
        wrong = copy.deepcopy(document)
        wrong["paths"]["/read"]["post"]["operationId"] = "intelligence_search"
        self.assertTrue(tool.document_problems(wrong, API_ROUTES, self.service.tool_server_tools(), self.base))
        wrong = copy.deepcopy(document)
        wrong["paths"].pop("/manifest")
        self.assertTrue(tool.document_problems(wrong, API_ROUTES, self.service.tool_server_tools(), self.base))
        wrong = copy.deepcopy(document)
        wrong["info"]["description"] = "Search Baltor."
        self.assertTrue(tool.document_problems(wrong, API_ROUTES, self.service.tool_server_tools(), self.base))
        self.assertEqual(self.fixture.reads, [])
        self.assertEqual(self.fixture.usage()["records"], 0)

    def test_protocol_initialize_instructions_and_search_guidance_cover_query_and_contract_card_rules(self):
        document = self.client.get(tool.DOCUMENT_PATH, headers={"Origin": self.origin}).json()
        search_description, search_schema = self.service.tool_server_tools()["intelligence_search"]
        self.assertEqual(
            tool.adoption_guidance_problems(PROTOCOL_INSTRUCTIONS, search_description, document["info"]["description"]),
            [],
        )
        self.assertIn("2 to 5 word", search_schema["properties"]["query"]["description"])
        self.assertIn("technical domain", search_schema["properties"]["query"]["description"])
        init_headers = {**self.fixture.headers("alpha"), "Accept": "application/json, text/event-stream"}
        init_response = self.client.post(
            "/mcp",
            headers=init_headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "adoption-check", "version": "1.0.0"},
                },
            },
        )
        self.assertEqual(init_response.status_code, 200, init_response.text)
        if init_response.headers.get("content-type", "").startswith("text/event-stream"):
            import json as _json
            data_lines = [line[5:].strip() for line in init_response.text.splitlines() if line.startswith("data:")]
            message = _json.loads(data_lines[-1])
        else:
            message = init_response.json()
        self.assertEqual(message["result"]["instructions"], PROTOCOL_INSTRUCTIONS)
        # Known-wrong controls: omitting 2-to-5-word query rules, contract card fields, or abstention rule must fail.
        self.assertTrue(
            tool.adoption_guidance_problems(
                "Search the Baltor library's metadata.",
                PROTOCOL_TOOL_DESCRIPTIONS["search"],
                document["info"]["description"],
            )
        )
        self.assertTrue(
            tool.adoption_guidance_problems(
                PROTOCOL_INSTRUCTIONS,
                PROTOCOL_TOOL_DESCRIPTIONS["search"].replace("2 to 5 word", "arbitrary"),
                document["info"]["description"],
            )
        )
        self.assertTrue(
            tool.adoption_guidance_problems(
                PROTOCOL_INSTRUCTIONS,
                PROTOCOL_TOOL_DESCRIPTIONS["search"],
                document["info"]["description"].replace("effects_to_declare", "permissions"),
            )
        )

    def test_preflight_is_scoped_to_the_documented_method_and_headers(self):
        headers = {"Origin": self.origin, "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "Authorization, Content-Type, X-Session-Id"}
        accepted = self.client.options(tool.READ_PATH, headers=headers)
        self.assertEqual(accepted.status_code, 204)
        self.assertEqual(accepted.headers["access-control-allow-origin"], "*")
        for changes in ({"Access-Control-Request-Method": "DELETE"},
                        {"Access-Control-Request-Headers": "Authorization, X-Operator-Key"}):
            refused = self.client.options(tool.READ_PATH, headers={**headers, **changes})
            self.assertEqual(refused.status_code, 403)
            self.assertNotIn("access-control-allow-origin", refused.headers)
        other = self.client.options("/api/v1/billing/checkout", headers=headers)
        self.assertEqual(other.status_code, 403)
        self.assertNotIn("access-control-allow-origin", other.headers)

    def test_search_needs_a_bearer_and_only_lists_the_accounts_granted_items(self):
        anonymous = self.client.post(tool.SEARCH_PATH, json={"query": "Alpha"},
                                     headers={"Origin": self.origin, "Cookie": "session=synthetic-cookie"})
        self.assertEqual(anonymous.status_code, 401)
        answer = self.client.post(tool.SEARCH_PATH, json={"query": "Alpha"}, headers=self.headers())
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual(answer.headers["access-control-allow-origin"], "*")
        self.assertNotIn("PRIVATE_BETA_BODY", answer.text)
        self.assertNotIn("APPROVED_ALPHA_BODY", answer.text)
        self.assertEqual(self.fixture.reads, [])
        self.assertEqual(self.fixture.usage()["records"], 0)

    def test_exact_read_uses_the_shared_meter_and_wrong_digest_or_tenant_does_not(self):
        fields = {"identity": "skill.alpha", "request_id": "connect-read-one",
                  "expected_digest": self.fixture.bindings["skill.alpha"].body_digest}
        wrong = self.client.post(tool.READ_PATH, json={**fields, "expected_digest": "0" * 64}, headers=self.headers())
        self.assertGreaterEqual(wrong.status_code, 400, wrong.text)
        denied = self.client.post(tool.READ_PATH, json=fields, headers=self.headers("beta"))
        self.assertGreaterEqual(denied.status_code, 400, denied.text)
        self.assertEqual(self.fixture.reads, [])
        self.assertEqual(self.fixture.usage()["records"], 0)
        first = self.client.post(tool.READ_PATH, json=fields, headers=self.headers())
        self.assertEqual(first.status_code, 200, first.text)
        self.assertIn("APPROVED_ALPHA_BODY", first.text)
        self.assertNotIn("PRIVATE_BETA_BODY", first.text)
        second = self.client.post(tool.READ_PATH, json={**fields, "request_id": "connect-read-two"}, headers=self.headers())
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(self.fixture.usage()["records"], 1)

    def test_malformed_or_extra_authority_fields_are_refused_before_a_body_read(self):
        for data in ({"query": "Alpha", "tenant_id": "beta"}, {"query": "Alpha", "oauth_context": {}}, []):
            response = self.client.post(tool.SEARCH_PATH, json=data, headers=self.headers())
            self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.fixture.reads, [])
        self.assertEqual(self.fixture.usage()["records"], 0)


if __name__ == "__main__":
    unittest.main()
