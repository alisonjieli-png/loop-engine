# Serving and connections

Kind: technical reference for the published protocol, direct interface and refusal codes.

Read `/api/v1/capabilities` for the deployment you connect to. A public check on
September 23, 2026 reported both protocol versions below, library version 2.2.0,
package downloads by path and an active failed-attempt limit. Values and enabled
features remain deployment settings; the capabilities response is the current
source for them.

## Protocol versions

| Flow | Version | Client behavior |
| --- | --- | --- |
| Handshake | `2025-11-25` | Start with `initialize`, then use the returned compatible version. |
| Per request | `2026-07-28` | Supply version and capabilities with each self-contained request. |

Both use the Model Context Protocol at `/mcp` over `streamable_http`. The service
reports `session_state` as `stateless`. Your service credential goes in the
Authorization header on each request, independently of protocol negotiation.
The published client recipes use a supplied token; an external authorization
flow is not qualified by the current capabilities.

The [2025-11-25 lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
allows a server to return a supported version when it cannot use the requested
one. The client continues only if it supports that result. The
[2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28)
uses self-contained requests and per-request capability negotiation.

### Handshake

An initialization request contains the protocol version, client capabilities
and client identity:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"my-client","version":"1.0.0"}}}
```

This service's handshake profile returns `2025-11-25`. If initialization requests
an unsupported older version, it can still return that supported version.
After the initialization result, complete the client's initialized notification
and send the negotiated `MCP-Protocol-Version` on subsequent requests.

A normal request with an unsupported version receives status 400 and protocol
error `-32022`, including supported versions. Missing, repeated or malformed
version headers receive protocol error `-32020`. These are not instructions to
silently downgrade a request that needs unsupported semantics.

### Per-request flow

At `2026-07-28`, requests carry the version in `MCP-Protocol-Version` and in
`params._meta`. They also carry `Mcp-Method`; a tool call carries `Mcp-Name`.
A client can request `server/discover` with these metadata keys:

```json
{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"my-client","version":"1.0.0"}}}}
```

Discovery and tool-list results can carry `cacheScope` and `ttlMs`. Respect
private cache scope and the returned lifetime. They do not waive authorization
checks on a later item read.

## Headers and tools

| Header | Purpose |
| --- | --- |
| `Authorization` | One Bearer service credential. |
| `Content-Type` | `application/json` for request bodies. |
| `Accept` | Accept both `application/json` and `text/event-stream` for the protocol transport. |
| `MCP-Protocol-Version` | Negotiated or per-request protocol version. |
| `Mcp-Method` | Method routing for the per-request protocol flow. |
| `Mcp-Name` | Tool name for a per-request `tools/call`. |
| `X-Content-SHA256` | Digest of a downloaded body or selected package file. |
| `X-Loop-Engine-Record-Type` | `service_download/v1` on a byte download. |
| `Retry-After` | Wait interval supplied with a rate refusal. |
| `WWW-Authenticate` | Authentication challenge information. |

The service lists `provisioning_discover`, `provisioning_list`,
`provisioning_manifest`, `provisioning_read` and `intelligence_search`. Use each
tool's returned input schema. Search has no read-only annotation in the current
implementation; it is still not metered. A body read can record usage. Do not
infer permissions or price from a tool annotation.

## Direct interface addresses

The direct interface uses versioned JSON records rather than protocol messages.
A success wrapper is `service_http_result/v1`. A refusal is
`service_http_error/v1`, with `error.code`, `error.message` and
`error.next_action`; it can include `request_reference`. A protocol transport
refusal instead uses the protocol's own error object.

| Address | Method | Purpose |
| --- | --- | --- |
| `/api/v1/capabilities` | GET | Public protocol, limits and feature settings. |
| `/api/v1/health` | GET | Public health and readiness checks. |
| `/api/v1/session` | GET | Account, authentication mode and credential expiry. |
| `/api/v1/retrieval` | POST | Search authorized metadata. |
| `/api/v1/provisioning` | POST | Discover, list, manifest or inline read. |
| `/api/v1/download` | POST | Download bytes, including a declared package path. |
| `/api/v1/usage` | GET | Read this account's recorded usage. |
| `/api/v1/account/identity` | GET | Browser identity configuration. |
| `/api/v1/account/activate` | POST | Bind an authenticated browser identity to its allowed account. |
| `/api/v1/account/logout` | POST | End the browser account authorization. |
| `/api/v1/account/access` | GET, POST | Customer token options, listing and management. |
| `/api/v1/account/signup` | POST | Account creation when enabled. |
| `/api/v1/account/recovery` | POST | Account recovery when available. |
| `/api/v1/account/promotion` | POST | Redeem an enabled promotion. |
| `/api/v1/waitlist` | POST | Request an invitation. |
| `/api/v1/admin/access` | GET, POST | Authorized operator token administration. |
| `/api/v1/admin/waitlist` | GET, POST | Authorized invitation administration. |
| `/api/v1/billing/plans` | GET | Plans offered to the authenticated account. |
| `/api/v1/billing/checkout` | POST | Create an authorized checkout session. |
| `/api/v1/billing/portal` | POST | Open an authorized customer portal session. |
| `/api/v1/billing/webhook` | POST | Receive provider events with signature verification. |

An address can exist while its feature is unavailable. Check capabilities and
the returned refusal. Authorization requirements differ: a public invitation
request is not an operator decision, and a billing webhook uses its provider
signature. A client token is not a browser-management session.

The external authorization metadata addresses
`/.well-known/oauth-protected-resource` and
`/.well-known/oauth-protected-resource/mcp` are conditional on that host
configuration. Their existence in the route table does not qualify an external
login flow.

## Limits, deadlines and retries

The capabilities record names `request_bytes`, `response_bytes`,
`search_results`, `concurrent_operations`,
`concurrent_operations_for_each_account`,
`concurrent_operations_waiting_on_another_service` and `request_nesting_depth`.
Delivery separately names `inline_body_bytes` and `download_bytes`.

The failed-attempt policy reports whether it is active, the counted refusal
categories, `failures_allowed` and `window_seconds`. Follow the returned wait
interval and correct the failed request before repeating it.

A deadline bounds how long the response waits. A running callback can still
finish after that deadline. The service does not automatically replay it.
Retain the original `request_id` and selection when retrying a body read after
an uncertain outcome; do not treat a timeout as proof that metering did not occur.

## Refusal reference

These are the codes most relevant to a client. The response also supplies a
plain message and next action. [Troubleshooting](service-troubleshooting.md)
explains how to diagnose them.

| Code | Status | Meaning |
| --- | --- | --- |
| `unauthorized` | 401 | Credential refused. |
| `tenant_disabled` | 401 | Account disabled. |
| `insufficient_scope` | 403 | Credential lacks the operation scope. |
| `scope_required` | 403 | Account lacks the operation scope. |
| `body_forbidden` | 403 | Body disclosure is not permitted. |
| `browser_session_required` | 403 | Customer token management needs browser sign-in. |
| `item_unavailable` | 404 | Identity or expected digest is unavailable to this account. |
| `item_withheld` | 400 | Requested selection excludes this material. |
| `item_withdrawn` | 404 | Selected item version withdrawn. |
| `package_file_not_found` | 404 | Path absent from the package. |
| `package_files_unavailable` | 404 | Separate file download unavailable for this item. |
| `package_file_requires_download` | 400 | Use the byte-download endpoint for a package path. |
| `search_filter_not_allowed` | 400 | Attribute is not public and filterable. |
| `search_filter_invalid` | 400 | Filter condition is invalid. |
| `unknown_request_field` | 400 | Request includes an unsupported field. |
| `unsupported_version` | 400 | Request record version is unsupported. |
| `invalid_request` | 400 | Request schema is invalid. |
| `nesting_limit_exceeded` | 400 | Request is nested too deeply. |
| `unsupported_protocol_version` | 400 | Protocol version is unsupported for this request. |
| `protocol_version_header_missing` | 400 | Version header missing. |
| `protocol_version_header_repeated` | 400 | Version header repeated. |
| `protocol_version_header_malformed` | 400 | Version header malformed. |
| `protocol_method_not_allowed` | 405 | Protocol endpoint method unsupported. |
| `download_required` | 413 | Body exceeds the inline limit. |
| `download_limit_exceeded` | 413 | Body exceeds the download limit. |
| `response_limit_exceeded` | 413 | Response exceeds the configured limit. |
| `body_integrity_failed` | 400 | Stored bytes fail their identity check. |
| `failed_attempt_limit_reached` | 429 | Failed-attempt allowance exhausted. |
| `tenant_concurrency_limit_reached` | 429 | Account operation capacity exhausted. |
| `service_busy` | 503 | Service operation capacity exhausted. |
| `external_provider_capacity_reached` | 503 | Capacity waiting on another service exhausted. |
| `deadline_exceeded` | 504 | Response deadline exceeded. |
| `meter_unavailable` | 400 | Required metering unavailable. |
| `meter_commit_unknown` | 503 | Meter outcome uncertain or read identity conflicts. |
| `commit_unknown` | 503 | Durable write outcome uncertain. |
| `scope_escalation_refused` | 403 | Requested token scopes exceed authority. |
| `access_lifetime_exceeded` | 400 | Requested token lifetime exceeds policy. |
| `access_token_limit_reached` | 409 | Active token limit reached. |
| `access_token_history_limit_reached` | 409 | Token record limit reached. |
| `access_request_identity_conflict` | 409 | Token-operation identity reused with different contents. |
| `managed_access_token_not_found` | 404 | Managed token unavailable to this account. |
| `concurrent_update` | 409 | A competing write changed the expected state. |
| `account_registration_unavailable` | 503 | Account creation is unavailable. |

## Related guides

- [Get set up](service-getting-set-up.md)
- [Searching and retrieving](service-searching-and-retrieving.md)
- [Your account](service-your-account.md)
- [Usage and what you pay for](service-usage-and-what-you-pay-for.md)
