# Capability supply and retrieval

Kind: current architecture guide. Checked September 30, 2026. The
[roadmap](../roadmap/roadmap.yaml) owns work status, and
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority) owns authority.
The [deployment record](MVP-CLIENT-SERVER.md#current-deployment) identifies
the running image and catalogue separately.

## One runtime, several component engines

Every executable graph vertex remains a `Loop`. The complete runtime
classification and behavioral explanation are in the
[Loop guide](../components/loop-object/README.md) and the
[complete explanation](../context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).
Discovery adapters, queues, package files, search indexes and renderers are
components used by that runtime; this diagram is a data flow, not a new
executable graph definition.

```mermaid
flowchart LR
  Sources[Official repositories, registries, feeds and private source work]
  Discover[Source adapters and dated observations]
  Consider[Managed research records and consideration]
  Prepare[Import, original implementation or upstream recipe]
  Candidates[Private candidate records and immutable bodies]
  Review[Checks and independent review]
  Release[Approved catalogue release]
  Search[Authorized metadata search]
  Deliver[Exact manifests and selected files]
  Compile[Harness Working Directory Compiler]
  Execute[Customer harness and permitted engines]
  Evidence[Observed use, failures and accepted results]
  Sources --> Discover --> Consider --> Prepare --> Candidates
  Candidates --> Review --> Release --> Search --> Deliver --> Compile --> Execute
  Execute --> Evidence --> Consider
```

The public service, customer client, internal server jobs and internal local
pipelines remain the four operating areas. Their boundaries are documented
in the [four-area architecture](FOUR-ZONE-ARCHITECTURE-2026-09-27.md).
Internal research does not run inside a public web request.

The wrapping design is:

```text
Functional component owned by a Loop
├── Typed, versioned request and result
├── Compatibility, effect and resource checks
├── Existing engine slot and declared selection policy
│   ├── Baltor implementation
│   ├── Adapter to a pinned upstream implementation
│   └── Other qualified implementations of the same contract
└── Result checks, exact implementation identity and execution evidence
```

The [functional component standard](FUNCTIONAL-COMPONENT-STANDARD.md) defines
the target. Its historical status tables and proposed lifecycle features
are not evidence that every slot is operational. The
[slot catalogue](../../src/loop_engine/data/engine_slots.yaml), factory code
and observed run determine what an installation can select today.

## What a harness retrieves

A capability's job, implementation language and delivery method are separate
fields. A Python program can ship inside an npm skill; a Rust executable can
be installed by Cargo or downloaded as a binary; an MCP server may expose
either one. `npx` names a runner, not a component category or quality grade.

| Delivery form | Material Baltor supplies | Required evidence |
| --- | --- | --- |
| Complete package | Native instructions, scripts, contracts, examples and required resources | Exact file inventory, hashes, rights and dependencies; native qualification is recorded separately |
| Upstream installation recipe | Official source, pinned version, available checksum, prerequisites, setup and verification steps | Source identity and artifact binding; dependency locking and execution status are explicit |
| Baltor adapter or original implementation | Stable inputs and outputs with code, tests and source rationale | Contract conformance and the conditions in which it may replace the upstream engine |
| Executable distribution | A binary or its official download recipe for a declared operating system and processor architecture | Version, checksum or signature evidence, runtime libraries and a bounded execution check |
| Python or Rust package | A wheel, source distribution, crate, complete source package or pinned installer recipe | Package and toolchain versions, dependency-lock status, entrypoints and build/import checks |
| Container image | An OCI image reference pinned by digest, or an artifact delivered through a suitable image store | Image identity, platform, runtime user, mounts, network, resource needs and observed startup behavior |
| Container build or run recipe | Dockerfile, Compose configuration, dependency locks and build/run instructions | Base-image digests, build inputs, explicit effects and reproducible build and lifecycle checks |
| Maintained knowledge | Dated evidence, scope, uncertainty and refresh conditions | Traceable sources and a rule for expiry or renewed research |

The recipe option avoids copying a complete external runtime into the library.
An installer still needs the customer's execution, network and file-write
authority. The download and any installation are different operations.
Installing a package is not proof that its advertised tools work.

An OCI registry can deliver image layers directly while Baltor supplies the
contract and run recipe. A wheel or executable can likewise come from an
official package registry. Full artifacts remain eligible when their rights,
delivery backend and compatibility are qualified. No large binary belongs in
a model's prompt merely because the model selected it.

One recipe is counted as the files Baltor actually serves. A link to an
upstream package does not add that package's files to the published total.
Unchanged implementations stay shared when parameters or presentation change.

Search should expose purpose, input and output contracts, component form,
language, runtime, installation method, supported harness placement, effects,
source and version, dependencies, review state and observed compatibility.
Current package and search contracts provide parts of this information;
registry-wide discovery and qualification remain ongoing work under
S-6.40, S-6.81, S-6.214 and S-6.215.

## Current search implementation

The hosted catalogue uses
[`ReleaseSearchIndex`](../../src/loop_engine/core/service_runtime/catalogue_search.py):
SQLite FTS5/BM25, deterministic character-hash vectors and authorized ranking.
It builds an index per catalogue view. These hash vectors are not learned
semantic embeddings. The general retrieval module also contains an optional
LanceDB/Tantivy adapter; the hosted catalogue does not select it.

`catalogue_serving.py` constructs `ReleaseSearchIndex` directly when it builds
a catalogue view. The lexical and vector slots are declared in the slot
catalogue, but that declaration does not make this constructor a selectable
Rust server. A replacement needs host configuration, a versioned engine
handshake and the same authorization and result checks before activation.

No Rust migration is complete. Compare index construction time, memory,
search latency and relevance through the existing retrieval edge before
selecting a replacement. Preserve account permissions, withdrawal behavior,
filters, exact references and unsupported-capability refusals in that comparison.

```text
Current hosted request
  → service authentication and request limits
  → immutable catalogue view
  → ReleaseSearchIndex (Python; SQLite FTS5 and hash-vector ranking)
  → permission-scoped results with exact package references
  → separately authorized and metered download

Planned optimization at the same boundaries
  → correlated stage timings and wrong-result regression cases
  → bounded ranking cache keyed by release, policy and normalized request
  → selectable qualified engine, including a Rust candidate
  → current access and withdrawal checks before returning or downloading
```

The website's public static-asset cache is separate from search computation.
An asset version or ETag cannot grant access to a component. Shared caches must
not hold account decisions, private bodies or unscoped model responses. Cache
misses, invalidation, fresh-result bypass and concurrent callers belong in the
same qualification as a warm hit. The
[retrieval delivery gate](../roadmap/DELIVERY-SEQUENCE.md#retrieval-quality-tracing-and-speed)
defines the required measurements and failure records. No Cloudflare KV cache
or Rust service is represented as deployed by this diagram.

## Small files and large media

Use one catalogue and authorization model, with different byte-delivery
capabilities. The current `catalogue_body_store/v1` implementation stores
immutable bodies on the service volume. Its package contract bounds each file
at 8 MiB and a package at 32 MiB. This is not yet a streaming service for large
video masters. Raising those limits alone would not establish safe memory use,
resumable delivery or cache revocation.

The proposed path is:

```text
One approved catalogue and permission-scoped search
├── Small descriptions, rights, versions and exact file manifests
├── Small-file delivery through the current qualified path
├── Large-media delivery through a qualified blob-store engine
│   ├── Bounded streaming and resumable byte ranges
│   ├── Authorized download grants and current withdrawal checks
│   └── Separate previews, thumbnails and original files
└── Customer harness verifies exact bytes and records transfer outcome
```

Keep the existing body-store owner and engine-selection standard. Add an
explicit versioned capability for streaming and ranges where the current
byte-returning edge is insufficient. A compatible client must negotiate that
capability; an unsupported client receives a named refusal, not a partial file
reported as a complete package. An object-store adapter does not introduce a
new Loop runtime or a second component registry.

Index descriptions, captions, transcripts, native metadata and declared rights.
Keep raw images and video outside model context unless the task explicitly
requests them. Visual-similarity search is a separately qualified engine, not
a capability of today's character-hash vectors. A preview must name the exact
original it represents and follow the same private/public access policy.

Choose a blob provider only after measuring file sizes, transfer concurrency,
memory, bandwidth cost and required revocation delay. Private signed links are
bearer credentials, not public-cache keys or permanent authorization. A short
expiry bounds access but does not provide immediate withdrawal. Use a checking
proxy or another qualified revocation mechanism when that delay is unacceptable.
Public Good library files still require a normal enabled account and a current
download authorization, even without a paid subscription. Do not expose their
origin blobs through an anonymous public URL or let a cache bypass that check.
Keep public website assets and marketing previews separate from account-gated
library delivery. Rights clearance alone does not grant anonymous access.

Serve untrusted originals as downloads with verified media types and isolated
origins. Do not let a supplied SVG, HTML file or filename execute in the signed-in
website's origin. Decode and transcode in a bounded sandbox; image dimensions,
duration, decompressed size and parser failures matter alongside upload bytes.

Test interrupted transfers, resume with a wrong digest, invalid and overlapping
ranges, partial responses, expired grants, withdrawals, private-preview leakage,
concurrent limits and incomplete client writes. Distinguish URL issuance,
server/provider delivery and client checksum confirmation in the activity log.
Do not bill a retry as another logical download. Keep large decoding and
thumbnail jobs out of interactive search requests. The delivery plan and
S-6.215 own this extension; no new blob service has been deployed.

## Creative production and daily research

Reusable targets include Ken Burns motion, caption and panel layouts,
source-backed fact scripts, train and location quizzes, procedural scene
construction, audio-event mapping, render checks and complete review bundles.
The social-video project's finished work is reference evidence and potential
source material. Its private histories and third-party footage are not public
package payloads by default.

The [knowledge radar](../../tools/knowledge_radar/README.md) owns discovery,
managed research work and candidate production. Its source-led expansion
asks what to build, interrogates reuse and failure conditions, and prepares
native files. Independent review and catalogue publication remain subsequent
stages. An installed timer, a successful run and published additions must each
be reported from their own evidence.
