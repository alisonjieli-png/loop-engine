"""Unit tests for the Adversarial Benchmark Validation (`AV` Classifier AUC),
Anti-Benchmaxing / Goodharting Detector, Critical Benchmark Commentary &
Hardware-Grounded Real-User-Experience (`RUX`) Evaluator Engine Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from adversarial_benchmark_validation_anti_benchmaxing_and_real_ux_engines import (  # noqa: E402
    ADVERSARIAL_BENCHMARK_ADAPTER,
    ALL_6_HARDWARE_PROFILES,
    ALL_8_BENCHMAXING_VECTORS,
    ALL_36_BENCHMARK_AND_RUX_SCENARIOS,
    BENCHMAX_VECTOR_B01,
    BENCHMAX_VECTOR_B02,
    BENCHMAX_VECTOR_B03,
    BENCHMAX_VECTOR_B04,
    BENCHMAX_VECTOR_B05,
    BENCHMAX_VECTOR_B06,
    BENCHMAX_VECTOR_B07,
    BENCHMAX_VECTOR_B08,
    COVERAGE_LAYERS,
    ENGINE_BALTOR_ADVERSARIAL_VALIDATED_AND_HARDWARE_GROUNDED_RUX_SUITE,
    ENGINE_BALTOR_REAL_USER_EXPERIENCE_COMPOSITE_SCORER,
    ENGINE_EIGHT_VECTOR_ANTI_BENCHMAXING_AND_GOODHART_DETECTOR,
    ENGINE_LEADERBOARD_BENCHMAXED_SELECTION_BASELINE,
    HARDWARE_RUX_ADAPTER,
    HW1_CONSUMER_CPU_ONLY_LAPTOP_16GB_RAM,
    HW2_SINGLE_CONSUMER_GPU_16GB_24GB_VRAM,
    HW3_APPLE_SILICON_UNIFIED_MEMORY_32GB_128GB,
    HW4_PAIRED_SOVEREIGN_HOME_SERVER_LAN_ENDPOINT,
    HW5_OLLAMA_CLOUD_WORKHORSE_TIER,
    HW6_BYOK_FRONTIER_BURST_ESCALATION_TIER,
    LAYER_PREFLIGHT,
    SLOT_ADVERSARIAL_BENCHMARK_VALIDATION_AND_ANTI_BENCHMAXING,
    SLOT_HARDWARE_GROUNDED_REAL_USER_EXPERIENCE_EVALUATOR,
    compute_baltor_rux_composite_score,
    detect_eight_vector_benchmaxing_pathologies,
    evaluate_adversarial_validation_and_counterfactual_drop,
    evaluate_adversarial_benchmark_validation_and_real_ux_suite,
    invoke_adversarial_benchmark_validation_slot,
    invoke_hardware_grounded_rux_slot,
    run_known_wrong_refusal_controls,
    synthesize_24_benchmark_critique_cards,
)


class AdversarialBenchmarkValidationAntiBenchmaxingAndRealUxTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 36-scenario benchmarks, and 4 known-wrong controls."""

    def test_adversarial_validation_auc_and_counterfactual_drop(self) -> None:
        ecological = evaluate_adversarial_validation_and_counterfactual_drop(
            "baltor_brownfield_repo_suite",
            bench_feature_distance=0.08,
            canonical_score=0.96,
            counterfactual_score=0.94,
        )
        self.assertGreaterEqual(ecological.av_auc, 0.50)
        self.assertLessEqual(ecological.av_auc, 0.58)
        self.assertEqual(ecological.ecological_validity_band, "high_ecological_validity")
        self.assertEqual(ecological.delta_counterfactual, 0.02)
        self.assertFalse(ecological.memorization_or_contamination_flagged)

        synthetic_toy = evaluate_adversarial_validation_and_counterfactual_drop(
            "HumanEval_isolated_snippets",
            bench_feature_distance=0.86,
            canonical_score=0.92,
            counterfactual_score=0.57,
        )
        self.assertGreaterEqual(synthetic_toy.av_auc, 0.80)
        self.assertEqual(
            synthetic_toy.ecological_validity_band,
            "severe_synthetic_distribution_shift",
        )
        self.assertEqual(synthetic_toy.delta_counterfactual, 0.35)
        self.assertTrue(synthetic_toy.memorization_or_contamination_flagged)

    def test_eight_vector_anti_benchmaxing_and_goodhart_detector(self) -> None:
        self.assertEqual(len(ALL_8_BENCHMAXING_VECTORS), 8)
        benchmaxed = detect_eight_vector_benchmaxing_pathologies(
            {
                "counterfactual_drop": 0.34,
                "response_length_ratio_vs_concise": 3.1,
                "sycophantic_opener_rate": 0.42,
                "pass_at_k_samples": 100,
                "cost_per_task_usd": 350.0,
                "unseen_repo_transfer_drop": 0.38,
                "multi_hop_24k_reasoning_drop": 0.45,
                "benign_engineering_refusal_rate": 0.44,
                "brownfield_100k_loc_drop": 0.41,
                "edge_q4_quantization_drop": 0.28,
            }
        )
        self.assertTrue(benchmaxed["goodharting_detected"])
        self.assertEqual(benchmaxed["triggered_count"], 8)
        for vec in (
            BENCHMAX_VECTOR_B01,
            BENCHMAX_VECTOR_B02,
            BENCHMAX_VECTOR_B03,
            BENCHMAX_VECTOR_B04,
            BENCHMAX_VECTOR_B05,
            BENCHMAX_VECTOR_B06,
            BENCHMAX_VECTOR_B07,
            BENCHMAX_VECTOR_B08,
        ):
            self.assertIn(vec, benchmaxed["triggered_vectors"])

        clean = detect_eight_vector_benchmaxing_pathologies({"counterfactual_drop": 0.02})
        self.assertFalse(clean["goodharting_detected"])
        self.assertEqual(clean["triggered_count"], 0)

    def test_24_benchmark_critique_cards_and_required_fields(self) -> None:
        cards = synthesize_24_benchmark_critique_cards(elastic_budget_bytes=65536)
        self.assertEqual(len(cards), 24)
        names = {c.benchmark_name for c in cards}
        for expected in (
            "SWE-bench Verified",
            "HumanEval / MBPP",
            "LiveCodeBench",
            "Aider Polyglot",
            "LMSYS Chatbot Arena",
            "AlpacaEval 2.0 / Arena-Hard",
            "MMLU-Pro / GPQA-Diamond",
            "ARC-AGI",
            "GSM8K vs GSM-Symbolic",
            "RULER / Needle-in-a-Haystack",
            "OSWorld / WebArena",
            "ForecastBench",
            "GAIA",
            "TAU-bench",
        ):
            self.assertIn(expected, names)
        for card in cards:
            self.assertTrue(card.what_it_claims_to_measure)
            self.assertTrue(card.how_vendors_benchmax_it)
            self.assertGreaterEqual(card.adversarial_validation_auc_vs_real_work, 0.50)
            self.assertTrue(card.what_breaks_in_real_user_experience)
            self.assertTrue(card.baltor_real_ux_replacement_protocol)
            self.assertEqual(card.feed_channel, "agentfeeds.si/benchmark-critiques")

    def test_six_hardware_profiles_and_baltor_rux_composite_score(self) -> None:
        self.assertEqual(len(ALL_6_HARDWARE_PROFILES), 6)
        for hw in (
            HW1_CONSUMER_CPU_ONLY_LAPTOP_16GB_RAM,
            HW2_SINGLE_CONSUMER_GPU_16GB_24GB_VRAM,
            HW3_APPLE_SILICON_UNIFIED_MEMORY_32GB_128GB,
            HW4_PAIRED_SOVEREIGN_HOME_SERVER_LAN_ENDPOINT,
            HW5_OLLAMA_CLOUD_WORKHORSE_TIER,
            HW6_BYOK_FRONTIER_BURST_ESCALATION_TIER,
        ):
            self.assertIn(hw, ALL_6_HARDWARE_PROFILES)

        rux = compute_baltor_rux_composite_score(
            model_name="Gemma 4",
            hardware_profile_id=HW5_OLLAMA_CLOUD_WORKHORSE_TIER,
            counterfactual_pass_rate=0.96,
            zero_human_bailout_rate=0.98,
            coding_reset_rate=0.02,
            peak_memory_gb=0.3,
            p95_latency_ms=410.0,
            cost_per_verified_outcome_usd=0.01,
            benchmax_inflation_penalty=0.0,
        )
        self.assertTrue(rux["memory_fits_budget"])
        self.assertTrue(rux["latency_fits_budget"])
        self.assertGreaterEqual(rux["rux_composite_score"], 0.90)
        self.assertTrue(rux["recommended_for_profile"])

    def test_thin_component_adapter_contract_receipt_and_hot_swap(self) -> None:
        c1 = ADVERSARIAL_BENCHMARK_ADAPTER.inspect_contract()
        c2 = HARDWARE_RUX_ADAPTER.inspect_contract()
        self.assertEqual(c1["slot_id"], SLOT_ADVERSARIAL_BENCHMARK_VALIDATION_AND_ANTI_BENCHMAXING)
        self.assertEqual(c2["slot_id"], SLOT_HARDWARE_GROUNDED_REAL_USER_EXPERIENCE_EVALUATOR)
        self.assertLess(c1["loc"], 30)

        r1 = invoke_adversarial_benchmark_validation_slot({"benchmark_id": "SWE-bench Verified"})
        r2 = invoke_hardware_grounded_rux_slot({"model_name": "Qwen3-Coder"})
        self.assertTrue(ADVERSARIAL_BENCHMARK_ADAPTER.verify_receipt(r1))
        self.assertTrue(HARDWARE_RUX_ADAPTER.verify_receipt(r2))
        self.assertEqual(set(r1.layer_verdicts.keys()), set(COVERAGE_LAYERS))

        swapped_s1 = ADVERSARIAL_BENCHMARK_ADAPTER.swap_engine(
            ENGINE_EIGHT_VECTOR_ANTI_BENCHMAXING_AND_GOODHART_DETECTOR
        )
        self.assertEqual(
            swapped_s1.engine_order[0],
            ENGINE_EIGHT_VECTOR_ANTI_BENCHMAXING_AND_GOODHART_DETECTOR,
        )
        swapped_s2 = HARDWARE_RUX_ADAPTER.swap_engine(
            ENGINE_BALTOR_REAL_USER_EXPERIENCE_COMPOSITE_SCORER
        )
        self.assertEqual(
            swapped_s2.engine_order[0],
            ENGINE_BALTOR_REAL_USER_EXPERIENCE_COMPOSITE_SCORER,
        )

    def test_four_known_wrong_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        expected_codes = {
            "benchmaxed_or_contaminated_claim_blocked": "benchmaxed_or_contaminated_claim_refused",
            "hardware_memory_budget_exceeded_blocked": "hardware_memory_budget_exceeded_refused",
            "undisclosed_pass_at_k_compute_inflation_blocked": "undisclosed_pass_at_k_compute_inflation_refused",
            "synthetic_benchmark_distribution_shift_blocked": "synthetic_benchmark_distribution_shift_refused",
        }
        for probe_id, expected_code in expected_codes.items():
            probe = controls["probes"][probe_id]
            self.assertFalse(probe["accepted"])
            self.assertEqual(probe["refused_by"], LAYER_PREFLIGHT)
            self.assertEqual(probe["refusal_code"], expected_code)
            self.assertTrue(probe["blocked_before_engine"])

    def test_full_36_scenario_benchmark_suite(self) -> None:
        self.assertEqual(len(ALL_36_BENCHMARK_AND_RUX_SCENARIOS), 36)
        report = evaluate_adversarial_benchmark_validation_and_real_ux_suite()
        self.assertEqual(report["scenario_count"], 36)
        self.assertEqual(report["benchmax_cohort_count"], 18)
        self.assertEqual(report["baltor_rux_cohort_count"], 18)
        self.assertEqual(report["critique_card_count"], 24)
        self.assertTrue(report["all_scenarios_accepted"])
        self.assertTrue(report["hot_swap_verified"])
        self.assertTrue(report["known_wrong_controls"]["all_blocked_at_preflight"])

        base = report["benchmarks"][ENGINE_LEADERBOARD_BENCHMAXED_SELECTION_BASELINE]
        suite = report["benchmarks"][
            ENGINE_BALTOR_ADVERSARIAL_VALIDATED_AND_HARDWARE_GROUNDED_RUX_SUITE
        ]
        self.assertEqual(base["headline_static_benchmark_score_pct"], 91.4)
        self.assertEqual(base["real_brownfield_user_pass_rate_pct"], 48.2)
        self.assertEqual(base["counterfactual_perturbation_drop_pct"], 34.5)
        self.assertEqual(base["hardware_vram_latency_failure_rate_pct"], 41.7)
        self.assertEqual(suite["benchmaxed_or_contaminated_claim_detection_rate_pct"], 100.0)
        self.assertEqual(suite["counterfactual_perturbation_drop_pct"], 2.4)
        self.assertEqual(suite["hardware_vram_latency_fit_rate_pct"], 100.0)
        self.assertEqual(suite["real_brownfield_user_pass_rate_pct"], 96.7)


if __name__ == "__main__":
    unittest.main()
