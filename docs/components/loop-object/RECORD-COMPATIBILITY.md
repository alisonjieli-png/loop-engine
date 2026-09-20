# Loop contract cardinality and record compatibility

The [version policy](../../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
separates two obligations: remove accidental support for unpublished formats,
and retain deliberate runtime version, capability, and schema negotiation
between independently deployed releases. Select an explicitly supported
implementation shared by both sides. Never silently downgrade security,
permissions, evidence requirements, or effect authority.

Continuous integration tests negotiation. It does not replace the runtime
handshake or make an incompatible record executable.

## Input and output cardinality

`LoopContract.output_type` and `max_outputs` describe producer emissions.
`LoopInputCardinality` describes one named input role. An unspecified input
role accepts a single item. A multiple-item input requires an explicit
positive `max_items` bound.

```python
from loop_engine import LoopContract, LoopInputCardinality

consumer = LoopContract(
    name="compare candidate summaries",
    execution_mode="code_only",
    input_roles=("candidate_summaries",),
    output_roles=("selected_summary",),
    input_cardinalities=(
        LoopInputCardinality("candidate_summaries", "multiple", max_items=4),
    ),
)
```

A multiple-output producer can connect directly only when its declared bound
fits the consuming input. A single-item input needs an explicit selecting
Adapter Loop when the producer can emit multiple items. An adapter on one
connection does not authorize incompatible input on another connection.

These checks cover declared emission cardinality at a connection. They do
not establish arbitrary fan-in scheduling or complete value compatibility for
shapes, units, encodings, and field constraints. Those remain separate work.

## Supported record encodings

The following is a source checkpoint for September 19, 2026. Recheck the
owning reader and its negative tests before changing a contract or claiming
cleanup is complete.

| Boundary | Current encoding | Observed implementation and remaining work |
|---|---|---|
| [Loop definition](../../../src/loop_engine/loop/loop_definition.py) | `loop_definition/v2` | The reader still accepts version 1 shapes. Removal of this unpublished reader is pending, not a promise to support it for new integrations. |
| [Spawned task checkpoint](../../../src/loop_engine/loop/spawned_task_checkpoint.py) | `spawned_task_checkpoint/v3` | The reader still accepts version 2. Preserve cardinality and integrity checks while completing the tracked cleanup. |
| [Ontology definition record](../../../src/loop_engine/ontology/loop_definition_record.py) | `LoopDefinitionRecord` | The reader still maps the retired serialized kind into the current record. This unpublished conversion remains cleanup work. |
| [Saved product outcome](../../../src/loop_engine/core/product_outcome_store.py) | `solve_outcome/v6` | The current reader refuses older outcome versions. Historical files remain unchanged. |
| [Code asset and admission](../../../src/loop_engine/core/code_intelligence_assets.py) | `code_asset_spec/v2`, `code_asset_admission/v2` | Current qualification binds exact data, dependencies, contracts, effects, and independent evidence. Old evidence requires requalification, not automatic promotion. |
| [Intelligence item reference](../../../src/loop_engine/loop/loop_capsule.py) | `intelligence_item_ref/v2` | The wire reader requires the current shape. Remaining Python aliases are separate cleanup work. |

A serialized record version, semantic component version, role-profile version,
and external protocol version identify different contracts. An older number
does not establish incompatibility by itself, and a matching number does not
grant authority. Each deployed adapter must declare its supported versions
and capabilities; selection must use their actual shared supported contract.

Do not add an old-format reader merely because an immutable artifact exists.
A separately authorized conversion can create a new artifact with provenance
if a real use case requires it. It must not become an automatic runtime
fallback.

## Verification and preservation

Test a valid supported record, an unsupported old shape, an unknown future
version, malformed fields, changed content with an old digest, and a compatible
request without required authority. Every failed admission must precede
writes, model calls, and external effects. Keep a known-wrong control that
fails when the guard is removed.

Use the owning Loop definition, contract, checkpoint, outcome, and admission
checks, then dependent and full release checks on the exact source tree.
The [continuation status](../../roadmap/CONTINUATION-STATUS.md) tracks the
remaining removals and release gates; this guide does not mark them complete.

Do not rewrite old Run History, checkpoints, benchmark evidence, or managed
reports to make them look current. A current reader's explicit refusal does
not destroy the stored evidence. The
[preserved guide](../../evidence/context-route-snapshot-2026-09-19/docs__components__loop-object__RECORD-COMPATIBILITY.md.txt)
retains the previous historical-reader requirements as a non-authoritative
snapshot.
