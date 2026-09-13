# Run paths and dimension coverage, September 13, 2026

The inventory has 25 required baseline dimensions, 21 proposed refinements,
and two additional wrapper/control dimensions. These are configuration
choices, not 48 independent executors. Valid combinations depend on exact
contracts, installed capabilities, authority, and task requirements.

This report lists path families and the coverage needed to qualify them.
It does not claim that all dimensions, values, fallbacks, or interactions
have been tested. The [dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
and [complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
remain the detailed requirements.

## Shared classification

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
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

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

## Paths with executable implementations

| Path family | Variants and entry point | Qualification boundary |
|---|---|---|
| Direct model reasoning | Native Practitioner through `ModelExecution` and the canonical gateway. | Real-provider component evidence exists; broad task success is not established. |
| External text-response harness | `HarnessSemanticBinding` and the configured harness manifests below. | Fresh confined process and brokered model calls. Native tool use is not implied. Availability and qualification are per manifest and version. |
| Generated project | Public `solve_task` with generated source, workspace execution, and independent verification. | Docker or another declared host execution policy is required. Capability gaps and material questions remain valid outcomes. |
| Host-owned operations | `HostRuntimeBinding` with explicit capabilities, approvals, and completion verifiers. | The host must implement and qualify its operations and evaluator. |
| Existing deterministic capability | Exact registered resolver or independently promoted reusable implementation. | Works within the capability's declared contract; not arbitrary natural-language solving without a model. |
| Solution Canvas | `compile_solution`, `run_compiled`, and `run_solution`. Atomic components and connected pipelines. | All three modes are representable; execution requires the selected compatible executor and model authority where applicable. |
| Solution composition | Ordered fallback, average, vote, weighted combination, evaluated selection, and routing. | Exact member contracts and required evaluator/router bindings must resolve. |
| Intelligence work | Search, select, materialize, frame, invoke, replay, and interpret through classified Intelligence Loops. | Context, Code, Runtime History and Solution, and User Feedback are the four persistent layers. Runtime Memory remains run-scoped. |
| Reactive work | Ephemeral, checkpointed, or durable activations; leases, heartbeat, cancellation, and output serving. | Offline lifecycle evidence exists. It does not qualify every long-running external harness. |
| Reuse and improvement | Candidate harvesting, independent qualification, explicit promotion, exact or compatible reuse. | A successful local repair does not automatically update active intelligence. |
| Transactional semantic work | Candidate semantic output, independent verification, exact effect authorization, and trusted-state commit. | Component contracts and controls exist; the similarly named experimental embodiment remains separately unqualified. |
| Reports and playback | Bound solve outcomes, Run History, graph views, artifact references, saved playback, and Studio. | Chain integrity does not prove complete physical accounting or a working exported solution. |

The [ways-of-running guide](../context/WAYS-OF-RUNNING.md),
[host guide](../guides/embedding-loop-engine.md), and
[Solution Canvas guide](../components/solution-canvas/README.md)
provide the owning interfaces. Mode, relationship, profile, and physical
placement remain separate choices on each Loop.

## Configured harness paths

Alongside the native gateway, the current manifests name these 19 adapters:

| Adapter | Adapter | Adapter |
|---|---|---|
| `aider` | `cline` | `codex` |
| `continue` | `forgecode` | `freebuff` |
| `gemini_cli` | `goose` | `gptme` |
| `hermes_agent` | `kilo` | `mini_swe_agent` |
| `mistral_vibe` | `nanocode` | `opencode` |
| `openinterpreter_rust` | `pi` | `qwen_code` |
| `trae_agent` | | |

This is a manifest inventory, not 19 currently qualified task solvers.
Freebuff's hosted protocol is explicitly unqualified. Other adapters have
different protocol, admission, and task results. Read the
[harness guide](../../embodiments/HARNESS-GUIDE.md) and
[recorded trials](HARNESS-EMBODIMENT-TRIALS-2026-09-10.md).

The separate `OpenCodeStepSession` supports a narrower trusted-host native
path. It refuses unsupported gateway request fields. It is not equivalent
to the confined text-response adapter or a complete `ModelExecutionSession`.
See [native session limits](../opencode-step-instances.md).

## Process, output, wrapper, and optimization paths

| Family | Choices | Current status |
|---|---|---|
| Process placement experiments | In-process, fresh process per step, persistent session, session pool, parallel portfolio, durable reactive worker. | Six executable deterministic arrangements; no general live-model qualification implied. |
| Other embodiment launchers | Adaptive tree, reuse-first, native OpenCode per step, brokered container, local agent host, transactional semantic, speculative decoding. | These particular launchers are planned and refuse. Related components elsewhere may exist. |
| Output behavior | One output, continued candidates, verified portfolios, best/all/random/as-of serving. | Bounded component and deterministic experiment coverage; no general live continued-production matrix. |
| Wrapper composition | Direct adapter, ordered wrapper layers, alternative compositions. | Versioned records and indexed enumeration; additional wrapper executors remain unqualified. |
| Native control ownership | Owning Loop, delegated, supervised, disabled, unsupported, unknown, independently per control. | Declarations and refusal checks; enumeration is not native goal or control execution. |
| Grid search | Lazy exact enumeration, resumable cursor, disjoint shards. | Implemented proposal computation. Cursor exhaustion is not whole-campaign completion. |
| Seeded exploration | Random configuration proposals. | Implemented proposal computation. |
| Bayesian optimization | Tree-structured Parzen estimation. | Actual optional Optuna implementation, tested on disclosed controls. |
| Genetic optimization | Non-dominated sorting, mutation, crossover, multiple objectives. | Actual optional Optuna implementation, tested on disclosed controls. |
| Numeric vector optimization | Covariance matrix adaptation. | Optional implementation for compatible ordered coordinates. |
| Task-vector warm start | Similar-task candidate priors with compatible feature encoding. | Implemented controls; scores are not transferred to the new task. |
| Other search vocabulary | Pairwise generation, beam search, successive halving, novelty, general adaptive portfolios, and future methods. | Names or proposals are not installed implementations. Qualify each separately. |
| Hyperlambda | Potential external program or tool implementation. | Researched only; not installed or qualified as a Loop Engine adapter. |

See [execution experiments](../../embodiments/README.md),
[generation implementation](../../src/loop_engine/generation/README.md), and
[Hyperlambda research](../research/HYPERLAMBDA-AND-WIDE-SEARCH-2026-09-13.md).

## Baseline dimension checklist

For every row, test the initial value, an alternate value, required/optional/
absent/unsupported/unknown states, permitted fallback transitions, forbidden
transitions, and evidence that the value reached the actual operation.
The final column identifies current evidence scope, not full qualification.

| Required dimension | Values or behavior to exercise | Current evidence scope |
|---|---|---|
| Harness implementation and process initialization | Native and selected manifests, launch versions, fresh/reused state, supported mechanics. | Broad offline protocol coverage; bounded live subsets. |
| Role profile | Exact Practitioner, Intelligence, and Solution profiles and compatible alternatives. | Contract and ontology checks; not every live profile/task combination. |
| Step profile | Atomic, compact, reference nine-step, custom/open sequences, reordered and repeated work. | Runtime checks and small staged-step experiments. |
| Model | Exact preferred model and authorized alternatives. | Configured route experiments; no universal model ranking. |
| Provider and route | Exact route, same-provider fallback, separately authorized cross-provider failover. | Gateway checks and bounded provider evidence. |
| Tools | Sets, versions, schemas, effects, discovery, selection, application, and replacements. | Engine-mediated controls; broad native-tool combinations unqualified. |
| Skills | None, reviewed skills, loading, invocation, stale/missing skill, and alternatives. | Skill contracts and a bounded live reviewed-skill treatment. |
| Context Markdown files | Relevant/full/selected material, revisions, order, absent and stale files. | Bounded live context and reference treatments. |
| Harness-native instruction Markdown files | Actual native discovery, precedence, loaded/absent/disabled controls. | Nine live Pi/OpenCode/Codex controls; not every filename or harness. |
| Prompt-injected Markdown and prompt construction | Templates, blocks, order, trust separation, content and references. | Prompt contracts and bounded live treatments. |
| Plugins | Exact handshakes, dependencies, enable/disable, compatibility, invocation, alternatives. | Component coverage; broad native plugin matrices unqualified. |
| Hooks | Trigger, order, arguments, failures, mandatory hooks, alternative implementations. | No complete live hook matrix. |
| Input contract | Ports, schemas, meaning, units, provenance, cardinality, explicit conversion. | Structural and selected binding checks; not every semantic representation. |
| Output contract | Schemas, exact output identity, multiplicity, consumption, explicit conversion. | Structural and lifecycle coverage; whole-system output completeness still limited. |
| Supervisors and independent verifiers | Exact evaluator, independence, unavailable review, disagreement, escalation. | Significant contract controls; evaluator quality still needs task-specific qualification. |
| Thinking power | Supported settings, unsupported states, authorized escalation/fallback. | Gateway checks; no broad task-quality comparison. |
| Model-call strategy | Single/multiple calls, retry, formatting repair, semantic repair, comparison. | Offline controls and bounded live recovery. |
| Model generation settings | Supported temperature and other exact model settings; application or refusal. | Small temperature treatment; not every setting or model. |
| Model output allocation | Known capacity, full capacity or explicit allocation, unknown/refused capacity. | Capacity and allocation contracts; route-specific evidence required. |
| Loop usage and orchestration | Repetition, decomposition, nesting, concurrency, state reuse, scheduling. | Runtime and deterministic placement controls; broader live coverage incomplete. |
| Run mode | Deterministic, hybrid, non-deterministic per member, compatible transitions. | Executor/authority preflight and component tests. |
| Intelligence and Runtime Memory | Four persistent layers, run-scoped state, retrieval, framing, source alternatives. | Contract and bounded retrieval controls; general transfer unproven. |
| Workspace and execution environment | Confinement, containers, dependencies, host declarations, alternatives. | Isolation and refusal controls; each external environment needs qualification. |
| Budgets, permissions, and effect policy | Independent grants, unknown/unbounded states, exhaustion, escalation, preservation. | Extensive refusal/accounting controls; some native ceilings remain post-run only. |
| Loop condition, exit condition, and output publication | Continue, repair, complete, cancel, publish and continue, consumer selection. | Runtime/lifecycle controls; publication remains separate from task acceptance. |

## Additional dimensions

The current refinement inventory also includes:

1. Reasoning and action method.
2. Objective and risk policy.
3. Task framing and uncertainty.
4. Modality and semantic representation.
5. Context allocation, ordering, and compression.
6. Information freshness and contradiction.
7. Transport, delivery, and backpressure.
8. State continuity and checkpointing.
9. Reuse, caching, and invalidation.
10. Search strategy and exploration.
11. Randomness and reproducibility.
12. Evaluation coverage and calibration.
13. Privacy and retention.
14. Dependency and environment reproducibility.
15. Cancellation and effect reconciliation.
16. Configuration binding and change control.
17. Failure classification and escalation.
18. Output serving and downstream feedback.
19. Learning transfer and promotion.
20. Schedule triggers and workload admission.
21. Observability and attribution.

Wrapper composition and native control ownership add the two distinct
choices described above. This inventory remains open to further dimensions.

## Reasonable coverage rule

1. Cover every registered level and boundary condition individually.
2. Exercise every permitted fallback trigger and reject forbidden transitions.
3. Cover valid pairs of dimensions, then higher-order combinations selected
   for risk. Prioritize harness/model/resources, context/contracts,
   nested controls/budgets/cancellation, and memory/reuse/evaluation.
4. Test stateful sequences separately: interruption, resume, retry,
   duplicate delivery, stale state, and publication followed by continued work.
5. Use exact grids for tractable subspaces and adaptive optimization for
   outcome exploration. Keep those coverage claims separate.
6. Cross these tests with the admitted task families and complexity strata,
   with repeated trials and a protected final-evaluation population.
7. Require linked applied-setting, execution, code, Canvas, accounting, and
   independent-evaluation records before claiming end-to-end success.

Combinatorial and sequence testing provide a basis for this approach;
pairwise coverage alone does not guarantee all higher-order behavior.
[NIST combinatorial testing research](https://csrc.nist.gov/Projects/automated-combinatorial-testing-for-software)

The broad coverage matrix has not yet been completed. The recent 120-Canvas
optimization control and one-trillion-address test establish much narrower
mechanics. Every missing field, unexercised transition, unqualified adapter,
and excluded task must remain visible in the campaign report.
