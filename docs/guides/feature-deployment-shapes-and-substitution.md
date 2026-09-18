# How each feature is containerized, separated, wrapped, and swapped

This guide says, for every feature in the comparison matrix, which process
shape it can take (in process, separate process, container, microservice),
what contract sits at its boundary, where middleware wraps it, how an
implementation is swapped for a newer or better one, and how versions are
told apart. The rule behind every row: the contract is the typed record or
endpoint, never the module path, so a replacement that honors the record
is a drop-in and one that does not is refused at the boundary.

## The five shapes

```text
Shapes a boundary can take
├── in process: imported and called; the fastest, the default for a demo
├── separate process: the same contract over a local socket or a subprocess
├── container: the separate process inside the worker image with declared limits
├── microservice: the container behind the service surface with a tenant key
└── external: a vendor endpoint behind a provider adapter and a route
```

Every boundary below names the shapes it supports today and the one it
can grow into. A shape never changes authority: a microservice has exactly
the permissions its Loop declared.

## Middleware points

Middleware is anything that wraps a call without changing its contract.
The engine has four wrap points, and every feature uses them the same way:

| Wrap point | What it adds | Where it lives |
|---|---|---|
| Capability directory | Invocation policy, fallback by handshake, cost capture per call, invocation events | `CapabilityDirectory.call` |
| Model gateway | Route choice, token accounting, response admission, repair, retry policy | `core/model_gateway` |
| Service surface | Tenant authentication, endpoint permission, metering, body size limits | `core/service_api` |
| Loop envelope | Relationship, budget, effect approval, run history events | `loop/encapsulate` and the Loop runtime |

A new middleware (for example an idempotency key store or a tracing
exporter) attaches at one of these points and never inside a feature
module.

## Substitution rules

| Registry | What is swapped | How | Version signal |
|---|---|---|---|
| Catalog adapter registry | The store behind the catalog contract | Register an adapter with its capability handshake; the composite negotiates | `adapter_version` in the handshake; `record_version` on rows |
| Capability directory | A surface and its endpoints | Register a `SurfaceRegistration` from the owning package | `protocol_version` on the handshake |
| Deterministic resolvers | A resolver for a typed task | Pass a new resolver in the run dependencies; the fast path tries them in order | `resolver_id` with a version suffix |
| Model routes | The model behind a purpose | Declare a route with a `ModelProfile` and qualification state | Route name, model identifier, profile version |
| Response contracts | The shape a step asks for | Register a new contract identifier and version; steps name it | `contract_id` and `version` |
| Question forms and strategies | How a step asks | Register a form; multiplication is deterministic | Form name and provenance |
| Specialists | A trained judge | Publish a new `SpecialistModel` with its dataset reference as a candidate | `content_digest` of the weights |
| Exported solutions | A shipped package | Export a new version; the manifest digest identifies it | `version` and `manifest_digest` |

## Feature by feature

| Feature | Boundary contract | Shapes today | Shape it grows into | Middleware | Swap |
|---|---|---|---|---|---|
| Persistent memory | `CatalogStore` (get, query, stream, put with precondition, export, import, health) | in process (in-memory, SQLite, DuckDB, packaged JSONL) | microservice over a server database behind the same contract | directory for reads through Loops; service surface for tenants | adapter registry |
| Graph or temporal facts | `TemporalFact` records; `FactGraph` over any store | in process | separate process when the store is remote | same as the store | swap the store; the graph is a view |
| Outcome changes retrieval | `ReuseEvidence` records and `apply_outcome` | in process | in process (pure function) | none needed | policy record version |
| Memory versioning | revision records inside the store | in process | follows the store | same as the store | none; it is a function over the contract |
| Multi-agent shared memory | `SharedMemoryScope` and signed writes | in process | microservice: the service binds the writer to the tenant | service surface | scope record version |
| Procedures as instructions | question forms, strategies, prompt resource bundles | in process | catalog records served by the store (S-2.10) | gateway renders; directory serves | form registration |
| Executable code reuse | `DeterministicTaskResolver` protocol; reusable capability records | in process | separate process or container per resolver when a resolver needs isolation | directory; Loop envelope | resolver registration |
| Executes code or tools | workspace backends (local, Docker) and generated projects | separate process (Docker) | container per run on a cluster (Job) | Loop envelope effect approval | backend registration |
| Standalone solution export | `SolutionExportSpec`, manifest, verification | in process writes; the export itself is a container | Job on a cluster | none; the export leaves the platform | new export version |
| Independent verification | verification policy and request records; read-only Docker | separate process | container per verification | Loop envelope | verifier profile version |
| Evaluation product | `EvaluationSuite`, `EvaluationReport` | in process; `evaluate` endpoint | microservice (endpoint exists) | service surface metering | grader registration |
| Per-implementation cost records | `OperationCostRecord`, capture, ledger | in process | ledger behind the store contract | directory | ledger backend |
| Model routing | `ModelRoute`, `ModelProfile`, gateway | external endpoints behind adapters | more adapters, same gateway | gateway | route declaration |
| Model versus non-model choice | `ImplementationDecision` | in process | in process | none | policy version |
| Harness or prompt optimization | `ParameterSpace`, `optimize`, `evaluate` callable | in process; `optimize` command | microservice over the evaluate endpoint; workers per cell | service surface | strategy and policy versions |
| Trains or exports specialists | `SpecialistModel` weights as JSON; resolver | in process | separate process per training run; a specialist served as a local endpoint with a `ModelProfile` | gateway when served as a route | candidate publication |
| Open source core | the package | any | any | none | package version |
| Self-hosted option | image and manifests | container | cluster | none | image digest |
| Hosted cloud | service surface | separate process | microservice on a cluster | service surface | image digest and tenant records |
| Public pricing | packaging guide | none | none | none | guide revision |

## What a swap must prove

Before a replacement becomes the default it passes the same checks the
original passed, its mutants are killed, its handshake or profile is
recorded, and its qualification state moves from candidate only through an
independent review. A replacement that is faster but returns a different
shape is not a swap; it is a new contract version, and every consumer names
the version it uses.
