# Cognitive-act recovery checkpoint, 2026-09-12

## Scope

This change improves response checks, reorientation, and recovery-learning
capture through the existing Loop architecture. It preserves native execution,
custom registered harnesses, single-harness execution, and multi-harness
recovery. It adds no operational runtime type.

All live model calls in this checkpoint use Tactical Engineering with
`gemma-4-coding-abliterated`. Automatic provider failover is disabled. The
owner reported that Ollama usage should reset in about 30 hours; that is not a
verified reset time or an instruction to switch automatically.

The implementation is described in
[Cognitive-act recovery](../components/practitioner/COGNITIVE-ACT-RECOVERY.md).

## Changes

- `ModelResponseContract` binds an explicit schema and normalization policy
  before a response reaches its consumer. Example prose is not executable
  authority. Action, method, and recovery-panel responses use these contracts.
- Safe format normalization reuses the existing admission Loop. Missing
  fields are not invented. Rejected-response feedback remains separate from
  transport failure and carries exact response digests and safe diagnostics.
- A method is bound to the selected action and its capabilities. The current
  planner refuses an action with no execution capability when its method
  would otherwise be impossible. Dedicated control and delegation paths stay
  separate, and other custom Loop bodies can implement other behavior.
- Progress comparison no longer treats pass IDs, stage IDs, confidence, or
  rewritten explanations as evidence of progress. It checks non-adjacent
  repeats and supports an opt-in unchanged-material-evidence diagnosis.
- With that option enabled, an exhausted action or method response-repair
  cycle can enter the existing diagnosis, proposal, and adjudication panel
  before execution. The panel does not recursively recover its own failure.
- Optional learning assessment runs through
  `practitioner.self_improvement@1.0.0`. It retains a task-local disposition or
  an unvalidated `LearningBundle` using the existing artifact store. It cannot
  update active intelligence, approve itself, or claim task improvement.

The public request exposes `diagnose_unchanged_evidence` and
`capture_recovery_learning` separately. Both default to false and add no model,
tool, file, spending, or promotion authority.

## Reproduced defects

The old progress comparison hashed complete action and verification records.
A control with unchanged executable work but different occurrence IDs failed
to request diagnosis. The corrected control passes, while changed input,
artifact content, host state, and new evidence remain distinguishable.

The live task exposed an impossible handoff: both native and OpenCode-led
runs selected `COMPOSE_SOLUTION` with `required_capabilities: []`. The current
planner had no valid method response for that selection. The prerequisite is
now checked at action admission, rather than asking several harnesses to
produce an impossible response.

The two previously reported full-suite issues were also corrected. The
catalog index was regenerated from `UnifiedCatalog` through a DuckDB writer,
with an expected-digest check and exact canonical-byte verification. Its six
entries now reflect the existing version 1.1.0 context manifest. The existing
capability-rejection test now returns a Boolean instead of a nonempty string.
No historical result was regraded or overwritten to make these checks pass.

## Verification

The final checked wheel was installed into a separate Python 3.10 environment
with base dependencies and DuckDB:

| Check | Result |
|---|---:|
| Focused source checks | 242/242 pass |
| Embodiment application checks | 21/21 pass |
| Installed full suite | 3,839/3,839 pass |
| Installed conformance gates | 27/27 pass |
| Changed component and contract Markdown | No structure issues |

Optional suites requiring MCP, Model2Vec, NumPy, OpenTelemetry SDK, pandas, or
scikit-learn were not exercised by the base installation. This is not a claim
that every optional integration passed or that GitHub CI ran.

The full report is saved under
`.loop-engine-dev/cognitive-act-20260912-lRaw69/qa/`. The live runtime was copied
before each experiment so later code changes could not alter an active run.
The final wheel includes an import-only cleanup of the live snapshot's
801-line module; the current source satisfies the 800-line size gate.

One earlier check failed because the host temporary filesystem hit its quota.
Checks were repeated using a short, dedicated temporary path on the main
filesystem. No unrelated temporary directories were deleted.

## Live diagnostics

These are debugging runs on one previously attempted task, not six unseen
tasks or a full-system benchmark. The task uses density-normalized nearest
neighbors. Each study has 3,500 original training points, eight development
queries, and 48 newly generated sealed queries. Scalar and vector references
agree, and real isolated positive and negative evaluator controls pass.

Each study compares native gateway execution with an OpenCode-first policy
whose permitted alternatives are Pi and Codex. Every failed attempt remains
in its own directory. Held-out results are released only after the study's
candidate files are frozen. Model calls and passes have no configured total
ceiling; response-repair safeguards and cancellation remain explicit.

| Study suffix | Native outcome | OpenCode-first outcome |
|---|---|---|
| `4dvatL` | Canceled after recurring method failures; 69 known calls, total unknown | `NO_PROGRESS`; 21 calls |
| `y2dvqH` | `NO_PROGRESS`; 11 calls | `NO_PROGRESS`; 19 calls |
| `lRaw69` | Canceled after repeated recovery without a verified implementation; 51 known calls, total unknown | Interrupted after repeated recovery; saved `BLOCKED_MATERIAL_INPUT`; 31 known calls, total unknown |

All three studies scored 0/2 on sealed evaluation, or 0/6 runs in this
diagnostic set. They cover one task, not six distinct tasks. There are 202
known physical model calls across the six runs. The interrupted runs have
unknown totals; cost is unknown for every run. Operator cancellation intent
and saved terminal codes are preserved separately. No active run remains from
these three diagnostic studies.

The different studies changed code and query instances, so they cannot be
pooled into a matched performance claim. No saved success or failure was
silently replaced by a later attempt.

The `lRaw69` native run automatically entered diagnosis, generated recovery
options, adjudicated them, and attempted learning assessment. Six recovery
rounds were saved. One learning assessment failed; five returned
`ephemeral_task_only`. All five saved bundle references verify, and none
contains a reusable candidate. An earlier study also saved one task-local
learning assessment. The final OpenCode-led arm completed two more recovery
rounds and saved two task-local learning assessments. Across the studies,
nine recovery rounds attempted learning assessment: eight returned task-local
dispositions and one failed. Zero reusable candidates were produced or
promoted. These outcomes demonstrate the workflow, not successful learning or
a solved task.

The derived database and JSON summary are in
[`artifacts/cognitive-act-recovery-20260912-05JQhk`](../../artifacts/cognitive-act-recovery-20260912-05JQhk/).
Its `summarize.py` verifies saved event chains and learning artifact references
before rebuilding the DuckDB projection. Canonical histories remain unchanged.

## What remains open

The runtime is better at detecting and describing the failure. It has not yet
demonstrated that its selected recovery changes solve this task. Repeated
diagnosis is not measured improvement, and a task-local learning disposition
is not a reusable lesson.

The next work is to make recovery receive the exact failed contract and a
small executable set of repair choices, then verify that the chosen change
was actually applied. Smaller capability-selection assignments are a useful
next comparison against the large combined action record.

Cross-task transfer, learned harness ranking, a live multi-solution matrix,
verified graph export and replay, and the full task/configuration campaign
remain separate unproven objectives. No AGI or reinforcement-learning result
is claimed here.
