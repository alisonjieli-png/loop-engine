# Retrieval, artifact delivery, and runtime compatibility

Kind: proposed architecture and acceptance plan. Date: 2026-09-19.
Owner direction: configurable search, stable component boundaries, separate
file delivery, shared authentication, coordinated harness work, and continuous
improvement. This document distinguishes that direction from shipped behavior.

The proposed public interface returns a small set of typed intelligence
references. A separate operation retrieves selected, authorized artifacts.
Search engines, embedding models, ranking methods, storage, and transport can
change behind those interfaces. A content delivery network distributes bytes;
it is not the search engine or the authority for access.

## Canonical runtime

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Search stages are internal mechanics of classified Intelligence work unless
they need independent governance. A separately governed query-refinement or
model-ranking operation uses a canonical Loop. Libraries, indexes, buckets,
brokers, ports, and passive configuration are not new executable graph types.

## Current implementation

`core.retrieval.Retriever` provides lexical, vector, and hybrid modes. Its
defaults are SQLite full-text search and deterministic hashed text features.
The default vectors support text overlap and spelling variation, not semantic
synonym understanding. The optional Model2Vec path provides learned local
embeddings. The current LanceDB adapter uses its full-text interface; its
presence does not prove a native approximate-vector query path is installed.

The four-layer query boundary returns selected references, applies common
filters and a global result limit, and refuses changed body identity during
materialization. The public Practitioner search currently selects lexical
mode and a fixed result count. Its local implementations build or load an
in-process corpus. There is no shipped external retrieval-backend registration
interface, PostgreSQL search adapter, or Elasticsearch adapter for this path.
Backend handshake descriptions are not evidence that those deployments exist.

The optional embedding path still needs stronger immutable model-revision,
actual-dimension, cache preparation, and download-authority qualification.
Historical small-corpus timing and quality comments do not establish current
production performance. Serving and native harness use have separate open
integration gates in the continuation plan.

## Initial storage and search choices

The expanded requirements justify evaluating Elasticsearch or OpenSearch as
the first dedicated search adapter. Keep authoritative identities, access,
qualification, subscriptions, and job state outside that derived index. The
lower-service-count alternative is PostgreSQL full-text search, trigram
similarity, and `pgvector`. The same caller contract should qualify both.
This is a proposed comparison, not a selected account or performance result.

```text
Information infrastructure
├── Authoritative catalog and operational records
│   └── Postgres candidate; existing local adapters for local profiles
├── Rebuildable search projection
│   ├── Elasticsearch or OpenSearch candidate
│   └── PostgreSQL text, trigram, and vector-search candidate
└── Immutable large artifacts
    ├── private object buckets in a hosted profile
    ├── confined files in a local profile
    └── authorized delivery, optionally through a content delivery network
```

Elasticsearch documents composable retrievers, vector search, result fusion,
and semantic reranking. OpenSearch documents hybrid queries and rank-based or
score-based combination. Check the exact server release, hosted edition,
license, and enabled features during adapter negotiation.
[Elasticsearch retrievers](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers),
[Elasticsearch reranking](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking),
[OpenSearch hybrid search](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/).

`pgvector` supports exact and approximate nearest-neighbor search. Approximate
indexes trade recall for speed, and filtering affects the candidate population.
Supabase documents combining PostgreSQL full-text search and vector search.
Measure filtered recall and latency on our authorized corpus before choosing
an index or a search profile.
[pgvector](https://github.com/pgvector/pgvector),
[Supabase hybrid search](https://supabase.com/docs/guides/ai/hybrid-search).

## Stable boundaries

Extend existing owners rather than adding a second orchestration or storage
system. The contracts below are requirements for the next implementation
slice, not new callable APIs already available in the package.

| Boundary | Input and output obligation | Existing owner |
|---|---|---|
| Query planning | Need, typed constraints, authorized scope, budget, and explicit enabled stages produce a versioned plan. | `core.intelligence_layers`, classified Intelligence Loops. |
| Candidate retrieval | Query and index-space identity produce references with score provenance, completeness, and unavailable-backend state. | `core.retrieval`. |
| Ranking and reranking | Reorder admitted candidates without inventing identities or modifying permissions and qualification. | Retrieval and existing typed decision/model boundaries. |
| Catalog storage | Versioned records, expected revision, namespace, and explicit write authority produce acknowledged or unknown outcomes. | `catalog`, `RecordOperationService`. |
| Artifact access | Exact selected reference produces a bounded manifest/body or a typed refusal. | `loop.loop_capsule`, existing artifact and provisioning contracts. |
| Harness preparation | Selected qualified resources and scoped authority produce confined files with observed digests. | `node_provisioning`, `instance_instructions`, `harness_process`. |
| Authentication delegation | Host credential reference and per-caller authority produce scoped revocable leases, never broadly shared secrets. | `credential_leases`, provider and approval boundaries. |
| Work coordination | Task and output identities produce durable state transitions and exact selected output references. | Delegation, shared memory, catalog, and Run History. |

Use wrappers for these replaceable boundaries and independently versioned
subcomponents. Keep ordinary implementation helpers inside their owner; a
wrapper around every function would add edges without creating a useful
contract or deployment boundary.

## Configurable retrieval stages

```text
Authorized intelligence query
├── Identity, entitlement, namespace, and qualification checks
├── Query and candidate generation
│   ├── exact identifier or fingerprint lookup
│   ├── lexical and typo-tolerant search
│   ├── semantic dense or sparse retrieval
│   └── optional graph expansion and similarity blocking
├── Selection
│   ├── common eligibility and deduplication
│   ├── rank fusion or calibrated score combination
│   ├── optional cross-encoder or language-model reranking
│   └── optional budgeted query refinement and repeated retrieval
└── Small typed references
    └── later selection, reauthorization, materialization, and client delivery
```

Each stage needs an identity, version, input/output contract, installed
implementation, declared effects, initial choice, ordered allowed fallbacks,
budget, and failure result. Unsupported settings refuse. Enabling a model
stage requires model and disclosure authority; it cannot silently activate
because a plugin is installed. A score cannot grant access or promote a
candidate into qualified intelligence.

The default result limit can be ten, but it is a request setting, not an
architectural law. Return fewer results or an explicit insufficiency state
when the authorized corpus does not support useful matches. Do not pad the
answer with inaccessible or irrelevant items.

Locality-sensitive hashes can reduce a candidate population or find near
duplicates. Cryptographic digests establish exact content identity. Neither
is a semantic embedding or an access-control decision. Blocking may lower
recall; test its omissions separately from ranking quality.

Embedding-space identity includes the encoder, immutable revision, actual
dimension, normalization, distance, preprocessing, and corpus/chunk version.
Changing it requires a new index generation and an explicit switch after
qualification. Do not compare vectors from different spaces or silently
reuse an old index because the model name is unchanged.

## References and file delivery

A returned reference needs the item identity, exact version, body digest,
qualified source identity, selected chunk or member, applicable contracts,
score provenance, and an authorized artifact locator. It must not merely be
an unrestricted public content-delivery URL.

Store complete programs, documents, skills, folder manifests, and package
archives in immutable artifact storage. The search projection can retain
bounded searchable text, chunks, symbols, labels, and embeddings. It should
not duplicate whole executable bundles or act as the authority for their
publication state.

The delivery service rechecks access and qualification after selection.
It verifies content identity and acknowledges required usage before claiming
successful metering. Signed delivery links need appropriate expiry and
cache partitioning. Revocation blocks future authorized delivery; it cannot
erase a copy the customer already downloaded. Database and object backups
need separate restoration tests.
[Private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals),
[content delivery](https://supabase.com/docs/guides/storage/cdn/fundamentals),
[backup scope](https://supabase.com/docs/guides/platform/backups).

## Runtime compatibility

Components negotiate when they connect, not only when the repository builds.
Resolve mutually supported protocol and schema versions, required features,
qualified translation adapters, security requirements, and exact component
identities. Record the selected binding and revalidate it at use.

An older component is usable only if its supported contract preserves the
requested behavior. Otherwise return a typed unavailable or incompatible
result. Never downgrade tenant isolation, permissions, integrity, or accounting.
The [version decision](ADR-PRELAUNCH-VERSIONED-CONTRACTS.md) separates this
deliberate compatibility from unwanted pre-launch legacy readers.

## Authentication and shared work

Keep provider credentials in a host-owned broker or secret service. Each
harness authenticates to that broker and receives only its permitted lease or
proxy operation. Bind the grant to caller identity, run, provider, audience,
operations, expiry, and remaining authority. Revocation and refresh must work
across simultaneous harnesses. Shared authentication is not shared unrestricted
authority.

The broker is normally an internal mechanic. Give authentication-management
work its own canonical Loop only when it needs independent lifecycle,
supervision, budget, or acceptance. It does not need a language-model harness
merely because it exposes an endpoint.

Memory, work queues, and Run History have different contracts even if they
share one physical database. Keep run-private, participant-shared, tenant,
and reusable-candidate scopes distinct. Store durable work transitions and
immutable output versions; notifications only announce that state may have
changed. Publication does not imply completion, and consumers name the exact
output they used. Lost contact does not prove process termination or permit
replaying a committed effect.

## Telemetry and improvement

Proposed default telemetry is operational metadata: request identity,
component versions, latency, sizes, known usage, error classes, and resource
identities within the permitted scope. Raw prompts, files, outputs, and traces
containing their bodies require separate opt-in, retention, and purpose rules.
Never collect credentials, authorization headers, or refresh tokens.

Embeddings and deterministic hashes are not automatic anonymization.
Research demonstrates text recovery from embeddings in studied settings;
that does not give a recovery rate for our proposed implementation, but it
does rule out treating vectors as inherently private.
[Embedding privacy research](https://arxiv.org/abs/2310.06816).

Offer privacy controls on every plan. Dedicated infrastructure, private
indexes, custom retention, and service guarantees can be paid deployment
features. Do not make raw-content collection the condition for basic service
access. These are proposed product choices, not selected prices or legal
assurances.

Use independent evidence to propose versioned pipeline improvements. Keep
training, selection, and untouched final evaluation populations separate.
Self-correction within a request is different from an improvement qualified
for later users. Self-improvement remains Practitioner work and cannot approve
its own candidate. See the [candidate-system review](../../artifacts/continuation-research-2026-09-19/improving-retrieval-systems.md).

## First integration proof

1. Search a frozen authorized corpus through interchangeable adapters. Include
   exact identifiers, typos, synonyms, code symbols, blocked near-duplicates,
   stale versions, missing results, and cross-tenant attempts.
2. Select exact references, retrieve real files, prepare a confined assignment,
   start a real separate harness process, and observe actual loading. Compare
   with a withheld-resource control. File placement alone is insufficient.
3. Run separate workers with shared and private memory views, shared broker
   authentication, multiple output versions, cancellation, lost responses,
   restart, and revoked access. Verify durable state and independent acceptance.

Measure ranking quality, filtered recall, cold and warm latency, bytes,
physical model calls, accounting completeness, and total cost state. Every
failure remains in the denominator. A local fixture, an authorized provider
trial, and a production deployment are different qualification records.
