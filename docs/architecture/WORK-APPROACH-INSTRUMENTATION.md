# Work-approach instrumentation and optimization

## Status

This document records an accepted architecture direction and a required
checkpoint. It does not claim that the checkpoint is implemented.

Loop Engine will represent observable work strategies as typed, versioned
configuration and measure how those strategies affect task outcomes. It will
not claim to reproduce biological consciousness. It will not persist private
reasoning traces.

## Architecture decision

`Loop` remains the sole operational runtime. A work approach changes the
configuration bound to a Loop. It does not create another runtime class.

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Exact assignment and typed input and output contracts
    ├── Procedure and step profile
    ├── Question and intelligence portfolios
    ├── Attention, control, memory-access, and context policies
    ├── Model route and prompt assembly when model use is permitted
    ├── Delegation, scheduling, verification, and exit policies
    └── Run History and typed Loop result
```

The target is one stable runtime with many composable passive contracts:

```text
Behavior at rest
├── LoopDefinition and LoopProfile
├── ProcedureDefinition and ProcedureStepSpec
├── GoalSpecification and objective settings
├── Question and Intelligence Portfolio definitions
├── Policy and Strategy records
├── PromptAssemblySpec and exact assembly evidence
├── Typed delegation inputs and context visibility
├── Verification and output contracts
└── Versioned approach definitions and suitability evidence

Behavior in motion
└── Loop
```

No `ResearchLoop`, `AuditLoop`, `CognitiveEngine`, or task-specific runtime is
needed. A materially independent assignment becomes another `Loop` with a
different definition, profile, relationship, contract, and policy set.

## Observable work functions

The human-work analogy is useful only after it is translated into precise
operational functions.

| Informal analogy | Architecture meaning | Typical implementation |
|---|---|---|
| Conscious work | Active questions, alternatives, decisions, and uncertainty | Working state, question graph, candidate plans, decision record |
| Attention | Selection of the information or question that deserves bounded work now | Attention strategy, salience observations, priority and routing policies |
| Automatic checks | Cheap controls that must run without discretionary prompting | Permission, schema, budget, deadline, redaction, freshness, and exit checks |
| Habit | A reviewed procedure that does not need to be reinvented | `ProcedureDefinition`, step specifications, procedural intelligence |
| Metacognition | Explicit monitoring of progress, assumptions, coverage, confidence, and method fit | Typed progress, epistemic, no-progress, and strategy-fit observations |
| Delegation | Another independently governed assignment, in series or parallel | `DelegationSpec`, typed ports, context visibility, scheduling, another `Loop` |

These are configuration and evidence dimensions. They are not new Loop roles
and do not change the three canonical roles.

## Governed granularity

Breaking work into small steps is useful. Turning every small operation into a
Loop is not.

```text
Reusable work program
└── LoopGraphDefinition
    └── Independently governed assignment
        └── Loop
            └── Configured procedure
                └── ProcedureStepSpec
                    └── Deterministic control check
                        └── Function, query, adapter call, or calculation
```

A step becomes another Loop only when it needs a materially independent goal,
contract, authority, budget, schedule, retry policy, verification obligation,
return destination, cancellation behavior, or Run History identity. Otherwise
it stays inside the owning Loop as a procedure step, control check, strategy
call, adapter call, or function.

## Typed reuse resolution

The implemented first slice resolves existing Solution priors through typed
records and the canonical Practitioner `Loop`:

```text
TaskFingerprintRequest
└── TaskFingerprint
    ├── SolutionLibrary candidate discovery
    ├── CompatibilityAssessment
    │   ├── hard matches
    │   ├── hard failures
    │   ├── soft differences
    │   └── unknown dimensions
    └── ResolutionRequest
        └── Practitioner Loop
            └── ResolutionDecision
```

`ResolutionOrigin` distinguishes exact reuse, parameterized reuse, a derived
candidate, composition, analogical guidance, external discovery, and novel
design. Human authority remains an independent permission or review dimension.
Run mode, scheduling, model thinking power, and placement also remain separate.

Hard compatibility and eligibility checks run before soft origin preferences,
quality, cost, latency, or verification ranking. Candidate-only derived work
cannot become executable reuse. A missing required candidate contract fails
closed. The selector makes zero model calls.

New Solution records store `task_fingerprint/v1` as structured fields with a
canonical digest. An exact compatibility reader accepts the former five-field
pipe representation. New code never emits it.

This slice does not complete Recursive Strategy Learning. Capability,
procedure, analogy, discovery, and novel-design producers still need adapters
to the shared `ResolutionCandidate` contract. Matched experiments, ablation,
held-out transfer, and suitability promotion remain part of this checkpoint.

## Minute guidance and Loop-specific instructions

Guidance must not become one giant prompt or an ambient shared-memory channel.
Small guidance units should be versioned, scoped, digest-pinned records such as
question templates, principles, failure patterns, decision rules, procedure
fragments, examples, counterexamples, and verification rules.

The flow for one Loop is:

```text
Available guidance records
├── Retrieve body-free references
├── Check scope, lifecycle, authority, and applicability
├── Rank within the permitted portfolio
├── Load only the selected bodies
├── Bind selected records to typed Loop input roles
└── Record considered, selected, rejected, loaded, and used references
```

Instructions supplied by a spawning Loop use the existing delegation boundary:

```text
Spawning Loop
├── DelegationSpec: goal, profile, contract, mode, budget, and constraints
├── LoopPortValue inputs: task-specific instructions and information
├── ContextVisibilityPolicy: exact selected references and memory visibility
└── Spawned Loop: fresh identity, bounded authority, and typed result
```

The default remains isolated. The spawning Loop must explicitly select every
shared reference and Runtime Memory capability. A preference or cached value
never grants authority.

## Interaction and optional feedback

Task compilation keeps interaction separate from execution authority:

```text
ask_when_material
├── continue through provided and delegated choices
└── ask only for a material non-delegable value

autonomous
├── continue through provided and policy-approved delegated choices
└── terminate with abstain_required when no safe policy exists
```

Autonomous mode does not grant model, network, spending, file, or external
effect authority. It prevents indefinite waiting; it does not guarantee that
every request can be completed.

A versioned template may expose optional `TaskFeedback` slots. Supplied values
become structured task input. Empty slots do not block autonomous work.
Persistent guidance during or after execution continues to use User Feedback
Intelligence rather than another feedback store.

## Memory type and access cost are independent

Memory meaning and access cost must remain separate axes.

```text
Memory meaning
├── Runtime Memory: bounded current-run working state
├── Episodic: reviewed prior experience
├── Semantic: reviewed reusable claims
└── Procedural: reviewed reusable procedures

Current access state
├── In context: already loaded for this invocation
├── Hot: available in the bounded current working set
├── Warm: locally indexed and cheap to retrieve
├── Cold: persistent or remote and more expensive to load
└── External: not yet governed intelligence and requires acquisition
```

The access labels above are proposed values for a typed access-state contract.
They do not redefine `Cache`, persistent intelligence, Runtime Memory, or Run
History. A cache is discardable. A promoted semantic or procedural record is
governed reusable intelligence even when no cache contains it.

## Existing prompt experiment authority

The current code already defines the beginning of the experiment boundary:

```text
ReasoningRequest
└── PromptAssemblySpec
    └── ModelInvocationRequest
        └── ModelGateway
            └── ModelInvocationResult
```

`PromptAssemblySpec` has named prompt blocks, a registered layout policy,
separate experiment seeds, a prompt digest, and a cache key. Authority stays at
the top of the prompt. Output contracts and final directives remain pinned at
the bottom.

This authority should be extended rather than replaced. The next checkpoint
must reconcile passive immutable records equivalent to:

```text
Exact prompt evidence
├── PromptAssemblySnapshot
│   ├── selected block IDs, versions, digests, and purposes
│   ├── ordering, token cost, and exclusion or truncation decisions
│   ├── selected intelligence and procedure references
│   ├── output and confidence contracts
│   └── model-route decision and assembly digest
└── Model invocation evidence
    ├── exact provider, model, deployment, and parameters
    ├── provider-reported usage when available
    ├── typed validation and verification outcomes
    └── result digest and Run History references
```

`PromptAssemblySnapshot` is a candidate contract name. Before adding it, the
implementation must prove that no existing record has the same meaning. The
same reuse check applies to every candidate type in this document.

## Styles are contracts, not adjectives

Question, confidence, list, and response styles affect behavior and evaluation.
They require typed identities instead of free-form labels.

```text
Question generation profile
├── first principles
├── historical analogy
├── adversarial or failure first
├── affected-person or future-maintainer view
├── uncertainty or information-gain first
└── exhaustive or minimal-sufficient coverage

Confidence contract
├── outcome probability
├── evidence strength and data quality
├── coverage and freshness
├── route agreement and stability
├── applicability and novelty risk
├── assumption dependence and robustness
└── review requirement

List contract
├── exhaustive, representative, or minimal sufficient
├── top-k or ranked
├── priority, risk, confidence, time, or dependency ordered
├── diversity maximized
├── Pareto frontier
└── exception or exclusion list

Response contract
├── boolean, label, score, scalar, probability, or interval
├── list, table, matrix, hierarchy, graph, or timeline
├── plan, schedule, policy, action, artifact, or alert
└── explicit abstention
```

Question, Operator, Response, and Decision remain independent coordinates. A
question style cannot grant permission or silently change the output contract.

## Exact approach evidence

An experiment cannot attribute improvement to a block merely because the block
was present. It needs exact configuration and outcome records.

The checkpoint must reconcile passive records equivalent to:

```text
LoopApproachSnapshot
├── task fingerprint and exact LoopDefinition reference
├── profile, procedure, active steps, and control policies
├── question, intelligence, memory-access, and context policies
├── exact prompt assembly references
├── model route, confidence, list, and response contracts
├── delegation, scheduling, verification, and exit policies
├── budgets and seeds
└── exact versions and digests

ApproachOutcomeEvidence
├── approach and task references
├── contract satisfaction and independent verification
├── task-specific quality measures
├── latency, cost state, model calls, and tool calls
├── failures, retries, repairs, and human intervention
├── context and question efficiency
├── intelligence, procedure, and delegation contribution
└── Run History and artifact references

ApproachSuitabilityRecord
├── applicable and incompatible task fingerprints
├── recommended configuration and alternatives
├── expected quality, cost, latency, and failure modes
├── sample size, uncertainty, and counterevidence
├── expiration and negative-transfer conditions
└── independent review and provenance
```

These objects are passive snapshots, evidence, and reviewed intelligence. None
executes work. None creates a new intelligence layer.

## Approach Experiment Practitioner

Approach optimization is a normal Practitioner assignment executed through the
same runtime.

```text
Practitioner Loop with an approach-experiment profile
├── Compile a frozen task population
├── Establish an exact baseline
├── Select configurable approach dimensions
├── Generate bounded approach variants
├── Run matched trials through Loops
├── Evaluate through independent Loops
├── Run single-factor ablations and interaction tests
├── Preserve failures and a Pareto archive
├── Test held-out task families and negative transfer
├── Stage suitability candidates
└── Route candidates to independent review
```

Useful experiment strategies include controlled ablation, factorial designs,
Bayesian search, evolutionary search with lineage, bounded online bandits, and
Pareto tournaments. The experiment strategy is a replaceable Strategy behind
one contract. It is not another runtime.

Matched claims must hold fixed the task, model, provider, deployment, effort,
tools, environment, budget, evaluator, and trial policy unless the changed
dimension is the declared treatment. Product-default comparisons remain useful
but must be labeled as product comparisons.

## Contribution and learning rules

Presence is not contribution. Use matched controls and interventions such as:

- leave-one-block-out prompt ablations;
- procedure-step removal;
- portfolio substitution;
- context-order swaps;
- model-route controls;
- memory and no-memory controls;
- delegation and no-delegation controls;
- identical seeds where the provider supports them.

Measure at least question-to-decision yield, intelligence-to-decision yield,
context-block contribution, procedure-step contribution, verification defect
yield, memory reuse benefit, research value of information, quality, cost,
latency, calibration, human intervention, and negative transfer.

The experiment-producing Loop cannot approve its own suitability candidate.
Promotion requires an independent Loop identity and authority. Later retrieval
and measured use are required before the system claims learning value.

## Privacy and observability boundary

Capture operational facts:

- activated and suppressed questions;
- selected and rejected references;
- exact context blocks and ordering;
- alternatives, decision criteria, and selected action;
- typed reason codes and short decision summaries;
- confidence dimensions, policy triggers, delegation decisions;
- verification findings, repairs, and outcomes.

Do not persist unrestricted private reasoning, hidden model traces, secrets, or
raw provider reasoning fields. Run History stores typed decisions, evidence
references, safe summaries, and measurements.

## Required checkpoint

The checkpoint name is **Work-Approach Instrumentation and Optimization**. Its
current state is `NOT YET PROVEN`.

The checkpoint is complete only when:

- the current contracts are inventoried before any new type is added;
- approach, prompt, context, question, confidence, list, and response
  configurations have exact versioned identities;
- memory meaning and access state are independent;
- active deliberation, attention, deterministic controls, procedure, and
  metacognitive observations are typed and bounded;
- spawning instructions use typed ports and explicit context visibility;
- exact approach and outcome evidence survives export and replay;
- at least one frozen task population has matched approach trials;
- ablations measure contribution rather than presence;
- held-out and negative-transfer tests run;
- suitability candidates require independent review;
- every experiment uses `Loop`, `LoopGraphDefinition`, Run History, and the
  canonical learning lifecycle;
- no new runtime class, untyped universal configuration, ambient service
  locator, or raw private reasoning store is introduced.

This checkpoint follows semantic recovery and the universal parameterization
and file-by-file alignment checkpoint. It does not authorize broad experiment
claims before the core runtime and installed-package path remain green.
