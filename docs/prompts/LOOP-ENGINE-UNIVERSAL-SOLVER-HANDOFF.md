# Continue the Loop Engine universal solver

Status: model-neutral development handoff and the sole broad continuation
brief. Load one prompt for a task. Do not combine this brief with another
repository prompt as a larger mandate.

This file is not an architecture authority. The current repository,
`AGENTS.md`, the Architecture Constitution, machine-readable contracts, and
enforcing tests take precedence.

Use this brief to continue the universal solver without turning an ambitious
research direction into a second runtime, a fixed workflow, or an unsupported
capability claim.

## Start from the live repository

Before changing anything:

1. Read `AGENTS.md`.
2. Record the branch, revision, dirty state, active processes, and concurrent
   writers.
3. Read the current architecture authority in the order given by `AGENTS.md`.
4. Preserve changes whose ownership is unknown.
5. Treat dated reports and prompts as evidence of what was believed or tested
   at that time, not as current source truth.

This durable brief does not carry a branch, revision, dirty-file count, owner
list, process list, or test total. Those facts become stale as work continues.
Use a generated packet conforming to
[`session_handoff/v1`](../contracts/session-handoff.schema.json) when one is
available. Recompute its HEAD and worktree digest before trusting it. If a
packet is absent or stale, inspect the checkout directly. Never infer file
ownership from a process ID or timestamp.

## Keep one operational runtime

Start every architecture explanation with the complete classification tree.

```text
Operational runtime type
└── Loop
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
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Show role-specific behavior through registered profiles, not subclasses.

```text
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence
│   │   └── serve, search, and frame
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

`Loop` is the sole executable graph vertex. `Node` is an ontology category.
`LoopNode` has no active public runtime meaning. The phrase "Loop Node
Framework" may describe the owner's concept, but it does not authorize a
`LoopNode` class, another executor, or another lifecycle.

## Define universal solving honestly

Universal solving means that a sufficiently representable unfamiliar task can
enter the same open task path without first matching a domain workflow. It does
not mean that every task can be completed with the available information,
authority, tools, models, time, or compute.

A valid terminal result may be:

- a verified solution;
- the best verified incumbent with explicit limits;
- a partial result with preserved evidence;
- a counterexample or contradiction;
- a material question;
- a precise capability, authority, information, or budget blocker; or
- an abstention with the next useful action.

The million-unseen-problem campaign is a research target. It remains unproven
until a frozen, varied population has been executed and independently
evaluated with exact denominators, exclusions, failures, costs, and holdouts.

## Use the correct operation boundary

Every meaningful operation is owned by a Loop. Not every helper call or data
transformation becomes another Loop.

Create an independent Loop only when the work needs its own goal, typed
contract, authority, budget, scheduling decision, retry, verification,
cancellation, or Run History identity. Keep serialization, arithmetic, local
transformations, adapter details, and other low-level mechanics inside the
owning Loop when they need none of those boundaries.

Represent repeated and recursive work without weakening that rule:

```text
Repeated work
├── One Loop repeats while its loop condition permits
├── A later activation continues from a new verified state revision
├── A spawning Loop creates bounded independent work through Spawned by
├── Intelligence work enters through Queried by and Retrieved by
├── Reusable Solution pipelines use Connected from
└── LoopGraphDefinition remains an acyclic reusable graph
```

Configuration lookup must have a bounded bootstrap. A Loop must not need an
unbounded chain of configuration Loops merely to learn how to start.

## Keep semantic work open and mechanics exact

During the current research phase, an authorized language model or explicit
user instruction owns unfamiliar task-conditioned meaning. Deterministic code
owns hard eligibility, permissions, budgets, state revisions, serialization,
workspace confinement, effect approval, exact computation, and evidence
capture.

A qualified narrow realization may later replace model reasoning within its
declared applicability region. It must retain an escape or escalation path.
The system must not infer authority from confidence, similarity, frequency, or
past success.

One semantic contract may have several realizations:

```text
Versioned Loop semantic contract
├── frontier or specialist language model
├── smaller language model
├── classical classifier, regressor, ranker, or forecaster
├── embedding, n-gram, LSH, or other retrieval projection
├── reviewed code or tool
├── reusable LoopGraphDefinition
├── narrow deterministic policy
└── human decision when authority or judgment requires it
```

These are implementations, candidates, evidence sources, or passive records.
They are not additional runtime types. A trained model remains a passive
artifact invoked by the classified Loop that owns the work. A domain inference
normally belongs to a Solution Loop. A cache remains a discardable
materialization, not trusted intelligence.

## Allocate computation for each cognitive responsibility

Treat the cognitive mesh as a task-specific arrangement of canonical Loops.
Select the realization, context, response program, compute allocation,
verification, and stopping conditions together. Measure controller overhead,
failed cheap attempts, verification, repair, and training amortization along
with execution cost. More historical information can justify cheaper work
only when it supports the current contract and measured task region.

Distillation can branch directly to a smaller LLM, classifier, ranker,
parameterized function, tool, or reusable Solution graph. Compare these
destinations instead of requiring every intermediate representation. Preserve
an observable return to broader reasoning when applicability fails. Keep
teacher agreement, independent correctness, relative routing regret, accepted
error risk, and coverage as separate outcomes.

For the research basis, proposed response formats, and twelve passive
cognitive Loop cards, see
[adaptive cognitive Loops and amortized computation](../research/ADAPTIVE-COGNITIVE-MESH-AND-AMORTIZED-COMPUTATION-2026-09-04.md).
The cards require exact profile and authority binding before runtime use.

## Preserve the current architecture boundaries

Do not create broad new planes because a conceptual diagram names them.

```text
Loop work
├── Starting Practitioner
│   ├── preserves the task and current state
│   ├── selects the next bounded responsibility
│   ├── queries Intelligence Loops when context is needed
│   ├── spawns independently governed Practitioner work when needed
│   ├── proposes Solution work through typed contracts
│   └── integrates verified observations
├── Intelligence Loops
│   ├── search first and return small typed references
│   └── materialize selected bodies after scope and permission checks
└── Solution Loops
    ├── execute typed actions and transformations
    ├── verify outputs and effects
    └── connect through the authoritative LoopGraphDefinition
```

Core Architecture has exactly three public capability groups: Intelligence
Search and Retrieval, Web Research, and Custom Plugins. Providers, models,
settings, stores, workspaces, approvals, Runtime Memory, Run History, reports,
and playback are internal runtime mechanics.

## Compile context and response shape per Loop

A consequential model call needs one coherent semantic responsibility. It
should not be a tiny pseudo-instruction or an unobservable whole project.

Use the current prompt-resource, context-manifest, choice, and template
negotiation contracts before adding new template types. A response shape is a
candidate interface. The answering model may accept, extend, simplify,
compose, replace, or reject negotiable fields. Identity, provenance,
authority, state revision, effects, and acceptance criteria remain fixed.

Retrieve small references first. Materialize a large body only after selection
and permission checks. Record why each context item was included, excluded,
compacted, or considered misleading. Do not place a complete architecture
mandate into every model call.

## Keep memory meanings separate

```text
Current-run memory
└── Runtime Memory

Persistent intelligence
├── Context Intelligence
├── Code Intelligence
├── Runtime History and Solution Intelligence
└── User Feedback Intelligence

Rebuildable access projections
├── exact and structured indexes
├── lexical and n-gram indexes
├── MinHash, SimHash, and LSH indexes when qualified
├── embedding indexes when qualified
└── graph and outcome projections when qualified
```

Episodic, semantic, procedural, negative, and social memory may classify the
meaning or use of records. They do not create persistent intelligence layers.
Hot, warm, cold, and external may describe access cost. They do not describe
meaning or lifecycle.

Historical path strength is evidence worth considering. It is not an order to
follow the popular path. Preserve failures, counterexamples, negative transfer,
late invalidation, scope, freshness, and uncertainty.

## Separate occurrence, similarity, and outcome

Do not use one digest for several kinds of identity.

```text
Exact occurrence identity
└── this activation in this run, branch, graph version, and state revision

Similarity descriptions
├── semantic situation signature
├── input and output shape signature
├── cognitive motif signature
├── Loop definition signature
└── structural subgraph signature

Outcome evidence
└── what was observed locally and what later work showed
```

The target fingerprint chain is:

```text
physical provider attempt
→ logical semantic call
→ exact Loop activation occurrence
→ state transition
→ cognitive episode
→ structural subgraph
→ solution branch
→ whole task
→ campaign
→ cross-run motif or policy experiment
```

Each scale needs a versioned record and explicit links. Derived lexical,
n-gram, embedding, graph, or outcome representations must be rebuildable from
canonical records.

A retrieval result is a candidate package. It should state why it matched,
where it differs, whether contracts and effects are compatible, what outcomes
are known, what failed, and that prior work is not proof for the current task.

## Diagnose and repair the smallest boundary

Recovery begins with observations, not a universal retry table.

```text
Preserve evidence
→ confirm whether the intended physical work ran
→ locate the earliest supported divergence
→ generate competing explanations
→ preserve valid work
→ choose a discriminating probe
→ propose the smallest changed recovery
→ validate authority and compatibility
→ execute the changed attempt
→ verify the original failure and regression surface
→ integrate, backtrack, roll back, return an incumbent, or abstain
```

A deterministic monitor may report repeated state, repeated failure, branch
growth, or budget depletion. It does not decide the semantic recovery. When no
reasoning route is available, preserve the incumbent and return a precise
blocker.

Self-modification remains a self-improvement Practitioner task. It may stage a
candidate. It may not review, approve, or promote its own work.

## Learn through governed comparisons

```text
Verified Run History
→ outcome-linked learning candidate
→ independent review
→ explicit promotion for a bounded scope
→ later retrieval into a fresh run
→ observed use
→ matched assisted and fresh comparison
→ negative-transfer and late-invalidation checks
→ retain, narrow, supersede, quarantine, or roll back
```

Shadow, advisory, challenger, paired, and canary describe experiment exposure.
They do not replace the governed candidate lifecycle.

Do not use whole-run success as every stage's label. Keep output admission,
local verification, downstream use, branch contribution, task outcome, later
invalidation, cost, latency, tokens, attribution method, and attribution
confidence separate. Missing observations remain unknown.

## Verify current maturity from saved evidence

The receiving agent must classify live facts rather than inherit a status table
from this prompt.

| State | Required meaning |
|---|---|
| Current | Implemented behavior with evidence bound to the checkout being inspected. |
| Partial | Some required links exist, but the complete product behavior is not established. |
| Target | Planned behavior with an identified authoritative boundary and acceptance test. |
| Blocked | Work cannot proceed within current information, authority, capability, or budget. |
| Unproven | A claim has no valid evidence at the requested scope. |

Verify separately whether the checkout contains stage occurrence records,
paired assignment and exposure contracts, a rebuildable evidence projection,
product-path exposure, packet-body inspection, complete control freezing,
stage contribution, and an executed assisted-versus-fresh comparison. A type,
index, diagram, or offline fixture does not establish model use or task
improvement.

Prior stage intelligence improving a live task, a cheaper model being
sufficient for a stage, a learned policy generalizing, a reusable custom model
forge, and one-million-problem performance all remain unproven unless a current
evidence packet says otherwise and links the exact supporting artifacts.

## Complete one vertical slice next

After reconciling concurrent work, prefer this sequence:

```text
Exact activation occurrence
→ semantic, shape, contract, and motif signatures
→ multi-channel prior candidate retrieval
→ hard contract, privacy, effect, and authority facts
→ model-owned USE, MODIFY, COMBINE, IGNORE, RETRIEVE_DEEPER,
  START_FRESH, or SPAWN_CHALLENGER decision
→ response program, context plan, and model portfolio
→ typed action
→ observation and local verification
→ stage outcome update
→ later branch and task contribution
→ paired assisted-versus-fresh comparison from one controlled stage state
```

Use those disposition names only after checking for equivalent current
contracts. Add the smallest missing typed extension at the existing authority.
Do not create a parallel store, selector, event vocabulary, graph authority,
settings service, or runtime.

Only after this slice produces valid comparative evidence should the work move
to broader context-plan reuse, stage-level model allocation, tuned small
models, classical cognitive support models, or campaign volume.

An advisory/fresh fixture classified as mechanism-only does not satisfy valid
paired comparative evidence.

## Verification and handoff report

Run the smallest relevant check first. Then run the owning component checks,
self-test, conformance, clean installation, examples, playback, and browser
checks when the claim depends on them.

Report:

- exact branch, commit, dirty state, and concurrent work;
- current architecture authority and any contradiction found;
- files changed, purpose, owning boundary, and key symbols;
- commands run and exact results;
- which evidence is fixture, local runtime, or live provider evidence;
- model calls, provider routes, token completeness, elapsed time, and cost
  state;
- treatment assignment, control construction, exclusions, and evaluator;
- failures and negative results with the same prominence as successes;
- what is current, partial, target, blocked, and still unknown; and
- the next smallest experiment with the highest architecture information
  value.

Put volatile facts and exact evidence records in an immutable generated
`session_handoff/v1` packet. Bind each test result to the full source HEAD,
worktree digest before and after the command, evidence class, artifact digest,
provider-call count, and limitations. Do not hand-write a packet or assign an
owner without an explicit claim.

Do not claim AGI, universal task completion, convergence, successful learning,
cheaper routing, or campaign readiness unless the saved evidence directly
supports that exact claim.

## Read these sources instead of copying them

- [LLM-first universal solving](../guides/llm-first-universal-solver.md)
- [Work-approach instrumentation and optimization](../architecture/WORK-APPROACH-INSTRUMENTATION.md)
- [Generalized self-tuning guidance](GENERALIZED-LOOP-NODE-SELF-TUNING-GUIDANCE.md)
- [Adaptive Practitioner architecture](../architecture/ADAPTIVE-WORK-APPROACH-ARCHITECTURE.md)
- [Universal Loop standard](../reference/UNIVERSAL-LOOP-STANDARD.md)
- [Cognitive architecture audit, 2026-09-02](../verification/COGNITIVE-ARCHITECTURE-AUDIT-2026-09-02.md)
- [`session_handoff/v1` packet schema](../contracts/session-handoff.schema.json)
- [Dated GPT-6 Astra readiness note](../context/GPT-6-ASTRA-READINESS-2026-09-04.md)
- [Dated long-horizon recurrence, skills, and state research review](../research/LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md)
- [Dated procedural-memory, predictive-state, and information-value review](../research/PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md)
- [Dated stage assistance integration audit](../verification/STAGE-ASSISTANCE-INTEGRATION-AUDIT-2026-09-04.md)
- [Current offline predictive-state, procedural-memory, and stage-assistance verification](../verification/PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md)
- [Dated Kaggle metadata campaign report](../verification/KAGGLE-120-ACCESS-PREFLIGHT-2026-09-04.md)

The governing rule is simple: Loops own the work. Models, tools, code, caches,
indexes, templates, and learned policies are replaceable realizations or
evidence used by Loops. They earn broader use through verified outcomes, not
through repetition or confidence.
