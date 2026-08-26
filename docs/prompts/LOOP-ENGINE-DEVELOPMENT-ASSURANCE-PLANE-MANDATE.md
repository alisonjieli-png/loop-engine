# Loop Engine Development Assurance Plane mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the senior architecture, implementation, migration, test,
security, and release harness for Loop Engine.

Aggressively inspect, adversarially challenge, revise, implement,
migrate, test, verify, document, and predeploy-gate the Development
Assurance Plane described here. Do not stop at a design memo.

You are explicitly authorized to:

- inspect every relevant source file, schema, record, manifest, test,
  migration, README, ADR, example, generated file, and package
  configuration;
- create a complete inventory of current review, conformance, and
  development-tool concepts;
- rename, move, split, merge, rewrite, or delete obsolete modules and
  folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL
  records, database migrations, and persisted references;
- replace scattered shell-script and CI-YAML review logic with the
  shared assurance Practitioner hierarchy;
- remove wrapper-only compatibility architecture after migration;
- add strict schemas, typed models, compatibility handshakes, versioned
  records, migrations, adapters, and conformance suites;
- create Devtools Core JSONL records and neutral shards;
- add property-based, fuzz, concurrency, failure-injection, security,
  migration, packaging, and clean-install tests;
- run tests repeatedly and continue repairing failures;
- reject or revise any part of this mandate that fails adversarial
  evaluation, provided you document the evidence and implement a
  stronger replacement;
- make reasonable architectural decisions without repeatedly asking for
  confirmation.

Do not merely add a new layer beside the old architecture. Do not leave
two competing review systems active. Do not satisfy this task with
documentation-only changes, empty folders, unreferenced schemas, unused
adapters, or new abstractions that production paths never call.

The task is complete only when the architecture is operational,
migrated, tested, packaged, documented, and the obsolete behavior is
absent or explicitly quarantined behind a time-bounded compatibility
shim.

Do not commit or push unless explicitly instructed. Preserve unrelated
concurrent work.

## 1. Mission

Implement the Development Assurance Plane: a first-class Loop Engine
application that reviews every aspect of the repository (code,
structure, folders, storage, compatibility, plugins, documentation,
tests) against the project's own rules.

The governing invariant:

> Devtools is a first-class Loop Engine application with its own
> recursive Practitioner hierarchy, Core intelligence, Learned
> intelligence, review profiles, supervisors, specialist loops, and
> development plugins, but it executes through the same LoopNode
> ontology, kernel, contracts, budgets, permissions, compatibility
> handshakes, and Chronicle as every other Loop Engine application.

Devtools is NOT a second Node engine and NOT a second runtime.

## 2. Architectural baseline

### 2.1 One shared kernel

```text
Loop Engine
└── One shared LoopNode kernel and runtime

Product Application
└── Product-facing LoopNode definitions and intelligence

Development Assurance Plane
└── Devtools-specific LoopNode definitions and intelligence
    running on the same kernel

Runtime Plugins
└── Extend the installed product

Development Plugins
└── Extend repository review, analysis, testing, and migration
```

### 2.2 Roles inside the assurance hierarchy

```text
Supervisor
└── Practitioner-role LoopNode
    profile = supervisor | reviewer | verifier | repairer

Scanner or indexer
└── Intelligence-role LoopNode
    profile = inventory | search | graph_query | evidence_retrieval

Validator or test executor
└── Solution-role LoopNode
    profile = validator | test_runner | migration_runner | effect_checker
```

Do not create SupervisorNode, ReviewNode, TestNode, StructureNode,
CodeAnalysisNode, or DevNode. Those would recreate the subclass
problem.

### 2.3 Supervisor versus router

```text
Review Router
├── makes one bounded dispatch decision
├── usually deterministic
├── does not maintain an extended supervisory context
└── returns immediately after routing

Review Supervisor
├── maintains the assurance goal
├── starts and monitors child reviews
├── adapts the review plan
├── reconciles disagreements
├── retries or replaces failed reviews
├── manages budgets and stop conditions
└── produces an integrated result
```

A router is generally an Intelligence- or Solution-role LoopNode. A
supervisor is generally a Practitioner-role LoopNode.

### 2.4 Child creation boundary

Use a child LoopNode when the review needs an independent goal, budget,
timeout, permission boundary, retry, evidence contract, result,
scheduling, or Chronicle identity. Otherwise use batched implementation
primitives.

Bad:

```text
50,000 files
└── 50,000 child LoopNodes
```

Better:

```text
Repository File Review LoopNode
├── partitions files into deterministic batches
├── processes batches using an adapter
├── streams findings
└── starts a child only for exceptional or ambiguous files
```

## 3. The recursive Practitioner hierarchy

### 3.1 Root: Repository Assurance Practitioner

The root can use the default nine-step Practitioner procedure as a Core
preset.

```text
Repository Assurance Practitioner
│
├── 1. Orient
│   ├── identify Git baseline
│   ├── identify worktree state
│   ├── determine requested review scope
│   ├── load repository identity
│   └── normalize the development request
│
├── 2. Reconcile Horizon
│   ├── determine whether this is precommit, PR, nightly, or release
│   ├── identify merge or release requirements
│   ├── identify protected architecture areas
│   └── define the final assurance objective
│
├── 3. Assess and Prepare
│   ├── load exact architecture rules
│   ├── load terminology rules
│   ├── load compatibility matrix
│   ├── inventory available analyzers and adapters
│   ├── build repository snapshot
│   └── determine missing evidence
│
├── 4. Decide Next
│   ├── calculate affected architecture domains
│   ├── calculate review risk
│   ├── select required supervisors
│   ├── select required scenarios
│   └── determine full versus incremental review
│
├── 5. Determine How
│   ├── bind static analyzers
│   ├── bind runtime observers
│   ├── bind storage adapters
│   ├── bind deterministic rules
│   ├── bind semantic reviewers
│   └── allocate review budgets
│
├── 6. Act
│   ├── start specialist supervisor LoopNodes
│   ├── run deterministic checks
│   ├── run runtime scenarios
│   ├── collect findings
│   └── collect proof records
│
├── 7. Verify
│   ├── independently reproduce blocking findings
│   ├── run negative fixtures
│   ├── run mutation checks
│   ├── verify evidence completeness
│   └── detect analyzer disagreement
│
├── 8. Integrate and Commit
│   ├── assemble the evidence graph
│   ├── assemble the conformance report
│   ├── stage repair candidates
│   ├── update review history
│   └── propose Learned Devtools Intelligence
│
└── 9. Route
    ├── PASS
    ├── PASS_WITH_DOCUMENTED_WARNINGS
    ├── BLOCKED
    ├── start repair Practitioner
    ├── request human review
    ├── rerun affected supervisors
    └── return findings to parent CI or OpenCode invocation
```

This is a Core default, not a hard-coded procedure. A custom
organization could replace it with a four-step fast review, a six-step
regulated review, parallel security and architecture review, an
iterative repair-and-reverify loop, or a release certification state
machine.

### 3.2 Specialist supervisor hierarchy

```text
1. Repository Understanding Supervisor
   ├── Git Inventory Intelligence Loop
   ├── Filesystem Inventory Intelligence Loop
   ├── Python Symbol Index Intelligence Loop
   ├── Import Graph Intelligence Loop
   ├── Static Call Graph Intelligence Loop
   ├── JSONL and Manifest Intelligence Loop
   ├── Schema Intelligence Loop
   ├── Documentation Intelligence Loop
   ├── Test Mapping Intelligence Loop
   └── Repository Snapshot Verification Loop

2. Static Conformance Supervisor
   ├── Folder Architecture Validator
   ├── Node Ontology Validator
   ├── Terminology Validator
   ├── Import Boundary Validator
   ├── Protected Call Validator
   ├── Contract and Schema Validator
   ├── Record Reference Validator
   ├── Plugin Boundary Validator
   ├── Provider Leakage Validator
   └── Documentation Drift Validator

3. Runtime Conformance Supervisor
   ├── Default Practitioner Scenario
   ├── Custom Practitioner Scenario
   ├── Deterministic Micro-Loop Scenario
   ├── Child Delegation Scenario
   ├── Permission Delegation Scenario
   ├── Model Invocation Scenario
   ├── External Effect Scenario
   ├── Repair and Reverification Scenario
   ├── Plugin Activation Scenario
   └── Chronicle Replay Scenario

4. Storage and Portability Supervisor
   ├── Core JSONL Review
   ├── DuckDB File Query Review
   ├── DuckDB Record Store Review
   ├── SQLite Review
   ├── PostgreSQL Review
   ├── Object Store Review
   ├── Portable Bundle Review
   ├── File and Database Synchronization Review
   ├── Alternative Query Engine Review
   └── Backend Substitution Review

5. Semantic Architecture Supervisor
   ├── Naming and Ontology Reviewer
   ├── Folder Boundary Reviewer
   ├── Conflation Reviewer
   ├── Provider Leakage Reviewer
   ├── Documentation Consistency Reviewer
   ├── Missing Test Reviewer
   ├── Portability Reviewer
   └── Adversarial Architecture Reviewer
```

The semantic reviewers may be independent LLM Practitioner children
with private contexts. Their outputs are finding candidates, not final
verdicts.

## 4. Devtools Core, Learned, and Plugins

### 4.1 Devtools Core

```text
Devtools Core Intelligence
├── architecture rules
├── terminology rules
├── standard review LoopNode definitions
├── supervisor definitions
├── review presets
├── proof obligations
├── negative fixture definitions
├── compatibility matrices
├── known prohibited structures
└── semantic review questions
```

### 4.2 Devtools Learned

```text
Devtools Learned Intelligence
├── approved regression patterns
├── accepted false-positive patterns
├── recurring architecture failures
├── successful repair patterns
├── observed performance baselines
├── accepted semantic findings
└── project-specific review strategies
```

Learned development intelligence must not be physically written into
the installed devtools source package. It can live in JSONL, DuckDB,
SQLite, PostgreSQL, or a remote development catalog.

### 4.3 Development Plugins

```text
Development Plugins
├── CodeQL adapter
├── Semgrep adapter
├── CodeGraph adapter
├── SCIP adapter
├── Tree-sitter adapter
├── Import Linter adapter
├── coverage adapter
├── mutation-testing adapter
├── database-specific analyzer
└── organization-specific policy pack
```

## 5. The "who reviews the reviewers" problem

A devtools hierarchy introduces circular trust. The system that
enforces rules may itself violate those rules. Four independent
protections are required.

### 5.1 Bootstrap verifier

A small deterministic verifier must run without importing Loop Engine.
It checks Python syntax, forbidden Node classes, forbidden paths,
package boundaries, basic manifests, architecture file validity, and
the devtools/runtime dependency direction. A broken LoopNode runtime
must never be able to disable all review.

### 5.2 Devtools reviews itself

The Repository Assurance Practitioner must include src/, devtools/,
dev_plugins/, conformance/, tests/, and .github/ in its scope. It must
not treat devtools/ as trusted or exempt.

### 5.3 Negative fixtures and mutation tests

Each reviewer must prove it still catches deliberately introduced
failures. Known bad fixtures must produce required findings. Known good
fixtures must produce no findings.

### 5.4 Independent final verification

The repair Practitioner must not be the final verifier.

```text
Review Practitioner
        ↓
Repair Candidate
        ↓
Independent Verification Practitioner
        ↓
Governance or human approval
```

## 6. Rule pinning

At review start, pin:

- architecture version;
- terminology version;
- conformance bundle version;
- rule content hashes;
- LoopNode definition versions;
- review profile versions;
- analyzer versions;
- plugin versions;
- model and prompt versions;
- repository commit;
- worktree snapshot;
- storage snapshot.

The rules must not change underneath the same run.

When a pull request changes the rules themselves, run:

```text
Baseline Rules
└── review proposed repository

Proposed Rules
└── review proposed repository

Rule Delta Review
├── findings removed
├── findings added
├── checks weakened
├── checks strengthened
├── new untested rules
└── potential self-exemption
```

A rule change that merely makes its own violation disappear must be
flagged.

## 7. Declared graph versus observed graph

The Repository Assurance Practitioner must maintain three graphs:

```text
Declared Architecture Graph
└── What architecture.yaml, manifests, contracts, and ports permit

Static Repository Graph
└── Files, symbols, imports, possible calls, references, and schemas

Observed Runtime Graph
└── Calls, effects, child spawns, stores, plugins, and versions
    actually observed in tests and scenarios
```

Then evaluate:

```text
Observed runtime relationships
            ⊆
Declared permitted relationships

Required declared relationships
            ⊆
Statically present or runtime-observed relationships
```

Findings include undeclared observed relationships, declared but
unreachable relationships, forbidden transitive dependencies,
unobserved critical paths, unresolved dynamic dispatch, stale declared
relationships, and duplicate relationship authority.

## 8. LLM reviewers inside the hierarchy

An LLM reviewer is a normal non-deterministic Practitioner child.

```text
Semantic Reviewer LoopNode
├── receives bounded evidence
├── receives exact invariant definitions
├── receives before/after repository graph slices
├── receives deterministic findings
├── answers a typed review contract
├── identifies ambiguity and likely drift
└── returns SemanticFindingCandidate[]
```

It may ask whether a new folder represents a stable architectural
boundary, whether a class creates a second ontology, whether an object
could be a typed field or record instead, whether a plugin introduces a
parallel runtime, whether an adapter leaks provider-specific semantics,
whether a README contradicts the implementation, whether a migration
leaves an obsolete duplicate active, whether a new rule weakens itself,
and whether new tests prove behavior or merely assert implementation.

It may not waive a deterministic violation, change permissions, change
the pinned rule bundle, approve its own repair, activate a plugin, or
alter a release verdict without evidence.

For high-risk changes, use several isolated semantic reviewers
(ontology, portability, security, migration, adversarial), then a
deterministic reconciler checks their structured findings.

## 9. Local, CI, and OpenCode use the same Practitioner

Do not implement local shell checks, GitHub YAML checks, OpenCode
checks, and release scripts as four unrelated systems. They all call
the same Devtools LoopNode definitions:

```bash
# Local changed-scope review
loop-dev assurance run \
  --preset devtools.core.review.precommit@1 \
  --changed

# Pull-request review
loop-dev assurance run \
  --preset devtools.core.review.pull_request@1 \
  --base origin/main

# Full repository review
loop-dev assurance run \
  --preset devtools.core.review.full@1

# Release review
loop-dev assurance run \
  --preset devtools.core.review.release@1 \
  --strict

# Semantic architecture question from OpenCode
loop-dev assurance ask \
  "Does this introduce a second runtime plugin system?" \
  --changed-only
```

## 10. Required repository structure

```text
loop-engine/
│
├── architecture.yaml
├── terminology.yaml
│
├── conformance/
│   ├── README.md
│   ├── invariants.yaml
│   ├── repository_structure.yaml
│   ├── relationship_rules.yaml
│   ├── import_boundaries.yaml
│   ├── protected_calls.yaml
│   ├── storage_profiles.yaml
│   ├── portability_rules.yaml
│   ├── compatibility_matrix.yaml
│   ├── migration_obligations.yaml
│   ├── plugin_boundaries.yaml
│   ├── proof_obligations.yaml
│   ├── failure_modes.yaml
│   ├── scenario_matrix.yaml
│   └── waivers.yaml
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
│           ├── bootstrap/
│           ├── assurance/
│           ├── intelligence/
│           │   └── core/
│           ├── plugin_host/
│           └── cli/
│
├── dev_plugins/
│   ├── codeql/
│   ├── semgrep/
│   ├── codegraph/
│   ├── scip/
│   ├── tree_sitter/
│   ├── mutation_testing/
│   └── organization_policy/
│
├── tests/
│   ├── devtools/
│   ├── conformance/
│   ├── negative_fixtures/
│   ├── meta_conformance/
│   └── end_to_end/
│
└── .loop-engine-dev/
    ├── repository_graph.duckdb
    ├── snapshots/
    ├── chronicles/
    ├── findings/
    ├── semantic_reviews/
    ├── repair_candidates/
    └── caches/
```

The dependency must be one-way:

```text
loop_engine_devtools
        ↓ imports public API from
loop_engine

loop_engine
        ✕ must never import
loop_engine_devtools
```

## 11. Required tests

### 11.1 Bootstrap tests

```text
test_bootstrap_runs_without_importing_loop_engine
test_bootstrap_detects_syntax_error
test_bootstrap_detects_forbidden_node_class
test_bootstrap_detects_forbidden_path
test_bootstrap_detects_import_direction_violation
test_bootstrap_passes_on_clean_tree
```

### 11.2 Assurance hierarchy tests

```text
test_assurance_runs_through_the_canonical_loop_kernel
test_assurance_verdict_is_typed
test_assurance_findings_are_typed
test_assurance_reports_evidence_counts
test_assurance_scope_precommit_is_smaller_than_full
test_assurance_strict_treats_warnings_as_blocking
test_assurance_repair_does_not_self_verify
```

### 11.3 Self-review tests

```text
test_devtools_reviews_itself
test_devtools_is_not_exempt_from_rules
test_negative_fixture_still_detected_after_devtools_change
test_mutation_in_devtools_is_killed
test_rule_change_that_hides_its_own_violation_is_flagged
```

### 11.4 Rule pinning tests

```text
test_review_pins_rule_versions
test_review_pins_repository_commit
test_rule_change_mid_review_is_refused
test_rule_delta_review_reports_weakened_checks
```

### 11.5 Graph conformance tests

```text
test_observed_relationships_are_subset_of_declared
test_required_relationships_are_present
test_undeclared_observed_relationship_is_found
test_declared_but_unreachable_relationship_is_found
test_unresolved_dynamic_dispatch_is_found
```

### 11.6 LLM reviewer tests

```text
test_llm_flags_provider_type_leak
test_llm_flags_parallel_plugin_system
test_llm_flags_semantic_folder_classification
test_llm_accepts_valid_new_adapter
test_llm_requests_review_for_ambiguous_boundary
test_llm_cannot_override_deterministic_failure
test_llm_output_validates_against_schema
test_llm_review_pins_prompt_and_model_version
test_llm_review_is_receipted
```

### 11.7 End-to-end scenarios

```text
Scenario A: clean repository passes full assurance
Scenario B: planted forbidden Node class blocks assurance
Scenario C: planted provider leak blocks assurance
Scenario D: planted missing README blocks assurance
Scenario E: planted rule change that hides its own violation is flagged
Scenario F: repair Practitioner fixes a finding and independent
             verification confirms it
Scenario G: LLM reviewer flags semantic drift that deterministic
             checks missed
Scenario H: assurance runs identically locally and in CI
```

## 12. Development workflow

- Phase 0: inventory. Read repository instructions, inspect current
  review and conformance code, inventory paths and symbols, identify
  production call paths, identify test gaps.
- Phase 1: adversarial decision record. Write the challenge report,
  select canonical terminology, document rejected alternatives, define
  invariants, define migration boundaries.
- Phase 2: bootstrap verifier. Implement the no-import bootstrap
  checks and their canary tests.
- Phase 3: assurance hierarchy. Implement the Repository Assurance
  Practitioner and specialist supervisors on the canonical Loop
  kernel.
- Phase 4: Devtools Core intelligence. Ship review presets, rules, and
  proof obligations as Core JSONL records.
- Phase 5: graph conformance. Implement the declared/static/observed
  graph comparison.
- Phase 6: LLM reviewers. Implement the bounded evidence packet, the
  typed review contract, and the no-waiver rule.
- Phase 7: CLI unification. Make local, CI, and OpenCode call the same
  assurance definitions.
- Phase 8: self-review. Prove devtools reviews itself and negative
  fixtures still fire.
- Phase 9: packaging. Build the devtools distribution, verify the
  one-way dependency, install cleanly.
- Phase 10: predeploy. Run one strict command returning PASS,
  PASS_WITH_DOCUMENTED_WARNINGS, or BLOCKED.

## 13. Prohibited shortcuts

Do not:

- create a second Node engine or runtime for devtools;
- create SupervisorNode, ReviewNode, or other node-named classes;
- exempt devtools from the rules it enforces;
- let an LLM reviewer waive deterministic violations;
- let the repair Practitioner verify its own repair;
- implement local, CI, and OpenCode review as separate systems;
- let rules change underneath a running review;
- let a rule change hide its own violation;
- create one child LoopNode per file by default;
- preserve the old shell-script review system beside the new one;
- claim completion because schemas exist;
- claim completion because unit tests pass while production paths
  still use legacy review code.

## 14. Required final deliverables

Return:

- architecture challenge report;
- selected canonical terminology;
- migration ledger;
- exact target and final repository trees;
- implemented bootstrap verifier;
- implemented assurance hierarchy;
- Devtools Core JSONL records and manifests;
- graph conformance implementation;
- LLM reviewer contract and no-waiver rule;
- unified CLI;
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

## 15. Final completion standard

The work is complete only when all of the following are true:

- Devtools is a first-class Loop Engine application on the shared
  kernel.
- The Repository Assurance Practitioner is an ordinary
  Practitioner-role LoopNode.
- Every supervisor, specialist, scanner, and reviewer is an ordinary
  LoopNode.
- No node-named class exists outside the LoopNode allowlist.
- The bootstrap verifier runs without importing Loop Engine.
- Devtools reviews itself and is not exempt.
- Negative fixtures and mutation tests prove every reviewer still
  detects violations.
- The repair Practitioner does not verify its own repair.
- Rules are pinned for every review run.
- Rule changes that hide their own violations are flagged.
- Observed relationships are a subset of declared relationships.
- LLM reviewers may identify drift but may not waive deterministic
  violations.
- Local, CI, and OpenCode call the same assurance definitions.
- The dependency direction is one-way: devtools imports loop_engine,
  never the reverse.
- A clean installation passes the assurance scenarios.
- The strict predeploy gate returns PASS.

If a requirement cannot be satisfied, return BLOCKED with concrete
evidence, the smallest unresolved issue, and the exact next
implementation step. Do not paper over the failure with documentation.
