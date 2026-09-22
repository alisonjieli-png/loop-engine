"""Local authenticated Model Context Protocol transport for provisioning.

This adapter uses real official-package JSON-RPC session streams with the explicitly
supported 2025-11-25 profile. A host binds one credential outside the message
stream. ProvisioningServer remains the authority for disclosure, qualification,
revocation, body integrity, and metering. This is not a remote HTTP or OAuth
server and does not serve the 2026-07-28 protocol version: the installed
library could open a connection in that version, so a request that carries
its per-request version is refused before the library sees it.

There is one domain attempt per tool call. Cancellation never retries it.
Synchronous host callbacks can finish after a client stops waiting; a missing
response is not proof that a metering operation did not commit.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import json
import math

from ..loop.encapsulate import as_practitioner_loop
from ..loop.recursive_loop import LoopLedger
from .provisioning_server import ProvisioningError, ProvisioningRequest, ProvisioningServer

PROTOCOL_VERSION = "2025-11-25"
PROFILE_RECORD_TYPE = "provisioning_mcp_profile/v1"
RESULT_RECORD_TYPE = "provisioning_mcp_result/v1"
REFUSAL_RECORD_TYPE = "provisioning_mcp_refusal/v1"
AUTHENTICATION_ERROR = -32001
#: The key a request of the 2026-07-28 protocol version carries in its `_meta`.
PER_REQUEST_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
TOOL_OPERATIONS = {
    "provisioning_discover": "discover",
    "provisioning_list": "list",
    "provisioning_manifest": "manifest",
    "provisioning_read": "read",
}


class ProvisioningMcpError(ValueError):
    """The local transport profile or its host binding is invalid."""


@dataclass(frozen=True)
class ProvisioningMcpProfile:
    """An exact supported protocol and a host-declared request-size bound."""

    protocol_version: str = PROTOCOL_VERSION
    maximum_request_bytes: int = 65_536
    client_timeout_seconds: float = 10.0

    def __post_init__(self):
        if self.protocol_version != PROTOCOL_VERSION:
            raise ProvisioningMcpError("unsupported provisioning protocol version")
        if type(self.maximum_request_bytes) is not int or self.maximum_request_bytes < 1:
            raise ProvisioningMcpError("maximum_request_bytes must be a positive integer")
        if (type(self.client_timeout_seconds) not in (float, int)
                or not math.isfinite(self.client_timeout_seconds)
                or self.client_timeout_seconds <= 0):
            raise ProvisioningMcpError("client timeout must be finite and positive")

    def to_dict(self):
        from importlib.metadata import version
        return {"record_type": PROFILE_RECORD_TYPE, "transport": "in_process_json_rpc",
                "protocol_version": self.protocol_version, "sdk_distribution": "mcp",
                "sdk_version": version("mcp"), "remote_http_supported": False,
                "oauth_supported": False, "maximum_request_bytes": self.maximum_request_bytes,
                "client_timeout_seconds": self.client_timeout_seconds}


def invoke_provisioning_as_loop(server: ProvisioningServer, request: ProvisioningRequest,
                               *, ledger=None, parent=None) -> dict:
    """Own one domain attempt with a canonical Loop and body-free events."""
    result = as_practitioner_loop(
        "Harness Intelligence provisioning " + request.operation,
        lambda: server.handle(request), ledger=ledger, parent=parent)
    return {"record_type": RESULT_RECORD_TYPE, "result": result["value"],
            "execution": {"runtime_type": "Loop", "loop_id": result["loop_id"],
                          "profile": "practitioner.code_execution@1.0.0",
                          "model_calls": result["model_calls"],
                          "loop_definition_digest": result["loop_definition_digest"]}}


def _schema(operation: str) -> dict:
    properties = {}
    if operation != "discover":
        properties = {
            "style": {"type": "string"},
            "authority_effects": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
            "kinds": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        }
    if operation in ("manifest", "read"):
        properties["identity"] = {"type": "string", "minLength": 1}
    if operation == "read":
        properties["request_id"] = {"type": "string", "minLength": 1}
    return {"type": "object", "properties": properties, "additionalProperties": False,
            "required": ["identity"] if operation in ("manifest", "read") else []}


@dataclass
class ProvisioningMcpTransport:
    """One host-bound authenticated session adapter; no credential messages."""

    server: ProvisioningServer = field(repr=False)
    key: str = field(repr=False)
    profile: ProvisioningMcpProfile = field(default_factory=ProvisioningMcpProfile)
    ledger: LoopLedger = field(default_factory=LoopLedger, repr=False)

    def __post_init__(self):
        if not isinstance(self.server, ProvisioningServer):
            raise ProvisioningMcpError("a typed provisioning server is required")
        if not isinstance(self.key, str) or not self.key.strip():
            raise ProvisioningMcpError("the host must bind a nonempty credential")
        if not isinstance(self.profile, ProvisioningMcpProfile) or not isinstance(self.ledger, LoopLedger):
            raise ProvisioningMcpError("typed transport profile and Loop ledger are required")

    def _sdk_server(self):
        import anyio
        import mcp.types as types
        from jsonschema import ValidationError, validate
        from mcp.server.lowlevel import Server
        from mcp.types.version import HANDSHAKE_PROTOCOL_VERSIONS
        if PROTOCOL_VERSION not in HANDSHAKE_PROTOCOL_VERSIONS:
            raise ProvisioningMcpError("installed SDK does not support the declared protocol profile")

        async def list_tools(_ctx, _params):
            self.server.tenant_for(self.key)
            return types.ListToolsResult(tools=[types.Tool(
                name=name, description="Authenticated Harness Intelligence " + operation + ".",
                inputSchema=_schema(operation),
                annotations=types.ToolAnnotations(
                    readOnlyHint=operation != "read", destructiveHint=False,
                    idempotentHint=operation != "read"))
                for name, operation in TOOL_OPERATIONS.items()])

        async def call_tool(_ctx, params):
            name, arguments = params.name, params.arguments or {}
            operation = TOOL_OPERATIONS.get(name)
            try:
                if operation is None:
                    raise ProvisioningMcpError("unknown provisioning operation")
                validate(arguments, _schema(operation))
                request = ProvisioningRequest(
                    operation, self.key, identity=arguments.get("identity", ""),
                    style=arguments.get("style", ""),
                    authority_effects=tuple(arguments.get("authority_effects", ())),
                    kinds=tuple(arguments.get("kinds", ())),
                    request_id=arguments.get("request_id", ""))
                # No retry: an abandoned wait cannot establish that metering
                # did not happen. Host callbacks retain their own deadlines.
                result = await anyio.to_thread.run_sync(
                    lambda: invoke_provisioning_as_loop(self.server, request, ledger=self.ledger))
                # The synchronous host operation is not forcibly interrupted.
                # Deliver a pending cancellation before constructing a second
                # response after the official session already acknowledged it.
                await anyio.lowlevel.checkpoint()
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=json.dumps(result))],
                    structuredContent=result, isError=False)
            except (ProvisioningError, ProvisioningMcpError, ValidationError):
                reason = "request_refused"
            except Exception:
                # Never reflect domain errors, callback contents, or secrets.
                reason = "operation_failed"
            refused = {"record_type": REFUSAL_RECORD_TYPE, "reason": reason,
                       "metering_status": "not_asserted"}
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(refused))],
                structuredContent=refused, isError=True)

        sdk = Server("loop-engine-provisioning", version="1.0.0",
                     on_list_tools=list_tools, on_call_tool=call_tool)
        # The library records every message as a trace span by default; this
        # adapter has no telemetry setting, so it records none.
        sdk.middleware = []
        return sdk

    async def _guard_requests(self, incoming, forwarded, outgoing):
        import mcp.types as types
        from mcp.shared.message import SessionMessage
        from pydantic import ValidationError
        initialization_accepted = False
        initialized = False
        async with forwarded:
            async for message in incoming:
                if not isinstance(message, SessionMessage):
                    raise ProvisioningMcpError("invalid local protocol message")
                root = message.message
                if isinstance(root, types.JSONRPCRequest):
                    error = None
                    try:
                        self.server.tenant_for(self.key)
                    except ProvisioningError:
                        error = types.ErrorData(code=AUTHENTICATION_ERROR, message="Authentication failed")
                    encoded = root.model_dump_json(by_alias=True)
                    if error is None and len(encoded.encode("utf-8")) > self.profile.maximum_request_bytes:
                        error = types.ErrorData(code=types.INVALID_PARAMS, message="Request exceeds transport limit")
                    meta = (root.params or {}).get("_meta")
                    if error is None and isinstance(meta, dict) and PER_REQUEST_VERSION_KEY in meta:
                        # The library opens a connection in the version its
                        # first request carries. This adapter serves only the
                        # handshake, so a per-request version never reaches it.
                        error = types.ErrorData(code=types.INVALID_REQUEST,
                                               message="This transport serves only the initialize handshake")
                    if (error is None and root.method == "initialize"
                            and (root.params or {}).get("protocolVersion") != self.profile.protocol_version):
                        error = types.ErrorData(code=types.INVALID_PARAMS, message="Unsupported protocol version",
                                               data={"supported": [self.profile.protocol_version]})
                    if error is None and root.method == "initialize":
                        try:
                            types.InitializeRequest(method="initialize", params=root.params)
                        except ValidationError:
                            error = types.ErrorData(code=types.INVALID_PARAMS, message="Invalid initialization")
                        if initialization_accepted:
                            error = types.ErrorData(code=types.INVALID_REQUEST, message="Session is already initialized")
                    elif error is None and root.method != "ping" and not initialized:
                        error = types.ErrorData(code=types.INVALID_REQUEST, message="Initialization is required")
                    if (error is None and root.method == "tools/call"
                            and (root.params or {}).get("name") not in TOOL_OPERATIONS):
                        error = types.ErrorData(code=types.INVALID_PARAMS, message="Unknown provisioning tool")
                    if error is not None:
                        await outgoing.send(SessionMessage(
                            types.JSONRPCError(jsonrpc="2.0", id=root.id, error=error)))
                        continue
                    if root.method == "initialize":
                        initialization_accepted = True
                    # Cross a real JSON serialization boundary and discard
                    # caller-supplied transport metadata, which is not authority.
                    message = SessionMessage(types.jsonrpc_message_adapter.validate_json(encoded))
                elif isinstance(root, types.JSONRPCNotification):
                    if root.method == "notifications/initialized":
                        if not initialization_accepted or initialized:
                            continue
                        initialized = True
                    elif not initialized:
                        continue
                await forwarded.send(message)

    async def run(self, read_stream, write_stream):
        """Run one SDK server over host-owned bidirectional local streams."""
        import anyio
        sdk = self._sdk_server()
        guarded_send, guarded_read = anyio.create_memory_object_stream(1)
        async with guarded_read, anyio.create_task_group() as tasks:
            tasks.start_soon(self._guard_requests, read_stream, guarded_send, write_stream)
            await sdk.run(guarded_read, write_stream, sdk.create_initialization_options())
            tasks.cancel_scope.cancel()

    @asynccontextmanager
    async def client_session(self):
        """Connect a real SDK client; callers explicitly initialize the session."""
        import anyio
        from mcp import ClientSession
        from mcp.shared.memory import create_client_server_memory_streams
        async with create_client_server_memory_streams() as (client, server):
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(self.run, *server)
                try:
                    async with ClientSession(
                            *client, read_timeout_seconds=float(self.profile.client_timeout_seconds)) as session:
                        yield session
                finally:
                    tasks.cancel_scope.cancel()
