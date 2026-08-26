# Continue building and verifying Loop Engine

Paste this prompt into OpenCode or Codex. Use
`/home/username/loop-engine` as the workspace directory.

## Authority and purpose

Read `AGENTS.md` first. It is the repository instruction source. This prompt
is a portable execution brief. It does not replace `AGENTS.md`, create a new
governance system, or override a newer explicit owner instruction.

Continue polishing, simplifying, implementing, testing, falsifying, and
documenting Loop Engine until the requested work is real and verified. Do not
stop at a plan when the next safe implementation or test is clear.

Use plain English. A developer using English as a second language should be
able to understand each public page on one reading. Avoid hype, AI slang, em
dashes, en dashes, decorative slogans, and vague evidence metaphors. Use
report, record, log, contract, event history, or evidence when accurate.

## Start from the current workspace

Run these checks before changing files:

```bash
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git remote -v
git status --short --branch
git worktree list
```

Both repository paths should resolve to `/home/username/loop-engine`. The
remote should be `https://github.com/alisonjieli-png/loop-engine.git`.

Inspect active processes and concurrent agents before editing. Existing
changes belong to the user or another session unless ownership is clear.
Preserve them. Use one writer per semantic boundary. Do not restore, discard,
reformat, commit, push, publish, delete, rerun a completed provider campaign,
or perform another external effect without authority from the current request.

Read in this order:

1. `AGENTS.md`
2. `docs/context/CODEX-START-HERE.md`
3. `docs/context/REFERENCE-SOURCES.md`
4. `README.md`
5. `docs/components/README.md`
6. only the component guides and source files needed for the current work
7. `humanizer-context.md` before changing public prose
8. verified case studies and benchmark artifacts only when a claim depends on
   them

Treat current code and executable evidence as authority for shipped behavior.
When code and documentation disagree, determine which behavior is correct,
fix the authoritative boundary, and update the dependent documentation. Do
not make a diagram appear correct while the runtime remains wrong.

## The architecture law

There is one operational runtime type: `Loop`.

```text
Operational runtime type
└── Loop
    ├── LoopDefinition
    │   ├── definition ID, semantic version, and content digest
    │   ├── registered role profile and version
    │   ├── typed input and output roles
    │   ├── supported modes and installed executors
    │   ├── step profile
    │   ├── loop condition and exit condition
    │   ├── configuration facts
    │   └── permissions, effects, and required capabilities
    ├── LoopRuntimeContext
    │   ├── Intelligence Search and Retrieval
    │   ├── Web Research
    │   ├── Custom Plugins
    │   └── internal runtime mechanics
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
    ├── Purpose and domain categories
    ├── Selected run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Work and call budgets
    ├── Model settings when model use is allowed
    │   ├── thinking power
    │   ├── provider and model route
    │   ├── exact maximum output capability
    │   └── retry and failover policy
    └── Run record
        ├── Run History events
        ├── returned result
        ├── validation outcome
        └── relationship targets and returned Loop IDs
```

Do not use these terms interchangeably:

- Runtime type says what runs. It is always `Loop`.
- Relationship says how the Loop entered the active structure. It is Starting,
  Spawned by, Queried by, Retrieved by, or Connected from.
- Role says the broad responsibility. It is Practitioner, Intelligence, or
  Solution.
- Profile is a reusable, versioned behavior preset within a role.
- Category organizes purpose, domain, search, and reporting metadata. It does
  not create a runtime class.
- Mode says how the Loop may resolve work.
- Step profile says which ordered steps the Loop may run.
- Settings carry contracts, budgets, permissions, effects, model routes,
  thinking power, loop conditions, and exit conditions.

`LoopGraphDefinition` is the one static DAG authority. Every graph vertex
contains an exact `LoopDefinitionRef`. Every edge names typed source and target
roles. `SolutionSpec` and `Canvas` build or project this graph. They do not
create another graph authority.

Every known operational boundary must be classified in the existing
`core.boundary_registry`. Its ontology entry must say
`runtime_type: Loop` and bind either an exact registered versioned role profile
or a validated typed profile source. Core Architecture has only
Intelligence Search and Retrieval, Web Research, and Custom Plugins. Internal
runtime mechanics remain separate. A classified Loop must own each
work-producing call. Treat a missing, extra, unknown, unversioned, or
role-incompatible boundary as a build failure.

Role and profile do not determine relationship. A Starting Practitioner may
spawn Practitioner subproblem Loops and query an Intelligence Query Loop. The
Query Loop retrieves Intelligence Item Loops. A Starting Solution connects to
deterministic Solution pipeline Loops and spawns Solution Loops only for real
dynamic branch, fallback, repair, or ensemble work.

Every Loop graph vertex has its own mode when its contract, executor coverage, and
permissions allow it. A Canvas or pipeline has no single execution mode. It
may only restrict the modes permitted on member Loops. Thinking power is
a model setting for authorized hybrid and non-deterministic Loops. It is not a
fourth mode.

`Sub` remains a compatibility alias for the legacy `spawned` topology value. In
current public language, use Spawned by only for a real dynamic spawn. Do not
create a Sub-Practitioner runtime, Sub-Intelligence runtime, or Sub-Solution
runtime.

## Role profile ontology

```text
Loop role profiles
├── Practitioner
│   ├── practitioner.reference_nine_step
│   ├── practitioner.compact_five_step
│   ├── practitioner.research
│   ├── practitioner.solver
│   ├── practitioner.verifier
│   ├── practitioner.self_improvement
│   └── practitioner.code_execution
├── Intelligence
│   ├── intelligence.search
│   ├── intelligence.materialize
│   ├── intelligence.context.serve, search, frame
│   ├── intelligence.code.resolve, invoke, package
│   ├── intelligence.runtime_history_solution.search, replay, compare
│   └── intelligence.user_feedback.serve, scope, interpret
└── Solution
    ├── solution.atomic_component
    ├── solution.pipeline
    ├── solution.router_fallback
    ├── solution.ensemble
    └── solution.validator
```

Profiles inherit only reusable definitions. Each running Loop still receives
its own relationship, role binding, mode, contract, step profile, budget,
permissions, exit condition, and event identity.

## Required separation of concerns

```text
Loop runtime
├── Executes one bounded Loop graph vertex
├── Owns lifecycle and spawning and spawned relationships
└── Emits canonical events

Loop Practitioner
├── Understands a task
├── Searches Intelligence and capabilities
├── Starts candidate, research, execution, repair, and verifier Loops
└── May compile a Solution Canvas

Intelligence Library
├── Context Intelligence
├── Code Intelligence
├── Runtime History and Solution Intelligence
└── User Feedback Intelligence

Solution Canvas
├── Describes what runs for a new input
├── Connects typed Solution Loop ports
└── Defines routing, fallback, ensemble, validation, and output behavior

Core Architecture
├── Intelligence Search and Retrieval
├── Web Research
└── Custom Plugins

Internal runtime mechanics
├── providers, model gateway, and typed settings
├── workspaces, sandboxes, and effect approvals
├── stores, context artifacts, and Runtime Memory
├── Run History and event log
└── reports, live view, playback, and trace export
```

Self-improvement is a Practitioner task. It is not a fourth role or a separate
engine. It reviews a bounded historical population, searches current
Intelligence, stages candidates, and stops before independent promotion.

Runtime Memory is temporary and run-scoped. It is not a fifth persistent
intelligence layer. A Markdown file, skill, repository, transcript, vector,
or database row is a source format, not an intelligence layer.

## Required relationship behavior

Use this tree when testing and documenting recursive work:

```text
Task
└── Starting Practitioner [non-deterministic]
    ├── queries Intelligence Query Loop [deterministic]
    │   └── retrieves Intelligence Item Loops from all four layers
    ├── may spawn Candidate Practitioner A [non-deterministic]
│   ├── Code Intelligence selection [deterministic]
│   └── Code execution [deterministic]
    ├── may spawn Candidate Practitioner B [non-deterministic]
│   ├── Code Intelligence selection [deterministic]
│   └── Code execution [deterministic]
    ├── may spawn a Synthesis Practitioner [non-deterministic]
    ├── may spawn a Verifier [deterministic]
    │   └── may spawn a Repair Practitioner after failure
    └── builds a compiled Solution Canvas
        └── Starting Solution Loop
            ├── Connected Solution Loop [mode declared on this node]
            ├── Connected Solution Loop [mode declared on this node]
            └── may spawn a dynamic branch or fallback Solution Loop
```

Then test a later input that starts the compiled solution directly:

```text
Starting Solution Loop
├── Connected Solution Loop: validate input
├── Connected Solution Loop: transform
├── Connected Solution Loop: execute selected capability
├── Connected Solution Loop: verify output
├── dynamic fallback selected
│   └── Spawned Solution Loop
└── Connected Solution Loop: format output
```

A Spawned Loop may use a different mode from its spawning Loop. Spawning Loop
permission limits delegation authority, but mode is not copied. Model use
never grants file, network, secret, spending, command, or external-effect
authority.

## Typed design and maintainability

- Prefer immutable data classes and small named request or service objects.
- Replace long argument lists and unstructured keyword dictionaries with one
  typed object when the values belong to one concept.
- Keep modules cohesive. Split implementation from focused checks before a
  module becomes a monolith.
- Keep public functions below the repository parameter cap.
- Give every Loop connection named, versioned, typed ports.
- Reject incompatible shapes before execution.
- Version public profiles, settings, serialized records, adapters, and event
  schemas.
- Extend current registries and canonical event vocabulary. Do not create
  parallel runtimes, stores, registries, ledgers, search engines, approval
  systems, or sources of truth.
- Separate discovery, eligibility, ranking, selection, materialization,
  execution, evaluation, acceptance, promotion, and publication.
- Keep artifact-valid, score-valid, quality-accepted, selected, promoted,
  invalidated, and failed as separate states.

## Delegation and context isolation

- A fresh Spawned Loop receives only its typed inputs and explicitly selected
  references.
- Do not expose a spawning Loop object, spawning Loop goal, private history,
  sibling context, or shared ledger to a Spawned Loop executor.
- Runtime Memory is available only through an explicit typed service and
  policy.
- Async lifecycle must include start, status, typed update, cancel, wait,
  terminal result, deadline handling, and no orphaned task.
- Context isolation in one Python process is a public contract boundary, not a
  hostile-code security sandbox. Run untrusted spawned Loops in a process or
  container boundary.

## Intelligence rules

- Query all four persistent layers when the task contract requires them.
- Keep empty layer results visible.
- Return small typed references from search. Materialize a body only after
  selection, compatibility checks, and permission checks.
- Use several reviewed Context lenses for model-led candidate work. Include
  first principles, alternatives, missing information, adversarial risks,
  cost and resources, verification, and output contract when relevant.
- Candidate A and Candidate B should receive meaningfully different Context
  portfolios.
- Code Intelligence must name immutable source identity, provenance, license
  state, version, dependencies, typed ports, effects, tests, independent
  verification, and digest before active use.
- Packages, repositories, tools, and large systems stay behind searchable
  references. Do not put a million-line body in a database row or model
  prompt.
- Imported skills and generated intelligence remain candidate-only. Candidate
  skill instructions may enter a candidate-review Loop, not an active task
  Loop.
- Nothing promotes itself because it ran, scored well, or came from a model.

## Providers and model calls

- Use real configured providers for provider integration and performance
  evidence.
- A local protocol fixture may test a contract. It does not prove provider
  connectivity or model quality.
- Never replace a failed provider call with canned or synthetic output.
- Resolve the exact provider-supported maximum output for the selected model.
  Request that maximum. Do not invent a lower default.
- Refuse before the call when the maximum cannot be established from a
  source-backed capability or exact provider response.
- Preserve provider-reported input and output tokens. Missing usage and price
  remain unknown, not zero.
- Count physical attempts at the actual provider boundary.
- Keep retry, same-provider fallback, cross-provider failover, formatting
  repair, evaluator-triggered repair, and replanning distinct.
- Do not enable failover unless the run contract permits it.
- Never place credentials, authorization headers, private prompts, or secrets
  in source, events, reports, traces, or artifacts.

## Effects, MCP, skills, workspaces, and sandboxes

- Capability and intelligence discovery must not execute the selected effect.
- Bind an approval to one exact effect, arguments digest, target, operation,
  and request identity.
- Consume one-use approval authority before crossing the effect boundary.
- Do not retry a failed effect automatically. A retry needs a new explicit
  attempt and idempotency decision.
- Validate MCP arguments against the discovered input schema.
- Enforce the declared timeout at the transport boundary.
- Launch local tool servers with a minimal explicit environment.
- Capture raw tool and harness output in the existing content-addressed
  Context Artifact store. Keep small output inline only under policy.
- Preserve raw and compacted artifacts separately.
- Run compaction as an Intelligence Loop through the universal Loop runtime.
- Confine workspace paths. Refuse absolute paths, traversal, symlink escape,
  and unsafe overwrite.
- Use immutable container images, no implicit pulls, bounded CPU, memory and
  processes, dropped capabilities, a read-only container filesystem, and network disabled by
  default.
- Treat E2B, Modal, or another remote backend as unavailable until a real
  adapter and connected verification exist.

## Run History, reporting, Studio, and tracing

- Run History is the canonical append-only event history.
- Use one canonical event vocabulary and one OpenTelemetry projection.
- Preserve parent span relationships in a real OpenTelemetry SDK export.
- Do not export raw prompts, secrets, tool bodies, intelligence bodies, or
  private spawned context.
- Generate reports, live views, playback, model-call panels, intelligence
  consumption, approvals, and Solution Canvas views from canonical events.
- Browser rendering needs real browser verification. Server or string tests do
  not prove visual behavior.

## Benchmark and comparison rules

A selected full-system run requires:

```text
frozen real task population
  -> Starting non-deterministic Practitioner
  -> reviewed Context and executable Code Intelligence
  -> bounded Spawned Practitioner Loops and typed Intelligence relationships
  -> candidate comparison and verification
  -> compiled and executed Solution Canvas
  -> independent evaluator
  -> verified Run History, playback, and report
```

Deterministic Intelligence Query and Item Loops may retrieve material. Other
deterministic Loops may execute, validate, and grade. A
component probe, provider check, partial Canvas run, or deterministic replay is
not a selected non-deterministic benchmark run.

Freeze task selection, source revision, input hashes, evaluator, metric
direction, call ceiling, time budget, model, provider, and output maximum
before outcomes. Keep every attempted task and failure in the denominator.
Preserve excluded diagnostics and all physical calls.

Use published competitor results only with their exact benchmark, task
population, model, harness version, evaluator, tools, attempts, source, and
limitations. Do not rerun a competitor merely to compare architecture. Do not
claim a winner unless Loop Engine and the comparison arm use the same frozen
population and evaluator, with enough configuration and cost information to
support a fair conclusion.

## Older Taedri sources

The Taedri repositories and isolated worktrees are reference material. Follow
`docs/context/REFERENCE-SOURCES.md`.

For one proposed semantic transfer:

```text
Older source idea
├── State one invariant
├── Verify the source revision and evidence
├── Find the exact Loop Engine gap
├── Map it to one existing component
├── Reimplement it in Loop Engine terms
├── Add positive and adversarial tests
├── Run it through Loop Engine
└── Record provenance and limitations
```

Do not bulk copy files, directories, registries, authority systems, campaign
state, business claims, caches, generated output, credentials, or old product
terminology. Do not make Taedri a runtime dependency of Loop Engine.

## Current completion posture

Assume completion is unproven. Recheck current code before relying on this
list. At the time this prompt was written, important audit areas included:

- enforced Spawned Loop context isolation and async lifecycle durability;
- one native durable approval path shared by MCP, workspaces, and harnesses;
- approval and event binding for workspace writes and commands;
- connected Context Artifact use at Spawned Loop, MCP, and harness boundaries;
- candidate skill isolation from active task context;
- one Run History-owned OpenTelemetry projection and real parented SDK traces;
- exact maximum-output application in every executable external adapter;
- honest unavailable status for optional harnesses without installed and
  tested packages;
- removal or containment of old public runtime surfaces that compete with the
  universal Loop;
- explicit result-state separation in benchmark evaluators and reports;
- reconciled README, registry, source-review, case-study, and saved-result
  status;
- real browser verification of Studio;
- a matched benchmark population before any harness-superiority claim.

Do not mark one of these complete because a class, field, diagram, or unit test
exists. Find the execution path and try to falsify the claim.

## Working loop

For each safe work packet:

1. State the accepted outcome and decisive check.
2. Inspect existing implementations and concurrent ownership.
3. Search for reuse before writing another abstraction.
4. Identify several feasible fixes.
5. Choose the smallest fix at the authoritative boundary.
6. Implement with typed objects and clear separation of concerns.
7. Test positive, negative, ambiguous, adversarial, and unrelated behavior in
   proportion to risk.
8. Run the real integration path when the claim depends on it.
9. Preserve failed attempts and unknown accounting.
10. Update current documentation and tree diagrams.
11. Run scoped checks, package self-test, conformance, clean installation,
    examples, and UI checks that match the claim.
12. Review the diff for secrets, generated debris, stale terms, broken links,
    hidden scope expansion, and concurrent overlap.
13. Continue to the next highest-value safe gap.

## Final report

Report:

- the state transition achieved;
- exact files and public APIs changed;
- tests, integrations, and falsification performed;
- real provider calls, input tokens, output tokens, cost, and unknown fields;
- failures and invalidated claims;
- current repository, branch, revision, dirty state, and concurrent work;
- what remains incomplete and why;
- rollback or recovery information for material changes;
- the next highest-value work packet.

Do not say the system follows all rules until a requirement-by-requirement
completion audit proves it from the current worktree.
