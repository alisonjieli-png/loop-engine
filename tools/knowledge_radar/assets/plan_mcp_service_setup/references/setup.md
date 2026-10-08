# Setup checklist

Use only the parts relevant to the chosen client and service.

| Check | Evidence to keep | Stop condition |
|---|---|---|
| Publisher and purpose | Official documentation URL, dated registry identity and the operation needed | Similar name without a matching publisher or purpose |
| Endpoint and transport | Exact public HTTPS endpoint and current transport declaration | Conflicting declarations or a redirect to an unreviewed origin |
| Client compatibility | Supported protocol and transport from the client's current documentation | Unsupported version; do not silently change transport |
| Authentication | Documented method and requested scopes, with credential values omitted | Unknown scopes, unavailable sign-in or authority not granted |
| Tool inventory | Observed tool names, input schemas and declared effects | A listing alone, undocumented writes or a changed schema |
| Trial | One authorized harmless read, its timestamp and outcome | Refusal or unknown outcome; do not retry a possible mutation |

Cloudflare's publisher page directs new connections to `/mcp` with Streamable
HTTP. Its historical `/sse` URLs are aliases, not the old SSE transport.
The API MCP endpoint supports OAuth and scoped API tokens. Its operations can
change account resources, so discovery must not imply permission to execute.
[Publisher documentation](https://developers.cloudflare.com/agents/model-context-protocol/cloudflare/servers-for-cloudflare/).

The MCP Registry list API supports name-substring search, an opaque cursor,
`updated_since` and `version=latest`. An incremental response may include
deleted entries; retain tombstones rather than leaving removed servers active.
Follow the caller's request ceiling and preserve the exact cursor when a scan
stops. A short page with a cursor is partial coverage, not a complete search.
[Registry API specification](https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/reference/api/openapi.yaml).

Record a successful connection separately from a successful tool call. An
authentication method documented by a publisher is not proof that the current
account is linked. A tool's read-only annotation is a claim to inspect, not
permission to use it or a substitute for a bounded effect policy.
