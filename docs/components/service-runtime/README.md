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
│   ├── one way in: only accounts its own sign-up created, marked in two places
│   ├── customer-owned client keys and their scopes
│   ├── administrator access grants
│   ├── staff roles fixed in code, and superadmin account administration
│   └── sign-up links a superadmin sends through Baltor's own sign-up
├── Authenticated delivery
│   ├── catalogue discovery, listing and manifests
│   ├── one selected body, inline or by download
│   ├── one file of a multi-file package, by download
│   └── metadata search over the authorized catalogue
├── Catalogue releases
│   ├── a content-addressed body store behind catalogue_body_store/v1
│   ├── releases, an active release pointer and durable withdrawals
│   ├── an attribute schema declared as data
│   └── a served view swapped in while the service runs
├── Accounting
│   ├── one usage record for each delivered item
│   └── the tenant's own usage total
└── Subscription
    ├── plan listing, checkout and customer portal sessions
    ├── one payment customer bound to one account
    └── free monthly Baltor Pro and the founding offer
```

It does not own the catalogue's content. Approval of an intelligence item
belongs to the independent review process described in
[the reusable capability admission guide](../intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md).
It publishes an approved release and serves it: the
[catalogue release design record](../../architecture/CATALOGUE-RELEASES-AND-HOT-SWAP-2026-09-22.md)
explains how new items, attributes and withdrawals reach a running service
without a new image.

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
| Metadata search | `service_retrieval_request/v2`, with optional `filters` and `authority_effects` | `service_retrieval_result/v1`, each hit with `attributes` and `package` |
| Usage | none | `durable_tenant_usage/v1` |
| Client access | `service_client_access_options/v1` | `service_client_access_result/v1` |
| Administrator access | `service_client_access_options/v1` | `service_client_access_result/v1` |
| Billing session | `billing_session_request/v1` | `billing_session_effect_outcome/v1` |
| Staff overview | none | `service_staff_overview/v1` |
| Account list | none | `service_account_listing/v1` |
| Account action | `service_account_administration_request/v1` | `service_account_administration_result/v1` |
| Staff sign-up links | `service_staff_sign_up_link_request/v1` | `service_staff_sign_up_link_result/v1` |

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
| `/api/v1/admin/overview` | A staff member's role, its permissions and what the role may read. |
| `/api/v1/admin/accounts` | The account list and one account action, for a superadmin. |
| `/api/v1/admin/sign-up-links` | Baltor's own sign-up link for up to ten addresses, sent by a superadmin. |
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
| `item_withdrawn` | The item version was withdrawn from the library after the served view was built. |
| `search_filter_not_allowed` | A search filtered on an attribute that is undeclared, internal or not filterable. |
| `package_file_not_found` | A download named a path the item's package does not hold. |
| `account_origin_unverified` | The sign-in was not created through Baltor's sign-up. Sign up again with the same address. |
| `staff_role_required` | The caller holds no staff role. |
| `account_administration_forbidden` | The caller's staff role does not include that action. |
| `sign_up_link_batch_too_large` | One request named more than ten addresses. Nothing was sent. |
| `sign_up_links_in_progress` | A batch under this request identity started and did not finish. It is never sent again under that identity. |

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

## Billing policies after a release

The service stores two billing policies from the host file: the entitlement
policy, which says which prices grant paid access, and the session policy,
record `service_billing_session_policy/v2`, which holds the checkout and portal
terms. Checkout and the portal are offered only while the stored session
policy is the one the running release computes. Release 13 computed a
different digest from an unchanged host file, and checkout stayed unavailable
until the policy was stored again.

- `loop-engine service apply-billing-policy --config /data/host.json` stores
  both policies again. It names each record version it read as the expected
  one, prints the held and the applied digests in one
  `service_billing_policy_application/v1` record, registers nothing, calls no
  provider, and changes nothing on a second run. It refuses an entitlement
  policy change that would end paid access, with
  `billing_policy_change_ends_paid_access`, unless the operator passes
  `--reset-paid-access`. A refusal prints a
  `service_billing_policy_refusal/v1` record with its code.
- The health record reports `billing_policy_current`, which fails with a code
  such as `session_policy_changed` and never shows a digest. It is reported and
  not required, because every other route still answers and only the command
  can repair it.
- The release workflow runs the command after the grant step and requires the
  capabilities record to report checkout and the portal as the host file
  offers them.

The session digest covers the terms alone: account, provider version, test or
live mode, plans, return addresses, portal configuration and the discount code
choice. A changed timeout or network switch no longer invalidates it. The
[service runtime guide](../../../src/loop_engine/core/service_runtime/README.md#billing-policies-after-a-release)
records the decision, its reasons and the checks that hold each rule.

## One way in

This section describes the source in this repository. A deployment serves it
only after a release that includes it and the marking command below.

The owner decided on September 23, 2026 that a customer account comes from
Baltor's sign-up and from nowhere else. The identity provider still takes its
own public sign-up until the owner closes it, and through that route anyone can
register an address that is not theirs with a password they chose. The service
therefore honours an identity only when two places say that the service
created it or marked it:

```text
One way in
├── The provider's mark
│   └── `baltor_account` in the user's `app_metadata`, which only the
│       provider's administration interface can write
├── The service's own record
│   └── `service_account_origin/v1`, keyed by issuer and provider user
├── Every sign-in and every activation checks both, in `require_admitted`
│   └── either one missing: refused with `account_origin_unverified`
└── Baltor's sign-up, in `AccountOrigins`
    ├── a new address: a marked user through the administration interface,
    │   then the service record, then the link
    ├── an account with both marks: the link, or for a confirmed account the
    │   usual notice
    ├── an account the service already holds a sign-in for: it predates the
    │   guard, keeps its place until the marking command marks it, and its
    │   owner is sent the usual notice
    └── any other account under the address
        ├── archived first in `service_account_replacement/v1`: provider user,
        │   creation time, confirmation state and a digest of the address
        ├── deleted at the provider, which removes its sessions and refresh tokens
        └── replaced by a fresh marked account for the same address
```

A public sign-up never deletes an account the service already holds a sign-in
for. Anyone who knows an address can ask for a sign-up, so deleting such an
account would let a stranger end a real person's account and its history. It
cannot open without both marks either way.

The archive keeps a digest of the address, not the address. The published
privacy notice lists no address in the service database outside the waiting
list, so the address stays with the identity provider on the replacement
account, and an operator reaches it through the replacement's provider user.

The provider's administration interface sits behind the edge
`identity_administration/v1`. `SupabaseIdentityAdministration` is its one
engine: create a marked user, look one address up, delete a user, mark a user,
and read one page of users.

Accounts that predate the guard get both marks once, through
`loop-engine service mark-accounts`. Without `--apply` the command reads every
provider user, lists each account it would mark, with its reason and a masked
address, prints the `plan_digest` and changes nothing. It marks an account
that the service already holds a sign-in for, and one the host's staff list
names. Everything else stays unmarked and refused, and is replaced when its
owner signs up through Baltor. With `--apply` and `--expected-plan` set to the
printed digest, it marks exactly the listed accounts; a plan that changed in
between is refused with `account_marking_plan_changed`, and a second run
changes nothing.

## Staff roles and account administration

Staff sign in on the website like anyone else. Three roles exist, and what
each may do is the table `ROLE_PERMISSIONS` in code:

```text
Staff roles
├── superadmin: every permission below
├── developer: service diagnostics, meaning the measured health record and
│   the newest refusal codes, counted; no account or billing change
└── analytics: account counts and usage counts; no address and no change
```

Who holds a role comes from the `staff` list of the host file's `accounts`
block, record `service_account_policy/v1`, by provider user identity or by
address. The addresses stay in the private host file. A host file that names
a permission, a fourth role or a field of its own is refused before the
service serves anything. A service key never holds a role, and nothing in a
request can name one.

A superadmin reads every account, with its address, creation, confirmation,
plan and last use, in the Administration view, and applies one action at a
time: `grant_free_monthly`, `revoke_free_monthly`, `disable` or `enable`. Each
action is one `service_account_administration_request/v1` with its own
request identity. A repeated identity returns the first result, and a changed
request under the same identity is refused. The action and its audit record,
`service_account_administration_event/v1`, commit together, and the write is
refused when the staff session was signed out or expired meanwhile. A
superadmin cannot switch off their own account, and a host tenant without a
browser sign-in is not an account here.

## Sign-up links a superadmin sends

This section describes the source in this repository. A deployment serves it
only after a release that includes it.

The owner asked on September 24, 2026 for a way for a superadmin to type email
addresses and have those people sign up. A sign-up link is Baltor's own
email-first sign-up, started by a staff member instead of by the visitor, so
it adds no way in. The account gets the same two marks, the link opens the same
`/auth/confirm` page, and the person chooses their own password there.

```text
One request from a superadmin, service_staff_sign_up_link_request/v1
├── refused before any request to the identity provider
│   ├── a caller without the permission accounts.send_sign_up_links
│   ├── more than ten addresses, or one address named twice
│   └── a service whose own sign-up is switched off
├── the request identity reserved in the audit record
├── for each address
│   ├── an account is already open under it
│   │   └── refused as address_has_an_account, and no message
│   ├── the allowance for one address that sign-up keeps is used up
│   │   └── refused as address_sent_recently, and no message
│   └── otherwise
│       ├── the account is prepared with both marks by prepare_signup
│       ├── one link to the /auth/confirm page
│       └── one message that names the staff member who sent it
└── one write: a pending record for each link and the completed audit record
When the person chooses a password and the account opens
└── the pending record is completed, and free monthly Baltor Pro is granted
    in the same write when the superadmin ticked the box
```

The message subject is "Sam at Baltor invited you to Baltor" when the
staff entry in the host file's `accounts` block has the optional `name`
"Sam at Baltor". Without a name, the message names the staff member's
verified address. The message asks for nothing but a password, and it says
that the account includes Baltor Pro free each month when the box was ticked.

A sign-up link counts against the same allowance for one address as a public
sign-up, three an hour by default, so a staff member cannot send more messages
to one person than a visitor could ask for. An address whose account is open,
or whose account the service already holds a sign-in for, gets no message; the
answer names it.

The audit record `service_account_administration_event/v1`, with operation
`send_sign_up_links`, holds the request identity, a digest of each address and
the result. The pending record `service_staff_sign_up_link/v1` holds the
provider user, a digest of the address, who sent it, when, and whether free
monthly Baltor Pro was asked for. Neither record holds an address. The account
list reads the address from the identity provider, as it does for every
account, and shows "Sign-up link sent, waiting for this person to choose a
password" with the date until the account opens.

A repeated request identity returns the first result. A batch interrupted
after its reservation stays in progress under its identity and is never sent
again under it. The superadmin sends the addresses again as a new request,
and the allowance for one address still applies.

An account opened with free monthly Baltor Pro from a sign-up link holds that
grant and takes no founding place, because the link is completed before the
founding offer is considered. An account opened from a link without the box
is considered for the founding offer like any other account.

The public pages do not change. Anyone can still sign up on the Get started
page, and the Administration view calls this a sign-up link.

## Free monthly Baltor Pro and the founding offer

Free monthly Baltor Pro is the existing operator entitlement with a
`grant_kind` of `free_monthly` or `founding_free_monthly`. Its `valid_until`
is the end of the current calendar month, and `FreeMonthlyRenewalSchedule`
moves it on by one month when it is three days away, until it is revoked. The
health record reports the task as `free_monthly_renewal_current`, a check that
is never required. A revocation takes effect at the account's next check.

The first accounts that finish Baltor's sign-up receive the founding offer.
The number is `founding_free_monthly_accounts` in the `accounts` block, ten
by default. `consider_founding_offer` decides once for each account, and every
grant commits against the exact version of one counter,
`service_founding_offer/v1`, so two sign-ups at the last place yield one
holder. A revoked founding place goes to the next account that finishes
sign-up. An account created by the marking command is not considered.

The account page and the Get started page say "Your account includes Baltor
Pro" for a founding or free monthly account. The session record names the
source as `access_source` and the caller's `staff_role`.

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

## Catalogue releases

This section describes the source in this repository. A deployment serves it
only after a release that includes it.

```text
Catalogue release operations, in `loop-engine service`
├── publish-catalogue                 check a bundle, store its bodies by digest, move the pointer
├── rollback-catalogue                move the pointer to an earlier release after verifying it
├── withdraw-catalogue-item           record a withdrawal every release, rollback and image honours
├── catalogue-status                  read the state version, the active release and every release
├── follow-catalogue-release          move a named account to grants that follow the active release;
│                                     --all-tenants moves only accounts already granted every item
└── stop-following-catalogue-release  return a named account to a fixed list of what it receives now
```

The host file's `catalogue` section, `service_catalogue_source/v1`, chooses
`image` or `store` and names the body folder and the refresh interval. The
health record names the served view under `catalogue_release`, with a
`catalogue_view_current` check that is reported and not required, so a failed
refresh keeps the previous view serving. An image refuses to start on a
catalogue state version it does not understand, and the rollback target of an
image rollback must understand the current one. The
[service runtime guide](../../../src/loop_engine/core/service_runtime/README.md#catalogue-releases)
has the full rules and the
[operations runbook](../../guides/launch-setup-runbook.md#publish-and-roll-back-a-catalogue-release)
the procedure.

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
- Object storage for catalogue bodies is a designed second engine behind
  `catalogue_body_store/v1`. Only the service volume engine is built.
- `sortable` attributes are declared and validated. No route sorts on them yet.
- Paging of the full catalogue listing is not built. At 10,000 items one
  listing is larger than the default response limit, so clients search and
  select instead of listing everything.

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
