# Loop Engine Current Architecture Map

This document describes the current implemented architecture: file
layout, database architecture, query paths, access paths, and runtime
paths. It is generated from the live repository and must be updated
when the tree changes. The authoritative machine-readable rules live in
`architecture.yaml`, `terminology.yaml`, and
`src/loop_engine/architecture_map.py`.

## 1. Repository layout

```text
loop-engine/
│
├── README.md
├── AGENTS.md
├── architecture.yaml          machine-readable invariants
├── terminology.yaml           canonical terms and forbidden names
├── pyproject.toml
│
├── src/
│   └── loop_engine/           the production package
│       ├── loop/              canonical Loop runtime and definitions
│       ├── ontology/          CatalogRecord, LoopDefinitionRecord,
│       │                      unified catalog
│       ├── catalog/           backend-neutral store adapters
│       │   └── stores/        package_jsonl, duckdb_files, duckdb_store,
│       │                      sqlite_store, in_memory
│       ├── core/              Core Architecture capability groups and
│       │                      internal runtime mechanics
│       ├── code_nodes/        solution graphs, canvases, reports,
│       │                      benchmarks, examples
│       ├── strings/           context, question, and template records
│       ├── intelligence/      four persistent layers at rest
│       │   ├── context/core/records/part-00000.jsonl
│       │   ├── code/core/
│       │   ├── runtime_history_solution/core/
│       │   └── user_feedback/
│       ├── governance/        candidates, review, approval, promotion
│       ├── runtime/           runs, runtime_memory, artifacts
│       ├── kernel/            loader, resolver, executor, enforcement
│       ├── node/              Node ontology namespace
│       │   └── loop_node/     passive compatibility-record namespace
│       ├── data/              benchmark evidence
│       └── evidence/          saved run evidence
│
├── devtools/                  Development Assurance Plane
│   └── src/loop_engine_devtools/
│       ├── bootstrap.py       no-import verifier
│       ├── assurance/         Repository Assurance Practitioner
│       ├── intelligence/core/ devtools Core records
│       └── cli.py             loop-dev command
│
├── docs/
│   ├── architecture/          CONSTITUTION.md and architecture docs
│   ├── prompts/               implementation mandates
│   ├── components/            component guides
│   └── contracts/             contract index
│
├── tests/                     test suite
├── examples/                  runnable examples
├── benchmarks/                benchmark populations
└── .loop-engine-dev/          generated devtools state (gitignored)
```

## 2. Package architecture

```text
src/loop_engine/
│
├── loop/                      the canonical Loop runtime
│   ├── recursive_loop.py      Loop, LoopConfig, LoopLedger, LoopResult
│   ├── loop_definition.py     LoopDefinition, LoopDefinitionRef,
│   │                          LoopStartRequest
│   ├── loop_contract.py       LoopContract, typed ports
│   ├── loop_role.py           LoopRole, LoopRelationship
│   ├── loop_control.py        loop and exit conditions
│   ├── loop_profile_catalog.py  registered role profiles
│   ├── loop_profile_ontology.py profile resolution
│   ├── runtime_context.py     LoopRuntimeContext, three public ports
│   ├── kernel.py              Practitioner kernel, ProblemSpec,
│   │                          KernelRunRequest, run_kernel_passes
│   ├── kernel_runtime.py      kernel-to-Loop operational boundary
│   ├── delegation_runtime.py  SpawnedTaskManager, Spawned Loops
│   ├── spawned_practitioner.py typed Spawned Practitioner entry point
│   ├── spawned_task_checkpoint.py durable task checkpoints
│   ├── spawned_task_state_store.py local JSONL task state
│   ├── spawned_workspace_executor.py workspace command execution
│   ├── effect_approval.py     EffectApprovalService, one-use approvals
│   ├── approval_state_store.py durable approval state
│   ├── capability_loops.py    capability invocation Loops
│   ├── intelligence_loops.py  IntelligenceItemEnvelope, serve paths
│   ├── loop_capsule.py        LoopRef, LoopCapsule
│   ├── canvas.py              Canvas, SolutionSlot, candidates
│   ├── encapsulate.py         as_practitioner_loop
│   ├── loop_templates.py      TEMPLATE_LIBRARY presets
│   ├── lens.py                role and method lenses
│   ├── loop_doctrine.py       baseline doctrine
│   └── service_loop_envelope.py ServiceLoopSpec
│
├── ontology/                  closed foundational vocabulary
│   ├── node.py                CatalogRecord, ObjectIdentity
│   ├── loop_node.py           exact legacy record migration reader
│   ├── artifacts.py           closed vocabularies
│   ├── folders.py             FOLDER_ONTOLOGY, semantic folder table
│   ├── catalog.py             UnifiedCatalog over three physical roots
│   ├── ontology_checks.py     structural validation
│   └── index.json             generated catalog index
│
├── catalog/                   backend-neutral store adapters
│   ├── protocol.py            CatalogStore protocol
│   ├── capabilities.py        StoreCapabilities
│   ├── handshake.py           StoreHandshake, negotiate
│   ├── query.py               IntelligenceQuery
│   ├── registry.py            AdapterRegistry, swappable backends
│   ├── composite.py           CompositeCatalog
│   ├── conformance.py         run_store_conformance
│   └── stores/
│       ├── package_jsonl.py   PackageJsonlStore (read-only Core)
│       ├── duckdb_files.py    DuckDBFileQueryEngine (SQL over files)
│       ├── duckdb_store.py    DuckDBRecordStore (writable)
│       ├── sqlite_store.py    SQLiteRecordStore (writable)
│       └── in_memory.py       EphemeralRecordStore (reference)
│
├── core/                      Core Architecture
│   ├── boundary_registry.py   operational boundary ontology
│   ├── intelligence_layers.py four layers, layer_handshake
│   ├── retrieval.py           Retrieval Engine
│   ├── capability_directory.py capability handshakes
│   ├── brave_search.py        Web Research
│   ├── run_history.py         RunHistory, saved runs
│   ├── runtime_memory.py      Runtime Memory
│   ├── context_artifacts.py   content-addressed artifacts
│   ├── model_gateway.py       model invocation gateway
│   ├── model_routes.py        provider routes
│   ├── provider_failover.py   failover policy
│   ├── workspace_operations.py confined workspaces
│   ├── mcp_adapter.py         MCP tools
│   ├── skill_registry.py      candidate-only skills
│   ├── otel_export.py         OpenTelemetry projection
│   ├── studio_server.py       playback interface
│   └── ...                    remaining internal mechanics
│
├── code_nodes/                solution and reporting code
│   ├── solution_graph.py      LoopGraphDefinition, vertices, edges
│   ├── solution_canvas.py     SolutionSpec, canvas projection
│   ├── solution_compiler.py  canvas compilation
│   ├── solution_records.py   SolutionRecord
│   ├── loop_report.py        run reports
│   ├── run_analytics.py      relationship projection
│   ├── run_playback.py       playback data
│   ├── self_improvement_loop.py self-improvement Practitioner
│   ├── campaign_runner.py    benchmark campaigns
│   └── ...                   examples, benchmarks, seeds
│
├── strings/                   context and template records
│   ├── knowledge.py          Knowledge, AskFrame
│   ├── context.py            CONTEXT_POLICIES, build_view
│   ├── question_engine.py    question forms
│   ├── intelligence_strings.py string intelligence
│   └── ...                   templates, notes, packs
│
├── intelligence/              four layers at rest
│   ├── context/core/         seed corpus (1000 records)
│   ├── code/core/            provenance pointers
│   ├── runtime_history_solution/core/ run history pointers
│   └── user_feedback/        user feedback layer
│
├── governance/                candidate lifecycle
│   ├── candidates/           staged candidates
│   ├── review/               independent review
│   ├── approval/             durable decisions
│   └── promotion/            explicit promotion
│
├── runtime/                   per-run state at rest
│   ├── runs/                 saved runs
│   ├── runtime_memory/       Runtime Memory scope rules
│   └── artifacts/            offloaded artifacts
│
├── kernel/                    kernel concerns documented at rest
│   ├── loader/               record and payload loading
│   ├── resolver/             reference resolution
│   ├── executor/             the one Loop executor
│   └── enforcement/          approvals, boundaries, workspaces
│
└── node/                      Node ontology namespace
    └── loop_node/            passive compatibility-record namespace
```

## 3. Database architecture

```text
Storage authority model
│
├── Core (package-shipped, read-only)
│   ├── intelligence/context/core/records/part-00000.jsonl
│   │   └── 1000 seed records, manifest-pinned digest
│   ├── intelligence/code/core/manifest.yaml
│   │   └── code_ref provenance pointers
│   └── intelligence/runtime_history_solution/core/manifest.yaml
│
├── Catalog store adapters (one protocol, many backends)
│   ├── PackageJsonlStore        read-only streaming over Core JSONL
│   ├── DuckDBFileQueryEngine    SQL over JSONL/Parquet files
│   ├── DuckDBRecordStore        writable embedded authority
│   ├── SQLiteRecordStore        writable embedded authority
│   ├── EphemeralRecordStore     in-memory reference
│   └── (planned) relational, object store, remote catalog
│
├── Instance state (outside the installed package)
│   └── ~/.loop-engine/
│       ├── intelligence/        learned records
│       ├── runs/                saved run history
│       └── candidates/          staged candidates
│
└── Devtools state (generated, gitignored)
    └── .loop-engine-dev/
        ├── repository_graph.duckdb
        ├── assurance/           findings, evidence, snapshots
        └── caches/
```

Authority rules:

- One authority per record version. Adapters declare their authority
  role in their capability handshake.
- Derived indexes (Parquet mirrors, DuckDB caches) are disposable and
  rebuildable. They are never the authority.
- No naive dual writes. Replication goes through an outbox or journal
  with idempotent replay and hash verification.
- Record identity never depends on the backend. The same logical
  record may be materialized as JSONL, DuckDB row, SQLite row, or a
  portable bundle.

## 4. Query paths

```text
IntelligenceQuery (typed, backend-neutral)
        ↓
CatalogStore.query / stream
        ↓
Adapter-specific execution
│
├── PackageJsonlStore
│   └── streaming line-by-line filter (client-side predicates)
│
├── DuckDBFileQueryEngine
│   └── read_json_auto over shards, parameterized SQL,
│       pushdown for layer/source/kind/lifecycle filters
│
├── DuckDBRecordStore / SQLiteRecordStore
│   └── parameterized SQL over records table,
│       JSON attributes and payload columns
│
├── EphemeralRecordStore
│   └── in-memory predicate evaluation
│
└── CompositeCatalog
    └── ordered store fan-out, dedupe by (record_id, record_version)
```

Query semantics:

- `IntelligenceQuery` carries layers, source_collections,
  artifact_kinds, lifecycle, namespaces, attribute predicates, limit,
  and offset.
- SQL is an execution language, not the ontology. Raw SQL is a
  privileged escape hatch only.
- Every adapter declares its real capabilities in a handshake before
  use. Unsupported operations raise `UnsupportedOperationError`.
- Golden queries must return equivalent normalized records across
  backends.

## 5. Access paths

```text
LoopStartRequest
        ↓
Loop (canonical runtime, refuses subclassing)
        ↓
LoopRuntimeContext
│
├── IntelligenceSearchRetrievalPort
│   └── four layers via layer_handshake, LoopRef results
├── WebResearchPort
│   └── Brave Search adapter
├── CustomPluginsPort
│   └── capability directory handshakes
└── InternalRuntimeMechanics
    ├── providers and model gateway
    ├── workspaces and effect approvals
    ├── stores and context artifacts
    ├── Runtime Memory
    ├── Run History and event log
    └── reports, playback, trace export
```

Access rules:

- Discovery is effect-free. Execution requires explicit typed
  authority.
- Approvals bind one exact effect, arguments digest, target,
  operation, and request identity. One-use consumption.
- Workspaces are path-confined. Traversal, symlink escape, and unsafe
  overwrite are refused.
- A Spawned Loop receives only its typed inputs and explicitly selected
  references. No parent goal, private history, sibling context, or
  shared ledger.
- Mode never grants file, network, secret, model, spending, or
  external-effect permission.

## 6. Runtime paths

```text
Task
        ↓
Starting Practitioner Loop
│
├── queries Intelligence Query Loop (deterministic)
│   └── retrieves Intelligence Item Loops from all four layers
│
├── may spawn Candidate Practitioner A (non-deterministic)
│   ├── Code Intelligence selection (deterministic)
│   └── Code execution (deterministic)
│
├── may spawn Candidate Practitioner B
├── may spawn a Synthesis Practitioner
├── may spawn a Verifier (deterministic)
│   └── may spawn a Repair Practitioner after failure
│
└── builds a compiled Solution Canvas
    └── Starting Solution Loop
        ├── Connected Solution Loop: validate input
        ├── Connected Solution Loop: transform
        ├── Connected Solution Loop: execute
        ├── Connected Solution Loop: verify
        ├── dynamic fallback → Spawned Solution Loop
        └── Connected Solution Loop: format output
```

Kernel boundary:

```text
Kernel (the only non-dogfooded substrate)
├── load definitions
├── resolve references
├── instantiate Loops
├── execute one Loop
├── enforce hard contracts, permissions, budgets, stop conditions
└── append Run History events atomically
```

Practitioner kernel:

```text
run_kernel_passes(KernelRunRequest)
        ↓
execute_kernel_run (kernel_runtime)
        ↓
canonical Loop with exact definition, relationship, context
        ↓
nine-node pass calculator (orient, reconcile_horizon,
assess_prepare, decide_next, how, act, verify,
integrate_commit, route)
```

## 7. Devtools architecture

```text
devtools/src/loop_engine_devtools/
│
├── bootstrap.py
│   └── runs without importing Loop Engine:
│       syntax, node classes, forbidden paths, import direction
│
├── assurance/
│   └── run_repository_assurance()
│       └── runs through the canonical Loop kernel
│           ├── repository conformance (files, symbols, imports,
│           │   references)
│           ├── structure checks (folders, READMEs, junk drawers)
│           ├── architecture contract (forbidden classes, paths,
│           │   canonical runtime)
│           └── backend isolation (provider leaks, base imports)
│
├── intelligence/core/records/part-00000.jsonl
│   └── devtools review presets and rules
│
└── cli.py
    ├── loop-dev --bootstrap
    └── loop-dev --assurance [--scope ...] [--strict]
```

Dependency direction: `loop_engine_devtools` imports `loop_engine`.
`loop_engine` never imports `loop_engine_devtools`.

## 8. Conformance commands

```bash
# Full self-test suite (canonical runtime, adapters, conformance)
PYTHONPATH=src python3 -m loop_engine --self-test

# Zero-tolerance conformance gates
PYTHONPATH=src python3 -m loop_engine --conformance

# Architecture map
PYTHONPATH=src python3 -m loop_engine --map

# Repository structure report
PYTHONPATH=src python3 -m loop_engine --structure
PYTHONPATH=src python3 -m loop_engine --structure-json

# Repository conformance harness (files, symbols, imports, references)
PYTHONPATH=src python3 -m loop_engine --repo-conformance

# Machine-readable architecture contract
PYTHONPATH=src python3 -m loop_engine --architecture-contract

# Devtools bootstrap (no Loop Engine import)
PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli --bootstrap

# Repository Assurance Practitioner (canonical Loop kernel)
PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli --assurance
```

## 9. Memory types

The field has converged on four cognitive memory types that map
directly to how human memory works. Loop Engine standardizes them as
classification labels served in every layer handshake, plus a fifth
type for human feedback.

```text
Memory type    Loop Engine component
├── working    Runtime Memory (RunNoteBoard)
│              temporary, run-scoped, discarded unless promoted
├── procedural Code Intelligence
│              how-to knowledge: runnable, repeatable work
├── semantic   Context Intelligence
│              facts and concepts: questions, methods, templates
├── episodic   Runtime History and Solution Intelligence
│              what happened: runs, decisions, failures, repairs
└── social     User Feedback Intelligence
               human advice; guidance, never truth
```

The vocabulary lives in `core/intelligence_layers.py`:

```text
MEMORY_TYPES = (working, procedural, semantic, episodic, social)
LAYER_MEMORY_TYPE = {
    context_intelligence: semantic
    code_intelligence: procedural
    runtime_history_solution_intelligence: episodic
    user_feedback_intelligence: social
}
RUNTIME_MEMORY_TYPE = working
```

`layer_handshake()` serves `memory_type` on every layer, the full
`memory_types` vocabulary with meanings, and `memory_type: working` on
the runtime-memory entry. These are classification labels, not new
layers and not new runtimes.

## 10. Current invariants

```text
LE-NODE-001  Loop is the sole concrete operational runtime and graph vertex
LE-NODE-002  No concrete generic Node class
LE-NODE-003  Roles are fields, not subclasses
LE-NODE-004  Run modes are fields, not subclasses
LE-NODE-005  Common behaviors use versioned Loop profiles
LE-NODE-006  Contained typed objects are not Nodes
LE-NODE-007  Governed steps run as Loops Spawned by their parent
LE-NODE-008  Ungoverned implementation primitives stay inside their owning Loop
LE-NODE-009  Presets are data, not subclasses
LE-CONFIG-001 Minimum resolved configuration exists before start
LE-CONFIG-002 No recursive configuration bootstrap
LE-INTEL-001  Functional domains are non-exclusive
LE-INTEL-002  No step name or path grants intelligence access
LE-INTEL-003  Access policy is separate from preferences
LE-PERM-001   Descendants narrow, never broaden
LE-DOC-001    Prose is non-executable
LE-TRUST-001  Retrieved text stays data
LE-VERSION-001 Resolved plans pin exact versions and hashes
LE-RUNTIME-001 Runtime Memory, Run History, records stay distinct
LE-PLUGIN-001 Plugins cannot define Node types
LE-GOV-001    No self-approval
```

See `docs/architecture/CONSTITUTION.md` for the full normative text and
`architecture.yaml` for the machine-readable form.
