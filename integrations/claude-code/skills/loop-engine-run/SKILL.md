---
name: loop-engine-run
description: Run a task through Loop Engine when the user asks it to build, solve, execute, verify, or resume work.
allowed-tools: Bash, Read, Write
---
# Loop Engine run

Use `loop-engine solve` with a preserved task file, explicit workspace, run
directory, provider route, and budgets. Use `loop-engine task build` only for
non-executing task structure. Pass only permissions, provider authority, and
effects the user supplied. Success requires `COMPLETED_VERIFIED` and readable
artifacts. Report blocked and no-progress outcomes honestly.
