# Discrete cognitive or act step Loop node: configuration dimensions

The owner confirmed this requirement on September 13, 2026: every discrete
cognitive or act step Loop node needs an explicit initial configuration and
ordered fallback priorities across all applicable configuration dimensions.
Harness and model choice are only two parts of that configuration. The first
25 recorded entries are a required baseline, not an exhaustive list or a
maximum. The owner explicitly confirmed that additional dimensions must be
discovered, proposed, and tested without waiting for the owner to name them.

This is an accepted design requirement, not a claim that automatic selection,
fallback, or live qualification already covers every dimension. The
machine-readable requirement is under `loop_dimensions.configuration_design`
in [architecture.yaml](../../architecture.yaml). It is a design inventory,
not an executable configuration format or permission grant.

The baseline requirement and the instruction to keep discovering dimensions
are owner-confirmed. The earlier additional choices below are assistant
proposals for review, not individually owner-approved choices. The owner
subsequently requested consideration of harness wrapper layers and native
controls as dimensions; their specific contracts and implementations still
need review.
The [review addendum](../context/CONFIGURATION-DIMENSION-DISCOVERY-ADDENDUM-2026-09-13.md)
records this clarification for the ongoing Claude Fable 5.1 review.

The [flexible cognitive and action composition direction](FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
and [configuration grid search guide](../guides/configuration-grid-search-and-optimization.md)
develop this requirement further. They support additional steps, prompts,
questions, intelligence, and action methods alongside compact alternatives,
with explicit experiments for their effects and interactions.

The [layered harness wrapper and native control proposal](LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
separates wrapper composition from control ownership. It covers one or more
wrapper layers, per-control delegation, initial choices, fallback priorities,
and coordination with the owning Loop. It is a design consideration, not an
enabled native goal mode or an implemented wrapper stack.

## Complete explanation

A discrete cognitive or act step Loop node is an independently governed
instance of the Loop runtime responsible for one clearly defined cognitive
step or action. A cognitive step might interpret information, identify a
missing requirement, compare alternatives, or evaluate a result. An action
might inspect a directory, build software, execute a test, create an artifact,
or send an authorized email.

Each discrete cognitive or act step Loop node receives the context,
instructions, skills, plugins, tools, and working files relevant to its
assignment. Essential information can be supplied directly, while additional
information can remain in centralized storage behind authorized, versioned
references. It does not automatically need the entire task history or every
available tool.

A separately initialized harness process, such as OpenCode, Pi, Codex, or a
custom implementation, can perform the assignment. When explicitly permitted,
another harness can attempt the same assignment after a failure. The
assignment's contracts, permissions, history, and remaining authority persist
across those attempts.

Discrete describes the scope of the assignment, not a restriction to one
attempt, one model call, or one output. A discrete cognitive or act step Loop
node can examine whether an observation matches its expectations, identify a
problem, repair or change its approach, and repeat until its declared
completion conditions are satisfied.

Alternatively, a discrete cognitive or act step Loop node can publish an
initial candidate output and continue working while its continuation
conditions and authority permit. It can produce additional alternatives over
time, including alternatives that are better, worse, or useful under different
circumstances. Consumers must identify exactly which output they used.
Publishing an output does not necessarily mean that the producing assignment
has finished.

For externally consequential actions, continued operation does not authorize
repeated effects. For example, generating alternative email drafts can
continue, but sending an email requires its own authorization and protection
against duplicate delivery.

That complete explanation must remain alongside the full phrase. A shorter
label alone is not an adequate replacement.

The explanation is preserved from the
[September 12 session handoff](../context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).

## Runtime classification

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

The phrase describes an executable graph vertex implemented by the canonical
`Loop`. It does not create a runtime class, role, mode, or `Node` subclass.
Tools, skills, plugins, hooks, contracts, and harness adapters are resources
or mechanics used by a Loop. They are not additional executable vertices.

The owner's phrase "starting harness" means the initial harness choice for
an assignment. It does not change whether the owning Loop is Starting,
Spawned by, Queried by, Retrieved by, or Connected from another Loop.
Practitioner style is a versioned role profile and step configuration, not
another runtime type. The same configuration discipline applies to
Intelligence and Solution responsibilities where their profiles permit it.

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

## Recorded baseline dimensions

Every row has its own initial choice and ordered fallback priorities. An
initial choice can be a set or a policy, not just one item. For example, an
assignment may need several tools together, with separate alternatives for
each required capability. An explicitly empty set is a valid initial choice
when the assignment needs no resource of that kind.

| Dimension | Initial configuration to record | Ordered fallback priorities to record |
|---|---|---|
| Harness implementation and process initialization | Custom implementation, native Practitioner, Pi, OpenCode, Codex, or another explicitly registered adapter; exact version, launch settings, process lifetime, and supported mechanics | Eligible alternative adapters or initialization recipes; trigger for each switch; state transferred, state discarded, and fresh-process requirements |
| Practitioner style or other role profile | Exact versioned role profile, supported responsibility, and required executor | Compatible profile alternatives that preserve the assignment contract; a changed role or responsibility requires a new governed definition |
| Step profile | Atomic, compact, reference nine-step, or custom ordered steps with repetition rules | Permitted changes to step order, decomposition, or repair procedure, with their own validation |
| Model | Preferred exact model identity and version where available; whether preference is configured or supported by matched evidence | Ordered eligible alternative models, with a separate reason and permission for each change |
| Provider and route | Exact provider, endpoint route, model binding, and credential reference | Same-provider alternatives and cross-provider failover priorities kept separate; cross-provider failover disabled unless explicitly authorized |
| Tools | Initial tool set, exact typed contracts, versions, effects, access scope, and required versus optional status | Alternatives per required capability and compatible tool combinations; no silent replacement by an unqualified tool |
| Skills | Initial reviewed skills, exact versions and digests, invocation conditions, and materialization policy | Ordered eligible skill alternatives or an explicit no-skill path when the contract permits it |
| Context Markdown files | Initial relevant context files, exact revisions, provenance, trust state, placement, and loading order | Alternative files or authorized retrieval sources; explicit behavior when a required file is absent, stale, or too large |
| Harness-native instruction Markdown files | Explicitly supported instruction filenames, scope, precedence, exact content, and loading mechanism | Ordered supported instruction files or initialization mechanisms; verify actual loading, not file presence |
| Prompt-injected Markdown and prompt construction | Selected Markdown bodies or references, placement in the prompt, trust separation, template version, and size policy | Permitted prompt templates, framing, materialization, or reference strategies; preserve task constraints and instruction authority |
| Plugins | Initial registered plugin set, exact handshakes, dependencies, compatibility, and effects | Ordered compatible plugins or built-in capabilities; installation and additional access require their own authority |
| Hooks | Initial lifecycle hooks, exact trigger points, order, contracts, failure policy, and effects | Compatible alternate hooks or a permitted no-hook path; mandatory approval or verification hooks cannot be bypassed |
| Input contract | Typed ports, schemas, semantic constraints, cardinality, provenance, and exact input references | Authorized alternate sources, encodings, or explicit adapter Loops; no silent weakening of required inputs |
| Output contract | Typed ports, schemas, semantic checks, cardinality, exact output identity, and consumer bindings | Compatible encodings or explicit adapter Loops; an alternative answer still has to satisfy the required contract |
| Supervisors and independent verifiers | Supervising Loop references, observation rules, evaluator contract and version, independence requirements, and escalation authority | Ordered qualified supervisors or verifiers and escalation paths; unavailable independent review cannot become self-approval |
| Thinking power | Model-supported thinking setting or explicit unsupported state, bound to the selected model route | Ordered supported thinking settings with decision evidence and remaining authority; increased thinking does not grant more effects |
| Model-call strategy | Whether model calls are needed, call purpose and sequencing, permitted retry, formatting repair, evaluator-triggered repair, and model comparison | Ordered alternate call strategies with distinct triggers; count every physical model call, including failures and harness changes |
| Model generation settings | Temperature and other settings actually supported by the exact provider and model | Ordered supported setting changes with their intended purpose; do not silently send unsupported settings |
| Model output allocation | Source-backed exact output capacity, selected allowance, allocation evidence, and unknown state when capacity is unavailable | Alternative authorized allocations within the known capacity; never invent a provider limit from a total budget or text estimate |
| Loop usage and orchestration | Assignment granularity, repetitions, nested governed work, relationship semantics, scheduling, concurrency, and permitted process reuse | Ordered changes to decomposition, repetition, scheduling, or authorized alternative attempts; each independently governed assignment remains a Loop |
| Run mode | Deterministic, hybrid, or non-deterministic, constrained by the profile, installed executor, and exact model authority | Ordered permitted mode alternatives; no mode change grants model, network, file, spending, or external-effect permission |
| Intelligence and Runtime Memory | Selected sources from the four persistent intelligence layers; separate run-scoped Runtime Memory; retrieval, selection, framing, and reference policies | Ordered authorized sources and access strategies; selection precedes large-body loading, and retrieved content remains data |
| Workspace and execution environment | Confined paths, declared sandbox, dependencies, installed runtimes, network policy, resource limits, and cancellation behavior | Ordered qualified environments or execution placements; failure never authorizes raw-host execution |
| Budgets, permissions, and effect policy | Separate time, model-call, token, spending, Loop-usage, file, network, secret, and external-effect authority; explicit unknown or unbounded states where allowed | Permitted narrower allocations or explicit escalation; fallback cannot replenish spent authority or manufacture a new grant |
| Loop condition, exit condition, and output publication | Conditions for continuing, repairing, completing, or stopping; early publication, additional candidates, and exact consumer selection | Ordered permitted recovery or escalation paths; terminal history remains terminal, and publishing a candidate is not acceptance or completion |

Instruction-file examples include `claude.md`, `CLAUDE.md`, `codex.md`, and
`AGENTS.md` where the selected harness or explicit initialization recipe
supports them. These filenames are not interchangeable. This requirement
does not assert that any harness automatically reads every listed filename.
A file's name never grants authority. Native loading and prompt injection
must be recorded and tested separately.

The four persistent intelligence layers are Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. Markdown files, skills, repositories, and vectors are source
formats, not extra intelligence layers. Runtime Memory is temporary and
scoped to one run.

## Additional dimensions to investigate

The following proposals make choices explicit that the baseline either
combines under a broad heading or does not describe separately. A refinement
separates decisions within an existing dimension. A cross-cutting choice
affects several dimensions. Neither automatically introduces another runtime
field, configuration service, registry, or top-level component.

The boundary column names existing code to inspect before designing an
extension. It does not assert that the code already implements the proposed
policy. All proposals inherit the initial-choice, ordered-fallback,
compatibility, authority, evidence, and outcome-recording requirements below.

| Proposed dimension | Relationship to the baseline and reason | Initial and fallback decisions to make explicit | Existing boundary to inspect |
|---|---|---|---|
| Harness wrapper composition | Owner-requested refinement of harness implementation. The same harness can operate inside different preparation, supervision, transport, and resource wrappers. | Choose wrapper identities, versions, depth, order, and lifecycle responsibilities. Declare ordered alternative compositions and the state and authority preserved across a change. | [Layering records](../../src/loop_engine/core/harness_layering.py) (`WrapperComposition`, `CompositionFallback`, `LayeredHarnessBinding`; declared and digested, not yet executed), [harness semantic binding](../../src/loop_engine/core/harness_semantic.py), [process boundary](../../src/loop_engine/core/harness_process.py) |
| Native control ownership | Owner-requested cross-cutting choice. The owning Loop and the native harness can expose overlapping goal, planning, iteration, retry, session, and cancellation controls. | Choose ownership separately per control, with disabled, unsupported, and unknown states. Define coordination, conflict resolution, and fallback between eligible control policies without resetting authority or duplicating effects. | [Layering records](../../src/loop_engine/core/harness_layering.py) (`NativeControlPolicy` with owning-Loop, delegated, supervised, disabled, unsupported, and unknown states), [harness capability contracts](../../src/loop_engine/core/harness_execution_contracts.py) (`native_controls` declared per adapter), [harness semantic binding](../../src/loop_engine/core/harness_semantic.py) |
| Objective and risk policy | Cross-cutting. A preferred harness depends on whether the task values correctness, latency, cost, reliability, or the consequences of an error. | Declare metric direction, hard constraints, tradeoffs, and acceptable uncertainty. Permit fallback tradeoffs only within the task's required acceptance standard. | [Harness selection](../../src/loop_engine/core/harness_selection.py), [portfolio policy](../../src/loop_engine/loop/reactive_contracts.py) |
| Task framing and uncertainty | Cross-cutting. More computation does not repair a wrong interpretation of the assignment. | Choose what to clarify, which assumptions must remain explicit, and when to gather evidence, ask the user, abstain, or request a revised contract. | [Task intake](../../src/loop_engine/templates/intake.py), [task frontier](../../src/loop_engine/core/task_frontier.py) |
| Reasoning and action method | Refinement of Practitioner style, step profile, and tools. A model choice or thinking-power setting does not specify the method. | Choose an applicable method, such as rule-based deduction, causal analysis, simulation, formal constraint solving, or direct tool execution. Define alternatives after a failed assumption or check, including a dry run when needed. Preserve the task and effect contracts. | [Method selection and repair](../../src/loop_engine/core/adaptive_practitioner_planning.py) |
| Modality and semantic representation | Refinement of input and output contracts. The same content can lose meaning when represented differently. | Declare text, image, audio, structured data, units, locale, precision, and supported conversions. Refuse unsupported conversion or use an authorized adapter without silently losing required information. | [Loop contracts](../../src/loop_engine/loop/loop_contract.py), [information access](../../src/loop_engine/core/information_access.py) |
| Context allocation, ordering, and compression | Refinement of context and prompt construction. File choice alone does not determine what information reaches the model. | Allocate space by source and purpose; record ordering, deduplication, truncation, summaries, and omissions. Fallback may retrieve exact material or change framing when compression loses required evidence. | [Context budget](../../src/loop_engine/core/context_budget.py), [context manifest](../../src/loop_engine/core/context_pack_manifest.py) |
| Information freshness and contradiction | Refinement of intelligence access. A valid digest can identify stale or conflicting information. | Declare source age limits, independent corroboration, contradiction handling, and revalidation triggers. Choose refresh, alternate sources, escalation, or refusal with uncertainty preserved. | [Information access](../../src/loop_engine/core/information_access.py), [context artifacts](../../src/loop_engine/core/context_artifacts.py) |
| Transport, delivery, and backpressure | Refinement of information passing and orchestration. A typed output can still be lost, duplicated, delayed, or consumed out of order. | Choose inline values or references, streaming or batch delivery, ordering, acknowledgments, queue limits, and slow-consumer behavior. Define retry and reconciliation without replaying committed effects. | [Information access](../../src/loop_engine/core/information_access.py), [reactive contracts](../../src/loop_engine/loop/reactive_contracts.py) |
| State continuity and checkpointing | Refinement of process initialization and Loop usage. A replacement process needs a defined view of prior work. | Choose ephemeral or durable state, checkpoint boundaries, exact resume identity, state transfer, and restart rules. Fall back to a compatible checkpoint or reconciliation, never an invented fresh budget. | [Spawned task checkpoints](../../src/loop_engine/loop/spawned_task_checkpoint.py), [reactive contracts](../../src/loop_engine/loop/reactive_contracts.py) |
| Reuse, caching, and invalidation | Refinement of intelligence and Runtime Memory. An old result is useful only within its validated scope. | Choose exact reuse keys, admissible similarity, freshness, scope, and invalidation. Distinguish reusing model input computation, an answer, or an executable Solution. Fall back to fresh computation when validity is uncertain. | [Practitioner reuse](../../src/loop_engine/core/adaptive_practitioner_reuse.py), [capability resolution](../../src/loop_engine/core/reusable_capability_resolution.py) |
| Search strategy and exploration | Cross-cutting. Always using the current preferred configuration cannot establish whether an alternative is better. | Choose search breadth, depth, candidate diversity, sequential or parallel trials, and the allocation between exploration and an established choice. Stop or narrow exploration under the existing authority. | [Task frontier](../../src/loop_engine/core/task_frontier.py), [exploration policy](../../src/loop_engine/loop/reactive_contracts.py) |
| Randomness and reproducibility | Refinement of generation settings and experiments. Variation can be intentional or an uncontrolled confounder. | Record supported seeds, sampling settings, versions, repeated-trial policy, and known nondeterminism. Use independent repetitions or a qualified deterministic route when available; do not promise determinism from a seed alone. | [Prompt experiments](../../src/loop_engine/core/prompt_experiment.py), [state-policy evidence](../../src/loop_engine/core/state_policy_evidence.py) |
| Evaluation coverage and calibration | Refinement of supervision. Evaluator choice alone does not define coverage, false acceptance, or disagreement handling. | Declare exact subject binding, semantic and structural checks, holdout isolation, tolerances, uncertainty calibration, and disagreement policy. Fall back to independent qualified checks or an inconclusive result, not a weaker acceptance threshold. | [Independent verification](../../src/loop_engine/core/independent_verification.py), [response evaluation](../../src/loop_engine/core/harness_response_evaluation.py) |
| Privacy and retention | Cross-cutting. Permission to read data does not automatically permit sending, retaining, or reusing it. | Declare permitted recipients, data minimization, redaction, isolation, location constraints, and retention. Use an authorized local or reduced-disclosure path when needed; never change recipients silently. | [Context artifacts](../../src/loop_engine/core/context_artifacts.py), [effect approval](../../src/loop_engine/loop/effect_approval.py) |
| Dependency and environment reproducibility | Refinement of plugins, tools, and workspaces. The same named tool can behave differently with different dependencies or hardware. | Pin executable, dependency, license, container, hardware, resource, and initialization facts. Define qualified alternative environments and version rollback with fresh compatibility checks. | [Code Intelligence assets](../../src/loop_engine/core/code_intelligence_assets.py), [workspace contracts](../../src/loop_engine/core/workspace_contracts.py) |
| Cancellation and effect reconciliation | Refinement of budgets and effects. Timing out a request is not proof that its work or external effect stopped. | Choose cancellation propagation, deadlines, interruptibility, descendant cleanup, checkpoint-on-stop, and effect-status queries. Fall back to reconciliation or refusal when the outcome is unknown. | [Delegation runtime](../../src/loop_engine/loop/delegation_runtime.py), [effect approval](../../src/loop_engine/loop/effect_approval.py) |
| Configuration binding and change control | Cross-cutting. A good policy can be applied at the wrong time or overridden by another layer. | Declare resolution precedence, inheritance, binding before initialization or between attempts, allowed mid-run changes, and complete old/new configuration identities. Apply compatible changes together and preserve explicit owner choices. | [Parameter resolution](../../src/loop_engine/core/parameter_resolution.py), [Loop definitions](../../src/loop_engine/loop/loop_definition.py) |
| Failure classification and escalation | Cross-cutting. Different failures require different responses, even with the same fallback candidates. | Distinguish temporary provider failure, incompatibility, wrong answers, bad inputs, exhausted authority, and uncertain effects. Select the appropriate dimension to change or escalate to a qualified supervisor or the user. | [Harness fallback](../../src/loop_engine/core/harness_fallback.py), [supervision policy](../../src/loop_engine/loop/supervision_policy.py) |
| Output serving and downstream feedback | Refinement of output publication. The producer's preferred candidate may not be the one a consumer used. | Declare consumer selection, freshness, revision semantics, retention, acknowledgment, and feedback binding to an exact output. Fall back to another compatible evaluated candidate or report unavailability without replacing a consumed identity. | [Reactive contracts](../../src/loop_engine/loop/reactive_contracts.py), [reactive outputs](../../src/loop_engine/loop/reactive_outputs.py) |
| Learning transfer and promotion | Refinement of intelligence and self-improvement. Task-local repair, reusable knowledge, and policy updates have different approval requirements. | Declare what may transfer between tasks, its validity domain, evidence independence, drift monitoring, and rollback. Keep generated changes candidate-only; fall back to a reviewed prior version or fresh work. | [Recovery learning](../../src/loop_engine/core/recovery_learning.py), [capability lifecycle](../../src/loop_engine/core/reusable_capability_flywheel.py) |
| Schedule triggers and workload admission | Refinement of Loop usage. A valid assignment still needs a policy for when and whether it starts. | Declare trigger types, queue discipline, concurrency, fairness, capacity, work coalescing, and duplicate suppression. Choose authorized deferral, serialization, or refusal without silently losing required work. | [Scheduling](../../src/loop_engine/scheduling.py), [reactive contracts](../../src/loop_engine/loop/reactive_contracts.py) |
| Observability and attribution | Cross-cutting. Results are not comparable when the applied configuration or failed attempts are missing. | Declare trace detail, occurrence identity, physical usage accounting, redaction, audit sampling, and attribution of configuration changes. Refuse success claims when required records are missing; optional telemetry loss cannot manufacture zero cost or successful work. | [Run History](../../src/loop_engine/core/run_history.py), [prompt experiments](../../src/loop_engine/core/prompt_experiment.py) |

These are proposed separations, not newly implemented capabilities or a set
of entirely independent variables. Review may combine overlapping entries or
split one further. The number of entries is not a progress metric.

## Ongoing dimension discovery

The owner subsequently requested additional model and harness preference
engines, capability-aware configuration setters, and meta-selectors or agents
that help choose grid parameters. Version 1.2.0 of the design inventory
includes these further refinements. The
[configuration preference guide](../guides/configuration-preferences-and-meta-selection.md)
maps their owning contracts and separates current in-memory and advisory
interfaces from proposed native setters and autonomous portfolios.

| Further refinement | Initial and fallback decisions |
|---|---|
| Model preference engine | Existing route ordering, reviewed evidence ranking, or a qualified custom proposal method. |
| Harness preference engine | Eligible configured order, matched trial ranking, or another qualified ordering method. |
| Meta-selector and engine priorities | Initial selector, alternate selectors, abstention, and permitted failure triggers. |
| Selector portfolio coordination | Serial proposals, permitted parallel proposals, proposal-combination policy, or a single engine. |
| Objective tradeoff and feasibility | Metric priorities and constrained tradeoffs without weakening acceptance. |
| Selector uncertainty and abstention | Confidence policy, additional information, another proposal, or stop. |
| Selector feedback partition and scope | Exact-task feedback, admissible cross-task feedback, or no reusable evidence. |
| Task feature encoding and distance | Exact feature representation, comparison method, and compatible alternatives. |
| Configuration setter backend | In-memory field binding, qualified native file or command interface, or remote control adapter. |
| Configuration change phase | Before initialization, per request, between steps, or explicit restart. |
| Atomic configuration change and rollback | Staged replacement, exact commit protocol, reconciliation, or refusal. |
| Support discovery and freshness | Host declaration, qualified handshake, sourced documentation, or permitted probe. |
| Effective configuration confirmation | Echoed effective settings, native load evidence, invocation observation, or unknown. |
| Deployment and serving realization | Qualified local or cloud deployment, serving implementation, hardware, and model realization. |
| Concurrency and service admission | Available capacity, queue policy, alternate deployment, or deferred work. |
| Search to execution binding | Exact proposal binding, revalidation, authorized dispatch, or recorded exclusion. |
| Selector drift and independent requalification | Current reviewed version, qualified replacement, or loss of eligibility. |

These entries inherit every choice and fallback requirement. They do not
turn the inventory into a fully implemented grid or an exhaustive design.

For each real assignment, ask what else could change the outcome while the
named harness and model remain fixed. Inspect the entire governed lifecycle:
intake, configuration resolution, preparation, execution, observation,
handoff, recovery, completion, and later reuse. Include cognitive assignments,
actions, and their interactions.

Record a proposed dimension when it names a distinct controllable decision or
an important interaction that the current configuration cannot express. State
the failure it could prevent, why an existing field is insufficient, the
owning boundary, initial and fallback choices, compatibility and authority
constraints, and an experiment that could support or reject its usefulness.
Classify it as already represented, a refinement, a missing choice, an
interaction, or an unresolved question. Keep rejected and merged proposals
visible rather than accumulating duplicate settings.

Some facts, such as provider availability, source age, task difficulty, or
machine load, are observations rather than controllable settings. Record the
observation separately from the policy that responds to it. A derived metric,
category, and permission grant are also not interchangeable dimensions.

Test interactions deliberately. For example, context compression can change
which model succeeds; process reuse can change latency and isolation; output
streaming can change cancellation and duplicate-delivery risk. Passing tests
for each setting in isolation does not establish that their combination is
safe or useful. Freeze a bounded comparison per experiment while keeping the
product's design inventory open to new dimensions.

An open-ended design inventory does not make runtime contracts permissive.
Unknown executable fields and unqualified combinations still refuse. Adding
a proposal here neither installs an implementation nor authorizes automatic
self-modification. Extend the existing typed boundary only after review and
verification, without a parallel runtime or store.

## Required choice and fallback record

For each dimension, a resolved configuration must distinguish:

1. The initial value, exact versioned identity or immutable content reference,
   and the source of the choice.
2. Required, optional, explicitly absent, unsupported, and unknown states.
   Missing configuration must not masquerade as a deliberate empty set.
3. Ordered fallback priorities, including an explicit no-fallback decision
   when there is no permitted alternative.
4. Eligibility and compatibility with every other selected dimension, the
   assignment's typed contracts, and the installed executor.
5. The observation that permits each transition, the expected effect of the
   change, and which settings must remain fixed.
6. The exact authority and remaining resources required before transition,
   including approval for changed external effects.
7. The comparison objective, independent evaluation method, evidence
   references, uncertainty, and the reason for selection or refusal.
8. The attempted value, observed outcome, failure disposition, physical model
   calls, known token usage, elapsed time, and cost state in Run History.

These are requirements for typed contracts at existing owning boundaries.
They are not permission to interpret this document as a configuration object,
create a parallel registry, or infer executable behavior from prose.

Initial priorities and fallback priorities can differ. A fast initial choice
may be unsuitable after a particular semantic failure. A fallback can change
one dimension or an explicitly compatible combination. A failed instruction
load does not necessarily require a different model. A provider outage does
not necessarily require different task inputs. Record the actual change.

## Selection, evaluation, and safe transitions

The intended decision sequence is:

```text
Typed assignment, contracts, and authority
  -> effect-free discovery
  -> eligibility and compatibility checks
  -> comparison using applicable reviewed evidence
  -> initial configuration selection
  -> authorized materialization and initialization
  -> execution owned by the canonical Loop
  -> structural checks and independent semantic evaluation
  -> continue, publish, complete, refuse, or select a permitted fallback
  -> preserve the attempt and decision in Run History
```

"Preferred" can mean an owner-configured choice. "Most optimal" requires a
declared objective and evidence for the exact assignment population and
configuration. No harness or model is universally best. When evidence is
missing or incomparable, retain an explicit configured preference or return
an unknown selection result. Do not invent a learned ranking.

Keep same-configuration retry, changed settings, harness fallback,
same-provider model fallback, cross-provider failover, formatting repair,
evaluator-triggered repair, and task replanning distinct. An unavailable
evaluator is not a passing evaluation. A response that satisfies its schema
can still be wrong.

Switching configuration must preserve the task identity, exact inputs and
output commitments, authority already consumed, prior failures, and relevant
Run History. Reusing a process must not leak another assignment's resources
or permission state. Reinitialization must not reset a deadline or budget.
An uncertain external-effect outcome requires reconciliation before retry;
a fallback must not send a second email or repeat another committed effect.

Every input or output contract change needs explicit compatibility checks.
Do not lower the acceptance standard because a harness cannot satisfy it.
A supervisor replacement must preserve independent review. A model-generated
configuration or a successful trial remains candidate-only until the
existing independent process approves it for reuse.

## Testing and implementation status

Qualification must measure both individual dimensions and their interactions.
Freeze real assignments, input identities, evaluator versions, allowed
effects, and the candidate configurations before a comparison. Record the
selection rule and the exact attempted and excluded denominators. Test the
initial choice, every permitted fallback trigger, refusal cases, and the
transition itself. A record saying that settings changed is insufficient;
verify that the selected settings reached the actual execution.

Separate harness-native resources from engine-mediated resources. Test absent
resources and disabled loaders as controls. Include incompatible combinations,
stale references, prompt injection, missing usage, exhausted authority,
unavailable supervisors, and effects with uncertain outcomes. Preserve all
failed and excluded attempts alongside successes.

The
[September 12 configuration report](../verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md)
records 70 real Tactical model calls, a forty-cell repair matrix, and nine
native Markdown loading controls. Those experiments cover a bounded subset
of this design. They do not qualify automatic selection or every fallback
dimension.

The current working tree also contains typed harness selection from matched,
reviewed trial evidence and a separate deterministic response-evaluation
boundary. These are a narrower implementation than this design requirement.
Do not claim that they jointly optimize models, resources, supervisors,
contracts, thinking power, or Loop usage. General cross-task selection and
the complete live configuration-and-fallback matrix remain unproven.

Future handoffs, including the requested Claude Fable 5.1 review, must preserve
the required baseline, the open-ended discovery requirement, and the complete
behavioral explanation. A review must identify missing dimensions and useful
refinements as well as classify what is implemented, locally tested, qualified
with a real provider, unsupported, or still proposed. Neither this list nor
the reviewer's additions are an exhaustive final configuration space.
