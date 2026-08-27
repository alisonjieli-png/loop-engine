# Loop profile ontology

Loop Engine has one runtime class: `Loop`. A loop profile is immutable data
that configures that class for a specific kind of work. Profiles do not create
new runtimes and do not use a deep Python class hierarchy.

Each profile names its base profile, version, step template, allowed modes,
allowed logical kinds, required fields, and required capabilities. A
specialized profile may add requirements or narrow permissions. It cannot
expand the permissions of its base profile.

`LoopDefinition` binds the exact profile ID and version to one contract,
configuration, mode policy, executor set, conditions, permissions, effects,
and capability set. A profile is reusable classification data. The definition
is the complete immutable contract for one runnable Loop.

The code keeps data and behavior separate. `loop_profile_catalog.py` contains
the immutable built-in definitions. `loop_profile_ontology.py` resolves
parents, validates the tree, binds profiles, and checks version compatibility.

## Operational relationship is not profile inheritance

Run relationships and role profile inheritance are separate structures.

```text
Operational relationship
├── Starting
├── Spawned by
├── Queried by
├── Retrieved by
└── Connected from
```

`LoopRoleIdentity` stores `role`, `profile_id`, and `profile_version`.
`LoopRelationship` separately stores one relationship kind and only the IDs
allowed for that kind. The five kinds are Starting, Spawned by, Queried by,
Retrieved by, and Connected from.

All three roles can use any relationship that is valid for the work. Query,
retrieval, and connection relationships do not create more runtime roles or
profile families.

The ordinary relationship pattern is:

```text
Task
└── Starting Practitioner
    ├── may spawn a Practitioner subproblem Loop
    ├── queries an Intelligence Query Loop
    │   └── retrieves Intelligence Item Loops
    └── builds a Solution Canvas
        └── Starting Solution
            ├── Connected Solution Loops
            └── Spawned Solution only for dynamic branch work
```

## The profile inheritance tree

The following diagram is catalog inheritance. Its top `Loop` box is the
abstract profile base, not the Starting Loop in a run.

```mermaid
flowchart TD
    L["Loop\nshared typed contract, exit condition, step profile, mode policy"]

    L --> P["Practitioner"]
    L --> I["Intelligence"]
    L --> S["Solution"]

    P --> PP["Profiles\nreference nine-step, compact five-step,\nresearch, solver, verifier,\nself-improvement task, code execution"]

    I --> IO["Cross-layer operations\nsearch, materialize"]
    I --> IC["Context Intelligence"]
    I --> IX["Code Intelligence"]
    I --> IH["Runtime History and Solution Intelligence"]
    I --> IU["User Feedback Intelligence"]

    IC --> ICP["serve, search, frame for task"]
    IX --> IXP["resolve reference, invoke capability,\nload package or repository"]
    IH --> IHP["search, replay, compare"]
    IU --> IUP["serve, scope, interpret for task"]

    S --> SP["Profiles\natomic component, pipeline,\nrouter and fallback, ensemble, validator"]
```

The three top branches answer different questions:

| Branch | Question |
|---|---|
| Practitioner | What work is the system doing to understand, build, test, or improve something? |
| Intelligence | What intelligence item is being searched, served, framed, loaded, replayed, or compared? |
| Solution | What finished component or composition runs for a new input? |

## Common role aliases

Aliases are topology-neutral. A spawning Loop may use one for delegated work,
while the same resolved profile can also be Starting.

| Role | Public selector | Purpose |
|---|---|---|
| Practitioner | `researcher` | Research and source checking. |
| Practitioner | `solver` | Build, test, diagnose, and repair. |
| Practitioner | `verifier` | Independent verification. |
| Intelligence | `intelligence.search` | Search selected layers. |
| Intelligence | `intelligence.materialize` | Verify and load one selected item. |
| Intelligence | `intelligence.invoke` | Invoke selected Code Intelligence. |
| Intelligence | `intelligence.replay` | Replay selected Runtime History. |
| Intelligence | `intelligence.interpret` | Interpret selected User Feedback. |
| Solution | `solution.component` | Run one typed component. |
| Solution | `solution.validator` | Check one result. |
| Solution | `solution.router` | Choose a permitted route. |
| Solution | `solution.fallback` | Try an ordered fallback. |
| Solution | `solution.ensemble` | Combine compatible results. |

Self-improvement belongs under Practitioner. It is a task given to the Loop
Practitioner. It is not a fourth runtime role and it cannot approve its own
candidates.

The Solution Canvas runner executes deterministic, hybrid, and
non-deterministic Solution Loops through the shared mode contract. Model-using
leaves require an installed gateway-backed executor and exact model-call
authority. When either is absent, execution fails with a typed unavailable
executor result and never changes mode silently.

## Terms that stay separate

These settings describe different parts of a loop. Combining them under one
name makes configuration harder to check.

| Setting | Meaning |
|---|---|
| Operational relationship | Starting, Spawned by, Queried by, Retrieved by, or Connected from. |
| Role identity | Practitioner, Intelligence, or Solution plus an exact profile version. |
| Loop profile | The loop's purpose and required interface. |
| Step profile | The number, order, and repetition of steps. |
| Run mode | Deterministic, hybrid, or non-deterministic execution. |
| Logical kind | Execution, task-semantic work, or search-improvement work. |
| Effort | Limits for iterations, retrieval, and model calls. |
| LLM thinking power | The configured model tier for a hybrid or non-deterministic loop. |

An LLM thinking power value is invalid on a deterministic-only loop. A profile
binding that selects hybrid or non-deterministic mode must provide a thinking
power value. The current levels are `small`, `medium`, `high`, `max`, and
`specialized`.

## Profile requirements

Every profile inherits these requirements from the shared `Loop` profile:

1. A `LoopContract` with typed input and output roles.
2. An exit condition.
3. A registered step profile.
4. A mode policy.

Specialized profiles add only what they need. For example, a Context search
profile adds a query and the Context search capability. A code package profile
adds an artifact manifest, an entry point, and an artifact loader. A Solution
ensemble adds member loops, a combination rule, and the ensemble capability.

The ontology and `LoopDefinition` check requirements before a Loop starts.
They do not treat a
field name as proof that a provider, store, package, or operation works. The
runtime still verifies the selected capability and records the run.

## Bind a profile to the current runtime

Pass one typed request to `bind_profile`. The result contains the resolved
profile, the original typed contract, and the existing `LoopConfig`.

```python
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.loop_profile_ontology import (
    LoopProfileBindingRequest,
    LoopProfileRef,
    bind_profile,
)

request = LoopProfileBindingRequest(
    profile=LoopProfileRef("practitioner.solver", "1.0.0"),
    goal="repair a failed customer import",
    contract=LoopContract(
        name="repair-customer-import",
        execution_mode="hybrid",
        input_roles=("import_failure/v1",),
        output_roles=("repair_patch/v1",),
    ),
    available_fields=("acceptance_test",),
    capabilities=(
        "loop_spawn",
        "run_history_write",
        "solution_build",
        "independent_verification",
    ),
    modes=("deterministic", "hybrid"),
    preferred_modes=("deterministic", "hybrid"),
    llm_thinking_power="high",
)

bound = bind_profile(request)
bound.config.framework       # "custom"
bound.config.custom_steps    # build, test, diagnose, and repair steps
bound.config.allowable_modes # ("deterministic", "hybrid")
```

The profile points to the existing `build_test_repair` Loop Template. The
binding does not copy that step sequence into another runtime.

## Version handshake

Every profile reference includes an exact semantic version. A consumer can
accept a profile branch and a compatible major version. A more specific
profile satisfies the branch requirement when its ancestry and version match.

```python
from loop_engine.loop.loop_profile_ontology import (
    LoopProfileRef,
    LoopProfileRequirement,
    profile_handshake,
)

result = profile_handshake(
    LoopProfileRef("intelligence.context.search", "1.0.0"),
    LoopProfileRequirement(
        "intelligence.context",
        minimum_version="1.0.0",
        compatible_major=1,
    ),
)

assert result.compatible
```

The handshake fails if the provided profile belongs to another branch, uses an
unsupported major version, is older than the required version, or is not in the
registered ontology.

Profile compatibility does not prove that two loop ports connect. Use
`LoopConnectionSpec` and `validate_loop_connection()` for the separate typed
input and output check.

## Validation rules

`validate_profile_ontology()` checks the full tree without running a loop. It
fails when:

- the shared `Loop` profile or any role branch is missing;
- an intelligence layer branch is missing;
- a role alias targets a missing profile;
- a parent reference is missing or cyclic;
- a specialized profile expands the modes or logical kinds of its base;
- a runnable profile points to a missing, invalid, or candidate Loop Template;
- a deterministic-only profile accepts LLM thinking power;
- a runnable profile has no exit condition or step template.

`LoopRoleIdentity` rejects a profile outside its declared role.
`LoopRelationship` rejects a Starting relationship that names another Loop,
a missing required relationship ID, or fields that belong to another
relationship kind.

Run the focused deterministic test with:

```bash
PYTHONPATH=src python -c \
  'from loop_engine.loop.loop_profile_ontology import self_test; print(self_test())'
```

Print the complete serializable catalog:

```bash
loop-engine --profiles
```
