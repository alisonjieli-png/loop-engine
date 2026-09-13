# Harness and embodiment trials, 2026-09-10

Offline rounds only (stub broker, explicit fixtures, zero live model calls).
Live comparison waits on the tactical endpoint's documented max output tokens
(gateway refuses with `unknown_model_output_limit` until a source-backed
integer is declared; no ceiling is invented).

## T1 transport gates: 17/19 (`tools/harness_t1_gates.py`, full sweep re-run)

Pass: aider, cline, codex, continue, forgecode, gemini_cli, goose, gptme,
hermes_agent, kilo, mini_swe_agent, mistral_vibe, nanocode, opencode, pi,
qwen_code, trae_agent.

Fail (recorded, distinct causes):

- `freebuff`: spec rejected. The style is absent from the process vocabulary
  and its recipe deliberately refuses it
  (`freebuff_hosted_protocol_not_qualified_for_model_broker`). Qualifying a
  hosted protocol is design work, not a repair. Verdict stands.
- `openinterpreter_rust`: the 0.0.42 binary routes `deepseek-*` slugs to its
  hosted DeepSeek catalog and refuses the private broker, so the uniform stub
  label cannot pass. No per-arm exception was added to the gate. Transport is
  proven with non-catalog slugs: with `gemma-4-coding-abliterated` (the live
  campaign model) the arm completes end to end (`ok: True`, stub answer
  extracted, 1 broker call).
- Fixed this round: `gptme` (gate probed `gptme-util --version`, a flag the
  binary lacks; the gate now probes each style's documented entrypoint).

Supporting fixes: the `openinterpreter_rust` recipe declares
`wire_api = "chat"` per the arm's own delta doc (Responses wire is refused
for non-o-series slugs), and the relay routes that arm by path, keeping
host-side model-identity and tool-ban checks for both wires.

## Full-solve qualification (fixture replies, 0 live calls): 14/17

Pass (COMPLETED_VERIFIED, harness invoked, independent verification passed):
pi, opencode, goose, aider, cline, codex, gemini_cli, gptme, hermes_agent,
kilo, mini_swe_agent, mistral_vibe, nanocode, trae_agent.

Fail (arm ran, history intact, answer not admitted):

- `continue`: VERIFICATION_FAILED.
- `forgecode`: NO_PROGRESS.
- `qwen_code`: VERIFICATION_FAILED.
- Signature for continue/qwen_code: `semantic harness did not produce an
  admitted response`. T1 delivery passes for these arms, so bytes reach the
  harness; the full-solve admission (exact fixture echo) rejects their
  replies. Arm characteristic, retained as failure.

Negative controls discriminate: `wrong_math` and `undeclared_dependency`
both yield VERIFICATION_FAILED with `independent_verification: failed`.

## Embodiment suites

- `devtools/embodiment_lab`: 19/19 pass after two compat repairs to the
  in-progress output-type feature (new dataclass fields moved to the end of
  `LoopContract`/`LoopConfig` to restore positional construction; single-
  output synthesis guarded to string outputs). `ReactiveWorkerOutcome`
  carries `underlying_error` so rows name the real failure.
- `devtools/embodiment_axes`: `registry.py check` ok (30 embodiments,
  7 families); `registry.py run` reproduces the committed finding
  (monolith/full_history fail at horizon 256; 53 solved rows).

## Gates

`--conformance` ALL PASS, `--repo-conformance` passed, recipe/process/
reactive checks 41/41, 11/11, 47/47. All edits uncommitted, staged for
owner review. Temp run dirs removed.

## Full engine health, 2026-09-10 (continued testing)

- `--self-test`: PASSED, 3742/3742, 424 s, 0 provider calls. (Up from the
  3412 recorded on 09-08; new modules since then.)
- Found and fixed: the suite crashed with `KeyError: 'tests'` because the
  new `core.harness_remaining_recipe_checks` returns a flat
  `{check: bool}` dict while the fold requires `{"tests": [...]}`. The
  fold now accepts the flat bool shape and still fails loudly on anything
  else. Every check in the repo runs; none are silently skipped.
- Product acceptance (`examples/22_product_quickstart`, fixture model
  semantics, real Docker effects): 4/4 COMPLETED_VERIFIED, both negative
  controls pass, repair path reproduced and verified.

## Task-database campaign staging, 2026-09-10 (continued testing)

`/home/username/task_database` holds 8 adapted tasks (gated) + 318 raw
Kaggle downloads (no gates, excluded until adapted). The engine had no
reference to the database; now surveyed.

- All 8 adapted gates validated offline: 7 honestly reject a constant
  predictor; `20-newsgroups-ciphertext-challenge` crashed with
  `_csv.Error: field larger than field limit` (ciphertext quotes) and was
  fixed with `csv.field_size_limit(sys.maxsize)` in its gate.sh, after
  which it rejects honestly too.
- Full task→gate loop proven on the smallest task: constant scores 0.32
  (floor 0.42, rejected), sklearn RandomForest scores 1.00 (accepted).
- `tools/task_campaign.py` (new, offline-validated): list, validate-all
  (8/8 valid), matrix over tasks × configured arms, dry-run that stages
  cells and refuses unknown tasks/arms without contacting any provider.
- Live dispatch (solve per cell via the arm embodiment + authorized route,
  gate.sh as evaluator) is staged, not run: it needs the counted-generation
  route's source-backed capacity.
- Full campaign launched (24 cells: 8 tasks x opencode, pi, goose;
  100 calls/cell, 3-way parallel, standardized report always written).
  Interim pattern: the opencode arm does real data science (a correct
  IsolationForest pipeline for the anomaly task) but emits `solve()`
  instead of the gate's `predict(row)` contract, motivating the staged
  evaluation contract. The pi arm burns
  its budget in orient/next-action repair loops (16 orient attempts,
  mostly schema repairs) and never acts: the small model's
  structured-output compliance, not the budget, is the binding
  constraint there.
- FIRST LIVE GATE PASS: opencode x 20-newsgroups-ciphertext-challenge,
  holdout 1.0000 vs floor 0.0782 (TF-IDF + RandomForest with `predict`,
  produced under the staged contract). It initially failed only because
  the staged gate env lacked pandas (system python); re-gated with the
  data-stack python. Runner gate env fixed for all remaining cells;
  final report reads cell records from disk so corrections persist.

## Live enablement, 2026-09-10 evening (trial and error, all measured)

No capacity number was invented; each was established by probe, with the
transcript as the source record:

- Output ceiling: acceptance sweep `max_tokens` 4096→1048576, all HTTP 200
  (up to 2^31-1 accepted; the server never declares a maximum). The model
  stops naturally after hundreds of tokens in every probe; no server
  truncation was ever observed. Declared 1048576 with that provenance.
- Context window: prompt sweep 8k→200k tokens, all accepted with correct
  short completions (200019 prompt tokens OK). Declared 200000 (below the
  measured 200019).
- Sanctioned `--verify-live-model` on `custom.tactical`:
  `provider_integration_proven: true`, usage complete.

Three live-path defects found and fixed while enabling the first solve:

1. Custom providers could not declare a context window, so the opencode
   recipe refused (`opencode_exact_model_capacity_required`). Settings now
   accept `context_window` (positive int, fail-closed) and build it into
   route capabilities. Checks added (settings 14/14).
2. Declared output (1048576) exceeds the 200k window, so gateway preflight
   refused every harness call. `HarnessGatewayClient` now attaches an
   explicit `ModelOutputAllocation` per attempt: requested = measured
   window minus estimated input, with the semantic call as decision
   provenance; a prompt filling the window is refused, never truncated.
   Checks added (semantic 15/15).
3. Campaign cell dirs exceed the 108-byte unix socket cap, so the relay
   socket never bound (instant harness failure). The runner uses short
   indexed socket dirs with a length guard.

Two environmental confounders identified along the way (not code): /tmp
tmpfs pressure caused transient `ENOSPC/EDQUOT` artifact writes (campaign
runs moved to disk; other sessions' /tmp debris left untouched), and the
run handler swallows adapter exceptions (a second `LOOPERROR`-class blind
spot; surfaced via PYTHONPATH shim, shim removed).

Status: first live harness call through opencode+tactical completed
(`DIRECT_OK`, 1 physical call, usage accounted). Pilot task solve ran
253 s / 30 calls before budget exhaustion; budget raised to 100 for the
full campaign now running (8 tasks x opencode, pi, goose).

## First live campaign cells, 2026-09-10 (continued testing)

- Pilot solve reached 6 passes / 259 loops / 30 calls with real workspace
  artifacts (`explore_data.py`) before budget exhaustion: the loop works,
  the budget was small. Campaign uses 100 calls/cell, 3-way parallel.
- Root-caused the instant harness failure in campaign cells: cell dirs
  exceed the 108-byte unix socket cap, so the relay socket never bound.
  The runner now uses short indexed `--harness-socket-dir` paths with a
  length guard.
- Runner upgrades: staged task.txt carries the machine-checked
  `predict(row)` evaluation contract (hash-recorded); the solver's latest
  `workspace/attempt-*/solution.py` is bridged to the gate dir (recorded,
  never fabricated); `--jobs N` parallelizes independent cells; the
  standardized report (JSON + markdown) is always written.
- First full cell (1-c-qualification x opencode, pre-fix run): 100/100
  calls in 20 min, solution.py produced but without `predict(row)`,
  motivating the contract append above.
- `--self-test` re-run after all live-path edits: PASSED, 3750/3750
  (includes the 8 new settings/semantic checks), 0 provider calls.

## Full campaign result, 2026-09-10 late (24/24 attempted, standardized report)

- In-campaign gates: 0/24. Fifteen cells burned 100/100 calls (~20 min
  each) without a gate pass; closest miss 2022-ucs at 0.5022 vs floor
  0.5263 on all three arms.
- Nine late cells (Kannada, aaiv, ai-assignment x 3 arms) never fought:
  the tactical endpoint went down mid-run (connection refused; it had
  slowed 30x earlier in the evening). Slated for re-run on recovery.
- Separately demonstrated (manual re-gate, same artifacts the opencode
  arm produced live): 20-newsgroups TF-IDF+RandomForest scores 1.0000
  vs floor 0.0782. The arm can solve; the campaign process, not the
  reasoning, failed that cell (bare gate env without pandas, fixed).
- Standing pattern, corrected by artifact audit: arms diverge on
  QUALITY more than activity. Cells yielding a scorable solution.py:
  opencode 4/8, pi 4/8, goose 1/8: pi does act in longer runs (its
  failures are contract/quality: missing predict, low scores), while
  goose rarely acts at all. Gate passes: opencode 2, others 0. The
  repair burn remains the budget killer, but the arm gap is finishing
  quality, not paralysis.
- Watcher self-resolution worked: endpoint recovered ~90 min later, the
  9 unfought cells retried automatically, merged report 24/24 attempted
  with a SECOND gate pass: Kannada-MNIST x opencode, holdout 1.0000 vs
  floor 0.12. Final: 2 passes / 24 cells, both opencode, both perfect
  holdouts. (Runner wart noted: model_calls null on the Kannada cell.
  Its stdout shape evaded the outcome scanner; gate record exact.)

## Paced operation, 2026-09-11 (rate limits after the outage)

- New key stored (0600, outside repos); endpoint healthy at 0.4 s.
- Cross-process throttle in `custom_endpoint._chat_once`: env-gated
  (`LOOP_ENGINE_CALL_SPACING_SECS`, off by default = zero behavior
  change), file-locked shared slot per endpoint, every claim traced
  (timestamp, endpoint, waited seconds). Checks 15/15 including a live
  2 s serialization test. Applies to all custom-endpoint traffic in
  every process; health probes stay unpaced (2 tiny calls per cell).
- Runner passes pacing env into solve subprocesses (it previously
  whitelisted only 3 vars).
- Running now: 2022-ucs (closest miss, 0.5022 vs 0.5263) x 3 arms at
  1 call / 5 min, jobs 1, health gate, 40-call budget (~10 h
  background). Full 22-cell retry at this pace would take weeks, so
  scope is deliberately the nearest misses first.

## Loop sweep, 2026-09-10 late (all aspects and layers)

- 43 modules under `loop/`; 26 carry suites, all green: 372/372
  (approval, atomic, canvas, delegation 26+26, effect approval,
  encapsulate, intelligence loops, kernel 18+27, lens, capsule,
  contract 16, control 19, definition 11, doctrine, handoff, profiles
  12, templates 9, reactive 9, recursive 52, spawned, supervision).
- Contract/config matrix: 7 valid combinations accept (nine/five/custom/
  open x deterministic/hybrid/non-deterministic x single/multiple);
  4 invalid shapes refuse precisely (quota missing on multiple, quota on
  single, unknown output type, stepless custom).
- Cross-role execution verified live: solution and practitioner loops run
  to `success_once` with single-output emission synthesis producing the
  portfolio record.

## Cognitive steps + preloaded intelligence, 2026-09-11 (continued testing)

- New kernel nodes deliberately NOT added: the kernel is a closed
  13-node vocabulary with a handshake contract; new nodes need an ADR
  plus live proof. Per repo pattern, new cognition ships as
  intelligence first, mechanism after evidence.
- Shipped as intelligence: 3 guidance entries (recognize_sufficiency,
  survey_established_facts, stop_on_recurrence), step questions in act
  (+established facts), verify (+sufficiency), decide_next (+failure
  forbids), 2 forms (sufficiency_check, established_facts). Suites:
  portfolio 12/12, engine 8/8, interrogation 8/8.
- Latent test fragility fixed along the way: question_engine self-test
  hardcoded `limit=40`, breaking the day the 41st form arrived; limits
  now scale with form count.
- Paced retry running: 2022-ucs x 3 arms at 1 call / 5 min (shared
  file-locked slot, trace-logged), health-gated, serial.

## Operating correction, 2026-09-11

- Time pressure was operator-invented, not requested: this setup runs
  overnight and thoroughness beats speed. Consequence: no more
  timeout-shrinking, budget-trimming, or deferred verification for the
  sake of the clock. Remaining batches use generous budgets; the full
  suite re-runs over all edits; slow honest measurements beat fast
  partial ones.

## Closed-loop verifier capability, 2026-09-11 (continued building)

- New `core.verifier.execute` capability: runs the operator-declared
  verifier script mid-solve as an observation for replanning (never as
  acceptance). Full vertical: request field + validation, CLI
  `--verifier`, capability definition + admission (sandbox authority +
  declared path), execution op (bash, cwd=verifier dir, bounded
  timeout, minimal env, tailed output), self-test 5/5 folded into the
  suite. Campaign runner passes `--verifier gate.sh` on every cell.
- Conformance held green throughout: new module classified + declared
  as subprocess adapter; over-cap additions relocated (plan outline
  helper to planning) or declared with split plans (solve_runtime →
  SolveVerificationPolicy; acceptance flows → flow fixtures); map
  counts regenerated (core 264).

## Thinking upgrades, 2026-09-11 (continued building)

- New guidance: reflect_before_repeat (no next action without a stated
  lesson), coverage_before_close (verify + calibrate since last
  surprise, else route back). New questions in decide_next (lesson
  first) and route (coverage check).
- Repair exhaustion now carries shapes: ModelResponseRepairStalled has
  step_id/attempts/failure_code/rejected_digests at both raise sites;
  acceptance check pins the contract. Recovery-panel wiring queued
  (needs ladder tracing).
- Plan outlines: every admitted method saves a readable outline
  artifact (how/act/capability/steps/spawned/rationale); failure to
  write degrades to diagnostic, never fails the step. Check pins it
  (acceptance 32/32).

## Folder-task failure, root-caused 2026-09-11 (corrected diagnosis)

- Initial (wrong) story: died in orient on accounting cascade. Retracted:
  the run reached act (104 events), completed atomic code ops vacuously,
  died on handler exceptions. task.txt appears ZERO times in 1269
  events; no listdir/scandir/walk/glob anywhere.
- True chain: pointer task names a folder in prose, but intake created
  no source_refs (no --dataset/--repository flag), so source inspection
  stayed off; workspace.read had nothing to read; only
  core.generated_project was selectable. The run generated code blind
  with nothing to ground it. A coverage failure, not a reasoning one:
  no capability inspects an arbitrary prose-named path.
- Fix applied: relaunched as `--repository <dir> --text <goal>
  --allow-source-to-model`, the intake shape built for exactly this.
- Queued (needs design + security review): prose-named path inference
  as candidate sources (path traversal risk: must not become implicit
  read authority). Queued: vacuous atomic completion counting as
  accepted success (acceptance hole).

## Memory path end-to-end, 2026-09-11 (continued testing)

- Full governance lifecycle exercised live: staged a placeholder
  ("test lesson") → independently reviewed → REJECTED with recorded
  reasoning; staged a real lesson (socket-dir cap) from the
  perfect-score run → reviewed → ACCEPTED → PROMOTED
  (`candidate_promoted`, verifier actor). Every refusal along the way
  (exact identity, unique evidence, reason required) was correct
  behavior, not friction to remove.
- Full reports generate (`--report`: loops, tokens, chain, artifacts,
  material questions, cost, ownership tree). Gap found: the report
  shows run-terminal attempt artifacts, not the best artifact. Our
  perfect solution.py (attempt-1) doesn't appear in its own run's
  report. Queued: best-artifact pointer in reports.
- Canvas confirmed live: solution_controller graphs spawned_by the
  practitioner with definition digests, completing success_once.
  Solutions run on canvas controllers, not just raw scripts.

## Repetition-guard policy, 2026-09-11 (continued building)

- The P0-1 guard is now policy, not just vocabulary: recovery withdraws
  `retry_same_route` after 3 consecutive same-shape failures (counted
  from session results in `_reasoned_recovery`), leaving abandon plus
  refused-novel; the recovery question states the withdrawal and its
  reason. Direction is fail-safe (removes the proven-futile option;
  the model still decides). Checks 9/9; conformance ALL PASS.

## Full-spectrum scorecard, 2026-09-11 (continued proving)

- New `tools/spectrum_score.py`: every aspect scored PASS/ABSENT/FAIL
  per run history (harness, all 13 kernel steps, recovery ladder,
  7 intelligence profiles, fingerprinting, memory, canvas, validators).
- Both scored runs show IDENTICAL missing sets: verify, calibrate,
  integrate_commit; full recovery ladder; code/history/feedback
  intelligence. Deterministic gaps, not noise: the same machinery is
  dark in every run regardless of task, harness, or budget.
- Implication: single-run variety will not light these; they need
  structural triggers (coverage rails, recurrence→ladder wiring,
  join execution, intelligence selection beyond context.serve).
