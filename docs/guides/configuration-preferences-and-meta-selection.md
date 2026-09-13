# Configuration preferences and meta-selection

The selection method is a configuration choice. Different assignments may use
different model preference engines, harness preference engines, parameter
proposal methods, or selectors that choose among those engines. Each choice
needs an initial value and ordered fallback priorities, or an explicit
no-fallback policy.

The current interfaces support checked in-memory setting changes and advisory
rankings. They do not automatically choose and launch an optimal model and
harness pair. Native configuration setters and autonomous live selector
portfolios still need implementation and qualification.

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

A selector agent is governed work performed by a Loop. The selector algorithm,
configuration descriptor, candidate list, and policy are passive objects.
They do not add runtime types or graph vertices. The relevant existing
profile families remain:

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

The implemented setting and preference boundaries use
`practitioner.code_execution@1.0.0` in deterministic mode. A separately
authorized model-led proposal must use an appropriate model-capable Loop
and the existing model gateway. Admitting its returned proposal is a
different operation from making that model call.

## Complete behavioral explanation

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

## Separate eligibility from preference

The existing model route selector owns model eligibility. The existing harness
selector owns harness eligibility for the exact assignment, provider, and
model. A caller must construct the eligible set from those checks before
using the preference boundary. The boundary validates an ordering of that
set; it does not establish that the caller's eligibility claims are true.

For joint selection, first establish compatible combinations. Do not choose
the highest-ranked model and highest-ranked harness independently and assume
they work together. Recheck eligibility before dispatch because availability,
credentials, serving configuration, and remaining authority may have changed.
Provider locality is a sourced property of the route, not a conclusion drawn
from a harness name or endpoint spelling.

```text
Assignment and exact configuration scope
  -> existing compatibility, availability, and authority checks
  -> eligible configurations and eligible selector engines
  -> meta-selector recommends an engine ordering
  -> selected engine recommends a configuration ordering
  -> existing parameter resolver and authorized setting owner
  -> revalidation and separately authorized execution
  -> independent evaluation and verified Run History
  -> admitted search feedback for later proposals
```

Every arrow that performs independently governed work belongs to a classified
Loop. A failed eligibility check is retained as a rejection. It is not a low
preference score that another selector can override.

## Current setting interface

`core.configuration_capabilities` describes exact field bindings using the
existing `ParameterDefinition`. Its sourced facts keep support, current
availability, and qualification separate. Unknown and expired facts remain
unknown. The descriptor also declares permitted change phases, applicable
modes, mutability, locality, and authority-bearing settings.

`core.configuration_setters.apply_configuration_as_loop` accepts a target
descriptor, a caller-owned dataclass instance, exact write authority, prior
parameter sources, and a change request. It checks the descriptor and current
value digests. All changes must resolve before it returns a new dataclass.
An error returns the original instance without a partial update. The target
constructor can refuse a combination that individual field checks accepted.

The first supplied candidate is the initial choice. Later candidates are
ordered alternatives at that source's precedence. An invalid explicit
invocation or run override cannot fall back silently. A user pin, profile,
or repository default keeps its existing precedence over an intelligence
proposal. Omitted, null, empty, false, and zero remain distinct inputs.

An experimental host authority may allow staging an unavailable or
unqualified setting. It cannot turn unknown support into supported behavior,
enable an authority-bearing field, or dispatch the resulting configuration.
Changed values invalidate the prior configuration's qualification. A
qualified setting implementation does not qualify every value combination.

This setter does not write native files, change environment variables, send
commands, call a remote control service, or reconfigure a running process.
The value-digest check is an in-memory guard over the declared fields, not a
distributed transaction or rollback guarantee. The embedding owner supplies
honest source facts, complete bindings, and trusted target constructors.

## Current preference interface

`core.configuration_preferences` uses `PreferenceSnapshot` for an exact
scope and eligible choices. `PreferenceEngineBinding` binds a trusted
deterministic adapter, its implementation identity, its captured settings,
and separate availability and qualification facts. Binding metadata is a
host attestation, not independent verification of arbitrary callback code.

`resolve_preference_as_loop` supports:

| Adapter | Current behavior |
|---|---|
| `ExistingOrderPreference` | Preserves the existing selector's ordering. |
| `ExplicitOrderPreference` | Places named eligible choices first and retains the rest. |
| `SuppliedAgentPreference` | Validates a separately produced, scope-bound agent proposal without calling a model. |
| Host-bound deterministic adapter | Uses the same `rank` and `descriptor` contract, with explicit implementation and qualification records. |

The result must be a complete ordering of the supplied eligible set. A stale
snapshot, invented choice, missing choice, changed adapter settings, or empty
eligible set cannot become a successful recommendation. Failed engine
attempts remain in the report. `MetaPreferencePolicy` permits fallback only
for named failure classes. Its first engine is initial; the rest are ordered
fallbacks, not automatic approval to run them after any failure.

The same interface can rank `preference_engine` or `search_adapter` choices.
A composing owner can run one preference Loop to choose the next engine,
then another preference Loop to rank configurations. Supply the active engine
references to refuse cycles. The boundary does not recursively start an
unbounded chain of selectors. Use a common parent Loop to preserve the graph
relationships and shared Run History; local Loop identifiers are scoped to
their run, not globally unique identities.

Candidate attributes, adapter descriptors, and source identities are public
metadata. Keep private prompts, keys, and resource bodies behind authorized
references. Mark sensitive setting definitions before inspection or update.
Reports contain ordered candidate digests, attempted resolutions, rejections,
and source identities. They do not prove task acceptance or promotion.

## Selector types to develop and compare

The following is an open design space, not a list of installed autonomous
agents. The [configuration search guide](configuration-grid-search-and-optimization.md)
describes the existing grid, random, vector, and optional optimizer adapters.

| Selector or controller | Proposed responsibility | Required comparison |
|---|---|---|
| Task-aware model preference | Rank eligible exact model routes for the assignment. | Matched task, contract, model revision, and evaluator evidence. |
| Task-aware harness preference | Rank compatible harnesses without changing model authority. | Same model, resources, contracts, and population across harnesses. |
| Bayesian search controller | Propose settings using admitted objective observations. | Search feedback partition, uncertainty, failed trials, and held-out evaluation. |
| Evolutionary search controller | Propose mutations or combinations of configurations. | Valid configuration operators, ancestry, diversity, and independent outcomes. |
| Vector-based transfer selector | Retrieve candidate configurations from related tasks. | Exact feature encoding and evidence that transfer helps without copying incomparable scores. |
| Model-led configuration planner | Propose a coherent joint configuration and explain missing facts. | Structured proposal validation and actual gateway call accounting. |
| Portfolio coordinator | Allocate proposal work among several selectors. | Measured contribution and overhead, including discarded proposals and failed selectors. |
| Uncertainty controller | Decide when to explore, abstain, or request more information. | Calibration and measured consequences of incorrect confidence. |
| Independent configuration verifier | Check a proposed configuration and its evaluation evidence. | Separate authority and inputs that do not permit producer self-approval. |
| Meta-selector | Choose or order the other selectors for this assignment. | Comparison against the constituent selectors under a frozen evaluation plan. |

The selector itself has a profile, mode, model and harness preferences,
context, tools, thinking setting, continuation conditions, and authority.
Those choices can also be studied. Declare the composition and stopping
conditions explicitly so selecting a selector does not require endless
selection before any useful work begins. More selectors, steps, prompts,
or model calls are candidate approaches, not evidence of more intelligence.

## Additional dimensions to retain

These refinements extend the required baseline in
`loop_dimensions.configuration_design.proposed_dimensions`. They are not
independent axes whose sizes can automatically be multiplied.

| Refinement | Initial and fallback choices to represent |
|---|---|
| Model preference engine | Existing route order, evidence ranker, or qualified custom proposal method. |
| Harness preference engine | Existing eligible order, reviewed trial ranking, or qualified custom ordering. |
| Meta-selector and engine priorities | Initial selector, alternate selectors, abstention, and explicit transition triggers. |
| Selector portfolio coordination | Serial proposals, permitted parallel proposals, agreement rules, or a single engine. |
| Objective tradeoff and feasibility | Metric priorities, constrained objectives, or an admitted alternative tradeoff policy. |
| Selector uncertainty and abstention | Confidence policy, information request, additional proposal, or stop. |
| Selector feedback partition and scope | Exact-task evidence, admitted cross-task evidence, or no reusable evidence. |
| Task feature encoding and distance | Versioned feature representation and compatible alternatives. |
| Configuration setter backend | In-memory field binding, qualified native file setter, command interface, or remote control adapter. |
| Configuration change phase | Before initialization, per request, between steps, or explicit restart. |
| Atomic configuration change and rollback | Staged replacement, exact commit protocol, reconciliation, or refusal. |
| Support discovery and freshness | Host declaration, qualified handshake, sourced documentation, or permitted probe. |
| Effective configuration confirmation | Echoed effective settings, native load evidence, invocation observation, or unknown. |
| Deployment and serving realization | Qualified local or cloud deployment, serving implementation, hardware, and model realization. |
| Concurrency and service admission | Eligible service capacity, queue policy, alternate deployment, or deferred work. |
| Search to execution binding | Exact proposed configuration binding, revalidation, authorized dispatch, or recorded exclusion. |
| Selector drift and independent requalification | Current reviewed selector version, qualified replacement, or loss of eligibility. |

Every refinement inherits the baseline requirements for exact identities,
ordered fallbacks, compatibility, authority, transition triggers, independent
evaluation, and retained failures. A new label does not install a setter,
grant a permission, or qualify a native harness capability.

## Verification boundary

The component checks exercise in-memory setting changes, the existing model
gateway with an offline fixture, existing harness eligibility, two-stage
meta-selection, and existing grid and random proposal adapters. They also
exercise unavailable and stale facts, sensitive-value reports, explicit pins,
invalid proposals, and atomic refusal.

These checks make no live provider calls and solve no real task population.
They do not establish optimal configurations, autonomous learning, or an
achieved artificial general intelligence system. Broad qualification still
requires frozen real tasks, permitted live execution, independent evaluators,
and complete reports that include selector overhead and failed attempts.
