# Loop Engine Universal Evolution, Compatibility, Storage, and Ontology Implementation Harness

Use this entire document as the goal prompt in a new Codex, Claude Code, OpenCode, or equivalent development-agent session.

Work directly in the current Loop Engine repository. Do not treat this as a documentation-only exercise. Inspect, research, compare, decide, implement, migrate, test, verify, simplify, and document the actual system until the source tree, persistent records, runtime behavior, storage backends, plugin system, governance flow, and public interfaces agree.

Do not commit or push unless explicitly instructed.

---

## 0. Operating posture

Act as an architecture researcher, systems designer, migration engineer, implementation engineer, test engineer, security reviewer, and documentation maintainer.

Do not blindly implement every idea in this prompt. Treat the non-negotiable ontology as authoritative, then aggressively research variations for everything else. For each meaningful design choice:

1. inspect the current repository;
2. identify the actual problem and constraints;
3. research current primary specifications and mature implementations;
4. generate multiple viable alternatives;
5. compare them using explicit criteria;
6. select the smallest design that preserves future flexibility;
7. record the decision and rejected alternatives;
8. implement a vertical slice;
9. test compatibility, migration, failure, and rollback behavior;
10. revise the design when evidence contradicts the initial choice;
11. continue until the architecture and implementation agree.

Prefer working software, machine-readable contracts, executable tests, and verified migrations over diagrams or prose alone.

Use plain, direct language. Do not hide uncertainty. Do not claim conformance to a standard without a conformance test or precise mapping document.

---

## 1. Mission

Aggressively evolve Loop Engine into a universal, ontology-first, storage-independent, version-aware, plugin-extensible Loop system with the following properties:

1. There is one operational runtime object: `Loop` or `LoopNode`, but not two independently executing classes.
2. `Node` is the general graph object; the operational specialization is the Loop object.
3. Practitioner, Intelligence, and Solution are roles or profiles of the same Loop object.
4. Root and Child are runtime positions, not subclasses.
5. Deterministic, Hybrid, and Non-Deterministic are run modes, not subclasses.
6. Context, Code, Previous Run and Solution, and User remain the four persistent intelligence layers.
7. Core, Learned, and Plugin are universal source or collection classes for reusable persistent intelligence.
8. Candidate is a governance lifecycle state, not a storage backend and not a fourth source class.
9. Core intelligence ships with the package as immutable, versioned seed intelligence, normally JSONL records plus referenced files and first-party implementation code.
10. Learned intelligence can be file-based, SQLite-based, server-database-based, object-store-based, remote-service-based, or represented in multiple synchronized materializations.
11. Plugin intelligence can be a portable bundle, installed package, container, remote service, local directory, database contribution, or hybrid deployment.
12. Record identity, artifact content, lifecycle, provenance, source class, storage backend, deployment location, and materialization are separate axes.
13. The same logical record can have multiple materializations without acquiring multiple identities.
14. Every reusable artifact uses a common record envelope and an artifact-specific typed specification.
15. Contracts, rules, policies, standardizations, vocabularies, attributes, relationships, plugins, evaluators, bindings, Loop definitions, Loop canvases, and migrations use standard ontologies.
16. The folder architecture follows the stable logical architecture as closely as practical without encoding high-cardinality semantic classifications as folders.
17. Learned solutions, nodes, canvases, patterns, and evaluations are categorized primarily by attributes, relationships, evidence, and indexes, not deep semantic directories.
18. One unified catalog resolves records across Core, Learned, Plugin, Candidate staging, files, databases, object stores, and remote services.
19. Compatibility is negotiated through explicit version and capability handshakes.
20. Migration paths are first-class, versioned, testable artifacts.
21. File and database representations must support lossless export, import, verification, and round-trip testing where the artifact type permits it.
22. Static or Core Architecture eats its own dog food: reusable operational behavior is defined as Core Code Intelligence and executes through ordinary Loops.
23. Only a minimal Kernel remains below the Loop abstraction.
24. Self-review and self-improvement may generate candidates but may not approve or activate their own outputs.
25. Every deployment has preflight, pre-deploy, post-deploy, compatibility, rollback, and recovery checks.
26. Documentation, manifests, schemas, generated views, code, tests, runtime metadata, and storage records use the same identifiers and terms.

The final result must be an implemented and verified system, not only a proposal.

---

## 2. Repository-first authority

Before changing architecture, inspect the current repository deeply.

At minimum, read:

- root `README.md`;
- every `AGENTS.md`, `CLAUDE.md`, or repository instruction file;
- all architecture decision records;
- all component READMEs;
- the Loop class and related models;
- Node, Loop profile, role, run-mode, step-profile, budget, stop-condition, and contract code;
- child-loop and delegation runtime code;
- intelligence layer models, indexes, stores, loaders, and importers;
- Core Architecture or equivalent code;
- Solution Canvas code;
- Practitioner and self-review code;
- governance and candidate code;
- plugin discovery, manifest, installation, activation, and sandbox code;
- serialization, schema, API, database, JSONL, object-store, and cache code;
- Chronicle, Runtime Memory, artifacts, checkpoints, and observability code;
- migration scripts and compatibility shims;
- tests, examples, demos, studio views, and CLI commands.

Use repository search aggressively. Begin with commands similar to:

```bash
find . -name AGENTS.md -o -name CLAUDE.md -o -name README.md -o -name ADR.md
rg -n "class Loop|class Node|LoopNode|LoopDefinition|LoopCanvas"
rg -n "core|Core Architecture|core_architecture"
rg -n "Practitioner|Intelligence|Solution|role_profile|run_mode"
rg -n "contract|rule|policy|standardization|normalization"
rg -n "plugin|manifest|entry_point|extension|adapter|capability"
rg -n "candidate|learned|promotion|approval|rollback|governance"
rg -n "jsonl|sqlite|postgres|database|object_store|remote_catalog"
rg -n "schema_version|ontology_version|compatibility|migration|handshake"
rg -n "Chronicle|runtime_memory|checkpoint|artifact|event"
rg -n "OpenAPI|AsyncAPI|CloudEvents|OpenTelemetry|JSON Schema"
```

Create a repository evidence report before the main migration. Include:

```text
Current object model
Current execution model
Current folder model
Current persistence model
Current plugin model
Current version model
Current compatibility behavior
Current migration behavior
Current governance flow
Current observability model
Current tests and missing tests
Terminology conflicts
Duplicate or parallel ontologies
Dead code and stale documentation
Public APIs that require compatibility shims
```

Use current code as evidence of present behavior. Use this harness as the target architecture. When current behavior and the target disagree:

1. record the disagreement;
2. identify affected users and persisted data;
3. determine whether a compatibility shim or migration is required;
4. implement the target architecture;
5. preserve old public imports temporarily when justified;
6. add deprecation warnings and removal conditions;
7. update docs and tests to describe verified behavior;
8. remove the compatibility layer only after migration gates pass.

Do not preserve an incoherent ontology merely because it already exists.

---

## 3. Normative language

Use these terms in architecture documents, schemas, contracts, and decisions:

```text
MUST / MUST NOT
    Required for correctness, integrity, security, or architectural coherence.

SHOULD / SHOULD NOT
    The default choice unless a documented exception has stronger evidence.

MAY
    Optional behavior that must remain interoperable when absent.
```

Every exception to a MUST requires an explicit architecture decision record and a failing-gate waiver with an owner and expiration condition.

---

## 4. Non-negotiable Loop ontology

### 4.1 One operational runtime

Conceptually:

```text
Node
└── LoopNode
```

If the current public runtime class is `Loop`, keep `Loop` as the canonical runtime implementation or migrate deliberately. Do not create a second independently executing `LoopNode` class.

A compatibility alias is acceptable temporarily:

```text
Conceptual ontology: Node -> LoopNode
Canonical runtime implementation: Loop
Compatibility alias: LoopNode
```

or the reverse, but there MUST be one implementation, one identity, one lifecycle, and one executor.

### 4.2 Independent Loop dimensions

```text
Loop
├── identity
├── definition reference
├── goal
├── typed input contract
├── typed output contract
├── position
│   ├── root
│   └── child
├── role
│   ├── practitioner
│   ├── intelligence
│   └── solution
├── run mode
│   ├── deterministic
│   ├── hybrid
│   └── non_deterministic
├── step profile
├── work budget
├── stop condition
├── permissions and effects
├── parent Loop reference
├── child Loop references
├── Runtime Memory reference
└── Chronicle reference
```

Do not create separate runtime classes for combinations of these dimensions.

### 4.3 Role is not artifact kind

A Loop role says why a Loop runs.

An artifact kind says what a persistent record defines.

Examples:

```text
artifact_kind = loop_definition
spec.loop_role = practitioner

artifact_kind = loop_canvas
spec.intended_root_role = solution

artifact_kind = evaluator
spec.invocation_role = solution
```

Do not make role the primary folder identity for large learned catalogs.

### 4.4 Position is runtime topology

Root and Child positions are assigned when a run tree is instantiated. They MUST NOT be encoded as permanent source folders or separate definition types unless a definition has a true constraint such as `allowed_positions`.

### 4.5 Everything that performs work is a Loop

Files, prompts, packages, models, contracts, rules, records, tools, and services are not operational nodes by themselves.

Operations such as these are Loops:

```text
retrieve a record
select a model
invoke a model
read a file
write a file
execute code
validate a contract
evaluate a rule
standardize a value
materialize an artifact
verify a signature
migrate a record
install a plugin
compare versions
approve an effect
build a report
```

The underlying code unit or remote endpoint is an implementation or binding used by the Loop.

### 4.6 Minimal Kernel boundary

The Kernel is the only intentionally non-dogfooded execution substrate.

It may:

```text
load a definition
resolve a reference
instantiate a Loop
advance Loop lifecycle state
invoke a selected implementation binding
enforce hard contracts, permissions, budgets, and stop conditions
append Chronicle events atomically
recover or fail safely after interruption
```

It MUST NOT become a second home for retrieval, model orchestration, solution logic, self-review, plugin business logic, semantic validation, or domain workflows.

---

## 5. Persistent intelligence ontology

The four persistent intelligence layers are fixed:

```text
Intelligence
├── Context Intelligence
├── Code Intelligence
├── Previous Run and Solution Intelligence
└── User Intelligence
```

Runtime Memory is separate and temporary.

A file type, table, vector row, Markdown page, model checkpoint, package, plugin, transcript, or database is a representation or source. It is not an intelligence layer.

### 5.1 Universal source collections

Every reusable persistent intelligence record belongs to one source collection:

```text
Core
Learned
Plugin
```

Definitions:

```text
Core
└── Shipped with Loop Engine or an official first-party distribution.
    Immutable within a released version.
    Available out of the box.
    Replaced only by a new version.

Learned
└── Created, derived, imported, discovered, or improved after installation.
    Independently reviewed and accepted.
    Versioned rather than overwritten.
    Scoped to an installation, organization, workspace, project, or user.

Plugin
└── Supplied by a namespaced plugin package or service.
    Immutable within an installed plugin version.
    Loaded through the same schemas, catalog, governance, and Loop runtime.
```

### 5.2 Candidate is lifecycle, not source

```text
Draft
Candidate
Under Review
Approved
Active
Deprecated
Rejected
Archived
Revoked
```

A candidate can originate from Core development, self-review, a user, a plugin, an import, or an external service. Candidate records remain outside the active Learned catalog until independent approval.

### 5.3 Generated is provenance, not source

Use provenance fields such as:

```text
creation_method = generated
producer_loop_ref = ...
derived_from = ...
```

Generated content becomes Learned only after governance accepts it.

### 5.4 Core Architecture

Retire Core Architecture as a parallel runtime or service kingdom.

Use:

```text
Core Architecture
= Core Code Intelligence
= intelligence/code/core
```

Core Code Intelligence contains built-in Loop definitions, canvases, code units, contracts, rules, policies, standardizations, evaluators, bindings, schemas, vocabularies, and related records.

When these definitions perform work, they instantiate ordinary Loops.

---

## 6. Stable architecture versus high-cardinality classification

Folders MUST encode only stable, low-cardinality ownership and persistence boundaries.

Good folder dimensions:

```text
node
ontology
intelligence layer
Core / Learned / Plugins
catalog
governance
runtime
kernel
interfaces
package-owned implementation code
portable bundle records versus large files
```

Do not encode these as deep folder taxonomies:

```text
Loop role
run mode
root or child
domain
industry
problem type
platform
Kaggle competition type
tabular / image / text / audio
classification / regression
model family
method
capability
constraint
resource requirement
quality tier
failure type
named solution
named learned pattern
individual canvas
individual evaluation
```

Those belong in typed specs, descriptors, attribute assertions, relationships, evidence, and indexes.

Bad:

```text
learned/solution/kaggle/tabular/classification/xgboost/high_cardinality/pipeline_42/
```

Good:

```text
Learned Code Intelligence record
├── artifact_kind: loop_canvas
├── intended_role: solution
├── descriptors.platforms: [kaggle]
├── descriptors.problem_types: [tabular, classification]
├── descriptors.methods: [xgboost, cross_validation]
├── descriptors.characteristics: [high_cardinality]
└── file_refs: [artifact://sha256/...]
```

Generated views MAY expose semantic groupings, but generated views are never canonical storage locations.

---

## 7. Target logical architecture tree

```text
Loop Engine
│
├── Ontology
│   ├── Constitutional Ontology
│   │   ├── Record Envelope
│   │   ├── Node
│   │   ├── Loop
│   │   ├── Loop Definition
│   │   ├── Loop Canvas
│   │   ├── Intelligence Record
│   │   ├── Intelligence Layer
│   │   ├── Source Collection
│   │   ├── Lifecycle
│   │   ├── Contract
│   │   ├── Rule
│   │   ├── Policy
│   │   ├── Standardization
│   │   ├── Attribute Definition
│   │   ├── Attribute Assertion
│   │   ├── Relationship Definition
│   │   ├── Relationship Assertion
│   │   ├── Evidence
│   │   ├── Evaluation
│   │   ├── Provenance
│   │   ├── Governance Event
│   │   ├── Store Descriptor
│   │   ├── Materialization
│   │   ├── Migration
│   │   └── Compatibility Handshake
│   │
│   ├── Artifact Schemas
│   │   ├── Loop Definition Schema
│   │   ├── Loop Canvas Schema
│   │   ├── Contract Schema
│   │   ├── Rule Schema
│   │   ├── Policy Schema
│   │   ├── Standardization Schema
│   │   ├── Plugin Manifest Schema
│   │   ├── Evaluator Schema
│   │   ├── Binding Schema
│   │   └── Migration Schema
│   │
│   ├── Vocabularies
│   │   ├── Core
│   │   ├── Learned
│   │   └── Plugins
│   │
│   └── Mappings
│       ├── External Standard Mappings
│       ├── Legacy Mappings
│       ├── Cross-Version Mappings
│       └── Plugin-to-Core Mappings
│
├── Node System
│   ├── Node
│   └── Loop
│       ├── Definition
│       ├── Invocation
│       ├── Runtime Instance
│       ├── Result
│       ├── Dimensions
│       ├── Contracts
│       ├── Effects
│       └── References
│
├── Intelligence
│   ├── Context
│   │   ├── Core
│   │   ├── Learned
│   │   └── Plugins
│   ├── Code
│   │   ├── Core
│   │   ├── Learned
│   │   └── Plugins
│   ├── Previous Run and Solution
│   │   ├── Core
│   │   ├── Learned
│   │   └── Plugins
│   └── User
│       ├── Core
│       ├── Learned
│       └── Plugins
│
├── Catalog
│   ├── Unified Registry
│   ├── Query Engine
│   ├── Version Resolver
│   ├── Relationship Resolver
│   ├── Compatibility Resolver
│   ├── Materialization Resolver
│   ├── Store Router
│   └── Derived Indexes
│
├── Storage and Materialization
│   ├── Package JSONL
│   ├── Portable Directory Bundle
│   ├── Portable Archive Bundle
│   ├── SQLite
│   ├── SQL Database
│   ├── Document Database
│   ├── Object Store
│   ├── Content-Addressed File Store
│   ├── Remote Catalog Service
│   ├── Plugin Bundle
│   ├── Plugin Service
│   └── Disposable Cache
│
├── Governance
│   ├── Candidate Staging
│   ├── Evaluation
│   ├── Independent Review
│   ├── Decision
│   ├── Approval
│   ├── Promotion to Learned
│   ├── Rejection
│   ├── Deprecation
│   ├── Revocation
│   └── Rollback
│
├── Runtime
│   ├── Loop Instances
│   ├── Run Trees
│   ├── Runtime Memory
│   ├── Chronicle
│   ├── Results
│   ├── Artifacts
│   ├── Checkpoints
│   └── Workspaces
│
├── Plugins
│   ├── Discovery
│   ├── Manifest Validation
│   ├── Compatibility Handshake
│   ├── Installation
│   ├── Activation
│   ├── Isolation
│   ├── Upgrade
│   ├── Rollback
│   └── Uninstallation
│
├── Interfaces
│   ├── Python API
│   ├── HTTP API
│   ├── Event API
│   ├── CLI
│   ├── Studio
│   └── Generated Catalog Views
│
└── Kernel
    ├── Definition Loader
    ├── Reference Resolver
    ├── Loop Instantiator
    ├── Loop Executor
    ├── Hard Enforcement
    ├── Lifecycle State Machine
    └── Chronicle Event Writer
```

---

## 8. Recommended source repository tree

Use this as a target, not a reason to create empty architecture theater. Adjust only when repository evidence supports a cleaner implementation.

```text
loop-engine/
│
├── README.md
├── AGENTS.md
├── pyproject.toml
├── architecture-decisions/
│   └── README.md
│
├── src/
│   └── loop_engine/
│       ├── README.md
│       │
│       ├── ontology/
│       │   ├── README.md
│       │   ├── constitution/
│       │   │   ├── README.md
│       │   │   ├── record-envelope.schema.json
│       │   │   ├── node.schema.json
│       │   │   ├── loop.schema.json
│       │   │   ├── intelligence-record.schema.json
│       │   │   ├── lifecycle.schema.json
│       │   │   ├── provenance.schema.json
│       │   │   ├── evidence.schema.json
│       │   │   ├── relationship.schema.json
│       │   │   ├── materialization.schema.json
│       │   │   ├── migration.schema.json
│       │   │   └── compatibility-handshake.schema.json
│       │   │
│       │   ├── artifact_schemas/
│       │   │   ├── README.md
│       │   │   ├── loop-definition.schema.json
│       │   │   ├── loop-canvas.schema.json
│       │   │   ├── contract.schema.json
│       │   │   ├── rule.schema.json
│       │   │   ├── policy.schema.json
│       │   │   ├── standardization.schema.json
│       │   │   ├── plugin-manifest.schema.json
│       │   │   ├── attribute-definition.schema.json
│       │   │   ├── relationship-definition.schema.json
│       │   │   ├── evaluator.schema.json
│       │   │   ├── binding.schema.json
│       │   │   └── store-descriptor.schema.json
│       │   │
│       │   ├── vocabularies/
│       │   │   ├── README.md
│       │   │   ├── core/
│       │   │   │   ├── README.md
│       │   │   │   ├── manifest.json
│       │   │   │   ├── records/
│       │   │   │   │   └── part-00000.jsonl
│       │   │   │   └── files/
│       │   │   ├── learned/
│       │   │   │   └── README.md
│       │   │   └── plugins/
│       │   │       └── README.md
│       │   │
│       │   └── mappings/
│       │       ├── README.md
│       │       ├── core/
│       │       ├── learned/
│       │       └── plugins/
│       │
│       ├── node/
│       │   ├── README.md
│       │   ├── models.py
│       │   ├── definitions.py
│       │   ├── dimensions.py
│       │   ├── lifecycle.py
│       │   ├── contracts.py
│       │   ├── effects.py
│       │   ├── references.py
│       │   └── serialization.py
│       │
│       ├── intelligence/
│       │   ├── README.md
│       │   ├── models.py
│       │   ├── artifact_specs.py
│       │   ├── attributes.py
│       │   ├── relationships.py
│       │   ├── evidence.py
│       │   ├── provenance.py
│       │   ├── query.py
│       │   ├── ranking.py
│       │   ├── validation.py
│       │   ├── serialization.py
│       │   │
│       │   ├── context/
│       │   │   ├── README.md
│       │   │   ├── core/
│       │   │   │   ├── README.md
│       │   │   │   ├── manifest.json
│       │   │   │   ├── records/part-00000.jsonl
│       │   │   │   └── files/
│       │   │   ├── learned/README.md
│       │   │   └── plugins/README.md
│       │   │
│       │   ├── code/
│       │   │   ├── README.md
│       │   │   ├── core/
│       │   │   │   ├── README.md
│       │   │   │   ├── manifest.json
│       │   │   │   ├── records/part-00000.jsonl
│       │   │   │   ├── files/
│       │   │   │   └── implementations/
│       │   │   │       ├── README.md
│       │   │   │       ├── catalog/
│       │   │   │       ├── contracts/
│       │   │   │       ├── rules/
│       │   │   │       ├── standardization/
│       │   │   │       ├── storage/
│       │   │   │       ├── plugins/
│       │   │   │       ├── governance/
│       │   │   │       ├── model_access/
│       │   │   │       ├── workspaces/
│       │   │   │       ├── validation/
│       │   │   │       └── reporting/
│       │   │   ├── learned/README.md
│       │   │   └── plugins/README.md
│       │   │
│       │   ├── previous_run_and_solution/
│       │   │   ├── README.md
│       │   │   ├── core/
│       │   │   │   ├── README.md
│       │   │   │   ├── manifest.json
│       │   │   │   ├── records/part-00000.jsonl
│       │   │   │   └── files/
│       │   │   ├── learned/README.md
│       │   │   └── plugins/README.md
│       │   │
│       │   └── user/
│       │       ├── README.md
│       │       ├── core/
│       │       │   ├── README.md
│       │       │   ├── manifest.json
│       │       │   └── records/part-00000.jsonl
│       │       ├── learned/README.md
│       │       └── plugins/README.md
│       │
│       ├── catalog/
│       │   ├── README.md
│       │   ├── interfaces.py
│       │   ├── registry.py
│       │   ├── query.py
│       │   ├── resolver.py
│       │   ├── versions.py
│       │   ├── compatibility.py
│       │   ├── materialization.py
│       │   ├── routing.py
│       │   └── stores/
│       │       ├── README.md
│       │       ├── base.py
│       │       ├── package_jsonl.py
│       │       ├── directory_bundle.py
│       │       ├── archive_bundle.py
│       │       ├── sqlite.py
│       │       ├── sql_database.py
│       │       ├── document_database.py
│       │       ├── object_store.py
│       │       ├── remote_catalog.py
│       │       ├── plugin_store.py
│       │       ├── composite.py
│       │       └── cache.py
│       │
│       ├── compatibility/
│       │   ├── README.md
│       │   ├── models.py
│       │   ├── handshake.py
│       │   ├── negotiation.py
│       │   ├── feature_registry.py
│       │   ├── matrices.py
│       │   ├── migration_planner.py
│       │   └── reports.py
│       │
│       ├── migrations/
│       │   ├── README.md
│       │   ├── models.py
│       │   ├── registry.py
│       │   ├── planner.py
│       │   ├── executor.py
│       │   ├── verification.py
│       │   └── rollback.py
│       │
│       ├── governance/
│       │   ├── README.md
│       │   ├── models.py
│       │   ├── candidates.py
│       │   ├── evaluations.py
│       │   ├── reviews.py
│       │   ├── decisions.py
│       │   ├── promotion.py
│       │   ├── revocation.py
│       │   └── rollback.py
│       │
│       ├── plugins/
│       │   ├── README.md
│       │   ├── models.py
│       │   ├── manifest.py
│       │   ├── discovery.py
│       │   ├── validation.py
│       │   ├── handshake.py
│       │   ├── installation.py
│       │   ├── activation.py
│       │   ├── isolation.py
│       │   ├── upgrade.py
│       │   ├── rollback.py
│       │   └── removal.py
│       │
│       ├── runtime/
│       │   ├── README.md
│       │   ├── models.py
│       │   ├── run_tree.py
│       │   ├── runtime_memory.py
│       │   ├── chronicle.py
│       │   ├── checkpoints.py
│       │   ├── results.py
│       │   ├── artifacts.py
│       │   ├── workspaces.py
│       │   └── recovery.py
│       │
│       ├── kernel/
│       │   ├── README.md
│       │   ├── loader.py
│       │   ├── resolver.py
│       │   ├── instantiator.py
│       │   ├── executor.py
│       │   ├── enforcement.py
│       │   ├── lifecycle.py
│       │   └── event_writer.py
│       │
│       └── interfaces/
│           ├── README.md
│           ├── api/
│           ├── events/
│           ├── cli/
│           └── studio/
│
├── tests/
│   ├── architecture/
│   ├── ontology/
│   ├── node/
│   ├── intelligence/
│   ├── catalog/
│   ├── compatibility/
│   ├── migrations/
│   ├── governance/
│   ├── plugins/
│   ├── runtime/
│   ├── storage_conformance/
│   ├── security/
│   └── end_to_end/
│
├── docs/
│   ├── architecture/
│   ├── concepts/
│   ├── standards/
│   ├── compatibility/
│   ├── migrations/
│   ├── plugin-development/
│   ├── deployment-profiles/
│   ├── runbooks/
│   └── generated/
│
├── examples/
│   ├── package_only/
│   ├── local_sqlite/
│   ├── server_database/
│   ├── portable_bundle/
│   ├── plugin_bundle/
│   ├── remote_plugin/
│   ├── compatibility_handshake/
│   ├── migration/
│   └── self_review_candidate/
│
└── tools/
    ├── validate_architecture.py
    ├── validate_core_bundles.py
    ├── validate_schemas.py
    ├── validate_compatibility.py
    ├── build_indexes.py
    ├── export_bundle.py
    ├── import_bundle.py
    ├── migrate_records.py
    ├── generate_catalog.py
    └── predeploy.py
```

Do not create every leaf merely because it appears here. Create a semantic folder when it has a real ownership, persistence, implementation, or policy boundary.

---

## 9. Writable deployment-state tree

The installed package MUST remain read-only. Learned intelligence, candidates, runtime data, caches, and installed plugin state belong in a writable deployment root or remote stores.

A local deployment may use:

```text
<LOOP_ENGINE_HOME>/
│
├── README.md
├── deployment.json
│
├── intelligence/
│   ├── context/
│   │   └── learned/
│   ├── code/
│   │   └── learned/
│   ├── previous_run_and_solution/
│   │   └── learned/
│   └── user/
│       └── learned/
│
├── governance/
│   ├── candidates/
│   ├── evaluations/
│   ├── reviews/
│   └── decisions/
│
├── catalog/
│   ├── learned.sqlite
│   ├── materializations.sqlite
│   ├── journal/
│   └── exports/
│
├── files/
│   └── sha256/
│
├── plugins/
│   └── <plugin-id>/
│       └── <plugin-version>/
│
├── runtime/
│   ├── runs/
│   ├── chronicles/
│   ├── checkpoints/
│   ├── artifacts/
│   └── workspaces/
│
└── cache/
    ├── search/
    ├── vectors/
    ├── materialized_code/
    └── generated_views/
```

A server deployment may replace local directories with database schemas, object stores, or remote services while exposing the same logical catalog interfaces.

---

## 10. Storage and authority profiles

Do not assume one persistence architecture fits every deployment. Research, implement, and document multiple profiles behind one contract.

### 10.1 Package-only profile

```text
Authority: Core package JSONL and files
Writable Learned store: none or ephemeral
Use cases: tests, read-only demos, constrained environments
```

### 10.2 Portable-first profile

```text
Authority: append-only portable files or bundles
Indexes: SQLite or derived local index
Use cases: offline work, Git-tracked projects, transfer between systems
```

### 10.3 Local-database profile

```text
Authority: SQLite or embedded database
Files: content-addressed payload store
Exports: portable bundles
Use cases: desktop, single-user, local agents
```

### 10.4 Server-database profile

```text
Authority: transactional SQL or document database
Files: object store
Exports: portable snapshots or bundles
Use cases: teams, hosted service, concurrent writers
```

### 10.5 Event-ledger profile

```text
Authority: append-only event or change ledger
Projections: database and portable files
Use cases: full auditability, complex synchronization, temporal reconstruction
```

### 10.6 Federated catalog profile

```text
Authority: multiple namespaced remote catalogs
Local state: read-through cache and selected mirrors
Use cases: organizations, plugin services, distributed deployments
```

### 10.7 Hybrid profile

```text
Authority: explicitly declared per namespace or record collection
Materializations: files, database rows, object blobs, and remote replicas
Use cases: mixed local/server operation
```

Do not permit accidental dual authority. Every record version MUST have an authority resolution rule.

Possible authority values:

```text
authoritative
primary_replica
read_only_replica
mirror
staging
cache
derived_projection
archive
```

If multiple writable authorities are supported, implement an explicit conflict protocol. Do not rely on timestamps alone.

---

## 11. Universal record envelope

Every reusable artifact MUST use one common envelope with an artifact-specific `spec`.

A recommended starting structure is:

```json
{
  "record_id": "urn:loop-engine:record:...",
  "record_version": "1.0.0",
  "envelope_version": "1.0.0",
  "schema_ref": "schema://core/loop-canvas@1.0.0",
  "artifact_kind": "loop_canvas",
  "intelligence_layer": "code",
  "source_collection": "learned",
  "lifecycle": "active",
  "namespace": "org:example",
  "scope": {
    "deployment_id": null,
    "organization_id": "example",
    "workspace_id": null,
    "project_id": "kaggle-lab",
    "user_id": null,
    "visibility": "organization"
  },
  "display": {
    "name": "Robust Tabular Classification Canvas",
    "summary": "A reviewed solution canvas for noisy tabular classification.",
    "aliases": []
  },
  "spec": {},
  "descriptors": {},
  "attribute_assertion_refs": [],
  "relationships": [],
  "contract_refs": [],
  "file_refs": [],
  "implementation_refs": [],
  "evidence_refs": [],
  "evaluation_refs": [],
  "provenance": {},
  "governance": {},
  "compatibility": {},
  "integrity": {
    "content_hash": "sha256:...",
    "canonicalization": "rfc8785-or-selected-equivalent",
    "signature_refs": []
  },
  "created_at": "...",
  "updated_at": "..."
}
```

### 11.1 Stable envelope versus extensible spec

The envelope contains universal identity, provenance, lifecycle, integrity, and references.

The `spec` contains authoritative fields for the artifact kind.

`descriptors` and attribute assertions characterize the artifact for discovery, ranking, and selection.

Do not place authoritative execution structure only in free-form descriptors.

### 11.2 Unknown fields

Research and define unknown-field behavior for each boundary:

```text
reject
preserve and ignore
preserve and warn
route to extension namespace
accept only in forward-compatible mode
```

Lossless readers SHOULD preserve unknown extension fields even when they cannot interpret them.

### 11.3 Immutable content and mutable membership

Artifact content SHOULD be immutable per record version.

Governance may change catalog membership or lifecycle through append-only events rather than mutating historical bytes.

Examples:

```text
candidate -> approved -> active learned
active -> deprecated
active -> revoked
```

Each transition MUST preserve evidence and decision history.

---

## 12. Artifact-specific ontologies

Implement a typed `spec` for at least these artifact kinds:

```text
loop_definition
loop_canvas
contract
rule
policy
standardization
evaluator
binding
code_unit
plugin_manifest
attribute_definition
relationship_definition
vocabulary_term
store_descriptor
materialization
migration
compatibility_profile
intelligence_portfolio
step_profile
verification_profile
prior_solution
run_pattern
failure_pattern
repair_pattern
```

### 12.1 Loop Definition spec

```text
LoopDefinitionSpec
├── goal template
├── allowed roles
├── default role
├── allowed run modes
├── default run mode
├── input contract refs
├── output contract refs
├── step profile ref
├── budget profile ref
├── stop condition ref
├── permission and effect contract refs
├── implementation bindings
├── child-spawn constraints
├── verification refs
├── fallback refs
├── compatibility requirements
└── parameter schema
```

### 12.2 Loop Canvas spec

```text
LoopCanvasSpec
├── intended root role
├── goal
├── external input contracts
├── external output contracts
├── Loop definition refs
├── local node aliases
├── typed connections
├── dependency relationships
├── routes
├── conditional branches
├── fallbacks
├── verification paths
├── repair paths
├── stop rules
├── parameter bindings
├── output bindings
├── compatibility requirements
└── compilation rules
```

Do not make Solution Canvas a separate runtime. It is a Code Intelligence artifact that compiles into a run tree of ordinary Loops.

### 12.3 Code Unit spec

```text
CodeUnitSpec
├── callable or executable identity
├── language
├── package and module
├── symbol
├── source or artifact ref
├── input contract refs
├── output contract refs
├── effect contract refs
├── resource requirements
├── dependency lock refs
├── isolation requirements
├── supported platforms
├── implementation API version
└── invocation adapter ref
```

### 12.4 Evaluator spec

```text
EvaluatorSpec
├── evaluator type
├── accepted subject kinds
├── input contract
├── output contract
├── expression or code binding
├── deterministic guarantee
├── failure semantics
├── explanation capability
├── resource limits
└── compatibility requirements
```

### 12.5 Binding spec

```text
BindingSpec
├── abstract capability or interface
├── provider
├── protocol
├── endpoint or locator
├── authentication method
├── supported versions
├── supported features
├── required permissions
├── health-check definition
├── timeout and retry behavior
├── rate limits
├── cost model
└── secret references
```

Secrets MUST be referenced, not embedded.

---

## 13. Contract ontology

A Contract is a persistent Code Intelligence artifact. It is not only a JSON Schema reference.

```text
Contract
├── Identity and Version
├── Contract Class
│   ├── Structural
│   ├── Behavioral
│   ├── Effect
│   ├── Resource
│   ├── Quality
│   ├── Compatibility
│   └── Governance
├── Subject and Scope
├── Assertions
├── Enforcement
├── Composition
├── Failure Semantics
├── Evidence
└── Governance
```

### 13.1 Contract families

```text
Structural
├── Input Contract
├── Output Contract
├── Data Contract
├── Port Contract
├── Event Contract
├── Interface Contract
└── Record Contract

Behavioral
├── Precondition
├── Postcondition
├── Invariant
├── Idempotence Contract
├── Determinism Contract
├── Ordering Contract
└── Termination Contract

Effect
├── Filesystem Read
├── Filesystem Write
├── Network Access
├── Secret Access
├── Package Installation
├── External Service Invocation
├── Spending
└── Human Approval

Resource
├── CPU
├── GPU
├── Memory
├── Storage
├── Wall Time
├── Model Calls
├── Concurrency
└── Monetary Budget

Quality
├── Correctness
├── Completeness
├── Freshness
├── Confidence
├── Reproducibility
├── Robustness
├── Stability
└── Acceptance Threshold

Compatibility
├── Engine Compatibility
├── Ontology Compatibility
├── Schema Compatibility
├── Vocabulary Compatibility
├── Plugin Compatibility
├── Store Compatibility
└── Neighbor Port Compatibility
```

### 13.2 Contract composition

Support explicit relationships:

```text
extends
combines
narrows
relaxes
conflicts_with
supersedes
compatible_with
incompatible_with
```

Research whether contract composition should be pure JSON Schema composition, a Loop Engine AST, or a hybrid. Do not force all non-structural contracts into JSON Schema.

### 13.3 Enforcement points

A contract MUST identify where it is enforced:

```text
on registration
on import
on materialization
on Loop instantiation
before execution
during execution
after execution
before persistence
before promotion
before deployment
```

### 13.4 Data contract mapping

Research Open Data Contract Standard and similar data-contract specifications. Implement a mapping or adapter when useful, but do not replace the universal Loop Engine Contract ontology with a data-only contract standard.

---

## 14. Rule ontology

A Rule is a declarative decision artifact. The evaluator is separate.

```text
RuleSpec
├── rule type
├── scope
├── inputs
├── expression or condition AST
├── decision or action
├── priority
├── effective period
├── exceptions
├── missing-value semantics
├── conflict strategy
├── evaluator ref
├── explanation template
├── evidence requirements
└── governance requirements
```

Rule families:

```text
validation
eligibility
selection
ranking
routing
transformation
standardization
permission
budget
stop
escalation
fallback
repair
verification
governance
conflict_resolution
compatibility
migration
```

### 14.1 Rule language research

Evaluate at least:

```text
A small native typed expression AST
Common Expression Language
Open Policy Agent / Rego
Decision Model and Notation / FEEL
JSON Logic or equivalent lightweight formats
Python callables behind strict evaluator contracts
```

Select by use case, not popularity.

Criteria:

```text
safety
portability
determinism
sandboxability
explainability
static typing
version stability
Python support
performance
partial evaluation
testing support
human readability
plugin isolation
```

A likely outcome is one small native rule envelope with one or more evaluator adapters. Do not create independent rule registries per language.

---

## 15. Policy ontology

A Policy is a governed collection of rules and authority metadata.

```text
PolicySpec
├── authority
├── scope
├── rule refs
├── enforcement points
├── exceptions
├── approval requirements
├── conflict policy
├── effective period
├── audit requirements
├── review schedule
└── rollback behavior
```

Examples:

```text
effect approval policy
plugin installation policy
candidate promotion policy
user intelligence consent policy
model spending policy
external network policy
data retention policy
migration policy
compatibility policy
```

Policies SHOULD produce explainable decisions and Chronicle evidence.

---

## 16. Standardization ontology

A Standardization definition is Code Intelligence. Execution occurs through Loops.

```text
StandardizationSpec
├── subject type
├── accepted source variants
├── canonical target contract
├── transformation step refs
├── ordering and dependencies
├── validation steps
├── error handling
├── lossiness classification
├── reversibility
├── idempotence
├── locale
├── time zone
├── units
├── encoding
├── provenance retention
├── confidence rules
└── output contract
```

Standardization operation vocabulary may include:

```text
parse
trim
case_normalize
unicode_normalize
whitespace_normalize
type_coerce
date_normalize
time_zone_normalize
unit_convert
number_normalize
boolean_normalize
enum_map
identifier_normalize
address_normalize
phone_normalize
name_normalize
schema_align
field_rename
field_split
field_merge
redact
deduplicate
entity_resolve
validate
emit_provenance
```

A complex standardization SHOULD be representable as a Loop Canvas.

Store the definition, transformation code, contracts, evidence, and evaluations separately but link them explicitly.

---

## 17. Attribute, vocabulary, and relationship ontology

The system may eventually need thousands of descriptors. Do not add thousands of fixed fields or folders.

### 17.1 Attribute Definition

```text
AttributeDefinition
├── key
├── namespace
├── version
├── display name
├── description
├── value type
├── cardinality
├── unit
├── allowed values
├── taxonomy ref
├── validation rules
├── searchable
├── filterable
├── sortable
├── rankable
├── embeddable
├── inheritable
├── confidence allowed
├── evidence required
├── merge strategy
├── conflict strategy
└── deprecation rules
```

### 17.2 Attribute Assertion

```text
AttributeAssertion
├── subject ref
├── attribute ref
├── value
├── confidence
├── evidence refs
├── provenance
├── scope
├── valid from
├── valid until
└── assertion status
```

Use assertions for observations that change over time or differ by scope. Do not rewrite a large canonical artifact record for every new evaluation.

### 17.3 Namespaces

```text
core.*
learned.*
plugin:<plugin-id>.*
org:<organization-id>.*
project:<project-id>.*
user:<user-id>.*
```

Plugins MUST NOT redefine `core.*` terms.

### 17.4 Relationship Definition

```text
RelationshipDefinition
├── predicate
├── namespace
├── version
├── source kinds
├── target kinds
├── cardinality
├── directionality
├── inverse predicate
├── transitivity
├── symmetry
├── qualifier schema
├── evidence requirements
└── lifecycle rules
```

Core predicates may include:

```text
contains
implements
uses
consumes
produces
validates
verifies
repairs
routes_to
falls_back_to
derived_from
supersedes
extends
narrows
conflicts_with
compatible_with
incompatible_with
evaluated_by
governed_by
approved_by
materialized_as
provided_by_plugin
generated_by_loop
observed_in_run
migrates_to
replaces
mirrors
replicates
```

### 17.5 Semantic-web mappings

Research JSON-LD, SKOS, PROV, and SHACL as interoperability mappings. Do not force the internal runtime to become an RDF engine unless evidence demonstrates a clear benefit.

A pragmatic design may use:

```text
JSON and JSON Schema internally
JSON-LD context for optional semantic export
PROV mapping for provenance
SKOS mapping for taxonomies and vocabulary relationships
SHACL mapping for graph validation and exchange
```

Document any semantic loss in mappings.

---

## 18. Descriptor families

Solutions, nodes, canvases, contracts, plugins, and learned patterns may be described across many dimensions without moving files.

```text
Ontology
Purpose
Applicability
Domains
Industries
Problem Types
Platforms
Input Modalities
Data Characteristics
Methods
Algorithms
Capabilities
Contracts
Resources
Effects and Permissions
Quality
Evidence
Failure Modes
Repair Strategies
Compatibility
Cost
Latency
Security
Privacy
Selection Signals
Provenance
Scope
Governance
Deployment Requirements
Storage Requirements
Observability
Maintenance State
```

Support both embedded descriptors and normalized assertions. The store may choose either representation while the catalog exposes one logical model.

---

## 19. Plugin ontology

A Plugin is a packaging, ownership, trust, namespace, and extension boundary. It is not a fourth Loop role and not a separate runtime.

```text
PluginManifestSpec
├── identity
│   ├── plugin ID
│   ├── version
│   ├── publisher
│   └── namespace
├── distribution
│   ├── portable bundle
│   ├── installed package
│   ├── container
│   ├── remote service
│   └── hybrid
├── compatibility
│   ├── engine versions
│   ├── kernel API versions
│   ├── ontology versions
│   ├── record envelope versions
│   ├── artifact schema versions
│   ├── store protocol versions
│   ├── Python versions
│   └── platform requirements
├── contributions
│   ├── Context Intelligence
│   ├── Code Intelligence
│   ├── Previous Run and Solution Intelligence
│   ├── User Intelligence
│   ├── vocabularies
│   ├── schemas
│   ├── Loop definitions
│   ├── Loop canvases
│   ├── contracts
│   ├── rules
│   ├── policies
│   ├── standardizations
│   ├── evaluators
│   ├── bindings
│   └── interface extensions
├── effects and permissions
├── dependencies
├── integrity
├── migrations
├── activation checks
├── health checks
├── rollback behavior
└── storage locations
```

A plugin MUST NOT:

```text
create a second Loop runtime
redefine constitutional Core terms
shadow a Core or Learned canonical ID
bypass permission enforcement
bypass compatibility checks
write directly into active Learned intelligence
approve its own candidates
silently acquire new effects
silently replace a Core binding
```

### 19.1 Plugin deployment variations

Research and support a clean abstraction across:

```text
Python package entry point
portable directory bundle
signed archive bundle
OCI artifact
containerized worker
WASI or other sandboxed component
remote HTTP service
remote event-driven service
local process with IPC
hybrid metadata bundle plus remote executor
```

Do not require every plugin to support every deployment form.

### 19.2 Plugin isolation

Select isolation based on effects and trust tier:

```text
in-process trusted
subprocess
container
sandboxed component runtime
remote service
read-only metadata-only plugin
```

The handshake MUST disclose the selected isolation mode.

---

## 20. Store and materialization ontology

A logical record is independent of its physical representation.

### 20.1 Store Descriptor

```text
StoreDescriptor
├── store ID
├── backend kind
├── authority role
├── namespace ownership
├── read policy
├── write policy
├── consistency model
├── transaction support
├── query capabilities
├── version support
├── content-addressing support
├── encryption
├── signature verification
├── availability
├── synchronization policy
├── retention policy
├── backup policy
└── locator
```

Backend kinds may include:

```text
package_jsonl
directory_bundle
archive_bundle
sqlite
sql_database
document_database
object_store
content_addressed_store
remote_catalog
plugin_bundle
plugin_service
in_memory
cache
```

### 20.2 Materialization

```text
Materialization
├── logical record ref
├── store ref
├── physical locator
├── representation format
├── content hash
├── media type
├── size
├── compression
├── encryption
├── signature refs
├── created at
├── verified at
├── availability status
└── authority role
```

The same record version may have:

```text
an authoritative PostgreSQL row
an object-store payload
a read-only SQLite replica
a JSONL export
a signed portable bundle record
a plugin-service representation
```

The canonical identity MUST remain unchanged.

### 20.3 Large bodies

Store large payloads outside record envelopes when appropriate:

```text
source code
model files
large prompts
documents
binary artifacts
canvas bodies
benchmark datasets
reports
```

Reference them by stable URI and content hash.

### 20.4 Content addressing

Research canonical JSON and content-addressed storage. Select deterministic canonicalization and hashing rules. At minimum:

```text
canonical bytes are defined
hash algorithm is explicit
hash covers a documented field set
signatures bind to the correct canonical content
mutable lifecycle metadata is excluded or versioned deliberately
```

---

## 21. Unified catalog and store interface

Do not create separate registries for every artifact kind or backend.

Use one logical catalog with typed views.

```text
Catalog
├── get(ref)
├── get_version(ref, version)
├── list_versions(ref)
├── query(filter)
├── search(query)
├── resolve_relationships(ref)
├── resolve_materializations(ref)
├── resolve_compatible(ref, consumer_profile)
├── stage_candidate(record)
├── export_bundle(selection)
├── import_bundle(bundle)
└── explain_resolution(decision)
```

Typed views MAY expose:

```text
catalog.contracts()
catalog.rules()
catalog.loop_definitions()
catalog.loop_canvases()
catalog.standardizations()
catalog.plugins()
```

but they MUST use the same identity, versioning, query, governance, and storage machinery.

### 21.1 Store contract

Every backend MUST implement a common conformance suite.

A possible interface:

```python
class RecordStore(Protocol):
    def capabilities(self) -> StoreCapabilities: ...
    def get(self, ref: RecordRef) -> Record | None: ...
    def put(self, record: Record, *, precondition: WritePrecondition) -> WriteResult: ...
    def query(self, query: CatalogQuery) -> Page[Record]: ...
    def list_versions(self, record_id: str) -> list[VersionInfo]: ...
    def append_event(self, event: GovernanceOrCatalogEvent) -> AppendResult: ...
    def resolve_materialization(self, ref: RecordRef) -> list[Materialization]: ...
    def export(self, selection: ExportSelection) -> BundleRef: ...
    def health(self) -> HealthReport: ...
```

Adjust after research. Keep the public abstraction smaller than any one backend.

### 21.2 Query capability negotiation

A JSONL store, SQLite store, and server database have different query capabilities.

The catalog MUST know whether a backend supports:

```text
exact filters
full text
vector search
relationship traversal
range queries
sorting
aggregation
transactions
compare-and-swap
subscriptions
server-side compatibility filtering
```

The query planner may combine backend filtering with client-side post-filtering, but MUST disclose degraded execution and cost.

---

## 22. Portable bundle standard

Core, Learned snapshots, Candidate submissions, Plugin packages, exports, and backups SHOULD share a common portable envelope.

```text
loop-bundle/
│
├── manifest.json
├── records/
│   ├── part-00000.jsonl
│   └── ...
├── assertions/
│   ├── part-00000.jsonl
│   └── ...
├── relationships/
│   ├── part-00000.jsonl
│   └── ...
├── evaluations/
│   ├── part-00000.jsonl
│   └── ...
├── governance/
│   ├── part-00000.jsonl
│   └── ...
├── migrations/
│   └── ...
├── schemas/
│   └── required extension schemas
├── vocabularies/
│   └── required extension vocabularies
├── files/
│   └── sha256/
│       └── <content-hash>
├── signatures/
│   ├── manifest signature
│   └── verification bundle
└── indexes/
    ├── optional search index
    └── optional vector index
```

Bundle type is metadata:

```text
core_release
learned_snapshot
candidate_submission
plugin_package
project_export
backup
replica_seed
migration_package
```

Indexes are optional and disposable. Authoritative content MUST remain usable without them.

### 22.1 Bundle import rules

A bundle imported from another trust boundary MUST NOT silently become active Learned Intelligence.

```text
External Bundle
    ↓
Integrity Verification
    ↓
Schema and Compatibility Validation
    ↓
Imported Candidate
    ↓
Local Evaluation and Independent Review
    ↓
Local Learned Intelligence
```

Trusted replication within one deployment may preserve lifecycle when policy explicitly permits it.

### 22.2 Distribution research

Evaluate OCI artifacts, signed archives, Python wheels, and plain directories for bundle distribution. Select one or more mappings without coupling logical identity to a distribution mechanism.

---

## 23. Version ontology

Do not collapse all versioning into one `version` field.

At minimum distinguish:

```text
engine_release_version
kernel_api_version
ontology_version
record_envelope_version
artifact_schema_version
vocabulary_version
record_content_version
contract_version
rule_language_version
implementation_api_version
plugin_manifest_version
plugin_package_version
bundle_format_version
store_protocol_version
remote_api_version
Chronicle_event_version
migration_version
serialization_format_version
```

### 23.1 Version semantics

Research and define rules per version dimension.

Possible policies:

```text
Semantic Versioning for public APIs and artifact contracts
PEP 440 for Python distribution dependencies
Date-based versions for immutable data snapshots when appropriate
Monotonic integer revisions for database rows or governance events
Content hashes for immutable payload identity
Schema URIs for schema dialect and version
```

Do not assume SemVer alone solves schema compatibility.

### 23.2 Version ranges

Represent compatible ranges explicitly. Avoid ad hoc string parsing.

Examples:

```text
>=1.2.0,<2.0.0
^1.4.0
exact hash pin
compatible major
compatible feature set
```

Select and document one canonical range grammar per domain.

### 23.3 Immutable versions

Core record versions are immutable.

Learned record versions SHOULD be append-only and immutable after activation.

Plugin contributions are immutable within a plugin version.

Candidates may be revised only by creating a new candidate version or revision with explicit lineage.

### 23.4 Deprecation

Every deprecation MUST define:

```text
deprecated version
replacement ref
reason
first deprecated release
minimum support window
migration path
removal condition
compatibility impact
rollback path
```

---

## 24. Compatibility handshake ontology

Compatibility MUST be computed, not guessed from folder location or one version string.

### 24.1 Handshake participants

Use the same handshake model for:

```text
engine startup
Core bundle loading
Learned store connection
portable bundle import
plugin installation
plugin activation
remote plugin service connection
remote catalog connection
Loop definition resolution
Loop Canvas compilation
migration execution
artifact materialization
```

### 24.2 Handshake request

A recommended shape:

```json
{
  "handshake_version": "1.0.0",
  "request_id": "uuid",
  "consumer": {
    "identity": "loop-engine-deployment",
    "engine_release_version": "...",
    "kernel_api_versions": ["..."],
    "ontology_versions": ["..."],
    "record_envelope_versions": ["..."],
    "artifact_schema_support": {
      "loop_definition": ["..."],
      "loop_canvas": ["..."],
      "contract": ["..."]
    },
    "vocabulary_support": {},
    "serialization_formats": ["json", "jsonl"],
    "store_protocol_versions": ["..."],
    "features": {},
    "effects_allowed": {},
    "resource_limits": {},
    "isolation_modes": [],
    "migration_capabilities": []
  },
  "provider": {},
  "artifact_or_service": {},
  "policy_context": {}
}
```

### 24.3 Handshake response

```json
{
  "verdict": "compatible",
  "selected": {
    "kernel_api_version": "...",
    "ontology_version": "...",
    "record_envelope_version": "...",
    "artifact_schema_versions": {},
    "serialization_format": "json",
    "store_protocol_version": "...",
    "features": {},
    "isolation_mode": "subprocess"
  },
  "required_migrations": [],
  "disabled_optional_features": [],
  "degraded_behavior": [],
  "warnings": [],
  "reasons": [],
  "evidence_refs": [],
  "expires_at": null
}
```

### 24.4 Verdicts

```text
compatible
compatible_with_migration
compatible_with_degradation
compatible_read_only
compatible_export_only
incompatible
unknown
refused_by_policy
```

Unknown MUST fail closed for execution unless policy explicitly permits a safe read-only path.

### 24.5 Handshake checks

Run checks in a clear sequence:

```text
1. Parse and envelope validation
2. Identity and namespace validation
3. Integrity and signature verification
4. Trust and publisher policy
5. Engine and Kernel API compatibility
6. Ontology compatibility
7. Record envelope compatibility
8. Artifact schema compatibility
9. Vocabulary compatibility
10. Required feature negotiation
11. Contract compatibility
12. Effect and permission compatibility
13. Resource compatibility
14. Dependency compatibility
15. Platform and runtime compatibility
16. Store protocol compatibility
17. Migration-path discovery
18. Unknown-field and degradation analysis
19. Policy decision
20. Final verdict and evidence report
```

### 24.6 Compatibility matrix

Generate machine-readable and human-readable matrices for supported combinations.

The matrix MUST distinguish:

```text
read compatibility
write compatibility
execute compatibility
migrate compatibility
export compatibility
import compatibility
rollback compatibility
```

Do not label a pair simply "compatible" when it is only readable but not executable.

---

## 25. Schema evolution and migration ontology

Migration is a first-class Code Intelligence artifact.

```text
MigrationSpec
├── migration ID
├── source schema or version range
├── target schema or version
├── artifact kinds
├── direction
│   ├── upgrade
│   ├── downgrade
│   └── bidirectional
├── transformation implementation ref
├── preconditions
├── postconditions
├── lossiness
├── reversibility
├── idempotence
├── online or offline mode
├── required locks
├── batch behavior
├── resume behavior
├── checkpoint behavior
├── verification refs
├── rollback ref
└── compatibility impact
```

### 25.1 Evolution rules

Research and define policies for:

```text
adding optional fields
adding required fields with defaults
renaming fields
splitting fields
merging fields
changing types
changing enum values
changing semantics without shape changes
removing fields
moving data to assertions
changing relationship direction
changing canonicalization
changing identifier schemes
changing contract behavior
```

### 25.2 Preserve source representations

For imported or migrated records, retain the original raw payload or content hash when policy and storage allow it. This enables audit, reprocessing, and improved future migrations.

### 25.3 Migration graph

Treat migrations as a graph, not a hardcoded linear chain.

```text
v1 -> v2
v1 -> v3
v2 -> v3
v3 -> v2 when reversible
```

The planner must select a valid path based on:

```text
lossiness
risk
cost
number of steps
verified coverage
available implementations
rollback requirements
```

### 25.4 Online migrations

For server deployments, research:

```text
expand-and-contract migrations
shadow reads
shadow writes
backfills
dual-read transitions
write fences
feature flags
compatibility windows
rolling upgrades
```

Do not perform unsafe dual writes without an explicit consistency mechanism.

---

## 26. File and database coexistence

File and database representations are equally valid materializations. They are not separate ontologies.

### 26.1 Supported authority patterns

Research and implement at least the abstractions needed for:

```text
Files authoritative, database derived
Database authoritative, files exported
Append-only ledger authoritative, both files and database projected
Remote catalog authoritative, local cache derived
Namespace-specific authority split
```

### 26.2 Avoid naive dual write

When database and file materializations must update together, evaluate:

```text
transactional outbox
write-ahead journal
unit of work
idempotent replay
compare-and-swap
content-hash preconditions
change feed
checkpointed exporter
```

Do not write to two authorities and hope both succeed.

### 26.3 Synchronization records

Track:

```text
source store
source revision or cursor
target store
target revision
last synchronized hash
last successful synchronization
pending operations
conflicts
retries
verification status
```

### 26.4 Conflict handling

Evaluate:

```text
single-writer authority
optimistic concurrency with ETags or revisions
last-write-wins only for low-risk metadata
three-way merge
field-specific merge strategies
append-only assertion union
manual governance review
CRDTs only where their semantics truly fit
```

Never use silent last-write-wins for contracts, governance decisions, plugin permissions, or executable definitions.

### 26.5 Round-trip guarantees

For every supported portable representation, test:

```text
Database -> Bundle -> Database
JSONL -> Database -> JSONL
Plugin Bundle -> Catalog -> Bundle
Candidate File -> Governance Store -> Candidate File
Learned Store -> Snapshot -> Read-only Replica
```

Verify:

```text
record identity unchanged
record version unchanged
canonical content hash unchanged where representation is canonical
unknown fields preserved
relationships preserved
assertions preserved
evidence preserved
governance history preserved
large file hashes preserved
no unauthorized lifecycle promotion
```

---

## 27. Chronicle and event ontology

The Chronicle is the authoritative ordered runtime history, not persistent intelligence by default.

Research mapping Chronicle events to a standard event envelope such as CloudEvents while preserving Loop-specific semantics.

A Chronicle event should include:

```text
event ID
spec version
event type
source
subject
run ID
Loop ID
parent Loop ID
definition ref
timestamp
sequence or ordering information
causation ID
correlation ID
trace context
payload schema ref
payload
integrity metadata
```

Persistent learning from runs occurs through a separate reviewed promotion flow:

```text
Chronicle population
    ↓
Self-review Practitioner
    ↓
Candidate intelligence
    ↓
Independent review
    ↓
Learned intelligence
```

Integrate OpenTelemetry traces, metrics, and logs without replacing the Chronicle's domain event model.

---

## 28. Standards research program

Research current primary specifications before finalizing implementations. Record exact versions, publication status, normative versus draft status, licenses, conformance tools, and implementation maturity.

Evaluate at least the following families.

### 28.1 Schemas and API descriptions

```text
JSON Schema Draft 2020-12 or current stable dialect
OpenAPI current stable release
AsyncAPI current stable release
Arazzo current stable release
OpenAPI Overlay current stable release
Open Data Contract Standard current stable release
Protocol Buffers, Avro, or equivalent when binary or strongly evolved schemas are needed
```

Possible use:

```text
JSON Schema for record and artifact structural validation
OpenAPI for HTTP interfaces
AsyncAPI for event or message interfaces
Arazzo as an interoperability mapping for API workflows
ODCS as a data-contract mapping
```

Do not let an external workflow standard replace Loop Canvas without evidence and explicit mapping.

### 28.2 Versioning and identifiers

```text
Semantic Versioning
PEP 440 for Python package constraints
RFC 9562 UUIDs
URI and URN conventions
content-addressed identifiers
RFC 8785 JSON Canonicalization Scheme or selected equivalent
JSON Pointer
JSON Patch
JSON Merge Patch
```

### 28.3 Semantic vocabularies and provenance

```text
JSON-LD
W3C PROV
SKOS
SHACL
RDF only where it provides concrete interoperability value
```

### 28.4 Rules and policy

```text
Common Expression Language
Open Policy Agent / Rego
Decision Model and Notation / FEEL
SHACL rules where graph semantics are required
native typed expression AST
```

### 28.5 Events and observability

```text
CloudEvents
OpenTelemetry
W3C Trace Context when applicable
```

### 28.6 Packaging, supply chain, and distribution

```text
SPDX stable specification
CycloneDX stable specification
OCI Image and Distribution specifications
Sigstore bundle and verification model
The Update Framework
SLSA current approved specification
Python packaging metadata and entry points
```

### 28.7 Standard-selection rule

For every candidate standard, document:

```text
problem solved
parts adopted
parts deliberately not adopted
mapping to Loop Engine ontology
version and status
reference implementation maturity
conformance tooling
license
security implications
migration implications
fallback when unavailable
```

Prefer standards-by-reference and adapters over copying large external schemas into the constitutional ontology.

Do not claim full conformance when only a partial mapping exists. Use labels such as:

```text
conformant
profile of
compatible mapping
partial mapping
inspired by
not selected
```

---

## 29. Research, compare, and selection protocol

For every major subsystem, create an option matrix.

Required options to compare include:

```text
Record model: embedded attributes vs normalized assertions vs hybrid
Learned authority: files vs SQLite vs server database vs event ledger
Rules: native AST vs CEL vs Rego vs hybrid
Plugin execution: in-process vs subprocess vs container vs remote
Bundle distribution: directory vs archive vs OCI artifact
Semantic interoperability: plain JSON vs JSON-LD export vs RDF-native
Version resolution: strict exact vs SemVer ranges vs feature negotiation
Migration: eager vs lazy vs read-time adaptation vs materialized upgrade
Catalog: monolithic local vs composite federated
Search: database indexes vs external search vs hybrid
```

Score each option against:

```text
ontology coherence
simplicity
portability
offline support
server scalability
migration safety
backward compatibility
forward compatibility
query performance
write performance
operational complexity
security
sandboxing
debuggability
observability
vendor neutrality
implementation maturity
Python ecosystem fit
plugin extensibility
testability
rollback safety
```

Do not select a complex design merely because it is theoretically general. Prefer progressive capability:

```text
simple local baseline
stable abstraction
optional advanced backend
same logical contract
```

Record decisions as ADRs with status:

```text
proposed
accepted
experimental
superseded
rejected
```

---

## 30. Compatibility and conformance test strategy

### 30.1 Golden fixtures

Maintain small canonical fixtures for every schema version and artifact kind.

### 30.2 Pairwise compatibility tests

Test supported version pairs for:

```text
reader old / writer new
reader new / writer old
Core old / engine new
Core new / engine old
plugin old / engine new
plugin new / engine old
bundle old / importer new
bundle new / importer old
store protocol old / client new
```

### 30.3 Store conformance suite

Run the same tests against:

```text
package JSONL
portable bundle
SQLite
server database
object store
remote catalog mock
plugin store
composite store
```

### 30.4 Property-based tests

Use property-based testing for:

```text
record serialization
canonicalization
round trips
migration idempotence
migration reversibility when claimed
version-range resolution
relationship integrity
unknown-field preservation
conflict resolution
bundle import/export
```

### 30.5 Fuzzing

Fuzz:

```text
manifests
JSONL records
schema references
plugin bundles
handshake messages
migration inputs
rule expressions
file paths
archive extraction
remote responses
```

### 30.6 Failure injection

Inject:

```text
partial writes
process termination
network partitions
stale replicas
corrupt files
invalid signatures
missing migrations
unsupported versions
plugin crashes
timeouts
rate limits
out-of-space conditions
concurrent updates
rollback failures
```

The system must fail visibly and preserve recoverability.

---

## 31. Governance requirements

Self-review is a Core Practitioner Loop definition and canvas.

It may:

```text
review bounded run populations
identify repeated failure or repair patterns
propose new attributes or vocabulary terms
propose contracts, rules, code units, definitions, or canvases
build candidates
run evaluations
stage evidence
```

It MUST NOT:

```text
approve its own candidate
promote directly into Learned
change Core in place
bypass independent policy
hide failed evaluations
```

### 31.1 Governance separation

At minimum distinguish:

```text
producer
reviewer
decision authority
promotion executor
runtime consumer
```

For low-risk local deployments, one human may fill several roles, but the system must still record the conceptual separation.

### 31.2 Promotion transaction

Promotion to Learned must atomically or recoverably establish:

```text
approved record version
Learned catalog membership
governance decision ref
evidence refs
materialization refs
active or staged lifecycle
compatibility status
rollback ref
```

### 31.3 Revocation

Support revocation for compromised plugins, incorrect learned rules, unsafe code units, and invalidated contracts.

Revocation must propagate to resolution and execution decisions without deleting historical evidence.

---

## 32. Security and supply-chain requirements

Research and implement appropriate controls for each trust tier.

### 32.1 Integrity

```text
content hashes
canonicalization
signatures
publisher identity
verification bundles
optional transparency evidence
```

### 32.2 Dependency transparency

Produce or consume an SBOM for Core and plugins. Evaluate SPDX and CycloneDX mappings.

### 32.3 Build provenance

Evaluate SLSA provenance and attestations for releases and plugin packages.

### 32.4 Secure updates

Evaluate TUF-style update metadata for Core and plugin distribution where a remote update channel exists.

### 32.5 Archive safety

Prevent:

```text
path traversal
symlink escape
zip bombs
unexpected executable permissions
case-collision attacks
Unicode path confusion
```

### 32.6 Plugin permissions

Require explicit permissions for:

```text
filesystem read
filesystem write
network
secrets
external APIs
package installation
subprocesses
containers
GPU
spending
user data
Learned candidate creation
```

### 32.7 Execution isolation

Untrusted code MUST NOT execute in the engine process without an explicit trust decision.

### 32.8 Secret handling

Store secret references only. Redact secrets from Chronicle events, reports, errors, bundles, and diagnostics.

---

## 33. Preflight and pre-deploy gates

Create one executable `predeploy` command that runs all required gates and produces a machine-readable and human-readable report.

### 33.1 Architecture gates

```text
one operational Loop runtime
no second role-specific executor
no Core Architecture service kingdom
Runtime Memory separate from persistent intelligence
Candidate separate from active Learned
folders do not encode high-cardinality taxonomy
Core immutable within release
```

### 33.2 Schema and ontology gates

```text
all schemas valid
all Core records validate
all references resolve or are explicitly optional
all namespaces valid
no plugin redefines Core terms
all extension fields namespaced
all required migrations registered
```

### 33.3 Compatibility gates

```text
supported version matrix generated
handshakes pass for supported profiles
unsupported combinations fail clearly
read/write/execute distinctions preserved
no silent degradation
```

### 33.4 Migration gates

```text
upgrade path verified
downgrade path verified when promised
backup created
resume behavior tested
rollback tested
lossiness reported
round-trip fixtures pass
```

### 33.5 Storage gates

```text
store conformance passes
authority rules unambiguous
replicas not treated as authorities
partial-write recovery tested
export/import parity passes
content hashes verified
```

### 33.6 Plugin gates

```text
manifest valid
publisher and signature policy passes
compatibility handshake passes
dependencies resolve
permissions approved
isolation selected
health check passes
activation and rollback tested
SBOM available when required
```

### 33.7 Security gates

```text
secret scan
dependency vulnerability scan
archive safety test
signature verification
permission diff review
unsafe effect review
supply-chain evidence review
```

### 33.8 Quality gates

```text
unit tests
contract tests
property tests
integration tests
end-to-end tests
performance thresholds
recovery tests
documentation validation
```

### 33.9 Deployment decision

Output exactly one:

```text
PASS
PASS_WITH_DOCUMENTED_WARNINGS
BLOCKED
```

A blocked deployment must provide remediation actions.

---

## 34. Documentation as local architecture contracts

Every meaningful semantic folder MUST contain `README.md`.

A folder README should explain:

```text
purpose
ontological identity
parent relationship
allowed contents
prohibited contents
source collection rules
storage authority
version rules
relationships
extension rules
validation requirements
examples
```

Use parent inheritance to avoid duplication.

Machine-readable manifests are authoritative for IDs, versions, dependencies, and registrations.

```text
README.md
└── explains meaning and local rules

manifest.json
└── records machine-readable identity and dependencies

schema
└── defines structural validity

code
└── implements behavior

tests
└── prove conformance
```

Add tests that verify folder paths, README metadata, manifests, schemas, and registrations agree.

Generated documentation must read from canonical architecture data rather than duplicating labels by hand.

---

## 35. API and event interfaces

Research and implement clear public interfaces.

### 35.1 HTTP API

Use an OpenAPI description for externally supported HTTP operations.

At minimum consider:

```text
catalog query
record fetch
bundle import/export
candidate staging
governance review
compatibility handshake
plugin status
migration planning
predeploy reports
```

### 35.2 Event API

Use AsyncAPI or an equivalent description for supported event streams.

Possible event families:

```text
Chronicle events
catalog change events
governance events
plugin lifecycle events
migration events
synchronization events
```

### 35.3 Workflow mapping

Evaluate Arazzo or similar workflow descriptions as an external mapping for API call sequences. Do not make it the internal Loop Canvas ontology unless the mapping is lossless and beneficial.

### 35.4 Error model

Define machine-readable errors with:

```text
stable code
human message
category
retryability
subject refs
compatibility details
contract violations
remediation
causation and trace refs
```

---

## 36. Performance and scale

Design for progressive scale without forcing server complexity on local use.

Test at least:

```text
10 thousand records
1 million records
10 million attribute assertions
large relationship graphs
large Core JSONL shards
concurrent server readers and writers
large plugin catalogs
large prior-run populations
```

Measure:

```text
startup time
Core seed loading
catalog query latency
version resolution latency
handshake latency
bundle import/export throughput
migration throughput
index rebuild time
memory use
cache effectiveness
relationship traversal cost
```

Keep indexes derived and rebuildable.

Avoid loading all learned intelligence into process memory.

Use pagination, streaming JSONL, batched migrations, and lazy materialization.

---

## 37. Implementation phases

Implement in small, reversible phases. Each phase must end with passing tests and a written verification report.

### Phase 0: Baseline and safety

```text
run existing tests
record failures
capture public APIs
inventory persisted formats
back up representative data
identify concurrent changes
create architecture discrepancy report
```

### Phase 1: Architecture decisions

Create ADRs for:

```text
one runtime class
Core / Learned / Plugin source classes
Candidate lifecycle
universal record envelope
folder-versus-metadata boundary
store abstraction
version ontology
handshake model
migration model
plugin trust model
```

### Phase 2: Canonical models and schemas

Implement:

```text
Node and Loop models
record envelope
artifact specs
attribute and relationship models
provenance and evidence
store descriptor and materialization
compatibility handshake
migration record
```

### Phase 3: Unified catalog and package Core store

Implement:

```text
package JSONL Core store
streaming reader
reference resolver
query basics
version resolver
schema validation
Core bundle validation
```

### Phase 4: Learned local store

Implement SQLite or the repository-appropriate local backend behind the same interface.

Support:

```text
records
versions
assertions
relationships
materializations
evidence
governance refs
transactions
optimistic concurrency
exports
```

### Phase 5: Portable bundles

Implement:

```text
bundle manifest
JSONL shards
content-addressed files
import validation
export
round trips
candidate import mode
```

### Phase 6: Compatibility handshakes

Implement handshakes for:

```text
Core loading
Learned store connection
bundle import
plugin installation
Loop definition resolution
```

### Phase 7: Migration framework

Implement:

```text
migration registry
path planning
checkpointed execution
verification
resume
rollback
reporting
```

Migrate at least one real legacy repository format.

### Phase 8: Core Architecture absorption

Move or register reusable Core Architecture behavior as Core Code Intelligence records and ordinary Loop definitions.

Preserve temporary import shims when needed.

### Phase 9: Contracts, rules, and standardizations

Implement the universal artifact records and at least one evaluator path for each.

Use research to select rule and policy adapters.

### Phase 10: Plugin system

Implement:

```text
manifest schema
bundle validation
compatibility handshake
permissions
installation
activation
isolation
upgrade
rollback
removal
```

Build one local plugin and one remote or isolated example.

### Phase 11: Governance and self-review

Implement candidate staging, evaluation, review, decision, promotion, revocation, and rollback.

Run the Core self-review Practitioner through ordinary Loops.

### Phase 12: Server store and federation

Implement or prototype a server database and remote catalog adapter when repository scope permits.

Prove the same logical records and handshakes work across local and server profiles.

### Phase 13: API, events, and observability

Generate and verify API descriptions, event descriptions, Chronicle mappings, and OpenTelemetry integration.

### Phase 14: Predeploy and conformance

Implement the complete gate suite and run it on all supported deployment profiles.

### Phase 15: Simplification and removal

Remove:

```text
duplicate registries
duplicate runtime types
stale Core Architecture imports after deprecation window
semantic folder taxonomies
unverified compatibility guesses
dead migrations
unused adapters
copied documentation that conflicts with manifests
```

---

## 38. Aggressive implementation loop

Repeat this loop until all gates pass:

```text
1. Observe
   ├── inspect code, data, tests, docs, and actual behavior
   └── identify the highest-risk incoherence

2. Research
   ├── find relevant primary standards
   ├── inspect mature reference implementations
   └── identify current stable versions and draft risks

3. Generate alternatives
   ├── smallest workable design
   ├── portable design
   ├── server-scalable design
   └── plugin-extensible design

4. Compare
   ├── score explicit criteria
   ├── identify irreversible decisions
   └── identify migration burden

5. Select
   ├── record ADR
   ├── define contracts
   └── define measurable success gates

6. Implement a vertical slice
   ├── model
   ├── schema
   ├── store
   ├── runtime path
   ├── CLI or API path
   ├── docs
   └── tests

7. Verify
   ├── normal behavior
   ├── compatibility
   ├── migration
   ├── failure
   ├── recovery
   ├── rollback
   └── performance

8. Simplify
   ├── remove duplicate abstractions
   ├── reduce folder depth
   ├── reduce configuration
   └── preserve explicit metadata

9. Integrate
   ├── update manifests
   ├── update generated views
   ├── update README contracts
   └── run predeploy

10. Reassess
    └── ask whether this is still the smallest coherent design
```

Do not stop after creating interfaces with no implementation or tests.

---

## 39. Required end-to-end demonstrations

Build automated demonstrations that prove the architecture.

### 39.1 Core seed to runtime

```text
load Core JSONL record
resolve Loop definition
run compatibility handshake
instantiate Loop
execute implementation binding
emit Chronicle events
return typed result
```

### 39.2 Learned candidate promotion

```text
self-review Practitioner creates candidate
candidate stored as portable file or database record
evaluations run
independent review approves
promotion creates Learned membership
resolver selects Learned record
old version remains reproducible
```

### 39.3 File/database round trip

```text
create Learned records in SQLite or server DB
export portable bundle
import into clean deployment
verify hashes, refs, relationships, and governance
query equivalent results
```

### 39.4 Plugin compatibility

```text
inspect signed plugin manifest
run handshake
refuse one incompatible version
install one compatible version
approve effects
activate in selected isolation
execute plugin-provided Loop definition
rollback plugin
```

### 39.5 Migration

```text
load legacy record
plan migration path
execute checkpointed migration
validate target
simulate interruption
resume
simulate post-deploy failure
rollback or restore
```

### 39.6 Mixed materializations

```text
resolve one logical record from database authority
materialize large file from object store
use local read-only cache
export portable JSONL
prove identity remains one
```

### 39.7 Compatibility degradation

```text
consumer lacks one optional feature
handshake returns compatible_with_degradation
feature is disabled explicitly
Chronicle records the degradation
required features still fail closed
```

### 39.8 Contract, rule, and standardization

```text
validate structural contract
evaluate permission policy
execute standardization canvas
verify idempotence
produce evidence and typed output
```

---

## 40. Architecture rejection gates

The implementation fails if it does any of the following:

```text
creates a second operational runtime type
uses separate Practitioner, Intelligence, or Solution executors
uses Root or Child as persistent subclasses
creates Core Architecture as a parallel service kingdom
places active Learned intelligence inside the installed package
uses folder location as the only semantic classification
creates deep folders for named learned solutions
uses one ambiguous version field for every compatibility dimension
loads unsupported versions without a handshake
silently drops unknown fields during a claimed lossless round trip
silently promotes imported intelligence to Learned
allows plugins to redefine Core terms
allows plugins or self-review to approve their own candidates
uses naive dual writes to files and database authorities
uses a cache as an authority without declaration
mutates Core records in place
mutates active Learned versions in place
executes untrusted plugin code in-process without a trust decision
claims standard conformance without evidence
claims migration reversibility without a rollback test
merges Runtime Memory into persistent intelligence
turns files, schemas, or services into fake operational nodes
stores secrets in records, bundles, or Chronicle events
continues deployment after a blocked predeploy gate
```

---

## 41. Required automated tests

At minimum create or update tests for:

```text
one-runtime invariant
Loop dimension independence
four intelligence layers
Core immutability
Learned governance
plugin namespacing
record envelope validation
artifact spec validation
attribute registry
relationship registry
contract composition
rule evaluation
standardization idempotence
store conformance
JSONL streaming
SQLite transactions
server-store adapter
composite catalog resolution
version-range handling
compatibility handshakes
migration planning
migration resume
migration rollback
unknown-field preservation
bundle import/export
content hashes
signature verification
archive safety
plugin activation and rollback
Runtime Memory separation
Chronicle ordering
predeploy gates
folder README contracts
generated documentation consistency
```

Add tests that deliberately attempt prohibited behavior.

---

## 42. Deliverables

Produce working code and these artifacts:

```text
1. Current-state architecture evidence report
2. Target architecture document
3. ADR set with selected and rejected options
4. Full repository tree after implementation
5. Universal record-envelope schema
6. Artifact-specific schemas
7. Core vocabulary seed records
8. Core intelligence bundle manifests
9. Unified catalog and store interfaces
10. Package JSONL store
11. Learned local store
12. Portable bundle implementation
13. Compatibility handshake implementation
14. Version compatibility matrix
15. Migration registry and at least one real migration
16. Contract, rule, policy, and standardization implementations
17. Plugin manifest, installer, handshake, isolation, and rollback
18. Governance and candidate promotion flow
19. Predeploy command and reports
20. Store conformance suite
21. End-to-end demonstrations
22. Generated architecture and catalog views
23. Updated README files and developer guides
24. Security and supply-chain report
25. Performance benchmark report
26. Remaining-risk and deferred-work register
```

Every deliverable must link to actual repository paths.

---

## 43. Final verification checklist

Before handoff, verify all of the following:

```text
[ ] The existing test suite passes or every remaining failure is documented.
[ ] New architecture tests pass.
[ ] Exactly one operational Loop implementation exists.
[ ] Core, Learned, and Plugin records use the same envelope.
[ ] Candidate remains a lifecycle state outside active Learned.
[ ] Core JSONL records load from a clean installation.
[ ] Learned records work in at least one writable store.
[ ] Portable export and import round-trip successfully.
[ ] Unknown extension fields survive lossless paths.
[ ] Compatibility handshakes produce explicit evidence.
[ ] Incompatible versions fail clearly.
[ ] Migrations are resumable and verified.
[ ] Rollback is tested.
[ ] File/database authority is unambiguous.
[ ] No naive dual-write path remains.
[ ] Plugins are namespaced, permissioned, and version-checked.
[ ] Plugin rollback works.
[ ] Self-review cannot approve its own candidate.
[ ] Revoked artifacts are no longer selected for new execution.
[ ] Runtime Memory is separate from persistent intelligence.
[ ] Chronicle events are ordered and traceable.
[ ] Predeploy blocks unsafe deployment.
[ ] Core is immutable within release.
[ ] Generated indexes are disposable and rebuildable.
[ ] Folder READMEs, manifests, schemas, code, and tests agree.
[ ] No large learned taxonomy is encoded as folder depth.
[ ] Performance is measured at realistic catalog sizes.
[ ] Security, signatures, supply-chain metadata, and secret handling are verified.
[ ] The complete system works from a clean checkout and clean deployment root.
```

---

## 44. Final handoff format

Return:

1. a concise statement of what was implemented;
2. clickable paths to every major deliverable;
3. the final repository tree;
4. the exact commands for tests, conformance, migration, examples, and predeploy;
5. the selected standards and exact versions;
6. the standards considered but rejected, with reasons;
7. the supported deployment and storage profiles;
8. the compatibility matrix;
9. migration and rollback results;
10. bundle round-trip results;
11. plugin install, activation, execution, and rollback results;
12. benchmark results;
13. security and supply-chain verification results;
14. architecture disagreements found in the original repository;
15. compatibility shims still present and their removal conditions;
16. incomplete items, blocked items, and remaining risks.

Do not claim completion unless the required checks have actually run.

---

## 45. Final architectural rule

```text
The constitutional ontology defines the grammar.

Core, Learned, and Plugin collections provide reusable intelligence
without changing the grammar.

Candidate is a governed lifecycle state.

Contracts, rules, policies, standardizations, plugins, Loop definitions,
Loop canvases, vocabularies, migrations, and compatibility profiles are
typed catalog records.

Folders express stable architectural ownership and storage boundaries.

Attributes, relationships, evidence, and indexes express the many ways
solutions, nodes, and intelligence can be described.

A record's identity does not depend on whether it is stored in JSONL,
SQLite, PostgreSQL, an object store, a plugin bundle, or a remote service.

Storage changes materialization.

Governance changes lifecycle and catalog membership.

Version handshakes determine whether records, plugins, stores, and runtimes
can read, write, migrate, or execute together.

When any artifact performs work, it executes as the same ordinary Loop.

The Kernel only makes Loop execution possible.
```
