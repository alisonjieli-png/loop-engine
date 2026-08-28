# Component interaction dictionary

The machine-readable catalog is
[`component_interactions.yaml`](../../src/loop_engine/data/component_interactions.yaml).
This page explains the active interactions in plain language.

## Context selection for a model step

```text
Practitioner step and current state
→ Queried Context Intelligence Loop
→ selected persona, supporting personas, guidance, and questions
→ LLMWorkPacket
```

The Practitioner does not read a context store and concatenate strings. The
Intelligence Loop returns selected passive components. No permission moves with
those records.

## Packet assembly

```text
LLMWorkPacket
→ deterministic prompt-assembly Loop
    → record.project atomic Loops
    → json.serialize atomic Loops
    → sequence.order atomic Loop
    → text.combine atomic Loop
→ PromptAssemblySnapshot
→ rendered LoopValue[str]
```

Each atomic operation has its own `Loop` identity, deterministic definition,
input digests, output digest, and Run History event. Native Python operations
exist only in the intrinsic kernel.

The assembly snapshot references the packet and the rendered prompt by digest.
It does not store raw private reasoning or a credential.

## Model invocation

```text
rendered prompt LoopValue
→ ModelGateway request
→ gateway Loop
→ physical model-attempt Loop
→ provider response
→ json.deserialize atomic Loop
→ phase-specific typed result validation
```

The model receives one bounded directive. It cannot grant itself capabilities,
permissions, budget, network access, file access, or terminal success.

Provider failure and output-format failure are different. A transport retry
repeats the exact route. A format repair rebuilds the packet through the
failure-focused prompt profile and preserves the previous attempt.

## Stalled-progress recovery

```text
progress snapshot comparison
→ PractitionerStallSignal
→ diagnose-stall model-attempt Loop
→ first recovery-proposal model-attempt Loop
→ alternative recovery-proposal model-attempt Loop
→ recovery-adjudication model-attempt Loop
→ PractitionerRecoveryDirective
→ normal next-action and method validation
→ governed capability execution
→ independent progress verification
```

Each semantic result gets one bounded repair attempt when its typed contract
fails. The adjudicator selects one already validated proposal rather than
restating its capability or authority fields. If the panel is unavailable,
the runtime preserves the signal and reframes; it does not claim success.

## Independent qualification

```text
QualificationCase
→ deterministic lab observations
→ one bounded Ollama prompt per semantic responsibility
→ typed QualificationVerdict
→ public Loop Engine run result
→ black-box contract and state-transition comparison
```

The lab is independent. Its own verdict does not promote a Loop Engine
component or waive repository conformance.

## Action to Solution graph

```text
NextActionDecision
→ method-selection Practitioner work
→ candidate Solution Canvas
→ capability and permission validation
→ LoopGraphDefinition
→ Connected Solution Loops
→ typed capability result
→ Practitioner verification and routing
```

The Canvas is passive. `LoopGraphDefinition` is the only reusable executable
graph authority.

## Parent and Spawned Loop work

The current runtime already records Starting, Spawned by, Queried by,
Retrieved by, and Connected from relationships. Full horizon-aware handoff
componentization remains an active checkpoint.

The accepted contract is:

```text
parent Loop
→ scoped assignment and permitted context refs
→ Spawned Loop with independent mode, budget, verification, and return contract
→ typed Spawned Loop result
→ parent integration
```

Parent private scratch, sibling private context, raw reasoning, unrelated user
data, and secrets do not transfer implicitly.

## Interaction fields

Every machine entry records:

- producer and consumer component kinds;
- operation and request/result contracts;
- Loop relationship;
- delivery and scheduling;
- retry, timeout, and cancellation;
- compatibility and version negotiation;
- context handoff and privacy;
- explicit absence or narrowing of authority transfer;
- failure, repair, and verification;
- Run History evidence;
- current implementation state.
