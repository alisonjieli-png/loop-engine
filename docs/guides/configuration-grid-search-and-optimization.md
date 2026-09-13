# Configuration grid search and optimization

Use configuration search to test different ways of performing a cognitive
assignment, an action, or a complete task. Search can add steps, prompts,
questions, intelligence, tools, verification, and alternative attempts.
It can also compare a simpler procedure when that is useful.

This guide covers experiment requirements and the existing proposal
interfaces. The [generation component](../../src/loop_engine/generation/README.md)
supports lazy indexed spaces, grid and seeded exploration, task-vector
candidate priors, and optional Bayesian, evolutionary, and covariance
adaptation through Optuna. Proposal computation does not dispatch tasks or
establish their quality. The [flexible composition direction](../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
and [open-ended dimension inventory](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
define what to keep extensible. Existing
[work-approach instrumentation](../architecture/WORK-APPROACH-INSTRUMENTATION.md)
remains the related architecture checkpoint, not a parallel experiment system.

The owner explicitly rejected a fixed 100-task sample. The entire task
catalog remains in scope for admission, and search spaces may contain
billions of possible configurations. Adaptive methods choose which trials
to propose next; exact enumeration remains available for declared finite
grids. Neither method may report unexecuted configurations as tested.
Use the [run-path and dimension coverage map](../verification/RUN-PATH-AND-DIMENSION-COVERAGE-2026-09-13.md)
to track individual settings, fallback transitions, interactions, and
stateful sequences separately from optimization outcomes.

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

## Existing runtime and profile boundaries

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

A search campaign describes candidate configurations. Its records and axes
are passive. Governed generation, selection, execution, evaluation, and review
belong to Loops using the existing profile families:

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

Use the existing generation contracts and the registered execution
boundaries. Do not introduce a grid-search runtime class, another Run History,
or a separate promotion store.

## Define what is being optimized

Choose the unit of comparison before generating candidates:

| Unit | What may vary | What the result can establish |
|---|---|---|
| One cognitive assignment | Reasoning method, context, question portfolio, model, harness, prompt sequence, or thinking setting. | Suitability for that assignment and the sampled task conditions. |
| One action assignment | Tool or execution method, prerequisites, environment, input representation, verification, or recovery path. | Verified action outcome under the tested effect contract. |
| A composed workflow | Step count and order, decomposition, graph alternatives, intelligence access, coordination, and per-assignment configuration. | End-to-end outcomes for the evaluated workflow and population. |
| A reusable selection or fallback policy | Initial priorities, observation-dependent alternatives, transition rules, and allowed adaptation. | Behavior of that policy, including the attempts and transitions it actually used. |

Do not describe an isolated prompt, model, or response-admission comparison as
an end-to-end workflow benchmark. A workflow comparison that changes several
settings is useful, but it does not identify which setting caused a change.

Declare the objective and metric direction. Possible objectives include
verified task quality, coverage, robustness, response time, throughput,
resource use, or human intervention. Required correctness, privacy, and effect
constraints remain hard constraints. A lower-cost candidate does not win by
failing a required check.

Keep configurations with different useful tradeoffs when the task calls for
them. Several choices with different quality, time, and resource tradeoffs
can be more appropriate than one global winner. The selected policy still
needs an explicit tie-break rule.

## Define a finite grid without closing the design space

A grid enumerates declared values for selected dimensions. Continuous values
need explicit levels for an exact grid. Resource sets, prompt orderings,
graph fragments, and fallback chains need exact candidate identities.

```text
Declared experiment
├── Frozen task population and exact input identities
├── Objective, hard constraints, evaluator, and trial policy
├── Variation dimensions
│   ├── cognitive and action methods
│   ├── step counts, ordering, branching, and repetition policies
│   ├── prompt, question, and intelligence portfolios
│   ├── harnesses, models, settings, and initialization resources
│   └── supervision, effects, delivery, and fallback policies
├── Conditional compatibility and eligibility checks
├── Explicit execution authority and accounting requirements
└── Exact configurations, results, exclusions, and review records
```

The raw grid size is the product of the declared candidate counts. The
eligible set can be smaller after compatibility and authority checks.
A finite grid is the scope of one experiment, not a fixed product-wide
dimension count, maximum step count, or universal resource ceiling.

A candidate with a deterministic mode has no model-call treatment. A
candidate that needs native skill loading is ineligible when the selected
adapter cannot load that skill. A changed provider requires the existing
explicit provider authority. These exclusions must be recorded, not
silently treated as zero-cost successes.

Give each dimension a unique identity. Keep fixed settings separate from
varying settings; reject a fixed context field that overwrites a varied
dimension. Pin exact resource versions and digests before launch. Prose names
such as "deep reasoning" or "more context" do not define executable settings.

## Working offline enumeration example

The existing `VariationDimension`, `ConditionalRule`, and
`GenerationCampaign` describe a variation space.
`generate_candidates` enumerates it through a canonical Loop using the
explicit `exact_enumeration` strategy.

Run the [documentation example](../../devtools/embodiment_lab/configuration_grid_example.py)
from the repository directory:

```bash
PYTHONPATH=src:devtools .venv/bin/python -m embodiment_lab.configuration_grid_example
```

The example declares three planned step counts, two prompt bundles, and two
intelligence bundles. This gives 3 × 2 × 2 = 12 raw combinations. An
illustrative rule requires the twelve-step candidate to use examples. That
rule excludes two combinations and leaves ten proposed configurations.

```text
Raw combinations: 12
Excluded by the example rule: 2
Proposed configurations: 10
Physical model calls: 0
The proposed task configurations were not executed or promoted.
```

The rule exists only to demonstrate conditional enumeration. It is not a
product requirement that longer workflows need examples. The resource names
are proposed labels, not installed prompt or intelligence registrations.
The planned step counts do not create executable profiles. A real experiment
must compile and validate those choices against the actual runtime.

The example does not install a harness, call a model, retrieve intelligence,
write candidate artifacts, evaluate task quality, or promote a candidate.
It is a reproducible check of enumeration and canonical Loop ownership.

## Resolve candidates before execution

Use the following sequence for real trials:

```text
Declare objective, population, and variable dimensions
  -> enumerate or otherwise propose configurations
  -> apply conditional rules
  -> compile exact Loop definitions and resource bindings
  -> check installed capabilities, authority, and compatibility
  -> retain rejected configurations and their reasons
  -> initialize the selected configuration
  -> run the exact task through its governed Loops
  -> verify the applied settings and observable effects
  -> independently evaluate the result
  -> compare outcomes and stage suitability evidence
  -> independent review before reuse or promotion
```

An enumerated dictionary is not a resolved execution contract. Named
operators, such as inserting a verifier or adding a fallback, need an actual
implementation that changes the compiled structure. Recording an operator
identifier does not prove that its transformation was applied.

For each candidate, retain enough information to answer:

| Required record | Purpose |
|---|---|
| Candidate, population, task, and repetition identity | Attribute an outcome to an exact assignment instead of an anonymous grid position. |
| Resolved Loop definitions, profiles, graph, ports, and conditions | Establish what was allowed to execute. |
| Applied harness, model, route, and generation settings | Separate configured intentions from the actual invocation. |
| Prompt, question, context, skill, plugin, hook, and tool identities | Establish which resources were loaded and used. |
| Initial choices and fallback policy | Explain both the starting configuration and permitted transitions. |
| Observed attempts, changes, and effects | Preserve failures, repairs, side effects, and uncertain outcomes. |
| Evaluator identity, qualification, and exact subject binding | Prevent wrong-task, stale-oracle, or self-review results from becoming success. |
| Physical model calls, token completeness, elapsed time, and cost state | Compare total work without substituting outer harness calls for physical calls or missing usage for zero. |
| Outcome, acceptance, and lifecycle state | Keep proposed, compiled, executed, evaluated, accepted, and promoted work separate. |

Use canonical Run History and existing artifact stores for execution
evidence. Development comparison tables can use the established DuckDB
projection writer. They remain derived reports, not a second execution
history or a new managed-record authority.

## Search initial choices and fallback policies separately

Include [wrapper composition and native control ownership](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
as candidate dimensions. Compare the existing direct adapter, additional
wrapper layers, and qualified native-control profiles without treating all
native features as one switch. Freeze who owns each transition so a native
retry and an outer retry cannot independently multiply the work. Wrapper
depth and control ownership remain separate from step count and run mode.

The initial choice and the response to a particular failure can have different
priorities. Compare a fixed configuration, an alternative fixed configuration,
and a policy that can transition between them.

Freeze allowed transitions and their triggers before the trial. Record every
attempt, the setting that changed, and the observed outcome. Preserve total
consumed authority and the original task identity across transitions.
Distinguish same-configuration retry, settings adjustment, harness fallback,
model fallback, provider failover, formatting repair, semantic repair, and
task replanning.

Measure fallback reach rate, conditional success after a trigger, additional
work, unresolved failures, and end-to-end outcome. A fallback arm that was
never reached is not tested simply because it was configured. If a natural
failure does not occur, a separate labeled mechanism test can exercise the
transition; it is not live model-quality evidence.

Do not remove failed first attempts from the denominator when a later
configuration succeeds. A stopped call with an unknown external-effect
outcome needs reconciliation, not another attempt disguised as a new cell.

## Compare more steps, prompts, and intelligence deliberately

Include both additions and removals in the experimental design. Examples are:

- an additional clarification or hypothesis-generation step;
- a dedicated method-selection or simulation assignment;
- another retrieval pass when the current evidence is insufficient;
- more examples, counterexamples, questions, or prompt perspectives;
- access to an additional qualified intelligence source;
- an independent verifier or a targeted repair step;
- a parallel alternative with different resources or reasoning method;
- a compact reviewed procedure for the same obligation.

Use matched controls for individual changes. Test interactions when two
changes may depend on one another. For example, an extra retrieval step may
help only when its returned material reaches a later prompt. More independent
verification may improve acceptance reliability while increasing elapsed
time. A longer sequence may expose a defect that a short procedure misses.

Report the declared objective instead of treating fewer steps or fewer calls
as an automatic improvement. Likewise, more steps, prompts, or intelligence
records are not proof of higher quality. Measure their contribution to
verified outcomes and relevant tradeoffs.

## Control the comparison

Use a development population for search and a separately qualified holdout
for final assessment. Do not tune against the holdout and continue describing
it as untouched. Preserve task-family coverage, ambiguous cases, negative
transfer, and previously failed cases.

Hold non-treatment settings fixed, or label the comparison as a bundled
configuration comparison. Balance trial order or record timing blocks when
provider load, cache state, or environment changes could affect the result.
Record supported seeds and independent repetitions without promising
determinism from a seed.

Equal requested settings do not imply equal consumed work. Report actual
model and tool calls, retries, fallback attempts, tokens, elapsed time, and
unknown costs. A grid with ten eligible configurations, five tasks, and three
repetitions has 150 planned task trials, not 150 guaranteed model calls.
Each task trial can make zero, one, or many physical calls.

Inspect per-task results as well as aggregates. State the exact denominator
for raw configurations, conditional exclusions, preflight refusals, scheduled
trials, launched trials, completed evaluations, successes, failures, and
unresolved outcomes. Do not compare different sampled populations as though
their averages were matched.

A selected high score on the search population is not proof of general
superiority. Require held-out confirmation and independent review before
using the result as reusable suitability evidence.

## Scale the search without losing flexibility

Exact enumeration is one option. A larger design can use smaller declared
blocks, coarse-to-fine levels, stratified sampling, pairwise interaction
coverage, beam search, evolutionary proposals, or other explicitly
implemented strategies. Record which parts of the possible space were
actually explored. Do not label a truncated traversal as exhaustive.

The current generation executor installs exact enumeration only. Its
`SEARCH_STRATEGIES` vocabulary also names other strategies, but a recognized
name is not an installed search implementation. Unsupported choices refuse.
The list of future strategies is not a closed research agenda.

Define any early-stopping, resource-allocation, or refinement rule before
using it to select outcomes. Record what was excluded and why. Preserve
owner-supplied authority; do not invent a campaign-wide numeric ceiling or
infer a spending grant from a finite candidate count.

## Current implementation map

| Mechanism | Existing source | Current limit |
|---|---|---|
| Typed axes and basic conditions | [Variation dimensions](../../src/loop_engine/generation/model/dimensions.py) | Describes values and conditional rules; not complete resource or runtime compatibility. |
| Exact enumeration | [Generation campaigns](../../src/loop_engine/generation/model/campaign.py) | Returns configurations after basic rules. A candidate limit truncates traversal; the helper does not supply a complete exclusion report. |
| Loop-owned candidate generation | [Generation operators](../../src/loop_engine/generation/operators.py) | Produces proposed metadata. Operator identifiers do not by themselves implement structural transformations, and the result is not a compiled execution contract. |
| Prompt composition and observations | [Prompt resources](../../src/loop_engine/strings/prompt_fragments.py), [prompt experiments](../../src/loop_engine/core/prompt_experiment.py), [context manifest](../../src/loop_engine/core/context_pack_manifest.py) | Integration depends on the actual caller; the presence of a resource does not prove contribution. |
| Live bounded configuration trials | [Configuration matrix](../../devtools/embodiment_lab/configuration_matrix.py) | A fixed development application with a disclosed population, not an arbitrary-grid optimizer for all dimensions. |
| Reviewed harness ordering | [Harness selection](../../src/loop_engine/core/harness_selection.py) | A fixed model route and resource scope; not joint model, prompt, intelligence, graph, and fallback optimization. |

A full applied optimization campaign still needs qualified resource
resolution, complete exclusion accounting, exact treatment application,
independent evaluation, and held-out confirmation for the claimed scope.
Use existing contracts where they already represent those facts. Add the
smallest typed extension at the owning boundary when a verified gap remains.

The [saved configuration report](../verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md)
is prior bounded live evidence. It is not a new grid run or proof of the
broader design in this guide.
