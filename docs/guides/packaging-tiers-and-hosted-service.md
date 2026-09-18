# Packaging tiers and the hosted service

This guide records how Loop Engine is packaged and how a hosted service
would be sold. It follows the
[competitive landscape and monetization record](../research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md),
which verified the pricing of nineteen adjacent companies on 2026-09-18,
and the fabric roadmap steps S-4.1 to S-4.6. Prices are not set here; the
owner sets them. What is fixed here is the shape: what is free, what is
metered, what is never metered, and what runs where.

## Two things a customer can buy

```text
Hosted intelligence
├── the packaged Context and Code Intelligence, kept current and searchable
├── judgment services: independent verification and the failed-check review
├── the specialist catalog: small trained models behind typed contracts
└── external intelligence access with authentication (the paid tier of R-10)

Hosted compute
├── solutioning runs: Practitioner Loops on the service's workers
├── solution execution: exported solutions run as Jobs on the service's cluster
├── evaluation and optimization runs over the customer's frozen suites
└── storage for run history, evidence, and shared memory scopes
```

A customer may take either without the other. A self-hosted customer runs
the compute on their own cluster and can still subscribe to hosted
intelligence; a hosted-compute customer can bring their own intelligence
stores through the same catalog contract.

## Tiers

| Tier | What it includes | Where it runs | Line |
|---|---|---|---|
| Open core | The engine, the runtime, the catalog contract and local adapters, text conformance and the detection and correction family, export to packages and containers, evaluation and optimization commands, examples | The customer's machine | Free, MIT |
| Self-hosted | Open core plus the worker image, Kubernetes manifests, the service software with tenants, keys, and metering, and the operations documents | The customer's cluster | Paid support and governance features |
| Hosted | Self-hosted features operated by the vendor: intelligence kept current, judgment services, specialist catalog, external intelligence access, evaluation and optimization runs, storage | The vendor's cluster | Metered |

Governance features (approval workflows for candidate promotion, audit
exports, tenant-wide policy records, retention controls) sit behind the
paid line in both paid tiers. The engine itself never does.

## Units that are metered

| Unit | What it counts | Why it fits |
|---|---|---|
| Verified completion | A task whose independent verification report passed | The customer pays for a result a separate process confirmed, not for attempts |
| Avoided model call | A step served by exact reuse, a deterministic resolver, or a specialist instead of a service model, recorded by the implementation decision | The engine's economic claim is fewer model calls for the same verified outcome; the meter measures that claim |
| Optimize hour | Wall-clock time of evaluation and optimization runs on the service's workers | Compute that the customer chose to spend on search |
| Judgment depth | The number of independent judgment calls (verification, failed-check review, escalation answers) in a run | Assurance is a distinct service with its own cost |

## Units that are never metered

- Outcome and verification records. A customer never pays to know whether
  a result was right, and the records that say so are never withheld.
- Reading their own run history, evidence, and shared memory.
- Exporting a solution. The package that leaves the platform is the
  customer's; charging for the exit would contradict the export's purpose.
- Refusals. A refused effect, a failed check, and an honest stop cost
  nothing.

## What a hosted customer's data path looks like

```text
Request with a tenant key
├── the key is checked against a stored digest; the key itself is never stored
├── the request body is validated against the typed contract of the endpoint
├── the work runs inside a Loop with the tenant's declared authority
├── metering records carry counts and digests, never prompt bodies
└── the response carries the record identifiers the customer can query later
```

Prompt text and model outputs are stored only inside the customer's own run
history under their tenant namespace. The metering ledger, the specialist
training data, and the shared intelligence never contain them; the
learnable call records carry digests and sizes by contract.

## Deployment shapes

| Shape | Placement of each node | Store | Step |
|---|---|---|---|
| Demo | Every node in one host process | In-memory or DuckDB over packaged files | published |
| Self-hosted | Nodes as containers on the customer's cluster; Jobs for exported solutions | SQLite or DuckDB for one host, a server database for a cluster | S-4.1, S-4.2 |
| Hosted | Nodes as containers on the vendor's cluster with per-tenant namespaces | A server database with vector columns behind the catalog contract | S-4.2, S-4.4 |

The engine image is built from the repository `Dockerfile`; example 28
carries the Kubernetes manifests for a worker and a Job and validates them
offline. Deployment to a cloud account, billing, and package index
publication are blocked on accounts the owner supplies (S-4.4 to S-4.6).

## What this guide does not claim

No hosted endpoint is operated on 2026-09-18, no price is published, and
no payment provider is integrated. The feature matrix records the hosted
cloud and public pricing cells as not present until those facts change.
