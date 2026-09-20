# Service identity, endpoint selection and domain changes

Kind: proposed extension at the existing service transport, provider registry,
artifact delivery and host configuration boundaries. This is not evidence of
implemented regional failover. The current pilot has one Fly Machine and one
authoritative SQLite store.

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

The services and adapters below are passive runtime mechanics, not additional
executable vertices. A classified Loop owns the operation that uses them.

## Initial choice

Keep stable hostnames in client configuration. Let the hosting provider route
requests to healthy machines behind those hostnames. Changing a Machine or its
address must not require a customer to edit a harness configuration.

```text
Configured service connection
├── Identity and trust
│   ├── service identity independent of brand and placement
│   ├── approved authorization issuer and resource audience
│   └── trusted discovery origin and optional manifest signing keys
├── Eligible endpoint set
│   ├── website and account access
│   ├── intelligence search and Model Context Protocol
│   └── selected artifact delivery
└── Request policy
    ├── supported contracts and required capabilities
    ├── allowed regions, privacy scope and deadline
    ├── selection, retry and failover rules
    └── exact request identity and uncertain-outcome reconciliation
```

These can share one deployment initially. Separate names are not a reason to
create separate Machines or databases. Keep browser requests same-origin where
possible. Reserve a future service hostname only when it removes a verified
migration or client-compatibility problem.

The pilot answers on `baltor.ai`, `www.baltor.ai`, `app.baltor.ai` and
`baltor-pilot.fly.dev`. Each hostname has its domain records and a valid
certificate, and each origin serves `/mcp`. The
[current deployment](MVP-CLIENT-SERVER.md#current-deployment) section records
these facts once.

The remaining work is the identity migration, not the certificate. The host
configuration still names the Fly hostname as the canonical protocol resource
and account origin. Do not move that canonical origin, a callback address or a
token audience to `app.baltor.ai` before the
[domain migration procedure](#domain-migration-procedure) has been run and
checked. An earlier version of this paragraph said that `app.baltor.ai` still
needed its domain records and certificate. It was corrected on September 20,
2026, after the records and the valid certificate were observed.

## What changes and what remains stable

| Change | Handling |
|---|---|
| Machine or IP address | Keep the hostname. Change the provider route or domain record, retain valid certificates and respect resolver caching. |
| Search or storage provider | Change the adapter behind the logical service. Preserve reference identity and contracts; rebuild derived indexes if needed. |
| Region | Select only an authorized region with a compatible healthy endpoint and access to the correct durable state. |
| Brand or domain | Run an explicit migration with old and new origins, certificates, callbacks and resource audiences. Keep the old domain controlled during the transition. |
| Artifact delivery host | Resolve the immutable artifact identity again and obtain a new authorized delivery grant. Verify the same digest after delivery. |
| Endpoint unavailable | Use a declared eligible fallback within the remaining deadline. Refuse if no trusted compatible route exists. |

Do not use arbitrary IP addresses as a generic fallback. Certificate hostname
validation and the intended service identity still apply. An emergency fixed
address would need a separately configured route that preserves the expected
hostname, certificate validation and network authority. It is off by default.

## Runtime handshake

Negotiate before sending task content or invoking an operation. A proposed
endpoint descriptor names its service identity, endpoint identity, origin,
region, supported protocol and contract versions, capabilities, authorization
resource, size limits, operation types and retirement state.

The client intersects those declarations with its installed implementations
and required capabilities. It selects the highest mutually qualified contract,
not merely the largest version number. Missing security requirements refuse;
optional search features may be omitted only when the request permits it.
Embedding compatibility still requires the exact model, preprocessing and
space identity. Equal vector dimensions do not establish compatibility.

Runtime negotiation chooses among tested adapters. It does not generate new
protocol conversions or waive security because another endpoint is reachable.
Continuous integration still tests old/new combinations and refusal cases.

For Model Context Protocol, use its standard protected-resource metadata and
authorization discovery. Its access tokens are bound to an intended resource.
A renamed hostname or different resource may require a new authorization;
a stable internal service identifier does not remove audience validation.
[Authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)

Discovery must start from an operator-trusted origin. A proposed downloadable
endpoint manifest should have a bounded expiry, monotonic generation, trusted
signer and tested key rotation. Never learn a new credential destination from
a retrieved document or an unrestricted redirect. Retain only explicitly
allowed last-known-good settings; expired authority cannot be extended locally.

## Multiple endpoints and round-robin routing

For the initial single-origin deployment, prefer provider routing over client
round robin. Fly can route requests within an application and supports explicit
request replay for more specialized routing. That does not make the database
shared or make application mutations safe to repeat.
[Fly request routing](https://fly.io/docs/networking/dynamic-request-routing/)

If multiple origins become necessary, choose among endpoints only after
permission, region, protocol, readiness and consistency checks. Weighted
selection, tenant affinity and circuit breakers are replaceable policies.
Use bounded backoff and jitter. One failed call must not fan out to every
region and multiply cost. Hedged requests remain disabled unless duplicate
execution and cost are explicitly allowed for that operation.

| Operation | Initial fallback rule |
|---|---|
| Public capabilities or metadata search | Bounded retry to an approved compatible endpoint. Reapply tenant filters. |
| Download | Reauthorize the exact artifact and retain its digest and usage request identity. Do not forward a service token to a storage host. |
| Token issue, checkout or other mutation | Reconcile the original operation identity before creating another effect. An unknown result is not a failure that can be safely repeated with a new identity. |
| Streaming or continuous work | Resume from a declared durable cursor only if the selected adapter supports that contract. Otherwise report interrupted work. |

All mutation-serving replicas must share authoritative permission, revocation
and idempotency state with the required consistency guarantees. Copying the
current SQLite volume to another Fly Machine would produce divergent state.
The shared-store adapter and its adversarial checks come before horizontal
scaling. A Model Context Protocol handshake is not a shared-storage protocol.

## Domain migration procedure

1. Inventory existing domain records, website forwarding, email routing,
   certificates, cookies, origin rules, authorization callbacks and webhooks.
2. Establish the new hostname and certificate without disabling the old one.
   Validate the new endpoint with no credentials first.
3. Configure exact host and browser-origin allowances. Register exact callback
   and webhook addresses. Keep secrets out of redirect URLs and access logs.
4. Authorize the new resource where required. Publish the signed migration
   configuration through the existing trusted connection and client updates.
5. Compare a small qualified client population, including old clients. Record
   which origin, route generation, contract and request identity each used.
6. Move traffic gradually. Keep a rollback route and monitor authentication,
   webhook duplicates, downloads, latency and unresolved mutations.
7. Retire the old endpoint only after the supported migration window. Continue
   controlling the old domain so a new owner cannot capture stale clients.

Switching domain-name providers is separate from changing the domain name.
For Cloudflare, review the full record inventory before changing nameservers.
If existing domain-name security is enabled, follow the documented migration
sequence rather than leaving a stale registrar trust record in place.
[Cloudflare setup](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/)

## Tests required before enabling failover

Use two real local endpoints and one shared test authority. Exercise a changed
address, old client, incompatible contract, stale manifest, forged signer,
expired certificate, wrong audience, revoked token, forbidden region,
redirect to an unrelated host, partial download, changed artifact digest,
replica disagreement and crash after commit but before response.

Each test must distinguish a successful fallback from duplicate work or a
security downgrade. Include a control with the required guard removed.
No such regional or domain-migration campaign has qualified this pilot yet.

## Current implementation boundary

The current transport already has configured origins and hosts, strict token
audiences for external identity, a declared Model Context Protocol version,
capability reporting, digest-bound delivery and durable request identities.
The website uses same-origin requests and refuses redirects. The administrator
token workflow records duplicate requests without minting another token.

Trusted multi-origin discovery, manifest signing, automatic regional failover,
shared PostgreSQL state and domain-migration qualification remain work items.
Do not mark them implemented from this design document.
