# Context artifacts and compaction

Context artifacts keep large tool output outside the active model context
without deleting it. The raw value is stored first by its SHA-256 digest. A
small value may also remain inline. A large value is represented by its stable
reference.

The implementation is
`loop_engine.core.context_artifacts`.

## Capture raw data first

```python
from loop_engine.core.context_artifacts import (
    ContextArtifactManager,
    ContextArtifactServices,
    ContextArtifactStore,
    ContextArtifactStoreSpec,
    ContextOffloadPolicy,
)
from loop_engine.loop.recursive_loop import LoopLedger
from loop_engine.core.runtime_observer import (
    RuntimeObservationServices,
)

ledger = LoopLedger()
store = ContextArtifactStore(ContextArtifactStoreSpec(
    "./.loop-engine/artifacts",
))
services = ContextArtifactServices(
    store,
    RuntimeObservationServices(ledger=ledger),
)
manager = ContextArtifactManager(
    services,
    ContextOffloadPolicy(
        max_inline_bytes=32_768,
        max_inline_tokens=8_192,
    ),
)

payload = manager.capture(tool_output)
```

`payload.raw` always identifies the canonical bytes. `payload.inline_text` is
present only when the text fits both thresholds. The default token counter is
a deterministic UTF-8 byte estimate. It is a policy estimate, not a provider
token measurement.

The store verifies the byte count and digest each time it reads an artifact.
A missing or changed object fails instead of returning unverified data.

## Compaction is a Loop

`DeterministicCompactor` defines the pure compaction service contract. The
built-in `HeadTailCompactor` keeps bounded text from both ends and inserts an
omission marker. `compact_context_as_loop()` runs that service through one
deterministic Intelligence Loop.

```python
from loop_engine.core.context_artifacts import (
    CompactionRequest,
    compact_context_as_loop,
)

result = compact_context_as_loop(
    CompactionRequest(
        raw=payload.raw,
        max_summary_bytes=4_096,
    ),
    services=services,
)
```

`result.raw` still points to the complete value. `result.compacted` points to a
second immutable artifact. The shorter artifact does not replace, overwrite,
or become the canonical raw output.

A model-written summary can implement the same result contract. It must run as
a hybrid or non-deterministic Loop with a model budget and a provider record.
The summary remains a derived artifact and keeps the raw reference.

## Context policy and history

Offloading changes the active context payload. Capture and compaction record
safe digest metadata on the existing Loop ledger. The events do not contain
raw or compacted text. A caller may later curate a useful artifact into an
intelligence layer through the normal candidate and review process.

The local store is the current implementation. Cloud object stores still need
a common adapter. Any later adapter must retain digest validation, immutable
raw references, and separate derived artifacts.
