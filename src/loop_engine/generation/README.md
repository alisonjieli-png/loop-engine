# Configuration generation and adaptive search

The generation component describes configuration spaces and proposes
candidates through the canonical Loop runtime. It can address billions of
finite combinations without constructing the Cartesian product in memory.
A proposed configuration is not an executed or accepted solution.

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

## Authoritative interfaces

| Interface | Responsibility |
|---|---|
| `VariationDimension`, `ConditionalRule`, `GenerationCampaign` | Existing declarations for values, applicability, campaign context, and owner-supplied limits. |
| `ConfigurationSpace` | Immutable JSON-compatible axis snapshot, exact address lookup, inverse lookup, and lazy shard traversal. |
| `SearchTask`, `SearchObjective`, `SearchObservation` | Exact task and metric identities, optional versioned features, observed values, and evidence references. |
| `SearchRequest`, `SearchServices` | One proposal batch, explicit computational effort, selected adapter, and host evidence resolver. |
| `propose_configurations` | Canonical Loop execution, evidence filtering, applicability checks, deduplication, and proposed candidate records. |

Integer ranges use constant-size bounds. Categorical values can contain
structured settings or versioned resource references. Changing an axis,
fixed context, condition, or campaign version changes the space identity.
Fixed context cannot overwrite a varying dimension. False, zero, null, and
text remain different choices.

`ConfigurationSpace.cardinality` is the raw product of the axes, before
conditional and runtime qualification. It is not the number of viable
configurations. Exact enumeration records a cursor for one declared shard.
Exhausting that cursor does not prove completion of other shards or earlier
addresses. The legacy `expand_variation_space` still returns a tuple; use
the indexed or lazy interfaces for large spaces.

## Proposal methods

```text
Configuration proposal adapters
├── GridSearchAdapter
│   └── lazy exact enumeration and explicit shard cursors
├── RandomSearchAdapter
│   └── seeded exploration
├── VectorWarmStartAdapter
│   └── non-dominated configurations from similar, comparably encoded tasks
└── OptunaSearchAdapter
    ├── BayesianSearchSettings
    │   └── tree-structured Parzen estimation
    ├── EvolutionarySearchSettings
    │   └── non-dominated sorting genetic search
    └── CovarianceSearchSettings
        └── covariance matrix adaptation over ordered numeric coordinates
```

Install the optional implementation with `pip install 'loop-engine[optimization]'`.
The adapter currently requires Optuna 5.0.0; covariance adaptation also
requires cmaes 0.12.0. Other versions and unsupported coordinate types receive
an explicit refusal. There is no automatic optimizer substitution.

Optuna studies are temporary in-memory projections of host-validated
observations. They are not another persistent trial store. Each batch rebuilds
from its supplied exact-task history and seed. This is reproducible proposal
computation, not exact restoration of an earlier optimizer's internal state.
The caller must query and validate the relevant evidence through existing
catalog, artifact, and Run History services.

Bayesian and evolutionary methods can use several explicitly directed
metrics. Covariance adaptation currently requires one metric and at least
two varying ordered numeric coordinates. Vector warm starts compare only
compatible feature spaces. They transfer candidate configurations, never
another task's score or acceptance.

## Evidence and execution

Every observation names its task, space, metric definitions, configuration
address, exact trial occurrence, Run History, evaluation, and evaluation
partition. The host must resolve those references before use. Distinct
occurrences may share one Run History and may repeat a configuration.
Repeated trial or exact occurrence identities,
changed spaces, incompatible metrics, unresolved evidence, and sealed final
evaluation are excluded with a recorded reason. Missing values remain
unknown. The optimizer cannot turn a failed trial into a successful one.

A batch's size and draw allowance govern only that proposal computation.
They are not a task-sample limit, total campaign budget, provider token
allocation, or permission to execute a candidate. Different batches can use
different authorized methods and settings. All task-catalog entries remain
in scope for admission; there is no fixed 100-task cap.

The product's existing executor, effect approvals, independent evaluation,
and promotion process still decide what may run and become reusable. Global
distributed claims, billion-trial storage and throughput, general task
coverage, automatic model-generated features, and fully linked live-solution
reports require separate integration and measurement. None follows from a
large address count or an optimizer control test.

See the [configuration search guide](../../../docs/guides/configuration-grid-search-and-optimization.md)
and the [Hyperlambda and wide-search review](../../../docs/research/HYPERLAMBDA-AND-WIDE-SEARCH-2026-09-13.md).
