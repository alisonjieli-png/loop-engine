"""Focused offline checks for the typed MCP adapter boundary.

This module owns adversarial fixtures, not transport or approval behavior.
The public ``mcp_adapter.self_test`` remains the suite entry point.
"""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from .mcp_adapter import (
    InjectedMcpTransport, McpCallRequest, McpDiscoveryPolicy,
    McpError, McpInvocationServices, McpRegistry, McpServerSpec, McpToolSpec,
)
from .runtime_observer import RuntimeObservationServices


def run_checks() -> dict:
    import tempfile

    from ..loop.effect_approval import (
        ApprovalDecision, ApprovalStatus, EffectApprovalService)
    from ..loop.recursive_loop import LoopLedger
    from .context_artifacts import (
        ContextArtifactManager, ContextArtifactRef,
        ContextArtifactServices, ContextArtifactStore,
        ContextArtifactStoreSpec, ContextOffloadPolicy)

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    temporary = tempfile.TemporaryDirectory(prefix="loop-engine-mcp-")
    ledger = LoopLedger()
    runtime = RuntimeObservationServices(ledger=ledger)
    store = ContextArtifactStore(ContextArtifactStoreSpec(temporary.name))
    artifacts = ContextArtifactManager(
        ContextArtifactServices(store, runtime),
        ContextOffloadPolicy(max_inline_bytes=96, max_inline_tokens=24))
    server = McpServerSpec(
        "fixture", "in_process",
        tool_allowlist=(
            "fail", "large", "lookup", "slow", "write", "write_alt",
            "write_fail"))
    empty_schema = {
        "type": "object", "properties": {}, "additionalProperties": False}
    lookup_schema = {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
        "required": ["id"], "additionalProperties": False}
    write_schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"], "additionalProperties": False}
    invalid_schema_refused = False
    try:
        McpToolSpec(
            "fixture", "invalid", "Invalid", {"type": "not-a-type"},
            "pure")
    except McpError:
        invalid_schema_refused = True
    check("invalid_discovered_JSON_schema_is_refused",
          invalid_schema_refused)
    tools = (
        McpToolSpec(
            "fixture", "lookup", "Read one value", lookup_schema, "pure"),
        McpToolSpec(
            "fixture", "large", "Return a large value", empty_schema, "pure"),
        McpToolSpec(
            "fixture", "slow", "Return slowly", empty_schema, "pure"),
        McpToolSpec("fixture", "write", "Write one value", write_schema,
                    "writes_fs", True),
        McpToolSpec(
            "fixture", "write_alt", "Write another value", write_schema,
                    "writes_fs", True),
        McpToolSpec(
            "fixture", "write_fail", "Fail one write", write_schema,
                    "writes_fs", True),
        McpToolSpec(
            "fixture", "fail", "Fail one call", empty_schema, "pure"),
    )

    async def tool_handler(request):
        if request.tool_name in ("fail", "write_fail"):
            return _raise_fixture_failure()
        if request.tool_name == "slow":
            await asyncio.sleep(0.05)
            return "late"
        if request.tool_name == "large":
            return "x" * 1_000
        return {"tool": request.tool_name, "ok": True}

    transport = InjectedMcpTransport(tools, tool_handler)
    registry = McpRegistry()
    registry.register(server, transport)
    discovered = registry.discover("fixture", runtime=runtime)
    check("MCP_discovery_is_a_loop_and_respects_allowlist",
          [tool.name for tool in discovered]
          == ["fail", "large", "lookup", "slow", "write", "write_alt",
              "write_fail"])

    remote_server = McpServerSpec(
        "remote", "streamable_http", url="https://example.invalid")
    async def remote_handler(_request):
        return {}
    remote_transport = InjectedMcpTransport((McpToolSpec(
        "remote", "lookup", "Read", empty_schema, "pure"),), remote_handler)
    registry.register(remote_server, remote_transport)
    default_remote_refused = False
    try:
        registry.discover("remote", runtime=runtime)
    except McpError:
        default_remote_refused = True
    remote_tools = registry.discover(
        "remote", runtime=runtime,
        policy=McpDiscoveryPolicy(allowed_effects=("network",)))
    check("MCP_session_discovery_requires_its_declared_effect",
          default_remote_refused and [tool.name for tool in remote_tools]
          == ["lookup"] and not remote_transport.calls)

    missing_artifacts = registry.invoke(
        McpCallRequest("fixture", "lookup", {"id": 1}),
        services=McpInvocationServices(runtime=runtime))
    check("MCP_invocation_requires_the_typed_artifact_manager",
          missing_artifacts.status == "refused"
          and missing_artifacts.error_code == "artifact_manager_required"
          and not transport.calls)

    basic_services = McpInvocationServices(
        runtime=runtime, artifact_manager=artifacts)
    invalid_arguments = registry.invoke(
        McpCallRequest("fixture", "lookup", {"id": "not-an-integer"}),
        services=basic_services)
    check("arguments_must_match_the_discovered_JSON_schema",
          invalid_arguments.status == "refused"
          and invalid_arguments.error_code == "arguments_invalid"
          and not transport.calls)
    invalid_approval_plan_refused = False
    try:
        registry.approval_plan(
            McpCallRequest("fixture", "write", {"value": 7}),
            loop_id="loop_invalid_schema", reason="Invalid fixture.")
    except McpError:
        invalid_approval_plan_refused = True
    check("invalid_arguments_cannot_enter_an_approval_plan",
          invalid_approval_plan_refused)

    unsafe_server = McpServerSpec("unsafe", "in_process")
    unsafe_transport = InjectedMcpTransport((McpToolSpec(
        "unsafe", "lookup", "Read", lookup_schema, "pure"),),
        lambda request: {})
    unsafe_registry = McpRegistry()
    unsafe_registry.register(unsafe_server, unsafe_transport)
    unsafe_registry.discover("unsafe", runtime=runtime)
    unsafe_timeout = unsafe_registry.invoke(
        McpCallRequest("unsafe", "lookup", {"id": 1}),
        services=basic_services)
    check("transport_without_timeout_enforcement_is_refused_before_call",
          unsafe_timeout.status == "refused"
          and unsafe_timeout.error_code == "timeout_not_enforced"
          and not unsafe_transport.calls)

    pure = registry.invoke(McpCallRequest("fixture", "lookup", {"id": 1}),
                           services=basic_services)
    check("small_tool_output_is_stored_and_returned_inline_by_policy",
          pure.status == "completed" and pure.loop_id.startswith("loop")
          and pure.output == {"tool": "lookup", "ok": True}
          and pure.output_ref.startswith("sha256/")
          and len(transport.calls) == 1)

    blocked = registry.invoke(McpCallRequest(
        "fixture", "write", {"value": "x"}), services=basic_services)
    check("effectful_tool_requires_exact_approval",
          blocked.status == "approval_required" and len(transport.calls) == 1)

    class LegacyApprovalHook:
        @staticmethod
        def is_approved(*_args, **_kwargs):
            return True

    generic_hook_failed = False
    try:
        McpInvocationServices(
            runtime=runtime, artifact_manager=artifacts,
            approval_service=LegacyApprovalHook())
    except TypeError:
        generic_hook_failed = True
    check("generic_is_approved_hooks_are_not_an_authority_source",
          generic_hook_failed)

    plan = registry.approval_plan(
        McpCallRequest("fixture", "write", {"value": "x"}),
        loop_id="loop_mcp_write", reason="Write one reviewed fixture value.")
    approval_service = EffectApprovalService(runtime)
    checkpoint = approval_service.create(plan.approval)
    decided = approval_service.resume(
        checkpoint.pending, checkpoint.resume_token,
        ApprovalDecision.approve(plan.approval.request_id, "reviewer"))
    restored_service = EffectApprovalService(runtime)
    restored_service.restore_json(decided.to_json())
    approved = registry.invoke(
        plan.call,
        services=McpInvocationServices(
            runtime=runtime, approval_service=restored_service,
            artifact_manager=artifacts))
    check("serialized_exact_MCP_approval_runs_once_after_restore",
          approved.status == "completed"
          and approved.approval_id == plan.approval.request_id
          and restored_service.state(plan.approval.request_id).status
          is ApprovalStatus.CONSUMED
          and len(transport.calls) == 2
          and dict(plan.binding.effect_spec.parameters) == {
              "argument_digest": plan.call.argument_digest,
              "declared_effect": "writes_fs",
              "server_id": "fixture",
              "tool_name": "write"})
    replay = registry.invoke(
        plan.call,
        services=McpInvocationServices(
            runtime=runtime, approval_service=restored_service,
            artifact_manager=artifacts))
    consumed_json = restored_service.serialize(plan.approval.request_id)
    replay_after_restore = EffectApprovalService(runtime)
    replay_after_restore.restore_json(consumed_json)
    replay_restored = registry.invoke(
        plan.call,
        services=McpInvocationServices(
            runtime=runtime, approval_service=replay_after_restore,
            artifact_manager=artifacts))
    check("consumed_MCP_approval_cannot_be_replayed_or_restored_for_reuse",
          replay.status == "refused" and replay_restored.status == "refused"
          and len(transport.calls) == 2)

    concurrent_plan = registry.approval_plan(
        McpCallRequest("fixture", "write", {"value": "concurrent"}),
        loop_id="loop_mcp_concurrent",
        reason="Write the reviewed value once across concurrent callers.")
    concurrent_service = EffectApprovalService(runtime)
    concurrent_checkpoint = concurrent_service.create(
        concurrent_plan.approval)
    concurrent_service.resume(
        concurrent_checkpoint.pending, concurrent_checkpoint.resume_token,
        ApprovalDecision.approve(
            concurrent_plan.approval.request_id, "reviewer"))
    concurrent_services = McpInvocationServices(
        runtime=runtime, approval_service=concurrent_service,
        artifact_manager=artifacts)
    before_concurrent = len(transport.calls)
    with ThreadPoolExecutor(max_workers=2) as workers:
        concurrent_results = tuple(workers.map(
            lambda _index: registry.invoke(
                concurrent_plan.call, services=concurrent_services),
            range(2)))
    check("one_use_approval_is_atomic_across_concurrent_invocations",
          sorted(result.status for result in concurrent_results)
          == ["completed", "refused"]
          and len(transport.calls) == before_concurrent + 1)

    adversarial_plan = registry.approval_plan(
        McpCallRequest("fixture", "write", {"value": "original"}),
        loop_id="loop_mcp_adversarial",
        reason="Write the exact reviewed value.")
    adversarial_service = EffectApprovalService(runtime)
    adversarial_checkpoint = adversarial_service.create(
        adversarial_plan.approval)
    adversarial_service.resume(
        adversarial_checkpoint.pending, adversarial_checkpoint.resume_token,
        ApprovalDecision.approve(
            adversarial_plan.approval.request_id, "reviewer"))
    before_adversarial = len(transport.calls)
    changed_arguments = registry.invoke(
        replace(adversarial_plan.call, arguments={"value": "edited"}),
        services=McpInvocationServices(
            runtime=runtime, approval_service=adversarial_service,
            artifact_manager=artifacts))
    changed_tool = registry.invoke(
        replace(adversarial_plan.call, tool_name="write_alt"),
        services=McpInvocationServices(
            runtime=runtime, approval_service=adversarial_service,
            artifact_manager=artifacts))
    changed_request_id = registry.invoke(
        replace(adversarial_plan.call, approval_id="approval_changed"),
        services=McpInvocationServices(
            runtime=runtime, approval_service=adversarial_service,
            artifact_manager=artifacts))
    original_tool = registry._tools[("fixture", "write")]
    registry._tools[("fixture", "write")] = McpToolSpec(
        "fixture", "write", "Changed effect", write_schema, "network", True)
    changed_effect = registry.invoke(
        adversarial_plan.call,
        services=McpInvocationServices(
            runtime=runtime, approval_service=adversarial_service,
            artifact_manager=artifacts))
    registry._tools[("fixture", "write")] = original_tool
    check("edited_arguments_tool_effect_and_request_id_fail_closed",
          all(result.status == "refused" for result in (
              changed_arguments, changed_tool, changed_effect,
              changed_request_id))
          and len(transport.calls) == before_adversarial
          and adversarial_service.state(
              adversarial_plan.approval.request_id).status
          is ApprovalStatus.DECIDED)

    failed_plan = registry.approval_plan(
        McpCallRequest("fixture", "write_fail", {"value": "x"}),
        loop_id="loop_mcp_failed_write", reason="Attempt one reviewed write.")
    failed_service = EffectApprovalService(runtime)
    failed_checkpoint = failed_service.create(failed_plan.approval)
    failed_service.resume(
        failed_checkpoint.pending, failed_checkpoint.resume_token,
        ApprovalDecision.approve(failed_plan.approval.request_id, "reviewer"))
    before_failed = len(transport.calls)
    failed = registry.invoke(
        failed_plan.call,
        services=McpInvocationServices(
            runtime=runtime, approval_service=failed_service,
            artifact_manager=artifacts))
    failed_replay = registry.invoke(
        failed_plan.call,
        services=McpInvocationServices(
            runtime=runtime, approval_service=failed_service,
            artifact_manager=artifacts))
    check("failed_approved_effect_crosses_transport_once_and_consumes_approval",
          failed.status == "failed"
          and failed.error_code == "transport_failed"
          and failed_replay.status == "refused"
          and len(transport.calls) == before_failed + 1
          and failed_service.state(failed_plan.approval.request_id).status
          is ApprovalStatus.CONSUMED)

    before_pure_failure = len(transport.calls)
    pure_failure = registry.invoke(
        McpCallRequest("fixture", "fail"), services=basic_services)
    check("one_invoke_crosses_transport_at_most_once_even_on_failure",
          pure_failure.status == "failed"
          and len(transport.calls) == before_pure_failure + 1)

    before_timeout = len(transport.calls)
    timed_out = registry.invoke(
        McpCallRequest("fixture", "slow", timeout_seconds=0.001),
        services=basic_services)
    check("async_transport_enforces_the_call_timeout_once",
          timed_out.status == "failed"
          and timed_out.error_code == "transport_failed"
          and len(transport.calls) == before_timeout + 1)

    large_value = "x" * 1_000
    large = registry.invoke(
        McpCallRequest("fixture", "large"), services=basic_services)
    artifact_events = [event for event in ledger.events
                       if event.get("event") == "context_artifact_stored"
                       and event.get("artifact_kind") == "mcp_tool_output"]
    large_event = max(artifact_events, key=lambda event: event["byte_count"])
    large_ref = ContextArtifactRef(
        large_event["digest"], large_event["byte_count"],
        media_type=large_event["media_type"],
        artifact_kind=large_event["artifact_kind"])
    check("large_tool_output_returns_only_its_digest_object_key",
          large.status == "completed" and large.output is None
          and large.output_ref == large_ref.object_key
          and store.get_text(large_ref) == json.dumps(large_value)
          and large_event["offloaded"])

    unknown = registry.invoke(McpCallRequest("fixture", "missing"),
                              services=basic_services)
    check("unknown_tools_fail_closed", unknown.status == "refused")
    disabled = McpServerSpec("disabled", "in_process", enabled=False)
    registry.register(disabled, InjectedMcpTransport((), lambda request: {}))
    unavailable = registry.invoke(McpCallRequest("disabled", "anything"),
                                  services=basic_services)
    unregistered = registry.invoke(McpCallRequest("missing", "anything"),
                                    services=basic_services)
    check("disabled_and_unregistered_servers_are_unavailable",
          unavailable.status == "unavailable"
          and unregistered.status == "unavailable"
          and unregistered.error_code == "server_not_registered")

    terminal_events = [event for event in ledger.events
                       if event.get("event") == "mcp_call_terminal"]
    from .event_vocabulary import to_canonical_events
    families = [row["type"] for row in to_canonical_events(terminal_events)]
    check("MCP_events_use_closed_statuses_and_never_include_output_bodies",
          {event["status"] for event in terminal_events} == {
              "completed", "approval_required", "failed", "refused",
              "unavailable"}
          and set(families) == {"tool.invocation.completed",
                               "tool.invocation.failed", "loop.paused",
                               "capability.rejected"}
          and all(not ({"arguments", "output", "inline_text", "content"}
                       & set(event))
                  for event in (*terminal_events, *artifact_events)))

    temporary.cleanup()
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


def _raise_fixture_failure():
    raise RuntimeError("fixture transport failure")
