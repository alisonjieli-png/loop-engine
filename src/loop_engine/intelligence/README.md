---
folder_id: intelligence
parent: ""
ontology_version: 2.0.0
---

# Intelligence

The four persistent intelligence layers at rest, each split into core, learned, and plugin provenance.

Path reading:

```text
intelligence
```

This folder inherits every rule from its ancestor READMEs:

```text
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
package root
|  -- intelligence (this folder)
```

## Where each layer is implemented

This folder declares the four layers and holds their packaged data. The
behavior lives in modules under ``core``, ``catalog``, ``memory``, and
``strings``; the [component interface record](../../../docs/architecture/COMPONENT-INTERFACES-AND-INTELLIGENCE-FLOW-2026-09-18.md)
names every hop between them.

| Layer | Folder | Implemented by |
|---|---|---|
| Context Intelligence | ``context/`` | ``core.intelligence_layers`` (search request and four-layer query), ``core.retrieval`` (ranking with reuse evidence), ``core.store_serve`` (store records), ``strings.question_engine`` (question forms), ``core.temporal_facts`` (validity intervals), ``catalog`` adapters (storage) |
| Code Intelligence | ``code/`` | ``core.capability_directory`` (surfaces and calls), ``core.reusable_capability_records`` and ``core.reusable_capability_flywheel`` (candidate to qualified admission), ``core.adaptive_practitioner_deterministic`` (registered resolvers and the fast path), ``code_nodes`` (the reusable solution capabilities) |
| Runtime History and Solution Intelligence | ``runtime_history_solution/`` | ``core.reuse_evidence`` (outcome posterior), ``core.operation_cost_records`` and ``core.operation_cost_capture`` (cost), ``core.independent_verification`` (verification reports), ``core.model_call_records`` (learnable call records), ``code_nodes.solutions_space`` (published solutions), ``memory.episodic`` |
| User Feedback Intelligence | ``user_feedback/`` | the advice store and typed task feedback slots in ``core.adaptive_practitioner_records``, approval state in ``loop.approval_state_store``, ``core.shared_memory_scopes`` (signed writes), ``memory.semantic`` (claims and contradictions) |

Runtime Memory is not a layer: ``core.runtime_memory`` keeps a temporary
board scoped to one run.
