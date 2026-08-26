# Loop Engine architecture drift audit

Date: 2026-08-25

This report compares the current Loop Engine implementation with the stated
architecture. It also records which ideas from `/home/username/taedri.dev`
remain useful reference material. The Taedri repository was reviewed as a
source of design lessons, not copied into Loop Engine.

## Audit question

Does the current repository implement this architecture?

```text
Every executable graph vertex is a Loop
├── one immutable versioned definition
├── one exact role profile
├── one selected mode
├── typed inputs and outputs
├── loop condition and exit condition
├── least-authority services and permissions
├── explicit graph relationships
└── ordered event history

Loop roles
├── Practitioner
├── Intelligence
│   ├── Context Intelligence
│   ├── Code Intelligence
│   ├── Runtime History and Solution Intelligence
│   └── User Feedback Intelligence
└── Solution
```

The answer is now mostly yes. The core definition, runtime context, profile
ontology, and graph authority are implemented and fail closed. Four narrower
gaps remain. They are listed with adversarial checks below.

## Sources reviewed

| Source | Use in this audit |
|---|---|
| Current Loop Engine source and tests | Implementation authority. |
| Current Loop Engine Markdown and showcase source | Public-claim audit. |
| `/home/username/taedri.dev` | Read-only reference for typed contracts, graph identity, evidence boundaries, and independent verification. |
| Preserved `taedri-loop-v2-*` worktrees | Read-only reference for versioned definitions and context isolation. |
| GitHub repository `alisonjieli-png/loop-engine` | Published-state comparison. The local worktree remains authoritative until current changes are pushed. |

No Taedri file, registry, governance system, or product name should become a
Loop Engine dependency. A useful idea must be restated in Loop Engine terms,
implemented in the current class system, and tested here.

## Target architecture

### One definition per Loop

`LoopDefinition` is the immutable definition authority. It contains:

- definition ID, semantic version, and SHA-256 content digest;
- exact role profile ID and version;
- typed input and output role names through `LoopContract`;
- supported modes and installed executor modes;
- step profile, loop condition, and exit condition;
- canonical configuration facts;
- permissions, effects, and required capabilities.

`LoopStartRequest` carries the goal, definition, relationship,
`LoopRuntimeContext`, and event log in one object. The runtime records the
definition ID, version, and digest in Loop lifecycle events.

### One graph authority

`LoopGraphDefinition` is the authoritative static DAG. It binds:

- exact `LoopDefinitionRef` objects;
- explicit `LoopGraphVertex` records;
- typed `LoopGraphEdge` records;
- graph input and output ports;
- stages and composition groups;
- permitted member-mode policy;
- graph version and content digest.

`SolutionSpec` and `Canvas` build or project this graph. They do not define a
parallel runtime or graph authority.

Practitioner work produces a dynamic graph through recorded Starting,
Spawned by, Queried by, and Retrieved by relationships. The static Solution
DAG and dynamic Practitioner graph answer different questions. Both use
`Loop` as their only executable vertex type.

### Three public capability groups

`LoopRuntimeContext` exposes three public Core Architecture ports:

1. Intelligence Search and Retrieval
2. Web Research
3. Custom Plugins

Providers, settings, workspaces, approvals, stores, Runtime Memory, event
storage, reports, playback, MCP, skills, and trace export are internal runtime
mechanics. They do not appear as peer architecture groups.

## Findings

### 1. The one-Loop runtime rule is enforced

Status: implemented.

The package has one operational runtime class: `Loop`. Practitioner,
Intelligence, and Solution are role-profile branches. Passive Canvas
candidates, ports, edges, service objects, and reports do not run as graph
vertices.

The boundary ontology registers independently invokable work against the
`Loop` runtime and an exact profile or validated profile source. Conformance
rejects an operational boundary outside that ontology.

Adversarial check: add an executable service that bypasses a Loop envelope.
The boundary completeness and graph-vertex checks must fail.

### 2. Loop identity is versioned and digest-bound

Status: implemented.

`LoopDefinition` canonicalizes its configuration, computes its digest, and
checks the digest during deserialization. It verifies the registered profile,
role, modes, effects, and capabilities before execution. Every Loop holds its
definition reference.

Adversarial checks:

- change one serialized field without changing the digest;
- name an unregistered profile;
- declare a contract role that conflicts with the profile;
- select a mode outside the profile or definition;
- omit a required capability.

Each case must fail before work.

### 3. The graph is explicit, typed, and acyclic

Status: implemented for named port roles.

`LoopGraphDefinition` resolves every vertex to a definition, checks typed
connections, validates relationships, rejects cycles, and binds the graph
content to a digest. An incompatible conversion must use an explicit Adapter
Loop vertex. An edge cannot execute a hidden conversion.

Remaining gap: role-name compatibility does not yet validate complete value
schemas. Units, shapes, encodings, optionality, and field constraints need a
versioned schema contract and runtime value checks.

Adversarial checks:

- create a cycle;
- change a referenced definition after graph construction;
- connect incompatible roles without an Adapter Loop;
- put a passive candidate in the vertex table;
- claim a graph output that no vertex produces.

The current validator rejects these structural cases. It does not yet catch
every value-level mismatch inside two records that use the same role name.

### 4. Mode labels match installed execution

Status: enforced at Loop start and graph validation.

A definition separates supported modes from installed executor modes. A
`LoopRuntimeContext` also declares installed executors. Missing executor
coverage fails before work.

The generic Loop runtime can represent deterministic, hybrid, and
non-deterministic work when the matching executor is installed. The built-in
Solution runner currently installs deterministic execution only. It refuses a
hybrid or non-deterministic Solution leaf instead of running deterministic
code under a semantic label.

Remaining gap: built-in hybrid and non-deterministic Solution executors are
not implemented.

### 5. Intelligence has exact role profiles

Status: implemented.

The profile ontology contains four Intelligence branches and registered
operations for serving, searching, framing, resolving, invoking, loading,
replaying, comparing, scoping, and interpreting. Cross-layer search and
materialization also have registered profiles.

Intelligence search returns typed references. A retrieved item is loaded only
after selection and validation. Runtime Memory remains outside the four
persistent layers.

Adversarial checks:

- emit an Intelligence result from a Practitioner profile;
- treat a Markdown file or skill as a fifth intelligence layer;
- load a large body during discovery;
- make a candidate record active without independent review.

Each behavior violates the current architecture.

### 6. Runtime services use one restricted context

Status: implemented.

`LoopRuntimeContext` groups the three public Core Architecture ports and
internal runtime mechanics. `require()` checks capabilities, permissions, and
mode executors. `derive()` can only remove authority.

Remaining gap: some established constructor paths create this context through
an observable compatibility composition step. The resulting Loop still has a
complete definition and context. New public APIs should accept
`LoopStartRequest` directly.

### 7. Solution Canvas has the correct authority boundary

Status: implemented.

`Canvas` stores passive candidate alternatives. Each
`SolutionLoopCandidate` contains a complete Solution `LoopDefinition`.
Execution projects the selected candidates into one `LoopGraphDefinition` and
runs Solution Loops. Sequential pipeline work uses `CONNECTED_FROM`. Dynamic
fallback or branch work uses `SPAWNED_BY`.

The Canvas may restrict member modes. It does not own one execution mode.

### 8. Self-improvement is not a separate system

Status: implemented in the ontology and documentation.

Self-improvement uses `practitioner.self_improvement`. It receives a bounded
history population, searches current intelligence, and stages candidate
changes. A separate review decides whether a candidate becomes active.

### 9. Public terminology is converging

Status: current source and primary docs use the intended language.

The public terms are `Run History`, `event log`, `run record`, `report`, and
`evidence` according to meaning. Dynamic work uses `Spawned` rather than
biological relationship language. Intelligence uses `Queried by` and
`Retrieved by`; Solution pipelines use `Connected from`.

Remaining gap: `LoopLedger` is still the internal event-log class name. A
rename needs a versioned migration because saved runs and integrations depend
on it.

## Drift correction status

| Earlier drift | Current state |
|---|---|
| Several partial Loop specifications | Consolidated into `LoopDefinition`, with compatibility composition for established calls. |
| Several graph records without one authority | Consolidated under `LoopGraphDefinition`; Canvas and SolutionSpec are builders or projections. |
| Mode labels without physical executors | Rejected before execution. |
| Intelligence wrappers without exact profiles | Registered Intelligence profiles cover all four branches. |
| Services presented as many peer Core Architecture systems | Reduced to three public capability groups. |
| Self-improvement presented as another architecture system | Classified as a Practitioner task. |
| Passive Canvas records described as runtime vertices | Candidates remain passive until projected into Loop graph vertices. |
| Public role aliases that implied another runtime | Removed from the package root. |

## Remaining work, in priority order

### 1. Add full value schemas to ports

Define a versioned schema object for shapes, units, encodings, optional fields,
and constraints. Validate values when they enter a graph, cross each edge, and
leave the graph.

### 2. Add semantic Solution executors

Implement hybrid and non-deterministic Solution executors through the same
model gateway, permission checks, budgets, event vocabulary, and independent
verification used by other model-capable Loops. Do not weaken the current
fail-closed preflight.

### 3. Reduce compatibility composition

Migrate public constructors to accept `LoopStartRequest` or another small
typed object that resolves to it. Keep the compatibility path visible until
all established call sites and saved records have a versioned migration.

### 4. Plan the event-log class rename

Replace the internal `LoopLedger` name only through a compatibility-preserving
versioned change. The public behavior is already described as an event log and
Run History.

## Adversarial release checklist

Before calling the architecture complete, verify all of the following against
the current worktree:

- every executable graph vertex resolves to a complete `LoopDefinition`;
- every definition reference and graph digest survives round-trip checking;
- every selected mode has an installed executor;
- every graph is acyclic and every edge is typed;
- every data conversion uses an explicit Adapter Loop;
- every Intelligence operation uses a registered Intelligence profile;
- every Loop receives only the capabilities and permissions it requires;
- every Canvas candidate remains passive before graph projection;
- every self-improvement output remains a candidate pending separate review;
- Core Architecture exposes only the three approved public groups;
- the full self-test and conformance commands pass;
- examples run from the installation instructions;
- the README and showcase match the current class and profile names.

## Verdict

The core no longer exhibits the earlier structural drift. One versioned Loop
definition, one restricted runtime context, and one digest-bound graph now
anchor the architecture. The remaining gaps are narrower: full value schemas,
semantic Solution executors, compatibility-path reduction, and the deferred
internal event-log class rename.

Those gaps matter. None requires a second runtime, another graph authority, or
another Core Architecture group.
