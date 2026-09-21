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
window, the cycle count and the outcome. `authorize_billing_customer_dispatch`
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
One customer for each account
├── The durable effect record: one for each account, reused by every attempt
├── The lease: a second caller during a running creation is refused
├── The search before creation: a customer left behind by an uncertain
│   attempt is bound instead of duplicated
└── The atomic binding: the existing catalogue guard refuses a second writer
```

Within the reconciliation window a retry reuses the stored provider
idempotency key. After that window the key can no longer reconcile anything,
so a new cycle takes a new key and the search before creation is what keeps
the account at one customer. A removed-guard control proves that step.

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

Signing out of the website clears private controls immediately. Client tokens
remain separate credentials until revoked, expired or disabled through their
local subject or tenant binding. Synchronizing a provider-side account deletion
with that local binding is still integration work. A provider outage returns
service unavailability instead of pretending that the user's password failed.

Real-provider qualification uses disposable, administratively confirmed test
identities. It does not prove confirmation email delivery, password recovery,
public registration, subscription processing or useful native task execution.

`set_operator_entitlement` is an explicit local host grant with an evidence
reference and expiry. It is not evidence of payment. Billing projections do
not override an administrative access revocation.

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

This subsection describes operator work that is not done yet. Merging or
deploying this code does not switch the limit on. The host file of the hosted
service has no `request_limits` mapping. After a deployment the hosted service
therefore still accepts unlimited refused sign-in attempts that carry a
credential, and each one still uses a worker slot. One change needs no
operator work: a request without exactly one credential no longer uses a
worker slot.

Do these steps in order, after the release that contains this limit runs:

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
  check shows this bound.
- A caller who controls more addresses than `maximum_tracked_addresses` can
  make the table forget the oldest address early. Such a caller already has
  that many separate allowances. The worker slots remain the ceiling for all
  callers together.
- People who share one address share one count. While one of them keeps
  failing, the others wait too.
- Only sign-in and account activation are limited. The billing webhook, the
  public pages, the capabilities record and the identity configuration are
  anonymous routes without such a limit.
- A governed operation can run its work twice for one refused request, because
  its Loop runs up to two steps. The limit counts one refused attempt for that
  request.

## Persistence and concurrency contract

The optional `catalog_atomic_write_batch/v1` contract checks all expected
record versions and absence conditions under one SQLite `BEGIN IMMEDIATE`
transaction, then commits every write or rolls back all of them. Read-only
guards can bind authentication and disclosure state to a usage append without
rewriting those records. Another store can implement the same declared
capability. Unsupported or unknown capability negotiation refuses; domain
code does not branch on a backend class.

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
    └── Reported dependencies are named and do not remove the machine
```

Recording is governed by `service_observability_policy/v1`. The default records
metadata and no request body; `metadata_and_request_body` is an explicit host
choice, and asking to record a body without it is refused with
`payload_capture_not_authorized`. A credential, an authorization header and any
other header that carries authority are never recorded under any setting.

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

Six guards have a removed-guard control inside the suite. Each control reruns
a scenario with the guard patched away and requires the scenario's own
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
