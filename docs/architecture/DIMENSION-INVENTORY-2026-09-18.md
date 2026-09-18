# Dimension inventory: every setting the engine can optimize, at every level

Date: 2026-09-18. Owner direction the same day: document every setting or
dimension at every level, from the two spaces down to one prompt element,
so that grids, meta-selectors, and the roadmap work from one list. This
inventory extends the
[configuration dimension requirement](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
which records the twenty-five baseline dimensions of one discrete cognitive
or act step Loop node with their initial choices and fallback priorities. It
does not repeat those rows; it places them in the levels above and below
and adds the dimensions the owner named since. Each row names its owning
boundary and its qualification state: `represented` (a typed field exists),
`grid` (a grid or campaign can vary it), `measured` (a recorded run compared
it), or `proposed`.

A dimension is a setting a run can vary; it is never an authority. Changing
a dimension grants no file, network, secret, model, spending, or external
effect permission.

## The levels

```text
Levels of configuration
├── Deployment: where the engine and its stores run
├── Solutioning space: how the Practitioner works on a task
│   ├── Graph: which nodes exist and how they connect
│   │   ├── Node: one discrete cognitive or act step Loop node (the twenty-five baseline rows)
│   │   │   ├── Step: one cognitive or act step inside the node
│   │   │   │   ├── Prompt: elements, style, and construction of one model call
│   │   │   │   └── Model call: route, settings, suggested output, contract
│   │   │   └── Harness instance: what the node's harness receives
│   │   └── Intelligence access: which layers, how retrieved, how framed
│   └── Search over the space: which configuration to try next
├── Solutions space: how published solutions run
│   ├── Solution graph: connected execution nodes with strict typed ports
│   ├── Solution node parameters: the values a parameterized node takes
│   └── Export and placement: package, container, worker
└── Economics and data: what is metered, what is learned, when a heuristic is adopted
```

## Deployment level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Deployment profile | demo, self-hosted, hosted | settings record (roadmap S-2.10) | proposed |
| Intelligence store | in-memory, packaged JSONL, DuckDB over packaged files, SQLite, server database with vectors | `catalog/` adapters and composite | represented; measured on 2026-09-18 |
| Placement of a node | host process, local container, cluster container | workspace backends, export Job manifest, placement policy (S-4.1) | represented for Docker; grid proposed |
| External intelligence access | none, project-shipped only, external with authentication | capability handshakes (`locality`, `effects`, `auth_method`) | represented |
| Secrets and credentials | reference names only | provider settings | represented |

## Solutioning space level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Space policy for member modes | deterministic, hybrid, non-deterministic per member | Canvas member-mode policy | represented |
| Persistence and supervision | budget-phase thresholds, non-progress counts, escalation ladder | supervision policy | represented; live rerun pending |
| Fast path before models | exact resolvers on or off | `allow_fast_path_resolution` | represented |
| Failed-check review | on; classification and confirmation routes | failed-check review | represented |
| Best-available resolution | required methods before a stop | resolution completion policy | represented |
| Search method over configurations | exhaustive grid, Bayesian, evolutionary, covariance adaptation, vector transfer, model-led | configuration grid and preference engines | represented; adaptive methods not qualified |
| Selector portfolio | which meta-selector chooses the next cell | configuration preferences | represented as advisory |
| Efficiency review per step | deterministic judge, specialist, model | `efficiency_check` form and contract (S-2.1 record) | contract represented; record proposed |

## Graph level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Node set | which discrete cognitive or act step Loop nodes exist | solution graph definition, Canvas | represented |
| Edges and typed ports | strict typed ports on solution edges; flexible modes in the solutioning space | `LoopContract`, contract matching modes | represented |
| Relationship kinds | Starting, Spawned by, Queried by, Retrieved by, Connected from | `LoopRelationship` | represented |
| Iterative publication | one output, or publish then continue with named outputs | solutions space record; S-2.3 runtime | explanation published; runtime proposed |
| Repetition and ensembles | repeated runs per cell, ensemble members, router and fallback | Solution role profiles | represented |

## Node level

The twenty-five baseline rows (harness implementation, role profile, step
profile, model, provider and route, tools, skills, context files,
harness-native instruction files, prompt-injected content, plugins, hooks,
input contract, output contract, supervisors and verifiers, thinking power,
model-call strategy, generation settings, output allocation, Loop usage,
run mode, intelligence and Runtime Memory, workspace, budgets and effect
policy, conditions and publication) are recorded in the requirement linked
above. Added here:

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Harness instance provisioning | the exact manifest of tools, plugins, context files, instruction files, contracts, hooks, lookups, intelligence access, external access, placement, and input | provisioning manifest (S-2.2) | proposed |
| Instance size | atomic (one step), compact, full nine-step | step profile | represented |
| Node fingerprint | exact atomic fingerprint of reason, build, or execute | stage fingerprint | represented; adoption policy proposed |
| Suggested output per step | shape, cardinality, confidence scale, abstention | `SuggestedOutput` | represented for decide_next; other steps open |

## Step level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Question form | the registered forms, including `disambiguate_value` and `efficiency_check` | question engine | represented |
| Ask strategy | direct, full solution first, blueprint, challenge, cold, masked | ask strategies | represented |
| Persona and context policy | registered personas; memory-informed, masked, cold | ask strategies, string bank | represented |
| Reuse rung | exact reuse, reuse then modify, fresh | reuse tiers direction | proposed |
| Model versus non-model | deterministic resolver, small specialist, service model | fast path, escalation, decision record (S-1.6) | partial |
| Double-check policy | none, deterministic recheck, specialist, frontier model | detection and correction nodes (S-1.10) | proposed |

## Prompt level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Prompt elements | task background, context background, atomic information, inputs and outputs, expectations, format | `core/prompt_elements` `PromptElementSelection` (S-2.7) | offline verified as a grid axis over 64 element sets; no live grid has measured it |
| Response style | full, concise, only what was asked; terse community styles as further rows of the style table | `core/prompt_elements` style table (S-2.7) | offline verified as a grid axis over three styles; no live grid has measured it |
| Block order and trust boundaries | system, constitution, role, objective, task, context, memory, evidence, constraints, examples, reasoning, output contract, verification | `StringFragment` block roles | represented |
| Size and omission policy | per-slot limits, omission rules, render digest | prompt resource bundle | represented |
| Response contract | the registered contracts and their matching modes | response contract registry, contract matching | represented |
| Examples and few-shot material | none, curated, retrieved | prompt fragments, intelligence retrieval | represented |

## Model call level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Model kind and profile | the model ontology vocabularies | `ModelProfile`, `ModelCallRequest` | represented; no non-text route |
| Determinism expectation | deterministic, seeded, stochastic | model call contract | represented |
| Allocation and capacity | source-backed capacity, selected allowance | output allocation | represented |
| Recording for learning | full record with digests, labeled by outcome | learnable call records | represented; not wired live |
| Verifier route separation | off, or every verifier call excludes the routes the producer used | `IndependentVerificationPolicy.separate_route`, `ModelGatewayConfig.excluded_routes` | offline verified; needs two authorized routes to separate |
| Typed decision route | a judgment profile with label and probability outputs behind the same call boundary | `core/typed_decision`, the `typed_decision.choice` contract | offline verified; no live provider route |

## Intelligence access level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Layers queried | any subset of the four persistent layers | intelligence search request | represented |
| Retrieval mode | lexical, hybrid, iterative, vector | Retriever; hybrid and vector proposed (S-2.11) | lexical represented |
| Blocking keys | which decisive facts must match exactly | contract matching, reuse tiers | represented for contracts |
| Framing and size | references first, large bodies after selection | intelligence loops | represented |
| Temporal validity | as of a time, current only | fact graph | represented |
| Scope and sharing | run, project, organization, public | shared memory scopes | represented |
| Versioning | current, history, rollback | catalog versioning | represented |

## Solutions space level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Solution node parameters | typed parameters with ranges | parameter resolution, grid (S-2.4) | represented per node; grid proposed |
| Strict port matching | exact typed ports | `LoopConnectionSpec` | represented |
| Export target | package, container, Kubernetes Job | solution export | represented |
| Verification of export | isolated interpreter checks | export verification | represented |

## Economics and data level

| Dimension | Values | Owning boundary | State |
|---|---|---|---|
| Metering unit | verified completions, avoided model calls, optimize hours, judgment depth | packaging tiers (S-4.3) | proposed |
| Cost records | per implementation, per operation | operation cost records | represented; wiring proposed (S-1.5) |
| Learning data placement | versioned dataset store with splits and exclusions | training data store (S-2.5) | proposed |
| Heuristic adoption | minimum run count; atomic exact fingerprints allowed | adoption policy (S-2.5) | proposed |

## Using the inventory

A grid names the dimensions it varies by the rows above and keeps the rest
fixed. A campaign report names which rows were varied, which were fixed,
and which were unknown. A meta-selector proposes values only for rows whose
state is at least `grid`. The competitor comparison is rerun against this
inventory when roadmap step S-1.9 regenerates the feature matrix, so that
planned dimensions appear as planned and not as present.
