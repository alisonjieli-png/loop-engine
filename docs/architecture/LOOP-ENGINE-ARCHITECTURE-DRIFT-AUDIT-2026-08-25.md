# Loop Engine architecture drift audit

**Date:** 2026-08-25  
**Decision state:** Architecture drift is confirmed. The local worktree contains
important corrections, but the ideal architecture is not yet implemented from
definition through execution. Do not treat the current diagrams as proof of the
runtime.

## Why this audit exists

Loop Engine has one governing idea:

> Every executable graph vertex is a Loop.

That sentence has concrete consequences. A Loop must be more than a function
wrapped for logging. It needs a stable and versioned definition, typed input and
output ports, a role, a profile, a selected run mode, settings, a loop condition,
an exit condition, permissions, budgets, relationships, and recorded execution.

This audit checks that idea against three different sources:

1. the published GitHub repository;
2. the current local Loop Engine worktree;
3. `/home/username/taedri.dev`, used only as design reference material.

The Taedri folder is not a source to copy wholesale. It contains valuable
contracts and graph ideas, but it also contains several competing graph models.
Only individually reviewed concepts should move into Loop Engine.

## Exact snapshots reviewed

| Surface | Snapshot | State during audit |
|---|---|---|
| GitHub `main` | commit `3491e2369639361893819ac6975a21bec47ea68c` | Confirmed with `git ls-remote`. The local `origin/main` and remote SHA matched. |
| Clean copy of GitHub `main` | archive of the same commit under `/tmp/loop-engine-head.ud2Nmg` | Conformance passed. Self-test passed 1,055 of 1,055. |
| Local Loop Engine | same committed base plus uncommitted work | 82 tracked files changed and 218 untracked files. This is an integration worktree, not a release candidate. |
| Taedri reference | `/home/username/taedri.dev` at commit `958fcc77a0ddf983a988dc884ff037451e7f2168` plus unrelated concurrent work | Read only. No Taedri files were changed. |

Passing tests on published `main` prove that its own stated checks pass. They do
not prove that the checks express the architecture described in this report.

## The target architecture

### One operational runtime

```text
Loop
├── Practitioner Loop
│   ├── understand
│   ├── research
│   ├── deliberate
│   ├── build
│   ├── verify
│   ├── repair
│   └── self-improvement task
├── Intelligence Loop
│   ├── Context Intelligence
│   ├── Code Intelligence
│   ├── User Feedback Intelligence
│   └── Runtime History and Solution Intelligence
└── Solution Loop
    ├── component
    ├── pipeline controller
    ├── validator
    ├── router
    ├── fallback
    ├── ensemble member
    └── output formatter
```

These are roles and profiles of one runtime. They are not separate runtime
classes.

### One complete Loop definition

Every runnable Loop definition should contain this information in one immutable
and versioned object:

```text
LoopDefinition
├── loop_definition_id
├── semantic_version
├── content_digest
├── role
├── exact role profile and profile version
├── typed input ports
├── typed output ports
├── supported run modes
│   ├── deterministic
│   ├── hybrid
│   └── non_deterministic
├── step profile and step-profile version
├── settings schema and defaults
├── loop condition
├── exit condition
├── budgets and permissions
├── effects and idempotency
├── required Static Architecture capabilities
└── Run History event contract
```

One run then binds that definition to values and execution state:

```text
LoopInstance
├── loop_instance_id
├── LoopDefinition reference
├── selected run mode
├── validated input values
├── relationship to other Loop instances
├── run-scoped settings
├── status and counters
├── output values
└── Run History event references
```

A Loop definition may support all three run modes. One Loop instance selects one
mode for a run. A graph or Canvas does not have one inherited mode.

### One authoritative graph

```text
Task input
    |
    v
Starting Practitioner Loop
    |
    +-- SPAWNED_BY --> Practitioner research Loop
    |
    +-- QUERIED_BY --> Intelligence query Loop
    |                      |
    |                      +-- RETRIEVED_BY --> Intelligence item Loop
    |
    v
Solution Canvas
    |
    v
Starting Solution Loop
    |
    +-- CONNECTED_FROM --> Solution Loop 2
                              |
                              +-- CONNECTED_FROM --> Solution Loop 3
                                                        |
                                                        v
                                                     Result
```

The static Solution graph is a directed acyclic graph. Repetition belongs inside
a Loop through its loop condition and exit condition. Dynamic branches add Loop
vertices. An edge never hides executable code.

Passive data is allowed, but it is not a fake graph vertex:

- a Context Intelligence record is passive content owned by an Intelligence
  Loop definition;
- a callable or package is passive Code Intelligence until a Loop invokes it;
- a port, edge, slot, report, file, or service is not an executable graph vertex;
- Static Architecture provides Intelligence Search and Retrieval, Web
  Research, and Custom Plugins. Providers, settings, workspaces, approvals,
  stores, memory, history, and viewing are internal runtime mechanics.

## Summary verdict

| Required property | Published GitHub `main` | Local worktree | Verdict |
|---|---|---|---|
| One canonical `Loop` runtime | Partial | Partial, with stronger conformance | The class exists, but several wrappers and internal algorithms still behave like parallel runtimes or pseudo-nodes. |
| Practitioner, Intelligence, and Solution roles | Mostly documentation | Implemented as a versioned profile ontology | Good direction, but the core constructor does not require a registered bound profile. |
| Four Intelligence branches | Present in docs and wrappers | Present in the profile catalog | Names and execution paths are inconsistent. Runtime History is still called several different things. |
| Every graph vertex resolves to a Loop | Asserted | Checked only by naming and references | Not proven. Arbitrary string references can validate as graph vertices. |
| Versioned Loop definitions | No | Profile version only | Missing as a single complete object. |
| Typed input and output ports | String role names | String role names plus connection checks | Useful start, but not type or schema enforcement. |
| One DAG representation | No | No | Three overlapping graph or Canvas models remain. |
| Loop-selected run mode | Declared | Better separated | Solution hybrid and non-deterministic modes still cannot execute locally. |
| Real deterministic, hybrid, and model-led execution | Partial | Partial | The default runtime can report non-deterministic success with zero provider calls. |
| Practitioner Loop spawning | Basic recursive `spawn()` | Typed lifecycle manager added | Stronger, but the default spawned executor is deterministic only. |
| Intelligence querying and retrieval as Loops | Thin wrappers | Relationship types added | Retrieval still calls `parent.spawn()`, so it emits a spawn event even when its semantic relationship says retrieved. |
| Every Loop can use Intelligence and Static Architecture | No | No | Capability and internal mechanic ports are passed to selected handlers and managers. They are not one standard Loop runtime context. |
| Solution Canvas is a matrix of working alternatives | Partial | Partial | The older Canvas has candidate slots. The newer SolutionSpec has linear loops and nested members. They are not one model. |
| Run History represents the full Loop graph | Spawning graph | More relationships in events | `LoopLedger.tree()` still reads only spawn edges. It does not build the complete relationship DAG. |
| Self-improvement is a Practitioner task | Documented | Profiled correctly | The role separation is sound. Promotion must remain independent. |
| Full local verification | 1,055 of 1,055 on clean published code | Failing | The worktree self-test stops on a stale field name and four conformance gates fail. |

## Critical findings

### 1. There is no single authoritative graph model

The local code has at least three overlapping structures:

| Structure | File | What it represents |
|---|---|---|
| `Canvas` and `SolutionLoopCandidate` | [`loop/canvas.py`](../../src/loop_engine/loop/canvas.py) | Ordered slots with candidates and fallbacks. |
| `SolutionSpec` and `SolutionLoopSpec` | [`code_nodes/solution_canvas.py`](../../src/loop_engine/code_nodes/solution_canvas.py) | A linear tuple of solution operations or nested solution members. |
| `LoopGraphSpec` and `LoopEdgeSpec` | [`code_nodes/solution_graph.py`](../../src/loop_engine/code_nodes/solution_graph.py) | Typed graph references and edge validation. |

The public Solution Canvas guide lists `SolutionSpec` and `LoopGraphSpec` as
separate main records. That is a direct sign that a Solution Canvas is not the
authoritative graph object yet. See
[`docs/components/solution-canvas/README.md`](../components/solution-canvas/README.md).

The older Taedri folder shows the same failure pattern. Its
`standard_graph_types.py` says the repository had three divergent graph models
and then added a projection layer instead of replacing them. See
`/home/username/taedri.dev/components/taedri_real_world_savings_evaluation/benchmarks/standard_graph_types.py:2-19`.

**Required correction:** Define one `LoopGraphDefinition`. Make Solution Canvas,
Practitioner run view, Intelligence retrieval view, Studio, and playback
projections of that object. Retire the other executable graph schemas after
explicit migration readers are in place.

### 2. A graph vertex does not have to resolve to a real Loop definition

`LoopVertexSpec` contains a `loop_ref` string and a `LoopContract`. Validation
checks that the string is non-empty. It does not resolve the reference through a
versioned Loop registry. See
[`solution_graph.py:44`](../../src/loop_engine/code_nodes/solution_graph.py#L44)
and [`solution_graph.py:101`](../../src/loop_engine/code_nodes/solution_graph.py#L101).

This runtime probe passed:

```text
LoopVertexSpec("not-a-real-loop", valid_contract)
LoopGraphSpec(...).validate() -> {"valid": true, "violations": []}
```

An Adapter Loop reference can also be attached to an edge without adding an
adapter vertex to the graph. `insert_adapter()` rewrites the edge but leaves the
graph's Loop set unchanged. See
[`solution_graph.py:196`](../../src/loop_engine/code_nodes/solution_graph.py#L196).

**Required correction:** Every executable vertex must contain an exact
`LoopDefinitionRef` with ID, semantic version, and digest. Validation must resolve
that reference, confirm a registered role profile, and confirm typed ports. An
adapter must be an explicit Loop vertex connected by explicit edges.

### 3. The core Loop constructor does not enforce the ontology

The local worktree added `LoopRoleIdentity` and versioned profiles. This is good.
However, [`Loop.__init__`](../../src/loop_engine/loop/recursive_loop.py#L323)
accepts any `LoopRoleIdentity` whose profile name begins with the role name. It
does not require a `BoundLoopProfile` or resolve the profile catalog.

This runtime probe succeeded when it should have failed:

```text
LoopRoleIdentity(INTELLIGENCE, "intelligence.not_registered")
Loop(...) -> accepted
```

The default contract is also built as a Practitioner baseline even when the
identity says Intelligence or Solution. See
[`recursive_loop.py:354`](../../src/loop_engine/loop/recursive_loop.py#L354).

**Required correction:** Construct runnable Loops from one validated
`LoopDefinition` or `BoundLoopProfile`. Refuse unregistered profiles, abstract
profiles, role-contract mismatches, mode-contract mismatches, and missing version
or digest fields.

### 4. Intelligence wrappers do not yet satisfy the full Loop contract

`IntelligenceLoop` is a six-field wrapper around content. It is not the canonical
runtime and does not carry a contract, version, mode policy, step profile,
settings object, loop condition, or exit condition. See
[`intelligence_loops.py:80`](../../src/loop_engine/loop/intelligence_loops.py#L80).

There are additional inconsistencies:

- Code Intelligence serving maps to `intelligence.materialize`, not a specific
  Code Intelligence profile.
- Runtime History serving maps to the abstract
  `intelligence.runtime_history_solution` profile.
- The wrapper can execute that abstract profile because it bypasses profile
  binding.
- The stored pillar names still use `context_intelligence` and
  `runtime_history_solution_intelligence`, while public language uses Context Intelligence and
  Runtime History and Solution Intelligence.

The call at
[`intelligence_loops.py:119`](../../src/loop_engine/loop/intelligence_loops.py#L119)
marks a retrieved relationship, but `as_loop()` then calls `parent.spawn()`.
The ledger therefore emits both a `retrieved_by` relationship and a `spawn`
event for the same operation.

**Required correction:** Use registered profiles such as
`intelligence.context.retrieve`, `intelligence.code.invoke`,
`intelligence.user_feedback.retrieve`, and
`intelligence.runtime_history.retrieve`. Build them through the same
`LoopDefinition` binder as every other Loop. A retrieval relationship must not be
recorded as spawning unless a new autonomous Loop was actually spawned.

### 5. Mode labels can disagree with physical execution

The canonical mode must describe what led the work:

- deterministic means no model call;
- hybrid means code leads and a real model may perform a bounded semantic step;
- non-deterministic means a real model leads semantic work.

The default handler in
[`recursive_loop.py:313`](../../src/loop_engine/loop/recursive_loop.py#L313)
returns generated strings. A Loop configured as non-deterministic completed with
this result:

```text
output: act:done
mode_counts: {"non_deterministic": 1}
model_calls: 0
accepted: true
```

That is not a non-deterministic run. It is a structural simulation mislabeled as
execution.

Published GitHub `main` has a second mode problem. A `SolutionLoopSpec` may
declare `hybrid` or `non_deterministic`, but `run_solution()` executes every
callable through a deterministic component wrapper and records the declared
label. Clean tests do not falsify that mismatch.

The local worktree improves honesty by refusing unsupported Solution modes in
[`solution_canvas.py:242`](../../src/loop_engine/code_nodes/solution_canvas.py#L242).
That is safer, but it also proves that all three Solution Loop modes are not
implemented.

**Required correction:** Remove the synthetic default execution path. A Loop
without a real executor should fail with `EXECUTOR_UNAVAILABLE` or run only in
an explicitly named structural-dry-run mode that is never reported as task
execution. Conformance must reject semantic mode events without matching physical
model attempts.

### 6. Solution Loop definitions are not complete Loop definitions

`SolutionLoopSpec` currently contains:

```text
loop_id, operation, mode, fallback_operations, params, input_role, output_role
```

It lacks a semantic version, digest, exact role profile, step profile, full typed
contract, settings schema, permissions, effects, loop condition, and exit
condition. See
[`solution_canvas.py:43`](../../src/loop_engine/code_nodes/solution_canvas.py#L43).

The runner reconstructs a hard-coded deterministic contract and profile later.
That means the Canvas record is not the complete definition of what will run.

The current `SolutionSpec` is also a linear tuple. It checks adjacent ports with
`zip(self.loops, self.loops[1:])`. It has no explicit edge list, branching
predicate, or general DAG ordering. See
[`solution_canvas.py:133`](../../src/loop_engine/code_nodes/solution_canvas.py#L133).

**Required correction:** Store exact `LoopDefinitionRef` vertices and explicit
typed edges in the Canvas. Linear pipelines should be a convenient constructor
for a DAG, not a second graph type.

### 7. Typed ports are labels, not enforced value types

`LoopContract.input_roles` and `output_roles` are tuples of strings. Connection
validation confirms that role names line up and that adapters are named. This is
useful, but it does not validate value schemas, shapes, versions, units, null
rules, or encodings. See
[`loop_contract.py:90`](../../src/loop_engine/loop/loop_contract.py#L90)
and [`loop_contract.py:221`](../../src/loop_engine/loop/loop_contract.py#L221).

The Taedri reference has a stronger list of contract fields, including semantic
version, digest, named typed ports, effects, idempotency, runtime requirements,
parameters, tests, and telemetry. See
`/home/username/taedri.dev/CLAUDE.md:485-525` and
`/home/username/taedri.dev/TAEDRI_SELF_AWARE_AUTONOMOUS_MAJOR_CONSTITUTION_CHARTER_GOAL_AND_LOOP.md:12173-12198`.

**Required correction:** Add a versioned `PortSpec` with a schema reference,
schema version, shape, optionality, validation rules, and media or encoding facts.
Use `PortValue` to validate actual inputs and outputs at every graph edge.

### 8. Loops do not receive one standard capability and runtime context

The core `Loop` instance contains goal, config, parent, identity, relationship,
depth, ledger, ID, and contract. It has no standard Retrieval Engine, Intelligence
Library, Capability Directory, Model Gateway, workspace, approval, MCP, skills,
or settings interface.

Selected handlers receive selected services. `directory_handler()` receives a
directory, a String bank, and optional intelligence records. The spawned runtime
port exposes Runtime Memory but not the full service set. This is dependency
injection by individual call path, not a universal Loop capability.

**Required correction:** Introduce one typed `LoopRuntimeContext` with
permission-limited ports for:

```text
LoopRuntimeContext
├── Static Architecture capabilities
│   ├── Intelligence Search and Retrieval
│   ├── Web Research
│   └── Custom Plugins
└── internal runtime mechanics
    ├── model_gateway
    ├── workspace and approvals
    ├── stores and Runtime Memory
    ├── Run History
    └── settings and viewing
```

Every Loop receives the context object. Permissions determine which calls are
allowed. A missing required service must fail before work starts. Each service
operation must still execute through a role-correct Loop boundary.

### 9. Typed spawning is much better, but not complete across modes

The local `DelegationSpec` is a strong improvement. It groups profile, contract,
inputs, mode, budget, context visibility, workspace policy, return destination,
effects, and model thinking power. It validates profile registration and mode
compatibility. See
[`delegation_runtime.py:173`](../../src/loop_engine/loop/delegation_runtime.py#L173)
and [`delegation_runtime.py:595`](../../src/loop_engine/loop/delegation_runtime.py#L595).

However, the built-in `DeterministicSpawnedExecutor` refuses every
non-deterministic request. A caller must inject another executor. No standard
hybrid or non-deterministic spawned executor completes the Model Gateway path.

**Required correction:** Keep one `DelegationSpec`, then provide three tested
executor strategies behind the same interface. All must use the Loop's
`LoopRuntimeContext`, exact profile, typed ports, budgets, and Run History.

### 10. Documentation is ahead of the runtime

The local README says every Loop has a version and graph relationships. The core
`LoopConfig` has no version field. Only the role profile has a version. The README
also presents more profiles than the registered catalog contains, including
experimenter, builder, reviewer, repairer, and output formatter.

The Loop object guide now uses `LoopRoleIdentity` and `LoopRelationship`.
Documentation drift can return because public tables and diagrams are not
generated from the registered runtime definitions.

**Required correction:** Do not repair diagrams in isolation. Generate public
architecture tables and tree diagrams from the same registered definitions used
by runtime validation. CI should fail when a documented profile or field has no
registered implementation.

### 11. Local integration is not currently green

The local worktree's focused contract, profile, Intelligence, graph, and Solution
Canvas tests passed. Full verification did not.

Current conformance failures:

```text
modules_over_size_cap_without_declared_exception = 1
modules_whose_self_test_the_suite_never_runs = 1
operational_boundaries_outside_loop_ontology = 2
architecture_map_freshness = 1
```

The full self-test stopped with:

```text
KeyError from a stale orphan-count field
```

The code now emits `orphaned_spawned_loops`, but the conformance test still reads
the old field. The boundary registry also still refers to retired class names.

**Required correction:** Do not push the current worktree as a completed
architecture migration. Finish one coherent migration packet, regenerate the
map and manifest, run the full suite, then inspect the built package from a clean
directory.

## What is worth carrying forward from Taedri

Use these ideas as references, not files to copy:

1. **The complete component contract.** Stable identity, version, digest, typed
   ports, effects, idempotency, runtime requirements, parameters, tests,
   provenance, and telemetry belong in the Loop definition.
2. **GraphIR fields.** Graph identity, version, digest, typed external ports,
   explicit edges, conditions, evaluator attachments, effect boundaries,
   checkpoints, policies, and resources are useful requirements.
3. **Capability handshakes.** A service must declare operations, schemas, limits,
   health, locality, pricing facts, and unsupported features before use.
4. **Immutable task capsules.** Practitioner Loops need one frozen, typed task
   input rather than a growing collection of unrelated arguments.
5. **Progressive disclosure.** Search should return short references before
   materializing bodies.

Do not copy these Taedri structures directly:

- `StandardNode` and `StandardGraph`, because a Loop Engine graph vertex must be
  a Loop definition, not a second Node runtime;
- the several legacy graph models that `standard_graph_types.py` admits were
  divergent;
- Taedri product authority, evidence, deployment, or billing systems that do not
  belong in the small Loop Engine runtime;
- historical Taedri vocabulary as new public Loop Engine terms.

## Recommended correction sequence

### Phase 0: Freeze public architecture claims

- Keep the published GitHub commit as the last stable package until the local
  migration is coherent.
- Do not publish a new architecture video as a statement of current behavior.
- Mark the redesigned showcase as the architecture contract until every scene is
  backed by an executable test.

### Phase 1: Define the canonical contracts

- Create `LoopDefinition`, `LoopDefinitionRef`, `LoopInstance`, `PortSpec`,
  `PortValue`, `LoopEdge`, `LoopGraphDefinition`, and `LoopRuntimeContext`.
- Give each serialized contract a semantic version and digest.
- Make role, profile, mode policy, selected mode, step profile, settings, loop
  condition, and exit condition separate fields.

### Phase 2: Make construction fail closed

- Require every runnable Loop to come from a registered `LoopDefinition`.
- Remove implicit Practitioner contracts from Intelligence and Solution paths.
- Refuse abstract or unknown profiles.
- Refuse a selected mode that lacks an installed executor.

### Phase 3: Consolidate graph models

- Make `LoopGraphDefinition` authoritative.
- Make Solution Canvas a projection plus candidate matrix over that graph.
- Make linear pipelines a builder for explicit edges.
- Make every adapter an explicit Loop vertex.
- Retire `Canvas`, `SolutionSpec`, and `LoopGraphSpec` as independent execution
  authorities after migration.

### Phase 4: Standardize capability and runtime ports

- Inject `LoopRuntimeContext` into every Loop.
- Route the three Static Architecture capability groups through typed ports.
- Route providers, settings, workspaces, approvals, stores, memory, history,
  and viewing through separate internal mechanic ports.
- Do not draw capabilities or internal mechanics as Loop vertices.

### Phase 5: Complete all three modes

- Implement one real executor for each mode behind one interface.
- Run the same versioned Loop definition in deterministic, hybrid, and
  non-deterministic modes where its profile permits them.
- Require physical model attempt records for semantic modes.
- Keep provider failure, validation failure, repair, and fallback separate.

### Phase 6: Migrate each role

1. Practitioner and typed spawning
2. Context Intelligence
3. Code Intelligence
4. User Feedback Intelligence
5. Runtime History and Solution Intelligence
6. Solution Canvas and Solution Loops
7. self-improvement as a Practitioner task

Complete and test one role before migrating the next.

### Phase 7: Prove one real end-to-end task

Use the proposed website and PDF task:

```text
discover sources
  -> download PDFs
  -> inspect document structure
  -> extract records
  -> validate and normalize data
  -> build model-ready data
  -> train competing models
  -> verify and repair
  -> compile a reusable Solution Canvas
```

Every executable step must have a Loop ID, definition version, selected mode,
typed input and output values, explicit edge, service calls, and Run History
events. Run at least one real hybrid or non-deterministic Practitioner path
through Ollama Cloud, Mistral, or OpenRouter. Do not use a fake model.

## Adversarial validation plan

The migration is not complete until all of these tests pass.

### Definition and identity

- [ ] An unregistered profile such as `intelligence.not_registered` is refused.
- [ ] An abstract profile cannot initialize a runnable Loop.
- [ ] A Loop definition without semantic version and digest is refused.
- [ ] A role-profile mismatch is refused.
- [ ] A role-contract mismatch is refused.
- [ ] Two definitions with the same ID and version but different bytes are
  refused as a collision.

### Graph

- [ ] A string that does not resolve to a registered Loop definition cannot be
  a graph vertex.
- [ ] Every executable graph vertex resolves to exactly one Loop definition.
- [ ] Every edge names real typed ports on both endpoint Loops.
- [ ] An adapter reference on an edge without an adapter Loop vertex is refused.
- [ ] A Solution graph cycle is refused.
- [ ] A linear builder and a hand-authored DAG produce the same canonical graph
  bytes when they describe the same solution.
- [ ] Canvas, Studio, report, live view, and playback all project the same graph
  digest.

### Modes

- [ ] Deterministic execution records zero physical model calls.
- [ ] Hybrid execution includes a real bounded semantic attempt when it uses the
  model path.
- [ ] Non-deterministic execution cannot succeed without a physical model
  attempt or an explicit externally supplied human result.
- [ ] A mode label cannot be copied into a result without matching execution
  evidence.
- [ ] The same spawning Loop can spawn Loops in different permitted modes.
- [ ] A deterministic Loop can spawn a non-deterministic Loop.
- [ ] A non-deterministic Loop can spawn a deterministic Loop.
- [ ] Mode changes never grant file, network, secret, or spending permission.

### Intelligence

- [ ] Querying Context Intelligence runs an Intelligence Query Loop.
- [ ] Retrieving an item runs an Intelligence Item Loop without falsely emitting
  a spawn relationship.
- [ ] Code Intelligence invocation runs through an exact versioned Code
  Intelligence Loop.
- [ ] User Feedback Intelligence can serve deterministically and interpret with
  a real model when requested.
- [ ] Runtime History Intelligence can search, replay, and compare saved runs.
- [ ] Missing layers remain visible and do not become empty success claims.
- [ ] Candidate intelligence cannot promote itself.

### Static Architecture

- [ ] The public architecture contains only Intelligence Search and Retrieval,
  Web Research, and Custom Plugins.
- [ ] Every Loop receives a typed `LoopRuntimeContext`.
- [ ] Required but unavailable capabilities or internal mechanics fail before
  work starts.
- [ ] Discovery remains effect-free.
- [ ] Materialization and execution start only after selection and permission
  checks.
- [ ] Every capability operation records the requesting Loop ID and role-correct
  Loop ID.
- [ ] Internal providers, workspaces, stores, history, and viewing remain
  runtime mechanics instead of new public capability groups.

### Solution Canvas

- [ ] Every Canvas component is a Solution Loop definition, not a bare callable.
- [ ] Deterministic, hybrid, and non-deterministic Solution Loops either execute
  correctly or fail preflight as unavailable.
- [ ] Multiple working solution graphs can remain in the candidate matrix.
- [ ] Selection, ordered fallback, routing, and ensemble behavior are explicit
  Solution Loops.
- [ ] Output values are validated against the declared output schemas.

### Whole repository

- [ ] Full self-test passes from the source tree.
- [ ] Full conformance passes with zero exceptions hidden by aliases.
- [ ] A built wheel passes the same checks from a clean directory.
- [ ] Documentation examples execute against the installed wheel.
- [ ] Public diagrams are generated from registered definitions.
- [ ] The redesigned video shows only behavior proved by these checks, or labels
  unimplemented behavior as target architecture.

## Showcase guidance derived from this audit

The proposed presentation sequence is sound if it uses one idea per slide:

1. Loop Engine
2. Loops are all you need
3. Architecture overview
4. One Loop object
5. Three run modes
6. Loop role hierarchy
7. Practitioner profile
8. Spawning and deliberation
9. Four Intelligence branches
10. Three Static Architecture capability groups
11. Solution Canvas as a candidate matrix
12. One canonical typed DAG
13. Website and PDF worked example
14. Data extraction and validation
15. Model building, verification, and repair
16. Run History, live view, and playback
17. Self-improvement as a normal Practitioner task
18. Architecture status and proof boundary

The public showcase should say:

> Every executable graph vertex is a Loop. Every Loop uses one selected mode,
> follows a versioned profile, receives typed values, and records its work.

Until the migration is complete, the final status slide must distinguish
implemented behavior from the architecture contract. It should not imply that
hybrid and non-deterministic Solution Canvas execution already works.

## Final decision

Loop Engine has not lost the core idea, but it has implemented that idea in
several overlapping layers. The local worktree is moving in the right direction
with role profiles, semantic relationships, typed delegation, and role-correct
Solution envelopes. The remaining problem is architectural consolidation.

The next implementation packet should not add another profile, diagram, wrapper,
or graph type. It should create the one versioned Loop definition, the one
runtime context, and the one authoritative Loop graph that every existing
surface must use.
