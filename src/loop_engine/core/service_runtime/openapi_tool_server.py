"""Baltor Connect's OpenAPI tool server: the library's read surface as three plain HTTP operations.

Kind: a second binding of three existing protocol tools (engine slot `protocol_endpoint`, interaction
`core.interaction.service.protocol_tool_call`). It adds no runtime type, store, scope, grant or authority. Each
operation calls the dispatch the `/mcp` tools call (`ServiceHttpApplication._protocol_output`) with the same input
schema, scopes, metering and refusals. Only the envelope differs: an HTTP POST whose JSON body is the tool's
arguments, answered with the `service_http_result/v1` record the tool returns.

```text
/api/v1/connect
├── GET  /openapi.json  the OpenAPI 3.1 document of the three operations; public, no credential needed
├── POST /search        intelligence_search      scope provisioning:metadata; never counted
├── POST /manifest      provisioning_manifest    scope provisioning:metadata; never counted
└── POST /read          provisioning_read        scope provisioning:read; counted as the protocol tool counts
```

Why it exists. Open WebUI lets a person add a tool server of their own under Settings, Integrations, and that path
takes OpenAPI servers only. The person's browser then calls the server directly: it fetches the document with the
bearer token in the Authorization header, and sends each tool call as a POST with Authorization, Content-Type and
X-Session-Id (Open WebUI 0.11.4, `src/lib/apis/index.ts`, `getToolServerData` and `executeToolServer`, read on
October 9, 2026). A browser call from another site needs a cross-origin policy, which the rest of this service
refuses on purpose, so this surface has its own policy and nothing else shares it:

- any origin may call it, because its only credential is the bearer token the person entered, never ambient state;
- no cookie or other browser credential is accepted or invited: the answers carry
  `Access-Control-Allow-Origin: *` and never `Access-Control-Allow-Credentials`, and browsers never send a
  credentialed request on that answer;
- a preflight is accepted only for the one method its address serves, and only for the request headers named in
  `ALLOWED_REQUEST_HEADERS`; any other method or header is refused before the browser sends the request.

Prior art considered on October 9, 2026: Open WebUI's `mcpo` turns an MCP server into an OpenAPI server, but it is a
separate process that holds one credential for everyone who reaches it, which makes a personal connection a shared
one; the FastAPI example in Open WebUI's tool server FAQ allows every origin, method and header together with
credentials, which is the policy this surface refuses. Both were rejected for this binding.
"""
from __future__ import annotations

#: The address under which the tool server lives. A host that adds the server by its address (Open WebUI's URL
#: field) and reads the document at its default path `openapi.json` reaches the document below.
BASE_PATH = "/api/v1/connect"
DOCUMENT_PATH = BASE_PATH + "/openapi.json"
SEARCH_PATH = BASE_PATH + "/search"
MANIFEST_PATH = BASE_PATH + "/manifest"
READ_PATH = BASE_PATH + "/read"
#: Each operation's address and the protocol tool it calls. The tool's name is the operation's `operationId`, so a
#: model sees the same tool names over this surface as over `/mcp`, and one skill describes both.
OPERATIONS = {SEARCH_PATH: "intelligence_search", MANIFEST_PATH: "provisioning_manifest",
              READ_PATH: "provisioning_read"}
#: Every address of the surface and the one method it serves. The service's route table includes these.
ROUTES = {DOCUMENT_PATH: ("GET",), **{path: ("POST",) for path in OPERATIONS}}
#: The version of this surface's own contract, stated as the document's `info.version`.
DOCUMENT_VERSION = "1.0.0"
OPENAPI_VERSION = "3.1.0"
#: The request headers a browser may ask to send. Open WebUI 0.11.4 sends Authorization and Content-Type on every
#: call and X-Session-Id on a call made in a chat; Baltor-Step-Effects is the service's own documented header,
#: which a client configuration may set. A safelisted header such as Accept needs no permission and is not listed.
ALLOWED_REQUEST_HEADERS = ("authorization", "content-type", "x-session-id", "baltor-step-effects")
ALLOWED_REQUEST_HEADER_NAMES = ("Authorization", "Content-Type", "X-Session-Id", "Baltor-Step-Effects")
#: How long a browser may reuse an accepted preflight, in seconds. The policy changes only with a release.
PREFLIGHT_MAX_AGE_SECONDS = 600
#: The refusal of a preflight this surface does not accept. It is answered without any sharing header, so the
#: browser does not send the request the preflight asked about.
REFUSAL_CODE = "cross_origin_request_refused"
#: What the answers of this surface carry for a browser caller, whichever origin it names.
SHARED_RESPONSE_HEADERS = {"Access-Control-Allow-Origin": "*"}
SECURITY_SCHEME = "baltor_client_token"


class CrossOriginRefusal(ValueError):
    """A preflight this surface refuses. `reason` is one fixed word, never text from the request."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def handles(path):
    """Whether an address belongs to this surface and is answered under its cross-origin policy."""
    return path in ROUTES


def preflight(path, origins, request_methods, request_headers):
    """The headers of an accepted preflight for `path`, or `CrossOriginRefusal` naming why it is refused.

    `origins`, `request_methods` and `request_headers` are every value the request sent for `Origin`,
    `Access-Control-Request-Method` and `Access-Control-Request-Headers`. A preflight names exactly one origin and
    exactly one method, the method its address serves, and asks only for headers this surface allows."""
    methods = ROUTES.get(path)
    if methods is None:
        raise CrossOriginRefusal("address")
    if len(origins) != 1 or not origins[0].strip():
        raise CrossOriginRefusal("origin")
    if len(request_methods) != 1 or request_methods[0] not in methods:
        raise CrossOriginRefusal("method")
    asked = [name.strip().lower() for value in request_headers for name in value.split(",") if name.strip()]
    if any(name not in ALLOWED_REQUEST_HEADERS for name in asked):
        raise CrossOriginRefusal("header")
    return {**SHARED_RESPONSE_HEADERS, "Access-Control-Allow-Methods": ", ".join(methods),
            "Access-Control-Allow-Headers": ", ".join(ALLOWED_REQUEST_HEADER_NAMES),
            "Access-Control-Max-Age": str(PREFLIGHT_MAX_AGE_SECONDS)}


def response_headers(origins):
    """The sharing headers of an answer on this surface: `*` for a browser caller, nothing for any other caller."""
    return dict(SHARED_RESPONSE_HEADERS) if len(origins) == 1 else {}


#: One line for each operation, shown as its OpenAPI summary. The full description is the protocol tool's own.
SUMMARIES = {"intelligence_search": "Search the Baltor library's metadata",
             "provisioning_manifest": "Describe one item version before reading it",
             "provisioning_read": "Read the exact files of one selected item version"}
RESULT_RECORD = "service_http_result/v1"
ERROR_RECORD = "service_http_error/v1"
RESULT_SCHEMA = {
    "type": "object", "required": ["record_type", "operation", "result"],
    "properties": {"record_type": {"const": RESULT_RECORD}, "operation": {"type": "string"},
                   "result": {"type": "object", "description": "The tool's own record: service_retrieval_result/v1, "
                              "provisioning_manifest/v3, provisioning_body/v3 or provisioning_package_read/v1."},
                   "execution": {"type": "object"}}}
ERROR_SCHEMA = {
    "type": "object", "required": ["record_type", "error"],
    "properties": {"record_type": {"const": ERROR_RECORD},
                   "error": {"type": "object", "required": ["code", "message", "next_action"],
                             "properties": {"code": {"type": "string"}, "message": {"type": "string"},
                                            "next_action": {"type": "string"}, "details": {"type": "object"}}},
                   "request_reference": {"type": "string"}}}
DOCUMENT_DESCRIPTION = (
    "Search Baltor's library of harness components, inspect one item version, and read its exact files. Every "
    "operation reads; none installs, runs or changes anything. Send a Baltor client token as a bearer token in "
    "the Authorization header: create one on your account page, and keep it out of prompts and files. Search and "
    "manifests are never counted; the first read of an item version in a calendar month counts once. Check each "
    "file's SHA-256 against its digest before you use it. Browsers may call these operations from any site with "
    "the bearer token alone; no cookie is accepted. The same operations are the intelligence_search, "
    "provisioning_manifest and provisioning_read tools of the Model Context Protocol endpoint at /mcp.")


def document(base_url, tools):
    """The OpenAPI 3.1 document of this surface for a service published at `base_url`.

    `tools` maps each protocol tool name in `OPERATIONS` to `(description, input_schema)`, the values the protocol
    endpoint lists for that tool, so the document cannot describe a tool differently from the endpoint."""
    paths = {}
    for path, tool in OPERATIONS.items():
        description, schema = tools[tool]
        paths[path[len(BASE_PATH):]] = {"post": {
            "operationId": tool, "summary": SUMMARIES[tool], "description": description,
            "requestBody": {"required": True, "content": {"application/json": {"schema": schema}}},
            "responses": {
                "200": {"description": "The tool's record inside the service's result wrapper.",
                        "content": {"application/json": {"schema": RESULT_SCHEMA}}},
                "default": {"description": "A refusal: its code, a plain message and the next action.",
                            "content": {"application/json": {"schema": ERROR_SCHEMA}}}}}}
    return {"openapi": OPENAPI_VERSION,
            "info": {"title": "Baltor library", "version": DOCUMENT_VERSION, "summary":
                     "Search, inspect and read Baltor harness components over plain HTTP.",
                     "description": DOCUMENT_DESCRIPTION},
            "servers": [{"url": base_url + BASE_PATH}],
            "security": [{SECURITY_SCHEME: []}],
            "components": {"securitySchemes": {SECURITY_SCHEME: {
                "type": "http", "scheme": "bearer",
                "description": "A Baltor client token from your account page, sent as Authorization: Bearer."}}},
            "paths": paths}


def document_problems(served, routes, tools, base_url):
    """Every way a served document disagrees with the routes the service answers and the tools it lists.

    `routes` is the service's route table, `tools` maps each protocol tool name to `(description, input_schema)` as
    the protocol endpoint lists it, and `base_url` is the service's published base. An empty list means the
    document names exactly this surface's addresses, each with the method the service answers, the tool it calls,
    that tool's description and that tool's input schema."""
    problems = []
    if served.get("openapi") != OPENAPI_VERSION:
        problems.append("the document is not OpenAPI " + OPENAPI_VERSION)
    servers = served.get("servers") or []
    base = servers[0].get("url") if servers and isinstance(servers[0], dict) else None
    if base != base_url + BASE_PATH:
        problems.append("the document's server is not the service's published base followed by " + BASE_PATH)
    prefix = BASE_PATH if base is None else base[len(base_url):] if base.startswith(base_url) else BASE_PATH
    seen = set()
    for relative, item in (served.get("paths") or {}).items():
        address = prefix + relative
        for method, operation in (item or {}).items():
            seen.add(address)
            if method.upper() not in routes.get(address, ()):
                problems.append(f"{method.upper()} {address} is in the document and the service does not answer it")
                continue
            tool = OPERATIONS.get(address)
            if tool is None or operation.get("operationId") != tool:
                problems.append(f"{address} names operation {operation.get('operationId')!r}, not the tool it calls")
                continue
            description, schema = tools[tool]
            body = (((operation.get("requestBody") or {}).get("content") or {}).get("application/json") or {})
            if body.get("schema") != schema:
                problems.append(f"{address} documents a request schema that is not the {tool} tool's input schema")
            if operation.get("description") != description:
                problems.append(f"{address} documents a description that is not the {tool} tool's description")
    for address in OPERATIONS:
        if address not in seen:
            problems.append(f"{address} is served and the document does not name it")
    return problems
