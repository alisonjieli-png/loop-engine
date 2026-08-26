# Loop Engine Development Assurance Intelligence mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the senior architecture, implementation, migration, test,
security, and release harness for Loop Engine.

Aggressively inspect, adversarially challenge, revise, implement,
migrate, test, verify, document, and predeploy-gate the Development
Assurance Intelligence system described here. Do not stop at a design
memo.

You are explicitly authorized to:

- inspect every relevant source file, schema, record, manifest, test,
  migration, README, ADR, example, generated file, and package
  configuration;
- create a complete inventory of current review, conformance, finding,
  and development-tool concepts;
- rename, move, split, merge, rewrite, or delete obsolete modules and
  folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL
  records, database migrations, and persisted references;
- replace scattered finding and review logic with the typed assurance
  intelligence model;
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
two competing finding systems active. Do not satisfy this task with
documentation-only changes, empty folders, unreferenced schemas, unused
adapters, or new abstractions that production paths never call.

The task is complete only when the architecture is operational,
migrated, tested, packaged, documented, and the obsolete behavior is
absent or explicitly quarantined behind a time-bounded compatibility
shim.

Do not commit or push unless explicitly instructed. Preserve unrelated
concurrent work.

## 1. Mission

Implement the Development Assurance Intelligence system: the
devtools auditor's own intelligence domain with Core records, Learned
records, plugin contributions, query profiles, seeking strategies,
typed questions, proof obligations, finding definitions, finding
occurrences, finding patterns, evidence, and governance.

The governing invariant:

> The auditor should write down everything it observes, but it should
> only call something intelligence after the observation has been
> interpreted, evidenced, reviewed, and deliberately admitted into the
> Development Assurance Intelligence catalog.

Development Assurance Intelligence is an application domain. It is NOT
a second universal intelligence ontology and NOT a fifth constitutional
intelligence layer.

## 2. Architectural baseline

### 2.1 One runtime

Every actual audit operation is performed by an ordinary LoopNode,
using Practitioner, Intelligence, or Solution as its role. Never create
AuditNode, ReviewNode, TestNode, or other node-named classes.

### 2.2 Independent dimensions

```text
Application Domain
└── Development Assurance

Functional Intelligence Domains
├── Ask
├── Horizon
├── Readiness
├── Deliberation
├── Implementation
├── Execution
├── Verification
├── Integration
└── Routing

Perspectives
├── Repository
├── Architecture
├── Runtime
├── Storage
├── Compatibility
├── Security
├── Governance
├── Delivery
├── Experience
└── Assurance

Catalog Namespace
├── Core
├── Learned
└── Plugin:<plugin_id>

Artifact Kind
├── Assurance Question
├── Proof Obligation
├── Rule
├── Policy
├── Finding Pattern
├── Repair Pattern
├── Regression Pattern
├── Evidence Requirement
├── Review Profile
├── Seeking Strategy
├── Benchmark
└── Example
```

Functional Intelligence Domains are non-exclusive classifications. A
single audit record may support several domains simultaneously. Audit
findings must not be forced into one rigid layer or folder.

## 3. Four separate information repositories

```text
Development Assurance Plane
│
├── Assurance Intelligence Catalog
│   ├── Core Development Assurance Intelligence
│   ├── Learned Development Assurance Intelligence
│   └── Development Plugin Intelligence
│
├── Assurance Run Evidence
│   ├── repository snapshots
│   ├── analyzer outputs
│   ├── test results
│   ├── observed calls
│   ├── coverage
│   ├── compatibility handshakes
│   ├── command outputs
│   └── content-addressed evidence files
│
├── Finding Management
│   ├── finding occurrences
│   ├── triage decisions
│   ├── waivers
│   ├── remediation attempts
│   ├── verification results
│   └── regression relationships
│
└── Candidate Assurance Intelligence
    ├── proposed new rules
    ├── proposed question sets
    ├── proposed finding patterns
    ├── proposed repair patterns
    ├── proposed profiles
    └── proposed architecture guidance
```

### 3.1 Core Development Assurance Intelligence

Shipped with devtools and immutable by released version:

```text
Core
├── constitutional questions
├── architecture rules
├── standard assurance profiles
├── seeking strategies
├── proof obligations
├── known-good examples
├── known-bad examples
├── negative fixtures
├── standard remediation guidance
├── compatibility matrices
├── failure-mode definitions
└── predeployment gates
```

### 3.2 Audit-run evidence

Raw evidence from one review. This is not automatically persistent
intelligence. It may be incomplete, duplicated, wrong, stale, or
specific to one commit.

### 3.3 Finding occurrences

A finding occurrence says: a particular rule appears to have been
violated at a particular repository state. It does not yet say: this is
a universally valid, reusable lesson.

### 3.4 Learned Development Assurance Intelligence

Only reviewed and generalized knowledge becomes Learned Intelligence:

```text
Learned
├── recurring violation patterns
├── repository-specific architecture precedents
├── confirmed false-positive patterns
├── accepted repair strategies
├── regression signatures
├── stable performance baselines
├── tool reliability observations
├── effective review strategies
├── approved compatibility exceptions
└── historically successful proof combinations
```

The reviewing or repair-producing Practitioner must not approve its own
proposed intelligence.

## 4. Assurance claims

The auditor should construct an assurance case for important claims.

```text
Assurance Claim
├── claim
├── scope
├── assumptions
├── supporting arguments
├── evidence
├── counterevidence
├── unresolved uncertainties
├── confidence
├── conclusion
└── validity period
```

Example:

```text
Claim:
    LoopNode is the only concrete operational Node at commit abc123.

Supporting Evidence:
├── complete AST class scan
├── public symbol scan
├── plugin contribution scan
├── runtime instance-type observations
├── negative fixture successfully rejected
└── mutation introducing ConfigurationNode caused the gate to fail

Counterevidence:
└── none found

Uncertainty:
└── dynamically loaded external plugins were not installed in this run

Verdict:
└── supported within declared review scope
```

## 5. Default intelligence questions

Each custom auditor Practitioner may use any questions in any order.
The following are Core defaults, not hard-coded steps.

### 5.1 Ask Intelligence

```text
What change, review, or release is being requested?
What exact repository state is under review?
Is the scope changed files, one subsystem, one plugin, one migration,
the full repository, or a release artifact?
Which branches, commits, worktree modifications, generated files,
submodules, plugin packages, and external stores are included?
What does the requester expect the auditor to prove?
What is explicitly outside the review scope?
Are there uncommitted or untracked files that materially change the
review result?
```

### 5.2 Horizon Intelligence

```text
What architectural outcome is this change intended to support?
Does the immediate implementation preserve the long-term ontology?
Does this change move toward or away from one LoopNode runtime,
portable intelligence, replaceable adapters, explicit compatibility,
reproducible runs, controlled extensibility, and independent
governance?
What downstream systems will consume this code, schema, record,
database, plugin, or bundle?
What will become harder to migrate, replace, test, or remove later?
Does a local convenience introduce permanent architectural debt?
```

### 5.3 Readiness Intelligence

```text
Is the repository snapshot complete?
Are all relevant files indexed?
Are manifests, schemas, architecture rules, and terminology rules
current?
Are Core JSONL records loadable?
Are generated indexes fresh?
Are database and file snapshots mutually consistent?
Are required analyzers installed and compatible?
Are plugin manifests and entry points discoverable?
Are migrations available for every affected version transition?
Are tests, negative fixtures, and golden datasets available?
What evidence cannot currently be collected?
```

### 5.4 Deliberation Intelligence

```text
Which review profiles should run?
Which checks are mandatory versus risk-triggered?
Should this change receive fast deterministic review, full repository
review, semantic architecture review, security review, storage
substitution review, migration review, plugin review, or release
certification?
What competing interpretations of the architecture exist?
Could the same object be metadata instead of a folder, a preset
instead of a subclass, a typed field instead of a new service, an
adapter instead of a new ontology, or a record instead of hard-coded
behavior?
What is the strongest counterargument against accepting the change?
Which evidence would distinguish the competing interpretations?
```

### 5.5 Implementation Intelligence

```text
Where is the governing invariant defined?
Which schema, rule, contract, policy, or port enforces it?
Which static analyzers can check it?
Which runtime observers can check it?
Which negative fixtures prove the detector works?
Which migrations update affected records and references?
Which adapter conformance kits apply?
Which previous fixes or implementation patterns are reusable?
Does an existing rule already cover this condition?
Would a new rule duplicate or conflict with another rule?
```

### 5.6 Execution Intelligence

```text
Which exact commands and LoopNode definitions should run?
Which commit, worktree snapshot, rule bundle, profile version, tool
version, database snapshot, and plugin version are pinned?
Which checks can run in parallel?
Which checks require exclusive access?
Which checks have side effects?
Which databases, files, services, or containers will be used?
What are the time, memory, query, model, and child-Loop budgets?
What happens if an analyzer, database, plugin, or remote service fails?
Can the review resume from a checkpoint?
Can it be rerun reproducibly?
```

### 5.7 Verification Intelligence

```text
What evidence is sufficient to support each assurance claim?
Was every production file examined or explicitly excluded?
Was every protected relationship checked?
Were runtime-critical paths actually observed?
Did intentionally invalid fixtures fail?
Did mutations of critical guards cause tests to fail?
Did file-backed and database-backed adapters return equivalent results?
Did a clean wheel installation reproduce the result?
Did an independent verifier reproduce blocking findings?
Are there contradictory analyzer results?
Is the evidence current for the exact reviewed commit and
configuration?
What remains unproven?
```

### 5.8 Integration Intelligence

```text
Where should the finding occurrence be stored?
Which evidence files and hashes belong to it?
Does it update a prior finding or create a new one?
Is it a regression of a resolved finding?
Which issue, pull request, invariant, file, symbol, record, plugin,
migration, or adapter should it reference?
Should the result generate a remediation candidate, a new regression
test, a new negative fixture, a new audit question, a new analyzer
rule, a new Learned finding pattern, or an architecture-decision
candidate?
What documentation, manifest, schema, or compatibility matrix must be
updated?
Can the evidence be exported portably?
```

### 5.9 Routing Intelligence

```text
Should the result be PASS, PASS_WITH_DOCUMENTED_WARNINGS, BLOCKED,
NEEDS_HUMAN_REVIEW, NEEDS_MORE_EVIDENCE, NEEDS_REPAIR, or
INDETERMINATE?
Should the auditor run another analyzer, expand review scope, request
an independent LLM reviewer, spawn a repair Practitioner, rerun only
affected checks, request approval, or stop?
Can a warning be accepted temporarily?
Does a waiver exist?
Is the waiver current, scoped, justified, independently approved, and
non-expired?
What must happen before the finding can be closed?
```

## 6. Specialized question packs

The auditor should have reusable, versioned Assurance Question Packs.

```text
Core Assurance Question Packs
│
├── Change and Scope
├── Node and LoopNode Ontology
├── Repository Structure
├── Naming and Terminology
├── Import and Dependency Boundaries
├── Calls, Effects, and Permissions
├── Contracts, Schemas, and References
├── Intelligence Ontology
├── Storage Authority
├── File and Database Synchronization
├── Portability and Adapter Substitution
├── Query Semantics
├── Versioning and Compatibility
├── Migrations and Rollback
├── Runtime Plugins
├── Development Plugins
├── Security and Trust Boundaries
├── Tenant and Scope Isolation
├── Tests and Proof Coverage
├── Documentation Drift
├── Packaging and Clean Installation
├── Performance and Resource Use
├── Runtime Chronicle and Observability
├── Governance and Review Independence
├── Historical Regression
└── Auditor Self-Conformance
```

### 6.1 Node and LoopNode ontology pack

```text
Does any concrete class other than LoopNode represent an operational
Node?
Does any class name end in Node without being LoopNode?
Does any plugin define a Node kind?
Are Practitioner, Intelligence, or Solution implemented as subclasses?
Are deterministic, hybrid, or non-deterministic implemented as
subclasses?
Is a preset being mistaken for a subclass?
Is a typed internal object being described as a Node?
Does any second executor instantiate operational objects?
```

### 6.2 Repository structure pack

```text
Does every semantic folder have a local ontology README?
Does every production file have an architectural owner?
Did this change create an unapproved top-level directory?
Does a folder represent stable ownership or merely one classification?
Is mutable Learned data stored under src/?
Are plugin implementations inside a plugin host?
Are development dependencies included in the runtime package?
Did a rename leave a parallel legacy structure active?
```

### 6.3 Portability and adapter substitution pack

```text
Does provider-specific code escape its adapter?
Does a public model expose DuckDB, SQLAlchemy, DataFusion, PostgreSQL,
or another provider type?
Can the base package import without the optional provider installed?
Does the adapter accurately declare its supported protocols?
Does it pass the same conformance kit as alternative adapters?
Can another engine replace it without changing LoopNode,
IntelligenceRecord, or persisted backend-neutral definitions?
Is degradation explicit and receipted?
```

### 6.4 Storage authority pack

```text
Which materialization is authoritative?
Can a file and database accept independent writes?
Is replication idempotent?
Are content hashes preserved?
Can interrupted synchronization resume safely?
Can a stale replica claim to be current?
Are tombstones and revocations propagated?
Can a portable export be reimported without identity loss?
```

### 6.5 Auditor self-conformance pack

```text
Does the auditor inspect devtools itself?
Can disabling a rule make its own violation disappear?
Does every rule have a positive and negative fixture?
Does every constitutional rule have more than one proof mechanism?
Can an LLM reviewer waive a deterministic finding?
Can a repair Practitioner approve its own repair?
Are analyzer versions and rule hashes pinned?
Can the audit be reproduced from a clean checkout?
```

## 7. Auditor profiles

A profile composes question packs, seeking strategies, proof
requirements, budgets, and routing rules.

```text
Core Auditor Profiles
│
├── Fast Precommit
├── Pull Request
├── Full Repository
├── Release Certification
├── Ontology Change
├── Repository Reorganization
├── Storage Backend Substitution
├── Query Engine Substitution
├── Database Migration
├── Plugin Installation
├── Plugin Upgrade
├── Security High Assurance
├── Semantic Architecture Review
├── Performance Regression
├── Incident and Regression
├── Repair Verification
└── Auditor Meta-Audit
```

### 7.1 Fast Precommit

```text
Scope: changed files and affected graph neighborhood
Primary strategy: diff-first
Checks: deterministic only by default
Evidence: syntax, structure, imports, references, focused tests
Routing: block clear violations; defer broad semantic questions to PR
review
```

### 7.2 Pull Request

```text
Scope: changed files plus transitive architectural impact
Primary strategies: diff-first, invariant-first, graph expansion
Evidence: static proofs, affected runtime scenarios, changed negative
fixtures, changed documentation
```

### 7.3 Release Certification

```text
Scope: full repository, packages, plugins, migrations, and release
artifacts
Primary strategies: proof-obligation-first, independent replication,
adversarial review
Evidence: full static graph, full test matrix, clean installation,
adapter conformance, backup and restore, historical replay
```

### 7.4 Storage Backend Substitution

```text
Scope: old adapter, new adapter, query semantics, migrations, rollback
Primary strategies: cross-backend differential, shadow execution,
failure injection
Evidence: golden-query equivalence, round-trip identity preservation,
concurrency behavior, performance baselines, fallback and rollback
```

### 7.5 Semantic Architecture Review

```text
Scope: ambiguous names, folders, object boundaries, ontology changes
Primary strategies: adversarial semantic review,
alternative-structure generation, negative-space search
Evidence: before and after trees, architecture rules, terminology
contract, graph slices, alternative designs, deterministic findings
```

### 7.6 Auditor Meta-Audit

```text
Scope: devtools, rules, profiles, analyzers, fixtures, and gates
Primary strategies: self-conformance, mutation testing, rule-delta
review, independent reviewer
Evidence: negative fixtures, detector precision, detector recall on
known cases, rule-change impact, attempts to bypass gates
```

## 8. Assurance seeking strategies

```text
Assurance Seeking Strategies
│
├── Diff First
│   └── Start with changed files, then expand through relationships
├── Invariant First
│   └── Select the constitutional rules affected by the change
├── Graph First
│   └── Traverse imports, calls, references, tests, and migrations
├── Proof Obligation First
│   └── Start from claims that must be proven
├── Risk Weighted
│   └── Allocate review effort according to impact and irreversibility
├── Counterexample First
│   └── Actively search for a violating example
├── Negative Space
│   └── Search for missing tests, missing documentation, missing
│       guards, unowned files, and unobserved critical paths
├── Differential
│   └── Compare old versus new implementation or backend
├── Historical Regression
│   └── Search previous failures, fixes, waivers, and regressions
├── Independent Replication
│   └── Ask a separate verifier to reproduce evidence
├── Rule Delta
│   └── Compare baseline and proposed conformance rules
├── Repair and Reverify
│   └── Validate the fix and rerun the original failing proof
└── Meta-Conformance
    └── Review the auditor, rules, profiles, and analyzers themselves
```

A custom auditor Practitioner can combine these. A repository
reorganization audit might use Diff First, Graph First, Invariant
First, Negative Space, and Independent Replication.

## 9. Typed audit question definitions

Questions must not exist only as English text.

```text
AssuranceQuestionDefinition
├── question_id
├── version
├── title
├── question_text
├── claim_template
├── applicable_when
├── target_selectors
├── invariant_refs
├── required_evidence_kinds
├── accepted_proof_methods
├── minimum_independent_proofs
├── preferred_analyzers
├── negative_fixture_refs
├── severity_if_failed
├── confidence_policy
├── failure_routing
├── remediation_guidance_refs
├── tags
└── documentation
```

Example:

```json
{
  "question_id": "devtools.question.only_loopnode_is_operational",
  "version": "1.0.0",
  "question_text": "Does the repository define any concrete operational Node other than LoopNode?",
  "claim_template": {
    "subject": "repository_snapshot",
    "predicate": "has_only_operational_node_type",
    "object": "loop_engine.node.loop_node.LoopNode"
  },
  "applicable_when": { "always": true },
  "target_selectors": [
    "python_classes",
    "plugin_contributions",
    "runtime_instance_types"
  ],
  "required_evidence_kinds": [
    "static_class_scan",
    "plugin_manifest_scan",
    "runtime_instance_observation",
    "negative_fixture_result"
  ],
  "minimum_independent_proofs": 2,
  "severity_if_failed": "constitutional",
  "failure_routing": "blocked"
}
```

## 10. Findings need three distinct objects

Do not use one overloaded Finding object.

```text
FindingDefinition
└── Reusable description of a detectable problem

FindingOccurrence
└── One observation of that problem in one repository snapshot

FindingPattern
└── Reviewed reusable intelligence generalized from occurrences
```

### 10.1 Finding definition

```text
FindingDefinition
├── finding_type_id
├── rule_ref
├── invariant_refs
├── default severity
├── affected artifact kinds
├── evidence requirements
├── remediation guidance
└── verification requirements
```

### 10.2 Finding occurrence

```text
FindingOccurrence
├── occurrence_id
├── finding_type_ref
├── assurance_run_id
├── repository snapshot
├── commit
├── worktree hash
├── affected paths
├── affected symbols
├── affected record refs
├── relationship path
├── evidence refs
├── analyzer refs and versions
├── confidence
├── reproducibility
├── first seen
├── last seen
├── baseline relationship
├── triage status
├── remediation status
├── verification status
├── waiver ref
└── Chronicle refs
```

### 10.3 Finding pattern

```text
FindingPattern
├── generalized conditions
├── known causes
├── confirmed examples
├── rejected examples
├── reliable detection methods
├── known false-positive conditions
├── repair patterns
├── regression signatures
├── evidence quality
└── governance approval
```

SARIF is the appropriate interchange format for static-analysis
results. The canonical Loop Engine occurrence model can be richer,
while supporting SARIF import and export for GitHub, IDE, and tool
interoperability.

## 11. Finding lifecycle

Avoid a single ambiguous status.

```text
Detection Status
├── detected
├── reproduced
├── not_reproduced
└── stale

Triage Status
├── unreviewed
├── investigating
├── confirmed
├── false_positive
├── duplicate
└── disputed

Remediation Status
├── not_started
├── proposed
├── in_progress
├── applied
├── failed
└── not_applicable

Verification Status
├── not_verified
├── passed
├── failed
├── partially_passed
└── indeterminate

Governance Decision
├── open
├── accepted_risk
├── waived
├── blocked
├── resolved
├── revoked
└── archived
```

A normal lifecycle is:

```text
Detected
    ↓
Reproduced
    ↓
Triaged
    ├── False Positive
    ├── Duplicate
    └── Confirmed
            ↓
       Remediation Proposed
            ↓
       Remediation Applied
            ↓
       Independent Reverification
            ├── Failed
            │    └── Reopen or Repair Again
            └── Passed
                 └── Resolved
                         ↓
                    Later Recurrence
                         └── Regression
```

Suppressions or waivers require typed scope, justification, approver,
expiration, compensating controls, and recheck conditions.

## 12. Promotion into Learned Assurance Intelligence

```text
Finding Occurrence
        ↓
Confirmed Finding
        ↓
Several occurrences or strong reusable evidence
        ↓
Pattern Generalization Practitioner
        ↓
Candidate Finding Pattern
        ↓
Independent Evaluation
        ↓
Independent Governance Review
        ├── Rejected
        └── Approved
            ↓
Learned Development Assurance Intelligence
```

Possible promoted artifacts include finding patterns, repair patterns,
regression signatures, question definitions, proof obligations,
analyzer rules, negative fixtures, auditor profiles, seeking
strategies, and architecture guidance.

A raw finding should never be promoted merely because an LLM described
it convincingly.

## 13. Evidence must be immutable and independently addressable

```text
AssuranceEvidence
├── evidence_id
├── evidence_kind
├── producing LoopNode
├── producing tool and version
├── producing rule bundle and hash
├── repository commit
├── worktree snapshot hash
├── store snapshot
├── command or query
├── structured result
├── file or blob refs
├── content hash
├── timestamp
├── scope
├── trust level
├── reproducibility instructions
└── retention policy
```

Every policy or gate decision must receipt the exact rule bundle and
input snapshot.

## 14. Recommended physical organization

```text
devtools/
├── README.md
├── pyproject.toml
└── src/
    └── loop_engine_devtools/
        ├── assurance/
        │   ├── README.md
        │   ├── model/
        │   │   ├── assurance_question_definition.py
        │   │   ├── assurance_claim.py
        │   │   ├── assurance_evidence.py
        │   │   ├── finding_definition.py
        │   │   ├── finding_occurrence.py
        │   │   ├── finding_pattern.py
        │   │   ├── proof_obligation.py
        │   │   ├── waiver.py
        │   │   ├── remediation_candidate.py
        │   │   ├── verification_result.py
        │   │   └── assurance_snapshot.py
        │   ├── questions/
        │   │   ├── question_resolver.py
        │   │   ├── applicability.py
        │   │   └── proof_planner.py
        │   ├── findings/
        │   │   ├── occurrence_manager.py
        │   │   ├── baseline_comparator.py
        │   │   ├── deduplicator.py
        │   │   ├── triage.py
        │   │   └── lifecycle.py
        │   ├── evidence/
        │   │   ├── collector.py
        │   │   ├── verifier.py
        │   │   ├── content_hashing.py
        │   │   └── export.py
        │   ├── profiles/
        │   │   ├── profile_resolver.py
        │   │   └── profile_binding.py
        │   ├── reporting/
        │   │   ├── console.py
        │   │   ├── json.py
        │   │   ├── sarif.py
        │   │   ├── html.py
        │   │   └── github.py
        │   └── governance/
        │       ├── candidate_staging.py
        │       ├── independent_review.py
        │       └── promotion.py
        ├── intelligence/
        │   └── core/
        │       ├── README.md
        │       ├── manifest.json
        │       ├── records/
        │       │   └── part-00000.jsonl
        │       └── files/
        │           └── sha256/
        └── plugin_host/
```

Mutable run and Learned state must remain outside the installed
devtools package:

```text
.loop-engine-dev/
└── assurance/
    ├── local.duckdb
    ├── runs/
    ├── evidence/
    │   └── sha256/
    ├── findings/
    ├── snapshots/
    ├── candidate_intelligence/
    ├── exports/
    │   ├── sarif/
    │   └── portable_bundles/
    └── caches/
```

A server deployment can use PostgreSQL plus object storage. The
logical IDs and schemas must remain identical.

## 15. Default auditor-profile object

```text
DevelopmentAssuranceProfile
├── profile_id
├── profile_version
├── applicable_change_traits
├── question_pack_refs
├── question_priorities
├── intelligence_seeking_strategy_refs
├── required_proof_methods
├── minimum_independent_proofs
├── required_analyzers
├── optional_analyzers
├── negative_fixture_requirements
├── mutation_test_requirements
├── runtime_scenario_requirements
├── storage_profile_requirements
├── evidence_quality_thresholds
├── confidence_policy
├── review_budget
├── LLM review policy
├── human review policy
├── routing policy
└── receipt policy
```

Example:

```json
{
  "profile_id": "devtools.core.profile.ontology_change",
  "profile_version": "1.0.0",
  "question_pack_refs": [
    "devtools.core.questions.node_ontology@1",
    "devtools.core.questions.terminology@1",
    "devtools.core.questions.repository_structure@1",
    "devtools.core.questions.compatibility@1",
    "devtools.core.questions.migration@1",
    "devtools.core.questions.documentation@1"
  ],
  "seeking_strategy_refs": [
    "devtools.core.strategy.invariant_first@1",
    "devtools.core.strategy.negative_space@1",
    "devtools.core.strategy.independent_replication@1"
  ],
  "required_proof_methods": [
    "static_analysis",
    "runtime_scenario",
    "negative_fixture"
  ],
  "minimum_independent_proofs": 2,
  "routing_policy": {
    "constitutional_failure": "blocked",
    "unresolved_semantic_ambiguity": "needs_human_review"
  }
}
```

## 16. Critical guardrails

1. Development Assurance Intelligence is an application domain, not a
   second universal intelligence ontology.
2. Raw run evidence is not Learned Intelligence.
3. A finding occurrence is not automatically a reusable finding
   pattern.
4. Every finding must point to exact evidence.
5. Evidence must pin the repository snapshot, rule bundle, analyzer,
   profile, plugin, model, prompt, and store versions used.
6. LLM findings are candidates until reproduced or supported by other
   evidence.
7. An LLM may identify semantic risk but cannot waive a deterministic
   constitutional violation.
8. A repair-producing Practitioner cannot be the only verifier of its
   repair.
9. A rule-changing Practitioner cannot approve its own proposed rule.
10. Suppressions and waivers require scope, justification, owner,
    approval, expiration, and recheck conditions.
11. Findings must survive file/database export and import without
    losing identity, evidence, or lifecycle history.
12. A finding that disappears because the rule was weakened must be
    reported by the Rule Delta profile.
13. Auditor rules and analyzers must have positive fixtures, negative
    fixtures, and mutation tests.
14. Devtools itself must remain inside the review scope.
15. Every release verdict should be expressible as an assurance claim
    linked to supporting and opposing evidence.

## 17. Required tests

```text
test_assurance_intelligence_is_an_application_domain
test_no_fifth_constitutional_intelligence_layer
test_audit_operations_run_through_ordinary_loop_nodes
test_no_audit_node_class

test_core_questions_load_from_jsonl
test_question_definitions_validate
test_question_packs_resolve
test_question_applicability_is_typed
test_question_requires_evidence_kinds

test_finding_definition_occurrence_pattern_are_distinct
test_occurrence_pins_repository_snapshot
test_occurrence_pins_rule_bundle_hash
test_occurrence_lifecycle_transitions_are_typed
test_occurrence_round_trips_through_file_and_database
test_sarif_export_and_import_preserve_identity

test_raw_evidence_is_not_learned_intelligence
test_finding_occurrence_is_not_a_finding_pattern
test_pattern_promotion_requires_independent_review
test_repair_practitioner_cannot_verify_its_own_repair
test_rule_changing_practitioner_cannot_approve_its_own_rule

test_waiver_requires_scope_owner_expiration
test_expired_waiver_blocks
test_rule_delta_reports_weakened_checks
test_finding_disappearing_with_weakened_rule_is_reported

test_llm_finding_is_candidate_until_reproduced
test_llm_cannot_waive_deterministic_violation
test_llm_review_pins_prompt_and_model_versions

test_auditor_meta_audit_reviews_devtools
test_negative_fixture_still_detected_after_devtools_change
test_mutation_in_auditor_is_killed

test_evidence_is_content_addressed
test_evidence_pins_versions
test_evidence_export_and_import_preserve_hashes
```

## 18. Development workflow

- Phase 0: inventory. Read repository instructions, inspect current
  review and finding code, inventory paths and symbols, identify test
  gaps.
- Phase 1: adversarial decision record. Write the challenge report,
  select canonical terminology, document rejected alternatives, define
  invariants, define migration boundaries.
- Phase 2: typed models. Implement assurance question definitions,
  claims, evidence, finding definitions, occurrences, patterns, proof
  obligations, waivers, and profiles.
- Phase 3: Core intelligence. Ship the default question packs,
  profiles, strategies, and proof obligations as Core JSONL records.
- Phase 4: finding lifecycle. Implement detection, triage,
  remediation, verification, and governance state machines.
- Phase 5: evidence. Implement content-addressed evidence collection,
  version pinning, and portable export.
- Phase 6: promotion. Implement candidate staging, independent review,
  and promotion into Learned Assurance Intelligence.
- Phase 7: reporting. Implement console, JSON, SARIF, HTML, and GitHub
  reports.
- Phase 8: self-review. Prove the auditor reviews itself and negative
  fixtures still fire.
- Phase 9: packaging. Build the devtools distribution, verify the
  one-way dependency, install cleanly.
- Phase 10: predeploy. Run one strict command returning PASS,
  PASS_WITH_DOCUMENTED_WARNINGS, or BLOCKED.

## 19. Prohibited shortcuts

Do not:

- create a fifth constitutional intelligence layer;
- create AuditNode, ReviewNode, or other node-named classes;
- treat raw run evidence as Learned Intelligence;
- treat a finding occurrence as a reusable pattern;
- let an LLM waive deterministic violations;
- let a repair Practitioner verify its own repair;
- let a rule-changing Practitioner approve its own rule;
- allow waivers without scope, owner, and expiration;
- let a rule change hide its own violation;
- preserve the old finding system beside the new one;
- claim completion because schemas exist;
- claim completion because unit tests pass while production paths
  still use legacy review code.

## 20. Required final deliverables

Return:

- architecture challenge report;
- selected canonical terminology;
- migration ledger;
- exact target and final repository trees;
- implemented typed models;
- Devtools Core JSONL records and manifests;
- finding lifecycle implementation;
- evidence implementation;
- promotion and governance implementation;
- reporting implementations;
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

## 21. Final completion standard

The work is complete only when all of the following are true:

- Development Assurance Intelligence is an application domain, not a
  fifth constitutional layer.
- Every audit operation runs through ordinary LoopNodes.
- Core questions, profiles, strategies, and proof obligations ship as
  versioned records.
- Finding definitions, occurrences, and patterns are distinct typed
  objects.
- Raw evidence, finding occurrences, candidate intelligence, and
  Learned intelligence are separate repositories.
- Evidence pins repository snapshot, rule bundle, analyzer, profile,
  plugin, model, prompt, and store versions.
- Promotion into Learned Assurance Intelligence requires independent
  review.
- The repair Practitioner does not verify its own repair.
- The rule-changing Practitioner does not approve its own rule.
- Waivers require scope, justification, owner, approval, expiration,
  and recheck conditions.
- LLM findings are candidates until reproduced.
- LLM reviewers may identify drift but may not waive deterministic
  violations.
- Findings survive file/database export and import without identity
  loss.
- The auditor reviews itself and negative fixtures still fire.
- A clean installation passes the assurance scenarios.
- The strict predeploy gate returns PASS.

If a requirement cannot be satisfied, return BLOCKED with concrete
evidence, the smallest unresolved issue, and the exact next
implementation step. Do not paper over the failure with documentation.
