# Per-step harness recovery, 2026-09-12

## Result and scope

One fresh live cognitive step recovered from a rejected Pi response by
launching OpenCode. OpenCode produced the required JSON object. Both used the
configured Tactical `gemma-4-coding-abliterated` route. No provider or harness
answer was replaced with a fixture.

This proves one structured-response recovery, not improved task quality or a
full-system benchmark. The experiment did not ask either harness to solve a
Kaggle task. It did not compare the complete context, skills, tools, and
intelligence matrix.

The implemented policy and its limits are in
[Per-step harness recovery](../components/core-architecture/HARNESS-FALLBACK.md).
The runtime remains `Loop`. Harnesses are registered adapters used by Loops.

## Live attempts, including failures

The study is stored locally at
`.loop-engine-dev/systematic-20260912-Ly6MoT/`.
`harness-recovery-review.duckdb` holds the derived review records. Per-attempt
records are in `fallback-diagnostics/` and the named `preflight/` directory.
The table includes all four recovery diagnostics at this checkpoint, not a
selected success rate.

| Attempt | Observed outcome | Physical model calls |
|---|---|---:|
| `pi-36eebc5872` | Pi returned a response rejected as invalid JSON. No fallback was configured. | 1 |
| `live-chain-c7412f7174` | Pi was rejected; OpenCode was admitted. The outer experiment wrapper then failed an accounting invariant. Overall attempt failed. | 2 |
| `live-chain-70c28bc6ee` | Pi was rejected; OpenCode was admitted; the enclosing cognitive step completed. Codex was not launched after success. | 2 |
| `preflight-opencode-d48cefa4f0` | OpenCode was rejected, then Pi was rejected, then Codex was rejected. The configured order was exhausted and the step failed. | 3 |

The wrapper defect was reporting the sum of delegated physical calls as the
outer Loop's own call count. The canonical runtime correctly refused two
physical calls attributed to one iteration. The wrapper now leaves those
counts with their existing gateway Loops. A regression test exercises two
fixture-gateway calls through the application and checks the saved
history for exactly two model-invocation records.

The successful attempt used Pi `0.85.1` and OpenCode `1.17.9`. Codex `0.153.4`
was the unused third alternative. Its invocation took 67.298 seconds,
excluding session configuration. The two provider calls reported 963 input
tokens and 64 output tokens in total. Token and call accounting were complete
for this diagnostic. Cost is unknown.

The saved successful run is
`fallback-diagnostics/live-chain-70c28bc6ee/execution/runs/semantic-50aecfa724d948aca4b1b7e81d4d62dd/`.
Its 70-event chain verifies intact. Playback produces 37 lines. It has no
bound product outcome, as expected for a response-admission diagnostic.

These attempts used different fresh random markers and included an intervening
wrapper correction. The last also required a readiness field. They are not
repeated samples from one frozen treatment. Switching harnesses does not
guarantee that one will meet the contract.

## Implemented behavior

`HarnessFallbackPolicy` selects a finite order of explicitly registered
adapters and the failure categories that permit switching. Each attempt gets
its own canonical Loop, request identity, and workspace. The original
semantic packet and system context remain bound. Later attempts receive small
typed failure observations, not an inherited conversation or working tree.

The model route and output allocation stay under the existing authority.
Calls, tokens, and elapsed time are shared across attempts. Unknown accounting,
possible tool effects, provider failures, exhausted budgets, and unclassified
failures do not authorize a switch. No native harness tools are enabled by
this policy.

An optional `ModelInvocationRequest.response_expectation` binds an explicit
JSON Schema to the exact prompt, system text, and semantic operation before
dispatch. A rejected response can trigger recovery. A structurally admitted
response remains a proposal, not an accepted task solution.

The process-config loader supports different orders and separately registered
forks. A development command exposes the policy for another authorized live
preflight. The default single-harness behavior is preserved.

## Verification status

- The current focused source checks pass 201/201, including 42 fallback
  controls. They also prove that unexpected effects block subsequent calls in
  the same session, separately from token accounting.
- The embodiment application suite passed 21/21, including the new outer-step
  accounting regression and strict test-result summary checks.
- The corrected source scanner checked 469 Python files with no violations.
- Markdown structure checks passed for all four changed component, contract,
  and verification pages. Their local link targets resolve.
- A wheel built and installed in a separate Python 3.10 environment with base
  dependencies and DuckDB. The first frozen snapshot failed two conformance
  checks: a short test-module docstring and a test helper not marked as a
  self-test for the resource-access scanner. Both were corrected in source
  without changing a baseline or exemption list. Its full suite then stopped
  because the long temporary path exceeded the Unix socket path limit. The
  corrected wheel in `qa-2ScKkB/` passes all 27 conformance gates and its 81
  focused installed checks.

The full installed suite completed and returned 3,788 results. Strict counting
finds 3,785 Boolean passes, two failures, and one malformed result. Both failures
report the same stale ontology index. The malformed result is an existing test
whose `passed` field contains a nonempty repair hint instead of a Boolean.
The package aggregator counts that string as true and reports 3,786 passes.
The experiment's summary helper originally tried to add it as a number and
failed after saving the complete suite results. That helper is corrected and
has a regression test. The original report remains saved.

The stale index names `core.context.practitioner_portfolio` version `1.0.0`,
while the existing working-tree manifest declares `1.1.0` with a different
digest. The six catalog identities otherwise remain the same. This recovery
change did not edit those source records or regenerate their index. The
string-valued test also exists at the starting HEAD revision. These findings
remain open, so the whole repository is not reported green.

The strict summary is `qa-2ScKkB/strict-self-test-summary.json`, generated through
DuckDB. The base-install run did not exercise optional adapters requiring MCP,
Model2Vec, NumPy, OpenTelemetry SDK, pandas, or scikit-learn.

## Open work

Recovery stops after the first admitted response. Producing a matrix of
candidate solutions is a separate use of the existing Canvas and reactive
output policies. This change does not implement learned harness ranking,
universal action-level semantic checks, or independent task acceptance.

The broader real-task baseline is separate. Native, OpenCode, and Codex
repeatedly returned decisions missing required fields or requesting permissions
outside the supplied core grant. All three were interrupted for diagnosis.
Native and OpenCode saved `CANCELLED`; Codex saved `BLOCKED_MATERIAL_INPUT`.
The recorded terminal codes are retained rather than rewritten to match the
operator intent. None passed development or sealed evaluation: 0/3.

The known physical-call subtotals were 27, 23, and 13 respectively. Because
interruption left accounting incomplete, total calls and costs remain unknown.
These attempts are not successful full-system benchmarks. Harness recovery
does not repair an overloaded shared contract by itself. The next controlled
task experiment needs the validated response checks at its actual decision
boundaries, with fixed-harness controls and a fresh sealed evaluation population.
