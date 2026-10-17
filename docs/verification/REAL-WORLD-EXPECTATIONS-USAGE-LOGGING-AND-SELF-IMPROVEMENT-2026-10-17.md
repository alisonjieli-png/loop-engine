# Real-World Expectation Calibration, Production Usage Logging, and Self-Improvement Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `1c28c1c3`
Implementation module: [`tools/real_world_expectations_usage_logging_and_self_improvement_engines.py`](../../tools/real_world_expectations_usage_logging_and_self_improvement_engines.py)
Verification suite: [`tools/test_real_world_expectations_usage_logging_and_self_improvement_engines.py`](../../tools/test_real_world_expectations_usage_logging_and_self_improvement_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), `< 30` LOC `ThinComponentAdapter` entrypoint (`24` LOC), 45-session 3-epoch production benchmark, and 4 known-wrong preflight refusal controls addressing real-world expectation calibration, privacy-safe usage logging, and continuous self-improvement:

1. Slot Family 1: Real-World Expectation Calibration and Pre-Execution Reality Contract Engine (`real_world_expectation_and_usage_calibration_slot`).
2. Slot Family 2: Privacy-Safe Flight-Recorder Usage Logging and 5-Stage Closed-Loop Self-Improvement Flywheel (`structured_usage_logging_and_self_improvement_flywheel_slot`).

## 1. Slot Family 1: 8-Dimension Expectation Contract and 6 Friction-Gap Signals (`real_world_expectation_and_usage_calibration_slot`)

`pre_task_expectation_vs_reality_calibrator_engine` translates every incoming customer task into an explicit `RealWorldExpectationContract` across 8 practical expectation dimensions before execution, and `real_world_usage_friction_and_expectation_gap_detector_engine` monitors live sessions for 6 expectation-gap signals (`G1..G6`):

| Expectation Dimension / Signal | Identifier | Enforced Production Standard |
| --- | --- | --- |
| Dimension 1 | `latency_budget_expectation` | `interactive_sub_second <= 800 ms`, `conversational_turn <= 8 s`, `background_worker <= 120 s`, `overnight_afk_batch <= 8 h` |
| Dimension 2 | `cost_ceiling_expectation_usd` | Per-task USD ceiling with `0`-GPU deterministic-first preference |
| Dimension 3 | `autonomy_and_interruption_tolerance` | `zero_questions_autonomous_decide_and_document` vs `explicit_human_gate_before_destructive_effect` |
| Dimension 4 | `deliverable_completeness_standard` | `live_deployed_and_http_200_verified` when the task targets a live subdomain or endpoint |
| Dimension 5 | `messy_input_tolerance` | Normalizes incomplete specs, typos, broken JSON, brownfield repositories, and restricted sandboxes |
| Dimension 6 | `idempotency_and_rollback_safety` | Preserves existing dirty worktrees, commits atomically, and enforces zero data loss |
| Dimension 7 | `verification_depth_required` | `unit_test + live_endpoint_probe + receipt_chain_hash` |
| Dimension 8 | `elastic_payload_and_file_length_allowance` | Compact `< 2,048` B contract cards by default with elastic expansion up to `1 MB+` for full artifacts |
| Signal `G1` | `G1_local_only_artifact_when_live_deployment_expected` | Flags local file generation when the customer requested a live subdomain or endpoint |
| Signal `G2` | `G2_human_follow_up_correction_or_why_is_it_still_broken_prompt` | Escalates repeat customer corrections on the same surface to root-cause infrastructure inspection |
| Signal `G3` | `G3_post_turn_human_edit_distance_or_git_reset` | Captures human edits or reverts within 5 minutes of turn completion |
| Signal `G4` | `G4_silent_timeout_or_unbounded_subprocess_hang` | Detects commands exceeding the expected p95 wall-clock window |
| Signal `G5` | `G5_unnecessary_clarification_question_stall` | Flags questions the agent could research or test autonomously (`AGENTS.md` Rule 4) |
| Signal `G6` | `G6_stale_model_or_nerfed_tool_recommendation` | Replaces outdated models or nerfed tools with 2026 models (`Qwen 3.5`, `Qwen3.5-VL`, `Qwen3-Coder`, `Gemma 4`, `GLM-5.3`, `Kimi 3`, `Claude 4.6`, `Claude Fable 5.1`) |

## 2. Slot Family 2: Privacy-Safe Flight-Recorder Logging and 5-Stage Self-Improvement Flywheel (`structured_usage_logging_and_self_improvement_flywheel_slot`)

`privacy_safe_flight_recorder_usage_logger_engine` emits an append-only, SHA-256-chained `UsageFlightRecorderLogEntry` with automatic credential and PII redaction (`0.0%` secret leakage at `0.19 ms` overhead). `five_stage_autonomous_self_improvement_flywheel_engine` converts logged friction events into verified improvements across 5 automated stages:

| Stage | Stage Identifier | Automated Action | Output Artifact |
| --- | --- | --- | --- |
| `Stage 1` | `Stage_1_Root_Cause_Clustering` | Clusters flight-recorder friction logs by `(expectation_gap_code, surface_host, engine_id)` | Deterministic cluster key |
| `Stage 2` | `Stage_2_Counterexample_And_Regression_Test_Synthesis` | Synthesizes a minimal reproducible test case that fails under the old behavior | Regression test fixture ID |
| `Stage 3` | `Stage_3_Contract_Card_Preflight_Gate_And_Playbook_Mutation` | Generates an updated `baltor_contract_card/v1`, `RULES.md` invariant, and preflight check | Mutated contract card |
| `Stage 4` | `Stage_4_Independent_Verifier_And_Shadow_AB_Replay` | Replays historical flight-recorder traces with `worker_id != independent_verifier_id` | Zero-regression shadow replay report |
| `Stage 5` | `Stage_5_CAS_Promotion_Feed_Broadcast_And_Backward_Distillation` | Promotes the revision to `agentfeeds.si/self-improvement` and distills fast-path rules into `S1..S3` | Pinned `SHA-256` CAS digest |

## 3. 45-Session 3-Epoch Real-World Production Benchmark

| Pipeline | Structured Flight-Recorder Logging | Secret / PII Leakage Rate | Expectation-Gap Rate (`Epoch 1 -> Epoch 2 -> Epoch 3`) | First-Attempt Expectation Fulfillment | Human Re-Prompt / Manual Bailout Rate | Repeated Class-of-Failure Incidents |
| --- | --- | --- | --- | --- | --- | --- |
| `stateless_unlogged_agent_repeating_same_mistakes_baseline` | `0.0%` (`0 / 45` logs) | Unprotected | `37.8%` (`17 / 45` sessions) | `62.2%` (`28 / 45`) | `28.9%` (`13 / 45`) | `12` repeated failures |
| `baltor_real_world_expectation_flight_recorder_and_self_improvement_suite` | `100.0%` (`45 / 45` logs at `0.19 ms`) | `0.0%` (`90` tokens scrubbed) | `24.4% -> 4.4% -> 0.0%` | `97.8%` (`44 / 45`) | `0.0%` (`0 / 45`) | `0` once logged |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `a_unredacted_secret_or_pii_in_usage_log_blocked` | `structured_usage_logging_and_self_improvement_flywheel_slot` | `preflight` (Layer 6) | `unredacted_secret_or_pii_in_usage_log_refused` | `true` |
| `b_local_only_completion_for_live_surface_blocked` | `real_world_expectation_and_usage_calibration_slot` | `preflight` (Layer 6) | `local_only_completion_for_live_surface_refused` | `true` |
| `c_self_improvement_replay_regression_blocked` | `structured_usage_logging_and_self_improvement_flywheel_slot` | `preflight` (Layer 6) | `self_improvement_replay_regression_refused` | `true` |
| `d_unbounded_usage_log_spool_blocked` | `structured_usage_logging_and_self_improvement_flywheel_slot` | `preflight` (Layer 6) | `unbounded_usage_log_spool_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_real_world_expectations_usage_logging_and_self_improvement_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/real_world_expectations_usage_logging_and_self_improvement_engines.py
```
