---
name: loop-engine-run
description: Run a user task through Loop Engine when the user asks Loop Engine to build, solve, execute, verify, or resume work.
---

# Loop Engine Run

Preserve the original task in a file for long requests, then invoke
`loop-engine solve --file <path>` with an explicit workspace, run directory,
interaction mode, provider route, model-call ceiling, and token ceiling.

Use `loop-engine task build` only when the user asks to structure or review a
task without executing it.

Do not infer permission for provider calls, file effects, commits, pushes, or
publication. Pass only authority the user supplied. Treat a verified terminal
result as success. Preserve and report blocked, capability-gap, and
no-progress results honestly.
