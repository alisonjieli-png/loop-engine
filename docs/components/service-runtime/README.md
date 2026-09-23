# The hosted intelligence service

Kind: component explanation for `src/loop_engine/core/service_runtime`.

This component is the server side of the product. A customer runs their own
harness and their own models. The service holds the reviewed catalogue, decides
who may see which item, delivers a selected body, and records what was
delivered. It does not solve the customer's task.

The local engine reaches it through two registered operational boundaries,
`remote intelligence service operation` and `remote intelligence metadata
search`. Both run as canonical Loops through
`core.service_runtime.http.invoke_http_service_as_loop` and
`core.service_runtime.http.invoke_http_retrieval_as_loop`. The transport is an
adapter used by a Loop. It is not another runtime type.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A route, a session, a client key, a usage row and a billing record are passive
records. None of them is an executable graph vertex.

## What this component owns

```text
Hosted intelligence service
├── Tenant authority
│   ├── durable tenant registration
│   ├── customer-owned client keys and their scopes
│   └── administrator access grants
├── Authenticated delivery
│   ├── catalogue discovery, listing and manifests
│   ├── one selected body, inline or by download
│   └── metadata search over the authorized catalogue
├── Accounting
│   ├── one usage record for each delivered item
│   └── the tenant's own usage total
└── Subscription
    ├── plan listing, checkout and customer portal sessions
    └── one payment customer bound to one account
```

It does not own the catalogue's content. Approval of an intelligence item
belongs to the independent review process described in
[the reusable capability admission guide](../intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md).

## Typed inputs and outputs

Every operation is a versioned record. An unknown version is refused before any
effect, so an older release cannot silently reinterpret a newer request.

| Operation | Request | Result |
|---|---|---|
| Capabilities | none | `service_capabilities/v1` |
| Health | none | `service_health/v2` |
| Session | `service_session/v1` | `service_session/v1` |
| Provisioning | `service_provisioning_request/v1` | `provisioning_discover/v2`, `provisioning_list/v2`, `provisioning_manifest/v2` or `provisioning_body/v2` |
| Download | `service_provisioning_request/v1` with operation `read` | `provisioning_body/v2` |
| Metadata search | `service_retrieval_request/v1` | `service_retrieval_result/v1` |
| Usage | none | `durable_tenant_usage/v1` |
| Client access | `service_client_access_options/v1` | `service_client_access_result/v1` |
| Administrator access | `service_client_access_options/v1` | `service_client_access_result/v1` |
| Billing session | `billing_session_request/v1` | `billing_session_effect_outcome/v1` |

These are the addresses the service answers on. They are read from
`core.service_runtime.http`, so a route renamed in the source fails the
component guide check rather than surviving here.

| Address | What it is for |
|---|---|
| `/api/v1/capabilities` | What this deployment can do. No credential needed. |
| `/api/v1/health` | Whether it is alive and whether it is ready. A machine that is not ready answers 503 and names the failed check. No credential needed. |
| `/api/v1/session` | Exchange a client key for a session. |
| `/api/v1/provisioning` | Discover, list, manifest or read the catalogue. |
| `/api/v1/download` | The body of one selected item. |
| `/api/v1/retrieval` | Metadata search over the authorized catalogue. |
| `/api/v1/usage` | The tenant's own usage total. |
| `/api/v1/account/identity` | The signed-in browser identity. |
| `/api/v1/account/activate` | Activate an invited account. |
| `/api/v1/account/access` | Issue or revoke a customer-owned client key. |
| `/api/v1/account/logout` | End the browser session. |
| `/api/v1/admin/access` | Administrator grants. |
| `/api/v1/billing/plans` | The plans on offer. |
| `/api/v1/billing/checkout` | Start a checkout session. |
| `/api/v1/billing/portal` | Open the customer portal. |
| `/api/v1/billing/webhook` | The payment provider's callback. |
| `/mcp` | The Model Context Protocol surface. |

A provisioning request carries one of four operations, declared in
`core.provisioning_server.OPERATIONS`:

```text
service_provisioning_request/v1
├── discover  what kinds of item exist
├── list      the items this caller may see
├── manifest  digests and sizes for a selected item
└── read      the body of one selected item
```

Two scopes separate looking from taking. `provisioning:metadata` allows
discovery, listing, manifests and metadata search. `provisioning:read` allows a
body. Usage reading needs `usage:read` and a billing session needs
`billing:manage`. The capabilities record reports this mapping under
`operation_scopes`, so a client does not have to guess.

Metering follows the same separation. The metered unit is
`provisioned_item`, defined in
`core.provisioning_server.METERED_UNIT`. The four cases in
`core.provisioning_server.NEVER_METERED` are never charged: listing authorized
items, a manifest with digests and sizes, a refusal before metering, and
reading the tenant's own usage.

## Model Context Protocol versions

This section describes the source in this repository. A deployment serves it
only after a release that includes it. The deployed release observed on
September 21, 2026 served 2025-11-25 alone.

The endpoint `/mcp` serves two protocol versions, and the capabilities record
names both under `protocol.versions`. They reach the service in two different
ways, which the record also names.

| Version | How a client reaches it | Capabilities field |
|---|---|---|
| `2025-11-25` | The `initialize` handshake, then the version in the `MCP-Protocol-Version` header of every later request | `handshake_versions` in the `protocol` object |
| `2026-07-28` | No handshake. The version in the header and in `_meta` of every request, and `server/discover` to ask which versions are served | `per_request_versions` in the `protocol` object |

The service chooses the version of every request before the protocol library
sees it, because the library also speaks older versions that this release has
not qualified.

```text
One request to /mcp
├── initialize         the 2025-11-25 handshake, whatever version header it carries
│   ├── a served version        answered with that version
│   └── any other version       answered with 2025-11-25; the client decides whether to continue
├── any other request  the version in MCP-Protocol-Version
│   ├── a served version        served at that version
│   ├── another version         400 and error -32022, listing every served version, newest first
│   └── no header, a repeated header or one that is not a version
│                               400 and error -32020
└── GET or DELETE      405 with Allow: POST, because the service keeps no session
```

A host can serve fewer versions. The `protocol_versions` member of the host's
HTTP configuration, record `service_http_configuration/v2`, names them, and
both are served when it is absent. Version 1 of that record pinned one version
in `protocol_version`, and a release with this change refuses it rather than
read it as both. The
[service runtime guide](../../../src/loop_engine/core/service_runtime/README.md#model-context-protocol-versions)
has the host file change a release needs and the checks that hold each rule.

## Refusals

The domain raises `ServiceRuntimeError` with an exact code before any effect.
These are the refusals a client meets most often:

| Code | What it means |
|---|---|
| `account_registration_unavailable` | Registration is closed on this deployment. |
| `unsupported_version` | The request record version is not one this release serves. |
| `privileged_scope_delegation_refused` | A customer key asked for a scope only the host may hold. |
| `access_writes_not_authorized` | The deployment has no write authority for access records. |
| `access_token_limit_reached` | The account already holds the permitted number of client keys. |
| `access_token_already_revoked` | The named key was revoked and cannot be reused. |
| `administrator_self_delegation_refused` | An administrator tried to widen their own grant. |
| `browser_session_required` | The operation needs a signed-in browser session, not a client key. |
| `billing_customer_not_bound` | The account has no payment customer yet. |
| `billing_customer_binding_mismatch` | The stored payment customer does not match the provider's. |
| `concurrent_update` | Another writer changed the record; read it again and retry. |
| `commit_unknown` | The effect may or may not have committed. It is never reported as success. |

The request limit is separate. When a client address exceeds the configured
failed-attempt limit, the service answers with
`service_request_limit_refusal/v1` carrying `retry_after_seconds`. The limit
record itself is `service_request_limits/v1`.

`commit_unknown` deserves its own sentence. The command layer in
`service_cli.py` maps it to the exit code path that prints
`service_cli_error/v1` with `effect_commitment` set to `not_asserted` and
`automatic_retry` set to false. An unknown commit is not a success and is never
retried on its own.

Every refusal also carries `request_reference`, a name issued for that one
request from the operating system random source and from nothing else. Before
the service answers, it writes one metadata record of the refusal,
`service_request_failure/v1`, into its own store. `loop-engine service failures`
reads those records by newest, by `--tenant` or by the `--reference` a customer
read out of a refusal, and it writes nothing. The operator procedure is in
[the service failure diagnosis guide](../../guides/service-failure-diagnosis.md).

## Records kept for a bounded time

The published privacy notice keeps two kinds of record for a bounded time: the
digest of a browser session that was signed out, until that session would have
expired, and the times of recent waiting list requests for one source, until
the counting window has passed. The service removes each one when its time has
passed and never before. The removal runs right after every sign-out, from a
periodic task that starts and stops with the service, and by hand through the
`remove-expired` service command, which prints only outcomes and counts. The
host sets how often the periodic task runs with `sweep_interval_seconds` in its
`service_retention_policy/v1` block, from one second to one hour, ten minutes
by default. The health answer reports the last run as
`retention_sweep_current`, a check that is never required.

Each removal is one `catalog_atomic_write_batch/v2` batch with an exact version
precondition for each removed record, applied only by a store that declares
the optional operation `atomic_record_removal`. The
[service runtime guide](../../../src/loop_engine/core/service_runtime/README.md#retention-of-expired-records)
has the rules, the checks that hold them and the design comparison.

## Current behaviour, observed today

These facts were read from the deployed service on September 21, 2026. They
describe one deployment, not the component's full capability.

- The capabilities record reports `registration_available` false and one
  authentication mode, `host_key`. Accounts are created by the operator.
- `browser_identity_available` and `client_access_available` are both true, so
  a signed-in browser session and customer-owned client keys both work.
- Retrieval reports the lexical backend `sqlite_fts5` and the vector backend
  `deterministic_character_hash`, with
  `semantic_embedding_model_installed` false. Search returns metadata only;
  `returns_bodies` is false.
- `oauth_authorization_server_installed` and
  `external_authorization_flow_qualified` are both false.
- Health reports `readiness_checked` false and
  `deployed_provider_qualification` false.

## Designed but not built

The component reports these as explicit negative facts rather than leaving them
unstated. Each one is designed and refused today, not silently missing.

- External token authentication is designed. The capabilities record carries
  `oauth_resource_metadata`, and the deployment answers false for both
  `oauth_authorization_server_installed` and
  `external_authorization_flow_qualified`. A client must not treat the field's
  presence as a working flow.
- A semantic embedding model for retrieval is designed. The deployment reports
  `semantic_embedding_model_installed` false, so hybrid search runs on the
  deterministic character hash today.
- Readiness checking and deployed provider qualification are designed. Health
  reports both as false, so a healthy answer is not a statement that the
  provider behind the service was qualified.

## How to check it

Run the component's own checks first, then the service smoke run:

```bash
PYTHONPATH=src python -c \
  'from loop_engine.core.service_runtime.runtime import self_test; print(self_test()["all_passed"])'
PYTHONPATH=src python -m loop_engine service smoke
```

The smoke run uses local loopback only. It is not a live provider
qualification and it creates no account, no payment and no deployment.

To read a deployment instead, ask it what it can do. The capabilities and
health operations need no credential:

```bash
curl -sS https://app.baltor.ai/api/v1/capabilities
curl -sS https://app.baltor.ai/api/v1/health
```

## What it deliberately does not do

- It does not solve tasks. The customer's harness and models do that.
- It does not approve intelligence. A producer never approves its own item.
- It does not return a body from a search. Search returns metadata, and a body
  needs a separate authorized read.
- It does not install, launch or supervise a model server.
- It does not report an uncertain effect as a success. `commit_unknown` stays
  unknown.
- It does not create accounts from the public internet while
  `registration_available` is false.

## Related reading

- [Core Architecture](../core-architecture/README.md) for the capability groups
  a Loop may use.
- [The four intelligence layers](../intelligence-layers/README.md) for what the
  catalogue holds.
- [The client and server map](../../architecture/MVP-CLIENT-SERVER.md) for how
  the local engine and this service divide the work.
