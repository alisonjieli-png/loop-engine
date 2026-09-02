# Everything Is a Loop: audit report, 2026-09-01

> **Point-in-time record.** This report describes the tree as it stood on its
> own date. Several findings below were closed afterwards; see
> `docs/verification/LIVE-KAGGLE-DIAGNOSTIC-2026-09-02.md` for what changed and
> which items no longer stand. Nothing here has been edited after the fact.

This report answers the mandate in `docs/prompts/LOOP-ENGINE-EVERYTHING-IS-A-LOOP-ADVERSARIAL-AUDIT.md`
against the working tree on 2026-09-01. The machine-readable scorecard is
`docs/evidence/everything-is-a-loop-audit-2026-09-01.json` (one row per question,
with verdict, severity, evidence, and the row's author).

## 1. Commit and environment

- Base commit `517e321e52e0` (`517e321e52e0c3d0dc7e1c53448499203f37dc59`) with uncommitted edits from the
  same day in the worktree; two other coding agents were active in the tree.
- Python 3.10 virtual environment, Docker 29.5.2 with the pinned sandbox image present.
- Providers by reference: `OLLAMA_API_KEY` present; Mistral, Tactical Engineering, and OpenRouter absent.
- Harnesses installed: Codex 0.151.0, OpenCode 1.18.25, Claude Code 2.1.257, Hermes 0.20.1, Aider 0.86.2.
  None was run for the benchmark (PR-20 NOT_EXECUTED); the account session limit ended four of the five
  auditor sessions mid-report.

## 2. The thesis as found

Which analogy the code earns. Not Python's "everything is an object": Python gets uniformity by letting
you subclass `object`, while Loop Engine gets it by refusing subclassing (`_LoopMeta`) and pushing every
variation into data (`LoopDefinition`, profiles, modes, relationships). The code earns the Erlang and
Kubernetes analogies more honestly: one process type with supervision and restart rungs, one reconcile
loop with declared conditions. What is new against the lineages in the mandate's section 1.4 is narrow
and real: one unit whose realization may be deterministic code, a gateway model call, a human answer,
or now a remote process, all under the same typed contract, evidence, and terminal vocabulary, with a
recorded path from model-led work to promoted deterministic capability. What is not yet new: the
distribution story (ids are process-local counters, there is no addressing or merge beyond the handoff
added today), the versioning story (definition versions are inert, 738 hand-spelled `/vN` strings), and
the learning story (no saved run has read a lesson a previous run wrote).

## 3. Scorecard

180 questions. Verdicts: ABSENT 20, CONTRADICTED 7, EXISTS 4, IMPLEMENTED_UNPROVEN 16, NEEDED 15, NOT_APPLICABLE 1, NOT_NEEDED 1, PARTIAL 83, PROVEN 33.
Severity: critical 1, high 48, low 26, medium 105.

| Section | Questions | PROVEN | IMPLEMENTED_UNPROVEN | PARTIAL | ABSENT | CONTRADICTED | EXISTS | NEEDED | NOT_NEEDED | NOT_APPLICABLE |
|---|---|---|---|---|---|---|---|---|---|---|
| 3. The invariant | 25 | 11 | 4 | 8 |  | 2 |  |  |  |  |
| 4. Four data actions | 10 |  |  | 7 | 2 | 1 |  |  |  |  |
| 5. Ports, edges, handshakes | 10 | 1 |  | 7 | 1 | 1 |  |  |  |  |
| 6. Modes and distillation | 13 | 2 |  | 7 | 3 | 1 |  |  |  |  |
| 7. Shortcuts and fingerprints | 11 |  |  | 6 | 5 |  |  |  |  |  |
| 8. Context and canvas | 10 | 2 | 3 | 4 | 1 |  |  |  |  |  |
| 9. Tools and hooks | 8 |  | 2 | 6 |  |  |  |  |  |  |
| 10. Supervisors and budgets | 10 |  | 1 | 7 | 1 | 1 |  |  |  |  |
| 11. Communication fabric | 15 | 2 |  | 11 | 2 |  |  |  |  |  |
| 12. Learning and experiments | 12 |  | 1 | 7 | 3 | 1 |  |  |  |  |
| 13. Information theory and cost | 10 | 5 | 1 | 4 |  |  |  |  |  |  |
| 14. Humans in the loop | 8 | 2 |  | 5 | 1 |  |  |  |  |  |
| 15. Structures still needed | 20 |  |  |  |  |  | 4 | 15 | 1 |  |
| 16. Harness comparison | 7 | 1 | 1 | 3 | 1 |  |  |  |  | 1 |
| 17. Safety and honesty | 11 | 7 | 3 | 1 |  |  |  |  |  |  |

Rows for sections 3, 8, 9, 13, and 17 were written by the coordinator from the auditors' probe outputs on
disk and from changes made and tested in this session; the other sections are the auditors' own rows.

### Contradicted claims

- **3.7** (high). architecture.yaml says every semantic value is a logical Loop while LE-NODE-008 keeps primitives inside a Loop; atomic primitives exist, cost 5333x wall, and no decision record says which rule wins.
- **3.9** (high). Over 1000 inputs a one-shot Loop matched the function on every accepted run at 657x wall and 2.2 KB ledger, but the 12 runs whose handler raised left the Loop with no terminal event.
- **4.8** (high). The approval path is fail-closed for token, effect-digest and single-consume checks, but the decision inside a serialized approval state is unauthenticated (a forged decided state is accepted by any service that has not seen the request) and any code holding the ledger can record an effect, approval or model call that never happened, so the ledger's claim to be 'everything that happened' is contradicted.
- **5.4** (high). Definitions have a semver field and a content digest, and the graph registry encodes 'one digest per id@version', but at runtime every definition is version 1.0.0 while digests vary freely (16 digests for one id@version), no rule says when a change needs a new version versus a new digest, and no requalification concept exists.
- **6.11** (high). No deterministic handler was caught calling a model, but the runtime cannot catch one: a deterministic-only Loop accepts a step that declares a model call, and a handler body that calls a gateway directly is reported as deterministic with 0 calls, so the invariant is asserted by comments, not enforced.
- **10.3** (high). Ladder and threshold exist and the receipt is in kernel events.jsonl, but the owner Practitioner Loop terminates ACCEPTED/done for a kernel run that routed stop_unprofitable (probe B), a fixture progressing one fact per 4 passes triggered 9 escalations in 40 budgeted passes because cold_restart itself changes the progress key (probe E), and escalation pseudo-records are counted as passes (49 reported for max_passes=40).
- **12.9** (high). run_parallel with join_policy=ensemble blended a numeric and a textual branch with no output-contract compatibility check and no independent verification, which the mandate says must not happen.

## 4. Probe results

| Probe | Status | Evidence |
|---|---|---|
| PR-01 function equivalence | ran | 1000 inputs, outputs equal on 988 accepted runs, 657x wall, 5 events and 2.2 KB per Loop; 12 handler exceptions left Loops with no terminal event |
| PR-02 identical failure churn | ran | stops `no_progress` / BLOCKED after 3 identical failures, 12 events |
| PR-03 runaway spawn | ran | typed refusal at depth 129 naming the 128 guard |
| PR-04 coercion visibility | ran | coercion recorded on init and spawn events |
| PR-05 fabricated recovery | ran | no fabricated outcome; failed final step now VERIFICATION_REJECTED |
| PR-06 kernel structure | ran | ten kernel nodes inside the owner's act step; other owner steps labelled structural_boundary |
| PR-07 atomic overhead | ran | 9 events, 3.5 KB, 5333x to 6433x wall per string join; fusion flag has no consumer |
| PR-08 context boundary | ran | requests at the window pass, over it refused before the network |
| PR-09 packet duplication | ran | 70 budget trims on the live run; static text still re-sent per call |
| PR-10 warm zero-model reuse | ran (auditor) | offline ladder completes with zero warm calls; counter is handler-declared, not gateway-observed |
| PR-11 elbow distillation | not runnable | no realization binding lets a deterministic realization share the model-led contract identity |
| PR-12 summer shortcut | ran (auditor) | byte-identical task matches by digest offline; no precondition or negative-evidence record existed (region statistics and advisory shortcut added today) |
| PR-13 canvas edit from incumbent | read only | packets carry attempt history; edit-versus-restart not measured |
| PR-14 tool parity | ran (auditor) | deterministic tool receipts captured; model-led path not diffed |
| PR-15 supervisor | ran (auditor) | detection, injection, soft reset, cold restart, stop recorded in kernel events; owner Loop terminal previously ACCEPTED regardless (fixed by done_failed) |
| PR-16 two-process handoff | ran | remote Loop in a subprocess, namespaced ids, digest verified, duplicate and tampered envelopes refused, merged chain intact |
| PR-17 crash mid-lease | ran (auditor) | see fabric scorecard 11.5 |
| PR-18 portfolio P2 and P8 | ran (auditor) | P2 offline with zero calls; lineage between candidates, graph versions, and context packs absent |
| PR-19 token curve | ran (auditor) | the only completed repeat rose 6.1x in prompt tokens; no falling curve exists yet |
| PR-20 harness benchmark | NOT_EXECUTED | inventory only; blocked by session limits and cost |
| PR-21 passive-data scan | ran | 11 record classes with executing methods, 3 invoke a provider port |
| PR-22 alias and version scan | ran (auditor) | 738 `/vN` literals in 190 files, 41 scattered constants |
| PR-23 default copies | ran (auditor) | 243 duplicated defaults, 46 across kinds |
| PR-24 second-loop scan | ran | no violations; sleeps only in the live demo and one asyncio yield |
| PR-25 SIGINT binding | ran (Kaggle agent, mocked) | CANCELLED terminal bound in Run History |

## 5. What was fixed in this session, with tests

| Finding | Change | Regression check |
|---|---|---|
| A failed final step still stopped ACCEPTED (17.1, PR-05) | `done_failed` stop reason maps to VERIFICATION_REJECTED | `failed_step_is_never_fabricated_into_a_recovered_outcome` |
| Direct `spawn()` calls were not counted (3.x accounting) | spawn counts include direct spawns and fold descendants on return | `direct_spawn_calls_are_counted_transitively_on_the_parent_result` |
| Guard constants were not policy (10.x, 15.10) | `SupervisionPolicy` on `LoopConfig` and `KernelRunRequest`, recorded on init | `declared_supervision_policy_governs_stops_and_is_recorded_on_init` |
| No per-call context manifest (8.8, 15.7) | `ContextPackManifest` per packet with trust classes, stored and recorded | `core.context_pack_manifest` self-test, offline solve emits 4 manifests for 4 calls |
| No checklist gate (6.4b, 14.5, 15.17) | `practitioner.checklist` profile, `gated_checklist` template | `clean_checklist_completes_with_zero_model_calls_and_no_spawn` |
| No cross-process merge (4.4, 11.7, PR-16) | `LoopHandoffRequest` and `LoopHandoffEnvelope` with digest and idempotency | two-process self-test in `loop.loop_handoff` |
| Forged approval decisions accepted (4.8) | service-key HMAC `decision_authority` verified on restore, load, consume | `a_hand_built_or_tampered_decision_is_not_authority_in_any_service` |
| Solved runs refused over stale questions (live defect) | solved runs carry `open_questions`; contract refusals labelled | `solved_run_reports_stale_questions_as_open_not_as_a_refusal` |
| No frontier, experiment, or region records (12.x, 7.x, 15.6, 15.8, 15.16) | `task_frontier`, `prompt_experiment`, `task_region_statistics` projections | each module's self-test; live-run projections below |

## 6. Missing abstractions still open

- **15.1**. NEEDED for 57 callables: smallest records are a `ModelCallRequest` (prompt, model, system, temperature, timeout, api_key, backoff, floor_frac, max_attempts, max_output_tokens, output_capability) owned by core/model_gateway.py and consumed by the three provider
- **15.2**. NEEDED: one passive `RecordSchemaEntry {record_type, current_version, readable_versions, owner_module, reader_ref}` table in core (beside event_vocabulary.py) plus a conformance scan asserting every `*/vN` literal resolves to an entry; the semantic data dictio
- **15.3**. NEEDED: a `DefinitionVersionPolicy` record naming which canonical-body fields are interface (contract roles, modes, effects, permissions: change => new MINOR/MAJOR and requalification) versus configuration facts (change => new digest under the same version), o
- **15.4**. NEEDED at the Loop-to-Loop boundary only: the existing LoopConnectionResult (producer ref, consumer ref, bindings, violations) must be emitted as a ledger event by code_nodes/solution_canvas.py when an edge is executed, and HarnessAdapterInfo needs a `protocol
- **15.5**. NEEDED: one `LoopMessageEnvelope {schema_version, message_id, activation_id, source_loop_id, causation (loop_id, event_index), idempotency_key, payload_digest, payload}` wrapping pause tokens and spawned checkpoints, owned by loop/recursive_loop.py and shaped
- **15.6**. NEEDED: `ExperimentRecord {experiment_id, hypothesis, task_region_ref, variant_refs, status, horizon, outcome_ref}` and `FrontierItem {item_id, kind, status, horizon, evidence_refs}` as passive catalog records owned by core/intelligence_portfolio.py, reusing t
- **15.8**. NEEDED: `PromptExperimentRecord {prompt_bundle_ref, context_policy_ref, model_route_ref, task_region_ref, run_id, outcome_ref}` owned by core/model_routing_records.py beside ModelOutcomeEvidence, linking pieces that already exist separately. 15.20: passive rec
- **15.9**. NEEDED: `ReuseReceipt {capability_ref, run_id, estimated_tokens_saved, realized_tokens_saved | unknown, baseline_run_ref, accounting_complete}` owned by core/reusable_capability_records.py. 15.20: passive record, no second runtime.
- **15.10**. NEEDED: `SupervisionPolicy {restart_strategy, max_restarts, intensity_window_seconds, escalation, stall_detection_ref}` as an optional LoopProfileSpec field owned by loop/loop_profile_catalog.py. 15.20: profile data, no second runtime.
- **15.12**. NEEDED: a `placement` field (from scheduling.PLACEMENTS) beside `locality` on LoopProfileSpec/LoopDefinition configuration facts, owned by loop/loop_profile_catalog.py with the vocabulary staying in scheduling.py. 15.20: a field on existing profile data, no se
- **15.13**. NEEDED: a `trust_class` enum {model_output, remote_loop_output, tool_output, user_input, retrieved_document, trusted_policy} on LoopValue/LoopPortValue owned by loop/atomic_primitives.py, so tool and remote outputs carry the class prompt slots already have. 15
- **15.14**. NEEDED as a merge, not a new registry: McpToolSpec and extension capability candidates should project into CapabilityHandshake (adding effect_class and requires_approval) so deterministic and model-led modes read one manifest; owner core/capability_directory.p
- **15.16**. NEEDED: `TaskRegionStatistics {region_id, attempts, successes, token_histogram_bins, call_histogram_bins, best_known_settings_ref, updated_at, accounting_complete}` owned by core/task_similarity_engine.py where regions are already keyed. 15.20: derived passive
- **15.17**. NEEDED: `ChecklistProfile {checklist_id, items: (check_ref, action in {gate, escalate, record}), applies_to_profile_ids}` as optional LoopProfileSpec data owned by loop/loop_profile_catalog.py. 15.20: profile data, no second runtime. NOTE: an untracked src/loo
- **15.18**. NEEDED: a canonical `RunCensus {run_id, loops, model_calls, prompt_tokens|unknown, eval_tokens|unknown, effects, unknown_fields}` projected once from RunHistory (owner core/run_history.py) and consumed by loop_report, run_playback and Studio, which today each

Of these, 15.5 (message envelope) and 15.7 (context pack manifest) now have first implementations;
15.6, 15.8, and 15.16 have projection records but no consumer yet.

## 7. Cost table

| Measure | Value | Method |
|---|---|---|
| One-shot Loop over a pure function | 657x wall, 5 events, 2.2 KB | PR-01, 1000 inputs |
| Empty ten-step Loop | 558 us median, 23 events, 8.6 KB | PR no-op, 500 Loops |
| Atomic string join | 9 events, 3.5 KB, 5333x to 6433x wall | PR-07 |
| Saved run ledger | 936 bytes per event, 8.8 events per Loop, 62.6 events per model call | census over saved runs |
| Live Kaggle cell 01 run | 113 calls, 13 passes, 3.80M input tokens, 331k output tokens, 1612 s | adaptive result |
| Live mean input per call | 33.6k provider-reported, 27.7k estimated | model usage and context snapshots |
| Estimate calibration | provider over estimate 1.21 mean, 1.10 to 1.45 by stage | prompt experiment projection |
| Context budget effect | 70 trims, 0 context-window refusals | ledger events |
| Fabric arithmetic | 8128 bytes per Loop activation; one million machines at one Loop per second is about 8 GB per second of ledger | fabric auditor 11.11 |

## 8. Harness comparison

NOT_EXECUTED. All five harnesses are installed (versions in section 1). The benchmark fixture and the
same-commit protocol are defined in the mandate; running it needs a fresh session budget.

## 9. Fabric readiness

| Concern | State |
|---|---|
| Unit of distribution | Loop activation, serialized as a `LoopHandoffRequest` (added today) |
| Identity | process-local counters, namespaced per handoff; not globally unique |
| Addressing and discovery | absent; registries are in-process objects |
| Messages | typed envelope with digest and idempotency key (added today); no transport |
| Leases and fencing | present in the reactive scheduler (fabric scorecard 11.5) |
| Clocks | wall clock plus per-run sequence; no cross-machine logical clock |
| Chain across writers | single writer per run; a handoff merges one remote history into the parent chain |
| Trust boundaries | effect authority is per service key (added today); no tenant policy on inbound Loops |
| Byzantine inputs | remote events are digest-verified, not content-verified |
| Back-pressure and placement | absent |

## 10. The honest sentence

At this commit "everything is a Loop" is true for the executable graph vertex and its terminal
vocabulary, and it is now honest at the edges the review found dishonest a day ago: no fabricated
recovery, no infinite identical churn, no ACCEPTED over a failed final step, no forged approval
authority, and a first real cross-process handoff. It is true only on paper for storage and transfer
(writes and closures carry no Loop identity), for versioning (versions never change while digests do),
and for learning (no run has yet read what another wrote). The single change that would move the most
questions from ABSENT to PROVEN is a consumer for the three new projections: a solve pre-check Loop
that reads region statistics and the frontier of the last run before the first model call, and records
whether it took a shortcut.

## 11. Gates

Round 1 (after the runtime fixes, before the new modules): self-test 1748 of 1749 with one
zero-tolerance failure (18 uses of the retired term "child" in new code, since replaced with
"spawned"); conformance 27 of 27; hardcoding audit blocked on 3 new high findings in new modules (one
None comparison rewritten, two test-fixture literals allowlisted with owner and rationale).

Round 2 (after the new modules): self-test 1766 of 1768 with three zero-tolerance hits from the new
code (the retired term "receipt" in one docstring, an undeclared `subprocess` import in the two-process
handoff proof, and the effect approval module 107 lines over the 800-line cap); conformance failed only
on architecture map freshness after new modules were registered; the audit reported 7 new high findings,
all numeric guards, index offsets, or ledger field-name reads in the new modules. Each was addressed
before round 3: the term replaced, the handoff module declared as a process boundary, a split plan
declared for the approval module, the map regenerated, and the seven literals allowlisted with owner and
rationale under the audit's own classification.

Round 3 (final tree): self-test 1768 of 1768 checks passed in 193 seconds with zero provider calls;
conformance all 27 gates pass; hardcoding audit 800 files, 189,647 literal candidates, 780 high findings
equal to the CI baseline, 140 new medium findings and 3 resolved, no blocking new finding, exit 0.

## 12. Next increment

Wire `recommend_shortcut` and the last frontier snapshot into the solve path as an advisory
pre-check Loop that records its decision, then run three repeats of one task region to produce the
first measured token curve with the shortcut on and off.
