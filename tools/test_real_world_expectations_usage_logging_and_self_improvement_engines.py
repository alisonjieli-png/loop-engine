"""Unit and conformance tests for Real-World Expectation Calibration, Production Usage
Telemetry, Privacy-Safe Flight-Recorder Logging & 5-Stage Autonomous Self-Improvement Flywheel.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from real_world_expectations_usage_logging_and_self_improvement_engines import (  # noqa: E402
    BASELINE_STATELESS_UNLOGGED_AGENT,
    EIGHT_PRACTICAL_EXPECTATION_DIMENSIONS,
    ENGINE_FIVE_STAGE_SELF_IMPROVEMENT_FLYWHEEL,
    ENGINE_PRE_TASK_EXPECTATION_CALIBRATOR,
    ENGINE_PRIVACY_SAFE_FLIGHT_RECORDER,
    ENGINE_USAGE_FRICTION_AND_GAP_DETECTOR,
    FIVE_SELF_IMPROVEMENT_STAGES,
    OBSERVED_THIN_ADAPTER_LOC,
    SIX_EXPECTATION_GAP_SIGNALS,
    SLOT_EXPECTATION_AND_USAGE_CALIBRATION,
    SLOT_USAGE_LOGGING_AND_SELF_IMPROVEMENT,
    SUITE_BALTOR_EXPECTATION_FLIGHT_RECORDER_SI,
    SUPPORTED_2026_MODELS,
    RealWorldExpectationCalibrationRequest,
    UsageLoggingAndSelfImprovementRequest,
    contains_unredacted_secret_or_pii,
    create_expectation_calibration_adapter,
    create_usage_logging_and_self_improvement_adapter,
    run_known_wrong_controls,
    run_real_world_expectation_and_usage_calibration_slot,
    run_real_world_expectations_logging_and_self_improvement_benchmark,
    run_structured_usage_logging_and_self_improvement_slot,
    scrub_secrets_and_pii,
)


class RealWorldExpectationsLoggingAndSelfImprovementTest(unittest.TestCase):
    """Verifies Slot Family 1, Slot Family 2, 7-layer ComponentEnvelope, ThinComponentAdapter,
    45-session 3-epoch benchmark, and 4 known-wrong preflight refusal controls.
    """

    def test_eight_expectation_dimensions_and_pre_task_calibrator(self) -> None:
        self.assertEqual(len(EIGHT_PRACTICAL_EXPECTATION_DIMENSIONS), 8)
        adapter = create_expectation_calibration_adapter()
        info = adapter.inspect_contract()
        self.assertEqual(info["slot_id"], SLOT_EXPECTATION_AND_USAGE_CALIBRATION)
        self.assertLess(int(info["adapter_loc"]), 30)
        self.assertEqual(int(info["adapter_loc"]), OBSERVED_THIN_ADAPTER_LOC)

        req = RealWorldExpectationCalibrationRequest(
            request_id="test_cal_01",
            surface_host="baltor.ai",
            task_archetype="live_subdomain_deployment",
            user_prompt_summary="Deploy and verify HTTPS 200 on baltor.ai.",
            latency_tier="interactive_sub_second",
            cost_ceiling_usd=0.03,
            requires_live_deployment=True,
            live_https_200_verified=True,
            attempt_mark_completed=True,
            payload_target_bytes=524_288,
        )
        res = adapter.execute(req)
        self.assertTrue(res.ok)
        self.assertTrue(adapter.verify_receipt(res))
        self.assertEqual(res.selected_engine, ENGINE_PRE_TASK_EXPECTATION_CALIBRATOR)
        contract = res.expectation_contract
        self.assertIsNotNone(contract)
        assert contract is not None
        self.assertEqual(contract.latency_ceiling_ms, 800)
        self.assertTrue(contract.zero_gpu_deterministic_first)
        self.assertEqual(
            contract.autonomy_and_interruption_tolerance,
            "zero_questions_autonomous_decide_and_document",
        )
        self.assertEqual(
            contract.deliverable_completeness_standard,
            "live_deployed_and_http_200_verified",
        )
        self.assertIn("524288_bytes", contract.elastic_payload_and_file_length_allowance)
        self.assertEqual(res.detected_expectation_gap_codes, ())
        self.assertTrue(res.expectation_fulfilled_first_attempt)

    def test_six_real_world_expectation_gap_signals_detection_and_engine_swap(self) -> None:
        self.assertEqual(len(SIX_EXPECTATION_GAP_SIGNALS), 6)
        adapter = create_expectation_calibration_adapter().swap_engine(ENGINE_USAGE_FRICTION_AND_GAP_DETECTOR)
        req = RealWorldExpectationCalibrationRequest(
            request_id="test_gaps_all_6",
            surface_host="agentfeeds.si",
            task_archetype="feed_pipeline_sync",
            user_prompt_summary="Why is the feed endpoint still broken?",
            latency_tier="interactive_sub_second",
            requires_live_deployment=True,
            live_https_200_verified=False,
            attempt_mark_completed=False,
            observed_turn_telemetry={
                "requires_live_deployment": True,
                "live_endpoint_probed": False,
                "human_follow_up_frustration_prompt": True,
                "post_turn_human_edit_distance": 42,
                "wall_clock_ms": 4_500.0,
                "asked_unnecessary_clarification_question": True,
                "nerfed_sandbox_tool_proposed": True,
            },
        )
        res = adapter.execute(req)
        self.assertTrue(res.ok)
        self.assertEqual(res.selected_engine, ENGINE_USAGE_FRICTION_AND_GAP_DETECTOR)
        self.assertEqual(len(res.detected_expectation_gap_codes), 6)
        self.assertEqual(set(res.detected_expectation_gap_codes), set(SIX_EXPECTATION_GAP_SIGNALS.keys()))
        self.assertFalse(res.expectation_fulfilled_first_attempt)

    def test_slot_1_and_slot_2_automatic_engine_failover_on_deferral(self) -> None:
        cal_res = run_real_world_expectation_and_usage_calibration_slot(
            RealWorldExpectationCalibrationRequest(
                request_id="test_defer_slot1",
                surface_host="getagentfoundry.si",
                task_archetype="pack_build",
                user_prompt_summary="Build pack.",
                simulate_primary_engine_deferral=True,
            )
        )
        self.assertTrue(cal_res.ok)
        self.assertEqual(cal_res.selected_engine, ENGINE_USAGE_FRICTION_AND_GAP_DETECTOR)
        self.assertEqual(
            cal_res.attempted_engines,
            (ENGINE_PRE_TASK_EXPECTATION_CALIBRATOR, ENGINE_USAGE_FRICTION_AND_GAP_DETECTOR),
        )

        log_res = run_structured_usage_logging_and_self_improvement_slot(
            UsageLoggingAndSelfImprovementRequest(
                request_id="test_defer_slot2",
                trace_id="trace_defer_02",
                surface_host="agentafk.si",
                task_archetype="afk_worker",
                expectation_contract_digest="sha256:abcdef0123456789",
                selected_slot_id=SLOT_EXPECTATION_AND_USAGE_CALIBRATION,
                selected_engine_id=ENGINE_PRE_TASK_EXPECTATION_CALIBRATOR,
                cascade_stage_exit="S1",
                wall_clock_ms=120.0,
                mem_peak_mb=32.0,
                tokens_in=200,
                tokens_out=80,
                cost_usd=0.0005,
                verifier_passed=True,
                live_endpoint_probed=True,
                expectation_gap_codes=(),
                human_satisfaction_proxy_score=0.99,
                raw_diagnostic_note="Normal telemetry note.",
                simulate_primary_engine_deferral=True,
            )
        )
        self.assertTrue(log_res.ok)
        self.assertEqual(log_res.selected_engine, ENGINE_FIVE_STAGE_SELF_IMPROVEMENT_FLYWHEEL)
        self.assertEqual(
            log_res.attempted_engines,
            (ENGINE_PRIVACY_SAFE_FLIGHT_RECORDER, ENGINE_FIVE_STAGE_SELF_IMPROVEMENT_FLYWHEEL),
        )

    def test_privacy_safe_flight_recorder_and_five_stage_flywheel(self) -> None:
        self.assertEqual(len(FIVE_SELF_IMPROVEMENT_STAGES), 5)
        self.assertIn("Qwen 3.5", SUPPORTED_2026_MODELS)
        self.assertIn("Gemma 4", SUPPORTED_2026_MODELS)
        self.assertIn("GLM-5.3", SUPPORTED_2026_MODELS)
        self.assertIn("Kimi 3", SUPPORTED_2026_MODELS)
        self.assertIn("Claude Fable 5.1", SUPPORTED_2026_MODELS)

        raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 api_key=sk-proj1234567890 user=founder@baltor.ai"
        scrubbed, count = scrub_secrets_and_pii(raw)
        self.assertGreaterEqual(count, 3)
        self.assertFalse(contains_unredacted_secret_or_pii(scrubbed))

        adapter = create_usage_logging_and_self_improvement_adapter()
        req = UsageLoggingAndSelfImprovementRequest(
            request_id="test_flywheel_01",
            trace_id="trace_fw_001",
            surface_host="agentstudios.si",
            task_archetype="3d_scene_publish",
            expectation_contract_digest="sha256:1234567890abcdef",
            selected_slot_id=SLOT_EXPECTATION_AND_USAGE_CALIBRATION,
            selected_engine_id=ENGINE_PRE_TASK_EXPECTATION_CALIBRATOR,
            cascade_stage_exit="S2",
            wall_clock_ms=210.0,
            mem_peak_mb=48.0,
            tokens_in=512,
            tokens_out=256,
            cost_usd=0.0014,
            verifier_passed=True,
            live_endpoint_probed=True,
            expectation_gap_codes=("G1_local_only_artifact_when_live_deployment_expected",),
            human_satisfaction_proxy_score=0.77,
            raw_diagnostic_note=raw,
        )
        res = adapter.execute(req)
        self.assertTrue(res.ok)
        self.assertTrue(adapter.verify_receipt(res))
        self.assertEqual(res.secret_leakage_rate_pct, 0.0)
        entry = res.flight_recorder_entry
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertFalse(contains_unredacted_secret_or_pii(entry.redacted_payload_summary))
        self.assertEqual(len(entry.entry_sha256), 64)

        fw = res.flywheel_cycle_report
        self.assertIsNotNone(fw)
        assert fw is not None
        self.assertEqual(fw.stages_completed, FIVE_SELF_IMPROVEMENT_STAGES)
        self.assertNotEqual(fw.stage_4_worker_id, fw.stage_4_independent_verifier_id)
        self.assertEqual(fw.stage_5_feed_channel, "agentfeeds.si/self-improvement")

    def test_45_session_3_epoch_benchmark_metrics(self) -> None:
        bench = run_real_world_expectations_logging_and_self_improvement_benchmark()
        self.assertEqual(bench["total_sessions"], 45)
        self.assertEqual(bench["epochs_evaluated"], 3)
        self.assertEqual(bench["sessions_per_epoch"], 15)
        self.assertTrue(bench["all_45_sessions_executed_through_7_layer_envelope"])

        baseline = bench["stateless_unlogged_agent_repeating_same_mistakes_baseline"]
        self.assertEqual(baseline["engine_id"], BASELINE_STATELESS_UNLOGGED_AGENT)
        self.assertEqual(baseline["expectation_gap_rate_pct"], "37.8%")
        self.assertEqual(baseline["structured_flight_recorder_logs_emitted"], 0)
        self.assertEqual(baseline["human_reprompt_or_bailout_rate_pct"], "28.9%")

        suite = bench["baltor_real_world_expectation_flight_recorder_and_self_improvement_suite"]
        self.assertEqual(suite["engine_id"], SUITE_BALTOR_EXPECTATION_FLIGHT_RECORDER_SI)
        self.assertEqual(suite["structured_pii_safe_logging_coverage_pct"], "100.0%")
        self.assertEqual(suite["secret_and_pii_leakage_rate_pct"], "0.0%")
        self.assertAlmostEqual(float(suite["mean_logging_overhead_ms"]), 0.19, places=2)
        self.assertEqual(suite["epoch_1_baseline_expectation_gap_rate_pct"], "24.4%")
        self.assertEqual(suite["epoch_2_log_driven_patch_expectation_gap_rate_pct"], "4.4%")
        self.assertEqual(suite["epoch_3_crystallized_expectation_aligned_gap_rate_pct"], "0.0%")
        self.assertEqual(suite["first_attempt_expectation_fulfillment_pct"], "97.8%")
        self.assertEqual(suite["repeated_class_of_failure_incidents_once_logged"], 0)
        self.assertTrue(suite["sha256_hash_chain_verified"])

    def test_four_known_wrong_controls(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "unredacted_secret_or_pii_in_usage_log_refused",
            "local_only_completion_for_live_surface_refused",
            "self_improvement_replay_regression_refused",
            "unbounded_usage_log_spool_refused",
        }
        actual_codes = {c["actual_refusal_code"] for c in kw["controls"]}
        self.assertEqual(actual_codes, expected_codes)
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertTrue(ctrl["refused_before_engine"])


if __name__ == "__main__":
    unittest.main()
