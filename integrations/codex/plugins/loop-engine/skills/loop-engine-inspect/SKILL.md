---
name: loop-engine-inspect
description: Inspect Loop Engine runs, reports, histories, plugins, or active state without starting new task work.
---

# Loop Engine Inspect

Use read-only commands first:

- `loop-engine --runs`
- `loop-engine --report <run-id> --format text`
- `loop-engine --report <run-id> --format json`
- `loop-engine --studio --runs-dir <path>` only when the user wants the local viewer

Do not refresh, resume, rerun, or call a provider merely to answer an inspection request. Keep observed facts, missing evidence, and inferred conclusions separate.
