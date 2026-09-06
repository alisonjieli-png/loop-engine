# Repair a host-owned JavaScript project

This example lets Loop Engine reason over an existing JavaScript project.
The host exposes inspection and digest-checked replacement of `clamp.mjs`.
The model cannot edit the host's test file or package configuration.
Verification uses fixed `npm test` commands in a pinned, read-only Node Docker
workspace with no network.

The source begins with a deliberate bug. The task and tests are example data,
not a special solver route. See [the embedding API](../../docs/guides/embedding-loop-engine.md)
for the general contract and host responsibilities.

For a different use of the same binding, see the
[tabular model portfolio](TABULAR-PORTFOLIO.md). It trains and evaluates
engine-selected model configurations on supplied datasets.

The [five-shape regression probe](GENERALIZATION-PROBE.md) uses one host
interface for utilities, CSV aggregation, scheduling, HTML delivery, and
existing-source repair. It preserves failed attempts and later invalidations.

The [exported-ticket pilot](EXPORTED-TICKET-PILOT.md) adds an immutable local
ticket, an independent completion audit, and a review bundle. It does not
connect to Jira or publish a branch. The [competition preparation guide](COMPETITION-PREDICTION.md)
covers the narrower CSV download, refit, and submission-file helpers.

## Run

From the repository root, install Loop Engine and Docker, configure the chosen
provider, and pull the exact runtime image:

```bash
docker pull node@sha256:4d676821dff059fd00d277ee4261ef34ea712317fed0737c03941481b5760c96

PYTHONPATH=src python examples/25_host_runtime/run.py \
  --work-dir ./host-example-output \
  --authorize-model-calls \
  --allow-source-to-model
```

The default model route is `cloud.default` with
`deepseek-v4-flash:0731`. The gateway still requires configured provider
credentials and a source-backed output capacity. The flags authorize live
model use and sharing this fixture's source and observations. No call-count,
pass-count, total-token, or monetary ceiling is added by the example.

The work directory must not exist. Setup creates a populated copy of the
example project there; the engine then uses host callbacks to work on that
copy. It does not copy the project into a generated Python attempt directory.
Existing output is never overwritten by another example launch.

## Inspect the outcome

A completed run returns `COMPLETED_VERIFIED` with a
`host_operation_result/v1` result. Its saved Run History contains the host
observations and verification reports. Inspect the repaired module in
`host-example-output/project/clamp.mjs` and confirm the protected files stayed
unchanged.

The demonstrated live run used two passes and 11 real model calls. It received
two failing test groups from the host, repaired the source, and passed the same
three test groups. No `TaskFeedback` or generated Python project was supplied.
This is a seeded adoption example, not a held-out benchmark.

The host adapter itself is trusted code. Its fixed editable-file schema and
effect authorizer define the scope. Do not reuse the example's approve callback
with an unrestricted operation catalog. A production host must supply its own
state, privacy, authorization, sandbox, idempotency, and verification policies.

This example does not create or push a Git branch. A Git-aware host can expose
such a capability through the same interface, but must own the exact Git rules
and external-effect approvals. A TypeScript daemon needs an explicit bridge to
this Python API; no remote transport SDK is provided here.
