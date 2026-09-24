# Durable hosted-service domain

Kind: internal service mechanics over the existing catalogue contracts.
Tenant state, key digests, external-subject bindings, disclosure grants,
subscription projections, verified billing-event state, and usage records
persist in the existing SQLite catalogue adapter. This package does not
create another intelligence layer, database adapter, or executable runtime.

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

The public HTTP and Model Context Protocol adapters own their governed Loop
operations. The classes below are host services and passive records consumed
by those operations.

```text
Existing service boundary
├── records.py: immutable host configuration and issued principal contracts
├── storage.py: scoped binding to CatalogStore, not a second storage engine
├── runtime.py: tenants, keys, subjects, grants, entitlements, and usage
├── provisioning.py: live durable authority over ProvisioningServer
├── billing.py and billing_records.py: signed-event state and reconciliation
├── stripe_provider.py: explicitly authorized read-only Stripe adapter
├── request_limits.py: failed-attempt settings record and its table in process memory
├── waitlist.py: the public waiting list, its operator decisions and removal on request
├── retention.py: removal of the records the privacy notice keeps for a bounded time
├── account_origin.py: the one way in, the identity administration edge and the marking command
├── account_policy.py: staff roles and permissions fixed in code, and the host's accounts block
├── account_administration.py: the staff overview, the account list and superadmin actions
├── staff_sign_up_links.py: sign-up links a superadmin sends through Baltor's own sign-up
├── free_monthly.py: free monthly Baltor Pro, the founding offer and the monthly renewal
├── web_pages.py: the served page address table and the packaged files behind it
├── catalogue_*.py: catalogue releases, the body store edge and the served view
└── http*.py: separately owned remote transport and host configuration
```

## Host setup and authority

`ServiceRuntimeConfig` requires an absolute, non-symbolic-link database path.
The containing directory must already exist. Constructing a configuration or
runtime does not open or create the database. `writes_authorized=False` is the
default. Host setup must explicitly authorize writes inside its configured
namespace before registration, key issue, policy changes, or metering.

`register_tenant(TenantRegistration(...))` atomically reserves a tenant and
its unique namespace. `issue_key(TenantKeyIssue(...))` returns the new key once;
only its digest is stored. Do not log the returned key. Key scope and expiry,
tenant disablement, subject revocation, subscription state, and administrative
body-access revocation are checked again at use.

The `billing:manage` scope is deliberately absent from `DEFAULT_SCOPES`.
`billing_customer_for(principal)` requires that explicit scope and resolves
the stored account/customer binding again. Merely authenticating a key does
not grant billing-management authority.

## One payment customer for each account

This section describes current behavior. An account that asks for checkout and
has no payment customer gets exactly one, created at the provider and bound
before the session. The portal never creates one. The full journey, its
evidence and its limits are in
[the subscription journey guide](../../../../docs/guides/subscription-journey.md).

`runtime.py` owns the durable state. `begin_billing_customer` reserves the one
creation an account may ever need, in one `service_billing_customer_effect`
record identified by the account itself. The record holds the provider
idempotency key, the current attempt identity, a lease, the reconciliation
window, the attempt's own dispatch deadline, the cycle count and the outcome.
Its version is `service_billing_customer_effect/v2`, because a release that
predates the recorded dispatch deadline must refuse the record rather than
rebuild that deadline from its own caller's lease; version one is refused with
`unsupported_or_corrupt_record`. `authorize_billing_customer_dispatch`
rechecks current authority, the lease and every reserved read-set guard before
the provider call. `bind_billing_customer(request, reservation=...)` commits
the account record, the absent customer record and the confirmed effect
together, so a second writer cannot bind a second customer.
`finish_billing_customer` retains an attempted outcome as unknown and a
never dispatched one as not attempted.

`stripe_sessions.py` owns the provider work. `ensure_customer` resolves the
secret, verifies the configured provider account, searches the provider for a
customer whose metadata names this account, and creates one only when the
search found none. `StripeCustomerProjection` in `billing_records.py` refuses a
provider customer from the other mode, a deleted one, and one whose metadata
names another account.

```text
One customer for each account at one provider account
├── The durable effect record: one for each account, reused by every attempt
├── The lease: a second caller during a running creation is refused
├── The search before creation: a customer left behind by an uncertain
│   attempt is bound instead of duplicated, and an answer the provider
│   marks as truncated is refused whatever its row count
├── The wait before a new key cycle: a retired key leaves the search as the
│   only protection, so a new cycle waits for the search to catch up, from
│   the deadline the attempt that ran recorded for itself
└── The atomic binding: the existing catalogue guard refuses a second writer
```

Within the reconciliation window a retry reuses the stored provider
idempotency key. After that window the key can no longer reconcile anything,
so a new cycle takes a new key and the search before creation is what keeps
the account at one customer. A removed-guard control proves that step.

That last sentence carries an assumption, and the assumption is named in the
source. The provider customer search is eventually consistent, so
`PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS` in `records.py` declares how
stale this service is willing to assume the search may be. It is sixty
seconds, it is a host choice rather than a measured provider fact, and nothing
in this repository bounds the real lag. A new key cycle may begin only once
that allowance has passed since the last moment the previous attempt could
have reached the provider, which is the earlier of that attempt's lease end
and its reconciliation window end. Until then the caller is refused with
`billing_customer_search_not_current_yet` and nothing reaches the provider. A
session configuration whose reconciliation window is shorter than the
allowance is refused as well. Both rules have named checks. The wait has a
removed-guard control inside the suite; the window floor was removed from the
source instead, and its named check failed. If the real provider search lags
longer than the allowance, the one
customer result does not hold for a repeat after a retired key; raise the
number rather than shortening a window to fit.

That deadline is written by the attempt that ran, as `dispatch_deadline`, and
read back from the record. It is never rebuilt from the lease of whichever
caller comes next. The lease follows the host request timeout, so a host that
lowers that timeout gives the next caller a shorter lease, and a rebuilt
deadline would land earlier than the real one. A record whose deadline is
missing or beyond its own window is treated as though its attempt ran to the
end of that window, which is never earlier than the real deadline.

A customer at one provider account does not exist at another, so the
configured provider account changing is its own case.
`begin_billing_customer` lets an account with no binding start a fresh cycle
at the new provider account, and keeps the provider account it left in
`superseded_provider_accounts`. An account that is bound stays refused until a
host calls `release_billing_customer_account` with the exact account identity,
the provider account being released and the provider account the service uses
now. The release refuses unless the binding and the creation record both name
the released provider account, refuses while a creation is running, and keeps
the customer record of the released provider account as evidence.
`ensure_customer` reports an account that already has a customer with the
separate record version `billing_customer_binding_held/v1`, which names the
customer and provider account the binding really holds.

Every supported provider mutation declares the exact parameter names it may
carry, in `POST_PARAMETERS`. The customer form may carry only
`metadata[loop_engine_tenant_id]`. The service holds no name, postal address
or email address for an account, so it sends none. The customer search is a
read with exactly two permitted fields, and both parts of its query are
checked as service identities first, so neither can carry a quotation mark or
a space into the provider query.

| Guard | Removed-guard control |
|---|---|
| The search before creation | `removed_customer_search_before_creation_is_detected` |
| The account identifier in the customer metadata | `removed_account_identifier_in_customer_metadata_is_detected` |
| The ownership check on a provider customer | `removed_customer_ownership_check_is_detected` |
| The provider account check before creation | `removed_provider_account_check_before_creation_is_detected` |
| The refusal of a truncated search answer | `removed_truncated_search_refusal_is_detected` |
| The wait before a new key cycle | `removed_search_freshness_wait_before_a_new_key_cycle_is_detected` |
| The recorded dispatch deadline of the attempt that ran | `removed_recorded_dispatch_deadline_is_detected` |
| The route from one provider account to another | `removed_provider_account_change_route_is_detected` |
| The host release of a provider account | `removed_provider_account_release_is_detected` |

A control passes only when its scenario returns a failed predicate. A
scenario that raises an error fails its control instead, so a patched rule
whose signature no longer matches its caller cannot pass one. The two rules
the creation record follows,
`billing_customer_request_differs_only_by_provider_account` and
`billing_customer_search_can_show_the_previous_attempt`, live in `records.py`
beside `PROVIDER_SEARCH_FRESHNESS_ALLOWANCE_SECONDS`, and `ServiceRuntime`
binds them, which keeps `runtime.py` inside the module size cap.

The lease has a named check and no removed-guard control inside the suite.
Removing it does not produce a second customer, because the reserved attempt
identity and the search before creation each stop the duplicate on their own.
The lease is what keeps a second caller away from the provider entirely.

A host configuration may still bind a customer by hand through the
`billing_customer` mapping of a tenant. That mapping is now optional.

`authenticate_subject(issuer, subject)` accepts only an exact durable binding
installed by the host. It does not verify a JSON Web Token itself and does not
trust a token's proposed tenant identity. The transport must validate the
issuer, signature, audience, expiry, and token profile before calling it.
Principals are issued in process and bind their authentication source. They
are not reconstructed from request JSON.

## Billing policies after a release

This section describes the source in this repository. A deployment serves it
only after a release that includes it.

The host file names two billing policies. The service stores each once, with a
digest, and compares the stored digest with the one the running release
computes from the host file.

```text
Stored billing policies
├── Entitlement policy, service_billing_policy/v1
│   ├── Which provider prices grant paid access
│   └── Every paid access record and payment notification names its digest
└── Session policy, service_billing_session_policy/v2
    ├── The session terms, a billing_session_terms/v1 document
    ├── The digest of the entitlement policy it was checked against
    └── Every checkout and portal session compares its digest with the running one
```

`loop-engine service configure` stores both once and cannot run again, because
it also registers tenants. Release 13 added `allow_promotion_codes` to the
session configuration. The version one digest covered every configuration
field, so it changed although the host file did not, and checkout and the
portal were unavailable with `session_policy_changed`. The health record still
passed `billing_sessions_installed`, and nothing could store the new policy.

### What the session digest covers

The digest covers the session terms: every field of `StripeSessionConfiguration`
except the ones `SESSION_OPERATION_FIELDS` in `stripe_sessions.py` names, each
with its reason there.

| Terms, which change the digest | Operational settings, which do not |
|---|---|
| Provider account, provider API version, test or live mode | The credential reference, which is checked against the account before every provider call |
| Each plan: price, quantity, reference and label | The network switch and the session creation switch, read at every use |
| The success, cancel and portal return addresses | The permission for loopback return addresses; the addresses themselves are terms |
| The portal configuration and whether a discount code is accepted | The timeout, the response size limit, the reconciliation window and the version of the host block |

The reason is what a digest decides. A customer's selection carries the
digest, so a changed operational setting refused an open selection with
`session_selection_changed`. Each checkout effect record names the digest too,
so after a changed timeout an uncertain checkout could no longer be reconciled
under its own idempotency key, and a new request would open a second session.
Neither setting changes what a customer is offered, what they are charged or
where they return. A field a release adds is a term until someone names it
operational with a reason, so a field nobody sorted can only make the digest
stricter.

Other systems draw the same line. The payment provider compares only the
parameters of a repeated idempotent request, not how the client sent it. A
Kubernetes object raises its generation only when its specification changes,
and a controller that reports an older observed generation has drifted.
Terraform compares the desired configuration with the recorded state and
applies a change only when asked, under a lock. Here the digest is the
specification, the health check reports drift, and the operator command
applies the change with the held record version as the lock.

`each_term_changes_the_policy_digest` changes the price, the quantity, the
plan reference and label, the account, the three return addresses, the portal
configuration, test or live mode, the discount code choice and the provider
version one at a time, and each must change the digest.
`each_operational_setting_leaves_the_policy_digest_unchanged` does the reverse
for every operational setting.

### Version two and one record for each version

The version two record holds the terms alone. `BillingSessionPolicyDefinition`
refuses a policy that is not a `billing_session_terms/v1` document, so the
version one shape, a whole host configuration, is refused with
`unsupported_session_policy` rather than read as terms.

Each record version is stored under its own identity,
`SESSION_POLICY_IDENTITY` in `billing_effects.py`. A release reads and writes
only the record of its own version. It never reads a version one record and
never overwrites one. Release 15 and earlier read the version one record, so a
rollback to one of them finds the record it left and can repair it with its own
writer. The first run of the command below on a deployment writes the version
two record beside the version one record, and reports the older one under
`other_record_versions`.

### The operator command

`loop-engine service apply-billing-policy --config /data/host.json` applies
both policies of the host file again, through the existing writers.

- It loads the host file through the loader the service itself uses.
- It reads the held record version of each policy and names it as the exact
  expected revision of `configure_billing_policy` and `configure_policy`. A
  writer that changed a record in between is refused with
  `billing_policy_revision_required` or `session_policy_revision_required`,
  not overwritten.
- It refuses a host file whose session prices are not all in its own
  entitlement policy, `session_price_not_in_billing_policy`, before anything is
  written.
- It refuses an entitlement policy change while any account holds paid access
  under the held policy, with `billing_policy_change_ends_paid_access`. Each
  paid access record names the digest it was decided under, so a changed
  entitlement policy reads it as no access until that account's next
  subscription notification. `--reset-paid-access` applies the change anyway,
  and the record counts those accounts in `paid_access_ended_for_accounts`.
  The release workflow never passes it.
- It prints one `service_billing_policy_application/v1` record: for each
  policy the held and the applied record version and digest and whether it
  changed, `every_installed_policy_current`, and `checkout_expected` and
  `portal_expected`, which say what the host file offers before any stored
  state is read. It prints no secret, resolves no credential, calls no
  provider and registers nothing.
- It exits with status one when a policy is still not current afterwards.
- A refusal it declares, one of `APPLICATION_REFUSALS` in `billing_policy.py`,
  prints a `service_billing_policy_refusal/v1` record with its code and exits
  with status one. The `loop-engine service` wrapper reports any other failure
  by one generic code, so without this record an operator could not read why
  the command stopped.
- A second run changes nothing.

### The health check

`billing_policy_current` passes only when three facts hold. The stored
entitlement policy is the one the host file names; otherwise every payment
notification is refused with `billing_policy_mismatch`. The stored session
policy is the one the running release computes. The session policy was stored
against the entitlement policy stored now. The last two are the comparison
every checkout and portal session makes, and both answers come from the same
code. The check reports a code and never a digest: `billing_policy_changed`,
`billing_policy_not_installed`, `session_policy_changed`,
`session_record_unavailable`, or `billing_not_installed` for a host without
billing.

The check is reported and not required, for three reasons. Every other route,
paid access for accounts that already have it included, still answers
correctly, so by the rule of `readiness_report` the machine stays in service.
Restarting cannot repair it; only the operator command can. And the release
checks readiness right after the deploy and runs the command after that check,
so a required check would stop every release before the step that repairs it.
The release instead requires the capabilities record to report checkout and
the portal as the host file offers them.

### The release step

The guarded workflow runs the command on the one started Machine right after
the grant step, through the Machines API exec call and `setpriv`, as the grant
step does. It requires exit status zero and one record whose policies are
current, with no paid access ended, no tenant registered and no provider call.
It then requires `billing.checkout` and `billing.portal` in the live
capabilities record to equal `checkout_expected` and `portal_expected`, and
ends with the shared readiness gate. `tools/test_fly_deployment.py` fails when
the step is removed, moved before the grant step or the deploy, runs another
command, passes `--reset-paid-access`, drops a gate, reads the capabilities
before the command, reaches another Machine or opens a remote shell. It runs
the step's own filters over what the real command prints and what the real
service serves, and the release 13 state must fail them.
`tools/check_fly_service_container.py` stores the release 13 state in the
image, runs the command as root the way the exec call does, and requires the
health record to pass afterwards and a second run to change nothing.

| Guard | Removed-guard control |
|---|---|
| The health check names a drifted policy | `removed_billing_policy_health_check_is_detected` |
| The command stores the session policy it reports | `removed_session_policy_application_is_detected` |
| The held version is the expected revision | `removed_expected_revision_is_detected` |
| The price check comes before any write | `removed_price_check_before_any_write_is_detected` |
| Paid access ends only when the operator says so | `removed_paid_access_guard_is_detected` |
| A return address is a term | `a_return_address_left_out_of_the_terms_is_detected` |
| A timeout is not a term | `a_timeout_counted_as_a_term_is_detected` |
| This release never reads the version one record | `reading_the_version_one_slot_is_detected` |

The checks live in `billing_policy_checks.py` and run with
`stripe_sessions.self_test()`. They use a real host file, the real entry point,
the served routes through the application's own interface and a real store.
The session transport and the secret resolver are replaced by recorders, so a
check shows that nothing reached either.

## Customer-owned client credentials

`ServiceAccessAdministration` applies either the existing administrator policy
or `ServiceClientAccessPolicy` over the same catalogue and transaction rules.
The customer profile requires an issued subject principal and a
`ServiceAccessSession` from the verified browser transport. The session binds
the subject record, credential digest, expiry and effective scopes without
carrying a raw token into stored records.

`GET` and `POST /api/v1/account/access` use the explicit
`service_client_access_request/v1` wire contract. A request cannot supply a
tenant. Service tokens and protocol-resource tokens cannot manage personal
credentials. The owner-installed policy permits only non-privileged service
scopes; billing and administration cannot be delegated. Defaults allow ten
active tokens, a one-day initial lifetime, at most seven days per token and
one thousand retained token records. These limits are configuration fields,
not customer-controlled request authority.

Issue, quota checks, operation identity and key metadata commit together.
The raw key is returned once; a repeat or lost acknowledgment returns no
recoverable secret. A revoked subject invalidates its linked client keys.
The write also guards browser-session revocation, so a concurrent sign-out
cannot commit another key from that revoked session. Listing and revocation
are restricted to the issuing subject, including when several subjects share
a tenant. History exhaustion refuses further issue rather than deleting
records silently.

Signing out of the website clears private controls immediately. The service
keeps a digest of the signed-out session, `service_browser_session_revocation/v1`,
until that session would have expired, and then removes it; the section on
retention below says when and how. Client tokens remain separate credentials
until revoked, expired or disabled through their local subject or tenant
binding. Synchronizing a provider-side account deletion
with that local binding is still integration work. A provider outage returns
service unavailability instead of pretending that the user's password failed.

Real-provider qualification uses disposable, administratively confirmed test
identities. It does not prove confirmation email delivery, password recovery,
public registration, subscription processing or useful native task execution.

`set_operator_entitlement` is an explicit local host grant with an evidence
reference and expiry. It is not evidence of payment. Billing projections do
not override an administrative access revocation.

## Promotion codes

`promotions.py` adds a second way to reach the same entitlement record: a
person redeems a code instead of an operator granting access for each person.
It adds no runtime type and no store. A promotion code is a passive typed
record, `service_promotion_code/v1`, in the existing catalogue, and redemption
writes the same `service_entitlement` record with the source
`promotion_code_grant`.

Three entitlement sources exist and they stay apart. `stripe_snapshot` is the
only revenue-bearing source. `explicit_host_grant` and `promotion_code_grant`
are comped. `ServiceRuntime.access_source_report` separates them and counts
them separately; it reads the recorded source and never infers money from an
expiry, a grant or a name. Every record it reads goes through the same version
check the rest of the service uses, so a record this release cannot read stops
the report instead of being counted. A release that predates `promotion_code_grant` reads
an unknown source as metadata only, so an older server refuses the access
rather than honoring a record whose rules it does not know.

A code's text decides nothing. Every effect comes from a separate typed field:
the grant, the total redemptions allowed, whether one account may repeat, the
window, the approver and the approval reference. The service stores the digest
of a code and never the code, so no listing can print one.

One redemption commits four records in one atomic batch: the code with its
exact revision, the per-account record, the request identity and the
entitlement. Two accounts competing for the last redemption both guard the same
code revision, so only one commits. A repeated request identity replays the
first result and spends nothing. The count is compared with the allowance
twice, once when the state is evaluated and once against the record that is
about to be written, so a wrong state evaluation cannot commit a count past the
allowance. The account's entitlement record is in the same read set at the
revision the redemption read, so a payment that lands during a redemption
refuses it rather than being replaced by a code grant.

Every refusal that depends on the offered code discloses one word,
`promotion_code_unusable`, with one status. The exact reason stays in the
process and reaches an operator. An unknown code is evaluated against a
stand-in record and reads the same rows, so the two paths do the same work.
Refused redemptions are counted by the existing failed-attempt limiter for the
client address.

The transport serves one address, `POST /api/v1/account/promotion`, and only
when the host configuration installs the `promotions` block. The operator side
is `tools/promotion_codes.py`. The full procedure is in
[the promotion code guide](../../../../docs/guides/promotion-codes.md).

## Shares of the worker pool

This section describes current behavior. The transport runs every operation
in a pool of `maximum_concurrent_operations` workers. A worker stays reserved
until its operation finishes, so anything that could hold every worker could
refuse every other caller. Each piece of work therefore names the shares of
the pool it draws on, and no share may hold more than
`maximum_concurrent_operations_for_each_tenant`, which is half the pool and
at least one.

```text
Shares of the worker pool
├── One account
│   ├── every operation that has already resolved its credential
│   └── over the share: status 429, Retry-After, tenant_concurrency_limit_reached
├── Work that waits on another service
│   ├── confirming a browser session or an external token at the identity provider
│   ├── account activation, which reads the identity provider
│   ├── creating a payment session, which also draws on the account's share
│   └── over the share: status 503, Retry-After, external_provider_capacity_reached
└── Everything else
    ├── resolving a host-issued key from this service's own records
    ├── the billing webhook and the public routes
    └── no worker free: status 503, service_busy
```

Resolving a host-issued key reads this service's own records and takes
microseconds. Confirming a browser session or an external token needs a read
at the identity provider, a machine this service does not control and cannot
hurry. One sign-in attempt is therefore up to two pieces of work: the local
record first, and the provider read only if the credential is not a host key.
Where no installed mode consults another service, one attempt stays one piece
of work.

The account share cannot be named by the provider share or the other way
round. A tenant identity may not contain a space, and the provider share is
named `external provider`.

Both ceilings are published under `limits` in the capabilities record, as
`concurrent_operations_for_each_account` and
`concurrent_operations_waiting_on_another_service`.

### Limits of the worker pool shares

- A signed browser session that a paying account already holds still reads
  the identity provider again inside its own operation, when that operation
  revalidates. That read draws on the account's share, not the provider
  share, so one account can hold half the pool across provider reads.
- The share is a count of workers, not of processor time. An account within
  its share can still ask for costly work. Metadata retrieval builds its
  index for each request, and on a catalogue of four hundred items one
  search took about one second of processor time in the probe of
  September 21, 2026.
- The shares are in the memory of one service process, like the
  failed-attempt table. More than one machine needs a shared count.

## Request nesting depth

This section describes current behavior. Every request body is scanned for
its deepest container nesting before it is parsed, and a body deeper than
`MAXIMUM_JSON_NESTING_DEPTH` is refused with status 400 and the code
`nesting_limit_exceeded`. The parser opens one recursive call for each
container it enters, and the interpreter's recursion allowance belongs to the
whole process, so a body deep enough to exhaust it would be an internal fault
rather than a bounded refusal. An internal fault is not a refused attempt, so
nothing counted it and nothing stopped an anonymous caller from sending it
again without end. The depth is published under `limits` as
`request_nesting_depth`.

## Model Context Protocol versions

This section describes current behavior of this source. A deployment serves
it only after a release that includes it.

`/mcp` serves protocol version `2025-11-25` through the `initialize`
handshake and `2026-07-28` with no handshake, where every request names its
version in the `MCP-Protocol-Version` header and in `_meta`. Both come from
the installed `mcp` library, version 2.2.0, behind one stateless Streamable
HTTP endpoint. The library speaks more versions than this release has
qualified, so `select_protocol_binding` in `http.py` chooses the version of
every request before the library sees it, and tells the library its choice in
the header the library routes on.

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

The 2025-11-25 lifecycle requires the answer to an `initialize` for an
unsupported version to name a supported one. This transport refused such a
request with status 400 until September 22, 2026. A refusal on `/mcp` that is
about the protocol itself is answered in the protocol's own error shape,
because a client chooses a version from its code and its list. Every other
refusal keeps the service's own record.

`server/discover` lists every served version, newest first. Its answer and
the tool list carry `ttlMs`, five minutes, and `cacheScope`, `private`, so a
client may reuse them for that long and a shared cache may not hand them to
another caller. The library records every protocol message as a trace span by
default. The service has no telemetry setting for protocol traffic, so it
turns that off. The application refuses to start when the installed library
cannot serve a version the host configured.

### The host record

A host can serve fewer versions. `protocol_versions` in the `http` block of
the host file, record `service_http_configuration/v2`, names them, oldest
first, and both are served when it is absent. Naming only `2025-11-25` stops
the per-request version without a new release.

Version 1 of the record pinned one version in `protocol_version`. Reading it
as both versions would widen what a host file meant, so this release refuses
it, and a release before it refuses version 2. Before a release with this
change starts, a host file whose `http` block carries
`"record_type": "service_http_configuration/v1"` or `"protocol_version"` needs
both members removed, which serves both versions, or replaced:

```json
{
  "http": {
    "record_type": "service_http_configuration/v2",
    "protocol_versions": ["2025-11-25", "2026-07-28"]
  }
}
```

Keep every other member of the block as it is. A host file written by
`examples/29_intelligence_service/prepare.py` before this change carries both
old members.

### The local protocol adapters

The in-process provisioning transport in `core/provisioning_mcp.py` and the
decision tool in `code_nodes/decision_tools.py` use the same library and serve
only the 2025-11-25 handshake. The library would open a connection in the
per-request version if the first request carried it, so both refuse such a
request before the library sees it, and the decision tool answers
`server/discover` as a server without it would, so a client falls back to the
handshake. Both still refuse an `initialize` for another version instead of
answering with 2025-11-25. That is the same lifecycle rule and is not repaired
yet.

### Checks

| Rule | Check in `http_checks.py` unless named |
|---|---|
| An `initialize` for an unsupported version is answered with 2025-11-25 | `initialize_for_an_unsupported_version_is_answered_with_a_supported_version` |
| An `initialize` gets the handshake whatever header it carries | `an_initialize_selects_the_handshake_whatever_version_header_it_carries` |
| A later request for an unserved version is refused before any effect | `a_request_naming_an_unsupported_version_is_refused_before_any_effect` |
| The refusal lists every served version, newest first | `an_unserved_version_is_answered_with_every_served_version_newest_first` |
| A missing, repeated or malformed header is a header fault | `a_missing_repeated_or_malformed_version_header_is_a_header_fault` |
| Only POST is answered | `the_protocol_endpoint_answers_only_POST` |
| Discovery lists every served version | `discovery_lists_every_served_version_newest_first` |
| The official client works at each version | `official_client_uses_real_StreamableHTTP_with_the_exact_supported_profile`, `official_client_uses_the_per_request_version_without_a_handshake`, `an_automatic_client_selects_the_per_request_version_through_discovery` |
| The host record refuses version 1 and unqualified versions | `the_http_record_refuses_version_one_and_versions_this_release_has_not_qualified` |
| A host that serves one version | `a_host_serving_only_the_handshake_refuses_the_per_request_version_and_clients_fall_back`, `a_host_serving_only_the_per_request_version_names_it_when_it_refuses_an_initialize` |
| The installed library must serve each configured version | `an_installed_library_that_cannot_serve_a_configured_version_refuses_the_application` |
| No trace spans without a telemetry setting | `protocol_messages_record_no_trace_spans_without_a_telemetry_setting` |
| The local adapters stay on the handshake | `a_per_request_opening_cannot_select_an_unqualified_protocol_version` in `provisioning_mcp_checks.py`, `a_per_request_probe_falls_back_to_the_handshake_without_a_provider_call` in `decision_tool_checks.py` |

## A binding the public can reach

This section describes current behavior. `serve` refuses to start on a
non-loopback binding unless the host has both declared a trusted proxy and
stated where the client address comes from. Without that statement the
failed-attempt limit is inactive, and nothing in a running service says so
out loud. The refusal names the exact repair. A loopback binding serves only
its own machine and needs no such statement.

## Failed-attempt limit for each client address

This section describes current behavior. The HTTP transport counts refused
sign-in attempts and refused account activations for each client address.
When an address has reached its limit, the transport refuses its next sign-in
attempt with status 429 and a `Retry-After` header. It does this before any
authentication work and before a worker slot is used. `request_limits.py`
owns the settings record and the table. `http.py` owns the places that use
them. This is an internal service mechanic. It adds no runtime type, store or
graph vertex.

The limit is active only when the host states where the client address comes
from. The service never guesses. Behind a proxy the socket peer is the proxy,
so a guessed socket peer would put every caller in one count, and one caller
with a wrong key could make every sign-in wait. A host file that says nothing
about this limit leaves it inactive, and the capabilities record says so.

```text
Request that needs sign-in
├── Host and Origin checks
├── No credential, or more than one credential
│   └── status 401 at once: no worker slot is used and nothing is counted
├── Failed-attempt limit for the client address
│   ├── address source not stated: the limit is inactive, continue
│   ├── at the limit: status 429, Retry-After, code failed_attempt_limit_reached
│   │   └── no authentication work, no worker slot, and not counted again
│   └── under the limit: continue
├── Authentication in a worker slot
│   ├── accepted: never counted, and never clears the count
│   ├── refused with a status from 400 to 499: counted for the address
│   └── answered with a status from 500 to 599: not counted
└── The governed operation
    └── a refusal here, such as a missing scope, is not counted
```

Account activation follows the same path. Every activation request that the
service refuses with a status from 400 to 499 is counted, including a
malformed request. A status from 500 to 599 means that the service or a
provider could not answer. It says nothing about the caller, so it is not
counted.

An address is refused while it has `failures_allowed` counted failures in the
last `window_seconds`. The wait ends when the oldest of those failures leaves
the window. A request that is refused with status 429 is not counted, so
repeated requests do not make the wait longer. While an address waits, a
correct key from that address is refused too, because checking a key is the
work that the limit protects. Public routes stay open to a waiting address.
Examples are the pages, the health route and the capabilities record.

### Settings

`ServiceRequestLimits` is an immutable record with the record type
`service_request_limits/v1`. It is the `request_limits` field of
`ServiceHttpConfiguration`. A host configuration file supplies it as a mapping
inside `http`. The mapping must name the record type. An unknown field, a
missing record type or another version is refused when the service starts.

| Field | Default | Meaning |
|---|---|---|
| `client_address_source` | `not_configured` | Where the client address comes from: `not_configured`, `socket_peer` or `header`. `not_configured` leaves the limit inactive. |
| `client_address_header` | empty | Exact name of the header that holds the client address. Required when the source is `header`, and refused with any other source. |
| `failures_allowed` | 30 | Counted failures that one address may have inside the window. From 1 to 1000. |
| `window_seconds` | 60 | Length of the window. From one second to one day. |
| `maximum_tracked_addresses` | 4096 | The most addresses that the table remembers. From 1 to 65,536. |
| `ipv6_prefix_bits` | 64 | An Internet Protocol version 6 address is counted by this prefix, because one subscriber usually controls the whole prefix. From 32 to 128. |

`failures_allowed` multiplied by `maximum_tracked_addresses` cannot exceed
1,000,000, so the table has a known largest size. When the table is full, the
address whose latest failure is the oldest leaves first. Addresses whose
window has passed leave before that.

The defaults are starting values chosen by judgment. They are not measured.
People behind one shared address share one count, so the default is generous.

The capabilities record publishes a projection of the settings at
`limits.failed_attempts_per_address`. The existing keys under `limits` are
unchanged. The projection is not the settings record, so it has its own
record type, `service_failed_attempt_limit/v1`. It holds `active`,
`client_address_source`, `failures_allowed`, `window_seconds`,
`ipv6_prefix_bits`, `counted`, `refusal_code` and `state`.

Anyone can read the capabilities record without signing in. The projection
therefore leaves out `client_address_header` and `maximum_tracked_addresses`.
No client needs them. If a host ever named a header that callers can set, the
header name would tell a caller which header to forge. The table size would
tell a caller how many addresses empty the table. An operator reads both
values from the host file.

### Which address is counted

```text
client_address_source
├── not_configured: the limit is inactive, and nothing is counted
├── socket_peer: the address that opened the connection to this process
│   └── right only when callers connect to this process directly
└── header: the address in the one header that the host named
    └── right only when the host's own trusted proxy overwrites that header
```

The service reads an address header only when the host configured its exact
name. With the `socket_peer` source, every address header that a caller sends
is ignored. A caller therefore cannot avoid the limit by changing a header,
and cannot put failures on another address.

With the `header` source, the header is used only when it appears exactly
once and holds exactly one address. A missing, repeated, listed or malformed
value is counted for the socket peer address instead. Name only a header that
your own trusted proxy overwrites on every request. A header that a caller can
set or extend is the known-wrong choice. `X-Forwarded-For` is such a header on
most platforms. A check shows that it lets a caller avoid the limit and name a
victim.

The hosted service runs behind the Fly proxy, so its host file needs the
`header` source. For Fly, the documented header is `Fly-Client-IP`:

```json
"request_limits": {
  "record_type": "service_request_limits/v1",
  "client_address_source": "header",
  "client_address_header": "Fly-Client-IP"
}
```

Observed: the [Fly request header documentation](https://fly.io/docs/networking/request-headers/)
says that `Fly-Client-IP` holds the client address as the Fly proxy sees it.
The same page says that with another reverse proxy in front of Fly, the
header holds the address of that proxy and not the address of the caller.
Missing: the page does not say what the Fly proxy does with a
`Fly-Client-IP` value that the caller sent. This has not been checked on the
hosted service.

### Switching the limit on for the hosted service

Merging or deploying code does not switch the limit on. The host file on the
volume does. A request without exactly one credential never uses a worker
slot, with or without the mapping.

State on September 22, 2026. Observed: a read of the public capabilities
record at 18:39 UTC showed `limits.failed_attempts_per_address.active` as
`true` and `client_address_source` as `header`, so the host file on the volume
states the header source. That is step 2 below, on one hostname. Reported the
same day by the engineering session that changed the host file, and not
recorded in this repository: the mapping above is in the host file, and the
Fly proxy overwrites a forged `Fly-Client-IP` value, which is step 3. Step 4
is not recorded. Under step 5 the limit is therefore not yet recorded as
working for the hosted service.

A release that contains the limit does not start without the mapping. The
hosted service starts with `--host 0.0.0.0 --behind-trusted-tls-proxy`, and
`serve` refuses a binding the public can reach when the host has not stated
where the client address comes from. The refusal names the exact repair.
Release 10 and every earlier release started before that refusal existed.
Every container check that writes its own host file and starts the image's
own command states a client address source in that file.
`tools/check_fly_service_container.py` writes the Fly mapping above, and
`tools/check_client_journey_in_containers.py` names a header of its own
because it has no proxy. Each keeps a case that removes the statement and
requires the service to refuse to start. The backup restore check,
`tools/check_pilot_backup_restore.py`, has no host file of its own. It starts
the image's own command with the host file it restored from the volume, so
its service starts only when that restored file carries the mapping.

Do these steps in order to switch the limit on, and repeat steps 2 to 4 after
any change to the proxy in front of the service:

1. Add the mapping above inside `http` in the host file on the volume. Then
   restart the service.
2. Read the capabilities record on every hostname. Confirm that
   `limits.failed_attempts_per_address.active` is `true` and that
   `client_address_source` is `header`.
3. Check a forged header value. From one address, send sign-in requests with a
   wrong key through the Fly proxy. Send one more request than
   `failures_allowed`. Give every request a different forged `Fly-Client-IP`
   value. The last request must be refused with status 429. If every request
   gets status 401, the proxy passed the forged values on. A caller can then
   avoid the limit and can name a victim. Remove the mapping in that case.
4. Check a second address while the first address still waits. Send one
   sign-in request with a wrong key from another network. It must get status
   401. If it gets status 429, the header does not arrive in a usable form,
   and all callers share one count. Remove the mapping in that case.
5. Do not record the limit as working for the hosted service before steps 2,
   3 and 4 have passed. Steps 3 and 4 make the first address wait for up to
   `window_seconds`.

Remove the mapping from the host file before you start a release that was
built before this limit existed. Such a release refuses a host file that
contains `request_limits`, and it does not start. At the time of writing these
are release 8 and every earlier release. A rollback is the usual case.

### Limits of this design

- The limit does nothing until the host states the address source. A host
  file written before this limit existed states none. Read
  `limits.failed_attempts_per_address.active` in the capabilities record to
  see the current state.
- A release from before this limit does not know the `request_limits` mapping
  and refuses a host file that contains it. Remove the mapping from the host
  file before you start such a release, for example during a rollback.
- The `Fly-Client-IP` mapping is right only while the Fly proxy is the
  outermost proxy. With another reverse proxy in front of Fly, the header
  holds the address of that proxy. All callers would then share the few
  addresses of that proxy, and one caller with a wrong key could make every
  sign-in wait. Change the mapping before such a proxy is placed in front of
  Fly. Name a header that the new outermost proxy overwrites, and repeat the
  hosted checks above. Today the domain records are not proxied.
  `docs/guides/launch-setup-runbook.md` says that Cloudflare proxying can be
  considered separately.
- With the `header` source, a request whose header is missing, repeated,
  listed or malformed is counted for the socket peer address. Behind a proxy
  that address is the proxy. If the configured header stops arriving in a
  usable form, every request is counted under the address of the proxy. All
  callers then share one count, and one caller with a wrong key can make
  every sign-in wait. The service does not report this state. The second
  address check above shows it.
- The table is in the memory of one service process. This is correct for one
  process on one machine, which is the current deployment. The table is not
  shared between processes or machines, and a restart empties it. More than
  one machine needs a shared store or a limit at the proxy.
- Attempts that are already inside authentication when an address reaches its
  limit are allowed to finish. At most `maximum_concurrent_operations`
  attempts can be inside authentication at one time, so at most that many
  refused attempts from one address can finish after the limit is reached. A
  check holds every worker slot open, sends further attempts while they are
  held, and requires each of those to be refused with `503 service_busy`.
- A caller who controls more addresses than `maximum_tracked_addresses` can
  make the table forget the oldest address early. Such a caller already has
  that many separate allowances. The worker slots remain the ceiling for all
  callers together.
- People who share one address share one count. While one of them keeps
  failing, the others wait too.
- This table limits sign-in and account activation. The public sign-up and
  recovery routes are limited too, but by their own two tables described in
  the next section, because a sign-up that is accepted still sends a message
  and this table counts only refused attempts. The billing webhook, the
  public pages, the capabilities record and the identity configuration are
  anonymous routes without such a limit.
- A governed operation can run its work twice for one refused request, because
  its Loop runs up to two steps. The limit counts one refused attempt for that
  request.

## Public sign-up and password recovery email

This section describes current behavior. `account_email.py` owns it.
`http.py` owns the two routes that use it. It is an internal service
mechanic and an adapter used by Loops. It adds no runtime type, no store and
no graph vertex. The whole journey stays on the service domain, and no
setting of the identity provider has to change.

```text
Public sign-up or password recovery
├── POST /api/v1/account/signup or /api/v1/account/recovery
├── The adapter is not installed
│   └── status 404, code account_email_unavailable, no provider request
├── The operation is switched off for this host
│   └── status 503, code account_signup_unavailable or account_recovery_unavailable
├── prepare: read the request and count the attempt
│   ├── unknown record version, unknown field, unreadable address or password
│   │   └── status 400 with a stable code, before any provider request
│   └── over the allowance of the client address or of the email address
│       └── status 429, Retry-After, code failed_attempt_limit_reached
└── deliver: exactly one request to each provider
    ├── the identity provider generates a link and sends nothing
    │   ├── a token hash for this address and this action
    │   │   └── the message carries this service's link
    │   ├── a definite refusal that could be about the address
    │   │   └── the message carries a notice, with no link and no token
    │   └── a refusal of this service itself, status 401, 403 or 429
    │       └── status 503, code identity_link_refused, nothing is sent
    ├── the mail provider sends exactly one message
    └── status 202 with the same record either way
```

The refusal branch is the one that keeps the interface from saying who is
registered. This release reads no field of a refusal body. Only the three
statuses that answer the same way for every address reach the caller: the
server key was refused, this service may not use the interface, or this
service is over the provider's own rate. Every other definite refusal, in any
shape, takes the same path as the expected one, so a caller reads the same
status and the same bytes whether or not the address has an account. The cost
is that a refusal this release cannot explain, such as a password that the
provider's own policy rejects, sends the notice message instead of reporting
the problem. Set `minimum_password_length` at or above the identity provider's
own minimum so that this does not happen.

The result record is `service_account_signup_result/v1` with status
`confirmation_sent`, or `service_account_recovery_result/v1` with status
`recovery_sent`. Like every other route under `/api/v1/`, the record is
carried inside `service_http_result/v1`, so a caller reads
`result.record_type` and `result.status`. The answer is the same for an
address that already has an account and for one that does not, and both
paths do the same amount of work: one request to each provider and one
message. `GET /api/v1/account/identity` reports `signup_available` and
`recovery_available` as Booleans.

The link in the message is
`<public origin>/auth/confirm?token_hash=<value>&type=signup` or
`&type=recovery`. The website's `/auth/confirm` view reads the token hash,
removes it from the address bar and the history at once, and asks for a new
password first. On submit it gives the token hash to the identity library's
`verifyOtp`, sets the chosen password with `updateUser`, and only then calls
`POST /api/v1/account/activate`, for sign-up and recovery alike. The link that
the identity provider generates for itself is never read and never appears in
a message.

Once `updateUser` has accepted the password, the card never again shows the
notice that the link cannot be used. While the activation and the session
request run, it keeps the password step with the status "Password set. Opening
your account…". If the service does not open the account, the card says "Your
password is set." and offers Sign in. The persona journeys of September 24,
2026 recorded the earlier behavior: for a quarter to half a second after the
password was accepted, the card said "This link cannot be used. ... Nothing
was changed." The browser checks
`password_set_keeps_its_card_while_the_account_opens`,
`the_unusable_notice_never_appears_after_the_password_is_accepted` and
`a_password_set_without_an_open_account_says_so_and_offers_sign_in` hold the
activation request back to reproduce a slow connection.

An email sign-in lasts as long as the browser tab. Once the service has opened
the account, the page keeps the identity provider's access token and its
expiry, and nothing else, in the tab's session storage under
`baltor.identity-session`, and opens the account again after a reload or an
address typed in the same tab, on the page asked for. Signing out, a refused
session or another sign-in removes it. No refresh token is kept, so a kept
sign-in ends when its access token expires. A confirmation's session is kept
only after its new password is set and the account opened, and a page opened
by a confirmation link starts from the link instead of a kept sign-in. The
browser checks `the_kept_sign_in_holds_the_access_token_and_its_expiry_alone`,
`a_reload_and_a_typed_address_keep_an_email_sign_in`,
`signing_out_forgets_the_kept_sign_in`,
`a_page_opened_by_a_confirmation_link_starts_from_the_link`,
`a_confirmation_whose_password_is_not_set_is_never_kept`,
`a_service_token_is_never_kept` and
`a_reload_keeps_the_administration_link_and_view_for_staff` hold these rules.

Sign-up is email first. `service_account_signup_request/v2` carries the
address alone, and the retired version 1, which carried a caller's password,
is refused. The provider's interface needs a password to create a user, so
the adapter generates one for each request with `generated_signup_password`
and keeps it nowhere. The probe of September 23, 2026,
`artifacts/architecture-audit-2026-09-19/identity-unconfirmed-signup-probe-1.json`,
showed why: a second sign-up link for an address that is not confirmed keeps
the first password. `GET /api/v1/account/identity` also publishes
`minimum_password_length`, the shortest password the confirmation page takes.

### What this adapter refuses

- A sign-up request that carries a password, in any field or in the retired
  version 1 record, before anything is counted or asked of a provider.
- An address that is not printable ASCII with one `@`, a local part of at most
  64 characters and a domain of at least two labels. An address written with
  the letters of another script can look the same as one written with Latin
  letters, and this service cannot tell the owners apart.
- A generated link whose answer names another address or another action. The
  provider returns `email` and `verification_type` beside the token hash, and
  both must match the request. Without this rule a token hash for another
  account would be put in a link and sent to the address that asked, and
  whoever opened it could confirm that account and then set its password.
- A redirect answer, an oversized answer, an answer that is not one JSON
  object, an answer with a repeated field, and an answer that arrives after
  the deadline. Each is reported with status 503 and a stable code, and
  nothing is sent a second time.
- A host file that opens sign-up or recovery without a stated client address
  source in `http.request_limits`. Code
  `account_email_needs_a_stated_client_address_source`.
- A host file that opens sign-up while `browser_identity.registration_enabled`
  or `browser_identity.email_signup_enabled` is false. Code
  `account_email_signup_needs_open_registration`. Sign-up finishes at
  `POST /api/v1/account/activate`, which refuses while account creation is
  closed, so opening sign-up against a closed browser identity would confirm
  an address at the identity provider and leave the person with no account of
  this service and no record. Recovery alone is not refused: a person who
  already has an account may need a new password while account creation stays
  closed, which is the private beta state.
- An installed adapter that declares a boundary other than `account_email/v1`,
  or none. The application refuses it before it serves either route.
- A provider key whose text does not start with the prefix of the key kind
  that slot needs, so a publishable browser key pasted into the server slot
  stops the request before it leaves.
- A host block with an unknown key, another record version or another
  provider pair. The loader refuses it before the service serves anything.

### Two allowances

Sign-up and recovery use the same limiter class as the sign-in limit, with
two tables of their own. Every attempt is counted, accepted or refused,
because the cost being limited is the message that an accepted attempt
sends.

| Table | Key | Default allowance | Active when |
|---|---|---|---|
| Client address | The address key the service already computes for sign-in | `attempts_for_each_address`, 10 in `attempt_window_seconds`, 3600 | The host stated an address source in `http.request_limits` |
| Email address | A SHA-256 digest of the address, so the table holds no address | `attempts_for_each_email`, 3 in the same window | Always |

The client address table follows the same source as the sign-in limit, but it
is not permitted to stay inactive here. The sign-in limit may: what an
inactive table costs there is bounded guessing against one credential. Here an
inactive table would leave only the allowance for each email address, and one
caller could then send a message to as many different addresses as it chose,
at the cost and the sender reputation of this deployment. A host that opens
either operation without a stated source is refused before the service starts.

### Limits of the account email design

- Nothing is stored. The service keeps no record that a message was asked for
  or sent. The two tables are in the memory of one service process and are
  empty again after a restart.
- A message that the mail provider accepted may still not arrive. The service
  reports what the provider answered, not delivery.
- The identity provider creates the account when sign-up generates a link.
  Until the address is confirmed the account cannot be used, because the
  browser identity adapter requires a confirmed address.
- Asking for sign-up with an address that already has an account sends a
  notice to that address. The two allowances bound how often that can happen.
- The sign-up and recovery routes are public. The service does not know who
  asked, only the address the request came from.
- For an address that has never been confirmed, a second sign-up link keeps
  the first password and makes the earlier link unusable, as observed on
  September 23, 2026. The service therefore never takes a password from a
  caller, and the confirmation page replaces the password before the account
  opens. The identity provider's own public sign-up still takes a password from
  anyone who holds the public key until the owner closes it; until then a
  password chosen first opens an address from its confirmation to the moment
  its owner submits a new password on the same page.
- A refusal this release cannot explain is indistinguishable, to the caller,
  from an address that is not eligible. That is deliberate. The operator's
  signal for such a refusal is the identity provider's own log, not this
  service, because this service stores nothing and its answer must not vary
  with the address.
- The deadline for one provider request bounds the whole body read from the
  moment the request started. The client's own deadline applies separately to
  connecting, writing and waiting for the answer's first line, so the worst
  case for one request is a small multiple of `timeout_seconds` rather than
  exactly that number. A provider that dripped the answer's headers, before
  any body, would still be bounded only by that per-phase deadline.

The operator guide is
[account email operations](../../../../docs/guides/account-email-operations.md).

## One way in, staff roles and free monthly Baltor Pro

This section describes current behavior of the source. The component guide
explains it for a reader of the service; this is the rule list and the checks
that hold each rule. The owner's decisions of September 23, 2026: one way in,
three staff roles with permissions fixed in code, and the first ten accounts
free each month.

- `require_admitted` refuses a provider identity unless its current user record
  carries `baltor_account` in `app_metadata` and the service holds
  `service_account_origin/v1` for the same issuer and provider user. The
  browser identity adapter calls it on every sign-in and every activation.
- The sign-up adapter calls `AccountOrigins.prepare_signup` before it asks for
  a link, whenever the host loader installed it, which it always does. The link
  must name the provider user that call prepared.
- A replacement archives first, then deletes at the provider, then creates
  the fresh marked account. The archive holds a digest of the address and no
  address, and it commits only while no service sign-in is bound to the
  account. An account the service already holds a sign-in for is never
  replaced by a public sign-up; its owner is sent the notice, and the marking
  command admits it.
- `ServiceAccountPolicy` reads the `accounts` host block. It names staff by
  provider user identity or address, and the founding count, ten by default.
  `ROLE_PERMISSIONS` is the only source of a permission.
- `AccountAdministration.apply` checks the permission, rechecks the staff
  session, its sign-out record and its expiry, and commits the action with its
  audit record against the request identity.
- `consider_founding_offer` compares the decision and the count about to be
  written separately, and commits against the counter's exact version.

| Guard | Named check | Removed-guard control |
|---|---|---|
| The provider's mark | `an_unmarked_provider_identity_is_refused_and_only_both_marks_admit` | `removed_provider_mark_requirement_is_detected` |
| The service's own record | the same check | `removed_service_record_requirement_is_detected` |
| The guard in the browser identity adapter | the same check | `removed_one_way_in_guard_is_detected` |
| Replacement of an unmarked account | `the_replacement_flow_leaves_no_old_session_refresh_token_or_password_usable` | `removed_replacement_keeps_the_first_registrant_in_and_is_detected` |
| Deletion at the provider | the same check | `removed_deletion_at_the_provider_is_detected` |
| The archive before replacement | the same check | `removed_archive_before_replacement_is_detected` |
| No public deletion of an account with a service sign-in | `an_account_the_service_already_holds_a_sign_in_for_is_never_deleted_by_a_public_sign_up` | `removed_bound_account_rule_is_detected` |
| The link names the prepared account | `a_sign_up_link_for_another_account_is_refused_before_any_message` | `removed_link_to_prepared_account_rule_is_detected` |
| The plan digest of the marking command | `the_marking_command_lists_before_changing_applies_only_the_listed_plan_and_is_idempotent` | `removed_plan_digest_rule_is_detected` |
| The permission table | `developer_and_analytics_roles_cannot_grant_revoke_disable_enable_or_list` | `removed_role_permission_table_is_detected` |
| Revocation | `revoking_free_monthly_removes_access_at_the_next_check` | `removed_revocation_is_detected` |
| The founding limit | `the_first_ten_accounts_hold_the_founding_offer_and_the_eleventh_does_not` | `removed_founding_limit_is_detected` |
| The founding counter's exact version | `a_race_for_the_last_founding_place_yields_exactly_ten` | `removed_counter_guard_lets_the_race_pass_ten_and_is_detected` |
| Monthly renewal | `free_monthly_renews_each_month_until_revoked` | `removed_renewal_is_detected` |

Other named checks hold the rest: the host loader installs all three parts and
refuses a permission or a fourth role in the host file; a customer or a host
key cannot reach the staff routes; a foreign browser origin is refused; an
expired or signed-out staff session changes nothing; every action writes one
audit record; a repeated request identity replays; analytics reads no address
and a developer reads no count; the sign-up answer is the same for a new, a
known and a replaced address. They run in `account_origin_checks.py` and
`account_administration_checks.py`, both from the service smoke run.

Limits. The number of requests a sign-up makes to the identity provider now
depends on who held the address, so the time an answer takes can differ; its
status and bytes do not. The founding decision is kept for each account, so an
account that finished sign-up while the places were full is not granted later.
The account list reads every provider user on each request, which suits a
young service and needs paging before many thousands of accounts.

### Sign-up links a superadmin sends

The owner's request of September 24, 2026: a superadmin types one or more
addresses, and each person gets one message that names who sent it and links
to the same `/auth/confirm` page. `send_sign_up_links` in
`staff_sign_up_links.py` is Baltor's own sign-up started by a staff member, so
it adds no way in.

- `StaffSignUpLinkRequest` refuses a record of another version, an unknown
  field, more than `MOST_ADDRESSES` (ten) addresses and an address named twice,
  before any request to the identity provider.
- The permission is `accounts.send_sign_up_links`, which only the superadmin
  row of `ROLE_PERMISSIONS` holds. The route rechecks the staff session like
  every staff action.
- The request identity is reserved first, as an audit record in progress. A
  completed identity replays its first result; an identity still in progress
  is refused with `sign_up_links_in_progress`, so an interrupted batch is never
  sent twice under it.
- For each address, an account the service already holds a sign-in for, or a
  confirmed account with both marks, is refused before any count or message.
  Then the allowance for one address that public sign-up keeps is checked and
  counted, then `AccountOrigins.prepare_signup` prepares the account with both
  marks, and the link must name the prepared provider user.
- The pending link records and the completed audit record commit in one
  write. They hold digests of the addresses, never an address.
- `complete_on_activation` runs from the browser identity adapter's
  activation, before the founding offer. It completes the pending record and,
  when free monthly Baltor Pro was asked for, commits the grant in the same
  write. An account that already holds free monthly or a paid plan keeps it.

| Guard | Named check | Removed-guard control |
|---|---|---|
| Only a superadmin sends | `developer_analytics_and_customers_cannot_send_sign_up_links` | `removed_sign_up_link_permission_is_detected` |
| No second message for an open account | `an_address_that_already_has_an_account_is_refused_without_a_second_message` | `removed_existing_account_rule_is_detected` |
| At most ten addresses | `a_batch_over_the_limit_is_refused_before_any_provider_request` | `removed_batch_limit_is_detected` |
| The allowance for one address | `a_repeat_within_the_allowance_sign_up_keeps_for_one_address_is_refused_without_a_message` | `removed_allowance_for_one_address_is_detected` |
| Free monthly when the account opens | `free_monthly_is_granted_when_the_account_opens_and_the_link_leaves_the_pending_list` | `removed_free_monthly_on_activation_is_detected` |
| The staff form in the Administration view | `a_superadmin_sends_a_sign_up_link_and_the_account_shows_as_waiting`, in the browser suite | `hide_the_sign_up_link_form` |
| Confirm waits for the sign-in settings | `the_confirm_button_waits_for_the_sign_in_settings`, in the browser suite | `let_confirm_run_before_the_sign_in_settings_load` |

Other named checks in `staff_sign_up_link_checks.py`, run from the service
smoke run: a superadmin's batch prepares each account with both marks and
sends one message naming the sender; a batch and its audit record share one
request identity and hold no address; an interrupted batch is not sent twice;
and the route serves a superadmin over HTTP and refuses an analytics staff
member, a customer, a host key, a foreign browser origin, a query string and a
batch over the limit.

Limits. The allowance for one address is kept in process memory, as it is for
public sign-up, so a restart starts it again. A batch interrupted after its
reservation leaves any account it prepared without a pending record, so that
account opens without the free monthly grant; a superadmin grants it from the
account list. A batch of ten addresses makes up to about fifty requests to the
identity provider and the mail sender in one staff request.

## Waiting list

This section describes current behavior. `waitlist.py` owns it. A host that
declares a `waitlist` block in its configuration serves
`POST /api/v1/waitlist`, where anyone can leave an email address and an
optional note without signing in, and `GET` and `POST /api/v1/admin/waitlist`,
where an operator with the administration scope reads the list and applies
one decision at a time. A host without that block serves neither, and both
answer `waitlist_unavailable`. The form is on the waiting list page at
`/waitlist`, and the guide at `/setup` links to it. The page offers the form, its link and the discount
sentence only when the capabilities record says `waitlist_available`, and
names the discount only when it also says `discount_code`. When the record
says `registration_available`, account creation leads the guide instead. Like every other public statement on the page, the offer is
read only from `service_capabilities/v1`, so a record version the page was not
written for offers nothing. The pricing page's list of unfinished work and the
sign-up page's note that the form is still being built name the waiting list
form only while the service offers no list.

A refused request to join is a refused attempt from one client address, so
the failed-attempt limit counts it like a refused sign-in. The list counts
accepted entries for each declared client address source on its own. With no
declared source, `FailedAttemptLimiter.address_key` names no address, and every
accepted entry records `no_declared_source` instead of one count shared by
every caller behind a proxy.

The count never stores the address. It is kept under a keyed one-way digest:
HMAC-SHA256 of the source key with the host secret that
`waitlist.source_secret_ref` names as an environment reference, read at use
through `environment_secret`, the resolver every other host secret uses. The
record `service_waitlist_source/v2` is named by that digest and holds only the
times of accepted entries inside the window, which is at most one hour, the
period the published privacy notice promises. Every request to join removes
the times that have left the window from every source record, and removes a
record with no time left through the catalogue removal batch. A record that
an earlier release left with an empty list is removed the same way. The
retention task below does the same on its own schedule, so a list that nobody
writes to keeps nothing past the window either. The reader refuses
`service_waitlist_source/v1`, which was named by the address itself, and any
record that carries a field beyond its times.

With a declared source and no named secret, every accepted entry records
`no_source_secret` and nothing about the address is stored; the guard never
falls back to an unkeyed digest. A named secret that the service cannot read
refuses the request with `waitlist_source_secret_unavailable`, and one
shorter than 32 characters with `waitlist_source_secret_unusable`, both status
503 and both before any write. `source_privacy_checks` in `waitlist_checks.py`
holds each rule, with a known-wrong case beside it, and
`source_removal_checks` in `waitlist_source_checks.py` holds the removal.

The entries, the decisions, removal on request and the invitation command are
described in
[the waiting list guide](../../../../docs/guides/waiting-list-and-invitations.md).

## Retention of expired records

This section describes current behavior. `retention.py` owns it. The published
privacy notice keeps two kinds of record for a bounded time, and the service
removes each one when its time has passed and never before:

```text
Records with a time limit
├── service_browser_session_revocation/v1
│   ├── kept until the signed-out session would have expired
│   ├── removed when expires_at is at or before the runtime clock
│   └── a record of any other version is left in place and counted
└── service_waitlist_source/v2
    ├── keeps only the times of accepted requests inside the window
    └── a record with no time left inside the window is removed
```

The removal runs in three places:

1. Right after every sign-out commits. `revoke_browser_session` calls
   `sweep_after_sign_out`, which removes every revocation that has already
   expired. A failure there changes nothing about the sign-out or its answer,
   and the answer never shows what was removed.
2. From one periodic task. The HTTP application starts it in its Starlette
   lifespan and cancels it when the service stops. It runs once soon after
   start, then every `sweep_interval_seconds` of the host's
   `service_retention_policy/v1` block, named `retention` in the host
   configuration. The default is 600 seconds, and the setting accepts 1 to
   3600. There is no setting that switches the removal off. A service without
   host write authority starts no task. A run that fails is recorded as the
   last outcome and the task keeps its schedule.
3. By hand, with `loop-engine service remove-expired --config <host file>`. It
   reads only the runtime and waiting list blocks, starts no server and prints
   one `service_retention_report/v1` record of outcomes and counts. It never
   prints a digest, a record identity or a tenant. It exits with status 1 when
   any part did not complete.

Each removal is a removal batch with an exact version precondition for each
removed record, so a record that another writer changed or removed first is
never removed from a stale read. A run that loses such a race reads again, for
three rounds at most, and then leaves the record for the next run. A run with
nothing to remove reads without write authority and writes nothing.

Removing a revocation early would let a signed-out session back in, so two
rules make the removal safe while a request of that session is being checked:

- The revocation keeps the token expiry rounded up to a whole second, so it
  outlives every moment the token can still be accepted.
- The expiry is read again after the revocation. `expired_by_now` in
  `browser_identity.py` refuses a token whose expiry has passed by the time
  its revocation was read, and `_customer_authorize` in `access.py` reads the
  session expiry after the revocation. A session whose revocation was removed
  between two reads is past its expiry by the second one.

The health answer carries `retention_sweep_current`, a reported check that is
never required. It passes when the last run completed. Otherwise its code
names why: `retention_sweep_not_run_yet` just after start,
`retention_sweep_not_running` when no task runs, or the code of the last
failure. Asking for health reads that outcome from memory and never runs a
removal.

`retention_checks.py` holds each rule over real records, with a known-wrong
case beside it: an expired revocation left after a run, a revocation removed
before its session expired, a sign-out without its removal, a lost race, a
removal handed to a store that does not declare it, an acknowledgment for a
batch that removes something else, a removal that was acknowledged and not
made, the expiry read before the revocation, a task that ends on its first
failure, a health answer that removes, and a report that names what it
removed. The two races of a request that is being checked are held in
`browser_identity_checks.py`.

## Persistence and concurrency contract

The optional `catalog_atomic_write_batch/v1` contract checks all expected
record versions and absence conditions under one SQLite `BEGIN IMMEDIATE`
transaction, then commits every write or rolls back all of them. Read-only
guards can bind authentication and disclosure state to a usage append without
rewriting those records. Another store can implement the same declared
capability. Unsupported or unknown capability negotiation refuses; domain
code does not branch on a backend class.

A batch that removes records is its own version,
`catalog_atomic_write_batch/v2`, and a store applies it only when it declares
the optional operation `atomic_record_removal` and that exact version.
`require_atomic_removal` negotiates both before the batch is built, and
`ServiceCatalogBinding.commit` refuses a removal with
`store_contract_unavailable` before any effect when the store declares
neither. The SQLite store and the in-memory reference store apply removal
batches. The DuckDB store, the DuckDB file engine and the package JSONL store
declare the operation unsupported.

```text
catalog_atomic_write_batch/v2
├── removals: exact record identities
├── each removal needs a precondition with the exact version the caller read
├── a missing record or another version fails that precondition, and the
│   whole batch is refused with nothing changed
├── a record is never written and removed in one batch
└── the batch digest covers the version, the writes, the removals and the
    read set, so an acknowledgment for any other batch is an unknown commit
```

After the acknowledgment, the binding reads every write back and confirms that
the store no longer holds each removed record at the removed version. A store
that acknowledges a removal it did not make is an unknown commit, never a
success.

Before choosing this shape we compared how other record stores express a
conditional removal. A DynamoDB `TransactWriteItems` request holds `Delete`
actions with condition expressions beside writes and read-only condition
checks, fails as a whole when any condition fails, and refuses two actions on
one item. A Kubernetes delete can carry preconditions on the resource version
and fails with a conflict when they do not hold. An etcd transaction compares
revisions before a delete, but it deletes a missing key with a count of zero
and no error. A log-compacted store such as Kafka writes a tombstone that
keeps the key. We adopted the DynamoDB and Kubernetes shape: a removal is
exact, guarded by the version the caller read, and applied in the same atomic
batch as writes. We rejected the silent zero-count delete, because a removal
that names a missing record is refused here rather than read as success, and
we rejected tombstones, because a tombstone keeps an identity derived from the
session digest that the privacy notice promises to remove.

Every domain operation opens a separate connection, preserving the existing
SQLite adapter's thread contract. This is a serialized embedded-database
profile, not a claim about multi-region consistency or clustered throughput.
The existing SQLite write-ahead-log runtime qualification guard still applies.

Usage is identified by tenant and caller request identity. The exact item,
source, body digest, unit, and quantity bind the effect. A retry reuses the
stored acknowledgment; a changed effect is refused. A missing or malformed
write acknowledgment remains unknown. Retrying the same request reconciles
an existing committed row without charging again.

## Operator observability

`observability.py` holds three separate facts about one request. They are not
merged and each is versioned on its own.

```text
Operator observability
├── Request reference
│   ├── Issued from the operating system random source and nothing else
│   ├── The issuing function takes no argument, so no credential can reach it
│   ├── Shown to the customer in a refusal, never on a successful answer
│   └── A reference this process did not issue is refused when recorded
├── Failure journal: service_request_failure/v1
│   ├── Reference, route, method, refusal code, status, tenant, time, version
│   ├── A bounded ring over the existing service collection and namespace
│   ├── An undeclared path is recorded as unmatched, never as it was sent
│   └── Recording never raises; a refusal cannot become a different failure
└── Readiness: service_health/v2
    ├── Alive and ready are separate fields with separate meanings
    ├── A required dependency that fails answers 503
    ├── Reported dependencies are named and do not remove the machine
    └── The retention task's last outcome is reported and never required
```

Recording is governed by `service_observability_policy/v1`. The default records
metadata and no request body; `metadata_and_request_body` is an explicit host
choice, and asking to record a body without it is refused with
`payload_capture_not_authorized`. A credential, an authorization header and any
other header that carries authority are never recorded under any setting. The
bodies of sign-up and promotion redemption carry a password and a promotion
code, so `CREDENTIAL_BODY_ROUTES` in `http.py` keeps both out of every failure
record even when the host captures bodies.

`loop-engine service failures` reads the journal by newest, by tenant or by
reference. It builds the journal from the host configuration with host write
authority withheld and starts no server, so it answers while the service is
refusing every request or is not running.

The operator procedure, including the first failure of each dependency, is the
[service failure diagnosis guide](../../../../docs/guides/service-failure-diagnosis.md).

## Disclosure binding

`DurableProvisioningBinding` uses persistent exact tenant grants and the
existing host qualification resolver. It rechecks principal and grant
revisions after body loading and metering. Payment alone never approves an
item. The optional `expected_digest` on manifest/read binds the caller's
selected body and refuses a changed item before loading or metering.

Host-attested review remains distinct from independent source qualification.
The service does not infer promotion from labels, subscriptions, or retrieval.
Metadata-only key scopes also narrow the returned `body_allowed` projection.

## Catalogue releases

This section describes the source in this repository. A deployment serves it
only after a release that includes it. The design, the prior art and the
decision record are in
[the catalogue release design record](../../../../docs/architecture/CATALOGUE-RELEASES-AND-HOT-SWAP-2026-09-22.md).

A host can add, change and withdraw harness intelligence items while the
service runs. The host file's `catalogue` section, record
`service_catalogue_source/v1`, chooses the source:

```text
Catalogue source
├── image   the reviewed manifest packaged in the image; the behaviour before this change
└── store   the active release in the service store, bodies in the declared body folder
```

```json
"catalogue": {"record_type": "service_catalogue_source/v1", "source": "store",
              "body_store_root": "/data/catalogue-bodies", "refresh_seconds": 60,
              "new_accounts_follow_release": false}
```

`refresh_seconds` is a whole number from 5 to 3600. `body_store_root` is an
existing absolute folder on the volume, never inside the image. With
`new_accounts_follow_release` true, a new account follows the active release
instead of copying `starter_identities` once, so the host file names no
starter identities.

```text
Catalogue modules
├── catalogue_packages.py   packages of any harness file type, and the body store edge catalogue_body_store/v1
├── catalogue_schema.py     the attribute schema catalogue_attribute_schema/v1
├── catalogue_bundle.py     the release bundle an operator publishes, read with the manifest rules
├── catalogue_releases.py   releases, the pointer, withdrawals, the state marker, publish and rollback
├── catalogue_grants.py     grants that follow the active release, service_grants/v2
├── catalogue_search.py     one reusable index for each view, and the authorized search over it
├── catalogue_serving.py    the served view, the refresher and the start gate
└── catalogue_commands.py   the operator commands
```

**What is served.** Every request captures one immutable view: the catalogue,
the qualification resolver, the body reader and one search index. The
refresher, started with the web application, reads the state marker every
`refresh_seconds`. When the active release changed, it builds the next view
off to the side on the default executor, reads every body of every served
item and checks its digest, builds the index, and installs the view with one
assignment. A request already running finishes on its own view. A failed
build keeps the previous view and writes a failure record with refusal code
`catalogue_refresh:<code>` to the failure journal, which
`loop-engine service failures` reads. A withdrawal alone does not rebuild the
index; the next view leaves the item out and shares the index.

**Search.** Full text covers the purpose, identity, kind and source layer, as
before, and the words of every searchable attribute. A request may add
`filters`, a mapping of at most eight attributes to `equals`, `any_of`, or
`at_least` and `at_most` for a number or date. A filter on an undeclared or
internal attribute is refused with `search_filter_not_allowed`. Each hit adds
`attributes`, with shown public attributes only, and `package`, with the file
list of a store item. The result names `catalogue_release`.

**Packages.** An item's files each carry a placement path, digest, size, media
type and role. A one-file UTF-8 text package serves the file itself. Any other
package serves its canonical `catalogue_package/v1` document, and
`/api/v1/download` with `path` returns one file of it, with that file's digest
in `X-Content-SHA256`. The same `request_id` for every file of one package
records one measured unit.

**Grants.** The grants record of an account is version 1, the exact snapshot
that `apply-grants` writes, or version 2, which follows the active release:
every approved item of the served view minus the account's denials.
`follow-catalogue-release --tenant ACCOUNT` moves one named account to version
2. With `--all-tenants` it moves only the accounts already granted every item
the served view offers, on the terms following gives, leaves an account that
follows already with its denials, and lists every account it left alone under
`left_out` with the reason `already_following` or `not_granted_every_item`.
`stop-following-catalogue-release --tenant ACCOUNT` returns one following
account to version 1: a snapshot of exactly what it receives from the served
view now, so an account that denies every current item keeps an empty list and
an item published later does not reach it. Both commands that read the served
view refuse with `catalogue_state_changed` when the catalogue changed after
that view was built, and the stop command refuses an account that does not
follow with `account_not_following_release`. `apply-grants` reports a
following account's count and never writes over it. An item that declares
effects is withheld until the client declares them, for both versions.

**Withdrawals and rollbacks.** A withdrawal names an item identity and its exact
body digest. A later release that lists it is refused, a rolled-back view
leaves it out, and every manifest and body read checks the withdrawal record
first, so a withdrawal is refused at once with `item_withdrawn` even on a view
built before it. An item left out of the view answers `item_unavailable`, the
answer the service gives for any item a caller may not see.

**The state marker.** The first catalogue write creates `catalogue_state/v1`
with state version 1. An image refuses to start on a state version it does not
list, and refuses to start when the store holds catalogue state and the host
file has no `catalogue` section. Every catalogue command needs that section, and
an image that predates this change refuses a host file that has it. The rule for
an image rollback follows: the rollback target must understand the current
catalogue state version, which `loop-engine service catalogue-status` prints.

The checks are `catalogue_release_checks.py`, in the folded self-test, and
`catalogue_serving_checks.py`, on loopback inside `http_checks.self_test()`.
Each known-wrong case has a removed-guard control, listed in the design record.

**Limits, measured locally.** On one workstation a synthetic 10,000-item release
built its view in 4.9 seconds with a peak of 168 megabytes resident, searched in
17 milliseconds at the median in lexical mode and 45 in hybrid mode, and swapped
to the next release in 4.9 seconds. At 100,000 items the view needs about 1.4
gigabytes and a swap about 2.0 gigabytes, and the bodies take 592 megabytes of
disk, so that size needs the next engines named in the design record: an index
file built by the publisher, and object storage for bodies. These are local
measurements, not production claims.

## Stripe event and provider contracts

The host installs exact account, event API version, test/live mode, signing
secret references, and owner-chosen Price IDs. There is no default price or
automatic checkout, customer, invoice, or payment creation.

Signature verification uses the exact raw body, timestamp, and version 1
signature scheme. Expired signatures, wrong account/mode/version, duplicate
JSON fields, and changed data under an existing event identity refuse.
The handler stores identifiers, statuses, selected subscription metadata, and
digests, not the raw webhook body or credentials.

Stripe does not guarantee event delivery order and says not to use event
creation timestamps as an ordering key. This implementation deduplicates by
event identity, invalidates paid access, then resolves current subscription
state. It guards that provider read with the preceding catalogue revision so
a delayed response cannot overwrite a concurrent newer decision.
[Stripe webhook guidance](https://docs.stripe.com/webhooks#event-ordering)

An active subscription grants body access only when an owner-configured Price
is present, the current period is valid, and the expanded latest invoice is
paid. Trial access needs an explicit policy choice. Incomplete, unknown,
unpaid, paused, canceled, expired, or unconfigured states do not grant access.
[Stripe subscription event guidance](https://docs.stripe.com/billing/subscriptions/webhooks)

`StripeSubscriptionReader` can read the exact account and all customer
subscriptions using bounded pagination. Its network flag defaults to false,
redirects refuse, and secrets resolve only after authority is checked.
It has no charge or checkout operation. `resume_event(event_id)` lets a host
worker reconcile a durable previously verified pending event after an outage.

## Verification and limits

`runtime.self_test()`, `billing.self_test()`, and `stripe_provider.self_test()`
exercise real temporary SQLite files, reopen, revocation, concurrent writes,
unknown acknowledgment recovery, local signed events, duplicate and out-of-order
delivery, and injected read-only provider transport contracts. Boundary checks
refuse a runtime import of a transport or a parallel database engine.

`http_checks.self_test()` also runs `request_limit_checks.py`. Those checks
drive the limiter with an injected clock, and drive the real application with
a chosen socket peer address and over loopback sockets. They count
authentication calls and worker entries. The clock moves between the refused
requests of a waiting address, so a refusal that was counted would show as a
wait that stops falling.

Nine guards have a removed-guard control inside the suite. Each control
reruns a scenario with the guard patched away and requires the scenario's own
predicate to fail. The other guards have named checks but no such control
inside the suite.

| Guard | Removed-guard control |
|---|---|
| The refusal comes before authentication and before a worker slot | `removed_failed_attempt_limit_is_detected` |
| A request that is refused with status 429 is not counted | `removed_uncounted_refusal_rule_is_detected` |
| Counted failures leave the window | `removed_window_expiry_is_detected` |
| The table stays bounded | `removed_eviction_is_detected` |
| An address header that the host did not configure is never read | `removed_header_configuration_rule_is_detected` |
| An unstated address source leaves the limit inactive | `removed_unstated_source_rule_is_detected` |
| A body nested past the reader is a counted refusal, not an internal fault | `removed_nesting_limit_is_detected` |
| Provider reads have their own share of the worker pool | `removed_provider_share_is_detected` |
| A request that names two origins names none | `removed_single_origin_rule_is_detected` |

`a_caller_controlled_header_is_the_known_wrong_case` runs the forged header
scenario with a known-wrong configuration. One more check sends a failure
from outside the service that carries its own response headers, and requires
that none of them reaches the client. Only the service's own refusal type can
add a response header, such as `Retry-After`.

These checks do not establish how a hosted proxy treats a forged address
header. The hosted checks above are for that, and nobody has run them yet.

These checks do not establish a real Stripe account, live provider access,
remote authorization profile, customer charges, or deployment readiness.
Provider credentials, account ownership, prices, spending, and deployment need
separate owner authority and live qualification. A failed webhook write is
not proof that access changed; return a retryable failure and reconcile the
same event. The host still needs an operated retry worker, monitoring, backup,
restore, and periodic reconciliation for missed notifications.

## Search effect selection

Hosted metadata search accepts `service_retrieval_request/v2`. The optional
`authority_effects` field uses the provisioning list's array shape and the
canonical effect vocabulary. Omitted or empty selection considers material
with no declared effects. Unknown values, duplicate entries and malformed
arrays refuse before ranking, including when the query has no candidates.
The public capabilities name the exact request version, and the protocol
tool publishes the current input schema. Version 1 HTTP requests are refused.

Search forwards the selection to the existing authorized provisioning list
for candidate identities. Account state, metadata scope, exact grants, item
qualification and final snapshot checks remain authoritative. The selector
never changes grants, body access or local execution permissions. Search
reads no body, records no download usage and calls no model. Its index and
ranking algorithm are unchanged.
