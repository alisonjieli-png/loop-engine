"""MCP Python SDK transport for registered Loop Engine MCP servers.

The transport supports stdio, Streamable HTTP, and SSE through the official
MCP Python SDK. Tool effects come from caller-owned policy data and never from
model-generated descriptions. Credentials are resolved from references only
when a connection is opened.

This module is the declared subprocess boundary for stdio MCP servers.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Mapping

from .mcp_adapter import (McpCallRequest, McpDiscoveryPolicy,
                          McpInvocationServices, McpRegistry, McpServerSpec,
                          McpToolSpec, McpTransport)
from .runtime_observer import RuntimeObservationServices


@dataclass(frozen=True)
class McpToolPolicy:
    effect: str
    requires_approval: bool


class McpSdkTransport(McpTransport):
    """Synchronous facade over the official SDK's async client sessions."""

    timeout_enforced = True
    _STDIO_ENV_ALLOWLIST = (
        "LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR",
        "WINDIR")

    def __init__(self, policies: Mapping[str, McpToolPolicy]):
        self.policies = dict(policies)

    @staticmethod
    def _run(coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "McpSdkTransport synchronous methods cannot run inside an active "
            "event loop; inject an async application transport")

    @staticmethod
    def _credential_values(server: McpServerSpec) -> dict[str, str]:
        values = {}
        for ref in server.credential_refs:
            if ref.startswith("env:"):
                name = ref.split(":", 1)[1]
                value = os.environ.get(name, "")
                if value:
                    values[name] = value
        return values

    @staticmethod
    def _stdio_environment(server: McpServerSpec) -> dict[str, str]:
        environment = {
            name: os.environ[name]
            for name in McpSdkTransport._STDIO_ENV_ALLOWLIST
            if os.environ.get(name)
        }
        environment.update({
            "PYTHONUNBUFFERED": "1",
            "PYTHONUTF8": "1",
        })
        environment.update(McpSdkTransport._credential_values(server))
        return environment

    @staticmethod
    def _client(server: McpServerSpec):
        if server.transport == "stdio":
            from mcp import StdioServerParameters
            from mcp.client.stdio import stdio_client
            params = StdioServerParameters(
                command=server.command[0], args=list(server.command[1:]),
                env=McpSdkTransport._stdio_environment(server))
            return stdio_client(params)
        headers = {}
        values = McpSdkTransport._credential_values(server)
        if values:
            headers["Authorization"] = "Bearer " + next(iter(values.values()))
        if server.transport == "streamable_http":
            from mcp.client.streamable_http import streamablehttp_client
            return streamablehttp_client(server.url, headers=headers)
        if server.transport == "sse":
            from mcp.client.sse import sse_client
            return sse_client(server.url, headers=headers)
        raise ValueError(
            "McpSdkTransport does not own in_process transports")

    async def _with_session(self, server: McpServerSpec, operation):
        from mcp import ClientSession
        async with self._client(server) as streams:
            read_stream, write_stream = streams[:2]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await operation(session)

    def list_tools(self, server: McpServerSpec, *,
                   timeout_seconds: float = 60.0) -> tuple[McpToolSpec, ...]:
        async def operation(session):
            response = await session.list_tools()
            tools = []
            for item in response.tools:
                policy = self.policies.get(item.name)
                if policy is None:
                    continue
                input_schema = (getattr(item, "inputSchema", None)
                                or getattr(item, "input_schema", None) or {})
                tools.append(McpToolSpec(
                    server.server_id, item.name,
                    str(item.description or item.name),
                    dict(input_schema),
                    policy.effect, policy.requires_approval))
            return tuple(tools)
        return self._run(asyncio.wait_for(
            self._with_session(server, operation), timeout=timeout_seconds))

    def call_tool(self, server: McpServerSpec,
                  request: McpCallRequest) -> object:
        async def operation(session):
            response = await session.call_tool(
                request.tool_name, request.transport_arguments())
            if hasattr(response, "model_dump"):
                return response.model_dump(mode="json")
            return response
        return self._run(asyncio.wait_for(
            self._with_session(server, operation),
            timeout=request.timeout_seconds))


def self_test() -> dict:
    """Exercise a real local stdio MCP session without network access."""
    import sys
    import tempfile
    from pathlib import Path

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    try:
        import mcp  # noqa: F401
    except ImportError:
        return {"tests": [{
            "test": "official_mcp_sdk_is_installed",
            "passed": False,
            "detail": "mcp is a declared Loop Engine dependency"}],
            "passed": 0, "total": 1, "all_passed": False}

    with tempfile.TemporaryDirectory(prefix="loop-engine-mcp-sdk-") as root:
        script = Path(root) / "server.py"
        script.write_text(
            "import asyncio\n"
            "from mcp.server.fastmcp import FastMCP\n"
            "server = FastMCP('loop-engine-official-sdk-test')\n"
            "@server.tool(description='Add two integers')\n"
            "def add(a: int, b: int) -> int:\n"
            "    return a + b\n"
            "@server.tool(description='Wait before returning')\n"
            "async def slow(delay: float) -> str:\n"
            "    await asyncio.sleep(delay)\n"
            "    return 'late'\n"
            "if __name__ == '__main__':\n"
            "    server.run(transport='stdio')\n",
            encoding="utf-8")
        server = McpServerSpec(
            "sdk-fixture", "stdio", command=(sys.executable, str(script)),
            credential_refs=("env:LOOP_ENGINE_MCP_ALLOWED_TEST",),
            tool_allowlist=("add", "slow"))
        transport = McpSdkTransport({
            "add": McpToolPolicy("pure", False),
            "slow": McpToolPolicy("pure", False),
        })
        environment_names = (
            "LOOP_ENGINE_MCP_ALLOWED_TEST", "LOOP_ENGINE_MCP_FORBIDDEN_TEST")
        previous_environment = {
            name: os.environ.get(name) for name in environment_names}
        os.environ[environment_names[0]] = "fixture-credential"
        os.environ[environment_names[1]] = "must-not-cross"
        spawned_environment = transport._stdio_environment(server)
        check("stdio_environment_is_an_explicit_minimal_allowlist",
              spawned_environment.get("LOOP_ENGINE_MCP_ALLOWED_TEST")
              == "fixture-credential"
              and "LOOP_ENGINE_MCP_FORBIDDEN_TEST" not in spawned_environment
              and set(spawned_environment) <= (
                  set(transport._STDIO_ENV_ALLOWLIST)
                  | {"PYTHONUNBUFFERED", "PYTHONUTF8",
                     "LOOP_ENGINE_MCP_ALLOWED_TEST"}))
        from ..loop.recursive_loop import LoopLedger
        from .context_artifacts import (
            ContextArtifactManager, ContextArtifactServices,
            ContextArtifactStore, ContextArtifactStoreSpec)
        ledger = LoopLedger()
        runtime = RuntimeObservationServices(ledger=ledger)
        artifacts = ContextArtifactManager(ContextArtifactServices(
            ContextArtifactStore(ContextArtifactStoreSpec(root)), runtime))
        registry = McpRegistry()
        registry.register(server, transport)
        tools = registry.discover(
            "sdk-fixture", runtime=runtime,
            policy=McpDiscoveryPolicy(allowed_effects=("spawns_process",)))
        check("official_FastMCP_server_lists_policy_classified_stdio_tool",
              [tool.name for tool in tools] == ["add", "slow"]
              and tools[0].input_schema.get("type") == "object")
        result = registry.invoke(
            McpCallRequest("sdk-fixture", "add", {"a": 2, "b": 3}),
            services=McpInvocationServices(
                runtime=runtime, artifact_manager=artifacts))
        text = str(result.output)
        check("official_FastMCP_server_executes_through_the_SDK_client",
              result.status == "completed" and result.loop_id.startswith("loop")
              and "5" in text and ("isError" in text or "is_error" in text)
              and any(event.get("event") == "mcp_call_terminal"
                      and event.get("status") == "completed"
                      for event in ledger.events),
              text[:200])
        timed_out = registry.invoke(
            McpCallRequest(
                "sdk-fixture", "slow", {"delay": 1.0},
                timeout_seconds=0.01),
            services=McpInvocationServices(
                runtime=runtime, artifact_manager=artifacts))
        check("official_SDK_call_timeout_is_enforced",
              timed_out.status == "failed"
              and timed_out.error_code == "transport_failed")
        for name, previous in previous_environment.items():
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous

    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
