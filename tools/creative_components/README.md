# Original creative components

This factory prepares original native tool packages through
`prepare_harness_candidates.py`. It does not introduce a runtime, store,
approval process or publication route. Its helper operations execute inside
their owning Loop; the runtime classification is the one in
[the supply-line guide](../supply_lines/README.md#runtime-classification).

The seed contains 35 numeric operations: easing, curve evaluation, frame and
beat timing, layout, vector math, orbit positions, signed distances, simple
physics, amplitude conversion, panning, alpha coverage and color conversion.
These operations are building blocks, not complete games, scenes or videos.

Each package contains eight files. Common launchers, checks, provenance and
licenses have repeated digests and count only once when measuring distinct
files. Parameters do not create copies of the source implementation.
`contracts/operation.json` describes the inputs, output, units, immutable implementation
digest and limitations without including the source body. The source and its
minimal helper closure remain available as `implementation.py`.
The small AGENTS.md entry satisfies the existing native review profile for
Codex. This is a declared placement, not proof of native loading in every
harness. No skill definition is generated.

## Preparation

Commit the generator and its declared sources before preparing a real batch.
The existing factory rejects a mismatch between current and committed source.
Choose a new run folder whose parent already exists:

```bash
PYTHONPATH=src:tools .venv/bin/python tools/build_creative_components.py \
  --run-folder /home/username/baltor-library/creative-seed-2026-09-29 \
  --authorize-preparation
```

The result is a native candidate catalogue. Independent review, staging,
admission and serving remain separate. No external provider, model or package
installation is used. The current generator uses the repository's MIT license
for its original files; inspiration links in the research record are not
copied implementations or bundled assets.

## Checks and limits

```bash
PYTHONPATH=src:tools .venv/bin/python -m unittest tools.test_creative_components
```

Each temporary package runs known-answer cases, malformed-input checks and a
constant-zero broken-implementation control. Additional checks cover source
closure, native metadata, shared-file deduplication, color round trips and
panning power. The test subprocesses run trusted first-party source in temporary
directories. They are not evidence of a security sandbox for third-party code.

The JSON launcher rejects non-finite output and bounds request bytes. Numeric
checks use floating-point tolerance, not a cross-platform byte-identity promise.
Native engine use, rendering quality, gameplay and accepted-task benefit have
not been qualified. New functions require meaningful behavior and independent
examples; changing a title, seed or constant is not a new implementation.
