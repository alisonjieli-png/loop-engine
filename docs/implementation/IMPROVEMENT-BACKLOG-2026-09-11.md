# Improvement backlog, 2026-09-11

Source: one full day of measured harness, embodiment, and live-task work
(2026-09-10). Every item below was observed, not inferred. Items marked
DONE were completed by the opencode session; the rest are scoped for
Codex or a follow-up session. General rules for all packets: work only
in `/home/username/loop-engine`, verify branch/revision/dirty state and
concurrent writers first, preserve existing changes, smallest typed
extension at the authoritative boundary, verify inside Loop Engine
(`--self-test`, `--conformance`, module suites), never commit/push
without explicit authorization.

## P0: verified defects

### 0. Solution-canvas wave execution in the solve path (new)

- State: `execute_development_plan` (pipeline controller + wave steps +
  spawned atomic loops + retries + blocked-work honesty) is tested
  (5/5) but called only by its own checks. No solve path produces
  `PlanDefinition`s or `TaskLoopBinding`s, so multi-slice plans never
  execute as graphs. Per-action `run_compiled` fires rarely (3× seen).
- Work: (a) author PlanDefinitions from orient subproblems;
  (b) bind slices to capabilities; (c) invoke the wave executor from
  act when a plan exists; (d) join via integrate_commit.
- Pointers: `core/development_execution.py:172`,
  `core/development_planning.py:389`,
  `code_nodes/solution_compiler.py:198`.
- Acceptance: an offline 3-slice diamond plan executes with wave
  ordering + a retry, then one live campaign cell showing pipeline
  controller loops in its history.

### 1. Same-shape repetition guard across step invocations

- Symptom: practitioner burns 100/100 model calls in orient/next-action
  repair loops (16 same-shape orient attempts in one run); per-invocation
  repair is bounded (`_MAXIMUM_FORMAT_ATTEMPTS = 4`,
  `adaptive_practitioner_records.py:255`) but the rejected-shape digest
  set dies with the invocation.
- Work: persist rejected-output shape digests in run state per step;
  third recurrence of one shape forces strategy rotation or
  escalate-to-ask, never a fourth same-shape retry.
- Pointers: `core/adaptive_practitioner_records.py` (~2267,
  `invalid_digests` loop), `core/adaptive_practitioner_recovery.py:160`,
  new `diagnose_stall` recurrence question and `repetition_circuit_breaker`
  form (already shipped as vocabulary).
- Acceptance: a new offline check proving 3 same-shape failures trigger
  rotation/escalation; full `--self-test` green; a live pilot showing
  fewer wasted calls on the wine task.
- Non-goal: changing the per-invocation bound of 4.

### 2. Builtin glm route preflight arithmetic

- Symptom (verified by inspection, needs a live confirm): `glm-5.3-flash`
  declares output maximum 1048576 against route window 131072, so every
  allocation-free standard call fails context preflight. Same structural
  defect tactical had before the fit-window allocation.
- Status, September 21, 2026: **superseded on `main`** by the harness-first
  decision in
  [ADR-HARNESS-FIRST-SERVING-AND-EXECUTION](../architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md).
  Every executable step on `main` delegates to a standard harness, and the
  customer brings their own models and provider routes. The in-process
  `ollama_client` route table that carried this defect is on the checkpoint
  branch (`checkpoint/full-capability-2026-09-21`, revision `a3bd0f1`), so
  the route table is not a live path on `main` and the defect cannot fail
  a served customer call here. The underlying arithmetic defect — a
  declared output maximum larger than the route window fails preflight —
  stays recorded because it is the known-wrong case any future provider
  route record must reject: fix or re-measure the values on the checkpoint
  branch if the owner restores the in-process path as the custom loop-node
  harness, behind the typed executor interface named in the ADR. A route
  record whose declared maximum exceeds its window must refuse to load,
  not fail on first use.
- Work (checkpoint branch, or a live `main` harness adapter that adds a
  provider route): confirm with one live call, then apply the same
  pattern (explicit per-attempt allocation within the window) or correct
  the declared values with measured provenance.
- Pointers: `core/ollama_client.py:55` (capability record),
  `core/model_routes.py` (cloud_caps), `core/harness_semantic.py`
  `_fit_window` (precedent).
- Acceptance: a route whose declared maximum exceeds its window is
  refused at load; a live probe transcript is the source for any
  corrected number; no invented numbers.

### 3. Campaign runner outcome-scan gap

- Symptom: Kannada cell passed its gate but `model_calls` recorded null;
  `_scan_outcome` misses that solve's stdout shape.
- Work: harden `tools/task_campaign.py` `_scan_outcome` against the
  observed shape; add an offline unit check with the saved stdout.
- Acceptance: re-parse of the saved Kannada stdout yields the call count.

## P1: measurement and proposals

### 4. Orient-compliance-per-arm study

- Question: how much of the arm gap (opencode acts; pi/goose stall) is
  prompt efficiency vs reasoning? Data already exists in run histories
  (prompt bytes, repair counts, compliance per arm).
- Work: offline analysis script + dated note. No runtime change.

### 5. Tool-use-tuned model on tactical (external proposal)

- Evidence: ToolGrad-12B scores 83.1 on BFCL (near frontier proprietary);
  our binding constraint is tool/schema compliance in a small generic
  model. Draft the serving proposal for the tactical owner alongside
  the clean-run protocol (single serial client, small prompts, shared
  timestamps, prompt_digest correlation).

### 6. freebuff protocol qualification (design)

- State: T1-FAIL retained; binary installed but hosted protocol refused
  by recipe (`freebuff_hosted_protocol_not_qualified_for_model_broker`).
  Qualifying it is protocol design work, not a repair.

## P2: robustness

### 7. Endpoint backoff in the campaign runner

- Observation: tactical slowed 30x then refused connections under our
  3-parallel load; the campaign hammered through it. Add latency
  tracking per cell and automatic backoff/pause when p50 degrades 10x.

## DONE 2026-09-10 (opencode session, uncommitted, for review)

- Tactical route (`custom.tactical`): probed capacities (accept to
  2^31-1, 200K prompts OK), declared 1048576/200000 with provenance,
  sanctioned verification passing.
- `context_window` on custom providers (settings → route capabilities).
- Fit-window per-attempt allocations in the harness client.
- Short indexed `--harness-socket-dir` (108-byte cap).
- Output-type compat repairs (fields to end; string-only synthesis).
- `underlying_error` on reactive outcomes and harness results
  (type-only in persisted records).
- T1 gate gptme probe fix; openinterpreter chat-wire recipe + relay
  path routing; 20-newsgroups gate csv fix (in task database).
- Question coverage: startup (folders/workdir/environment), mid-act
  drift, verify format-conformance, integrate report-shaping,
  diagnose recurrence, repetition circuit-breaker form.
- Resilient campaign runner + standardized report; endpoint watcher
  (already self-resolved once).
