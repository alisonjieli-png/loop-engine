# Executable HTTP service checkpoint

Date: 2026-09-19. This is focused local acceptance, not public deployment or
live identity-provider/payment-provider qualification.

The service now runs on real HTTP sockets with the installed official Model
Context Protocol client and Streamable HTTP transport. It delegates tenant,
qualification, disclosure, entitlement, and usage decisions to the durable
Python service. Domain operations run through the canonical Loop. Retrieval
uses the registered Intelligence search profile and returns exact body-free
`provisioning_item_binding/v1` references.

The supported protocol is exactly `2025-11-25` with `mcp==1.29.1`.
Unsupported protocol versions refuse. The adapter does not claim current
2026 interoperability. The official maintenance-line documentation describes
the supported web transport and resource-server authorization mechanisms.
[Official version 1 documentation](https://py.sdk.modelcontextprotocol.io/v1/),
[Server transport documentation](https://py.sdk.modelcontextprotocol.io/v1/server/),
[Authorization documentation](https://py.sdk.modelcontextprotocol.io/v1/authorization/).

## Implemented routes

| Route | Boundary |
|---|---|
| `GET /api/v1/health` | Limited liveness; readiness and deployment qualification are not asserted. |
| `GET /api/v1/capabilities` | Versioned protocol, authentication, retrieval, delivery, and resource-limit declarations. |
| `GET /api/v1/session` | Current durable identity and effective token/key scopes. |
| `POST /api/v1/provisioning` | Existing discover, list, manifest, and read operations. |
| `POST /api/v1/retrieval` | Authorized metadata ranking only; hash vectors are explicitly not learned semantic embeddings. |
| `POST /api/v1/download` | Reauthorized exact UTF-8 artifact bytes outside the normal response allowance. |
| `GET /api/v1/usage` | Current durable tenant usage. |
| `POST /api/v1/billing/webhook` | Signed events through the installed billing processor; pending and unknown state produce retryable failure. |
| `/mcp` | Actual stateless Streamable HTTP for four provisioning tools and `intelligence_search`. |
| `GET /.well-known/oauth-protected-resource` and `/mcp` suffix | Resource metadata for configured external-token mode, not an authorization server. |

Normal web responses use `service_http_result/v1`. Refusals use
`service_http_error/v1`. Request bodies cannot choose a tenant, inject a key,
install a resolver, or change effect authority. Optional `expected_digest`
binds a selected manifest or body before loading and metering.

Host keys are resolved from durable records. External tokens use a configured
issuer, fixed key endpoint, exact audience, asymmetric algorithm allowlist,
expiry, and scopes. The audience must match the advertised service resource.
The runtime maps issuer and subject to a tenant. Token tenant claims are not
authority. Effective scopes are the intersection of token and durable scopes.
Key endpoint redirects and oversized responses refuse. Both new-key and
same-identifier rotation were exercised using locally signed tokens.

Host and Origin values are explicit. Body and response limits are checked.
Large bodies require the separate download operation. A timed-out or cancelled
wait does not imply physical callback cancellation or rollback. Running work
retains its capacity slot until completion; there is no automatic replay.
Caller retries reuse the same durable usage identity.

## Executable setup

`python -m loop_engine.core.service_runtime.http_entrypoint` supports `configure`,
`issue-key`, `serve`, and `smoke`. Host configuration uses
`service_http_host_configuration/v1` and an exact
`host_attested_intelligence_manifest/v1`. Serving does not recreate tenants
or restore revoked grants. Configuration and key issuance are separate host
commands. The key command displays the newly issued credential once; the
database stores its digest. Do not capture that command in public logs.

The body manifest binds source identities, content digests, confined paths,
and explicit host-review references. Host attestation is not independent Code
Intelligence admission. The current delivery body format is UTF-8 text, not a
claim that arbitrary binary packages are served or executed.

## Evidence

The executable `smoke` command and owning checks pass 39/39. The tests use
temporary SQLite state, real loopback listeners, official client streams,
local key-set HTTP servers, locally signed tokens, and signed billing-event
fixtures. Seventeen restored in-memory mutants were detected by named failing
checks. These include removed issuer/audience/expiry checks, broadened token
scopes, redirected key retrieval, false semantic-vector claims, omitted body
preconditions, premature capacity release, and false billing acknowledgment.

An initial mutation-runner attempt incorrectly reused existing fixture roots
and double-wrapped a property. Those results were not accepted as protection
evidence. The corrected runner first passes every isolated fixture and then
detects all seventeen mutants through actual assertions. An unknown-commit
fixture also needed to patch the frozen catalogue class instead of assigning
an instance attribute. The collector and security checks were not weakened.

[http-service-verification.py](http-service-verification.py) is the reproducer.
[http-service-checkpoint.json](http-service-checkpoint.json) records exact
source hashes, installed package versions, counts, and limits. Full frozen-tree
integration, production hosting, real external authorization, and real payment
acceptance remain separate work. Checkout and portal creation were not installed
at this checkpoint; they are the next explicitly authorized slice.
