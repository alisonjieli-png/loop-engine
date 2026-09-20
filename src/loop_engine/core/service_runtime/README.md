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

These checks do not establish a real Stripe account, live provider access,
remote authorization profile, customer charges, or deployment readiness.
Provider credentials, account ownership, prices, spending, and deployment need
separate owner authority and live qualification. A failed webhook write is
not proof that access changed; return a retryable failure and reconcile the
same event. The host still needs an operated retry worker, monitoring, backup,
restore, and periodic reconciliation for missed notifications.
