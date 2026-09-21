# Service interface conventions

Kind: engineering standard for the hosted intelligence service. The source is
`src/loop_engine/core/service_runtime/`. Its
[README](../../src/loop_engine/core/service_runtime/README.md) owns the
domain rules. The [client and server map](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
says what the running release has switched on. This standard describes how a
route is built, so that a new route matches the existing routes.

The service does not run customer tasks and does not call a model. The HTTP
adapter and the Model Context Protocol adapter are transports. Each domain
operation runs inside a governed Loop: `invoke_http_service_as_loop` and
`invoke_http_retrieval_as_loop` in
[http.py](../../src/loop_engine/core/service_runtime/http.py) attach the
runtime type, the profile and the mode to the result. A new route does the
same. It does not create another runtime type.

## Request and result records

- Every data route is under `/api/v1/`. The Model Context Protocol endpoint
  is `/mcp`. The website pages and assets are the fixed list `WEB_ASSETS`.
- A request body is one JSON object with a `record_type`, for example
  `service_provisioning_request/v1`, `service_retrieval_request/v1`,
  `service_client_access_request/v1` or `billing_session_request/v1`. The
  content type must be `application/json` (`unsupported_media_type`).
- The adapter refuses a duplicate field, a value that is not finite, a body
  that is not an object, an unknown field and an unknown version. It does
  this before it calls the domain. See
  [Records, versions and compatibility](RECORDS-VERSIONS-AND-COMPATIBILITY.md#4-refuse-what-you-do-not-understand).
- A request becomes a typed immutable record before use, for example
  `ServiceAccessRequest.from_customer_dict` and `BillingSessionRequest.from_dict`.
  A customer request cannot supply a tenant. The tenant comes from the
  authenticated principal.
- Every JSON answer of an `/api/v1/` route is wrapped as `service_http_result/v1` with `operation`
  and `result`. Every refusal is `service_http_error/v1` with `error.code`,
  `effect_commitment` and `automatic_retry: false` (`_error_record`).
- A downloaded body is returned as bytes with the headers
  `X-Loop-Engine-Record-Type: service_download/v1` and `X-Content-SHA256`.
- Every response carries `Cache-Control: no-store` and
  `X-Content-Type-Options: nosniff`.

## Authentication

A request carries exactly one `Authorization` header of the form
`Bearer CREDENTIAL`. `ServiceHttpAuthenticator.authenticate` in
[http_auth.py](../../src/loop_engine/core/service_runtime/http_auth.py)
refuses a missing header, a repeated header, white space inside the
credential and a header above 16,384 characters.

| Mode | Credential | What switches it on |
|---|---|---|
| `host_key` | A service key that starts with `le_`. Only its SHA-256 digest is stored. | The `modes` field of `ServiceHttpAuthentication`, whose default is `(HOST_KEY_AUTHENTICATION,)`. |
| `browser_identity` | A sign-in token from the identity provider, accepted only on `/api/` routes. | A host configuration block for the identity provider. `capabilities()` then reports `browser_identity_available` as true. |
| `external_jwt` | A JSON Web Token from a configured issuer, with the audience bound to `/mcp`. | A configured issuer added to `modes`. The source sets `external_authorization_flow_qualified` to false, so the authorization flow is not qualified. |

Which modes a running release has switched on is deployment state, not a
standard. Read it in the
[current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
section, or ask the running service itself with `GET /api/v1/capabilities`.

- Authenticating is not authorization to act. The adapter calls
  `revalidate` again inside the worker, at use. Key expiry, tenant state,
  subject state, entitlement and administrative revocation are read again.
- A refused credential answers `unauthorized` with status 401. The answer
  does not say which part was wrong. An identity provider that cannot be
  reached answers status 503 instead of a false password failure.
- The `Host` header must be one exact configured value (`invalid_host`, 421).
  An `Origin` header must be an exact configured origin (`invalid_origin`).
  There is no wildcard.
- Health, capabilities and the static pages need no credential. They disclose
  no tenant data.

## Scopes

The closed list is `SCOPES` in
[records.py](../../src/loop_engine/core/service_runtime/records.py).

| Scope | Permits |
|---|---|
| `provisioning:metadata` | Listing, manifests and search over granted items. |
| `provisioning:read` | Loading a body and downloading. |
| `usage:read` | Reading usage totals. |
| `billing:manage` | Billing sessions. Not in `DEFAULT_SCOPES`. |
| `access:manage` | Operator administration of keys. Never granted by account activation (`automatic_administration_forbidden`). |

The effective scopes are the intersection of the tenant's scopes and the
key's scopes (`ServiceRuntime._principal`). A key can never receive more than
its tenant (`scope_escalation_refused`). A route calls `_require_scope` and
answers `insufficient_scope` with status 403. Payment alone never grants an
item: disclosure needs an exact grant as well.

## Idempotent request identities

Every operation with an effect takes a caller-chosen `request_id` and binds
it to a digest of the exact request.

| Operation | Identity | Same identity, same request | Same identity, changed request |
|---|---|---|---|
| Body read and download | tenant and `request_id`; required (`request_identity_required`) | The stored usage acknowledgment is reused. The customer is not charged again. | `usage_identity_conflict` |
| Key issue and revoke | profile, subject record and `request_id`, or tenant and `request_id` for the operator | The stored result with `replayed: true` and `token: null`. A raw key is returned once only. | `access_request_identity_conflict`, status 409 |
| Billing session | tenant, `request_id` and operation, bound to the policy digest and the exact parameters | The reconciled session. | `session_request_identity_conflict`, status 409 |

A new operation with an effect follows the same pattern: store the request
digest with the result, and commit both in one transaction with the guards
that bind authentication state.

## Unknown outcomes

A lost acknowledgment is not a success and not a failure.

- The domain raises `ServiceCommitUnknown` (`commit_unknown`). The adapter
  answers status 503. It never retries by itself.
- A metering write with an unknown outcome returns an acknowledgment whose
  `committed` value is `None`. The provisioning server then refuses the read
  with `meter_commit_unknown` and no body
  (`src/loop_engine/core/provisioning_server.py`). The client repeats the
  same `request_id`.
- A billing session answers `billing_session_uncertainty/v1`, which carries
  `retry_same_request` and `retry_before`. The value is conditional:
  `BillingSessionError` sets `retry_same_request` to `reservation is not None`
  (`stripe_sessions.py` line 55). The client repeats the same `request_id`
  only when that field is true, and it honors `retry_before`. When the field
  is false, repeating the request is not permitted.
- When the response deadline passes, the adapter answers `deadline_exceeded`
  with status 504. The running callback may still commit, and its worker slot
  stays held until it ends (`ServiceHttpApplication._work`).
- `effect_commitment` in the error record is `not_asserted`, or
  `durable_pending` for a committed billing event that waits for
  reconciliation.

## Limits

The limits are fields of the frozen record `ServiceHttpConfiguration`. They
are host configuration, not request authority. The capabilities record
publishes them.

| Field | Default | Refusal |
|---|---|---|
| `maximum_request_bytes` | 65,536 | `request_limit_exceeded`, 413 |
| `maximum_response_bytes` | 262,144 | `response_limit_exceeded`, 413 |
| `maximum_inline_body_bytes` | 16,384 | `download_required`, 413 |
| `maximum_download_bytes` | 64 MiB | `download_limit_exceeded`, 413 |
| `maximum_search_results` | 50 | `invalid_search_limit` |
| `maximum_concurrent_operations` | 8 | `service_busy`, 503 |
| `request_timeout_seconds` | 30 | `request_body_deadline`, 408, or `deadline_exceeded`, 504 |

A search query is at most 4,096 bytes. Customer key limits are fields of
`ServiceClientAccessPolicy` in `access.py`.

Not implemented today: a request limit for each address. The takeover
checkpoint lists it as an open finding.

## No secret in any output

- A raw key is returned once, by `IssuedServiceKey`, and only its digest is
  stored. A repeated request returns no key.
- An exception text never includes a credential (`ServiceRuntimeError`). The
  error record carries a code, not the exception text.
- The check `missing_and_wrong_credentials_refuse_without_secret_echo` in
  `http_checks.py` sends a wrong credential and asserts that the answer does
  not contain it.
- `ServicePrincipal.to_dict` leaves out the authentication record and the
  proof. Usage rows store a digest of the `request_id`, not the value.
- Provider secrets are environment references in the host configuration. A
  value never appears in source, events, reports, logs or exported records.
  The conformance gate `secret_shaped_literals_in_code_or_run_records` scans
  for them.
- The website keeps a service token in page memory only
  ([web assets README](../../src/loop_engine/core/service_runtime/web_assets/README.md)).
