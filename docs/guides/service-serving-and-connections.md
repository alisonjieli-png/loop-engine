# Serving and connections

Kind: reference for a paying customer and for anyone writing a client. It
states the protocol, the transport, what the handshake exchanges, what happens
when versions disagree, how sessions behave, and every refusal a client can
meet with its exact code.

The facts below were read from the service source in this repository and
confirmed against the deployed service and a local instance on 2026-09-21.
The protocol version facts changed on 2026-09-22 and were confirmed against a
local instance only. A deployment serves them after a release that includes
that change. Each recorded answer is marked **deployed** or **local**.

## The connection in one view

```text
One client request
├── Host and origin           exact Host, and Origin only when the browser sends one
├── Credential                one Authorization header, Bearer, one token
├── Protocol version          2025-11-25 through initialize, or 2026-07-28 on every request
├── Address
│   ├── /mcp                  the protocol transport for a harness
│   └── /api/v1/retrieval     one of the direct JSON addresses
├── Work                      one attempt, inside a worker slot, under a deadline
└── Answer
    ├── service_http_result/v1     on success
    └── service_http_error/v1      on refusal, with a stable code
```

## Protocol and transport

| Fact | Value | Where the service states it |
|---|---|---|
| Protocol versions | `2025-11-25` and `2026-07-28` | `protocol.versions` in the capabilities record |
| Reached through the `initialize` handshake | `2025-11-25` | `protocol.handshake_versions` |
| Named on every request, with no handshake | `2026-07-28` | `protocol.per_request_versions` |
| Transport | `streamable_http` | `protocol.transport` |
| Session state | `stateless` | `protocol.session_state` |
| Endpoint | `/mcp` | The Connect page at `/connect` shows it with the origin filled in |
| External authorization metadata | Not published | `oauth_resource_metadata` is false |

The deployed service reported `sdk_version` as `1.29.1` on 2026-09-21 and
offered `2025-11-25` alone. The source now uses version `2.2.0` of the same
library and offers both versions. A client that asks for a version the
service does not serve is told which versions it does serve, and chooses. The
service never serves a request at a version the client did not name.

Read the capabilities record without a credential at any time:

```bash
curl -sS https://app.baltor.ai/api/v1/capabilities
```

## What the handshake exchanges

**Local.** The request:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize",
 "params": {"protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "documentation-probe", "version": "1.0.0"}}}
```

The answer, delivered as one server-sent event on a `text/event-stream`
response:

```json
{"jsonrpc": "2.0", "id": 1,
 "result": {"protocolVersion": "2025-11-25",
            "capabilities": {"experimental": {}, "tools": {"listChanged": false}},
            "serverInfo": {"name": "loop-engine-intelligence", "version": "1.0.0"}}}
```

Three things are exchanged and nothing else. The client states the protocol
version it wants and names itself. The server states the same protocol
version, the capabilities it offers, which is tools only, and its own name.
No credential, no session identifier and no tenant travel in the message
stream. The credential is carried by the `Authorization` header on every
request, and the service resolves the account from it each time.

After the handshake the client asks for the tool list and gets five tools:
`provisioning_discover`, `provisioning_list`, `provisioning_manifest`,
`provisioning_read` and `intelligence_search`. Each one carries its own input
schema, and `provisioning_read` is the only one the server does not mark as
read only.

### Without a handshake

At `2026-07-28` there is no handshake. Every request names its version in the
`MCP-Protocol-Version` header and again in `_meta`, together with its
capabilities, and names its method in `Mcp-Method`. A client may first ask
which versions the service serves.

**Local**, on 2026-09-22. The request, sent with
`MCP-Protocol-Version: 2026-07-28` and `Mcp-Method: server/discover`:

```json
{"jsonrpc": "2.0", "id": 4, "method": "server/discover",
 "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                      "io.modelcontextprotocol/clientCapabilities": {},
                      "io.modelcontextprotocol/clientInfo": {"name": "documentation-probe", "version": "1.0.0"}}}}
```

The answer, delivered as `application/json`:

```json
{"jsonrpc": "2.0", "id": 4,
 "result": {"cacheScope": "private", "capabilities": {"tools": {"listChanged": false}},
            "resultType": "complete", "supportedVersions": ["2026-07-28", "2025-11-25"],
            "ttlMs": 300000,
            "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "loop-engine-intelligence", "version": "1.0.0"}}}}
```

The tool list at this version is the same five tools. It and the discovery
answer carry `ttlMs` and `cacheScope`: a client may reuse them for five
minutes, and a shared cache may not give them to another caller.

### Headers a client sends and receives

| Header | Direction | Purpose |
|---|---|---|
| `Authorization` | sent | `Bearer` and one token. Exactly one such header, or the request is refused. |
| `Content-Type` | sent | `application/json` on every request that carries a body. |
| `MCP-Protocol-Version` | sent | `2025-11-25` on every `/mcp` request after `initialize`, or `2026-07-28` on every request. |
| `Mcp-Method` | sent | At `2026-07-28`, the method of the request, on every request. |
| `Mcp-Name` | sent | At `2026-07-28`, the tool name of a `tools/call`. |
| `Accept` | sent | `application/json, text/event-stream` for the protocol transport. |
| `X-Content-SHA256` | received | The SHA-256 digest of a downloaded body. |
| `X-Loop-Engine-Record-Type` | received | `service_download/v1` on a download answer. |
| `Retry-After` | received | Whole seconds to wait, on a failed-attempt refusal. |
| `WWW-Authenticate` | received | `Bearer` on an unauthenticated refusal. |

The `Accept` header is not optional on the protocol endpoint. Verified
**local** on 2026-09-21, a `tools/list` sent with `Accept` set to
`application/json` alone was refused with status 406 and a protocol-level
error stating that the client must accept both `application/json` and
`text/event-stream`. That refusal comes from the protocol layer, so it is a
JSON-RPC error object and not a `service_http_error/v1` record. A request that
gets past the protocol layer is always refused in the service's own shape.

## What happens when versions do not match

The version is checked before the service does anything else with a protocol
request, and an `initialize` is treated differently from every other request.

1. An `initialize` always starts the `2025-11-25` handshake, whatever version
   header it carries. When its `protocolVersion` names a version the service
   does not serve, the answer names `2025-11-25` instead. This is the
   negotiation rule of the 2025-11-25 lifecycle: the server answers with a
   version it supports, and the client decides whether to continue. A client
   that cannot speak `2025-11-25` disconnects.
2. Every other request is served at the version in its `MCP-Protocol-Version`
   header. A version the service does not serve is refused with status 400 and
   the error the 2026-07-28 revision defines, code `-32022`, which lists every
   version the service serves, newest first, so that a client can choose one
   and send the request again. A missing header, a repeated one or one that is
   not a version is refused with status 400 and code `-32020`. Nothing is done
   for a refused request.

**Local**, on 2026-09-22, an `initialize` that asked for `2025-06-18` was
answered with status 200 and one server-sent event:

```json
{"jsonrpc": "2.0", "id": 1,
 "result": {"capabilities": {"experimental": {}, "tools": {"listChanged": false}},
            "protocolVersion": "2025-11-25",
            "serverInfo": {"name": "loop-engine-intelligence", "version": "1.0.0"}}}
```

**Deployed**, the release that ran on 2026-09-21 refused that same
`initialize` with status 400 and `unsupported_protocol_version`. That refusal
broke the negotiation rule above. A deployment serves the answer shown here
only after a release that includes this change.

**Local**, a `tools/list` request carrying
`MCP-Protocol-Version: 2025-06-18` was refused with status 400:

```json
{"jsonrpc": "2.0", "id": 2,
 "error": {"code": -32022, "message": "Unsupported protocol version",
           "data": {"supported": ["2026-07-28", "2025-11-25"], "requested": "2025-06-18"}}}
```

**Local**, the same request with no `MCP-Protocol-Version` header:

```json
{"jsonrpc": "2.0", "id": 3,
 "error": {"code": -32020, "message": "The MCP-Protocol-Version header is required"}}
```

These refusals are about the protocol itself, so they come in the protocol's
own error shape and not as a `service_http_error/v1` record: a client chooses
a version from the code and the list. Negotiation is not a downgrade. After
the handshake, a request is never served at a version other than the one it
names, and the service will not reinterpret a request under an older profile. The record
contracts behave the same way: a request record whose `record_type` is not the
exact supported version is refused with `unsupported_version` rather than read
under a guess.

### Clients observed on 2026-09-22

**Local**, each client configured from its published recipe against a local
instance of this source, with no model call:

| Client | Command | Result |
|---|---|---|
| Claude Code 2.1.280 | `claude mcp list` | Connected at `2026-07-28`: `server/discover`, then `tools/list`, with no handshake. Against a local instance of revision `74aa21e`, the source before this change, it asked for `2026-07-28` first, was refused, and fell back to the `2025-11-25` handshake. |
| OpenCode 1.18.32 | `opencode mcp list` | Connected at `2025-11-25` through the handshake. Its request to open a stream was answered with 405 and it continued. |
| Codex 0.155.1 | `codex mcp list` | Listed the configuration. This command does not connect, so it proves no handshake. |

## Session behaviour

Sessions are stateless. The service keeps no per-connection state between
requests, so:

- Every request must carry the credential. There is no login that makes later
  requests implicit.
- The account, its scopes and its disclosure grants are resolved again on
  every request, and again before a metadata answer is released. If your
  permissions change while a search is in flight, the answer is refused with
  `disclosure_grant_changed` rather than delivered under the old permissions.
- There is nothing to close. Stopping the client is enough. A `GET` or a
  `DELETE` on `/mcp`, which open a stream or end a session in the
  `2025-11-25` transport, are refused with status 405 and `Allow: POST`,
  because there is no session and no stream to open.
- A request that reaches its deadline is refused with `deadline_exceeded`. The
  work it started may still finish on the server. The service never retries it
  for you, and a missing answer is not proof that nothing was recorded.

Concurrency is bounded. The deployed service publishes
`concurrent_operations` as 8. A request that arrives when every worker slot is
taken is refused at once with `service_busy` rather than queued.

## Every refusal a client can meet

Every refusal is the same record, `service_http_error/v1`, with a stable
`code`, an `effect_commitment` and `automatic_retry`. `effect_commitment` is
`not_asserted` unless the service can state that a durable effect is pending,
in which case it is `durable_pending`. `automatic_retry` is always false: the
service never repeats your request for you.

### Credential and permission

| Code | Status | Meaning | What to do |
|---|---|---|---|
| `unauthorized` | 401 | No credential, a malformed one, an unknown one, an expired one, or an account that is not enabled. | Check that exactly one `Authorization` header is sent and that the token is current. Create a new client token on `/account`. |
| `insufficient_scope` | 403 | The token is valid but does not hold the scope this operation needs. | Read `scopes` from `/api/v1/session`. Create a token that holds the scope you need. |
| `scope_required` | 403 | The account itself does not hold the scope the operation needs. | The account, not the token, must be granted the scope. Ask your operator. |
| `body_forbidden` | 403 | The account may see the item but may not download its body. | Check `body_allowed` and `entitlement` before you read. Ask your operator for body access. |
| `disclosure_grant_changed` | 403 | Your permissions changed while the request was being answered. | Repeat the request. The answer was refused rather than served under stale permissions. |
| `browser_session_required` | 403 | A signed-in browser session is needed, and a service token was used. | Use the account page in a browser. A client token cannot manage credentials. |
| `invalid_origin` | 403 | The `Origin` header is not an allowed browser origin. | Do not send `Origin` from a server-side client. |
| `invalid_host` | 421 | The `Host` header is not one this service answers for. | Use the published address. |

### The request itself

| Code | Status | Meaning | What to do |
|---|---|---|---|
| `invalid_json` | 400 | The body is not JSON, or an object has a repeated field. | Send well formed JSON with unique field names. |
| `object_required` | 400 | The body is valid JSON but not an object. | Send a JSON object. |
| `unsupported_media_type` | 415 | `Content-Type` is not `application/json`. | Set the header. |
| `unsupported_version` | 400 | `record_type` is not the exact supported version. | Use the version named in this documentation. |
| `unsupported_operation` | 400 | `operation` is not one the service offers. | Use `discover`, `list`, `manifest` or `read`. |
| `invalid_request` | 400 | The fields do not match the operation's schema. | Compare against the tool's input schema. A `read` needs `identity` and `request_id`. |
| `unknown_request_field` | 400 | A field the request contract does not define. | Remove it. The service refuses rather than ignores. |
| `invalid_query` | 400 | The search text is empty, only spaces, or over 4096 bytes. | Send shorter, non-empty text. |
| `unsupported_retrieval_mode` | 400 | `mode` is not `lexical` or `hybrid`. | Use one of those two. |
| `invalid_search_limit` | 400 | `top_n` is not a whole number within the published limit. | Use 1 to the published `search_results` value. |
| `download_requires_read` | 400 | `/api/v1/download` was asked for an operation other than `read`. | Send `read`, or use `/api/v1/provisioning`. |
| `request_limit_exceeded` | 413 | The request body is larger than the published `request_bytes`. | Send a smaller request. |
| `request_body_deadline` | 408 | The body did not arrive within the request deadline. | Send the whole body promptly. |
| `route_unavailable` | 404 | No such address, or not with that method. | Check the address list on this page. |
| `unsupported_protocol_version` | 400 | A `/mcp` request names a protocol version the service does not serve. It comes as protocol error `-32022` with the served versions. | Send a version from the list: `2025-11-25` after the handshake, or `2026-07-28` on every request. |
| `protocol_version_header_missing` | 400 | A `/mcp` request other than `initialize` carries no `MCP-Protocol-Version` header. It comes as protocol error `-32020`. | Send the header with the version you use. |
| `protocol_version_header_repeated` | 400 | The `MCP-Protocol-Version` header appears more than once. It comes as protocol error `-32020`. | Send it once. |
| `protocol_version_header_malformed` | 400 | The `MCP-Protocol-Version` header is not a protocol version. It comes as protocol error `-32020`. | Send a version such as `2025-11-25`. |
| `protocol_method_not_allowed` | 405 | `/mcp` was asked with a method other than `POST`. | Send every protocol message as a `POST`. |

The schema is checked before anything else, so a field that is present but
malformed answers `invalid_request` rather than a more specific code. Verified
**local** on 2026-09-21: a `read` with no `request_id`, a `read` with an empty
`request_id`, an `expected_digest` on an operation that does not take one, and
an `expected_digest` that is not hexadecimal all answered `invalid_request`
with status 400.

### The item and its body

| Code | Status | Meaning | What to do |
|---|---|---|---|
| `item_unavailable` | 404 | No such item for this account, or the `expected_digest` you sent does not match the item. The service does not reveal whether the item exists for anyone else. | List what you may see first. Search again to pick up a changed digest. Ask your operator for a grant. |
| `item_withheld` | 400 | The item exists for you but your request's filters exclude it. | Relax `style`, `kinds` or `authority_effects`. |
| `download_required` | 413 | The body is larger than the published `inline_body_bytes`. | Use `/api/v1/download`. |
| `download_limit_exceeded` | 413 | The body is larger than the published `download_bytes`. | The service will not deliver it. Ask your operator. |
| `response_limit_exceeded` | 413 | The answer is larger than the published `response_bytes`. | Ask for fewer results with `top_n`. |
| `body_integrity_failed` | 400 | The stored body does not match the item's digest or size. | Report it. Do not use the material. |
| `body_reader_unavailable` | 400 | The host cannot read the body at all. | Report it to your operator. |
| `meter_unavailable` | 400 | The item requires metering and the meter is not installed. | Report it to your operator. |
| `meter_commit_unknown` | 503 | The measured unit may or may not have been recorded. | Retry with the **same** `request_id`. A repeat with the same identity is not measured twice. |
| `commit_unknown` | 503 | A durable write was attempted and its outcome is unknown. | Read the current state before acting. Do not assume it failed. |

### Rate, capacity and time

| Code | Status | Meaning | What to do |
|---|---|---|---|
| `failed_attempt_limit_reached` | 429 | This client address made too many refused attempts inside the window. | Wait the number of seconds in `Retry-After` and in `retry_after_seconds`. Fix the credential before trying again. |
| `service_busy` | 503 | Every worker slot is in use. | Retry after a short pause. Lower your concurrency. |
| `deadline_exceeded` | 504 | The operation did not finish inside the request deadline. | Do not assume nothing happened. Read `/api/v1/usage` before repeating a body read, or repeat with the same `request_id`. |

**Local.** The failed-attempt refusal, exactly as returned, after three
refused attempts from one address against an instance configured with
`client_address_source` set to `socket_peer` and `failures_allowed` set to 3:

```json
{"record_type": "service_http_error/v1",
 "error": {"code": "failed_attempt_limit_reached",
           "details": {"record_type": "service_request_limit_refusal/v1",
                       "retry_after_seconds": 21}},
 "effect_commitment": "not_asserted", "automatic_retry": false}
```

The header `Retry-After` carried `21` on the same answer. The limit counts
refused attempts that carried a credential. A request with no credential at
all is refused without being counted. The limit is active only when the host
states where the client address comes from; until then the capabilities record
reports `failed_attempts_per_address` as inactive. The deployed pilot answers
from an image built before this limit was published, so its capabilities
record does not yet carry `failed_attempts_per_address` at all.

### Managing your own client tokens

These refusals belong to `/api/v1/account/access`, which the account page
uses. A client token cannot reach them.

| Code | Status | Meaning | What to do |
|---|---|---|---|
| `access_writes_not_authorized` | 403 | The host has not authorized credential writes. | Ask your operator. |
| `access_target_forbidden` | 403 | The request named an account that is not yours. | Do not send another account's identity. |
| `scope_escalation_refused` | 403 | The token asked for a scope the account or the session does not hold. | Ask for a subset of your own scopes. |
| `access_lifetime_exceeded` | 400 | The requested lifetime is longer than the policy allows. | Ask for a shorter lifetime. |
| `access_token_limit_reached` | 409 | You already hold the maximum number of active tokens. | Revoke one first. |
| `access_token_history_limit_reached` | 409 | The stored token history is full. | Ask your operator. |
| `access_token_already_revoked` | 409 | That token was already revoked. | Nothing to do. |
| `access_request_identity_conflict` | 409 | The same request identity was reused with different contents. | Use a new request identity. |
| `managed_access_token_not_found` | 404 | No such token for you. | Refresh the list on `/account`. |
| `concurrent_update` | 409 | Another change landed first. | Read the current list and try again. |
| `tenant_disabled` | 401 | The account is not enabled. | Ask your operator. |
| `client_access_unavailable` | 503 | Customer credential management is not installed on this service. | Ask your operator for a token. |
| `invalid_access_request` | 400 | The request record is malformed. | Use the account page. |

## Addresses this service answers

| Address | Method | Credential | Purpose |
|---|---|---|---|
| `/mcp` | POST | yes | The protocol transport a harness connects to. |
| `/api/v1/capabilities` | GET | no | Protocol, limits, delivery and billing facts. |
| `/api/v1/health` | GET | no | A liveness answer. It does not check readiness. |
| `/api/v1/session` | GET | yes | The account, mode, scopes and expiry behind your token. |
| `/api/v1/retrieval` | POST | yes | Search over authorized metadata. |
| `/api/v1/provisioning` | POST | yes | `discover`, `list`, `manifest` and inline `read`. |
| `/api/v1/download` | POST | yes | A body as bytes, with its digest in a header. |
| `/api/v1/usage` | GET | yes | Your own measured usage. |
| `/api/v1/account/access` | GET, POST | yes | Your own client tokens, from a browser session. |
| `/api/v1/account/identity` | GET | no | The identity provider settings the browser needs. |
| `/api/v1/billing/plans` | GET | yes | The plans this service offers. |

`/.well-known/oauth-protected-resource/mcp` exists only when the service is
configured for external tokens. On the deployed service it answers
`external_authorization_not_configured` with status 404.

## Related pages

- [Getting set up](service-getting-set-up.md)
- [Searching and retrieving](service-searching-and-retrieving.md)
- [Troubleshooting](service-troubleshooting.md)
- [Service interface conventions](../standards/SERVICE-INTERFACE-CONVENTIONS.md),
  for why the codes are shaped this way
