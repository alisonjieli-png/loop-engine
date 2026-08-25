# Architecture map

This document is **generated from the code** and lives with it, so the
projection can never drift from what is on disk:

    src/loop_engine/ARCHITECTURE-MAP.md

Regenerate rather than hand-edit:

```bash
python -m loop_engine --map
```

Freshness is enforced by the `architecture_map_freshness` conformance gate — a
committed map whose module census disagrees with the live projection fails the
build.
