# Studio runtime views

Studio shows bounded runtime metadata without copying private agent context.
The views are computed at request time from a saved Run History or from live
objects supplied by the host application.

## Available views

`/api/runtime` returns the live adapter and control inventory. The Runtime
page renders the same payload.

Each saved run includes a `runtime` object in `/api/run/<run-id>`. The run's
Runtime tab renders spawned tasks, external harness summaries, MCP terminal
results, approvals, context artifacts, compactions, and skill loads.

The live demo also provides `/api/runs/live/runtime`. It projects the current
ledger with the same field allowlist used for saved runs.

## What saved playback supports

| Surface | Saved playback | Source |
|---|---|---|
| Spawned Loop delegation tasks | Yes | `spawned_task_started`, `spawned_task_updated`, and `spawned_task_terminal` details in Run History `custom` events. |
| External harness runs | Yes | `external_harness_result/v2` safe summaries in Run History `custom` events. |
| MCP calls | Yes | Completed, failed, refused, unavailable, and approval-required results record safe terminal metadata. |
| Effect approvals | Yes | Requested and decided observations record safe identity, status, action, and revision fields. |
| Context artifacts and compaction | Yes | Capture and compaction observations record digests, counts, strategy, and Loop profile. |
| Skill loads | Yes | Terminal observations record skill id, version, lifecycle, manifest digest, and file count. |

The implementation does not create another node type or event store. A shared
`RuntimeObservationServices` object writes safe raw kinds to the existing Loop
ledger. The canonical vocabulary maps them to `loop.paused`, `loop.resumed`,
`state.committed`, `tool.invocation.completed`, `tool.invocation.failed`,
`capability.rejected`, or `intelligence.string.retrieved` as appropriate.

## Live inventories

The host can pass authoritative objects to Studio. Studio holds references. It
does not copy their records into another registry.

```python
from loop_engine.static_architecture.studio_operational_views import (
    StudioReadSources,
)
from loop_engine.static_architecture.studio_server import serve

sources = StudioReadSources(
    harness_registry=harness_registry,
    mcp_registry=mcp_registry,
    mcp_server_ids=("catalog", "browser"),
    skill_registry=skill_registry,
    approval_states=tuple(current_approval_states),
    context_payloads=tuple(current_context_payloads),
    compactions=tuple(current_compaction_results),
)

serve(port=8765, read_sources=sources)
```

MCP server ids are explicit because `McpRegistry` does not have a public
all-server inventory method. Studio does not inspect the registry's private
dictionaries.

Supplied live objects show current state. Saved playback comes from the
Run History observations and remains available after those objects disappear.

## Privacy boundary

The projections use fixed output fields. They do not pass event details or
object dictionaries through to the browser.

Studio does not expose:

- raw prompts or model responses;
- spawned inputs, updates, summaries, output values, or private history;
- tool arguments or tool output;
- skill instructions, supporting file paths, or workspace base paths;
- MCP commands, URLs, credential references, or input schemas;
- approval reasons, targets, reviewer identity, resume tokens, or token
  digests;
- raw context or compacted text;
- checkpoint, trace, artifact, or raw-event locations.

The view may show counts, statuses, public roles, digest prefixes, and boolean
signals such as whether a stored output exists. A digest prefix helps a person
match records. It does not grant access to the referenced content.
