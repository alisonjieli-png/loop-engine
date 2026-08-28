# Prompt and invocation encapsulation

Loop Engine treats a model as one bounded semantic resolver. The model does
not own the task, tools, permissions, provider, filesystem, budget, artifacts,
verification, or terminal success.

## Current path

```text
Practitioner semantic step
→ Queried Context Intelligence Loop
→ passive LLMWorkPacket
→ deterministic prompt-assembly Loop
    → record.project atomic Loops
    → json.serialize atomic Loops
    → sequence.order atomic Loop
    → text.combine atomic Loop
→ PromptAssemblySnapshot
→ ModelGateway Loop
→ physical model-attempt Loop
→ json.deserialize atomic Loop
→ phase-specific typed validation
→ Practitioner integration and route
```

The same path is used for orientation, next-action selection, method
selection, project construction, verification, and routing. Each call has one
`WorkDirective` and one output contract.

## Packet sections

`LLMWorkPacket` separates persona, task, Loop, Context Intelligence, questions,
capabilities, attempt history, directive, output contract, policy, budget,
sources, and exact selected context blocks. The original request remains
separate from normalized interpretation.

The packet is serialized through a deterministic JSON primitive Loop and saved
as an artifact. Run History stores its ref and digest, not the raw model prompt.

## Profiles

Core currently provides two installed prompt profiles:

- `core.prompt.standard_balanced` uses the canonical provider-neutral block
  order.

- `core.prompt.failure_repair` moves prior attempts and failures earlier while
  preserving authority and output-contract pins.

The existing `PromptAssemblySpec` remains the layout authority. A profile
selects a policy; it does not implement another prompt engine.

Future profiles may add minimal, hierarchy-preserving, references-only,
summary-plus-refs, demand-pull, adaptive-expansion, and explicitly authorized
firehose experiments. Each requires a versioned component, selection evidence,
and matched evaluation.

## Strict primitive boundary

Native Python string and JSON operations live only in
`loop/intrinsic_kernel.py`. The intrinsic kernel is finite and cannot import
task, domain, provider, store, permission, policy, routing, or example logic.

`loop/atomic_primitives.py` gives every semantic operation a logical `Loop`,
typed input, typed `LoopValue` output, definition ref, input and output digest,
lineage, mode, and Run History event.

The physical executor may later fuse compatible pure atomic Loops. Fusion must
retain logical Loop IDs, definition refs, provenance, failure location, replay
data, and cache evidence.

## Repair

A provider transport failure and an output-format failure are different.

```text
transport failure
→ retry the exact route under bounded policy

invalid JSON
→ rebuild with the failure-repair profile
→ call the same bounded semantic step
→ parse through json.deserialize Loop

invalid phase contract
→ typed semantic repair attempt
→ failed action result if still invalid
→ verification and next Practitioner pass
```

No canned model output or task-specific fallback is inserted.

## Evidence

Each context snapshot records packet ID and digest, packet artifact ref,
Intelligence Loop ID, prompt-assembly Loop ID, atomic primitive Loop IDs, block
metadata, selected layout, block order, prompt digest, and estimated size.
Provider-reported token usage remains the accounting authority after the call.
