"""A narrow harness tool over the same typed gateway and host-owned budget.

This application boundary owns a canonical Practitioner operation. Provider
registration, authority, usage and model execution remain in the existing
gateway and model session. Tool arguments cannot change those host bindings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json

from ..core.decisions.contracts import DecisionBatchRequest, DecisionProtocolError, REQUEST_VERSION, PROVIDER_CAPABILITY, QUESTION_KINDS


def decision_input_schema():
    return {"type": "object", "additionalProperties": False, "required": ["record_type", "state", "questions"],
        "properties": {"record_type": {"const": REQUEST_VERSION},
            "state": {"type": ["string", "object", "array"]}, "semantic_call_id": {"type": "string", "maxLength": 192},
            "questions": {"type": "array", "minItems": 1, "items": {
                "type": "object", "additionalProperties": False, "required": ["question_id", "kind", "instructions"],
                "properties": {"question_id": {"type": "string", "minLength": 1},
                    "kind": {"enum": list(QUESTION_KINDS)},
                    "instructions": {"type": "string", "minLength": 1},
                    "choices": {"type": "object", "additionalProperties": {"type": ["string", "null"]}},
                    "levels": {"type": "array", "items": {"type": "string"}},
                    "positive": {"type": "string"}, "negative": {"type": "string"}}}}}}


@dataclass(frozen=True)
class DecisionToolBinding:
    """One explicitly allocated session; tool arguments cannot replace its authority."""
    session: object = field(repr=False)
    ledger: object = field(default=None, repr=False)
    maximum_request_bytes: int = 262_144
    maximum_response_bytes: int = 1_048_576

    def __post_init__(self):
        from .solution_model_port import ModelExecutionSession
        from ..loop.recursive_loop import LoopLedger
        if not isinstance(self.session, ModelExecutionSession):
            raise DecisionProtocolError("host_owned_model_session_required")
        if self.ledger is None:
            object.__setattr__(self, "ledger", LoopLedger())
        if not isinstance(self.ledger, LoopLedger):
            raise DecisionProtocolError("existing_run_ledger_required")
        for value in (self.maximum_request_bytes, self.maximum_response_bytes):
            if type(value) is not int or value < 1:
                raise DecisionProtocolError("positive_transport_allowance_required")

    def describe(self):
        authority = self.session.authority
        providers = []
        for route, _attempt in authority.gateway._routes(authority.config):
            spec = authority.gateway.providers.get(route.provider)
            if spec is not None and PROVIDER_CAPABILITY in spec.capabilities:
                providers.append({"route": route.name, "provider": route.provider,
                                  **spec.adapter.decision_capabilities()})
        return {"record_type": "decision_tool_capabilities/v1", "engines": providers,
            "input_contract": REQUEST_VERSION, "calls_used": self.session.calls_used,
            "maximum_calls": authority.max_model_calls, "usage_complete": self.session.total_tokens_used is not None,
            "credentials_returned": False, "task_acceptance": "independent_required",
            "native_harness_loading_qualified": False}

    def evaluate(self, payload):
        from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
        from ..loop.loop_role import LoopRole, LoopRoleIdentity
        from ..core.decisions.contracts import canonical
        encoded = canonical(payload)
        if len(encoded.encode()) > self.maximum_request_bytes:
            raise DecisionProtocolError("decision_request_allowance_exceeded")
        request = DecisionBatchRequest.from_dict(payload)
        holder = {}
        owner = Loop("Evaluate the declared typed questions", LoopConfig(
            framework="custom", custom_steps=("evaluate",), allowable_modes=("hybrid",),
            preferred_modes=("hybrid",), delegated_modes=("non_deterministic",)),
            ledger=self.ledger, identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.solver"))
        def handler(loop, _step, _context):
            holder["value"] = self.session.invoke_decisions(request, loop)
            return StepOutcome(output="typed decision admitted; task acceptance remains separate", mode="hybrid", model_calls=0)
        result = owner.run(handler=handler, max_steps=2)
        if "value" not in holder:
            raise DecisionProtocolError("decision_operation_failed")
        output = {**holder["value"], "execution": {"runtime_type": "Loop", "loop_id": result.loop_id,
            "profile": "practitioner.solver@1.0.0", "mode": "hybrid"}, "calls_used": self.session.calls_used}
        if len(canonical(output).encode()) > self.maximum_response_bytes:
            raise DecisionProtocolError("decision_response_allowance_exceeded")
        return output

    def sdk_server(self):
        import anyio
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from jsonschema import validate

        async def list_tools(_ctx, _params):
            return types.ListToolsResult(tools=[
                types.Tool(name="decision_capabilities", description="Inspect configured decision engines without a model call.",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                annotations=types.ToolAnnotations(readOnlyHint=True, idempotentHint=True)),
                types.Tool(name="decision_evaluate", description=("Evaluate Choice, Score or boolean probability questions under the host's "
                    "configured model allowance. Returns typed judgments, not verified task outcomes. "
                    "Does not execute the selected action. A repeat can incur another model call."),
                    inputSchema=decision_input_schema(), annotations=types.ToolAnnotations(
                        readOnlyHint=False, destructiveHint=False, idempotentHint=False))])

        async def call_tool(_ctx, params):
            name, arguments = params.name, params.arguments or {}
            try:
                if name == "decision_capabilities":
                    if arguments:
                        raise DecisionProtocolError("unexpected_discovery_arguments")
                    value = self.describe()
                elif name == "decision_evaluate":
                    validate(arguments, decision_input_schema())
                    value = await anyio.to_thread.run_sync(lambda: self.evaluate(arguments))
                    await anyio.lowlevel.checkpoint()
                else:
                    raise DecisionProtocolError("unknown_decision_tool")
                return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(value))],
                                            structuredContent=value, isError=False)
            except Exception:
                value = {"record_type": "decision_tool_refusal/v1", "reason": "decision_refused",
                         "calls_used": self.session.calls_used, "automatic_retry": False,
                         "task_accepted": False}
                return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(value))],
                                            structuredContent=value, isError=True)

        sdk = Server("loop-engine-decisions", version="1.0.0", on_list_tools=list_tools, on_call_tool=call_tool)
        # The library records every message as a trace span by default; this
        # tool has no telemetry setting, so it records none.
        sdk.middleware = []
        return sdk

    async def serve(self):
        """Host-launched standard-I/O transport; operating-system access is authority."""
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (incoming, outgoing):
            await self.run_streams(incoming, outgoing)

    async def run_streams(self, incoming, outgoing):
        """Serve one connection at the 2025-11-25 handshake and nothing else.

        The installed protocol library opens a connection in whatever version
        the first request carries. This tool has qualified only the handshake,
        so a request that carries the 2026-07-28 per-request version is
        refused before the library sees it. `server/discover` is answered as a
        server without it would answer, so a client that probes with it falls
        back to the handshake.
        """
        import anyio
        import mcp.types as types
        from mcp.shared.message import SessionMessage
        from ..core.provisioning_mcp import PER_REQUEST_VERSION_KEY, PROTOCOL_VERSION
        sdk = self.sdk_server()
        guarded_send, guarded_receive = anyio.create_memory_object_stream(0)
        async def refuse(value, code, message):
            await outgoing.send(SessionMessage(types.JSONRPCError(
                jsonrpc="2.0", id=value.id, error=types.ErrorData(code=code, message=message))))
        async def forward():
            async with guarded_send:
                async for message in incoming:
                    if not isinstance(message, SessionMessage):
                        continue
                    value = message.message
                    if isinstance(value, types.JSONRPCRequest):
                        oversized = len(value.model_dump_json(by_alias=True).encode()) > self.maximum_request_bytes
                        unsupported = value.method == "initialize" and (value.params or {}).get("protocolVersion") != PROTOCOL_VERSION
                        if oversized or unsupported:
                            await refuse(value, types.INVALID_PARAMS, "Unsupported decision protocol request")
                            continue
                        if value.method == "server/discover":
                            await refuse(value, types.METHOD_NOT_FOUND, "Method not found")
                            continue
                        meta = (value.params or {}).get("_meta")
                        if isinstance(meta, dict) and PER_REQUEST_VERSION_KEY in meta:
                            await refuse(value, types.INVALID_REQUEST, "This tool serves only the initialize handshake")
                            continue
                    await guarded_send.send(message)
        async with anyio.create_task_group() as group:
            group.start_soon(forward)
            await sdk.run(guarded_receive, outgoing, sdk.create_initialization_options())
            group.cancel_scope.cancel()


def self_test():
    from .decision_tool_checks import run_checks
    from .decision_gateway_checks import run_checks as gateway_checks
    from ..core.decisions.contract_checks import report
    return report(run_checks()["tests"] + gateway_checks()["tests"])
