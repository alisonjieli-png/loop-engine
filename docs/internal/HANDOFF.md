# Loop Engine maintainer handoff

This is a stable pointer, not a live checkout report.

Use the [coding-agent start page](../context/CODEX-START-HERE.md) first. For
broad continued development, load only the
[universal solver continuation brief](../prompts/LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md).
Do not combine it with historical prompts.

Volatile state belongs in an immutable generated packet that conforms to
[`session_handoff/v1`](../contracts/session-handoff.schema.json). A packet must
record the full source revision, worktree digests, explicit ownership claims,
test records, evidence limits, active objective, and next work. It is stale
when its HEAD or worktree snapshot no longer matches. This page does not claim
that such a packet has been generated.

Do not infer ownership from this file, a process ID, or a file timestamp.
Preserve every dirty path whose owner is not supported by an explicit claim.

Use the [main README](../../README.md) for current installation and
verification commands. Do not copy commands or adapter-availability claims
into this page because those details change with the package.

For a GPT-6 Astra consumer, read the dated
[compatibility note](../context/GPT-6-ASTRA-READINESS-2026-09-04.md). Loop
Engine remains model-neutral, and model access remains unproven until an
authorized provider probe succeeds.

For work on long-horizon skills, execution state, recursive inference,
recurrent models, or test-time memory, read the dated
[primary-source research review](../research/LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md).
