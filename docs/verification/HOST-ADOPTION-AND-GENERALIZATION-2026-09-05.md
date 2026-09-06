# Host adoption and generalization limits

Loop Engine repaired a seeded JavaScript project through a caller's registered
host operations. It read the source, received failing repository tests, changed
one expression, and passed the same protected tests. The completed run used
two passes and 11 real model calls. No caller supplied `TaskFeedback`.

This demonstrates one embedding path over a populated project. The task was
a deliberately defective example, so it does not establish performance on
an unseen task population. The [structured evidence](../evidence/host-adoption-and-generalization-2026-09-05.json)
preserves both launches and references their exact saved records.

## Host execution and acceptance

The [embedding guide](../guides/embedding-loop-engine.md) describes the public
API and full Loop classification. `SolveRequest.host_runtime` accepts a typed
`HostRuntimeBinding` backed by the existing Capability Directory and Custom
Plugins port. The [architecture decision](../architecture/ADR-HOST-OWNED-EXECUTION.md)
defines the execution and trust boundaries.

The model selects registered host operations. Each invocation checks its
schemas, frozen registration, state precondition, and exact host approval.
Host permission names apply only to the selected host operations; they do not
enable the core file or command permissions. The host also grants model access
to its output explicitly. Omitted disclosure authority refuses the binding.

A separate Practitioner verifier runs the host's registered gates. A passed
observation can support another pass, while final success requires an issued
report with `task_complete: true` for the current task and state. The result
keeps its `host_operation_result/v1` contract. Neither live launch created a
generated Python project.

## Live JavaScript repair

Both launches used `ollama_cloud / cloud.default / deepseek-v4-flash:0731` on
the same seeded example. The first stopped before a host callback because
decision admission incorrectly applied core permissions to a scoped host
inspection request. Its failure remains in the saved history.

| Launch | Outcome | Physical model calls | Seconds | Host operations |
|---|---|---:|---:|---:|
| `adaptive-7da6dce947a06efcb2bace8a` | `AUTHORITY_REQUIRED` | 2 | 24.134 | 0 |
| `adaptive-b7e5a405ca3892000d7ddb05` | `COMPLETED_VERIFIED` | 11 | 130.651 | 2 |

After the scoped permission correction, the engine inspected `clamp.mjs`.
The host's first `npm test` run passed one test group and failed two, with
observed values `0` where the tests expected `5` and `10`. The recorded failure
entered the next planning packet through normal runtime state. Its
`TaskFeedback` list remained empty.

The model requested this single expression change:

```diff
- return Math.max(minimum, Math.min(minimum, value));
+ return Math.max(minimum, Math.min(maximum, value));
```

The host applied it with the expected source digest. It then ran the unchanged
tests in the pinned Node Docker image with a read-only workspace and no
network. All three test groups passed, with zero failures or skipped groups.
The passing suite evaluated 12 assertions covering in-range values, outer
regions, boundaries, equal bounds, and the declared error cases.

| File | SHA-256 after the repair |
|---|---|
| `clamp.mjs` | `cc0c72d08fe855b2bec2ae68cb2cb66a3688b028e23784265d3cfac1d127f52d` |
| Protected `test.mjs` | `62f9099ef17667642b74f24e7771fa82892ae550ffe1f59561e20d9f2164f4f9` |
| Protected `package.json` | `f654fc7287ab0458252efefac32b59e9b07ce1060b75425ea2f21c3039e085ab` |

Both protected files match the original example bytes. The successful run
reported 217,833 input and 28,610 output tokens, totaling 246,443, with complete
accounting. Invoiced cost remains unknown. No call, pass, total-token, or
monetary ceiling was added by the example; provider output capacity and host
effect controls still applied.

The canonical saved-run verifier confirms intact histories and bound outcomes
for both launches: 157 events for the failure and 995 for the success. The
successful product digest is
`91e938f5c42efc73e2d69319a02f8a9a48757acd0da23b8feabe1f73c6df79ea`.
Embedded history snapshots predate final outcome binding and still say
unbound. Use canonical saved-run verification to check the final state.

The [reproduction example](../../examples/25_host_runtime/README.md) includes
the original source, protected tests, host binding, explicit model/disclosure
flags, and pinned image. It creates a fresh copy of the project and never
overwrites an earlier run directory. Reproduction makes new provider calls;
the saved results above are sufficient for inspecting this checkpoint.

## Source admission and offline verification

The built-in source reader admits UTF-8 text by content instead of a
programming-language suffix allowlist. It records protected, binary,
unsupported, unreadable, and pruned inputs as exclusions. Selected bodies
still need disclosure authority and complete-text validation. This broadens
source inspection without adding an executor for every language or format.

The frozen verification summary passed 3,120/3,120 source tests,
3,075/3,075 applicable clean-base-wheel tests, and 27/27 conformance gates in
each environment. Build, offline installation, dependency checks, CLI help,
and all 483 runtime file comparisons passed. The clean installation ran
Python 3.14.4 and explicitly omitted seven optional adapter families.
These checks made no provider calls.

The exact summary and its digest are referenced in the structured evidence.
Its runtime hashes match the current source at this checkpoint. The source
conformance phase refreshed the generated `architecture_conformance.json`;
the source test phase recorded no file changes. The report exports compact
projections and source record identities, not full runtime hash maps or raw
private prompts.

## Limits

The host is trusted for callback behavior, snapshot coverage, isolation, and
gate meaning. The engine checks the host's declared identities and approvals;
it does not prove arbitrary callbacks safe or repository tests complete.
The JavaScript example protects its gates and confines the editable file.
Other hosts need their own policies.

This checkpoint does not demonstrate Git branch automation, a remote
TypeScript SDK, automatic capability qualification or promotion, or durable
reconciliation of unknown external effects. It also makes no local-model or
held-out generalization claim. A fixed test suite passing after one repair is
the demonstrated result.

This host/source checkpoint made zero new Kaggle downloads, submissions, or
grades. Earlier campaigns and subsequent dataset/model evaluations have
separate populations and records. The separate CI hardcoding audit remains
outside these conformance results.
