# Code review, 2026-09-07

Date: 2026-09-07, 00:05 to 00:40 local. Revision reviewed: `f2e8b151`
(GitHub main at the start), plus the then-untracked campaign modules under
`examples/25_host_runtime/` (`novel_task_population.py`,
`novel_task_offline_check.py`, `novel_task_campaign.py`, and, from 00:08,
`novel_task_audit.py`). A codex process (`codex -m gpt-5.6-sol --yolo`,
running for 23 hours) edited this worktree during the review: it patched the
offline check at 00:11, wrote a campaign report and evidence folder at 00:12
to 00:14, and committed and pushed all of it as `14153a1` at 00:15. The
committed files are byte-identical to the versions reviewed here (checked
after the commit), so every campaign finding below applies to `14153a1`. No
core module changed between `f2e8b15` and `14153a1`. Every statement below
names the time it was observed.

Scope: the four campaign modules and the live campaign they ran; the
2026-09-06 merge of the codex branch (`6686de4`) and the core modules it
changed (host runtime, reactive worker, adaptive dependency bindings, Loop
runtime); the repository gates, locally and on GitHub. Method: one
coordinator and three parallel reviewers, each limited to executing real
classes with fixture models and no provider calls. Every finding marked
CONFIRMED was reproduced by running code; the coordinator re-ran the three
highest-severity reviewer probes and got the same results. Reading alone
never produced a CONFIRMED status.

## Summary

The engine solved ten small algorithmic tasks end to end with complete call
and token accounting, and every host-boundary invariant that was attacked
held: no forged observation, replayed state, malformed gate reply, or
unauthorized operation reached `task_complete`. That is real progress and it
is recorded in section 11.

Three things stand in the way of trusting the rest.

1. The evidence behind the new campaign is weaker than its report says.
   Three of the ten sealed prompts contradict their own hidden oracles; the
   model paid 172 of the campaign's 283 calls discovering that and then
   satisfied the oracles by contradicting the prompts. The "independent"
   offline check encodes the same contradictions, so it could not have
   caught them. The report's single invalidation rests on a reference whose
   verdict depends on loop order, and its "500-input stress" exists in no
   record.
2. GitHub CI has failed on 45 consecutive pushes to `main` since 2026-09-02,
   including the commit made during this review. The suite job has failed the
   hardcoding delta gate on every push since 2026-09-05 and the count of new
   findings has grown from 61 to 2,980. Every verification report in that
   window describes local gates as green.
3. Three runtime defects survive from earlier reviews or the new work: Run
   History still accepts forged step, usage, and terminal events; a Loop
   under `accepted_success` has no iteration ceiling unless its failures are
   byte-identical; and two reactive workers on one database can wedge each
   other's SQLite connection for good.

Thirty-one findings follow: 6 high, 14 medium, 11 low. Twenty-nine are
CONFIRMED by execution; two are direct observations of repository state.

## Findings register

| ID | Severity | Area | Status | One line |
|---|---|---|---|---|
| R1 | high | repository | CONFIRMED | GitHub CI red on 45 consecutive pushes since 2026-09-02; hardcoding delta gate at 2,980 new findings, reproduced locally |
| C1 | high | campaign | CONFIRMED | three sealed prompts contradict their oracles; spec-faithful solutions fail 5, 2, and 1 cases; live run paid 172 calls for it |
| C2 | high | campaign | CONFIRMED | offline check references encode the same contradictions; the evaluator control tests the wrong thing |
| W1 | high | reactive | CONFIRMED | Run History and the verified reactive reader accept forged step, model-usage, and terminal events |
| W2 | high | reactive | CONFIRMED | lost primary-key race between `terminal()` and a peer's `recover_expired()` wedges the loser's connection permanently |
| B1 | high | loop runtime | CONFIRMED | `accepted_success` iteration is unbounded unless failures are byte-identical (3,001 iterations observed) |
| C3 | medium | campaign | CONFIRMED | `matrix_spiral` cannot detect a non-spiral; `poly_hash` "unicode" hashes ASCII; `word_square` has a duplicate misnamed case |
| C4 | medium | campaign | CONFIRMED | the sole audit invalidation rests on an order-dependent reference; the cited 500-input stress is unrecorded |
| C5 | medium | campaign | CONFIRMED | three reference implementations deviate from their prompts (crash on start wall, zero-length interval, `+5`) |
| C6 | medium | campaign | CONFIRMED | population and runner sources are not digest-bound; the probe's per-task frozen-runner check is absent |
| C7 | medium | campaign | CONFIRMED | the audit executes model-authored code on the host interpreter; hardcoded `/tmp` paths; dead invalid-input branch |
| C8 | medium | campaign | observed | 93 MB of campaign evidence exists only on tmpfs; the report cites `/tmp` as where evidence lives |
| R2 | medium | repository | observed | merge tree identical to the codex tip; two extra branches on origin against the main-only rule |
| H1 | medium | host | CONFIRMED | a callback that raises before any effect marks the run "unknown outcome" with no reconciliation path; reachable by a chars-versus-bytes limit mismatch |
| W3 | medium | reactive | CONFIRMED | the worker never heartbeats; a healthy handler past `lease_seconds` is dead-lettered and its result refused |
| W4 | medium | reactive | CONFIRMED | fencing token readable by any reader; `terminal()` checks possession only; forged terminal attributed to the victim worker |
| W5 | medium | reactive | CONFIRMED | a stale fence at `start()` escapes `run_once`; `run_many` discards every sibling outcome |
| W6 | medium | reactive | CONFIRMED | "required" history is a worker flag; `DURABLE_SERIES` is never read; durable series publish without history |
| B2 | medium | loop runtime | CONFIRMED | deeply nested model JSON raises `RecursionError` through admission and aborts the run without repair |
| B3 | medium | bindings | CONFIRMED | reference delivery is body-inaccessible; `frame.resolvers` is written and never read |
| B4 | medium | loop runtime | CONFIRMED | synthetic kernel completions were relabeled, not removed: 12 accepted `run_step` events per kernel run |
| B5 | medium | bindings | CONFIRMED | no size bound on dependency values; a 1.49 MB consumer packet from one producer result |
| C9 | low | campaign | observed | "invented domains" overstates six textbook tasks; no tests or README entry; `.codegraph/` was untracked and unignored |
| C10 | low | gates | CONFIRMED | three live-demo self-test checks depend on machine speed; failed under load, passed alone |
| H2 | low | host | CONFIRMED | candidate code can return `probe-input.json`, exposing every case's arguments despite the `tool_only` label |
| H3 | low | host | CONFIRMED | the Node bridge's `harness_text` frames are silently dropped by the Python bridge |
| H4 | low | host | CONFIRMED | absolute host paths appear in model-visible records and manifests |
| W7 | low | reactive | CONFIRMED | post-cancel model usage recorded only as a `custom` event; canonical and OpenTelemetry views show zero |
| W8 | low | reactive | CONFIRMED | `LEGACY_UNRECORDED` is a writable disposition for new version 2 records |
| W9 | low | reactive | CONFIRMED | `cancel()` after `terminal` appends a status change after `loop.completed` |
| W10 | low | reactive | CONFIRMED | canceled and dead-letter records carry false status metadata; a post-save failure leaves an orphan committed run |
| B6 | low | loop runtime | CONFIRMED | duck-typed contract objects are re-typed silently; only `LoopContract` inputs record coercion |
| B7 | low | bindings | CONFIRMED | a non-binding error from `frame.register` replaces a successful spawned summary with a generic record |

## 1. The sealed novel population contradicts its own oracles (C1)

Three of the ten tasks in `novel_task_population.py` state a contract that
the frozen cases refuse. A solution written from the prompt fails; a solution
written from the hidden expected values passes.

| Task | Prompt says | Cases require | Spec-faithful solution fails |
|---|---|---|---|
| `grid_path_cost` | "period-separated cells" | every grid uses commas | 5 of 12 (`plain`, `cheaper_detour`, `wall_detour`, `blocked`, `single_row`) |
| `calendar_slots` | "minutes 0 through 1439"; "times outside the day" raise `ValueError` | `24:00` must be accepted as an end time | 2 of 12 (`full_day`, `end_midnight`) |
| `state_machine` | "an optionally signed ASCII decimal integer" | `01` must raise `ValueError` | 1 of 12 (`leading_zero`) |

Probe: `novel_probe.py` section A, run through the probe's own `WORKER` and
`evaluate()` with a host Python runner instead of Docker. Swapping the
separator from period to comma in the same grid solution turns 5 failures
into 12 passes.

The live campaign in `/tmp/novel-campaign-20260906/` (22:44 to 00:06, ten
tasks, 283 calls, 7,636,923 input and 961,827 output tokens, all reported
`COMPLETED_VERIFIED`) shows the same three defects from the model's side:

- `grid_path_cost`: observations 1 through 4 failed on exactly the five
  cases above with period parsing. Observation 5 failed all twelve.
  Observation 6 passed after the model switched to commas. The task took 106
  calls, 2,634 seconds, and 3,686,088 input tokens. The run's own
  verification record states the cause: "The probe's grid_text uses commas
  as the cell separator ... rather than periods as the task text states; the
  installed comma-splitting implementation matches the observed probe
  format."
- `calendar_slots`: observation 1 failed `full_day` and `end_midnight`; the
  passing source special-cases `24:00`. 26 calls.
- `state_machine`: observation 1 failed `leading_zero`; the passing source
  adds a regex the prompt never asked for. 40 calls.

So the three accepted artifacts satisfy the oracle by contradicting the
written contract. By the standard the campaign report applies to
`word_square` ("not correct for its full prompt"), these three are not
correct for their exact prompts either, and here the mismatch is on the
oracle's side. About 61 percent of the campaign's model calls and 69 percent
of its input tokens went to these three tasks; the other seven took 15 to 17
calls each.

## 2. The offline check is circular where it matters (C2, C5)

`novel_task_offline_check.py` promises references "written independently from
the prompt". The references encode the same three contradictions: they split
on commas, accept `24:00`, and reject a leading zero, so all 109 cases match
and the check passes (reproduced: exit 0). A reference written from the
prompt would have caught all three.

The "every evaluator must fail a deliberately wrong solution" control compares
the reference function against one wrong constant (for example the balanced
ledger against `None`). It never runs the campaign evaluator against a wrong
solution. `prompt_entrypoint_mismatches` is initialized, never populated, and
not part of the exit code.

Reference defects found by running them (probe section B):

- `ref_path_cost('X,1\n1,1')` raised `TypeError`; the prompt says return
  `None` when no path exists. The codex process patched this at 00:11:48,
  after its audit tripped over it.
- `ref_free_minutes('[["09:00","09:00"]]')` raises `ValueError`; the prompt
  forbids only an end before its start.
- `ref_final_state('+5')` raises `ValueError`; the prompt says "optionally
  signed".

## 3. Cases that cannot test what they name (C3)

- `matrix_spiral`: the sum of elements in spiral order equals the sum in any
  order. A flat double loop with the same validation passes all ten cases
  (probe section A, `flat_sum_no_spiral`). The accepted live solution does
  walk a spiral, but the evaluator could not have told.
- `poly_hash` case `unicode`: the Python source spells the argument
  `'\\u00e9'`, a six-character ASCII string (code points 92, 117, 48, 48, 101,
  57). Its expected value 2 is the hash of that string; the hash of `é` is 39.
  No case tests a code point above 127. The audit generator's alphabet
  repeats the same doubled backslash, so the audit never tests one either.
- `word_square`: `three_by_three_square` and `false_case` carry identical
  arguments and the same expected value `False`; the first is misnamed. No
  positive three-by-three square is tested (`['cat','are','ted']` is one).

## 4. The one audit invalidation rests on an order-dependent reference (C4)

The campaign report says the post-hoc audit invalidated `word_square` because
the accepted source raises `ValueError` whenever any word is shorter than the
list, while "the task contract rejects that only when the list length exceeds
every element length". The reference does not implement that reading either.
It compares characters in nested loops and raises `too short` only when the
loop reaches a missing character before it finds a mismatch:

```text
ref_is_word_square(['ab', 'a'])  -> False
ref_is_word_square(['aa', 'a'])  -> ValueError('too short')
ref_is_word_square(['ba', 'a'])  -> ValueError('too short')
```

Same shape, different verdicts. The nine audit mismatches recorded in
`audit.json` (9 of 60; the report's "500-input boundary stress" and "109
inputs" exist in no saved record) are exactly the inputs where an early
column mismatch preempts the short-word check. The model's solution applies
one consistent rule that the prompt's own parenthetical ("some pair i, j
would need characters that do not exist") supports. The report's "10 percent
false-acceptance rate" is therefore unsupported as written; the prompt is
ambiguous and the reference is inconsistent.

## 5. Provenance, sandboxing, and durability of the campaign (C6 to C9)

- `campaign_manifest()` reuses `population_manifest()`, whose `source_digest`
  is the SHA-256 of `generalization_probe.py`. Neither
  `novel_task_population.py` nor `novel_task_campaign.py` is digest-bound
  anywhere in the manifest or report; the probe's per-task "frozen runner
  source changed" check is absent from the campaign loop; the constant
  `RUNNER_DIGEST_NOTE` is defined and never used. The population that ran is
  byte-identical to the population on disk (all ten task digests match), so
  nothing was altered after the fact; the point is that the record could not
  have shown it if it had been.
- `novel_task_audit.py` loads each model-authored `solution.py` with
  `importlib` and executes it in the host interpreter, with network and
  without resource limits. The campaign ran the same files only inside the
  pinned Docker image with no network. AGENTS.md: "Run untrusted code in a
  declared sandbox with bounded resources and network policy." The audit
  also hardcodes `/tmp/novel-campaign-20260906` and
  `/tmp/novel-campaign-audit.json`, its grid generator's invalid-input branch
  is dead code (`if False`), and most generators emit only valid inputs, so
  error paths are unaudited.
- Evidence durability: the per-task outcomes, observations, sources, and Run
  History (93 MB) exist only under `/tmp`, which is tmpfs on this machine. The
  repository copy under `docs/evidence/novel-campaign-20260906/` holds the
  population, the report, and the audit JSON. The campaign report cites the
  `/tmp` paths as where "evidence lives".
- The population docstring says "invented domains". At least six tasks are
  textbook problems with contract twists: minimum path sum, decode string,
  Josephus, polynomial rolling hash, spiral matrix, valid word square. The
  report's "Not established" paragraph does say novelty to the model is not
  claimed; the module text should say the same.
- None of the four modules has a unit test or a README entry. `.codegraph/`
  (57 MB) was untracked and not in `.gitignore`; this review adds the line.

## 6. GitHub CI has been red on main since 2026-09-02 (R1, C10)

Of the last 46 workflow runs on `main`, one succeeded (`a67525a`, 2026-09-02
17:37). The 45 pushes since then all failed, `14153a1` included:

| Failing job | Runs | Cause seen in logs |
|---|---:|---|
| public documentation | 43 | vale on pushed Markdown: `NoDashes` (134 hits in the `288348e` run), `RetiredTerms` (34), `RetiredTopology` (12) |
| suite + conformance gates (3.10, 3.11, 3.12) | 16 | the hardcoding delta gate, every time; on all 12 pushes since 2026-09-05 |

In every sampled suite failure the self-test and conformance steps passed and
the job died at `--hardcoding-audit ... --fail-on-new high`. The count of new
findings has grown at each sample:

| Push | Date | New hardcoding findings |
|---|---|---:|
| `138c844` | 2026-09-03 15:49 | 61 |
| `22ee440` | 2026-09-04 01:28 | 270 |
| `d121379` | 2026-09-05 01:31 | 1,660 |
| `b9b7d85` | 2026-09-05 22:16 | 2,327 |
| `1ea1335` | 2026-09-06 04:28 | 2,652 |
| `f2e8b15`, `14153a1` | 2026-09-07 | 2,980 |

Reproduced locally at HEAD with identical totals: 12,885 material findings
(1,018 high, 11,867 medium), 2,980 new, 168 resolved, exit 1. Of the 260
blocking new high findings, 167 are in `src/loop_engine/core`, 94 are in
files changed by the 2026-09-06 work, 192 are closed-vocabulary literals, 65
are provider or strategy bindings, and one is a credential reference
(`OPENAI_API_KEY` in `openai_responses_client.py:582`). Fifty-one are
URL literals inside two `docs/research/*.json` files, which look like
classifier noise rather than defects. The 2026-09-06 checkpoint report
discloses the delta ("2,958 new findings ... need review before release
acceptance") while describing the checkpoint as passing 3,363 of 3,363
checks. Both statements are true; only one of them is the release gate, and
it has not passed on `main` for four days.

Local gates on Python 3.10 (`.venv`), this review:

| Gate | Result |
|---|---|
| `--self-test` | 3,381 of 3,384; the three failures are the live-demo checks in `code_nodes/live_run_demo.py`, whose own message says a partial run "measures machine speed, not the server"; they ran at load average 41 and passed 6 of 6 when re-run alone |
| `--conformance` | all gates pass, 8 guard-enforced rails |
| `--repo-conformance` | passed |
| `examples/25_host_runtime` unit tests | 127 of 127 in 52 seconds |
| devtools self-test | pass |
| hardcoding delta gate | fail, 2,980 new |

## 7. The merge and the branches (R2)

`6686de4` merges `73976c3` (codex branch) into `288348e` (main). Its tree is
byte-identical to `73976c3`: `git diff 6686de4^2 6686de4` is empty. `288348e`
was committed three minutes before `73976c3` from the same stream of work.
Of the 3,400 nontrivial lines `288348e` added, 48 are absent from the merge
result; spot checks of `kernel_runtime.py`, `make_host()`, and the planning
module show newer versions of the same code (for example the planning refusal
of dependency fields replaced by `adaptive_practitioner_bindings.py`). An AST
scan of the 16 touched modules found no duplicate definitions. No independent
main-side work was found dropped. No conflict markers remain.

`origin` carries `codex/generalized-adaptive-work-20260906` (at `73976c3`)
and `overnight/opencode-step-instances` (at `ab746aa`) in addition to `main`
and the 2026-08-25 checkpoint. The owner's standing instruction is main only.

## 8. Host boundary and OpenCode quarantine (H1 to H4)

Reviewed by driving `HostRuntimeBinding`, the example `make_host()` closures,
`execute_adaptive_capability`, and the OpenCode bridge with a fake `docker`
binary on `PATH`, plus the pre-merge module at `1ea1335` on the same fixture.

- CONFIRMED, medium. A host callback that raises before performing any effect
  is recorded as a mutating effect with unknown outcome (`_invoke`,
  `core/host_runtime.py:360-377`), after which `_approve` (`:312-313`) refuses
  every later `workspace_replace`, `workspace_run`, and completion gate with
  "reconciliation is required". No reconciliation path exists; the phrase
  appears only in the message and one test. The example host makes this
  reachable from benign model input: `replace_source`
  (`generalization_probe.py:876`) raises for content over 65,536 bytes, while
  the registered schema caps `maxLength: 65536` characters (`:1014`). A
  content string of 65,536 `é` characters passes the schema, the host raises,
  `solution.py` is unchanged on disk, and the run can never write, run, or
  complete again. The digest-mismatch refusal, by contrast, returns a typed
  dict and the run continues. Probe `probe_g_unknown_outcome.py`.
- CONFIRMED, low. `workspace_inspect` labels `probe_arguments` as
  `tool_only`, but candidate code can return the contents of
  `probe-input.json` as its value, and `feedback()` relays the full observed
  value with no size cap on the primary path (`generalization_probe.py:527`).
  All ten cases' arguments, including the audit regression inputs, reached
  the model-visible run record. Expected answers never enter the sandbox and
  were not exposed. Probe `probe_h_argument_exfil.py`.
- CONFIRMED, low. The Node bridge emits a `harness_text` frame for every
  non-JSON OpenCode stdout line (`opencode_stdio_bridge.mjs:106`); the Python
  bridge has no branch for that record type
  (`opencode_gateway_bridge.py:346-348`), so those lines vanish from the
  events artifact, against the adapter's own rule "Unknown event types are
  counted, never dropped silently" (`opencode_harness_adapter.py:120`). All
  other frame shapes agree between the two sides. Probe `probe_e_bridge.py`.
- CONFIRMED, low. Every model-visible host record, the manifest, and each
  descriptor's `permission_scope` carry the host's absolute work directory;
  artifact and completion record paths are absolute too. Filesystem layout
  disclosure only. Probe `probe_c_leakage.py`.

Probes: `agent_host/probe_a_forgery.py` through `probe_h_argument_exfil.py`
with JSON outputs, `bin/docker`, `host_runtime_v0.py`.

## 9. Reactive worker and Run History (W1 to W10)

Reviewed by executing the real `RunHistory`, `LoopLedger`, `ReactiveScheduler`
(SQLite), and `AsyncReactiveWorker` classes with the repository's own fixture
style. The 2026-09-06 report's claims about attempt policy, expired leases,
dead letter, cancellation, kernel preparation, and the version 1 reader all
held (section 11). What did not hold:

- CONFIRMED, high. Run History accepts forged events in process, and the new
  verified reactive reader accepts them too. `RunHistory.append`
  (`core/run_history.py:152-166`) admits any registered event type with any
  fields and maintains only the digest chain; `LoopLedger.record`
  (`loop/recursive_loop.py:299-310`) enforces definition fields only for
  registered loop ids; `_read_verified_history`
  (`core/reactive_worker.py:347-385`) checks count, head, committed flag,
  binding, one terminal, and the init digest, not authorship. A reactive step
  handler that records a `verify` step reading "FORGED: independent
  verification passed", a model invocation for a model never called (12,345
  input and 678 output tokens), and a `terminal` for a phantom loop id, then
  returns normally, ends `completed` with `history_disposition: persisted` and
  `load_verified_history: ACCEPTED`. The 2026-09-01 open finding stands; the
  verified reader mitigates only a forged terminal for the same loop id and a
  forged init with the wrong definition digest. Probe `probe_e_forge.py`,
  re-run by the coordinator with the same result.
- CONFIRMED, high. Two workers sharing one scheduler database can lose a
  primary-key race between `terminal()` and a peer's `recover_expired()`
  (`core/reactive_scheduler.py:344-431`). Both read then insert revision N+1
  with no explicit transaction; the loser receives a raw
  `sqlite3.IntegrityError` and its connection stays inside an implicit
  transaction, so every later `claim()` on it raises "cannot start a
  transaction within a transaction". Reproduced with two independent
  connections and only a start barrier, no forced interleaving: connection B
  wedged after 40 rounds (`probe_g_natural_race.py`, re-run by the
  coordinator). Durable state stayed consistent; the worker did not.
- CONFIRMED, medium. `AsyncReactiveWorker` never calls `heartbeat`
  (`core/reactive_worker.py:452-505`); the only caller is a check module. A
  healthy handler that outlives `lease_seconds` is dead-lettered by the first
  peer `claim()` as `RUNNING_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED` and its
  finished result is refused, although the Loop reached `success_once`.
- CONFIRMED, medium. The fencing token is readable by any database reader,
  `_require_fence` checks lease id and token only, and
  `ActivationTerminalRequest` carries no worker id
  (`loop/reactive_activation.py:560-609`). A process that never claimed can
  publish COMPLETED for another worker's running activation with a forged
  `loop_id`; the record keeps the victim's `worker_id`, and the owner's real
  terminal is then refused.
- CONFIRMED, medium. A stale fence at `start()` raises before the `try` in
  `run_once` (`core/reactive_worker.py:461-469`), and `run_many` uses a bare
  `asyncio.gather`, so one stale lease discards every sibling outcome while
  the database shows them `completed` and `running`.
- CONFIRMED, medium. "Required" history is a per-binding worker flag
  (`ReactiveHistoryPolicy.required`, default `False`); the series profile's
  `PersistenceMode.DURABLE_SERIES` is never read. A default binding on a
  durable series publishes COMPLETED with `history_disposition:
  not_persisted`. The repository's own check asserts this behavior.
- CONFIRMED, low. Model usage from a post-cancel handler return is recorded
  only as a `custom` ledger event; the canonical Run History and
  OpenTelemetry projections show zero model invocations while `LoopResult`
  reports one (`loop/recursive_loop.py:1437-1451`, `core/run_history.py:202-260`).
- CONFIRMED, low. `LEGACY_UNRECORDED` is a writable disposition: a new
  version 2 record can be published labeled legacy, and later revisions after
  a genuine version 1 row inherit the label
  (`loop/reactive_activation.py:573-609`). Records are distinguishable only by
  raw `record_type`, not through the reader.
- CONFIRMED, low. `cancel()` on a terminal Loop appends a `cancel` event
  after `terminal` (relabel correctly refused), so the canonical projection
  emits `run.status_changed` after `loop.completed`; the kernel preparation
  rejection path does this to ACCEPTED owners.
- CONFIRMED, low. Canceled and dead-letter records carry false metadata: the
  runtime observation labels them `reactive_activation_failed` with
  `status: failed`, and a dead-letter revision inherits `not_persisted` even
  when a committed history for that attempt exists on disk. A persistence
  failure after `save()` leaves a committed orphan run directory, fails the
  activation permanently with attempts remaining, and drops the exception
  type.

Probes: `agent_reactive/probe_a_lease.py` through `probe_g_natural_race.py`,
each with a `.out.json`, plus `baseline_worker_selftest.txt` (reactive
scheduler checks 13 of 13, reactive worker checks 43 of 43, kernel runtime
self-test 27 of 27 at HEAD).

## 10. Adaptive dependency bindings and the Loop runtime re-probe (B1 to B7)

Reviewed by compiling and executing plans through the public adaptive gate
with a fixture model (zero provider calls), driving `SpawnedDependencyFrame`
directly, and running minimal Loops while reading the ledger.

- CONFIRMED, high. Iteration under `exit_condition="accepted_success"` is
  bounded only for byte-identical failures. `identical_failures_before_stop`
  stops a repeating failure at 3 (`BLOCKED/no_progress`), but a handler whose
  failure text varies, alternates, or returns unaccepted outcomes without
  `failed=True` runs without a ceiling: 3,001 invocations before the probe
  stopped it, `max_iterations=None` by default, and
  `non_progress_passes_before_escalation` is enforced only in `kernel.py`
  for kernel passes, never in `Loop.run_next_iteration`
  (`loop/recursive_loop.py:1293-1301, 1401-1425`). Any real handler that
  includes a counter or timestamp in its failure output defeats the guard.
  Not a merge regression; the 2026-09-01 "bounded iteration" fix holds only
  for identical failures. Probe `probe_loop_runtime.py` (b2), re-run by the
  coordinator with the same result.
- CONFIRMED, medium. Deeply nested model output aborts the whole run.
  `model_response_admission.py:252-253` catches only `JSONDecodeError`; a
  response nested about 1,000 levels deep raises `RecursionError`, which
  escapes admission (no admission record), the session, and the planning
  repair loop, ending the run with `failure_code: RecursionError` after
  three calls and no repair attempt. Depths of 300 to 900 are refused typed
  by the plan gate, so admission is the only abort surface.
- CONFIRMED, medium. Reference delivery is body-inaccessible. A consumer
  bound by reference receives only `value_ref` in its delegated task text;
  the only `materialize` call is inside `resolve()` before dispatch;
  `frame.resolvers[consumer.loop_id]` is written and never read anywhere
  (`adaptive_practitioner_bindings.py:444-446, 456`;
  `adaptive_practitioner_scope.py:246`). The self-test passes because its
  fixture echoes the reference back as its value. `resolve()` also records
  `information_materialized` on the consumer for reference delivery it never
  performs.
- CONFIRMED, medium. The 2026-09-01 "synthetic kernel completions" fix was a
  relabel. Each Practitioner kernel run still emits one `run_step
  accepted=True confidence=1.0 mode=deterministic` event per non-act node
  (12 of the 13 `KERNEL_NODES`), output `kernel:<step>:structural_boundary`,
  persisted in Run History as `iteration` events with status `ok`
  (`loop/kernel_runtime.py:181-201`); resolver-completed spawned loops emit
  13 accepted `<step>:trace_preserved` iterations although the kernel never
  ran. A ledger consumer filtering on `run_step` and `accepted` cannot
  separate these from executed steps. This is the information-theory
  concern from the 2026-09-01 review, unchanged in substance.
- CONFIRMED, medium. No size bound anywhere on dependency values:
  `InformationAccessRequest` sets no `maximum_bytes`, `_inline_snapshot` has
  no cap, and value delivery deep-copies the body into the delegated task
  text. A 200,000-integer producer result yielded a 1,489,748-byte consumer
  task packet (prompt material) in 18.9 seconds end to end.
- CONFIRMED, low. Silent re-typing persists for duck-typed contract objects:
  `_contract_coercion_fields` returns `{}` when the requested contract is
  not a `LoopContract`, so a legacy object declaring `model_led`/`solution`
  binds as `code_only practitioner` with no coercion recorded
  (`recursive_loop.py:398-419`, `loop_definition.py:376-388`). Real
  `LoopContract` inputs are recorded and mismatched ports are refused.
- Frame-level CONFIRMED, low. When `frame.register` raises anything other
  than `DependencyBindingError`, the successful spawned run's summary is
  replaced by a generic error record with no `binding_disposition` and no
  `adaptive_spawned_result_returned` event; the consumer is blocked (safe)
  but the record taxonomy is inconsistent (`adaptive_practitioner_scope.py:262-296`).

Re-probe of the five 2026-09-01 runtime defects at HEAD, by execution:

| Defect | Verdict | Evidence |
|---|---|---|
| Fabricated "recovered" step outcomes | still fixed | fallback hybrid to deterministic recorded as `run_step accepted=False`, terminal `done_failed`, result `VERIFICATION_REJECTED`; no "recovered" text |
| Unbounded iteration under accepted_success | fixed for identical failures only | 3,001 iterations with varying failure text |
| Masked `RecursionError` in loop definition | still fixed | propagates with its own type; unbounded spawn is a typed `LoopError` at depth 129 |
| Silent contract coercion | fixed for `LoopContract`, open for duck-typed objects | coercion recorded on `init`; `'a/v1' cannot feed 'b/v1' without an Adapter Loop` |
| Synthetic kernel step completions | relabeled, not removed | 12 accepted structural-boundary `run_step` events per kernel run |

Probes: `agent_bindings/probe_compile.py`, `probe_frame.py`, `probe_public.py`,
`probe_loop_runtime.py`, `probe_admission_kernel.py`, `probe_followup.py`,
`probe_history.py`, `probe_history2.py`, each with a `.out` file.

## 11. What held

Attacked by execution and found sound, with the probe that shows it:

- Host completion cannot be forged or replayed: forged `run_ref`, extra
  fields, model-composed lookalike records, flipped `comparison.passed` with
  recomputed digests, replay after a source change, a `source_replacement`
  presented as complete, and changed task text were all refused
  (`agent_host/probe_a_forgery.py`).
- Completion gates run and fail closed: `task_complete='yes'`, `None`,
  missing observations, a raising gate, `ok: False`, state drift between the
  primary verifier and the gate, drift during gate approval, swapped or
  duplicated gate lists, and a re-issued failed report were all refused or
  marked unavailable (`probe_b_gates.py`).
- No expected value, expected error, or passing-case failure note reaches the
  model; generated completion cases expose neither expected values nor
  arguments (`probe_c_leakage.py`). `share_outputs_with_model` is mandatory
  and the runtime redacts nothing; redaction is the host callback's job.
- Every approval binds `host_binding_digest`, `host_invocation_digest`,
  `state`, and `task_digest` under a fresh request id; stale, edited, and
  rejected decisions raise before the callback; the verifier and completion
  gate cannot be dispatched as operations (`probe_d_authority.py`).
- The OpenCode quarantine holds: `OpenCodeProcessAdapter` refuses
  unconditionally; the bridge runs `docker` with a fixed argv (`--pull never
  --network none --read-only --cap-drop ALL`), the goal travels only in the
  stdin frame, and model `bash`, out-of-set reads, missing core context, and
  oversize frames fail closed with zero model responses reaching the
  container (`probe_e_bridge.py`).
- `HostRuntimeBinding` without completion gates behaves identically to the
  pre-merge module on the same fixture (`probe_f_compat.py`).
- Reactive attempt policy, lease expiry boundaries, dead letter on expired
  running work, refusal of late owner terminals, the restart proof (effect
  count stays 1), the reopen check (a re-digested tamper that plain load
  accepts is refused by the verified reader), terminal cancellation with no
  output retention or spawn, and the exact version 1 reader all held
  (`agent_reactive/probe_a_lease.py`, `probe_c_history.py`, `probe_d_cancel.py`,
  `probe_f_v1.py`).
- Whole-plan admission refuses self-dependency, cycles, missing producers,
  unlisted-producer inputs, bindings without prerequisites, nonexistent
  ports, duplicate consumer roles, fourteen hostile schema shapes, wrong
  record versions, surplus fields, and malformed task ids before dispatch;
  producers are ordered before consumers regardless of listing; mutated,
  failed, forged, cross-ledger, and second-start producers are refused; NaN,
  infinity, bool-as-integer, and 10**5000 values are refused; spawned
  summaries carry `completes_spawning_task: false` and cannot certify the
  spawning task (`agent_bindings/probe_compile.py`, `probe_frame.py`,
  `probe_public.py`, `probe_history.py`).
- No second executor, scheduler, thread pool, or run loop was added to `src/`
  since the merge base.
- The population that ran the campaign is byte-identical to the population on
  disk, the probe source digest matches, model-call and token accounting were
  complete on all ten tasks, and the accepted `matrix_spiral` solution does
  walk a spiral.

## 12. Recommended order of work

1. Make `main` green and keep it green. Triage the 260 blocking hardcoding
   findings (start with the credential reference and the 94 in the 2026-09-06
   files; the 51 URL literals in `docs/research/*.json` want an allowlist
   entry or a classifier fix), and run vale with the repository's rules
   before every push. Until CI passes, verification reports should cite the
   CI run, not local gate counts.
2. Reactive worker: wrap read-then-insert in explicit transactions and turn
   `IntegrityError` into a typed, rolled-back refusal (W2); call `heartbeat`
   from the worker (W3); carry the worker id in terminal requests and bind
   the fence to the claimant (W4); `return_exceptions=True` and move
   `start()` inside the guarded region (W5); read `DURABLE_SERIES` (W6).
3. Loop runtime: a default hard ceiling for `accepted_success` that counts
   non-accepted iterations, not identical failures (B1); catch
   `RecursionError` in admission as `invalid_json_value` (B2); emit kernel
   structural boundaries as their own event kind rather than accepted
   `run_step` events (B4).
4. Run History authorship: bind each event to the Loop that may emit it
   (definition-registered event kinds per loop id, or a per-run signing key
   held by the runtime) so a handler cannot append a `verify` step it never
   ran (W1). This is the third review to record the finding.
5. Bindings: either materialize reference deliveries for the consumer or
   refuse reference delivery until a resolver is wired (B3); bound value
   sizes (B5).
6. Campaign: repair the three prompts or their cases and re-seal as a new
   population with a new digest; derive references from prompts by an author
   who has not seen the cases, or use two independent authors (C1, C2); run
   the campaign evaluator against wrong solutions as the control; add a
   positive three-by-three word square, a real non-ASCII code point, and a
   spiral check sensitive to visit order (C3); digest-bind the population and
   runner and restore the frozen-runner check (C6); run the audit inside the
   pinned container and let it take its root as an argument (C7); copy the
   per-task evidence off tmpfs (C8); correct the campaign report so that the
   `word_square` invalidation, the unrecorded stress test, and the three
   oracle-side mismatches read as what they are (C4).
7. Host example: reconcile bytes and characters, or return a typed refusal
   for oversize content, and give unknown-outcome a reconciliation path
   (H1); cap `feedback()` observed sizes and either hide `probe-input.json`
   from the candidate or relabel its visibility (H2); handle `harness_text`
   in the Python bridge (H3).

## Probe scripts and outputs

All under the session scratch directory
`/tmp/claude-1000/-home-username-loop-engine/6d8b36e1-c0bf-4f98-a765-7be966b7d9c2/scratchpad/`:

- `novel_probe.py` (sections A to E) and `novel_runs/` (campaign contradictions, references, provenance)
- `selftest.out`, `conformance.out`, `repo_conformance.json`, `host_runtime_tests.out`, `devtools_selftest.out`, `hardcoding_audit.out`, `hardcoding.jsonl`, `hardcoding_audit.json`
- `ci_runs.json`, `ci_rows.json`, `ci_14153a1_failed.log`
- `main_added.txt`, `merge_removed.txt`, `dropped_by_merge.txt`
- `agent_host/`, `agent_reactive/`, `agent_bindings/` as listed in sections 8 to 10

Nothing in the repository was modified by this review except this report and
one `.gitignore` line for `.codegraph/`. The campaign modules were not
edited; they were still being written by the codex process when the review
began.
