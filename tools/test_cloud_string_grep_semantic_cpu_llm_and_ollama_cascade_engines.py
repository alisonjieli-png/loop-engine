"""Unit tests for the Cloud-Facilitated 6-Stage Action & Retrieval Cascade Engine Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from cloud_string_grep_semantic_cpu_llm_and_ollama_cascade_engines import (  # noqa: E402
    ALL_6_CASCADE_STAGES,
    ALL_60_CLOUD_CASCADE_REQUESTS,
    COVERAGE_LAYERS,
    EARLY_EXIT_OPTIMIZER_ENGINE_ORDER,
    ENGINE_ALWAYS_LLM_BASELINE,
    ENGINE_BALTOR_6STAGE_CASCADE,
    ENGINE_EARLY_EXIT_VERIFIER,
    ENGINE_PARETO_TELEMETRY,
    ENGINE_S1_STRING_TRIE,
    ENGINE_S2_GREP_AST,
    ENGINE_S3_SEMANTIC_LSH,
    ENGINE_S4_CLOUD_CPU_LLM,
    ENGINE_S5_OLLAMA_CLOUD,
    ENGINE_S6_FRONTIER_ESCALATION,
    ENGINE_UNVERIFIED_STRING_GREP_BASELINE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    SIX_STAGE_CASCADE_ENGINE_ORDER,
    SLOT_CASCADE_EARLY_EXIT_OPTIMIZER,
    SLOT_SIX_STAGE_CLOUD_CASCADE,
    STAGE_BY_ID,
    CascadeEarlyExitAndTelemetryOptimizerSlot,
    CloudSixStageActionFacilitatorCascadeSlot,
    EnvelopeInvocationRequest,
    run_known_wrong_controls,
    run_six_stage_cloud_cascade_benchmark,
)


class CloudSixStageCascadeEngineSuiteTests(unittest.TestCase):
    def test_six_ordered_stages_specifications_and_latencies(self) -> None:
        self.assertEqual(len(ALL_6_CASCADE_STAGES), 6)
        self.assertEqual(
            SIX_STAGE_CASCADE_ENGINE_ORDER,
            (
                ENGINE_S1_STRING_TRIE,
                ENGINE_S2_GREP_AST,
                ENGINE_S3_SEMANTIC_LSH,
                ENGINE_S4_CLOUD_CPU_LLM,
                ENGINE_S5_OLLAMA_CLOUD,
                ENGINE_S6_FRONTIER_ESCALATION,
            ),
        )
        self.assertAlmostEqual(STAGE_BY_ID["S1"].mean_latency_ms, 0.02)
        self.assertAlmostEqual(STAGE_BY_ID["S2"].mean_latency_ms, 0.18)
        self.assertAlmostEqual(STAGE_BY_ID["S3"].mean_latency_ms, 0.75)
        self.assertAlmostEqual(STAGE_BY_ID["S4"].mean_latency_ms, 4.20)
        self.assertAlmostEqual(STAGE_BY_ID["S5"].mean_latency_ms, 340.0)
        self.assertAlmostEqual(STAGE_BY_ID["S6"].mean_latency_ms, 1950.0)
        self.assertEqual(STAGE_BY_ID["S1"].generative_tokens_per_call, 0)
        self.assertEqual(STAGE_BY_ID["S2"].generative_tokens_per_call, 0)
        self.assertEqual(STAGE_BY_ID["S3"].generative_tokens_per_call, 0)
        self.assertIn("BitNet-b1.58-2B", STAGE_BY_ID["S4"].backing_primitives_or_models)
        self.assertIn("ollama_cloud/gemma4:31b", STAGE_BY_ID["S5"].backing_primitives_or_models)

    def test_slot_family_1_six_stage_cascade_7_layer_envelope(self) -> None:
        slot = CloudSixStageActionFacilitatorCascadeSlot()
        res_s1 = slot.execute_cloud_action_cascade("CLOUD_REQ_01", request_id="test_s1_req")
        self.assertTrue(res_s1.accepted)
        self.assertEqual(res_s1.slot_id, SLOT_SIX_STAGE_CLOUD_CASCADE)
        self.assertEqual(res_s1.selected_engine, ENGINE_S1_STRING_TRIE)
        self.assertEqual(res_s1.fallback_chain_tried, (ENGINE_S1_STRING_TRIE,))
        self.assertEqual(set(res_s1.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertTrue(all(v == "full" for v in res_s1.layer_verdicts.values()))
        self.assertTrue(res_s1.output["resolved_without_gpu_llm"])
        self.assertTrue(res_s1.output["nested_optimizer_accepted"])

        res_s4 = slot.execute_cloud_action_cascade("CLOUD_REQ_35", request_id="test_s4_req")
        self.assertTrue(res_s4.accepted)
        self.assertEqual(res_s4.selected_engine, ENGINE_S4_CLOUD_CPU_LLM)
        self.assertEqual(
            res_s4.fallback_chain_tried,
            (
                ENGINE_S1_STRING_TRIE,
                ENGINE_S2_GREP_AST,
                ENGINE_S3_SEMANTIC_LSH,
                ENGINE_S4_CLOUD_CPU_LLM,
            ),
        )
        self.assertTrue(res_s4.output["resolved_without_gpu_llm"])

        res_s5 = slot.execute_cloud_action_cascade("CLOUD_REQ_45", request_id="test_s5_req")
        self.assertTrue(res_s5.accepted)
        self.assertEqual(res_s5.selected_engine, ENGINE_S5_OLLAMA_CLOUD)
        self.assertFalse(res_s5.output["resolved_without_gpu_llm"])

    def test_slot_family_2_early_exit_optimizer_and_receipt_savings(self) -> None:
        opt = CascadeEarlyExitAndTelemetryOptimizerSlot()
        res = opt.evaluate_early_exit_and_emit_receipt(
            "CLOUD_REQ_12",
            request_id="test_opt_s2",
            preferred_engine=ENGINE_PARETO_TELEMETRY,
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_CASCADE_EARLY_EXIT_OPTIMIZER)
        self.assertEqual(res.selected_engine, ENGINE_PARETO_TELEMETRY)
        self.assertEqual(res.fallback_chain_tried, EARLY_EXIT_OPTIMIZER_ENGINE_ORDER)
        self.assertTrue(res.output["early_exit_triggered"])
        self.assertEqual(res.output["exited_at_stage_id"], "S2")
        self.assertEqual(res.output["stages_evaluated"], ["S1", "S2"])
        self.assertEqual(res.output["stages_skipped"], ["S3", "S4", "S5", "S6"])
        self.assertTrue(res.output["gamma_meets_or_exceeds_tau"])
        self.assertAlmostEqual(res.output["cumulative_latency_ms"], 0.20, places=2)
        self.assertGreater(res.output["latency_saved_vs_full_cascade_ms"], 2290.0)
        self.assertGreater(res.output["cost_saved_vs_full_cascade_usd"], 0.0110)

    def test_envelope_idempotency_and_carrier_handshake_guards(self) -> None:
        slot = CloudSixStageActionFacilitatorCascadeSlot()
        r1 = slot.execute_cloud_action_cascade("CLOUD_REQ_01", request_id="idem_req_01")
        r2 = slot.execute_cloud_action_cascade("CLOUD_REQ_01", request_id="idem_req_01")
        self.assertEqual(r1.payload_digest, r2.payload_digest)
        self.assertTrue(r2.accepted)

        conflict = slot.execute_cloud_action_cascade("CLOUD_REQ_02", request_id="idem_req_01")
        self.assertFalse(conflict.accepted)
        self.assertIsNotNone(conflict.refusal)
        assert conflict.refusal is not None
        self.assertEqual(conflict.refusal.code, "idempotency_payload_conflict")

        bad_schema_req = EnvelopeInvocationRequest(
            slot_id=SLOT_SIX_STAGE_CLOUD_CASCADE,
            request_id="bad_schema_req",
            payload={"cloud_request_id": "CLOUD_REQ_01"},
            schema_version="unsupported.schema.v0",
        )
        bad_schema_res = slot.envelope.execute(bad_schema_req, slot._dispatch)
        self.assertFalse(bad_schema_res.accepted)
        assert bad_schema_res.refusal is not None
        self.assertEqual(bad_schema_res.refusal.code, "carrier_schema_invalid")

    def test_60_request_cloud_cascade_benchmark_metrics(self) -> None:
        self.assertEqual(len(ALL_60_CLOUD_CASCADE_REQUESTS), 60)
        bench = run_six_stage_cloud_cascade_benchmark()
        self.assertEqual(bench["total_requests"], 60)
        self.assertEqual(bench["requests_per_complexity_tier"], 10)
        self.assertTrue(bench["all_60_requests_executed_through_7_layer_envelope"])

        always_llm = bench["always_llm_cloud_baseline_without_string_grep_cascade"]
        self.assertEqual(always_llm["engine_id"], ENGINE_ALWAYS_LLM_BASELINE)
        self.assertEqual(always_llm["llm_invocation_rate_pct"], "100.0%")
        self.assertEqual(always_llm["mean_latency_ms"], 1420.0)
        self.assertEqual(always_llm["total_batch_cost_usd"], 0.4860)

        grep_only = bench["unverified_string_grep_only_baseline"]
        self.assertEqual(grep_only["engine_id"], ENGINE_UNVERIFIED_STRING_GREP_BASELINE)
        self.assertEqual(grep_only["mean_latency_ms"], 0.10)
        self.assertEqual(grep_only["total_batch_cost_usd"], 0.0)
        self.assertEqual(grep_only["verified_pass_rate_pct"], "33.3%")

        cascade = bench["baltor_6stage_string_grep_semantic_cpu_ollama_cascade"]
        self.assertEqual(cascade["engine_id"], ENGINE_BALTOR_6STAGE_CASCADE)
        self.assertEqual(cascade["verified_pass_rate_pct"], "98.3%")
        self.assertEqual(cascade["requests_passed"], 59)
        self.assertEqual(cascade["requests_resolved_in_s1_to_s4_without_gpu_llm"], 41)
        self.assertEqual(cascade["resolved_without_gpu_llm_pct"], "68.3%")
        self.assertEqual(cascade["frontier_s6_escalation_count"], 2)
        self.assertEqual(cascade["frontier_s6_escalation_rate_pct"], "3.3%")
        self.assertEqual(cascade["median_latency_ms"], 42.5)
        self.assertEqual(cascade["total_batch_cost_usd"], 0.0142)
        self.assertEqual(cascade["cost_reduction_vs_always_llm_pct"], "97.1%")

    def test_four_known_wrong_preflight_refusal_controls(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "premature_early_exit_on_unverified_stage_refused",
            "direct_frontier_llm_bypass_without_cascade_refused",
            "catastrophic_backtracking_redos_regex_refused",
            "unrecorded_model_usage_in_cascade_stage_refused",
        }
        observed_codes = {c["actual_refusal_code"] for c in kw["controls"]}
        self.assertEqual(observed_codes, expected_codes)
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertEqual(ctrl["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(ctrl["refused_before_engine"])


if __name__ == "__main__":
    unittest.main()
