# The subscription journey

Kind: component guide for the hosted service. It describes what happens from
the moment a person presses subscribe to the moment their account is allowed
to download item bodies. It separates what the source does today from what is
still planned, and it names the evidence for each claim.

The owning code is `src/loop_engine/core/service_runtime`. The parts are
`stripe_sessions.py` for checkout, portal and customer creation, `runtime.py`
for the durable account records, `billing.py` for the provider event, and
`http.py` for the public routes.

## The whole path

```text
Subscription journey
├── 1. The person signs in and the browser holds a session
├── 2. The browser reads the plans record
│   └── GET /api/v1/billing/plans returns billing_session_options/v1
├── 3. The person presses a plan button
│   └── POST /api/v1/billing/checkout with one request identity
├── 4. The service resolves the account's payment customer
│   ├── a customer is already bound: use it
│   └── no customer is bound: create exactly one and bind it
│       ├── reserve the one creation this account may ever need
│       ├── read the provider account and refuse another account
│       ├── search the provider for this account identifier
│       ├── create the customer only when the search found none
│       └── bind the customer to the account in one atomic write
├── 5. The service creates the checkout session for that customer
│   └── the browser opens the provider redirect address
├── 6. The person pays at the provider
├── 7. The provider sends a subscription event to the service
│   └── POST /api/v1/billing/webhook with a signature header
├── 8. The service removes paid access, then reads current provider state
└── 9. The entitlement record allows bodies until the paid period ends
```

Steps one to five and steps seven to nine are separate. Creating a checkout
session never confirms a payment and never changes an entitlement. The result
record says so in its own fields, `payment_confirmed` and
`entitlement_changed`, and both are always false.

## Exactly one payment customer for each account

An account gets one payment customer, once, for its whole lifetime. Four
separate mechanisms keep it at one. Each one covers a case that the others
cannot.

```text
One customer for each account
├── The durable effect record
│   ├── One record for each account, identified by the account itself
│   ├── It holds the provider idempotency key, the attempt identity,
│   │   the lease, the reconciliation window and the outcome
│   └── A restart, a retry and a later repeat all reuse that one record
├── The lease
│   └── A second caller during a running creation is refused with
│       billing_customer_creation_in_progress and reaches no provider call
├── The search before creation
│   ├── The service asks the provider for a customer whose metadata names
│   │   this account, and binds that one instead of creating another
│   └── This is what covers a repeat after the stored idempotency key can
│       no longer reconcile the earlier attempt
└── The atomic binding
    ├── The account record and the absent customer record commit together
    └── A second writer is refused with billing_customer_already_bound
```

### Why the search is needed as well as the idempotency key

Within the reconciliation window, a retry sends the same provider idempotency
key, so a creation whose answer was lost is reconciled rather than repeated.
`billing_effects.py` records the observed provider fact that the key is kept
for at least twenty four hours, and the session configuration keeps the
reconciliation window strictly inside that period, with one hour of margin.

After that window the stored key can no longer reconcile anything. The account
still needs a customer, and the account identity is the only request identity
it has, so a new cycle takes a new key and counts the cycle in the record. The
search before creation is then the only thing that keeps the account at one
customer. A removed-guard control proves it: with the search step patched
away, the repeat after the window creates a second customer and the named
check fails.

### What the customer carries

The created customer carries one metadata field and nothing else.

| Field | Value | Why |
|---|---|---|
| `metadata[loop_engine_tenant_id]` | the account identifier | An operator reading the provider dashboard can tell which account a customer belongs to, and the search before creation finds the customer again. |

The service holds no name, no postal address and no email address for an
account, so it sends none and invents none. The wire contract enforces this
rather than leaving it to the caller: every supported provider mutation
declares the exact parameter names it may carry, and the customer form may
carry only that one metadata field. A form that carries `email` is refused
with `unsupported_session_wire_parameters` before any provider call.

## What an operator can see at the provider

This section describes what the source sends. Nobody has read the live
provider dashboard as part of this work, so treat the dashboard column as
expected rather than observed.

| At the provider | What the source sends | State |
|---|---|---|
| The customer list | One customer for each subscribing account, with `metadata.loop_engine_tenant_id` set to the account identifier | Observed in the source and in the injected-transport checks. Not observed at the provider. |
| The customer creation request | An `Idempotency-Key` header holding the durable key of the account's one creation effect | Observed in the source and in the wire checks. Not observed at the provider. |
| Checkout sessions | One session for each request identity, bound to that customer and to an owner-chosen Price | Observed in the source and in the injected-transport checks. Not observed at the provider. |
| Subscriptions and invoices | Created by the provider when the person pays | Not exercised by this work. |

To find the account behind a provider customer, read its
`loop_engine_tenant_id` metadata field. To find the provider customer behind
an account, read the account's billing customer binding through
`billing_customer_for`.

## Proven and not proven

Observed facts come from checks that ran on this branch. Every check uses an
injected transport and a real temporary catalogue file. No provider call was
made, no account was created and no money moved.

| Behaviour | Evidence | State |
|---|---|---|
| A first checkout on an account that never paid creates one customer, binds it and creates the session for it | `an_account_that_never_paid_is_offered_checkout_and_gets_one_customer_and_one_session` | Observed |
| A second checkout reuses the bound customer and creates nothing | `a_second_checkout_reuses_the_bound_customer_and_creates_nothing_at_the_provider` | Observed |
| Two requests at the same moment end with one customer and one binding | `two_concurrent_first_requests_end_with_exactly_one_customer_and_one_binding` | Observed |
| An uncertain creation is reported as uncertain and is not retried by the service | `an_uncertain_creation_is_reported_as_uncertain_and_is_not_retried_by_the_service` | Observed |
| The retry after an uncertain creation finds the customer by its metadata and binds that one | `the_retry_finds_the_customer_left_behind_by_its_metadata_and_binds_that_one` | Observed |
| A repeat after the reconciliation window finds the existing customer instead of creating another | `a_repeat_after_the_idempotency_window_finds_the_existing_customer_instead_of_creating_another` | Observed |
| A creation refused by the provider leaves no binding and reports the refusal | `a_creation_refused_by_the_provider_leaves_no_binding_and_reports_the_refusal` | Observed |
| An account bound to another provider account is refused and gets no second customer | `an_account_bound_to_another_provider_account_is_refused_and_gets_no_second_customer` | Observed |
| A caller without the billing scope reaches no provider call | `a_caller_without_the_billing_scope_creates_no_customer_and_reaches_no_provider_call` | Observed |
| A disabled account, or a configuration without network or session authority, creates no customer | `a_disabled_account_or_absent_network_authority_creates_no_customer` | Observed |
| A provider customer that names another account is never bound | `a_provider_customer_that_names_another_account_is_never_bound` | Observed |
| More than one customer for one account is refused instead of choosing one | `more_than_one_customer_for_one_account_is_refused_instead_of_choosing_one` | Observed |
| The customer carries no personal detail | `a_created_customer_carries_only_the_account_identifier_and_no_personal_detail` | Observed |
| The same behaviour against the real provider | none | Not proven. No provider call was made. |
| A person completing a payment and receiving an entitlement | none | Not proven end to end. The event path has its own checks in `billing_checks.py`, and nobody has run the whole journey against a real account. |
| The browser journey from the sign-in page to the provider page | none | Not proven. `web_assets/service.js` already reads the plans record and posts the checkout request, and the route checks drive the real HTTP path, but no browser run of the whole journey was recorded here. |

### Removed-guard controls

Each control reruns a named scenario with one guard patched away and requires
the scenario's own predicate to fail.

| Guard | Control |
|---|---|
| The search before creation | `removed_customer_search_before_creation_is_detected` |
| The account identifier in the customer metadata | `removed_account_identifier_in_customer_metadata_is_detected` |
| The ownership check on a provider customer | `removed_customer_ownership_check_is_detected` |
| The provider account check before creation | `removed_provider_account_check_before_creation_is_detected` |

The lease has a named check and no removed-guard control inside the suite.
Removing it does not produce a second customer, because the reserved attempt
identity and the search before creation each stop the duplicate on their own.
That is a finding about the design, not a reason to remove the lease: the
lease is what keeps a second caller away from the provider entirely.

## Current behaviour

- The account needs the `billing:manage` scope. It is deliberately absent from
  the default scopes.
- Checkout is offered to an account with no payment customer, because checkout
  creates one. The portal is not offered until a customer is bound, because
  the portal needs an existing customer and never creates one.
- The host configuration decides whether the service may reach the network at
  all. `allow_network` and `allow_session_creation` both default to false, and
  both are required before a secret is resolved or a provider call is made.
- The host may still bind a customer by hand through the `billing_customer`
  mapping of a tenant in the host configuration file. That mapping is now
  optional. An account without it gets its customer on its first checkout.
- An uncertain outcome is reported with status 503, the record type
  `billing_customer_uncertainty/v1`, `creation_attempted`,
  `provider_commitment: not_asserted` and `retry_same_request`. The service
  never retries it by itself and never retries it under another identity.
- The durable records hold identifiers, statuses and the idempotency key. They
  hold no credential and no provider redirect address.

## Planned behaviour

These are not implemented. They are recorded here so that nobody reads the
current behaviour as covering them.

- No operated worker reconciles an account that is left with an unknown
  creation outcome and never returns. Today the next checkout attempt by that
  person reconciles it.
- The service does not read or remove a provider customer that an operator
  created by hand outside this path, unless its metadata names the account.
- Nothing cancels a subscription from inside the service. The provider portal
  is the only route, and it needs a bound customer.
- The live pilot recorded on September 20, 2026 has checkout and the billing
  webhook switched off. Switching them on is host configuration work and a
  release, and it is not done by merging this code.

## Refusals and what they mean

| Code | Meaning | Status |
|---|---|---|
| `scope_required` | The caller has no `billing:manage` scope. Nothing reached the provider. | 403 |
| `session_network_authority_required` | The host configuration does not allow network access or session creation. | 503 |
| `billing_customer_creation_in_progress` | Another request is creating this account's customer. Send the same request again. | 503 |
| `billing_customer_not_created` | The creation was never dispatched. The reason is in `diagnostic_code`. | 503 |
| `billing_customer_uncertain` | The creation was dispatched and its outcome is unknown. Send the same request again; it reconciles. | 503 |
| `stripe_account_or_customer_mismatch` | The account is bound to a different provider account than the one configured. An operator must resolve it. | 400 |
| `billing_customer_already_bound` | The account already has a customer. Read the binding instead of creating one. | 400 |

## Checks to run

```bash
PYTHONPATH=src .venv/bin/python -c "from loop_engine.core.service_runtime import stripe_sessions; print(stripe_sessions.self_test())"
PYTHONPATH=src .venv/bin/python -c "from loop_engine.core.service_runtime import runtime; print(runtime.self_test())"
PYTHONPATH=src .venv/bin/python -m loop_engine service smoke
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
```
