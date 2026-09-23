# Harness material hierarchy and the Harness Working Directory Compiler

September 23, 2026. The owner requested broad file compatibility, a first
100-file campaign using Tactical Engineering's Hermes route, and a standard
integration pattern: wrap reused functionality behind a component contract,
provide a Baltor implementation where useful, and allow qualified engines to
be selected or replaced. The owner-standardized name is **Harness Working Directory Compiler**.
The direction is accepted. The detailed structures
below are proposals until their owning contracts and checks are implemented.

Read the [Agent Harness adoption analysis](MADEBYWILD-AGENT-HARNESS-COMPATIBILITY-AND-ADOPTION-2026-09-23.md)
and [context, tools and binaries research](HARNESS-CONTEXT-TOOLS-BINARIES-AND-WORKSPACES-2026-09-23.md)
for observed behavior and primary sources. Roadmap D-19 and S-6.44 own compiler
engines; S-6.40 and S-6.63 own generation and admission. This is not a second
task tracker.

## Backend vocabulary

Use **Harness Working Directory Package** for a selected versioned bundle
and **Harness Working Directory File** for one exact member. The current
`CataloguePackage` and `CataloguePackageFile` contracts own those structures.
Keep **component** for a functional boundary, including the
**Harness Working Directory Compiler**, and **engine** for an eligible
implementation behind it. A compatibility profile is data consumed by an engine.

The broader existing harness-intelligence family remains an ownership and
catalogue classification. These precise backend descriptions do not silently
rename `harness_local`, serialized record versions or public interfaces. Update
those contracts and all callers together if a later implementation changes them.
Use the precise package/file terms in new development assignments so the model
knows whether it is editing contents, placement metadata or executable logic.

## Runtime classification comes first

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

A file is passive material until an authorized execution mechanism consumes it.
An index entry, graph edge, plugin, compiler, protocol transport or worker
process does not create an additional executable graph-vertex type.
Deterministic, hybrid and non-deterministic describe the owning Loop's permitted
work. A single package can support several modes through different bindings.
Calling a file a hybrid file would conceal which part needs a model and which
part has a deterministic implementation.

## A useful hierarchy has independent dimensions

```text
Intelligence item and complete package
├── Identity and authority
│   ├── Persistent owner and intelligence family
│   ├── Immutable source, version, rights and package digest
│   └── Candidate, reviewed, released or withdrawn status
├── Meaning and use
│   ├── Task method, domain and applicability
│   ├── Typed input/output contract and acceptance rule
│   └── Evidence of use and benefit for a task population
├── File contents
│   ├── Instructions, context and reference information
│   ├── Skills, commands and native agent definitions
│   ├── Tools, reusable source, binaries and WebAssembly
│   ├── Plugins, hooks, extensions and protocol configuration
│   ├── Schemas, fixtures, tests and validation rules
│   └── Graphs, indexes, templates, data and bounded state
├── Execution binding
│   ├── Direct function or subprocess
│   ├── Protocol or HTTP service
│   ├── Native harness extension
│   └── Container, microvirtual machine or WebAssembly runtime
├── Delivery profile
│   ├── Harness, interface, release and operating system
│   ├── Native location, scope, load trigger and precedence
│   └── Required capabilities and explicit unsupported behavior
└── Dependencies and effects
    ├── Exact transitive resources, runtimes and environment
    ├── Secret references and permitted endpoints
    └── File, process, network, model and external-effect authority
```

These are facets on existing package and capability records. They do not add
intelligence layers. Harness-native bodies retain their identity in the
`harness_local` source layer. Loop-native and Open Knowledge Format material
follow their existing ownership rules. Runtime Memory remains temporary.

The package contract already records path, digest, size, media type and role.
Extend that contract deliberately for needed activation, runtime and platform
facts. A free-form tag cannot substitute for a typed capability or permission.
Unknown extensions require a supported contract version, not silent guessing.

## What can be put into a workspace

| Kind | Examples | How it becomes useful | Important constraint |
| --- | --- | --- | --- |
| Immediate assignment | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | Native instruction discovery or explicit launch input | Keep objective, first action and acceptance visible; account for parent/user instructions |
| Additional context | `node_context.md`, Markdown, JSON, text excerpts | Explicit file read or supported import | The filename alone does not cause automatic loading |
| Reusable procedure | `SKILL.md` and its directory | Skill discovery, selection and activation | Capitalization and frontmatter are part of the selected profile; arbitrary `skills.md` is not equivalent |
| Native command | Claude commands, Copilot prompt files | User/agent invocation in a supporting surface | Commands can have side effects and host-specific argument rules |
| Native agent definition | Agent Markdown or TOML | Harness delegation | Conversation isolation does not establish workspace or authority isolation |
| Deterministic script | Python, JavaScript, shell, SQL | Explicit tool binding or direct execution | Interpreter, dependencies, inputs, output and effects must be declared |
| Native binary | ELF, Mach-O, PE | Explicit invocation | Verify bytes, executable mode, operating system, architecture and application binary interface |
| WebAssembly module | `.wasm` plus imports/runtime binding | Qualified module host | Imports and resource limits determine authority; the suffix grants nothing |
| Harness executable | A pinned Codex, Pi or other runtime installation | Executor launches it | Store/runtime dependency, not ordinary model context; never execute a downloaded binary by filename guess |
| Plugin or extension | Native manifest with skills/tools/agents | Explicit install/enable or documented discovery | Some hosts execute imports immediately; activation must be authorized |
| Hook | Native lifecycle declaration plus handler | Event registration and invocation | Required checks must refuse unsupported events or return semantics |
| Protocol configuration | MCP project/user settings, MCPB package | A supporting loader creates the connection | Configuration syntax, transport, authentication and protocol revision differ |
| Contract | JSON Schema, OpenAPI, protobuf, typed records | Validator or generated binding consumes it | A schema sitting on disk is not enforced by the model |
| Test or verifier | Fixture, executable test, golden output | Independent evaluation | Producer tests are useful evidence, not independent approval |
| Code graph | Symbols, edges, source ranges and graph schema | Selected graph query tool | Tie every symbol and edge to an exact source snapshot; derived claims can be stale |
| Search index | Lexical postings, vector index, graph index | A registered search engine | Match tokenizer/embedding/schema, permissions and corpus digest |
| State and handoff | Structured state snapshot and selected artifacts | Explicit task initialization | Never treat it as a universal resumable session or include credentials |
| Template or data | HTML, CSV, SQL, image, office document | Referenced by procedure/tool | Opaque bytes must survive packaging unchanged |
| Run evidence | Native events, traces, tool results, validation | Supervisor collects and interprets | Keep authoritative records outside worker write authority |

Native discovery evidence is recorded per interface and version. Installation,
discovery, activation, execution and accepted output remain different facts.

## Generated workspace and shared stores

Use the existing task working folder with scoped views. Shared immutable
packages and caches live outside an attempt; each attempt gets selected inputs
and a separate writable area. The following is an illustrative generated
layout, not a new universal harness specification:

```text
attempt workspace
├── AGENTS.md                         essential assignment
├── node_context.md                   explicitly referenced context
├── native adapter files              selected harness only
├── .agents/skills/<selected>/        when the profile supports this location
├── tools/                            selected, pinned executable resources
├── contracts/                        input, output and acceptance definitions
├── references/                       selectively read information
├── inputs/                           immutable declared task data
├── indexes/                          declared derived data and source manifest
├── outputs/                          candidate deliverables
└── scratch/                          disposable work
```

The supervisor owns the resolved manifest, lock, permission bindings and final
run record. It can expose a read-only explanatory copy. A folder name or file
permission alone does not prove isolation; the selected runtime must enforce
the claimed boundary. A new attempt must not inherit stale outputs or an
unrelated user plugin.

Native projection locations belong in versioned `ClientLayoutProfile` records.
Do not create all providers' files in every attempt. Development authoring can
support simultaneous projections as an explicit alternative. A customer may
choose the native form directly or the Agent Harness source form, with the
same package identity and a separate digest for every resulting artifact.

## Harness Working Directory Compiler

```text
Versioned material compilation edge
├── Input
│   ├── Selected exact package trees and dependency closure
│   ├── Assignment and effective authority
│   ├── Target compatibility profile
│   └── Declared advisory model/task variants
├── Eligible engines
│   ├── Baltor native compiler
│   ├── madebywild Agent Harness adapter
│   └── Future qualified compiler adapters
└── Output
    ├── Proposed exact files and source-to-output mapping
    ├── Required runtime/dependencies and secret references
    ├── Capability resolutions, omissions and refusal reasons
    └── Deterministic plan digest and expected existing-file state
```

Compilation produces data. A separate, existing confined writer applies the
authorized plan. This separation supports inspection and comparison without
granting an external compiler unrestricted access to the destination. If an
upstream tool only offers a filesystem interface, run it in a disposable staging
workspace and import its bounded output through the same validation boundary.

Initial engine priority: qualified Baltor direct compiler, then a qualified
Agent Harness adapter when the customer selected that workspace ecosystem.
Fallback requires an explicit allowed order and preserves required semantics,
authority, task state and cumulative budget. An unsupported mandatory feature
refuses the attempt; it does not become a prose suggestion.

For a package with executable content, native runtime behavior and interpreted
configuration must be checked after compilation. Raw settings cannot replace
the approved command or add a network server unnoticed. File hashes identify
bytes; they do not establish semantic equivalence or permission enforcement.

## Applying the pattern to every reused project

For each reused functionality, record its invariant, existing owning boundary,
typed request/result/error contract, supported version/capabilities, source
revision/license, engine-specific configuration, effects, and qualification
evidence. Keep it behind the existing engine registry and boundary registry.
Search for an equivalent component before adding another one.

| Function | Candidate external engine | Baltor implementation/adapter responsibility |
| --- | --- | --- |
| Native file compilation | Agent Harness | Direct profiles plus a checked upstream wrapper |
| Tool exposure | FastMCP | Selected typed operations, explicit authentication/effects and native wrappers |
| Sandboxed execution | OpenSandbox, WebAssembly runtimes | Common execution contract, authority and independent acceptance |
| Durable scheduling | DBOS or existing scheduler | Replay classification, budgets and external-effect reconciliation |
| Evaluation | Harbor, Inspect AI | Frozen populations and evaluator adapters with explicit denominators |
| Retrieval | Lexical, vector and graph engines | Eligibility before ranking, corpus/source bindings and abstention |
| User interaction | OpenMuse, AG-UI, A2UI, MCP Apps | A qualified interface adapter without moving task authority into presentation |

These are research candidates, not installed engines. The external project may
be a library, a subprocess, a container service or a remote service. Select the
appropriate containment for that execution interface. Wrapping a component
does not require importing its whole application or renaming the Loop runtime.

The requested Baltor variation should implement the same contract and run the
same conformance population. Start with the smallest useful implementation,
then use measured failures to improve it. Retain useful alternative engines;
do not make superficial API similarity proof of interchangeable behavior.

## Code graph, index and retrieval rules

Code graph systems are a strong match for focused context selection. A step can
request callers, definitions, affected tests or a bounded dependency neighborhood
instead of reading the whole repository. A graph provider can return exact
source spans with file digest, commit and parser revision. The model sees the
selected evidence; the graph remains a derived resource behind a query tool.

An index manifest should identify the corpus and schema, index engine/version,
chunking and tokenizer, embedding model/dimension/distance when used, source
digests, access scope and build state. Never reuse vectors from another embedding
space because their dimensions happen to match. Apply customer permissions before
returning names, scores or snippets. An index of private code must not be packaged
into a public intelligence item.

Candidate ranking can combine exact symbols, lexical retrieval, vector retrieval
and graph expansion. The first implementation should compare those engines
against a frozen relevant/irrelevant query set, report retrieval failures and
abstention, and optimize accepted task output under the customer's constraints.
Any new graph or embedding engine stays optional behind the same search edge.

## Model-specific intelligence

Treat simplified, condensed or reworded instructions as derived variants with
their own bytes, parent identity, transformation configuration and evaluation
evidence. The method's mandatory constraints and output contract are invariants.
A smaller model may benefit from more examples or more explicit steps; fewer
tokens is a hypothesis to test, not a universal objective.

Keep independent choices for context size, procedure detail, model, heuristic
versus model decision, deterministic implementation, verification strength and
ensemble use. Compare variants on identical tasks with a fixed acceptance rule.
Successful generation does not authorize automatic promotion of the variant.

## First 100-file campaign

Build a bounded population of complete original packages with 100 planned
payload paths. Include instruction files, a real native skill, a native plugin,
deterministic helper code, contracts, fixtures, acceptance tests, context/index
examples and references. The files must serve declared purposes; manifests,
duplicate projections and attempt journals do not count as new logical methods.

The model supplies candidate contents. The frozen plan owns package identity,
paths, roles, source/license evidence, dependencies, effects and acceptance.
Record Tactical Engineering's exact reported model and capacity evidence before
calls. Preserve outages, invalid JSON, repairs and unknown usage; never quietly
substitute another provider or fabricate missing files.

The first gate is complete exact-tree preparation. Then independently test
deterministic behavior, contracts, native discovery and applicable plugin
activation. Formal library admission still requires the existing independent
review policy. Public claims must report prepared, checked, approved and served
counts separately. One hundred generated files is not one hundred approved
packages, one hundred native plugins or a production-ready million-item service.
