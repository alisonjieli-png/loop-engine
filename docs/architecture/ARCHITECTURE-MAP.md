# Architecture map

This document is **generated from the code** and lives with it, so the
projection can never drift from what is on disk:

```text
src/loop_engine/ARCHITECTURE-MAP.md
```

Regenerate rather than hand-edit:

```bash
python -m loop_engine --map
```

The `architecture_map_freshness` conformance check enforces freshness. A
committed map fails the build when its module list differs from the live
projection.
