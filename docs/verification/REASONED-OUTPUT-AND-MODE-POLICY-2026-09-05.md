# Reasoned output, shared modes, and accounting repairs

This checkpoint changes shared Loop, model-session, output-allocation and
frontier boundaries. It introduces no industry controller or second runtime.
The [research follow-up](../research/ADAPTIVE-QUESTIONS-COMPILATION-AND-CAPABILITY-RESEARCH-2026-09-05.md)
supplies questions, source limitations, and proposed experiments. Those
experiments are not all implemented by this checkpoint.

## Scope and ownership

Work continued on `main` from
`d121379773e46a1255fd3e86436d907dc2a0b4d0`, preserving the preceding local
record-access and harness repairs. The user subsequently authorized committing
and pushing the verified changes. The separate showcase worktree and existing
operator processes were not changed. Provider credentials were not exposed.

## Reasoning and configuration boundaries

Every executable vertex remains `Loop`. The shared mode-policy view exposes
deterministic, hybrid and non-deterministic modes even when a profile permits
only one. Preference order, profile restrictions, installed executors and
model/effect authority are separate. Missing or infeasible executors now
produce typed refusal, and a fallback cannot report a different mode as though
it executed the requested one.

New configuration crosses boundaries as class objects: `LoopModePolicy`,
`ModelOutputAllocation`, `TokenBoundRequest` and `ProviderTokenBound`. Existing
`LoopConfig`, `ModelInvocationRequest` and `HarnessServices` remain the enclosing
contracts. This is not a claim that every legacy constructor has been migrated.
The allocation decision is explained in the
[output-allocation ADR](../architecture/ADR-REASONED-OUTPUT-ALLOCATION.md).

Provider capacity is a sourced fact. The selected allowance is a separate
decision. Without an allocation the gateway requests full known capacity.
An explicit typed allocation carries exact provider/model/route identity,
capacity snapshot, chosen allowance, decision reference and reason. The gateway
refuses a changed identity, stale capacity or contradictory scalar hint.
Unknown capacity cannot be replaced by an arbitrary guessed ceiling.

The gateway no longer clips output to an internal 512-token floor or remaining
context room. Runtime settings no longer take a maximum across heterogeneous
route capacities. CLI total-token authority no longer filters OpenRouter's
output-capacity catalog. Native wire fields still contain numbers because
provider APIs require them; those numbers come from capacity or allocation.

The existing recovery seam previously asked for a nonexistent `invoke_raw`
method and therefore could not reach the actual typed model session. It now
makes a counted reasoning call under the current Practitioner and the same
budget. It receives bounded task/contract context, recent failure and completion
facts, capacity evidence and history references. An admitted output adjustment
becomes `ModelOutputAllocation` on the next retry of that same responsibility.
The transport-error table no longer chooses retries before consulting reasoning;
the existing outer iteration guard remains a safety bound.

Two prompt-sensitive offline histories select different allowances and the
counted retry receives those exact values. A separate 33-check native-builder
suite covers full defaults, allocations, reservations, source/route mismatches,
and scalar conflicts for Ollama, Mistral and OpenRouter with sockets disabled.
It makes 15 intercepted HTTP requests and zero live provider calls. Dynamic
OpenRouter use must pin the same capability snapshot for selection and dispatch;
changed catalog evidence requires a new decision, not relaxed equality checks.

## Budget and failure paths

| Path | Repair | Limit |
|---|---|---|
| Pre-dispatch total budget | Require an exact-request, source-backed input/output bound before dispatch | No production tokenizer/wire-bound resolver is qualified yet; bounded production calls may refuse `token_bound_unavailable`. |
| Retries and failover | Recompute the remaining allowance for each physical request | No silent budget replenishment or provider-output reduction. |
| Concurrent session calls | Single-flight execution prevents overlapping use of the same allowance | This first implementation refuses an overlapping invocation; it is not a distributed reservation service. |
| Mutable accounting results | Private counters do not depend on the public result list | Host code remains trusted; these are not OS isolation boundaries. |
| Provider callback exception | Preserve a physical invocation with unknown usage | An exception does not prove zero spending. |
| Cancellation or outer orchestration failure | Mark accounting uncertain before releasing the session; preserve cancellation propagation | No automatic refund or next bounded dispatch. |
| Bound violation | Preserve actual reported usage, reject the attempt, and stop | A local declaration cannot prevent a provider from violating its contract. |
| Incomplete response | Reject contradictory completion/error/limit flags even when `ok=True` | Output admission and independent task verification remain separate. |
| Hidden adapter retries | Refuse reported multiplicity outside the one-attempt contract | Aggregate token usage stays unknown when per-attempt accounting is missing. |
| Exact model authority | A request cannot broaden the session's model allowlist; matching is exact | No implicit family or substring authorization. |

The saved historical 30,130-token remainder with a 65,536-token output request
is now a zero-dispatch refusal in the regression fixture. This closes that
unsafe dispatch path. It does not qualify a real provider's input bound or
prove successful live task execution.

## Frontier truth

The frontier remains a passive projection. Disappearing or renamed questions
no longer become answered without evidence. Unknown, malformed, contradictory,
or unbound verdicts cannot fabricate work completion. Supplied verification
records remain advisory references until a future trusted resolver can
authenticate complete action/execution/outcome lineage.

Independent review found that a provisional subject-only fix still confused
repeated action IDs and verifier pass numbers. That design was rejected. The
committed design does not create a second verification authority inside the
projection. It preserves unresolved work and the source references.

## Evidence classification

Focused checks use deterministic fixtures, including intercepted native HTTP
request builders. Interception verifies request serialization and reservation
binding, not provider connectivity or model quality. No live provider or
unseen-task experiment was performed in this checkpoint. Historical failed
Kaggle-shaped attempts remain failures, not completions or training successes.

The source and clean-wheel verification record for this checkpoint is kept
separately from earlier reports. Historical counts in the storage and harness
reports must not be presented as fresh counts for this changed checkout.

Final checks: **2,805/2,805** source tests and **2,760/2,760** applicable base-wheel
tests passed, with zero provider calls. Source and wheel conformance each passed
**27/27**. All **475** runtime file bodies matched both archives and the installed
wheel. Base installation explicitly did not test optional DuckDB, MCP,
model2vec, NumPy, OpenTelemetry SDK, pandas or scikit-learn adapters.

The [verification artifact](../evidence/reasoned-output-mode-verification-2026-09-05.json)
records exact commands, source snapshots, archive hashes, output hashes, and
earlier failures. Two old fixture handlers did not honor the requested fallback
mode; they were corrected without weakening mode checks. One retired term in
a helper docstring failed the naming scan and was corrected. No test was
excluded. Final documentation was completed separately from runtime-body checks.

The structured local handoff was written through `loop-engine records` as
`session.reasoned-output-mode-20260905`, revision 1, artifact digest
`b5229870397d95a4c6f432b3d23aae299b6f469883c54775c1f27a297e2aae5d`.
It remains candidate reporting data, not promotion authority. Its revision
chain is durable; the CLI explicitly reports that execution Run History is
not separately persisted by that tool.

## Remaining work

The current product-path assisted/fresh gate remains open. It still needs
immutable source consumption, canonical preallocated assignments, exact base
packet comparison, fresh-arm isolation, an independent evaluator and a
Run History-to-projection bridge. A completed provider key setup is not that
proof, and archived run budgets are not new run authority.

Further work includes production token-bound qualification, explicit capacity
refresh and expiry, arbitrary historical-log query/materialization, first-call
allocation learning, route-changing recovery, semantic context replanning,
distributed reservations, complete legacy parameter-object migration, and
the wider research experiments. No claim of AGI or exhaustive defect removal
is made.
