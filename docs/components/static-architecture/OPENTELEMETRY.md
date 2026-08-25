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
    │       └── search spans
    └── safe scalar attributes only
```

`run_history_to_spans()` owns the projection. `RunHistory.to_otel_spans()` calls
that same function and returns dictionaries for compatibility. There is no
second tracing interpretation in Run History.

The exporter preserves span links by starting every Spawned Loop or event span
with the actual upstream span context. It also includes the logical Run
History trace and span IDs as attributes. A missing or cyclic upstream
reference fails before export.

Raw prompts, tool output, intelligence bodies, secrets, approval tokens, and
private context for a Spawned Loop are not exported. Loop goals are not used
as span names.

## Export a saved run

```python
from loop_engine import OpenTelemetrySpanExporter
from loop_engine.static_architecture.otel_export import (
    export_run_history_as_loop,
)

exporter = OpenTelemetrySpanExporter("loop_engine")
result = export_run_history_as_loop(
    saved_ledger_events,
    run_id="run-42",
    exporter=exporter,
)
```

The export itself is a deterministic Loop. The installed-package test uses the
real OpenTelemetry SDK with an in-memory SDK exporter and verifies that the
Starting Loop, Spawned Loop, and model event share one trace with the correct
links. This test proves local SDK integration. It does not prove connection to
an external collector.
