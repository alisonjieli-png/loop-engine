# Troubleshooting

Kind: customer guide to connection, access, selection and uncertain download outcomes.

Start with the response code and message. The direct interface returns
`service_http_error/v1` with `error.code`, `error.message` and
`error.next_action`. It can include `request_reference` for support. Protocol
transport errors use the protocol's own error shape instead.

## Check the connection first

1. Open `/api/v1/capabilities` to see whether the service answers and which
   protocol versions and limits it reports.
2. Confirm that the client process received `BALTOR_SERVICE_TOKEN` and uses
   the endpoint shown by [Get set up](service-getting-set-up.md).
3. Check `/api/v1/session` with that credential to identify the account, scopes
   and expiry. A browser sign-in and a client token are different credentials.
4. Confirm the native client lists the server's tools. A configuration listing
   alone does not prove a successful handshake.

## Credential and account refusals

| Code | Status | Next step |
| --- | --- | --- |
| `unauthorized` | 401 | Check the credential and the process environment that supplies it. |
| `tenant_disabled` | 401 | Ask the operator about the account state. |
| `insufficient_scope` | 403 | The credential lacks the scope required by this operation. |
| `scope_required` | 403 | The account lacks a required scope. Ask the operator. |
| `body_forbidden` | 403 | Metadata access does not currently permit this body download. |
| `browser_session_required` | 403 | Use browser sign-in for customer token management. |
| `account_registration_unavailable` | 503 | Follow the current access path at Get started. |

Expired, revoked or disabled credentials can answer `unauthorized`; the service
does not disclose a more specific authentication reason. An account entitlement,
a token scope and an item grant are separate checks.
[Your account](service-your-account.md) explains each one.

## Empty search or unavailable material

An empty result is not a connection failure. It can mean the query has no match,
the account lacks grants, the item is withdrawn, or the current selection excludes
it. Search with `authority_effects` only for effects already permitted for your
step. Omitted or empty effect selection withholds material that declares effects.
This choice does not authorize executing the material. Read the current request
version from `/api/v1/capabilities` and update an older client when it is refused.

| Code | Status | Next step |
| --- | --- | --- |
| `item_unavailable` | 404 | Refresh your authorized list and selected digest. The response does not distinguish an unknown identity from an inaccessible one. |
| `item_withheld` | 400 | Check the requested style, kind and effect selection. |
| `item_withdrawn` | 404 | Search again; the selected published version is no longer available. |
| `package_file_not_found` | 404 | Use a path from the selected package document. |
| `package_files_unavailable` | 404 | This item has no separately downloadable package files. |
| `search_filter_not_allowed` | 400 | Use only declared public filterable attributes. |
| `search_filter_invalid` | 400 | Check the filter condition and value types. |

## Version and request problems

For the handshake-based protocol, use the version returned by `initialize` if
your client supports it. A different returned version is a negotiation result;
a client that cannot support it must stop. Other requests with unsupported,
missing or malformed version information are refused.

| Code | Status | Next step |
| --- | --- | --- |
| `unsupported_protocol_version` | 400 | Select a supported protocol version from the response or capabilities. |
| `protocol_version_header_missing` | 400 | Supply the negotiated version header. |
| `protocol_version_header_repeated` | 400 | Send the version header once. |
| `protocol_version_header_malformed` | 400 | Send a supported version string. |
| `protocol_method_not_allowed` | 405 | The protocol endpoint accepts POST messages. |
| `unsupported_version` | 400 | Use the exact request record version this interface supports. |
| `unknown_request_field` | 400 | Remove fields outside the declared request schema. |
| `nesting_limit_exceeded` | 400 | Reduce the nested request structure. |

The protocol transport requires an `Accept` header supporting both
`application/json` and `text/event-stream`; an incompatible header can receive
406. See [Serving and connections](service-serving-and-connections.md) for the
headers and the two supported protocol flows.

## Capacity, size and time

Read current limits from `/api/v1/capabilities`. A larger local allowance does
not change a server limit.

| Code | Status | Next step |
| --- | --- | --- |
| `failed_attempt_limit_reached` | 429 | Wait for `Retry-After`, then correct the rejected request or credential. |
| `tenant_concurrency_limit_reached` | 429 | Reduce concurrent work from this account. |
| `service_busy` | 503 | Retry after a pause with lower concurrency. |
| `external_provider_capacity_reached` | 503 | Work waiting on another service has reached its capacity. |
| `download_required` | 413 | Use the download endpoint instead of an inline body. |
| `download_limit_exceeded` | 413 | The selected body exceeds the service's download limit. |
| `response_limit_exceeded` | 413 | Ask for fewer results or a smaller response. |
| `deadline_exceeded` | 504 | A server callback may still finish. Keep the original request identity for a read retry. |

## Uncertain metering and mismatched bytes

`meter_commit_unknown` means the usage outcome is uncertain. Inspect usage and
retry the same item with the same `request_id`. If that identity was used for a
different item, repeating the conflicting request will not repair it. See
[Usage and what you pay for](service-usage-and-what-you-pay-for.md).

If downloaded bytes do not match the selected digest, do not treat that file as
the selected item. Keep the item identity, expected digest and request reference
for the operator. `body_integrity_failed` identifies a service-side integrity
problem; the client should also check its received bytes.

## Send a useful report

Include the endpoint, time, error code and `request_reference` when present.
State whether the failure was a client listing, handshake, search, manifest or
download. Do not include credentials or private task content. The service's
readiness endpoint is `/api/v1/health`; its result does not prove that your
specific account or native client can complete the task.
