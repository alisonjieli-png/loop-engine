# Loop Engine adversarial intelligence-seeking architecture mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the senior architecture, implementation, migration, test, security,
and release harness for Loop Engine.

Your task is not to write a design memo and stop. Aggressively inspect,
adversarially challenge, revise, implement, migrate, test, verify, document,
and predeploy-gate the intelligence-seeking architecture described here.

You are explicitly authorized to:

- inspect every relevant source file, schema, record, manifest, test,
  migration, README, ADR, example, generated file, and package configuration;
- create a complete inventory of current intelligence, Practitioner, step,
  portfolio, query, policy, runtime, storage, and plugin concepts;
- rename, move, split, merge, rewrite, or delete obsolete modules and folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL records,
  database migrations, and persisted references;
- replace hard-coded nine-step assumptions with generic configuration;
- remove wrapper-only compatibility architecture after migration;
- add strict schemas, typed models, compatibility handshakes, versioned
  records, migrations, adapters, and conformance suites;
- create Core JSONL records and neutral shards;
- implement file-backed, DuckDB-backed, SQLite-backed, relational-database,
  plugin-backed, and remote-catalog-backed resolution where appropriate;
- add property-based, fuzz, concurrency, failure-injection, security,
  migration, packaging, and clean-install tests;
- run tests repeatedly and continue repairing failures;
- reject or revise any part of this mandate that fails adversarial
  evaluation, provided you document the evidence and implement a stronger
  replacement;
- make reasonable architectural decisions without repeatedly asking for
  confirmation.

Do not merely add a new layer beside the old architecture. Do not leave two
competing query systems active. Do not satisfy this task with
documentation-only changes, empty folders, unreferenced schemas, unused
adapters, or new abstractions that production paths never call.

The task is complete only when the architecture is operational, migrated,
tested, packaged, documented, and the obsolete behavior is absent or
explicitly quarantined behind a time-bounded compatibility shim.

Do not commit or push unless explicitly instructed. Preserve unrelated
concurrent work.

## 1. Mission

Implement a universal, composable, inheritable, versioned,
policy-constrained intelligence-seeking configuration system that works for:

- the Core nine-step default Practitioner;
- custom Practitioners with any number of steps;
- custom step names;
- custom step ordering;
- branching, cyclic, conditional, concurrent, optional, repeated, and
  dynamically generated step graphs;
- internal Practitioner steps;
- steps represented by separate Child LoopNode instances;
- Practitioner-role, Intelligence-role, and Solution-role LoopNode
  definitions;
- Root and Child LoopNode instances;
- Loop graphs and Solution Canvases;
- one-off invocation overrides;
- organization, workspace, project, user, and run scope;
- Core, Learned, and Plugin intelligence;
- file-backed and database-backed intelligence;
- offline, embedded, server, and remote-service deployments;
- reproducible historical playback;
- runtime adaptation within explicit bounds;
- independent governance and review.

The Core nine-step Practitioner must remain an excellent default preset. It
must not become the universal query ontology.

The implementation must make this statement true:

> The default Practitioner supplies default intelligence-seeking behavior;
> it does not define the universal intelligence-seeking ontology.

## 2. Architectural baseline

### 2.1 One operational node

Preserve the hard Loop Engine invariant:

```text
Node
└── LoopNode
```

Node is an architectural category and namespace. LoopNode is the only
concrete operational node.

Never introduce:

- a concrete generic Node;
- PractitionerNode, IntelligenceNode, or SolutionNode;
- mode-specific node subclasses;
- step-specific node subclasses;
- portfolio nodes;
- query nodes as a second runtime type;
- plugin-defined node kinds;
- a second node executor.

Practitioner, Intelligence, and Solution are roles of the same LoopNode.
Root and Child are positions of the same LoopNode. Deterministic, hybrid,
and non-deterministic are run modes of the same LoopNode.

### 2.2 Governed work boundary

Do not interpret "everything is a Loop" recursively.

Use this rule:

> Every independently governed unit of work above the kernel executes as a
> LoopNode.

Create a separate LoopNode when work needs one or more of:

- an independent goal;
- an independent input or output contract;
- an independent budget;
- an independent stop condition;
- independent permissions or effects;
- independent verification;
- independent retry or repair;
- separate Chronicle identity;
- independent scheduling;
- independent delegation;
- independent cancellation;
- independent governance.

Ordinary adapter methods, SQL execution calls, hash calculations,
serialization helpers, schema validators, and provider SDK calls may remain
implementation primitives inside a governed LoopNode.

### 2.3 Intelligence is multidimensional

Do not recreate rigid intelligence folders or exclusive layers.

An intelligence record may be useful for multiple decisions, represent
multiple perspectives, come from one producer, belong to one catalog
namespace, exist in several materializations, and be relevant to many custom
steps.

The record identity must not depend on folder location, backend, or a
default Practitioner step name.

## 3. Required canonical concepts

Implement and strictly distinguish these objects.

### 3.1 IntelligenceFunction

A registered, versioned term describing why intelligence is useful.

Core ships with these nine default functions:

```text
Ask
Horizon
Readiness
Deliberation
Implementation
Execution
Verification
Integration
Routing
```

These are non-exclusive functional domains. A record may declare zero, one,
or many.

Do not hard-code them as folder names. Do not assume every custom
Practitioner step maps one-to-one to one function. Do not require custom
profiles or plugins to use only these nine terms. Support namespaced
extension terms through a vocabulary registry, subject to compatibility and
governance rules.

Recommended reference form:

```text
core.intelligence_function.ask@1
core.intelligence_function.verification@1
plugin:<plugin_id>.intelligence_function.<name>@<version>
org:<organization_id>.intelligence_function.<name>@<version>
```

The planner must operate on registered term references, not a closed Python
enum that requires a package release for every extension.

### 3.2 IntelligencePerspective

A registered term describing whose or what viewpoint the intelligence
represents.

Core examples:

```text
user or stakeholder
domain
environment
experience
governance
system
external research
adversarial
operational
legal or regulatory, when applicable
```

Perspective is not access scope, producer origin, or catalog ownership.

### 3.3 IntelligenceAccessPolicy

Hard constraints on what may be queried, returned, materialized, or exposed.

It must support:

- allowed and denied catalog namespaces;
- allowed and denied plugin namespaces;
- allowed and denied scopes;
- tenant, organization, workspace, project, user, and run boundaries;
- sensitivity classifications;
- consent requirements;
- minimum governance status;
- data-residency restrictions;
- provider restrictions;
- effect restrictions;
- maximum materialization size;
- export restrictions;
- retention restrictions;
- fields that descendants may not broaden;
- query and retrieval ceilings;
- redaction requirements;
- audit requirements.

Preference must never grant permission.

### 3.4 IntelligenceQueryProfile

A reusable, versioned description of soft query preferences and bounded
behavioral rules.

It may express:

- functional priorities;
- perspective priorities;
- artifact-kind priorities;
- catalog namespace preferences;
- producer-origin preferences;
- scope preferences;
- trust and evidence preferences;
- recency preferences;
- compatibility preferences;
- cost, latency, novelty, diversity, and quality priorities;
- required and preferred lenses;
- required and preferred artifact kinds;
- minimum and maximum source diversity;
- candidate-generation strategies;
- relationship traversal;
- ranking stages;
- fallback and expansion behavior;
- termination behavior;
- query budgets;
- runtime adaptation bounds;
- observability requirements.

A profile is not an access policy, not a selected portfolio, and not a
runtime query result.

### 3.5 IntelligenceSeekingStrategy

The unique search, branching, expansion, challenge, selection, and stopping
behavior of one unit of work.

A strategy is a declarative control-flow graph over registered operators:

```text
Strategy Operators
├── Query
├── Filter
├── Expand
├── Traverse Relationships
├── Generate Subqueries
├── Sequence
├── Parallel
├── Branch
├── Repeat Until
├── Fallback
├── Compare
├── Challenge
├── Diversify
├── Rerank
├── Verify Sources
├── Synthesize
├── Select
└── Stop
```

The strategy graph is a definition, not another operational object. When it
executes:

```text
IntelligenceSeekingStrategy
        ↓ compiled into
ResolvedIntelligenceSeekingPlan
        ↓ executed by
Intelligence-role LoopNode
        ↓ may start
Child Intelligence-role LoopNodes
        ↓ returns
Portfolio Snapshot + Receipt
```

A simple strategy may execute inside one Intelligence-role LoopNode. A
complex strategy may compile into a LoopGraphSpec containing several
Intelligence-role child LoopNodes. Either way, LoopNode remains the only
operational node type.

### 3.6 IntelligenceSeekingBinding

The universal configuration object that attaches access policies, one or
more profiles, and a strategy to an architectural subject.

The same binding schema must apply to:

- LoopDefinition;
- PractitionerDefinition;
- LoopGraphSpec;
- SolutionCanvas;
- StepDefinition;
- Child Loop spawn requests;
- LoopInvocation;
- organization, workspace, project, user, and deployment configuration.

The binding may declare:

- access-policy references;
- strategy reference or strategy selection mode;
- profile references and weights;
- inheritance sources and modes;
- local overrides;
- field-specific merge operators;
- frozen fields;
- adaptable fields;
- compatibility requirements;
- runtime adaptation rules;
- fallback behavior.

Do not create separate binding models for each step type or Loop role.

### 3.7 ResolvedIntelligenceSeekingPlan

The exact runtime seeking configuration after:

- resolving version ranges;
- pinning exact record versions and content hashes;
- resolving inheritance;
- detecting cycles and conflicts;
- applying deterministic merge rules;
- performing compatibility handshakes;
- applying invocation overrides;
- applying the final governance and access-policy clamp;
- calculating effective budgets;
- recording any degradation or rejected override.

The resolved plan is immutable for the invocation unless a bounded
adaptation produces a new versioned plan with a receipt.

### 3.8 IntelligencePortfolioSnapshot

The exact intelligence records selected for one invocation or one query
phase.

It must preserve:

- exact record references, versions, and content hashes;
- materialization references;
- query-plan reference;
- query receipts;
- ranking receipts;
- selected and rejected candidate summaries;
- selection reasons;
- evidence and trust signals;
- redactions;
- unresolved or unavailable references;
- the compatibility verdict;
- the time or snapshot boundary used.

Do not call a reusable query strategy a portfolio snapshot.

### 3.9 IntelligenceSeekingReceipt

A structured account of what occurred.

It should include:

- requester LoopNode ID and definition reference;
- requesting step or graph position, if applicable;
- resolved plan reference;
- bound access policy, strategy, and profiles with versions and hashes;
- strategy-selection reason;
- adapters and stores queried;
- store handshakes;
- query fragments and pushdown decisions;
- fallback decisions;
- candidate counts;
- deduplication decisions;
- conflict handling;
- ranking stages and results;
- selected records;
- rejected records and reasons;
- budget consumption;
- latency;
- errors and partial failures;
- redactions;
- runtime adaptations;
- final status.

Do not log sensitive payloads when references or hashes are sufficient.

## 4. Core defaults without hard-coded step dependence

The default nine-step Practitioner is a versioned Core preset, not a kernel
assumption.

Ship Core query profiles such as:

```text
core.intelligence_query_profile.practitioner_general@1
core.intelligence_query_profile.ask_heavy@1
core.intelligence_query_profile.horizon_heavy@1
core.intelligence_query_profile.readiness_heavy@1
core.intelligence_query_profile.deliberation_heavy@1
core.intelligence_query_profile.implementation_heavy@1
core.intelligence_query_profile.execution_heavy@1
core.intelligence_query_profile.verification_heavy@1
core.intelligence_query_profile.integration_heavy@1
core.intelligence_query_profile.routing_heavy@1
core.intelligence_query_profile.high_assurance@1
core.intelligence_query_profile.low_cost@1
core.intelligence_query_profile.adversarial_review@1
core.intelligence_query_profile.offline@1
```

Ship Core strategies such as:

```text
core.strategy.balanced@1
core.strategy.user_first@1
core.strategy.implementation_first@1
core.strategy.experience_first@1
core.strategy.adversarial@1
core.strategy.novelty_first@1
core.strategy.cost_first@1
core.strategy.breadth_first@1
core.strategy.depth_first@1
core.strategy.just_in_time@1
core.strategy.exhaustive_before_action@1
core.strategy.explore_exploit@1
core.strategy.local_core_only@1
```

The Core default Practitioner may bind the nine heavy profiles to its nine
default steps. No query-planner source code may branch on those default step
names. No base intelligence record may require a fixed nine-key
step_affinity map. No schema may require exactly nine steps. No index may
assume a fixed step order. No profile resolver may depend on numeric step
positions.

Custom Practitioners may use arbitrary step IDs and display names.

## 5. Step traits and custom behavior

### 5.1 Registered traits

Support registered, namespaced StepTrait references.

Core examples:

```text
core.step_trait.orientation
core.step_trait.goal_reconciliation
core.step_trait.readiness_assessment
core.step_trait.option_generation
core.step_trait.tradeoff_analysis
core.step_trait.execution
core.step_trait.external_effect
core.step_trait.verification
core.step_trait.adversarial_review
core.step_trait.rollback_required
core.step_trait.human_approval
core.step_trait.repository_change
core.step_trait.high_risk
core.step_trait.low_latency
core.step_trait.offline
core.step_trait.exploratory
core.step_trait.deterministic
```

Traits may help recommend or inherit default profiles. Traits must not
silently expand access, grant permissions, or be inferred from a display
name and then treated as authoritative without a receipt.

### 5.2 Free-form labels

Free-form tags and labels may support display, search, analytics, and
discovery. Unregistered labels must not directly control permissions,
access, execution, effects, governance, compatibility, budget, or profile
inheritance. If a label needs behavioral meaning, define and register a
versioned trait or attribute.

### 5.3 Explicit bindings beat recommendations

Trait matching may recommend profiles. Explicit bindings are authoritative
unless an access policy or compatibility rule rejects them. The runtime must
record inferred profiles, explicit bindings, rejected inferences,
compatibility failures, and policy clamps.

## 6. Universal inheritance model

Implement configuration composition through records and resolvers, not
Python subclass inheritance.

### 6.1 Potential inheritance sources

```text
Constitutional constraints
Deployment policy
Organization policy
Workspace policy
Project policy
User policy
Core Loop-role default
Practitioner-family default
Practitioner definition
LoopGraphSpec or SolutionCanvas
Step-trait defaults
Step definition
Parent LoopNode
Child-spawn request
Invocation override
Bounded runtime adaptation
Final governance clamp
```

Not every deployment must use every level. The resolver must preserve the
exact sources and order.

### 6.2 Inheritance modes

Support precise modes:

```text
none
constraints_only
defaults_only
preferences_only
constraints_and_defaults
full
selected_fields
```

Define their semantics formally. Recommended default for child LoopNodes:
`constraints_and_defaults`. A Child LoopNode may specialize query
preferences but may not broaden inherited hard access restrictions without
an explicit delegated grant authorized by policy.

### 6.3 Precedence

Define one canonical precedence order. Do not rely on dictionary insertion
order, filesystem order, plugin discovery order, database row order, or
import order.

Recommended precedence from broadest to most specific:

```text
constitutional
deployment
organization
workspace
project
user
role default
practitioner family
practitioner definition
graph or canvas
trait-derived profiles
step definition
parent delegation
child-spawn request
invocation override
bounded runtime adaptation
final policy clamp
```

Document and test the order.

### 6.4 Diamond inheritance

Profiles and bindings may form diamonds. Implement cycle detection,
duplicate ancestor detection, stable linearization, idempotent application
of an ancestor, deterministic tie-breaking, and explicit conflict receipts.
Do not apply the same ancestor twice. Do not silently choose one side of a
conflict.

### 6.5 Inheritance cycles

Reject or quarantine profile cycles with a typed compatibility or
configuration error containing the complete cycle path. Add fuzz tests for
large cyclic graphs.

### 6.6 Revocation and deprecation

Historical runs retain the exact profile versions they used. New
resolutions must not silently choose a revoked profile. A version range
that resolves only to revoked versions must fail or require explicit
degradation. A profile revoked during a running invocation does not mutate
the already resolved plan unless emergency policy requires termination.
Emergency revocation must emit a Chronicle event and a typed stop or
degradation decision.

## 7. Deterministic merge semantics

Every configurable field must declare a merge operator. Do not use a
generic deep-merge library as the architecture.

### 7.1 Recommended merge rules

| Field | Default merge rule |
|---|---|
| hard denials | union |
| hard required restrictions | union |
| allowed scopes | intersection |
| allowed namespaces | intersection unless delegated expansion is explicit |
| required functions | union |
| prohibited functions | union |
| preferred function weights | weighted overlay, then normalization |
| perspective weights | weighted overlay, then normalization |
| artifact-kind weights | weighted overlay, then normalization |
| penalties | additive |
| minimum evidence quality | most restrictive |
| minimum governance status | most restrictive |
| hard query budget | minimum ceiling |
| maximum records | minimum hard maximum |
| soft target count | most specific value |
| required lenses | union |
| optional lenses | weighted union |
| query templates | stable unique append |
| fallback stages | stable append unless replaced explicitly |
| frozen fields | union |
| adaptable fields | intersection with fields not frozen |
| required independent producers | maximum minimum |
| maximum duplicate lineage | minimum maximum |
| retention restriction | most restrictive |
| redaction requirement | union |
| logging restriction | most restrictive |

### 7.2 Weight rules

Specify allowed numeric range, whether zero disables or merely
deprioritizes, whether negative weights are allowed, normalization
behavior, behavior when all weights are zero, behavior with missing terms,
behavior when required terms have zero preference, deterministic rounding,
serialization precision, and tie-breaking.

Recommended baseline:

- persisted weights are decimals in [0, 1];
- no negative weights in the first implementation;
- zero means no positive preference, not a hard prohibition;
- prohibitions use explicit deny fields;
- required terms remain required regardless of weight;
- normalized scores are derived, not authoritative persisted values.

### 7.3 Unsatisfiable merges

Detect profiles that produce impossible requirements, such as a required
namespace that is also denied, a required sensitivity exceeding the maximum
allowed, minimum distinct perspectives exceeding maximum result count,
strict mode requiring an unavailable provider, a required artifact kind
with no compatible schema version, a hard budget of zero while a query is
required, mutually exclusive lifecycle constraints, or contradictory time
windows.

Do not silently relax hard requirements. Return a typed
UnsatisfiableQueryPlan with a minimal conflict set when feasible.

### 7.4 Merge receipts

The resolver must produce a merge receipt containing source profiles and
versions, source bindings and versions, precedence, field-level merge
operators, before and after values, rejected values, conflicts, and final
effective values. This receipt must be inspectable without exposing
sensitive record bodies.

## 8. Query modes

Support explicit query modes:

```text
open
guided
bounded
strict
```

- Open: any permitted intelligence may be queried; preferences influence
  candidate generation and ranking.
- Guided: start with preferred functions, perspectives, sources, and
  artifacts; expand when result count is insufficient, confidence is low,
  coverage is inadequate, sources conflict, verification fails, diversity
  requirements are unmet, or the Practitioner explicitly requests
  expansion.
- Bounded: query only explicitly permitted functions, perspectives,
  artifact kinds, namespaces, and relationship depths. No automatic
  semantic expansion beyond declared bounds.
- Strict: query exact required sources and constraints. Failure to satisfy
  produces a typed refusal, escalation, or incomplete result rather than
  silent broadening.

Recommended defaults: general Practitioner work is guided; exploratory
Intelligence work is open or guided; high-assurance verification is
bounded; regulated deterministic execution is strict.

The query mode is not the LoopNode run mode. Avoid naming collisions
between query mode and deterministic, hybrid, or non-deterministic
execution mode.

## 9. Query planning pipeline

Implement a multi-stage pipeline:

```text
Request
↓
Resolve and pin configuration
↓
Apply hard access filters
↓
Perform compatibility handshakes
↓
Resolve authoritative stores and snapshot boundaries
↓
Generate candidates
↓
Normalize records
↓
Deduplicate logical identities and materializations
↓
Validate record schemas and signatures
↓
Apply compatibility filters
↓
Apply trust and governance filters
↓
Rank
↓
Diversify
↓
Apply quotas and budgets
↓
Select
↓
Review or verify when required
↓
Create Portfolio Snapshot and receipts
```

Do not collapse all of this into one opaque vector-search call.

### 9.1 Candidate generation

Support combinations of exact ID lookup, exact attribute filters,
registered term filters, relationship traversal, full-text search, vector
search, lexical search, structured SQL query, temporal query, provenance
query, compatibility query, prior-run similarity, and plugin-provided
candidate generators. Every candidate generator must declare capabilities
through a handshake.

### 9.2 Hard filters before soft ranking

Hard access, scope, consent, sensitivity, governance, and compatibility
restrictions must execute before untrusted records are exposed to
model-based ranking. Do not allow an LLM reranker to see records the
requester is not authorized to see.

### 9.3 Multi-stage ranking

Support explicit ranking stages such as semantic relevance, function and
perspective affinity, compatibility, evidence quality, trust, recency,
cost and latency, source independence, diversity, novelty, and lineage
duplication penalty. Each stage must be versioned or identified. Do not
pretend one scalar similarity score is sufficient.

### 9.4 Deterministic ranking

For deterministic profiles use stable sorting, define tie-breaking, pin
index generations, pin embedding model and version if embeddings are used,
pin query-normalization versions, record database snapshot or as-of
boundaries, and do not rely on nondeterministic parallel-return order.

For non-deterministic reranking record model, provider, model version,
route, prompt, seed where available, temperature, and response hash; keep
hard filters outside the model; verify the reranker output against
candidate IDs; reject invented IDs.

### 9.5 Diversity

Support diversity constraints across perspectives, producers, catalog
namespaces, lineage, artifact kinds, methods, time periods, and independent
evidence sources. Prevent one prolific producer or duplicated
materialization from dominating the result.

### 9.6 Empty results

Profiles must declare behavior when no compatible records exist:

```text
return_empty
broaden_soft_preferences
broaden_functions
broaden_perspectives
query_external_research
spawn_intelligence_child
request_user_input
degrade_with_warning
escalate
refuse
```

Do not fabricate intelligence. Do not silently treat an empty result as a
successful comprehensive search.

### 9.7 Excessive results

Profiles must declare candidate caps, streaming behavior, pagination,
sampling, aggregation, summarization, diversity selection, minimum evidence
retention, and whether rejected-candidate receipts are complete or sampled.
Do not load millions of records into memory.

### 9.8 Conflicting intelligence

Support explicit conflict handling: retain both, prefer higher governance
status, prefer newer valid version, prefer more authoritative source,
request independent verification, create a conflict record, escalate, or
refuse to decide. Do not overwrite or merge conflicting claims silently.

## 10. Runtime adaptation

A Practitioner may adapt a resolved seeking plan only within declared
bounds.

### 10.1 Adaptable fields

Possible adaptable fields: soft function weights, soft perspective
weights, preferred artifact kinds, search breadth, diversity targets,
candidate caps within a ceiling, expansion triggers, fallback ordering,
recency preference, and cost versus quality tradeoff within bounds.

### 10.2 Frozen fields

Normally frozen: access policy, tenant and scope boundaries, maximum
sensitivity, consent requirements, minimum governance status, hard budget
ceilings, effect permissions, denied plugins, retention and logging
restrictions, required independent review, and required contracts.

### 10.3 Adaptation protocol

A runtime adaptation must identify a typed trigger, propose a diff,
validate the diff against adaptable fields, apply hard ceilings, explain
the reason, create a new immutable resolved-plan version, emit a Chronicle
event, update the query receipt, and preserve the original plan. An LLM
must not mutate the plan object directly.

### 10.4 Adaptation triggers

Examples: no results, insufficient evidence, low confidence,
contradictory records, source outage, required diversity unmet,
verification failure, budget pressure, latency pressure, user change,
parent instruction, emergency policy change.

### 10.5 Runaway expansion

Prevent recursive unlimited broadening, repeated query loops with no new
information, unbounded external research, child Loops repeatedly spawning
query children, and budget bypass through delegation. Require maximum
expansion depth, maximum additional query count, maximum child count,
information-gain or novelty threshold, stop condition, and shared budget
accounting where configured.

## 11. Custom Practitioner and graph corner cases

The implementation must support and test all of these.

### 11.1 Arbitrary step count

Zero-step declarative Practitioner that delegates immediately; one-step
Practitioner; four-step custom Practitioner; nine-step Core Practitioner;
hundreds of generated steps; dynamic steps created after the run begins.
Define valid behavior for zero-step and empty graphs.

### 11.2 Arbitrary names

Step behavior must not depend on names such as orient, act, verify, or
route. Test names such as alpha, compare_architecture_variants, 批准,
مرحلة_الفحص, and step-001. Use stable IDs separate from display names.

### 11.3 Renamed steps

A step display name may change without changing its stable ID or
historical references.

### 11.4 Repeated steps

The same definition may execute multiple times. Each invocation must
receive a unique runtime identity, a pinned resolved seeking plan, its own
receipts, inherited constraints, and explicit previous-attempt references.

### 11.5 Optional and skipped steps

A skipped step must record the skip reason, conditions evaluated, whether
a seeking plan was resolved, whether any required intelligence was
omitted, and the routing decision.

### 11.6 Branches

Different branches may bind different profiles. The merge system must not
leak branch-private adaptations into siblings.

### 11.7 Concurrency

Concurrent steps may share read-only snapshots, use separate private
portfolio snapshots, consume shared budgets, and encounter catalog updates
mid-run. Define snapshot consistency and isolation.

### 11.8 Cycles and iterative loops

A Practitioner graph may revisit a step. Prevent profile-resolution
accumulation on every pass, duplicate inherited weights, unbounded receipt
growth, and stale record reuse when refresh is required. Define whether
each iteration reuses or refreshes the plan and portfolio.

### 11.9 Dynamic graph generation

A generated step must pass schema validation, trait validation,
access-policy inheritance, profile compatibility, budget allocation,
parent authorization, and Chronicle registration. A generated step may not
introduce an unregistered executable node type.

### 11.10 Internal step versus Child LoopNode

Use the same IntelligenceSeekingBinding schema. Document the atomicity
rule determining when an internal step becomes a Child LoopNode. Test
equivalent query behavior when the same governed work is represented
internally versus as a child, except where isolation or budget scope
intentionally differs.

### 11.11 Parent and child privacy

A child may inherit shared run context according to policy. A child must
not automatically receive sibling private history, sibling portfolio
snapshots, user-scoped intelligence outside delegated scope, parent
secrets not explicitly delegated, or private model transcripts. Test data
isolation.

### 11.12 Nested Practitioners

A Practitioner-role Child Loop may start another Practitioner-role Child
Loop. Ensure constraints remain monotonic, budgets are accounted, exact
profile versions are pinned, no privilege broadening occurs through deep
nesting, and cycle and depth limits work.

## 12. Functional vocabulary extensibility

### 12.1 Core functions are defaults, not a closed universe

Allow namespaced extension terms. An extension term must declare stable
ID, version, display name, description, parent or related terms,
compatibility with Core terms, query-planner support requirements, ranking
semantics, deprecation policy, and governance status.

### 12.2 Unknown terms

Define behavior when a store returns an unknown term: reject,
preserve_but_do_not_use, map_through_registered_mapping,
degrade_with_warning, or request_plugin. Never silently coerce an unknown
term to a similarly named Core term.

### 12.3 Vocabulary collisions

Prevent a plugin from registering
`core.intelligence_function.verification`. Plugin terms must remain
namespaced.

### 12.4 Mappings

Support versioned mappings: plugin term to Core term, deprecated term to
successor, organization taxonomy to Core taxonomy, external vocabulary to
internal vocabulary. Mappings must be explicit records, not filename
conventions.

### 12.5 Taxonomy depth

Do not assume a flat taxonomy. Support parent, child, broader, narrower,
equivalent, and related relationships. Bound relationship expansion depth
and prevent cycles.

## 13. Record ontology and assertions

### 13.1 Intelligence record

A record should distinguish identity, specification, descriptors,
attribute assertions, relationships, evidence, provenance, evaluation,
governance, and materializations. Do not place every field in one untyped
attributes bag.

### 13.2 Functional classifications

Functional classifications should be assertions with function reference,
confidence, evidence, producer, valid time, scope, and assertion
lifecycle. A Core record may have authoritative classifications. A Learned
classification may be revised by a new assertion rather than rewriting the
immutable prior assertion.

### 13.3 Conflicting classifications

A record may have conflicting function assertions from different
producers. The query planner must apply trust, scope, governance, and
evidence rules. Do not select whichever assertion appears last in a file.

### 13.4 Temporal validity

Support valid from, valid until, observed at, recorded at, and superseded
at. Historical playback must use the appropriate as-of view.

### 13.5 Scope

A record or assertion may be global, organization-scoped,
workspace-scoped, project-scoped, user-scoped, or run-scoped. Scope is not
producer origin or catalog namespace.

## 14. Core, Learned, Plugin, and Candidate semantics

Do not conflate these.

### 14.1 Catalog namespace

```text
core
learned
plugin:<plugin_id>
```

### 14.2 Producer origin

Examples: core_release, user, practitioner_run, plugin:<plugin_id>,
external_import, administrator, migration.

### 14.3 Lifecycle

Examples: draft, candidate, under_review, approved, active, deprecated,
rejected, revoked, archived.

### 14.4 Candidate

Candidate is a governance lifecycle state, not a storage backend and not a
catalog namespace. A candidate may be stored in JSON, JSONL, DuckDB,
SQLite, PostgreSQL, object storage, a portable bundle, or a remote review
service.

### 14.5 Learned

A record becomes Learned only through the configured governance process.
Self-review and self-improvement may create candidates. They may not
approve their own candidates.

### 14.6 Plugin-produced Learned intelligence

Support `catalog_namespace: learned` with
`producer_origin: plugin:<plugin_id>`. Do not lose producer provenance when
promoting a plugin-produced candidate.

## 15. Storage independence and authority

### 15.1 Logical identity is storage-independent

A record identity must not change when represented as package JSONL,
Parquet, DuckDB row, SQLite row, PostgreSQL row, document database
document, object-store payload, plugin bundle record, or remote catalog
response.

### 15.2 One authority, many materializations

For each logical record version, declare authoritative materialization,
replicas, mirrors, caches, and derived indexes. Do not allow two
independent writable authorities without an explicit consensus or conflict
protocol.

### 15.3 Core

Recommended: authoritative package JSONL plus content-addressed files;
derived Parquet and DuckDB indexes. Core released versions are immutable.
A new package release may introduce a new version. It must not rewrite old
released bytes.

### 15.4 Learned local

Possible profiles: DuckDB authority, SQLite authority, append-only JSONL
journal authority, portable directory bundle authority.

### 15.5 Learned server

Possible profile: PostgreSQL authority, object-store blobs, Parquet
exports, local DuckDB read replica.

### 15.6 Plugins

Possible authorities: signed installed package, portable bundle, plugin
database, container service, remote catalog service.

### 15.7 File and database coexistence

Never implement "write file, write database, hope both succeed". Use an
authoritative transaction, then an outbox or append-only journal, then
idempotent replication, then watermark and hash verification, then replica
activation.

### 15.8 Snapshot consistency

A resolved seeking plan must identify the consistency model: exact
database transaction snapshot, as-of timestamp, manifest generation, JSONL
bundle hash, plugin version, remote cursor or ETag, or best-effort live
view. If strong cross-store snapshots are unavailable, record the
limitation.

## 16. Adapter and query-backend corner cases

### 16.1 Common adapter protocols

Prefer granular protocols: RecordReader, RecordWriter, RecordQuerier,
RelationshipQuerier, SnapshotReader, TransactionalWriter, BlobReader,
BlobWriter, BundleImporter, BundleExporter, FullTextSearchProvider,
VectorSearchProvider. Do not force every backend into one oversized
interface.

### 16.2 Handshake

Each adapter must declare adapter ID and version, supported ontology
versions, supported record-schema versions, supported query-protocol
versions, read/write/query/stream/export/import operations, transaction
behavior, snapshot behavior, filter and projection pushdown, relationship
traversal, full-text search, vector search, temporal queries, result
formats, authority class, consistency model, limits, and degradation
behavior.

### 16.3 Cross-backend equivalence

Normalize null semantics, decimal precision, timestamp and time-zone
handling, Unicode normalization, case sensitivity, collation, array
semantics, map semantics, boolean coercion, sorting, pagination, and
duplicate handling. Golden queries must return equivalent normalized
records across supported backends.

### 16.4 DuckDB

Distinguish DuckDBFileQueryEngine and DuckDBRecordStore. Test both.
DuckDB over Core JSONL or Parquet must not make a generated DuckDB file
authoritative unless the deployment explicitly selects that authority
profile.

### 16.5 Partial source outage

If one source fails, enforce the profile failure policy, never imply the
search was complete, include failed sources in the receipt, do not
silently shift trust weights, and decide whether to retry, degrade,
continue, or refuse.

### 16.6 Stale replicas

Detect stale manifest generation, lagging replication cursor, mismatched
content hash, expired snapshot, and unavailable authoritative source.

### 16.7 Duplicate materializations

Deduplicate by logical record identity and version, not file path.

### 16.8 Conflicting versions

Define selection rules for exact pin, compatible range, latest active,
as-of time, plugin compatibility, and migration-required versions. The
resolved plan must pin exact versions.

## 17. Security and trust adversarial cases

### 17.1 Prompt injection in intelligence records

Treat all non-Core and external record bodies as untrusted content.
Separate metadata used by the planner, body materialized for the
requesting Loop, executable implementations, and instructions. Do not let
an intelligence record modify access policy or query configuration merely
by containing text such as "ignore prior policy."

### 17.2 Malicious metadata

Validate registered term references, namespace ownership, signatures,
schema, size limits, relationship depth, URI schemes, and content hashes.

### 17.3 SQL injection

Use parameterized queries and typed query plans. Raw SQL must be an
explicitly privileged escape hatch. Do not concatenate record values into
SQL.

### 17.4 Vector poisoning

Test adversarial records designed to dominate semantic search. Use trust
filters, producer quotas, evidence thresholds, duplicate-lineage
penalties, and optional robust reranking.

### 17.5 Plugin shadowing

A plugin must not shadow Core or Learned IDs.

### 17.6 Tenant isolation

Test cross-tenant query attempts through direct ID lookup, relationship
traversal, cached results, vector indexes, portable exports, error
messages, portfolio snapshots, and query receipts.

### 17.7 Secret leakage

Do not include secrets in resolved plans, receipts, Chronicle events,
errors, snapshots, exported bundles, or generated reports. Use secret
references and redaction.

### 17.8 Executable intelligence

Discovery is effect-free. Execution requires a selected implementation,
compatibility check, effect contract, permissions, budget, sandbox or
isolation where required, ordinary LoopNode execution, and Chronicle
events. Do not execute code during ranking or preview.

### 17.9 Denial of service

Enforce query timeout, record-size limit, relationship-depth limit,
decompression limit, vector-result cap, external-call cap, plugin-call
cap, child-Loop cap, memory cap, and receipt-size strategy.

## 18. Governance and review corner cases

### 18.1 Self-approval

A self-review Practitioner may propose a new query profile, a new function
classification, a new mapping, a new ranking rule, or a new default
binding. It may not approve its own candidate.

### 18.2 Exact approved bytes

Approval must bind record ID, version, content hash, schema version,
evidence references, and compatibility verdict. A post-approval byte
change invalidates approval.

### 18.3 Partial approval

Support approval of one profile but not its optional extension, one
mapping but not another, metadata without executable payload, read-only
activation, limited scope, and limited duration.

### 18.4 Revocation

Revocation must affect new resolutions. Historical runs retain the prior
record and decision history. Emergency revocation behavior must be
explicit.

### 18.5 Imported Learned bundle

An externally exported Learned bundle should enter a new environment as
Candidate by default, unless it is trusted replication within the same
governance domain.

### 18.6 Policy conflict

When user, project, organization, plugin, and deployment policies
conflict, hard policy precedence must be explicit and auditable.

## 19. Compatibility and versioning

Do not use one ambiguous version field. Track, where applicable:
engine_version, ontology_version, record_schema_version, artifact_version,
profile_version, policy_version, vocabulary_version, query_protocol_version,
adapter_protocol_version, plugin_version, bundle_format_version,
store_schema_version, index_generation, and implementation_version.

### 19.1 Handshake verdicts

Support compatible, compatible_with_migration,
compatible_with_degradation, compatible_read_only, compatible_export_only,
incompatible, unknown, and refused_by_policy.

### 19.2 Range versus pin

Definitions may reference compatible ranges. Runtime resolution must pin
exact versions and hashes.

### 19.3 Migration

Migrations must be versioned, directional, idempotent where feasible,
resumable, checkpointed, verifiable, reversible where feasible, tested
from multiple historical versions, and recorded in governance and
Chronicle where applicable.

### 19.4 Profile schema evolution

Test added optional field, added required field, renamed field, changed
merge operator, changed term reference, changed default, split profile,
merged profiles, deprecated profile, and revoked profile. Do not
reinterpret historical records using new defaults without an explicit
migration or historical schema reader.

## 20. Performance and scale

Test at realistic and stress scales.

### 20.1 Record scale

Include fixtures for 100 records, 100,000 records, 10 million metadata
assertions, large relationship graphs, thousands of profiles, deeply
composed profiles, and many plugin namespaces.

### 20.2 Planner scale

Measure profile resolution time, merge time, compatibility handshake time,
candidate generation, ranking, relationship traversal, snapshot creation,
and receipt creation.

### 20.3 Caching

Cache only derived results. Cache keys must include query-plan hash, store
snapshot, vocabulary versions, index generation, access-policy
fingerprint, scope, and requester authorization context where needed.
Prevent cross-user cache leakage.

### 20.4 Incremental indexes

Support rebuildable structured indexes, full-text indexes, vector indexes,
relationship indexes, and profile-affinity indexes. Never make a derived
index the only authority.

## 21. Real-use scenarios that must work

Implement executable fixtures and tests for all scenarios.

- Scenario A: Core nine-step Practitioner. Every default step resolves its
  Core profile. No source code branches on the step name.
- Scenario B: Four-step repository-migration Practitioner with steps
  inspect, compare, migrate, prove. Each composes different profiles.
- Scenario C: One-step deterministic validator using strict, bounded
  Verification Intelligence. No model call.
- Scenario D: Dynamic research Practitioner creating new steps based on
  missing information. Uses guided expansion with a hard budget.
- Scenario E: Concurrent candidate Practitioners. Two children receive
  different profiles and private portfolio snapshots. No sibling leakage.
- Scenario F: Regulated high-assurance Practitioner. Organization policy
  requires reviewed Core or Learned contracts, denies unapproved plugins,
  requires independent evidence, and prohibits external research.
- Scenario G: Offline local deployment. Core JSONL and local DuckDB or
  SQLite Learned store work without network access.
- Scenario H: Server deployment. Core package files, PostgreSQL Learned
  records, object-store payloads, and remote plugin service appear through
  one logical catalog.
- Scenario I: Plugin-provided profile. A plugin contributes a namespaced
  profile and function term. The plugin cannot shadow Core, broaden
  access, or self-approve Learned output.
- Scenario J: Profile update during a long run. The running invocation
  remains pinned. A later invocation resolves the new active version.
- Scenario K: Source outage. One remote source fails. The receipt records
  incomplete coverage and the profile's declared degradation behavior is
  followed.
- Scenario L: Empty catalog match. Strict verification refuses. Guided
  exploration broadens within allowed bounds.
- Scenario M: Conflicting evidence. Two active records disagree. The
  system preserves conflict and invokes the configured verification or
  escalation route.
- Scenario N: Multi-tenant server. Tenant A cannot discover IDs, metadata,
  counts, embeddings, or cached results from Tenant B.
- Scenario O: Portable round trip. Export Learned profile and records to a
  bundle, import as Candidate elsewhere, review, approve, and verify
  identity and hashes.
- Scenario P: Cyclic profile inheritance. Resolution fails with a readable
  cycle path.
- Scenario Q: Unsatisfiable policy. Required plugin is denied by
  deployment policy. Resolution returns a minimal conflict report.
- Scenario R: Malicious intelligence record. Record contains prompt
  injection and malicious relationship expansion. Planner treats it as
  untrusted content and does not change policy.
- Scenario S: Large result set. Millions of records are streamed and
  filtered with pushdown. No full in-memory load.
- Scenario T: Repeated iterative step. Each iteration receives a clear
  plan-refresh policy and separate receipts.

## 22. Required implementation architecture

Inspect the current repository and adapt paths as needed, but target a
compact architecture like this:

```text
src/loop_engine/
├── node/
│   └── loop_node/
│       ├── model.py
│       ├── dimensions.py
│       ├── invocation.py
│       ├── result.py
│       └── references.py
│
├── ontology/
│   ├── record_envelope.py
│   ├── vocabulary_term.py
│   ├── attribute_assertion.py
│   ├── relationship.py
│   ├── evidence.py
│   ├── provenance.py
│   ├── governance.py
│   └── schemas/
│
├── intelligence/
│   ├── model/
│   │   ├── intelligence_record.py
│   │   ├── intelligence_function.py
│   │   ├── intelligence_perspective.py
│   │   ├── intelligence_portfolio_snapshot.py
│   │   └── intelligence_query_receipt.py
│   │
│   ├── query/
│   │   ├── intelligence_access_policy.py
│   │   ├── intelligence_query_profile.py
│   │   ├── intelligence_seeking_strategy.py
│   │   ├── intelligence_seeking_binding.py
│   │   ├── resolved_intelligence_seeking_plan.py
│   │   ├── profile_resolver.py
│   │   ├── inheritance_resolver.py
│   │   ├── profile_merger.py
│   │   ├── strategy_compiler.py
│   │   ├── compatibility_handshake.py
│   │   ├── query_planner.py
│   │   ├── candidate_generation.py
│   │   ├── ranking.py
│   │   ├── diversification.py
│   │   ├── selection.py
│   │   ├── runtime_adaptation.py
│   │   └── receipts.py
│   │
│   ├── catalog/
│   │   ├── catalog.py
│   │   ├── record_resolver.py
│   │   ├── version_resolver.py
│   │   ├── vocabulary_registry.py
│   │   ├── adapter_registry.py
│   │   └── protocols/
│   │
│   └── core/
│       ├── README.md
│       ├── manifest.json
│       ├── records/
│       │   └── part-00000.jsonl
│       └── files/
│           └── sha256/
│
├── governance/
├── compatibility/
├── runtime/
├── kernel/
├── plugin_host/
└── interfaces/
```

Do not create physical folders for ask, horizon, readiness, deliberation,
implementation, execution, verification, integration, routing, learned,
individual solutions, individual profiles, or default step names, unless a
folder represents a real package, ownership, storage, or deployment
boundary.

Core records ship in package data. Learned data lives in instance stores.
Plugin data lives in plugin packages, bundles, stores, or services.

## 23. Suggested typed models

Implement equivalent typed models using the repository's chosen validation
library.

```python
@dataclass(frozen=True)
class WeightedProfileRef:
    profile_ref: RecordRef
    weight: Decimal = Decimal("1")
    required: bool = False


@dataclass(frozen=True)
class IntelligenceSeekingBinding:
    access_policy_refs: tuple[RecordRef, ...]
    strategy_binding: StrategyBinding
    profile_refs: tuple[WeightedProfileRef, ...]
    inheritance: InheritanceSpec
    overrides: QueryProfileOverlay
    frozen_fields: frozenset[FieldPath]
    adaptable_fields: frozenset[FieldPath]
    compatibility_requirements: CompatibilityRequirements


@dataclass(frozen=True)
class ResolvedIntelligenceSeekingPlan:
    plan_id: UUID
    plan_version: int
    requester_ref: LoopNodeRef
    exact_profile_refs: tuple[VersionedRecordRef, ...]
    exact_policy_refs: tuple[VersionedRecordRef, ...]
    exact_strategy_ref: VersionedRecordRef
    effective_access_policy: EffectiveAccessPolicy
    effective_preferences: EffectiveQueryPreferences
    effective_requirements: EffectiveQueryRequirements
    effective_budget: QueryBudget
    effective_adaptation_policy: AdaptationPolicy
    store_snapshot_refs: tuple[StoreSnapshotRef, ...]
    compatibility_receipt_ref: ReceiptRef
    merge_receipt_ref: ReceiptRef
    content_hash: str


@dataclass(frozen=True)
class IntelligencePortfolioSnapshot:
    snapshot_id: UUID
    plan_ref: ResolvedPlanRef
    selected_record_refs: tuple[VersionedRecordRef, ...]
    selected_materialization_refs: tuple[MaterializationRef, ...]
    query_receipt_refs: tuple[ReceiptRef, ...]
    created_at: datetime
    content_hash: str
```

Do not blindly copy these examples. Adapt them to the current codebase
while preserving the semantic distinctions.

## 24. Schema and Core record requirements

Create schemas for: intelligence function term, intelligence perspective
term, step trait, access policy, query profile, seeking strategy, seeking
binding, resolved seeking plan, query receipt, portfolio snapshot, merge
receipt, compatibility handshake, vocabulary mapping, adaptation proposal,
and adaptation receipt.

Core JSONL must contain: the nine Core function terms, Core perspectives,
Core step traits, Core default access policies, Core general profiles, nine
heavy profiles, high-assurance, low-cost, adversarial-review, and offline
profiles, Core default strategies, Core default Practitioner bindings, and
schema and compatibility metadata.

Core JSONL shard names must be neutral: part-00000.jsonl, part-00001.jsonl.
Do not name shards by semantic categories.

## 25. Migration mandate

Inventory current intelligence layers, portfolios, step-affinity maps,
default Practitioner profiles, static architecture intelligence code, query
helpers, record schemas, hard-coded step names, hard-coded nine-step lists,
access checks, plugin query logic, storage adapters, docs, and examples.

Create a migration ledger with legacy path or symbol, current
responsibility, target responsibility, target path, action, data migration,
compatibility shim, test coverage, rollback, and status.

Required migrations include:

- old fixed IntelligencePortfolioDefinition to query profiles and bindings;
- fixed step affinity to generic function classifications or profile
  affinities;
- old four-layer fields to multidimensional perspectives, artifact kinds,
  producer origin, scope, and functions;
- hard-coded step-name logic to Core records;
- duplicate access and query configuration to canonical models;
- legacy records to versioned schemas;
- documentation and diagrams;
- serialized references and database rows.

Do not delete historical provenance. Do not reinterpret old records
silently. Provide migration readers or explicit conversion records.

## 26. Adversarial review before implementation

Before coding the final architecture, produce an internal architecture
challenge report.

For every proposed concept, ask:

- Is it a type, attribute, relationship, policy, runtime object, or storage
  representation?
- Is it independent from the other axes?
- Can one record legitimately have multiple values?
- Does a custom Practitioner invalidate the assumption?
- Does a plugin need to extend it?
- Can it be versioned independently?
- Can it exist in files and databases?
- Can it be queried without loading the body?
- Can it create a privilege escalation?
- Can it create an inheritance cycle?
- Can it become unsatisfiable?
- Can it be reproduced historically?
- Can it be represented without a semantic folder?
- Can it survive renaming a step?
- Can it survive moving from local JSONL to PostgreSQL?
- Can it survive a plugin being removed?
- Can it survive an ontology migration?
- Can it be tested deterministically?
- Can it be audited without exposing secrets?
- What is the failure behavior?

Do not proceed with a concept that cannot answer these questions.

## 27. Required test suite

### 27.1 Architecture tests

```text
test_loop_node_is_only_operational_node
test_no_concrete_generic_node
test_no_role_specific_node_classes
test_query_engine_has_no_default_step_name_dependency
test_no_fixed_nine_step_schema_requirement
test_no_function_domain_folders
test_no_fake_learned_package_tree
test_no_plugin_data_inside_runtime_host
test_semantic_folders_have_readmes
test_architecture_manifest_matches_tree
```

### 27.2 Profile, strategy, and binding tests

```text
test_same_binding_schema_applies_to_loop_and_step
test_custom_practitioner_accepts_any_step_count
test_custom_practitioner_accepts_any_step_name
test_explicit_profile_beats_trait_recommendation
test_unregistered_label_cannot_change_behavior
test_multiple_profiles_compose_deterministically
test_profile_resolution_pins_exact_versions
test_profile_cycle_is_rejected_with_cycle_path
test_diamond_inheritance_applies_ancestor_once
test_revoked_profile_is_not_selected_for_new_run
test_running_plan_remains_pinned_after_profile_update
test_merge_receipt_explains_every_effective_field
test_fixed_strategy_selection
test_ranked_strategy_selection
test_rule_based_strategy_selection
test_model_selected_strategy_from_approved_set
test_llm_generated_run_scoped_strategy
test_adaptive_strategy_within_declared_bounds
test_user_defined_sequence_strategy
test_parallel_strategy
test_fallback_strategy
test_challenge_strategy
test_repeat_until_requires_hard_bound
test_strategy_graph_cycle_detection
test_strategy_cannot_select_itself_recursively
test_strategy_graphs_are_not_deep_merged
test_explicit_strategy_composition
```

### 27.3 Policy tests

```text
test_preference_never_grants_permission
test_hard_denial_survives_all_overrides
test_child_cannot_broaden_parent_scope
test_plugin_cannot_override_core_policy
test_user_preference_cannot_override_org_denial
test_strategy_cannot_broaden_access
test_strategy_cannot_raise_hard_budget
test_tenant_isolation_for_direct_lookup
test_tenant_isolation_for_relationship_traversal
test_tenant_isolation_for_vector_search
test_tenant_isolation_for_cache
test_redaction_applies_to_receipts_and_snapshots
test_unsatisfiable_policy_returns_conflict_set
```

### 27.4 Merge property tests

Use property-based testing. Verify determinism, idempotence where
required, associativity only where promised, monotonicity of denials,
monotonicity of hard restrictions, no privilege broadening, stable
normalization, stable serialization, order independence where promised,
and explicit order dependence where intended.

### 27.5 Query tests

```text
test_empty_result_behavior_for_each_query_mode
test_guided_expansion_stays_within_bounds
test_bounded_mode_does_not_expand
test_strict_mode_refuses_unsatisfied_requirement
test_conflicting_records_are_preserved
test_duplicate_materializations_are_deduplicated
test_ranking_ties_are_stable
test_untrusted_reranker_cannot_invent_candidate_id
test_diversity_quotas_work
test_source_outage_is_recorded
test_partial_results_are_not_reported_as_complete
test_large_results_stream
test_recursive_relationship_depth_is_bounded
test_no_result_fallback_behavior
test_plugin_unavailable_behavior
test_untrusted_record_cannot_issue_runtime_instructions
test_file_and_database_backends_produce_equivalent_candidates
test_exact_store_snapshots_are_receipted
test_historical_replay_uses_original_strategy_versions
```

### 27.6 Runtime adaptation tests

```text
test_adaptation_cannot_change_frozen_field
test_adaptation_respects_weight_delta
test_adaptation_respects_query_budget
test_adaptation_creates_new_immutable_plan
test_adaptation_emits_chronicle_event
test_runaway_expansion_stops
test_low_confidence_trigger_expands_once_as_configured
test_repeated_step_does_not_accumulate_profile_weights
```

### 27.7 Storage conformance tests

Run the same suite against package JSONL, directory bundle, DuckDB file
query, DuckDB record store, SQLite, PostgreSQL or containerized relational
test backend, plugin bundle, remote catalog mock, and in-memory reference
store.

Test exact ID, exact version, range resolution, structured filters,
registered term filters, relationship traversal, streaming, snapshot
reads, export, import, round trip, null semantics, time zones, decimal
precision, Unicode, stable ordering, corruption detection, stale replica
detection, and interrupted synchronization.

### 27.8 Security tests

```text
test_prompt_injection_record_cannot_change_policy
test_malicious_metadata_is_rejected
test_sql_parameters_are_not_concatenated
test_plugin_namespace_shadowing_is_rejected
test_secret_refs_are_redacted
test_executable_payload_is_not_run_during_discovery
test_decompression_bomb_is_bounded
test_large_record_is_rejected_or_streamed
test_cross_tenant_error_does_not_leak_existence
test_vector_poisoning_is_limited_by_trust_and_diversity
```

### 27.9 Governance tests

```text
test_self_review_cannot_self_approve
test_approval_pins_content_hash
test_modified_approved_bytes_are_rejected
test_external_learned_import_becomes_candidate
test_partial_approval_limits_scope
test_revocation_blocks_new_resolution
test_historical_run_retains_revoked_profile_reference
test_strategy_candidate_requires_independent_review
test_strategy_generator_cannot_self_approve
```

### 27.10 Migration tests

```text
test_old_four_layer_record_migrates_without_data_loss
test_fixed_step_affinity_migrates_to_generic_metadata
test_old_portfolio_definition_migrates_to_profile_and_binding
test_old_profile_version_remains_readable
test_migration_is_resumable
test_migration_is_idempotent
test_migration_round_trip_preserves_identity
test_interrupted_migration_recovers
test_rollback_restores_prior_authority
```

### 27.11 End-to-end scenarios

Automate Scenarios A through T from this mandate.

### 27.12 Performance tests

Set and document thresholds for Core catalog startup, profile resolution,
query-plan resolution, JSONL and Parquet scanning, DuckDB queries,
relational-store queries, million-record candidate filtering, snapshot
creation, relationship traversal, and memory use. Do not claim performance
without measurements.

## 28. Fuzzing and mutation testing

Fuzz profile graphs, inheritance graphs, malformed term references,
extreme weights, Unicode identifiers, deeply nested overlays,
contradictory policies, large relationship graphs, corrupt JSONL,
truncated bundles, stale manifests, malicious plugin manifests, and
unexpected database values.

Use mutation testing or equivalent targeted mutation to ensure
architecture tests fail when a hard denial is changed to a soft penalty, a
Child Loop is allowed to broaden scope, step-name branching is introduced,
profile versions are not pinned, policy clamping is skipped, untrusted
records are passed to ranking before access filtering, Candidate
self-approval is enabled, or duplicate materializations are treated as
distinct records.

## 29. Observability and explainability

Expose developer-facing views for the effective seeking plan, inheritance
graph, merge receipt, compatibility handshake, access-policy clamp,
adapters and snapshots, query stages, ranking factors, diversity
decisions, selected and rejected records, adaptations, budget consumption,
source failures, and redactions.

Do not expose sensitive record bodies by default. Support a concise
user-facing explanation and a detailed administrator receipt.

## 30. Documentation requirements

Create or update: root architecture overview, IntelligenceFunction
glossary, access policy versus preference explanation, query profile
guide, seeking strategy guide, binding and inheritance guide, custom
Practitioner guide, custom step-trait guide, runtime adaptation guide,
storage and materialization guide, compatibility and versioning guide,
plugin contribution guide, security guide, migration guide,
troubleshooting guide, and examples for each real-use scenario.

Every semantic folder must have a focused README.md. READMEs explain
meaning and relationships. Schemas define structural contracts. Manifests
define machine-readable registrations and hashes. Code implements
behavior. Tests enforce agreement.

## 31. Development workflow

Execute in this order.

- Phase 0: inventory. Read repository instructions, inspect current
  architecture, inventory paths and symbols, identify production call
  paths, identify persistence and serialized references, identify
  hard-coded step assumptions, identify test gaps.
- Phase 1: adversarial decision record. Write the challenge report, select
  canonical terminology, document rejected alternatives, define
  invariants, define migration boundaries.
- Phase 2: schemas and models. Implement registered term references,
  access policy, query profile, seeking strategy, seeking binding,
  resolved plan, receipts, and portfolio snapshot. Add schemas and
  contract tests.
- Phase 3: resolver and merge engine. Deterministic precedence, cycle
  detection, conflict detection, merge receipts, exact version pinning,
  compatibility handshakes.
- Phase 4: catalog and adapters. Core JSONL, file query, embedded store,
  relational store, plugin and remote sources, normalized result model,
  conformance tests.
- Phase 5: query planner. Hard filters, candidate generation,
  normalization, deduplication, ranking, diversity, selection, empty and
  failure behavior, receipts.
- Phase 6: Core defaults. Core functions, perspectives, traits, policies,
  profiles, strategies, and default Practitioner bindings.
- Phase 7: runtime integration. Internal steps, Child Loop delegation,
  Runtime Memory, Chronicle, budgets, adaptation, portfolio snapshots.
- Phase 8: migration. Migrate production paths, migrate records, migrate
  docs, remove legacy architecture, add temporary shims only when
  necessary.
- Phase 9: red team. Run security tests, fuzz tests, failure injection,
  concurrency tests, multi-tenant tests, mutation tests.
- Phase 10: packaging and clean install. Build wheel and source
  distribution, inspect package data, verify Core JSONL and schemas ship,
  install in a clean environment, run default and custom Practitioner
  scenarios, verify no dev-only packages are imported.
- Phase 11: predeploy. Run one strict command, such as
  `python -m loop_engine.predeploy --strict`. Return one verdict: PASS,
  PASS_WITH_DOCUMENTED_WARNINGS, or BLOCKED. Architecture, security,
  policy, data-loss, compatibility, and reproducibility violations are
  blocking.

## 32. Prohibited shortcuts

Do not:

- hard-code the nine default step names;
- make function domains physical folders;
- use free-form labels for access or execution behavior;
- merge access policy and preferences;
- use one generic config dictionary;
- use one ambiguous version, status, or source;
- trust filesystem order or plugin discovery order;
- silently broaden a query;
- silently drop conflicts;
- silently ignore unavailable sources;
- load all records into memory;
- execute code during discovery;
- let an LLM edit hard policy;
- let a Child Loop broaden parent scope;
- let self-review approve itself;
- make both files and a database independent writable authorities;
- make a derived index authoritative;
- preserve the old architecture indefinitely beside the new one;
- claim completion because schemas exist;
- claim completion because unit tests pass while production paths still
  use legacy code.

## 33. Required final deliverables

Return:

- architecture challenge report;
- selected canonical terminology;
- migration ledger;
- exact target and final repository trees;
- implemented schemas and models;
- Core JSONL records and manifests;
- adapter and store implementations;
- compatibility matrix;
- migration scripts;
- architecture tests;
- property-based and fuzz tests;
- security and failure-injection results;
- end-to-end scenario results;
- performance measurements;
- package and clean-install verification;
- strict predeploy report;
- list of deleted obsolete paths;
- list of remaining compatibility shims with removal conditions;
- unresolved risks, if any;
- exact commands required to reproduce every verification.

Do not hide failures. Do not say "implemented" when a path is only
scaffolded. Do not say "compatible" without a handshake and test. Do not
say "portable" without a round trip. Do not say "secure" without
adversarial tests. Do not say "reproducible" without exact version, hash,
and snapshot pinning.

## 34. Final completion standard

The work is complete only when all of the following are true:

- Custom Practitioners may define any step names, counts, orders, and
  graphs.
- Any Loop, graph, Practitioner, step, child spawn, or invocation may use
  the same IntelligenceSeekingBinding schema.
- The default nine-step Practitioner is expressed entirely through Core
  versioned records and bindings.
- The query planner contains no dependency on default step names.
- Functional intelligence terms are registered, versioned, non-exclusive,
  and extensible through namespaced vocabularies.
- Access policies remain hard and monotonic.
- Preferences remain soft and composable.
- Seeking strategies are declarative, versioned, and executable only
  through ordinary Intelligence-role LoopNodes.
- Inheritance is deterministic, cycle-safe, conflict-aware, and receipted.
- Runtime adaptation is bounded, versioned, and observable.
- Core, Learned, Plugin, Candidate, scope, producer origin, lifecycle,
  storage authority, and materialization remain separate dimensions.
- File, embedded-database, server-database, bundle, plugin, and remote
  sources resolve through compatible interfaces.
- Resolved plans pin exact versions, hashes, and store snapshots.
- Portfolio snapshots preserve the exact selected intelligence.
- Security, privacy, tenant isolation, and prompt-injection boundaries
  pass.
- Migrations preserve identity, evidence, provenance, and history.
- The obsolete fixed-step portfolio architecture is absent from active
  production paths.
- A clean installation passes the default and custom scenarios.
- The strict predeploy gate returns PASS.

If a requirement cannot be satisfied, return BLOCKED with concrete
evidence, the smallest unresolved issue, and the exact next implementation
step. Do not paper over the failure with documentation.
