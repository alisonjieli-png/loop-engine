"""The staff transports: the protocol endpoint `/admin/mcp` and the staff routes under `/api/v1/admin/`.

Kind: remote transport adapters over the staff tools. Each call runs as one
governed operation through `invoke_http_service_as_loop`, the envelope of the
existing boundary "remote intelligence service operation". They add no runtime
type, no store and no graph vertex.

```text
Staff transports
├── POST /admin/mcp
│   ├── the same protocol library and version negotiation as /mcp, one
│   │   stateless Streamable HTTP endpoint, 2025-11-25 and 2026-07-28
│   ├── a staff key and nothing else: a customer key, a host key or a browser
│   │   session is refused with staff_credential_required
│   └── the tool list names only the tools the key's role may call
├── POST /api/v1/admin/tools/<tool>
│   ├── the same arguments and the same answer as the protocol tool
│   └── a staff key, or a signed-in staff browser session for the
│       Administration page; a customer key is refused with staff_role_required
└── GET and POST /api/v1/admin/staff-keys
    └── a superadmin browser session lists, mints and revokes staff keys; a
        staff key never reaches this route, so a leaked key cannot mint another
```

Refused credentials are counted by the existing failed-attempt limit for each
client address, before any key is looked up.
"""
from __future__ import annotations

import json

from .http import (EXTERNAL_PROVIDER_SHARE, PROTOCOL_CACHE_SCOPE, PROTOCOL_CACHE_TTL_MS, ServiceHttpError,
                   _error_record, _parse_json, _status, invoke_http_service_as_loop)
from .http_auth import HttpAuthenticationError
from .observability import SCOPE_REFERENCE_KEY
from .staff_keys import BROWSER_SESSION, KEY_PREFIX, StaffKeyRequest
from .staff_routes import STAFF_KEYS_PATH, STAFF_TOOL_ROUTES

#: The ASGI scope key that carries the verified staff caller of one protocol request.
STAFF_ACTOR_KEY = "service_staff_actor"
SERVER_NAME = "baltor-staff-tools"


def _bearer(request, missing):
    values = request.headers.getlist("authorization")
    if len(values) != 1:
        raise HttpAuthenticationError(missing)
    value = values[0]
    if not value.startswith("Bearer ") or value.count(" ") != 1 or len(value) > 16_384:
        raise HttpAuthenticationError(missing)
    return value[7:]


def _tools(application):
    tools = getattr(application, "staff_tools", None)
    if tools is None:
        raise ServiceHttpError("staff_tools_unavailable", 503)
    return tools


async def staff_protocol_actor(application, request):
    """The staff key behind one request to `/admin/mcp`; nothing else is accepted there."""
    tools = _tools(application)
    credential = _bearer(request, "staff_credential_required")
    async with application._limited(request):
        return await application._work(lambda: tools.keys.authenticate(credential))


def _session_staff(application, context):
    current = application.authenticator.revalidate(context)
    return application.account_administration.staff_session(current, application.authenticator.credential_digest(current))


async def staff_route_actor(application, request, *, keys_allowed):
    """A staff key, or a staff member's signed-in browser session, behind one staff route request."""
    tools = _tools(application)
    credential = _bearer(request, "unauthorized")
    if credential.startswith(KEY_PREFIX):
        if not keys_allowed:
            raise ServiceHttpError("browser_session_required", 403)
        async with application._limited(request):
            return await application._work(lambda: tools.keys.authenticate(credential))
    context = await application._authenticated(request)
    staff = await application._work(lambda: _session_staff(application, context), shares=(EXTERNAL_PROVIDER_SHARE,))
    return tools.keys.session_actor(staff)


async def _staff_body(application, request):
    body = await application._body(request)
    return _parse_json(body)


async def staff_route(application, request, path):
    """Answer one staff route: a staff key page request or one staff tool call."""
    tools = _tools(application)
    if request.query_params:
        raise ServiceHttpError("unknown_request_field")
    reference = request.scope[SCOPE_REFERENCE_KEY]
    if path == STAFF_KEYS_PATH:
        actor = await staff_route_actor(application, request, keys_allowed=False)
        if actor.kind != BROWSER_SESSION:
            raise ServiceHttpError("browser_session_required", 403)
        if request.method == "POST":
            wanted = StaffKeyRequest.from_dict(await _staff_body(application, request))
            work = lambda: tools.keys.apply(actor.session, wanted, reference)
        else:
            work = lambda: tools.keys.listing(actor.session)
        return await application._work(lambda: invoke_http_service_as_loop("staff_keys", work), shares=(actor.share,))
    name = STAFF_TOOL_ROUTES[path]
    actor = await staff_route_actor(application, request, keys_allowed=True)
    arguments = await _staff_body(application, request)
    tool = tools.tools.get(name)
    shares = (actor.share, EXTERNAL_PROVIDER_SHARE) if tool is not None and tool.provider_reads else (actor.share,)
    return await application._work(lambda: invoke_http_service_as_loop(
        "staff_" + name, lambda: tools.call(actor, name, arguments, reference, "http")), shares=shares)


def _refresh(tools, actor):
    """Check a staff key again for a protocol request that reads no record of its own."""
    with tools.runtime._catalog.store() as store:
        tools.keys.current_guards(store, actor)


def staff_protocol_server(application):
    """The protocol library's server for the staff tools, bound to the versions the host serves."""
    import mcp.types as types
    from mcp.server.caching import CacheHint
    from mcp.server.lowlevel import Server
    tools = _tools(application)
    configuration = application.configuration

    async def list_tools(ctx, _params):
        actor = ctx.request.scope[STAFF_ACTOR_KEY]
        await application._work(lambda: _refresh(tools, actor), shares=(actor.share,))
        return types.ListToolsResult(tools=[types.Tool(
            name=tool.name, description=tool.description, inputSchema=tool.input_schema(),
            annotations=types.ToolAnnotations(readOnlyHint=not tool.effect, destructiveHint=tool.effect,
                                              idempotentHint=not tool.effect, openWorldHint=tool.provider_reads))
            for tool in tools.visible(actor)])

    async def call_tool(ctx, params):
        name, arguments = params.name, params.arguments or {}
        scope = ctx.request.scope
        reference = scope.get(SCOPE_REFERENCE_KEY)
        try:
            actor = scope[STAFF_ACTOR_KEY]
            tool = tools.tools.get(name)
            shares = (actor.share, EXTERNAL_PROVIDER_SHARE) if tool is not None and tool.provider_reads else (actor.share,)
            output = await application._work(lambda: invoke_http_service_as_loop(
                "staff_" + (name if tool is not None else "unknown"),
                lambda: tools.call(actor, name, arguments, reference, "mcp")), shares=shares)
            text = json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            response = types.CallToolResult(content=[types.TextContent(type="text", text=text)],
                                            structuredContent=output, isError=False)
            if len(response.model_dump_json(by_alias=True).encode()) > configuration.maximum_response_bytes:
                raise ServiceHttpError("response_limit_exceeded", 413)
            return response
        except Exception as error:
            status, code = _status(error)
            details = error.details if isinstance(error, ServiceHttpError) else None
        await application._record_failure(scope, ctx.request, code, status)
        refused = _error_record(code, status, details, reference.value if reference is not None else None)
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(refused))],
                                    structuredContent=refused, isError=True)

    hint = CacheHint(ttl_ms=PROTOCOL_CACHE_TTL_MS, scope=PROTOCOL_CACHE_SCOPE)
    sdk = Server(SERVER_NAME, version="1.0.0", on_list_tools=list_tools, on_call_tool=call_tool,
                 cache_hints={"tools/list": hint, "server/discover": hint})

    async def discover(ctx, _params):
        actor = ctx.request.scope[STAFF_ACTOR_KEY]
        await application._work(lambda: _refresh(tools, actor), shares=(actor.share,))
        return types.DiscoverResult(supported_versions=list(reversed(configuration.protocol_versions)),
                                    capabilities=sdk.get_capabilities(protocol_version=ctx.protocol_version))
    sdk.add_request_handler("server/discover", types.RequestParams, discover)
    # The library records every protocol message as a trace span by default,
    # and the service has no telemetry setting for protocol traffic.
    sdk.middleware = []
    return sdk


def staff_protocol_manager(application):
    """One stateless Streamable HTTP manager for the staff endpoint, or None when no staff tools are installed."""
    if getattr(application, "staff_tools", None) is None:
        return None
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp.server.transport_security import TransportSecuritySettings
    config = application.configuration
    return StreamableHTTPSessionManager(staff_protocol_server(application), stateless=True,
        security_settings=TransportSecuritySettings(allowed_hosts=list(config.allowed_hosts),
                                                   allowed_origins=list(config.allowed_origins)),
        max_request_body_size=config.maximum_request_bytes)
