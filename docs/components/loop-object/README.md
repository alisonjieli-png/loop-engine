# The Loop object

`Loop` is the only executable graph-vertex type in Loop Engine. A Loop may
understand a task, search intelligence, run code, call a model, validate a
result, or execute one part of a finished Solution. Its definition and role
profile state exactly which work it may perform.

## Complete definition

```text
LoopDefinition
├── definition ID, semantic version, content digest
├── registered role profile and version
├── LoopContract with typed input and output roles
├── supported modes
├── installed executor modes
├── step profile
├── loop condition
├── exit condition
├── canonical configuration facts
├── permissions and effects
└── required capabilities
```

`LoopDefinition` is immutable. Its canonical content determines its SHA-256
digest. Loading a changed record with the old digest fails.

## Start boundary

`LoopStartRequest` carries five fields:

| Field | Purpose |
|---|---|
| `goal` | Names the bounded work. |
| `definition` | Supplies every immutable execution fact. |
| `relationship` | States how this Loop entered the graph. |
| `runtime_context` | Supplies permitted capabilities, permissions, and executors. |
| `event_log` | Records definition-bound lifecycle and work events. |

The Loop refuses to start when the profile is unregistered, the contract role
conflicts with the profile, a selected mode is unsupported, or the runtime
context lacks a required capability, permission, or executor.

Some established call sites still use the older constructor shape. That
observable compatibility path composes the same complete definition and
runtime context before work starts.

## Relationship and role are separate

```text
Loop
├── relationship
│   ├── Starting
│   ├── Spawned by
│   ├── Queried by
│   ├── Retrieved by
│   └── Connected from
└── role profile
    ├── Practitioner
    ├── Intelligence
    └── Solution
```

A Starting Solution is not a separate runtime class or profile. It combines a
Starting relationship with a Solution profile. Intelligence queries use
Queried by. Selected Intelligence items use Retrieved by. Sequential Solution
work normally uses Connected from. Dynamic delegated work uses Spawned by.

## Three run modes

| Mode | Meaning |
|---|---|
| `deterministic` | Code, rules, calculations, retrieval, or execution lead the work. No language model is called. |
| `hybrid` | Code leads. A language model may resolve one bounded semantic step. |
| `non_deterministic` | A language model leads semantic work while the Loop controls tools, permissions, budgets, events, and verification. |

The definition separates supported modes from installed executors. The
runtime context also lists installed executors. A mode without a physical
executor fails before work.

Mode belongs to each Loop. A deterministic Practitioner can spawn a
non-deterministic research Practitioner, and that research Practitioner can
spawn a deterministic verifier, if the explicit definitions and runtime
contexts permit those choices.

## Step profiles and role profiles

A role profile answers, "What is this Loop for?" A step profile answers,
"Which ordered steps may run?" They remain separate.

| Step profile | Shape |
|---|---|
| `atomic_code_only` | One bounded action. |
| `compact_five_beat` | Load, choose, act, check, commit. |
| `reference_nine_step` | Orient, reconcile, assess, decide, determine how, act, verify, integrate, route. |
| Validated custom template | A bounded caller-defined sequence. |

Registered role profiles bind one of these templates or another registered
task-specific template. The complete profile tree is in the
[profile ontology](LOOP-PROFILE-ONTOLOGY.md).

## Loop and exit conditions

The loop condition controls whether another iteration may run. The exit
condition controls when the Loop has reached an accepted terminal state.

The current canonical values are:

```text
loop condition
├── steps_remain
└── chooser_selects_work

exit condition
├── steps_complete
└── accepted_success
```

An attempt, iteration, accepted result, and terminal state are separate event
facts.

## Runtime context

`LoopRuntimeContext` gives a Loop only the services and authority it needs.

```text
LoopRuntimeContext
├── Intelligence Search and Retrieval
├── Web Research
├── Custom Plugins
└── internal mechanics
    ├── service bindings
    ├── permissions
    └── installed mode executors
```

`derive()` creates a narrower context for another Loop. It cannot add a
capability, permission, or executor that the current context does not have.

## Definition example

```python
from loop_engine import (
    ConfigurationFacts,
    LoopContract,
    LoopDefinition,
)

definition = LoopDefinition(
    definition_id="practitioner.verify_import",
    version="1.0.0",
    role_profile_id="practitioner.verifier",
    role_profile_version="1.0.0",
    contract=LoopContract(
        name="verify customer import",
        execution_mode="code_only",
        input_roles=("customer_rows",),
        output_roles=("validation_result",),
        effects=("pure",),
        role="practitioner",
    ),
    configuration_facts=ConfigurationFacts.from_mapping({}),
    supported_modes=("deterministic",),
    installed_executor_modes=("deterministic",),
    step_profile="adversarial_review",
    loop_condition="steps_remain",
    exit_condition="steps_complete",
    effects=("pure",),
    required_capabilities=(
        "loop_spawn",
        "run_history_write",
        "independent_verification",
    ),
)

print(definition.ref)
```

The exact start request also needs a relationship, a compatible
`LoopRuntimeContext`, and an event log. See the
[contract index](../../contracts/) for those objects.

## Reactive capability

Every Loop can participate in a reactive series without becoming another
runtime type. The series, trigger, lease, candidate, evaluation, and portfolio
are passive records. Every claimed activation still starts one exact `Loop`.

```text
ReactiveSeriesDefinition
├── exact LoopDefinitionRef
├── exact ReactiveLoopProfile identity
├── input contract
├── output ports
├── attempt limit
└── active-activation limit
    ↓
TriggerEnvelope
    ↓
finite Loop activation
    ↓
CandidateOutput and Run History
```

The safe default remains one-shot and ephemeral. A durable series explicitly
enables reactivation, storage, scheduling, liveness, output portfolio, and
retention policies. Reading the current output portfolio does not wake the
producer.

See [Reactive Loop activation and output serving](../../architecture/REACTIVE-LOOP-ACTIVATION-AND-OUTPUT-SERVING.md).

## Current limits

- Typed input and output role names are enforced. Complete value schemas are
  not yet checked at every edge.
- Some established constructors still use compatibility composition.
- Existing `LoopDefinition` records do not yet carry an exact reactive profile
  reference. The current series definition binds it separately.
- `LoopLedger` remains the internal event-log class name pending a versioned
  migration.
