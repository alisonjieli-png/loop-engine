# Flexible cognitive steps and actions

Loop Engine should support many ways of thinking, acting, and learning from
verified outcomes. Its design should accommodate additional cognitive steps,
action methods, prompts, questions, intelligence, tools, and configuration
dimensions as the work requires them.

The owner requested this direction on September 13, 2026. It is an accepted
design requirement with partially implemented mechanisms. The term
"artificial general intelligence" names a research ambition: investigate
general-purpose composition across varied tasks. It is not a new runtime,
role, mode, permission level, or claim that Loop Engine has achieved general
intelligence.

Compact workflows remain useful. So do expanded workflows with more
deliberation, research, tests, alternative solutions, and repeated improvement.
Minimizing step count, prompt count, context, or model calls is not the
universal optimization objective. The objective belongs to the assignment.
Growth and simplification are both choices to evaluate.

Read the [open-ended dimension inventory](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
and [work-approach instrumentation](WORK-APPROACH-INSTRUMENTATION.md) with this
document. The [grid search guide](../guides/configuration-grid-search-and-optimization.md)
turns the direction into an experiment protocol using existing boundaries.

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

## One runtime, many compositions

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

Every executable graph vertex remains the canonical `Loop`. Each displayed
Loop needs its own exact profile, mode, typed ports, loop and exit conditions,
relationships, budget, and permissions. A graph can contain different modes;
the graph itself does not acquire one mode.

The role profiles remain the existing families, with versioned extensions
where their contracts permit them:

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

An independently governed cognitive assignment or action can use a custom
implementation or a separately initialized registered harness. Different
assignments may use different profiles, prompts, resources, models, and
fallback priorities. An implementation primitive remains inside its owning
Loop unless it needs a separate goal, contract, authority, scheduling,
verification, or Run History identity.

## Cognitive work to extend

The following is an open-ended map of work to represent and test. These are
capability categories, not additional runtime classes or claims of installed
capabilities.

```text
Cognitive work
├── Interpret and represent
│   ├── understand a request and its context
│   ├── interpret supported text, images, audio, or structured data
│   └── identify assumptions, entities, relations, units, and ambiguity
├── Ask and acquire
│   ├── identify a missing fact or material question
│   ├── select sources and compare conflicting evidence
│   └── retrieve, inspect, or request relevant information
├── Reason and model
│   ├── apply rules and constraints
│   ├── compare analogies, explanations, and hypotheses
│   └── examine causal, counterfactual, mathematical, or simulated outcomes
├── Plan and choose
│   ├── decompose a task and identify dependencies
│   ├── compare methods, resources, and configurations
│   └── choose a justified next action or a request for clarification
├── Check and revise
│   ├── compare observations with expectations
│   ├── test assumptions and search for counterexamples
│   └── revise a plan, representation, or method after a mismatch
└── Generalize and prepare reuse
    ├── describe applicability and failure conditions
    ├── propose a reusable procedure or Solution
    └── stage a lesson or configuration for independent review
```

A cognitive method is separate from thinking power. Causal analysis, direct
rule application, formal constraint solving, simulation, analogy, and
candidate comparison can call for different inputs, tools, and checks even
when the model and thinking setting are unchanged.

The system should support adding a useful cognitive operation without
forcing it into a fixed nine-step script. A selected profile can impose its
own finite structure. That profile's structure is not the limit of what the
product may represent.

## Action work to extend

Actions obtain observations or change state. Their contracts must describe
which of those effects occur. The action repertoire is also open-ended:

```text
Action work
├── Observe
│   ├── inspect a permitted file, directory, service, or tool state
│   └── measure an outcome or collect a bounded observation
├── Compute and test
│   ├── run a calculation, solver, simulation, or transformation
│   └── build software and execute qualified checks
├── Create and modify
│   ├── draft an artifact or propose a change
│   └── apply an approved change inside a confined workspace
├── Communicate and coordinate
│   ├── pass exact typed inputs, outputs, references, and status
│   └── send an authorized message or request independent review
├── Operate an external system
│   ├── use a qualified browser, service, or device adapter
│   └── bind each consequential effect to its exact approval
└── Recover and reconcile
    ├── inspect whether an attempted effect committed
    └── resume, repair, compensate, or stop under the applicable contract
```

These examples do not assert that browser, service, device, or physical-world
adapters are all installed. A new action needs a typed adapter and a qualified
execution boundary. The design should make that extension possible without
a second runtime.

A cognitive proposal and its material action may be separate governed
assignments. Choosing an email draft is different from sending it. Generating
additional drafts can continue; sending again needs exact authority and
duplicate protection. The same distinction applies to file changes, purchases,
deployments, database writes, and device operations.

## More steps and different step structures

Harness implementation can also vary through one or more wrapper layers and
through selected native goal, planning, session, and continuation controls.
Read [layered harness wrappers and native control](LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md).
Wrapper depth, wrapper order, and control ownership are separate choices.
They do not impose another runtime or a fixed number of steps.

Support variable step count, granularity, order, repetition, and branching.
The existing atomic, compact, reference, and custom profiles are reusable
choices, not an exhaustive progression or a universal maximum.

| Change to investigate | What it makes possible | What must remain explicit |
|---|---|---|
| Insert a step | Add clarification, retrieval, simulation, inspection, reflection, or a verifier where it is useful. | Purpose, dependencies, exact profile, inputs, outputs, and the evidence expected from the new work. |
| Split a step | Give two different questions or actions independent configuration and evaluation. | Distinct contracts, authority allocation, context transfer, and output identities. |
| Reorder steps | Move a useful prerequisite or check earlier. | Dependency compatibility and which observations are available at each point. |
| Repeat a step | Improve a candidate, resolve uncertainty, or retry an authorized operation. | Continuation conditions, failure classification, remaining authority, and effect reconciliation. |
| Branch and compare | Explore alternative explanations, methods, harnesses, or solutions. | Eligibility, independent candidate identity, evaluation policy, and comparison population. |
| Merge or specialize | Use a reviewed compact procedure when the combined behavior is justified. | Preserved semantics, required checks, scope of validity, and an available permitted fallback. |
| Continue after publication | Produce additional evaluated alternatives while authorized consumers can use an earlier result. | Publication versus completion, exact consumer bindings, and terminal activation boundaries. |

The historical identifier `reference_nine_step` currently names a ten-step
template. Preserve the identifier and its existing compatibility behavior.
It is not a numerical limit for a custom profile. Read
[the Loop object guide](../components/loop-object/README.md).

A diagram is not an executable graph. Each proposed topology must compile to
existing typed definitions and relationships before execution. A dynamically
selected extra step needs a supported executor, exact resource bindings, and
remaining authority. Repetition never resets a consumed budget.

## More prompts and questions

Support prompt portfolios and task-specific question generation, not one
universal instruction file. Useful additions include prompts for interpreting
a requirement, generating hypotheses, choosing a method, retrieving evidence,
checking an action's prerequisites, examining a counterexample, repairing a
failure, and preparing an independent review.

A prompt portfolio should record the purpose and exact identity of each
component. It can vary instructions, examples, counterexamples, perspectives,
question forms, evidence order, output representations, and the point in the
work at which a prompt is used. One assignment may use several prompts or
model calls. A deterministic assignment may use none.

Use the existing `PromptResourceBundle`, typed prompt slots, context
manifests, model-prompt envelopes, and response contracts as starting points.
Prompt generation can propose new material. It does not authorize the
material to override a task contract, change permissions, register tools, or
promote itself.

Keep harness-native Markdown loading, explicit prompt injection, selected
Context Intelligence, skills, plugins, hooks, and ordinary working files
distinct. Test actual loading and use, not only file existence. Preserve
versioned references and record the material that was considered, selected,
omitted, loaded, and applied.

More prompts need not mean pasting all available guidance into every call.
The design supports both broader context and focused context, including
retained references and additional retrieval when needed. Compare those
choices on the actual task rather than treating compression or maximum
context as automatically better.

Record decisions, safe summaries, configuration identities, and observable
outcomes. Do not collect private reasoning traces as a substitute for
operational evidence.

## More intelligence within the existing layers

Expand the available knowledge, executable capabilities, prior outcomes, and
human guidance through the four persistent layers:

```text
Persistent intelligence
├── Context Intelligence
│   └── methods, questions, examples, counterexamples, domain facts, and warnings
├── Code Intelligence
│   └── qualified tools, packages, procedures, adapters, and executable capabilities
├── Runtime History and Solution Intelligence
│   └── prior decisions, failures, repairs, comparisons, and reusable Solutions
└── User Feedback Intelligence
    └── scoped corrections, preferences, constraints, approvals, and review findings

Temporary run state
└── Runtime Memory
    └── current observations, assumptions, selected references, and working state
```

A richer intelligence strategy can seek additional sources, improve coverage,
compare contradictory sources, load deeper material, invoke useful code,
inspect a relevant failure, or request human guidance. These are different
operations with different evaluation questions.

Add domain coverage and useful granularity without inventing a new layer
for Markdown, skills, repositories, vectors, prompts, or transcripts. Search
returns small typed references; selected material is loaded after scope and
permission checks. Facts, executable capabilities, histories, and user
instructions retain their different trust and lifecycle rules.

Generated intelligence remains candidate-only until independent qualification
and approval. After promotion, test whether later work actually retrieves and
uses it. More stored records do not by themselves establish learning, and a
successful retrieval does not prove that the material helped.

## Optimize configurations and compositions

A Practitioner task can investigate how additional steps, prompts,
intelligence, and resources change outcomes. Compare complete configurations
and individual changes, including the initial selections and the fallback
policy for each applicable dimension.

The [grid search guide](../guides/configuration-grid-search-and-optimization.md)
describes exact enumeration, conditional eligibility, larger search spaces,
matched evaluation, interaction tests, and independent review. It reuses the
existing generation, execution, Run History, and candidate-lifecycle
boundaries.

A useful result can be a set of configurations for different circumstances.
For example, one may favor verified quality, another response time, and
another low resource use. State the tradeoffs and uncertainty. Do not force
every task onto one winning harness, one prompt, or the shortest workflow.

## Flexibility requirements for future development

1. Preserve supported alternatives when adding another way of working. A
   refactor must not silently remove a mode, profile, prompt path, intelligence
   source, or configuration option.
2. Keep dimension and capability inventories open-ended. Propose new choices
   and interactions when the current representation misses a real decision.
3. Support expansion as well as simplification. Adding checks, research, or
   deliberation can be a legitimate optimization.
4. Keep configuration choices separate from runtime types and authority.
   Unknown executable fields still require a typed extension and validation.
5. Preserve initial choices and ordered fallback priorities. A fallback may
   change several compatible dimensions, but the applied change must be
   recorded and checked.
6. Keep reusable resources versioned, discoverable, and independently
   qualified. Do not create another registry or intelligence store.
7. Measure task outcomes and transfer, not the number of steps, prompts,
   dimensions, or records created.
8. Keep experimental candidates, executed work, evaluated results, accepted
   results, and promoted intelligence distinct.

## Existing mechanisms and remaining qualification

| Area | Existing boundary | Evidence limit |
|---|---|---|
| Custom profiles and governed work | `LoopDefinition`, `LoopProfileSpec`, `LoopConfig`, and delegation contracts | A profile and installed executor must support the selected composition; not every topology or action adapter is qualified. |
| Variation-space enumeration | `VariationDimension`, `ConditionalRule`, `GenerationCampaign`, and `generate_candidates` | Exact enumeration creates proposed configurations. It does not automatically execute, optimize, or promote them. |
| Prompt and context composition | Prompt resources, context manifests, and model-prompt envelopes | Runtime integration and resource loading vary by caller and harness. |
| Intelligence growth | Existing layer catalogs, Context seeding, Code admission, and capability lifecycle | Seeding and candidate presence do not prove useful cross-task learning. |
| Live configuration comparisons | The development configuration study and resource matrix | The saved 70-call study covers bounded component configurations, not general intelligence or the complete design. |
| Harness selection and semantic recovery | Optional reviewed-evidence policy and registered response evaluator | Current scope is narrower than joint optimization across all dimensions. |

This document promotes architectural flexibility. It does not declare a
completed artificial general intelligence system, an automatically applied
universal optimizer, or authority to start a new model campaign.
