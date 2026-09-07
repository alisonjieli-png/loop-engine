# Improvement plan, 2026-09-07

Source: the execution-verified review in
[`docs/verification/CODE-REVIEW-2026-09-07.md`](../verification/CODE-REVIEW-2026-09-07.md)
(31 findings at `f2e8b15` and `14153a1`), the owner's request of
2026-09-07 to try more configurations and logic paths so the engine can solve
unfamiliar problems and learn from its own runs, and the owner's later
instruction on the same day: build new features, policies, and ways of
running; remove no components.

This file has two jobs. It lists every fix, adjustment, and improvement that
the review supports, with the file it touches and the check that proves it.
It also describes the variation built from those improvements: a second
campaign runner, population, offline check, and audit that live next to the
sealed 2026-09-06 originals without altering them.

Status values: `done` means implemented in this pass with its check passing;
`partial` means part of the change landed and the rest is specified;
`proposed` means specified here and not yet implemented; `decision` means
the owner has to choose before work can start. Every `done` item names the
check that proves it. Finding IDs refer to the review's findings register.
Nothing in this pass removed a component or an option; the one path that now
refuses (reference delivery, B3) never delivered a body, and its build-out is
specified in section 7.

## 1. Loop runtime and admission

| ID | Finding | Change | Files | Check | Status |
|---|---|---|---|---|---|
| B1 | `accepted_success` iterates without a ceiling unless failures are byte-identical | `SupervisionPolicy.unaccepted_passes_before_stop` (default 9, the kernel's three escalations of three passes; policy version 1.1.0). When `max_iterations` is not declared, a Loop that completes that many passes without one accepted success stops as `no_progress` with a `non_progress_stop` ledger event naming the count. A declared `max_iterations` keeps its own meaning | `loop/supervision_policy.py`, `loop/recursive_loop.py` | recursive_loop self-test 47 of 47: distinct failures with no budget stop at 9 as `BLOCKED/no_progress`; third-try success and explicit-budget cases unchanged; supervision self-test 4 of 4 | done |
| B2 | Deeply nested model JSON raises `RecursionError` through admission | `RecursionError` from either JSON decoder is a syntax refusal for that candidate with a `Nesting depth exceeded` diagnostic at offset zero; admission returns a typed failure instead of aborting the run | `core/model_response_admission.py` | admission self-test 18 of 18: 1,500-level object, array, and double-encoded text all refused typed | done |
| B4 | Kernel structural boundaries are emitted as accepted `run_step` events | Now: `StepOutcome.structural_boundary` marks every kernel boundary event with `structural_boundary: true` in the ledger and the step record, so a reader can separate a boundary from an executed step. Next: a boundary event kind of its own, projected to Run History as a boundary, never as an accepted iteration | `loop/recursive_loop.py`, `loop/kernel_runtime.py` | kernel_runtime self-test 27 of 27; the marker appears on the twelve boundary events per kernel run | partial, see section 7 |
| B6 | Duck-typed contract objects are re-typed silently | The coercion record covers any contract-like object: its declared role and mode are a request, and a rewrite of either is recorded on `init` | `loop/recursive_loop.py` | recursive_loop self-test: a legacy object declaring `model_led`/`solution` records `contract_coerced_from` and `contract_coerced_to` | done |
| W1 | Run History accepts forged events in process | First layer: once any Loop on a ledger is bound to a definition, the ledger refuses `run_step`, `terminal`, `iteration_started`, `cancel`, `budget_stop`, `fallback`, `model_boundary_deferred`, and `pause` events for an id no Loop registered. A raw fixture ledger stays permissive. Second layer (section 7): an authority token held by the runtime | `loop/recursive_loop.py` | recursive_loop self-test: a phantom terminal raises `LoopError`; the review probe `probe_e_forge.py` now ends the forged activation `failed` instead of `completed` | done (first layer) |
| W9 | `cancel()` on a terminal Loop appends a `cancel` event after `terminal` | `cancel()` is idempotent on a terminal Loop: no event, no relabel | `loop/recursive_loop.py` | recursive_loop self-test: a second cancel leaves the ledger unchanged; `probe_d_cancel.py` no longer finds a `cancel` after `terminal` | done |
| C10 | Live-demo self-test depends on machine speed | The wait for the real demo run is 600 seconds instead of 180; the check still fails plainly if the run never finishes | `code_nodes/live_run_demo.py` | live_run_demo self-test 6 of 6 | done |

## 2. Adaptive dependency bindings

| ID | Finding | Change | Files | Check | Status |
|---|---|---|---|---|---|
| B3 | Reference delivery is body-inaccessible; `frame.resolvers` is written and never read | `delivery: reference` is refused at plan admission with `binding_disposition: incompatible` and a reason, until a consumer-side materialization capability exists (section 7); the dead `resolvers` field is gone; `value` delivery is unchanged | `core/adaptive_practitioner_bindings.py`, bindings checks | bindings self-test 50 of 50: reference delivery refused before dispatch; an unknown delivery kind refused; the public run dispatches no consumer | done |
| B5 | No size bound on dependency values | `DependencyValuePolicy` (default 262,144 canonical JSON bytes) applied when a producer result is registered; over the bound is `incompatible`; `BoundDependencyInput.value_bytes` and the frame's bound are recorded on the `adaptive_dependency_inputs_bound` event | `core/adaptive_practitioner_bindings.py`, `core/adaptive_practitioner_scope.py`, bindings checks | bindings self-test: a four-byte bound refuses the fixture result; the default bound admits it; the event carries `value_bytes` and `maximum_value_bytes`; scope self-test 36 of 36; planning 40 of 40 | done |
| B7 | A non-binding error from `frame.register` replaces a successful summary with a generic record | Catch `InformationAccessError` beside `DependencyBindingError` in the spawned scope and give it `binding_disposition: incompatible` plus the `adaptive_dependency_output_rejected` event | `core/adaptive_practitioner_scope.py` | scope checks: a producer result with non-string keys yields a typed rejected summary | proposed |

## 3. Reactive worker and scheduler

| ID | Finding | Change | Files | Check | Status |
|---|---|---|---|---|---|
| W2 | Lost primary-key race wedges a SQLite connection | `start()`, `heartbeat()`, `terminal()`, and `recover_expired()` run inside one `BEGIN IMMEDIATE` write transaction with the current record read inside it; any error rolls back; `sqlite3.IntegrityError` becomes a typed revision conflict | `core/reactive_scheduler.py` | scheduler checks 17 of 17: a late terminal after a peer's recovery is typed and the connection claims again; `probe_g_natural_race.py`: no wedged connection over 41 rounds, only typed errors; `probe_b_race.py`: `A_connection_in_transaction_after: false` | done |
| W3 | The worker never renews its lease | `ReactiveWorkerHeartbeatPolicy(interval_seconds, clock)` on `AsyncReactiveWorker`; when set, a background task renews the lease while the handler runs and the outcome counts `heartbeats_sent`; without it, behavior is unchanged and the docstring says the lease must outlast the handler | `core/reactive_worker.py`, worker checks | worker checks 47 of 47: a handler that outlives one interval completes with renewals and a moved expiry; a nonpositive interval is refused | done |
| W4 | `terminal()` checks token possession only | `ActivationTerminalRequest.worker_id`; the scheduler refuses a terminal without a worker name or from a worker that does not hold the lease | `loop/reactive_activation.py`, `core/reactive_scheduler.py`, `core/reactive_worker.py`, checks | scheduler checks: an impostor and an unnamed terminal are refused and the record stays running; `probe_a_lease.py`: `B_terminal_accepted: false` | done |
| W5 | A stale fence at `start()` escapes `run_once`; `run_many` discards siblings | The claim, start, and lookups sit inside the guarded region; a refusal or stale fence becomes a typed FAILED terminal and an outcome with an error code; `run_many` gathers with `return_exceptions=True` and converts exceptions into outcomes | `core/reactive_worker.py` | worker checks: one stale start yields one error outcome beside one accepted sibling | done |
| W6 | "Required" history is a worker flag; `DURABLE_SERIES` is never read | The executor receives the series' registered profile; a `DURABLE_SERIES` profile under a binding without a required history policy fails typed before the handler runs: `HISTORY_POLICY_MISSING_FOR_DURABLE_SERIES`, disposition `unavailable`, no handler call, no approval | `core/reactive_worker.py`, `core/reactive_scheduler.py` (`profile_for`), worker checks | worker checks: the durable refusal; the default binding on an ephemeral profile completes `not_persisted` | done |
| W7 | Post-cancel model usage vanishes from canonical history | `terminal_handler_return` custom events that carry reported model calls project as model invocation events | `core/run_history.py` | run_history self-test 21 of 21; `probe_w7_usage.py`: canonical history shows one model invocation | done |
| W8 | `LEGACY_UNRECORDED` is writable | The disposition is refused in `ActivationTerminalRequest`; only the version 1 reader may produce it | `loop/reactive_activation.py` | scheduler checks: the request raises | done |
| W10 | Canceled and dead-letter records carry false metadata | Observation `status` reads `canceled` or `dead_letter` (added to the runtime observer's vocabulary); a dead letter from a running lease carries `history_disposition: unavailable`; `ReactiveWorkerOutcome.history_error_code` keeps the exception type of a persistence failure | `core/reactive_scheduler.py`, `core/reactive_worker.py`, `core/runtime_observer.py` | scheduler and worker checks; `probe_c_history.py`: `history_disposition_on_dead_letter: unavailable` | done |

## 4. Host boundary and OpenCode bridge

| ID | Finding | Change | Files | Check | Status |
|---|---|---|---|---|---|
| H1 | A callback that raises before any effect wedges the run as "unknown outcome" | Core: after a failed dispatch or a raising callback, the host snapshot is compared with the snapshot before the call; unchanged means a known no-effect outcome (`effect_observed: false`, `error_type` recorded) and later operations proceed; a changed or unreadable snapshot stays unknown. Example: `replace_source` returns a typed refusal for content over 65,536 bytes instead of raising | `core/host_runtime.py`, `core/adaptive_host_runtime_checks.py`, `examples/25_host_runtime/generalization_probe.py` | host_runtime self-test 45 of 45: a mutating failure still blocks; a no-effect failure does not; `probe_g_unknown_outcome.py`: the next valid replace and run succeed | done |
| H2 | Candidate code can read `probe-input.json` and return every case's arguments | `feedback()` caps each observed value at 1,024 canonical bytes with a digest and summary, the same rule the completion gate used; the completion gate reuses it; `probe_arguments` visibility now reads `readable_by_candidate_code_at_execution` | `examples/25_host_runtime/generalization_probe.py` | `probe_h_argument_exfil.py`: 0 of 10 case argument sets in the model-visible record; 99 example tests | done |
| H3 | `harness_text` frames are dropped by the Python bridge | `record_side_frame()` counts `harness_text` digests and any unknown frame kind into the evidence record | `examples/25_host_runtime/opencode_gateway_bridge.py`, bridge test | bridge test: harness text and an unknown kind are counted, known kinds pass through | done |
| H4 | Absolute host paths in model-visible records | An opaque root reference (first 16 hex digits of the SHA-256 of the absolute root) in the scope reference and effect targets; artifact and completion record paths relative to the task root, resolved against the root when checked; older absolute paths still read | `examples/25_host_runtime/generalization_probe.py`, `repair_evidence.py`, tests | `probe_c_leakage.py`: no absolute root path in visible text; 99 example tests including repair evidence and counterexample suites | done |

## 5. The campaign variation

The originals (`novel_task_population.py`, `novel_task_offline_check.py`,
`novel_task_campaign.py`, `novel_task_audit.py`) stay as they are: they are
the record of the 2026-09-06 run. The variation adds four modules and a test:

| ID | Finding | Change | Files | Check | Status |
|---|---|---|---|---|---|
| C1, C3 | Three prompts contradict their oracles; `matrix_spiral` cannot detect a non-spiral; the "unicode" case is ASCII; `word_square` duplicates a case and has no positive 3x3 | Population version 2: prompts and cases agree (commas; `24:00` as the only end-of-day sentinel; the no-leading-zero rule and both signs stated), `spiral_weighted_sum` returns the visit-number weighted sum so order matters, code points 233 and U+1F600 are tested, a positive three-by-three square exists, and the short-word rule is one sentence. 129 cases | `examples/25_host_runtime/novel_task_population_v2.py` | offline check version 2 exit 0; `test_novel_task_v2.py` 12 of 12 | done |
| C2, C5 | The offline check's references encode the case errors; the control tests the reference, not the evaluator | Offline check version 2: references written from the prompt text before the cases were consulted, seven recorded resolutions, and a control that runs the real `evaluate()` through the probe `WORKER` against a deliberately wrong solution per task | `examples/25_host_runtime/novel_task_offline_check_v2.py` | 129 cases, 0 mismatches, 0 control failures, 7 resolutions | done |
| C6 | Population and runner are not digest-bound | Campaign runner version 2 records the SHA-256 of itself, the population, the offline check, and the probe, and rechecks all four before each dispatch | `examples/25_host_runtime/novel_task_campaign_v2.py` | plan output shows four digests; a changed digest refuses before dispatch (test) | done |
| learning | Each task had its own runs directory, so no task could see another's stages | `--shared-runs-dir` puts every task in one Run History root; `--passes N` repeats the population; the report groups calls, tokens, observations, and the region evidence each run saw per pass | `examples/25_host_runtime/novel_task_campaign_v2.py` | plan output; report shape test with two passes | done |
| C7 | The audit runs model code on the host | Audit version 2 takes its campaign root and output as arguments, executes every candidate through the probe `WORKER` in the pinned container, generates valid and invalid inputs, and refuses a source whose digest is not the accepted one | `examples/25_host_runtime/novel_task_audit_v2.py` | tests with a host-Python fixture runner: a right solution passes, a wrong one is invalidated, a drifted digest is refused | done |
| C8 | 93 MB of evidence lives only on tmpfs | `--evidence-out DIR` copies frozen task, observations, outcome, and final source after each task | `examples/25_host_runtime/novel_task_campaign_v2.py` | copy test | done |
| C4, C9 | The campaign report overstates; module text says "invented domains" | A dated corrections section appended to the 2026-09-06 report; README paragraph; version 2 docstrings say textbook tasks with contract twists | `docs/verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md`, `examples/25_host_runtime/README.md` | documentation lint | done |

Experiment arms the variation supports, cheapest first. None has run yet;
each needs an explicit `--authorize-model-calls` grant and live provider
spend.

| Arm | Command shape | Measures |
|---|---|---|
| B | `novel_task_campaign_v2.py --shared-runs-dir --passes 2 --evidence-out DIR` | calls, tokens, and observations per task on pass two against pass one; region evidence consulted |
| C | Arm B plus dependency bindings once reference delivery exists | decomposition benefit |
| D | prompt-experiment variants of the option universe with a control arm | which perspectives earn their place, read through `option_evidence()` |
| E | a third population sealed by an author who never sees the references | held-out generalization |

## 6. Repository gates

| ID | Finding | Change | Status |
|---|---|---|---|
| R1 | CI red on main since 2026-09-02; hardcoding delta at 2,980 new findings | Triage the blocking new high findings in this order: the credential reference in `openai_responses_client.py` (declare the provider in `ModelSettings.providers` with `credential_env`, the audit's named authority, and read the key through that declaration); the 51 URL literals in `docs/research/*.json` (classifier scope or an owned allowlist entry per file); the findings in files from the 2026-09-06 work, by module. Do not weaken the gate or refresh the baseline silently. Add the vale rules to the pre-push routine | proposed |
| R1 | Verification reports cite local counts while CI is red | Every future report cites the CI run for its commit | proposed |
| R2 | Two extra branches on origin | Delete `codex/generalized-adaptive-work-20260906` and `overnight/opencode-step-instances` after confirming nothing on them is missing from main (`git log main..branch`) | decision |

## 7. Designs that need a decision before implementation

- **B4, kernel boundary events.** Introducing a new ledger event kind touches
  the event vocabulary, the semantic dictionary, the Run History projection,
  and every check that counts kernel events. The `structural_boundary` marker
  landed in this pass is additive and honest; the new kind removes the
  accepted `run_step` events altogether. The review recommends the new kind.
- **W1, event authorship.** A per-run authority token held by the runtime and
  passed by its own emit sites, refused when absent, is the smallest change
  that stops a handler from appending a step or model usage it never
  performed for a Loop it does own. It changes the signature of
  `LoopLedger.record` at every runtime call site. The first layer landed in
  this pass closes phantom Loop ids only.
- **B3, reference delivery.** A consumer needs a
  `dependency_input_materialize` capability that resolves an admitted
  reference through the frame's resolver under the consumer's own grant, with
  `DependencyValuePolicy` bounding the body. Until it exists, reference
  delivery is refused typed rather than delivered empty; the option stays in
  the plan vocabulary and the refusal names the reason.
- **R1, allowlist policy.** 192 of the blocking findings are
  closed-vocabulary literals. Either the classifier learns that ledger field
  names and record type strings read from passive records are not behavior
  selectors, or each gets an owned allowlist entry. The former is one change;
  the latter is 192.

## 8. New policies and ways of running, from the overnight solver session

On 2026-09-07 the owner shared a session from a separate solver (the
"overnight" repository) and asked that its ideas be considered here as new
features, policies, and ways of running, without removing anything. Each idea
below is mapped to the Loop Engine boundary that owns it. All are proposed;
none changes an existing default.

| Idea from the session | Loop Engine mapping | Shape of the change | Status |
|---|---|---|---|
| Partial patch application: a patch with one bad field keeps its good fields, and the refused fields are named (`rejected_fields`, `partial`, `accepted`) | `core/model_response_admission.py` today refuses a whole response on `schema_validation_failed` | A `ModelResponseAdmissionPolicy` option `partial_admission` (default off) that admits the fields that validate and returns the refused field names and reasons in the typed result; the planning repair loop reads them so the model repairs only what was refused | proposed |
| Shallow-structure flattening: a dict or list one or two levels deep stored in a string field becomes `k: v; k2: v2` text; deeper structures become capped JSON text | the admission normalization strategies (`_NORMALIZATION_STRATEGIES`) | A new strategy `shallow_structure_flattened` with a depth cap of 2 and a length cap, recorded in the transformation trace like every other strategy; never applied unless the policy lists it | proposed |
| A provisioner ("stagehand") node between steps that proposes per-node grants of skills, files, and a route hint, validated against closed vocabularies, with the engine granting | an Intelligence Loop between kernel passes; `core/skill_registry.py`, `core/capability_directory.py`, the permission scope, and `core/solve_control_manifest.py` | An optional `provisioner` policy in the solve control manifest: before each pass an Intelligence Loop proposes `{skills, files, capabilities, route_hint}` from the registries; the runtime admits only entries the registries hold and the scope permits, records the grant on the ledger, and the pass runs with that context. The grant is data; the Loop that uses it stays the executor | proposed |
| Completion-signal grants: end a node when its patch lands, not when its wall-clock share expires | `exit_condition="accepted_success"` plus the new `unaccepted_passes_before_stop` ceiling; `DelegationBudget` | A `DelegationBudget.completion_signal` field naming the typed record whose arrival ends the spawned Loop, so a node stops on its own evidence and the pass ceiling is the backstop | proposed |
| Queryable cross-node store: every node's patch, tokens, and duration; "how did the metric change" is a query | `core/stage_store.py` and `core/task_region_statistics.py` with a shared runs directory | A `metric_history(runs_dir, region_ref)` query over stage records that returns the sequence of accepted results and their model cost per pass; the campaign runner version 2 already shares the store so the query has data | proposed |
| Route hints honored through a legal-kind check | the option universe and `core/option_selection.py` | Record a model-proposed `route_hint` as an option selection so `option_evidence()` can count whether honored hints correlate with solved runs; no new runtime | proposed |
| More tasks, more datasets, more proofs, A/B of two methods on a second dataset | the campaign version 2 arms in section 5; a Kaggle-shaped population beside the algorithmic one | Arm B first; then a tabular population that mirrors the overnight Spaceship Titanic proof through the existing tabular portfolio example, scored by the same host-owned holdout | proposed |

## 8b. From the "one node per step" design note

The owner also shared a research and design note from a separate build (one
headless OpenCode instance per cognitive step, a typed patch channel, an
engine-run gate, static and model-led composers, adaptive divide-on-failure,
an experience store) and asked that Loop Engine be able to run these ways
too, beside its own streamlined nodes and other harnesses, as configurations
rather than replacements. The mapping below keeps one Loop runtime: every
option is a per-Loop setting, a policy record, or an adapter, never a second
executor.

| Element of the note | Loop Engine boundary that owns it | Configuration to add | Status |
|---|---|---|---|
| One OpenCode process per node, its own agent, skills, tools, and model tier | `core/external_harness_adapters.py`, `core/opencode_harness_adapter.py`, the OpenCode bridge under `examples/25_host_runtime/` | A per-Loop `step_realization` setting with values `native` (the current in-process step), `opencode_instance` (the bridged container instance), and `harness:<name>` for other registered adapters; chosen per spawned assignment, recorded on the ledger, and refused when the named adapter is not registered or quarantined | proposed |
| Streamlined native nodes: orient, understand, locate, decide, plan, build, configure, optimize, verify, observe, decompose, summarize, compose | the reference nine-step and compact five-step profiles in `loop/loop_profile_ontology.py`; kernel nodes in `loop/kernel.py` | Register the note's kinds as Loop profiles with their write scopes as typed output contracts, so a native node and an OpenCode node of the same kind carry the same contract and the same ledger evidence | proposed |
| Typed patch channel (`emit_patch` with a per-node schema; unknown or out-of-scope fields refused, the refusal returned as the next observation) | `core/model_response_admission.py` and the typed ports in `loop/atomic_primitives.py` | The partial-admission policy of section 8, plus a per-kind write scope taken from the profile's output contract; a rejected field is a diagnostic the next pass reads | proposed |
| The engine runs the gate; a self-reported result is never evidence | `core/host_runtime.py` completion verifiers; `adaptive_host_verification.py` | Already the rule here; add a `gate_before` completion check so a task whose acceptance already passes is reported `already_green` without a model call | proposed |
| Composers: static rules, a model-led composer node, hybrid with rule veto; the composer restricts but never grants | the provisioner Loop of section 8 with `core/skill_registry.py` and `core/capability_directory.py` as the closed catalog | `provisioner_policy` values `static`, `model_led`, `hybrid`; grants clamp to the catalog and the permission scope; `manifest.errors` becomes an `option_selection` count so composer quality is measured | proposed |
| Adaptive divide-on-failure with a depth cap and a fan-out cap; divide-first as the alternative | `core/adaptive_practitioner_planning.py` spawned assignments; `SupervisionPolicy.spawn_depth_guard` | A `decomposition_strategy` setting (`adaptive`, `divide_first`) on the solve control manifest with `max_fanout` beside the existing depth guard; the outcome ladder (`verified`, `cause_localised`, `blocked_named`, `narrowed`, `no_progress`, `budget_exhausted`, `void`, `already_green`) maps onto the existing terminal codes as a reporting projection, not new codes | proposed |
| Constant-size prompts: procedure, state slice, latest observation | `core/context_pack_manifest.py`, `core/context_budget.py`, `core/practitioner_runtime_facts.py` | A `context_slicing` policy that names which state fields a kind receives, measured by the packet byte counts the runtime already records | proposed |
| Experience store across nights; composers read verified-rate advice per task signature and kind | `core/stage_store.py`, `core/task_region_statistics.py`, `core/self_tuning.py`, the shared runs directory of section 5 | `option_evidence()` already reads solved and unsolved counts per option; add a per-kind view so a provisioner can read "skills with a verified rate at or above a threshold on at least two observations" for the region | proposed |
| Integrity: hash the gate folder and the run's own record before and after each node; a change voids the run | Run History digest chains, `core/action_fence.py`, the host snapshot in `core/host_runtime.py` | The host snapshot already covers host state; add a `void` terminal projection when a frozen input changes mid-run, which section 1's ledger refusal partly provides | proposed |
| Traps paid for: stdin must not inherit a pipe, per-run data directory, config through the environment, permissions under `--pure` | `examples/25_host_runtime/opencode_stdio_bridge.mjs` and `run_opencode_instance.py` | Carry the four verified traps into the bridge's checks so the quarantine list is verified rather than asserted | proposed |

Read together with section 8: the provisioner, the completion signal, and
the experience view are the same three additions the overnight session
proposed, so both notes converge on one set of new policies.

## 8c. Gaps named by the five-system comparison

On 2026-09-07 the owner shared a feature matrix comparing five systems
(overnight, this repository with its runner branch, the TypeScript Overnight
daemon, the tree solvers, and vigil) and asked whether this engine, meant to
be the most capable, is working correctly. The honest reading from this
pass: the host boundary, approvals, and completion gates held under attack
(review section 11); the defects were runtime honesty and concurrency
(sections 1 to 3 above, now landed) and evidence discipline (the campaign
report, and pushes on a red CI). Several matrix cells marked "not verified"
for this repository are exercised here (the Docker candidate sandbox ran
three live campaigns; the gateway with exact-route failover ran the Kaggle
and campaign calls). The cells where the smaller systems are ahead are
listed below as configurations to add; none replaces an existing path.

| Capability the matrix credits elsewhere | Loop Engine boundary | Configuration to add | Status |
|---|---|---|---|
| OS sandbox around the step that runs model-written code (bwrap: read-only root, hidden homes, no network) | `core/workspace_backends.py` (Docker and restricted local backends) | A `bubblewrap` workspace backend beside Docker, selected per workspace spec, with the same read-only and no-network declarations; Docker stays the default | proposed |
| Regression gates beyond the failing gate: baseline gates before, rerun after, a `verified_narrow` grade when one regresses | `HostRuntimeBinding.completion_verifiers`, `core/adaptive_host_verification.py` | A `baseline_gates` completion policy that records the gate set before the first write and reruns it after acceptance; a regression maps to a distinct terminal projection rather than `task_complete` | proposed |
| Repository instruction files quarantined unless trusted (AGENTS.md, CLAUDE.md, `.claude`, `.opencode`, `.cursorrules`) | `core/practitioner_runtime_facts.py`, `core/context_classification.py` | An `instruction_source_policy` that classifies repository instruction files as untrusted material unless the operator lists them, and records which ones reached a packet | proposed |
| Git protection enforced by the runtime: push, commit, merge, reset, checkout denied to steps; the engine commits | `loop/effect_approval.py`, host `authorize` callbacks | A default `EffectDenyPolicy` record for version-control effects that a host must override explicitly, plus a check that the example hosts never approve them | proposed |
| Hermetic harness configuration per run (private data directory, generated config, no inherited global config) | `examples/25_host_runtime/opencode_stdio_bridge.mjs`, `run_opencode_instance.py` | Already done for the bridge container; carry the four verified traps (stdin, data directory, config through the environment, permissions under `--pure`) into the adapter's registration checks | proposed |
| Per-candidate budget partition so one task cannot starve the night | `core/context_budget.py`, the runner branch's night budget | A `campaign_budget` record on the campaign runner version 2 that partitions calls and minutes per task and pass, recorded in the report | proposed |
| Intake from CI logs, JUnit, Actions runs, and agent transcripts | the runner branch (`overnight/opencode-step-instances`), `templates/intake.py` | Land the runner branch's intake on main as an intake template family after the R2 decision, so main carries every intake path | decision |
| Secret redaction at intake with a tested rule set | `core/brave_search.py` secret providers, the hardcoding audit | A redaction step in `TaskIntakeRequest` admission with a rule set and positive tests, applied before any packet is rendered | proposed |

## 9. Order of work

1. Sections 1 to 4 landed in this pass with their checks; the full local
   gates and the hardcoding delta are recorded in the commit that carries
   this file.
2. Section 5 landed in this pass; the first live arm only on an explicit grant.
3. Section 6 triage as its own change set, so CI can go green without
   mixing it with behavior changes.
4. Sections 7 and 8 after the owner's decisions, one policy at a time, each
   with its own check and its own line in this file.
