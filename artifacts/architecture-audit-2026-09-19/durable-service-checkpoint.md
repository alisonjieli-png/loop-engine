# Durable service and billing domain checkpoint

Date: September 19, 2026. This checkpoint implements and tests persistent
service behavior locally. It is not a live Stripe, remote identity-provider,
payment, or deployment qualification.

## Outcome

Tenant and key lookup, external-subject bindings, revocation, exact item
grants, subscription projections, and usage persist through the existing
SQLite catalogue adapter. No parallel database engine or managed-note
shortcut was added.

Body serving revalidates the principal and durable grant revision before
materialization and metering. Exact retries use one durable usage record.
Unknown commit acknowledgment remains unknown until the same operation
identity is reconciled. The optional selected-body digest prevents a
manifest-to-read replacement from silently selecting different content.

The complete runtime classification and module boundaries are in the
[component guide](../../src/loop_engine/core/service_runtime/README.md).
These host services and records are mechanics consumed by canonical Loops,
not another executable runtime or persistent intelligence layer.

## Public integration contracts

| Boundary | Interface and invariant |
|---|---|
| Host configuration | `ServiceRuntimeConfig(database_path, namespace, writes_authorized=False)`. No database creation or write without explicit host authority. |
| Tenant and key setup | `register_tenant(TenantRegistration)`, `issue_key(TenantKeyIssue)`, `revoke_key`, and `set_tenant_enabled`. Tenant namespace reservation is atomic; only key digests persist. |
| External identity | `bind_subject(SubjectBindingRequest)`, `authenticate_subject(issuer, subject)`, and `revoke_subject`. The transport must verify the token first; the token never chooses its own tenant. |
| Current principal | `authenticate_key` and `revalidate` return an issued, integrity-bound `ServicePrincipal`. Forged or modified fields do not inherit authority. |
| Disclosure | `set_grants` persists exact `ProvisioningGrant` records. `DurableProvisioningBinding.invoke` and `invoke_for_principal` use current grants and qualification decisions. |
| Selected reference | Optional `expected_digest` is accepted only for manifest/read and checked before body loading or metering. |
| Usage | `record_usage` returns the existing exact `ProvisioningMeterAcknowledgment`; `usage_for` is authenticated and tenant-scoped. Caller request identities are hashed in stored usage metadata. |
| Billing authority | `billing_customer_for` requires explicit `billing:manage` and resolves the durable account/customer binding. This scope is absent from `DEFAULT_SCOPES`. |
| Billing policy | `configure_billing_policy(StripeEntitlementPolicy, expected_version=...)` is idempotent for the same policy and requires an exact revision for replacement. |
| Signed events | `StripeEventProcessor.handle(raw_body, signature_header)` returns `BillingEventResult`. `resume_event(event_id)` reconciles previously verified durable pending work. |
| Provider reads | `StripeSubscriptionReader(StripeProviderConfig, secret_resolver).as_resolver()` is read-only, fixed-origin, bounded, and network-denied by default. It cannot create a checkout or charge. |

The separately owned HTTP/Model Context Protocol adapter consumes these
interfaces. Checkout and portal creation are a separate scoped extension;
they do not replace subscription reconciliation or grant entitlement from
a redirect.

## Atomic storage contract

`CatalogRecordPrecondition`, `CatalogWriteBatch`, and
`CatalogBatchAcknowledgment` extend the existing catalogue protocol through
the optional `atomic_write_batch` operation. Its exact version is
`catalog_atomic_write_batch/v1`.

The SQLite adapter checks all absence and version predicates under one
`BEGIN IMMEDIATE` transaction and commits every write or rolls them all
back. Read-only guards bind current tenant, key, entitlement, billing policy,
and disclosure state to the write. Other adapters must declare and implement
the same semantics; unsupported or unknown negotiation refuses.

Existing per-record writes and imports retain their earlier behavior and
checks. The SQLite write-ahead-log qualification guard remains in place.
This is an embedded, serialized-writer profile. It is not evidence of
clustered throughput, multi-region consistency, or a hosted database adapter.

## Stripe verification and ordering

The processor verifies the exact raw body, version 1 HMAC signature, bounded
timestamp, configured account, test/live mode, and event API version before
state changes. It refuses duplicate JSON keys and conflicting contents under
an existing event identity. No signing secret, provider key, or raw webhook
body is saved in service records.

Stripe documents unordered delivery and warns that event creation timestamps
cannot determine order. The implementation therefore deduplicates by event
identity, durably invalidates access, and fetches current subscription state.
A pre-fetch catalogue revision guard rejects a delayed response after a
concurrent decision. [Stripe webhook guidance](https://docs.stripe.com/webhooks#event-ordering)

The subscription projection requires an owner-configured Price, a valid
period, and an active subscription with a paid latest invoice. Trial access
requires an explicit policy. Unknown, incomplete, unpaid, paused, canceled,
expired, or unconfigured states do not grant body access.
[Stripe subscription event guidance](https://docs.stripe.com/billing/subscriptions/webhooks)

The production read adapter verifies the account and lists current customer
subscriptions with bounded pagination and complete item lists. It refuses
redirects before following them. Its declared page size stays within the
published range. [Stripe subscription-list API](https://docs.stripe.com/api/subscriptions/list)

## Verification

The saved [results](durable-service-verification-results.json) pass
153 checks: 68 owning checks and 85 dependent checks. No check is marked
untested. They include real SQLite reopen, cross-tenant isolation, key and
subject revocation, expiry, issued-principal integrity, read-only metadata
readiness, selected-digest refusal, atomic rollback and competing writers,
durable usage, unknown acknowledgment recovery, signed-event refusal,
duplicate and same-second delivery, out-of-order reconciliation,
administrative revocation, and a stale concurrent provider response.

All 11 known-wrong implementations were detected. They remove atomic read-set
checks, rollback, key revocation, principal validation, usage idempotency,
commit acknowledgment checks, signature verification, timestamp bounds,
invoice-paid evidence, provider snapshot identity, or network authority.

Run the [saved runner](durable-service-verification.py):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src HF_HUB_OFFLINE=1 .venv/bin/python artifacts/architecture-audit-2026-09-19/durable-service-verification.py
```

The results retain the initial policy serialization defect and the mutant
runner correction. Neither was hidden by weakening a check. The component
README passes Markdown lint, and the scoped source difference check passes.

The collected public test entrypoints are:

- `loop_engine.core.service_runtime.runtime.self_test()`: 25 checks;
- `loop_engine.core.service_runtime.billing.self_test()`: 38 checks;
- `loop_engine.core.service_runtime.stripe_provider.self_test()`: 5 checks.

Each returns a versioned report containing `tests`, `passed`, `total`,
and `all_passed`. The root agent owns architecture registration and full-tree
source, conformance, package, and release verification.

## Remaining qualifications

No Stripe account call, real checkout, charge, live identity-provider call,
or deployment was performed. Prices and credentials remain owner-supplied.
The injected provider transport and local HMAC fixtures prove local contracts,
not live provider integration.

Host-attested catalogue review remains distinct from independent qualification.
Authoritative resolvers across every intelligence layer remain separate
integration work. HTTP and Model Context Protocol acceptance is recorded by
the transport owner rather than counted in this domain report.

An operated service still needs its retry worker, monitoring, backup/restore,
periodic reconciliation for missed notifications, and an authorized live
provider exercise. A failed or unknown webhook write does not prove that
access changed. Return a retryable failure and reconcile the same identity.
Unknown metering response or failed body delivery does not prove no usage
was committed. No automatic refund or exactly-once network delivery is claimed.
