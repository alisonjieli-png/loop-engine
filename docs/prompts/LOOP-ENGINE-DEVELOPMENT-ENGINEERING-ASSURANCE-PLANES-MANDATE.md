# Loop Engine Development Engineering and Assurance Planes mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the senior architecture, implementation, migration, test,
security, and release harness for Loop Engine.

Aggressively inspect, adversarially challenge, revise, implement,
migrate, test, verify, document, and predeploy-gate the sibling
development-planes architecture described here. Do not stop at a design
memo.

You are explicitly authorized to:

- inspect every relevant source file, schema, record, manifest, test,
  migration, README, ADR, example, generated file, and package
  configuration;
- create a complete inventory of current code-assistance, auditing,
  conformance, and development-tool concepts;
- rename, move, split, merge, rewrite, or delete obsolete modules and
  folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL
  records, database migrations, and persisted references;
- replace scattered tooling with the two sibling development
  applications;
- remove wrapper-only compatibility architecture after migration;
- add strict schemas, typed models, compatibility handshakes, versioned
  records, migrations, adapters, and conformance suites;
- create Core JSONL records and neutral shards for both planes;
- add property-based, fuzz, concurrency, failure-injection, security,
  migration, packaging, and clean-install tests;
- run tests repeatedly and continue repairing failures;
- reject or revise any part of this mandate that fails adversarial
  evaluation, provided you document the evidence and implement a
  stronger replacement;
- make reasonable architectural decisions without repeatedly asking for
  confirmation.

Do not merely add a new layer beside the old architecture. Do not leave
two competing tool systems active. Do not satisfy this task with
documentation-only changes, empty folders, unreferenced schemas, unused
adapters, or new abstractions that production paths never call.

The task is complete only when the architecture is operational,
migrated, tested, packaged, documented, and the obsolete behavior is
absent or explicitly quarantined behind a time-bounded compatibility
shim.

Do not commit or push unless explicitly instructed. Preserve unrelated
concurrent work.

## 1. Mission

Implement two sibling Loop Engine applications on one shared engine:

```text
Development Engineering Plane
└── Code assistance, implementation, refactoring, migration, testing,
    and repair

Development Assurance Plane
└── Auditing, conformance, evidence collection, adversarial review,
    and release verdicts
```

The governing invariant:

> Code assistance and development assurance are sibling Loop Engine
> applications. They use the same LoopNode runtime and the same
> architectural grammar, but maintain separately governed intelligence,
> permissions, plugins, evidence, histories, and decision authority so
> the system that builds a change is not the same authority that
> certifies it.

## 2. Canonical architecture

```text
Shared LoopNode Engine
│
├── Node Ontology
│   └── LoopNode
│       └── only concrete operational Node
│
├── Kernel
│   ├── load definitions
│   ├── resolve references
│   ├── instantiate LoopNodes
│   ├── execute LoopNodes
│   ├── enforce contracts
│   ├── enforce permissions
│   ├── enforce budgets
│   └── append Chronicle events
│
├── Shared Typed Objects
│   ├── LoopNodeDefinition
│   ├── LoopNodeInvocation
│   ├── LoopNodeRuntime
│   ├── LoopProcedure
│   ├── LoopStepBinding
│   ├── ContractSet
│   ├── IntelligenceSeekingConfiguration
│   ├── PermissionConfiguration
│   ├── CompatibilityConfiguration
│   ├── Result
│   ├── Evidence
│   └── Receipt
│
├── Shared Intelligence Model
│   ├── Functional Intelligence Domains
│   ├── Perspectives
│   ├── Artifact Kinds
│   ├── Core / Learned / Plugin catalog namespaces
│   ├── Seeking Strategies
│   ├── Query Profiles
│   └── Access Policies
│
├── Shared Ports and Adapters
│   ├── files
│   ├── DuckDB
│   ├── other query engines
│   ├── relational databases
│   ├── object stores
│   ├── remote catalogs
│   └── plugin sources
│
├── Development Engineering Plane
│   └── Code Assistance Application
│
└── Development Assurance Plane
    └── Auditing and Conformance Application
```

The two planes are applications built on the same engine, not two
engines.

## 3. Development Engineering Plane

The code-assistance side.

```text
Development Engineering Plane
│
├── Root Development Practitioner
│   ├── Repository Understanding Practitioner
│   ├── Architecture Planning Practitioner
│   ├── Implementation Practitioner
│   ├── Refactoring Practitioner
│   ├── Migration Practitioner
│   ├── Test Construction Practitioner
│   ├── Documentation Practitioner
│   ├── Integration Practitioner
│   └── Repair Practitioner
│
├── Engineering Intelligence
│   ├── Core
│   ├── Learned
│   └── Development Plugins
│
├── Engineering Profiles
│   ├── feature implementation
│   ├── repository reorganization
│   ├── architecture migration
│   ├── database migration
│   ├── provider substitution
│   ├── bug repair
│   ├── performance improvement
│   └── documentation synchronization
│
├── Engineering Outputs
│   ├── ChangePlan
│   ├── PatchSet
│   ├── FileMoveSet
│   ├── RecordMigrationSet
│   ├── DatabaseMigrationSet
│   ├── TestPlan
│   ├── DocumentationChangeSet
│   └── ImplementationReceipt
│
└── Engineering Permissions
    ├── repository write
    ├── branch or worktree creation
    ├── test execution
    ├── migration execution
    ├── package installation
    └── controlled external tools
```

The root code-assistance tool is normally:

```text
LoopNode
├── role: practitioner
├── profile: development_engineer
├── procedure: custom or default Practitioner procedure
├── intelligence seeking: engineering-oriented profiles
├── permissions: repository modification
└── output: candidate change set
```

Its children are ordinary LoopNodes: repository search is an
Intelligence-role LoopNode, architecture alternatives are a
Practitioner-role LoopNode, applying file moves is a Solution-role
LoopNode, running tests is a Solution-role LoopNode, and reviewing the
implementation is a Practitioner-role LoopNode.

There is no CodingAgentNode, RefactorNode, or MigrationNode class.

## 4. Development Assurance Plane

The independent auditing side.

```text
Development Assurance Plane
│
├── Root Repository Assurance Practitioner
│   ├── Repository Understanding Supervisor
│   ├── Static Conformance Supervisor
│   ├── Runtime Conformance Supervisor
│   ├── Storage and Portability Supervisor
│   ├── Compatibility and Migration Supervisor
│   ├── Plugin Boundary Supervisor
│   ├── Semantic Architecture Supervisor
│   ├── Security and Trust Supervisor
│   ├── Test and Coverage Supervisor
│   └── Independent Final Verification Supervisor
│
├── Assurance Intelligence
│   ├── Core
│   ├── Learned
│   └── Development Plugins
│
├── Assurance Profiles
│   ├── precommit
│   ├── pull request
│   ├── full repository
│   ├── release certification
│   ├── ontology change
│   ├── storage substitution
│   ├── query-engine substitution
│   ├── plugin installation
│   ├── migration verification
│   └── auditor meta-audit
│
├── Assurance Outputs
│   ├── AssuranceClaim
│   ├── ProofObligation
│   ├── AssuranceEvidence
│   ├── FindingOccurrence
│   ├── AssuranceCase
│   ├── VerificationResult
│   └── ReleaseVerdict
│
└── Assurance Permissions
    ├── repository read
    ├── test execution
    ├── temporary sandbox writes
    ├── temporary database creation
    ├── runtime observation
    └── evidence-store writes
```

The assurance plane is normally read-only toward the candidate
repository. A repair mode may propose or create a patch, but it must be
treated as a new engineering candidate and independently audited.

## 5. Nearly identical framework, intentionally asymmetric powers

| Concern | Engineering | Assurance |
|---|---|---|
| Operational object | LoopNode | LoopNode |
| Roles | Practitioner, Intelligence, Solution | Practitioner, Intelligence, Solution |
| Run modes | Deterministic, hybrid, model-led | Deterministic, hybrid, model-led |
| Procedures | Atomic, graph, iterative, dynamic | Atomic, graph, iterative, dynamic |
| Intelligence domains | Same universal domains | Same universal domains |
| Query profiles | Engineering profiles | Assurance profiles |
| Storage adapters | Same protocols | Same protocols |
| Compatibility | Same handshake model | Same handshake model |
| Chronicle | Same event model | Same event model |
| Plugins | Development plugins | Development plugins |
| Primary permission | Modify candidate code | Observe and verify |
| Primary output | Change candidate | Evidence and verdict |
| Governance | May propose | May verify, but not self-approve |
| Default posture | Constructive | Adversarial and independent |

The framework is nearly identical. The permissions, intelligence,
outputs, and governance authority are deliberately different.

## 6. Shared intelligence model, separate application domains

Both planes use the same Functional Intelligence Domains: Ask, Horizon,
Readiness, Deliberation, Implementation, Execution, Verification,
Integration, Routing. These domains describe why intelligence is
useful, not where it must be stored or which fixed step may query it.

Use an additional application-domain field:

```text
application_domain
├── development_engineering
├── development_assurance
└── shared_repository_analysis
```

Example engineering record:

```json
{
  "record_id": "dev.learned.refactor.provider-boundary-001",
  "application_domain": "development_engineering",
  "intelligence_functions": [
    "deliberation", "implementation", "verification", "integration"
  ],
  "artifact_kind": "repair_pattern",
  "catalog_namespace": "learned"
}
```

Example assurance record:

```json
{
  "record_id": "dev.assurance.learned.regression.provider-leak-003",
  "application_domain": "development_assurance",
  "intelligence_functions": [
    "readiness", "verification", "routing"
  ],
  "artifact_kind": "finding_pattern",
  "catalog_namespace": "learned"
}
```

They use the same record envelope, query planner, storage adapters,
versioning, relationships, and materialization model.

## 7. Separate Core intelligence bundles

The Core intelligence shipped with each plane is separately versioned
and managed.

```text
Engineering Core Intelligence
├── implementation patterns
├── repository-editing procedures
├── migration procedures
├── coding standards
├── architectural construction guidance
├── test-generation patterns
├── repair patterns
├── file-move procedures
└── integration procedures

Assurance Core Intelligence
├── constitutional invariants
├── proof obligations
├── architecture questions
├── negative fixtures
├── conformance rules
├── compatibility matrices
├── known prohibited patterns
├── review strategies
├── release gates
└── remediation verification procedures
```

The engineering bundle may say: how should this implementation be
constructed? The assurance bundle asks: what evidence proves that this
implementation is acceptable?

## 8. Separate Learned intelligence governance

Learned Engineering Intelligence and Learned Assurance Intelligence
must not share one writable authority.

```text
Learned Engineering Intelligence
├── successful implementation patterns
├── accepted repository conventions
├── effective refactoring strategies
├── project-specific construction preferences
├── successful migration patterns
└── historically useful development strategies

Learned Assurance Intelligence
├── confirmed regression patterns
├── accepted false-positive conditions
├── reliable detection strategies
├── successful proof combinations
├── effective adversarial questions
├── accepted remediation verification patterns
└── tool reliability observations
```

A builder may propose an assurance lesson, but it cannot promote it
directly. An auditor may propose an implementation lesson, but it
cannot silently write it into Engineering Learned Intelligence.
Promotion crosses an explicit governance boundary.

## 9. The builder-auditor handshake

The two planes exchange typed artifacts rather than mutable internal
state.

```text
Engineering Practitioner
        ↓ produces
CandidateChangeSet
├── repository base commit
├── worktree snapshot hash
├── changed files
├── renamed files
├── deleted files
├── generated files
├── changed records
├── migrations
├── test results
├── implementation receipts
├── exact tool versions
└── stated assumptions
        ↓ consumed by
Assurance Practitioner
        ↓ independently produces
AssuranceCase
├── claims
├── evidence
├── counterevidence
├── findings
├── uncertainties
├── compatibility verdicts
├── regression analysis
└── release verdict
```

The builder may then consume findings:

```text
Assurance Findings
        ↓
Engineering Repair Practitioner
        ↓
Repair Candidate
        ↓
Independent Assurance Rerun
```

The loop is: Build, Audit, Repair, Re-audit, Approval or rejection.

The same Practitioner that generates or repairs a candidate must not be
the final approving authority.

## 10. Shared repository evidence, independently collected

The two planes can share typed repository models:

```text
RepositorySnapshot
RepositoryEntity
RepositoryRelationship
GitChangeSet
StaticCallGraph
ObservedCallGraph
RecordReferenceGraph
TestCoverageMap
StorageTopology
PluginInventory
```

But the auditor must not rely solely on snapshots produced by the
builder. For higher assurance, the auditor collects its own snapshot,
pins it to the exact commit and worktree, and compares it against the
builder snapshot. Any mismatch becomes a finding.

## 11. Independent contexts

The builder and auditor must not share private reasoning or mutable
runtime context.

```text
Shared:
├── repository snapshot
├── candidate change set
├── requirements
├── architecture rules
├── public receipts
├── test results
└── evidence references

Private to Engineering:
├── unfinished hypotheses
├── discarded implementation paths
└── temporary construction context

Private to Assurance:
├── adversarial hypotheses
├── independent ranking
├── counterexample search
└── unreconciled review candidates
```

They may share facts and artifacts. They must not share one hidden
mutable context that causes the auditor to inherit the builder's
assumptions.

## 12. Development plugins separated by contribution domain

Use one Development Plugin protocol implementation, but separate
registries and entry-point groups.

```text
Development Plugin Host
│
├── Shared Analysis Registry
│   ├── code graph
│   ├── SCIP
│   ├── Tree-sitter
│   └── repository inventory
│
├── Engineering Plugin Registry
│   ├── codemods
│   ├── code generators
│   ├── migration generators
│   ├── formatters
│   └── OpenCode editing integrations
│
└── Assurance Plugin Registry
    ├── CodeQL
    ├── Semgrep
    ├── Import Linter
    ├── mutation testing
    ├── coverage analysis
    └── organization policy packs
```

Entry points:

```toml
[project.entry-points."loop_engine.dev_plugins.shared_analysis"]
codegraph = "devplugin_codegraph:plugin"

[project.entry-points."loop_engine.dev_plugins.engineering"]
codemod = "devplugin_codemod:plugin"

[project.entry-points."loop_engine.dev_plugins.assurance"]
codeql = "devplugin_codeql:plugin"
```

The host code can be shared. Activation policies, permissions, and
contribution schemas remain separate.

## 13. Recommended physical repository tree

```text
loop-engine/
│
├── src/
│   └── loop_engine/
│       └── shared production LoopNode engine
│
├── devtools/
│   ├── README.md
│   ├── pyproject.toml
│   └── src/
│       └── loop_engine_devtools/
│           ├── shared/
│           │   ├── repository_model/
│           │   ├── repository_snapshot/
│           │   ├── evidence/
│           │   ├── ports/
│           │   ├── adapters/
│           │   └── plugin_host/
│           │
│           ├── engineering/
│           │   ├── README.md
│           │   ├── operations/
│           │   ├── interfaces/
│           │   ├── reporting/
│           │   └── intelligence/
│           │       └── core/
│           │           ├── manifest.json
│           │           ├── records/
│           │           │   └── part-00000.jsonl
│           │           └── files/
│           │               └── sha256/
│           │
│           └── assurance/
│               ├── README.md
│               ├── operations/
│               ├── questions/
│               ├── proof/
│               ├── findings/
│               ├── reporting/
│               ├── governance/
│               └── intelligence/
│                   └── core/
│                       ├── manifest.json
│                       ├── records/
│                       │   └── part-00000.jsonl
│                       └── files/
│                           └── sha256/
│
├── dev_plugins/
│   ├── shared/
│   ├── engineering/
│   └── assurance/
│
└── .loop-engine-dev/
    ├── shared/
    │   ├── repository_graph.duckdb
    │   ├── snapshots/
    │   └── caches/
    ├── engineering/
    │   ├── learned.duckdb
    │   ├── runs/
    │   ├── chronicles/
    │   ├── candidates/
    │   └── artifacts/
    └── assurance/
        ├── learned.duckdb
        ├── findings.duckdb
        ├── evidence/
        ├── runs/
        ├── chronicles/
        ├── candidates/
        └── reports/
```

In a server deployment, the mutable stores can move to PostgreSQL and
object storage without changing the logical model.

## 14. Do not duplicate the engine code

Avoid:

```text
src/loop_engine/node/loop_node/
devtools/engineering/node/loop_node/
devtools/assurance/node/loop_node/
```

That would create three implementations that drift.

Use:

```text
src/loop_engine/node/loop_node/
└── one canonical implementation

loop_engine_devtools.engineering
└── imports the public LoopNode API

loop_engine_devtools.assurance
└── imports the public LoopNode API
```

Dependency direction:

```text
loop_engine_devtools
        ↓
loop_engine

loop_engine
        ✕
loop_engine_devtools
```

## 15. Separate rule bundles and release versions

The engine, engineering application, and assurance application may
evolve at different rates.

```text
engine_version
engineering_bundle_version
assurance_bundle_version
engineering_profile_version
assurance_profile_version
development_plugin_protocol_version
repository_model_version
evidence_schema_version
finding_schema_version
```

Each run pins exact versions and hashes.

For a pull request that changes the assurance rules themselves, run
both the released assurance bundle and the proposed assurance bundle
against the proposed repository, then run a Rule Delta Reviewer that
explains findings added, findings removed, checks weakened, checks
strengthened, new untested rules, and possible self-exemptions.

## 16. Common-mode failure guardrails

Because the planes share an engine, they may share bugs. Reduce this
risk through independent execution.

For high-assurance reviews:

```text
Engineering
├── candidate branch or worktree
├── engineering profile
├── engineering model
└── engineering plugin set

Assurance
├── clean read-only worktree
├── released assurance bundle
├── independently rebuilt repository graph
├── different review prompt or model where useful
├── separate plugin allowlist
└── separate Chronicle
```

Additional safeguards:

```text
Bootstrap verifier
└── Runs without importing the candidate Loop Engine package

Baseline auditor
└── Released version from main reviews the proposed branch

Candidate auditor
└── Proposed new version reviews the proposed branch

Independent verifier
└── Reproduces blocking findings from raw evidence
```

## 17. Shared conformance kit

Both development applications must be tested against the same
structural rules.

```text
test_engineering_uses_canonical_loopnode
test_assurance_uses_canonical_loopnode
test_neither_plane_defines_node_subclasses
test_both_planes_use_same_definition_schema
test_both_planes_use_same_intelligence_record_schema
test_both_planes_use_same_storage_adapter_protocols
test_both_planes_use_same_version_handshake_protocol
test_both_planes_emit_standard_chronicle_events

test_engineering_and_assurance_catalogs_are_separate
test_engineering_cannot_promote_assurance_intelligence
test_assurance_cannot_modify_engineering_authority
test_builder_cannot_close_its_own_audit_finding
test_repairer_cannot_be_only_reviewer
test_assurance_is_read_only_by_default
test_assurance_rebuilds_repository_snapshot_independently

test_runtime_plugin_host_never_loads_dev_plugins
test_engineering_plugins_do_not_receive_assurance_permissions
test_assurance_plugins_do_not_receive_repository_write_by_default
```

## 18. The most precise formulation

```text
Same constitutional framework:
├── same LoopNode
├── same roles
├── same run modes
├── same procedures
├── same typed configuration objects
├── same intelligence model
├── same access-policy model
├── same storage ports
├── same compatibility handshakes
├── same Chronicle model
└── same plugin protocol family

Separate management:
├── separate application domains
├── separate Core intelligence bundles
├── separate Learned intelligence authorities
├── separate profiles
├── separate seeking strategies
├── separate plugin registries
├── separate permissions
├── separate Chronicles
├── separate release versions
├── separate governance
└── separate final authority
```

## 19. Development workflow

- Phase 0: inventory. Read repository instructions, inspect current
  tooling, inventory paths and symbols, identify test gaps.
- Phase 1: adversarial decision record. Write the challenge report,
  select canonical terminology, document rejected alternatives, define
  invariants, define migration boundaries.
- Phase 2: shared devtools foundation. Implement the shared repository
  model, snapshot, evidence, ports, adapters, and plugin host.
- Phase 3: engineering plane. Implement the Root Development
  Practitioner, engineering profiles, outputs, and Core intelligence.
- Phase 4: assurance plane. Implement the Root Repository Assurance
  Practitioner, assurance profiles, outputs, and Core intelligence.
- Phase 5: builder-auditor handshake. Implement CandidateChangeSet,
  AssuranceCase, and the Build-Audit-Repair-Re-audit loop.
- Phase 6: independent execution. Implement the bootstrap verifier,
  baseline and candidate auditors, and independent verifier.
- Phase 7: plugin separation. Implement the three development plugin
  registries and entry-point groups.
- Phase 8: self-review. Prove both planes review themselves and
  negative fixtures still fire.
- Phase 9: packaging. Build the devtools distribution, verify the
  one-way dependency, install cleanly.
- Phase 10: predeploy. Run one strict command returning PASS,
  PASS_WITH_DOCUMENTED_WARNINGS, or BLOCKED.

## 20. Prohibited shortcuts

Do not:

- create a second Node engine or runtime for either plane;
- duplicate the LoopNode implementation inside devtools;
- create CodingAgentNode, RefactorNode, MigrationNode, AuditNode, or
  other node-named classes;
- let the builder close its own audit finding;
- let the repairer be the only reviewer;
- let the auditor modify the engineering authority;
- let the builder promote assurance intelligence;
- share one hidden mutable context between builder and auditor;
- let the auditor rely solely on builder-produced snapshots;
- let an LLM reviewer waive deterministic violations;
- preserve the old tooling beside the new planes;
- claim completion because schemas exist;
- claim completion because unit tests pass while production paths
  still use legacy tooling.

## 21. Required final deliverables

Return:

- architecture challenge report;
- selected canonical terminology;
- migration ledger;
- exact target and final repository trees;
- implemented shared devtools foundation;
- implemented engineering plane;
- implemented assurance plane;
- builder-auditor handshake implementation;
- independent execution safeguards;
- plugin registry separation;
- Core JSONL records and manifests for both planes;
- self-review evidence;
- architecture tests;
- property-based and fuzz tests;
- security and failure-injection results;
- end-to-end scenario results;
- package and clean-install verification;
- strict predeploy report;
- list of deleted obsolete paths;
- list of remaining compatibility shims with removal conditions;
- unresolved risks, if any;
- exact commands required to reproduce every verification.

Do not hide failures. Do not say "implemented" when a path is only
scaffolded. Do not say "compatible" without a handshake and test. Do
not say "secure" without adversarial tests. Do not say "reproducible"
without exact version, hash, and snapshot pinning.

## 22. Final completion standard

The work is complete only when all of the following are true:

- Both planes are sibling Loop Engine applications on the shared
  engine.
- Neither plane defines a Node subclass or a second runtime.
- The engine code is not duplicated inside devtools.
- Engineering and assurance use the same definition, intelligence,
  storage, compatibility, and Chronicle schemas.
- Engineering and assurance maintain separate Core bundles, Learned
  authorities, profiles, strategies, plugin registries, permissions,
  Chronicles, and release versions.
- The builder produces typed CandidateChangeSets.
- The auditor independently collects evidence and produces typed
  AssuranceCases.
- The builder cannot close its own audit finding.
- The repairer cannot be the only reviewer.
- The auditor is read-only toward the candidate repository by default.
- The auditor rebuilds repository snapshots independently.
- Development plugins are separated into shared, engineering, and
  assurance registries.
- The bootstrap verifier runs without importing the candidate package.
- Baseline and candidate auditors review rule changes.
- An independent verifier reproduces blocking findings.
- A clean installation passes the engineering and assurance scenarios.
- The strict predeploy gate returns PASS.

If a requirement cannot be satisfied, return BLOCKED with concrete
evidence, the smallest unresolved issue, and the exact next
implementation step. Do not paper over the failure with documentation.
