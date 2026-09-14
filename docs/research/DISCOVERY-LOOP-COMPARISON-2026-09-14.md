# Discovery Loop and Loop Engine

Discovery Loop and Loop Engine share a central idea: a system can propose
experiments, execute them, evaluate results, and use those results to choose
later work. This is a meaningful overlap. It does not establish that the
implementations are equivalent or that either is better.

This review uses public sources checked on September 14, 2026. Discovery
Loop's undisclosed capabilities remain unknown. Loop Engine's repository
contracts and experiments are not substitutes for comparable production
measurements.

## Confirmed direction and reported financing

Discovery Loop describes a plan to automate experimental cycles, run thousands
of experiments in parallel, begin with machine-learning research and
engineering, and use the results to improve its own technology before
expanding to other domains. These are company statements, not independently
reproduced benchmark results. [Company site](https://www.discoveryloop.com/).

Jeff Dean's launch statement names Sanjay Ghemawat, Quoc Le, and Oriol Vinyals
as cofounders. It describes a public benefit corporation and work on
infrastructure, models, and research systems. Radical Ventures and Khosla
Ventures were selected to lead the initial financing. This supports a
system-level research direction, but not an assumption that Discovery Loop
only wraps third-party models. [Founder statement, published by Radical Ventures](https://radical.vc/articles/radical-reads-jeff-dean-on-launching-discovery-loop/).

The screenshot matches Ben Bergman's September 11 report: Discovery Loop was
seeking roughly a $50 billion valuation after earlier discussions around
$1 billion of financing at roughly $10 billion. The article says terms could
change and that the higher valuation was not guaranteed. This is a reported
fundraising target, not a confirmed closed round or a technical result.
[Business Insider report](https://www.businessinsider.com/jeff-deans-startup-discovery-loop-is-eyeing-a-valuation-2026-9).

## Loop Engine classification for the comparison

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

This is Loop Engine's architecture, not an inferred diagram of Discovery
Loop. The [research and integration guide](RECURRENT-MODELS-AND-SYSTEM-IMPROVEMENT-2026-09-14.md)
provides the complete role-profile branches and intelligence-layer mapping.

| Question | Discovery Loop public evidence | Loop Engine evidence and qualification needed |
|---|---|---|
| Does the system automate experimental iteration? | This is its stated purpose. | Canonical execution, task experiments, verification, and history exist. Autonomous experiment selection connected to qualified outcomes remains incomplete. |
| Is improving the research system itself in scope? | The company explicitly plans to be its own first customer. | Self-improvement is a Practitioner task. Candidate staging and independent promotion are separate; general cross-task gains are not established. |
| Can each assignment use a different harness or endpoint? | The reviewed sources do not specify that interface. | Typed harness and provider adapters exist. Installed support and live qualification vary. A registered manifest is not a successful integration test. |
| Are configurations and graph structures searchable? | Detailed parameter spaces and selection algorithms were not disclosed in the reviewed sources. | Versioned configuration spaces and proposal mechanisms exist. The large declared grid has not been exhaustively executed or optimized. |
| How is intelligence reused? | A comparable public memory or lifecycle specification was not found in the reviewed sources. | Four persistent intelligence layers and separate Runtime Memory are explicit. Experiments still need to measure retrieval quality, later reuse, and negative transfer. |
| Who verifies improvements? | Evaluator isolation, promotion, and rollback details remain unknown from these sources. | Independent qualification and effect authority are explicit contracts. Broad task-evaluator qualification and complete live-cycle evidence remain open. |
| Does scale translate into useful discoveries? | Parallel scale is a company objective; the reviewed pages do not provide a reproducible task-level result set. | The current catalog has 1,771 tasks and 1,606 frozen source-ready inputs. This is preparation, not a solved population or demonstrated distributed throughput. |

The company's stated direction in this table comes from its
[approach description](https://www.discoveryloop.com/) and the
[founder's launch statement](https://radical.vc/articles/radical-reads-jeff-dean-on-launching-discovery-loop/).
The unknowns mean that public information is insufficient, not that Discovery
Loop lacks those mechanisms. Unrelated papers that use the phrase
"discovery loop" are not evidence about this company.

## Where differentiation could be tested

Loop Engine's candidate distinction is an inspectable, composable runtime
across heterogeneous reasoning and action assignments, with portable harness
bindings and explicit intelligence lifecycles. That is a product hypothesis.
More dimensions also introduce search cost, weak defaults, and additional
failure paths. The recent unproductive live continuations demonstrate why
flexibility alone is insufficient.

Test this hypothesis against accessible baselines: a fixed direct-model
procedure, a fixed installed harness, the same procedure with reviewed
intelligence, and a governed adaptive selector. Keep the model, tasks,
evaluation rules, and resource accounting comparable. Report verified task
success, transfer to unseen tasks, human intervention, recovery, latency,
cost completeness, and repeated effects. Include the cost of exploration.

A direct Discovery Loop comparison requires access to its implementation or
a reproducible published result with the same controls. Until then, the
defensible conclusion is that the research directions overlap and Loop
Engine has explicit design choices worth testing. Neither a valuation nor
our architecture diagram establishes superiority.
