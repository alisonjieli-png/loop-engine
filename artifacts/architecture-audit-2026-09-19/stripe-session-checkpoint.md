# Checkout and portal session checkpoint

Observed on September 19, 2026. The bounded implementation passes 52 of 52
checks, and all 18 restored in-memory mutants fail named assertions. The
[machine-readable result](stripe-session-checkpoint.json) binds those results
to exact source digests. The [runner](stripe-session-verification.py) uses
temporary catalogue records, real loopback HTTP, locally signed identity
tokens, and explicitly injected Stripe-shaped responses. It made no remote
Stripe call and created no remote account, customer, session, subscription,
invoice, or charge.

## Implemented boundary

The server owns the exact Stripe account, durable tenant/customer mapping,
Price identity, quantity, portal configuration, and return URLs. A client
selects only a public plan reference, current policy digest, and request
identity. The required `billing:manage` scope is absent from default tenant
and key scopes. Verified external-token scopes can narrow durable subject
authority, not borrow its broader permissions.

| Boundary | Current owner |
|---|---|
| Immutable session configuration, request, fixed-origin provider transport | `core/service_runtime/stripe_sessions.py` |
| Policy installation, exact request reservation, atomic read-set guards, outcome retention | `core/service_runtime/billing_effects.py` |
| Existing tenants, keys, subjects, customer mappings, financial policy | `core/service_runtime/runtime.py` |
| Existing catalogue and transaction contract | `core/service_runtime/storage.py` |
| Authenticated routes and bounded response waiting | `core/service_runtime/http.py` |
| Host manifest and explicit setup commands | `core/service_runtime/http_entrypoint.py` |
| Direct state-machine checks | `core/service_runtime/stripe_session_checks.py` |
| Provider response, serializer, identity, actual HTTP, timeout and setup checks | `core/service_runtime/stripe_session_transport_checks.py` |

The public routes are `GET /api/v1/billing/plans`,
`POST /api/v1/billing/checkout`, and `POST /api/v1/billing/portal`.
`GET /api/v1/capabilities` reports the installed availability. Each request
uses the existing canonical Loop wrapper and current versioned HTTP envelope.
No session-creation tool is added to Model Context Protocol. Domain policy
remains in Python; these adapters do not create another executable runtime.

The host configuration accepts optional `billing.sessions` settings and exact
`tenants[].billing_customer` mappings. Serving never creates or restores them.
The separate `configure` command installs host-authorized state. Network and
session-creation flags default to false. No new dependency was required beyond
the previously reported serving dependency set.

## Effect semantics

An atomic catalogue reservation binds tenant, request identity, operation,
account, customer, policy digest, and exact serialized parameter digest.
Concurrent attempts share a lease and a single stored random provider
idempotency key. Authentication, customer, financial policy, session policy,
and their record revisions are checked again before dispatch. Reservations
are internally issued and integrity-bound; a caller cannot strip their
authority guards.

Changed parameters cannot reuse a request identity. A lost provider response
or uncertain local acknowledgment is not success. There is no automatic
creation retry. An explicit same-request retry reuses the stored key, including
after restart, inside its original bounded reconciliation window. Exhaustion
refuses; it never silently generates another key. Stripe documents that keys
can be removed once they are at least 24 hours old, so the adapter caps its
window at 23 hours and defaults to one hour. This is an application safety
margin, not an invented provider limit.
[Stripe idempotency contract](https://docs.stripe.com/api/idempotent_requests)

Response waiting can expire while a synchronous callback is still running.
The HTTP response then refuses success, retains occupied capacity until the
callback finishes, and does not claim physical cancellation or replay it.
Post-dispatch authority loss also refuses success while retaining the observed
effect. A later authorized same-request attempt can reconcile it.

Provider responses must match customer, test/live mode, object kind and
approved redirect host. Checkout also checks exact return URLs, subscription
mode, open status, and expiry. Portal checks exact configuration and return
URL. Credentials and ephemeral redirect URLs are not written to effect records.
The records retain identifiers, status and response digests. Session creation
does not grant entitlement or confirm payment; current verified subscription
state remains the separate authority.
[Checkout session contract](https://docs.stripe.com/api/checkout/sessions/create),
[Portal session contract](https://docs.stripe.com/api/customer_portal/sessions/create)

## Verification and retained limitations

The current dependent checks also pass: HTTP 39/39, durable runtime 25/25,
signed billing and reconciliation 38/38, and read-only Stripe adapter 5/5.
At this checkpoint, the conformance collector passed 4/5 and correctly flagged
two new network-owner registrations still owned by the integration agent:
`stripe_sessions.py` and `stripe_session_transport_checks.py`. No scanner rule
or baseline was weakened. The subsequent full hardcoding audit found zero new
blocking service-runtime findings and no allowlist problems; three unrelated
architecture-report findings were reported to their owner.

Two initial mutant attempts interrupted fixtures through domain and HTTP
exceptions. Those attempts were not retained as named-check evidence. The
checks now capture those unexpected outcomes as explicit failed assertions,
and the final runner refuses to count fixture interruption as detection.
A provisional fragment rejection was also wrong: Stripe's official example
contains a fragment in its Checkout URL. The supported positive fixture and
implementation preserve it while still checking the destination authority.

This is not live Stripe interoperability, a deployed identity-provider flow,
cloud deployment, or full-system benchmark evidence. A configured external
issuer still needs its real authorization flow qualified. Exact Stripe API
version, account permissions, Price configuration, portal behavior, signed
webhook delivery, and subscription-state reconciliation still need authorized
live qualification. The service uses the existing serialized SQLite profile,
not a claim of clustered or multi-region consistency. No source changes,
commits, deployments, or remote effects are implied beyond the named slice.
