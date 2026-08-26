# Loop Engine cleanup and intelligence access implementation

Paste this prompt into a new Codex, Claude Code, or OpenCode session rooted at
`/home/username/loop-engine`.

## 0. Mandate

You are explicitly authorized and required to delete, rename, move, rewrite,
and regenerate repository content. The current tree still contains:

1. a legacy decision-spine cluster that predates the canonical Loop runtime;
2. a misnamed `core` package that must become `core`;
3. no intelligence access adapter layer for querying files and databases
   through one contract.

Fix all three in this session. Do not stop at a plan. Do not preserve legacy
code because it exists. Do not leave a rename half done. Every phase below ends
with green verification gates. A phase is not complete until its gates pass.

## 1. Hard rules

1. One operational runtime: `Loop` in `src/loop_engine/loop/recursive_loop.py`.
   Nothing else executes work. `Node` and `LoopNode` in
   `src/loop_engine/ontology/` are at-rest catalog records, not runtimes.
2. Preserve uncommitted user work. Run `git status --short` first. Do not
   discard, restore, or reformat changes you did not make.
3. Use the import-graph evidence script in section 2 before deleting any
   module. Deletion decisions come from evidence, not guesses.
4. Update every registry, map, and document in the same change as the code it
   describes. The architecture map, forbidden paths, boundary registry,
   self-test list, conformance report, and docs must agree with the tree.
5. Do not commit or push unless explicitly instructed.

## 2. Evidence tool: import graph

Save this script as `/tmp/opencode/import_graph.py` and run it before and
after every deletion phase. It prints every module that no canonical entry
point can reach.

```python
import ast, os
ROOT = "src/loop_engine"
mods = {}
for dirpath, _, files in os.walk(ROOT):
    if "__pycache__" in dirpath: continue
    for f in files:
        if not f.endswith(".py"): continue
        path = os.path.join(dirpath, f)
        rel = os.path.relpath(path, ROOT)[:-3].replace(os.sep, ".")
        if rel.endswith(".__init__"): rel = rel[:-9]
        full = "loop_engine." + rel
        try:
            tree = ast.parse(open(path).read())
        except Exception:
            continue
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.level and node.level > 0:
                    parts = full.split(".")
                    base = parts[:-node.level]
                    target = ".".join(base + ([node.module] if node.module else []))
                    imports.add(target)
                elif node.module.startswith("loop_engine"):
                    imports.add(node.module)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith("loop_engine"):
                        imports.add(a.name)
        mods[full] = imports

seeds = [
    "loop_engine.__main__", "loop_engine.__init__", "loop_engine._self_test",
    "loop_engine._conformance_test", "loop_engine._conformance_scan",
    "loop_engine.architecture_map", "loop_engine.conformance_report",
    "loop_engine.nomenclature_conformance", "loop_engine.public_runtime_conformance",
    "loop_engine.loop.recursive_loop", "loop_engine.loop.kernel_runtime",
    "loop_engine.loop.delegation_runtime", "loop_engine.loop.capability_loops",
    "loop_engine.loop.intelligence_loops", "loop_engine.loop.effect_approval",
    "loop_engine.loop.canvas", "loop_engine.loop.loop_capsule",
    "loop_engine.code_nodes.solution_graph", "loop_engine.code_nodes.solution_canvas",
    "loop_engine.code_nodes.solution_compiler", "loop_engine.code_nodes.self_improvement_loop",
    "loop_engine.code_nodes.campaign_runner", "loop_engine.code_nodes.context_seed",
    "loop_engine.code_nodes.run_analytics", "loop_engine.code_nodes.run_playback",
    "loop_engine.code_nodes.loop_report", "loop_engine.code_nodes.public_examples",
    "loop_engine.code_nodes.guided_setup", "loop_engine.code_nodes.smoke_ladder",
    "loop_engine.code_nodes.complex_task_benchmark", "loop_engine.code_nodes.complex_task_native_evidence",
    "loop_engine.code_nodes.complex_task_published_evidence", "loop_engine.code_nodes.live_run_demo",
    "loop_engine.code_nodes.kaggle_executor", "loop_engine.code_nodes.self_improve",
    "loop_engine.code_nodes.review_mode", "loop_engine.code_nodes.learning_bundle",
    "loop_engine.code_nodes.change_proposals", "loop_engine.code_nodes.foundry_probes",
    "loop_engine.code_nodes.guidance_ledger", "loop_engine.code_nodes.string_foundry",
    "loop_engine.code_nodes.pack_curation", "loop_engine.code_nodes.enrichment",
    "loop_engine.code_nodes.closure", "loop_engine.code_nodes.planning",
    "loop_engine.code_nodes.blueprint", "loop_engine.code_nodes.capture",
    "loop_engine.code_nodes.failure_response", "loop_engine.code_nodes.follow_up",
    "loop_engine.code_nodes.housekeeping", "loop_engine.code_nodes.measurement",
    "loop_engine.code_nodes.logic_ast", "loop_engine.code_nodes.rl_vocabulary",
    "loop_engine.code_nodes.runtime_contracts", "loop_engine.code_nodes.run_quality",
    "loop_engine.code_nodes.solution_records", "loop_engine.code_nodes.solution_graph_builder",
    "loop_engine.code_nodes.solution_graph_validation", "loop_engine.code_nodes.solution_graph_checks",
    "loop_engine.code_nodes.solution_canvas_checks", "loop_engine.code_nodes.competition_solver",
    "loop_engine.code_nodes.universal_solve",
    "loop_engine.core.boundary_registry", "loop_engine.core.intelligence_layers",
    "loop_engine.core.retrieval", "loop_engine.core.capability_directory",
    "loop_engine.core.brave_search", "loop_engine.core.run_history",
    "loop_engine.core.runtime_memory", "loop_engine.core.context_artifacts",
    "loop_engine.core.context_catalog", "loop_engine.core.context_classification",
    "loop_engine.core.context_ontology", "loop_engine.core.code_intelligence_assets",
    "loop_engine.core.intelligence_portfolio", "loop_engine.core.intelligence_registry",
    "loop_engine.core.knowledge_loader", "loop_engine.core.store_serve",
    "loop_engine.core.duckdb_catalog", "loop_engine.core.persistence",
    "loop_engine.core.solution_library", "loop_engine.core.skill_registry",
    "loop_engine.core.mcp_adapter", "loop_engine.core.mcp_sdk_transport",
    "loop_engine.core.model_gateway", "loop_engine.core.model_call",
    "loop_engine.core.model_capabilities", "loop_engine.core.model_routes",
    "loop_engine.core.model_discovery", "loop_engine.core.autoconfigure",
    "loop_engine.core.custom_endpoint", "loop_engine.core.ollama_client",
    "loop_engine.core.ollama_resolvers", "loop_engine.core.mistral_client",
    "loop_engine.core.openrouter_client", "loop_engine.core.opencode_client",
    "loop_engine.core.provider_failover", "loop_engine.core.provider_pinned",
    "loop_engine.core.reasoning_call", "loop_engine.core.live_model_verification",
    "loop_engine.core.runtime_settings", "loop_engine.core.settings_loader",
    "loop_engine.core.operating_profile", "loop_engine.core.config",
    "loop_engine.core.otel_export", "loop_engine.core.runtime_observer",
    "loop_engine.core.event_vocabulary", "loop_engine.core.facets",
    "loop_engine.core.asset_class", "loop_engine.core.asset_lifecycle",
    "loop_engine.core.api_quality", "loop_engine.core.workspace_contracts",
    "loop_engine.core.workspace_operations", "loop_engine.core.workspace_backends",
    "loop_engine.core.workspace_local", "loop_engine.core.workspace_optional",
    "loop_engine.core.external_harness", "loop_engine.core.external_harness_adapters",
    "loop_engine.core.harness_intelligence_bridge", "loop_engine.core.user_feedback_intelligence",
    "loop_engine.core.studio_server", "loop_engine.core.studio_operational_views",
    "loop_engine.core.saas_routes",
    "loop_engine.ontology.node", "loop_engine.ontology.loop_node",
    "loop_engine.ontology.catalog", "loop_engine.ontology.folders",
    "loop_engine.ontology.artifacts", "loop_engine.ontology.ontology_checks",
]

reachable = set(seeds)
changed = True
while changed:
    changed = False
    for m in list(reachable):
        for i in mods.get(m, ()):
            if i not in reachable:
                reachable.add(i); changed = True

unreachable = sorted(set(mods) - reachable)
print("TOTAL:", len(mods), "REACHABLE:", len(reachable), "UNREACHABLE:", len(unreachable))
for m in unreachable:
    print(" ", m)
```

After Phase B the seeds use `loop_engine.core.*`. Before Phase B, replace
`loop_engine.core.` with `loop_engine.core.` in the seed list.

## 3. Phase A: delete the legacy decision-spine cluster

These modules predate the canonical Loop runtime. They are not imported by any
canonical module. Delete them:

```text
src/loop_engine/loop/acceptance.py
src/loop_engine/loop/arbiter.py
src/loop_engine/loop/builtin_resolvers.py
src/loop_engine/loop/context_shuffle.py
src/loop_engine/loop/decision_engine.py
src/loop_engine/loop/decision_envelope.py
src/loop_engine/loop/decision_episode.py
src/loop_engine/loop/decision_need.py
src/loop_engine/loop/decision_service.py
src/loop_engine/loop/decision_slates.py
src/loop_engine/loop/delegation.py
src/loop_engine/loop/deliberation.py
src/loop_engine/loop/effective_spec.py
src/loop_engine/loop/escalation_governor.py
src/loop_engine/loop/hybrid_dimension_lattice.py
src/loop_engine/loop/iteration_records.py
src/loop_engine/loop/kernel_model_impls.py
src/loop_engine/loop/lens.py
src/loop_engine/loop/list_intelligence.py
src/loop_engine/loop/loop_handlers.py
src/loop_engine/loop/methodical.py
src/loop_engine/loop/moves.py
src/loop_engine/loop/practitioner_campaign.py
src/loop_engine/loop/practitioner_loop.py
src/loop_engine/loop/practitioner_methods.py
src/loop_engine/loop/regimes/            (whole subpackage)
src/loop_engine/loop/registry.py
src/loop_engine/loop/research_to_capability.py
src/loop_engine/loop/resolvers.py
src/loop_engine/loop/route_bridge.py
src/loop_engine/loop/runner.py
src/loop_engine/loop/solve.py
src/loop_engine/loop/solver.py
src/loop_engine/loop/spawned_practitioner.py
src/loop_engine/loop/step_registry.py
src/loop_engine/loop/steps/              (whole subpackage)
src/loop_engine/loop/studio.py
src/loop_engine/loop/tuning.py
src/loop_engine/loop/wiring.py
```

Procedure:

1. Run the import-graph script. Confirm each module above is unreachable or
   only reachable through other modules on this list.
2. Remove legacy imports from `src/loop_engine/_self_test.py`. The file has a
   large legacy section that imports `decision_service`, `moves`, `knowledge`,
   `regimes`, `resolvers`, `registry`, `solve`, `solver`, and `strings.frame`.
   Delete that section and its tests. Keep only tests for canonical modules.
3. Remove legacy imports from `src/loop_engine/__main__.py`. It imports
   `loop.moves`, `loop.resolvers`, and `loop.step_registry`. Replace the
   `--map` implementation with `architecture_map.render_map()`. Remove any CLI
   feature that only the legacy cluster supported.
4. Fix `src/loop_engine/code_nodes/universal_solve.py`. It imports
   `loop.solver`. Replace the import with the canonical path
   (`loop.kernel_runtime` or `loop.delegation_runtime`) or delete
   `universal_solve.py` if it is itself legacy. Decide from evidence.
5. Delete the files listed above.
6. Update `src/loop_engine/architecture_map.py`:
   - remove every deleted module from `MODULE_MAP`;
   - remove `"regimes"` and `"steps"` from the `loop` entry;
   - remove the `strings` subpackage if every `strings` module is deleted.
7. Delete `src/loop_engine/strings/` modules that the import graph shows as
   unreachable after step 2. Keep any `strings` module that canonical code
   still imports. If none remain, delete the whole `strings/` package and
   remove it from `SUBPACKAGES` and `MODULE_MAP`.
8. Run the gates in section 7. Fix every failure before continuing.

## 4. Phase B: rename core to core

The public name is Core Architecture. The package name is `core`.

Exact steps:

1. Move the package:

```bash
git mv src/loop_engine/core src/loop_engine/core
```

2. Replace every import. Run these replacements across `src/`, `examples/`,
   `benchmarks/`, and `tools/`:

```text
from ..core        -> from ..core
from .core         -> from .core
from loop_engine.core -> from loop_engine.core
loop_engine.core   -> loop_engine.core
```

3. Update `src/loop_engine/architecture_map.py`:
   - `SUBPACKAGES` becomes `("ontology", "loop", "strings", "code_nodes", "core")`
     or without `strings` if Phase A removed it;
   - rename the `"core"` key in `MODULE_MAP` to `"core"`;
   - update `PUBLIC_STATIC_ARCHITECTURE_CAPABILITY_GROUPS` to
     `PUBLIC_CORE_ARCHITECTURE_CAPABILITY_GROUPS` and update every caller.
4. Update `src/loop_engine/forbidden_paths.json`: replace every
   `core/` path with `core/`.
5. Update `src/loop_engine/__init__.py` public exports that reference
   `core`.
6. Update `src/loop_engine/loop/recursive_loop.py` and every other module that
   imports `..core` or `..core` relative paths.
7. Update `src/loop_engine/core/boundary_registry.py` (now
   `core/boundary_registry.py`) if it names its own package.
8. Update the docs. Replace `core` with `core` and
   `Core Architecture` with `Core Architecture` in:
   - `README.md`
   - `AGENTS.md`
   - `humanizer-context.md`
   - `docs/` (all files)
   - `docs/prompts/` (all files)
   - `src/loop_engine/ARCHITECTURE-MAP.md`
   - `src/loop_engine/ontology/README.md` if it names the package
9. Update `docs/components/core-architecture/` folder name to
   `docs/components/core-architecture/` and fix every link to it.
10. Run the gates in section 7. Fix every failure before continuing.

## 5. Phase C: fix every conformance gate

The current `src/loop_engine/architecture_conformance.json` reports these
failures. Fix each one at its source, then regenerate the report.

1. `unclassified_files`: `loop/spawned_workspace_executor.py` and
   `loop/spawned_workspace_executor_checks.py` are missing from
   `architecture_map.MODULE_MAP`. Add both under `loop`.
2. `reachable_legacy_flat_paths`: `kernel`. Caused by the dynamic import in
   `loop/step_registry.py`. Phase A deletes that module, which fixes the gate.
   Verify after Phase A.
3. `operational_graph_vertex_types_outside_canonical_loop`: three hits.
   - `ontology/node.py` `Node` and `ontology/loop_node.py` `LoopNode` are
     at-rest catalog records, not runtime vertices. Add a declared exception
     for these two classes in the conformance scanner with the reason
     "at-rest ontology record, not an executable graph vertex".
   - `code_nodes/run_analytics.py` `LoopRelationshipVertex` is a report
     projection. Rename it to `LoopRelationshipRecord` or make it a plain
     dataclass that does not look like a vertex type.
4. `retired_source_nomenclature`: five hits for `chronicle`, `receipt`,
   `root loop`, and `child`. Find each file and line in the report, replace
   the retired term with the current term (`Run History`, `record`, `Starting
   Loop`, `Spawned Loop`), and re-run.
5. `dynamic_import_registration_bypasses`: one hit. Caused by
   `loop/step_registry.py`. Phase A fixes it.
6. `modules_missing_llm_context_docstring`: two hits. Add the required
   docstring header to each module.
7. `modules_whose_self_test_the_suite_never_runs`: five hits. The ontology
   modules define `self_test()` but `_self_test.py` never collects them. Add
   `ontology.artifacts`, `ontology.catalog`, `ontology.folders`,
   `ontology.node`, `ontology.loop_node`, and `ontology.ontology_checks` to
   `_FOLDED_SUBMODULE_TESTS` in `_self_test.py`.
8. `architecture_map_freshness`: one hit. Regenerate the map artifact after
   every change with the repository's map command.
9. The conformance report itself contains retired terms and gets flagged by
   the retired-term scan. Exclude generated report files
   (`architecture_conformance.json`) from that scan, or rename the terms in
   the report output.
10. The ontology README claims `python -m loop_engine --ontology-check` exists.
    It does not. Add the `--ontology-check` and `--write-ontology-index` CLI
    flags to `src/loop_engine/__main__.py`, wired to
    `ontology.ontology_checks.run_checks` and the index writer.

## 6. Phase D: build the intelligence access layer

Implement one backend-neutral intelligence access layer. Files and databases
are materializations of the same logical records. DuckDB is the default local
SQL engine. It must not become the ontology or the only store.

### 6.1 Architecture

```text
Intelligence Access Architecture
│
├── Intelligence Catalog
│   ├── Record Resolution
│   ├── Version Resolution
│   ├── Relationship Resolution
│   ├── Materialization Resolution
│   ├── Source Selection
│   └── Conflict Resolution
│
├── Intelligence Query
│   ├── Layers
│   ├── Source Collections
│   ├── Artifact Kinds
│   ├── Attribute Predicates
│   ├── Relationship Predicates
│   ├── Projections
│   ├── Ordering
│   ├── Limits
│   ├── Version Constraints
│   ├── Lifecycle Constraints
│   ├── Temporal / As-Of Constraints
│   └── Required Capabilities
│
├── Query Planner
│   ├── Validate Query
│   ├── Resolve Sources
│   ├── Inspect Adapter Capabilities
│   ├── Select Pushdown Operations
│   ├── Select Federation Strategy
│   ├── Compile Backend Query
│   ├── Execute
│   └── Normalize Results
│
├── Adapter Contract
│   ├── Handshake
│   ├── Get
│   ├── Query
│   ├── Stream
│   ├── Write
│   ├── Compare and Swap
│   ├── Begin Snapshot
│   ├── Export
│   ├── Import
│   ├── Health Check
│   └── Close
│
├── Adapters
│   ├── File SQL
│   │   ├── DuckDB JSONL Adapter
│   │   ├── DuckDB Parquet Adapter
│   │   └── PyArrow Dataset Adapter
│   ├── Embedded Database
│   │   ├── DuckDB Adapter
│   │   └── SQLite Adapter
│   ├── Server Database
│   │   ├── SQLAlchemy Adapter
│   │   ├── ADBC Adapter
│   │   ├── PostgreSQL Adapter
│   │   └── Other Database Adapters
│   ├── Plugin
│   │   ├── Portable Bundle Adapter
│   │   ├── Installed Package Adapter
│   │   └── Remote Plugin Service Adapter
│   ├── Remote Files
│   │   └── Fsspec Adapter
│   └── Composite
│       └── Unified Core + Learned + Plugin Adapter
│
├── Materialization
│   ├── Inline Record
│   ├── Local File
│   ├── Content-Addressed File
│   ├── Object Store
│   ├── Database Payload
│   ├── Plugin Resource
│   └── Remote Resource
│
├── Result Transport
│   ├── Arrow RecordBatch
│   ├── Arrow RecordBatchReader
│   ├── Python Records
│   ├── JSONL
│   └── Parquet
│
└── Conformance
    ├── Adapter Contract Tests
    ├── Query Equivalence Tests
    ├── Round-Trip Tests
    ├── Version Handshake Tests
    ├── Failure Injection Tests
    └── Cross-Backend Golden Queries
```

Everything here is Code Intelligence. When querying, materializing,
synchronizing, exporting, or importing performs work, that operation runs
through an ordinary Intelligence-role or Solution-role Loop. The access layer
is a capability used by Loops, not a new runtime.

### 6.2 Package roles

| Package | Role |
|---|---|
| `duckdb` | Default local SQL engine over JSONL, CSV, Parquet, DuckDB files, and attached databases |
| `ibis-framework` | Backend-neutral query-expression layer |
| `sqlalchemy` | Database connections, transactions, DDL, and mutation support |
| `adbc-driver-manager` | Arrow-native, high-throughput database reads and writes |
| `pyarrow` | Canonical tabular interchange and streaming batch format |
| `sqlglot` | SQL parsing, validation, rewriting, and dialect translation |
| `fsspec` | Uniform local, remote, cloud, archive, and object-store file access |
| `datafusion` | Optional alternative Arrow-native SQL engine |
| `polars` | Optional local LazyFrame and in-memory SQL execution |

Add the required packages to `pyproject.toml` dependencies. Keep optional
engines optional.

### 6.3 Physical structure

```text
src/loop_engine/
│
├── intelligence/
│   ├── access/
│   │   ├── README.md
│   │   ├── catalog.py
│   │   ├── query.py
│   │   ├── planner.py
│   │   ├── handshake.py
│   │   ├── capabilities.py
│   │   ├── results.py
│   │   ├── materialization.py
│   │   ├── synchronization.py
│   │   └── adapters/
│   │       ├── README.md
│   │       ├── base.py
│   │       ├── duckdb_files.py
│   │       ├── duckdb_database.py
│   │       ├── pyarrow_dataset.py
│   │       ├── sqlalchemy_database.py
│   │       ├── adbc_database.py
│   │       ├── plugin_bundle.py
│   │       ├── remote_catalog.py
│   │       ├── fsspec_files.py
│   │       └── composite.py
│   ├── context/
│   │   ├── core/
│   │   ├── learned/
│   │   └── plugins/
│   ├── code/
│   │   ├── core/
│   │   ├── learned/
│   │   └── plugins/
│   ├── previous_run_and_solution/
│   │   ├── core/
│   │   ├── learned/
│   │   └── plugins/
│   └── user/
│       ├── core/
│       ├── learned/
│       └── plugins/
│
├── catalog/
│   ├── registry.py
│   ├── resolver.py
│   └── indexes.py
│
└── tests/
    └── intelligence_access/
        ├── test_adapter_contract.py
        ├── test_query_equivalence.py
        ├── test_core_files.py
        ├── test_duckdb.py
        ├── test_postgres.py
        ├── test_composite_catalog.py
        └── test_portable_round_trip.py
```

Do not reproduce the four intelligence-layer folders inside every adapter. An
adapter works with records from any layer.

### 6.4 Core Intelligence: files that behave like tables

```text
intelligence/
└── code/
    └── core/
        ├── README.md
        ├── manifest.json
        ├── records/
        │   ├── part-00000.jsonl
        │   └── ...
        ├── query/
        │   ├── records.parquet
        │   ├── attributes.parquet
        │   ├── relationships.parquet
        │   └── materializations.parquet
        └── files/
            └── sha256/
                └── <large-content-files>
```

Authority model:

```text
JSONL    Canonical, portable, package-shipped Core records
Parquet  Generated query-optimized mirror
DuckDB   Runtime SQL engine and optional disposable catalog cache
Manifest Hashes, schema versions, record counts, shard list,
         generation version, and compatibility declaration
```

The Parquet mirror must never silently become a second authority. Its manifest
must include the source manifest hash, source JSONL hashes, record count,
schema version, ontology version, generator version, generated timestamp, and
Parquet content hash. When those values do not match, the mirror is rebuilt.

### 6.5 Learned Intelligence deployment profiles

```text
Local portable profile
├── Authoritative local DuckDB database
├── Content-addressed files
└── Periodic JSONL / Parquet portable exports

Local file-authoritative profile
├── Append-only JSONL journal
├── Content-addressed files
├── Generated Parquet snapshots
└── Disposable DuckDB query cache

Server profile
├── Authoritative PostgreSQL database
├── Object-store files
├── Optional Arrow / Parquet exports
└── DuckDB used for local analytical federation

Remote service profile
├── Remote Catalog API
├── Server-side database
├── Server-side object storage
└── Local read-through cache
```

Plugins use the same adapter contract. A plugin must not need a special Plugin
Query API. It implements the same adapter contract and returns the same
normalized records.

### 6.6 Adapter handshake

Every adapter declares its actual capabilities before use:

```json
{
  "adapter_id": "core.duckdb-files",
  "adapter_version": "1.2.0",
  "adapter_kind": "file_sql",
  "engine": "duckdb",
  "ontology_versions": { "read": [3, 4], "write": [] },
  "record_schema_versions": { "read": ["2.0", "2.1"], "write": [] },
  "source_collections": ["core"],
  "operations": {
    "get": true, "query": true, "stream": true,
    "write": false, "delete": false,
    "export": true, "import": false
  },
  "query_capabilities": {
    "projection": true, "filter": true, "join": true,
    "aggregation": true, "relationship_traversal": false,
    "full_text_search": false, "vector_search": false,
    "temporal_as_of": false
  },
  "pushdown": { "projection": true, "filter": true, "limit": true, "order": true },
  "transactions": { "supported": false, "snapshot_reads": true },
  "result_formats": ["arrow_record_batch_reader", "arrow_table", "python_records"],
  "materializations": ["jsonl", "parquet", "local_file"],
  "authority": "authoritative_read_only",
  "compatibility_verdict": "compatible"
}
```

A PostgreSQL adapter reports `write: true`, `transactions: true`,
`compare_and_swap: true`, `authority: authoritative`, `portable_export: true`.
A plugin service reports `read: true`, `write: false`, `query_pushdown:
partial`, `full_text_search: true`, `vector_search: true`,
`offline_available: false`.

### 6.7 One authority, many materializations

```text
One logical record
├── One current authority
└── Zero or more materializations
    ├── JSONL
    ├── Parquet
    ├── DuckDB table
    ├── PostgreSQL row
    ├── SQLite replica
    ├── Object-store file
    └── Portable bundle
```

Authority profiles:

```text
Core              Package files are authoritative
Learned Local     Local database or append-only file journal is authoritative
Learned Server    Server database is authoritative
Candidate Bundle  Bundle is authoritative until imported into Governance
Plugin Bundle     Installed signed plugin version is authoritative
Remote Plugin     Remote plugin service is authoritative
```

Never make files and a database independently writable authorities at the same
time. When both must update, use an authoritative write, then a transactional
outbox or append-only journal, then idempotent replication, then hash and
watermark verification. Never write to two authorities and hope both succeed.

### 6.8 Public query contract

The public API is a typed query object, not a SQL string:

```python
query = IntelligenceQuery(
    layers={"code"},
    source_collections={"core", "learned", "plugin"},
    artifact_kinds={"loop_definition", "loop_canvas"},
    attributes={
        "core.problem_type": {"contains": "tabular_classification"},
        "core.resource.gpu.required": {"equals": False},
    },
    lifecycle={"active"},
    limit=50,
)
```

The planner compiles this to DuckDB SQL, PostgreSQL SQL, a local Arrow scan,
or a plugin-specific query. SQL is an execution language, not the canonical
ontology. Raw SQL may remain available as a trusted administrative escape
hatch, parsed by SQLGlot, with prohibited statements rejected.

### 6.9 Conformance suite

Every adapter must pass the same golden suite:

```text
Adapter Conformance
├── Connect and handshake
├── Read one record by exact ID
├── Read one exact version
├── Stream a large result
├── Filter by intelligence layer
├── Filter by source collection
├── Filter by artifact kind
├── Filter by lifecycle
├── Filter by typed attribute
├── Traverse a relationship
├── Resolve a file materialization
├── Preserve nested values
├── Preserve NULL semantics
├── Preserve timestamp and time-zone semantics
├── Preserve record and content hashes
├── Export to portable bundle
├── Import portable bundle
├── File to database to file round trip
├── Database to file to database round trip
├── Reject unsupported schema version
├── Reject incompatible ontology version
├── Reject a duplicate immutable version
├── Detect a corrupted file
├── Detect stale derived Parquet
├── Recover from interrupted synchronization
├── Behave correctly when remote database is unavailable
└── Produce the same normalized result for golden queries
```

### 6.10 First implementation stack

```text
Core file authority        JSONL + referenced files
Core query representation  Generated Parquet
Local SQL engine           DuckDB
Backend-neutral contract   Loop Engine IntelligenceQuery
Database connections       SQLAlchemy
Arrow-native transfer      PyArrow, ADBC when supported
SQL parsing and safety     SQLGlot
Remote filesystem access   fsspec
Initial server database    PostgreSQL
Unified catalog            CompositeIntelligenceAdapter
```

The resulting model:

```text
Core JSONL / Parquet ──────────┐
                               │
Local Learned DuckDB ──────────┤
                               │
Server Learned PostgreSQL ─────┼──► Unified Intelligence Catalog
                               │        ↓
Plugin Bundles ────────────────┤    IntelligenceQuery
                               │        ↓
Remote Plugin Services ────────┘    Arrow Results
                                        ↓
                                  Intelligence LoopNode
```

## 7. Verification gates

Run these commands after every phase. All must pass before the session ends.

```bash
PYTHONPATH=src python3 -m loop_engine --self-test
PYTHONPATH=src python3 -m loop_engine --conformance
PYTHONPATH=src python3 -m loop_engine --map
PYTHONPATH=src python3 -m loop_engine --ontology-check
PYTHONPATH=src python3 -m loop_engine --profiles
```

Additional checks:

```bash
python3 /tmp/opencode/import_graph.py
rg -n "core" src/ docs/ examples/ README.md AGENTS.md humanizer-context.md
rg -n "decision_service|DecisionService|loop\.moves|loop\.solver|loop\.runner|loop\.regimes|loop\.steps" src/ examples/
python3 -m pytest tests/ -q
```

Pass criteria:

1. `--self-test` reports zero failures.
2. `--conformance` reports `all_gates_pass: true` with zero zero-tolerance
   violations.
3. `--map` prints the new tree with `core` and without the deleted modules.
4. `--ontology-check` runs and passes on the live tree.
5. The import-graph script reports zero unreachable modules that are not
   declared legacy or intentionally standalone.
6. No `core` string remains in source, docs, or examples.
7. No import of a deleted module remains anywhere.
8. The intelligence access conformance suite passes for the DuckDB files
   adapter, the DuckDB database adapter, and the composite adapter.
9. A golden query returns identical normalized results from the JSONL file
   adapter and the DuckDB database adapter.
10. A file to database to file round trip preserves record identity, version,
    content hash, relationships, and unknown fields.

## 8. Completion report

Report:

1. the exact list of deleted files;
2. the exact rename performed and every file touched;
3. the new `src/loop_engine/` tree;
4. the conformance gate failures found and how each was fixed;
5. the intelligence access modules implemented and their public API;
6. the adapter handshake fields implemented;
7. the conformance suite results per adapter;
8. the round-trip results;
9. the exact commands run and their output summaries;
10. remaining failures, if any, with reasons;
11. anything you could not complete and why.

Do not claim completion unless every gate in section 7 has actually run and
passed in the current worktree.
