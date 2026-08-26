# OpenTelemetry export

Loop Engine can export a safe trace view of a saved Run History. Run History stays
the source of truth. Exporting a trace does not change task acceptance, run
history, or the Run History hash chain.

```text
Run History
├── canonical ordered events
├── verified hash chain
└── one OpenTelemetry projection
    ├── Starting Loop span
    │   └── Spawned Loop spans
    │       ├── model spans
    │       ├── tool spans
    │       ├── search spans
    │       ├── skill spans
    │       ├── context artifact and compaction spans
    │       └── approval spans
    └── safe scalar attributes only
```

`run_history_to_spans()` owns the projection. `RunHistory.to_otel_spans()`
passes the complete `RunHistory` to that function. The projection recomputes
the hash chain and refuses changed history before it creates a span. There is
no second tracing interpretation in Run History.

A caller that has only live ledger dictionaries must wrap them in
`RawLedgerEvents`. Bare sequences are refused. Spans and the export result from
that compatibility path carry `source_kind="raw_ledger_unverified"` and
`chain_verified=False`, so raw events cannot be mistaken for verified saved
history.

The exporter preserves span links by starting every Spawned Loop or event span
with the actual upstream span context. It also includes the logical Run
History trace and span IDs as attributes. A declared Spawned Loop with an
absent, conflicting, or cyclic parent fails before export.

Raw prompts, tool output, intelligence bodies, secrets, approval tokens, and
private context for a Spawned Loop are not exported. Loop goals are not used
as span names.

MCP completion, skill loading, context storage, compaction, and approval state
events use the same safe scalar allowlist. Their bodies, credentials, approval
tokens, and file paths do not enter trace attributes.

## Export a saved run

```python
from loop_engine import OpenTelemetrySpanExporter
from loop_engine.core.otel_export import (
    export_run_history_as_loop,
)

exporter = OpenTelemetrySpanExporter(tracer=configured_recording_tracer)
result = export_run_history_as_loop(
    saved_run_history,
    run_id=saved_run_history.run_id,
    exporter=exporter,
)
```

`configured_recording_tracer` must come from an OpenTelemetry SDK
`TracerProvider` with the intended span processor. A no-op or otherwise
non-recording tracer is refused. Returning a projected count is not treated as
successful export when the SDK records nothing.

For explicitly unverified live events:

```python
from loop_engine import RawLedgerEvents

source = RawLedgerEvents(tuple(live_ledger_events))
result = export_run_history_as_loop(
    source,
    run_id="live-run-42",
    exporter=exporter,
)
assert result.chain_verified is False
```

The export itself is a deterministic Loop. The installed-package test uses the
real OpenTelemetry SDK with an in-memory SDK exporter and verifies that the
Starting Loop, Spawned Loop, and model event share one trace with the correct
links. It also rejects changed Run History, missing parents, bare event
sequences, and a non-recording SDK tracer. This proves local SDK integration.
It does not prove connection to an external collector.
