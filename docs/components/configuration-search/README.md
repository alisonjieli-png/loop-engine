# Configuration space and adaptive search

Kind: component explanation for `src/loop_engine/generation`.

A discrete cognitive or act step Loop node can be configured in many ways. The
harness, the model, the prompt, the questions asked, the intelligence
retrieved, the actions permitted and the wrapper layers around a harness are
separate choices, and each one has an initial choice and ordered fallback
priorities. This component describes that space and proposes exact candidates
from it. A proposed configuration is not an executed one, and an executed one
is not an accepted one.

The registered operational boundary is `configuration search proposal`, whose
envelope is `generation.search.propose_configurations`. It runs as a canonical
Practitioner Loop.

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

An axis, a space, a task, an objective, an observation and a proposal batch are
passive records. None of them is an executable graph vertex.

## What this component owns

```text
Configuration generation and adaptive search
├── Declaration
│   ├── ConfigurationAxis and ConfigurationSpace
│   ├── conditional rules that exclude inapplicable addresses
│   └── fixed context that cannot overwrite a varying dimension
├── Addressing
│   ├── an exact integer address for every configuration
│   ├── inverse lookup from a configuration to its address
│   └── lazy shard traversal, so a large space costs time, not memory
├── Proposal
│   ├── SearchRequest, SearchServices and propose_configurations
│   └── the adapters listed below
└── Evidence
    ├── SearchTask, SearchObjective and SearchObservation
    └── exclusion of evidence the host cannot resolve
```

`ConfigurationSpace.cardinality` is the raw product of the axes, before
conditional rules and runtime qualification. It is not the number of viable
configurations, and it is not a claim that any of them ran.

## Proposal adapters

```text
Configuration proposal adapters
├── GridSearchAdapter
│   └── lazy exact enumeration with explicit shard cursors
├── RandomSearchAdapter
│   └── seeded exploration
├── VectorWarmStartAdapter
│   └── non-dominated configurations from similar, comparably encoded tasks
└── OptunaSearchAdapter
    ├── BayesianSearchSettings, tree-structured Parzen estimation
    ├── EvolutionarySearchSettings, non-dominated sorting genetic search
    └── CovarianceSearchSettings, covariance matrix adaptation
```

The last adapter is optional. Install it with
`pip install 'loop-engine[optimization]'`. It requires an exact version, and an
unsupported version or coordinate type receives an explicit refusal. There is
no automatic substitution of another optimizer.

## The two harness layering dimensions

Wrapper composition and native control ownership join a space through
`generation.layering_axes` as two `integer_range` axes, the control policy
index first and the composition index last. A fixed context field carries the
layering space digest, so a configuration addressed in one layering space is
refused on decode in another rather than read against the wrong table.

Admissibility under the run's outer harness fallback policy is not a value
equality rule, so it cannot be written as a conditional rule.
`layering_exclusions` reports it for each address in the same form as the
space's conditional exclusions, and `refuse_inadmissible_proposals` splits a
proposal batch into a separate record without altering the record the search
wrote.

`address_availability` answers, for one configuration and one adapter, whether
the address executes now, is refused by the outer policy, or is a declaration
no executor implements yet. Read
[per-step harness recovery](../core-architecture/HARNESS-FALLBACK.md) for the
declarations themselves.

## Typed inputs and outputs

| Record | Purpose |
|---|---|
| `configuration_axis/v1` | One declared axis with its values and applicability. |
| `configuration_search_batch/v1` | One proposal batch with its seed, cursor, shard, batch size and draw allowance beside the request digest. |
| `SearchCursor` | A resume point bound to one space digest and one shard. |
| `SearchObservation` | One measured trial, naming its task, space, metric definitions, address, occurrence, Run History, evaluation and evaluation partition. |

Every one of those records has a `from_dict` reader that rebuilds it with the
same digest and refuses a record with unknown or missing fields, or a record of
another type.

## Refusals

- A conditional rule that could never match, or that would exclude every
  address it matches, is refused when the space is built.
- A cursor from another space or another shard is refused, and so is a cursor
  that disagrees with an integer cursor supplied beside it.
- A configuration addressed in a different layering space is refused on decode.
- An unsupported optimizer version or coordinate type is refused explicitly.
- Repeated trial identities, a repeated evaluation artifact under another trial
  identity, changed spaces, incompatible metrics, a changed evaluator
  implementation when both sides state its digest, unresolved evidence and a
  sealed final evaluation are excluded with a recorded reason.

Missing values stay unknown. The optimizer cannot turn a failed trial into a
successful one.

## How to check it

These four self tests return a report whose only key is `tests`, a list of named
results each carrying `passed`. They do not return the `all_passed` summary that
most other self tests in the package return, so read the list:

```bash
PYTHONPATH=src python -c \
  'from loop_engine.generation.space import self_test; print(all(t["passed"] for t in self_test()["tests"]))'
PYTHONPATH=src python -c \
  'from loop_engine.generation.search import self_test; print(all(t["passed"] for t in self_test()["tests"]))'
PYTHONPATH=src python -c \
  'from loop_engine.generation.layering_axes import self_test; print(all(t["passed"] for t in self_test()["tests"]))'
PYTHONPATH=src python -c \
  'from loop_engine.generation.operators import self_test; print(all(t["passed"] for t in self_test()["tests"]))'
```

That difference in report shape is a known inconsistency in the source, not a
property of this component. It is recorded so a reader who copies a command from
another guide is not surprised by it.

The optional optimizer has its own check,
`loop_engine.generation.search_optuna.self_test`, which reports an explicit
refusal when the optional dependency is absent rather than passing quietly.

## Current behaviour and what is not established

Exhausting one shard's cursor does not prove that other shards or earlier
addresses were covered. A study built by the optional optimizer is a temporary
in-memory projection of host validated observations, rebuilt from the supplied
history and seed for each batch. That is reproducible proposal computation, not
exact restoration of an earlier optimizer's internal state.

A large space and an adaptive proposal method do not show that every
configuration ran. Read
[the configuration search guide](../../guides/configuration-grid-search-and-optimization.md)
for the population, exclusion and holdout rules a comparison must report.

## What it deliberately does not do

- It does not execute a configuration. Proposal, execution, evaluation,
  acceptance and promotion stay separate operations.
- It does not resolve evidence. The host queries and validates observations
  through the existing catalog, artifact and Run History services.
- It does not transfer another task's score or acceptance. A warm start
  transfers candidate configurations only.
- It does not treat a smaller step count, prompt count, context or model use as
  the objective. Read
  [flexible cognitive and action composition](../../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md).

## Related reading

- [The complete configuration dimension requirement](../../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
  which records the initial choice and ordered fallback priorities for each
  dimension.
- The package's own architecture contract at
  `src/loop_engine/generation/README.md`.
