"""Checks for the staff transports over real loopback sockets, with the official protocol client.

A superadmin mints a staff key through the Administration page's route with a
signed browser session, and the official protocol client then lists and calls
the staff tools at `/admin/mcp` in both protocol versions this release serves.
The same service refuses a customer key, a host key and a browser session at
the staff endpoint, and a staff key at every customer route and at the staff
key route. No provider, mailbox or network outside loopback is used.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import inspect
import json
import re
import uuid

from .account_origin_checks import signed_identity
from .http_test_fixtures import running_http
from .staff_tool_checks import StaffWorld

_PER_REQUEST = "2026-07-28"
_ACCEPT = "application/json, text/event-stream"


@asynccontextmanager
async def _staff_client(base, key, mode):
    """The official protocol client over real Streamable HTTP, carrying one staff key."""
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    async with httpx2.AsyncClient(headers={"Authorization": "Bearer " + key}, trust_env=False, timeout=10) as http:
        async with Client(streamable_http_client(base + "/admin/mcp", http_client=http), mode=mode) as client:
            yield client


def _initialize(client, base, credential):
    return client.post(base + "/admin/mcp", headers={"Authorization": "Bearer " + credential, "Accept": _ACCEPT},
                       json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                           "protocolVersion": "2025-11-25", "capabilities": {},
                           "clientInfo": {"name": "staff-checks", "version": "1"}}})


def _mint(client, base, token, member, label="protocol client"):
    return client.post(base + "/api/v1/admin/staff-keys", headers={"Authorization": "Bearer " + token}, json={
        "record_type": "service_staff_key_request/v1", "operation": "mint", "request_id": uuid.uuid4().hex,
        "staff_member": member, "label": label})


async def _client_checks(check, base, owner_key, analytics_key, world):
    first = world.tenants["first"]
    for mode, version, names in (("legacy", "2025-11-25", ("official_client_lists_and_calls_staff_tools_by_handshake",)),
                                 (_PER_REQUEST, _PER_REQUEST, ("official_client_lists_and_calls_staff_tools_per_request",))):
        async with _staff_client(base, owner_key, mode) as client:
            listed = await client.list_tools()
            found = await client.call_tool("accounts_search", {"text": "first.customer"})
            planned = await client.call_tool("credits_grant", {"step": "plan", "tenant_id": first, "downloads": 2,
                                                              "reason": "protocol check " + version})
            digest_value = planned.structured_content["result"]["plan_digest"]
            applied = await client.call_tool("credits_grant", {
                "step": "apply", "tenant_id": first, "downloads": 2, "reason": "protocol check " + version,
                "plan_digest": digest_value, "request_id": "protocol-" + version})
            wrong = await client.call_tool("credits_grant", {
                "step": "apply", "tenant_id": first, "downloads": 2, "reason": "protocol check " + version,
                "plan_digest": "0" * 64, "request_id": "protocol-wrong-" + version})
            rows = found.structured_content["result"]["result"]["accounts"]
            check(names[0], client.protocol_version == version and len(listed.tools) == 15
                  and not found.is_error and [row["email"] for row in rows] == ["first.customer@example.com"]
                  and not planned.is_error and not applied.is_error
                  and applied.structured_content["result"]["result"]["committed"] is True
                  and wrong.is_error and wrong.structured_content["error"]["code"] == "plan_changed")
    async with _staff_client(base, analytics_key, "legacy") as client:
        listed = await client.list_tools()
        counts = await client.call_tool("accounts_search", {})
        forbidden = await client.call_tool("credits_grant", {"step": "plan", "tenant_id": first, "downloads": 1,
                                                            "reason": "analytics may not"})
        check("an_analytics_key_lists_its_own_tools_reads_counts_and_is_refused_an_effect",
              sorted(tool.name for tool in listed.tools)
              == ["accounts_search", "activity_search", "catalogue_status", "data_search"]
              and "@example.com" not in json.dumps(counts.structured_content)
              and counts.structured_content["result"]["result"]["total"] == 5
              and forbidden.is_error and forbidden.structured_content["error"]["code"] == "staff_tool_forbidden")


def _transport_checks(check, root):
    import httpx
    with signed_identity(root / "transport", operator_access=False) as identity:
        world = StaffWorld(identity)
        with running_http(identity.fixture, application_factory=world.application_for) as (base, service):
            owner_token = identity.token(world.people["owner"])
            with httpx.Client(trust_env=False, timeout=10) as client:
                minted = _mint(client, base, owner_token, "owner@example.com")
                owner_key = minted.json()["result"]["key"]
                analytics_key = _mint(client, base, owner_token, "numbers@example.com").json()["result"]["key"]
                listing = client.get(base + "/api/v1/admin/staff-keys",
                                     headers={"Authorization": "Bearer " + owner_token}).json()["result"]
                check("a_superadmin_mints_a_staff_key_on_the_page_route_and_the_listing_never_shows_it",
                      minted.status_code == 200 and owner_key.startswith("bsk_") and len(listing["keys"]) == 2
                      and owner_key not in json.dumps(listing) and listing["environment_variable"] == "BALTOR_STAFF_KEY")
                asyncio.run(_client_checks(check, base, owner_key, analytics_key, world))
                from .records import TenantKeyIssue
                customer_key = world.runtime.issue_key(TenantKeyIssue(world.tenants["first"], "customer key")).key
                host_key = identity.fixture.keys["alpha"].key
                customer_session = identity.token(world.people["first"])
                refused = [_initialize(client, base, credential) for credential in
                           (customer_key, host_key, customer_session, owner_token, "bsk_" + "z" * 43)]
                check("a_customer_key_host_key_or_browser_session_never_reaches_the_staff_endpoint",
                      [answer.status_code for answer in refused] == [401] * 5
                      and {answer.json()["error"]["code"] for answer in refused} == {"staff_credential_required"})
                staff_elsewhere = [client.get(base + "/api/v1/session", headers={"Authorization": "Bearer " + owner_key}),
                                   _mint(client, base, owner_key, "owner@example.com"),
                                   client.post(base + "/mcp", headers={"Authorization": "Bearer " + owner_key,
                                                                       "Accept": _ACCEPT}, json={})]
                check("a_staff_key_reaches_no_customer_route_and_mints_no_key",
                      [answer.status_code for answer in staff_elsewhere] == [401, 403, 401]
                      and staff_elsewhere[1].json()["error"]["code"] == "browser_session_required")
                route = client.post(base + "/api/v1/admin/tools/accounts_search",
                                    headers={"Authorization": "Bearer " + owner_key},
                                    json={"text": "second.customer"})
                customer_route = client.post(base + "/api/v1/admin/tools/accounts_search",
                                             headers={"Authorization": "Bearer " + customer_key}, json={})
                session_route = client.post(base + "/api/v1/admin/tools/service_health",
                                            headers={"Authorization": "Bearer " + owner_token}, json={})
                accounts = route.json()["result"]["result"]["accounts"] if route.status_code == 200 else []
                check("the_staff_tool_routes_answer_like_the_protocol_tools_for_a_key_or_a_staff_session",
                      [row["email"] for row in accounts] == ["second.customer@example.com"]
                      and customer_route.status_code == 403
                      and customer_route.json()["error"]["code"] == "staff_role_required"
                      and session_route.status_code == 200)
                revoked = client.post(base + "/api/v1/admin/staff-keys", headers={"Authorization": "Bearer " + owner_token},
                                      json={"record_type": "service_staff_key_request/v1", "operation": "revoke",
                                            "request_id": uuid.uuid4().hex,
                                            "key_id": minted.json()["result"]["key_id"]})
                after = _initialize(client, base, owner_key)
                check("a_revoked_staff_key_is_refused_at_the_staff_endpoint",
                      revoked.status_code == 200 and after.status_code == 401
                      and after.json()["error"]["code"] == "staff_key_revoked")
                reference = after.json().get("request_reference")
                logged = service.failure_journal.detail(reference)["failures"] if reference else []
                check("a_refused_staff_call_is_journalled_under_the_staff_endpoint",
                      len(logged) == 1 and logged[0]["route"] == "/admin/mcp"
                      and logged[0]["refusal_code"] == "staff_key_revoked")


def _route_table_checks(check):
    """Every staff route is in the table the router reads before it asks who is calling, and nothing more."""
    from . import http as _http
    from .staff_routes import STAFF_BODY_ROUTES, STAFF_KEYS_PATH, STAFF_TOOL_NAMES, STAFF_TOOL_ROUTES
    from .staff_tools import registry
    source = inspect.getsource(_http.ServiceHttpApplication._web_route)
    check("the_staff_tool_names_are_exactly_the_registered_staff_tools",
          sorted(STAFF_TOOL_NAMES) == sorted(registry()) and len(STAFF_TOOL_NAMES) == 15)
    check("every_staff_route_is_declared_and_answered",
          all(_http.API_ROUTES.get(path) == ("POST",) for path in STAFF_TOOL_ROUTES)
          and _http.API_ROUTES.get(STAFF_KEYS_PATH) == ("GET", "POST")
          and "path in STAFF_TOOL_ROUTES" in source and "/admin/mcp" in _http.DECLARED_ROUTES
          and set(STAFF_BODY_ROUTES) >= {"/admin/mcp", STAFF_KEYS_PATH, *STAFF_TOOL_ROUTES}
          and not re.search(r"STAFF_BODY_ROUTES", inspect.getsource(_http.ServiceHttpApplication._web_route)))


def run_checks(check, root):
    _route_table_checks(check)
    _transport_checks(check, root)
