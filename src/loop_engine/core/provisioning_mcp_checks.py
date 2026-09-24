"""Real local protocol checks, not hosted or external-provider qualification.

The installed official Python package is exercised through its ClientSession,
low-level server, JSON-RPC messages, and bidirectional in-memory streams.
Protocol sources accessed 2026-09-19:
https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
"""
from __future__ import annotations

import asyncio
import json
import threading
from unittest.mock import patch

from .harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
from .provisioning_mcp import (
    AUTHENTICATION_ERROR, PROTOCOL_VERSION, ProvisioningMcpError,
    ProvisioningMcpProfile, ProvisioningMcpTransport)
from .provisioning_server import (
    VERIFIED_TIER, ProvisioningAccessPolicy, ProvisioningGrant, ProvisioningItemBinding,
    ProvisioningMeterAcknowledgment, ProvisioningQualification,
    ProvisioningQualificationResolver, ProvisioningServer, ProvisioningTenant,
    RecordedMeter)
from .service_api import key_digest

_KEY = "LOCAL_PROVISIONING_CREDENTIAL_FIXTURE"
_BODY = "PRIVATE_APPROVED_BODY_FIXTURE"
_PRIVATE = "private-ungranted-fixture"
_CANDIDATE = "candidate-unapproved-fixture"


def _fixture(*, meter=None, metering="required"):
    catalogue = HarnessIntelligenceCatalogue()
    bodies = {"approved": _BODY, "metadata": "METADATA_ONLY_BODY_FIXTURE",
              _CANDIDATE: "CANDIDATE_BODY_FIXTURE", _PRIVATE: "PRIVATE_UNGRANTED_BODY_FIXTURE"}
    for identity, body in bodies.items():
        catalogue.register(item_from_body(HarnessIntelligenceDraft(
            identity, "skill", "Local protocol fixture", "context_intelligence",
            "fixture:" + identity, "MIT"), body))
    bindings = {name: ProvisioningItemBinding.from_item(item) for name, item in catalogue.items.items()}

    def qualify(binding):
        candidate = binding.identity == _CANDIDATE
        return ProvisioningQualification(
            binding, "unknown" if candidate else "approved",
            "host_attested", "" if candidate else "fixture-review:" + binding.identity,
            "" if candidate else VERIFIED_TIER)

    policy = ProvisioningAccessPolicy(tuple(
        ProvisioningGrant("tenant", binding, name != "metadata", metering)
        for name, binding in bindings.items() if name != _PRIVATE),
        ProvisioningQualificationResolver("fixture-read-only", qualify))
    reads = []

    def body_reader(item):
        reads.append(item.identity)
        return bodies[item.identity]

    server = ProvisioningServer(
        catalogue, (ProvisioningTenant("tenant", key_digest(_KEY), "bodies"),),
        body_reader=body_reader, meter=meter, access_policy=policy)
    return server, reads


async def _checks(check):
    import mcp.types as types
    from mcp.shared.exceptions import MCPError
    meter = RecordedMeter()
    server, reads = _fixture(meter=meter)
    transport = ProvisioningMcpTransport(server, _KEY)
    responses = []
    async with transport.client_session() as session:
        initialized = await session.initialize()
        tools = await session.list_tools()
        responses.extend((initialized.model_dump(mode="json"), tools.model_dump(mode="json")))
        check("actual_local_client_negotiates_only_the_declared_profile_and_discovers_four_tools",
              initialized.protocol_version == PROTOCOL_VERSION
              and {tool.name for tool in tools.tools} == {
                  "provisioning_discover", "provisioning_list", "provisioning_manifest", "provisioning_read"}
              and all("key" not in tool.input_schema.get("properties", {}) for tool in tools.tools))
        discovery = await session.call_tool("provisioning_discover", {})
        listed = await session.call_tool("provisioning_list", {})
        manifest = await session.call_tool("provisioning_manifest", {"identity": "approved"})
        responses.extend(row.model_dump(mode="json") for row in (discovery, listed, manifest))
        visible = listed.structured_content["result"]
        check("protocol_metadata_operations_are_scoped_body_free_and_unmetered",
              not any(row.is_error for row in (discovery, listed, manifest))
              and discovery.structured_content["result"]["items_held"] == 2
              and {row["identity"] for row in visible["items"]} == {"approved", "metadata"}
              and _CANDIDATE not in json.dumps(responses) and _PRIVATE not in json.dumps(responses)
              and _BODY not in json.dumps(responses) and not reads and not meter.rows
              and all(row.structured_content["result"]["metered"] is False
                      for row in (discovery, listed, manifest)))
        body = await session.call_tool("provisioning_read", {"identity": "approved", "request_id": "read-one"})
        result = body.structured_content["result"]
        repeated = await session.call_tool("provisioning_read", {"identity": "approved", "request_id": "read-one"})
        responses.extend(row.model_dump(mode="json") for row in (body, repeated))
        check("body_result_preserves_exact_committed_acknowledgment_and_volatile_durability",
              not body.is_error and result["body"] == _BODY and result["metered"] is True
              and result["metering_acknowledgment"]["committed"] is True
              and result["metering_acknowledgment"]["durability"] == "volatile"
              and result["metering_acknowledgment"]["request"]["request_id"] == "read-one"
              and repeated.structured_content["result"]["metering_acknowledgment"]
                  == result["metering_acknowledgment"]
              and len(meter.rows) == 1)
        before = len(reads)
        refusals = []
        for identity in (_CANDIDATE, _PRIVATE, "metadata", "missing"):
            row = await session.call_tool("provisioning_read", {"identity": identity, "request_id": "not-used"})
            refusals.append(row)
        for identity in (_CANDIDATE, _PRIVATE, "missing"):
            refusals.append(await session.call_tool("provisioning_manifest", {"identity": identity}))
        check("candidate_private_and_metadata_only_bodies_refuse_without_read_or_meter",
              all(row.is_error for row in refusals) and len(reads) == before and len(meter.rows) == 1
              and all(row.structured_content["metering_status"] == "not_asserted" for row in refusals)
              and all(identity not in json.dumps([row.model_dump(mode="json") for row in refusals])
                      for identity in (_CANDIDATE, _PRIVATE, "CANDIDATE_BODY_FIXTURE", "METADATA_ONLY_BODY_FIXTURE")))
        malformed = await session.call_tool("provisioning_read", {
            "identity": "approved", "request_id": "not-used", "key": "ATTEMPTED_CREDENTIAL_OVERRIDE"})
        old_request = await session.call_tool("provisioning_read", {
            "identity": "approved", "record_type": "provisioning_request/v1"})
        check("tool_arguments_cannot_replace_credentials_or_domain_contract_version",
              malformed.is_error and old_request.is_error and len(reads) == before
              and "ATTEMPTED_CREDENTIAL_OVERRIDE" not in str(malformed))
        unrelated_code, unrelated_message = None, ""
        try:
            await session.call_tool("unregistered_fixture_tool", {"text": "UNRELATED_INPUT_FIXTURE"})
        except MCPError as error:
            unrelated_code, unrelated_message = error.error.code, str(error)
        check("unregistered_tools_refuse_without_domain_work_or_input_echo",
              unrelated_code == types.INVALID_PARAMS and len(reads) == before
              and "UNRELATED_INPUT_FIXTURE" not in unrelated_message)
        responses.extend(row.model_dump(mode="json") for row in (*refusals, malformed, old_request))
        server.replace_access_policy(ProvisioningAccessPolicy())
        revoked = await session.call_tool("provisioning_read", {"identity": "approved", "request_id": "revoked"})
        empty = await session.call_tool("provisioning_list", {})
        check("an_open_protocol_session_observes_host_grant_revocation",
              revoked.is_error and empty.structured_content["result"]["items"] == []
              and len(reads) == before and len(meter.rows) == 1)
        responses.extend(row.model_dump(mode="json") for row in (revoked, empty))
    check("credentials_and_disclosed_bodies_do_not_enter_loop_events_or_adapter_representations",
          _KEY not in json.dumps(responses) and _KEY not in repr(transport)
          and _KEY not in json.dumps(transport.ledger.events)
          and _BODY not in json.dumps(transport.ledger.events))
    from .boundary_registry import BOUNDARIES, BOUNDARY_ONTOLOGY
    binding = BOUNDARY_ONTOLOGY["Harness Intelligence provisioning transport"]
    starts = [event for event in transport.ledger.events if event.get("event") == "init"]
    check("protocol_domain_work_matches_its_registered_canonical_loop_boundary",
          binding.runtime_type == "Loop" and binding.profile_ref == "practitioner.code_execution@1.0.0"
          and any(row["boundary"] == "Harness Intelligence provisioning transport"
                  and row["envelope"] == "core.provisioning_mcp.invoke_provisioning_as_loop" for row in BOUNDARIES)
          and bool(starts) and all(event.get("role") == "practitioner"
              and event.get("profile_id") == "practitioner.code_execution"
              and event.get("profile_version") == "1.0.0"
              and event.get("relationship_kind") == "starting" for event in starts))

    wrong = ProvisioningMcpTransport(server, "WRONG_CREDENTIAL_FIXTURE")
    async with wrong.client_session() as session:
        code = None
        safe_error = False
        try:
            await session.initialize()
        except MCPError as error:
            code = error.error.code
            safe_error = "WRONG_CREDENTIAL_FIXTURE" not in str(error)
        check("authentication_errors_do_not_reflect_credentials", safe_error)
        check("wrong_key_fails_actual_initialize_before_tools_or_domain_work",
              code == AUTHENTICATION_ERROR and wrong.ledger.events == [])

    fresh, fresh_reads = _fixture(meter=RecordedMeter())
    incompatible = ProvisioningMcpTransport(fresh, _KEY)
    async with incompatible.client_session() as session:
        code = bypass_code = None
        try:
            await session.send_request(types.InitializeRequest(params=types.InitializeRequestParams(
                protocol_version="2026-07-28", capabilities=types.ClientCapabilities(),
                client_info=types.Implementation(name="unsupported-profile-fixture", version="1.0.0"))),
                types.InitializeResult)
        except MCPError as error:
            code = error.error.code
        await session.send_notification(types.InitializedNotification())
        try:
            await session.call_tool("provisioning_discover", {})
        except MCPError as error:
            bypass_code = error.error.code
        check("unsupported_initialization_and_forged_initialized_notification_cannot_reach_domain",
              code == types.INVALID_PARAMS and bypass_code == types.INVALID_REQUEST
              and not incompatible.ledger.events and not fresh_reads)

    bounded = ProvisioningMcpTransport(fresh, _KEY, ProvisioningMcpProfile(maximum_request_bytes=1024))
    async with bounded.client_session() as session:
        await session.initialize()
        code = None
        try:
            await session.call_tool("provisioning_manifest", {"identity": "x" * 2048})
        except MCPError as error:
            code = error.error.code
        check("oversized_serialized_request_refuses_before_domain_work",
              code == types.INVALID_PARAMS and not bounded.ledger.events and not fresh_reads)

    uncertain_calls = []
    def uncertain_meter(request):
        uncertain_calls.append(request)
        return ProvisioningMeterAcknowledgment(request, None)
    for label, installed_meter in (("absent", None), ("unknown", uncertain_meter)):
        service, _reads = _fixture(meter=installed_meter)
        adapter = ProvisioningMcpTransport(service, _KEY)
        async with adapter.client_session() as session:
            await session.initialize()
            reply = await session.call_tool("provisioning_read", {"identity": "approved", "request_id": label})
            check(label + "_meter_acknowledgment_never_becomes_body_success",
                  reply.is_error and "body" not in reply.structured_content
                  and "metered" not in reply.structured_content
                  and reply.structured_content["metering_status"] == "not_asserted")
    check("unknown_meter_commit_has_one_attempt_without_automatic_retry", len(uncertain_calls) == 1)
    unmetered, _ = _fixture(metering="unmetered")
    async with ProvisioningMcpTransport(unmetered, _KEY).client_session() as session:
        await session.initialize()
        reply = await session.call_tool("provisioning_read", {"identity": "approved"})
        check("explicit_unmetered_grant_reports_no_acknowledgment_and_no_charge_claim",
              not reply.is_error and reply.structured_content["result"]["metered"] is False
              and reply.structured_content["result"]["metering_acknowledgment"] is None)

    entered, release = threading.Event(), threading.Event()
    calls, completed = [], []
    def delayed_meter(request):
        calls.append(request)
        entered.set()
        if not release.wait(2.0):
            raise RuntimeError("fixture release deadline expired")
        completed.append(request)
        return ProvisioningMeterAcknowledgment(request, True, "fixture-committed-after-cancel", "volatile")
    delayed, _ = _fixture(meter=delayed_meter)
    adapter = ProvisioningMcpTransport(delayed, _KEY)
    original_guard = adapter._guard_requests
    wire_request_ids, wire_cancellations = [], []

    async def observed_guard(incoming, forwarded, outgoing):
        async def messages():
            async for message in incoming:
                root = message.message
                if isinstance(root, types.JSONRPCRequest) and root.method == "tools/call":
                    wire_request_ids.append(root.id)
                if isinstance(root, types.JSONRPCNotification) and root.method == "notifications/cancelled":
                    wire_cancellations.append((root.params or {}).get("requestId"))
                yield message
        await original_guard(messages(), forwarded, outgoing)

    with patch.object(adapter, "_guard_requests", observed_guard):
        async with adapter.client_session() as session:
            await session.initialize()
            request = asyncio.create_task(session.call_tool("provisioning_read", {
                "identity": "approved", "request_id": "cancelled-once"}, read_timeout_seconds=3.0))
            deadline = asyncio.get_running_loop().time() + 1.0
            while not entered.is_set() and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.001)
            cancelled = False
            try:
                if entered.is_set():
                    # The client cancels its own call; the protocol library
                    # tells the server with notifications/cancelled.
                    request.cancel()
                await request
            except asyncio.CancelledError:
                cancelled = True
            finally:
                release.set()
            deadline = asyncio.get_running_loop().time() + 1.0
            while ((not completed or not wire_cancellations)
                   and asyncio.get_running_loop().time() < deadline):
                await asyncio.sleep(0.001)
            check("client_cancellation_does_not_retry_uncertain_metering_or_claim_no_commit",
                  cancelled and entered.is_set() and len(calls) == len(completed) == 1
                  and wire_cancellations == wire_request_ids[:1] and len(wire_request_ids) == 1)

    # The installed library opens a connection in whatever version its first
    # request carries. A request that carries the 2026-07-28 per-request
    # version must not open one here, even a ping, which is allowed before
    # the handshake, because this transport has qualified only the handshake.
    probe, probe_reads = _fixture(meter=RecordedMeter())
    per_request = ProvisioningMcpTransport(probe, _KEY)
    per_request_meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                        "io.modelcontextprotocol/clientCapabilities": {}}
    openings = ((types.PingRequest(params=types.RequestParams(_meta=per_request_meta)), types.EmptyResult),
                (types.DiscoverRequest(params=types.RequestParams(_meta=per_request_meta)), types.DiscoverResult),
                (types.ListToolsRequest(params=types.PaginatedRequestParams(_meta=per_request_meta)),
                 types.ListToolsResult))
    async with per_request.client_session() as session:
        refused_codes = []
        for opening, result_type in openings:
            try:
                await session.send_request(opening, result_type)
            except MCPError as error:
                refused_codes.append(error.error.code)
        initialized = await session.initialize()
        check("a_per_request_opening_cannot_select_an_unqualified_protocol_version",
              refused_codes == [types.INVALID_REQUEST] * 3 and initialized.protocol_version == PROTOCOL_VERSION
              and not per_request.ledger.events and not probe_reads)


def self_test() -> dict:
    """Exercise actual local protocol framing with host-owned offline fixtures."""
    try:
        import mcp
    except ImportError:
        return {"tests": [{"test": "provisioning_protocol_adapter_not_tested", "passed": None,
                           "not_tested": True, "outcome": "NOT_APPLICABLE",
                           "missing_optional_dependencies": ["mcp"],
                           "detail": "The optional official protocol package is not installed."}]}
    tests = []
    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})
    invalid_profiles = (
        {"protocol_version": "2026-07-28"}, {"protocol_version": "2024-11-05"},
        {"maximum_request_bytes": True}, {"maximum_request_bytes": 0},
        {"client_timeout_seconds": float("nan")}, {"client_timeout_seconds": True},
    )
    refused = 0
    for values in invalid_profiles:
        try:
            ProvisioningMcpProfile(**values)
        except ProvisioningMcpError:
            refused += 1
    check("unsupported_profiles_and_unbounded_or_non_numeric_limits_refuse",
          refused == len(invalid_profiles))
    asyncio.run(_checks(check))
    profile = ProvisioningMcpProfile().to_dict()
    passed = sum(row["passed"] for row in tests)
    return {"record_type": "provisioning_mcp_checks/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests),
            "profile": profile, "provider_calls": 0, "network_connections": 0,
            "hosted_authorization_qualified": False}
