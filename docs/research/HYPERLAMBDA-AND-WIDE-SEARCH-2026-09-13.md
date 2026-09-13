# Hyperlambda, executable solutions, and wide configuration search

The owner asked for working Solution Canvases, reports linking actions,
model calls, code, and outputs, and a system that explores billions of
possible configurations. The owner explicitly rejected a fixed 100-task
sample. The full task catalog remains in scope for admission and testing.

## Current Loop Engine evidence

A Solution Canvas can compile and execute registered operations. The saved
customer-import example completed a deterministic pipeline with a real
fallback, 75 Run History events, and no model calls. This is an executed
example, not proof that arbitrary tasks produce reusable solutions.

The three saved later task outcomes have intact Run History chains but no
delivered artifact records and incomplete physical model-call accounting.
Two contain selected Canvas declarations and graph digests despite ending
as cancelled; the third is blocked on material input. None establishes a
working, independently verified deliverable. The other three starts in
that cohort failed before producing those outcomes. The
[September 12 checkpoint](COGNITIVE-STEP-ARCHITECTURE-AND-STATE-2026-09-12.md)
records these failures separately from component progress.

The configuration study verified 244 history chains and reconciled 70
physical calls. Those records cover small disclosed controls, not the
complete task library. The [study report](../verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md)
states its population and limitations.

## Hyperlambda research

The supplied `app.ainiro.io/hyperlambda` page could not be retrieved by the
web reader. This review therefore used the current project site, official
documentation, and source pinned to Magic revision
`100ce0ec1c41c1c148692560d017eed334ede3b6`, dated September 12, 2026.
No Hyperlambda service was installed, invoked, or exposed to the network.

### Program representation and execution

Magic is the application platform; Hyperlambda is its executable tree
language. The project describes generating an abstract syntax tree from
natural language and checking function availability. That is a useful
structural boundary, but it does not establish semantic correctness.
The project itself distinguishes a nonexistent function from logically
wrong code. [Project overview](https://github.com/polterguy/magic/tree/100ce0ec1c41c1c148692560d017eed334ede3b6)

The actual `Whitelist` implementation creates a scoped vocabulary and
result context, clones the supplied program, and evaluates that clone.
The evaluator checks the active vocabulary before each dispatched
operation. A whitelist is conditional on the execution scope: its existence
in the language does not mean every possible invocation has the same
permissions. [Whitelist source](https://github.com/polterguy/magic/blob/100ce0ec1c41c1c148692560d017eed334ede3b6/plugins/magic.lambda/magic.lambda/eval/Whitelist.cs),
[evaluator source](https://github.com/polterguy/magic/blob/100ce0ec1c41c1c148692560d017eed334ede3b6/plugins/magic.lambda/magic.lambda/eval/Eval.cs)

Inference: Loop Engine should retain its existing separation between
generation, compilation, exact capability resolution, effect authorization,
execution, and independent acceptance. An allowlisted operation can still
have broad effects, incorrect arguments, or a wrong result. Source inspection
here is not a security audit or an endorsement of the project's performance
comparisons.

### Reporting and debugging

Hyperlambda's debugger records dispatched operations, their tree locations,
elapsed time, and the program state after each operation. It preserves the
recording when execution throws. The evaluator limits a recording to 10,000
steps and emits an explicit truncation marker. This is useful diagnostic
behavior, not an unlimited durable execution history.
[Debugger source](https://github.com/polterguy/magic/blob/100ce0ec1c41c1c148692560d017eed334ede3b6/plugins/magic.lambda.system/review/DebugHyperlambda.cs),
[recording implementation](https://github.com/polterguy/magic/blob/100ce0ec1c41c1c148692560d017eed334ede3b6/plugins/magic.lambda/magic.lambda/eval/Eval.cs)

The exposed debugging endpoint requires the root role. Recording arbitrary
program state can include sensitive material, so Loop Engine should not
copy full-state logging into public reports. Exact references, digests,
authorized artifact access, safe summaries, and explicit missing or truncated
records are the relevant ideas. Debugging playback must never replay a
committed external effect. [Debugging endpoint](https://github.com/polterguy/magic/blob/100ce0ec1c41c1c148692560d017eed334ede3b6/backend/files/system/evaluator/debug.post.hl)

### Licensing and independence

The inspected repository has an MIT license. Its documentation says the
specialized generator's training dataset is not public. A self-hostable
runtime and durable generated programs are therefore distinct from an
independently reproducible generation service. Any integration still needs
dependency, license, version, and provenance review.
[License](https://github.com/polterguy/magic/blob/100ce0ec1c41c1c148692560d017eed334ede3b6/LICENSE),
[generator description](https://github.com/polterguy/magic/tree/100ce0ec1c41c1c148692560d017eed334ede3b6#the-llm)

## Wide search within the existing runtime

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

Keep the complete explanation in [ASTRA.md](../../ASTRA.md#complete-behavioral-explanation).
Search adapters and configuration addresses are passive mechanics used by
Loops. Hyperlambda, if later qualified, would be an optional external adapter
or Code Intelligence implementation, not another Loop Engine runtime.

```text
Configuration search
├── Exact enumeration and seeded exploration
├── Bayesian search from observed task results
├── Evolutionary mutation, crossover, and multi-objective selection
├── Covariance adaptation over ordered numeric coordinates
├── Vector-based candidate priors from related tasks
└── Future compatible algorithms through the same proposal boundary
```

The new proposal implementation uses existing generation contracts, lazy
mixed-radix addresses, and a canonical proposal Loop. Optional Optuna 5.0.0
adapters run actual Bayesian and genetic samplers; covariance adaptation
uses cmaes 0.12.0. These are implementations of proposal computation, not
proof of task quality or distributed billion-trial throughput.
[Component guide](../../src/loop_engine/generation/README.md)

Optuna's ask-and-tell interface separates proposal from objective execution,
which fits this boundary. Its Bayesian sampler learns distributions from
observed results, while its non-dominated sorting sampler implements genetic
search. The search method and its parameters can vary by assignment.
[Ask and tell](https://optuna.readthedocs.io/en/v5.0.0/tutorial/20_recipes/009_ask_and_tell.html),
[Bayesian sampler](https://optuna.readthedocs.io/en/v5.0.0/reference/samplers/generated/optuna.samplers.TPESampler.html),
[genetic sampler](https://optuna.readthedocs.io/en/v5.0.0/reference/samplers/generated/optuna.samplers.NSGAIISampler.html)

Task conditioning must preserve evaluator compatibility and leakage
boundaries. Exact-task measurements may train the current search.
Comparable task vectors may suggest configurations to retest, but their
scores do not become the new task's scores. Sealed final evaluation cannot
guide search. Other algorithm-configuration systems also distinguish
optimization for one instance from performance across problem instances.
[SMAC3 paper](https://arxiv.org/abs/2109.09831)

## What a complete trial must deliver

| Required output | Evidence that must be linked |
|---|---|
| Task record | Exact task version, files, disclosure authority, input/output contract, and evaluation partition. |
| Configuration record | Every applied initial setting, fallback order, resource version, optimizer setting, and excluded choice. |
| Practitioner history | Exact cognitive and action occurrences, parent relationships, decisions, observations, and failures. |
| Physical call records | Provider, model, harness, actual call identity, usage completeness, retries, and unknown outcomes. |
| Executable Solution Canvas | Versioned graph, resolved operations, code and dependency digests, typed connections, and permitted modes. |
| Output artifacts | Exact code and output references with access policy and immutable content identity. |
| Independent evaluation | Qualified evaluator, exact subject binding, measured outcomes, negative controls, and held-out results. |
| Fresh-input execution | The exported solution runs in a clean declared environment without the original investigative state. |
| Report | Joined references above, plus represented, proposed, executed, failed, verified, and promoted counts kept separate. |

A task missing its source, evaluator, physical capability, or authority
remains visible as an admission or execution gap. It is not silently removed
from the denominator. The owner has not supplied a total campaign ceiling;
one proposal batch's memory and draw allowance is not such a ceiling.

The next integration work is durable trial dispatch through existing leases,
complete execution/evaluation joins, independently qualified task adapters,
and repeated live experiments over the admitted task pool. A large address
space, a generated diagram, or an optimizer-only test cannot stand in for
that work.

## Implementation verification

The [saved controls](../../artifacts/wide-search-20260913-0U0br7/README.md)
retain the measured results. Source checks passed 4,392 of 4,392; the clean
base installation passed 4,357 of 4,357. All 27 conformance gates passed in
both environments. After installing the optional optimizer dependencies in
the clean installation, all 15 dedicated optimizer controls passed.

The executable control ran 120 parameterized Canvases, with all trial
histories retained, and replayed the five selected Canvases on fresh inputs.
Two selected configurations passed and three did not. The address test
checked 10,000 lookups in a one-trillion-address space. These controls made
no provider calls and executed no task-database tasks. They do not complete
the requested broad live campaign.
