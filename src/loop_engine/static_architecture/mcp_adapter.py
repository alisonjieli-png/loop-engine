"""Typed MCP discovery and invocation under Loop Engine effect policy.

MCP is a transport for tools, not an authority grant. Every server and tool is
registered explicitly. Discovery and invocation each run as a Loop. Unknown
tools, unknown effects, missing approvals, and unregistered servers fail
closed.

This module contains no network or subprocess code. Optional SDK transports
and injected application transports implement the small ``McpTransport``
protocol.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence

from ..loop.effect_approval import (
    ApprovalRequest, EffectApprovalService, EffectClass, EffectSpec)
from .context_artifacts import ContextArtifactManager
from .facets import EFFECTS
from .runtime_observer import (
    RuntimeObservation, RuntimeObservationServices)


MCP_TRANSPORTS = ("in_process", "stdio", "streamable_http", "sse")
MCP_CALL_STATUSES = (
    "completed", "failed", "refused", "approval_required", "unavailable")
_MCP_EFFECT_CLASSES = {
    "reads_fs": EffectClass.LOCAL_READ,
    "writes_fs": EffectClass.LOCAL_WRITE,
    "reads_secret": EffectClass.SECRET_ACCESS,
    "network": EffectClass.NETWORK_WRITE,
    "spawns_process": EffectClass.COMMAND_EXECUTION,
}


class McpError(RuntimeError):
    pass


@dataclass(frozen=True)
class McpServerSpec:
    server_id: str
    transport: str
    command: tuple[str, ...] = ()
    url: str = ""
    credential_refs: tuple[str, ...] = ()
    tool_allowlist: tuple[str, ...] = ()
    enabled: bool = True
    protocol_version: str = "2025-11-25"
    discovery_effect: str = ""

    def __post_init__(self) -> None:
        if not self.server_id:
            raise McpError("an MCP server needs server_id")
        if self.transport not in MCP_TRANSPORTS:
            raise McpError(f"transport must be one of {MCP_TRANSPORTS}")
        if self.transport == "stdio" and not self.command:
            raise McpError("stdio MCP server needs a command")
        if self.transport in ("streamable_http", "sse") \
                and not self.url.startswith(("http://", "https://")):
            raise McpError("HTTP MCP server needs an http or https URL")
        for ref in self.credential_refs:
            if not ref.startswith(("env:", "secret:")):
                raise McpError(
                    "MCP credentials must be references, not values")
        required_effect = {
            "in_process": "pure",
            "stdio": "spawns_process",
            "streamable_http": "network",
            "sse": "network",
        }[self.transport]
        if self.discovery_effect and self.discovery_effect != required_effect:
            raise McpError(
                f"{self.transport} discovery must declare {required_effect}")
        object.__setattr__(self, "discovery_effect", required_effect)


@dataclass(frozen=True)
class McpDiscoveryPolicy:
    """Effects and timeout authorized for MCP session discovery."""

    allowed_effects: tuple[str, ...] = ("pure",)
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if (not self.allowed_effects
                or any(effect not in EFFECTS for effect in self.allowed_effects)):
            raise McpError("discovery allowed_effects must use known effects")
        if self.timeout_seconds <= 0:
            raise McpError("discovery timeout must be positive")


@dataclass(frozen=True)
class McpToolSpec:
    server_id: str
    name: str
    description: str
    input_schema: Mapping[str, object]
    effect: str
    requires_approval: bool = False

    def __post_init__(self) -> None:
        if not self.server_id or not self.name or not self.description:
            raise McpError("an MCP tool needs server, name, and description")
        if self.effect not in EFFECTS:
            raise McpError(f"effect must be one of {EFFECTS}")
        if self.effect != "pure" and not self.requires_approval:
            raise McpError(
                "effectful MCP tools must declare approval requirement")
        try:
            schema_text = json.dumps(
                dict(self.input_schema), sort_keys=True, separators=(",", ":"))
            schema = json.loads(schema_text)
            from jsonschema.validators import validator_for
            validator_for(schema).check_schema(schema)
        except Exception as exc:
            raise McpError("MCP tool input_schema must be valid JSON Schema") from exc
        object.__setattr__(self, "input_schema", MappingProxyType(schema))

    def validate_arguments(self, arguments: Mapping[str, object]) -> None:
        from jsonschema.exceptions import ValidationError
        from jsonschema.validators import validator_for
        try:
            validator_for(dict(self.input_schema))(
                dict(self.input_schema)).validate(dict(arguments))
        except ValidationError as exc:
            raise McpError(
                "MCP arguments do not match the discovered input schema") from exc


@dataclass(frozen=True)
class McpCallRequest:
    server_id: str
    tool_name: str
    arguments: Mapping[str, object] = field(default_factory=dict)
    timeout_seconds: float = 60.0
    approval_id: str = ""
    trace_id: str = ""
    _arguments_json: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.server_id or not self.tool_name:
            raise McpError("MCP call needs server_id and tool_name")
        if self.timeout_seconds <= 0:
            raise McpError("MCP timeout must be positive")
        if any(not isinstance(key, str) or not key for key in self.arguments):
            raise McpError("MCP argument keys must be non-empty strings")
        secret_keys = [key for key in self.arguments
                       if any(part in str(key).lower() for part in
                              ("secret", "password", "api_key", "token"))]
        if secret_keys:
            raise McpError(
                f"MCP arguments contain secret-shaped keys {secret_keys}")
        try:
            canonical = json.dumps(
                dict(self.arguments), sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False)
            snapshot = json.loads(canonical)
        except (TypeError, ValueError) as exc:
            raise McpError("MCP arguments must be JSON values") from exc
        object.__setattr__(self, "arguments", MappingProxyType(snapshot))
        object.__setattr__(self, "_arguments_json", canonical)

    @property
    def argument_digest(self) -> str:
        return hashlib.sha256(self._arguments_json.encode("utf-8")).hexdigest()

    def transport_arguments(self) -> dict[str, object]:
        """Return a fresh JSON snapshot for one physical transport call."""
        return json.loads(self._arguments_json)

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps({
            "server": self.server_id, "tool": self.tool_name,
            "argument_digest": self.argument_digest, "trace": self.trace_id,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class McpApprovalBinding:
    """Exact MCP identity represented by one generic EffectSpec."""

    server_id: str
    tool_name: str
    argument_digest: str
    effect: str

    def __post_init__(self) -> None:
        if not self.server_id or not self.tool_name:
            raise McpError("MCP approval binding needs server and tool")
        if (len(self.argument_digest) != 64
                or any(char not in "0123456789abcdef"
                       for char in self.argument_digest)):
            raise McpError("MCP argument digest must be SHA-256")
        if self.effect not in _MCP_EFFECT_CLASSES:
            raise McpError("MCP approval binding needs a known effect")

    @classmethod
    def from_call(cls, request: McpCallRequest,
                  tool: McpToolSpec) -> "McpApprovalBinding":
        if (request.server_id != tool.server_id
                or request.tool_name != tool.name):
            raise McpError("MCP call and tool identity do not match")
        return cls(
            request.server_id, request.tool_name,
            request.argument_digest, tool.effect)

    @property
    def effect_spec(self) -> EffectSpec:
        return EffectSpec(
            effect_class=_MCP_EFFECT_CLASSES[self.effect],
            operation="invoke_mcp_tool",
            target=f"mcp:{self.server_id}:{self.tool_name}",
            parameters=(
                ("argument_digest", self.argument_digest),
                ("declared_effect", self.effect),
                ("server_id", self.server_id),
                ("tool_name", self.tool_name),
            ),
        )


@dataclass(frozen=True)
class McpApprovalPlan:
    """A call and generic approval request bound to one MCP effect."""

    call: McpCallRequest
    approval: ApprovalRequest
    binding: McpApprovalBinding

    def __post_init__(self) -> None:
        if self.call.approval_id != self.approval.request_id:
            raise McpError("MCP call and approval request id do not match")
        if self.approval.effect != self.binding.effect_spec:
            raise McpError("MCP approval effect does not match its binding")


@dataclass
class McpCallResult:
    server_id: str
    tool_name: str
    status: str
    output: object = None
    output_ref: str = ""
    error_code: str = ""
    error: str = ""
    loop_id: str = ""
    approval_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in MCP_CALL_STATUSES:
            raise McpError(f"status must be one of {MCP_CALL_STATUSES}")


class McpTransport(Protocol):
    timeout_enforced: bool

    def list_tools(self, server: McpServerSpec, *,
                   timeout_seconds: float) -> Sequence[McpToolSpec]: ...
    def call_tool(self, server: McpServerSpec,
                  request: McpCallRequest) -> object: ...


class InjectedMcpTransport:
    """Offline and application transport with inspectable calls."""

    def __init__(self, tools: Sequence[McpToolSpec], handler):
        self.tools = tuple(tools)
        self.handler = handler
        self.calls = []
        self.timeout_enforced = inspect.iscoroutinefunction(handler)

    def list_tools(self, server: McpServerSpec, *,
                   timeout_seconds: float = 60.0) -> tuple[McpToolSpec, ...]:
        return tuple(tool for tool in self.tools
                     if tool.server_id == server.server_id)

    def call_tool(self, server: McpServerSpec,
                  request: McpCallRequest) -> object:
        if not self.timeout_enforced:
            raise McpError(
                "injected synchronous handler cannot enforce timeout")
        self.calls.append(request)
        async def bounded_call():
            return await asyncio.wait_for(
                self.handler(request), timeout=request.timeout_seconds)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(bounded_call())
        raise McpError(
            "synchronous MCP registry cannot run inside an active event loop")


@dataclass(frozen=True)
class McpInvocationServices:
    """Runtime, approval, and artifact services for MCP operations."""

    runtime: RuntimeObservationServices = field(
        default_factory=RuntimeObservationServices)
    approval_service: "EffectApprovalService | None" = None
    artifact_manager: "ContextArtifactManager | None" = None

    def __post_init__(self) -> None:
        if (self.approval_service is not None
                and not isinstance(
                    self.approval_service, EffectApprovalService)):
            raise TypeError(
                "approval_service must be an EffectApprovalService")
        if (self.artifact_manager is not None
                and not isinstance(self.artifact_manager,
                                   ContextArtifactManager)):
            raise TypeError(
                "artifact_manager must be a ContextArtifactManager")


class McpRegistry:
    def __init__(self):
        self._servers: dict[str, McpServerSpec] = {}
        self._transports: dict[str, McpTransport] = {}
        self._tools: dict[tuple[str, str], McpToolSpec] = {}

    def register(self, server: McpServerSpec, transport: McpTransport, *,
                 replace: bool = False) -> None:
        if server.server_id in self._servers and not replace:
            raise McpError(f"MCP server {server.server_id!r} already registered")
        self._servers[server.server_id] = server
        self._transports[server.server_id] = transport
        for key in [key for key in self._tools if key[0] == server.server_id]:
            del self._tools[key]

    def server(self, server_id: str) -> McpServerSpec:
        if server_id not in self._servers:
            raise McpError(f"no MCP server {server_id!r}")
        return self._servers[server_id]

    def tools(self, server_id: str) -> tuple[McpToolSpec, ...]:
        return tuple(tool for (sid, _name), tool in sorted(self._tools.items())
                     if sid == server_id)

    def discover(self, server_id: str, *,
                 runtime: "RuntimeObservationServices | None" = None,
                 policy: "McpDiscoveryPolicy | None" = None
                 ) -> tuple[McpToolSpec, ...]:
        selected = runtime or RuntimeObservationServices()
        selected_policy = policy or McpDiscoveryPolicy()
        server = self.server(server_id)
        if not server.enabled:
            return ()
        if server.discovery_effect not in selected_policy.allowed_effects:
            raise McpError(
                f"MCP discovery effect {server.discovery_effect!r} is not "
                "authorized")

        def load_tools():
            tools = tuple(self._transports[server_id].list_tools(
                server, timeout_seconds=selected_policy.timeout_seconds))
            for tool in tools:
                if tool.server_id != server_id:
                    raise McpError("transport returned tool for another server")
                if (server.tool_allowlist
                        and tool.name not in server.tool_allowlist):
                    continue
                self._tools[(server_id, tool.name)] = tool
            return self.tools(server_id)

        from ..loop.encapsulate import as_loop
        from ..loop.loop_role import (LoopRelationship, LoopRole,
                                     LoopRoleIdentity)
        identity = LoopRoleIdentity(
            LoopRole.INTELLIGENCE, "intelligence.code.resolve")
        relationship = (LoopRelationship.queried_by(selected.parent.loop_id)
                        if selected.parent is not None
                        else LoopRelationship.starting())
        wrapped = as_loop(
            f"discover tools from MCP server {server_id}", load_tools,
            parent=selected.parent, ledger=selected.ledger,
            identity=identity, relationship=relationship)
        if wrapped.get("error") is not None:
            raise wrapped["error"]
        return tuple(wrapped["value"])

    def approval_plan(self, request: McpCallRequest, *, loop_id: str,
                      reason: str) -> McpApprovalPlan:
        """Build one exact approval request for a discovered MCP call."""
        server = self.server(request.server_id)
        if not server.enabled:
            raise McpError("cannot approve a disabled MCP server")
        tool = self._tools.get((request.server_id, request.tool_name))
        if tool is None:
            raise McpError("cannot approve an undiscovered MCP tool")
        if (server.tool_allowlist
                and request.tool_name not in server.tool_allowlist):
            raise McpError("cannot approve a tool outside the allowlist")
        if not tool.requires_approval:
            raise McpError("pure MCP tools do not need effect approval")
        tool.validate_arguments(request.transport_arguments())
        binding = McpApprovalBinding.from_call(request, tool)
        if request.approval_id:
            approval = ApprovalRequest(
                request.approval_id, loop_id, binding.effect_spec, reason,
                requested_by="mcp_registry")
            bound_call = request
        else:
            approval = ApprovalRequest.create(
                loop_id, binding.effect_spec, reason,
                requested_by="mcp_registry")
            bound_call = replace(request, approval_id=approval.request_id)
        return McpApprovalPlan(bound_call, approval, binding)

    def invoke(self, request: McpCallRequest, *,
               services: "McpInvocationServices | None" = None
        ) -> McpCallResult:
        selected = services or McpInvocationServices()
        try:
            server = self.server(request.server_id)
        except McpError:
            result = McpCallResult(
                request.server_id, request.tool_name, "unavailable",
                error_code="server_not_registered")
            _observe_terminal(selected, request, result)
            return result
        if not server.enabled:
            result = McpCallResult(
                request.server_id, request.tool_name, "unavailable",
                error_code="server_disabled")
            _observe_terminal(selected, request, result)
            return result
        tool = self._tools.get((request.server_id, request.tool_name))
        if tool is None:
            result = McpCallResult(
                request.server_id, request.tool_name, "refused",
                error_code="tool_not_discovered")
            _observe_terminal(selected, request, result)
            return result
        if (server.tool_allowlist
                and request.tool_name not in server.tool_allowlist):
            result = McpCallResult(
                request.server_id, request.tool_name, "refused",
                error_code="tool_not_allowed")
            _observe_terminal(selected, request, result, effect=tool.effect)
            return result
        transport = self._transports[request.server_id]
        if not bool(getattr(transport, "timeout_enforced", False)):
            result = McpCallResult(
                request.server_id, request.tool_name, "refused",
                error_code="timeout_not_enforced",
                approval_id=request.approval_id)
            _observe_terminal(selected, request, result, effect=tool.effect)
            return result
        try:
            tool.validate_arguments(request.transport_arguments())
        except McpError:
            result = McpCallResult(
                request.server_id, request.tool_name, "refused",
                error_code="arguments_invalid",
                approval_id=request.approval_id)
            _observe_terminal(selected, request, result, effect=tool.effect)
            return result
        if selected.artifact_manager is None:
            result = McpCallResult(
                request.server_id, request.tool_name, "refused",
                error_code="artifact_manager_required",
                approval_id=request.approval_id)
            _observe_terminal(selected, request, result, effect=tool.effect)
            return result
        if tool.requires_approval:
            if not request.approval_id or selected.approval_service is None:
                result = McpCallResult(
                    request.server_id, request.tool_name,
                    "approval_required", error_code="approval_required",
                    approval_id=request.approval_id)
                _observe_terminal(selected, request, result, effect=tool.effect)
                return result
            try:
                binding = McpApprovalBinding.from_call(request, tool)
                selected.approval_service.consume(
                    request.approval_id, binding.effect_spec)
            except KeyError:
                result = McpCallResult(
                    request.server_id, request.tool_name, "refused",
                    error_code="approval_not_found",
                    approval_id=request.approval_id)
                _observe_terminal(
                    selected, request, result, effect=tool.effect)
                return result
            except (McpError, PermissionError, RuntimeError, ValueError):
                result = McpCallResult(
                    request.server_id, request.tool_name, "refused",
                    error_code="approval_not_usable",
                    approval_id=request.approval_id)
                _observe_terminal(
                    selected, request, result, effect=tool.effect)
                return result

        from ..loop.loop_role import (LoopRelationship, LoopRole,
                                     LoopRoleIdentity)
        from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
        config = LoopConfig(
            framework="custom", custom_steps=("invoke_mcp_tool",),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",), power="light",
            exit_condition="accepted_success")
        identity = LoopRoleIdentity(
            LoopRole.INTELLIGENCE, "intelligence.code.invoke")
        relationship = (LoopRelationship.retrieved_by(
            selected.runtime.parent.loop_id)
            if selected.runtime.parent is not None
            else LoopRelationship.starting())
        loop = (selected.runtime.parent.spawn(
            f"invoke MCP tool {request.tool_name}", config,
            identity=identity, relationship=relationship)
                if selected.runtime.parent is not None else Loop(
                    f"invoke MCP tool {request.tool_name}", config,
                    ledger=selected.runtime.ledger,
                    identity=identity, relationship=relationship))
        holder = {"transport_crossed": False}

        def handler(_active_loop, _step, _context):
            if holder["transport_crossed"]:
                return StepOutcome(
                    output=f"mcp:{request.tool_name}:already_attempted",
                    mode="deterministic", confidence=1.0)
            holder["transport_crossed"] = True
            try:
                value = self._transports[request.server_id].call_tool(
                    server, request)
            except Exception as exc:  # noqa: BLE001
                holder["result"] = McpCallResult(
                    request.server_id, request.tool_name, "failed",
                    error_code="transport_failed",
                    error=f"{type(exc).__name__}: {str(exc)[:160]}",
                    approval_id=request.approval_id)
            else:
                try:
                    output_text = json.dumps(
                        value, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False, allow_nan=False)
                    payload = selected.artifact_manager.capture(
                        output_text, media_type="application/json",
                        artifact_kind="mcp_tool_output")
                    holder["result"] = McpCallResult(
                        request.server_id, request.tool_name, "completed",
                        output=None if payload.offloaded else value,
                        output_ref=payload.raw.object_key,
                        approval_id=request.approval_id)
                except Exception as exc:  # noqa: BLE001
                    holder["result"] = McpCallResult(
                        request.server_id, request.tool_name, "failed",
                        error_code="output_capture_failed",
                        error=f"{type(exc).__name__}: {str(exc)[:160]}",
                        approval_id=request.approval_id)
            return StepOutcome(
                output=f"mcp:{request.tool_name}:{holder['result'].status}",
                mode="deterministic", confidence=1.0)

        loop.run(handler=handler, max_steps=1)
        result = holder["result"]
        result.loop_id = loop.loop_id
        _observe_terminal(selected, request, result, effect=tool.effect)
        return result


def _observe_terminal(services: McpInvocationServices,
                      request: McpCallRequest, result: McpCallResult, *,
                      effect: str = "") -> None:
    services.runtime.emit(RuntimeObservation(
        "mcp_call_terminal",
        {"server_id": request.server_id,
         "tool_name": request.tool_name,
         "status": result.status,
         "effect": effect,
         "request_digest": request.digest,
         "has_output_ref": bool(result.output_ref),
         "has_approval": bool(result.approval_id),
         "error_code": result.error_code},
        loop_id=result.loop_id))


def self_test() -> dict:
    """Run exact approval, timeout, schema, artifact, and event checks."""
    from .mcp_adapter_checks import run_checks
    return run_checks()


def _raise_fixture_failure():
    raise RuntimeError("fixture transport failure")
