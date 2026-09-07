# Fixes, adjustments, and the hardened fork

Companion to `CODE-REVIEW-2026-09-07.md`. That document says what is wrong
and proves it by execution. This one says what to change, in what order, how
each change is verified, and how the work is organized so that eight groups
can proceed at once without touching each other's files.

Branch: `fork/hardened-learning`, cut from `main` at `cc6117f`. The branch
`overnight/opencode-step-instances` (ten commits of composed OpenCode steps,
multi-path solving, and provisioning) is not folded in yet: it conflicts with
`main` in seven files. Folding it is listed as follow-up item F1, not done
silently and not dropped silently.

## Ground rules for this work

1. Nothing is edited in `/home/username/loop-engine`. A `codex --yolo`
   process has been committing there unattended for over 23 hours. All work
   happens in worktrees under the session scratch directory.
2. Every fix carries a probe that fails before and passes after. Twenty-nine
   of the review's findings were reproduced by running code; the probe
   scripts survive at
   `/tmp/claude-1000/-home-username-loop-engine/6d8b36e1-c0bf-4f98-a765-7be966b7d9c2/scratchpad/`
   and are the regression tests for this fork.
3. A group edits only the files listed for it. Cross-file hooks (for example
   the ledger authorship hook) are integrated by the coordinator after the
   groups land.
4. The gate order is the one CI runs: self-test, conformance, devtools
   self-test, hardcoding delta with `--fail-on-new high`, vale on Markdown.
   The fork is not called done until all five pass locally on the fork tip.
5. Local gate counts are reported next to the CI run they predict, never in
   place of it. Forty-five consecutive red pushes were each described
   locally as green.

## Findings to fixes

| ID | Sev | Fix | Files | Verified by | Group |
|---|---|---|---|---|---|
| R1 | high | Remove the credential literal at `openai_responses_client.py:582`; allowlist the 51 URL literals in `docs/research/*.json` as documentation, not code; classify the 192 closed-vocabulary literals and 65 provider bindings and either allowlist with a reason or move to configuration; re-baseline only what is justified in writing | `core/openai_responses_client.py`, `devtools/hardcoding-allowlist.yaml`, `devtools/hardcoding-ci-baseline.json` | hardcoding delta gate exits 0 with `--fail-on-new high` | gates |
| C10 | low | Live-demo checks measure wall time; measure user CPU time with `getrusage`, or mark them advisory when load average exceeds core count | `code_nodes/live_run_demo.py` | 6 of 6 at load average above 30 | gates |
| W2 | high | `terminal()` and `recover_expired()` wrap read-then-insert in `BEGIN IMMEDIATE`; a unique-constraint violation rolls back and raises a typed `ReactiveSchedulerError`; the connection is usable afterward | `core/reactive_scheduler.py` | `probe_g_natural_race.py`: no wedged connection after 200 rounds | reactive-scheduler |
| W4 | medium | `ActivationTerminalRequest` carries `worker_id`; `_require_fence` binds lease, token, and claimant; a terminal from a non-claimant is refused by name | `core/reactive_scheduler.py`, `loop/reactive_activation.py` | `probe_b_race.py` forged terminal refused; owner's real terminal accepted | reactive-scheduler |
| W6 | medium | Read `PersistenceMode.DURABLE_SERIES` from the series profile; a durable series refuses to publish COMPLETED without a persisted history | `core/reactive_scheduler.py` or `core/reactive_worker.py` (one owner, stated in the diff) | new check: durable series with `not_persisted` history is refused | reactive-scheduler |
| W3 | medium | The worker calls `heartbeat` at half the lease interval while a handler runs | `core/reactive_worker.py` | `probe_a_lease.py`: handler outliving `lease_seconds` is not dead-lettered | reactive-worker |
| W5 | medium | `start()` moves inside the guarded region of `run_once`; `run_many` gathers with `return_exceptions=True` and records every sibling outcome | `core/reactive_worker.py` | one stale fence, siblings still reported | reactive-worker |
| W7, W9, W10 | low | Post-cancel model usage reaches the canonical projection; `cancel()` on a terminal Loop is refused instead of appended; canceled and dead-letter records carry true status | `core/reactive_worker.py`, `core/run_history.py` (projection only) | `probe_d_cancel.py`, `probe_c_history.py` | reactive-worker |
| B1 | high | `LoopConfig.max_non_accepted_iterations`, default 25, counts every iteration under `accepted_success` that did not produce an accepted success; reaching it terminates `no_progress` with the count in the event; `None` must be asked for explicitly | `loop/recursive_loop.py` | `probe_loop_runtime.py` b2: varying failure text stops at 25, not 3,001 | loop-runtime |
| B2 | medium | Admission catches `RecursionError` and records `invalid_json_value`; the run repairs instead of aborting | `core/model_response_admission.py` | `probe_admission_kernel.py`: 1,000-deep response is refused typed | loop-runtime |
| B4 | medium | Kernel structural boundaries are their own event kind (`kernel_boundary`), never `run_step accepted=True` | `loop/kernel_runtime.py` | ledger filter on `run_step and accepted` returns zero synthetic rows | loop-runtime |
| B6 | low | Duck-typed contract objects are refused or coerced with a recorded coercion, same as `LoopContract` | `loop/recursive_loop.py`, `loop/loop_definition.py` | new check | loop-runtime |
| W1 | high | Event authorship: the ledger holds a per-run key; `record()` computes an HMAC over the event body under that key; handlers receive a recorder facade that can emit only the event kinds registered for its loop id; `RunHistory.append` refuses an event whose authorship tag does not verify; `_read_verified_history` verifies every tag | `core/run_history.py` (new `run_history_authorship.py`), hooks in `loop/recursive_loop.py` and `core/reactive_worker.py` integrated by the coordinator | `probe_e_forge.py`: forged `verify`, `model_invocation`, and `terminal` are refused | run-history-authorship |
| B3 | medium | Reference delivery materializes the value for the consumer, or the frame refuses reference delivery until a resolver is wired; `information_materialized` is recorded only when it happened | `core/adaptive_practitioner_bindings.py`, `core/adaptive_practitioner_scope.py` | `probe_frame.py`, `probe_public.py` | bindings |
| B5 | medium | `InformationAccessRequest.maximum_bytes` defaults to 64 KB; `_inline_snapshot` caps and states the truncation; oversize values are delivered by reference | same | 200,000-integer producer result yields a bounded consumer packet | bindings |
| B7 | low | A non-binding error from `frame.register` keeps the successful spawned summary and adds the error as its own record | `core/adaptive_practitioner_scope.py` | new check | bindings |
| C1 | high | The prompt is the contract. Fix the cases: `grid_path_cost` grids use periods; `calendar_slots` rejects `24:00`; `state_machine` accepts `01`. Re-seal as population version 2 with a new digest; keep version 1 under `docs/evidence/` as the record of what ran | `novel_task_population.py` | `novel_runs/*_per_prompt/probe.py` pass; `*_per_cases` fail | campaign |
| C2, C5 | high, medium | References are rewritten from the prompts by an author who has not read the cases (a separate agent, given prompts only); the evaluator control runs the campaign evaluator against a wrong solution; `prompt_entrypoint_mismatches` is populated and part of the exit code; the three reference deviations are fixed | `novel_task_offline_check.py` | offline check fails on version 1 population, passes on version 2 | campaign |
| C3 | medium | `matrix_spiral` gains a visit-order case; `poly_hash` gains a real non-ASCII code point; `word_square` gains a positive 3 by 3 case and the misnamed duplicate is renamed | `novel_task_population.py` | `flat_sum_no_spiral` now fails | campaign |
| C4 | medium | The campaign report states the `word_square` invalidation as prompt ambiguity plus an inconsistent reference; the 500-input stress claim is removed or recorded | `docs/evidence/novel-campaign-20260906/*.md` | text review | campaign |
| C6 | medium | `campaign_manifest()` digests `novel_task_population.py` and `novel_task_campaign.py`; the frozen-runner check runs per task | `novel_task_campaign.py` | manifest carries both digests; a changed runner fails the run | campaign |
| C7 | medium | The audit takes its root as an argument, runs candidate code inside the pinned image, and its generators emit invalid inputs | `novel_task_audit.py` | audit runs against a temp root; invalid-input branch executes | campaign |
| C8 | medium | Per-task evidence is copied off tmpfs into `docs/evidence/` or the runs directory | `novel_task_campaign.py` | evidence path is not under `/tmp` | campaign |
| C9 | low | The population docstring says "textbook problems with contract twists"; README entry; unit tests for the four modules | same four modules, `README.md` | tests run | campaign |
| H1 | medium | The host schema and the callback agree on bytes; an oversize payload returns a typed refusal; unknown outcome gets a reconciliation call that re-reads the artifact digest | `core/host_runtime.py`, `examples/.../generalization_probe.py` | `probe_g_unknown_outcome.py`: run continues after a 65,536 `é` payload | host-boundary |
| H2 | low | `feedback()` caps observed values; `probe-input.json` is not readable by candidate code, or its label becomes `candidate_visible` | `generalization_probe.py` | `probe_h_argument_exfil.py`: arguments do not reach the record | host-boundary |
| H3 | low | The Python bridge handles `harness_text` and counts it | `opencode_gateway_bridge.py` | `probe_e_bridge.py`: no dropped frames | host-boundary |
| H4 | low | Model-visible records carry workspace-relative paths | `core/host_runtime.py` | `probe_c_leakage.py` | host-boundary |

## Design notes for the four hard ones

### W1, event authorship

Three reviews have recorded this. The digest chain proves order, not
authorship. The fix has two halves.

The ledger owns a per-run key, created at run start and never written to
Run History or any model-visible record. `record()` computes
`HMAC-SHA256(key, canonical_body)` and stores it as `authorship_tag`. A
handler does not see the ledger; it sees a `RecorderFacade` bound to its
loop id, whose `record()` refuses any event kind not registered for that
loop id in the definition, and refuses `loop_id` values other than its own.
`RunHistory.append` requires the tag and verifies it. `_read_verified_history`
verifies every tag against the key recovered from the runtime, not from the
file.

What this closes: a handler cannot append `verify`, `model_invocation`, or
`terminal` for a loop it does not own, and cannot append an event kind its
loop was not defined to emit. What it does not close: a handler that owns a
loop can still lie inside an event kind it is allowed to emit. That is the
model's own output and is the verification problem, not the authorship one.

### B1, iteration ceiling

`identical_failures_before_stop` stops churn only when the failure text
repeats byte for byte. A counter or timestamp in the output defeats it. The
ceiling that matches the exit condition is a count of iterations that did
not produce an accepted success, whatever their text. Default 25. The event
that terminates says both numbers: the ceiling and how many identical
failures were seen, so a reader can tell "stuck repeating" from "kept
trying different things and none worked".

### W2, the race

`terminal()` reads the current revision, then inserts revision N+1.
`recover_expired()` on a peer connection does the same for the same row.
SQLite serializes the writes but not the read-then-write pair. `BEGIN
IMMEDIATE` at the start of each takes the write lock before the read, so the
second caller waits and then reads the new revision. An `IntegrityError`
that still arrives is rolled back and raised as `ReactiveSchedulerError`
with the activation id, and the connection is left outside any transaction.

### C1, fix the cases, not the prompts

The prompt is what the model reads. When the prompt and the hidden cases
disagree, changing the prompt to match the cases rewards the accepted
solutions after the fact. The cases move. The old population stays on disk
as version 1 with its digest, because the campaign that ran against it is a
real record and the report about it must stay checkable.

## Learning across runs

The campaign measured zero-learning solving by construction: each task ran
in its own `runs_dir`, so no stage record from one task was visible to any
other. The instruments exist and fired (option selection counts, region
statistics, 266 stage records, tuning decisions). They were never read
across tasks.

Arm B is one flag in the campaign runner: `--shared-runs-dir`. Run the
population twice into one directory. Compare pass two against pass one on
calls, tokens, and observations per task. This is the cheapest evidence that
within-region reuse does anything. Arms C through E (dependency bindings,
prompt-experiment variants with a control arm, a second sealed population
by an author who never sees the references) follow only if Arm B moves the
numbers.

Arm B must not run before B1, W1, and C1 are fixed. A learner fed by an
unbounded loop, forgeable events, and contradictory oracles learns noise.

## The fork process

Eight groups, one worktree each, cut from `fork/hardened-learning`:

`reactive-scheduler`, `reactive-worker`, `loop-runtime`,
`run-history-authorship`, `campaign`, `host-boundary`, `gates`, `bindings`.

Each group: run its probes red on the untouched tree; implement; extend the
module's `self_test()`; run the probes green; return a structured report
(files changed, probes before and after, self-test counts, what was left
undone). Six adversarial verifiers then re-run the high-severity probes in
the finished worktrees without reading the implementer's report first.

Integration order: gates first (so every later measurement runs against a
gate that can pass), then loop-runtime, reactive-scheduler,
reactive-worker, bindings, host-boundary, campaign, and run-history-
authorship last because its hooks touch two other groups' files. After each
merge: self-test and conformance. After all: the full CI gate list, then the
six high probes once more on the integrated tip.

## Follow-ups, not in this fork

- F1: fold `overnight/opencode-step-instances` (seven conflicting files, all
  in the adaptive practitioner and generated-project modules).
- F2: copy the 93 MB of campaign evidence off tmpfs before it is lost.
- F3: run vale locally before every push; 43 of the 45 red pushes failed
  the documentation job, most on dashes.
- F4: two extra branches on origin against the main-only rule (R2).
